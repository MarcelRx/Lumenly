# apps/backend/app/ai/llm/metrics.py
"""
LLM metrics collection utilities.

Provides metrics collection for LLM provider operations.
"""
import time
from functools import wraps
from typing import Callable, Any

from app.core.metrics import (
    llm_requests_total,
    llm_request_failures_total,
    llm_request_duration_seconds,
    llm_input_tokens_total,
    llm_output_tokens_total,
)


def track_llm_request(provider: str, model: str):
    """
    Decorator to track LLM request metrics.
    
    Args:
        provider: The LLM provider name (e.g., 'groq', 'gemini')
        model: The model name
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                
                # Record successful request
                duration = time.time() - start_time
                llm_requests_total.labels(provider=provider, model=model).inc()
                llm_request_duration_seconds.labels(provider=provider).observe(duration)
                
                # Record token usage if available
                if hasattr(result, 'usage') and result.usage:
                    if 'prompt_tokens' in result.usage:
                        llm_input_tokens_total.labels(provider=provider).inc(result.usage['prompt_tokens'])
                    if 'completion_tokens' in result.usage:
                        llm_output_tokens_total.labels(provider=provider).inc(result.usage['completion_tokens'])
                
                return result
                
            except Exception as e:
                # Record failed request
                duration = time.time() - start_time
                llm_request_failures_total.labels(
                    provider=provider,
                    failure_type=type(e).__name__
                ).inc()
                llm_request_duration_seconds.labels(provider=provider).observe(duration)
                raise
                
        return wrapper
    return decorator