"""FastAPI entry point — routes, CORS, lifespan."""
from __future__ import annotations

import json
import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

from app.config import get_settings
from app.logging_config import configure_logging
from app.rag import (
    answer_stream,
    count_indexed_documents,
    get_indexed_sources,
)
from app.schemas import ChatRequest, HealthResponse, SourcesResponse

configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Startup / shutdown hooks."""
    settings = get_settings()
    logger.info("=" * 60)
    logger.info("Customer Support RAG Chatbot starting")
    logger.info("LLM provider:     %s", settings.llm_provider)
    if settings.llm_provider == "ollama":
        logger.info("Ollama model:     %s @ %s", settings.ollama_model, settings.ollama_base_url)
    else:
        logger.info("Groq model:       %s", settings.groq_model)
    logger.info("Chroma dir:       %s", settings.chroma_dir)
    logger.info("Top-K / threshold: %d / %.2f", settings.top_k, settings.similarity_threshold)
    logger.info("CORS origins:     %s", settings.cors_origins)
    logger.info("=" * 60)
    yield
    logger.info("Shutting down")


app = FastAPI(
    title="Customer Support RAG Chatbot",
    description="Retrieval-Augmented Generation chatbot with streaming SSE.",
    version="1.0.0",
    lifespan=lifespan,
)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


# ──────────────────────────────────────────────────────────────────────
# Routes
# ──────────────────────────────────────────────────────────────────────
@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Liveness probe. 503 if the vector store is missing."""
    if not os.path.isdir(settings.chroma_dir):
        raise HTTPException(
            status_code=503,
            detail=(
                f"Vector store not found at {settings.chroma_dir!r}. "
                "Run `python ingest.py` to build it."
            ),
        )
    try:
        count = count_indexed_documents()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return HealthResponse(
        status="ok",
        vector_store="ready",
        documents_indexed=count,
    )


@app.get("/sources", response_model=SourcesResponse)
async def sources() -> SourcesResponse:
    """List indexed source filenames."""
    src = get_indexed_sources()
    return SourcesResponse(sources=src, count=len(src))


@app.post("/chat")
async def chat(req: ChatRequest) -> EventSourceResponse:
    """Stream a RAG answer as Server-Sent Events.

    Each event has `event: message` (default) and `data: <JSON>`.
    JSON shapes:
      - {"token": "..."} — partial token
      - {"sources": [...], "done": true} — final event
      - {"error": "..."} — terminal error
    """
    question = req.question.strip()
    logger.info("CHAT: %r", question[:100])

    async def event_generator() -> AsyncIterator[dict]:
        try:
            async for event in answer_stream(question):
                yield {"data": json.dumps(event)}
        except Exception as exc:
            logger.exception("Unhandled error in /chat stream")
            yield {"data": json.dumps({"error": str(exc)})}

    return EventSourceResponse(event_generator())


@app.get("/")
async def root() -> dict:
    """Friendly landing JSON."""
    return {
        "name": "Customer Support RAG Chatbot",
        "version": "1.0.0",
        "endpoints": ["/health", "/sources", "/chat"],
        "docs": "/docs",
    }
