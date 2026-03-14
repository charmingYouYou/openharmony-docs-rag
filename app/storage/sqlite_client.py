"""SQLite client for metadata storage."""

import aiosqlite
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from app.storage.models import DocumentModel
from app.settings import settings
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class SQLiteClient:
    """SQLite client for document metadata."""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or settings.sqlite_db_path
        self._ensure_db_directory()

    def _ensure_db_directory(self):
        """Ensure database directory exists."""
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)

    async def initialize(self):
        """Initialize database schema."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    doc_id TEXT PRIMARY KEY,
                    path TEXT NOT NULL UNIQUE,
                    title TEXT,
                    source_url TEXT,
                    top_dir TEXT,
                    sub_dir TEXT,
                    page_kind TEXT,
                    kit TEXT,
                    subsystem TEXT,
                    owner TEXT,
                    is_api_reference BOOLEAN DEFAULT 0,
                    is_guide BOOLEAN DEFAULT 0,
                    is_design_spec BOOLEAN DEFAULT 0,
                    chunk_count INTEGER DEFAULT 0,
                    indexed_chunk_count INTEGER DEFAULT 0,
                    content_hash TEXT,
                    index_signature TEXT,
                    index_status TEXT DEFAULT 'pending',
                    last_error TEXT,
                    last_indexed_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            await self._migrate_schema(db)

            # Create indexes
            await db.execute("CREATE INDEX IF NOT EXISTS idx_documents_top_dir ON documents(top_dir)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_documents_kit ON documents(kit)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_documents_page_kind ON documents(page_kind)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_documents_is_api_reference ON documents(is_api_reference)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_documents_is_guide ON documents(is_guide)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_documents_is_design_spec ON documents(is_design_spec)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_documents_index_status ON documents(index_status)")

            await db.commit()
            logger.info("Database initialized successfully")

    async def insert_document(self, doc: DocumentModel):
        """Insert or replace a document."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO documents (
                    doc_id, path, title, source_url, top_dir, sub_dir,
                    page_kind, kit, subsystem, owner,
                    is_api_reference, is_guide, is_design_spec,
                    chunk_count, indexed_chunk_count, content_hash,
                    index_signature, index_status, last_error,
                    last_indexed_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                doc.doc_id, doc.path, doc.title, doc.source_url,
                doc.top_dir, doc.sub_dir, doc.page_kind,
                doc.kit, doc.subsystem, doc.owner,
                doc.is_api_reference, doc.is_guide, doc.is_design_spec,
                doc.chunk_count,
                doc.indexed_chunk_count,
                doc.content_hash,
                doc.index_signature,
                doc.index_status,
                doc.last_error,
                doc.last_indexed_at.isoformat() if doc.last_indexed_at else None,
                doc.created_at.isoformat() if doc.created_at else None
            ))
            await db.commit()

    async def get_document(self, doc_id: str) -> Optional[DocumentModel]:
        """Get document by ID."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM documents WHERE doc_id = ?", (doc_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return self._row_to_model(row)
                return None

    async def get_all_documents(self) -> List[DocumentModel]:
        """Get all documents."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM documents") as cursor:
                rows = await cursor.fetchall()
                return [self._row_to_model(row) for row in rows]

    async def count_documents(self) -> int:
        """Count total documents."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT COUNT(*) FROM documents") as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0

    async def delete_document(self, doc_id: str):
        """Delete a document."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM documents WHERE doc_id = ?", (doc_id,))
            await db.commit()

    async def clear_all(self):
        """Clear all documents."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM documents")
            await db.commit()
            logger.info("All documents cleared from database")

    def _row_to_model(self, row: aiosqlite.Row) -> DocumentModel:
        """Convert database row to DocumentModel."""
        return DocumentModel(
            doc_id=row["doc_id"],
            path=row["path"],
            title=row["title"],
            source_url=row["source_url"],
            top_dir=row["top_dir"],
            sub_dir=row["sub_dir"],
            page_kind=row["page_kind"],
            kit=row["kit"],
            subsystem=row["subsystem"],
            owner=row["owner"],
            is_api_reference=bool(row["is_api_reference"]),
            is_guide=bool(row["is_guide"]),
            is_design_spec=bool(row["is_design_spec"]),
            chunk_count=row["chunk_count"],
            indexed_chunk_count=row["indexed_chunk_count"],
            content_hash=row["content_hash"],
            index_signature=row["index_signature"],
            index_status=row["index_status"],
            last_error=row["last_error"],
            last_indexed_at=datetime.fromisoformat(row["last_indexed_at"]) if row["last_indexed_at"] else None,
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None
        )

    async def _migrate_schema(self, db: aiosqlite.Connection):
        """Add missing columns to existing databases."""
        async with db.execute("PRAGMA table_info(documents)") as cursor:
            rows = await cursor.fetchall()

        existing_columns = {row[1] for row in rows}
        required_columns = {
            "indexed_chunk_count": "INTEGER DEFAULT 0",
            "content_hash": "TEXT",
            "index_signature": "TEXT",
            "index_status": "TEXT DEFAULT 'pending'",
            "last_error": "TEXT",
        }

        for column_name, column_type in required_columns.items():
            if column_name in existing_columns:
                continue
            await db.execute(
                f"ALTER TABLE documents ADD COLUMN {column_name} {column_type}"
            )
