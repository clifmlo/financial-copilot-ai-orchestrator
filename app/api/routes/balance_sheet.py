"""Proxy / orchestrator routes for balance-sheet intelligence.

These endpoints either forward to the Spring Boot API or run local
deterministic calculations (bond math) that the frontend or AI can consume.
"""

from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel, Field

from app.auth_context import set_auth_token
from app.clients.portfolio_api import PortfolioApiError, get_portfolio_client
from app.tools.balance_sheet import (
    compute_bond_vs_savings,
    compute_daily_bond_interest,
    compute_extra_payment_scenario,
    compute_home_equity,
)

router = APIRouter(prefix="/api/v1/balance-sheet", tags=["balance-sheet"])


def _apply_auth(authorization: str | None) -> None:
    if authorization and authorization.startswith("Bearer "):
        set_auth_token(authorization[7:].strip())
    elif authorization:
        set_auth_token(authorization.strip())
    else:
        set_auth_token(None)


# ---- Forwarded from Spring Boot API ----------------------------------------


@router.get("/summary")
async def balance_sheet_summary(
    authorization: str | None = Header(default=None),
):
    _apply_auth(authorization)
    try:
        return await get_portfolio_client().get_balance_sheet_summary()
    except PortfolioApiError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.get("/net-worth")
async def net_worth(
    authorization: str | None = Header(default=None),
):
    _apply_auth(authorization)
    try:
        return await get_portfolio_client().get_net_worth()
    except PortfolioApiError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.get("/asset-allocation")
async def asset_allocation(
    authorization: str | None = Header(default=None),
):
    _apply_auth(authorization)
    try:
        return await get_portfolio_client().get_asset_allocation()
    except PortfolioApiError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.get("/debt-ratio")
async def debt_ratio(
    authorization: str | None = Header(default=None),
):
    _apply_auth(authorization)
    try:
        return await get_portfolio_client().get_debt_ratio()
    except PortfolioApiError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.get("/home-equity")
async def home_equity_endpoint(
    authorization: str | None = Header(default=None),
):
    _apply_auth(authorization)
    try:
        return await get_portfolio_client().get_home_equity()
    except PortfolioApiError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


# ---- Local calculators (deterministic, no API call) -------------------------


class ExtraPaymentRequest(BaseModel):
    balance: float = Field(..., gt=0)
    annual_rate: float = Field(..., gt=0, le=1)
    monthly_payment: float = Field(..., gt=0)
    extra_payment: float = Field(..., gt=0)


@router.post("/simulate-extra-payment")
async def simulate_extra_payment(request: ExtraPaymentRequest):
    """Run a local extra-payment simulation (no API dependency)."""
    return compute_extra_payment_scenario(
        balance=request.balance,
        annual_rate=request.annual_rate,
        monthly_payment=request.monthly_payment,
        extra_payment=request.extra_payment,
    )


class BondVsSavingsRequest(BaseModel):
    amount: float = Field(..., gt=0)
    bond_rate: float = Field(..., gt=0, le=1)
    savings_rate: float = Field(..., gt=0, le=1)


@router.post("/compare-bond-vs-savings")
async def compare_bond_vs_savings(request: BondVsSavingsRequest):
    """Compare access bond deposit vs savings account yield."""
    return compute_bond_vs_savings(
        amount=request.amount,
        bond_rate=request.bond_rate,
        savings_rate=request.savings_rate,
    )


@router.get("/daily-interest")
async def daily_interest_endpoint(
    balance: float = Query(..., gt=0),
    annual_rate: float = Query(..., gt=0, le=1),
):
    """Calculate daily and monthly interest on a bond balance."""
    return {"explanation": compute_daily_bond_interest(balance, annual_rate)}


@router.get("/equity")
async def equity_endpoint(
    property_value: float = Query(..., gt=0),
    bond_balance: float = Query(..., ge=0),
):
    """Calculate home equity from property value and bond balance."""
    return {"explanation": compute_home_equity(property_value, bond_balance)}
