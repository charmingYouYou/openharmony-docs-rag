"""Synchronous embedding generation for configured /v1/embeddings APIs."""

import time
from urllib.parse import urlsplit, urlunsplit
from typing import List

import requests

from app.settings import settings
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class Embedder:
    """Generate embeddings through the configured embeddings endpoint."""

    def __init__(self):
        self.api_key = settings.embedding_api_key
        self.base_url = settings.embedding_base_url
        self.model = settings.embedding_model
        self.document_input_type = settings.embedding_document_input_type
        self.query_input_type = settings.embedding_query_input_type
        self.document_prefix = settings.embedding_document_prefix
        self.query_prefix = settings.embedding_query_prefix
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def embed_text(self, text: str) -> List[float]:
        """Generate one query embedding."""
        return self._embed(
            [self._apply_prefix(text, self.query_prefix)],
            input_type=self.query_input_type,
        )[0]

    def embed_batch(
        self, texts: List[str], text_type: str | None = None
    ) -> List[List[float]]:
        """Generate embeddings for many texts."""
        prepared_texts = [self._apply_prefix(text, self.document_prefix) for text in texts]
        return self._embed(
            prepared_texts,
            input_type=text_type or self.document_input_type,
        )

    def _embed(self, texts: List[str], input_type: str) -> List[List[float]]:
        if not texts:
            return []

        response = None
        for attempt in range(1, settings.embedding_max_retries + 1):
            response = requests.post(
                self._embeddings_url(),
                headers=self.headers,
                json={
                    "model": self.model,
                    "input": texts,
                    "input_type": input_type,
                },
                timeout=60,
            )

            if response.status_code != 429:
                response.raise_for_status()
                break

            if attempt == settings.embedding_max_retries:
                response.raise_for_status()

            logger.warning(
                "Embedding request hit rate limit on attempt "
                f"{attempt}/{settings.embedding_max_retries}; sleeping "
                f"{settings.embedding_retry_backoff_seconds}s before retry"
            )
            time.sleep(settings.embedding_retry_backoff_seconds)

        payload = response.json()
        data = payload.get("data", [])
        embeddings = [item["embedding"] for item in data if "embedding" in item]

        if len(embeddings) != len(texts):
            raise ValueError(
                f"Incomplete embedding response: expected {len(texts)} embeddings, got {len(embeddings)}"
            )

        logger.info(f"Generated {len(embeddings)} embeddings via configured API")
        return embeddings

    def _embeddings_url(self) -> str:
        """Normalize configured base URL to the official embeddings endpoint."""
        parsed = urlsplit(self.base_url.rstrip("/"))
        path = parsed.path.rstrip("/")

        if path.endswith("/v1/embeddings"):
            normalized_path = path
        elif path.endswith("/v1"):
            normalized_path = f"{path}/embeddings"
        elif path:
            normalized_path = f"{path}/v1/embeddings"
        else:
            normalized_path = "/v1/embeddings"

        return urlunsplit((parsed.scheme, parsed.netloc, normalized_path, "", ""))

    def _apply_prefix(self, text: str, prefix: str) -> str:
        """Prepend an optional configured prefix to the text payload."""
        if not prefix:
            return text
        return f"{prefix.replace('\\n', '\n')}{text}"
