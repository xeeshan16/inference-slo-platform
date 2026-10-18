#!/usr/bin/env python3
"""Query Prometheus for SLO results of one load-test window and merge them with k6's summary.

Usage:
  collect_results.py --prom http://localhost:9090 --start 1700000000 --end 1700000300 \
      --k6-summary run.k6.json --scenario steady --out results/steady.json

Only the standard library is used so it runs on any CI runner.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

SLO_TARGET = 0.99
THRESHOLD = "0.3"
SEL = 'route="/predict"'
BUCKET = "inference_request_duration_seconds_bucket"
COUNT = "inference_request_duration_seconds_count"
NS = 'namespace="inference", container="inference-service"'


def query(prom: str, expr: str, at: int) -> float | None:
    url = f"{prom}/api/v1/query?" + urllib.parse.urlencode({"query": expr, "time": at})
    with urllib.request.urlopen(url, timeout=30) as resp:
        body = json.load(resp)
    result = body["data"]["result"]
    if not result:
        return None
    value = float(result[0]["value"][1])
    return None if math.isnan(value) else value


def query_range(prom: str, expr: str, start: int, end: int, step: int = 15) -> list[list[Any]]:
    params = {"query": expr, "start": start, "end": end, "step": step}
    url = f"{prom}/api/v1/query_range?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=30) as resp:
        body = json.load(resp)
    series = body["data"]["result"]
    if not series:
        return []
    return [[int(float(t)), float(v)] for t, v in series[0]["values"]]


def k6_metrics(summary: dict[str, Any]) -> dict[str, Any]:
    metrics = summary.get("metrics", {})

    def val(name: str, key: str) -> float | None:
        metric = metrics.get(name, {})
        values = metric.get("values", metric)  # k6 summary layouts differ across versions
        raw = values.get(key)
        return None if raw is None else float(raw)

    duration = "http_req_duration"
    good = val("sli_good", "count") or 0.0
    bad = {
        "slow": val("sli_bad_slow", "count") or 0.0,
        "5xx": val("sli_bad_5xx", "count") or 0.0,
        "transport": val("sli_bad_transport", "count") or 0.0,
    }
    total = good + sum(bad.values())
    return {
        "sli": (good / total) if total else None,
        "sli_bad": bad,
        "requests": val("http_reqs", "count"),
        "rps": val("http_reqs", "rate"),
        "failed_ratio": val("http_req_failed", "rate"),
        "dropped_iterations": val("dropped_iterations", "count") or 0.0,
        "latency_ms": {
            "p50": val(duration, "med"),
            "p90": val(duration, "p(90)"),
            "p95": val(duration, "p(95)"),
            "p99": val(duration, "p(99)"),
            "max": val(duration, "max"),
        },
        "vus_max": val("vus_max", "value") or val("vus_max", "max"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prom", required=True)
    parser.add_argument("--start", type=int, required=True)
    parser.add_argument("--end", type=int, required=True)
    parser.add_argument("--scenario", required=True)
    parser.add_argument("--k6-summary", type=Path)
    parser.add_argument("--meta", type=Path, help="JSON file with extra run metadata")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    window = f"{args.end - args.start}s"
    at = args.end
    total_expr = f"sum(increase({COUNT}{{{SEL}}}[{window}]))"
    good_expr = (
        f'sum(increase({BUCKET}{{{SEL},le="{THRESHOLD}",status_code!~"5.."}}[{window}]))'
    )
    errors_expr = f'sum(increase({COUNT}{{{SEL},status_code=~"5.."}}[{window}]))'
    q = {
        "requests": total_expr,
        "good": good_expr,
        "errors_5xx": errors_expr,
        **{
            f"p{int(p * 100)}_s": (
                f"histogram_quantile({p}, sum by (le) (increase({BUCKET}{{{SEL}}}[{window}])))"
            )
            for p in (0.5, 0.95, 0.99)
        },
        "max_burn_rate_5m": f'max_over_time(slo:burn_rate:5m{{slo="inference-predict"}}[{window}])',
        "cpu_throttled_ratio": (
            f"sum(increase(container_cpu_cfs_throttled_periods_total{{{NS}}}[{window}]))"
            f" / sum(increase(container_cpu_cfs_periods_total{{{NS}}}[{window}]))"
        ),
        "cpu_cores_avg": f"sum(rate(container_cpu_usage_seconds_total{{{NS}}}[{window}]))",
        "replicas_max": (
            'max_over_time(kube_horizontalpodautoscaler_status_current_replicas{namespace="inference"}'
            f"[{window}])"
        ),
        "replicas_min": (
            'min_over_time(kube_horizontalpodautoscaler_status_current_replicas{namespace="inference"}'
            f"[{window}])"
        ),
        "container_restarts": (
            f'sum(increase(kube_pod_container_status_restarts_total{{namespace="inference"}}[{window}]))'
        ),
        "alerts_fired": (
            'count(max_over_time(ALERTS{alertstate="firing", slo="inference-predict"}'
            f"[{window}])) or vector(0)"
        ),
    }
    prom: dict[str, float | None] = {}
    for key, expr in q.items():
        try:
            prom[key] = query(args.prom, expr, at)
        except Exception as exc:  # report, don't crash the whole collection
            print(f"query {key} failed: {exc}", file=sys.stderr)
            prom[key] = None

    sli = None
    if prom["requests"] and prom["good"] is not None:
        sli = prom["good"] / prom["requests"]
    burn = None if sli is None else (1 - sli) / (1 - SLO_TARGET)

    series_exprs = {
        "p99_s": f"histogram_quantile(0.99, sum by (le) (rate({BUCKET}{{{SEL}}}[1m])))",
        "bad_ratio_1m": (
            f'1 - (sum(rate({BUCKET}{{{SEL},le="{THRESHOLD}",status_code!~"5.."}}[1m]))'
            f" / sum(rate({COUNT}{{{SEL}}}[1m])))"
        ),
        "rps": f"sum(rate({COUNT}{{{SEL}}}[1m]))",
        "errors_5xx_rps": f'sum(rate({COUNT}{{{SEL},status_code=~"5.."}}[1m])) or vector(0)',
        "burn_rate_5m": 'slo:burn_rate:5m{slo="inference-predict"}',
        "replicas": 'kube_horizontalpodautoscaler_status_current_replicas{namespace="inference"}',
        "ready_pods": 'count(kube_pod_status_ready{namespace="inference", condition="true"} == 1)',
        "cpu_throttled_ratio": (
            f"sum(rate(container_cpu_cfs_throttled_periods_total{{{NS}}}[1m]))"
            f" / sum(rate(container_cpu_cfs_periods_total{{{NS}}}[1m]))"
        ),
        "cpu_cores": f"sum(rate(container_cpu_usage_seconds_total{{{NS}}}[1m]))",
    }
    series: dict[str, list[list[Any]]] = {}
    for key, expr in series_exprs.items():
        try:
            series[key] = query_range(args.prom, expr, args.start, args.end)
        except Exception as exc:
            print(f"range query {key} failed: {exc}", file=sys.stderr)
            series[key] = []

    result: dict[str, Any] = {
        "scenario": args.scenario,
        "window": {"start": args.start, "end": args.end, "seconds": args.end - args.start},
        "slo": {"target": SLO_TARGET, "threshold_s": float(THRESHOLD)},
        "server": {
            "sli": sli,
            "burn_rate_over_window": burn,
            **prom,
        },
        "series": series,
    }
    if args.k6_summary and args.k6_summary.exists():
        result["client_k6"] = k6_metrics(json.loads(args.k6_summary.read_text()))
    if args.meta and args.meta.exists():
        result["meta"] = json.loads(args.meta.read_text())

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2))
    printable = {k: v for k, v in result.items() if k != "series"}
    print(json.dumps(printable, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
