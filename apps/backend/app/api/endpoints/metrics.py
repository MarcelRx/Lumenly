"""Metrics Endpoint for Lumenly Backend"""
import os

from fastapi import APIRouter
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry, generate_latest
from prometheus_client.multiprocess import MultiProcessCollector

router = APIRouter()

@router.get("/metrics")
async def get_metrics() -> Response:
    """Returns Prometheus metrics in text format"""
    # Use multiprocess collector if in multiprocess mode (Uvicorn with --workers > 1)
    if 'PROMETHEUS_MULTIPROC_DIR' in os.environ:
        registry = CollectorRegistry()
        MultiProcessCollector(registry)
        return Response(
            content=generate_latest(registry),
            media_type=CONTENT_TYPE_LATEST,
        )
    else:
        return Response(
            content=generate_latest(),
            media_type=CONTENT_TYPE_LATEST,
        )
