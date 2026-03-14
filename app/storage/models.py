"""SQLite storage models."""

from datetime import datetime
from typing import Optional


class DocumentModel:
    """Document metadata model for SQLite."""

    def __init__(
        self,
        doc_id: str,
        path: str,
        title: Optional[str] = None,
        source_url: Optional[str] = None,
        top_dir: Optional[str] = None,
        sub_dir: Optional[str] = None,
        page_kind: Optional[str] = None,
        kit: Optional[str] = None,
        subsystem: Optional[str] = None,
        owner: Optional[str] = None,
        is_api_reference: bool = False,
        is_guide: bool = False,
        is_design_spec: bool = False,
        chunk_count: int = 0,
        indexed_chunk_count: int = 0,
        content_hash: Optional[str] = None,
        index_signature: Optional[str] = None,
        index_status: str = "pending",
        last_error: Optional[str] = None,
        last_indexed_at: Optional[datetime] = None,
        created_at: Optional[datetime] = None
    ):
        self.doc_id = doc_id
        self.path = path
        self.title = title
        self.source_url = source_url
        self.top_dir = top_dir
        self.sub_dir = sub_dir
        self.page_kind = page_kind
        self.kit = kit
        self.subsystem = subsystem
        self.owner = owner
        self.is_api_reference = is_api_reference
        self.is_guide = is_guide
        self.is_design_spec = is_design_spec
        self.chunk_count = chunk_count
        self.indexed_chunk_count = indexed_chunk_count
        self.content_hash = content_hash
        self.index_signature = index_signature
        self.index_status = index_status
        self.last_error = last_error
        self.last_indexed_at = last_indexed_at
        self.created_at = created_at or datetime.now()

    def to_dict(self):
        """Convert to dictionary."""
        return {
            "doc_id": self.doc_id,
            "path": self.path,
            "title": self.title,
            "source_url": self.source_url,
            "top_dir": self.top_dir,
            "sub_dir": self.sub_dir,
            "page_kind": self.page_kind,
            "kit": self.kit,
            "subsystem": self.subsystem,
            "owner": self.owner,
            "is_api_reference": self.is_api_reference,
            "is_guide": self.is_guide,
            "is_design_spec": self.is_design_spec,
            "chunk_count": self.chunk_count,
            "indexed_chunk_count": self.indexed_chunk_count,
            "content_hash": self.content_hash,
            "index_signature": self.index_signature,
            "index_status": self.index_status,
            "last_error": self.last_error,
            "last_indexed_at": self.last_indexed_at.isoformat() if self.last_indexed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
