variable "monitoring_namespace" {
  description = "Namespace for Prometheus, Alertmanager and Grafana."
  type        = string
  default     = "monitoring"
}

variable "observability_namespace" {
  description = "Namespace for the OpenTelemetry Collector and Tempo."
  type        = string
  default     = "observability"
}

variable "chart_versions" {
  description = "Pinned Helm chart versions."
  type = object({
    kube_prometheus_stack   = string
    opentelemetry_collector = string
    tempo                   = string
    metrics_server          = string
  })
  default = {
    kube_prometheus_stack   = "92.10.1"
    opentelemetry_collector = "0.176.0"
    tempo                   = "1.24.4"
    metrics_server          = "3.14.0"
  }
}

variable "otel_collector_image_tag" {
  description = "Pinned otel/opentelemetry-collector-contrib image tag."
  type        = string
  default     = "0.162.0"
}

variable "install_metrics_server" {
  description = "Install metrics-server (needed by the HPA on kind; managed clusters often ship it)."
  type        = bool
  default     = true
}

variable "metrics_server_insecure_tls" {
  description = "Pass --kubelet-insecure-tls to metrics-server. Only for kind, whose kubelet certs are self-signed."
  type        = bool
  default     = false
}

variable "disable_control_plane_scrapes" {
  description = "Skip scraping etcd/scheduler/controller-manager/kube-proxy (not reachable on kind or managed control planes)."
  type        = bool
  default     = true
}

variable "prometheus_retention" {
  description = "Prometheus TSDB retention."
  type        = string
  default     = "2d"
}

variable "helm_timeout_seconds" {
  description = "Timeout for each Helm release to become ready."
  type        = number
  default     = 600
}
