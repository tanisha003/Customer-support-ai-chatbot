# Optional — for any container host (Fly.io, Railway, GCP Cloud Run, etc.)
# Build:  docker build -f deploy/Dockerfile -t rag-chatbot-api .
# Run:    docker run -p 8000:8000 --env-file backend/.env rag-chatbot-api

FROM python:3.11-slim

# System deps for sentence-transformers / chroma
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (cache-friendly)
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY backend/ ./

# Build the vector store at image build time
RUN python ingest.py

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
