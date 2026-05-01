"""
Seed the database with realistic demo data for AgroVault.
Run: python seed.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from datetime import datetime, timedelta, timezone
from db.session import engine, SessionLocal
from db.session import Base
from models.models import (
    User, Shipment, ShipmentStatusHistory, QCRecord,
    CustomsRecord, Transaction, StorageBay, AuditLog,
    UserRole, ShipmentType, ShipmentStatus, CustomsStatus,
    TransactionType, TransactionStatus, TransportMode
)
from core.security import hash_password


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # ── Users ──────────────────────────────────────────────────────────────
    users_data = [
        ("admin@agrovault.com", "System Admin", "admin123", UserRole.owner),
        ("ceo@agrovault.com", "Azer Karimov", "demo123", UserRole.ceo),
        ("director@agrovault.com", "Dinar Nazarov", "demo123", UserRole.director),
        ("manager@agrovault.com", "Rauf Mammadov", "demo123", UserRole.manager),
        ("accountant@agrovault.com", "Farida Hasanova", "demo123", UserRole.accountant),
        ("operator@agrovault.com", "Murad Aliyev", "demo123", UserRole.operator),
    ]
    users = {}
    for email, name, pw, role in users_data:
        if not db.query(User).filter(User.email == email).first():
            u = User(email=email, full_name=name, hashed_password=hash_password(pw), role=role)
            db.add(u)
            db.flush()
            users[email] = u.id
        else:
            users[email] = db.query(User).filter(User.email == email).first().id
    db.commit()

    admin_id = users["admin@agrovault.com"]
    manager_id = users["manager@agrovault.com"]

    # ── Storage Bays ───────────────────────────────────────────────────────
    bays = [
        ("A-01", "Cold Bay 1", "cold", 0, 4, 50000),
        ("A-02", "Cold Bay 2", "cold", 0, 4, 50000),
        ("A-03", "Cold Bay 3", "cold", 2, 6, 40000),
        ("B-01", "Ambient Bay 1", "ambient", 15, 22, 30000),
        ("B-02", "Ambient Bay 2", "ambient", 15, 22, 30000),
    ]
    for code, name, btype, tmin, tmax, cap in bays:
        if not db.query(StorageBay).filter(StorageBay.bay_code == code).first():
            db.add(StorageBay(bay_code=code, bay_name=name, bay_type=btype,
                              temp_min_c=tmin, temp_max_c=tmax, capacity_kg=cap))
    db.commit()

    # ── Shipments + associated records ────────────────────────────────────
    now = datetime.now(timezone.utc)

    shipments_seed = [
        {
            "ref": "SH-2026-0001", "stype": ShipmentType.import_, "status": ShipmentStatus.in_transit,
            "product": "Tomatoes", "weight": 12000, "value": 24000,
            "origin": "Turkey", "dest": "Azerbaijan", "buyer": "BakuFresh LLC",
            "transport": TransportMode.truck_refrigerated, "bay": "A-01",
            "departure": now - timedelta(days=3), "eta": now + timedelta(days=2),
        },
        {
            "ref": "SH-2026-0002", "stype": ShipmentType.export, "status": ShipmentStatus.import_customs,
            "product": "Apples", "weight": 8000, "value": 19200,
            "origin": "Azerbaijan", "dest": "Russia", "buyer": "Soyuz Import",
            "transport": TransportMode.truck_refrigerated, "bay": None,
            "departure": now - timedelta(days=4), "eta": now + timedelta(days=1),
        },
        {
            "ref": "SH-2026-0003", "stype": ShipmentType.import_, "status": ShipmentStatus.import_customs,
            "product": "Citrus Mix", "weight": 20000, "value": 38000,
            "origin": "Egypt", "dest": "Azerbaijan", "buyer": "Internal",
            "transport": TransportMode.sea_container, "bay": "A-02",
            "departure": now - timedelta(days=8), "eta": now + timedelta(days=1),
        },
        {
            "ref": "SH-2026-0004", "stype": ShipmentType.export, "status": ShipmentStatus.packaging,
            "product": "Grapes", "weight": 5000, "value": 15500,
            "origin": "Azerbaijan", "dest": "UAE", "buyer": "Al-Nour Trading",
            "transport": TransportMode.air_freight, "bay": "A-03",
            "departure": now + timedelta(days=3), "eta": now + timedelta(days=5),
        },
        {
            "ref": "SH-2026-0005", "stype": ShipmentType.export, "status": ShipmentStatus.qc_sorting,
            "product": "Pomegranate", "weight": 3000, "value": 11400,
            "origin": "Azerbaijan", "dest": "Germany", "buyer": "FrischMarkt GmbH",
            "transport": TransportMode.truck_refrigerated, "bay": "A-01",
            "departure": now + timedelta(days=6), "eta": now + timedelta(days=12),
        },
        {
            "ref": "SH-2026-0006", "stype": ShipmentType.export, "status": ShipmentStatus.payment_received,
            "product": "Apples", "weight": 10000, "value": 24000,
            "origin": "Azerbaijan", "dest": "Russia", "buyer": "Soyuz Import",
            "transport": TransportMode.truck_refrigerated, "bay": None,
            "departure": now - timedelta(days=20), "eta": now - timedelta(days=14),
        },
    ]

    for s in shipments_seed:
        if db.query(Shipment).filter(Shipment.shipment_ref == s["ref"]).first():
            continue
        shipment = Shipment(
            shipment_ref=s["ref"], shipment_type=s["stype"], status=s["status"],
            product_name=s["product"], weight_kg=s["weight"], declared_value_usd=s["value"],
            origin_country=s["origin"], destination_country=s["dest"],
            buyer_name=s["buyer"], transport_mode=s["transport"],
            storage_bay=s["bay"], departure_date=s["departure"],
            expected_arrival=s["eta"], created_by=manager_id,
        )
        db.add(shipment)
        db.flush()

        # Status history
        db.add(ShipmentStatusHistory(
            shipment_id=shipment.id, from_status=None,
            to_status="draft", changed_by=manager_id, note="Created",
        ))
        db.add(ShipmentStatusHistory(
            shipment_id=shipment.id, from_status="draft",
            to_status=s["status"].value, changed_by=manager_id, note="Status advanced",
        ))

        # QC for relevant statuses
        if s["status"].value in ("qc_sorting", "packaging", "export_customs",
                                  "in_transit", "delivered", "payment_received"):
            db.add(QCRecord(
                shipment_id=shipment.id, lot_number=f"LOT-{s['ref']}",
                inspector_name="M. Hasanov",
                grade_a_kg=s["weight"] * 0.87,
                grade_b_kg=s["weight"] * 0.09,
                rejected_kg=s["weight"] * 0.04,
                packaging_type="5kg export cartons", pallets_count=int(s["weight"] / 125),
                storage_temp_at_inspection=3.5, cold_chain_maintained=True,
            ))

        # Customs
        if s["status"].value in ("import_customs", "export_customs", "in_transit",
                                  "in_storage", "delivered", "invoiced", "payment_received"):
            cs = CustomsStatus.cleared if s["status"].value != "import_customs" else (
                CustomsStatus.hold if s["ref"] == "SH-2026-0003" else CustomsStatus.processing
            )
            cr = CustomsRecord(
                shipment_id=shipment.id, direction="export" if s["stype"] == ShipmentType.export else "import",
                status=cs, border_point="Baku International Port",
                declaration_ref=f"DECL-{s['ref']}" if cs == CustomsStatus.cleared else None,
                duty_amount_usd=s["value"] * 0.048,
                vat_amount_usd=s["value"] * 0.18 if s["stype"] == ShipmentType.import_ else 0,
                hold_reason="Phytosanitary certificate missing" if s["ref"] == "SH-2026-0003" else None,
                cleared_at=now - timedelta(days=1) if cs == CustomsStatus.cleared else None,
                submitted_at=now - timedelta(days=2) if cs != CustomsStatus.not_started else None,
            )
            db.add(cr)

    db.commit()

    # ── Transactions ───────────────────────────────────────────────────────
    txns = [
        ("TXN-2026-0001", "revenue", 19200, "SH-2026-0002", "Soyuz Import", TransactionStatus.paid),
        ("TXN-2026-0002", "customs_duty", -1840, "SH-2026-0002", "AZE Customs", TransactionStatus.paid),
        ("TXN-2026-0003", "freight", -3200, "SH-2026-0001", "TransCargo LLC", TransactionStatus.pending),
        ("TXN-2026-0004", "storage", -1800, "SH-2026-0001", "Bay A-01", TransactionStatus.paid),
        ("TXN-2026-0005", "revenue", 14200, "SH-2026-0004", "Al-Nour Trading", TransactionStatus.overdue),
        ("TXN-2026-0006", "packaging", -620, "SH-2026-0004", "PackSupply Co", TransactionStatus.paid),
        ("TXN-2026-0007", "procurement", -19000, "SH-2026-0003", "EgyptFresh Ltd", TransactionStatus.paid),
        ("TXN-2026-0008", "revenue", 24000, "SH-2026-0006", "Soyuz Import", TransactionStatus.paid),
        ("TXN-2026-0009", "tax", -2400, "SH-2026-0006", "Tax Authority", TransactionStatus.paid),
        ("TXN-2026-0010", "freight", -4100, "SH-2026-0003", "SeaCargo Ltd", TransactionStatus.paid),
    ]

    for ref, ttype, amt, ship_ref, party, tstatus in txns:
        if db.query(Transaction).filter(Transaction.ref == ref).first():
            continue
        s = db.query(Shipment).filter(Shipment.shipment_ref == ship_ref).first()
        db.add(Transaction(
            ref=ref, transaction_type=ttype, amount_usd=amt,
            description=f"{ttype.replace('_', ' ').title()} — {ship_ref}",
            shipment_id=s.id if s else None,
            counterparty=party, status=tstatus,
            created_by=admin_id,
            paid_at=now - timedelta(days=1) if tstatus == TransactionStatus.paid else None,
            due_date=now - timedelta(days=7) if tstatus == TransactionStatus.overdue else now + timedelta(days=30),
        ))
    db.commit()
    db.close()
    print("✓ Database seeded successfully")


if __name__ == "__main__":
    seed()
