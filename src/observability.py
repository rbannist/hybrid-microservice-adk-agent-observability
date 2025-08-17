from opentelemetry import trace
from opentelemetry.sdk.resources import get_aggregated_resources, Resource, SERVICE_NAME
from opentelemetry.sdk.trace import TracerProvider, sampling
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
from opentelemetry.resourcedetector.gcp_resource_detector import GoogleCloudResourceDetector
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from fastapi import FastAPI
from loguru import logger
import sys

def setup_logging():
    """
    Configures Loguru to provide structured, colorful logging.
    """
    logger.remove()  # Remove default handler
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
               "<level>{level: <8}</level> | "
               "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="INFO",
        colorize=True,
    )
    return logger

def setup_telemetry(service_name: str, app: FastAPI):
    """
    Configures OpenTelemetry for a given FastAPI service to export traces to Google Cloud Trace.

    Args:
        service_name: The name of the service for which telemetry is being set up.
        app: The FastAPI application instance to instrument.
    """
    resource = get_aggregated_resources(
        [
            GoogleCloudResourceDetector(raise_on_error=True),
        ],
        Resource.create({SERVICE_NAME: service_name})
    )

    provider = TracerProvider(resource=resource, sampler=sampling.ALWAYS_ON)
    trace.set_tracer_provider(provider)

    cloud_trace_exporter = CloudTraceSpanExporter(resource_regex=r".*")
    provider.add_span_processor(BatchSpanProcessor(cloud_trace_exporter))

    FastAPIInstrumentor.instrument_app(app)
    HTTPXClientInstrumentor().instrument()

    logger.info(f"OpenTelemetry configured for service: {service_name}")