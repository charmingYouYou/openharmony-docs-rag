"""Synchronous reranking through configured /v1/rerank APIs."""

import time
from typing import Dict, List
from urllib.parse import urlsplit, urlunsplit

import requests

from app.settings import Settings, settings
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class Reranker:
    """Rerank recalled documents through the configured rerank endpoint."""

    def __init__(self, settings_snapshot: Settings | None = None):
        """Bind rerank requests to one optional runtime settings snapshot."""
        self.settings_snapshot = settings_snapshot or settings
        self.api_key = (
            self.settings_snapshot.rerank_api_key
            or self.settings_snapshot.embedding_api_key
        )
        self.base_url = (
            self.settings_snapshot.rerank_base_url
            or self.settings_snapshot.embedding_base_url
        )
        self.model = self.settings_snapshot.rerank_model
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def rerank(
        self,
        query: str,
        documents: List[str],
        top_n: int | None = None,
    ) -> List[Dict[str, float]]:
        """Rerank candidate documents for one query."""
        if not documents:
            return []

        payload = {
            "model": self.model,
            "query": query,
            "documents": documents,
            "return_documents": False,
        }
        if top_n is not None:
            payload["top_n"] = top_n

        response = None
        for attempt in range(1, self.settings_snapshot.rerank_max_retries + 1):
            response = requests.post(
                self._rerank_url(),
                headers=self.headers,
                json=payload,
                timeout=60,
            )

            if response.status_code != 429:
                response.raise_for_status()
                break

            if attempt == self.settings_snapshot.rerank_max_retries:
                response.raise_for_status()

            logger.warning(
                "Rerank request hit rate limit on attempt "
                f"{attempt}/{self.settings_snapshot.rerank_max_retries}; sleeping "
                f"{self.settings_snapshot.rerank_retry_backoff_seconds}s before retry"
            )
            time.sleep(self.settings_snapshot.rerank_retry_backoff_seconds)

        results = response.json().get("results", [])
        logger.info(f"Reranked {len(documents)} candidates via configured API")
        return results

    def _rerank_url(self) -> str:
        """Normalize configured base URL to the official rerank endpoint."""
        parsed = urlsplit(self.base_url.rstrip("/"))
        path = parsed.path.rstrip("/")

        if path.endswith("/v1/rerank"):
            normalized_path = path
        elif path.endswith("/v1"):
            normalized_path = f"{path}/rerank"
        elif path:
            normalized_path = f"{path}/v1/rerank"
        else:
            normalized_path = "/v1/rerank"

        return urlunsplit((parsed.scheme, parsed.netloc, normalized_path, "", ""))
