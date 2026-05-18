"""Chat turn execution with session memory and streaming."""

import json
import uuid
from collections.abc import AsyncIterator

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langgraph.checkpoint.memory import MemorySaver

from app.graph.orchestrator import (
    AgentState,
    build_graph,
    trim_message_history,
)

MAX_HISTORY_MESSAGES = 20

_checkpointer = MemorySaver()
orchestrator = build_graph(checkpointer=_checkpointer)


def ensure_session_id(session_id: str | None) -> str:
    return session_id or str(uuid.uuid4())


def thread_config(session_id: str) -> dict:
    return {"configurable": {"thread_id": session_id}}


def initial_state(user_text: str) -> AgentState:
    return {
        "messages": [HumanMessage(content=user_text)],
        "portfolio_context": "",
        "active_agent": "general",
    }


def _message_content(message: BaseMessage) -> str:
    content = message.content
    return content if isinstance(content, str) else str(content)


async def invoke_chat(session_id: str, user_text: str) -> tuple[str, str]:
    """Run one conversational turn; history is persisted via LangGraph checkpointer."""
    config = thread_config(session_id)
    result = await orchestrator.ainvoke(initial_state(user_text), config=config)
    reply = _message_content(result["messages"][-1])
    return reply, result.get("active_agent", "general")


async def stream_chat(session_id: str, user_text: str) -> AsyncIterator[str]:
    """Yield Server-Sent Events: token chunks, then done metadata."""
    config = thread_config(session_id)
    input_state = initial_state(user_text)

    async for event in orchestrator.astream_events(
        input_state,
        config=config,
        version="v2",
    ):
        if event.get("event") != "on_chat_model_stream":
            continue
        chunk = event.get("data", {}).get("chunk")
        if chunk is None:
            continue
        text = getattr(chunk, "content", None)
        if isinstance(text, str) and text:
            payload = json.dumps({"text": text})
            yield f"event: token\ndata: {payload}\n\n"

    snapshot = await orchestrator.aget_state(config)
    active_agent = "general"
    if snapshot and snapshot.values:
        active_agent = snapshot.values.get("active_agent", "general")

    done_payload = json.dumps(
        {"active_agent": active_agent, "session_id": session_id}
    )
    yield f"event: done\ndata: {done_payload}\n\n"


async def get_session_messages(session_id: str) -> list[dict[str, str]]:
    """Return persisted message history for a session (for UI restore)."""
    config = thread_config(session_id)
    snapshot = await orchestrator.aget_state(config)
    if not snapshot or not snapshot.values:
        return []

    history: list[dict[str, str]] = []
    for msg in snapshot.values.get("messages", []):
        if isinstance(msg, HumanMessage):
            history.append({"role": "user", "content": _message_content(msg)})
        elif isinstance(msg, AIMessage):
            history.append({"role": "assistant", "content": _message_content(msg)})
    return trim_message_history_dicts(history, MAX_HISTORY_MESSAGES)


def trim_message_history_dicts(
    history: list[dict[str, str]], max_messages: int
) -> list[dict[str, str]]:
    if len(history) <= max_messages:
        return history
    return history[-max_messages:]
