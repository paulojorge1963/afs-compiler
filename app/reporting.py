"""Orchestrates the calc engine into one consistent report for a FinancialYear.

This is the single place that turns a FinancialYear ORM object (with its
relationships loaded) into every number and note-number cross-reference used
by both the on-screen preview templates and the .docx generator - so a figure
is never computed two different ways in two different places (per Section 6).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app import calc
from app.models import FinancialYear
from app.policy_library import POLICY_LIBRARY


@dataclass
class NoteRegistry:
    """Assigns sequential note numbers (Notes to the AFS start at 2 - Note 1 is
    always the Accounting Policies section) to only the notes that actually apply.
    """

    _numbers: dict = field(default_factory=dict)
    _order: list = field(default_factory=list)

    def register(self, key: str, applicable: bool) -> None:
        if applicable and key not in self._numbers:
            self._order.append(key)

    def finalise(self, start: int = 2) -> None:
        for i, key in enumerate(self._order):
            self._numbers[key] = start + i

    def get(self, key: str) -> int | None:
        return self._numbers.get(key)

    def has(self, key: str) -> bool:
        return key in self._numbers


@dataclass
class ReportData:
    fy: FinancialYear
    entity: object

    income_current: calc.IncomeStatementFigures
    income_prior: calc.IncomeStatementFigures
    balance_sheet_current: calc.BalanceSheetFigures
    balance_sheet_prior: calc.BalanceSheetFigures
    equity_statement: calc.EquityStatement
    cash_flow: calc.CashFlowFigures
    tax: calc.TaxComputationResult

    notes: NoteRegistry
    validations: list

    detailed_opex_lines: list  # [(account_name, current, prior)], alphabetical

    @property
    def is_valid(self) -> bool:
        return all(v.ok for v in self.validations)


def build_report(fy: FinancialYear) -> ReportData:
    entity = fy.entity
    tb_lines = fy.trial_balance_lines
    ppe_assets = fy.ppe_assets
    loans = fy.shareholder_loans

    income_current = calc.compute_income_statement(
        tb_lines, ppe_assets, fy.prior_year_depreciation_charge, year="current"
    )
    income_prior = calc.compute_income_statement(
        tb_lines, ppe_assets, fy.prior_year_depreciation_charge, year="prior"
    )

    retained_income_current = calc.retained_income_closing(
        fy.opening_retained_income, income_prior.profit_for_the_year, income_current.profit_for_the_year
    )
    retained_income_prior = calc.retained_income_prior_closing(
        fy.opening_retained_income, income_prior.profit_for_the_year
    )

    share_capital_current = calc.sum_category(tb_lines, "Share Capital", "current")
    share_capital_prior = calc.sum_category(tb_lines, "Share Capital", "prior")

    balance_sheet_current = calc.compute_balance_sheet(
        tb_lines, ppe_assets, loans, retained_income_current, share_capital_current, year="current"
    )
    balance_sheet_prior = calc.compute_balance_sheet(
        tb_lines, ppe_assets, loans, retained_income_prior, share_capital_prior, year="prior"
    )

    equity_statement = calc.compute_equity_statement(
        opening_share_capital=fy.opening_share_capital,
        opening_retained_income=fy.opening_retained_income,
        share_capital_prior_close=share_capital_prior,
        share_capital_current_close=share_capital_current,
        prior_year_profit=income_prior.profit_for_the_year,
        current_year_profit=income_current.profit_for_the_year,
    )

    cash_flow = calc.compute_cash_flow(
        tb_lines,
        ppe_assets,
        loans,
        income_current,
        cash_prior=balance_sheet_prior.cash,
        cash_current=balance_sheet_current.cash,
    )

    tax_diffs = fy.tax_differences
    assessed_loss_bf = fy.tax_computation_meta.assessed_loss_brought_forward if fy.tax_computation_meta else 0.0
    tax = calc.compute_tax(income_current.profit_for_the_year, tax_diffs, assessed_loss_bf, fy.tax_brackets)

    validations = calc.run_validation(
        balance_sheet_current,
        cash_flow,
        cash_current=balance_sheet_current.cash,
        ppe_assets=ppe_assets,
        shareholder_loans=loans,
        retained_income_prior_year_closing=retained_income_prior,
        opening_retained_income_current_year=retained_income_prior,
    )

    notes = NoteRegistry()
    notes.register("ppe", len(ppe_assets) > 0)
    notes.register("loans", len(loans) > 0)
    notes.register(
        "receivables",
        any(calc._cat(l.afs_category) == "Trade and Other Receivables" for l in tb_lines),
    )
    notes.register("inventory", any(calc._cat(l.afs_category) == "Inventory" for l in tb_lines))
    notes.register(
        "payables", any(calc._cat(l.afs_category) == "Trade and Other Payables" for l in tb_lines)
    )
    notes.register(
        "current_tax_payable",
        any(calc._cat(l.afs_category) == "Current Tax Payable" for l in tb_lines),
    )
    notes.register(
        "investment_revenue",
        any(calc._cat(l.afs_category) == "Investment Revenue" for l in tb_lines),
    )
    notes.register("cash_generated", True)
    notes.finalise(start=2)

    opex_lines = sorted(
        (
            (l.account_name, l.current_year_amount, l.prior_year_amount)
            for l in tb_lines
            if calc._cat(l.afs_category) == "Operating Expense"
        ),
        key=lambda t: t[0].lower(),
    )
    if len(ppe_assets) > 0 or fy.prior_year_depreciation_charge:
        opex_lines.append(("Depreciation", income_current.depreciation, income_prior.depreciation))
        opex_lines.sort(key=lambda t: t[0].lower())

    return ReportData(
        fy=fy,
        entity=entity,
        income_current=income_current,
        income_prior=income_prior,
        balance_sheet_current=balance_sheet_current,
        balance_sheet_prior=balance_sheet_prior,
        equity_statement=equity_statement,
        cash_flow=cash_flow,
        tax=tax,
        notes=notes,
        validations=validations,
        detailed_opex_lines=opex_lines,
    )


def applicable_policies(fy: FinancialYear) -> list[dict]:
    """Returns ordered [{policy_area, heading, body}] for every applicable PolicyElection,
    in the canonical order defined by the policy library / POLICY_AREAS list."""
    from app.models import POLICY_AREAS

    applicable_areas = {pe.policy_area for pe in fy.policy_elections if pe.applicable}
    out = []
    for area in POLICY_AREAS:
        if area in applicable_areas and area in POLICY_LIBRARY:
            entry = POLICY_LIBRARY[area]
            out.append({"policy_area": area, "heading": entry["heading"], "body": entry["body"]})
    return out
