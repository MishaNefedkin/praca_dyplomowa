from contextlib import asynccontextmanager
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .database import Base, SessionLocal, engine
from .routers import analytics, audit, auth, clients, consents, inquiries, offers, tracking
from .services.seed import seed_admin_user, seed_sample_data


def validate_runtime_settings() -> None:
    environment = os.getenv("APP_ENV", "development").lower()
    if environment not in {"production", "prod"}:
        return

    unsafe_values = {
        "SECRET_KEY": {"change-this-secret-in-production", "change-this-secret-before-production"},
        "ADMIN_PASSWORD": {"admin12345", "change-this-admin-password"},
    }
    for name, defaults in unsafe_values.items():
        value = os.getenv(name)
        if not value or value in defaults:
            raise RuntimeError(f"{name} must be set to a non-default value in production")


@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_runtime_settings()
    if os.getenv("AUTO_CREATE_TABLES", "true").lower() in {"1", "true", "yes"}:
        Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_admin_user(db)
        seed_sample_data(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title="Construction CRM Analytics API",
    description="System wspomagający zarządzanie i analizę aktywności klientów firmy budowlanej.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip()
        for origin in os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000").split(",")
        if origin.strip()
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers.setdefault("Content-Security-Policy", "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    return response

app.include_router(auth.router)
app.include_router(clients.router)
app.include_router(inquiries.router)
app.include_router(offers.router)
app.include_router(tracking.router)
app.include_router(analytics.router)
app.include_router(consents.router)
app.include_router(audit.router)

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/admin", include_in_schema=False)
def admin() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "admin.html")


@app.get("/services/{slug}", include_in_schema=False)
def service_page(slug: str) -> FileResponse:
    service_pages = {
        "homes": "homes.html",
        "multifamily": "multifamily.html",
        "renovation": "renovation.html",
        "commercial": "commercial.html",
    }
    filename = service_pages.get(slug)
    if filename is None:
        raise HTTPException(status_code=404, detail="Service page not found")
    return FileResponse(FRONTEND_DIR / "services" / filename)


@app.get("/projects/{slug}", include_in_schema=False)
def project_page(slug: str) -> FileResponse:
    project_pages = {
        "willa-panorama": "willa-panorama.html",
        "zielone-tarasy": "zielone-tarasy.html",
        "nowa-era": "nowa-era.html",
        "river-view": "river-view.html",
    }
    filename = project_pages.get(slug)
    if filename is None:
        raise HTTPException(status_code=404, detail="Project page not found")
    return FileResponse(FRONTEND_DIR / "projects" / filename)
