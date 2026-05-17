from fastapi import APIRouter

from app import agents

router = APIRouter(prefix="/api/v1", tags=["agents"])


@router.get("/agents")
async def list_agents():
    return {
        "agents": agents.ALL_AGENTS,
        "active": agents.ACTIVE_AGENTS,
        "data_source": "financial-copilot-api",
    }
