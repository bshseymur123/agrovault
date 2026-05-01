from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import (
    String, Integer, Float, Boolean, DateTime, Text,
    ForeignKey, Enum as SAEnum, JSON
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from db.session import Base
import enum


def utcnow():
    return datetime.now(timezone.utc)


# ─── Enumerations ────────────────────────────────────────────────────────────

class UserRole(str, enum.Enum):
    owner = "owner"
    ceo = "ceo"
    director = "director"
    manager = "manager"
    accountant = "accountant"
    operator = "operator"


class ShipmentType(str, enum.Enum):
    import_ = "import"
    export = "export"
    transit = "transit"
    internal = "internal"


class ShipmentStatus(str, enum.Enum):
    draft = "draft"
    confirmed = "confirmed"
    qc_sorting = "qc_sorting"
    packaging = "packaging"
    export_customs = "export_customs"
    in_transit = "in_transit"
    import_customs = "import_customs"
    in_storage = "in_storage"
    delivered = "delivered"
    invoiced = "invoiced"
    payment_received = "payment_received"
    cancelled = "cancelled"


class CustomsStatus(str, enum.Enum):
    not_started = "not_started"
    submitted = "submitted"
    processing = "processing"
    hold = "hold"
    cleared = "cleared"
    rejected = "rejected"


class TransactionType(str, enum.Enum):
    revenue = "revenue"
    freight = "freight"
    customs_duty = "customs_duty"
    storage = "storage"
    packaging = "packaging"
    procurement = "procurement"
    tax = "tax"
    other_opex = "other_opex"


class TransactionStatus(str, enum.Enum):
    pending = "pending"
    paid = "paid"
    overdue = "overdue"
    cancelled = "cancelled"


class QCGrade(str, enum.Enum):
    grade_a = "A"
    grade_b = "B"
    rejected = "rejected"


class TransportMode(str, enum.Enum):
    truck_refrigerated = "truck_refrigerated"
    air_freight = "air_freight"
    sea_container = "sea_container"
    rail_reefer = "rail_reefer"


# ─── Models ──────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255))
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(SAEnum(UserRole), default=UserRole.operator)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    shipments: Mapped[list["Shipment"]] = relationship("Shipment", back_populates="created_by_user")
    audit_logs: Mapped[list["AuditLog"]] = relationship("AuditLog", back_populates="user")


class Shipment(Base):
    __tablename__ = "shipments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    shipment_ref: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    shipment_type: Mapped[ShipmentType] = mapped_column(SAEnum(ShipmentType))
    status: Mapped[ShipmentStatus] = mapped_column(SAEnum(ShipmentStatus), default=ShipmentStatus.draft)

    product_name: Mapped[str] = mapped_column(String(100))
    product_variety: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    hs_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    weight_kg: Mapped[float] = mapped_column(Float)
    declared_value_usd: Mapped[float] = mapped_column(Float)

    origin_country: Mapped[str] = mapped_column(String(100))
    origin_city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    destination_country: Mapped[str] = mapped_column(String(100))
    destination_city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    supplier_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    buyer_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    transport_mode: Mapped[TransportMode] = mapped_column(SAEnum(TransportMode), default=TransportMode.truck_refrigerated)
    carrier_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    tracking_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    storage_bay: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    storage_temp_c: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    departure_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    expected_arrival: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    actual_arrival: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))

    created_by_user: Mapped["User"] = relationship("User", back_populates="shipments")
    qc_records: Mapped[list["QCRecord"]] = relationship("QCRecord", back_populates="shipment", cascade="all, delete-orphan")
    customs_records: Mapped[list["CustomsRecord"]] = relationship("CustomsRecord", back_populates="shipment", cascade="all, delete-orphan")
    transactions: Mapped[list["Transaction"]] = relationship("Transaction", back_populates="shipment")
    status_history: Mapped[list["ShipmentStatusHistory"]] = relationship("ShipmentStatusHistory", back_populates="shipment", cascade="all, delete-orphan")
    documents: Mapped[list["Document"]] = relationship("Document", back_populates="shipment", cascade="all, delete-orphan")


class ShipmentStatusHistory(Base):
    __tablename__ = "shipment_status_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    shipment_id: Mapped[int] = mapped_column(Integer, ForeignKey("shipments.id"))
    from_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    to_status: Mapped[str] = mapped_column(String(50))
    changed_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    shipment: Mapped["Shipment"] = relationship("Shipment", back_populates="status_history")


class QCRecord(Base):
    __tablename__ = "qc_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    shipment_id: Mapped[int] = mapped_column(Integer, ForeignKey("shipments.id"))
    lot_number: Mapped[str] = mapped_column(String(50))
    inspection_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    inspector_name: Mapped[str] = mapped_column(String(255))

    grade_a_kg: Mapped[float] = mapped_column(Float, default=0)
    grade_b_kg: Mapped[float] = mapped_column(Float, default=0)
    rejected_kg: Mapped[float] = mapped_column(Float, default=0)

    packaging_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    pallets_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    storage_temp_at_inspection: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    cold_chain_maintained: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    shipment: Mapped["Shipment"] = relationship("Shipment", back_populates="qc_records")


class CustomsRecord(Base):
    __tablename__ = "customs_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    shipment_id: Mapped[int] = mapped_column(Integer, ForeignKey("shipments.id"))
    direction: Mapped[str] = mapped_column(String(20))  # export | import
    status: Mapped[CustomsStatus] = mapped_column(SAEnum(CustomsStatus), default=CustomsStatus.not_started)

    declaration_ref: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    border_point: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    cleared_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    duty_amount_usd: Mapped[float] = mapped_column(Float, default=0)
    vat_amount_usd: Mapped[float] = mapped_column(Float, default=0)
    other_fees_usd: Mapped[float] = mapped_column(Float, default=0)

    hold_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    shipment: Mapped["Shipment"] = relationship("Shipment", back_populates="customs_records")
    documents: Mapped[list["Document"]] = relationship("Document", back_populates="customs_record")


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    shipment_id: Mapped[int] = mapped_column(Integer, ForeignKey("shipments.id"))
    customs_record_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("customs_records.id"), nullable=True)
    doc_type: Mapped[str] = mapped_column(String(80))
    filename: Mapped[str] = mapped_column(String(255))
    file_path: Mapped[str] = mapped_column(String(500))
    uploaded_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    shipment: Mapped["Shipment"] = relationship("Shipment", back_populates="documents")
    customs_record: Mapped[Optional["CustomsRecord"]] = relationship("CustomsRecord", back_populates="documents")


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    ref: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    shipment_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("shipments.id"), nullable=True)

    transaction_type: Mapped[TransactionType] = mapped_column(SAEnum(TransactionType))
    status: Mapped[TransactionStatus] = mapped_column(SAEnum(TransactionStatus), default=TransactionStatus.pending)

    description: Mapped[str] = mapped_column(String(500))
    amount_usd: Mapped[float] = mapped_column(Float)  # positive = credit, negative = debit
    currency: Mapped[str] = mapped_column(String(10), default="USD")
    exchange_rate: Mapped[float] = mapped_column(Float, default=1.0)

    counterparty: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    invoice_ref: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))

    shipment: Mapped[Optional["Shipment"]] = relationship("Shipment", back_populates="transactions")


class StorageBay(Base):
    __tablename__ = "storage_bays"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    bay_code: Mapped[str] = mapped_column(String(20), unique=True)
    bay_name: Mapped[str] = mapped_column(String(100))
    bay_type: Mapped[str] = mapped_column(String(50))  # cold | ambient | frozen
    temp_min_c: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    temp_max_c: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    capacity_kg: Mapped[float] = mapped_column(Float)
    current_load_kg: Mapped[float] = mapped_column(Float, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_temp_reading: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    last_temp_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    entity_type: Mapped[str] = mapped_column(String(50))
    entity_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    action: Mapped[str] = mapped_column(String(50))  # create | update | delete | login | export
    detail: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped[Optional["User"]] = relationship("User", back_populates="audit_logs")
