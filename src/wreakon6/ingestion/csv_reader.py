from __future__ import annotations

import csv
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterator

from wreakon6.domain.transaction import (
    CanonicalTransaction,
    TransactionDirection,
    TransactionStatus,
    TransactionType,
)


REQUIRED_COLUMNS = {
    "Amount",
    "ID",
    "UserId",
    "CardId",
    "TransactionId",
    "Type",
    "Status",
    "Currency",
    "Memo",
    "Metadata",
    "CreatedAt",
    "UpdatedAt",
    "ServiceReference",
}


def _parse_datetime(value: str) -> datetime:
    if not value or not value.strip():
        raise ValueError("Missing transaction timestamp")

    try:
        return datetime.strptime(
            value.strip(),
            "%B %d, %Y, %I:%M %p",
        )
    except ValueError as exc:
        raise ValueError(
            f"Invalid transaction timestamp: {value!r}"
        ) from exc


def _parse_amount(value: str) -> Decimal:
    try:
        return Decimal(value.strip())
    except (InvalidOperation, AttributeError) as exc:
        raise ValueError(
            f"Invalid transaction amount: {value!r}"
        ) from exc


def _transaction_type(value: str, memo: str = "") -> TransactionType:
    value = (value or "").strip().upper()
    memo = (memo or "").strip().upper()

    # The fintech source uses several names for charges/fees.
    fee_types = {
        "CROSS_BORDER",
        "CROSS_BORDER_SPREAD",
        "DECLINE_DOM",
        "DECLINE_INTL",
        "AUTHORIZATION_FEE",
        "MAINTENANCE_FEE",
    }

    if value in fee_types:
        return TransactionType.FEE

    if "FEE" in value or "CHARGE" in value:
        return TransactionType.FEE

    if "FEE" in memo or "CHARGE" in memo:
        return TransactionType.FEE

    if "REFUND" in value:
        return TransactionType.REFUND

    if "AUTHORIZATION" in value:
        return TransactionType.AUTHORIZATION

    if "HOLD_RELEASE" in value:
        return TransactionType.HOLD_RELEASE

    if "HOLD" in value:
        return TransactionType.HOLD

    if not value:
        return TransactionType.OTHER

    return TransactionType.PAYMENT


def _status(value: str) -> TransactionStatus:
    value = (value or "").strip().upper()

    mapping = {
        "SUCCESS": TransactionStatus.POSTED,
        "POSTED": TransactionStatus.POSTED,
        "PENDING": TransactionStatus.PENDING,
        "REVERSED": TransactionStatus.REVERSED,
        "FAILED": TransactionStatus.FAILED,
    }

    return mapping.get(value, TransactionStatus.UNKNOWN)


def _is_incomplete_row(row: dict[str, str | None]) -> bool:
    """
    Detect a source row that does not contain enough information to
    represent a financial transaction.

    The supplied fintech report contains one truncated final row.
    It contains identifiers and an amount but no transaction type,
    status, currency, or timestamps.
    """

    required_values = (
        "Type",
        "Status",
        "Currency",
        "CreatedAt",
        "UpdatedAt",
    )

    return any(
        not (row.get(column) or "").strip()
        for column in required_values
    )


def read_fintech_csv(path: str | Path) -> Iterator[CanonicalTransaction]:
    """
    Stream the fintech CSV.

    The file is intentionally not loaded into memory all at once.

    Incomplete source rows are ignored rather than converted into
    fabricated financial transactions.
    """

    path = Path(path)

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)

        columns = set(reader.fieldnames or [])
        missing = REQUIRED_COLUMNS - columns

        if missing:
            raise ValueError(
                "Fintech CSV is missing required columns: "
                f"{sorted(missing)}"
            )

        for line_number, row in enumerate(reader, start=2):
            if _is_incomplete_row(row):
                continue

            try:
                transaction_type = _transaction_type(
                    row.get("Type", ""),
                    row.get("Memo", ""),
                )

                yield CanonicalTransaction(
                    source="FINTECH",
                    source_record_id=(row.get("ID") or "").strip(),
                    transaction_id=(row.get("TransactionId") or "").strip()
                    or None,
                    reference=(row.get("ServiceReference") or "").strip()
                    or None,
                    account_id=(row.get("UserId") or "").strip()
                    or None,
                    event_at=_parse_datetime(row.get("CreatedAt", "")),
                    value_at=_parse_datetime(row.get("UpdatedAt", "")),
                    amount=_parse_amount(row.get("Amount", "")),
                    currency=(row.get("Currency") or "").strip().upper(),
                    direction=TransactionDirection.DEBIT,
                    transaction_type=transaction_type,
                    status=_status(row.get("Status", "")),
                    is_hold=transaction_type
                    in {
                        TransactionType.HOLD,
                        TransactionType.HOLD_RELEASE,
                    },
                    is_reversal=_status(row.get("Status", ""))
                    == TransactionStatus.REVERSED,
                    counterparty_reference=(
                        row.get("CardId") or ""
                    ).strip()
                    or None,
                    narration=(row.get("Memo") or "").strip() or None,
                )

            except Exception as exc:
                raise ValueError(
                    "Invalid fintech record at CSV line "
                    f"{line_number}: {exc}"
                ) from exc
