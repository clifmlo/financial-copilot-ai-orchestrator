"""Schemas for bank statement cashflow extraction."""

from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from enum import Enum

from pydantic import BaseModel, Field, field_validator

MONEY_QUANT = Decimal("0.01")


def _money(value: object) -> Decimal:
    return Decimal(str(value)).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


class BankStatementProvider(str, Enum):
    FNB = "FNB"
    ABSA = "ABSA"
    STANDARD_BANK = "STANDARD_BANK"
    NEDBANK = "NEDBANK"
    CAPITEC = "CAPITEC"
    OTHER = "OTHER"


class ParsedBankTransaction(BaseModel):
    transaction_date: date
    description: str = Field(..., min_length=1)
    money_in: Decimal = Field(default=Decimal("0"), ge=0)
    money_out: Decimal = Field(default=Decimal("0"), ge=0)
    balance_after: Decimal | None = Field(default=None, ge=0)

    @field_validator("money_in", "money_out", "balance_after", mode="before")
    @classmethod
    def round_money(cls, v: object) -> object:
        if v is None:
            return v
        return _money(v)


class ParsedBankStatement(BaseModel):
    account_name: str = Field(default="Bank Account")
    institution: str = Field(default="")
    currency: str = Field(default="ZAR", min_length=3, max_length=3)
    account_number_masked: str | None = Field(
        default=None,
        description="Last 4 digits or masked account number only",
    )
    transactions: list[ParsedBankTransaction] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
