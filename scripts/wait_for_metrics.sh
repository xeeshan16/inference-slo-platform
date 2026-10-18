#!/usr/bin/env bash
# Block until application metrics are visible in Prometheus and the SLO rules are loaded.
set -euo pipefail
PORT="${PROM_PORT:-9090}"
kubectl -n monitoring port-forward svc/kps-prometheus "$PORT:9090" >/dev/null 2>&1 &
PF=$!
trap 'kill $PF 2>/dev/null || true' EXIT
q() { curl -sf "http://localhost:$PORT/api/v1/query" --data-urlencode "query=$1" | jq -r '.data.result | length'; }
for i in $(seq 1 60); do
  series=$(q 'inference_request_duration_seconds_count{route="/predict"}' 2>/dev/null || echo 0)
  rules=$(q 'slo:objective:ratio' 2>/dev/null || echo 0)
  echo "attempt $i: predict series=$series slo rules=$rules"
  if [[ "$series" -gt 0 && "$rules" -gt 0 ]]; then
    curl -sf "http://localhost:$PORT/api/v1/query" \
      --data-urlencode 'query=inference_request_duration_seconds_count{route="/predict"}' | jq -c '.data.result[].metric'
    exit 0
  fi
  sleep 5
done
echo "metrics did not arrive in Prometheus" >&2
curl -sf "http://localhost:$PORT/api/v1/targets?state=active" | jq -c '.data.activeTargets[] | {job: .labels.job, health, lastError}' | grep -i otel || true
exit 1
