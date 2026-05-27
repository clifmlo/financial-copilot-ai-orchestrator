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


def _yield_token(text: str) -> str:
    payload = json.dumps({"text": text})
    return f"event: token\ndata: {payload}\n\n"


def _yield_done(active_agent: str, session_id: str) -> str:
    done_payload = json.dumps({"active_agent": active_agent, "session_id": session_id})
    return f"event: done\ndata: {done_payload}\n\n"


def _yield_error(message: str) -> str:
    payload = json.dumps({"message": message})
    return f"event: error\ndata: {payload}\n\n"


def _chunk_text(text: str, size: int = 80) -> list[str]:
    return [text[i : i + size] for i in range(0, len(text), size)]


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
    emitted_tokens = False

    try:
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
                emitted_tokens = True
                yield _yield_token(text)

        snapshot = await orchestrator.aget_state(config)
        active_agent = "general"
        reply = ""
        if snapshot and snapshot.values:
            active_agent = snapshot.values.get("active_agent", "general")
            messages = snapshot.values.get("messages", [])
            if messages:
                reply = _message_content(messages[-1])

        if not emitted_tokens and reply:
            for piece in _chunk_text(reply):
                yield _yield_token(piece)

        yield _yield_done(active_agent, session_id)
    except Exception as exc:
        yield _yield_error(str(exc))
        yield _yield_done("general", session_id)


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
