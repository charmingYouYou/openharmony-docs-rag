"""FastAPI application entry point."""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.api import query, health, management
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


# Create FastAPI app
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


@app.on_event("startup")
async def startup_event():
    """Startup event handler."""
    logger.info("Starting OpenHarmony Docs RAG API")


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event handler."""
    logger.info("Shutting down OpenHarmony Docs RAG API")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True
    )
