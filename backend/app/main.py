import sentry_sdk
import asyncio
from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.main import api_router
from app.core.config import settings
# Remove redundant imports since they're already included in api_router
from app.api.routes import config as config_router


def custom_generate_unique_id(route: APIRoute) -> str:
    # Handle routes without tags by using 'root' as fallback tag
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
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Add TrustedHostMiddleware
app.add_middleware(
    TrustedHostMiddleware, allowed_hosts=["*"]
)

# Mount the API router with the correct prefix (crucial for compatibility with frontend)
app.include_router(api_router, prefix=settings.API_V1_STR)

# Add a basic health check for the root path
@app.get("/")
def root():
    return {"message": "Welcome to Imacall API! Use /api/v1/ prefix for all endpoints."}

# WebSocket health check endpoint
@app.websocket("/ws-health")
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
