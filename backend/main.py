"""
main.py — FastAPI application entry point for AI-Studio.
"""
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.config import get_settings
from backend.utils.logger import configure_logging, get_logger
from backend.routes import generate, jobs, health, analyse
from backend.services.job_store import job_store

# ── Boot ─────────────────────────────────────────────────────────────────────

configure_logging()
logger = get_logger("ai_studio.main")
settings = get_settings()


async def _ttl_cleanup_loop() -> None:
    """Background task: purge jobs older than 24h every hour."""
    while True:
        await asyncio.sleep(3600)  # wait first, then purge
        try:
            purged = await job_store.purge_expired(ttl_hours=24)
            if purged:
                logger.info("ttl_cleanup_complete", purged=purged)
        except Exception as exc:
            logger.error("ttl_cleanup_error", error=str(exc))


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "startup",
        app="AI-Studio",
        fal_model=settings.fal_image_model,
        replicate_model=settings.replicate_video_model,
        groq_model=settings.groq_model,
        # NEVER log key values — only confirm they are set
        fal_key_set=bool(settings.fal_key),
        replicate_key_set=bool(settings.replicate_api_token),
        groq_key_set=bool(settings.groq_api_key),
    )
    cleanup_task = asyncio.create_task(_ttl_cleanup_loop())
    try:
        yield
    finally:
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass
    logger.info("shutdown", app="AI-Studio")


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="AI-Studio",
    description="AI-powered image and video generation — internal POC",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ──────────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Global exception handler — never expose raw stack traces ──────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(
        "unhandled_exception",
        path=request.url.path,
        method=request.method,
        error_type=type(exc).__name__,
        error=str(exc),
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_error",
            "message": "An unexpected error occurred. Please try again.",
        },
    )

# ── Routers ───────────────────────────────────────────────────────────────────

app.include_router(generate.router)
app.include_router(jobs.router)
app.include_router(health.router)
app.include_router(analyse.router)


@app.get("/", tags=["root"])
async def root():
    return {"service": "AI-Studio", "version": "0.1.0", "docs": "/docs"}
