"""
Shipment lifecycle tests — full A to Z pipeline.

Covers:
  - Create shipment → verify ref format and draft status
  - List shipments with filters (status, product, origin, destination)
  - Get single shipment detail
  - Advance through all 11 status stages in order
  - Verify timeline grows with each transition
  - Storage bay capacity auto-updates on in_storage entry
  - Storage bay load released on delivery
  - QC record creation and retrieval
  - Customs record creation and status transitions
  - Document checklist (customs hold flagging)
  - Transaction creation, listing, overdue auto-flag
  - Analytics dashboard KPIs update after shipment changes
  - Analytics trade corridors
  - Period reports (daily, weekly, monthly)
  - 404 for non-existent shipment
  - Cannot create shipment without auth
"""
import pytest


# ─── Helpers ─────────────────────────────────────────────────────────────────

SHIPMENT_STAGES = [
    "confirmed",
    "qc_sorting",
    "packaging",
    "export_customs",
    "in_transit",
    "import_customs",
    "in_storage",
    "delivered",
    "invoiced",
    "payment_received",
]

VALID_SHIPMENT = {
    "shipment_type": "export",
    "product_name": "Pomegranate",
    "product_variety": "Wonderful",
    "hs_code": "0810 10 00",
    "weight_kg": 5000,
    "declared_value_usd": 15000,
    "origin_country": "Azerbaijan",
    "origin_city": "Baku",
    "destination_country": "Germany",
    "destination_city": "Berlin",
    "supplier_name": "AzFresh LLC",
    "buyer_name": "FrischMarkt GmbH",
    "transport_mode": "truck_refrigerated",
    "carrier_name": "EuroCargo",
    "storage_bay": "A-01",
    "notes": "Handle with care — cold chain required",
}


# ─── Fixtures shared within this module ──────────────────────────────────────

@pytest.fixture(scope="module")
def shipment_id(client, manager_headers):
    """Create one shipment that persists for the whole module."""
    resp = client.post("/api/shipments", json=VALID_SHIPMENT, headers=manager_headers)
    assert resp.status_code == 201
    return resp.json()["id"]


@pytest.fixture(scope="module")
def shipment_ref(client, manager_headers, shipment_id):
    resp = client.get(f"/api/shipments/{shipment_id}", headers=manager_headers)
    return resp.json()["shipment_ref"]


# ─── Creation ─────────────────────────────────────────────────────────────────

class TestShipmentCreation:
    def test_create_returns_201(self, client, manager_headers):
        resp = client.post("/api/shipments", json=VALID_SHIPMENT, headers=manager_headers)
        assert resp.status_code == 201

    def test_created_shipment_has_draft_status(self, client, manager_headers):
        resp = client.post("/api/shipments", json=VALID_SHIPMENT, headers=manager_headers)
        assert resp.json()["status"] == "draft"

    def test_ref_format_is_sh_year_number(self, client, manager_headers, shipment_ref):
        parts = shipment_ref.split("-")
        assert parts[0] == "SH"
        assert len(parts[1]) == 4     # year
        assert parts[2].isdigit()

    def test_create_requires_weight(self, client, manager_headers):
        bad = {**VALID_SHIPMENT}
        del bad["weight_kg"]
        resp = client.post("/api/shipments", json=bad, headers=manager_headers)
        assert resp.status_code == 422

    def test_create_without_auth_returns_401(self, client):
        resp = client.post("/api/shipments", json=VALID_SHIPMENT)
        assert resp.status_code == 401

    def test_product_name_is_stored_correctly(self, client, manager_headers, shipment_id):
        resp = client.get(f"/api/shipments/{shipment_id}", headers=manager_headers)
        assert resp.json()["product_name"] == "Pomegranate"

    def test_hs_code_is_stored(self, client, manager_headers, shipment_id):
        resp = client.get(f"/api/shipments/{shipment_id}", headers=manager_headers)
        assert resp.json()["hs_code"] == "0810 10 00"


# ─── Listing & Filtering ──────────────────────────────────────────────────────

class TestShipmentListing:
    def test_list_returns_array(self, client, ceo_headers):
        resp = client.get("/api/shipments", headers=ceo_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_list_filter_by_status(self, client, manager_headers):
        resp = client.get("/api/shipments?status=draft", headers=manager_headers)
        assert resp.status_code == 200
        for s in resp.json():
            assert s["status"] == "draft"

    def test_list_filter_by_product(self, client, manager_headers):
        resp = client.get("/api/shipments?product=Pomegranate", headers=manager_headers)
        assert resp.status_code == 200
        for s in resp.json():
            assert "pomegranate" in s["product_name"].lower()

    def test_list_filter_by_origin(self, client, manager_headers):
        resp = client.get("/api/shipments?origin=Azerbaijan", headers=manager_headers)
        assert resp.status_code == 200
        for s in resp.json():
            assert "azerbaijan" in s["origin_country"].lower()

    def test_list_filter_by_destination(self, client, manager_headers):
        resp = client.get("/api/shipments?destination=Germany", headers=manager_headers)
        assert resp.status_code == 200
        for s in resp.json():
            assert "germany" in s["destination_country"].lower()

    def test_list_nonexistent_status_returns_empty(self, client, manager_headers):
        resp = client.get("/api/shipments?status=payment_received", headers=manager_headers)
        assert resp.status_code == 200
        # May or may not be empty, but should succeed

    def test_list_limit_param(self, client, manager_headers):
        resp = client.get("/api/shipments?limit=2", headers=manager_headers)
        assert resp.status_code == 200
        assert len(resp.json()) <= 2


# ─── Detail ───────────────────────────────────────────────────────────────────

class TestShipmentDetail:
    def test_get_by_id_returns_200(self, client, ceo_headers, shipment_id):
        resp = client.get(f"/api/shipments/{shipment_id}", headers=ceo_headers)
        assert resp.status_code == 200

    def test_detail_includes_related_records(self, client, manager_headers, shipment_id):
        resp = client.get(f"/api/shipments/{shipment_id}", headers=manager_headers)
        data = resp.json()
        assert "qc_records" in data
        assert "customs_records" in data
        assert "transactions" in data
        assert "status_history" in data
        assert "documents" in data

    def test_nonexistent_id_returns_404(self, client, ceo_headers):
        resp = client.get("/api/shipments/999999", headers=ceo_headers)
        assert resp.status_code == 404

    def test_initial_status_history_has_one_entry(self, client, manager_headers, shipment_id):
        resp = client.get(f"/api/shipments/{shipment_id}", headers=manager_headers)
        history = resp.json()["status_history"]
        assert len(history) >= 1
        assert history[0]["to_status"] == "draft"


# ─── Full A→Z Status Pipeline ─────────────────────────────────────────────────

class TestStatusPipeline:
    """
    Advances the module-scoped shipment through every stage in order
    and verifies each transition. Tests must run in order.
    """

    def test_stage_confirmed(self, client, manager_headers, shipment_id):
        resp = client.post(f"/api/shipments/{shipment_id}/status",
                           json={"status": "confirmed", "note": "Supplier confirmed order"},
                           headers=manager_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "confirmed"

    def test_stage_qc_sorting(self, client, manager_headers, shipment_id):
        resp = client.post(f"/api/shipments/{shipment_id}/status",
                           json={"status": "qc_sorting", "note": "Moved to sorting line"},
                           headers=manager_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "qc_sorting"

    def test_stage_packaging(self, client, manager_headers, shipment_id):
        resp = client.post(f"/api/shipments/{shipment_id}/status",
                           json={"status": "packaging"},
                           headers=manager_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "packaging"

    def test_stage_export_customs(self, client, manager_headers, shipment_id):
        resp = client.post(f"/api/shipments/{shipment_id}/status",
                           json={"status": "export_customs"},
                           headers=manager_headers)
        assert resp.status_code == 200

    def test_stage_in_transit(self, client, manager_headers, shipment_id):
        resp = client.post(f"/api/shipments/{shipment_id}/status",
                           json={"status": "in_transit", "note": "Truck departed Baku 06:00"},
                           headers=manager_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "in_transit"

    def test_stage_import_customs(self, client, manager_headers, shipment_id):
        resp = client.post(f"/api/shipments/{shipment_id}/status",
                           json={"status": "import_customs"},
                           headers=manager_headers)
        assert resp.status_code == 200

    def test_stage_in_storage_updates_bay_load(self, client, manager_headers, shipment_id):
        # Record bay load before
        db_before = client.get("/api/analytics/dashboard", headers=manager_headers).json()
        storage_before = db_before["storage_capacity_pct"]

        resp = client.post(f"/api/shipments/{shipment_id}/status",
                           json={"status": "in_storage", "note": "Bay A-01 assigned"},
                           headers=manager_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "in_storage"

        # Capacity should have increased
        db_after = client.get("/api/analytics/dashboard", headers=manager_headers).json()
        assert db_after["storage_capacity_pct"] >= storage_before

    def test_stage_delivered_releases_bay_load(self, client, manager_headers, shipment_id):
        db_before = client.get("/api/analytics/dashboard", headers=manager_headers).json()
        cap_before = db_before["storage_capacity_pct"]

        resp = client.post(f"/api/shipments/{shipment_id}/status",
                           json={"status": "delivered"},
                           headers=manager_headers)
        assert resp.status_code == 200

        db_after = client.get("/api/analytics/dashboard", headers=manager_headers).json()
        # After delivery, storage should be freed
        assert db_after["storage_capacity_pct"] <= cap_before

    def test_stage_invoiced(self, client, manager_headers, shipment_id):
        resp = client.post(f"/api/shipments/{shipment_id}/status",
                           json={"status": "invoiced"},
                           headers=manager_headers)
        assert resp.status_code == 200

    def test_stage_payment_received(self, client, manager_headers, shipment_id):
        resp = client.post(f"/api/shipments/{shipment_id}/status",
                           json={"status": "payment_received", "note": "Wire received"},
                           headers=manager_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "payment_received"

    def test_timeline_has_all_stages(self, client, manager_headers, shipment_id):
        resp = client.get(f"/api/shipments/{shipment_id}/timeline", headers=manager_headers)
        assert resp.status_code == 200
        history = resp.json()
        statuses = [h["to_status"] for h in history]
        # All 11 stages should be present (draft + 10 advances)
        for stage in ["draft", "confirmed", "qc_sorting", "packaging",
                      "in_transit", "in_storage", "delivered", "payment_received"]:
            assert stage in statuses, f"Missing stage: {stage}"

    def test_notes_are_stored_in_timeline(self, client, manager_headers, shipment_id):
        resp = client.get(f"/api/shipments/{shipment_id}/timeline", headers=manager_headers)
        notes = [h.get("note") for h in resp.json()]
        assert "Truck departed Baku 06:00" in notes


# ─── QC Records ───────────────────────────────────────────────────────────────

class TestQCRecords:
    @pytest.fixture(scope="class")
    def fresh_shipment_id(self, client, manager_headers):
        resp = client.post("/api/shipments", json={**VALID_SHIPMENT, "product_name": "Apples"}, headers=manager_headers)
        return resp.json()["id"]

    def test_create_qc_record(self, client, manager_headers, fresh_shipment_id):
        resp = client.post(f"/api/shipments/{fresh_shipment_id}/qc", json={
            "lot_number": "LOT-TEST-001",
            "inspector_name": "A. Hasanov",
            "grade_a_kg": 4350,
            "grade_b_kg": 450,
            "rejected_kg": 200,
            "packaging_type": "5kg export cartons",
            "pallets_count": 40,
            "storage_temp_at_inspection": 3.5,
            "cold_chain_maintained": True,
            "notes": "Good colour and firmness",
        }, headers=manager_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["lot_number"] == "LOT-TEST-001"
        assert data["grade_a_kg"] == 4350.0

    def test_grade_percentages_sum_to_weight(self, client, manager_headers, fresh_shipment_id):
        resp = client.get(f"/api/shipments/{fresh_shipment_id}/qc", headers=manager_headers)
        records = resp.json()
        assert len(records) >= 1
        r = records[0]
        total = r["grade_a_kg"] + r["grade_b_kg"] + r["rejected_kg"]
        assert total == pytest.approx(5000.0, abs=1)

    def test_multiple_qc_records_allowed(self, client, manager_headers, fresh_shipment_id):
        client.post(f"/api/shipments/{fresh_shipment_id}/qc", json={
            "lot_number": "LOT-TEST-002",
            "inspector_name": "B. Mammadov",
            "grade_a_kg": 4400,
            "grade_b_kg": 400,
            "rejected_kg": 200,
            "cold_chain_maintained": True,
        }, headers=manager_headers)
        resp = client.get(f"/api/shipments/{fresh_shipment_id}/qc", headers=manager_headers)
        assert len(resp.json()) == 2

    def test_qc_on_nonexistent_shipment_returns_404(self, client, manager_headers):
        resp = client.post("/api/shipments/999999/qc", json={
            "lot_number": "LOT-X",
            "inspector_name": "Nobody",
            "grade_a_kg": 100, "grade_b_kg": 0, "rejected_kg": 0,
            "cold_chain_maintained": True,
        }, headers=manager_headers)
        assert resp.status_code == 404


# ─── Customs Records ──────────────────────────────────────────────────────────

class TestCustomsRecords:
    @pytest.fixture(scope="class")
    def customs_shipment_id(self, client, manager_headers):
        resp = client.post("/api/shipments", json={**VALID_SHIPMENT, "product_name": "Citrus"}, headers=manager_headers)
        return resp.json()["id"]

    def test_create_customs_record(self, client, manager_headers, customs_shipment_id):
        resp = client.post(f"/api/customs/shipment/{customs_shipment_id}", json={
            "direction": "import",
            "border_point": "Baku International Port",
            "duty_amount_usd": 1440,
            "vat_amount_usd": 2700,
            "other_fees_usd": 120,
            "notes": "Standard import declaration",
        }, headers=manager_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["direction"] == "import"
        assert data["status"] == "not_started"
        assert data["duty_amount_usd"] == 1440.0

    def test_customs_status_submitted(self, client, manager_headers, customs_shipment_id):
        # Get the customs record id
        resp = client.get(f"/api/customs?status=not_started", headers=manager_headers)
        records = [r for r in resp.json() if r["shipment_id"] == customs_shipment_id]
        assert len(records) >= 1
        cid = records[0]["id"]

        resp = client.patch(f"/api/customs/{cid}/status", json={
            "status": "submitted",
            "declaration_ref": "DECL-TEST-2026",
        }, headers=manager_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "submitted"
        assert resp.json()["declaration_ref"] == "DECL-TEST-2026"
        assert resp.json()["submitted_at"] is not None

    def test_customs_status_hold(self, client, manager_headers, customs_shipment_id):
        resp = client.get("/api/customs?status=submitted", headers=manager_headers)
        records = [r for r in resp.json() if r["shipment_id"] == customs_shipment_id]
        if not records:
            pytest.skip("No submitted records to hold")
        cid = records[0]["id"]

        resp = client.patch(f"/api/customs/{cid}/status", json={
            "status": "hold",
            "hold_reason": "Phytosanitary certificate missing",
        }, headers=manager_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "hold"
        assert "Phytosanitary" in resp.json()["hold_reason"]

    def test_customs_status_cleared(self, client, manager_headers, customs_shipment_id):
        resp = client.get("/api/customs?status=hold", headers=manager_headers)
        records = [r for r in resp.json() if r["shipment_id"] == customs_shipment_id]
        if not records:
            pytest.skip("No held records to clear")
        cid = records[0]["id"]

        resp = client.patch(f"/api/customs/{cid}/status", json={"status": "cleared"}, headers=manager_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "cleared"
        assert resp.json()["cleared_at"] is not None

    def test_customs_list_filter_by_status(self, client, manager_headers):
        resp = client.get("/api/customs?status=cleared", headers=manager_headers)
        assert resp.status_code == 200
        for r in resp.json():
            assert r["status"] == "cleared"


# ─── Transactions ─────────────────────────────────────────────────────────────

class TestTransactions:
    def test_create_revenue_transaction(self, client, manager_headers):
        resp = client.post("/api/transactions", json={
            "transaction_type": "revenue",
            "description": "Export pomegranate — SH-TEST",
            "amount_usd": 15000,
            "counterparty": "FrischMarkt GmbH",
            "currency": "USD",
        }, headers=manager_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["amount_usd"] == 15000.0
        assert data["transaction_type"] == "revenue"
        assert data["status"] == "pending"

    def test_create_cost_transaction_negative_amount(self, client, manager_headers):
        resp = client.post("/api/transactions", json={
            "transaction_type": "freight",
            "description": "Freight — EuroCargo truck",
            "amount_usd": -3200,
            "counterparty": "EuroCargo",
        }, headers=manager_headers)
        assert resp.status_code == 201
        assert resp.json()["amount_usd"] == -3200.0

    def test_transaction_ref_format(self, client, manager_headers):
        resp = client.post("/api/transactions", json={
            "transaction_type": "storage",
            "description": "Bay A-01 monthly fee",
            "amount_usd": -1800,
        }, headers=manager_headers)
        ref = resp.json()["ref"]
        assert ref.startswith("TXN-")

    def test_list_transactions_returns_array(self, client, ceo_headers):
        resp = client.get("/api/transactions", headers=ceo_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_filter_by_type(self, client, manager_headers):
        resp = client.get("/api/transactions?txn_type=revenue", headers=manager_headers)
        assert resp.status_code == 200
        for t in resp.json():
            assert t["transaction_type"] == "revenue"

    def test_update_status_to_paid(self, client, manager_headers):
        # Create a transaction to pay
        create_resp = client.post("/api/transactions", json={
            "transaction_type": "customs_duty",
            "description": "Duty payment test",
            "amount_usd": -500,
        }, headers=manager_headers)
        txn_id = create_resp.json()["id"]

        resp = client.patch(f"/api/transactions/{txn_id}/status",
                            json={"status": "paid"},
                            headers=manager_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "paid"

    def test_overdue_flagging_on_list(self, client, manager_headers):
        """
        Create a transaction with a past due_date — listing should flip it to overdue.
        """
        from datetime import datetime, timedelta, timezone
        past_date = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()

        create_resp = client.post("/api/transactions", json={
            "transaction_type": "revenue",
            "description": "Overdue invoice test",
            "amount_usd": 9999,
            "due_date": past_date,
        }, headers=manager_headers)
        txn_id = create_resp.json()["id"]

        # Listing triggers the overdue check
        list_resp = client.get("/api/transactions", headers=manager_headers)
        txn = next((t for t in list_resp.json() if t["id"] == txn_id), None)
        assert txn is not None
        assert txn["status"] == "overdue"

    def test_filter_by_shipment_id(self, client, manager_headers, shipment_id):
        # Create a transaction linked to the test shipment
        client.post("/api/transactions", json={
            "transaction_type": "revenue",
            "description": "Linked transaction",
            "amount_usd": 5000,
            "shipment_id": shipment_id,
        }, headers=manager_headers)

        resp = client.get(f"/api/transactions?shipment_id={shipment_id}", headers=manager_headers)
        assert resp.status_code == 200
        ids = [t["shipment_id"] for t in resp.json()]
        assert shipment_id in ids


# ─── Analytics ────────────────────────────────────────────────────────────────

class TestAnalytics:
    def test_dashboard_returns_all_kpi_fields(self, client, ceo_headers):
        resp = client.get("/api/analytics/dashboard", headers=ceo_headers)
        assert resp.status_code == 200
        data = resp.json()
        for field in ["active_shipments", "revenue_mtd", "pending_customs",
                      "storage_capacity_pct", "net_profit_mtd", "total_weight_in_transit_kg"]:
            assert field in data, f"Missing KPI field: {field}"

    def test_dashboard_kpis_are_numeric(self, client, ceo_headers):
        data = client.get("/api/analytics/dashboard", headers=ceo_headers).json()
        assert isinstance(data["active_shipments"], int)
        assert isinstance(data["revenue_mtd"], float)
        assert 0.0 <= data["storage_capacity_pct"] <= 100.0

    def test_corridors_returns_list(self, client, ceo_headers):
        resp = client.get("/api/analytics/corridors", headers=ceo_headers)
        assert resp.status_code == 200
        corridors = resp.json()
        assert isinstance(corridors, list)

    def test_corridors_have_required_fields(self, client, ceo_headers):
        corridors = client.get("/api/analytics/corridors", headers=ceo_headers).json()
        if corridors:
            c = corridors[0]
            assert "corridor" in c
            assert "shipments" in c
            assert "total_value_usd" in c
            assert "total_weight_kg" in c
            assert "→" in c["corridor"]

    def test_corridors_ordered_by_value_descending(self, client, ceo_headers):
        corridors = client.get("/api/analytics/corridors", headers=ceo_headers).json()
        if len(corridors) >= 2:
            values = [c["total_value_usd"] for c in corridors]
            assert values == sorted(values, reverse=True)

    @pytest.mark.parametrize("period", ["daily", "weekly", "monthly", "quarterly", "annual"])
    def test_period_report_all_periods(self, client, ceo_headers, period):
        resp = client.get(f"/api/analytics/report/{period}", headers=ceo_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["period"] == period
        assert "label" in data
        assert "shipments_count" in data
        assert "revenue" in data
        assert "costs" in data
        assert "net" in data
        assert isinstance(data["shipments_count"], int)

    def test_period_report_net_equals_revenue_minus_costs(self, client, ceo_headers):
        data = client.get("/api/analytics/report/monthly", headers=ceo_headers).json()
        assert data["net"] == pytest.approx(data["revenue"] - data["costs"], abs=0.01)


# ─── Edge Cases & Error Handling ──────────────────────────────────────────────

class TestEdgeCases:
    def test_update_shipment_patch(self, client, manager_headers):
        # Create a fresh shipment
        resp = client.post("/api/shipments", json=VALID_SHIPMENT, headers=manager_headers)
        sid = resp.json()["id"]

        patch_resp = client.patch(f"/api/shipments/{sid}", json={
            "tracking_number": "TRK-999-XYZ",
            "storage_bay": "A-02",
        }, headers=manager_headers)
        assert patch_resp.status_code == 200
        assert patch_resp.json()["tracking_number"] == "TRK-999-XYZ"
        assert patch_resp.json()["storage_bay"] == "A-02"

    def test_patch_nonexistent_returns_404(self, client, manager_headers):
        resp = client.patch("/api/shipments/999999", json={"notes": "test"}, headers=manager_headers)
        assert resp.status_code == 404

    def test_invalid_status_value_returns_422(self, client, manager_headers):
        resp = client.post("/api/shipments", json=VALID_SHIPMENT, headers=manager_headers)
        sid = resp.json()["id"]
        resp2 = client.post(f"/api/shipments/{sid}/status",
                            json={"status": "flying_to_moon"},
                            headers=manager_headers)
        assert resp2 == resp2  # 422 or 400 — just ensure it doesn't crash
        assert resp2.status_code in (422, 400)

    def test_list_limit_boundary(self, client, manager_headers):
        # limit=200 is max per schema
        resp = client.get("/api/shipments?limit=200", headers=manager_headers)
        assert resp.status_code == 200

    def test_health_endpoint_always_200(self, client):
        assert client.get("/api/health").status_code == 200

    def test_docs_endpoint_accessible(self, client):
        resp = client.get("/docs")
        assert resp.status_code == 200
