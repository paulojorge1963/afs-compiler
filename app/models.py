"""SQLAlchemy models mirroring the AFS Compiler Input Template workbook (see Section 5 of the spec)."""
from __future__ import annotations

import enum
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class ReportType(str, enum.Enum):
    COMPILATION = "Compilation Report"
    REVIEW = "Independent Review Report"
    AUDIT = "Audit Report"


class IFRSEdition(str, enum.Enum):
    SECOND_2015 = "Second Edition (2015)"
    THIRD_2025_EARLY = "Third Edition (2025) - early adopted"


class AFSCategory(str, enum.Enum):
    REVENUE = "Revenue"
    COST_OF_SALES = "Cost of Sales"
    OPERATING_EXPENSE = "Operating Expense"
    INVESTMENT_REVENUE = "Investment Revenue"
    FINANCE_COSTS = "Finance Costs"
    OTHER_INCOME = "Other Income"
    TRADE_AND_OTHER_RECEIVABLES = "Trade and Other Receivables"
    INVENTORY = "Inventory"
    CASH_AND_CASH_EQUIVALENTS = "Cash and Cash Equivalents"
    SHARE_CAPITAL = "Share Capital"
    TRADE_AND_OTHER_PAYABLES = "Trade and Other Payables"
    CURRENT_TAX_PAYABLE = "Current Tax Payable"
    OTHER_CURRENT_ASSET = "Other Current Asset"
    OTHER_CURRENT_LIABILITY = "Other Current Liability"
    OTHER_NON_CURRENT_LIABILITY = "Other Non-Current Liability"


class LoanDirection(str, enum.Enum):
    TO = "To"
    FROM = "From"


# Policy areas mirror the "Policy Elections" sheet exactly (Section 7 / 8.8).
POLICY_AREAS: list[str] = [
    "Property, plant and equipment (Section 17)",
    "Financial instruments (Sections 11 & 12)",
    "Income tax, current and deferred (Section 29)",
    "Employee benefits, short-term (Section 28)",
    "Revenue (Section 23)",
    "Inventories (Section 13)",
    "Leases (Section 20)",
    "Provisions and contingencies (Section 21)",
    "Related party disclosures (Section 33)",
    "Impairment of assets (Section 27)",
    "Foreign currency translation (Section 30)",
    "Government grants (Section 24)",
    "Borrowing costs (Section 25)",
    "Statement of cash flows (Section 7)",
]


class Entity(Base):
    __tablename__ = "entities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_name: Mapped[str] = mapped_column(String, nullable=False)
    registration_number: Mapped[str] = mapped_column(String, nullable=False)
    tax_reference_number: Mapped[str | None] = mapped_column(String)
    vat_number: Mapped[str | None] = mapped_column(String)
    country_of_incorporation: Mapped[str] = mapped_column(String, default="South Africa")
    nature_of_business: Mapped[str | None] = mapped_column(Text)
    registered_office_address: Mapped[str | None] = mapped_column(Text)
    business_address: Mapped[str | None] = mapped_column(Text)
    postal_address: Mapped[str | None] = mapped_column(Text)
    bankers: Mapped[str | None] = mapped_column(String)
    practitioner_name: Mapped[str | None] = mapped_column(String)
    practitioner_firm: Mapped[str | None] = mapped_column(String)
    report_type: Mapped[ReportType] = mapped_column(
        Enum(ReportType), default=ReportType.COMPILATION
    )
    is_sbc: Mapped[bool] = mapped_column(Boolean, default=True)
    incorporation_date: Mapped[date | None] = mapped_column(Date)
    certificate_to_commence_business_date: Mapped[date | None] = mapped_column(Date)

    directors: Mapped[list["Director"]] = relationship(
        back_populates="entity", cascade="all, delete-orphan", order_by="Director.id"
    )
    financial_years: Mapped[list["FinancialYear"]] = relationship(
        back_populates="entity", cascade="all, delete-orphan", order_by="FinancialYear.year_end_date"
    )


class Director(Base):
    __tablename__ = "directors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id"))
    full_name: Mapped[str] = mapped_column(String, nullable=False)
    nationality: Mapped[str | None] = mapped_column(String)
    date_appointed: Mapped[date | None] = mapped_column(Date)
    date_resigned: Mapped[date | None] = mapped_column(Date)
    signs_approval: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str | None] = mapped_column(Text)

    entity: Mapped[Entity] = relationship(back_populates="directors")


class FinancialYear(Base):
    __tablename__ = "financial_years"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id"))

    year_end_date: Mapped[date] = mapped_column(Date, nullable=False)
    comparative_year_end_date: Mapped[date | None] = mapped_column(Date)
    date_approved: Mapped[date | None] = mapped_column(Date)

    ifrs_edition: Mapped[IFRSEdition] = mapped_column(
        Enum(IFRSEdition), default=IFRSEdition.SECOND_2015
    )

    # Opening balances at the START of the comparative/prior year.
    opening_retained_income: Mapped[float] = mapped_column(Float, default=0.0)
    opening_share_capital: Mapped[float] = mapped_column(Float, default=0.0)
    opening_cash: Mapped[float] = mapped_column(Float, default=0.0)

    # Supplementary figure used only to reconstruct prior-year profit for the
    # equity roll-forward / validation - NOT used in the PPE note.
    prior_year_depreciation_charge: Mapped[float] = mapped_column(Float, default=0.0)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    entity: Mapped[Entity] = relationship(back_populates="financial_years")
    trial_balance_lines: Mapped[list["TrialBalanceLine"]] = relationship(
        back_populates="financial_year", cascade="all, delete-orphan"
    )
    ppe_assets: Mapped[list["PPEAsset"]] = relationship(
        back_populates="financial_year", cascade="all, delete-orphan"
    )
    shareholder_loans: Mapped[list["ShareholderLoan"]] = relationship(
        back_populates="financial_year", cascade="all, delete-orphan"
    )
    tax_differences: Mapped[list["TaxDifference"]] = relationship(
        back_populates="financial_year", cascade="all, delete-orphan"
    )
    tax_brackets: Mapped[list["TaxBracket"]] = relationship(
        back_populates="financial_year", cascade="all, delete-orphan", order_by="TaxBracket.lower_limit"
    )
    policy_elections: Mapped[list["PolicyElection"]] = relationship(
        back_populates="financial_year", cascade="all, delete-orphan"
    )
    tax_computation_meta: Mapped["TaxComputationMeta"] = relationship(
        back_populates="financial_year", uselist=False, cascade="all, delete-orphan"
    )


class TrialBalanceLine(Base):
    __tablename__ = "trial_balance_lines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    financial_year_id: Mapped[int] = mapped_column(ForeignKey("financial_years.id"))
    account_name: Mapped[str] = mapped_column(String, nullable=False)
    afs_category: Mapped[AFSCategory] = mapped_column(Enum(AFSCategory), nullable=False)
    current_year_amount: Mapped[float] = mapped_column(Float, default=0.0)
    prior_year_amount: Mapped[float] = mapped_column(Float, default=0.0)
    notes: Mapped[str | None] = mapped_column(Text)

    financial_year: Mapped[FinancialYear] = relationship(back_populates="trial_balance_lines")


class PPEAsset(Base):
    __tablename__ = "ppe_assets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    financial_year_id: Mapped[int] = mapped_column(ForeignKey("financial_years.id"))
    asset_category: Mapped[str] = mapped_column(String, nullable=False)
    depreciation_method: Mapped[str] = mapped_column(String, default="Straight line")
    useful_life_years: Mapped[float] = mapped_column(Float, default=0.0)
    opening_cost: Mapped[float] = mapped_column(Float, default=0.0)
    additions: Mapped[float] = mapped_column(Float, default=0.0)
    disposals_cost: Mapped[float] = mapped_column(Float, default=0.0)
    opening_accumulated_depreciation: Mapped[float] = mapped_column(Float, default=0.0)
    depreciation_charge: Mapped[float] = mapped_column(Float, default=0.0)
    accumulated_depreciation_on_disposals: Mapped[float] = mapped_column(Float, default=0.0)

    financial_year: Mapped[FinancialYear] = relationship(back_populates="ppe_assets")

    @property
    def closing_cost(self) -> float:
        return self.opening_cost + self.additions - self.disposals_cost

    @property
    def closing_accumulated_depreciation(self) -> float:
        return (
            self.opening_accumulated_depreciation
            + self.depreciation_charge
            - self.accumulated_depreciation_on_disposals
        )

    @property
    def carrying_value(self) -> float:
        return self.closing_cost - self.closing_accumulated_depreciation


class ShareholderLoan(Base):
    __tablename__ = "shareholder_loans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    financial_year_id: Mapped[int] = mapped_column(ForeignKey("financial_years.id"))
    shareholder_name: Mapped[str] = mapped_column(String, nullable=False)
    direction: Mapped[LoanDirection] = mapped_column(Enum(LoanDirection), nullable=False)
    opening_balance: Mapped[float] = mapped_column(Float, default=0.0)
    advances: Mapped[float] = mapped_column(Float, default=0.0)
    repayments: Mapped[float] = mapped_column(Float, default=0.0)
    interest_rate_pa: Mapped[float] = mapped_column(Float, default=0.0)
    interest_charged: Mapped[float] = mapped_column(Float, default=0.0)
    secured_or_unsecured: Mapped[str] = mapped_column(String, default="Unsecured")
    repayment_terms: Mapped[str | None] = mapped_column(Text)

    financial_year: Mapped[FinancialYear] = relationship(back_populates="shareholder_loans")

    @property
    def closing_balance(self) -> float:
        return self.opening_balance + self.advances - self.repayments


class TaxComputationMeta(Base):
    """One-to-one with FinancialYear - holds the scalar tax computation inputs."""

    __tablename__ = "tax_computation_meta"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    financial_year_id: Mapped[int] = mapped_column(ForeignKey("financial_years.id"), unique=True)
    assessed_loss_brought_forward: Mapped[float] = mapped_column(Float, default=0.0)

    financial_year: Mapped[FinancialYear] = relationship(back_populates="tax_computation_meta")


class TaxDifference(Base):
    __tablename__ = "tax_differences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    financial_year_id: Mapped[int] = mapped_column(ForeignKey("financial_years.id"))
    description: Mapped[str] = mapped_column(String, nullable=False)
    amount: Mapped[float] = mapped_column(Float, default=0.0)

    financial_year: Mapped[FinancialYear] = relationship(back_populates="tax_differences")


class TaxBracket(Base):
    __tablename__ = "tax_brackets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    financial_year_id: Mapped[int] = mapped_column(ForeignKey("financial_years.id"))
    lower_limit: Mapped[float] = mapped_column(Float, default=0.0)
    upper_limit: Mapped[float | None] = mapped_column(Float, nullable=True)  # None = open-ended
    rate: Mapped[float] = mapped_column(Float, default=0.0)

    financial_year: Mapped[FinancialYear] = relationship(back_populates="tax_brackets")


class PolicyElection(Base):
    __tablename__ = "policy_elections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    financial_year_id: Mapped[int] = mapped_column(ForeignKey("financial_years.id"))
    policy_area: Mapped[str] = mapped_column(String, nullable=False)
    applicable: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(Text)

    financial_year: Mapped[FinancialYear] = relationship(back_populates="policy_elections")
