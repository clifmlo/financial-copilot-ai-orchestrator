from typing import Literal

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, model_validator

from app.auth_context import set_auth_token
from app.graph.chat_service import (
    ensure_session_id,
    get_session_messages,
    invoke_chat,
    stream_chat,
)

router = APIRouter(prefix="/api/v1", tags=["chat"])


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(..., min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    message: str | None = Field(default=None, max_length=4000)
    messages: list[ChatMessage] | None = None
    session_id: str | None = None

    @model_validator(mode="after")
    def require_message_or_history(self) -> "ChatRequest":
        has_message = self.message and self.message.strip()
        has_history = self.messages and len(self.messages) > 0
        if not has_message and not has_history:
            raise ValueError("Provide message or messages")
        return self


class ChatResponse(BaseModel):
    reply: str
    active_agent: str
    session_id: str


class SessionHistoryResponse(BaseModel):
    session_id: str
    messages: list[ChatMessage]


def _apply_auth(authorization: str | None) -> None:
    if authorization and authorization.startswith("Bearer "):
        set_auth_token(authorization[7:].strip())
    elif authorization:
        set_auth_token(authorization.strip())
    else:
        set_auth_token(None)


def _resolve_user_text(request: ChatRequest) -> str:
    if request.message and request.message.strip():
        return request.message.strip()
    if request.messages:
        for item in reversed(request.messages):
            if item.role == "user" and item.content.strip():
                return item.content.strip()
    raise HTTPException(status_code=400, detail="No user message found")


@router.get("/chat/session/{session_id}", response_model=SessionHistoryResponse)
async def get_session(
    session_id: str,
    authorization: str | None = Header(default=None),
):
    _apply_auth(authorization)
    history = await get_session_messages(session_id)
    return SessionHistoryResponse(
        session_id=session_id,
        messages=[ChatMessage(role=m["role"], content=m["content"]) for m in history],
    )


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    authorization: str | None = Header(default=None),
):
    _apply_auth(authorization)
    session_id = ensure_session_id(request.session_id)
    user_text = _resolve_user_text(request)
    reply, active_agent = await invoke_chat(session_id, user_text)
    return ChatResponse(
        reply=reply,
        active_agent=active_agent,
        session_id=session_id,
    )


@router.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    authorization: str | None = Header(default=None),
):
    _apply_auth(authorization)
    session_id = ensure_session_id(request.session_id)
    user_text = _resolve_user_text(request)

    return StreamingResponse(
        stream_chat(session_id, user_text),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
