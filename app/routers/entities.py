from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Director, Entity, IFRSEdition, ReportType
from app.reporting import build_report
from app.templating import templates

router = APIRouter()


@router.get("/")
def dashboard(request: Request, db: Session = Depends(get_db)):
    entities = db.query(Entity).order_by(Entity.company_name).all()
    rows = []
    for entity in entities:
        years = []
        for fy in entity.financial_years:
            valid = None
            try:
                report = build_report(fy)
                valid = report.is_valid
            except Exception:
                valid = False
            years.append({"fy": fy, "valid": valid})
        rows.append({"entity": entity, "years": years})
    return templates.TemplateResponse("dashboard.html", {"request": request, "rows": rows})


@router.get("/entities/new")
def new_entity_form(request: Request):
    return templates.TemplateResponse(
        "entity_form.html",
        {"request": request, "entity": None, "report_types": list(ReportType), "ifrs_editions": list(IFRSEdition)},
    )


@router.get("/entities/{entity_id}/edit")
def edit_entity_form(entity_id: int, request: Request, db: Session = Depends(get_db)):
    entity = db.get(Entity, entity_id)
    return templates.TemplateResponse(
        "entity_form.html",
        {"request": request, "entity": entity, "report_types": list(ReportType), "ifrs_editions": list(IFRSEdition)},
    )


@router.post("/entities/new")
@router.post("/entities/{entity_id}/edit")
async def save_entity(request: Request, entity_id: int | None = None, db: Session = Depends(get_db)):
    form = await request.form()

    if entity_id:
        entity = db.get(Entity, entity_id)
    else:
        entity = Entity(registration_number="")
        db.add(entity)

    entity.company_name = form.get("company_name", "").strip()
    entity.registration_number = form.get("registration_number", "").strip()
    entity.tax_reference_number = form.get("tax_reference_number") or None
    entity.vat_number = form.get("vat_number") or None
    entity.country_of_incorporation = form.get("country_of_incorporation") or "South Africa"
    entity.nature_of_business = form.get("nature_of_business") or None
    entity.registered_office_address = form.get("registered_office_address") or None
    entity.business_address = form.get("business_address") or None
    entity.postal_address = form.get("postal_address") or None
    entity.bankers = form.get("bankers") or None
    entity.practitioner_name = form.get("practitioner_name") or None
    entity.practitioner_firm = form.get("practitioner_firm") or None
    entity.report_type = ReportType(form.get("report_type", ReportType.COMPILATION.value))
    entity.is_sbc = form.get("is_sbc") == "on"

    incorp = form.get("incorporation_date") or None
    cert = form.get("certificate_to_commence_business_date") or None
    from datetime import date as _date

    entity.incorporation_date = _date.fromisoformat(incorp) if incorp else None
    entity.certificate_to_commence_business_date = _date.fromisoformat(cert) if cert else None

    db.flush()

    # Directors: full replace from the submitted repeating rows.
    for d in list(entity.directors):
        db.delete(d)
    db.flush()

    names = form.getlist("director_full_name")
    nationalities = form.getlist("director_nationality")
    appointed = form.getlist("director_date_appointed")
    resigned = form.getlist("director_date_resigned")
    signs = form.getlist("director_signs_approval")  # values are the row-index of checked boxes
    for i, name in enumerate(names):
        if not name.strip():
            continue
        db.add(
            Director(
                entity_id=entity.id,
                full_name=name.strip(),
                nationality=nationalities[i] if i < len(nationalities) else None,
                date_appointed=_date.fromisoformat(appointed[i]) if i < len(appointed) and appointed[i] else None,
                date_resigned=_date.fromisoformat(resigned[i]) if i < len(resigned) and resigned[i] else None,
                signs_approval=str(i) in signs,
            )
        )

    db.commit()
    return RedirectResponse(f"/entities/{entity.id}/edit", status_code=303)


@router.post("/entities/{entity_id}/delete")
def delete_entity(entity_id: int, db: Session = Depends(get_db)):
    entity = db.get(Entity, entity_id)
    if entity:
        db.delete(entity)
        db.commit()
    return RedirectResponse("/", status_code=303)
