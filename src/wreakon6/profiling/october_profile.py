from __future__ import annotations

from collections import Counter
from datetime import date
from decimal import Decimal
from pathlib import Path

from wreakon6.ingestion.csv_reader import read_fintech_csv
from wreakon6.ingestion.xlsx_reader import read_bank_xlsx


PROJECT_ROOT = Path(__file__).resolve().parents[3]

FINTECH_FILE = PROJECT_ROOT / "data" / "input" / "fintech_report.csv"
BANK_FILE = PROJECT_ROOT / "data" / "input" / "bank_statement.xlsx"

TARGET_DATES = {
    date(2026, 10, 2),
    date(2026, 10, 3),
}


def profile_transactions(name, transactions):
    transactions = list(transactions)

    amounts = Counter(
        (tx.currency, tx.amount)
        for tx in transactions
    )

    references = Counter(
        tx.reference
        for tx in transactions
        if tx.reference
    )

    transaction_ids = Counter(
        tx.transaction_id
        for tx in transactions
        if tx.transaction_id
    )

    print()
    print("=" * 72)
    print(name)
    print("=" * 72)

    print(f"Transactions:        {len(transactions):,}")

    currencies = Counter(tx.currency for tx in transactions)
    print(f"Currencies:           {dict(currencies)}")

    directions = Counter(tx.direction.value for tx in transactions)
    print(f"Directions:           {dict(directions)}")

    statuses = Counter(tx.status.value for tx in transactions)
    print(f"Statuses:             {dict(statuses)}")

    transaction_types = Counter(
        tx.transaction_type.value
        for tx in transactions
    )
    print(f"Transaction types:    {dict(transaction_types)}")

    total_debits = sum(
        (tx.amount for tx in transactions
         if tx.direction.value == "DEBIT"),
        Decimal("0"),
    )

    total_credits = sum(
        (tx.amount for tx in transactions
         if tx.direction.value == "CREDIT"),
        Decimal("0"),
    )

    print(f"Debit amount:         {total_debits}")
    print(f"Credit amount:        {total_credits}")

    duplicate_references = {
        key: count
        for key, count in references.items()
        if count > 1
    }

    duplicate_transaction_ids = {
        key: count
        for key, count in transaction_ids.items()
        if count > 1
    }

    print(
        f"Duplicate references: "
        f"{len(duplicate_references):,}"
    )

    print(
        f"Duplicate tx IDs:     "
        f"{len(duplicate_transaction_ids):,}"
    )

    print(
        f"Unique amount pairs:  "
        f"{len(amounts):,}"
    )

    if transactions:
        timestamps = [tx.event_at for tx in transactions]

        print(f"First event:          {min(timestamps)}")
        print(f"Last event:           {max(timestamps)}")


def filter_target_dates(transactions):
    for transaction in transactions:
        if transaction.event_at.date() in TARGET_DATES:
            yield transaction


def main():
    print("WREAKON6 OCTOBER 2–3 PROFILING")
    print(f"Fintech file: {FINTECH_FILE}")
    print(f"Bank file:    {BANK_FILE}")

    fintech_transactions = filter_target_dates(
        read_fintech_csv(FINTECH_FILE)
    )

    bank_transactions = filter_target_dates(
        read_bank_xlsx(BANK_FILE)
    )

    profile_transactions(
        "FINTECH — OCTOBER 2–3",
        fintech_transactions,
    )

    profile_transactions(
        "BANK — OCTOBER 2–3",
        bank_transactions,
    )


if __name__ == "__main__":
    main()
