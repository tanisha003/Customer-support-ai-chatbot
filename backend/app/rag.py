"""Retrieval-Augmented Generation chain.

Responsibilities:
- Open the persisted Chroma collection and expose a retriever.
- Convert a user question into top-k retrieved chunks.
- Apply the similarity threshold; return the standard fallback if nothing relevant.
- Build a strict, anti-hallucination prompt with retrieved context.
- Stream LLM tokens, then emit a final sources event.
"""
from __future__ import annotations

import logging
import os
from functools import lru_cache
from typing import AsyncIterator, List, Tuple

from langchain_chroma import Chroma

from app.config import get_settings
from app.embeddings import get_embeddings
from app.llm import stream_completion
from app.schemas import RetrievedChunk

logger = logging.getLogger(__name__)

FALLBACK_MESSAGE = "I don't have information on that in the knowledge base."

SYSTEM_PROMPT_TEMPLATE = """You are a customer support assistant. Answer the user's \
question using ONLY the context below. If the context does not contain the answer, \
reply EXACTLY with: "I don't have information on that in the knowledge base."

Do not invent facts. Do not use outside knowledge. Be concise and direct.
Cite the source filenames you used at the end of your answer in this exact format:
Sources: <comma-separated filenames>

CONTEXT:
{context}

QUESTION:
{question}

ANSWER:"""


# ──────────────────────────────────────────────────────────────────────
# Vector store access
# ──────────────────────────────────────────────────────────────────────
@lru_cache(maxsize=1)
def get_vectorstore() -> Chroma:
    """Open the persisted Chroma collection (cached process-wide)."""
    settings = get_settings()
    if not os.path.isdir(settings.chroma_dir):
        raise RuntimeError(
            f"Chroma directory not found at {settings.chroma_dir!r}. "
            "Run `python ingest.py` first to build the vector store."
        )
    return Chroma(
        collection_name=settings.chroma_collection,
        embedding_function=get_embeddings(),
        persist_directory=settings.chroma_dir,
    )


def get_indexed_sources() -> List[str]:
    """Return the unique list of source filenames currently indexed."""
    try:
        vs = get_vectorstore()
        # Chroma exposes the underlying collection
        col = vs._collection  # type: ignore[attr-defined]
        data = col.get(include=["metadatas"])
        metadatas = data.get("metadatas") or []
        sources = sorted({m.get("source", "") for m in metadatas if m})
        return [s for s in sources if s]
    except Exception as exc:
        logger.warning("Could not list indexed sources: %s", exc)
        return []


def count_indexed_documents() -> int:
    """Return the number of unique source documents indexed."""
    return len(get_indexed_sources())


# ──────────────────────────────────────────────────────────────────────
# Retrieval
# ──────────────────────────────────────────────────────────────────────
def retrieve(question: str) -> List[RetrievedChunk]:
    """Top-k similarity search with score threshold filtering."""
    settings = get_settings()
    vs = get_vectorstore()

    # similarity_search_with_relevance_scores returns scores in [0, 1] where higher = better.
    # (Chroma's raw distance is converted via the embedding function's relevance method.)
    results: List[Tuple] = vs.similarity_search_with_relevance_scores(
        question, k=settings.top_k
    )

    chunks: List[RetrievedChunk] = []
    for doc, score in results:
        if score < settings.similarity_threshold:
            continue
        chunks.append(
            RetrievedChunk(
                content=doc.page_content,
                source=doc.metadata.get("source", "unknown"),
                score=float(score),
                chunk_index=doc.metadata.get("chunk_index"),
            )
        )

    logger.info(
        "retrieve: question=%r kept=%d/%d top_score=%.3f",
        question[:80],
        len(chunks),
        len(results),
        chunks[0].score if chunks else 0.0,
    )
    return chunks


# ──────────────────────────────────────────────────────────────────────
# Prompt construction
# ──────────────────────────────────────────────────────────────────────
def build_prompt(question: str, chunks: List[RetrievedChunk]) -> str:
    """Format retrieved chunks into the system prompt."""
    context_parts: List[str] = []
    for i, c in enumerate(chunks, start=1):
        context_parts.append(f"[{i}] Source: {c.source}\n{c.content.strip()}")
    context = "\n\n".join(context_parts) if context_parts else "(no context retrieved)"
    return SYSTEM_PROMPT_TEMPLATE.format(context=context, question=question.strip())


# ──────────────────────────────────────────────────────────────────────
# Top-level streaming generator
# ──────────────────────────────────────────────────────────────────────
async def answer_stream(question: str) -> AsyncIterator[dict]:
    """Yield SSE-ready dicts: token events, then a final done event.

    Output contract:
    - {"token": "..."} for each generated token
    - {"sources": [...], "done": True} as the final event
    - {"error": "..."} if something went wrong (terminal)
    """
    chunks = retrieve(question)

    # Empty / weak retrieval → fallback, do NOT call the LLM.
    if not chunks:
        for ch in FALLBACK_MESSAGE:
            yield {"token": ch}
        yield {"sources": [], "done": True}
        return

    prompt = build_prompt(question, chunks)
    sources = sorted({c.source for c in chunks})

    try:
        async for token in stream_completion(prompt):
            yield {"token": token}
    except Exception as exc:
        logger.exception("LLM streaming failed")
        yield {"error": str(exc)}
        return

    yield {"sources": sources, "done": True}
