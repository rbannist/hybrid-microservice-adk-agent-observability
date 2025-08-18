# Hybrid Microservice and AI Agent Observability with OpenTelemetry

This project provides a working example of how to achieve end-to-end distributed tracing in a hybrid architecture that combines traditional microservices with an AI agent built using the Google Agent Development Kit (ADK).  It demonstrates how to propagate a single trace context across a `FastAPI service -> ADK Agent -> FastAPI service` call chain, resulting in a unified trace view in Google Cloud Trace.

## The Challenge

In modern architectures, a single user request might traverse multiple systems.  While tracing across standard microservices is a well-understood problem, introducing AI agents as intermediate steps can break the trace continuity.  This is because the agent framework might not automatically propagate the necessary tracing headers.  This example solves that problem.

## Architecture

The request flows through three distinct services running locally:

1.  **`calling_service`** (Port 8000): A FastAPI microservice that initiates the entire process.  It creates the root span of our trace.
2.  **`adk_agent_service`** (Port 8001): A service that hosts a Google ADK agent.  It receives the request from the `calling_service`.  The ADK framework, powered by a Gemini model, decides to use a tool to fulfill the request.
3.  **`downstream_service`** (Port 8002): Another FastAPI microservice that represents the final destination.  It's called by the ADK agent's tool.

```
+-----------------+      (1) HTTP POST      +--------------------+      (3) HTTP GET       +--------------------+
| calling_service | ----------------------> | adk_agent_service  | ----------------------> | downstream_service |
| (FastAPI)       | (with trace context)  | (ADK + Gemini)     | (with trace context)  | (FastAPI)          |
+-----------------+                       +--------------------+                       +--------------------+
                         | (2) ADK invokes tool |
                         +----------------------+
```

The key is that OpenTelemetry's context propagation ensures the `trace_id` is maintained across all hops, allowing Google Cloud Trace to stitch all the individual spans into a single, cohesive trace.

## What is included with this example?

- **Centralised Configuration:** All configuration (ports, project IDs, URLs) is managed in `src/config.py` using `pydantic-settings` and loaded from a `.env` file, eliminating hardcoded values.
- **Reusable Observability Setup:** OpenTelemetry and logging setup is centralised in `src/observability.py` to avoid code duplication across services.  If you need to split into separate deployable units - i.e. 3 services on Cloud Run - you'll need to couple `src/observability.py` with both the calling_service and the downstream_service.
- **Logging:** Uses `loguru` for structured, colorful, and more informative logs than standard `print` or `logging`.
- **Simplified Execution:** A `run_services.sh` script is provided to start all services with a single command.

## Prerequisites

- Python 3.12+
- A Google Cloud Project with the **Cloud Trace API** enabled.
- Google Cloud SDK installed and authenticated. Run `gcloud auth application-default login`.
- `uv` (optional, but recommended for fast dependency management).  You can install it with `pip install uv` (alternatively, create a venv and then install dependencies with `pip install -r src/requirements.txt`).

## Setup

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd hybrid-microservice-adk-agent-observability
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    # Using uv
    uv venv
    source .venv/bin/activate

    # Or using standard venv
    # python3 -m venv .venv
    # source .venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    uv pip install -r src/requirements.txt
    ```

4.  **Configure Environment:**
    Create a `.env` file in the root of the project by copying the example:
    ```bash
    cp .env.example .env
    ```
    Now, edit the `.env` file and replace `"your-gcp-project-id"` with your actual Google Cloud Project ID.

    ```
    # .env
    GOOGLE_CLOUD_PROJECT="your-gcp-project-id"
    ```

## Running the Services

With the new setup, you can start all services with a single script. Make sure you are in the project root directory with your virtual environment activated.

1.  **Make the script executable:**
    ```bash
    chmod +x run_services.sh
    ```

2.  **Run the script:**
    ```bash
    ./run_services.sh
    ```
    This will start all three services in the background.

3.  **To stop all services,** find the process IDs printed by the script and use `kill <PID1> <PID2> <PID3>`.

## Triggering a Trace

Once all services are running, open another terminal and send a request to the `calling_service`:

```bash
curl http://127.0.0.1:8000/start-trace
```

You will see a JSON response in your terminal containing the logs from the ADK agent's execution.  In the terminals running the services, you will see log output indicating requests being received.

## Viewing the Result in Cloud Trace

1.  Wait a minute or two for the trace data to be exported and processed.
2.  Navigate to the Google Cloud Trace dashboard in your project:
    `https://console.cloud.google.com/traces/list?project=your-gcp-project-id`
3.  You should see a new trace for the URI `/start-trace`. Clicking on it will reveal the waterfall view of the entire distributed operation.

You will see a trace composed of multiple, connected spans, similar to this:
- `GET /start-trace` (from `calling_service`)
  - `initiate-adk-agent-call`
    - `POST /run_sse` (HTTP call to `adk_agent_service`)
      - `POST /run_sse` (Server-side span in `adk_agent_service`)
        - `downstream_caller_agent` (ADK agent execution)
          - `call-downstream-service` (ADK tool execution)
            - `GET /status` (HTTP call to `downstream_service`)
              - `GET /status` (Server-side span in `downstream_service`)
                - `process-status-request`


Here is an example screenshot: [End-to-End Trace in Google Cloud Trace](media/e2e-trace-console-example.png)

This unified view is the goal of the project, demonstrating successful context propagation.

## How It Works

- **Instrumentation:** Each FastAPI service is instrumented with `FastAPIInstrumentor`. Crucially, `HTTPXClientInstrumentor` is also used to automatically trace outgoing HTTP requests made with the `httpx` library.
- **Context Propagation:** When an instrumented `httpx` client makes a request, it automatically injects the current trace context (e.g., `traceparent` header) into the outgoing request. The receiving instrumented FastAPI service automatically extracts this context, ensuring the new span is correctly parented.
- **ADK Integration:**
    - The `adk_agent_service.py` is a FastAPI app, so `FastAPIInstrumentor` handles the incoming trace context.
    - We call `HTTPXClientInstrumentor().instrument()` once when the ADK service starts. This patches `httpx` for the entire process.
    - The ADK uses `httpx` internally to make tool calls. Because `httpx` is already instrumented, when our agent's tool (`call_downstream_microservice`) makes its `httpx.get()` call, the trace context is automatically propagated to the `downstream_service`.
    - The `trace_to_cloud=True` flag in `get_fast_api_app` simplifies the OpenTelemetry setup for the ADK service itself.
