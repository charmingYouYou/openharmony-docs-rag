"""Management API endpoints."""

import subprocess
from pathlib import Path
from fastapi import APIRouter, HTTPException

from app.settings import get_settings
from app.storage.sqlite_client import SQLiteClient
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
        runtime_settings = get_settings()

        repo_path = Path(runtime_settings.docs_local_path)

        if not repo_path.exists():
            # Clone repository
            logger.info(f"Cloning repository to {repo_path}")
            result = subprocess.run(
                [
                    "git", "clone",
                    "--depth", "1",
                    "--branch", runtime_settings.docs_branch,
                    runtime_settings.docs_repo_url,
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
                [
                    "git",
                    "-C",
                    str(repo_path),
                    "pull",
                    "origin",
                    runtime_settings.docs_branch,
                ],
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode != 0:
                raise Exception(f"Pull failed: {result.stderr}")

            logger.info("Repository updated successfully")

        # Count files
        file_count = 0
        for dir_name in runtime_settings.include_dirs_list:
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
    index_status: str = None,
    limit: int = 100,
    offset: int = 0
):
    """
    List indexed documents with optional filters.

    Query parameters:
    - top_dir: Filter by top directory (e.g., "application-dev")
    - kit: Filter by Kit (e.g., "ArkUI")
    - page_kind: Filter by page kind (e.g., "guide")
    - index_status: Filter by index status (e.g., "ready")
    - limit: Maximum number of results (default 100)
    - offset: Offset for pagination (default 0)
    """
    try:
        sqlite = SQLiteClient()
        return await sqlite.list_documents(
            top_dir=top_dir,
            kit=kit,
            page_kind=page_kind,
            index_status=index_status,
            limit=limit,
            offset=offset,
        )

    except Exception as e:
        logger.error(f"Failed to list documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents/{doc_id}")
async def get_document_detail(doc_id: str):
    """
    Return one indexed document record as a read-only detail payload.

    This endpoint exists for the web explorer detail drawer and intentionally
    does not expose any mutation operation.
    """
    try:
        sqlite = SQLiteClient()
        document = await sqlite.get_document_detail(doc_id)
        if document is None:
            raise HTTPException(status_code=404, detail="文档不存在")
        return document
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get document detail: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_stats():
    """
    Get system statistics.

    Returns document counts by type, kit, etc.
    """
    try:
        sqlite = SQLiteClient()
        return await sqlite.get_stats()

    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
