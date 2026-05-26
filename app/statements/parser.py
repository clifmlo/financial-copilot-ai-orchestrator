import json
import re
from decimal import Decimal

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import ValidationError

from app.llm import build_chat_model, llm_is_configured, missing_llm_config_message
from app.statements.schemas import (
    MONEY_QUANT,
    ParsedLiability,
    ParsedStatement,
    StatementProvider,
)

PROVIDER_INSTITUTION = {
    StatementProvider.EASY_EQUITIES: "EasyEquities",
    StatementProvider.FNB: "FNB",
    StatementProvider.ABSA: "ABSA",
    StatementProvider.TENX_RA: "10X",
}

PROVIDER_HINTS = {
    StatementProvider.EASY_EQUITIES: """
EasyEquities investment statement. Look for account name (TFSA, ZAR portfolio, USD portfolio),
holdings with symbols/tickers, quantities, and market values in ZAR or USD.
Use ZAR_BROKER or USD_BROKER for brokerage accounts, TFSA for tax-free savings.
This provider only has investment statements, so statement_type is always INVESTMENT.
""",
    StatementProvider.FNB: """
FNB bank, investment, or home loan statement.
- For transactional/savings accounts: use statement_type INVESTMENT, account_type BANK, and
  list balances as CASH holdings.
- For brokerage/share portfolio statements: use statement_type INVESTMENT, account_type ZAR_BROKER.
- For home loan or vehicle finance statements: use statement_type LOAN, account_type LOAN, and
  populate parsed_liability with the outstanding balance, interest rate, monthly instalment,
  original and remaining term, and account number.
""",
    StatementProvider.ABSA: """
ABSA bank, investment, or home loan statement.
- For transactional/savings accounts: use statement_type INVESTMENT, account_type BANK, and
  list balances as CASH holdings.
- For share/ETF portfolio statements: use statement_type INVESTMENT, account_type ZAR_BROKER.
- For home loan or vehicle finance statements: use statement_type LOAN, account_type LOAN, and
  populate parsed_liability with:
  - liability_type: HOME_LOAN for home loans, VEHICLE_FINANCE for vehicle finance
  - outstanding_balance: use the CLOSING BALANCE from transactions (not the total loan amount)
  - interest_rate: the annual interest rate (e.g. 9.4 for 9.4%)
  - minimum_payment: the "Total Repayment" or monthly instalment amount
  - original_term_months: the original loan term in months (e.g. 240 for 20 years) if shown
  - remaining_term_months: remaining months if shown
  - account_number: the loan account number
  Holdings should be empty for loan statements.
  If a FlexiReserve balance is shown, set accessFacilityEnabled to true.

IMPORTANT: Look for these keywords that indicate a LOAN statement (NOT investment):
  "Mortgage", "Home Loan", "Interim Mortgage", "Total loan amount", "Repayment",
  "FlexiReserve", "INTEREST CAPITALIZED", "CLOSING BALANCE", "Property Description".
  If ANY of these appear, this is a LOAN statement — set statement_type to "LOAN".
""",
    StatementProvider.TENX_RA: """
10X retirement annuity (RA) statement. Extract RA account name, fund names, and fund values in ZAR.
Use account_type RA and institution 10X. Each fund is typically an ETF or OTHER holding.
This provider only has investment statements, so statement_type is always INVESTMENT.
""",
}

_JSON_SCHEMA_HINT = """{
  "statement_type": "INVESTMENT or LOAN",
  "account": {
    "name": "string",
    "account_type": "TFSA|RA|ZAR_BROKER|USD_BROKER|BANK|CASH|LOAN|OTHER",
    "currency": "ZAR",
    "institution": "string"
  },
  "holdings": [
    {
      "symbol": "string",
      "name": "string",
      "asset_class": "CASH|ETF|STOCK|BOND|PROPERTY|OTHER",
      "value": 0.0,
      "currency": "ZAR",
      "quantity": null
    }
  ],
  "parsed_liability": {
    "liability_type": "HOME_LOAN|VEHICLE_FINANCE|PERSONAL_LOAN|CREDIT_CARD|STUDENT_LOAN|BUSINESS_LOAN|OTHER",
    "name": "string",
    "institution": "string",
    "currency": "ZAR",
    "outstanding_balance": 0.0,
    "interest_rate": 0.0,
    "minimum_payment": null,
    "original_term_months": null,
    "remaining_term_months": null,
    "account_number": null,
    "access_facility_enabled": false,
    "available_redraw_amount": null
  },
  "warnings": ["optional strings"],
  "statement_total": null
}"""


def _reconcile_totals(result: ParsedStatement) -> ParsedStatement:
    if not result.holdings:
        return result
    line_sum = sum((h.value for h in result.holdings), Decimal("0"))
    if result.statement_total is not None:
        diff = abs(line_sum - result.statement_total)
        if diff > Decimal("1.00"):
            result.warnings.append(
                f"Holdings sum to {line_sum} but the statement total is "
                f"{result.statement_total} (difference {diff}). "
                "Edit line values or discard and re-upload if needed."
            )
        result.statement_total = line_sum.quantize(MONEY_QUANT)
    return result


def _message_text(content: object) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("text", "")))
        return "\n".join(parts)
    return str(content)


def _strip_json_fence(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped, flags=re.IGNORECASE)
        stripped = re.sub(r"\s*```$", "", stripped)
    return stripped.strip()


def _parse_llm_json(raw: str) -> ParsedStatement:
    cleaned = _strip_json_fence(raw)
    if not cleaned:
        raise ValueError("The AI returned an empty response. Try again.")

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(
            "The AI response was not valid JSON. Try again or pick a different provider."
        ) from exc

    try:
        return ParsedStatement.model_validate(data)
    except ValidationError as exc:
        raise ValueError(f"AI output did not match the expected statement shape: {exc}") from exc


async def parse_statement_pdf(text: str, provider: StatementProvider) -> ParsedStatement:
    if not llm_is_configured():
        raise RuntimeError(missing_llm_config_message())

    institution = PROVIDER_INSTITUTION[provider]
    system = f"""You extract structured data from South African financial PDF statements.
Provider: {institution}
{PROVIDER_HINTS[provider]}

Rules:
- First determine if the statement is an investment/bank statement or a loan statement.
- Set statement_type to "INVESTMENT" for bank/investment/portfolio statements.
- Set statement_type to "LOAN" for home loan, vehicle finance, or any loan/bond statements.
- Set account.institution to "{institution}" unless the statement shows a clearer label.
- Use ISO currency codes (ZAR, USD).

For INVESTMENT statements:
- For each holding, set value to the market value in that holding's currency (2 decimal places).
- If the statement shows a portfolio/account grand total, set statement_total.
- If only a total balance is shown with no units, use symbol CASH, asset_class CASH.
- Omit holdings with zero value.
- Set parsed_liability to null.

For LOAN statements:
- Set account.account_type to "LOAN".
- Populate parsed_liability with all available loan details from the statement.
- Extract: outstanding_balance, interest_rate (annual %), minimum_payment (monthly instalment),
  original_term_months, remaining_term_months, account_number.
- If a FlexiReserve or access bond balance is shown, set access_facility_enabled to true and
  available_redraw_amount to that balance.
- Set holdings to an empty array [].
- Set statement_total to the outstanding balance.

General:
- Add warnings for ambiguous or missing fields.
- Do not round line items; copy amounts exactly as shown on the statement.

Respond with ONLY a single JSON object (no markdown, no commentary) matching this shape:
{_JSON_SCHEMA_HINT}

For INVESTMENT statements, set parsed_liability to null.
For LOAN statements, set holdings to [] and populate parsed_liability."""

    llm = build_chat_model(max_tokens=8192)
    messages = [
        SystemMessage(content=system),
        HumanMessage(
            content=f"Extract data from this statement text:\n\n{text[:80000]}"
        ),
    ]
    response = llm.invoke(messages)

    raw = _message_text(response.content)
    result = _parse_llm_json(raw)

    if not result.account.institution:
        result.account.institution = institution

    result = _auto_detect_loan(result, text, institution)

    if result.statement_type == "LOAN":
        if result.parsed_liability and not result.parsed_liability.institution:
            result.parsed_liability.institution = institution
        if result.parsed_liability and not result.parsed_liability.name:
            result.parsed_liability.name = result.account.name
        if not result.parsed_liability:
            result.warnings.append(
                "This looks like a loan statement but no loan details could be extracted."
            )
    else:
        if not result.holdings:
            result.warnings.append(
                "No holdings were detected. Check the PDF or try another provider."
            )

    return _reconcile_totals(result)


_LOAN_KEYWORDS = re.compile(
    r"mortgage|home\s*loan|vehicle\s*finance|total\s*loan\s*amount|"
    r"flexireserve|interest\s*capitali[sz]ed|repayment\s*due\s*day|"
    r"interim\s*mortgage|bond\s*statement|property\s*description",
    re.IGNORECASE,
)


def _auto_detect_loan(
    result: ParsedStatement, pdf_text: str, institution: str
) -> ParsedStatement:
    """Fix misclassified loan statements using keyword detection and account_type."""
    if result.statement_type == "LOAN":
        return result

    is_loan_account_type = result.account.account_type == "LOAN"
    has_loan_keywords = bool(_LOAN_KEYWORDS.search(pdf_text[:5000]))

    if not is_loan_account_type and not has_loan_keywords:
        return result

    result.statement_type = "LOAN"
    result.account.account_type = "LOAN"

    if result.parsed_liability:
        return result

    balance = _extract_amount(pdf_text, r"closing\s*balance\s*(?:R?\s*)([\d,]+\.?\d*)")
    if not balance:
        balance = _extract_amount(pdf_text, r"total\s*loan\s*amount\s*(?:R?\s*)([\d,]+\.?\d*)")
    rate = _extract_amount(pdf_text, r"interest\s*rate\s*([\d.]+)\s*%")
    payment = _extract_amount(pdf_text, r"total\s*repayment\s*(?:R?\s*)([\d,]+\.?\d*)")
    if not payment:
        payment = _extract_amount(pdf_text, r"instalment\s*(?:R?\s*)([\d,]+\.?\d*)")
    acct_num = _extract_text(pdf_text, r"account\s*number\s*([\d]+)")

    flexi = _extract_amount(pdf_text, r"flexireserve\s*balance\s*(?:R?\s*)([\d,]+\.?\d*)")

    if balance:
        from decimal import Decimal

        result.parsed_liability = ParsedLiability(
            liability_type="HOME_LOAN" if has_loan_keywords else "OTHER",
            name=result.account.name,
            institution=institution,
            currency=result.account.currency,
            outstanding_balance=Decimal(str(balance)),
            interest_rate=Decimal(str(rate)) if rate else Decimal("0"),
            minimum_payment=Decimal(str(payment)) if payment else None,
            account_number=acct_num,
            access_facility_enabled=flexi is not None and flexi > 0,
            available_redraw_amount=Decimal(str(flexi)) if flexi else None,
        )
        result.holdings = []
        result.statement_total = Decimal(str(balance))
        result.warnings.append(
            "Statement was auto-detected as a loan from PDF keywords."
        )

    return result


def _extract_amount(text: str, pattern: str) -> float | None:
    m = re.search(pattern, text, re.IGNORECASE)
    if m:
        try:
            return float(m.group(1).replace(",", ""))
        except ValueError:
            pass
    return None


def _extract_text(text: str, pattern: str) -> str | None:
    m = re.search(pattern, text, re.IGNORECASE)
    return m.group(1).strip() if m else None
