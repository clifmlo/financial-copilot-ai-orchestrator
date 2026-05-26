"""
HTTP client for financial-copilot-api versioned REST endpoints.

The orchestrator must not access financial data stores directly.
All portfolio, account, asset, liability, bond, and tax figures are
fetched from the Spring Boot API (system of record).
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

    # ----- Dashboard / legacy ------------------------------------------------

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

    # ----- Assets ------------------------------------------------------------

    async def create_asset(self, payload: dict) -> dict:
        return await self._request("POST", "/assets", json=payload)

    async def list_assets(self) -> list:
        return await self._request("GET", "/assets")

    async def get_asset(self, asset_id: int) -> dict:
        return await self._request("GET", f"/assets/{asset_id}")

    async def update_asset(self, asset_id: int, payload: dict) -> dict:
        return await self._request("PUT", f"/assets/{asset_id}", json=payload)

    async def delete_asset(self, asset_id: int) -> None:
        return await self._request("DELETE", f"/assets/{asset_id}")

    async def get_valuation_history(self, asset_id: int) -> list:
        return await self._request("GET", f"/assets/{asset_id}/valuation-history")

    # ----- Liabilities -------------------------------------------------------

    async def create_liability(self, payload: dict) -> dict:
        return await self._request("POST", "/liabilities", json=payload)

    async def list_liabilities(self) -> list:
        return await self._request("GET", "/liabilities")

    async def get_liability(self, liability_id: int) -> dict:
        return await self._request("GET", f"/liabilities/{liability_id}")

    async def update_liability(self, liability_id: int, payload: dict) -> dict:
        return await self._request("PUT", f"/liabilities/{liability_id}", json=payload)

    async def delete_liability(self, liability_id: int) -> None:
        return await self._request("DELETE", f"/liabilities/{liability_id}")

    async def link_liability_to_asset(
        self, liability_id: int, asset_id: int
    ) -> dict:
        return await self._request(
            "POST", f"/liabilities/{liability_id}/link-asset/{asset_id}"
        )

    async def get_amortisation(self, liability_id: int) -> list:
        return await self._request(
            "GET", f"/liabilities/{liability_id}/amortisation"
        )

    async def simulate_extra_payment(
        self, liability_id: int, extra_amount: float
    ) -> dict:
        return await self._request(
            "POST",
            f"/liabilities/{liability_id}/simulate-extra-payment",
            json={"extraAmount": extra_amount},
        )

    # ----- Balance sheet -----------------------------------------------------

    async def get_balance_sheet_summary(self) -> dict:
        return await self._request("GET", "/balance-sheet/summary")

    async def get_net_worth(self) -> dict:
        return await self._request("GET", "/balance-sheet/net-worth")

    async def get_asset_allocation(self) -> list:
        return await self._request("GET", "/balance-sheet/asset-allocation")

    async def get_debt_ratio(self) -> dict:
        return await self._request("GET", "/balance-sheet/debt-ratio")

    async def get_home_equity(self) -> dict:
        return await self._request("GET", "/balance-sheet/home-equity")

    async def get_balance_sheet_history(self) -> list:
        return await self._request("GET", "/balance-sheet/history")

    async def take_snapshot(self) -> dict:
        return await self._request("POST", "/balance-sheet/snapshot")


def get_portfolio_client() -> PortfolioApiClient:
    return PortfolioApiClient()
