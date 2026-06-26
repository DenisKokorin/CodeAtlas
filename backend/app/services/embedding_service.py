"""
Embedding service for the RAG chatbot.

Uses Gemini Embedding API to generate vector embeddings (768 dimensions).
Embeddings are stored as BLOBs in SQLite. Cosine similarity is computed with numpy.

Available models:
  - embedding-001 (older, widely available, 768 dimensions)
  - text-embedding-004 (newer, 768 dimensions, may require newer API access)

Gemini Embedding API:
  POST https://generativelanguage.googleapis.com/v1beta/models/{model}:embedContent
  Body: {"model": "models/{model}", "content": {"parts": [{"text": "..."}]}}
  Response: {"embedding": {"values": [0.012, -0.034, ...]}}
"""

import os
import struct

import httpx
import numpy as np
from fastapi import HTTPException

GEMINI_EMBEDDING_API_URL = "https://generativelanguage.googleapis.com/v1beta/models"
DEFAULT_EMBEDDING_MODEL = "embedding-001"
FALLBACK_EMBEDDING_MODEL = "embedding-001"
MAX_TEXT_LENGTH = 30000
BATCH_MAX_SIZE = 100


def is_embeddings_available() -> bool:
    """Check if Gemini API key is configured for embeddings."""
    return bool(os.getenv("GEMINI_API_KEY"))


def get_api_key() -> str:
    """Get Gemini API key or empty string."""
    return os.getenv("GEMINI_API_KEY", "")


def get_model() -> str:
    """Get the configured embedding model name."""
    return os.getenv("GEMINI_EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL)


def embedding_to_blob(embedding: list[float]) -> bytes:
    """Serialize a list of floats to a BLOB (float32, 4 bytes per value)."""
    return struct.pack(f"{len(embedding)}f", *embedding)


def blob_to_embedding(blob: bytes) -> list[float]:
    """Deserialize a BLOB back to a list of floats."""
    return list(struct.unpack(f"{len(blob) // 4}f", blob))


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors. Returns [-1, 1]."""
    a_np = np.array(a, dtype=np.float32)
    b_np = np.array(b, dtype=np.float32)
    dot_product = float(np.dot(a_np, b_np))
    norm_a = float(np.linalg.norm(a_np))
    norm_b = float(np.linalg.norm(b_np))

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot_product / (norm_a * norm_b)


def truncate_text(text: str, max_chars: int = MAX_TEXT_LENGTH) -> str:
    """Truncate text to fit embedding model limits."""
    if len(text) <= max_chars:
        return text

    return text[: max_chars - 100] + "\n\n[Текст обрезан из-за ограничения размера.]"


async def generate_embedding(
    text: str,
    api_key: str | None = None,
    model: str | None = None,
) -> list[float]:
    """
    Generate an embedding vector using Gemini Embedding API.

    Tries the configured model first, falls back to embedding-001 on any error.
    Raises HTTPException(502) only if both models fail.

    Returns a list of 768 floats.
    """
    api_key = api_key or get_api_key()
    model = model or get_model()
    models_to_try = [model]

    if model != FALLBACK_EMBEDDING_MODEL:
        models_to_try.append(FALLBACK_EMBEDDING_MODEL)

    last_error: Exception | None = None

    for attempt_model in models_to_try:
        try:
            return await _embed_single(text, api_key, attempt_model)
        except Exception as exc:
            last_error = exc

    raise HTTPException(
        status_code=502,
        detail=f"Gemini Embedding API is unavailable: {last_error!s}",
    ) from last_error


async def _embed_single(text: str, api_key: str, model: str) -> list[float]:
    """Call the Gemini Embedding API for a single text."""
    url = f"{GEMINI_EMBEDDING_API_URL}/{model}:embedContent"
    params = {"key": api_key}
    payload = {
        "model": f"models/{model}",
        "content": {"parts": [{"text": truncate_text(text)}]},
    }

    timeout = httpx.Timeout(15.0, connect=5.0)

    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(url, params=params, json=payload)

    response.raise_for_status()
    data = response.json()
    embedding = data.get("embedding", {}).get("values")

    if embedding is None:
        raise ValueError("Gemini Embedding API returned no embedding values")

    return [float(v) for v in embedding]


async def generate_embeddings_batch(
    texts: list[str],
    api_key: str | None = None,
    model: str | None = None,
) -> list[list[float]]:
    """
    Generate embeddings for multiple texts via sequential single calls.

    Tries the configured model first. If all embeddings fail,
    falls back to embedding-001. Failed individual embeddings
    return empty list ([]).

    Returns a list of embedding vectors (one per input text).
    """
    api_key = api_key or get_api_key()
    model = model or get_model()

    if not texts:
        return []

    models_to_try = [model]
    if model != FALLBACK_EMBEDDING_MODEL:
        models_to_try.append(FALLBACK_EMBEDDING_MODEL)

    for attempt_model in models_to_try:
        try:
            embeddings = await _call_sequential(texts, api_key, attempt_model)

            # Check if any embeddings actually succeeded
            if any(e for e in embeddings):
                return embeddings
        except Exception:
            pass

    return [[] for _ in texts]


async def _call_sequential(
    texts: list[str],
    api_key: str,
    model: str,
) -> list[list[float]]:
    """Call embedding API sequentially for all texts with concurrency."""
    import asyncio

    semaphore = asyncio.Semaphore(5)

    async def _embed_one(text: str) -> list[float]:
        async with semaphore:
            try:
                return await _embed_single(text, api_key, model)
            except Exception:
                return []

    tasks = [_embed_one(t) for t in texts]
    results = await asyncio.gather(*tasks)

    return results
