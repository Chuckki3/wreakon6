from datetime import datetime
from decimal import Decimal

from wreakon6.domain.transaction import (
    CanonicalTransaction,
    TransactionDirection,
    TransactionStatus,
    TransactionType,
)
from wreakon6.reconciliation.candidate import CandidateDecision
from wreakon6.reconciliation.candidate_engine import generate_candidates


def make_transaction(
    *,
    source,
    source_record_id,
    transaction_id=None,
    reference=None,
    counterparty_reference=None,
    amount=Decimal("0.50"),
    currency="USD",
    transaction_type=TransactionType.PAYMENT,
    direction=TransactionDirection.DEBIT,
    event_at=None,
):
    return CanonicalTransaction(
        source=source,
        source_record_id=source_record_id,
        transaction_id=transaction_id,
        reference=reference,
        account_id="account-1",
        event_at=event_at or datetime(2026, 10, 3, 12, 0),
        value_at=None,
        amount=amount,
        currency=currency,
        direction=direction,
        transaction_type=transaction_type,
        status=TransactionStatus.POSTED,
        is_hold=False,
        is_reversal=False,
        counterparty_reference=counterparty_reference,
        narration="test transaction",
    )


def make_fintech(**overrides):
    values = {
        "source": "FINTECH",
        "source_record_id": "fintech-1",
        "transaction_id": "ftx-1",
        "reference": None,
        "counterparty_reference": None,
        "transaction_type": TransactionType.PAYMENT,
    }
    values.update(overrides)
    return make_transaction(**values)


def make_bank(**overrides):
    values = {
        "source": "BANK",
        "source_record_id": "bank-1",
        "transaction_id": "bank-1",
        "reference": None,
        "counterparty_reference": None,
        "transaction_type": TransactionType.PAYMENT,
    }
    values.update(overrides)
    return make_transaction(**values)


def test_normalized_transaction_id_generates_candidate():
    fintech = make_fintech(transaction_id="  TX-123 ")
    bank = make_bank(transaction_id="tx-123")

    candidates = generate_candidates([fintech], [bank])

    assert len(candidates) == 1
    assert candidates[0].fintech is fintech
    assert candidates[0].bank is bank
    assert candidates[0].evidence.exact_transaction_id is True
    assert candidates[0].decision == CandidateDecision.MATCH


def test_normalized_reference_generates_candidate():
    fintech = make_fintech(
        transaction_id=None,
        reference="  REF-123 ",
    )
    bank = make_bank(
        transaction_id=None,
        reference="ref-123",
    )

    candidates = generate_candidates([fintech], [bank])

    assert len(candidates) == 1
    assert candidates[0].evidence.exact_reference is True
    assert candidates[0].decision == CandidateDecision.MATCH


def test_shared_counterparty_reference_generates_review_candidate():
    fintech = make_fintech(
        transaction_id="fee-1",
        counterparty_reference="  CARD-UUID ",
        transaction_type=TransactionType.FEE,
    )
    bank = make_bank(
        transaction_id="card-creation-1",
        counterparty_reference="card-uuid",
        transaction_type=TransactionType.CARD_CREATION,
    )

    candidates = generate_candidates([fintech], [bank])

    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.evidence.counterparty_reference is True
    assert candidate.evidence.population_compatible is False
    assert candidate.decision == CandidateDecision.REVIEW
    assert "incompatible transaction populations" in candidate.reason


def test_multiple_fee_records_can_share_one_card_reference_without_auto_matching():
    fintech_transactions = [
        make_fintech(
            source_record_id="fee-1",
            transaction_id="fee-tx-1",
            counterparty_reference="card-uuid",
            transaction_type=TransactionType.FEE,
        ),
        make_fintech(
            source_record_id="fee-2",
            transaction_id="fee-tx-2",
            counterparty_reference="card-uuid",
            transaction_type=TransactionType.FEE,
        ),
    ]
    bank_transactions = [
        make_bank(
            source_record_id="bank-card-1",
            transaction_id="card-creation-1",
            counterparty_reference="card-uuid",
            transaction_type=TransactionType.CARD_CREATION,
        ),
    ]

    candidates = generate_candidates(
        fintech_transactions,
        bank_transactions,
    )

    assert len(candidates) == 2
    assert {
        (candidate.fintech.source_record_id, candidate.bank.source_record_id)
        for candidate in candidates
    } == {
        ("fee-1", "bank-card-1"),
        ("fee-2", "bank-card-1"),
    }
    assert all(
        candidate.decision == CandidateDecision.REVIEW
        for candidate in candidates
    )


def test_same_pair_found_by_multiple_identifiers_is_deduplicated():
    fintech = make_fintech(
        transaction_id="shared-tx",
        reference="shared-ref",
        counterparty_reference="shared-card",
    )
    bank = make_bank(
        transaction_id="shared-tx",
        reference="shared-ref",
        counterparty_reference="shared-card",
    )

    candidates = generate_candidates([fintech], [bank])

    assert len(candidates) == 1
    assert candidates[0].evidence.exact_transaction_id is True
    assert candidates[0].evidence.exact_reference is True
    assert candidates[0].evidence.counterparty_reference is True


def test_incompatible_types_with_shared_transaction_id_are_reviewed():
    fintech = make_fintech(
        transaction_id="shared-tx",
        transaction_type=TransactionType.PAYMENT,
    )
    bank = make_bank(
        transaction_id="shared-tx",
        transaction_type=TransactionType.REFUND,
    )

    candidates = generate_candidates([fintech], [bank])

    assert len(candidates) == 1
    assert candidates[0].evidence.exact_transaction_id is True
    assert candidates[0].evidence.population_compatible is True
    assert candidates[0].evidence.compatible_type is False
    assert candidates[0].decision == CandidateDecision.REVIEW


def test_amount_and_date_match_without_shared_identifier_generate_no_candidate():
    fintech = make_fintech(
        transaction_id=None,
        reference=None,
        counterparty_reference=None,
        amount=Decimal("25.00"),
        event_at=datetime(2026, 10, 3, 10, 0),
    )
    bank = make_bank(
        transaction_id=None,
        reference=None,
        counterparty_reference=None,
        amount=Decimal("25.00"),
        event_at=datetime(2026, 10, 3, 15, 0),
    )

    candidates = generate_candidates([fintech], [bank])

    assert candidates == []


def test_blank_identifiers_do_not_generate_candidates():
    fintech = make_fintech(
        transaction_id="  ",
        reference="",
        counterparty_reference=None,
    )
    bank = make_bank(
        transaction_id="",
        reference="   ",
        counterparty_reference=None,
    )

    candidates = generate_candidates([fintech], [bank])

    assert candidates == []


def test_same_amount_and_date_do_not_override_population_conflict():
    fintech = make_fintech(
        transaction_id=None,
        reference=None,
        counterparty_reference="card-uuid",
        amount=Decimal("0.50"),
        transaction_type=TransactionType.FEE,
    )
    bank = make_bank(
        transaction_id=None,
        reference=None,
        counterparty_reference="card-uuid",
        amount=Decimal("0.50"),
        transaction_type=TransactionType.CARD_CREATION,
    )

    candidates = generate_candidates([fintech], [bank])

    assert len(candidates) == 1
    assert candidates[0].evidence.same_amount is True
    assert candidates[0].evidence.same_date is True
    assert candidates[0].decision == CandidateDecision.REVIEW
