"""
Authentication tests.

Covers:
  - Successful login returns token + user object
  - Login with wrong password returns 401
  - Login with unknown email returns 401
  - /me returns correct user when authenticated
  - /me returns 401 when no token provided
  - /me returns 401 when token is garbage
  - Register creates a new user
  - Register with duplicate email returns 409
  - Any protected endpoint without token returns 401
"""
import pytest


class TestLogin:
    def test_login_success_returns_token(self, client):
        resp = client.post("/api/auth/login", json={
            "email": "ceo@test.com",
            "password": "pass123",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert len(data["access_token"]) > 20

    def test_login_success_returns_user_object(self, client):
        resp = client.post("/api/auth/login", json={
            "email": "ceo@test.com",
            "password": "pass123",
        })
        user = resp.json()["user"]
        assert user["email"] == "ceo@test.com"
        assert user["role"] == "ceo"
        assert user["is_active"] is True
        assert "hashed_password" not in user

    def test_login_wrong_password_returns_401(self, client):
        resp = client.post("/api/auth/login", json={
            "email": "ceo@test.com",
            "password": "wrongpassword",
        })
        assert resp.status_code == 401
        assert "detail" in resp.json()

    def test_login_unknown_email_returns_401(self, client):
        resp = client.post("/api/auth/login", json={
            "email": "nobody@test.com",
            "password": "pass123",
        })
        assert resp.status_code == 401

    def test_login_missing_fields_returns_422(self, client):
        resp = client.post("/api/auth/login", json={"email": "ceo@test.com"})
        assert resp.status_code == 422

    def test_oauth_token_endpoint_also_works(self, client):
        resp = client.post("/api/auth/token", data={
            "username": "manager@test.com",
            "password": "pass123",
        })
        assert resp.status_code == 200
        assert "access_token" in resp.json()


class TestMe:
    def test_me_returns_own_profile(self, client, ceo_headers):
        resp = client.get("/api/auth/me", headers=ceo_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "ceo@test.com"
        assert data["role"] == "ceo"

    def test_me_without_token_returns_401(self, client):
        resp = client.get("/api/auth/me")
        assert resp.status_code == 401

    def test_me_with_garbage_token_returns_401(self, client):
        resp = client.get("/api/auth/me", headers={"Authorization": "Bearer notavalidtoken"})
        assert resp.status_code == 401

    def test_me_with_malformed_bearer_returns_401(self, client):
        resp = client.get("/api/auth/me", headers={"Authorization": "Token abc123"})
        assert resp.status_code == 401

    def test_operator_me_returns_correct_role(self, client, operator_headers):
        resp = client.get("/api/auth/me", headers=operator_headers)
        assert resp.status_code == 200
        assert resp.json()["role"] == "operator"


class TestRegister:
    def test_register_new_user(self, client, ceo_headers):
        resp = client.post("/api/auth/register", json={
            "email": "newuser@test.com",
            "full_name": "New User",
            "password": "secure123",
            "role": "operator",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["email"] == "newuser@test.com"
        assert data["role"] == "operator"
        assert "hashed_password" not in data

    def test_register_duplicate_email_returns_409(self, client):
        # First registration
        client.post("/api/auth/register", json={
            "email": "duplicate@test.com",
            "full_name": "First",
            "password": "pass123",
        })
        # Second registration with same email
        resp = client.post("/api/auth/register", json={
            "email": "duplicate@test.com",
            "full_name": "Second",
            "password": "pass456",
        })
        assert resp.status_code == 409

    def test_registered_user_can_login(self, client):
        client.post("/api/auth/register", json={
            "email": "logintest@test.com",
            "full_name": "Login Test",
            "password": "mypass999",
        })
        resp = client.post("/api/auth/login", json={
            "email": "logintest@test.com",
            "password": "mypass999",
        })
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    def test_register_invalid_email_returns_422(self, client):
        resp = client.post("/api/auth/register", json={
            "email": "notanemail",
            "full_name": "Bad Email",
            "password": "pass123",
        })
        assert resp.status_code == 422


class TestProtectedEndpoints:
    """Spot-check that every protected area requires a valid token."""

    def test_shipments_list_requires_auth(self, client):
        assert client.get("/api/shipments").status_code == 401

    def test_transactions_list_requires_auth(self, client):
        assert client.get("/api/transactions").status_code == 401

    def test_customs_list_requires_auth(self, client):
        assert client.get("/api/customs").status_code == 401

    def test_analytics_dashboard_requires_auth(self, client):
        assert client.get("/api/analytics/dashboard").status_code == 401

    def test_health_is_public(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
