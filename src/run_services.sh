#!/bin/bash
# This script starts all three microservices in the background.
# It assumes you have activated your virtual environment and are in the src directory.

echo "Starting all services..."

# Load environment variables from .env file if it exists
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi

# Use the configured ports or defaults from the .env file
CALLING_PORT=${CALLING_SERVICE_PORT:-8000}
ADK_PORT=${ADK_SERVICE_PORT:-8001}
DOWNSTREAM_PORT=${DOWNSTREAM_SERVICE_PORT:-8002}

# Start services and store their PIDs
uvicorn downstream_service:app --port $DOWNSTREAM_PORT &
DOWNSTREAM_PID=$!
echo "Started downstream_service on port $DOWNSTREAM_PORT (PID: $DOWNSTREAM_PID)"

uvicorn adk_agent_service:app --port $ADK_PORT &
ADK_PID=$!
echo "Started adk_agent_service on port $ADK_PORT (PID: $ADK_PID)"

uvicorn calling_service:app --port $CALLING_PORT &
CALLING_PID=$!
echo "Started calling_service on port $CALLING_PORT (PID: $CALLING_PID)"

echo "All services started."
echo "To stop them, run: kill $DOWNSTREAM_PID $ADK_PID $CALLING_PID"