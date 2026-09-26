"""FastAPI application factory."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from google.adk.cli.fast_api import get_fast_api_app
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from .config import AGENTS_DIR, HOST, PORT, ensure_data_dir, session_service_uri
from .llm_providers import apply_litellm_env
from .provider_settings import get_provider_settings
from .bundled_templates import ensure_bundled_templates_imported
from .providers_api import router as providers_router
from .requests_api import router as requests_router
from .schedules_api import router as schedules_router
from .scheduler_service import start_scheduler, stop_scheduler
from .automation_api import router as automation_router
from .templates_api import router as templates_router
from .workflow_api import router as workflow_router

load_dotenv()

log = logging.getLogger(__name__)

# Dev UI + common local origins. Override with ORCHESTRUMAI_CORS_ORIGINS (comma-separated).
_DEFAULT_CORS_ORIGINS = (
    "http://127.0.0.1:5173",
    "http://localhost:5173",
    "http://127.0.0.1:8000",
    "http://localhost:8000",
)


def _cors_origins() -> list[str]:
    raw = os.environ.get("ORCHESTRUMAI_CORS_ORIGINS", "").strip()
    if raw:
        return [o.strip() for o in raw.split(",") if o.strip()]
    return list(_DEFAULT_CORS_ORIGINS)


def _api_token() -> str:
    return os.environ.get("ORCHESTRUMAI_API_TOKEN", "").strip()


def _is_loopback_host(host: str) -> bool:
    h = (host or "").strip().lower()
    return h in ("127.0.0.1", "localhost", "::1")


class LocalApiTokenMiddleware(BaseHTTPMiddleware):
    """Require ORCHESTRUMAI_API_TOKEN on /api when configured (recommended for non-localhost binds)."""

    async def dispatch(self, request: Request, call_next):
        token = _api_token()
        if not token or not request.url.path.startswith("/api"):
            return await call_next(request)
        # Allow unauthenticated health checks for probes
        if request.url.path in ("/api/health", "/api/health/"):
            return await call_next(request)
        provided = request.headers.get("X-OrchestrumAI-Token", "").strip()
        if provided != token:
            return JSONResponse({"detail": "Invalid or missing API token"}, status_code=401)
        return await call_next(request)


def _frontend_dist() -> Path | None:
    root = Path(__file__).resolve().parent.parent.parent
    dist = root / "frontend" / "dist"
    if (dist / "index.html").exists():
        return dist
    return None


def create_app() -> FastAPI:
    ensure_data_dir()
    os.environ.setdefault("ADK_DEFAULT_APP_NAME", "workflow_agent")

    if not _is_loopback_host(HOST) and not _api_token():
        log.warning(
            "ORCHESTRUMAI_HOST=%s is not loopback and ORCHESTRUMAI_API_TOKEN is unset. "
            "Set a token before exposing this API on a network interface.",
            HOST,
        )

    cors_origins = _cors_origins()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        settings = get_provider_settings()
        import os

        if settings.ollama_host:
            os.environ.setdefault("OLLAMA_HOST", settings.ollama_host)
        if settings.lm_studio_base_url:
            os.environ.setdefault("LM_STUDIO_BASE_URL", settings.lm_studio_base_url)
        apply_litellm_env()
        ensure_bundled_templates_imported()
        from .inbox_watcher import inbox_tick

        async def _inbox_job():
            await inbox_tick()

        sched = start_scheduler()
        sched.add_job(
            _inbox_job,
            "interval",
            seconds=90,
            id="inbox_watch_tick",
            replace_existing=True,
        )
        yield
        stop_scheduler()

    app = get_fast_api_app(
        agents_dir=str(AGENTS_DIR),
        session_service_uri=session_service_uri(),
        web=False,
        allow_origins=cors_origins,
        lifespan=lifespan,
        auto_create_session=True,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(LocalApiTokenMiddleware)

    app.include_router(requests_router, prefix="/api")
    app.include_router(providers_router, prefix="/api")
    app.include_router(workflow_router, prefix="/api")
    app.include_router(templates_router, prefix="/api")
    app.include_router(schedules_router, prefix="/api")
    app.include_router(automation_router, prefix="/api")

    dist = _frontend_dist()
    if dist is not None:
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

        @app.get("/")
        async def index() -> FileResponse:
            return FileResponse(dist / "index.html")

    return app


def main() -> None:
    import uvicorn

    uvicorn.run(
        "orchestrumai.app:create_app",
        factory=True,
        host=HOST,
        port=PORT,
        reload=False,
    )


if __name__ == "__main__":
    main()
