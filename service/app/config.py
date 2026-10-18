"""Service configuration, read once from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    return default if raw is None or raw == "" else int(raw)


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True, slots=True)
class Settings:
    model_dir: Path
    host: str
    port: int
    max_batch_size: int
    log_level: str
    telemetry_enabled: bool
    metric_export_interval_ms: int
    graceful_shutdown_seconds: int

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            model_dir=Path(os.environ.get("MODEL_DIR", "/app/model")),
            host=os.environ.get("HOST", "0.0.0.0"),
            port=_env_int("PORT", 8080),
            max_batch_size=_env_int("MAX_BATCH_SIZE", 32),
            log_level=os.environ.get("LOG_LEVEL", "INFO").upper(),
            telemetry_enabled=_env_bool("TELEMETRY_ENABLED", True),
            metric_export_interval_ms=_env_int("OTEL_METRIC_EXPORT_INTERVAL", 10_000),
            graceful_shutdown_seconds=_env_int("GRACEFUL_SHUTDOWN_SECONDS", 20),
        )
