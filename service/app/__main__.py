"""Process entrypoint: ``python -m app``."""

from __future__ import annotations

import uvicorn

from app.config import Settings
from app.logging_setup import configure_logging
from app.main import create_app
from app.telemetry import build_telemetry, install_global


def main() -> None:
    settings = Settings.from_env()
    configure_logging(settings.log_level)
    telemetry = build_telemetry(
        export=settings.telemetry_enabled,
        export_interval_ms=settings.metric_export_interval_ms,
    )
    install_global(telemetry)
    app = create_app(settings, telemetry)
    # Uvicorn handles SIGTERM: it stops accepting new connections, waits up to
    # timeout_graceful_shutdown for in-flight requests, then runs lifespan shutdown.
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        log_config=None,
        access_log=False,
        timeout_graceful_shutdown=settings.graceful_shutdown_seconds,
    )


if __name__ == "__main__":
    main()
