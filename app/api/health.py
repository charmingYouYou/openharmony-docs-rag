"""Health check and capabilities endpoints."""

from fastapi import APIRouter

from app.schemas import HealthResponse, CapabilitiesResponse
from app.storage.qdrant_client import QdrantClient
from app.storage.sqlite_client import SQLiteClient
from app.settings import settings
from app.utils.logger import setup_logger

logger = setup_logger(__name__)
router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    try:
        # Check Qdrant connection
        qdrant = QdrantClient()
        qdrant_connected = True
        try:
            qdrant.count_points()
        except:
            qdrant_connected = False

        # Check SQLite connection
        sqlite = SQLiteClient()
        sqlite_connected = True
        indexed_documents = 0
        try:
            indexed_documents = await sqlite.count_documents()
        except:
            sqlite_connected = False

        return HealthResponse(
            status="healthy" if (qdrant_connected and sqlite_connected) else "degraded",
            version="0.1.0",
            qdrant_connected=qdrant_connected,
            sqlite_connected=sqlite_connected,
            indexed_documents=indexed_documents
        )

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthResponse(
            status="unhealthy",
            version="0.1.0",
            qdrant_connected=False,
            sqlite_connected=False,
            indexed_documents=0
        )


@router.get("/capabilities", response_model=CapabilitiesResponse)
async def get_capabilities():
    """Get system capabilities."""
    return CapabilitiesResponse(
        supported_intents=["guide", "api_usage", "design_spec", "concept", "general"],
        supported_filters=["top_dir", "kit", "subsystem", "page_kind", "exclude_readme"],
        max_top_k=50,
        embedding_model=settings.openai_embedding_model,
        chat_model=settings.openai_chat_model
    )
