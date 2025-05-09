import sentry_sdk
import asyncio
from fastapi import FastAPI
from fastapi.routing import APIRoute
from starlette.middleware.cors import CORSMiddleware

from app.api.main import api_router
from app.core.config import settings
from app.api.routes import (login, users, utils, items, characters, 
                                conversations, admin_characters, ws_debug)
# Add the new config router
from app.api.routes import config as config_router


def custom_generate_unique_id(route: APIRoute) -> str:
    # Fix for IndexError - handle routes without tags
    tag = route.tags[0] if route.tags else "root"
    return f"{tag}-{route.name}"


if settings.SENTRY_DSN and settings.ENVIRONMENT != "local":
    sentry_sdk.init(dsn=str(settings.SENTRY_DSN), enable_tracing=True)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    generate_unique_id_function=custom_generate_unique_id,
)

# Set all CORS enabled origins
if settings.all_cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.all_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(api_router, prefix=settings.API_V1_STR)
# Add the new config router
app.include_router(config_router.router, prefix=settings.API_V1_STR)

app.include_router(login.router, tags=["login"])
app.include_router(users.router, prefix=settings.API_V1_STR, tags=["users"])
app.include_router(utils.router, prefix=settings.API_V1_STR, tags=["utils"])
app.include_router(items.router, prefix=settings.API_V1_STR, tags=["items"])
app.include_router(characters.router, prefix=settings.API_V1_STR, tags=["characters"])
app.include_router(conversations.router, prefix=settings.API_V1_STR, tags=["conversations"])
app.include_router(admin_characters.router, prefix=settings.API_V1_STR, tags=["admin-characters"])
app.include_router(ws_debug.router, prefix=settings.API_V1_STR, tags=["ws-debug"])

# Root endpoint for Railway health checks
@app.get("/")
def root():
    return {"message": "Welcome to Imacall API! Use /api/v1/ prefix for all endpoints."}

# Add simple endpoint handlers for /api and /api/v1 paths
@app.get("/api")
def api_root():
    return {"message": "API endpoint. Use /api/v1/ for the current API version."}

@app.get("/api/v1")
def api_v1_root():
    return {"message": "Imacall API v1 root endpoint"}

# Health check endpoint (optional, can be part of utils)
@app.get("/health", tags=["health"])
def health_check():
    return {"status": "ok"}

# WebSocket health check endpoint
@app.websocket("/api/v1/utils/ws-health")
async def websocket_health_endpoint(websocket):
    # Immediately accept the connection
    await websocket.accept()
    
    # Send a welcome message
    await websocket.send_json({
        "status": "ok",
        "message": "WebSocket server is healthy"
    })
    
    # Keep the connection open briefly then close it properly
    await asyncio.sleep(1)
    await websocket.close()
