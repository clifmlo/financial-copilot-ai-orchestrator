from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import agents, chat, health, statements
from app.config import settings

app = FastAPI(
    title="Financial Copilot AI Orchestrator",
    description=(
        "LangGraph multi-agent orchestration for Financial Copilot. "
        "Reads financial data from financial-copilot-api only."
    ),
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(chat.router)
app.include_router(agents.router)
app.include_router(statements.router)
