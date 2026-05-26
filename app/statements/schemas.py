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
    account: ParsedAccount
    holdings: list[ParsedHolding] = Field(default_factory=list)
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
