locals {
  otel_collector_service = "otel-collector"
  tempo_service          = "tempo"
}

resource "kubernetes_namespace_v1" "monitoring" {
  metadata {
    name   = var.monitoring_namespace
    labels = { "app.kubernetes.io/part-of" = "inference-slo-platform" }
  }
}

resource "kubernetes_namespace_v1" "observability" {
  metadata {
    name   = var.observability_namespace
    labels = { "app.kubernetes.io/part-of" = "inference-slo-platform" }
  }
}

resource "random_password" "grafana_admin" {
  length  = 24
  special = false
}

resource "helm_release" "metrics_server" {
  count = var.install_metrics_server ? 1 : 0

  name       = "metrics-server"
  repository = "https://kubernetes-sigs.github.io/metrics-server/"
  chart      = "metrics-server"
  version    = var.chart_versions.metrics_server
  namespace  = "kube-system"
  timeout    = var.helm_timeout_seconds

  values = [yamlencode({
    args = concat(
      ["--metric-resolution=15s"],
      var.metrics_server_insecure_tls ? ["--kubelet-insecure-tls"] : [],
    )
  })]
}

resource "helm_release" "kube_prometheus_stack" {
  name       = "kube-prometheus-stack"
  repository = "https://prometheus-community.github.io/helm-charts"
  chart      = "kube-prometheus-stack"
  version    = var.chart_versions.kube_prometheus_stack
  namespace  = kubernetes_namespace_v1.monitoring.metadata[0].name
  timeout    = var.helm_timeout_seconds

  values = [templatefile("${path.module}/values/kube-prometheus-stack.yaml.tftpl", {
    retention                     = var.prometheus_retention
    disable_control_plane_scrapes = var.disable_control_plane_scrapes
    otel_collector_target         = "${local.otel_collector_service}.${var.observability_namespace}.svc.cluster.local"
    tempo_url                     = "http://${local.tempo_service}.${var.observability_namespace}.svc.cluster.local:3200"
  })]

  set_sensitive = [{
    name  = "grafana.adminPassword"
    value = random_password.grafana_admin.result
  }]
}

resource "helm_release" "tempo" {
  name       = "tempo"
  repository = "https://grafana.github.io/helm-charts"
  chart      = "tempo"
  version    = var.chart_versions.tempo
  namespace  = kubernetes_namespace_v1.observability.metadata[0].name
  timeout    = var.helm_timeout_seconds

  values = [file("${path.module}/values/tempo.yaml")]
}

resource "helm_release" "otel_collector" {
  name       = "otel-collector"
  repository = "https://open-telemetry.github.io/opentelemetry-helm-charts"
  chart      = "opentelemetry-collector"
  version    = var.chart_versions.opentelemetry_collector
  namespace  = kubernetes_namespace_v1.observability.metadata[0].name
  timeout    = var.helm_timeout_seconds

  values = [templatefile("${path.module}/values/otel-collector.yaml.tftpl", {
    image_tag  = var.otel_collector_image_tag
    tempo_otlp = "${local.tempo_service}.${var.observability_namespace}.svc.cluster.local:4317"
    fullname   = local.otel_collector_service
  })]

  depends_on = [helm_release.tempo]
}
