"""OpenTelemetry setup: traces and RED metrics exported over OTLP/HTTP."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import MetricReader, PeriodicExportingMetricReader
from opentelemetry.sdk.metrics.view import ExplicitBucketHistogramAggregation, View
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import SpanProcessor, TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# Bucket boundaries (seconds). Dense around the 300 ms SLO threshold so the
# SLI ("le=0.3") is an exact bucket boundary and p95/p99 interpolation near
# the threshold is reasonably precise.
REQUEST_DURATION_BUCKETS: tuple[float, ...] = (
    0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.15, 0.2, 0.25, 0.3,
    0.35, 0.4, 0.5, 0.75, 1.0, 2.5, 5.0, 10.0,
)  # fmt: skip
MODEL_DURATION_BUCKETS: tuple[float, ...] = (
    0.0005, 0.001, 0.0025, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0,
)  # fmt: skip

REQUEST_DURATION = "inference.request.duration"
MODEL_DURATION = "inference.model.duration"
INFLIGHT = "inference.requests.inflight"
BATCH_SIZE = "inference.batch.size"


@dataclass
class Telemetry:
    meter_provider: MeterProvider
    tracer_provider: TracerProvider

    def __post_init__(self) -> None:
        meter = self.meter_provider.get_meter("inference-service")
        self.tracer = self.tracer_provider.get_tracer("inference-service")
        self.request_duration = meter.create_histogram(
            REQUEST_DURATION, unit="s", description="Server-side HTTP request latency."
        )
        self.model_duration = meter.create_histogram(
            MODEL_DURATION, unit="s", description="Time spent inside the model runtime."
        )
        self.inflight = meter.create_up_down_counter(
            INFLIGHT, unit="{request}", description="Requests currently being handled."
        )
        self.batch_size = meter.create_histogram(
            BATCH_SIZE, unit="{instance}", description="Instances per predict request."
        )

    def shutdown(self) -> None:
        self.tracer_provider.shutdown()
        self.meter_provider.shutdown()


def _views() -> list[View]:
    return [
        View(
            instrument_name=REQUEST_DURATION,
            aggregation=ExplicitBucketHistogramAggregation(REQUEST_DURATION_BUCKETS),
        ),
        View(
            instrument_name=MODEL_DURATION,
            aggregation=ExplicitBucketHistogramAggregation(MODEL_DURATION_BUCKETS),
        ),
        View(
            instrument_name=BATCH_SIZE,
            aggregation=ExplicitBucketHistogramAggregation((1, 2, 4, 8, 16, 32, 64)),
        ),
    ]


def build_telemetry(
    *,
    export: bool,
    export_interval_ms: int = 10_000,
    metric_readers: Sequence[MetricReader] = (),
    span_processors: Sequence[SpanProcessor] = (),
) -> Telemetry:
    """Create meter and tracer providers.

    With ``export=True`` the OTLP exporters read their endpoint and headers from
    the standard ``OTEL_EXPORTER_OTLP_*`` environment variables. Tests pass
    in-memory readers/processors and ``export=False`` instead.
    """
    resource = Resource.create()  # honours OTEL_SERVICE_NAME / OTEL_RESOURCE_ATTRIBUTES
    readers = list(metric_readers)
    processors = list(span_processors)
    if export:
        readers.append(
            PeriodicExportingMetricReader(
                OTLPMetricExporter(), export_interval_millis=export_interval_ms
            )
        )
        processors.append(BatchSpanProcessor(OTLPSpanExporter()))

    meter_provider = MeterProvider(resource=resource, metric_readers=readers, views=_views())
    tracer_provider = TracerProvider(resource=resource)
    for processor in processors:
        tracer_provider.add_span_processor(processor)
    return Telemetry(meter_provider=meter_provider, tracer_provider=tracer_provider)


def install_global(telemetry: Telemetry) -> None:
    trace.set_tracer_provider(telemetry.tracer_provider)
    metrics.set_meter_provider(telemetry.meter_provider)
