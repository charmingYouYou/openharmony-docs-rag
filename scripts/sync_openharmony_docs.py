#!/usr/bin/env python3
"""Script to sync OpenHarmony documentation repository."""

import subprocess
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.settings import settings
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


def sync_repo():
    """
    Clone or update OpenHarmony documentation repository.

    Only syncs the specified directories (application-dev and design).
    """
    repo_path = Path(settings.docs_local_path)
    repo_url = settings.docs_repo_url
    branch = settings.docs_branch

    logger.info(f"Syncing repository from {repo_url}")
    logger.info(f"Target path: {repo_path}")
    logger.info(f"Branch: {branch}")

    # Ensure parent directory exists
    repo_path.parent.mkdir(parents=True, exist_ok=True)

    if repo_path.exists():
        logger.info("Repository already exists, updating...")
        try:
            # Pull latest changes
            subprocess.run(
                ["git", "-C", str(repo_path), "fetch", "origin"],
                check=True,
                capture_output=True
            )
            subprocess.run(
                ["git", "-C", str(repo_path), "reset", "--hard", f"origin/{branch}"],
                check=True,
                capture_output=True
            )
            logger.info("Repository updated successfully")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to update repository: {e}")
            logger.error(f"stderr: {e.stderr.decode()}")
            raise
    else:
        logger.info("Cloning repository...")
        try:
            # Clone with depth 1 for faster download
            subprocess.run(
                [
                    "git", "clone",
                    "--depth", "1",
                    "--branch", branch,
                    repo_url,
                    str(repo_path)
                ],
                check=True,
                capture_output=True
            )
            logger.info("Repository cloned successfully")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to clone repository: {e}")
            logger.error(f"stderr: {e.stderr.decode()}")
            raise

    # Verify target directories exist
    for dir_name in settings.include_dirs_list:
        target_dir = repo_path / dir_name
        if not target_dir.exists():
            logger.warning(f"Target directory does not exist: {target_dir}")
        else:
            # Count markdown files
            md_files = list(target_dir.rglob("*.md"))
            logger.info(f"Found {len(md_files)} markdown files in {dir_name}")

    logger.info("Repository sync completed")


if __name__ == "__main__":
    try:
        sync_repo()
    except Exception as e:
        logger.error(f"Sync failed: {e}")
        sys.exit(1)
