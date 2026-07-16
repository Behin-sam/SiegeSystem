"""
Application entrypoint. Wires together settings, logging, middleware,
exception handlers, the versioned API router, and the database seed.

Run with: uvicorn app.main:app --reload
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.middleware.logging_middleware import RequestLoggingMiddleware

configure_logging()
logger = get_logger("apmisn.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("application_startup", app_name=settings.APP_NAME, env=settings.APP_ENV)
    # Run database seeding on startup
    try:
        from app.db.seed import seed_roles_permissions, seed_super_admin
        from app.db.session import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            await seed_roles_permissions(db)
            await seed_super_admin(db)
    except Exception as e:
        logger.error("seed_failed", error=str(e))
    yield
    logger.info("application_shutdown")


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="Auth, RBAC, and Federated Identity backend for the Autonomous Multi-Region Payment & Identity Settlement Network.",
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    docs_url=f"{settings.API_V1_PREFIX}/docs",
    redoc_url=f"{settings.API_V1_PREFIX}/redoc",
    lifespan=lifespan,
)

# ---- Middleware (order matters: outermost registered last is outermost executed) ----
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestLoggingMiddleware)

# ---- Exception handlers ----
register_exception_handlers(app)

# ---- Routers ----
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/", tags=["Root"], summary="Service info")
async def root() -> dict:
    return {
        "service": settings.APP_NAME,
        "status": "online",
        "docs": f"{settings.API_V1_PREFIX}/docs",
    }
