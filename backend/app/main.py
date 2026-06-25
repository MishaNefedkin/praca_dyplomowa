from contextlib import asynccontextmanager
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .database import Base, SessionLocal, engine
from .routers import analytics, auth, clients, consents, inquiries, offers, tracking
from .services.seed import seed_admin_user, seed_sample_data


@asynccontextmanager
async def lifespan(app: FastAPI):
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
