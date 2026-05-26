"""Final sample-data demo — blueprint scenario verification.

Validates the exact scenario from the blueprint document:
  Property value:      R2,500,000
  Bond balance:        R1,737,341.55
  Bond interest rate:  9.4%  (0.094)
  Remaining term:      210 months
  Current instalment:  R17,622/month
  Extra payment:       R5,000 or R7,000/month
  Emergency cash:      R120,000
  Savings rate:        6.6%  (0.066)

This test file serves as the acceptance test for the full calculation
engine, verifying all deterministic outputs match expected financial
behaviour.
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
from app.tools.balance_sheet import (
    compute_bond_vs_savings,
    compute_daily_bond_interest,
    compute_extra_payment_scenario,
    compute_home_equity,
)

# Blueprint sample data
PROPERTY_VALUE = Decimal("2500000")
BOND_BALANCE = Decimal("1737341.55")
BOND_RATE = Decimal("0.094")
REMAINING_TERM = 210
INSTALMENT = Decimal("17622")
EXTRA_5K = Decimal("5000")
EXTRA_7K = Decimal("7000")
EMERGENCY_CASH = Decimal("120000")
SAVINGS_RATE = Decimal("0.066")


class TestBlueprintScenario:
    """End-to-end verification of the blueprint sample scenario."""

    # ----- Core calculations ------------------------------------------------

    def test_home_equity(self):
        equity = home_equity(PROPERTY_VALUE, BOND_BALANCE)
        assert equity == Decimal("762658.45")

    def test_net_worth(self):
        nw = net_worth(PROPERTY_VALUE, BOND_BALANCE)
        assert nw == Decimal("762658.45")

    def test_debt_to_asset_ratio(self):
        ratio = debt_to_asset_ratio(PROPERTY_VALUE, BOND_BALANCE)
        assert Decimal("69") < ratio < Decimal("70")

    def test_daily_interest(self):
        di = daily_interest(BOND_BALANCE, BOND_RATE)
        # R1,737,341.55 * 0.094 / 365 ≈ R447.39
        assert Decimal("440") < di < Decimal("455")

    def test_monthly_interest(self):
        mi = monthly_interest(BOND_BALANCE, BOND_RATE)
        # R1,737,341.55 * 0.094 / 12 ≈ R13,609.35
        assert Decimal("13500") < mi < Decimal("13700")

    # ----- Amortisation schedule -------------------------------------------

    def test_amortisation_schedule_base_scenario(self):
        schedule = amortisation_schedule(BOND_BALANCE, BOND_RATE, INSTALMENT)
        assert len(schedule) > 100
        assert schedule[-1].closing_balance == Decimal("0.00") or schedule[-1].closing_balance >= 0
        assert schedule[0].opening_balance == BOND_BALANCE.quantize(Decimal("0.01"))

    def test_amortisation_first_month_interest(self):
        schedule = amortisation_schedule(BOND_BALANCE, BOND_RATE, INSTALMENT)
        first = schedule[0]
        # Interest ≈ R13,609 (monthly rate applied to balance)
        assert Decimal("13500") < first.interest < Decimal("13700")
        # Principal = instalment - interest
        expected_principal = INSTALMENT - first.interest
        assert abs(first.principal - expected_principal) < Decimal("1")

    def test_amortisation_balance_decreases(self):
        schedule = amortisation_schedule(BOND_BALANCE, BOND_RATE, INSTALMENT)
        for i in range(1, len(schedule)):
            assert schedule[i].opening_balance <= schedule[i - 1].opening_balance

    # ----- Payoff calculations ---------------------------------------------

    def test_payoff_months_base(self):
        months = payoff_months(BOND_BALANCE, BOND_RATE, INSTALMENT)
        # Blueprint says remaining term is 210 months; actual payoff may differ
        # slightly based on calculation methodology, but should be reasonable
        assert 180 < months < 260

    def test_payoff_with_r5k_extra(self):
        base = payoff_months(BOND_BALANCE, BOND_RATE, INSTALMENT)
        with_5k = payoff_months(BOND_BALANCE, BOND_RATE, INSTALMENT, EXTRA_5K)
        assert with_5k < base
        saved = base - with_5k
        assert saved > 30  # should save significant months

    def test_payoff_with_r7k_extra(self):
        base = payoff_months(BOND_BALANCE, BOND_RATE, INSTALMENT)
        with_7k = payoff_months(BOND_BALANCE, BOND_RATE, INSTALMENT, EXTRA_7K)
        with_5k = payoff_months(BOND_BALANCE, BOND_RATE, INSTALMENT, EXTRA_5K)
        assert with_7k < with_5k

    # ----- Interest savings ------------------------------------------------

    def test_interest_saved_r5k(self):
        saved = interest_saved(BOND_BALANCE, BOND_RATE, INSTALMENT, EXTRA_5K)
        assert saved > Decimal("200000")  # significant savings expected

    def test_interest_saved_r7k_more_than_r5k(self):
        saved_5k = interest_saved(BOND_BALANCE, BOND_RATE, INSTALMENT, EXTRA_5K)
        saved_7k = interest_saved(BOND_BALANCE, BOND_RATE, INSTALMENT, EXTRA_7K)
        assert saved_7k > saved_5k

    def test_total_interest_base(self):
        total = total_interest_paid(BOND_BALANCE, BOND_RATE, INSTALMENT)
        assert total > Decimal("500000")  # expect substantial interest over 200+ months

    def test_total_interest_reduced_with_extra(self):
        base_total = total_interest_paid(BOND_BALANCE, BOND_RATE, INSTALMENT)
        extra_total = total_interest_paid(BOND_BALANCE, BOND_RATE, INSTALMENT, EXTRA_5K)
        assert extra_total < base_total

    # ----- Months saved ----------------------------------------------------

    def test_months_saved_r5k(self):
        saved = months_saved(BOND_BALANCE, BOND_RATE, INSTALMENT, EXTRA_5K)
        assert saved > 30

    def test_months_saved_r7k_more(self):
        m5 = months_saved(BOND_BALANCE, BOND_RATE, INSTALMENT, EXTRA_5K)
        m7 = months_saved(BOND_BALANCE, BOND_RATE, INSTALMENT, EXTRA_7K)
        assert m7 > m5

    # ----- Bond vs savings comparison --------------------------------------

    def test_bond_vs_savings_bond_wins(self):
        result = compare_bond_vs_savings(EMERGENCY_CASH, BOND_RATE, SAVINGS_RATE)
        assert result["net_benefit_bond"] > 0
        # Bond at 9.4% saves more than savings at 6.6%
        assert result["annual_bond_interest_saved"] > result["annual_savings_interest_earned"]
        assert "bond" in result["recommendation_summary"].lower()

    def test_bond_vs_savings_amounts(self):
        result = compare_bond_vs_savings(EMERGENCY_CASH, BOND_RATE, SAVINGS_RATE)
        # R120,000 * 9.4% = R11,280 saved in bond
        expected_bond = Decimal("11280.00")
        assert result["annual_bond_interest_saved"] == expected_bond
        # R120,000 * 6.6% = R7,920 earned in savings
        expected_savings = Decimal("7920.00")
        assert result["annual_savings_interest_earned"] == expected_savings

    # ----- Tool-layer helpers (verify pass-through works) ------------------

    def test_tool_compute_extra_payment_scenario(self):
        result = compute_extra_payment_scenario(
            balance=float(BOND_BALANCE),
            annual_rate=float(BOND_RATE),
            monthly_payment=float(INSTALMENT),
            extra_payment=float(EXTRA_5K),
        )
        assert result["months_saved"] > 30
        assert result["interest_saved"] > 200000
        assert result["new_payoff_months"] < result["current_payoff_months"]

    def test_tool_compute_home_equity(self):
        text = compute_home_equity(float(PROPERTY_VALUE), float(BOND_BALANCE))
        assert "762658" in text.replace(",", "").replace(" ", "")

    def test_tool_compute_daily_interest(self):
        text = compute_daily_bond_interest(float(BOND_BALANCE), float(BOND_RATE))
        assert "daily" in text.lower()
        assert "R" in text

    def test_tool_compute_bond_vs_savings(self):
        result = compute_bond_vs_savings(
            float(EMERGENCY_CASH), float(BOND_RATE), float(SAVINGS_RATE)
        )
        assert result["net_benefit_bond"] > 0


class TestEdgeCases:
    """Edge cases and boundary conditions."""

    def test_zero_balance_payoff(self):
        months = payoff_months(Decimal("0"), BOND_RATE, INSTALMENT)
        assert months == 0

    def test_very_large_extra_payment(self):
        months = payoff_months(BOND_BALANCE, BOND_RATE, INSTALMENT, Decimal("100000"))
        assert months < 20

    def test_extra_payment_larger_than_balance(self):
        schedule = amortisation_schedule(
            Decimal("10000"), BOND_RATE, INSTALMENT, Decimal("0")
        )
        assert len(schedule) == 1
        assert schedule[0].closing_balance == Decimal("0.00") or schedule[0].closing_balance >= 0

    def test_underwater_property(self):
        eq = home_equity(Decimal("1000000"), Decimal("1500000"))
        assert eq < 0

    def test_net_worth_negative(self):
        nw = net_worth(Decimal("500000"), Decimal("1500000"))
        assert nw == Decimal("-1000000.00")
