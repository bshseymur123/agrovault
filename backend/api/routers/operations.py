from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from typing import List, Optional
from datetime import datetime, timezone, date

from db.session import get_db
from models.models import (
    QCRecord, CustomsRecord, Transaction, Shipment,
    CustomsStatus, TransactionStatus
)
from schemas.schemas import (
    QCCreate, QCOut, CustomsCreate, CustomsOut, CustomsStatusUpdate,
    TransactionCreate, TransactionOut, TransactionStatusUpdate,
    DashboardKPI, ReportPeriod, TradeCorridorStat
)
from core.security import get_current_user_id
from services.ref_generator import generate_transaction_ref
from services.transaction_service import flag_overdue_transactions

# ─── QC Router ───────────────────────────────────────────────────────────────

qc_router = APIRouter(prefix="/api/shipments", tags=["qc"])


@qc_router.post("/{shipment_id}/qc", response_model=QCOut, status_code=201)
def create_qc(
    shipment_id: int,
    body: QCCreate,
    db: Session = Depends(get_db),
    _: int = Depends(get_current_user_id),
):
    if not db.query(Shipment).filter(Shipment.id == shipment_id).first():
        raise HTTPException(404, "Shipment not found")
    record = QCRecord(**body.model_dump(), shipment_id=shipment_id)
    db.add(record)
    db.commit()
    db.refresh(record)
    return QCOut.model_validate(record)


@qc_router.get("/{shipment_id}/qc", response_model=List[QCOut])
def list_qc(
    shipment_id: int,
    db: Session = Depends(get_db),
    _: int = Depends(get_current_user_id),
):
    records = db.query(QCRecord).filter(QCRecord.shipment_id == shipment_id).all()
    return [QCOut.model_validate(r) for r in records]


# ─── Customs Router ──────────────────────────────────────────────────────────

customs_router = APIRouter(prefix="/api/customs", tags=["customs"])


@customs_router.get("", response_model=List[CustomsOut])
def list_customs(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    _: int = Depends(get_current_user_id),
):
    q = db.query(CustomsRecord)
    if status:
        q = q.filter(CustomsRecord.status == status)
    q = q.order_by(CustomsRecord.created_at.desc())
    return [CustomsOut.model_validate(r) for r in q.limit(100).all()]


@customs_router.post("/shipment/{shipment_id}", response_model=CustomsOut, status_code=201)
def create_customs(
    shipment_id: int,
    body: CustomsCreate,
    db: Session = Depends(get_db),
    _: int = Depends(get_current_user_id),
):
    if not db.query(Shipment).filter(Shipment.id == shipment_id).first():
        raise HTTPException(404, "Shipment not found")
    record = CustomsRecord(**body.model_dump(), shipment_id=shipment_id)
    db.add(record)
    db.commit()
    db.refresh(record)
    return CustomsOut.model_validate(record)


@customs_router.patch("/{customs_id}/status", response_model=CustomsOut)
def update_customs_status(
    customs_id: int,
    body: CustomsStatusUpdate,
    db: Session = Depends(get_db),
    _: int = Depends(get_current_user_id),
):
    record = db.query(CustomsRecord).filter(CustomsRecord.id == customs_id).first()
    if not record:
        raise HTTPException(404, "Customs record not found")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(record, k, v)
    if body.status == CustomsStatus.submitted:
        record.submitted_at = datetime.now(timezone.utc)
    if body.status == CustomsStatus.cleared:
        record.cleared_at = datetime.now(timezone.utc)
    record.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(record)
    return CustomsOut.model_validate(record)


# ─── Transactions Router ──────────────────────────────────────────────────────

txn_router = APIRouter(prefix="/api/transactions", tags=["transactions"])


@txn_router.get("", response_model=List[TransactionOut])
def list_transactions(
    shipment_id: Optional[int] = None,
    txn_type: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(100, le=500),
    offset: int = 0,
    db: Session = Depends(get_db),
    _: int = Depends(get_current_user_id),
):
    # Auto-flag any pending transactions whose due_date has passed
    flag_overdue_transactions(db)

    q = db.query(Transaction)
    if shipment_id:
        q = q.filter(Transaction.shipment_id == shipment_id)
    if txn_type:
        q = q.filter(Transaction.transaction_type == txn_type)
    if status:
        q = q.filter(Transaction.status == status)
    q = q.order_by(Transaction.created_at.desc())
    return [TransactionOut.model_validate(t) for t in q.offset(offset).limit(limit).all()]


@txn_router.post("", response_model=TransactionOut, status_code=201)
def create_transaction(
    body: TransactionCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    ref = generate_transaction_ref(db)
    txn = Transaction(**body.model_dump(), ref=ref, created_by=user_id)
    db.add(txn)
    db.commit()
    db.refresh(txn)
    return TransactionOut.model_validate(txn)


@txn_router.patch("/{txn_id}/status", response_model=TransactionOut)
def update_txn_status(
    txn_id: int,
    body: TransactionStatusUpdate,
    db: Session = Depends(get_db),
    _: int = Depends(get_current_user_id),
):
    txn = db.query(Transaction).filter(Transaction.id == txn_id).first()
    if not txn:
        raise HTTPException(404, "Transaction not found")
    txn.status = body.status
    if body.paid_at:
        txn.paid_at = body.paid_at
    db.commit()
    db.refresh(txn)
    return TransactionOut.model_validate(txn)


# ─── Analytics & Dashboard Router ─────────────────────────────────────────────

analytics_router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@analytics_router.get("/dashboard", response_model=DashboardKPI)
def dashboard_kpi(
    db: Session = Depends(get_db),
    _: int = Depends(get_current_user_id),
):
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    active_statuses = [
        "confirmed", "qc_sorting", "packaging",
        "export_customs", "in_transit", "import_customs", "in_storage"
    ]
    active_count = db.query(func.count(Shipment.id)).filter(
        Shipment.status.in_(active_statuses)
    ).scalar() or 0

    revenue_mtd = db.query(func.coalesce(func.sum(Transaction.amount_usd), 0)).filter(
        Transaction.transaction_type == "revenue",
        Transaction.created_at >= month_start,
    ).scalar() or 0

    costs_mtd = db.query(func.coalesce(func.sum(func.abs(Transaction.amount_usd)), 0)).filter(
        Transaction.amount_usd < 0,
        Transaction.created_at >= month_start,
    ).scalar() or 0

    pending_customs = db.query(func.count(CustomsRecord.id)).filter(
        CustomsRecord.status.in_(["submitted", "processing", "hold"])
    ).scalar() or 0

    # Storage capacity (simplified)
    in_storage_weight = db.query(func.coalesce(func.sum(Shipment.weight_kg), 0)).filter(
        Shipment.status == "in_storage"
    ).scalar() or 0
    total_capacity = 200000  # 200t total configured capacity (kg)
    storage_pct = min(100.0, (in_storage_weight / total_capacity) * 100)

    in_transit_weight = db.query(func.coalesce(func.sum(Shipment.weight_kg), 0)).filter(
        Shipment.status == "in_transit"
    ).scalar() or 0

    return DashboardKPI(
        active_shipments=active_count,
        revenue_mtd=float(revenue_mtd),
        pending_customs=pending_customs,
        storage_capacity_pct=round(storage_pct, 1),
        net_profit_mtd=float(revenue_mtd) - float(costs_mtd),
        total_weight_in_transit_kg=float(in_transit_weight),
    )


@analytics_router.get("/corridors", response_model=List[TradeCorridorStat])
def trade_corridors(
    db: Session = Depends(get_db),
    _: int = Depends(get_current_user_id),
):
    rows = (
        db.query(
            Shipment.origin_country,
            Shipment.destination_country,
            func.count(Shipment.id).label("shipments"),
            func.sum(Shipment.declared_value_usd).label("total_value"),
            func.sum(Shipment.weight_kg).label("total_weight"),
        )
        .group_by(Shipment.origin_country, Shipment.destination_country)
        .order_by(func.sum(Shipment.declared_value_usd).desc())
        .limit(10)
        .all()
    )
    return [
        TradeCorridorStat(
            corridor=f"{r.origin_country} → {r.destination_country}",
            shipments=r.shipments,
            total_value_usd=float(r.total_value or 0),
            total_weight_kg=float(r.total_weight or 0),
        )
        for r in rows
    ]


@analytics_router.get("/report/{period}", response_model=ReportPeriod)
def period_report(
    period: str,
    db: Session = Depends(get_db),
    _: int = Depends(get_current_user_id),
):
    now = datetime.now(timezone.utc)
    if period == "daily":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        label = now.strftime("%b %d, %Y")
    elif period == "weekly":
        from datetime import timedelta
        start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
        label = f"Week of {start.strftime('%b %d')}"
    elif period == "monthly":
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        label = now.strftime("%B %Y")
    elif period == "quarterly":
        q_month = ((now.month - 1) // 3) * 3 + 1
        start = now.replace(month=q_month, day=1, hour=0, minute=0, second=0, microsecond=0)
        label = f"Q{(now.month-1)//3+1} {now.year}"
    else:  # annual
        start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        label = str(now.year)

    shipments_count = db.query(func.count(Shipment.id)).filter(Shipment.created_at >= start).scalar() or 0
    revenue = db.query(func.coalesce(func.sum(Transaction.amount_usd), 0)).filter(
        Transaction.transaction_type == "revenue", Transaction.created_at >= start
    ).scalar() or 0
    costs = db.query(func.coalesce(func.sum(func.abs(Transaction.amount_usd)), 0)).filter(
        Transaction.amount_usd < 0, Transaction.created_at >= start
    ).scalar() or 0
    customs_clears = db.query(func.count(CustomsRecord.id)).filter(
        CustomsRecord.status == "cleared", CustomsRecord.cleared_at >= start
    ).scalar() or 0
    qc_count = db.query(func.count(QCRecord.id)).filter(QCRecord.inspection_date >= start).scalar() or 0
    alerts = db.query(func.count(CustomsRecord.id)).filter(
        CustomsRecord.status == "hold"
    ).scalar() or 0

    return ReportPeriod(
        period=period,
        label=label,
        shipments_count=shipments_count,
        revenue=float(revenue),
        costs=float(costs),
        net=float(revenue) - float(costs),
        customs_clearances=customs_clears,
        qc_inspections=qc_count,
        alerts_count=alerts,
    )


# ─── Storage Bays API ─────────────────────────────────────────────────────────

storage_router = APIRouter(prefix="/api/storage", tags=["storage"])


@storage_router.get("/bays")
def list_storage_bays(
    db: Session = Depends(get_db),
    _: int = Depends(get_current_user_id),
):
    """Live status of all storage bays with utilisation %."""
    from services.storage_service import get_all_bays_status
    return get_all_bays_status(db)
