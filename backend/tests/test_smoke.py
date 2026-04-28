"""Smoke tests — assume the vector store has been built via `python ingest.py`.

Run from the backend/ directory:
    pytest -v

These tests exercise the retrieval layer only (no LLM call), which keeps them
fast and offline-friendly.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# Make `app` importable
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.rag import retrieve, FALLBACK_MESSAGE  # noqa: E402

CHROMA_DIR = Path(__file__).parent.parent / "chroma_db"

pytestmark = pytest.mark.skipif(
    not CHROMA_DIR.is_dir(),
    reason="Chroma store not built yet — run `python ingest.py` first.",
)


# ──────────────────────────────────────────────────────────────────────
# Questions that ARE in the knowledge base
# ──────────────────────────────────────────────────────────────────────
IN_KB_QUESTIONS = [
    ("What is the return window?", "returns_policy.md"),
    ("How long does shipping take in metro cities?", "shipping_policy.md"),
    ("In which cities is PrimeStay available?", "product_faq.md"),
    ("What payment methods are accepted?", "product_faq.md"),
    ("Is Cash on Delivery available?", "shipping_policy.md"),
]


# ──────────────────────────────────────────────────────────────────────
# Off-topic questions that should retrieve nothing meaningful
# ──────────────────────────────────────────────────────────────────────
OFF_TOPIC_QUESTIONS = [
    "Who won the 2024 World Cup?",
    "Explain the theory of relativity.",
]


@pytest.mark.parametrize("question,expected_source", IN_KB_QUESTIONS)
def test_retrieves_relevant_chunks(question: str, expected_source: str) -> None:
    chunks = retrieve(question)
    assert chunks, f"No chunks retrieved for in-KB question: {question!r}"
    sources = {c.source for c in chunks}
    assert expected_source in sources, (
        f"Expected source {expected_source!r} for question {question!r}, "
        f"got {sources}"
    )


@pytest.mark.parametrize("question", OFF_TOPIC_QUESTIONS)
def test_off_topic_returns_few_or_no_chunks(question: str) -> None:
    chunks = retrieve(question)
    # We don't strictly require zero chunks; we require the retrieval system
    # to either return nothing OR very low-confidence matches that the
    # threshold filter would reject in production. The fact that retrieve()
    # already applies the threshold means anything coming back here scored
    # above 0.3 — we just assert it's a small list.
    assert len(chunks) <= 2, (
        f"Off-topic question {question!r} retrieved too many chunks: "
        f"{[c.source for c in chunks]}"
    )


def test_fallback_message_is_stable() -> None:
    """Lightweight sanity check on the constant we expose."""
    assert FALLBACK_MESSAGE.startswith("I don't have information")
