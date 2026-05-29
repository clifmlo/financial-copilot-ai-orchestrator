"""Rule-based parser for FNB transactional PDF text (avoids LLM truncation on long statements)."""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal

from app.cashflow.schemas import ParsedBankStatement, ParsedBankTransaction

_MONTHS = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}

# e.g. "01 Apr FNB App Payment To ... 80.00 97,893.79Cr" or "... 2,000.00Cr 57,744.69Cr 7.40"
_FNB_TXN_LINE = re.compile(
    r"^(\d{2}\s+[A-Za-z]{3})\s+"
    r"(.+?)\s+"
    r"([\d,]+\.\d{2})(Cr)?\s+"
    r"([\d,]+\.\d{2})(Cr|Dr)"
    r"(?:\s+([\d,]+\.\d{2}))?"
    r"\s*$"
)

_STATEMENT_YEAR = re.compile(
    r"Statement\s+Period\s*:\s*\d{1,2}\s+\w+\s+\d{4}\s+to\s+\d{1,2}\s+\w+\s+(\d{4})",
    re.IGNORECASE,
)
_ACCOUNT_LINE = re.compile(
    r"(?:Current\s+Acc|Account)\s*:?\s*(\d{6,})",
    re.IGNORECASE,
)


def _amount(value: str) -> Decimal:
    return Decimal(value.replace(",", ""))


def _infer_year(text: str) -> int:
    match = _STATEMENT_YEAR.search(text)
    if match:
        return int(match.group(1))
    match = re.search(r"Statement\s+Date\s*:\s*\d{1,2}\s+\w+\s+(\d{4})", text, re.I)
    if match:
        return int(match.group(1))
    return date.today().year


def _parse_txn_date(dd_mon: str, year: int) -> date | None:
    parts = dd_mon.split()
    if len(parts) != 2:
        return None
    day = int(parts[0])
    month = _MONTHS.get(parts[1].lower()[:3])
    if not month:
        return None
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _money_in_out(description: str, amount: Decimal, amount_is_credit: bool) -> tuple[Decimal, Decimal]:
    desc_lower = description.lower()
    credit_phrases = (
        "payment from",
        "magtape credit",
        "cash deposit",
        "deposit",
        " refund",
        "transfer from",
    )
    if amount_is_credit or any(p in desc_lower for p in credit_phrases):
        return amount, Decimal("0")
    return Decimal("0"), amount


def parse_fnb_statement_text(text: str) -> ParsedBankStatement | None:
    """Return parsed statement when text looks like an FNB transactional export."""
    if "fnb" not in text.lower() and "transactions in rand" not in text.lower():
        return None

    year = _infer_year(text)
    transactions: list[ParsedBankTransaction] = []

    account_name = "FNB Account"
    account_masked: str | None = None
    acc_match = _ACCOUNT_LINE.search(text)
    if acc_match:
        num = acc_match.group(1)
        account_masked = f"****{num[-4:]}"
        account_name = "FNB Private Clients Current Account"

    in_txn_section = False
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.lower().startswith("transactions in rand"):
            in_txn_section = True
            continue
        if not in_txn_section:
            continue
        if line.lower().startswith("date description"):
            continue
        if line.lower().startswith(("accrued", "bank", "charges", "branch number")):
            continue
        if re.match(r"^Page\s+\d+", line, re.I):
            in_txn_section = True
            continue

        match = _FNB_TXN_LINE.match(line)
        if not match:
            continue

        dd_mon, description, amt_str, amt_cr_flag, bal_str, _bal_sd, _fee = match.groups()
        txn_date = _parse_txn_date(dd_mon, year)
        if not txn_date:
            continue

        amount = _amount(amt_str)
        money_in, money_out = _money_in_out(description, amount, amt_cr_flag is not None)

        transactions.append(
            ParsedBankTransaction(
                transaction_date=txn_date,
                description=description.strip(),
                money_in=money_in,
                money_out=money_out,
                balance_after=_amount(bal_str),
            )
        )

    if not transactions:
        return None

    return ParsedBankStatement(
        account_name=account_name,
        institution="FNB",
        currency="ZAR",
        account_number_masked=account_masked,
        transactions=transactions,
        warnings=[],
    )
