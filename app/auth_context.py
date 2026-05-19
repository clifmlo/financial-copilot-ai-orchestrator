"""Request-scoped portfolio API auth token (forwarded from web client)."""

from contextvars import ContextVar

_auth_token: ContextVar[str | None] = ContextVar("portfolio_auth_token", default=None)


def set_auth_token(token: str | None) -> None:
    _auth_token.set(token)


def get_auth_token() -> str | None:
    return _auth_token.get()


def clear_auth_token() -> None:
    _auth_token.set(None)
