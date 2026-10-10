from enum import Enum

from wreakon6.domain.transaction import (
    CanonicalTransaction,
    TransactionStatus,
    TransactionType,
)


class TransactionPopulation(str, Enum):
    CARD_ACTIVITY = "CARD_ACTIVITY"
    FEE = "FEE"
    HOLD = "HOLD"
    REVERSAL = "REVERSAL"
    UNKNOWN = "UNKNOWN"


def classify_population(
    transaction: CanonicalTransaction,
) -> TransactionPopulation:
    """
    Classify a canonical transaction into a reconciliation population.

    This classification does not alter the original transaction or
    determine whether two transactions should be matched.
    """

    if (
        transaction.is_reversal
        or transaction.status == TransactionStatus.REVERSED
    ):
        return TransactionPopulation.REVERSAL

    if (
        transaction.is_hold
        or transaction.transaction_type
        in {
            TransactionType.HOLD,
            TransactionType.HOLD_RELEASE,
        }
    ):
        return TransactionPopulation.HOLD

    if transaction.transaction_type == TransactionType.FEE:
        return TransactionPopulation.FEE

    if transaction.transaction_type in {
        TransactionType.PAYMENT,
        TransactionType.REFUND,
        TransactionType.AUTHORIZATION,
        TransactionType.CARD_CREATION,
    }:
        return TransactionPopulation.CARD_ACTIVITY

    return TransactionPopulation.UNKNOWN
