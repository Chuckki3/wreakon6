from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional


class TransactionDirection(str, Enum):
    DEBIT = "DEBIT"
    CREDIT = "CREDIT"
    UNKNOWN = "UNKNOWN"


class TransactionStatus(str, Enum):
    POSTED = "POSTED"
    PENDING = "PENDING"
    REVERSED = "REVERSED"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"


class TransactionType(str, Enum):
    PAYMENT = "PAYMENT"
    REFUND = "REFUND"
    FEE = "FEE"
    HOLD = "HOLD"
    HOLD_RELEASE = "HOLD_RELEASE"
    CARD_CREATION = "CARD_CREATION"
    AUTHORIZATION = "AUTHORIZATION"
    OTHER = "OTHER"


@dataclass(frozen=True)
class CanonicalTransaction:
    """
    Source-independent representation of a financial transaction.

    The reconciliation engine should work only with this model,
    never with raw CSV/XLSX-specific records.
    """

    source: str
    source_record_id: str

    transaction_id: Optional[str]
    reference: Optional[str]

    account_id: Optional[str]

    event_at: datetime
    value_at: Optional[datetime]

    amount: Decimal
    currency: str
    direction: TransactionDirection

    transaction_type: TransactionType
    status: TransactionStatus

    is_hold: bool
    is_reversal: bool

    counterparty_reference: Optional[str]

    narration: Optional[str]

    def signed_amount(self) -> Decimal:
        """
        Return the transaction amount using accounting direction.

        DEBIT  -> negative
        CREDIT -> positive
        UNKNOWN -> positive, because the source did not establish direction.
        """
        if self.direction == TransactionDirection.DEBIT:
            return -abs(self.amount)

        if self.direction == TransactionDirection.CREDIT:
            return abs(self.amount)

        return self.amount