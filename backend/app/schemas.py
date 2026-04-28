"""Pydantic request and response models."""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Incoming chat request."""

    question: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="The user's question. 1–1000 characters.",
    )


class ChatTokenEvent(BaseModel):
    """A single streamed token event."""

    token: str


class ChatDoneEvent(BaseModel):
    """Final SSE event with the source list."""

    sources: List[str] = Field(default_factory=list)
    done: bool = True


class ChatErrorEvent(BaseModel):
    """SSE error event."""

    error: str


class HealthResponse(BaseModel):
    """Liveness probe response."""

    status: str
    vector_store: str
    documents_indexed: int


class SourcesResponse(BaseModel):
    """List of indexed source filenames."""

    sources: List[str]
    count: int


class RetrievedChunk(BaseModel):
    """An individual retrieved chunk for internal use."""

    content: str
    source: str
    score: float
    chunk_index: Optional[int] = None
