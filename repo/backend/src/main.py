import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles

from .api.dependencies import require_role
from .api.errors import register_exception_handlers
from .api.middleware import AccessLogMiddleware, TraceIdMiddleware
from .api.routes import api_router
from .config import get_settings
from .domain.enums import UserRole
from .persistence.database import get_session_factory
from .schemas.common import SuccessResponse, make_success
from .telemetry.logging import configure_logging
from .telemetry.metrics import render_metrics
from .workers.auto_cancel import run_auto_cancel_loop
from .workers.bargaining_expiry import run_bargaining_expiry_loop
from .workers.cache_stats import run_cache_stats_loop
from .workers.forecasting import run_forecasting_loop
from .workers.refund_progression import run_refund_progression_loop
from .workers.stale_queue import run_stale_queue_loop

settings = get_settings()
configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    session_factory = get_session_factory()
    tasks = [
        asyncio.create_task(run_auto_cancel_loop(session_factory)),
        asyncio.create_task(run_bargaining_expiry_loop(session_factory)),
        asyncio.create_task(run_stale_queue_loop(session_factory)),
        asyncio.create_task(run_cache_stats_loop(session_factory)),
        asyncio.create_task(run_forecasting_loop(session_factory)),
        asyncio.create_task(run_refund_progression_loop(session_factory)),
    ]
    yield
    for t in tasks:
        t.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)


app = FastAPI(
    title="MeritTrack",
    description="Admissions & Transaction Operations Platform",
    version="0.1.0",
    docs_url="/api/docs" if settings.environment == "development" else None,
    redoc_url="/api/redoc" if settings.environment == "development" else None,
    lifespan=lifespan,
)

# Middleware (outermost wraps first)
app.add_middleware(AccessLogMiddleware)
app.add_middleware(TraceIdMiddleware)

# Exception handlers
register_exception_handlers(app)

# API routes
app.include_router(api_router)


class _HealthPayload(dict):
    """Typed payload for the health endpoint.

    Using a plain ``dict`` subclass keeps the JSON shape stable while
    letting us return it through ``SuccessResponse`` so the health
    endpoint matches the unified envelope documented in
    docs/api-spec.md §1.
    """


@app.get(
    "/api/v1/internal/health",
    tags=["internal"],
    response_model=SuccessResponse[dict],
)
async def health() -> SuccessResponse[dict]:
    return make_success({"status": "ok", "service": "merittrack"})


@app.get(
    "/api/v1/internal/metrics",
    tags=["internal"],
    response_class=PlainTextResponse,
    dependencies=[Depends(require_role(UserRole.admin))],
)
async def metrics_endpoint() -> str:
    return render_metrics()


# Serve compiled Vue frontend from same process (same-deployment strategy)
_dist = Path(settings.frontend_dist_path)
if _dist.exists():
    app.mount("/", StaticFiles(directory=str(_dist), html=True), name="frontend")
