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
    return f"{route.tags[0]}-{route.name}"


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

# Allow any host for WebSocket connections - critical for Render.com
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])

# Include all routes via the api_router
app.include_router(api_router, prefix=settings.API_V1_STR)
# Add the config router separately since it's not in api_router
app.include_router(config_router.router, prefix=settings.API_V1_STR)

# Remove redundant router registrations
# These are already included via api_router above

# Health check endpoint (non-prefixed for kubernetes/monitoring access)
@app.get("/health", tags=["health"])
def health_check():
    return {"status": "ok"}

# Add a WebSocket health check endpoint to verify WebSocket functionality
@app.websocket("/ws-health")
async def websocket_health_check(websocket):
    # Always accept the connection first - critical for Render.com
    await websocket.accept()
    
    try:
        # Send a welcome message
        await websocket.send_json({
            "status": "ok", 
            "message": "WebSocket connection established",
            "environment": str(settings.ENVIRONMENT)
        })
        
        # Wait for an optional message from the client
        try:
            data = await asyncio.wait_for(websocket.receive_text(), timeout=5.0)
            await websocket.send_json({
                "status": "echo",
                "message": f"Echoed: {data}"
            })
        except Exception:
            # Timeout or other error is fine here, just proceed to close
            pass
            
        # Gracefully close
        await websocket.close()
    except Exception as e:
        print(f"WebSocket health check error: {e}")
        try:
            await websocket.close(code=1011, reason=str(e))
        except:
            pass

# Also add the health endpoint at the API prefix
@app.websocket(f"{settings.API_V1_STR}/ws-health")
async def websocket_health_check_api(websocket):
    # Always accept the connection first - critical for Render.com
    await websocket.accept()
    
    try:
        # Send a welcome message with API prefix
        await websocket.send_json({
            "status": "ok", 
            "message": "WebSocket connection established via API prefix",
            "environment": str(settings.ENVIRONMENT)
        })
        await websocket.close()
    except Exception as e:
        print(f"API WebSocket health check error: {e}")
        try:
            await websocket.close(code=1011, reason=str(e))
        except:
            pass
