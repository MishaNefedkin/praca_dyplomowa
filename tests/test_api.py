import os
import tempfile
from pathlib import Path

os.environ["DATABASE_URL"] = f"sqlite:///{Path(tempfile.gettempdir()) / f'construction_crm_test_{os.getpid()}.db'}"
os.environ["ADMIN_LOGIN"] = "admin"
os.environ["ADMIN_PASSWORD"] = "admin12345"
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["SEED_SAMPLE_DATA"] = "false"
os.environ["LOGIN_RATE_LIMIT_MAX_FAILURES"] = "5"

from fastapi.testclient import TestClient  # noqa: E402

from backend.app.database import Base, engine  # noqa: E402
from backend.app.main import app, validate_runtime_settings  # noqa: E402


def setup_module() -> None:
    Base.metadata.drop_all(bind=engine)


def teardown_module() -> None:
    Base.metadata.drop_all(bind=engine)


def auth_headers(client: TestClient) -> dict[str, str]:
    response = client.post("/auth/login", json={"login": "admin", "password": "admin12345"})
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def login_headers(client: TestClient, login: str, password: str) -> dict[str, str]:
    response = client.post("/auth/login", json={"login": login, "password": password})
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_login_and_protected_endpoint() -> None:
    with TestClient(app) as client:
        unauthenticated = client.get("/clients")
        assert unauthenticated.status_code == 401

        headers = auth_headers(client)
        response = client.get("/clients", headers=headers)

    assert response.status_code == 200
    assert response.json() == []


def test_security_headers_are_set() -> None:
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]


def test_failed_login_attempts_are_rate_limited() -> None:
    with TestClient(app) as client:
        for _ in range(5):
            response = client.post("/auth/login", json={"login": "blocked-user", "password": "bad-password"})
            assert response.status_code == 401

        blocked_response = client.post("/auth/login", json={"login": "blocked-user", "password": "bad-password"})

    assert blocked_response.status_code == 429


def test_public_inquiry_links_existing_tracking_session_to_client() -> None:
    session_id = "test-session-123"
    with TestClient(app) as client:
        tracking_response = client.post(
            "/tracking/event",
            json={
                "session_id": session_id,
                "page_url": "/",
                "event_type": "page_view",
                "event_data": {"source": "pytest"},
                "referrer": None,
                "time_on_page": 3,
            },
        )
        assert tracking_response.status_code == 200
        assert tracking_response.json()["client_id"] is None

        inquiry_response = client.post(
            "/inquiries",
            json={
                "name": "Test Client",
                "email": "test.client@example.com",
                "phone": "+48 600 000 000",
                "message": "Please prepare a construction quote.",
                "session_id": session_id,
                "consent_granted": True,
                "consent_scope": "contact_and_analytics",
            },
        )
        assert inquiry_response.status_code == 200
        client_id = inquiry_response.json()["client_id"]

        headers = auth_headers(client)
        logs_response = client.get("/tracking/logs", headers=headers)

    assert logs_response.status_code == 200
    assert logs_response.json()[0]["client_id"] == client_id


def test_public_inquiry_rejects_phone_letters() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/inquiries",
            json={
                "name": "Letter Phone",
                "email": "letter.phone@example.com",
                "phone": "aaaooa",
                "message": "Please call me about construction.",
                "session_id": "letter-phone-session",
                "consent_granted": True,
                "consent_scope": "contact_and_analytics",
            },
        )

    assert response.status_code == 422


def test_admin_can_create_offer_and_update_inquiry_status() -> None:
    with TestClient(app) as client:
        headers = auth_headers(client)
        client_response = client.post(
            "/clients",
            headers=headers,
            json={"name": "Offer Client", "email": "offer.client@example.com", "phone": "+48 601 000 000"},
        )
        assert client_response.status_code == 200
        client_id = client_response.json()["id"]

        inquiry_response = client.post(
            "/inquiries/admin",
            headers=headers,
            json={"client_id": client_id, "message": "Admin-created inquiry", "status": "new"},
        )
        assert inquiry_response.status_code == 200
        inquiry_id = inquiry_response.json()["id"]

        offer_response = client.post(
            "/offers",
            headers=headers,
            json={"inquiry_id": inquiry_id, "value": 12000, "status": "sent"},
        )
        assert offer_response.status_code == 200

        inquiries_response = client.get("/inquiries?status=offer_sent", headers=headers)

    assert inquiries_response.status_code == 200
    assert any(inquiry["id"] == inquiry_id for inquiry in inquiries_response.json())


def test_admin_actions_are_written_to_audit_log() -> None:
    with TestClient(app) as client:
        headers = auth_headers(client)
        client_response = client.post(
            "/clients",
            headers=headers,
            json={"name": "Audit Client", "email": "audit.client@example.com"},
        )
        assert client_response.status_code == 200
        client_id = client_response.json()["id"]

        export_response = client.get(f"/clients/{client_id}/export", headers=headers)
        assert export_response.status_code == 200

        audit_response = client.get("/audit/logs", headers=headers)

    assert audit_response.status_code == 200
    actions = [entry["action"] for entry in audit_response.json()]
    assert "client.create" in actions
    assert "client.export" in actions


def test_audit_log_access_is_limited_by_role() -> None:
    with TestClient(app) as client:
        admin_headers = auth_headers(client)
        manager_response = client.post(
            "/auth/users",
            headers=admin_headers,
            json={"login": "audit-manager", "password": "manager123", "role": "manager"},
        )
        assert manager_response.status_code == 200
        sales_response = client.post(
            "/auth/users",
            headers=admin_headers,
            json={"login": "audit-sales", "password": "sales12345", "role": "sales"},
        )
        assert sales_response.status_code == 200

        manager_headers = login_headers(client, "audit-manager", "manager123")
        sales_headers = login_headers(client, "audit-sales", "sales12345")
        manager_audit_response = client.get("/audit/logs", headers=manager_headers)
        sales_audit_response = client.get("/audit/logs", headers=sales_headers)

    assert manager_audit_response.status_code == 200
    assert sales_audit_response.status_code == 403


def test_roles_limit_manager_write_access() -> None:
    with TestClient(app) as client:
        admin_headers = auth_headers(client)
        create_user_response = client.post(
            "/auth/users",
            headers=admin_headers,
            json={"login": "manager", "password": "manager123", "role": "manager"},
        )
        assert create_user_response.status_code == 200

        manager_headers = login_headers(client, "manager", "manager123")
        analytics_response = client.get("/analytics/kpi", headers=manager_headers)
        create_client_response = client.post(
            "/clients",
            headers=manager_headers,
            json={"name": "Blocked Client", "email": "blocked.client@example.com"},
        )

    assert analytics_response.status_code == 200
    assert create_client_response.status_code == 403


def test_sales_role_can_write_clients_but_cannot_access_analytics() -> None:
    with TestClient(app) as client:
        admin_headers = auth_headers(client)
        create_user_response = client.post(
            "/auth/users",
            headers=admin_headers,
            json={"login": "sales-user", "password": "sales12345", "role": "sales"},
        )
        assert create_user_response.status_code == 200

        sales_headers = login_headers(client, "sales-user", "sales12345")
        create_client_response = client.post(
            "/clients",
            headers=sales_headers,
            json={"name": "Sales Client", "email": "sales.client@example.com"},
        )
        analytics_response = client.get("/analytics/kpi", headers=sales_headers)
        logs_response = client.get("/tracking/logs", headers=sales_headers)

    assert create_client_response.status_code == 200
    assert analytics_response.status_code == 403
    assert logs_response.status_code == 403


def test_admin_anonymize_removes_personal_data_and_deactivates_consents() -> None:
    with TestClient(app) as client:
        inquiry_response = client.post(
            "/inquiries",
            json={
                "name": "Private Client",
                "email": "private.client@example.com",
                "phone": "+48 602 000 000",
                "message": "Please contact me about renovation.",
                "session_id": "privacy-session-001",
                "consent_granted": True,
                "consent_scope": "contact_and_analytics",
            },
        )
        assert inquiry_response.status_code == 200
        client_id = inquiry_response.json()["client_id"]

        headers = auth_headers(client)
        anonymize_response = client.delete(f"/clients/{client_id}/anonymize", headers=headers)
        consents_response = client.get(f"/consents/client/{client_id}", headers=headers)

    assert anonymize_response.status_code == 200
    anonymized = anonymize_response.json()
    assert anonymized["name"] == "Anonymized client"
    assert anonymized["email"] is None
    assert anonymized["phone"] is None
    assert consents_response.status_code == 200
    assert all(consent["active"] is False for consent in consents_response.json())


def test_admin_can_export_client_personal_data() -> None:
    session_id = "export-session-001"
    with TestClient(app) as client:
        tracking_response = client.post(
            "/tracking/event",
            json={
                "session_id": session_id,
                "page_url": "/",
                "event_type": "page_view",
                "event_data": {"source": "export-test"},
                "referrer": None,
                "time_on_page": 8,
            },
        )
        assert tracking_response.status_code == 200

        inquiry_response = client.post(
            "/inquiries",
            json={
                "name": "Export Client",
                "email": "export.client@example.com",
                "phone": "+48 603 000 000",
                "message": "Please export my CRM data.",
                "session_id": session_id,
                "consent_granted": True,
                "consent_scope": "contact_and_analytics",
            },
        )
        assert inquiry_response.status_code == 200
        client_id = inquiry_response.json()["client_id"]

        headers = auth_headers(client)
        export_response = client.get(f"/clients/{client_id}/export", headers=headers)

    assert export_response.status_code == 200
    exported = export_response.json()
    assert exported["client"]["email"] == "export.client@example.com"
    assert len(exported["consents"]) == 1
    assert len(exported["inquiries"]) == 1
    assert len(exported["activity_logs"]) == 1


def test_clients_support_search_and_pagination() -> None:
    with TestClient(app) as client:
        headers = auth_headers(client)
        for name, email in [
            ("Alpha Search", "alpha.search@example.com"),
            ("Beta Search", "beta.search@example.com"),
        ]:
            response = client.post("/clients", headers=headers, json={"name": name, "email": email})
            assert response.status_code == 200

        search_response = client.get("/clients?q=Alpha&limit=1&offset=0", headers=headers)

    assert search_response.status_code == 200
    assert len(search_response.json()) == 1
    assert search_response.json()[0]["email"] == "alpha.search@example.com"


def test_production_runtime_settings_reject_default_secret(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", "change-this-secret-before-production")
    monkeypatch.setenv("ADMIN_PASSWORD", "strong-admin-password")

    try:
        validate_runtime_settings()
    except RuntimeError as exc:
        assert "SECRET_KEY" in str(exc)
    else:
        raise AssertionError("Production runtime settings accepted a default SECRET_KEY")
