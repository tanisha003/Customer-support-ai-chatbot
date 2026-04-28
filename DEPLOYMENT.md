# Deployment Guide

**Frontend on Vercel + backend on Render + LLM via Groq** — total cost: $0/month.

The repo is already deployment-ready:
- `render.yaml` at the repo root — Render auto-discovers it on Blueprint import.
- `frontend/vercel.json` — Vercel auto-detects it (Vite framework, SPA rewrites, security headers).
- `backend/runtime.txt` and `backend/Procfile` — standard pin/start specs.

> **About Render's free tier (Jan 2026 onward):** Render no longer provides persistent disks on the free plan. This project handles that automatically — the FastAPI app rebuilds the vector store in `/tmp` on each cold start. No upgrade needed. See "Cold start behaviour" at the bottom for what users will experience.

---

## Phase A — Pre-deploy checklist

- [ ] Project runs locally end-to-end (Ollama or Groq)
- [ ] Secrets in `.env` files only — never committed (`.env.example` is the template)
- [ ] `requirements.txt` and `package.json` versions are pinned (already done)
- [ ] `python ingest.py` succeeds on a fresh venv
- [ ] GitHub repo created, code pushed to `main`

---

## Phase B — Get a free Groq API key (2 min)

Render's free tier can't run Ollama (RAM-limited). Groq's free tier replaces it — same code path, faster inference.

1. Go to [console.groq.com](https://console.groq.com)
2. Sign up (Google/GitHub login works)
3. **API Keys** → **Create API Key** → copy it (starts with `gsk_…`)
4. Free tier: ~30 req/min, 14,400 req/day

Test it locally first by setting in `backend/.env`:
```
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_your_key_here
```
Restart the backend, ask a question, confirm streaming still works, then commit and push (without the key — `.env` is gitignored).

---

## Phase C — Deploy backend to Render (10 min)

### C.1 Push to GitHub
```bash
git init
git add .
git commit -m "feat: initial RAG chatbot"
git branch -M main
git remote add origin https://github.com/<your-username>/customer-support-rag-chatbot.git
git push -u origin main
```

### C.2 Create the Render service
1. Open [dashboard.render.com](https://dashboard.render.com)
2. **New +** → **Blueprint** → connect GitHub → select the repo
3. Render reads `render.yaml` and proposes a service named `rag-chatbot-api`. Click **Apply**.

### C.3 Add the two secrets
Render flagged `GROQ_API_KEY` and `ALLOWED_ORIGINS` as `sync: false` in the Blueprint, so you set them in the dashboard.

In the service → **Environment** tab:

| Key | Value |
|---|---|
| `GROQ_API_KEY` | `gsk_…` (your key) |
| `ALLOWED_ORIGINS` | `*` (you'll tighten this after the frontend deploys) |

Render auto-redeploys on save. The build itself takes ~3 min (just `pip install`). The first HTTP request after the build wakes the app and triggers vector-store ingest in `/tmp` — that takes another ~30s.

### C.4 Verify the backend
- Open `https://rag-chatbot-api.onrender.com/health`
- The first hit may return `503` for ~30 seconds while ingest runs. Wait, refresh, and you should see:
  ```json
  {"status":"ok","vector_store":"ready","documents_indexed":3}
  ```
- Open `https://rag-chatbot-api.onrender.com/sources` → lists your KB files.

> **Free-tier cold starts:** Render free services sleep after 15 min idle. Each wake re-runs the in-memory ingest because `/tmp` resets — first request after a sleep takes ~30s. Subsequent requests are fast.

Note your service URL — you'll paste it into Vercel next.

---

## Phase D — Deploy frontend to Vercel (5 min)

### D.1 Import the repo
1. Open [vercel.com/new](https://vercel.com/new)
2. **Import Git Repository** → pick your repo

### D.2 Configure the project
Vercel auto-detects Vite, but the **Root Directory** matters because the frontend is in a subfolder:

| Setting | Value |
|---|---|
| **Framework Preset** | `Vite` (auto-detected) |
| **Root Directory** | `frontend` ← important — click "Edit" and set this |
| **Build Command** | `npm run build` (auto-filled) |
| **Output Directory** | `dist` (auto-filled) |
| **Install Command** | `npm install` (auto-filled) |

`vercel.json` inside `frontend/` configures SPA rewrites and security headers — no further setup needed.

### D.3 Add the env var
Before clicking Deploy, expand **Environment Variables** and add:

| Key | Value |
|---|---|
| `VITE_API_URL` | `https://rag-chatbot-api.onrender.com` (your Render URL, **no trailing slash**) |

Apply to all three environments (Production, Preview, Development).

### D.4 Deploy
Click **Deploy**. ~90 seconds later you have a URL like `https://customer-support-rag-chatbot.vercel.app`. Optionally rename under **Settings → Domains** or add a custom domain.

---

## Phase E — Lock CORS

Back in Render → **Environment** → update:
```
ALLOWED_ORIGINS=https://your-app.vercel.app
```
Render redeploys automatically. Your frontend can now talk to your backend, and nothing else can.

---

## Phase F — Smoke test production

Open your Vercel URL and confirm:
- [ ] **Wait through the cold start.** First message after a long idle takes ~30–45s. Subsequent messages stream in real time.
- [ ] Tap each suggestion chip → cited answer appears
- [ ] Ask off-topic ("Who won the 2024 World Cup?") → fallback message
- [ ] Empty input — submit button stays disabled
- [ ] Mobile view — open on phone, layout responsive
- [ ] Refresh — session resets cleanly
- [ ] Browser DevTools → Network → POST `/chat` shows SSE `data:` events streaming

---

## Cold start behaviour (what your users will see)

Render's free tier puts the service to sleep after 15 minutes of inactivity. When the next user arrives:

1. **Container wake** (~5–10s) — Render starts the Python process
2. **Vector store rebuild** (~25–35s) — `app/main.py` lifespan runs `ingest.py` because `/tmp` was wiped
3. **First answer** — streams normally

After that, **all subsequent requests are fast** (top-k retrieval + Groq inference, well under 3 seconds end-to-end) until the service idles again.

For a portfolio demo this is fine — interviewers understand free-tier cold starts. Add this note to your README so visitors aren't confused:

> *First message after inactivity may take ~30 seconds to wake up the free-tier backend. Subsequent messages stream in real time.*

If you ever want to eliminate cold starts, upgrade Render to the **Starter plan ($7/mo)** — it stays warm 24/7 and you can re-add a persistent disk so ingest only runs on deploy.

---

## Updating the knowledge base

Drop new files into `backend/knowledge_base/` and push:
```bash
git add backend/knowledge_base/
git commit -m "docs: update FAQ"
git push
```
Render redeploys automatically. The next request triggers a fresh ingest with the new docs.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `disks are not supported for free tier services` | Already fixed in `render.yaml` — make sure your repo has the latest version (no `disk:` block) |
| Render build OOM on `sentence-transformers` | Free tier RAM is tight — wait 5 min and retry. Almost always works on second attempt |
| `/health` returns 503 for >2 min after deploy | Check service logs for ingest errors; restart via "Manual Deploy" → "Deploy latest commit" |
| Vercel build can't find `package.json` | Root Directory not set to `frontend` — fix in Vercel project settings |
| Browser CORS error | `ALLOWED_ORIGINS` on Render must match your Vercel URL exactly (incl. `https://`) |
| `VITE_API_URL` undefined in production | Vercel env vars apply at build time — redeploy after adding |
| First message takes 30s | Free-tier cold start with in-memory ingest — expected |
| Groq returns 429 | Hit free-tier rate limit; wait or upgrade |

---

## Alternative backend hosts (if Render doesn't fit)

| Host | Backend free tier? | Notes |
|---|---|---|
| **Railway** | $5 credit/mo | Cleaner UX, Docker-native, persistent volumes available |
| **Fly.io** | Generous free | Great for FastAPI, requires CLI, persistent volumes available |
| **Hugging Face Spaces** | Free CPU | Self-contained option, persistent storage included |

The included [`deploy/Dockerfile`](deploy/Dockerfile) works for any container host. The frontend stays on Vercel either way.

---

## Post-deploy: update your resume

Replace the placeholder lines in your LaTeX resume with your live URLs:

> **Customer Support Chatbot — RAG-Based AI Assistant** &nbsp;|&nbsp; [Live Demo](https://your-app.vercel.app) &nbsp;|&nbsp; [GitHub](https://github.com/<you>/customer-support-rag-chatbot)
> *React.js · FastAPI · LangChain · ChromaDB · Groq · Vercel · Render*
