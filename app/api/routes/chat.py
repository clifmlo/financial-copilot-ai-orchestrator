from fastapi import APIRouter
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field

from app.graph.orchestrator import orchestrator

router = APIRouter(prefix="/api/v1", tags=["chat"])


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    session_id: str | None = None


class ChatResponse(BaseModel):
    reply: str
    active_agent: str
    session_id: str | None = None


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    result = await orchestrator.ainvoke(
        {
            "messages": [HumanMessage(content=request.message)],
            "portfolio_context": "",
            "active_agent": "general",
        }
    )
    reply = result["messages"][-1].content
    return ChatResponse(
        reply=reply,
        active_agent=result.get("active_agent", "general"),
        session_id=request.session_id,
    )
