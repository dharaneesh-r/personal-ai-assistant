import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.sdk.trace.export import SimpleSpanProcessor

from app.tracing import trace_span, get_tracer, instrument_span


@pytest.fixture(scope="module")
def memory_tracer():
    """Sets up an in-memory tracer provider to verify span recording."""
    provider = trace.get_tracer_provider()
    exporter = InMemorySpanExporter()
    processor = SimpleSpanProcessor(exporter)
    
    # Check if the global provider is a real TracerProvider
    if hasattr(provider, "add_span_processor"):
        provider.add_span_processor(processor)
    else:
        # Fallback to creating a new one if it's just a proxy
        provider = TracerProvider()
        provider.add_span_processor(processor)
        try:
            trace.set_tracer_provider(provider)
        except Exception:
            pass
    
    yield exporter


def test_trace_span_context_manager(memory_tracer):
    memory_tracer.clear()
    
    with trace_span("my_test_span", {"attr1": "val1", "attr2": 42}) as span:
        assert span is not None
        span.set_attribute("inline_attr", "inline_val")
        
    spans = memory_tracer.get_finished_spans()
    assert len(spans) == 1
    recorded_span = spans[0]
    assert recorded_span.name == "my_test_span"
    assert recorded_span.attributes["attr1"] == "val1"
    assert recorded_span.attributes["attr2"] == 42
    assert recorded_span.attributes["inline_attr"] == "inline_val"


def test_trace_span_decorator(memory_tracer):
    memory_tracer.clear()
    
    @instrument_span("my_decorated_span", {"decorator_attr": "yes"})
    def target_func(x):
        return x * 2
        
    res = target_func(10)
    assert res == 20
    
    spans = memory_tracer.get_finished_spans()
    assert len(spans) == 1
    recorded_span = spans[0]
    assert recorded_span.name == "my_decorated_span"
    assert recorded_span.attributes["decorator_attr"] == "yes"
