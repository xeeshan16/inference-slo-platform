output "monitoring_namespace" {
  description = "Namespace running Prometheus, Alertmanager and Grafana."
  value       = kubernetes_namespace_v1.monitoring.metadata[0].name
}

output "observability_namespace" {
  description = "Namespace running the OpenTelemetry Collector and Tempo."
  value       = kubernetes_namespace_v1.observability.metadata[0].name
}

output "otel_collector_otlp_http_endpoint" {
  description = "In-cluster OTLP/HTTP endpoint for applications."
  value       = "http://${local.otel_collector_service}.${var.observability_namespace}.svc.cluster.local:4318"
}

output "prometheus_service" {
  description = "Prometheus service (namespace/name:port) for port-forwarding."
  value       = "${var.monitoring_namespace}/kps-prometheus:9090"
}

output "grafana_service" {
  description = "Grafana service (namespace/name:port) for port-forwarding."
  value       = "${var.monitoring_namespace}/grafana:80"
}

output "grafana_admin_password" {
  description = "Generated Grafana admin password (user: admin)."
  value       = random_password.grafana_admin.result
  sensitive   = true
}

output "ready" {
  description = "Marker other modules can depend on once the platform charts are installed."
  value = {
    kube_prometheus_stack = helm_release.kube_prometheus_stack.status
    otel_collector        = helm_release.otel_collector.status
    tempo                 = helm_release.tempo.status
  }
}
