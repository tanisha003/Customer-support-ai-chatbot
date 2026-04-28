# API Reference

Base URL (local): `http://localhost:8000`

All endpoints are JSON unless specified. CORS allows the origin(s) listed in `ALLOWED_ORIGINS`.

---

## `GET /health`

Liveness probe. Returns 503 if the vector store hasn't been built yet.

### Response — `200 OK`
```json
{
  "status": "ok",
  "vector_store": "ready",
  "documents_indexed": 3
}
```

### Response — `503 Service Unavailable`
```json
{
  "detail": "Vector store not found at './chroma_db'. Run `python ingest.py` to build it."
}
```

---

## `GET /sources`

Lists every unique source filename indexed in the vector store.

### Response — `200 OK`
```json
{
  "sources": ["product_faq.md", "returns_policy.md", "shipping_policy.md"],
  "count": 3
}
```

---

## `POST /chat`

Streaming Server-Sent Events endpoint.

### Request body
```json
{ "question": "What's your return policy?" }
```

| Field | Type | Constraints |
|---|---|---|
| `question` | string | 1–1000 characters |

### Response — `text/event-stream`

Each line is `data: <JSON>`. Three event shapes:

**Token event** (zero or more, in order):
```
data: {"token": "Our "}

data: {"token": "return "}

data: {"token": "window "}
```

**Done event** (always last on success):
```
data: {"sources": ["returns_policy.md"], "done": true}
```

**Error event** (terminal):
```
data: {"error": "Could not reach Ollama. Is `ollama serve` running?"}
```

### Behavior

- If retrieval finds no chunks above the similarity threshold, the bot streams the fallback message **without calling the LLM**:

  > I don't have information on that in the knowledge base.

- Empty / whitespace-only / >1000-char questions get a `422 Unprocessable Entity` from Pydantic before the stream starts.

### Curl example
```bash
curl -N -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "How long does shipping take?"}'
```

The `-N` flag disables curl buffering so you see tokens as they arrive.

---

## `GET /`

Friendly landing JSON listing endpoints.

### Response
```json
{
  "name": "Customer Support RAG Chatbot",
  "version": "1.0.0",
  "endpoints": ["/health", "/sources", "/chat"],
  "docs": "/docs"
}
```

FastAPI also auto-generates Swagger UI at `/docs` and ReDoc at `/redoc`.
