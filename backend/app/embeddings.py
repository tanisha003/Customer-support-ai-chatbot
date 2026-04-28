"""Embeddings via Jina AI's free hosted API.

Why not sentence-transformers? It loads PyTorch (~600 MB resident) which
exhausts Render free tier's 512 MB RAM. By calling a hosted API instead,
we keep the app's memory footprint small enough to run on free hosts.

Jina AI's free tier: 1M tokens, no credit card required.
Get your free key at https://jina.ai/?sui=apikey
The default key embedded below works without signup but is rate-limited
to community use — set JINA_API_KEY for production volumes.
"""
from __future__ import annotations

import logging
from functools import lru_cache
from typing import List

import httpx
from langchain_core.embeddings import Embeddings

from app.config import get_settings

logger = logging.getLogger(__name__)

JINA_API_URL = "https://api.jina.ai/v1/embeddings"
JINA_MODEL = "jina-embeddings-v2-small-en"  # 512 dims, English, fast
EMBEDDING_DIM = 512


class JinaEmbeddings(Embeddings):
    """LangChain-compatible Embeddings wrapper around Jina's HTTP API.

    Implements both `embed_documents` (batch) and `embed_query` (single).
    Returns L2-normalized vectors so cosine similarity works out of the box.
    """

    def __init__(self, api_key: str, model: str = JINA_MODEL) -> None:
        self.api_key = api_key
        self.model = model
        self._client = httpx.Client(
            timeout=httpx.Timeout(connect=10.0, read=60.0, write=10.0, pool=10.0),
        )

    def _embed(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "input": texts,
            "normalized": True,
        }

        try:
            resp = self._client.post(JINA_API_URL, json=payload, headers=headers)
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            logger.error("Jina embeddings request failed: %s", exc)
            raise RuntimeError(
                "Embeddings API call failed. Check JINA_API_KEY and network."
            ) from exc

        data = resp.json()
        # Sort by index to preserve input order (Jina returns them in order, but be safe)
        items = sorted(data.get("data", []), key=lambda d: d.get("index", 0))
        return [item["embedding"] for item in items]

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        # Batch in chunks of 64 to keep payloads small
        out: List[List[float]] = []
        BATCH = 64
        for i in range(0, len(texts), BATCH):
            batch = texts[i : i + BATCH]
            out.extend(self._embed(batch))
            logger.debug("Embedded batch %d/%d", i // BATCH + 1, (len(texts) + BATCH - 1) // BATCH)
        return out

    def embed_query(self, text: str) -> List[float]:
        result = self._embed([text])
        return result[0] if result else [0.0] * EMBEDDING_DIM


@lru_cache(maxsize=1)
def get_embeddings() -> JinaEmbeddings:
    """Return a process-wide cached Jina embeddings client."""
    settings = get_settings()
    if not settings.jina_api_key:
        raise RuntimeError(
            "JINA_API_KEY is not set. Get a free key at https://jina.ai/?sui=apikey "
            "and set it in your .env or in your host's environment variables."
        )
    return JinaEmbeddings(api_key=settings.jina_api_key)
