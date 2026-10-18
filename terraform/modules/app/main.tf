locals {
  image = "${var.image_repository}:${var.image_tag}"
}

resource "kubernetes_namespace_v1" "app" {
  metadata {
    name   = var.namespace
    labels = { "app.kubernetes.io/part-of" = "inference-slo-platform" }
  }
}

resource "kubernetes_namespace_v1" "loadtest" {
  metadata {
    name   = var.loadtest_namespace
    labels = { "app.kubernetes.io/part-of" = "inference-slo-platform" }
  }
}

# kind nodes cannot pull images built on the host, so side-load them.
# Re-runs whenever the tag changes.
resource "terraform_data" "kind_load_image" {
  count            = var.kind_cluster_name == null ? 0 : 1
  triggers_replace = [local.image, var.kind_cluster_name]

  provisioner "local-exec" {
    command = "kind load docker-image ${local.image} --name ${var.kind_cluster_name}"
  }
}

resource "helm_release" "inference" {
  name      = "inference-service"
  chart     = var.chart_path
  namespace = kubernetes_namespace_v1.app.metadata[0].name
  timeout   = 300
  wait      = true
  atomic    = false

  values = concat([yamlencode({
    image = {
      repository = var.image_repository
      tag        = var.image_tag
    }
    otel = {
      endpoint = var.otel_endpoint
    }
    networkPolicy = {
      ingressNamespaces = [var.loadtest_namespace, var.monitoring_namespace]
      otelNamespace     = var.otel_namespace
    }
  })], var.chart_values)

  depends_on = [terraform_data.kind_load_image]
}

resource "kubernetes_config_map_v1" "dashboard" {
  metadata {
    name      = "inference-slo-dashboard"
    namespace = var.monitoring_namespace
    labels    = { grafana_dashboard = "1" }
  }
  data = {
    "inference-slo.json" = file("${path.module}/dashboards/inference-slo.json")
  }
}
