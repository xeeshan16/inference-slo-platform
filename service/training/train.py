"""Train the digits classifier and export it to ONNX.

Runs inside the Docker builder stage, so the runtime image only needs
onnxruntime and never ships scikit-learn. The dataset (8x8 handwritten
digits, 1797 samples) is bundled with scikit-learn, so the build is
hermetic and reproducible (fixed random_state).
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
from skl2onnx import to_onnx
from sklearn.datasets import load_digits
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split

N_FEATURES = 64


def train(out_dir: Path, n_estimators: int = 300, seed: int = 0) -> dict[str, object]:
    features, labels = load_digits(return_X_y=True)
    features = features.astype(np.float32)
    x_train, x_test, y_train, y_test = train_test_split(
        features, labels, test_size=0.2, random_state=seed, stratify=labels
    )
    model = RandomForestClassifier(n_estimators=n_estimators, random_state=seed, n_jobs=-1)
    model.fit(x_train, y_train)
    accuracy = float(model.score(x_test, y_test))

    onnx_model = to_onnx(
        model,
        x_train[:1],
        options={id(model): {"zipmap": False}},
        target_opset={"": 17, "ai.onnx.ml": 3},
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "model.onnx").write_bytes(onnx_model.SerializeToString())

    metadata: dict[str, object] = {
        "name": "digits-random-forest",
        "version": f"rf{n_estimators}-seed{seed}",
        "dataset": "sklearn.datasets.load_digits",
        "n_features": N_FEATURES,
        "classes": [int(c) for c in model.classes_],
        "test_accuracy": round(accuracy, 4),
        "trained_at": int(time.time()),
    }
    (out_dir / "model.json").write_text(json.dumps(metadata, indent=2))
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("model"))
    parser.add_argument("--n-estimators", type=int, default=300)
    args = parser.parse_args()
    print(json.dumps(train(args.out, args.n_estimators)))


if __name__ == "__main__":
    main()
