from pathlib import Path
from typing import Annotated, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

from app import agents
from app.config import settings
from app.tools.portfolio import fetch_dashboard

SYSTEM_PROMPT = (Path(__file__).parent.parent / "prompts" / "system_prompt.txt").read_text()


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
    if any(k in lower for k in ("bond", "mortgage", "home loan")):
        return agents.BOND_OPTIMISATION
    if any(k in lower for k in ("risk", "volatility", "drawdown")):
        return agents.RISK_ANALYSIS
    if any(k in lower for k in ("portfolio", "holding", "net worth", "allocation", "etf", "invest")):
        return agents.PORTFOLIO_ANALYSIS
    return agents.GENERAL


async def planner_node(state: AgentState) -> AgentState:
    last = state["messages"][-1].content if state["messages"] else ""
    agent = _route_agent(last)
    return {**state, "active_agent": agent}


async def portfolio_context_node(state: AgentState) -> AgentState:
    """Load portfolio snapshot from financial-copilot-api for downstream agents."""
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
            "Suggest seeding demo data via POST /api/v1/demo/seed on the portfolio API."
        )
    return {**state, "portfolio_context": context}


def _needs_portfolio_context(agent: str) -> bool:
    return agent in {
        agents.PORTFOLIO_ANALYSIS,
        agents.TAX,
        agents.BOND_OPTIMISATION,
        agents.RISK_ANALYSIS,
        agents.RECOMMENDATION,
        agents.REPORT_GENERATION,
        agents.SCENARIO,
    }


async def respond_node(state: AgentState) -> AgentState:
    if not settings.openai_api_key:
        fallback = (
            "AI responses require OPENAI_API_KEY. "
            f"Active agent: {state.get('active_agent')}. "
            f"Portfolio context: {state.get('portfolio_context', 'N/A')}"
        )
        return {**state, "messages": state["messages"] + [AIMessage(content=fallback)]}

    llm = ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=0.3,
    )
    agent = state.get("active_agent", agents.GENERAL)
    agent_instruction = {
        agents.REPORT_GENERATION: "Produce a concise wealth report narrative using only the portfolio context.",
        agents.SCENARIO: "Interpret the user's scenario using portfolio context; discuss trade-offs, not advice.",
        agents.RECOMMENDATION: "Narrate recommendations grounded in the portfolio context; explain reasoning.",
        agents.TAX: "Discuss tax considerations educationally; defer calculations to the portfolio API.",
        agents.BOND_OPTIMISATION: "Discuss bond/mortgage trade-offs using liability figures from context.",
        agents.RISK_ANALYSIS: "Assess risk and diversification using holdings and allocation from context.",
        agents.PORTFOLIO_ANALYSIS: "Analyse the portfolio using the provided figures.",
    }.get(agent, "Answer the user's question clearly.")

    system = SystemMessage(content=SYSTEM_PROMPT)
    context_msg = SystemMessage(
        content=(
            f"Active agent: {agent}\n"
            f"Task: {agent_instruction}\n"
            f"{state.get('portfolio_context', '')}"
        )
    )
    response = await llm.ainvoke([system, context_msg, *state["messages"]])
    return {**state, "messages": state["messages"] + [response]}


def _after_planner(state: AgentState) -> str:
    return "portfolio" if _needs_portfolio_context(state.get("active_agent", "")) else "respond"


def build_graph():
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
    return graph.compile()


orchestrator = build_graph()
