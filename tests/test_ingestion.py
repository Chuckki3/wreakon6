from decimal import Decimal
from pathlib import Path

from wreakon6.domain.transaction import (
    TransactionDirection,
    TransactionStatus,
    TransactionType,
)
from wreakon6.ingestion.csv_reader import read_fintech_csv
from wreakon6.ingestion.xlsx_reader import read_bank_xlsx


PROJECT_ROOT = Path(__file__).resolve().parents[1]

FINTECH_FILE = PROJECT_ROOT / "data" / "input" / "fintech_report.csv"
BANK_FILE = PROJECT_ROOT / "data" / "input" / "bank_statement.xlsx"


def test_fintech_reader_reads_first_transaction():
    transaction = next(read_fintech_csv(FINTECH_FILE))

    assert transaction.source == "FINTECH"
    assert transaction.source_record_id
    assert transaction.transaction_id
    assert transaction.account_id

    assert transaction.currency == "USD"
    assert transaction.amount == Decimal("0.11")

    assert transaction.direction == TransactionDirection.DEBIT
    assert transaction.status == TransactionStatus.POSTED

    assert transaction.transaction_type == TransactionType.FEE
    assert transaction.is_hold is False


def test_bank_reader_reads_first_transaction():
    transaction = next(read_bank_xlsx(BANK_FILE))

    assert transaction.source == "BANK"
    assert transaction.source_record_id == "47315370"
    assert transaction.transaction_id == "S22028652"

    assert transaction.amount == Decimal("30")
    assert transaction.currency == "USD"

    assert transaction.direction == TransactionDirection.DEBIT
    assert transaction.status == TransactionStatus.POSTED

    assert transaction.transaction_type == TransactionType.AUTHORIZATION
    assert transaction.is_hold is False


def test_fintech_reader_streams_all_records():
    count = sum(1 for _ in read_fintech_csv(FINTECH_FILE))

    assert count == 385548


def test_bank_reader_reads_all_records():
    count = sum(1 for _ in read_bank_xlsx(BANK_FILE))

    assert count == 1000

def test_bank_reversal_flag_parsing():
    import pytest

    from wreakon6.ingestion.xlsx_reader import _parse_is_reversed

    cases = [
        (True, True),
        (False, False),
        (1, True),
        (0, False),
        ("true", True),
        ("TRUE", True),
        ("yes", True),
        ("1", True),
        ("false", False),
        ("False", False),
        ("FALSE", False),
        ("no", False),
        ("0", False),
    ]

    for raw_value, expected in cases:
        assert _parse_is_reversed(raw_value) is expected


def test_bank_reversal_flag_rejects_ambiguous_values():
    import pytest

    from wreakon6.ingestion.xlsx_reader import _parse_is_reversed

    for raw_value in (None, "", "unknown", "maybe", 2, -1):
        with pytest.raises(ValueError, match="Invalid reversal flag"):
            _parse_is_reversed(raw_value)
