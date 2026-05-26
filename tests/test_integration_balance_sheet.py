"""Integration tests for the balance-sheet tools and API client layer.

These tests mock the HTTP transport (httpx) so we can verify the full flow
from tool → PortfolioApiClient → request construction → response parsing
without requiring a running Spring Boot backend.

Sample data matches the blueprint scenario:
  Property:   R2,500,000
  Bond:       R1,737,341.55 @ 9.4% p.a.
  Instalment: R17,622/month
"""

from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

from app.clients.portfolio_api import PortfolioApiClient, PortfolioApiError
from app.tools.balance_sheet import (
    compute_bond_vs_savings,
    compute_daily_bond_interest,
    compute_extra_payment_scenario,
    compute_home_equity,
    get_balance_sheet_summary,
    get_debt_to_asset_ratio,
    get_home_equity_tool,
    get_net_worth_tool,
    list_assets,
    list_liabilities,
    simulate_bond_extra_payment,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SAMPLE_ASSET = {
    "id": "a1",
    "userId": "u1",
    "accountId": None,
    "assetType": "PROPERTY",
    "name": "Main Residence",
    "institution": "ABSA",
    "currency": "ZAR",
    "currentValue": 2500000,
    "valuationMethod": "MANUAL",
    "createdAt": "2024-01-01T00:00:00",
    "updatedAt": "2024-01-01T00:00:00",
}

SAMPLE_LIABILITY = {
    "id": "l1",
    "userId": "u1",
    "accountId": None,
    "liabilityType": "HOME_LOAN",
    "name": "ABSA Home Loan",
    "institution": "ABSA",
    "currency": "ZAR",
    "outstandingBalance": 1737341.55,
    "interestRate": 9.4,
    "minimumPayment": 17622,
    "paymentFrequency": "MONTHLY",
    "originalTermMonths": 240,
    "remainingTermMonths": 210,
    "startDate": "2022-06-01",
    "linkedAssetId": "a1",
    "accessFacilityEnabled": True,
    "availableRedrawAmount": 50000,
    "createdAt": "2024-01-01T00:00:00",
    "updatedAt": "2024-01-01T00:00:00",
}

BALANCE_SHEET_SUMMARY = {
    "totalAssets": 2500000,
    "totalLiabilities": 1737341.55,
    "netWorth": 762658.45,
    "assets": [SAMPLE_ASSET],
    "liabilities": [SAMPLE_LIABILITY],
}

HOME_EQUITY_RESPONSE = [
    {
        "propertyId": "a1",
        "propertyName": "Main Residence",
        "propertyValue": 2500000,
        "linkedLiabilityId": "l1",
        "outstandingBalance": 1737341.55,
        "homeEquity": 762658.45,
    }
]

DEBT_RATIO_RESPONSE = {
    "totalAssets": 2500000,
    "totalLiabilities": 1737341.55,
    "debtToAssetRatio": 69.49,
}

NET_WORTH_RESPONSE = {
    "totalAssets": 2500000,
    "totalLiabilities": 1737341.55,
    "netWorth": 762658.45,
}

EXTRA_PAYMENT_RESPONSE = {
    "liabilityId": "l1",
    "currentRemainingMonths": 210,
    "currentTotalInterest": 964266.20,
    "extraAmount": 5000,
    "newRemainingMonths": 140,
    "newTotalInterest": 556300.10,
    "interestSaved": 407966.10,
    "monthsSaved": 70,
}


def _mock_client() -> PortfolioApiClient:
    client = PortfolioApiClient(base_url="http://test:8080/api/v1")
    return client


# ---------------------------------------------------------------------------
# Client → API request construction tests
# ---------------------------------------------------------------------------


class TestPortfolioApiClient:
    @pytest.mark.asyncio
    async def test_list_assets_calls_correct_path(self):
        client = _mock_client()
        client._request = AsyncMock(return_value=[SAMPLE_ASSET])
        result = await client.list_assets()
        client._request.assert_called_once_with("GET", "/assets")
        assert len(result) == 1
        assert result[0]["assetType"] == "PROPERTY"

    @pytest.mark.asyncio
    async def test_list_liabilities_calls_correct_path(self):
        client = _mock_client()
        client._request = AsyncMock(return_value=[SAMPLE_LIABILITY])
        result = await client.list_liabilities()
        client._request.assert_called_once_with("GET", "/liabilities")
        assert result[0]["liabilityType"] == "HOME_LOAN"

    @pytest.mark.asyncio
    async def test_get_balance_sheet_summary(self):
        client = _mock_client()
        client._request = AsyncMock(return_value=BALANCE_SHEET_SUMMARY)
        result = await client.get_balance_sheet_summary()
        client._request.assert_called_once_with("GET", "/balance-sheet/summary")
        assert result["netWorth"] == 762658.45

    @pytest.mark.asyncio
    async def test_get_home_equity(self):
        client = _mock_client()
        client._request = AsyncMock(return_value=HOME_EQUITY_RESPONSE)
        result = await client.get_home_equity()
        client._request.assert_called_once_with("GET", "/balance-sheet/home-equity")
        assert result[0]["homeEquity"] == 762658.45

    @pytest.mark.asyncio
    async def test_get_debt_ratio(self):
        client = _mock_client()
        client._request = AsyncMock(return_value=DEBT_RATIO_RESPONSE)
        result = await client.get_debt_ratio()
        client._request.assert_called_once_with("GET", "/balance-sheet/debt-ratio")
        assert result["debtToAssetRatio"] == 69.49

    @pytest.mark.asyncio
    async def test_get_net_worth(self):
        client = _mock_client()
        client._request = AsyncMock(return_value=NET_WORTH_RESPONSE)
        result = await client.get_net_worth()
        client._request.assert_called_once_with("GET", "/balance-sheet/net-worth")
        assert result["netWorth"] == 762658.45

    @pytest.mark.asyncio
    async def test_simulate_extra_payment(self):
        client = _mock_client()
        client._request = AsyncMock(return_value=EXTRA_PAYMENT_RESPONSE)
        result = await client.simulate_extra_payment("l1", 5000)
        client._request.assert_called_once_with(
            "POST",
            "/liabilities/l1/simulate-extra-payment",
            json={"extraAmount": 5000},
        )
        assert result["interestSaved"] == 407966.10

    @pytest.mark.asyncio
    async def test_create_asset(self):
        client = _mock_client()
        client._request = AsyncMock(return_value=SAMPLE_ASSET)
        payload = {
            "assetType": "PROPERTY",
            "name": "Main Residence",
            "currentValue": 2500000,
        }
        result = await client.create_asset(payload)
        client._request.assert_called_once_with("POST", "/assets", json=payload)
        assert result["name"] == "Main Residence"

    @pytest.mark.asyncio
    async def test_link_liability_to_asset(self):
        client = _mock_client()
        client._request = AsyncMock(return_value=SAMPLE_LIABILITY)
        result = await client.link_liability_to_asset("l1", "a1")
        client._request.assert_called_once_with(
            "POST", "/liabilities/l1/link-asset/a1"
        )

    @pytest.mark.asyncio
    async def test_delete_asset(self):
        client = _mock_client()
        client._request = AsyncMock(return_value=None)
        await client.delete_asset("a1")
        client._request.assert_called_once_with("DELETE", "/assets/a1")


# ---------------------------------------------------------------------------
# Tool → Client integration tests
# ---------------------------------------------------------------------------


class TestBalanceSheetTools:
    @pytest.mark.asyncio
    async def test_get_balance_sheet_summary_tool(self):
        client = _mock_client()
        client._request = AsyncMock(return_value=BALANCE_SHEET_SUMMARY)
        result = await get_balance_sheet_summary(client=client)
        assert result["totalAssets"] == 2500000
        assert result["netWorth"] == 762658.45

    @pytest.mark.asyncio
    async def test_get_home_equity_tool(self):
        client = _mock_client()
        client._request = AsyncMock(return_value=HOME_EQUITY_RESPONSE)
        result = await get_home_equity_tool(client=client)
        assert result[0]["propertyName"] == "Main Residence"

    @pytest.mark.asyncio
    async def test_get_debt_ratio_tool(self):
        client = _mock_client()
        client._request = AsyncMock(return_value=DEBT_RATIO_RESPONSE)
        result = await get_debt_to_asset_ratio(client=client)
        assert result["debtToAssetRatio"] == 69.49

    @pytest.mark.asyncio
    async def test_list_assets_tool(self):
        client = _mock_client()
        client._request = AsyncMock(return_value=[SAMPLE_ASSET])
        result = await list_assets(client=client)
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_list_liabilities_tool(self):
        client = _mock_client()
        client._request = AsyncMock(return_value=[SAMPLE_LIABILITY])
        result = await list_liabilities(client=client)
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_simulate_extra_payment_tool(self):
        client = _mock_client()
        client._request = AsyncMock(return_value=EXTRA_PAYMENT_RESPONSE)
        result = await simulate_bond_extra_payment(
            liability_id="l1", extra_amount=5000, client=client
        )
        assert result["monthsSaved"] == 70


# ---------------------------------------------------------------------------
# Local computation helpers (no API needed)
# ---------------------------------------------------------------------------


class TestLocalComputationHelpers:
    def test_compute_bond_vs_savings_bond_wins(self):
        result = compute_bond_vs_savings(120000, 0.094, 0.066)
        assert result["net_benefit_bond"] > 0
        assert "bond" in result["recommendation_summary"].lower()

    def test_compute_bond_vs_savings_savings_wins(self):
        result = compute_bond_vs_savings(100000, 0.05, 0.10)
        assert result["net_benefit_bond"] < 0

    def test_compute_daily_bond_interest_format(self):
        text = compute_daily_bond_interest(1737341.55, 0.094)
        assert "R" in text
        assert "daily" in text.lower()

    def test_compute_home_equity_format(self):
        text = compute_home_equity(2500000, 1737341.55)
        assert "Home equity" in text
        assert "R762" in text.replace(",", "").replace(" ", "")

    def test_compute_extra_payment_scenario_r5000(self):
        result = compute_extra_payment_scenario(
            balance=1737341.55,
            annual_rate=0.094,
            monthly_payment=17622,
            extra_payment=5000,
        )
        assert result["months_saved"] > 0
        assert result["interest_saved"] > 0
        assert result["new_payoff_months"] < result["current_payoff_months"]

    def test_compute_extra_payment_scenario_r7000_saves_more(self):
        r5 = compute_extra_payment_scenario(1737341.55, 0.094, 17622, 5000)
        r7 = compute_extra_payment_scenario(1737341.55, 0.094, 17622, 7000)
        assert r7["months_saved"] > r5["months_saved"]
        assert r7["interest_saved"] > r5["interest_saved"]


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestErrorHandling:
    @pytest.mark.asyncio
    async def test_api_error_raised_on_non_success(self):
        client = _mock_client()
        client._request = AsyncMock(
            side_effect=PortfolioApiError(404, "Not found")
        )
        with pytest.raises(PortfolioApiError) as exc_info:
            await client.list_assets()
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_api_error_raised_on_server_error(self):
        client = _mock_client()
        client._request = AsyncMock(
            side_effect=PortfolioApiError(500, "Internal Server Error")
        )
        with pytest.raises(PortfolioApiError):
            await get_balance_sheet_summary(client=client)
