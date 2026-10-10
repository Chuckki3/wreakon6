from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

from wreakon6.domain.transaction import CanonicalTransaction


class CandidateDecision(str, Enum):
    MATCH = "MATCH"
    REVIEW = "REVIEW"
    REJECT = "REJECT"


@dataclass(frozen=True)
class MatchEvidence:
    counterparty_reference: bool
    exact_reference: bool
    exact_transaction_id: bool
    same_currency: bool
    same_date: bool
    same_amount: bool
    population_compatible: bool
    compatible_type: bool
    amount_difference: Decimal


@dataclass(frozen=True)
class MatchCandidate:
    fintech: CanonicalTransaction
    bank: CanonicalTransaction
    evidence: MatchEvidence
    score: Decimal
    decision: CandidateDecision
    reason: str
