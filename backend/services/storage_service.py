"""
Storage bay capacity management.
Called whenever a shipment status transitions to/from in_storage.
"""
from sqlalchemy.orm import Session
from models.models import StorageBay, Shipment, ShipmentStatus
from datetime import datetime, timezone


def _get_bay(db: Session, bay_code: str) -> StorageBay | None:
    if not bay_code:
        return None
    # Normalise: strip extra label text like "A-01 (Cold, 0–4°C)" → "A-01"
    code = bay_code.split(" ")[0].strip()
    return db.query(StorageBay).filter(StorageBay.bay_code == code).first()


def assign_to_storage(db: Session, shipment: Shipment) -> dict:
    """
    Called when a shipment moves INTO in_storage.
    Adds its weight to the bay's current load.
    Returns a dict with bay info or a warning if bay not found / over capacity.
    """
    bay = _get_bay(db, shipment.storage_bay)
    if not bay:
        return {"warning": f"Bay '{shipment.storage_bay}' not found — load not tracked"}

    new_load = bay.current_load_kg + shipment.weight_kg
    if new_load > bay.capacity_kg:
        return {
            "warning": (
                f"Bay {bay.bay_code} would exceed capacity "
                f"({new_load:.0f} kg / {bay.capacity_kg:.0f} kg). "
                f"Assign a different bay."
            )
        }

    bay.current_load_kg = new_load
    bay.last_temp_at = datetime.now(timezone.utc)
    db.commit()
    return {
        "bay": bay.bay_code,
        "current_load_kg": bay.current_load_kg,
        "capacity_kg": bay.capacity_kg,
        "utilisation_pct": round((bay.current_load_kg / bay.capacity_kg) * 100, 1),
    }


def release_from_storage(db: Session, shipment: Shipment) -> dict:
    """
    Called when a shipment moves OUT of in_storage (delivered / cancelled).
    Subtracts its weight from the bay's current load.
    """
    bay = _get_bay(db, shipment.storage_bay)
    if not bay:
        return {"warning": "Bay not found — nothing to release"}

    bay.current_load_kg = max(0, bay.current_load_kg - shipment.weight_kg)
    db.commit()
    return {
        "bay": bay.bay_code,
        "current_load_kg": bay.current_load_kg,
        "freed_kg": shipment.weight_kg,
    }


def get_all_bays_status(db: Session) -> list[dict]:
    """Return live status of all storage bays."""
    bays = db.query(StorageBay).filter(StorageBay.is_active == True).all()
    return [
        {
            "bay_code": b.bay_code,
            "bay_name": b.bay_name,
            "bay_type": b.bay_type,
            "temp_range": f"{b.temp_min_c}–{b.temp_max_c}°C" if b.temp_min_c is not None else "—",
            "capacity_kg": b.capacity_kg,
            "current_load_kg": b.current_load_kg,
            "available_kg": max(0, b.capacity_kg - b.current_load_kg),
            "utilisation_pct": round((b.current_load_kg / b.capacity_kg) * 100, 1) if b.capacity_kg else 0,
            "last_temp_c": b.last_temp_reading,
            "last_temp_at": b.last_temp_at,
            "alert": b.current_load_kg > b.capacity_kg * 0.90,
        }
        for b in bays
    ]
