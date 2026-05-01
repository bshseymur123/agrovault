from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone

from db.session import get_db
from models.models import Shipment, ShipmentStatusHistory, ShipmentStatus
from schemas.schemas import (
    ShipmentCreate, ShipmentUpdate, ShipmentOut, ShipmentDetail,
    ShipmentStatusUpdate, StatusHistoryOut
)
from core.security import get_current_user_id
from services.ref_generator import generate_shipment_ref
from services.storage_service import assign_to_storage, release_from_storage

router = APIRouter(prefix="/api/shipments", tags=["shipments"])


@router.get("", response_model=List[ShipmentOut])
def list_shipments(
    status: Optional[str] = None,
    product: Optional[str] = None,
    origin: Optional[str] = None,
    destination: Optional[str] = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: Session = Depends(get_db),
    _: int = Depends(get_current_user_id),
):
    q = db.query(Shipment)
    if status:
        q = q.filter(Shipment.status == status)
    if product:
        q = q.filter(Shipment.product_name.ilike(f"%{product}%"))
    if origin:
        q = q.filter(Shipment.origin_country.ilike(f"%{origin}%"))
    if destination:
        q = q.filter(Shipment.destination_country.ilike(f"%{destination}%"))
    q = q.order_by(Shipment.created_at.desc())
    return [ShipmentOut.model_validate(s) for s in q.offset(offset).limit(limit).all()]


@router.post("", response_model=ShipmentOut, status_code=201)
def create_shipment(
    body: ShipmentCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    ref = generate_shipment_ref(db)
    shipment = Shipment(**body.model_dump(), shipment_ref=ref, created_by=user_id)
    db.add(shipment)
    db.flush()
    history = ShipmentStatusHistory(
        shipment_id=shipment.id,
        from_status=None,
        to_status=ShipmentStatus.draft.value,
        changed_by=user_id,
        note="Shipment created",
    )
    db.add(history)
    db.commit()
    db.refresh(shipment)
    return ShipmentOut.model_validate(shipment)


@router.get("/{shipment_id}", response_model=ShipmentDetail)
def get_shipment(
    shipment_id: int,
    db: Session = Depends(get_db),
    _: int = Depends(get_current_user_id),
):
    s = db.query(Shipment).filter(Shipment.id == shipment_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Shipment not found")
    return ShipmentDetail.model_validate(s)


@router.patch("/{shipment_id}", response_model=ShipmentOut)
def update_shipment(
    shipment_id: int,
    body: ShipmentUpdate,
    db: Session = Depends(get_db),
    _: int = Depends(get_current_user_id),
):
    s = db.query(Shipment).filter(Shipment.id == shipment_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Shipment not found")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(s, k, v)
    s.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(s)
    return ShipmentOut.model_validate(s)


@router.post("/{shipment_id}/status", response_model=ShipmentOut)
def advance_status(
    shipment_id: int,
    body: ShipmentStatusUpdate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    s = db.query(Shipment).filter(Shipment.id == shipment_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Shipment not found")
    prev = s.status.value if s.status else None
    new_status = body.status

    s.status = new_status
    s.updated_at = datetime.now(timezone.utc)

    # ── Storage bay capacity tracking ──────────────────────────────────────
    if new_status == ShipmentStatus.in_storage:
        assign_to_storage(db, s)
    elif prev == ShipmentStatus.in_storage.value and new_status in (
        ShipmentStatus.delivered, ShipmentStatus.cancelled
    ):
        release_from_storage(db, s)

    history = ShipmentStatusHistory(
        shipment_id=s.id,
        from_status=prev,
        to_status=body.status.value,
        changed_by=user_id,
        note=body.note,
    )
    db.add(history)
    db.commit()
    db.refresh(s)
    return ShipmentOut.model_validate(s)


@router.get("/{shipment_id}/timeline", response_model=List[StatusHistoryOut])
def get_timeline(
    shipment_id: int,
    db: Session = Depends(get_db),
    _: int = Depends(get_current_user_id),
):
    records = (
        db.query(ShipmentStatusHistory)
        .filter(ShipmentStatusHistory.shipment_id == shipment_id)
        .order_by(ShipmentStatusHistory.changed_at.asc())
        .all()
    )
    return [StatusHistoryOut.model_validate(r) for r in records]
