from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, field_validator
from models.models import (
    UserRole, ShipmentType, ShipmentStatus, CustomsStatus,
    TransactionType, TransactionStatus, TransportMode
)


# ─── Auth ─────────────────────────────────────────────────────────────────────

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserOut"


class LoginRequest(BaseModel):
    email: str
    password: str


# ─── Users ───────────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    email: EmailStr
    full_name: str
    password: str
    role: UserRole = UserRole.operator


class UserOut(BaseModel):
    id: int
    email: str
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Shipments ───────────────────────────────────────────────────────────────

class ShipmentCreate(BaseModel):
    shipment_type: ShipmentType
    product_name: str
    product_variety: Optional[str] = None
    hs_code: Optional[str] = None
    weight_kg: float
    declared_value_usd: float
    origin_country: str
    origin_city: Optional[str] = None
    destination_country: str
    destination_city: Optional[str] = None
    supplier_name: Optional[str] = None
    buyer_name: Optional[str] = None
    transport_mode: TransportMode = TransportMode.truck_refrigerated
    carrier_name: Optional[str] = None
    tracking_number: Optional[str] = None
    storage_bay: Optional[str] = None
    storage_temp_c: Optional[float] = None
    departure_date: Optional[datetime] = None
    expected_arrival: Optional[datetime] = None
    notes: Optional[str] = None


class ShipmentUpdate(BaseModel):
    status: Optional[ShipmentStatus] = None
    tracking_number: Optional[str] = None
    carrier_name: Optional[str] = None
    storage_bay: Optional[str] = None
    actual_arrival: Optional[datetime] = None
    notes: Optional[str] = None


class ShipmentStatusUpdate(BaseModel):
    status: ShipmentStatus
    note: Optional[str] = None


class StatusHistoryOut(BaseModel):
    from_status: Optional[str]
    to_status: str
    note: Optional[str]
    changed_at: datetime

    class Config:
        from_attributes = True


class ShipmentOut(BaseModel):
    id: int
    shipment_ref: str
    shipment_type: ShipmentType
    status: ShipmentStatus
    product_name: str
    product_variety: Optional[str]
    hs_code: Optional[str]
    weight_kg: float
    declared_value_usd: float
    origin_country: str
    origin_city: Optional[str]
    destination_country: str
    destination_city: Optional[str]
    supplier_name: Optional[str]
    buyer_name: Optional[str]
    transport_mode: TransportMode
    carrier_name: Optional[str]
    tracking_number: Optional[str]
    storage_bay: Optional[str]
    departure_date: Optional[datetime]
    expected_arrival: Optional[datetime]
    actual_arrival: Optional[datetime]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ShipmentDetail(ShipmentOut):
    qc_records: List["QCOut"] = []
    customs_records: List["CustomsOut"] = []
    transactions: List["TransactionOut"] = []
    status_history: List[StatusHistoryOut] = []
    documents: List["DocumentOut"] = []


# ─── QC ──────────────────────────────────────────────────────────────────────

class QCCreate(BaseModel):
    lot_number: str
    inspector_name: str
    grade_a_kg: float = 0
    grade_b_kg: float = 0
    rejected_kg: float = 0
    packaging_type: Optional[str] = None
    pallets_count: Optional[int] = None
    storage_temp_at_inspection: Optional[float] = None
    cold_chain_maintained: bool = True
    notes: Optional[str] = None


class QCOut(BaseModel):
    id: int
    shipment_id: int
    lot_number: str
    inspector_name: str
    grade_a_kg: float
    grade_b_kg: float
    rejected_kg: float
    packaging_type: Optional[str]
    pallets_count: Optional[int]
    cold_chain_maintained: bool
    inspection_date: datetime
    notes: Optional[str]

    class Config:
        from_attributes = True


# ─── Customs ─────────────────────────────────────────────────────────────────

class CustomsCreate(BaseModel):
    direction: str  # export | import
    border_point: Optional[str] = None
    declaration_ref: Optional[str] = None
    duty_amount_usd: float = 0
    vat_amount_usd: float = 0
    other_fees_usd: float = 0
    notes: Optional[str] = None


class CustomsStatusUpdate(BaseModel):
    status: CustomsStatus
    declaration_ref: Optional[str] = None
    hold_reason: Optional[str] = None
    duty_amount_usd: Optional[float] = None
    notes: Optional[str] = None


class CustomsOut(BaseModel):
    id: int
    shipment_id: int
    direction: str
    status: CustomsStatus
    declaration_ref: Optional[str]
    border_point: Optional[str]
    submitted_at: Optional[datetime]
    cleared_at: Optional[datetime]
    duty_amount_usd: float
    vat_amount_usd: float
    other_fees_usd: float
    hold_reason: Optional[str]
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Documents ───────────────────────────────────────────────────────────────

class DocumentOut(BaseModel):
    id: int
    doc_type: str
    filename: str
    uploaded_at: datetime

    class Config:
        from_attributes = True


# ─── Transactions ─────────────────────────────────────────────────────────────

class TransactionCreate(BaseModel):
    shipment_id: Optional[int] = None
    transaction_type: TransactionType
    description: str
    amount_usd: float
    currency: str = "USD"
    exchange_rate: float = 1.0
    counterparty: Optional[str] = None
    due_date: Optional[datetime] = None
    invoice_ref: Optional[str] = None
    notes: Optional[str] = None


class TransactionStatusUpdate(BaseModel):
    status: TransactionStatus
    paid_at: Optional[datetime] = None


class TransactionOut(BaseModel):
    id: int
    ref: str
    shipment_id: Optional[int]
    transaction_type: TransactionType
    status: TransactionStatus
    description: str
    amount_usd: float
    currency: str
    counterparty: Optional[str]
    due_date: Optional[datetime]
    paid_at: Optional[datetime]
    invoice_ref: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Analytics / Reports ──────────────────────────────────────────────────────

class DashboardKPI(BaseModel):
    active_shipments: int
    revenue_mtd: float
    pending_customs: int
    storage_capacity_pct: float
    net_profit_mtd: float
    total_weight_in_transit_kg: float


class ReportPeriod(BaseModel):
    period: str  # daily | weekly | monthly | quarterly | annual
    label: str
    shipments_count: int
    revenue: float
    costs: float
    net: float
    customs_clearances: int
    qc_inspections: int
    alerts_count: int


class TradeCorridorStat(BaseModel):
    corridor: str
    shipments: int
    total_value_usd: float
    total_weight_kg: float


# Allow forward references
ShipmentDetail.model_rebuild()
