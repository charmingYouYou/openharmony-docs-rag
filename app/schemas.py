from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class PageKind(str, Enum):
    """Document page type classification."""
    README = "readme"
    GUIDE = "guide"
    REFERENCE = "reference"
    DESIGN_SPEC = "design_spec"
    CONCEPT = "concept"
    UNKNOWN = "unknown"


class QueryIntent(str, Enum):
    """Query intent types."""
    GUIDE = "guide"
    API_USAGE = "api_usage"
    DESIGN_SPEC = "design_spec"
    CONCEPT = "concept"
    GENERAL = "general"


class DocumentMetadata(BaseModel):
    """Metadata extracted from document."""
    kit: Optional[str] = None
    subsystem: Optional[str] = None
    owner: Optional[str] = None


class ParsedDocument(BaseModel):
    """Parsed document structure."""
    doc_id: str
    path: str
    title: Optional[str] = None
    content: str
    metadata: DocumentMetadata
    page_kind: PageKind
    is_api_reference: bool = False
    is_guide: bool = False
    is_design_spec: bool = False
    top_dir: str
    sub_dir: Optional[str] = None


class Chunk(BaseModel):
    """Document chunk."""
    chunk_id: str
    doc_id: str
    text: str
    heading_path: str
    chunk_index: int
    metadata: Dict[str, Any]


class RetrievalFilters(BaseModel):
    """Filters for retrieval."""
    top_dir: Optional[str] = None
    kit: Optional[str] = None
    subsystem: Optional[str] = None
    page_kind: Optional[PageKind] = None
    exclude_readme: bool = False


class PreprocessedQuery(BaseModel):
    """Preprocessed query with intent."""
    normalized_query: str
    intent: QueryIntent
    confidence: float
    filters: RetrievalFilters


class RetrievedChunk(BaseModel):
    """Retrieved chunk with score."""
    chunk_id: str
    text: str
    heading_path: str
    score: float
    metadata: Dict[str, Any]


class Citation(BaseModel):
    """Citation for answer."""
    path: str
    title: Optional[str] = None
    heading_path: str
    snippet: str
    source_url: str


class QueryRequest(BaseModel):
    """Request for /query endpoint."""
    query: str
    top_k: int = Field(default=6, ge=1, le=20)
    filters: Optional[RetrievalFilters] = None


class QueryResponse(BaseModel):
    """Response for /query endpoint."""
    answer: str
    citations: List[Citation]
    trace_id: str
    latency_ms: int
    used_chunks: int
    intent: Dict[str, Any]


class RetrieveRequest(BaseModel):
    """Request for /retrieve endpoint."""
    query: str
    top_k: int = Field(default=10, ge=1, le=50)
    filters: Optional[RetrievalFilters] = None


class RetrieveResponse(BaseModel):
    """Response for /retrieve endpoint."""
    chunks: List[RetrievedChunk]
    trace_id: str
    latency_ms: int


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    qdrant_connected: bool
    sqlite_connected: bool
    indexed_documents: int


class CapabilitiesResponse(BaseModel):
    """Capabilities response."""
    supported_intents: List[str]
    supported_filters: List[str]
    max_top_k: int
    embedding_model: str
    chat_model: str
