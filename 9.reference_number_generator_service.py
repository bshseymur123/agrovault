from datetime import datetime, timezone
from sqlalchemy.orm import Session
from models.models import Shipment, Transaction


def generate_shipment_ref(db: Session) -> str:
    year = datetime.now(timezone.utc).year
    count = db.query(Shipment).filter(
        Shipment.shipment_ref.like(f"SH-{year}-%")
    ).count()
    return f"SH-{year}-{count + 1:04d}"


def generate_transaction_ref(db: Session) -> str:
    year = datetime.now(timezone.utc).year
    count = db.query(Transaction).filter(
        Transaction.ref.like(f"TXN-{year}-%")
    ).count()
    return f"TXN-{year}-{count + 1:04d}"
