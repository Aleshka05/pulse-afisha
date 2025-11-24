from fastapi import APIRouter

from app.api.routes import auth, users, categories, events, admin_events

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(categories.router)
api_router.include_router(events.router)
api_router.include_router(admin_events.router)
