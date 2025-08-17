import httpx
from fastapi import FastAPI
import uuid
import json
import re
from opentelemetry import trace

from config import settings
from observability import setup_telemetry, setup_logging


# --- Setup ---
logger = setup_logging()
app = FastAPI(title="Calling Service")
setup_telemetry(service_name="calling_service", app=app)
tracer = trace.get_tracer(__name__)


def pretty_print_sse_stream(stream_data: str) -> list[dict]:
    """
    Parses a raw SSE stream string and returns a list of pretty-printed JSON objects.
    """
    cleaned_events = []
    # Use a regular expression to find all JSON objects prefixed with "data: "
    events = re.findall(r"data: (.*?)(?:\n\n|\n$|(?=data: ))", stream_data, re.DOTALL)
    
    for event_str in events:
        try:
            event_data = json.loads(event_str)
            cleaned_events.append(event_data)
        except json.JSONDecodeError:
            # Handle cases where the chunk is not a complete JSON object.
            # This is normal in a stream.
            pass # Ignore incomplete JSON objects at the end of the stream
            
    return cleaned_events


@app.get("/start-trace")
async def start_trace():
    """
    This endpoint starts a trace and calls the ADK agent service using the
    session-based API as described in the examples.
    """
    with tracer.start_as_current_span("initiate-adk-agent-call") as span:
        try:
            async with httpx.AsyncClient() as client:
                # Generate IDs for the session
                user_id = str(uuid.uuid4())
                session_id = str(uuid.uuid4())

                # Add custom attributes to the span for better traceability
                span.set_attribute("app.user_id", user_id)
                span.set_attribute("app.session_id", session_id)

                # Step 1: Create or update the session
                session_url = f"{settings.ADK_SERVICE_BASE_URL}/apps/{settings.AGENT_ID}/users/{user_id}/sessions/{session_id}"
                session_response = await client.post(session_url, json={}, timeout=60)
                session_response.raise_for_status()

                # Step 2: Run the agent
                run_url = f"{settings.ADK_SERVICE_BASE_URL}/run_sse"
                run_payload = {
                    "app_name": settings.AGENT_ID,
                    "user_id": user_id,
                    "session_id": session_id,
                    "new_message": {
                        "role": "user",
                        "parts": [{
                            "text": "What is the status from the downstream service?"
                        }]
                    },
                    "streaming": True
                }

                # Use client.stream() for the SSE endpoint
                async with client.stream("POST", run_url, json=run_payload, timeout=60) as run_response:
                    run_response.raise_for_status()
                    full_response_text = ""
                    async for chunk in run_response.aiter_bytes():
                        full_response_text += chunk.decode('utf-8')

                    # Process the raw SSE string into a clean, readable format
                    pretty_logs = pretty_print_sse_stream(full_response_text)
                    
                    # Log the response for clarity
                    logger.info("ADK Agent Response Logs:\n{logs}", logs=json.dumps(pretty_logs, indent=2))

                    return {"response_from_adk": pretty_logs}

        except httpx.HTTPStatusError as exc:
            error_content = exc.response.text
            return {
                "error": f"An HTTP error {exc.response.status_code} occurred while requesting {exc.request.url!r}: {error_content}"
            }
        except httpx.RequestError as exc:
            return {"error": f"An error occurred while requesting {exc.request.url!r}: {exc}"}

# To run this service:
# uvicorn src.calling_service:app --port 8000