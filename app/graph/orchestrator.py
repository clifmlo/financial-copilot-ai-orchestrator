import asyncio
from pathlib import Path
from typing import Annotated, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

from app import agents
from app.config import settings
from app.llm import build_chat_model, llm_is_configured, missing_llm_config_message
from app.tools.portfolio import fetch_dashboard
from app.tools.balance_sheet import (
    get_balance_sheet_summary,
    get_home_equity_tool,
    list_assets,
    list_liabilities,
)

SYSTEM_PROMPT = (Path(__file__).parent.parent / "prompts" / "system_prompt.txt").read_text()

BRIEF_TASK_SUFFIX = (
    " Keep the reply conversational and concise (2–4 short paragraphs max). "
    "Offer to go deeper only if the user wants more."
)


def messages_from_history(history: list[dict[str, str]]) -> list[BaseMessage]:
    """Convert API message dicts to LangChain messages."""
    result: list[BaseMessage] = []
    for item in history:
        role = item.get("role", "")
        content = (item.get("content") or "").strip()
        if not content:
            continue
        if role == "user":
            result.append(HumanMessage(content=content))
        elif role == "assistant":
            result.append(AIMessage(content=content))
    return result


def trim_message_history(messages: list[BaseMessage], max_messages: int) -> list[BaseMessage]:
    if len(messages) <= max_messages:
        return messages
    return messages[-max_messages:]


def _last_user_text(messages: list[BaseMessage]) -> str:
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            content = msg.content
            return content if isinstance(content, str) else str(content)
    return ""


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    portfolio_context: str
    active_agent: str


def _route_agent(user_text: str) -> str:
    lower = user_text.lower()
    if any(k in lower for k in ("report", "summary", "overview document")):
        return agents.REPORT_GENERATION
    if any(k in lower for k in ("scenario", "what if", "simulate")):
        return agents.SCENARIO
    if any(k in lower for k in ("recommend", "suggest", "should i")):
        return agents.RECOMMENDATION
    if any(k in lower for k in ("tax", "cgt", "ra deduction")):
        return agents.TAX
    if any(k in lower for k in (
        "bond", "mortgage", "home loan", "extra payment",
        "overpayment", "amortisation", "amortization",
    )):
        return agents.BOND_OPTIMISATION
    if any(k in lower for k in (
        "balance sheet", "asset", "liabilit", "debt",
        "equity", "property value", "net worth",
    )):
        return agents.BALANCE_SHEET
    if any(k in lower for k in ("risk", "volatility", "drawdown")):
        return agents.RISK_ANALYSIS
    if any(k in lower for k in ("portfolio", "holding", "allocation", "etf", "invest")):
        return agents.PORTFOLIO_ANALYSIS
    return agents.GENERAL


async def planner_node(state: AgentState) -> AgentState:
    last = _last_user_text(state["messages"])
    agent = _route_agent(last)
    return {**state, "active_agent": agent}


async def portfolio_context_node(state: AgentState) -> AgentState:
    """Load portfolio snapshot from financial-copilot-api for downstream agents."""
    agent = state.get("active_agent", "")

    # For balance-sheet or bond agents, fetch richer context
    if agent in {agents.BALANCE_SHEET, agents.BOND_OPTIMISATION}:
        return await _balance_sheet_context(state)

    try:
        dashboard = await fetch_dashboard()
        context = (
            f"Net worth (ZAR): {dashboard.get('netWorthZar')}\n"
            f"Total assets (ZAR): {dashboard.get('totalAssetsZar')}\n"
            f"Liabilities (ZAR): {dashboard.get('totalLiabilitiesZar')}\n"
            f"Health score: {dashboard.get('healthScore')}\n"
            f"Currency exposure: {dashboard.get('currencyExposure')}\n"
            f"Allocation by region: {dashboard.get('allocationByRegion')}\n"
            f"Top holdings: {[h.get('symbol') for h in dashboard.get('topHoldings', [])[:5]]}"
        )
    except Exception as exc:
        context = (
            f"Portfolio data unavailable from API: {exc}. "
            "Suggest signing in and importing portfolio data, or checking API connectivity."
        )
    return {**state, "portfolio_context": context}


async def _balance_sheet_context(state: AgentState) -> AgentState:
    """Build rich context for balance-sheet and bond-optimisation agents."""
    parts: list[str] = []

    try:
        summary = await get_balance_sheet_summary()
        parts.append(
            f"Balance Sheet Summary:\n"
            f"  Total assets: {summary.get('totalAssets')}\n"
            f"  Total liabilities: {summary.get('totalLiabilities')}\n"
            f"  Net worth: {summary.get('netWorth')}"
        )
    except Exception as exc:
        parts.append(f"Balance sheet unavailable: {exc}")

    try:
        assets = await list_assets()
        if assets:
            asset_lines = []
            for a in assets:
                asset_lines.append(
                    f"  - {a.get('name')} ({a.get('assetType')}): "
                    f"{a.get('currency', 'ZAR')} {a.get('currentValue')}"
                )
            parts.append("Assets:\n" + "\n".join(asset_lines))
    except Exception:
        pass

    try:
        liabs = await list_liabilities()
        if liabs:
            liab_lines = []
            for l in liabs:
                liab_lines.append(
                    f"  - {l.get('name')} ({l.get('liabilityType')}): "
                    f"balance {l.get('currency', 'ZAR')} {l.get('outstandingBalance')}, "
                    f"rate {l.get('interestRate')}%, "
                    f"payment {l.get('minimumPayment')}/month"
                )
            parts.append("Liabilities:\n" + "\n".join(liab_lines))
    except Exception:
        pass

    try:
        equity = await get_home_equity_tool()
        if equity:
            parts.append(
                f"Home Equity:\n"
                f"  Property: {equity.get('propertyName')} — value {equity.get('propertyValue')}\n"
                f"  Bond balance: {equity.get('outstandingBalance')}\n"
                f"  Equity: {equity.get('homeEquity')}"
            )
    except Exception:
        pass

    # Fall back to the dashboard if nothing came through
    if not parts:
        try:
            dashboard = await fetch_dashboard()
            parts.append(
                f"Net worth (ZAR): {dashboard.get('netWorthZar')}\n"
                f"Total assets (ZAR): {dashboard.get('totalAssetsZar')}\n"
                f"Liabilities (ZAR): {dashboard.get('totalLiabilitiesZar')}"
            )
        except Exception as exc:
            parts.append(
                f"All financial data unavailable: {exc}. "
                "Suggest importing data or checking API connectivity."
            )

    return {**state, "portfolio_context": "\n\n".join(parts)}


def _needs_portfolio_context(agent: str) -> bool:
    return agent in {
        agents.PORTFOLIO_ANALYSIS,
        agents.TAX,
        agents.BOND_OPTIMISATION,
        agents.BALANCE_SHEET,
        agents.RISK_ANALYSIS,
        agents.RECOMMENDATION,
        agents.REPORT_GENERATION,
        agents.SCENARIO,
    }


async def respond_node(state: AgentState) -> AgentState:
    if not llm_is_configured():
        fallback = (
            f"{missing_llm_config_message()} "
            f"Active agent: {state.get('active_agent')}. "
            f"Portfolio context: {state.get('portfolio_context', 'N/A')}"
        )
        return {**state, "messages": state["messages"] + [AIMessage(content=fallback)]}

    llm = build_chat_model()
    agent = state.get("active_agent", agents.GENERAL)
    agent_instruction = {
        agents.REPORT_GENERATION: (
            "Give a brief wealth snapshot from the portfolio context (bullet highlights). "
            "Offer a fuller report only if the user asks."
        ),
        agents.SCENARIO: (
            "Answer the what-if question in plain language with 2–3 key trade-offs from context."
        ),
        agents.RECOMMENDATION: (
            "Suggest 2–3 practical next steps grounded in context; one sentence each."
        ),
        agents.TAX: (
            "Explain the tax point simply; flag that exact numbers come from the portfolio API."
        ),
        agents.BOND_OPTIMISATION: (
            "Use the liability and balance-sheet context to explain bond optimisation. "
            "Compare extra repayment scenarios using the figures provided. "
            "Explain how access bond deposits reduce daily interest. "
            "Present scenarios, not commands. Mention assumptions. "
            "Never invent interest savings or payoff dates — only use figures from context."
        ),
        agents.BALANCE_SHEET: (
            "Explain the user's balance sheet in plain language. "
            "A home loan is a liability; the property is the asset; the difference is equity. "
            "Present total assets, total liabilities, net worth, and home equity clearly. "
            "Never invent balances — only use figures from context."
        ),
        agents.RISK_ANALYSIS: (
            "Summarise main risk/concentration issues in a few bullets from holdings and allocation."
        ),
        agents.PORTFOLIO_ANALYSIS: (
            "Summarise portfolio health in a short, friendly answer using the figures provided."
        ),
    }.get(agent, "Answer the user's latest question in a conversational tone.")

    agent_instruction += BRIEF_TASK_SUFFIX

    system = SystemMessage(
        content=(
            f"{SYSTEM_PROMPT}\n\n"
            f"Active agent: {agent}\n"
            f"Task: {agent_instruction}\n"
            f"{state.get('portfolio_context', '')}"
        )
    )
    history = trim_message_history(state["messages"], 20)
    # REST transport does not support LangChain async LLM calls (see langchain-google#791).
    if settings.llm_provider == "gemini":
        response = await asyncio.to_thread(llm.invoke, [system, *history])
    else:
        response = await llm.ainvoke([system, *history])
    return {**state, "messages": state["messages"] + [response]}


def _after_planner(state: AgentState) -> str:
    return "portfolio" if _needs_portfolio_context(state.get("active_agent", "")) else "respond"


def build_graph(*, checkpointer=None):
    graph = StateGraph(AgentState)
    graph.add_node("planner", planner_node)
    graph.add_node("portfolio", portfolio_context_node)
    graph.add_node("respond", respond_node)

    graph.set_entry_point("planner")
    graph.add_conditional_edges(
        "planner",
        _after_planner,
        {"portfolio": "portfolio", "respond": "respond"},
    )
    graph.add_edge("portfolio", "respond")
    graph.add_edge("respond", END)
    return graph.compile(checkpointer=checkpointer)
