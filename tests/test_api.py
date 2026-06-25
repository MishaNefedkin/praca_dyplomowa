import os
import tempfile
from pathlib import Path

os.environ["DATABASE_URL"] = f"sqlite:///{Path(tempfile.gettempdir()) / f'construction_crm_test_{os.getpid()}.db'}"
os.environ["ADMIN_LOGIN"] = "admin"
os.environ["ADMIN_PASSWORD"] = "admin12345"
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["SEED_SAMPLE_DATA"] = "false"

from fastapi.testclient import TestClient  # noqa: E402

from backend.app.database import Base, engine  # noqa: E402
from backend.app.main import app  # noqa: E402


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
