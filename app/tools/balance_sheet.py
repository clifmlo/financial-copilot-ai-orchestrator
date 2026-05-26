"""LangGraph tools for balance-sheet intelligence.

These tools call the Spring Boot API (system of record) and return
deterministic results for the LLM to explain.  The LLM must never
invent balances, interest savings, or payoff dates.
"""

from decimal import Decimal

from app.calculators.bond_math import (
    compare_bond_vs_savings,
    daily_interest,
    home_equity,
    interest_saved,
    monthly_interest,
    months_saved,
    payoff_months,
    total_interest_paid,
)
from app.clients.portfolio_api import PortfolioApiClient, get_portfolio_client


async def get_balance_sheet_summary(
    client: PortfolioApiClient | None = None,
) -> dict:
    """Fetch total assets, total liabilities, net worth, and item lists."""
    return await (client or get_portfolio_client()).get_balance_sheet_summary()


async def get_home_equity_tool(
    client: PortfolioApiClient | None = None,
) -> dict:
    """Fetch home equity: property value minus outstanding bond balance."""
    return await (client or get_portfolio_client()).get_home_equity()


async def get_debt_to_asset_ratio(
    client: PortfolioApiClient | None = None,
) -> dict:
    """Fetch debt-to-asset ratio from the API."""
    return await (client or get_portfolio_client()).get_debt_ratio()


async def get_net_worth_tool(
    client: PortfolioApiClient | None = None,
) -> dict:
    """Fetch net worth = total assets - total liabilities."""
    return await (client or get_portfolio_client()).get_net_worth()


async def get_asset_allocation_tool(
    client: PortfolioApiClient | None = None,
) -> list:
    """Fetch asset allocation breakdown by asset type."""
    return await (client or get_portfolio_client()).get_asset_allocation()


async def simulate_bond_extra_payment(
    liability_id: int,
    extra_amount: float,
    client: PortfolioApiClient | None = None,
) -> dict:
    """Simulate extra bond repayment and return months / interest saved."""
    return await (client or get_portfolio_client()).simulate_extra_payment(
        liability_id, extra_amount
    )


async def get_amortisation_schedule(
    liability_id: int,
    client: PortfolioApiClient | None = None,
) -> list:
    """Fetch full amortisation schedule for a liability."""
    return await (client or get_portfolio_client()).get_amortisation(liability_id)


async def list_assets(client: PortfolioApiClient | None = None) -> list:
    """List all assets for the authenticated user."""
    return await (client or get_portfolio_client()).list_assets()


async def list_liabilities(client: PortfolioApiClient | None = None) -> list:
    """List all liabilities for the authenticated user."""
    return await (client or get_portfolio_client()).list_liabilities()


# ---------------------------------------------------------------------------
# Local calculation helpers (used when the API response provides raw fields
# but no pre-computed result, or for quick scenario comparisons).
# ---------------------------------------------------------------------------

def compute_bond_vs_savings(
    amount: float,
    bond_rate: float,
    savings_rate: float,
) -> dict:
    """Compare depositing cash into an access bond vs a savings account."""
    return compare_bond_vs_savings(
        Decimal(str(amount)),
        Decimal(str(bond_rate)),
        Decimal(str(savings_rate)),
    )


def compute_daily_bond_interest(balance: float, annual_rate: float) -> str:
    """Return a human-readable daily interest string."""
    d = daily_interest(Decimal(str(balance)), Decimal(str(annual_rate)))
    m = monthly_interest(Decimal(str(balance)), Decimal(str(annual_rate)))
    return (
        f"At a balance of R{balance:,.2f} and {annual_rate*100:.1f}% p.a., "
        f"daily interest is approximately R{d:,.2f} "
        f"(~R{m:,.2f}/month)."
    )


def compute_home_equity(property_value: float, bond_balance: float) -> str:
    """Return a human-readable home equity string."""
    equity = home_equity(Decimal(str(property_value)), Decimal(str(bond_balance)))
    return (
        f"Property value: R{property_value:,.2f}\n"
        f"Outstanding bond: R{bond_balance:,.2f}\n"
        f"Home equity: R{equity:,.2f}"
    )


def compute_extra_payment_scenario(
    balance: float,
    annual_rate: float,
    monthly_payment: float,
    extra_payment: float,
) -> dict:
    """Run a local extra-payment simulation and return a summary dict."""
    b = Decimal(str(balance))
    r = Decimal(str(annual_rate))
    p = Decimal(str(monthly_payment))
    e = Decimal(str(extra_payment))

    base_months = payoff_months(b, r, p)
    new_months = payoff_months(b, r, p, e)
    saved_interest = interest_saved(b, r, p, e)
    saved_months = months_saved(b, r, p, e)
    base_interest = total_interest_paid(b, r, p)
    new_interest = total_interest_paid(b, r, p, e)

    return {
        "balance": balance,
        "annual_rate": annual_rate,
        "monthly_payment": monthly_payment,
        "extra_payment": extra_payment,
        "current_payoff_months": base_months,
        "new_payoff_months": new_months,
        "months_saved": saved_months,
        "current_total_interest": float(base_interest),
        "new_total_interest": float(new_interest),
        "interest_saved": float(saved_interest),
    }
