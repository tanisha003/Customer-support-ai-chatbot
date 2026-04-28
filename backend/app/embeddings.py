"""HuggingFace sentence-transformers embeddings — single shared instance."""
from __future__ import annotations

from functools import lru_cache

from langchain_huggingface import HuggingFaceEmbeddings

# Lightweight, fast, well-tested. 384-dim, ~80 MB on disk.
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


@lru_cache(maxsize=1)
def get_embeddings() -> HuggingFaceEmbeddings:
    """Return a process-wide cached embedding model.

    Loaded lazily on first call. Subsequent calls return the same instance,
    so we avoid reloading the ~80 MB model on every request.
    """
    return HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL_NAME,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )
