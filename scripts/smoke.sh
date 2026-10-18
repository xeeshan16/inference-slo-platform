#!/usr/bin/env bash
# Call /predict through the Service from the loadtest namespace (exercises the
# NetworkPolicy) using the service image itself, so no extra image is pulled.
set -euo pipefail
IMAGE="$(kubectl -n inference get deploy inference-service -o jsonpath='{.spec.template.spec.containers[0].image}')"
kubectl -n loadtest delete pod smoke --ignore-not-found >/dev/null
kubectl -n loadtest run smoke --image="$IMAGE" --restart=Never --image-pull-policy=IfNotPresent \
  --overrides='{"spec":{"securityContext":{"runAsNonRoot":true,"runAsUser":10001}}}' \
  --command -- python -c '
import json, urllib.request
url = "http://inference-service.inference.svc.cluster.local:8080"
body = json.dumps({"instances": [[float(i % 17) for i in range(64)]] * 4}).encode()
for i in range(20):
    req = urllib.request.Request(url + "/predict", data=body, headers={"content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=5) as r:
        out = json.load(r)
print(json.dumps(out))
print(urllib.request.urlopen(url + "/readyz", timeout=5).read().decode())
'
for _ in $(seq 1 60); do
  phase=$(kubectl -n loadtest get pod smoke -o jsonpath='{.status.phase}')
  [[ "$phase" == "Succeeded" || "$phase" == "Failed" ]] && break
  sleep 2
done
kubectl -n loadtest logs smoke
[[ "$phase" == "Succeeded" ]]
