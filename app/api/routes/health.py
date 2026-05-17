from fastapi import APIRouter

from app.clients.portfolio_api import PortfolioApiError, get_portfolio_client
from app.config import settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "financial-copilot-ai-orchestrator",
        "portfolio_api": settings.portfolio_api_url,
    }


@router.get("/health/dependencies")
async def health_dependencies():
    """Verify connectivity to financial-copilot-api (system of record)."""
    try:
        portfolio = await get_portfolio_client().health()
        return {"status": "ok", "portfolio_api": portfolio}
    except PortfolioApiError as exc:
        return {
            "status": "degraded",
            "portfolio_api": {"error": exc.detail, "status_code": exc.status_code},
        }
