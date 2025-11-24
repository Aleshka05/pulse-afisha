from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.db.base import Base
from app.db.session import engine
from app.api.routes import admin_users
from app.api.routes import organizer_requests, admin_organizer_requests
from app.api.routes import (
    support_tickets,
    admin_support_tickets,
    # ...
)
from app.api.routes import favorites
from app.api.routes import rsvp 
# ВАЖНО: импортировать модели
import app.models  # noqa: F401


app = FastAPI(
    title=settings.project_name,
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.backend_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup() -> None:
    """Создаёт таблицы при старте (для учебного проекта)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Проверка доступности сервиса."""
    return {"status": "ok"}


app.include_router(api_router, prefix=settings.api_v1_prefix)
app.include_router(admin_users.router, prefix="/api/v1")
app.include_router(organizer_requests.router, prefix="/api/v1")
app.include_router(admin_organizer_requests.router, prefix="/api/v1")
app.include_router(support_tickets.router, prefix="/api/v1")
app.include_router(admin_support_tickets.router, prefix="/api/v1")
app.include_router(favorites.router, prefix="/api/v1")
app.include_router(rsvp.router, prefix="/api/v1")