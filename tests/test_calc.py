"""Unit tests for the calculation engine (app.calc), using the Example Photography Studio
FY2026 worked example as fixtures - independent of the document generation step,
per Section 9 of the spec.
"""
import pytest

from app import calc


def test_income_statement_current_year(example_financial_year):
    fy = example_financial_year
    ic = calc.compute_income_statement(fy.trial_balance_lines, fy.ppe_assets, fy.prior_year_depreciation_charge, year="current")

    assert ic.revenue == 96423
    assert ic.cost_of_sales == 8122
    assert ic.gross_profit == 88301
    assert ic.depreciation == 408
    assert ic.total_operating_expenses == 76287 + 408
    assert ic.operating_profit == 88301 - (76287 + 408)
    assert ic.investment_revenue == 11841
    assert ic.finance_costs == 0
    assert ic.profit_for_the_year == pytest.approx(23447)


def test_income_statement_prior_year(example_financial_year):
    fy = example_financial_year
    ip = calc.compute_income_statement(fy.trial_balance_lines, fy.ppe_assets, fy.prior_year_depreciation_charge, year="prior")
    assert ip.depreciation == 2079
    assert ip.profit_for_the_year == pytest.approx(8180)


def test_retained_income_roll_forward(example_financial_year):
    fy = example_financial_year
    ic = calc.compute_income_statement(fy.trial_balance_lines, fy.ppe_assets, fy.prior_year_depreciation_charge, year="current")
    ip = calc.compute_income_statement(fy.trial_balance_lines, fy.ppe_assets, fy.prior_year_depreciation_charge, year="prior")

    prior_closing = calc.retained_income_prior_closing(fy.opening_retained_income, ip.profit_for_the_year)
    current_closing = calc.retained_income_closing(fy.opening_retained_income, ip.profit_for_the_year, ic.profit_for_the_year)

    assert prior_closing == pytest.approx(146358)
    assert current_closing == pytest.approx(169805)


def test_balance_sheet_ties_to_the_cent(example_financial_year):
    fy = example_financial_year
    ic = calc.compute_income_statement(fy.trial_balance_lines, fy.ppe_assets, fy.prior_year_depreciation_charge, year="current")
    ip = calc.compute_income_statement(fy.trial_balance_lines, fy.ppe_assets, fy.prior_year_depreciation_charge, year="prior")
    retained_current = calc.retained_income_closing(fy.opening_retained_income, ip.profit_for_the_year, ic.profit_for_the_year)
    share_capital_current = calc.sum_category(fy.trial_balance_lines, "Share Capital", "current")

    bs = calc.compute_balance_sheet(
        fy.trial_balance_lines, fy.ppe_assets, fy.shareholder_loans, retained_current, share_capital_current, year="current"
    )

    assert bs.ppe_carrying_value == pytest.approx(2)
    assert bs.loans_to_shareholders == pytest.approx(164625)
    assert bs.total_assets == pytest.approx(170805)
    assert bs.total_equity_and_liabilities == pytest.approx(170805)
    assert bs.total_assets == pytest.approx(bs.total_equity_and_liabilities)


def test_cash_flow_closes_to_trial_balance_cash(example_financial_year):
    fy = example_financial_year
    ic = calc.compute_income_statement(fy.trial_balance_lines, fy.ppe_assets, fy.prior_year_depreciation_charge, year="current")
    cash_prior = calc.sum_category(fy.trial_balance_lines, "Cash and Cash Equivalents", "prior")
    cash_current = calc.sum_category(fy.trial_balance_lines, "Cash and Cash Equivalents", "current")

    cf = calc.compute_cash_flow(fy.trial_balance_lines, fy.ppe_assets, fy.shareholder_loans, ic, cash_prior, cash_current)

    assert cash_prior == 430
    assert cash_current == 6178
    assert cf.cash_at_end_of_year == pytest.approx(6178)
    assert cf.cash_at_end_of_year == pytest.approx(cash_current)


def test_tax_computation(example_financial_year):
    fy = example_financial_year
    ic = calc.compute_income_statement(fy.trial_balance_lines, fy.ppe_assets, fy.prior_year_depreciation_charge, year="current")
    tax = calc.compute_tax(
        ic.profit_for_the_year, fy.tax_differences, fy.tax_computation_meta.assessed_loss_brought_forward, fy.tax_brackets
    )

    assert tax.net_profit_per_income_statement == pytest.approx(23447)
    assert tax.total_temporary_differences == pytest.approx(0)
    assert tax.calculated_tax_profit == pytest.approx(23447)
    assert tax.taxable_income == pytest.approx(23447)
    assert tax.assessed_loss_carried_forward == pytest.approx(0)
    # Entirely within the 0% SBC bracket (up to 95 750) -> no tax payable.
    assert tax.tax_thereon == pytest.approx(0)


def test_tax_computation_progressive_brackets():
    from app.models import TaxBracket

    brackets = [
        TaxBracket(lower_limit=0, upper_limit=95750, rate=0.0),
        TaxBracket(lower_limit=95751, upper_limit=365000, rate=0.07),
        TaxBracket(lower_limit=365001, upper_limit=550000, rate=0.21),
        TaxBracket(lower_limit=550001, upper_limit=None, rate=0.27),
    ]
    tax = calc.compute_tax(profit_for_the_year=600000, temporary_differences=[], assessed_loss_brought_forward=0, tax_brackets=brackets)

    assert tax.taxable_income == pytest.approx(600000)
    expected = (365000 - 95750) * 0.07 + (550000 - 365000) * 0.21 + (600000 - 550000) * 0.27
    assert tax.tax_thereon == pytest.approx(expected)


def test_run_validation_all_pass(example_financial_year):
    fy = example_financial_year
    ic = calc.compute_income_statement(fy.trial_balance_lines, fy.ppe_assets, fy.prior_year_depreciation_charge, year="current")
    ip = calc.compute_income_statement(fy.trial_balance_lines, fy.ppe_assets, fy.prior_year_depreciation_charge, year="prior")
    retained_current = calc.retained_income_closing(fy.opening_retained_income, ip.profit_for_the_year, ic.profit_for_the_year)
    retained_prior = calc.retained_income_prior_closing(fy.opening_retained_income, ip.profit_for_the_year)
    share_capital_current = calc.sum_category(fy.trial_balance_lines, "Share Capital", "current")

    bs_current = calc.compute_balance_sheet(
        fy.trial_balance_lines, fy.ppe_assets, fy.shareholder_loans, retained_current, share_capital_current, year="current"
    )
    cash_prior = calc.sum_category(fy.trial_balance_lines, "Cash and Cash Equivalents", "prior")
    cf = calc.compute_cash_flow(fy.trial_balance_lines, fy.ppe_assets, fy.shareholder_loans, ic, cash_prior, bs_current.cash)

    checks = calc.run_validation(
        bs_current, cf, bs_current.cash, fy.ppe_assets, fy.shareholder_loans, retained_prior, retained_prior
    )
    assert all(c.ok for c in checks), [(c.name, c.difference) for c in checks if not c.ok]


def test_minimal_entity_has_no_ppe_or_loans(minimal_financial_year):
    fy = minimal_financial_year
    assert fy.ppe_assets == []
    assert fy.shareholder_loans == []
    ic = calc.compute_income_statement(fy.trial_balance_lines, fy.ppe_assets, fy.prior_year_depreciation_charge, year="current")
    assert ic.depreciation == 0
    assert ic.profit_for_the_year == pytest.approx(40000)

    bs = calc.compute_balance_sheet(fy.trial_balance_lines, fy.ppe_assets, fy.shareholder_loans, 40000, 100, year="current")
    assert bs.ppe_carrying_value == 0
    assert bs.loans_to_shareholders == 0
    assert bs.non_current_assets == 0
