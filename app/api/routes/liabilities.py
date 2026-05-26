"""Proxy routes for liability CRUD — forwards to the Spring Boot API."""

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from app.auth_context import set_auth_token
from app.balance_sheet.schemas import LiabilityCreate, LiabilityUpdate
from app.clients.portfolio_api import PortfolioApiError, get_portfolio_client

router = APIRouter(prefix="/api/v1/liabilities", tags=["liabilities"])


def _apply_auth(authorization: str | None) -> None:
    if authorization and authorization.startswith("Bearer "):
        set_auth_token(authorization[7:].strip())
    elif authorization:
        set_auth_token(authorization.strip())
    else:
        set_auth_token(None)


@router.post("")
async def create_liability(
    body: LiabilityCreate,
    authorization: str | None = Header(default=None),
):
    _apply_auth(authorization)
    try:
        return await get_portfolio_client().create_liability(
            body.model_dump(mode="json", exclude_none=True)
        )
    except PortfolioApiError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.get("")
async def list_liabilities(
    authorization: str | None = Header(default=None),
):
    _apply_auth(authorization)
    try:
        return await get_portfolio_client().list_liabilities()
    except PortfolioApiError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.get("/{liability_id}")
async def get_liability(
    liability_id: int,
    authorization: str | None = Header(default=None),
):
    _apply_auth(authorization)
    try:
        return await get_portfolio_client().get_liability(liability_id)
    except PortfolioApiError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.put("/{liability_id}")
async def update_liability(
    liability_id: int,
    body: LiabilityUpdate,
    authorization: str | None = Header(default=None),
):
    _apply_auth(authorization)
    try:
        return await get_portfolio_client().update_liability(
            liability_id, body.model_dump(mode="json", exclude_none=True)
        )
    except PortfolioApiError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.delete("/{liability_id}")
async def delete_liability(
    liability_id: int,
    authorization: str | None = Header(default=None),
):
    _apply_auth(authorization)
    try:
        await get_portfolio_client().delete_liability(liability_id)
        return {"status": "deleted", "liability_id": liability_id}
    except PortfolioApiError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.post("/{liability_id}/link-asset/{asset_id}")
async def link_to_asset(
    liability_id: int,
    asset_id: int,
    authorization: str | None = Header(default=None),
):
    _apply_auth(authorization)
    try:
        return await get_portfolio_client().link_liability_to_asset(
            liability_id, asset_id
        )
    except PortfolioApiError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.get("/{liability_id}/amortisation")
async def amortisation(
    liability_id: int,
    authorization: str | None = Header(default=None),
):
    _apply_auth(authorization)
    try:
        return await get_portfolio_client().get_amortisation(liability_id)
    except PortfolioApiError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


class SimulateExtraPaymentRequest(BaseModel):
    extra_amount: float = Field(..., gt=0)


@router.post("/{liability_id}/simulate-extra-payment")
async def simulate_extra_payment(
    liability_id: int,
    body: SimulateExtraPaymentRequest,
    authorization: str | None = Header(default=None),
):
    _apply_auth(authorization)
    try:
        return await get_portfolio_client().simulate_extra_payment(
            liability_id, body.extra_amount
        )
    except PortfolioApiError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
