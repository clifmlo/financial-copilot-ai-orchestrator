"""Deterministic bond / mortgage calculations.

These are local helpers used for formatting and explaining results returned
by the Spring Boot API.  They may also be used as a fallback when the API
does not yet expose a particular calculation, but the canonical source of
truth remains the backend.

All functions are pure — no IO, no LLM calls.
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

TWO_DP = Decimal("0.01")


def _q(value: Decimal) -> Decimal:
    return value.quantize(TWO_DP, rounding=ROUND_HALF_UP)


def daily_interest(balance: Decimal, annual_rate: Decimal) -> Decimal:
    """Daily interest = balance * annual_rate / 365."""
    return _q(balance * annual_rate / Decimal("365"))


def monthly_interest(balance: Decimal, annual_rate: Decimal) -> Decimal:
    """Approximate monthly interest = balance * annual_rate / 12."""
    return _q(balance * annual_rate / Decimal("12"))


def home_equity(property_value: Decimal, outstanding_balance: Decimal) -> Decimal:
    return _q(property_value - outstanding_balance)


def debt_to_asset_ratio(
    total_assets: Decimal, total_liabilities: Decimal
) -> Decimal:
    if total_assets == 0:
        return Decimal("0")
    return _q(total_liabilities / total_assets * Decimal("100"))


def net_worth(total_assets: Decimal, total_liabilities: Decimal) -> Decimal:
    return _q(total_assets - total_liabilities)


# ---------------------------------------------------------------------------
# Amortisation
# ---------------------------------------------------------------------------

@dataclass
class AmortisationRow:
    month: int
    opening_balance: Decimal
    payment: Decimal
    interest: Decimal
    principal: Decimal
    closing_balance: Decimal


def amortisation_schedule(
    balance: Decimal,
    annual_rate: Decimal,
    monthly_payment: Decimal,
    extra_payment: Decimal = Decimal("0"),
    max_months: int = 600,
) -> list[AmortisationRow]:
    """Generate a month-by-month amortisation schedule.

    Returns when the balance reaches zero or ``max_months`` is hit.
    """
    monthly_rate = annual_rate / Decimal("12")
    schedule: list[AmortisationRow] = []
    remaining = balance

    for month in range(1, max_months + 1):
        if remaining <= 0:
            break
        interest = _q(remaining * monthly_rate)
        total_payment = monthly_payment + extra_payment
        principal = total_payment - interest
        if principal > remaining:
            principal = remaining
            total_payment = principal + interest
        closing = _q(remaining - principal)
        schedule.append(
            AmortisationRow(
                month=month,
                opening_balance=_q(remaining),
                payment=_q(total_payment),
                interest=interest,
                principal=_q(principal),
                closing_balance=max(closing, Decimal("0")),
            )
        )
        remaining = max(closing, Decimal("0"))
    return schedule


def payoff_months(
    balance: Decimal,
    annual_rate: Decimal,
    monthly_payment: Decimal,
    extra_payment: Decimal = Decimal("0"),
) -> int:
    """Number of months to pay off the loan."""
    schedule = amortisation_schedule(balance, annual_rate, monthly_payment, extra_payment)
    return len(schedule)


def total_interest_paid(
    balance: Decimal,
    annual_rate: Decimal,
    monthly_payment: Decimal,
    extra_payment: Decimal = Decimal("0"),
) -> Decimal:
    """Sum of all interest over the life of the loan."""
    schedule = amortisation_schedule(balance, annual_rate, monthly_payment, extra_payment)
    return _q(sum(row.interest for row in schedule))


def interest_saved(
    balance: Decimal,
    annual_rate: Decimal,
    monthly_payment: Decimal,
    extra_payment: Decimal,
) -> Decimal:
    """Interest saved by making extra payments vs the base payment."""
    base = total_interest_paid(balance, annual_rate, monthly_payment)
    with_extra = total_interest_paid(balance, annual_rate, monthly_payment, extra_payment)
    return _q(base - with_extra)


def months_saved(
    balance: Decimal,
    annual_rate: Decimal,
    monthly_payment: Decimal,
    extra_payment: Decimal,
) -> int:
    base = payoff_months(balance, annual_rate, monthly_payment)
    with_extra = payoff_months(balance, annual_rate, monthly_payment, extra_payment)
    return base - with_extra


def compare_bond_vs_savings(
    amount: Decimal,
    bond_annual_rate: Decimal,
    savings_annual_rate: Decimal,
) -> dict:
    """Compare depositing cash into an access bond vs a savings account.

    Access bond: the deposit reduces the outstanding balance, saving daily
    interest at the bond rate (effectively a tax-free return).
    Savings account: earns interest at the savings rate (taxable).
    """
    bond_saved = _q(amount * bond_annual_rate)
    savings_earned = _q(amount * savings_annual_rate)
    net = _q(bond_saved - savings_earned)
    if net > 0:
        summary = (
            f"Depositing R{amount:,.2f} into the access bond saves "
            f"R{bond_saved:,.2f}/year in interest (tax-free), compared to "
            f"R{savings_earned:,.2f}/year earned in a savings account (taxable). "
            f"Net annual benefit of the bond: R{net:,.2f}."
        )
    else:
        summary = (
            f"The savings account yields R{savings_earned:,.2f}/year vs "
            f"R{bond_saved:,.2f}/year saved in the bond. "
            f"In this scenario the savings account earns more, but bond "
            f"interest savings are tax-free."
        )
    return {
        "amount": amount,
        "bond_interest_rate": bond_annual_rate,
        "savings_interest_rate": savings_annual_rate,
        "annual_bond_interest_saved": bond_saved,
        "annual_savings_interest_earned": savings_earned,
        "net_benefit_bond": net,
        "recommendation_summary": summary,
    }
