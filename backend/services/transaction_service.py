"""
Transaction overdue detection.
Runs on every transactions list/fetch — flips 'pending' → 'overdue'
when due_date has passed. Lightweight, no background worker needed.
"""
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from models.models import Transaction, TransactionStatus


def flag_overdue_transactions(db: Session) -> int:
    """
    Check all pending transactions with an expired due_date
    and mark them overdue. Returns count of updated records.
    """
    now = datetime.now(timezone.utc)
    updated = (
        db.query(Transaction)
        .filter(
            Transaction.status == TransactionStatus.pending,
            Transaction.due_date != None,
            Transaction.due_date < now,
        )
        .all()
    )
    for txn in updated:
        txn.status = TransactionStatus.overdue

    if updated:
        db.commit()

    return len(updated)
