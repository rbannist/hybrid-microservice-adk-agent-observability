import httpx
from google.adk.agents import Agent
from opentelemetry import trace

from config import settings

# Note: HTTPXClientInstrumentor is already called in the main service file.

# --- Function Tool Definition ---

def call_downstream_microservice() -> str:
    """
    Calls the downstream microservice to get a status update.
    This tool explicitly propagates the current trace context.
    """
    downstream_url = settings.DOWNSTREAM_SERVICE_URL
    tracer = trace.get_tracer(__name__)

    with tracer.start_as_current_span("call-downstream-service") as span:
        try:
            with httpx.Client() as client:
                # With HTTPXClientInstrumentor, trace context is injected automatically.
                response = client.get(downstream_url)
                response.raise_for_status()
                span.set_attribute("http.status_code", response.status_code)
                return response.text
        except httpx.RequestError as exc:
            span.set_attribute("error", True)
            span.record_exception(exc)
            return f"Error contacting downstream service: {exc}"

# --- ADK Agent Definition ---
# The ADK framework will discover this agent instance.
downstream_caller_agent = Agent(
    name="downstream_caller_agent",
    instruction="""
    Your only purpose is to call the downstream microservice to get its status.
    Use the call_downstream_microservice tool for any user request.
    """,
    model=settings.GEMINI_MODEL,
    tools=[call_downstream_microservice],
)

root_agent = downstream_caller_agent