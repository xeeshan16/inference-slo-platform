"""FastAPI application: /predict, /healthz, /readyz."""

from __future__ import annotations

import logging
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Response, status
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.metrics import NoOpMeterProvider

from app.config import Settings
from app.middleware import MetricsMiddleware
from app.model import DigitsModel
from app.schemas import HealthResponse, Prediction, PredictRequest, PredictResponse
from app.telemetry import Telemetry

logger = logging.getLogger("inference")


class State:
    """Mutable process state shared by the handlers."""

    def __init__(self) -> None:
        self.model: DigitsModel | None = None
        self.draining = False


def create_app(
    settings: Settings, telemetry: Telemetry, model: DigitsModel | None = None
) -> FastAPI:
    state = State()

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        started = time.perf_counter()
        state.model = model or DigitsModel.load(settings.model_dir)
        state.model.warmup()
        logger.info(
            "model loaded",
            extra={
                "model_version": state.model.version,
                "load_seconds": round(time.perf_counter() - started, 3),
            },
        )
        yield
        # Uvicorn calls this after it has stopped accepting connections and
        # in-flight requests have finished (or the graceful timeout expired).
        state.draining = True
        logger.info("shutting down, flushing telemetry")
        telemetry.shutdown()

    app = FastAPI(title="digits-inference", version="1.0.0", lifespan=lifespan)

    @app.get("/healthz", response_model=HealthResponse)
    async def healthz() -> HealthResponse:
        """Liveness: the process is up and the event loop is responsive."""
        return HealthResponse(status="ok")

    @app.get("/readyz", response_model=HealthResponse)
    async def readyz(response: Response) -> HealthResponse:
        """Readiness: the model is loaded and the pod is not draining."""
        if state.model is None or state.draining:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            return HealthResponse(status="not-ready")
        return HealthResponse(status="ready")

    @app.post("/predict", response_model=PredictResponse)
    async def predict(request: PredictRequest) -> PredictResponse:
        if state.model is None:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "model not loaded")
        batch = len(request.instances)
        if batch > settings.max_batch_size:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                f"batch size {batch} exceeds limit {settings.max_batch_size}",
            )
        telemetry.batch_size.record(batch)
        with telemetry.tracer.start_as_current_span("model.predict") as span:
            span.set_attribute("model.version", state.model.version)
            span.set_attribute("model.batch_size", batch)
            started = time.perf_counter()
            output = state.model.predict(request.instances)
            telemetry.model_duration.record(time.perf_counter() - started)
        return PredictResponse(
            model_version=state.model.version,
            predictions=[
                Prediction(label=label, probability=prob)
                for label, prob in zip(output.labels, output.probabilities, strict=True)
            ],
        )

    FastAPIInstrumentor.instrument_app(
        app,
        tracer_provider=telemetry.tracer_provider,
        meter_provider=NoOpMeterProvider(),  # RED metrics come from MetricsMiddleware
        excluded_urls="healthz,readyz",
    )
    app.add_middleware(MetricsMiddleware, telemetry=telemetry)
    return app
