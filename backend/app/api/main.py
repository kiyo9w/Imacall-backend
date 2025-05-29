from fastapi import APIRouter

from app.api.routes import items, login, private, users, utils, characters, admin_characters, conversations, config, ws_debug
from app.core.config import settings

api_router = APIRouter()
api_router.include_router(login.router)
api_router.include_router(users.router)
api_router.include_router(utils.router)
api_router.include_router(items.router)
api_router.include_router(characters.router)
api_router.include_router(admin_characters.router)
api_router.include_router(conversations.router)
api_router.include_router(config.router)
# api_router.include_router(admin.router) # Commented out as this module doesn't exist
api_router.include_router(ws_debug.router)


if settings.ENVIRONMENT == "local":
    api_router.include_router(private.router)
