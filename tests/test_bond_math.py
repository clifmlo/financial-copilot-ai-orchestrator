"""Unit tests for the deterministic bond-math calculation engine.

Uses the sample scenario from the blueprint:
  Property value:      R2,500,000
  Bond balance:        R1,737,341.55
  Bond interest rate:  9.4%  (0.094)
  Remaining term:      210 months
  Current instalment:  R17,622/month
  Extra payment:       R5,000 or R7,000/month
  Emergency cash:      R120,000
  Savings rate:        6.6%  (0.066)
"""

from decimal import Decimal

import pytest

from app.calculators.bond_math import (
    amortisation_schedule,
    compare_bond_vs_savings,
    daily_interest,
    debt_to_asset_ratio,
    home_equity,
    interest_saved,
    monthly_interest,
    months_saved,
    net_worth,
    payoff_months,
    total_interest_paid,
)

BALANCE = Decimal("1737341.55")
RATE = Decimal("0.094")
PAYMENT = Decimal("17622")
PROPERTY_VALUE = Decimal("2500000")
SAVINGS_RATE = Decimal("0.066")
EMERGENCY_CASH = Decimal("120000")


class TestDailyInterest:
    def test_positive_balance(self):
        result = daily_interest(BALANCE, RATE)
        expected = (BALANCE * RATE / Decimal("365")).quantize(Decimal("0.01"))
        assert result == expected

    def test_zero_balance(self):
        assert daily_interest(Decimal("0"), RATE) == Decimal("0.00")


class TestMonthlyInterest:
    def test_positive_balance(self):
        result = monthly_interest(BALANCE, RATE)
        expected = (BALANCE * RATE / Decimal("12")).quantize(Decimal("0.01"))
        assert result == expected


class TestHomeEquity:
    def test_positive_equity(self):
        result = home_equity(PROPERTY_VALUE, BALANCE)
        assert result == (PROPERTY_VALUE - BALANCE).quantize(Decimal("0.01"))

    def test_underwater(self):
        result = home_equity(Decimal("1000000"), Decimal("1500000"))
        assert result == Decimal("-500000.00")


class TestNetWorth:
    def test_positive(self):
        assert net_worth(PROPERTY_VALUE, BALANCE) == home_equity(PROPERTY_VALUE, BALANCE)

    def test_negative(self):
        result = net_worth(Decimal("100000"), Decimal("500000"))
        assert result == Decimal("-400000.00")


class TestDebtToAssetRatio:
    def test_ratio(self):
        result = debt_to_asset_ratio(PROPERTY_VALUE, BALANCE)
        expected = (BALANCE / PROPERTY_VALUE * 100).quantize(Decimal("0.01"))
        assert result == expected

    def test_zero_assets(self):
        assert debt_to_asset_ratio(Decimal("0"), Decimal("100")) == Decimal("0")


class TestAmortisationSchedule:
    def test_schedule_length(self):
        schedule = amortisation_schedule(BALANCE, RATE, PAYMENT)
        assert len(schedule) > 0
        assert schedule[-1].closing_balance == Decimal("0.00") or schedule[-1].closing_balance >= 0

    def test_first_row(self):
        schedule = amortisation_schedule(BALANCE, RATE, PAYMENT)
        first = schedule[0]
        assert first.month == 1
        assert first.opening_balance == BALANCE.quantize(Decimal("0.01"))
        assert first.interest > 0
        assert first.principal > 0

    def test_extra_payment_reduces_length(self):
        base = amortisation_schedule(BALANCE, RATE, PAYMENT)
        extra = amortisation_schedule(BALANCE, RATE, PAYMENT, Decimal("5000"))
        assert len(extra) < len(base)


class TestPayoffMonths:
    def test_base_payoff(self):
        months = payoff_months(BALANCE, RATE, PAYMENT)
        assert months > 0
        assert months <= 600

    def test_extra_reduces_payoff(self):
        base = payoff_months(BALANCE, RATE, PAYMENT)
        with_extra = payoff_months(BALANCE, RATE, PAYMENT, Decimal("5000"))
        assert with_extra < base


class TestTotalInterestPaid:
    def test_positive(self):
        result = total_interest_paid(BALANCE, RATE, PAYMENT)
        assert result > 0

    def test_extra_payment_saves_interest(self):
        base = total_interest_paid(BALANCE, RATE, PAYMENT)
        with_extra = total_interest_paid(BALANCE, RATE, PAYMENT, Decimal("5000"))
        assert with_extra < base


class TestInterestSaved:
    def test_r5000_extra(self):
        saved = interest_saved(BALANCE, RATE, PAYMENT, Decimal("5000"))
        assert saved > 0

    def test_r7000_extra(self):
        saved = interest_saved(BALANCE, RATE, PAYMENT, Decimal("7000"))
        saved_5k = interest_saved(BALANCE, RATE, PAYMENT, Decimal("5000"))
        assert saved > saved_5k


class TestMonthsSaved:
    def test_r5000_extra(self):
        result = months_saved(BALANCE, RATE, PAYMENT, Decimal("5000"))
        assert result > 0

    def test_r7000_saves_more(self):
        m5 = months_saved(BALANCE, RATE, PAYMENT, Decimal("5000"))
        m7 = months_saved(BALANCE, RATE, PAYMENT, Decimal("7000"))
        assert m7 > m5


class TestBondVsSavings:
    def test_bond_wins(self):
        result = compare_bond_vs_savings(EMERGENCY_CASH, RATE, SAVINGS_RATE)
        assert result["net_benefit_bond"] > 0
        assert "bond" in result["recommendation_summary"].lower()

    def test_savings_wins(self):
        result = compare_bond_vs_savings(
            Decimal("100000"), Decimal("0.05"), Decimal("0.10")
        )
        assert result["net_benefit_bond"] < 0
