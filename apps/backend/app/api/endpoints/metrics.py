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
    # Check if multiprocess directory has metrics files (indicates multiprocess mode is active)
    if 'PROMETHEUS_MULTIPROC_DIR' in os.environ:
        import glob
        multiproc_dir = os.environ['PROMETHEUS_MULTIPROC_DIR']
        # Check if there are any metric files in the multiprocess directory
        metric_files = glob.glob(os.path.join(multiproc_dir, '*.db'))
        if metric_files:
            # Multiprocess mode is active - use MultiProcessCollector
            registry = CollectorRegistry()
            MultiProcessCollector(registry)
            return Response(
                content=generate_latest(registry),
                media_type=CONTENT_TYPE_LATEST,
            )

    # Single-process mode or multiprocess not yet initialized
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )
