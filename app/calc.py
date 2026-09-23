"""Pure calculation engine for the AFS Compiler (Section 6 of the spec).

Every function here is pure: it takes plain data in and returns plain data out,
so it can be unit tested without a database session, and reused identically by
both the on-screen preview and the .docx generator (never compute a number two
different ways in two different places).

Functions accept duck-typed objects (ORM model instances, or any object with
matching attribute names) so they work equally well fed from SQLAlchemy models
or from lightweight test fixtures.
"""
from __future__ import annotations

from dataclasses import dataclass, field


def _cat(value) -> str:
    """Normalise an AFSCategory enum (or plain string) to its string value."""
    return getattr(value, "value", value)


def _dir(value) -> str:
    return getattr(value, "value", value)


def sum_category(lines, category: str, year: str = "current") -> float:
    attr = "current_year_amount" if year == "current" else "prior_year_amount"
    return sum(getattr(line, attr) for line in lines if _cat(line.afs_category) == category)


# ---------------------------------------------------------------------------
# Income statement
# ---------------------------------------------------------------------------


@dataclass
class IncomeStatementFigures:
    revenue: float
    cost_of_sales: float
    gross_profit: float
    operating_expenses_excl_depreciation: float
    depreciation: float
    total_operating_expenses: float
    operating_profit: float
    investment_revenue: float
    finance_costs: float
    profit_for_the_year: float
    other_comprehensive_income: float
    total_comprehensive_income: float


def total_depreciation_charge(ppe_assets) -> float:
    """Current-year depreciation charge, summed across the PPE register."""
    return sum(asset.depreciation_charge for asset in ppe_assets)


def compute_income_statement(trial_balance_lines, ppe_assets, prior_year_depreciation: float,
                              other_comprehensive_income: float = 0.0, year: str = "current") -> IncomeStatementFigures:
    revenue = sum_category(trial_balance_lines, "Revenue", year)
    cost_of_sales = sum_category(trial_balance_lines, "Cost of Sales", year)
    gross_profit = revenue - cost_of_sales

    opex_excl_dep = sum_category(trial_balance_lines, "Operating Expense", year)
    depreciation = total_depreciation_charge(ppe_assets) if year == "current" else prior_year_depreciation
    total_opex = opex_excl_dep + depreciation

    operating_profit = gross_profit - total_opex

    investment_revenue = sum_category(trial_balance_lines, "Investment Revenue", year)
    finance_costs = sum_category(trial_balance_lines, "Finance Costs", year)

    profit_for_the_year = operating_profit + investment_revenue - finance_costs
    total_comprehensive_income = profit_for_the_year + other_comprehensive_income

    return IncomeStatementFigures(
        revenue=revenue,
        cost_of_sales=cost_of_sales,
        gross_profit=gross_profit,
        operating_expenses_excl_depreciation=opex_excl_dep,
        depreciation=depreciation,
        total_operating_expenses=total_opex,
        operating_profit=operating_profit,
        investment_revenue=investment_revenue,
        finance_costs=finance_costs,
        profit_for_the_year=profit_for_the_year,
        other_comprehensive_income=other_comprehensive_income,
        total_comprehensive_income=total_comprehensive_income,
    )


# ---------------------------------------------------------------------------
# Statement of financial position
# ---------------------------------------------------------------------------


@dataclass
class BalanceSheetFigures:
    ppe_carrying_value: float
    loans_to_shareholders: float
    non_current_assets: float
    trade_and_other_receivables: float
    inventory: float
    other_current_asset: float
    cash: float
    current_assets: float
    total_assets: float

    share_capital: float
    retained_income: float
    total_equity: float

    loans_from_shareholders: float
    trade_and_other_payables: float
    current_tax_payable: float
    other_current_liability: float
    other_non_current_liability: float
    total_liabilities: float

    total_equity_and_liabilities: float


def compute_balance_sheet(trial_balance_lines, ppe_assets, shareholder_loans, retained_income: float,
                           share_capital: float, year: str = "current") -> BalanceSheetFigures:
    if year == "current":
        ppe_carrying_value = sum(a.carrying_value for a in ppe_assets)
        loans_to = sum(l.closing_balance for l in shareholder_loans if _dir(l.direction) == "To")
        loans_from = sum(l.closing_balance for l in shareholder_loans if _dir(l.direction) == "From")
    else:
        ppe_carrying_value = sum(a.opening_cost - a.opening_accumulated_depreciation for a in ppe_assets)
        loans_to = sum(l.opening_balance for l in shareholder_loans if _dir(l.direction) == "To")
        loans_from = sum(l.opening_balance for l in shareholder_loans if _dir(l.direction) == "From")

    non_current_assets = ppe_carrying_value + loans_to

    receivables = sum_category(trial_balance_lines, "Trade and Other Receivables", year)
    inventory = sum_category(trial_balance_lines, "Inventory", year)
    other_current_asset = sum_category(trial_balance_lines, "Other Current Asset", year)
    cash = sum_category(trial_balance_lines, "Cash and Cash Equivalents", year)
    current_assets = receivables + inventory + other_current_asset + cash

    total_assets = non_current_assets + current_assets

    total_equity = share_capital + retained_income

    payables = sum_category(trial_balance_lines, "Trade and Other Payables", year)
    current_tax_payable = sum_category(trial_balance_lines, "Current Tax Payable", year)
    other_current_liability = sum_category(trial_balance_lines, "Other Current Liability", year)
    other_non_current_liability = sum_category(trial_balance_lines, "Other Non-Current Liability", year)
    total_liabilities = (
        loans_from + payables + current_tax_payable + other_current_liability + other_non_current_liability
    )

    total_equity_and_liabilities = total_equity + total_liabilities

    return BalanceSheetFigures(
        ppe_carrying_value=ppe_carrying_value,
        loans_to_shareholders=loans_to,
        non_current_assets=non_current_assets,
        trade_and_other_receivables=receivables,
        inventory=inventory,
        other_current_asset=other_current_asset,
        cash=cash,
        current_assets=current_assets,
        total_assets=total_assets,
        share_capital=share_capital,
        retained_income=retained_income,
        total_equity=total_equity,
        loans_from_shareholders=loans_from,
        trade_and_other_payables=payables,
        current_tax_payable=current_tax_payable,
        other_current_liability=other_current_liability,
        other_non_current_liability=other_non_current_liability,
        total_liabilities=total_liabilities,
        total_equity_and_liabilities=total_equity_and_liabilities,
    )


def retained_income_closing(opening_retained_income: float, prior_year_profit: float, current_year_profit: float) -> float:
    return opening_retained_income + prior_year_profit + current_year_profit


def retained_income_prior_closing(opening_retained_income: float, prior_year_profit: float) -> float:
    return opening_retained_income + prior_year_profit


# ---------------------------------------------------------------------------
# Statement of changes in equity
# ---------------------------------------------------------------------------


@dataclass
class EquityRow:
    label: str
    share_capital: float
    retained_income: float

    @property
    def total(self) -> float:
        return self.share_capital + self.retained_income


@dataclass
class EquityStatement:
    opening_prior_year: EquityRow
    prior_year_profit: EquityRow
    prior_year_oci: EquityRow
    opening_current_year: EquityRow
    current_year_profit: EquityRow
    current_year_oci: EquityRow
    closing_current_year: EquityRow


def compute_equity_statement(
    opening_share_capital: float,
    opening_retained_income: float,
    share_capital_prior_close: float,
    share_capital_current_close: float,
    prior_year_profit: float,
    current_year_profit: float,
    prior_year_oci: float = 0.0,
    current_year_oci: float = 0.0,
) -> EquityStatement:
    opening_prior_year = EquityRow("Balance at [start of comparative year]", opening_share_capital, opening_retained_income)

    prior_profit_row = EquityRow("Profit for the year", 0.0, prior_year_profit)
    prior_oci_row = EquityRow("Other comprehensive income", 0.0, prior_year_oci)

    retained_income_at_opening_of_current = opening_retained_income + prior_year_profit + prior_year_oci
    opening_current_year = EquityRow(
        "Balance at [start of current year]", share_capital_prior_close, retained_income_at_opening_of_current
    )

    current_profit_row = EquityRow("Profit for the year", 0.0, current_year_profit)
    current_oci_row = EquityRow("Other comprehensive income", 0.0, current_year_oci)

    retained_income_at_close_of_current = retained_income_at_opening_of_current + current_year_profit + current_year_oci
    closing_current_year = EquityRow(
        "Balance at [end of current year]", share_capital_current_close, retained_income_at_close_of_current
    )

    return EquityStatement(
        opening_prior_year=opening_prior_year,
        prior_year_profit=prior_profit_row,
        prior_year_oci=prior_oci_row,
        opening_current_year=opening_current_year,
        current_year_profit=current_profit_row,
        current_year_oci=current_oci_row,
        closing_current_year=closing_current_year,
    )


# ---------------------------------------------------------------------------
# Statement of cash flows
# ---------------------------------------------------------------------------


@dataclass
class CashFlowFigures:
    receipts_from_customers: float
    paid_to_suppliers_and_employees: float
    cash_generated_from_operations: float
    interest_income_received: float
    finance_costs_paid: float
    net_cash_from_operating_activities: float

    purchase_of_ppe: float
    loan_advances: float
    loan_repayments: float
    net_cash_from_investing_activities: float

    total_cash_movement: float
    cash_at_beginning_of_year: float
    cash_at_end_of_year: float

    # Reconciliation note: "Cash generated from (used in) operations"
    profit_before_tax: float
    depreciation_addback: float
    investment_revenue_deduction: float
    finance_costs_addback: float
    receivables_movement: float
    payables_movement: float
    reconciliation_total: float


def compute_cash_flow(
    trial_balance_lines,
    ppe_assets,
    shareholder_loans,
    income_statement: IncomeStatementFigures,
    cash_prior: float,
    cash_current: float,
) -> CashFlowFigures:
    revenue = sum_category(trial_balance_lines, "Revenue", "current")
    receivables_current = sum_category(trial_balance_lines, "Trade and Other Receivables", "current")
    receivables_prior = sum_category(trial_balance_lines, "Trade and Other Receivables", "prior")
    receivables_movement = receivables_current - receivables_prior
    receipts_from_customers = revenue - receivables_movement

    cost_of_sales = sum_category(trial_balance_lines, "Cost of Sales", "current")
    opex_excl_dep = sum_category(trial_balance_lines, "Operating Expense", "current")
    payables_current = sum_category(trial_balance_lines, "Trade and Other Payables", "current")
    payables_prior = sum_category(trial_balance_lines, "Trade and Other Payables", "prior")
    payables_movement = payables_current - payables_prior
    paid_to_suppliers_and_employees = -(cost_of_sales + opex_excl_dep) + payables_movement

    cash_generated_from_operations = receipts_from_customers + paid_to_suppliers_and_employees

    interest_income_received = income_statement.investment_revenue
    finance_costs_paid = -income_statement.finance_costs

    net_cash_from_operating_activities = (
        cash_generated_from_operations + interest_income_received + finance_costs_paid
    )

    purchase_of_ppe = -sum(a.additions for a in ppe_assets)
    loan_advances = sum(l.advances for l in shareholder_loans)
    loan_repayments = sum(l.repayments for l in shareholder_loans)
    net_cash_from_investing_activities = purchase_of_ppe + (loan_repayments - loan_advances)

    total_cash_movement = net_cash_from_operating_activities + net_cash_from_investing_activities
    cash_at_end_of_year = cash_prior + total_cash_movement

    reconciliation_total = (
        income_statement.profit_for_the_year
        + income_statement.depreciation
        - income_statement.investment_revenue
        + income_statement.finance_costs
        - receivables_movement
        + payables_movement
    )

    return CashFlowFigures(
        receipts_from_customers=receipts_from_customers,
        paid_to_suppliers_and_employees=paid_to_suppliers_and_employees,
        cash_generated_from_operations=cash_generated_from_operations,
        interest_income_received=interest_income_received,
        finance_costs_paid=finance_costs_paid,
        net_cash_from_operating_activities=net_cash_from_operating_activities,
        purchase_of_ppe=purchase_of_ppe,
        loan_advances=loan_advances,
        loan_repayments=loan_repayments,
        net_cash_from_investing_activities=net_cash_from_investing_activities,
        total_cash_movement=total_cash_movement,
        cash_at_beginning_of_year=cash_prior,
        cash_at_end_of_year=cash_at_end_of_year,
        profit_before_tax=income_statement.profit_for_the_year,
        depreciation_addback=income_statement.depreciation,
        investment_revenue_deduction=-income_statement.investment_revenue,
        finance_costs_addback=income_statement.finance_costs,
        receivables_movement=-receivables_movement,
        payables_movement=payables_movement,
        reconciliation_total=reconciliation_total,
    )


# ---------------------------------------------------------------------------
# Tax computation
# ---------------------------------------------------------------------------


@dataclass
class TaxComputationResult:
    net_profit_per_income_statement: float
    temporary_differences: list
    total_temporary_differences: float
    calculated_tax_profit: float
    assessed_loss_brought_forward: float
    assessed_loss_utilised: float
    taxable_income: float
    assessed_loss_carried_forward: float
    bracket_breakdown: list
    tax_thereon: float


def compute_tax(
    profit_for_the_year: float,
    temporary_differences,
    assessed_loss_brought_forward: float,
    tax_brackets,
) -> TaxComputationResult:
    total_temp_diff = sum(td.amount for td in temporary_differences)
    calculated_tax_profit = profit_for_the_year + total_temp_diff

    assessed_loss_utilised = -min(assessed_loss_brought_forward, max(0.0, calculated_tax_profit))
    taxable_income = max(0.0, calculated_tax_profit + assessed_loss_utilised)
    assessed_loss_carried_forward = max(0.0, assessed_loss_brought_forward + assessed_loss_utilised) + max(
        0.0, -(calculated_tax_profit + assessed_loss_utilised)
    )

    breakdown = []
    tax_thereon = 0.0
    for bracket in sorted(tax_brackets, key=lambda b: b.lower_limit):
        upper = bracket.upper_limit if bracket.upper_limit else taxable_income
        amount_in_bracket = max(0.0, min(taxable_income, upper) - (bracket.lower_limit - 1))
        tax_for_bracket = amount_in_bracket * bracket.rate
        breakdown.append(
            {
                "lower_limit": bracket.lower_limit,
                "upper_limit": bracket.upper_limit,
                "rate": bracket.rate,
                "amount_in_bracket": amount_in_bracket,
                "tax_for_bracket": tax_for_bracket,
            }
        )
        tax_thereon += tax_for_bracket

    return TaxComputationResult(
        net_profit_per_income_statement=profit_for_the_year,
        temporary_differences=list(temporary_differences),
        total_temporary_differences=total_temp_diff,
        calculated_tax_profit=calculated_tax_profit,
        assessed_loss_brought_forward=assessed_loss_brought_forward,
        assessed_loss_utilised=assessed_loss_utilised,
        taxable_income=taxable_income,
        assessed_loss_carried_forward=assessed_loss_carried_forward,
        bracket_breakdown=breakdown,
        tax_thereon=tax_thereon,
    )


# ---------------------------------------------------------------------------
# Validation (mirrors the workbook's "Validation Summary" sheet)
# ---------------------------------------------------------------------------


@dataclass
class ValidationCheck:
    name: str
    value_a: float
    value_b: float

    @property
    def difference(self) -> float:
        return round(self.value_a - self.value_b, 2)

    @property
    def ok(self) -> bool:
        return abs(self.difference) < 0.01


def run_validation(
    balance_sheet_current: BalanceSheetFigures,
    cash_flow: CashFlowFigures,
    cash_current: float,
    ppe_assets,
    shareholder_loans,
    retained_income_prior_year_closing: float,
    opening_retained_income_current_year: float,
) -> list[ValidationCheck]:
    checks = [
        ValidationCheck(
            "Total Assets = Total Equity + Liabilities (current year)",
            balance_sheet_current.total_assets,
            balance_sheet_current.total_equity_and_liabilities,
        ),
        ValidationCheck(
            "Cash Flow computed closing cash vs Statement of Financial Position cash",
            cash_flow.cash_at_end_of_year,
            cash_current,
        ),
        ValidationCheck(
            "PPE Register total carrying value vs its own cost-less-depreciation total",
            sum(a.carrying_value for a in ppe_assets),
            sum(a.closing_cost - a.closing_accumulated_depreciation for a in ppe_assets),
        ),
        ValidationCheck(
            "Loans Register closing balance vs Opening + Advances - Repayments",
            sum(l.closing_balance for l in shareholder_loans),
            sum(l.opening_balance + l.advances - l.repayments for l in shareholder_loans),
        ),
        ValidationCheck(
            "Retained income roll-forward: prior-year closing vs current-year opening",
            retained_income_prior_year_closing,
            opening_retained_income_current_year,
        ),
    ]
    return checks
