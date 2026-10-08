from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


MONEY_SCALE = Decimal("0.01")


def parse_money(value) -> Decimal:
    """
    Parse a source monetary value into a canonical two-decimal Decimal.

    Financial amounts are normalized at ingestion so that downstream
    reconciliation never depends on floating-point representation.

    ROUND_HALF_UP is used for conventional financial cent rounding.
    """

    if value is None:
        raise ValueError("Missing transaction amount")

    try:
        amount = Decimal(str(value).strip())
    except (InvalidOperation, AttributeError, ValueError) as exc:
        raise ValueError(
            f"Invalid transaction amount: {value!r}"
        ) from exc

    if not amount.is_finite():
        raise ValueError(
            f"Transaction amount must be finite, got {value!r}"
        )

    return amount.quantize(
        MONEY_SCALE,
        rounding=ROUND_HALF_UP,
    )
