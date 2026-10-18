#!/usr/bin/env bash
# Make scenarios independent: wait until the HPA has scaled back to its minimum
# and every pod is ready before starting the next load test.
set -euo pipefail
TIMEOUT="${BASELINE_TIMEOUT:-600}"
deadline=$(( $(date +%s) + TIMEOUT ))
min=$(kubectl -n inference get hpa inference-service -o jsonpath='{.spec.minReplicas}')
while true; do
  replicas=$(kubectl -n inference get deploy inference-service -o jsonpath='{.status.replicas}')
  ready=$(kubectl -n inference get deploy inference-service -o jsonpath='{.status.readyReplicas}')
  if [[ "$replicas" == "$min" && "$ready" == "$min" ]]; then
    echo "baseline reached: $ready/$min ready"
    sleep 30   # let the 1m/5m rate windows drain the previous scenario
    exit 0
  fi
  if (( $(date +%s) > deadline )); then
    echo "baseline not reached after ${TIMEOUT}s (replicas=$replicas ready=$ready min=$min); continuing"
    exit 0
  fi
  sleep 10
done
