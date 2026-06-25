import os

from sqlalchemy.orm import Session

from .. import models
from ..auth import hash_password


def seed_admin_user(db: Session) -> None:
    login = os.getenv("ADMIN_LOGIN", "admin")
    password = os.getenv("ADMIN_PASSWORD", "admin12345")
    user = db.query(models.User).filter(models.User.login == login).first()
    if user:
        return
    db.add(models.User(login=login, password_hash=hash_password(password), role="admin"))
    db.commit()


def seed_sample_data(db: Session) -> None:
    if os.getenv("SEED_SAMPLE_DATA", "true").lower() not in {"1", "true", "yes"}:
        return
    if db.query(models.Client).first():
        return

    client = models.Client(
        name="Jan Kowalski",
        email="jan.kowalski@example.com",
        phone="+48 500 100 200",
        session_id="sample-session-001",
    )
    db.add(client)
    db.flush()

    inquiry = models.Inquiry(client_id=client.id, message="Proszę o wycenę remontu mieszkania 60 m2.", status="new")
    db.add(inquiry)
    db.flush()

    db.add(models.Offer(inquiry_id=inquiry.id, value=24500, status="sent"))
    db.add(models.Consent(client_id=client.id, scope="contact_and_analytics", active=True))
    db.add(
        models.ActivityLog(
            session_id="sample-session-001",
            client_id=client.id,
            page_url="/",
            event_type="page_view",
            event_data={"source": "seed"},
            referrer="https://google.com",
            time_on_page=82,
        )
    )
    db.commit()
