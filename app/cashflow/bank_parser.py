"""Extract transactional bank statement rows from PDF text."""

import asyncio
import json
import re

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import ValidationError

from app.cashflow.fnb_parser import parse_fnb_statement_text
from app.cashflow.schemas import BankStatementProvider, ParsedBankStatement
from app.llm import build_chat_model, llm_is_configured, missing_llm_config_message
from app.statements.parser import _message_text, _strip_json_fence

PROVIDER_INSTITUTION = {
    BankStatementProvider.FNB: "FNB",
    BankStatementProvider.ABSA: "ABSA",
    BankStatementProvider.STANDARD_BANK: "Standard Bank",
    BankStatementProvider.NEDBANK: "Nedbank",
    BankStatementProvider.CAPITEC: "Capitec",
    BankStatementProvider.OTHER: "Other",
}

PROVIDER_HINTS = {
    BankStatementProvider.FNB: """
FNB transactional bank account statement. Extract every transaction line with date, description,
money in (credit), money out (debit), and running balance when shown.
Ignore opening balance summary rows unless they are dated transactions.
""",
    BankStatementProvider.ABSA: """
ABSA transactional bank account statement. Extract dated debit/credit transactions.
Use CLOSING BALANCE only as balance_after on the last transaction if no per-line balance exists.
""",
    BankStatementProvider.STANDARD_BANK: """
Standard Bank transactional statement. Map deposits to money_in and payments to money_out.
""",
    BankStatementProvider.NEDBANK: """
Nedbank transactional statement. Extract all dated transaction lines.
""",
    BankStatementProvider.CAPITEC: """
Capitec transactional statement. Extract dated transactions with amounts.
""",
    BankStatementProvider.OTHER: """
Generic South African bank transactional statement. Extract dated transactions only.
""",
}

_JSON_SCHEMA_HINT = """{
  "account_name": "string",
  "institution": "string",
  "currency": "ZAR",
  "account_number_masked": "****1234 or null",
  "transactions": [
    {
      "transaction_date": "YYYY-MM-DD",
      "description": "string",
      "money_in": 0.0,
      "money_out": 0.0,
      "balance_after": null
    }
  ],
  "warnings": ["optional strings"]
}"""


def _salvage_json_object(cleaned: str) -> dict:
    """Recover a partial LLM JSON payload when the response was truncated."""
    start = cleaned.find("{")
    if start < 0:
        raise ValueError("The AI response was not valid JSON. Try again.")

    fragment = cleaned[start:]
    for end in range(len(fragment), 0, -1):
        try:
            return json.loads(fragment[:end])
        except json.JSONDecodeError:
            continue

    txn_start = fragment.find('"transactions"')
    if txn_start >= 0:
        array_start = fragment.find("[", txn_start)
        if array_start >= 0:
            objects: list[str] = []
            depth = 0
            current: list[str] = []
            for ch in fragment[array_start + 1 :]:
                if ch == "{":
                    depth += 1
                if depth > 0:
                    current.append(ch)
                if ch == "}":
                    depth -= 1
                    if depth == 0 and current:
                        objects.append("{" + "".join(current) + "}")
                        current = []
            if objects:
                txns = [json.loads(o) for o in objects]
                prefix = fragment[:array_start + 1]
                return json.loads(f'{prefix}{json.dumps(txns)}]}}')

    raise ValueError(
        "The AI response was cut off before it finished. Try again or use a shorter statement period."
    )


def _parse_llm_json(raw: str) -> ParsedBankStatement:
    cleaned = _strip_json_fence(raw)
    if not cleaned:
        raise ValueError("The AI returned an empty response. Try again.")

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        data = _salvage_json_object(cleaned)

    try:
        return ParsedBankStatement.model_validate(data)
    except ValidationError as exc:
        raise ValueError(f"AI output did not match the expected bank statement shape: {exc}") from exc


def _filter_valid_transactions(result: ParsedBankStatement) -> ParsedBankStatement:
    valid = []
    for txn in result.transactions:
        if txn.money_in <= 0 and txn.money_out <= 0:
            continue
        if txn.money_in > 0 and txn.money_out > 0:
            result.warnings.append(
                f"Skipped ambiguous line with both debit and credit: {txn.description[:60]}"
            )
            continue
        valid.append(txn)
    result.transactions = valid
    return result


def _parse_bank_statement_llm(text: str, provider: BankStatementProvider) -> ParsedBankStatement:
    if not llm_is_configured():
        raise RuntimeError(missing_llm_config_message())

    institution = PROVIDER_INSTITUTION[provider]
    system = f"""You extract transactional data from South African BANK ACCOUNT statements (not investment portfolios, not home loans).

Provider: {institution}
{PROVIDER_HINTS[provider]}

Rules:
- Extract ONLY individual dated transactions from the statement period.
- transaction_date must be ISO format YYYY-MM-DD.
- money_in = credits/deposits (positive number, 0 if debit only).
- money_out = debits/payments (positive number, 0 if credit only).
- Never put the same amount in both money_in and money_out for one row.
- description = narrative as shown (payee, reference, etc.).
- balance_after = running balance after the transaction when the statement shows it; else null.
- Set institution to "{institution}" unless the PDF shows a clearer bank name.
- account_number_masked: only last 4 digits with mask, e.g. ****1234 — never full account numbers.
- Omit duplicate header/footer lines and opening/closing summary blocks that are not dated transactions.
- Do NOT include home loan, bond, or investment holdings — only bank account transactions.
- Add warnings for missing pages, unclear amounts, or password-protected sections.

Respond with ONLY a single JSON object matching:
{_JSON_SCHEMA_HINT}
"""

    llm = build_chat_model(max_tokens=16384)
    messages = [
        SystemMessage(content=system),
        HumanMessage(
            content=f"Extract bank transactions from this statement text:\n\n{text[:100000]}"
        ),
    ]
    response = llm.invoke(messages)
    raw = _message_text(response.content)
    result = _parse_llm_json(raw)

    if not result.institution:
        result.institution = institution
    if not result.account_name:
        result.account_name = f"{institution} Account"

    result = _filter_valid_transactions(result)

    if not result.transactions:
        result.warnings.append(
            "No transactions were detected. Check the PDF is a transactional bank statement."
        )

    return result


async def parse_bank_statement_pdf(
    text: str, provider: BankStatementProvider
) -> ParsedBankStatement:
    if provider == BankStatementProvider.FNB:
        fnb = parse_fnb_statement_text(text)
        if fnb and fnb.transactions:
            return _filter_valid_transactions(fnb)

    return await asyncio.to_thread(_parse_bank_statement_llm, text, provider)
