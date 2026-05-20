from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class StatementProvider(str, Enum):
    EASY_EQUITIES = "EASY_EQUITIES"
    FNB = "FNB"
    ABSA = "ABSA"
    TENX_RA = "TENX_RA"


AccountTypeLiteral = Literal[
    "TFSA", "RA", "ZAR_BROKER", "USD_BROKER", "BANK", "CASH", "OTHER"
]


class ParsedHolding(BaseModel):
    symbol: str = Field(..., description="Ticker or identifier, e.g. STX40, CASH")
    name: str = Field(..., description="Human-readable holding label")
    asset_class: str = Field(
        default="OTHER",
        description="One of: CASH, ETF, STOCK, BOND, PROPERTY, OTHER",
    )
    value: float = Field(..., ge=0, description="Market value in the holding currency")
    currency: str = Field(default="ZAR", min_length=3, max_length=3)
    quantity: float | None = Field(
        default=None,
        ge=0,
        description="Units held; if omitted, value is treated as a lump-sum balance",
    )


class ParsedAccount(BaseModel):
    name: str = Field(..., description="Account label from the statement")
    account_type: AccountTypeLiteral = Field(
        ...,
        description="TFSA, RA, ZAR_BROKER, USD_BROKER, BANK, CASH, or OTHER",
    )
    currency: str = Field(default="ZAR", min_length=3, max_length=3)
    institution: str = Field(..., description="Provider name, e.g. EasyEquities, FNB")


class ParsedStatement(BaseModel):
    account: ParsedAccount
    holdings: list[ParsedHolding] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
