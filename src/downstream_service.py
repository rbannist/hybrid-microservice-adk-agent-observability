from fastapi import FastAPI, Request
from opentelemetry import trace

from config import settings
from observability import setup_telemetry, setup_logging


# --- Setup ---
logger = setup_logging()
app = FastAPI(title="Downstream Service")
# The shared setup_telemetry function handles all necessary instrumentation.
setup_telemetry(service_name="downstream_service", app=app)
tracer = trace.get_tracer(__name__)


@app.get("/status")
async def get_status(request: Request):
   """
   This is the final endpoint in the trace. It receives the call
   from the ADK agent.
   """
   # FastAPIInstrumentor automatically extracts the trace context from headers.
   # Any spans created here will be children of the ADK agent's span.
   with tracer.start_as_current_span("process-status-request") as span:
       trace_id = span.get_span_context().trace_id
       logger.info("Downstream service received request with trace ID: {trace_id}", trace_id=f"{trace_id:x}")
       span.set_attribute("service.status", "ok")
       return "Status OK from the downstream microservice."


# To run this service:
# uvicorn src.downstream_service:app --port 8002