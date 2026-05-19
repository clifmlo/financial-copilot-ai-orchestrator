"""
HTTP client for financial-copilot-api versioned REST endpoints.

The orchestrator must not access financial data stores directly.
All portfolio, account, bond, and tax figures are fetched from the Spring Boot API.
"""

from typing import Any

import httpx

from app.auth_context import get_auth_token
from app.config import settings


class PortfolioApiError(Exception):
    """Raised when the portfolio API returns a non-success response."""

    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"Portfolio API error {status_code}: {detail}")


class PortfolioApiClient:
    """Thin client for /api/v1/* resources exposed by financial-copilot-api."""

    def __init__(
        self,
        base_url: str | None = None,
        timeout: float = 30.0,
    ):
        self._base = (base_url or settings.portfolio_api_base).rstrip("/")
        self._timeout = timeout

    def _auth_headers(self) -> dict[str, str]:
        token = get_auth_token()
        if not token:
            return {}
        return {"Authorization": f"Bearer {token}"}

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        url = f"{self._base}{path}"
        headers = {**self._auth_headers(), **kwargs.pop("headers", {})}
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.request(method, url, headers=headers, **kwargs)
        if response.is_error:
            raise PortfolioApiError(response.status_code, response.text)
        if response.status_code == 204:
            return None
        return response.json()

    async def get_dashboard(self) -> dict:
        return await self._request("GET", "/dashboard")

    async def list_accounts(self) -> list:
        return await self._request("GET", "/accounts")

    async def list_holdings(self, account_id: str) -> list:
        return await self._request("GET", f"/accounts/{account_id}/holdings")

    async def health(self) -> dict:
        """Actuator health on the portfolio service root (not versioned)."""
        root = settings.portfolio_api_url.rstrip("/")
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.get(f"{root}/actuator/health")
        if response.is_error:
            raise PortfolioApiError(response.status_code, response.text)
        return response.json()


def get_portfolio_client() -> PortfolioApiClient:
    return PortfolioApiClient()
