# apps/backend/app/middleware/metrics.py
"""
Metrics middleware for automatic HTTP request metrics collection.

Integrates with existing middleware architecture to collect:
- HTTP request count
- HTTP request latency
- HTTP in-flight requests
- Response status codes

All metrics follow low-cardinality principles and never expose sensitive data.
"""
import time
from typing import Callable

from fastapi import Request, Response

from app.core.metrics import (
    http_request_duration_seconds,
    http_requests_in_flight,
    http_requests_total,
)


def get_route_template(request: Request) -> str:
    """
    Extract the route template from the request for low-cardinality metrics.

    Instead of using actual paths like /api/v1/documents/12345, this returns
    the route template like /api/v1/documents/{document_id} to prevent
    unbounded cardinality from dynamic path parameters.
    """
    # Try to get the route from the request's scope
    route_path = request.scope.get("route")
    if route_path and hasattr(route_path, "path"):
        route_template = route_path.path
        # If this contains parameters, it's the template we want
        if '{' in route_template and '}' in route_template:
            return route_template
        # If no parameters, it might be a static route
        return route_template

    # More robust fallback: try to match against registered routes
    request_path = request.url.path
    request_segments = request_path.split('/')

    for route in request.app.routes:
        if hasattr(route, "path") and hasattr(route, "methods"):
            if request.method in route.methods:
                route_path_template = route.path
                route_segments = route_path_template.split('/')

                # Check if segment counts match
                if len(route_segments) == len(request_segments):
                    # Check if non-parameter segments match
                    match = True
                    for route_seg, req_seg in zip(route_segments, request_segments):
                        if route_seg.startswith('{') and route_seg.endswith('}'):
                            # This is a parameter, skip matching
                            continue
                        if route_seg != req_seg:
                            match = False
                            break

                    if match:
                        return route_path_template

    # Ultimate fallback: FORCE normalization by replacing any potentially dynamic segments
    # This is critical for preventing unbounded cardinality on 404 routes
    segments = request_path.split('/')
    normalized_segments = []
    for seg in segments:
        # Replace numeric segments with placeholders
        if seg.isdigit():
            normalized_segments.append('{id}')
        # Replace UUID-like segments with placeholders
        elif len(seg) == 36 and seg.count('-') == 4:
            normalized_segments.append('{uuid}')
        # Replace MongoDB ObjectId-like segments (24 hex chars)
        elif len(seg) == 24:
            try:
                int(seg, 16)  # Try to parse as hex
                normalized_segments.append('{id}')
            except ValueError:
                # Not hex, might still be an ID
                if len(seg) > 8 and seg.isalnum():
                    normalized_segments.append('{id}')
                else:
                    normalized_segments.append(seg)
        # Replace long alphanumeric segments that might be IDs
        elif len(seg) > 8 and seg.isalnum():
            normalized_segments.append('{id}')
        else:
            normalized_segments.append(seg)

    return '/'.join(normalized_segments)


async def metrics_middleware(request: Request, call_next: Callable) -> Response:
    """
    Middleware to collect HTTP request metrics.

    This middleware:
    - Tracks in-flight requests per method
    - Records request count with method, route, and status code
    - Records request latency with histogram
    - Maintains low-cardinality labels (no user IDs, no sensitive data)

    Skips metrics collection for health and metrics endpoints to reduce noise.
    """
    # Skip metrics for health and metrics endpoints
    if request.url.path in ["/health", "/health/live", "/health/ready", "/metrics", "/v1/metrics"]:
        return await call_next(request)

    method = request.method
    route = get_route_template(request)

    # Increment in-flight counter
    http_requests_in_flight.labels(method=method).inc()

    start_time = time.time()

    try:
        response = await call_next(request)

        # Calculate duration
        duration = time.time() - start_time

        # Extract status code
        status_code = str(response.status_code)

        # Record metrics
        http_requests_total.labels(
            method=method,
            route=route,
            status_code=status_code
        ).inc()

        http_request_duration_seconds.labels(
            method=method,
            route=route,
            status_code=status_code
        ).observe(duration)

        return response

    finally:
        # Always decrement in-flight counter
        http_requests_in_flight.labels(method=method).dec()
