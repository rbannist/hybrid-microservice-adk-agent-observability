import os
from fastapi import FastAPI
from pathlib import Path
from google.adk.cli.fast_api import get_fast_api_app

# OpenTelemetry specific imports
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from config import settings

# Set environment variables from the centralised settings.
# This is necessary for the ADK and other Google libraries that read from the environment.
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = str(settings.USE_VERTEXAI)
os.environ["GOOGLE_CLOUD_PROJECT"] = settings.GCP_PROJECT_ID
os.environ["GOOGLE_CLOUD_LOCATION"] = settings.GCP_LOCATION

# It is not necessary to manually configure exporters here because
# `trace_to_cloud=True` in `get_fast_api_app` handles the setup for
# Google Cloud Trace.

# Instrument httpx to automatically propagate trace context
# This needs to be done once in the main process.
HTTPXClientInstrumentor().instrument()

# --- ADK Application Setup ---

# The ADK's get_fast_api_app will automatically discover agents
# defined in the specified directory.
app: FastAPI = get_fast_api_app(
    agents_dir="agents",
    web=True,
    trace_to_cloud=True  # This is the key to enable Cloud Trace integration
)

# Instrument the FastAPI app to handle incoming trace context from calling_service.
# This allows the agent's spans to be part of the same trace.
FastAPIInstrumentor.instrument_app(app)

# To run this service:
# uvicorn src.adk_agent_service:app --port 8001