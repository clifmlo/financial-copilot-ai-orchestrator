from decimal import ROUND_HALF_UP, Decimal
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, field_validator

MONEY_QUANT = Decimal("0.01")


def _money(value: object) -> Decimal:
    return Decimal(str(value)).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


class StatementProvider(str, Enum):
    EASY_EQUITIES = "EASY_EQUITIES"
    FNB = "FNB"
    ABSA = "ABSA"
    TENX_RA = "TENX_RA"


AccountTypeLiteral = Literal[
    "TFSA", "RA", "ZAR_BROKER", "USD_BROKER", "BANK", "CASH", "LOAN", "OTHER"
]

StatementTypeLiteral = Literal["INVESTMENT", "LOAN"]

LiabilityTypeLiteral = Literal[
    "HOME_LOAN", "VEHICLE_FINANCE", "PERSONAL_LOAN",
    "CREDIT_CARD", "STUDENT_LOAN", "BUSINESS_LOAN", "OTHER",
]


class ParsedHolding(BaseModel):
    symbol: str = Field(..., description="Ticker or identifier, e.g. STX40, CASH")
    name: str = Field(..., description="Human-readable holding label")
    asset_class: str = Field(
        default="OTHER",
        description="One of: CASH, ETF, STOCK, BOND, PROPERTY, OTHER",
    )
    value: Decimal = Field(..., ge=0, description="Market value in the holding currency")
    currency: str = Field(default="ZAR", min_length=3, max_length=3)
    quantity: Decimal | None = Field(
        default=None,
        ge=0,
        description="Units held; if omitted, value is treated as a lump-sum balance",
    )

    @field_validator("value", "quantity", mode="before")
    @classmethod
    def round_money_fields(cls, v: object) -> object:
        if v is None:
            return v
        return _money(v)


class ParsedLiability(BaseModel):
    """Structured data extracted from a loan/bond statement."""

    liability_type: LiabilityTypeLiteral = Field(
        default="HOME_LOAN",
        description="HOME_LOAN, VEHICLE_FINANCE, PERSONAL_LOAN, CREDIT_CARD, STUDENT_LOAN, BUSINESS_LOAN, or OTHER",
    )
    name: str = Field(default="", description="Loan account name from the statement")
    institution: str = Field(default="", description="Lender name, e.g. ABSA, Standard Bank")
    currency: str = Field(default="ZAR", min_length=3, max_length=3)
    outstanding_balance: Decimal = Field(..., ge=0, description="Current outstanding balance")
    interest_rate: Decimal = Field(
        ..., ge=0, le=100, description="Annual interest rate as a percentage, e.g. 9.4"
    )
    minimum_payment: Decimal | None = Field(
        default=None, ge=0, description="Monthly instalment amount"
    )
    original_term_months: int | None = Field(
        default=None, ge=1, description="Original loan term in months"
    )
    remaining_term_months: int | None = Field(
        default=None, ge=0, description="Remaining months on the loan"
    )
    account_number: str | None = Field(
        default=None, description="Loan account number from the statement"
    )

    @field_validator("outstanding_balance", "interest_rate", "minimum_payment", mode="before")
    @classmethod
    def round_money_fields(cls, v: object) -> object:
        if v is None:
            return v
        return _money(v)


class ParsedAccount(BaseModel):
    name: str = Field(default="Unknown Account", description="Account label from the statement")
    account_type: AccountTypeLiteral = Field(
        default="OTHER",
        description="TFSA, RA, ZAR_BROKER, USD_BROKER, BANK, CASH, LOAN, or OTHER",
    )
    currency: str = Field(default="ZAR", min_length=3, max_length=3)
    institution: str = Field(default="", description="Provider name, e.g. EasyEquities, FNB")

    @field_validator("name", mode="before")
    @classmethod
    def name_default(cls, v: object) -> object:
        return v if v else "Unknown Account"

    @field_validator("account_type", mode="before")
    @classmethod
    def account_type_default(cls, v: object) -> object:
        return v if v else "OTHER"

    @field_validator("currency", mode="before")
    @classmethod
    def currency_default(cls, v: object) -> object:
        return v if v else "ZAR"


class ParsedStatement(BaseModel):
    statement_type: StatementTypeLiteral = Field(
        default="INVESTMENT",
        description="INVESTMENT for portfolio/bank statements, LOAN for home loan/vehicle/personal loan statements",
    )
    account: ParsedAccount
    holdings: list[ParsedHolding] = Field(default_factory=list)
    parsed_liability: ParsedLiability | None = Field(
        default=None,
        description="Populated when statement_type is LOAN, containing extracted loan details",
    )
    warnings: list[str] = Field(default_factory=list)
    statement_total: Decimal | None = Field(
        default=None,
        ge=0,
        description="Grand total printed on the statement, if visible",
    )

    @field_validator("statement_total", mode="before")
    @classmethod
    def round_statement_total(cls, v: object) -> object:
        if v is None:
            return v
        return _money(v)
