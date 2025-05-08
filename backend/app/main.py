import sentry_sdk
from fastapi import FastAPI
from fastapi.routing import APIRoute
from starlette.middleware.cors import CORSMiddleware

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
