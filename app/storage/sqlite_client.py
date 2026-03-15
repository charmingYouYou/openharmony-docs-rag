"""SQLite storage client with configurable table scoping for runtime and E2E isolation."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional

import aiosqlite

from app.settings import Settings, get_settings
from app.storage.models import DocumentModel
from app.utils.logger import setup_logger

logger = setup_logger(__name__)
IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class SQLiteClient:
    """SQLite client for document metadata."""

    def __init__(
        self,
        db_path: str | None = None,
        table_name: str | None = None,
        settings_snapshot: Settings | None = None,
    ):
        """Bind one client instance to a specific database file and logical table."""
        self.settings_snapshot = settings_snapshot or get_settings()
        self.db_path = db_path or self.settings_snapshot.sqlite_db_path
        self.table_name = self._validate_identifier(
            table_name or self.settings_snapshot.sqlite_documents_table
        )
        self._ensure_db_directory()

    def _ensure_db_directory(self) -> None:
        """Ensure database directory exists before any connection is opened."""
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)

    async def initialize(self) -> None:
        """Initialize the scoped database schema and supporting indexes."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {self._quoted_table_name} (
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
                """
            )

            await self._migrate_schema(db)
            await self._create_indexes(db)
            await db.commit()
            logger.info(
                "Database initialized successfully for table %s", self.table_name
            )

    async def insert_document(self, doc: DocumentModel) -> None:
        """Insert or replace one document in the scoped table."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                f"""
                INSERT OR REPLACE INTO {self._quoted_table_name} (
                    doc_id, path, title, source_url, top_dir, sub_dir,
                    page_kind, kit, subsystem, owner,
                    is_api_reference, is_guide, is_design_spec,
                    chunk_count, indexed_chunk_count, content_hash,
                    index_signature, index_status, last_error,
                    last_indexed_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    doc.doc_id,
                    doc.path,
                    doc.title,
                    doc.source_url,
                    doc.top_dir,
                    doc.sub_dir,
                    doc.page_kind,
                    doc.kit,
                    doc.subsystem,
                    doc.owner,
                    doc.is_api_reference,
                    doc.is_guide,
                    doc.is_design_spec,
                    doc.chunk_count,
                    doc.indexed_chunk_count,
                    doc.content_hash,
                    doc.index_signature,
                    doc.index_status,
                    doc.last_error,
                    doc.last_indexed_at.isoformat() if doc.last_indexed_at else None,
                    doc.created_at.isoformat() if doc.created_at else None,
                ),
            )
            await db.commit()

    async def get_document(self, doc_id: str) -> Optional[DocumentModel]:
        """Get one document by ID from the scoped table."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                f"SELECT * FROM {self._quoted_table_name} WHERE doc_id = ?",
                (doc_id,),
            ) as cursor:
                row = await cursor.fetchone()
                return self._row_to_model(row) if row else None

    async def get_all_documents(self) -> List[DocumentModel]:
        """Return all documents from the scoped table."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                f"SELECT * FROM {self._quoted_table_name}"
            ) as cursor:
                rows = await cursor.fetchall()
                return [self._row_to_model(row) for row in rows]

    async def count_documents(self) -> int:
        """Count total documents in the scoped table."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                f"SELECT COUNT(*) FROM {self._quoted_table_name}"
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0

    async def delete_document(self, doc_id: str) -> None:
        """Delete one document from the scoped table."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                f"DELETE FROM {self._quoted_table_name} WHERE doc_id = ?",
                (doc_id,),
            )
            await db.commit()

    async def clear_all(self) -> None:
        """Clear all documents from the scoped table."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(f"DELETE FROM {self._quoted_table_name}")
            await db.commit()
            logger.info("All documents cleared from table %s", self.table_name)

    async def list_documents(
        self,
        *,
        top_dir: str | None = None,
        kit: str | None = None,
        page_kind: str | None = None,
        index_status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        """List scoped documents with filters and pagination metadata."""
        where_clause, params = self._build_filter_clause(
            top_dir=top_dir,
            kit=kit,
            page_kind=page_kind,
            index_status=index_status,
        )

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                (
                    f"SELECT * FROM {self._quoted_table_name} {where_clause} "
                    "ORDER BY path LIMIT ? OFFSET ?"
                ),
                [*params, limit, offset],
            ) as cursor:
                rows = await cursor.fetchall()
                documents = [dict(row) for row in rows]

            async with db.execute(
                f"SELECT COUNT(*) FROM {self._quoted_table_name} {where_clause}",
                params,
            ) as cursor:
                row = await cursor.fetchone()
                total = row[0] if row else 0

        return {
            "documents": documents,
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    async def get_document_detail(self, doc_id: str) -> dict[str, Any] | None:
        """Return one read-only document record as a plain dictionary."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                f"SELECT * FROM {self._quoted_table_name} WHERE doc_id = ?",
                (doc_id,),
            ) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def get_stats(self) -> dict[str, Any]:
        """Return scoped document distribution statistics for the explorer view."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                f"SELECT COUNT(*) FROM {self._quoted_table_name}"
            ) as cursor:
                row = await cursor.fetchone()
                total_docs = row[0] if row else 0

            async with db.execute(
                (
                    f"SELECT top_dir, COUNT(*) as count FROM {self._quoted_table_name} "
                    "GROUP BY top_dir"
                )
            ) as cursor:
                rows = await cursor.fetchall()
                by_top_dir = {row[0]: row[1] for row in rows}

            async with db.execute(
                (
                    f"SELECT kit, COUNT(*) as count FROM {self._quoted_table_name} "
                    "WHERE kit IS NOT NULL GROUP BY kit ORDER BY count DESC LIMIT 10"
                )
            ) as cursor:
                rows = await cursor.fetchall()
                by_kit = {row[0]: row[1] for row in rows}

            async with db.execute(
                (
                    f"SELECT page_kind, COUNT(*) as count FROM {self._quoted_table_name} "
                    "GROUP BY page_kind"
                )
            ) as cursor:
                rows = await cursor.fetchall()
                by_page_kind = {row[0]: row[1] for row in rows}

            async with db.execute(
                (
                    f"SELECT SUM(is_api_reference), SUM(is_guide), SUM(is_design_spec) "
                    f"FROM {self._quoted_table_name}"
                )
            ) as cursor:
                row = await cursor.fetchone()
                api_count = row[0] if row and row[0] else 0
                guide_count = row[1] if row and row[1] else 0
                design_count = row[2] if row and row[2] else 0

        return {
            "total_documents": total_docs,
            "by_top_dir": by_top_dir,
            "by_kit": by_kit,
            "by_page_kind": by_page_kind,
            "document_types": {
                "api_reference": api_count,
                "guide": guide_count,
                "design_spec": design_count,
            },
        }

    def _build_filter_clause(
        self,
        *,
        top_dir: str | None,
        kit: str | None,
        page_kind: str | None,
        index_status: str | None,
    ) -> tuple[str, list[Any]]:
        """Build one reusable WHERE clause for list and count queries."""
        conditions = []
        params: list[Any] = []

        if top_dir:
            conditions.append("top_dir = ?")
            params.append(top_dir)
        if kit:
            conditions.append("kit = ?")
            params.append(kit)
        if page_kind:
            conditions.append("page_kind = ?")
            params.append(page_kind)
        if index_status:
            conditions.append("index_status = ?")
            params.append(index_status)

        if not conditions:
            return "", params
        return "WHERE " + " AND ".join(conditions), params

    def _row_to_model(self, row: aiosqlite.Row) -> DocumentModel:
        """Convert one SQLite row into the in-memory document model."""
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
            last_indexed_at=(
                datetime.fromisoformat(row["last_indexed_at"])
                if row["last_indexed_at"]
                else None
            ),
            created_at=(
                datetime.fromisoformat(row["created_at"])
                if row["created_at"]
                else None
            ),
        )

    async def _migrate_schema(self, db: aiosqlite.Connection) -> None:
        """Add missing columns to existing tables without rewriting data."""
        async with db.execute(
            f"PRAGMA table_info({self._quoted_table_name})"
        ) as cursor:
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
                f"ALTER TABLE {self._quoted_table_name} ADD COLUMN {column_name} {column_type}"
            )

    async def _create_indexes(self, db: aiosqlite.Connection) -> None:
        """Create the scoped indexes used by explorer filters and status checks."""
        index_prefix = f"idx_{self.table_name}"
        await db.execute(
            f"CREATE INDEX IF NOT EXISTS {index_prefix}_top_dir ON {self._quoted_table_name}(top_dir)"
        )
        await db.execute(
            f"CREATE INDEX IF NOT EXISTS {index_prefix}_kit ON {self._quoted_table_name}(kit)"
        )
        await db.execute(
            f"CREATE INDEX IF NOT EXISTS {index_prefix}_page_kind ON {self._quoted_table_name}(page_kind)"
        )
        await db.execute(
            f"CREATE INDEX IF NOT EXISTS {index_prefix}_is_api_reference ON {self._quoted_table_name}(is_api_reference)"
        )
        await db.execute(
            f"CREATE INDEX IF NOT EXISTS {index_prefix}_is_guide ON {self._quoted_table_name}(is_guide)"
        )
        await db.execute(
            f"CREATE INDEX IF NOT EXISTS {index_prefix}_is_design_spec ON {self._quoted_table_name}(is_design_spec)"
        )
        await db.execute(
            f"CREATE INDEX IF NOT EXISTS {index_prefix}_index_status ON {self._quoted_table_name}(index_status)"
        )

    @property
    def _quoted_table_name(self) -> str:
        """Return the validated table name in a safe quoted form for SQL composition."""
        return f'"{self.table_name}"'

    def _validate_identifier(self, identifier: str) -> str:
        """Reject invalid SQL identifiers before any query is composed."""
        if not IDENTIFIER_PATTERN.match(identifier):
            raise ValueError(f"非法 SQLite 标识符：{identifier}")
        return identifier
