from __future__ import annotations

from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from opentelemetry.sdk.metrics.export import InMemoryMetricReader
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from app.config import Settings
from app.main import create_app
from app.telemetry import build_telemetry
from training.train import train


@pytest.fixture(scope="session")
def model_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    out = tmp_path_factory.mktemp("model")
    train(out, n_estimators=10)
    return out


@pytest.fixture
def settings(model_dir: Path) -> Settings:
    return replace(Settings.from_env(), model_dir=model_dir, telemetry_enabled=False)


class Harness:
    def __init__(
        self, client: TestClient, metrics: InMemoryMetricReader, spans: InMemorySpanExporter
    ) -> None:
        self.client = client
        self.metrics = metrics
        self.spans = spans


@pytest.fixture
def harness(settings: Settings) -> Iterator[Harness]:
    reader = InMemoryMetricReader()
    exporter = InMemorySpanExporter()
    telemetry = build_telemetry(
        export=False, metric_readers=[reader], span_processors=[SimpleSpanProcessor(exporter)]
    )
    app = create_app(settings, telemetry)
    with TestClient(app) as client:
        yield Harness(client, reader, exporter)
