from datetime import date

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse, StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.docgen import generate_afs_docx
from app.models import (
    AFSCategory,
    Entity,
    FinancialYear,
    IFRSEdition,
    LoanDirection,
    PPEAsset,
    PolicyElection,
    ShareholderLoan,
    TaxBracket,
    TaxComputationMeta,
    TaxDifference,
    TrialBalanceLine,
    POLICY_AREAS,
)
from app.reporting import build_report
from app.templating import templates

router = APIRouter()


def _num(v) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


@router.get("/entities/{entity_id}/years/new")
def new_year_form(entity_id: int, request: Request, db: Session = Depends(get_db)):
    entity = db.get(Entity, entity_id)
    return templates.TemplateResponse("year_new.html", {"request": request, "entity": entity})


@router.post("/entities/{entity_id}/years/new")
async def create_year(entity_id: int, request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    fy = FinancialYear(
        entity_id=entity_id,
        year_end_date=date.fromisoformat(form["year_end_date"]),
        comparative_year_end_date=date.fromisoformat(form["comparative_year_end_date"]) if form.get("comparative_year_end_date") else None,
        date_approved=date.fromisoformat(form["date_approved"]) if form.get("date_approved") else None,
        ifrs_edition=IFRSEdition(form.get("ifrs_edition", IFRSEdition.SECOND_2015.value)),
        opening_retained_income=_num(form.get("opening_retained_income")),
        opening_share_capital=_num(form.get("opening_share_capital")),
        opening_cash=_num(form.get("opening_cash")),
        prior_year_depreciation_charge=_num(form.get("prior_year_depreciation_charge")),
    )
    db.add(fy)
    db.flush()
    db.add(TaxComputationMeta(financial_year_id=fy.id, assessed_loss_brought_forward=0.0))
    for area in POLICY_AREAS:
        db.add(PolicyElection(financial_year_id=fy.id, policy_area=area, applicable=False))
    db.commit()
    return RedirectResponse(f"/years/{fy.id}", status_code=303)


@router.get("/years/{year_id}")
def year_detail(year_id: int, request: Request, db: Session = Depends(get_db)):
    fy = db.get(FinancialYear, year_id)
    report = None
    error = None
    try:
        report = build_report(fy)
    except Exception as e:
        error = str(e)
    return templates.TemplateResponse(
        "financial_year_detail.html",
        {
            "request": request,
            "fy": fy,
            "entity": fy.entity,
            "report": report,
            "error": error,
            "afs_categories": list(AFSCategory),
            "loan_directions": list(LoanDirection),
            "ifrs_editions": list(IFRSEdition),
        },
    )


@router.post("/years/{year_id}/scalars")
async def update_year_scalars(year_id: int, request: Request, db: Session = Depends(get_db)):
    fy = db.get(FinancialYear, year_id)
    form = await request.form()
    fy.year_end_date = date.fromisoformat(form["year_end_date"])
    fy.comparative_year_end_date = date.fromisoformat(form["comparative_year_end_date"]) if form.get("comparative_year_end_date") else None
    fy.date_approved = date.fromisoformat(form["date_approved"]) if form.get("date_approved") else None
    fy.ifrs_edition = IFRSEdition(form.get("ifrs_edition", IFRSEdition.SECOND_2015.value))
    fy.opening_retained_income = _num(form.get("opening_retained_income"))
    fy.opening_share_capital = _num(form.get("opening_share_capital"))
    fy.opening_cash = _num(form.get("opening_cash"))
    fy.prior_year_depreciation_charge = _num(form.get("prior_year_depreciation_charge"))
    db.commit()
    return RedirectResponse(f"/years/{year_id}#basics", status_code=303)


@router.post("/years/{year_id}/trial-balance")
async def update_trial_balance(year_id: int, request: Request, db: Session = Depends(get_db)):
    fy = db.get(FinancialYear, year_id)
    form = await request.form()
    for line in list(fy.trial_balance_lines):
        db.delete(line)
    db.flush()

    names = form.getlist("tb_account_name")
    categories = form.getlist("tb_afs_category")
    currents = form.getlist("tb_current_year_amount")
    priors = form.getlist("tb_prior_year_amount")
    notes = form.getlist("tb_notes")
    for i, name in enumerate(names):
        if not name.strip():
            continue
        db.add(
            TrialBalanceLine(
                financial_year_id=fy.id,
                account_name=name.strip(),
                afs_category=AFSCategory(categories[i]),
                current_year_amount=_num(currents[i] if i < len(currents) else 0),
                prior_year_amount=_num(priors[i] if i < len(priors) else 0),
                notes=notes[i] if i < len(notes) and notes[i] else None,
            )
        )
    db.commit()
    return RedirectResponse(f"/years/{year_id}#trial-balance", status_code=303)


@router.post("/years/{year_id}/ppe")
async def update_ppe(year_id: int, request: Request, db: Session = Depends(get_db)):
    fy = db.get(FinancialYear, year_id)
    form = await request.form()
    for asset in list(fy.ppe_assets):
        db.delete(asset)
    db.flush()

    categories = form.getlist("ppe_asset_category")
    methods = form.getlist("ppe_depreciation_method")
    lives = form.getlist("ppe_useful_life_years")
    opening_costs = form.getlist("ppe_opening_cost")
    additions = form.getlist("ppe_additions")
    disposals = form.getlist("ppe_disposals_cost")
    opening_accs = form.getlist("ppe_opening_accumulated_depreciation")
    dep_charges = form.getlist("ppe_depreciation_charge")
    acc_disposals = form.getlist("ppe_accumulated_depreciation_on_disposals")

    for i, category in enumerate(categories):
        if not category.strip():
            continue
        db.add(
            PPEAsset(
                financial_year_id=fy.id,
                asset_category=category.strip(),
                depreciation_method=methods[i] if i < len(methods) else "Straight line",
                useful_life_years=_num(lives[i] if i < len(lives) else 0),
                opening_cost=_num(opening_costs[i] if i < len(opening_costs) else 0),
                additions=_num(additions[i] if i < len(additions) else 0),
                disposals_cost=_num(disposals[i] if i < len(disposals) else 0),
                opening_accumulated_depreciation=_num(opening_accs[i] if i < len(opening_accs) else 0),
                depreciation_charge=_num(dep_charges[i] if i < len(dep_charges) else 0),
                accumulated_depreciation_on_disposals=_num(acc_disposals[i] if i < len(acc_disposals) else 0),
            )
        )
    db.commit()
    return RedirectResponse(f"/years/{year_id}#ppe", status_code=303)


@router.post("/years/{year_id}/loans")
async def update_loans(year_id: int, request: Request, db: Session = Depends(get_db)):
    fy = db.get(FinancialYear, year_id)
    form = await request.form()
    for loan in list(fy.shareholder_loans):
        db.delete(loan)
    db.flush()

    names = form.getlist("loan_shareholder_name")
    directions = form.getlist("loan_direction")
    openings = form.getlist("loan_opening_balance")
    advances = form.getlist("loan_advances")
    repayments = form.getlist("loan_repayments")
    rates = form.getlist("loan_interest_rate_pa")
    interest = form.getlist("loan_interest_charged")
    secured = form.getlist("loan_secured_or_unsecured")
    terms = form.getlist("loan_repayment_terms")

    for i, name in enumerate(names):
        if not name.strip():
            continue
        db.add(
            ShareholderLoan(
                financial_year_id=fy.id,
                shareholder_name=name.strip(),
                direction=LoanDirection(directions[i] if i < len(directions) else LoanDirection.TO.value),
                opening_balance=_num(openings[i] if i < len(openings) else 0),
                advances=_num(advances[i] if i < len(advances) else 0),
                repayments=_num(repayments[i] if i < len(repayments) else 0),
                interest_rate_pa=_num(rates[i] if i < len(rates) else 0),
                interest_charged=_num(interest[i] if i < len(interest) else 0),
                secured_or_unsecured=secured[i] if i < len(secured) else "Unsecured",
                repayment_terms=terms[i] if i < len(terms) else None,
            )
        )
    db.commit()
    return RedirectResponse(f"/years/{year_id}#loans", status_code=303)


@router.post("/years/{year_id}/tax")
async def update_tax(year_id: int, request: Request, db: Session = Depends(get_db)):
    fy = db.get(FinancialYear, year_id)
    form = await request.form()

    if fy.tax_computation_meta is None:
        db.add(TaxComputationMeta(financial_year_id=fy.id, assessed_loss_brought_forward=_num(form.get("assessed_loss_brought_forward"))))
    else:
        fy.tax_computation_meta.assessed_loss_brought_forward = _num(form.get("assessed_loss_brought_forward"))

    for diff in list(fy.tax_differences):
        db.delete(diff)
    for bracket in list(fy.tax_brackets):
        db.delete(bracket)
    db.flush()

    descriptions = form.getlist("td_description")
    amounts = form.getlist("td_amount")
    for i, desc in enumerate(descriptions):
        if not desc.strip():
            continue
        db.add(TaxDifference(financial_year_id=fy.id, description=desc.strip(), amount=_num(amounts[i] if i < len(amounts) else 0)))

    lowers = form.getlist("tb_lower_limit")
    uppers = form.getlist("tb_upper_limit")
    rates = form.getlist("tb_rate")
    for i, lower in enumerate(lowers):
        if lower == "":
            continue
        upper_raw = uppers[i] if i < len(uppers) else ""
        db.add(
            TaxBracket(
                financial_year_id=fy.id,
                lower_limit=_num(lower),
                upper_limit=None if not upper_raw.strip() else _num(upper_raw),
                rate=_num(rates[i] if i < len(rates) else 0),
            )
        )
    db.commit()
    return RedirectResponse(f"/years/{year_id}#tax", status_code=303)


@router.post("/years/{year_id}/policies")
async def update_policies(year_id: int, request: Request, db: Session = Depends(get_db)):
    fy = db.get(FinancialYear, year_id)
    form = await request.form()
    applicable_areas = set(form.getlist("policy_applicable"))
    notes = form.getlist("policy_notes")
    areas = form.getlist("policy_area")

    for pe in list(fy.policy_elections):
        db.delete(pe)
    db.flush()

    for i, area in enumerate(areas):
        db.add(
            PolicyElection(
                financial_year_id=fy.id,
                policy_area=area,
                applicable=area in applicable_areas,
                notes=notes[i] if i < len(notes) and notes[i] else None,
            )
        )
    db.commit()
    return RedirectResponse(f"/years/{year_id}#policies", status_code=303)


@router.get("/years/{year_id}/generate")
def generate_document(year_id: int, db: Session = Depends(get_db)):
    fy = db.get(FinancialYear, year_id)
    report = build_report(fy)
    if not report.is_valid:
        return RedirectResponse(f"/years/{year_id}#validation", status_code=303)
    buf = generate_afs_docx(report)
    filename = f"{fy.entity.company_name.replace(' ', '_')}_AFS_{fy.year_end_date.isoformat()}.docx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/years/{year_id}/delete")
def delete_year(year_id: int, db: Session = Depends(get_db)):
    fy = db.get(FinancialYear, year_id)
    entity_id = fy.entity_id
    db.delete(fy)
    db.commit()
    return RedirectResponse(f"/entities/{entity_id}/edit", status_code=303)


@router.post("/years/{year_id}/roll-forward")
def roll_forward(year_id: int, db: Session = Depends(get_db)):
    from app.rollforward import create_next_year

    fy = db.get(FinancialYear, year_id)
    report = build_report(fy)
    new_fy = create_next_year(db, fy, report)
    return RedirectResponse(f"/years/{new_fy.id}", status_code=303)


@router.get("/years/{year_id}/export-workbook")
def export_workbook(year_id: int, db: Session = Depends(get_db)):
    from app.exporter import export_workbook_for_year

    fy = db.get(FinancialYear, year_id)
    report = build_report(fy)
    buf = export_workbook_for_year(fy, report)
    filename = f"{fy.entity.company_name.replace(' ', '_')}_FY{fy.year_end_date.year}_AFS-Input.xlsx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
