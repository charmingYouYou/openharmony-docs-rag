"""Management API endpoints."""

import subprocess
from pathlib import Path
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any

from app.storage.sqlite_client import SQLiteClient
from app.settings import settings
from app.utils.logger import setup_logger

logger = setup_logger(__name__)
router = APIRouter()


@router.post("/sync-repo")
async def sync_repo():
    """
    Sync OpenHarmony documentation repository.

    This endpoint pulls the latest changes from the remote repository.
    """
    try:
        logger.info("Starting repository sync")

        repo_path = Path(settings.docs_local_path)

        if not repo_path.exists():
            # Clone repository
            logger.info(f"Cloning repository to {repo_path}")
            result = subprocess.run(
                [
                    "git", "clone",
                    "--depth", "1",
                    "--branch", settings.docs_branch,
                    settings.docs_repo_url,
                    str(repo_path)
                ],
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode != 0:
                raise Exception(f"Clone failed: {result.stderr}")

            logger.info("Repository cloned successfully")
        else:
            # Pull latest changes
            logger.info(f"Pulling latest changes for {repo_path}")
            result = subprocess.run(
                ["git", "-C", str(repo_path), "pull", "origin", settings.docs_branch],
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode != 0:
                raise Exception(f"Pull failed: {result.stderr}")

            logger.info("Repository updated successfully")

        # Count files
        file_count = 0
        for dir_name in settings.include_dirs_list:
            target_dir = repo_path / dir_name
            if target_dir.exists():
                files = list(target_dir.rglob("*.md"))
                file_count += len(files)
                logger.info(f"Found {len(files)} files in {dir_name}")

        return {
            "status": "success",
            "message": "Repository synced successfully",
            "repo_path": str(repo_path),
            "total_files": file_count
        }

    except subprocess.TimeoutExpired:
        logger.error("Repository sync timeout")
        raise HTTPException(status_code=504, detail="Repository sync timeout")
    except Exception as e:
        logger.error(f"Repository sync failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reindex")
async def reindex():
    """
    Rebuild the document index.

    This endpoint triggers a full reindex of all documents.
    Note: This is a long-running operation (30-60 minutes).
    """
    try:
        logger.info("Starting reindex operation")

        # Import here to avoid circular dependency
        from scripts.build_index import IndexBuilder

        # Create builder and run
        builder = IndexBuilder()
        await builder.build()

        return {
            "status": "success",
            "message": "Reindex completed successfully"
        }

    except Exception as e:
        logger.error(f"Reindex failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents")
async def list_documents(
    top_dir: str = None,
    kit: str = None,
    page_kind: str = None,
    limit: int = 100,
    offset: int = 0
):
    """
    List indexed documents with optional filters.

    Query parameters:
    - top_dir: Filter by top directory (e.g., "application-dev")
    - kit: Filter by Kit (e.g., "ArkUI")
    - page_kind: Filter by page kind (e.g., "guide")
    - limit: Maximum number of results (default 100)
    - offset: Offset for pagination (default 0)
    """
    try:
        sqlite = SQLiteClient()

        # Build query
        query = "SELECT * FROM documents WHERE 1=1"
        params = []

        if top_dir:
            query += " AND top_dir = ?"
            params.append(top_dir)

        if kit:
            query += " AND kit = ?"
            params.append(kit)

        if page_kind:
            query += " AND page_kind = ?"
            params.append(page_kind)

        query += " ORDER BY path LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        # Execute query
        import aiosqlite
        async with aiosqlite.connect(sqlite.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                documents = [dict(row) for row in rows]

            # Get total count
            count_query = "SELECT COUNT(*) FROM documents WHERE 1=1"
            count_params = []

            if top_dir:
                count_query += " AND top_dir = ?"
                count_params.append(top_dir)

            if kit:
                count_query += " AND kit = ?"
                count_params.append(kit)

            if page_kind:
                count_query += " AND page_kind = ?"
                count_params.append(page_kind)

            async with db.execute(count_query, count_params) as cursor:
                row = await cursor.fetchone()
                total = row[0] if row else 0

        return {
            "documents": documents,
            "total": total,
            "limit": limit,
            "offset": offset
        }

    except Exception as e:
        logger.error(f"Failed to list documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_stats():
    """
    Get system statistics.

    Returns document counts by type, kit, etc.
    """
    try:
        sqlite = SQLiteClient()

        import aiosqlite
        async with aiosqlite.connect(sqlite.db_path) as db:
            # Total documents
            async with db.execute("SELECT COUNT(*) FROM documents") as cursor:
                row = await cursor.fetchone()
                total_docs = row[0] if row else 0

            # By top_dir
            async with db.execute(
                "SELECT top_dir, COUNT(*) as count FROM documents GROUP BY top_dir"
            ) as cursor:
                rows = await cursor.fetchall()
                by_top_dir = {row[0]: row[1] for row in rows}

            # By kit
            async with db.execute(
                "SELECT kit, COUNT(*) as count FROM documents WHERE kit IS NOT NULL GROUP BY kit ORDER BY count DESC LIMIT 10"
            ) as cursor:
                rows = await cursor.fetchall()
                by_kit = {row[0]: row[1] for row in rows}

            # By page_kind
            async with db.execute(
                "SELECT page_kind, COUNT(*) as count FROM documents GROUP BY page_kind"
            ) as cursor:
                rows = await cursor.fetchall()
                by_page_kind = {row[0]: row[1] for row in rows}

            # Document type flags
            async with db.execute(
                "SELECT SUM(is_api_reference) as api_count, SUM(is_guide) as guide_count, SUM(is_design_spec) as design_count FROM documents"
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
                "design_spec": design_count
            }
        }

    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
