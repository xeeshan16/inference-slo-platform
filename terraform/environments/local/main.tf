module "cluster" {
  source = "../../modules/cluster"

  name         = var.cluster_name
  node_image   = var.node_image
  worker_count = var.worker_count
}

module "platform" {
  source = "../../modules/platform"

  # kind kubelets use self-signed serving certificates.
  metrics_server_insecure_tls = true

  depends_on = [module.cluster]
}

module "app" {
  source = "../../modules/app"

  chart_path           = "${path.module}/../../../charts/inference-service"
  image_tag            = var.image_tag
  kind_cluster_name    = module.cluster.name
  monitoring_namespace = module.platform.monitoring_namespace
  otel_namespace       = module.platform.observability_namespace
  otel_endpoint        = module.platform.otel_collector_otlp_http_endpoint
  chart_values         = [for f in var.app_values_files : file("${path.module}/${f}")]

  depends_on = [module.platform]
}
