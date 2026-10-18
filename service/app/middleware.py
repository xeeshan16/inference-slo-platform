"""ASGI middleware that records RED metrics for every HTTP request."""

from __future__ import annotations

import time

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.telemetry import Telemetry

# Bound label cardinality: unknown paths collapse into one series.
KNOWN_ROUTES = frozenset({"/predict", "/healthz", "/readyz"})


class MetricsMiddleware:
    def __init__(self, app: ASGIApp, telemetry: Telemetry) -> None:
        self.app = app
        self.telemetry = telemetry

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path: str = scope["path"]
        route = path if path in KNOWN_ROUTES else "other"
        method: str = scope["method"]
        status_code = 500
        inflight_attrs = {"route": route}
        self.telemetry.inflight.add(1, inflight_attrs)
        start = time.perf_counter()

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = int(message["status"])
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            elapsed = time.perf_counter() - start
            self.telemetry.inflight.add(-1, inflight_attrs)
            self.telemetry.request_duration.record(
                elapsed,
                {"route": route, "method": method, "status_code": str(status_code)},
            )
