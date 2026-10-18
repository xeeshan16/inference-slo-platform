from __future__ import annotations

from typing import Any

import numpy as np
import pytest
from sklearn.datasets import load_digits

from tests.conftest import Harness


def _digits(n: int) -> list[list[float]]:
    features, _ = load_digits(return_X_y=True)
    return [[float(v) for v in row] for row in features[:n]]


def test_healthz_and_readyz(harness: Harness) -> None:
    assert harness.client.get("/healthz").json() == {"status": "ok"}
    ready = harness.client.get("/readyz")
    assert ready.status_code == 200
    assert ready.json() == {"status": "ready"}


def test_predict_returns_one_prediction_per_instance(harness: Harness) -> None:
    response = harness.client.post("/predict", json={"instances": _digits(8)})
    assert response.status_code == 200
    body = response.json()
    assert len(body["predictions"]) == 8
    assert body["model_version"].startswith("rf10")
    for prediction in body["predictions"]:
        assert 0 <= prediction["label"] <= 9
        assert 0.0 < prediction["probability"] <= 1.0


def test_predict_is_accurate_on_known_digits(harness: Harness) -> None:
    features, labels = load_digits(return_X_y=True)
    rows = [[float(v) for v in row] for row in features[:32]]
    body = harness.client.post("/predict", json={"instances": rows}).json()
    predicted = np.array([p["label"] for p in body["predictions"]])
    assert (predicted == labels[:32]).mean() >= 0.9


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"instances": []},
        {"instances": [[1.0] * 63]},
        {"instances": [[1.0] * 65]},
        {"instances": [[17.0] * 64]},
        {"instances": [[-1.0] * 64]},
        {"instances": [["x"] * 64]},
        {"instances": [[1.0] * 64], "unexpected": True},
    ],
)
def test_predict_rejects_invalid_input(harness: Harness, payload: dict[str, Any]) -> None:
    assert harness.client.post("/predict", json=payload).status_code == 422


def test_predict_rejects_oversized_batch(harness: Harness) -> None:
    response = harness.client.post("/predict", json={"instances": [[0.0] * 64] * 33})
    assert response.status_code == 422
    assert "exceeds limit" in response.json()["detail"]


def _histogram_points(harness: Harness, name: str) -> list[Any]:
    data = harness.metrics.get_metrics_data()
    assert data is not None
    points: list[Any] = []
    for resource_metrics in data.resource_metrics:
        for scope_metrics in resource_metrics.scope_metrics:
            for metric in scope_metrics.metrics:
                if metric.name == name:
                    points.extend(metric.data.data_points)
    return points


def test_request_duration_metric_has_slo_bucket_and_labels(harness: Harness) -> None:
    harness.client.post("/predict", json={"instances": _digits(1)})
    harness.client.post("/predict", json={"instances": []})
    points = _histogram_points(harness, "inference.request.duration")
    by_status = {
        p.attributes["status_code"]: p for p in points if p.attributes["route"] == "/predict"
    }
    assert set(by_status) == {"200", "422"}
    assert 0.3 in by_status["200"].explicit_bounds
    assert by_status["200"].count == 1


def test_unknown_routes_collapse_to_single_label(harness: Harness) -> None:
    harness.client.get("/does-not-exist")
    harness.client.get("/also-missing")
    points = _histogram_points(harness, "inference.request.duration")
    routes = {p.attributes["route"] for p in points}
    assert "other" in routes
    assert "/does-not-exist" not in routes


def test_predict_emits_model_span(harness: Harness) -> None:
    harness.client.post("/predict", json={"instances": _digits(2)})
    names = [span.name for span in harness.spans.get_finished_spans()]
    assert "model.predict" in names
    model_span = next(s for s in harness.spans.get_finished_spans() if s.name == "model.predict")
    assert model_span.attributes is not None
    assert model_span.attributes["model.batch_size"] == 2


def test_health_probes_are_not_traced(harness: Harness) -> None:
    harness.client.get("/healthz")
    harness.client.get("/readyz")
    assert harness.spans.get_finished_spans() == ()
