from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import create_access_token, get_current_user, hash_password, require_roles, verify_password
from ..database import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=schemas.Token)
def login(payload: schemas.LoginRequest, db: Annotated[Session, Depends(get_db)]) -> schemas.Token:
    user = db.query(models.User).filter(models.User.login == payload.login).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid login or password")
    return schemas.Token(access_token=create_access_token(user.login, user.role))


@router.get("/me", response_model=schemas.UserRead)
def me(user: Annotated[models.User, Depends(get_current_user)]) -> models.User:
    return user


@router.post("/users", response_model=schemas.UserRead)
def create_user(
    payload: schemas.UserCreate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[models.User, Depends(require_roles("admin"))],
) -> models.User:
    if db.query(models.User).filter(models.User.login == payload.login).first():
        raise HTTPException(status_code=409, detail="User already exists")
    user = models.User(login=payload.login, password_hash=hash_password(payload.password), role=payload.role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
