from datetime import datetime
from decimal import Decimal

import pytest

from wreakon6.domain.transaction import (
    CanonicalTransaction,
    TransactionDirection,
    TransactionStatus,
    TransactionType,
)
from wreakon6.reconciliation.candidate import CandidateDecision
from wreakon6.reconciliation.scorer import build_candidate


def make_transaction(
    *,
    source,
    source_record_id,
    transaction_id,
    reference=None,
    counterparty_reference="shared-1",
    amount=Decimal("-0.50"),
    transaction_type,
):
    return CanonicalTransaction(
        source=source,
        source_record_id=source_record_id,
        transaction_id=transaction_id,
        reference=reference,
        account_id="account-1",
        event_at=datetime(2026, 10, 3, 12, 0),
        value_at=None,
        amount=amount,
        currency="USD",
        direction=TransactionDirection.DEBIT,
        transaction_type=transaction_type,
        status=TransactionStatus.POSTED,
        is_hold=False,
        is_reversal=False,
        counterparty_reference=counterparty_reference,
        narration="test transaction",
    )


def make_fintech(
    *,
    transaction_id="ftx-1",
    reference=None,
    counterparty_reference="shared-1",
    amount=Decimal("-0.50"),
    transaction_type=TransactionType.FEE,
):
    return make_transaction(
        source="FINTECH",
        source_record_id="fintech-record",
        transaction_id=transaction_id,
        reference=reference,
        counterparty_reference=counterparty_reference,
        amount=amount,
        transaction_type=transaction_type,
    )


def make_bank(
    *,
    transaction_id="bank-1",
    reference=None,
    counterparty_reference="shared-1",
    amount=Decimal("-0.50"),
    transaction_type=TransactionType.CARD_CREATION,
):
    return make_transaction(
        source="BANK",
        source_record_id="bank-record",
        transaction_id=transaction_id,
        reference=reference,
        counterparty_reference=counterparty_reference,
        amount=amount,
        transaction_type=transaction_type,
    )


def test_counterparty_reference_is_not_transaction_identity():
    candidate = build_candidate(
        make_fintech(),
        make_bank(),
    )

    assert candidate.evidence.counterparty_reference is True
    assert candidate.evidence.same_amount is True
    assert candidate.evidence.same_date is True
    assert candidate.evidence.population_compatible is False
    assert candidate.decision == CandidateDecision.REVIEW
    assert "incompatible transaction populations" in candidate.reason


def test_exact_transaction_id_matches_with_compatible_populations():
    candidate = build_candidate(
        make_fintech(
            transaction_id="same-id",
            transaction_type=TransactionType.PAYMENT,
        ),
        make_bank(
            transaction_id="same-id",
            transaction_type=TransactionType.PAYMENT,
        ),
    )

    assert candidate.evidence.exact_transaction_id is True
    assert candidate.evidence.population_compatible is True
    assert candidate.decision == CandidateDecision.MATCH


def test_exact_reference_matches_with_compatible_populations():
    candidate = build_candidate(
        make_fintech(
            reference="same-reference",
            transaction_type=TransactionType.PAYMENT,
        ),
        make_bank(
            reference="same-reference",
            transaction_type=TransactionType.PAYMENT,
        ),
    )

    assert candidate.evidence.exact_reference is True
    assert candidate.evidence.population_compatible is True
    assert candidate.decision == CandidateDecision.MATCH


def test_counterparty_reference_with_amount_variance_is_review():
    candidate = build_candidate(
        make_fintech(amount=Decimal("-0.40")),
        make_bank(amount=Decimal("-0.50")),
    )

    assert candidate.evidence.counterparty_reference is True
    assert candidate.evidence.same_amount is False
    assert candidate.evidence.population_compatible is False
    assert candidate.decision == CandidateDecision.REVIEW


def test_exact_transaction_id_cannot_override_population_conflict():
    candidate = build_candidate(
        make_fintech(transaction_id="shared-id"),
        make_bank(transaction_id="shared-id"),
    )

    assert candidate.evidence.exact_transaction_id is True
    assert candidate.evidence.population_compatible is False
    assert candidate.decision == CandidateDecision.REVIEW
    assert "incompatible transaction populations" in candidate.reason


def test_exact_reference_cannot_override_population_conflict():
    candidate = build_candidate(
        make_fintech(reference="shared-reference"),
        make_bank(reference="shared-reference"),
    )

    assert candidate.evidence.exact_reference is True
    assert candidate.evidence.population_compatible is False
    assert candidate.decision == CandidateDecision.REVIEW


@pytest.mark.parametrize(
    ("fintech_type", "bank_type"),
    [
        (TransactionType.FEE, TransactionType.CARD_CREATION),
        (TransactionType.FEE, TransactionType.AUTHORIZATION),
        (TransactionType.FEE, TransactionType.REFUND),
        (TransactionType.PAYMENT, TransactionType.HOLD),
        (TransactionType.PAYMENT, TransactionType.HOLD_RELEASE),
        (TransactionType.PAYMENT, TransactionType.FEE),
    ],
)
def test_incompatible_populations_never_auto_match(
    fintech_type,
    bank_type,
):
    candidate = build_candidate(
        make_fintech(
            transaction_id="shared-id",
            reference="shared-reference",
            transaction_type=fintech_type,
        ),
        make_bank(
            transaction_id="shared-id",
            reference="shared-reference",
            transaction_type=bank_type,
        ),
    )

    assert candidate.evidence.population_compatible is False
    assert candidate.decision == CandidateDecision.REVIEW


def test_matching_fee_populations_can_match_on_exact_transaction_id():
    candidate = build_candidate(
        make_fintech(
            transaction_id="same-id",
            transaction_type=TransactionType.FEE,
        ),
        make_bank(
            transaction_id="same-id",
            transaction_type=TransactionType.FEE,
        ),
    )

    assert candidate.evidence.population_compatible is True
    assert candidate.evidence.compatible_type is True
    assert candidate.decision == CandidateDecision.MATCH


def test_unknown_populations_are_not_compatible_for_matching():
    candidate = build_candidate(
        make_fintech(
            transaction_id="shared-id",
            transaction_type=TransactionType.OTHER,
        ),
        make_bank(
            transaction_id="shared-id",
            transaction_type=TransactionType.OTHER,
        ),
    )

    assert candidate.evidence.population_compatible is False
    assert candidate.decision == CandidateDecision.REVIEW


def test_exact_id_does_not_override_transaction_type_mismatch():
    candidate = build_candidate(
        make_fintech(
            transaction_id="shared-id",
            transaction_type=TransactionType.PAYMENT,
        ),
        make_bank(
            transaction_id="shared-id",
            transaction_type=TransactionType.REFUND,
        ),
    )

    assert candidate.evidence.population_compatible is True
    assert candidate.evidence.compatible_type is False
    assert candidate.decision == CandidateDecision.REVIEW
    assert "transaction type mismatch" in candidate.reason


def test_exact_reference_does_not_override_transaction_type_mismatch():
    candidate = build_candidate(
        make_fintech(
            reference="shared-reference",
            transaction_type=TransactionType.PAYMENT,
        ),
        make_bank(
            reference="shared-reference",
            transaction_type=TransactionType.REFUND,
        ),
    )

    assert candidate.evidence.population_compatible is True
    assert candidate.evidence.compatible_type is False
    assert candidate.decision == CandidateDecision.REVIEW
    assert "transaction type mismatch" in candidate.reason
