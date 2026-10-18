"""ONNX Runtime model wrapper."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import numpy.typing as npt
import onnxruntime as ort


@dataclass(frozen=True, slots=True)
class ModelOutput:
    labels: list[int]
    probabilities: list[float]


class DigitsModel:
    """Loads the exported classifier once and runs batched inference."""

    def __init__(self, session: Any, metadata: dict[str, Any]) -> None:
        self._session = session
        self._input_name: str = session.get_inputs()[0].name
        self.metadata = metadata
        self.version = str(metadata.get("version", "unknown"))
        self.n_features = int(metadata.get("n_features", 64))

    @classmethod
    def load(cls, model_dir: Path) -> DigitsModel:
        options = ort.SessionOptions()
        session = ort.InferenceSession(
            str(model_dir / "model.onnx"), options, providers=["CPUExecutionProvider"]
        )
        metadata = json.loads((model_dir / "model.json").read_text())
        return cls(session, metadata)

    def predict(self, instances: list[list[float]]) -> ModelOutput:
        batch: npt.NDArray[np.float32] = np.asarray(instances, dtype=np.float32)
        labels, probabilities = self._session.run(None, {self._input_name: batch})
        best = np.max(probabilities, axis=1)
        return ModelOutput(
            labels=[int(v) for v in labels],
            probabilities=[round(float(v), 6) for v in best],
        )

    def warmup(self) -> None:
        """Run one inference so the first real request does not pay one-off init costs."""
        self.predict([[0.0] * self.n_features])
