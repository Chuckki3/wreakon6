from __future__ import annotations

from decimal import Decimal

from wreakon6.domain.transaction import CanonicalTransaction
from wreakon6.reconciliation.candidate import (
    CandidateDecision,
    MatchCandidate,
    MatchEvidence,
)
from wreakon6.reconciliation.population_classifier import (
    TransactionPopulation,
    classify_population,
)


def normalize(value):
    if value is None:
        return None

    value = str(value).strip().lower()
    return value or None


def populations_compatible(
    fintech: CanonicalTransaction,
    bank: CanonicalTransaction,
) -> bool:
    fintech_population = classify_population(fintech)
    bank_population = classify_population(bank)

    return (
        fintech_population != TransactionPopulation.UNKNOWN
        and bank_population != TransactionPopulation.UNKNOWN
        and fintech_population == bank_population
    )


def compatible_type(
    fintech: CanonicalTransaction,
    bank: CanonicalTransaction,
) -> bool:
    return (
        populations_compatible(fintech, bank)
        and fintech.transaction_type == bank.transaction_type
    )


def build_evidence(
    fintech: CanonicalTransaction,
    bank: CanonicalTransaction,
) -> MatchEvidence:
    fintech_reference = normalize(fintech.reference)
    bank_reference = normalize(bank.reference)

    fintech_transaction_id = normalize(fintech.transaction_id)
    bank_transaction_id = normalize(bank.transaction_id)

    fintech_counterparty = normalize(fintech.counterparty_reference)
    bank_counterparty = normalize(bank.counterparty_reference)

    amount_difference = (
        fintech.signed_amount()
        - bank.signed_amount()
    )

    return MatchEvidence(
        counterparty_reference=(
            fintech_counterparty is not None
            and bank_counterparty is not None
            and fintech_counterparty == bank_counterparty
        ),
        exact_reference=(
            fintech_reference is not None
            and bank_reference is not None
            and fintech_reference == bank_reference
        ),
        exact_transaction_id=(
            fintech_transaction_id is not None
            and bank_transaction_id is not None
            and fintech_transaction_id == bank_transaction_id
        ),
        same_currency=fintech.currency == bank.currency,
        same_date=fintech.event_at.date() == bank.event_at.date(),
        same_amount=(
            fintech.signed_amount() == bank.signed_amount()
        ),
        population_compatible=populations_compatible(fintech, bank),
        compatible_type=compatible_type(fintech, bank),
        amount_difference=amount_difference,
    )


def score_evidence(
    evidence: MatchEvidence,
) -> Decimal:
    score = Decimal("0")

    if evidence.exact_transaction_id:
        score += Decimal("100")

    if evidence.exact_reference:
        score += Decimal("90")

    if evidence.counterparty_reference:
        score += Decimal("40")

    if evidence.same_currency:
        score += Decimal("10")

    if evidence.same_date:
        score += Decimal("10")

    if evidence.same_amount:
        score += Decimal("20")

    if evidence.compatible_type:
        score += Decimal("5")

    return score


def decision_for_score(
    score: Decimal,
    evidence: MatchEvidence,
) -> CandidateDecision:
    """
    Automatic matching requires compatible populations and transaction types.

    Conflicting or unknown populations, and transaction-type conflicts,
    remain available for investigation rather than becoming MATCH results.
    """

    if not evidence.population_compatible:
        return CandidateDecision.REVIEW

    if (
        evidence.exact_transaction_id
        or evidence.exact_reference
    ) and not evidence.compatible_type:
        return CandidateDecision.REVIEW

    if evidence.exact_transaction_id:
        return CandidateDecision.MATCH

    if evidence.exact_reference:
        return CandidateDecision.MATCH

    if evidence.counterparty_reference:
        return CandidateDecision.REVIEW

    if score >= Decimal("50"):
        return CandidateDecision.REVIEW

    return CandidateDecision.REJECT


def explain(
    evidence: MatchEvidence,
    decision: CandidateDecision,
) -> str:
    reasons = []

    if not evidence.population_compatible:
        reasons.append(
            "incompatible transaction populations (including unknown); "
            "investigation required"
        )

    if (
        evidence.population_compatible
        and not evidence.compatible_type
        and (
            evidence.exact_transaction_id
            or evidence.exact_reference
        )
    ):
        reasons.append(
            "transaction type mismatch; manual review required"
        )

    if evidence.exact_transaction_id:
        reasons.append("exact transaction ID")

    if evidence.exact_reference:
        reasons.append("exact reference")

    if evidence.counterparty_reference:
        reasons.append("shared counterparty reference")

    if evidence.same_currency:
        reasons.append("same currency")

    if evidence.same_date:
        reasons.append("same date")

    if evidence.same_amount:
        reasons.append("same amount")

    if evidence.compatible_type:
        reasons.append("same transaction type within compatible population")

    if not reasons:
        reasons.append("no meaningful supporting evidence")

    return f"{decision.value}: " + ", ".join(reasons)


def build_candidate(
    fintech: CanonicalTransaction,
    bank: CanonicalTransaction,
) -> MatchCandidate:
    evidence = build_evidence(fintech, bank)
    score = score_evidence(evidence)
    decision = decision_for_score(score, evidence)

    return MatchCandidate(
        fintech=fintech,
        bank=bank,
        evidence=evidence,
        score=score,
        decision=decision,
        reason=explain(evidence, decision),
    )
