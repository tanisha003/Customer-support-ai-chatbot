"""Build (or rebuild) the Chroma vector store from knowledge_base/.

Usage:
    python ingest.py
    python ingest.py --kb-dir ./knowledge_base --reset

Idempotent: by default, the existing collection is cleared before re-indexing.
"""
from __future__ import annotations

import argparse
import logging
import os
import shutil
import sys
from pathlib import Path
from typing import List

from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Make `app` importable when running this script directly
sys.path.insert(0, str(Path(__file__).parent))

from app.config import get_settings  # noqa: E402
from app.embeddings import get_embeddings  # noqa: E402
from app.logging_config import configure_logging  # noqa: E402

configure_logging()
logger = logging.getLogger("ingest")

SUPPORTED_EXTS = {".pdf", ".md", ".txt"}
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50


def discover_files(kb_dir: Path) -> List[Path]:
    """Recursively find all supported files under kb_dir."""
    if not kb_dir.is_dir():
        raise FileNotFoundError(f"Knowledge base directory not found: {kb_dir}")
    files = sorted(
        p for p in kb_dir.rglob("*") if p.is_file() and p.suffix.lower() in SUPPORTED_EXTS
    )
    return files


def load_file(path: Path) -> List[Document]:
    """Use the appropriate LangChain loader for each file type."""
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        loader = PyPDFLoader(str(path))
    else:
        # .md and .txt → plain text loader
        loader = TextLoader(str(path), encoding="utf-8")
    docs = loader.load()
    # Force the source metadata to be just the filename (not the full path)
    for d in docs:
        d.metadata["source"] = path.name
    return docs


def chunk_documents(docs: List[Document]) -> List[Document]:
    """Split docs into ~500-char chunks with 50-char overlap."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
        length_function=len,
    )
    chunks = splitter.split_documents(docs)
    # Add a per-source chunk index for traceability
    counters: dict = {}
    for c in chunks:
        src = c.metadata.get("source", "unknown")
        counters[src] = counters.get(src, 0) + 1
        c.metadata["chunk_index"] = counters[src]
    return chunks


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the Chroma vector store.")
    parser.add_argument(
        "--kb-dir",
        default="./knowledge_base",
        help="Path to the knowledge base directory (default: ./knowledge_base)",
    )
    parser.add_argument(
        "--keep-existing",
        action="store_true",
        help="Do NOT clear the existing collection before re-indexing.",
    )
    args = parser.parse_args()

    settings = get_settings()
    kb_dir = Path(args.kb_dir).resolve()
    chroma_dir = Path(settings.chroma_dir).resolve()

    logger.info("Knowledge base: %s", kb_dir)
    logger.info("Chroma dir:     %s", chroma_dir)
    logger.info("Collection:     %s", settings.chroma_collection)

    files = discover_files(kb_dir)
    if not files:
        logger.error("No %s files found under %s", SUPPORTED_EXTS, kb_dir)
        return 1
    logger.info("Found %d source file(s):", len(files))
    for f in files:
        logger.info("  - %s", f.name)

    # Reset existing store unless --keep-existing
    if chroma_dir.exists() and not args.keep_existing:
        logger.info("Clearing existing Chroma directory at %s", chroma_dir)
        shutil.rmtree(chroma_dir)

    chroma_dir.mkdir(parents=True, exist_ok=True)

    # Load + chunk
    all_docs: List[Document] = []
    for f in files:
        try:
            docs = load_file(f)
            all_docs.extend(docs)
            logger.info("Loaded %s (%d sub-doc(s))", f.name, len(docs))
        except Exception as exc:
            logger.error("Failed to load %s: %s", f.name, exc)

    if not all_docs:
        logger.error("No documents loaded — aborting.")
        return 2

    chunks = chunk_documents(all_docs)
    logger.info("Created %d chunks (chunk_size=%d, overlap=%d)", len(chunks), CHUNK_SIZE, CHUNK_OVERLAP)

    # Embed + persist
    logger.info("Loading embedding model (first run downloads ~80 MB) ...")
    embeddings = get_embeddings()

    logger.info("Embedding and writing to Chroma ...")
    Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        collection_name=settings.chroma_collection,
        persist_directory=str(chroma_dir),
    )

    # Summary
    sources = sorted({c.metadata.get("source", "?") for c in chunks})
    logger.info("=" * 60)
    logger.info("✅ Ingestion complete.")
    logger.info("   Sources:     %d", len(sources))
    logger.info("   Total chunks: %d", len(chunks))
    logger.info("   Persisted at: %s", chroma_dir)
    logger.info("=" * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
