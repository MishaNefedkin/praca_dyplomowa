import os
import tempfile
from pathlib import Path

import pytest

os.environ["DATABASE_URL"] = f"sqlite:///{Path(tempfile.gettempdir()) / f'construction_crm_test_{os.getpid()}.db'}"
os.environ["ADMIN_LOGIN"] = "admin"
os.environ["ADMIN_PASSWORD"] = "admin12345"
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["SEED_SAMPLE_DATA"] = "false"
os.environ["LOGIN_RATE_LIMIT_MAX_FAILURES"] = "5"

from fastapi.testclient import TestClient  # noqa: E402

from backend.app.database import Base, engine  # noqa: E402
from backend.app.main import app, validate_runtime_settings  # noqa: E402
from backend.app.routers.auth import failed_login_attempts  # noqa: E402
from backend.app.routers.tracking import rate_limit_hits  # noqa: E402


@pytest.fixture(autouse=True)
def clean_test_state():
    Base.metadata.drop_all(bind=engine)
    failed_login_attempts.clear()
    rate_limit_hits.clear()
    yield
    Base.metadata.drop_all(bind=engine)
    failed_login_attempts.clear()
    rate_limit_hits.clear()


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


def create_client_record(client: TestClient, headers: dict[str, str], email: str = "api.client@example.com") -> dict:
    response = client.post(
        "/clients",
        headers=headers,
        json={"name": "API Client", "email": email, "phone": "+48 600 555 000"},
    )
    assert response.status_code == 200
    return response.json()


def create_inquiry_record(client: TestClient, headers: dict[str, str], client_id: int) -> dict:
    response = client.post(
        "/inquiries/admin",
        headers=headers,
        json={"client_id": client_id, "message": "Need a focused API test offer.", "status": "new"},
    )
    assert response.status_code == 200
    return response.json()


def create_offer_record(client: TestClient, headers: dict[str, str], inquiry_id: int) -> dict:
    response = client.post(
        "/offers",
        headers=headers,
        json={"inquiry_id": inquiry_id, "value": 4500, "status": "draft"},
    )
    assert response.status_code == 200
    return response.json()


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


def test_admin_assets_are_not_cached() -> None:
    with TestClient(app) as client:
        admin_response = client.get("/admin")
        script_response = client.get("/static/admin.js")

    assert admin_response.status_code == 200
    assert admin_response.headers["cache-control"] == "no-store"
    assert script_response.status_code == 200
    assert script_response.headers["cache-control"] == "no-store"


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


def test_public_inquiry_does_not_reassign_existing_client_session() -> None:
    original_session_id = "owned-session-001"
    attacker_session_id = "attacker-session-001"
    with TestClient(app) as client:
        original_inquiry = client.post(
            "/inquiries",
            json={
                "name": "Original Client",
                "email": "session.owner@example.com",
                "phone": "+48 600 100 100",
                "message": "Please prepare the first offer.",
                "session_id": original_session_id,
                "consent_granted": True,
                "consent_scope": "contact_and_analytics",
            },
        )
        assert original_inquiry.status_code == 200
        client_id = original_inquiry.json()["client_id"]

        attacker_log = client.post(
            "/tracking/event",
            json={
                "session_id": attacker_session_id,
                "page_url": "/",
                "event_type": "page_view",
                "event_data": {"source": "unknown"},
                "referrer": None,
                "time_on_page": 1,
            },
        )
        assert attacker_log.status_code == 200

        second_inquiry = client.post(
            "/inquiries",
            json={
                "name": "Changed Name",
                "email": "session.owner@example.com",
                "phone": "+48 699 999 999",
                "message": "Second inquiry with known email.",
                "session_id": attacker_session_id,
                "consent_granted": True,
                "consent_scope": "contact_and_analytics",
            },
        )
        assert second_inquiry.status_code == 200
        headers = auth_headers(client)
        client_response = client.get(f"/clients/{client_id}", headers=headers)
        logs_response = client.get("/tracking/logs", headers=headers)

    assert client_response.status_code == 200
    stored_client = client_response.json()
    assert stored_client["session_id"] == original_session_id
    assert stored_client["name"] == "Original Client"
    assert stored_client["phone"] == "+48 600 100 100"
    attacker_logs = [log for log in logs_response.json() if log["session_id"] == attacker_session_id]
    assert attacker_logs[0]["client_id"] is None


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


def test_public_inquiry_rejects_phone_without_enough_digits() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/inquiries",
            json={
                "name": "Short Phone",
                "email": "short.phone@example.com",
                "phone": "+()--",
                "message": "Please call me about construction.",
                "session_id": "short-phone-session",
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


def test_admin_can_list_users() -> None:
    with TestClient(app) as client:
        admin_headers = auth_headers(client)
        create_user_response = client.post(
            "/auth/users",
            headers=admin_headers,
            json={"login": "listed-sales", "password": "sales12345", "role": "sales"},
        )
        assert create_user_response.status_code == 200

        users_response = client.get("/auth/users", headers=admin_headers)

    assert users_response.status_code == 200
    logins = [user["login"] for user in users_response.json()]
    assert "admin" in logins
    assert "listed-sales" in logins


def test_admin_can_update_user_role_and_password() -> None:
    with TestClient(app) as client:
        admin_headers = auth_headers(client)
        create_user_response = client.post(
            "/auth/users",
            headers=admin_headers,
            json={"login": "editable-user", "password": "sales12345", "role": "sales"},
        )
        assert create_user_response.status_code == 200
        user_id = create_user_response.json()["id"]

        update_response = client.put(
            f"/auth/users/{user_id}",
            headers=admin_headers,
            json={"role": "manager", "password": "manager12345"},
        )
        login_response = client.post("/auth/login", json={"login": "editable-user", "password": "manager12345"})
        audit_response = client.get("/audit/logs", headers=admin_headers)

    assert update_response.status_code == 200
    assert update_response.json()["role"] == "manager"
    assert login_response.status_code == 200
    assert "user.update" in [entry["action"] for entry in audit_response.json()]


def test_user_delete_rejects_self_delete_and_non_admin_access() -> None:
    with TestClient(app) as client:
        admin_headers = auth_headers(client)
        sales_response = client.post(
            "/auth/users",
            headers=admin_headers,
            json={"login": "delete-sales", "password": "sales12345", "role": "sales"},
        )
        assert sales_response.status_code == 200
        sales_headers = login_headers(client, "delete-sales", "sales12345")

        users_response = client.get("/auth/users", headers=admin_headers)
        admin_id = next(user["id"] for user in users_response.json() if user["login"] == "admin")
        self_delete_response = client.delete(f"/auth/users/{admin_id}", headers=admin_headers)
        sales_delete_response = client.delete(f"/auth/users/{admin_id}", headers=sales_headers)

    assert self_delete_response.status_code == 400
    assert sales_delete_response.status_code == 403


def test_admin_can_delete_user_but_cannot_remove_last_admin_role() -> None:
    with TestClient(app) as client:
        admin_headers = auth_headers(client)
        sales_response = client.post(
            "/auth/users",
            headers=admin_headers,
            json={"login": "deleted-sales", "password": "sales12345", "role": "sales"},
        )
        assert sales_response.status_code == 200

        delete_response = client.delete(f"/auth/users/{sales_response.json()['id']}", headers=admin_headers)
        deleted_login_response = client.post("/auth/login", json={"login": "deleted-sales", "password": "sales12345"})
        users_response = client.get("/auth/users", headers=admin_headers)
        admin_id = next(user["id"] for user in users_response.json() if user["login"] == "admin")
        last_admin_update_response = client.put(
            f"/auth/users/{admin_id}",
            headers=admin_headers,
            json={"role": "manager"},
        )
        audit_response = client.get("/audit/logs", headers=admin_headers)

    assert delete_response.status_code == 200
    assert deleted_login_response.status_code == 401
    assert last_admin_update_response.status_code == 400
    assert "user.delete" in [entry["action"] for entry in audit_response.json()]


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
        tracking_response = client.post(
            "/tracking/event",
            json={
                "session_id": "privacy-session-001",
                "page_url": "/",
                "event_type": "page_view",
                "event_data": {"source": "privacy-test"},
                "referrer": None,
                "time_on_page": 4,
            },
        )
        assert tracking_response.status_code == 200

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
        exported_response = client.get(f"/clients/{client_id}/export", headers=headers)

    assert anonymize_response.status_code == 200
    anonymized = anonymize_response.json()
    assert anonymized["name"] == "Anonymized client"
    assert anonymized["email"] is None
    assert anonymized["phone"] is None
    assert anonymized["session_id"] is None
    assert consents_response.status_code == 200
    assert all(consent["active"] is False for consent in consents_response.json())
    assert exported_response.status_code == 200
    assert exported_response.json()["activity_logs"] == []


def test_client_update_rejects_duplicate_email() -> None:
    with TestClient(app) as client:
        headers = auth_headers(client)
        first_response = client.post(
            "/clients",
            headers=headers,
            json={"name": "First Duplicate", "email": "first.duplicate@example.com"},
        )
        second_response = client.post(
            "/clients",
            headers=headers,
            json={"name": "Second Duplicate", "email": "second.duplicate@example.com"},
        )
        assert first_response.status_code == 200
        assert second_response.status_code == 200

        update_response = client.put(
            f"/clients/{second_response.json()['id']}",
            headers=headers,
            json={"email": "first.duplicate@example.com"},
        )

    assert update_response.status_code == 409


def test_admin_can_delete_client_and_audit_action() -> None:
    with TestClient(app) as client:
        headers = auth_headers(client)
        client_record = create_client_record(client, headers, "delete.client@example.com")
        client_id = client_record["id"]
        inquiry_record = create_inquiry_record(client, headers, client_id)
        create_offer_record(client, headers, inquiry_record["id"])

        delete_response = client.delete(f"/clients/{client_id}", headers=headers)
        get_response = client.get(f"/clients/{client_id}", headers=headers)
        audit_response = client.get("/audit/logs", headers=headers)

    assert delete_response.status_code == 200
    assert delete_response.json()["id"] == client_id
    assert get_response.status_code == 404
    assert "client.delete" in [entry["action"] for entry in audit_response.json()]


def test_manager_cannot_delete_client() -> None:
    with TestClient(app) as client:
        admin_headers = auth_headers(client)
        create_user_response = client.post(
            "/auth/users",
            headers=admin_headers,
            json={"login": "client-delete-manager", "password": "manager123", "role": "manager"},
        )
        assert create_user_response.status_code == 200
        client_record = create_client_record(client, admin_headers, "manager.delete.client@example.com")
        manager_headers = login_headers(client, "client-delete-manager", "manager123")

        delete_response = client.delete(f"/clients/{client_record['id']}", headers=manager_headers)

    assert delete_response.status_code == 403


def test_inquiry_detail_and_delete_endpoints() -> None:
    with TestClient(app) as client:
        headers = auth_headers(client)
        client_record = create_client_record(client, headers, "inquiry.delete.client@example.com")
        inquiry_record = create_inquiry_record(client, headers, client_record["id"])
        inquiry_id = inquiry_record["id"]

        get_response = client.get(f"/inquiries/{inquiry_id}", headers=headers)
        delete_response = client.delete(f"/inquiries/{inquiry_id}", headers=headers)
        missing_response = client.get(f"/inquiries/{inquiry_id}", headers=headers)
        audit_response = client.get("/audit/logs", headers=headers)

    assert get_response.status_code == 200
    assert get_response.json()["id"] == inquiry_id
    assert delete_response.status_code == 200
    assert missing_response.status_code == 404
    assert "inquiry.delete" in [entry["action"] for entry in audit_response.json()]


def test_sales_cannot_delete_inquiry() -> None:
    with TestClient(app) as client:
        admin_headers = auth_headers(client)
        create_user_response = client.post(
            "/auth/users",
            headers=admin_headers,
            json={"login": "inquiry-delete-sales", "password": "sales12345", "role": "sales"},
        )
        assert create_user_response.status_code == 200
        client_record = create_client_record(client, admin_headers, "sales.delete.inquiry@example.com")
        inquiry_record = create_inquiry_record(client, admin_headers, client_record["id"])
        sales_headers = login_headers(client, "inquiry-delete-sales", "sales12345")

        delete_response = client.delete(f"/inquiries/{inquiry_record['id']}", headers=sales_headers)

    assert delete_response.status_code == 403


def test_offer_detail_and_delete_endpoints() -> None:
    with TestClient(app) as client:
        headers = auth_headers(client)
        client_record = create_client_record(client, headers, "offer.delete.client@example.com")
        inquiry_record = create_inquiry_record(client, headers, client_record["id"])
        offer_record = create_offer_record(client, headers, inquiry_record["id"])
        offer_id = offer_record["id"]

        get_response = client.get(f"/offers/{offer_id}", headers=headers)
        delete_response = client.delete(f"/offers/{offer_id}", headers=headers)
        missing_response = client.get(f"/offers/{offer_id}", headers=headers)
        audit_response = client.get("/audit/logs", headers=headers)

    assert get_response.status_code == 200
    assert get_response.json()["id"] == offer_id
    assert delete_response.status_code == 200
    assert missing_response.status_code == 404
    assert "offer.delete" in [entry["action"] for entry in audit_response.json()]


def test_sales_cannot_delete_offer() -> None:
    with TestClient(app) as client:
        admin_headers = auth_headers(client)
        create_user_response = client.post(
            "/auth/users",
            headers=admin_headers,
            json={"login": "offer-delete-sales", "password": "sales12345", "role": "sales"},
        )
        assert create_user_response.status_code == 200
        client_record = create_client_record(client, admin_headers, "sales.delete.offer@example.com")
        inquiry_record = create_inquiry_record(client, admin_headers, client_record["id"])
        offer_record = create_offer_record(client, admin_headers, inquiry_record["id"])
        sales_headers = login_headers(client, "offer-delete-sales", "sales12345")

        delete_response = client.delete(f"/offers/{offer_record['id']}", headers=sales_headers)

    assert delete_response.status_code == 403


def test_admin_can_update_consent_active_state_and_missing_consent_returns_404() -> None:
    with TestClient(app) as client:
        inquiry_response = client.post(
            "/inquiries",
            json={
                "name": "Consent Client",
                "email": "consent.client@example.com",
                "phone": "+48 604 000 000",
                "message": "Please store and later change my consent.",
                "session_id": "consent-session-001",
                "consent_granted": True,
                "consent_scope": "contact_and_analytics",
            },
        )
        assert inquiry_response.status_code == 200
        client_id = inquiry_response.json()["client_id"]
        headers = auth_headers(client)
        consents_response = client.get(f"/consents/client/{client_id}", headers=headers)
        assert consents_response.status_code == 200
        consent_id = consents_response.json()[0]["id"]

        update_response = client.put(f"/consents/{consent_id}", headers=headers, json={"active": False})
        missing_response = client.put("/consents/999999", headers=headers, json={"active": True})
        audit_response = client.get("/audit/logs", headers=headers)

    assert update_response.status_code == 200
    assert update_response.json()["active"] is False
    assert missing_response.status_code == 404
    assert "consent.update" in [entry["action"] for entry in audit_response.json()]


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
