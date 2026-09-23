"""Test fixtures built from the Paulo Jorge Photography FY2026 worked example
(the same data as AFS-Compiler-Input-Template.xlsx), used as the acceptance-test
dataset per Section 9 of the spec. Model instances are built in-memory, without a
database session, so the calc engine tests stay independent of document generation.
"""
import pytest

from app.models import (
    FinancialYear,
    PPEAsset,
    PolicyElection,
    ShareholderLoan,
    TaxBracket,
    TaxComputationMeta,
    TaxDifference,
    TrialBalanceLine,
)


@pytest.fixture
def pjp_financial_year():
    fy = FinancialYear(
        opening_retained_income=138178,
        opening_share_capital=1000,
        opening_cash=489,
        prior_year_depreciation_charge=2079,
    )

    tb_rows = [
        ("Rendering of services", "Revenue", 96423, 41899),
        ("Purchases", "Cost of Sales", 8122, 12892),
        ("Accounting fees", "Operating Expense", 13628, 5750),
        ("Advertising", "Operating Expense", 5251, 0),
        ("Bank charges", "Operating Expense", 5803, 3941),
        ("Consumables", "Operating Expense", 1495, 0),
        ("Employee costs", "Operating Expense", 10300, 0),
        ("Entertainment", "Operating Expense", 2815, 144),
        ("IT expenses", "Operating Expense", 5266, 4482),
        ("Levies", "Operating Expense", 2600, 2050),
        ("Motor vehicle expenses", "Operating Expense", 9169, 3812),
        ("Petrol and oil", "Operating Expense", 11192, 6712),
        ("Repairs and maintenance", "Operating Expense", 8699, 0),
        ("Subscriptions", "Operating Expense", 0, 833),
        ("Telephone and fax", "Operating Expense", 69, 312),
        ("Utilities", "Operating Expense", 0, 2500),
        ("Interest received - loans to directors/managers/employees", "Investment Revenue", 11841, 11789),
        ("Finance costs", "Finance Costs", 0, 1),
        ("Cash and cash equivalents", "Cash and Cash Equivalents", 6178, 430),
        ("Share capital", "Share Capital", 1000, 1000),
    ]
    fy.trial_balance_lines = [
        TrialBalanceLine(account_name=n, afs_category=cat, current_year_amount=cur, prior_year_amount=pri)
        for n, cat, cur, pri in tb_rows
    ]

    fy.ppe_assets = [
        PPEAsset(
            asset_category="Office equipment", depreciation_method="Straight line", useful_life_years=6,
            opening_cost=7200, additions=0, disposals_cost=0,
            opening_accumulated_depreciation=7199, depreciation_charge=0, accumulated_depreciation_on_disposals=0,
        ),
        PPEAsset(
            asset_category="IT equipment", depreciation_method="Straight line", useful_life_years=3,
            opening_cost=6300, additions=0, disposals_cost=0,
            opening_accumulated_depreciation=5891, depreciation_charge=408, accumulated_depreciation_on_disposals=0,
        ),
    ]

    fy.shareholder_loans = [
        ShareholderLoan(
            shareholder_name="Paulo Jorge Nunes Goncalves", direction="To",
            opening_balance=146518, advances=18107, repayments=0,
            interest_rate_pa=0.0775, interest_charged=11841,
            secured_or_unsecured="Unsecured", repayment_terms="No fixed terms of repayment have been set",
        ),
    ]

    fy.tax_computation_meta = TaxComputationMeta(assessed_loss_brought_forward=0)
    fy.tax_differences = [
        TaxDifference(description="Plant and machinery where company qualifies as SBC: s12E wear-and-tear", amount=-408),
        TaxDifference(description="Depreciation according to the financial statements", amount=408),
    ]
    fy.tax_brackets = [
        TaxBracket(lower_limit=0, upper_limit=95750, rate=0.0),
        TaxBracket(lower_limit=95751, upper_limit=365000, rate=0.07),
        TaxBracket(lower_limit=365001, upper_limit=550000, rate=0.21),
        TaxBracket(lower_limit=550001, upper_limit=None, rate=0.27),
    ]

    fy.policy_elections = [
        PolicyElection(policy_area="Property, plant and equipment (Section 17)", applicable=True),
        PolicyElection(policy_area="Financial instruments (Sections 11 & 12)", applicable=True),
        PolicyElection(policy_area="Income tax, current and deferred (Section 29)", applicable=True),
        PolicyElection(policy_area="Employee benefits, short-term (Section 28)", applicable=True),
        PolicyElection(policy_area="Revenue (Section 23)", applicable=True),
        PolicyElection(policy_area="Related party disclosures (Section 33)", applicable=True),
        PolicyElection(policy_area="Statement of cash flows (Section 7)", applicable=True),
        PolicyElection(policy_area="Inventories (Section 13)", applicable=False),
        PolicyElection(policy_area="Leases (Section 20)", applicable=False),
        PolicyElection(policy_area="Provisions and contingencies (Section 21)", applicable=False),
        PolicyElection(policy_area="Impairment of assets (Section 27)", applicable=False),
        PolicyElection(policy_area="Foreign currency translation (Section 30)", applicable=False),
        PolicyElection(policy_area="Government grants (Section 24)", applicable=False),
        PolicyElection(policy_area="Borrowing costs (Section 25)", applicable=False),
    ]

    return fy


@pytest.fixture
def minimal_financial_year():
    """No PPE, no shareholder loans, zero comparatives - tests clean omission of
    notes/statement lines that don't apply (Section 9's second acceptance test)."""
    fy = FinancialYear(
        opening_retained_income=0,
        opening_share_capital=100,
        opening_cash=0,
        prior_year_depreciation_charge=0,
    )
    fy.trial_balance_lines = [
        TrialBalanceLine(account_name="Consulting fees", afs_category="Revenue", current_year_amount=50000, prior_year_amount=0),
        TrialBalanceLine(account_name="Sundry expenses", afs_category="Operating Expense", current_year_amount=10000, prior_year_amount=0),
        TrialBalanceLine(account_name="Cash and cash equivalents", afs_category="Cash and Cash Equivalents", current_year_amount=40000, prior_year_amount=0),
        TrialBalanceLine(account_name="Share capital", afs_category="Share Capital", current_year_amount=100, prior_year_amount=100),
    ]
    fy.ppe_assets = []
    fy.shareholder_loans = []
    fy.tax_computation_meta = TaxComputationMeta(assessed_loss_brought_forward=0)
    fy.tax_differences = []
    fy.tax_brackets = [
        TaxBracket(lower_limit=0, upper_limit=95750, rate=0.0),
        TaxBracket(lower_limit=95751, upper_limit=365000, rate=0.07),
        TaxBracket(lower_limit=365001, upper_limit=550000, rate=0.21),
        TaxBracket(lower_limit=550001, upper_limit=None, rate=0.27),
    ]
    fy.policy_elections = []
    return fy
