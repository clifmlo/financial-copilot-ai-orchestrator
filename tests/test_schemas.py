"""Unit tests for balance-sheet Pydantic schemas."""

from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.balance_sheet.schemas import (
    Asset,
    AssetCreate,
    AssetType,
    BalanceSheetSummary,
    HomeEquity,
    Liability,
    LiabilityCreate,
    LiabilityType,
    PaymentFrequency,
    ValuationMethod,
)


class TestAssetCreate:
    def test_valid_property(self):
        a = AssetCreate(
            asset_type=AssetType.PROPERTY,
            name="Main residence",
            institution="ABSA",
            current_value=Decimal("2500000"),
        )
        assert a.asset_type == AssetType.PROPERTY
        assert a.current_value == Decimal("2500000")
        assert a.currency == "ZAR"
        assert a.valuation_method == ValuationMethod.MANUAL

    def test_rejects_negative_value(self):
        with pytest.raises(ValidationError):
            AssetCreate(
                asset_type=AssetType.CASH,
                name="Savings",
                current_value=Decimal("-100"),
            )

    def test_all_asset_types(self):
        for t in AssetType:
            a = AssetCreate(asset_type=t, name=f"Test {t}", current_value=Decimal("1"))
            assert a.asset_type == t


class TestLiabilityCreate:
    def test_valid_home_loan(self):
        l = LiabilityCreate(
            liability_type=LiabilityType.HOME_LOAN,
            name="ABSA Home Loan",
            institution="ABSA",
            outstanding_balance=Decimal("1737341.55"),
            interest_rate=Decimal("9.4"),
            minimum_payment=Decimal("17622"),
            remaining_term_months=210,
            access_facility_enabled=True,
            available_redraw_amount=Decimal("50000"),
        )
        assert l.liability_type == LiabilityType.HOME_LOAN
        assert l.access_facility_enabled is True

    def test_rejects_invalid_rate(self):
        with pytest.raises(ValidationError):
            LiabilityCreate(
                liability_type=LiabilityType.HOME_LOAN,
                name="Bad loan",
                outstanding_balance=Decimal("100000"),
                interest_rate=Decimal("150"),
            )

    def test_all_liability_types(self):
        for t in LiabilityType:
            l = LiabilityCreate(
                liability_type=t,
                name=f"Test {t}",
                outstanding_balance=Decimal("1000"),
                interest_rate=Decimal("5"),
            )
            assert l.liability_type == t


class TestAssetModel:
    def test_from_api_response(self):
        a = Asset(
            id=1,
            user_id=42,
            asset_type=AssetType.PROPERTY,
            name="My House",
            current_value=Decimal("2500000"),
        )
        assert a.id == 1
        assert a.user_id == 42


class TestLiabilityModel:
    def test_from_api_response(self):
        l = Liability(
            id=10,
            user_id=42,
            liability_type=LiabilityType.HOME_LOAN,
            name="Home Loan",
            outstanding_balance=Decimal("1737341.55"),
            interest_rate=Decimal("9.4"),
        )
        assert l.id == 10
        assert l.outstanding_balance == Decimal("1737341.55")


class TestBalanceSheetSummary:
    def test_net_worth(self):
        s = BalanceSheetSummary(
            total_assets=Decimal("3000000"),
            total_liabilities=Decimal("1737341.55"),
            net_worth=Decimal("1262658.45"),
        )
        assert s.net_worth == s.total_assets - s.total_liabilities


class TestHomeEquity:
    def test_equity_calculation(self):
        e = HomeEquity(
            property_id=1,
            property_name="Main residence",
            property_value=Decimal("2500000"),
            linked_liability_id=10,
            outstanding_balance=Decimal("1737341.55"),
            home_equity=Decimal("762658.45"),
        )
        assert e.home_equity == e.property_value - e.outstanding_balance
