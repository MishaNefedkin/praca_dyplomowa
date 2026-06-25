import os
from time import monotonic
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import create_access_token, get_current_user, hash_password, require_roles, verify_password
from ..database import get_db
from ..services.audit import record_audit_log

router = APIRouter(prefix="/auth", tags=["auth"])
LOGIN_RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("LOGIN_RATE_LIMIT_WINDOW_SECONDS", "300"))
LOGIN_RATE_LIMIT_MAX_FAILURES = int(os.getenv("LOGIN_RATE_LIMIT_MAX_FAILURES", "5"))
failed_login_attempts: dict[str, list[float]] = {}


def login_rate_limit_key(request: Request, login: str) -> str:
    client_host = request.client.host if request.client else "unknown"
    return f"{client_host}:{login.lower()}"


def check_login_rate_limit(request: Request, login: str) -> None:
    now = monotonic()
    key = login_rate_limit_key(request, login)
    recent_failures = [
        attempt for attempt in failed_login_attempts.get(key, []) if now - attempt < LOGIN_RATE_LIMIT_WINDOW_SECONDS
    ]
    failed_login_attempts[key] = recent_failures
    if len(recent_failures) >= LOGIN_RATE_LIMIT_MAX_FAILURES:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed login attempts. Try again later.",
        )


def register_failed_login(request: Request, login: str) -> None:
    key = login_rate_limit_key(request, login)
    failed_login_attempts.setdefault(key, []).append(monotonic())


def clear_failed_logins(request: Request, login: str) -> None:
    failed_login_attempts.pop(login_rate_limit_key(request, login), None)


@router.post("/login", response_model=schemas.Token)
def login(payload: schemas.LoginRequest, request: Request, db: Annotated[Session, Depends(get_db)]) -> schemas.Token:
    check_login_rate_limit(request, payload.login)
    user = db.query(models.User).filter(models.User.login == payload.login).first()
    if not user or not verify_password(payload.password, user.password_hash):
        register_failed_login(request, payload.login)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid login or password")
    clear_failed_logins(request, payload.login)
    return schemas.Token(access_token=create_access_token(user.login, user.role))


@router.get("/me", response_model=schemas.UserRead)
def me(user: Annotated[models.User, Depends(get_current_user)]) -> models.User:
    return user


@router.get("/users", response_model=list[schemas.UserRead])
def list_users(
    db: Annotated[Session, Depends(get_db)],
    _actor: Annotated[models.User, Depends(require_roles("admin"))],
) -> list[models.User]:
    return db.query(models.User).order_by(models.User.created_at.desc()).all()


@router.post("/users", response_model=schemas.UserRead)
def create_user(
    payload: schemas.UserCreate,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[models.User, Depends(require_roles("admin"))],
) -> models.User:
    if db.query(models.User).filter(models.User.login == payload.login).first():
        raise HTTPException(status_code=409, detail="User already exists")
    user = models.User(login=payload.login, password_hash=hash_password(payload.password), role=payload.role)
    db.add(user)
    db.flush()
    record_audit_log(
        db,
        actor,
        action="user.create",
        entity_type="user",
        entity_id=user.id,
        details={"login": user.login, "role": user.role},
    )
    db.commit()
    db.refresh(user)
    return user


@router.put("/users/{user_id}", response_model=schemas.UserRead)
def update_user(
    user_id: int,
    payload: schemas.UserUpdate,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[models.User, Depends(require_roles("admin"))],
) -> models.User:
    user = db.get(models.User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    changes = payload.model_dump(exclude_unset=True, exclude_none=True)
    if "role" in changes and changes["role"] != user.role and user.role == "admin" and changes["role"] != "admin":
        admin_count = db.query(models.User).filter(models.User.role == "admin").count()
        if admin_count <= 1:
            raise HTTPException(status_code=400, detail="Cannot remove the last admin")

    if "password" in changes:
        user.password_hash = hash_password(changes["password"])
    if "role" in changes:
        user.role = changes["role"]

    record_audit_log(
        db,
        actor,
        action="user.update",
        entity_type="user",
        entity_id=user.id,
        details={"login": user.login, "fields": sorted(changes.keys())},
    )
    db.commit()
    db.refresh(user)
    return user


@router.delete("/users/{user_id}", response_model=schemas.UserRead)
def delete_user(
    user_id: int,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[models.User, Depends(require_roles("admin"))],
) -> schemas.UserRead:
    user = db.get(models.User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == actor.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    if user.role == "admin":
        admin_count = db.query(models.User).filter(models.User.role == "admin").count()
        if admin_count <= 1:
            raise HTTPException(status_code=400, detail="Cannot delete the last admin")

    deleted_user = schemas.UserRead.model_validate(user)
    record_audit_log(
        db,
        actor,
        action="user.delete",
        entity_type="user",
        entity_id=user.id,
        details={"login": user.login, "role": user.role},
    )
    db.query(models.AuditLog).filter(models.AuditLog.actor_user_id == user.id).update(
        {"actor_user_id": None},
        synchronize_session=False,
    )
    db.delete(user)
    db.commit()
    return deleted_user
