import json
import re

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import ValidationError

from app.llm import build_chat_model, llm_is_configured, missing_llm_config_message
from app.statements.schemas import ParsedStatement, StatementProvider

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
""",
    StatementProvider.FNB: """
FNB bank or investment statement. Look for account number/name, balances, and listed investments.
Use BANK for transactional accounts or ZAR_BROKER if brokerage holdings are listed.
Include cash balance as a CASH holding if present.
""",
    StatementProvider.ABSA: """
ABSA bank or investment statement. Extract account label, cash balance, and any funds or shares listed.
Use BANK for bank accounts; use ZAR_BROKER if share/ETF holdings appear.
""",
    StatementProvider.TENX_RA: """
10X retirement annuity (RA) statement. Extract RA account name, fund names, and fund values in ZAR.
Use account_type RA and institution 10X. Each fund is typically an ETF or OTHER holding.
""",
}

_JSON_SCHEMA_HINT = """{
  "account": {
    "name": "string",
    "account_type": "TFSA|RA|ZAR_BROKER|USD_BROKER|BANK|CASH|OTHER",
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
  "warnings": ["optional strings"]
}"""


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
    system = f"""You extract structured portfolio data from South African financial PDF statements.
Provider: {institution}
{PROVIDER_HINTS[provider]}

Rules:
- Set account.institution to "{institution}" unless the statement shows a clearer label.
- Use ISO currency codes (ZAR, USD).
- For each holding, set value to the market value in that holding's currency.
- If only a total balance is shown with no units, use symbol CASH, asset_class CASH, and value as the balance.
- Omit holdings with zero value.
- Add warnings for ambiguous or missing fields.

Respond with ONLY a single JSON object (no markdown, no commentary) matching this shape:
{_JSON_SCHEMA_HINT}"""

    llm = build_chat_model(max_tokens=8192)
    response = await llm.ainvoke(
        [
            SystemMessage(content=system),
            HumanMessage(
                content=f"Extract account and holdings from this statement text:\n\n{text[:80000]}"
            ),
        ]
    )

    raw = _message_text(response.content)
    result = _parse_llm_json(raw)

    if not result.account.institution:
        result.account.institution = institution
    if not result.holdings:
        result.warnings.append("No holdings were detected. Check the PDF or try another provider.")
    return result
