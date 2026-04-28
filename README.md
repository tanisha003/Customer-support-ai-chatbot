# Customer Support Chatbot — RAG-Based AI Assistant

> Production-grade Retrieval-Augmented Generation chatbot that answers customer queries from a custom knowledge base, with source citations and zero-hallucination guardrails.

![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![LangChain](https://img.shields.io/badge/LangChain-0.3-1C3C3C)
![ChromaDB](https://img.shields.io/badge/ChromaDB-0.5-FF6B6B)
![Vercel](https://img.shields.io/badge/Vercel-Frontend-black?logo=vercel)
![Render](https://img.shields.io/badge/Render-Backend-46E3B7?logo=render&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

---

## Architecture

```mermaid
flowchart LR
    A[React Frontend<br/>Vite + Tailwind<br/>on Vercel] -->|POST /chat| B[FastAPI Backend<br/>on Render]
    B -->|SSE stream| A
    B -->|similarity search| C[(ChromaDB<br/>persistent disk)]
    B -->|prompt + context| D[LLM<br/>Ollama / Groq]
    D -->|tokens| B
    E[knowledge_base/<br/>*.pdf, *.md, *.txt] -.ingest.py.-> C
```

## Features

- **Retrieval-Augmented Generation** — answers grounded in your own documents, never the LLM's general training.
- **Suggested questions** — topic chips inside the welcome message let users start with one tap.
- **Source citations** — every answer ends with the source filenames it drew from.
- **Zero-hallucination fallback** — when no chunk meets the similarity threshold, the bot says *"I don't have information on that"* instead of inventing.
- **Streaming responses** — Server-Sent Events stream tokens to the UI as they're generated.
- **Pluggable LLM** — swap between local Ollama and cloud Groq with one env var.
- **One-command re-indexing** — drop new docs into `knowledge_base/`, run `python ingest.py`.
- **Deployment-ready** — `render.yaml` and `frontend/vercel.json` are auto-discovered by their respective platforms.

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, Vite, Tailwind CSS, `@microsoft/fetch-event-source`, lucide-react |
| Backend | Python 3.11, FastAPI, sse-starlette, Pydantic v2 |
| Orchestration | LangChain (loaders, splitters, retrievers, LCEL) |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` (HuggingFace) |
| Vector DB | ChromaDB (persistent, local) |
| LLM | Ollama (`llama3.2:3b`) for local, Groq (`llama-3.1-8b-instant`) for cloud |
| Hosting | **Vercel** (frontend) + **Render** (backend) — both free tier |

## Prerequisites

- **Python 3.11+** ([download](https://www.python.org/downloads/))
- **Node.js 20+** ([download](https://nodejs.org/))
- **Ollama** for local LLM ([download](https://ollama.com)) — or a [Groq API key](https://console.groq.com) for cloud
- **Git**

## Quick Start (Local)

### 1. Clone and configure

```bash
git clone https://github.com/<your-username>/customer-support-rag-chatbot.git
cd customer-support-rag-chatbot
cp .env.example .env
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

### 2. Pull the local LLM

```bash
ollama pull llama3.2:3b
ollama serve   # leave running in its own terminal
```

### 3. Backend — install, ingest, serve

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python ingest.py                    # builds vector store from knowledge_base/
uvicorn app.main:app --reload --port 8000
```

Verify: open [http://localhost:8000/health](http://localhost:8000/health) — should return `{"status": "ok"}`.

### 4. Frontend — install and run

```bash
# new terminal
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) and start chatting. Tap any of the four suggested topic chips inside the welcome message to try the bot instantly.

### 5. Try it

| Question | Expected behavior |
|---|---|
| Tap "Return policy" chip | Cited answer from `returns_policy.md` |
| Tap "Shipping times" chip | Cited answer from `shipping_policy.md` |
| Tap "Available cities" chip | Cited answer from `product_faq.md` |
| "Who won the 2024 World Cup?" | Falls back: *"I don't have information on that..."* |

## Deployment ($0/month)

The repo is set up for **one-click deploys** — `render.yaml` at the root and `frontend/vercel.json` are auto-discovered.

**Why split hosts:** Vercel's serverless functions can't hold a persistent ChromaDB on disk. Render's free tier gives a 1 GB persistent disk and keeps the FastAPI process warm. Frontend goes to Vercel where static React deploys are best-in-class.

**1. Push to GitHub** — `git init && git add . && git commit -m "feat: initial RAG chatbot" && git push`

**2. Backend → Render**
- New → **Blueprint** → connect your repo → Render reads `render.yaml` and creates the service.
- In the Render dashboard set `GROQ_API_KEY` (free key from [console.groq.com](https://console.groq.com)) and `ALLOWED_ORIGINS` (your Vercel URL once the frontend deploys).
- A 1 GB persistent disk for ChromaDB is provisioned automatically.

**3. Frontend → Vercel**
- [vercel.com/new](https://vercel.com/new) → import your repo.
- **Set "Root Directory" to `frontend`** (this is the one manual step — Vercel needs to know the frontend isn't at the repo root).
- Vercel auto-detects Vite + reads `frontend/vercel.json`.
- Add env var `VITE_API_URL` = your Render URL (no trailing slash).

**4. Lock CORS** — in Render, set `ALLOWED_ORIGINS` to your final Vercel URL.

Full step-by-step (with screenshots and troubleshooting): see [`DEPLOYMENT.md`](DEPLOYMENT.md).

## API Reference

### `GET /health`
```json
{ "status": "ok", "vector_store": "ready", "documents_indexed": 3 }
```

### `POST /chat`
Streaming Server-Sent Events. Body: `{ "question": "..." }`. Stream emits `{"token": "..."}` events, ending with `{"sources": [...], "done": true}`.

### `GET /sources`
```json
{ "sources": ["product_faq.md", "shipping_policy.md", "returns_policy.md"], "count": 3 }
```

Full reference: [`docs/API.md`](docs/API.md).

## Project Structure

```
customer-support-rag-chatbot/
├── README.md
├── DEPLOYMENT.md                   # Step-by-step Vercel + Render walkthrough
├── LICENSE
├── .gitignore
├── .env.example
├── render.yaml                     # ← Auto-discovered by Render
│
├── backend/
│   ├── requirements.txt
│   ├── runtime.txt                 # Python 3.11.9 pin
│   ├── Procfile                    # Heroku-style start spec
│   ├── ingest.py                   # CLI to rebuild the vector store
│   ├── .env.example
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI app + routes
│   │   ├── config.py
│   │   ├── schemas.py
│   │   ├── embeddings.py
│   │   ├── llm.py                  # Ollama | Groq provider switch
│   │   ├── rag.py                  # Retrieval + generation chain
│   │   └── logging_config.py
│   ├── knowledge_base/
│   │   ├── product_faq.md
│   │   ├── shipping_policy.md
│   │   └── returns_policy.md
│   └── tests/
│       ├── __init__.py
│       └── test_smoke.py
│
├── frontend/
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   ├── vercel.json                 # ← Auto-discovered by Vercel
│   ├── index.html
│   ├── .env.example
│   ├── .env.production.example
│   ├── public/favicon.svg
│   └── src/
│       ├── main.jsx
│       ├── App.jsx
│       ├── api.js
│       ├── index.css
│       └── components/
│           ├── ChatWindow.jsx
│           ├── Message.jsx
│           ├── InputBox.jsx
│           ├── SourcePill.jsx
│           └── SuggestedQuestions.jsx
│
├── docs/
│   ├── ARCHITECTURE.md
│   └── API.md
│
└── deploy/
    ├── Dockerfile                  # Optional container deploy
    └── netlify.toml.example        # Reference — if you ever switch from Vercel
```

## Resume Bullets

- Designed and developed a Retrieval-Augmented Generation (RAG) system to answer customer queries from custom support documents, product FAQs, and knowledge-base articles — production pattern directly applicable to the Ace Team charter.
- Implemented document ingestion pipeline with chunking, embedding generation, and semantic search using a vector database (ChromaDB/FAISS) for accurate, low-hallucination contextual retrieval.
- Built RESTful APIs using FastAPI for seamless interaction between the React frontend and AI backend services, with streaming response support and clean separation of concerns.
- Grounded LLM outputs with retrieved document context, reducing hallucinations and ensuring factual, source-backed answers suitable for enterprise customer-facing deployment.

## License

MIT — see [LICENSE](LICENSE).
