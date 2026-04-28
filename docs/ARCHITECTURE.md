# Architecture

## High-Level Diagram

```mermaid
flowchart LR
    subgraph Client
        UI[React Frontend<br/>Vite + Tailwind]
    end

    subgraph Server[FastAPI Backend]
        ROUTES["/health · /sources · /chat"]
        RAG[RAG Chain<br/>retrieve → prompt → stream]
        LLM[LLM Provider<br/>Ollama / Groq]
    end

    subgraph Storage
        VS[(ChromaDB<br/>persistent)]
        KB[knowledge_base/<br/>*.pdf · *.md · *.txt]
    end

    UI -->|POST /chat<br/>question| ROUTES
    ROUTES --> RAG
    RAG -->|top-k similarity| VS
    RAG -->|prompt + context| LLM
    LLM -->|tokens| RAG
    RAG -->|SSE stream| ROUTES
    ROUTES -->|tokens + sources| UI
    KB -.python ingest.py.-> VS
```

## Data Flow

### Offline — Ingestion (`ingest.py`)
1. Walk `knowledge_base/` recursively
2. Load each `.pdf` (PyPDFLoader) / `.md` / `.txt` (TextLoader)
3. Split with `RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)`
4. Stamp metadata: `{ "source": <filename>, "chunk_index": <n> }`
5. Embed with `sentence-transformers/all-MiniLM-L6-v2` (CPU, normalized)
6. Persist to Chroma at `./chroma_db/`

### Online — Query (`POST /chat`)
1. Frontend sends `{ "question": "..." }`
2. Backend embeds the question with the same model
3. Chroma returns top-4 chunks with relevance scores in [0, 1]
4. Filter: drop chunks below `SIMILARITY_THRESHOLD` (default 0.3)
5. **If nothing remains** → stream the fallback message and stop (no LLM call)
6. Otherwise build the strict system prompt with retrieved context
7. Stream tokens from the LLM (Ollama or Groq) with `temperature=0.1`
8. Emit a final SSE event with the deduplicated source list

## Strict Anti-Hallucination Prompt

```
You are a customer support assistant. Answer the user's question using ONLY the
context below. If the context does not contain the answer, reply EXACTLY with:
"I don't have information on that in the knowledge base."

Do not invent facts. Do not use outside knowledge. Be concise and direct.
Cite the source filenames you used at the end of your answer in this exact format:
Sources: <comma-separated filenames>

CONTEXT:
{context}

QUESTION:
{question}

ANSWER:
```

## Module Map

| File | Responsibility |
|---|---|
| `app/main.py` | FastAPI app, CORS, routes, lifespan |
| `app/config.py` | Pydantic-settings, env-var loading |
| `app/embeddings.py` | Cached HuggingFace embedding singleton |
| `app/rag.py` | Vector store access, retrieval, prompt building, streaming generator |
| `app/llm.py` | Provider switch — Ollama via `httpx`, Groq via `groq` SDK |
| `app/schemas.py` | Pydantic request/response models |
| `app/logging_config.py` | Structured logging |
| `ingest.py` | One-shot CLI: load → chunk → embed → persist |
| `frontend/src/App.jsx` | Top-level state, health check, send orchestration |
| `frontend/src/api.js` | SSE client (fetchEventSource), fetch helpers |
| `frontend/src/components/*` | ChatWindow, Message, InputBox, SourcePill |

## Production Topology ($0/month)

```
┌──────────────────┐                  ┌──────────────────────┐
│  Netlify (Free)  │                  │  Render (Free Tier)  │
│  Frontend (Vite) │ ────HTTPS────▶  │  FastAPI + Chroma    │
└──────────────────┘                  └──────────┬───────────┘
                                                 │
                                                 ▼
                                      ┌──────────────────────┐
                                      │  Groq API (Free Tier)│
                                      └──────────────────────┘
```

- **Render Free** runs the FastAPI app with a 1 GB persistent disk for Chroma.
- **Netlify Free** serves the Vite-built static frontend.
- **Groq Free** replaces Ollama in cloud (Render free tier can't host Ollama).
- All three free tiers cover the demo with zero recurring cost.

## Performance Targets

| Metric | Local (Ollama) | Cloud (Groq) |
|---|---|---|
| First token | < 2 s | < 1 s |
| Full 200-token answer | < 8 s | < 3 s |
| Ingestion of 50 pages | < 30 s | n/a |

## Security Notes

- No authentication in v1 — fine for demo, called out in the README.
- CORS strictly limited to `ALLOWED_ORIGINS` in production.
- Secrets only in `.env` — `.env.example` is committed, real `.env` is gitignored.
- No PII logged; question strings are truncated to 100 chars in logs.
