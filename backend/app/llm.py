"""LLM provider abstraction — Ollama (local) and Groq (cloud).

Both providers expose a single async generator: `stream_completion(prompt)`.
Switching is done via the LLM_PROVIDER env var; the rest of the app does not
care which one is in use.
"""
from __future__ import annotations

import logging
from typing import AsyncIterator

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────
# Public entry point
# ──────────────────────────────────────────────────────────────────────
async def stream_completion(prompt: str) -> AsyncIterator[str]:
    """Stream LLM tokens for the given prompt, regardless of provider."""
    settings = get_settings()

    if settings.llm_provider == "ollama":
        async for token in _stream_ollama(prompt):
            yield token
    elif settings.llm_provider == "groq":
        async for token in _stream_groq(prompt):
            yield token
    else:
        raise ValueError(f"Unknown LLM_PROVIDER: {settings.llm_provider!r}")


# ──────────────────────────────────────────────────────────────────────
# Ollama (local) — uses the native /api/generate streaming endpoint
# ──────────────────────────────────────────────────────────────────────
async def _stream_ollama(prompt: str) -> AsyncIterator[str]:
    settings = get_settings()
    url = f"{settings.ollama_base_url.rstrip('/')}/api/generate"
    payload = {
        "model": settings.ollama_model,
        "prompt": prompt,
        "stream": True,
        "options": {"temperature": 0.1},
    }

    timeout = httpx.Timeout(connect=10.0, read=120.0, write=10.0, pool=10.0)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream("POST", url, json=payload) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line:
                        continue
                    # Each line is a JSON object: {"response": "...", "done": false}
                    import json

                    try:
                        chunk = json.loads(line)
                    except json.JSONDecodeError:
                        logger.debug("Skipping malformed Ollama line: %s", line)
                        continue
                    token = chunk.get("response", "")
                    if token:
                        yield token
                    if chunk.get("done"):
                        return
    except httpx.HTTPError as exc:
        logger.error("Ollama request failed: %s", exc)
        raise RuntimeError(
            "Could not reach Ollama. Is `ollama serve` running and is the model "
            f"`{settings.ollama_model}` pulled?"
        ) from exc


# ──────────────────────────────────────────────────────────────────────
# Groq (cloud) — OpenAI-compatible streaming via the official SDK
# ──────────────────────────────────────────────────────────────────────
async def _stream_groq(prompt: str) -> AsyncIterator[str]:
    settings = get_settings()
    if not settings.groq_api_key:
        raise RuntimeError(
            "GROQ_API_KEY is not set. Add it to your .env or get one at "
            "https://console.groq.com"
        )

    # Imported lazily so people running Ollama-only don't pay the import cost.
    from groq import AsyncGroq

    client = AsyncGroq(api_key=settings.groq_api_key)
    try:
        stream = await client.chat.completions.create(
            model=settings.groq_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            stream=True,
        )
        async for event in stream:
            if not event.choices:
                continue
            delta = event.choices[0].delta
            token = getattr(delta, "content", None)
            if token:
                yield token
    except Exception as exc:  # groq SDK raises various typed errors
        logger.error("Groq request failed: %s", exc)
        raise RuntimeError(f"Groq API call failed: {exc}") from exc
