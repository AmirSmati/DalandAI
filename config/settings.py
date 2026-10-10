import json
import os
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()


# Load persistent JSON configuration if present.
CONFIG_PATH = Path(__file__).parent / "config.json"

if CONFIG_PATH.exists():
    with open(CONFIG_PATH, "r", encoding="utf-8") as config_file:
        CONFIG = json.load(config_file)
    INNKUBE_MODEL = CONFIG.get("model", os.getenv("INNKUBE_MODEL", "qwen-agentworld-35b-a3b"))
    INNKUBE_TEMPERATURE = CONFIG.get("temperature", 0.2)
else:
    INNKUBE_MODEL = os.getenv("INNKUBE_MODEL", "qwen-agentworld-35b-a3b")
    INNKUBE_TEMPERATURE = 0.2


# Authentication stays in environment variables.
INNKUBE_API_KEY = os.getenv("INNKUBE_API_KEY")
INNKUBE_BASE_URL = os.getenv("INNKUBE_BASE_URL")

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

if not INNKUBE_API_KEY:
    raise RuntimeError("INNKUBE_API_KEY is not configured")

if not INNKUBE_BASE_URL:
    raise RuntimeError("INNKUBE_BASE_URL is not configured")


# Google Calendar MCP configuration
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
TOKEN_FILE_PATH = os.getenv("TOKEN_FILE_PATH", ".gcp-saved-tokens.json")

#HF Token (Embeddings)
HF_TOKEN = os.getenv("HF_TOKEN")

# OpenTelemetry tracing configuration.
# All optional: tracing degrades to a no-op tracer if unset/disabled.
OTEL_ENABLED = os.getenv("OTEL_ENABLED", "true").strip().lower() not in {
    "false",
    "0",
    "no",
}
OTEL_SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME", "agent-harness")
OTEL_ENVIRONMENT = os.getenv("OTEL_ENVIRONMENT", "development")


OTEL_EXPORTER_OTLP_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")
OTEL_EXPORTER_OTLP_PROTOCOL = os.getenv(
    "OTEL_EXPORTER_OTLP_PROTOCOL", "http/protobuf"
)


MIN_SIMILARITY = 0.41