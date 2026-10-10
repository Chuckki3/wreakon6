from __future__ import annotations

from collections import defaultdict

from wreakon6.domain.transaction import CanonicalTransaction
from wreakon6.reconciliation.candidate import MatchCandidate
from wreakon6.reconciliation.scorer import build_candidate


def normalize(value):
    if value is None:
        return None

    value = str(value).strip().lower()

    return value or None


def build_index(
    transactions: list[CanonicalTransaction],
    field_name: str,
):
    index = defaultdict(list)

    for transaction in transactions:
        value = normalize(
            getattr(
                transaction,
                field_name,
            )
        )

        if value:
            index[value].append(transaction)

    return index


def generate_candidates(
    fintech_transactions: list[CanonicalTransaction],
    bank_transactions: list[CanonicalTransaction],
) -> list[MatchCandidate]:
    bank_by_transaction_id = build_index(
        bank_transactions,
        "transaction_id",
    )

    bank_by_reference = build_index(
        bank_transactions,
        "reference",
    )

    bank_by_counterparty = build_index(
        bank_transactions,
        "counterparty_reference",
    )

    candidates = {}

    for fintech in fintech_transactions:
        blocks = []

        transaction_id = normalize(
            fintech.transaction_id
        )

        reference = normalize(
            fintech.reference
        )

        counterparty = normalize(
            fintech.counterparty_reference
        )

        if transaction_id:
            blocks.extend(
                bank_by_transaction_id.get(
                    transaction_id,
                    [],
                )
            )

        if reference:
            blocks.extend(
                bank_by_reference.get(
                    reference,
                    [],
                )
            )

        if counterparty:
            blocks.extend(
                bank_by_counterparty.get(
                    counterparty,
                    [],
                )
            )

        for bank in blocks:
            key = (
                fintech.source_record_id,
                bank.source_record_id,
            )

            if key in candidates:
                continue

            candidates[key] = build_candidate(
                fintech,
                bank,
            )

    return list(candidates.values())
