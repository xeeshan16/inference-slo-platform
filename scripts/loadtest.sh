#!/usr/bin/env bash
# Run one k6 scenario in-cluster, then collect SLO results from Prometheus.
#
#   scripts/loadtest.sh <scenario> [results_dir]
#
# Scenarios: steady | ramp | spike | rollout (steady load + a rolling restart).
# Tunables (env): RATE, PEAK, DURATION, BATCH, ROLLOUT_AFTER (seconds), SETTLE (seconds).
set -euo pipefail

SCENARIO="${1:?usage: loadtest.sh <steady|ramp|spike|rollout> [results_dir]}"
RESULTS_DIR="${2:-results/local}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export RATE="${RATE:-100}" PEAK="${PEAK:-400}" DURATION="${DURATION:-4m}" BATCH="${BATCH:-8}"
ROLLOUT_AFTER="${ROLLOUT_AFTER:-60}"
SETTLE="${SETTLE:-60}"   # OTel export (10s) + scrape (15s) + rule evaluation, with margin
PROM_PORT="${PROM_PORT:-9090}"

K6_SCENARIO="$SCENARIO"
[[ "$SCENARIO" == "rollout" ]] && K6_SCENARIO="steady"
export SCENARIO="$K6_SCENARIO"
export RUN_ID="${SCENARIO}-$(date +%s)"
mkdir -p "$RESULTS_DIR"
OUT="$RESULTS_DIR/$1"

log() { echo "[$(date -u +%H:%M:%S)] $*"; }

kubectl -n loadtest create configmap k6-scripts --from-file="$ROOT/loadtest/inference.js" \
  --dry-run=client -o yaml | kubectl apply -f - >/dev/null

log "scenario=$1 rate=$RATE peak=$PEAK duration=$DURATION batch=$BATCH"
kubectl -n inference get deploy,hpa,pods -o wide > "$OUT.before.txt" 2>&1 || true

START=$(date +%s)
envsubst < "$ROOT/loadtest/job.yaml.tpl" | kubectl apply -f - >/dev/null
JOB="k6-$RUN_ID"

ROLLOUT_PID=""
if [[ "$1" == "rollout" ]]; then
  (
    sleep "$ROLLOUT_AFTER"
    log "triggering rolling restart"
    kubectl -n inference rollout restart deploy/inference-service
    kubectl -n inference rollout status deploy/inference-service --timeout=300s
    log "rolling restart finished"
  ) &
  ROLLOUT_PID=$!
fi

# Wait for the Job to finish (k6 exits non-zero when its informational thresholds fail;
# that is a result, not a script error).
log "waiting for job $JOB"
for _ in $(seq 1 180); do
  succeeded=$(kubectl -n loadtest get job "$JOB" -o jsonpath='{.status.succeeded}' 2>/dev/null || true)
  failed=$(kubectl -n loadtest get job "$JOB" -o jsonpath='{.status.failed}' 2>/dev/null || true)
  [[ "${succeeded:-0}" -ge 1 || "${failed:-0}" -ge 1 ]] && break
  sleep 5
done
END=$(date +%s)
[[ -n "$ROLLOUT_PID" ]] && wait "$ROLLOUT_PID" || true
log "job finished (succeeded=${succeeded:-0} failed=${failed:-0}) after $((END - START))s"

kubectl -n loadtest logs "job/$JOB" > "$OUT.k6.log" 2>&1 || true
sed -n '/^K6_SUMMARY_BEGIN$/,/^K6_SUMMARY_END$/p' "$OUT.k6.log" | sed '1d;$d' > "$OUT.k6.json" || true
kubectl -n inference get deploy,hpa,pods -o wide > "$OUT.after.txt" 2>&1 || true
kubectl -n inference get events --sort-by=.lastTimestamp > "$OUT.events.txt" 2>&1 || true

cat > "$OUT.meta.json" <<JSON
{"scenario": "$1", "rate": $RATE, "peak": $PEAK, "duration": "$DURATION", "batch": $BATCH,
 "rollout_after_s": $([[ "$1" == "rollout" ]] && echo "$ROLLOUT_AFTER" || echo null),
 "git_sha": "${GITHUB_SHA:-$(git -C "$ROOT" rev-parse HEAD 2>/dev/null || echo unknown)}",
 "run_url": "${GITHUB_SERVER_URL:-}/${GITHUB_REPOSITORY:-}/actions/runs/${GITHUB_RUN_ID:-}"}
JSON

log "settling ${SETTLE}s so the last samples reach Prometheus"
sleep "$SETTLE"

kubectl -n monitoring port-forward svc/kps-prometheus "$PROM_PORT:9090" >/dev/null 2>&1 &
PF_PID=$!
trap 'kill $PF_PID 2>/dev/null || true' EXIT
for _ in $(seq 1 30); do curl -sf "http://localhost:$PROM_PORT/-/ready" >/dev/null && break; sleep 1; done

python3 "$ROOT/scripts/collect_results.py" --prom "http://localhost:$PROM_PORT" \
  --start "$START" --end "$((END + 30))" --scenario "$1" \
  --k6-summary "$OUT.k6.json" --meta "$OUT.meta.json" --out "$OUT.json"
