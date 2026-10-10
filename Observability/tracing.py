"""
Central OpenTelemetry tracing bootstrap.

Every other module gets a tracer via `get_tracer()` and wraps a block of
work with `traced_span(...)`. When tracing is disabled (OTEL_ENABLED=false)
or the SDK/exporter fails to initialize, the OpenTelemetry API's built-in
no-op TracerProvider is used instead, so call sites never need to branch on
whether tracing is active.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any, Iterator, Optional

from opentelemetry import trace
from opentelemetry.trace import Span, Status, StatusCode

_initialized = False


def init_tracing() -> None:
    """
    Configure the global TracerProvider from OTEL_* environment variables.

    Safe to call multiple times (only the first call has an effect) and
    safe to call when the OTel SDK or an OTLP endpoint is unavailable: any
    setup failure is logged and tracing silently falls back to the
    no-op provider so the application's behavior never changes because of
    observability wiring.
    """
    global _initialized

    if _initialized:
        return

    _initialized = True

    from config.settings import OTEL_ENABLED

    if not OTEL_ENABLED:
        print("[TRACING] OpenTelemetry disabled (OTEL_ENABLED=false).")
        return

    try:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
            OTLPSpanExporter,
        )
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        from config.settings import (
            OTEL_ENVIRONMENT,
            OTEL_EXPORTER_OTLP_ENDPOINT,
            OTEL_SERVICE_NAME,
        )

        resource = Resource.create(
            {
                "service.name": OTEL_SERVICE_NAME,
                "deployment.environment": OTEL_ENVIRONMENT,
            }
        )

        provider = TracerProvider(resource=resource)

        if OTEL_EXPORTER_OTLP_ENDPOINT:
            # The http/protobuf exporter expects the full signal path.
            traces_endpoint = OTEL_EXPORTER_OTLP_ENDPOINT.rstrip("/") + "/v1/traces"
            exporter = OTLPSpanExporter(endpoint=traces_endpoint)
            provider.add_span_processor(BatchSpanProcessor(exporter))
            print(
                f"[TRACING] Exporting traces via OTLP/HTTP to {traces_endpoint}"
            )
        else:
            print(
                "[TRACING] OTEL_EXPORTER_OTLP_ENDPOINT not set; "
                "spans will be created but not exported."
            )

        trace.set_tracer_provider(provider)

    except Exception as exc:
        print(f"[TRACING] Setup skipped, falling back to no-op tracer: {exc}")


def get_tracer(name: str = "agent-harness") -> trace.Tracer:
    """Return a tracer bound to the given instrumentation scope name."""
    return trace.get_tracer(name)


@contextmanager
def traced_span(
    name: str,
    attributes: Optional[dict[str, Any]] = None,
    tracer_name: str = "agent-harness",
) -> Iterator[Span]:
    """
    Start a span named `name`, set the given (non-sensitive) attributes,
    and yield it as the current span.

    `attributes` keys follow OTel semantic-convention style (dotted, e.g.
    "run.id", "tool.name") so it is a plain dict rather than **kwargs.

    Exceptions raised inside the `with` block are recorded on the span
    (exception type/message + ERROR status) and then re-raised unchanged —
    this never swallows an exception, it only observes it.
    """
    tracer = get_tracer(tracer_name)

    with tracer.start_as_current_span(name) as span:
        for key, value in (attributes or {}).items():
            if value is not None:
                span.set_attribute(key, value)

        yield span


def mark_ok(span: Span) -> None:
    """Explicitly mark a span as successfully completed."""
    span.set_status(Status(StatusCode.OK))


def mark_error(span: Span, error: BaseException) -> None:
    """Record an exception on a span without raising or swallowing it."""
    span.record_exception(error)
    span.set_status(Status(StatusCode.ERROR, str(error)))


def current_trace_context() -> dict[str, Optional[str]]:
    """
    Return the active trace_id/span_id as hex strings for log correlation,
    or {"trace_id": None, "span_id": None} when nothing is recording.
    """
    span = trace.get_current_span()
    ctx = span.get_span_context()

    if ctx is None or not ctx.is_valid:
        return {"trace_id": None, "span_id": None}

    return {
        "trace_id": format(ctx.trace_id, "032x"),
        "span_id": format(ctx.span_id, "016x"),
    }
