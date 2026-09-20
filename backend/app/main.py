import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.app.core.config import settings
from backend.app.api.v1 import api_router
from backend.app.api.websockets import ws_router
from backend.app.services.alert_dispatcher import alert_dispatcher

logger = logging.getLogger("main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info("Starting up %s (Version %s)...", settings.PROJECT_NAME, settings.VERSION)
    settings.ensure_directories()

    # Register active asyncio event loop for thread-safe alert broadcasting
    try:
        loop = asyncio.get_running_loop()
        alert_dispatcher.set_event_loop(loop)
    except Exception as e:
        logger.warning("Could not set alert dispatcher event loop: %s", e)
    yield
    logger.info("Shutting down IBVAP backend...")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Backend API and Real-Time Video Analytics Gateway for Border Surveillance",
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# -----------------------------------------------------------------------------
# CORS Middleware
# -----------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------------------------------------------------------
# Static Media Mount (Serves local evidence images & uploads to frontend)
# -----------------------------------------------------------------------------
if settings.DATA_DIR.exists():
    app.mount("/data", StaticFiles(directory=str(settings.DATA_DIR)), name="data")

# -----------------------------------------------------------------------------
# API Routers & WebSocket Gateway
# -----------------------------------------------------------------------------
app.include_router(api_router, prefix=settings.API_V1_PREFIX)
app.include_router(ws_router, prefix="/ws", tags=["Real-Time WebSockets"])

@app.get("/", tags=["Health"])
def root():
    return {
        "status": "ONLINE",
        "system": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "database": "SQLite (WAL Mode)",
        "docs_url": "/docs",
    }

@app.get("/health", tags=["Health"])
def health():
    return {"status": "HEALTHY", "mode": "100% On-Premise Air-Gapped"}
