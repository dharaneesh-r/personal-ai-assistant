import functools
import socket
from contextlib import contextmanager
from typing import Any, Dict, Optional
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource

tracer = None


def is_collector_running(host: str = "localhost", port: int = 6006) -> bool:
    """Check if a local OTel collector port is active to avoid connection warning noise."""
    try:
        with socket.create_connection((host, port), timeout=0.2):
            return True
    except Exception:
        return False


def init_tracer(service_name: str = "groq-ai-workspace") -> trace.Tracer:
    """Initialize OpenTelemetry Tracer exporting to local Arize Phoenix collector."""
    global tracer
    if tracer is not None:
        return tracer

    # Configure Resource attributes (service name)
    resource = Resource.create(attributes={
        "service.name": service_name
    })

    provider = TracerProvider(resource=resource)

    # Only export to local Arize Phoenix collector if it's currently running
    if is_collector_running("localhost", 6006):
        otlp_exporter = OTLPSpanExporter(endpoint="http://localhost:6006/v1/traces")
        span_processor = BatchSpanProcessor(otlp_exporter)
        provider.add_span_processor(span_processor)

    trace.set_tracer_provider(provider)
    tracer = trace.get_tracer(service_name)
    return tracer


def get_tracer() -> trace.Tracer:
    """Get the initialized tracer, falling back to a dummy tracer if uninitialized."""
    global tracer
    if tracer is None:
        return trace.get_tracer("groq-ai-workspace")
    return tracer


@contextmanager
def trace_span(name: str, attributes: Optional[Dict[str, Any]] = None):
    """Context manager for tracing code blocks."""
    t = get_tracer()
    with t.start_as_current_span(name) as span:
        if attributes:
            for k, v in attributes.items():
                if v is not None:
                    span.set_attribute(k, str(v) if isinstance(v, (dict, list, tuple)) else v)
        yield span


def instrument_span(name: Optional[str] = None, attributes: Optional[Dict[str, Any]] = None):
    """Decorator to trace functions."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            span_name = name or func.__name__
            with trace_span(span_name, attributes):
                return func(*args, **kwargs)
        return wrapper
    return decorator
