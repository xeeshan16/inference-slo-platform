#!/usr/bin/env python3
"""Render a Markdown table from the *.json files written by collect_results.py.

  summarize_results.py results/<label> > results/<label>/SUMMARY.md
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ORDER = ["steady", "ramp", "spike", "rollout"]


def fmt(value: Any, kind: str) -> str:
    if value is None:
        return "n/a"
    if kind == "pct":
        return f"{value * 100:.2f}%"
    if kind == "ms_from_s":
        return f"{value * 1000:.0f}"
    if kind == "ms":
        return f"{value:.0f}"
    if kind == "x":
        return f"{value:.1f}x"
    if kind == "int":
        return f"{value:.0f}"
    return str(value)


def main() -> int:
    directory = Path(sys.argv[1])
    rows = []
    files = [p for p in directory.glob("*.json") if p.name.count(".") == 1]
    files.sort(key=lambda p: ORDER.index(p.stem) if p.stem in ORDER else 99)
    for path in files:
        data = json.loads(path.read_text())
        server, client = data["server"], data.get("client_k6", {})
        meta = data.get("meta", {})
        lat = client.get("latency_ms", {})
        load = f"{meta.get('rate')}" + (
            f"->{meta.get('peak')}" if data["scenario"] in ("ramp", "spike") else ""
        )
        rows.append(
            "| "
            + " | ".join(
                [
                    data["scenario"],
                    f"{load} rps",
                    fmt(server.get("requests"), "int"),
                    fmt(server.get("sli"), "pct"),
                    fmt(client.get("sli"), "pct"),
                    fmt(server.get("burn_rate_over_window"), "x"),
                    fmt(server.get("max_burn_rate_5m"), "x"),
                    fmt(server.get("errors_5xx"), "int"),
                    fmt(server.get("p50_s"), "ms_from_s"),
                    fmt(server.get("p95_s"), "ms_from_s"),
                    fmt(server.get("p99_s"), "ms_from_s"),
                    fmt(lat.get("p95"), "ms"),
                    fmt(lat.get("p99"), "ms"),
                    fmt(client.get("failed_ratio"), "pct"),
                    fmt(client.get("sli_bad", {}).get("transport"), "int"),
                    fmt(client.get("dropped_iterations"), "int"),
                    fmt(server.get("cpu_throttled_ratio"), "pct"),
                    f"{fmt(server.get('replicas_min'), 'int')}-{fmt(server.get('replicas_max'), 'int')}",
                    fmt(server.get("container_restarts"), "int"),
                ]
            )
            + " |"
        )
    header = (
        "| scenario | load | requests (server) | SLI (server) | SLI (k6) | burn (window) | max burn 5m | 5xx "
        "| p50 ms | p95 ms | p99 ms | k6 p95 ms | k6 p99 ms | k6 failed | k6 transport errors | k6 dropped "
        "| CPU throttled | replicas | restarts |\n"
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"
    )
    print(header)
    print("\n".join(rows))
    print(
        "\nServer-side columns come from Prometheus (OTel histogram, buckets interpolated);"
        " k6 columns are measured by the client. SLI = share of /predict requests that are"
        " non-5xx and <= 300 ms. SLI (k6) applies the same rule on the client and also counts"
        " requests that never got an HTTP response (transport errors)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
