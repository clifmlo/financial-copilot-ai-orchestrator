"""Pydantic schemas for the balance-sheet domain.

These mirror the entities managed by the Spring Boot API (system of record).
The orchestrator uses them for type-safe serialisation / deserialisation when
calling the API — it never writes directly to the database.
"""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class AssetType(str, Enum):
    ETF = "ETF"
    EQUITY = "EQUITY"
    CASH = "CASH"
    PROPERTY = "PROPERTY"
    RETIREMENT = "RETIREMENT"
    CRYPTO = "CRYPTO"
    COMMODITY = "COMMODITY"
    BUSINESS = "BUSINESS"
    VEHICLE = "VEHICLE"
    OTHER = "OTHER"


class LiabilityType(str, Enum):
    HOME_LOAN = "HOME_LOAN"
    VEHICLE_FINANCE = "VEHICLE_FINANCE"
    PERSONAL_LOAN = "PERSONAL_LOAN"
    CREDIT_CARD = "CREDIT_CARD"
    OVERDRAFT = "OVERDRAFT"
    STUDENT_LOAN = "STUDENT_LOAN"
    BUSINESS_LOAN = "BUSINESS_LOAN"
    OTHER = "OTHER"


class PaymentFrequency(str, Enum):
    MONTHLY = "MONTHLY"
    WEEKLY = "WEEKLY"
    FORTNIGHTLY = "FORTNIGHTLY"
    ANNUALLY = "ANNUALLY"


class ValuationMethod(str, Enum):
    MARKET = "MARKET"
    MANUAL = "MANUAL"
    PURCHASE_PRICE = "PURCHASE_PRICE"


# ---------------------------------------------------------------------------
# Asset
# ---------------------------------------------------------------------------

class AssetBase(BaseModel):
    asset_type: AssetType
    name: str = Field(..., min_length=1, max_length=200)
    institution: str | None = None
    currency: str = Field(default="ZAR", min_length=3, max_length=3)
    current_value: Decimal = Field(..., ge=0)
    valuation_method: ValuationMethod = ValuationMethod.MANUAL


class AssetCreate(AssetBase):
    account_id: int | None = None


class AssetUpdate(BaseModel):
    asset_type: AssetType | None = None
    name: str | None = None
    institution: str | None = None
    currency: str | None = None
    current_value: Decimal | None = None
    valuation_method: ValuationMethod | None = None


class Asset(AssetBase):
    id: int
    user_id: int
    account_id: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


# ---------------------------------------------------------------------------
# Liability
# ---------------------------------------------------------------------------

class LiabilityBase(BaseModel):
    liability_type: LiabilityType
    name: str = Field(..., min_length=1, max_length=200)
    institution: str | None = None
    currency: str = Field(default="ZAR", min_length=3, max_length=3)
    outstanding_balance: Decimal = Field(..., ge=0)
    interest_rate: Decimal = Field(..., ge=0, le=100)
    minimum_payment: Decimal | None = None
    payment_frequency: PaymentFrequency = PaymentFrequency.MONTHLY
    original_term_months: int | None = None
    remaining_term_months: int | None = None
    start_date: date | None = None
    linked_asset_id: int | None = None
    access_facility_enabled: bool = False
    available_redraw_amount: Decimal | None = None


class LiabilityCreate(LiabilityBase):
    account_id: int | None = None


class LiabilityUpdate(BaseModel):
    liability_type: LiabilityType | None = None
    name: str | None = None
    institution: str | None = None
    currency: str | None = None
    outstanding_balance: Decimal | None = None
    interest_rate: Decimal | None = None
    minimum_payment: Decimal | None = None
    payment_frequency: PaymentFrequency | None = None
    original_term_months: int | None = None
    remaining_term_months: int | None = None
    start_date: date | None = None
    linked_asset_id: int | None = None
    access_facility_enabled: bool | None = None
    available_redraw_amount: Decimal | None = None


class Liability(LiabilityBase):
    id: int
    user_id: int
    account_id: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


# ---------------------------------------------------------------------------
# Balance-sheet aggregates
# ---------------------------------------------------------------------------

class BalanceSheetSummary(BaseModel):
    total_assets: Decimal
    total_liabilities: Decimal
    net_worth: Decimal
    assets: list[Asset] = Field(default_factory=list)
    liabilities: list[Liability] = Field(default_factory=list)


class HomeEquity(BaseModel):
    property_id: int
    property_name: str
    property_value: Decimal
    linked_liability_id: int | None = None
    outstanding_balance: Decimal = Decimal("0")
    home_equity: Decimal = Decimal("0")


class DebtRatio(BaseModel):
    total_assets: Decimal
    total_liabilities: Decimal
    debt_to_asset_ratio: Decimal


class AssetAllocation(BaseModel):
    asset_type: AssetType
    total_value: Decimal
    percentage: Decimal


# ---------------------------------------------------------------------------
# Simulation / scenario results
# ---------------------------------------------------------------------------

class AmortisationEntry(BaseModel):
    month: int
    opening_balance: Decimal
    payment: Decimal
    interest: Decimal
    principal: Decimal
    closing_balance: Decimal


class ExtraPaymentSimulation(BaseModel):
    liability_id: int
    current_remaining_months: int
    current_total_interest: Decimal
    extra_amount: Decimal
    new_remaining_months: int
    new_total_interest: Decimal
    interest_saved: Decimal
    months_saved: int


class BondVsSavingsComparison(BaseModel):
    amount: Decimal
    bond_interest_rate: Decimal
    savings_interest_rate: Decimal
    annual_bond_interest_saved: Decimal
    annual_savings_interest_earned: Decimal
    net_benefit_bond: Decimal
    recommendation_summary: str
