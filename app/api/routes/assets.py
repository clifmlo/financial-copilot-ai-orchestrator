"""Proxy routes for asset CRUD — forwards to the Spring Boot API."""

from fastapi import APIRouter, Header, HTTPException

from app.auth_context import set_auth_token
from app.balance_sheet.schemas import AssetCreate, AssetUpdate
from app.clients.portfolio_api import PortfolioApiError, get_portfolio_client

router = APIRouter(prefix="/api/v1/assets", tags=["assets"])


def _apply_auth(authorization: str | None) -> None:
    if authorization and authorization.startswith("Bearer "):
        set_auth_token(authorization[7:].strip())
    elif authorization:
        set_auth_token(authorization.strip())
    else:
        set_auth_token(None)


@router.post("")
async def create_asset(
    body: AssetCreate,
    authorization: str | None = Header(default=None),
):
    _apply_auth(authorization)
    try:
        return await get_portfolio_client().create_asset(
            body.model_dump(mode="json", exclude_none=True)
        )
    except PortfolioApiError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.get("")
async def list_assets(
    authorization: str | None = Header(default=None),
):
    _apply_auth(authorization)
    try:
        return await get_portfolio_client().list_assets()
    except PortfolioApiError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.get("/{asset_id}")
async def get_asset(
    asset_id: int,
    authorization: str | None = Header(default=None),
):
    _apply_auth(authorization)
    try:
        return await get_portfolio_client().get_asset(asset_id)
    except PortfolioApiError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.put("/{asset_id}")
async def update_asset(
    asset_id: int,
    body: AssetUpdate,
    authorization: str | None = Header(default=None),
):
    _apply_auth(authorization)
    try:
        return await get_portfolio_client().update_asset(
            asset_id, body.model_dump(mode="json", exclude_none=True)
        )
    except PortfolioApiError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.delete("/{asset_id}")
async def delete_asset(
    asset_id: int,
    authorization: str | None = Header(default=None),
):
    _apply_auth(authorization)
    try:
        await get_portfolio_client().delete_asset(asset_id)
        return {"status": "deleted", "asset_id": asset_id}
    except PortfolioApiError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.get("/{asset_id}/valuation-history")
async def valuation_history(
    asset_id: int,
    authorization: str | None = Header(default=None),
):
    _apply_auth(authorization)
    try:
        return await get_portfolio_client().get_valuation_history(asset_id)
    except PortfolioApiError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
