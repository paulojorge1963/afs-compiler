""""Create Next Year" (user flow 4): clones an entity's financial year forward,
carrying closing balances into the new year's opening balances and pre-populating
the prior-year comparative column, so only the new year's movements need typing.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import (
    POLICY_AREAS,
    FinancialYear,
    PPEAsset,
    PolicyElection,
    ShareholderLoan,
    TaxBracket,
    TaxComputationMeta,
    TrialBalanceLine,
)
from app.reporting import ReportData


def create_next_year(db: Session, fy: FinancialYear, report: ReportData) -> FinancialYear:
    next_year_end = fy.year_end_date.replace(year=fy.year_end_date.year + 1)

    new_fy = FinancialYear(
        entity_id=fy.entity_id,
        year_end_date=next_year_end,
        comparative_year_end_date=fy.year_end_date,
        date_approved=None,
        ifrs_edition=fy.ifrs_edition,
        opening_retained_income=report.balance_sheet_prior.retained_income,
        opening_share_capital=report.balance_sheet_prior.share_capital,
        opening_cash=report.balance_sheet_prior.cash,
        prior_year_depreciation_charge=report.income_current.depreciation,
    )
    db.add(new_fy)
    db.flush()

    for line in fy.trial_balance_lines:
        db.add(
            TrialBalanceLine(
                financial_year_id=new_fy.id,
                account_name=line.account_name,
                afs_category=line.afs_category,
                current_year_amount=0.0,
                prior_year_amount=line.current_year_amount,
                notes=line.notes,
            )
        )

    for asset in fy.ppe_assets:
        db.add(
            PPEAsset(
                financial_year_id=new_fy.id,
                asset_category=asset.asset_category,
                depreciation_method=asset.depreciation_method,
                useful_life_years=asset.useful_life_years,
                opening_cost=asset.closing_cost,
                additions=0.0,
                disposals_cost=0.0,
                opening_accumulated_depreciation=asset.closing_accumulated_depreciation,
                depreciation_charge=0.0,
                accumulated_depreciation_on_disposals=0.0,
            )
        )

    for loan in fy.shareholder_loans:
        db.add(
            ShareholderLoan(
                financial_year_id=new_fy.id,
                shareholder_name=loan.shareholder_name,
                direction=loan.direction,
                opening_balance=loan.closing_balance,
                advances=0.0,
                repayments=0.0,
                interest_rate_pa=loan.interest_rate_pa,
                interest_charged=0.0,
                secured_or_unsecured=loan.secured_or_unsecured,
                repayment_terms=loan.repayment_terms,
            )
        )

    db.add(
        TaxComputationMeta(
            financial_year_id=new_fy.id,
            assessed_loss_brought_forward=report.tax.assessed_loss_carried_forward,
        )
    )
    for bracket in fy.tax_brackets:
        db.add(
            TaxBracket(
                financial_year_id=new_fy.id,
                lower_limit=bracket.lower_limit,
                upper_limit=bracket.upper_limit,
                rate=bracket.rate,
            )
        )

    existing_policy_areas = {pe.policy_area: pe for pe in fy.policy_elections}
    for area in POLICY_AREAS:
        existing = existing_policy_areas.get(area)
        db.add(
            PolicyElection(
                financial_year_id=new_fy.id,
                policy_area=area,
                applicable=existing.applicable if existing else False,
                notes=existing.notes if existing else None,
            )
        )

    db.commit()
    db.refresh(new_fy)
    return new_fy
