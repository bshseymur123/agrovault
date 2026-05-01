"""
Shared pytest fixtures — uses SQLite shared-cache in-memory DB.
The key: all sessions share ONE connection so tables persist across threads.
"""
import sys, os

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SECRET_KEY"]   = "test-secret-key-32-chars-long!!!"

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

# ── Single shared connection ──────────────────────────────────────────────────
# SQLite :memory: creates a NEW db per connection.
# By reusing ONE connection for everything, tables persist across sessions.
CONNECT_ARGS = {"check_same_thread": False}
TEST_ENGINE = create_engine("sqlite://", connect_args=CONNECT_ARGS)

# Keep one connection alive for the whole test session
_connection = TEST_ENGINE.connect()

# Patch SessionLocal to always use this connection
from sqlalchemy.orm import Session as _Session
TestSessionLocal = sessionmaker(bind=_connection)

import db.session as _db
_db.engine = TEST_ENGINE
_db.SessionLocal = TestSessionLocal

from db.session import Base, get_db
from main import app
from models.models import User, StorageBay, UserRole
from core.security import hash_password

# Create all tables on the shared connection
Base.metadata.create_all(bind=_connection)

# ── Override get_db to use the shared connection ──────────────────────────────
def override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

# ── Seed data once ────────────────────────────────────────────────────────────
def _seed():
    db = TestSessionLocal()
    if db.query(User).count() == 0:
        for u in [
            User(email="ceo@test.com",       full_name="Test CEO",        hashed_password=hash_password("pass123"), role=UserRole.ceo),
            User(email="manager@test.com",    full_name="Test Manager",    hashed_password=hash_password("pass123"), role=UserRole.manager),
            User(email="accountant@test.com", full_name="Test Accountant", hashed_password=hash_password("pass123"), role=UserRole.accountant),
            User(email="operator@test.com",   full_name="Test Operator",   hashed_password=hash_password("pass123"), role=UserRole.operator),
        ]:
            db.add(u)
        for b in [
            StorageBay(bay_code="A-01", bay_name="Cold Bay 1", bay_type="cold",    temp_min_c=0,  temp_max_c=4,  capacity_kg=50000),
            StorageBay(bay_code="A-02", bay_name="Cold Bay 2", bay_type="cold",    temp_min_c=0,  temp_max_c=4,  capacity_kg=50000),
            StorageBay(bay_code="B-01", bay_name="Ambient 1",  bay_type="ambient", temp_min_c=15, temp_max_c=22, capacity_kg=30000),
        ]:
            db.add(b)
        db.commit()
    db.close()

_seed()

# ── Fixtures ──────────────────────────────────────────────────────────────────
@pytest.fixture(scope="session")
def client():
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c

def _get_token(client, email, password="pass123"):
    resp = client.post("/api/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, f"Login failed for {email}: {resp.json()}"
    return resp.json()["access_token"]

@pytest.fixture(scope="session")
def ceo_token(client):     return _get_token(client, "ceo@test.com")
@pytest.fixture(scope="session")
def manager_token(client): return _get_token(client, "manager@test.com")
@pytest.fixture(scope="session")
def operator_token(client): return _get_token(client, "operator@test.com")

@pytest.fixture(scope="session")
def ceo_headers(ceo_token):     return {"Authorization": f"Bearer {ceo_token}"}
@pytest.fixture(scope="session")
def manager_headers(manager_token): return {"Authorization": f"Bearer {manager_token}"}
@pytest.fixture(scope="session")
def operator_headers(operator_token): return {"Authorization": f"Bearer {operator_token}"}
