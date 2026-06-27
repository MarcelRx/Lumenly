# apps/backend/app/services/chat_service.py - Enhanced with Production-Ready Features
import asyncio
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import List, Optional

import httpx
from fastapi import HTTPException
from fastembed import TextEmbedding
from qdrant_client.models import FieldCondition, Filter, MatchValue
from prometheus_client import Histogram, Counter
from app.core.config import settings
from app.core.qdrant import get_qdrant_client
from app.schemas.chat import ChatResponse

logger = logging.getLogger(__name__)

# ========= NEW: Prometheus Metrics =========
RETRIEVE_CONTEXT_LATENCY = Histogram(
    "retrieve_context_latency_seconds",
    "Time spent retrieving context from Qdrant",
    ["user_id"]
)
CALL_GEMINI_LATENCY = Histogram(
    "gemini_api_latency_seconds",
    "Time spent calling Gemini API",
    ["endpoint"]
)
RAG_RESPONSE_LATENCY = Histogram(
    "rag_response_latency_seconds",
    "Total time to generate RAG response",
    ["user_id"]
)

GEMINI_REQUESTS_TOTAL = Counter(
    "gemini_requests_total",
    "Total number of requests made to Gemini API"
)
GEMINI_REQUESTS_SUCCESS = Counter(
    "gemini_requests_success_total",
    "Successful Gemini API requests"
)
GEMINI_REQUESTS_FAILURE = Counter(
    "gemini_requests_failure_total",
    "Failed Gemini API requests"
)

# ========= LENGTH LIMITS & QUALITY CHECKS =========
MAX_CONTEXT_CHUNKS = 3
MIN_CONTEXT_SCORE_THRESHOLD = 0.65
CONTEXT_LENGTH_THRESHOLD = 500
MAX_RAG_RETRIES = 3

# ========= RATE LIMITING =========
_USER_RATE_LIMIT = defaultdict(lambda: {"tokens": 5, "last_reset": datetime.now()})
_RATE_LIMIT_REFILL_RATE = timedelta(seconds=5)
_BASE_RATE_LIMIT = 10

def _refill_tokens(user_id: str):
    now = datetime.now()
    user_state = _USER_RATE_LIMIT[user_id]
    elapsed = now - user_state["last_reset"]

    if elapsed >= _RATE_LIMIT_REFILL_RATE:
        refill_amount = int(elapsed.total_seconds() / _RATE_LIMIT_REFILL_RATE.total_seconds()) * 1
        user_state["tokens"] = min(user_state["tokens"] + refill_amount, _BASE_RATE_LIMIT)
        user_state["last_reset"] = now

def _can_make_request(user_id: str) -> bool:
    _refill_tokens(user_id)
    user_state = _USER_RATE_LIMIT[user_id]
    if user_state["tokens"] >= 1:
        user_state["tokens"] -= 1
        return True
    return False

_embedding_model: Optional[TextEmbedding] = None

def get_embedding_model() -> TextEmbedding:
    global _embedding_model
    if _embedding_model is None:
        logger.info("Initializing fastembed embedding model...")
        _embedding_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
        logger.info("Fastembed embedding model initialized")
    return _embedding_model

async def retrieve_context(
    query: str,
    user_id: str,
    collection_name: str,
    top_k: int = 5,
) -> List[str]:
    start_time = asyncio.get_event_loop().time()
    avg_score = 0.0

    try:
        embedding_model = get_embedding_model()
        query_embedding = list(embedding_model.embed([query]))[0]
        qdrant_client = get_qdrant_client()

        filter_ = Filter(
            must=[FieldCondition(key="user_id", match=MatchValue(value=user_id))]
        )

        # FIXED: Using query_points instead of get_scored_points
        search_result = await qdrant_client.query_points(
            collection_name=collection_name,
            query=query_embedding,
            limit=top_k,
            # Change 'filter' to 'query_filter'
            query_filter=filter_,
            with_payload=True,
        )

        context_chunks = []
        scores = []

        # FIXED: Iterating directly over search_result.points
        for point in search_result.points:
            payload = point.payload or {}
            text = payload.get("text")

            if isinstance(text, str) and len(text) > 0:
                context_chunks.append(text)
                scores.append(point.score)

        if scores:
            avg_score = sum(scores) / len(scores)
            if avg_score < MIN_CONTEXT_SCORE_THRESHOLD:
                logger.warning("Low context quality: %.2f", avg_score)
                if not context_chunks:
                    return []

        logger.info("Retrieved %s chunks for %s (avg score: %.2f)", len(context_chunks), user_id, avg_score)

        # FIXED: Prometheus labels syntax
        RETRIEVE_CONTEXT_LATENCY.labels(user_id=user_id).observe(asyncio.get_event_loop().time() - start_time)
        return context_chunks

    except Exception as e:
        logger.error("Error retrieving context: %s", e)
        RETRIEVE_CONTEXT_LATENCY.labels(user_id=user_id).observe(asyncio.get_event_loop().time() - start_time)
        return []

async def call_gemini_api(query: str, context: List[str]) -> str:
    if not settings.GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not configured")

    # Use configurable model + API version (prevents 404 from hardcoded model names)
    model = (settings.GEMINI_MODEL or "").strip()
    api_version = (settings.GEMINI_API_VERSION or "v1beta").strip()

    if not model:
        raise ValueError("GEMINI_MODEL is not configured")

    url = (
        "https://generativelanguage.googleapis.com/"
        f"{api_version}/models/{model}:generateContent"
    )

    # Strip any accidental hidden spaces or newlines from the .env file
    api_key = settings.GEMINI_API_KEY.strip()

    # Pass the key in the standard Google API header
    headers = {
        "x-goog-api-key": api_key,
        "Content-Type": "application/json",
    }

    context_text = "\n\n".join(context[:MAX_CONTEXT_CHUNKS]) if context else "No relevant context found."

    payload = {
        "contents": [{"parts": [{"text": f"Context:\n{context_text}\n\nQuestion: {query}"}]}]
    }

    # Fallback between API versions on 404 to handle account/model availability differences.
    api_versions_to_try = []
    primary = api_version
    other = "v1" if primary == "v1beta" else "v1beta"
    api_versions_to_try.append(primary)
    if other not in api_versions_to_try:
        api_versions_to_try.append(other)

    attempted_urls: list[str] = []

    async with httpx.AsyncClient(timeout=30.0) as client:
        last_http_404: Optional[httpx.HTTPStatusError] = None

        for ver in api_versions_to_try:
            ver_url = (
                "https://generativelanguage.googleapis.com/"
                f"{ver}/models/{model}:generateContent"
            )
            attempted_urls.append(ver_url)

            for attempt in range(MAX_RAG_RETRIES):
                try:
                    start_time = asyncio.get_event_loop().time()
                    response = await client.post(ver_url, headers=headers, json=payload)
                    call_duration = asyncio.get_event_loop().time() - start_time

                    CALL_GEMINI_LATENCY.labels(endpoint="generateContent").observe(
                        call_duration
                    )
                    GEMINI_REQUESTS_TOTAL.inc()

                    response.raise_for_status()
                    data = response.json()

                    if "candidates" in data:
                        GEMINI_REQUESTS_SUCCESS.inc()
                        return data["candidates"][0]["content"]["parts"][0]["text"]

                    raise ValueError("Unexpected response format")

                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 404:
                        last_http_404 = e
                        # Try other api version; don't raise immediately.
                        break

                    if attempt == MAX_RAG_RETRIES - 1:
                        GEMINI_REQUESTS_FAILURE.inc()
                        raise
                    await asyncio.sleep(1.0 * (2 ** attempt))

                except Exception:
                    if attempt == MAX_RAG_RETRIES - 1:
                        GEMINI_REQUESTS_FAILURE.inc()
                        raise
                    await asyncio.sleep(1.0 * (2 ** attempt))

        GEMINI_REQUESTS_FAILURE.inc()
        if last_http_404 is not None:
            raise HTTPException(
                status_code=502,
                detail=(
                    "Gemini model not found (404) for all tried API versions. "
                    f"model={settings.GEMINI_MODEL}. "
                    f"primary_api_version={primary}. other_api_version={other}. "
                    f"attempted_urls={attempted_urls}"
                ),
            ) from last_http_404
        raise HTTPException(
            status_code=502,
            detail=f"Gemini API request failed after retries. attempted_urls={attempted_urls}",
        )

async def generate_rag_response(
    query: str,
    user_id: str,
    collection_name: str,
) -> ChatResponse:
    if not _can_make_request(user_id):
        raise Exception("Rate limit exceeded")

    start_time = asyncio.get_event_loop().time()

    try:
        context = await retrieve_context(query, user_id, collection_name)
        answer = await call_gemini_api(query, context)

        # FIXED: Prometheus labels syntax
        total_latency = asyncio.get_event_loop().time() - start_time
        RAG_RESPONSE_LATENCY.labels(user_id=user_id).observe(total_latency)

        return ChatResponse(answer=answer, context=context)

    except Exception as e:
        logger.error("Error generating RAG response: %s", e)
        RAG_RESPONSE_LATENCY.labels(user_id=user_id).observe(asyncio.get_event_loop().time() - start_time)
        raise
