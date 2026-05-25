"""FastAPI application factory."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from google.adk.cli.fast_api import get_fast_api_app

from .config import AGENTS_DIR, HOST, PORT, ensure_data_dir, session_service_uri
from .llm_providers import apply_litellm_env
from .provider_settings import get_provider_settings
from .providers_api import router as providers_router
from .requests_api import router as requests_router
from .workflow_api import router as workflow_router

load_dotenv()


def _frontend_dist() -> Path | None:
    root = Path(__file__).resolve().parent.parent.parent
    dist = root / "frontend" / "dist"
    if (dist / "index.html").exists():
        return dist
    return None


def create_app() -> FastAPI:
    ensure_data_dir()
    os.environ.setdefault("ADK_DEFAULT_APP_NAME", "workflow_agent")

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        settings = get_provider_settings()
        import os

        if settings.ollama_host:
            os.environ.setdefault("OLLAMA_HOST", settings.ollama_host)
        if settings.lm_studio_base_url:
            os.environ.setdefault("LM_STUDIO_BASE_URL", settings.lm_studio_base_url)
        apply_litellm_env()
        yield

    app = get_fast_api_app(
        agents_dir=str(AGENTS_DIR),
        session_service_uri=session_service_uri(),
        web=False,
        allow_origins=["*"],
        lifespan=lifespan,
        auto_create_session=True,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(requests_router, prefix="/api")
    app.include_router(providers_router, prefix="/api")
    app.include_router(workflow_router, prefix="/api")

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
        "openminiagents.app:create_app",
        factory=True,
        host=HOST,
        port=PORT,
        reload=False,
    )


if __name__ == "__main__":
    main()
