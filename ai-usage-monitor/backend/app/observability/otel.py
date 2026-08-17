"""Real OpenTelemetry setup for FastAPI and HTTPX instrumentation."""

from __future__ import annotations

from typing import Any

from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor

_tracer_provider: TracerProvider | None = None
_httpx_instrumented = False


def initialize_observability(app: Any) -> TracerProvider | None:
    """Configure a lightweight OpenTelemetry provider and attach it to the app."""
    global _tracer_provider, _httpx_instrumented

    initialized = getattr(app.state, "otel_initialized", False)
    if initialized:
        return _tracer_provider

    resource = Resource.create({
        "service.name": "ai-usage-monitor",
        "service.version": "1.0.0",
        "deployment.environment": "development",
    })

    current_provider = trace.get_tracer_provider()
    if current_provider.__class__.__name__ == "ProxyTracerProvider":
        provider = TracerProvider(resource=resource)
        trace.set_tracer_provider(provider)
    else:
        provider = current_provider

    if not getattr(provider, "_otel_span_processor_added", False):
        provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
        provider._otel_span_processor_added = True

    if not initialized:
        FastAPIInstrumentor.instrument_app(app, tracer_provider=provider)
        if not _httpx_instrumented:
            HTTPXClientInstrumentor().instrument(tracer_provider=provider)
            _httpx_instrumented = True
        app.state.otel_initialized = True

    _tracer_provider = provider
    return provider


def build_tracer(name: str):
    return trace.get_tracer(name)
