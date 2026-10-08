from decimal import Decimal

import pytest

from wreakon6.normalization.money import parse_money


def test_parse_money_normalizes_to_two_decimal_places():
    assert parse_money("0.11") == Decimal("0.11")
    assert parse_money("10") == Decimal("10.00")
    assert parse_money("10.1") == Decimal("10.10")


def test_parse_money_rounds_half_up():
    assert parse_money("1.005") == Decimal("1.01")
    assert parse_money("1.004") == Decimal("1.00")


def test_parse_money_preserves_negative_amounts():
    assert parse_money("-0.02") == Decimal("-0.02")


def test_parse_money_rejects_missing_values():
    with pytest.raises(ValueError):
        parse_money(None)


def test_parse_money_rejects_non_numeric_values():
    with pytest.raises(ValueError):
        parse_money("not-a-number")
