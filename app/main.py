"""FastAPI application entry point with optional built-web serving for deployment."""

from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.api import query, health, management
from app.api.web import router as web_router
from app.settings import settings
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class CallerTypeMiddleware(BaseHTTPMiddleware):
    """Middleware to track caller type (ui, skill, mcp)."""

    async def dispatch(self, request: Request, call_next):
        # Extract caller type from header
        caller_type = request.headers.get("X-Caller-Type", "ui")

        # Store in request state
        request.state.caller_type = caller_type

        # Log the request
        logger.info(f"Request from {caller_type}: {request.method} {request.url.path}")

        response = await call_next(request)
        return response


def _resolve_web_dist_dir(web_dist_dir: Path | None = None) -> Path:
    """Return the frontend build directory used for deployment-time static serving."""
    if web_dist_dir is not None:
        return web_dist_dir
    return Path(__file__).resolve().parent.parent / "web" / "dist"


def _register_web_routes(app: FastAPI, web_dist_dir: Path | None = None) -> None:
    """Serve built web assets and SPA routes from the deployment bundle when available."""
    dist_dir = _resolve_web_dist_dir(web_dist_dir)
    index_file = dist_dir / "index.html"
    if not dist_dir.exists() or not index_file.exists():
        return

    resolved_dist_dir = dist_dir.resolve()

    @app.get("/", include_in_schema=False)
    async def serve_web_index():
        """Serve the single-page app entrypoint from the built frontend bundle."""
        return FileResponse(index_file)

    @app.get("/{web_path:path}", include_in_schema=False)
    async def serve_web_path(web_path: str):
        """Serve static assets directly and fall back to the SPA entrypoint for app routes."""
        candidate = (resolved_dist_dir / web_path).resolve()
        try:
            candidate.relative_to(resolved_dist_dir)
        except ValueError:
            return Response(status_code=404)

        if candidate.is_file():
            return FileResponse(candidate)
        if "." not in Path(web_path).name:
            return FileResponse(index_file)
        return Response(status_code=404)


def create_app(web_dist_dir: Path | None = None) -> FastAPI:
    """Create the API application and optionally attach built frontend routes."""
    app = FastAPI(
        title="OpenHarmony Docs RAG API",
        description="RAG system for OpenHarmony Chinese documentation",
        version="0.1.0"
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add caller type middleware
    app.add_middleware(CallerTypeMiddleware)

    # Include routers
    app.include_router(query.router, tags=["Query"])
    app.include_router(health.router, tags=["Health"])
    app.include_router(management.router, tags=["Management"])
    app.include_router(web_router, tags=["Web"])

    _register_web_routes(app, web_dist_dir=web_dist_dir)

    @app.on_event("startup")
    async def startup_event():
        """Log API startup for local runs and deployed instances."""
        logger.info("Starting OpenHarmony Docs RAG API")

    @app.on_event("shutdown")
    async def shutdown_event():
        """Log API shutdown for local runs and deployed instances."""
        logger.info("Shutting down OpenHarmony Docs RAG API")

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True
    )
