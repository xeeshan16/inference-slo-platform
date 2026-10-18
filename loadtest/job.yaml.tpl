# Rendered by scripts/loadtest.sh (envsubst). One Job per scenario run.
apiVersion: batch/v1
kind: Job
metadata:
  name: k6-${RUN_ID}
  namespace: loadtest
  labels:
    app.kubernetes.io/name: k6
    loadtest/run-id: "${RUN_ID}"
spec:
  backoffLimit: 0
  ttlSecondsAfterFinished: 3600
  template:
    metadata:
      labels:
        app.kubernetes.io/name: k6
    spec:
      restartPolicy: Never
      securityContext:
        runAsNonRoot: true
        runAsUser: 12345
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: k6
          image: grafana/k6:2.3.0
          args: ["run", "--quiet", "--no-color", "/scripts/inference.js"]
          env:
            - { name: SCENARIO, value: "${SCENARIO}" }
            - { name: RATE, value: "${RATE}" }
            - { name: PEAK, value: "${PEAK}" }
            - { name: DURATION, value: "${DURATION}" }
            - { name: BATCH, value: "${BATCH}" }
            - { name: K6_NO_USAGE_REPORT, value: "true" }
          resources:
            requests:
              cpu: 500m
              memory: 256Mi
            limits:
              cpu: "1"
              memory: 1Gi
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities:
              drop: ["ALL"]
          volumeMounts:
            - { name: scripts, mountPath: /scripts }
            - { name: tmp, mountPath: /tmp }
      volumes:
        - name: scripts
          configMap:
            name: k6-scripts
        - name: tmp
          emptyDir: {}
