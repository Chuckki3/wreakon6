from datetime import datetime
from decimal import Decimal

import pytest

from wreakon6.domain.transaction import (
    CanonicalTransaction,
    TransactionDirection,
    TransactionStatus,
    TransactionType,
)
from wreakon6.reconciliation.population_classifier import (
    TransactionPopulation,
    classify_population,
)


def make_transaction(
    *,
    transaction_type=TransactionType.OTHER,
    status=TransactionStatus.POSTED,
    is_hold=False,
    is_reversal=False,
):
    return CanonicalTransaction(
        source="TEST",
        source_record_id="record-1",
        transaction_id="transaction-1",
        reference=None,
        account_id="account-1",
        event_at=datetime(2026, 10, 3, 12, 0),
        value_at=None,
        amount=Decimal("10.00"),
        currency="USD",
        direction=TransactionDirection.DEBIT,
        transaction_type=transaction_type,
        status=status,
        is_hold=is_hold,
        is_reversal=is_reversal,
        counterparty_reference=None,
        narration="test transaction",
    )


@pytest.mark.parametrize(
    "transaction_type",
    [
        TransactionType.PAYMENT,
        TransactionType.REFUND,
        TransactionType.AUTHORIZATION,
        TransactionType.CARD_CREATION,
    ],
)
def test_card_activity_types_are_classified_correctly(transaction_type):
    transaction = make_transaction(transaction_type=transaction_type)

    assert classify_population(transaction) == TransactionPopulation.CARD_ACTIVITY


def test_fee_is_classified_as_fee():
    transaction = make_transaction(transaction_type=TransactionType.FEE)

    assert classify_population(transaction) == TransactionPopulation.FEE


@pytest.mark.parametrize(
    "transaction_type",
    [
        TransactionType.HOLD,
        TransactionType.HOLD_RELEASE,
    ],
)
def test_hold_types_are_classified_as_hold(transaction_type):
    transaction = make_transaction(transaction_type=transaction_type)

    assert classify_population(transaction) == TransactionPopulation.HOLD


def test_hold_flag_classifies_transaction_as_hold():
    transaction = make_transaction(
        transaction_type=TransactionType.PAYMENT,
        is_hold=True,
    )

    assert classify_population(transaction) == TransactionPopulation.HOLD


def test_reversal_flag_takes_priority_over_fee_type():
    transaction = make_transaction(
        transaction_type=TransactionType.FEE,
        is_reversal=True,
    )

    assert classify_population(transaction) == TransactionPopulation.REVERSAL


def test_reversed_status_takes_priority_over_card_activity():
    transaction = make_transaction(
        transaction_type=TransactionType.PAYMENT,
        status=TransactionStatus.REVERSED,
    )

    assert classify_population(transaction) == TransactionPopulation.REVERSAL


def test_reversal_takes_priority_over_hold_flag():
    transaction = make_transaction(
        transaction_type=TransactionType.HOLD,
        is_hold=True,
        is_reversal=True,
    )

    assert classify_population(transaction) == TransactionPopulation.REVERSAL


def test_other_type_is_classified_as_unknown():
    transaction = make_transaction(transaction_type=TransactionType.OTHER)

    assert classify_population(transaction) == TransactionPopulation.UNKNOWN


def test_unknown_population_does_not_change_original_transaction():
    transaction = make_transaction(transaction_type=TransactionType.OTHER)

    classify_population(transaction)

    assert transaction.transaction_type == TransactionType.OTHER
    assert transaction.status == TransactionStatus.POSTED
    assert transaction.amount == Decimal("10.00")
    assert transaction.direction == TransactionDirection.DEBIT
