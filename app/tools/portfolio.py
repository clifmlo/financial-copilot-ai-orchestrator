"""LangGraph tools that read financial data exclusively via financial-copilot-api."""

from app.clients.portfolio_api import PortfolioApiClient, get_portfolio_client


async def fetch_dashboard(client: PortfolioApiClient | None = None) -> dict:
    return await (client or get_portfolio_client()).get_dashboard()


async def fetch_accounts(client: PortfolioApiClient | None = None) -> list:
    return await (client or get_portfolio_client()).list_accounts()


async def fetch_holdings(account_id: str, client: PortfolioApiClient | None = None) -> list:
    return await (client or get_portfolio_client()).list_holdings(account_id)
