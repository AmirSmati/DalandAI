import json
import logging
import sys
from datetime import datetime, timezone


class StructuredLogger:
    """
    Structured JSON logger for agent observability.

    Each event is emitted as a single JSON object so that
    individual agent runs can be inspected using run_id.
    """

    def __init__(self):
        self.logger = logging.getLogger("agent_observability")

        if not self.logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            self.logger.addHandler(handler)

        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False

    def log(
        self,
        event: str,
        run_id: str,
        level: str = "INFO",
        component: str | None = None,
        status: str | None = None,
        **fields,
    ) -> None:
        # Local import avoids a hard dependency on the OTel SDK for callers
        # that only care about structured logging.
        from Observability.tracing import current_trace_context
        from config.settings import OTEL_SERVICE_NAME

        trace_context = current_trace_context()

        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "service": OTEL_SERVICE_NAME,
            "event": event,
            "run_id": run_id,
            "trace_id": trace_context["trace_id"],
            "span_id": trace_context["span_id"],
            "component": component,
            "status": status,
            **fields,
        }


        self.logger.info(json.dumps(record, default=str))