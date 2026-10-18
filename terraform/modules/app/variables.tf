variable "namespace" {
  description = "Namespace for the inference service."
  type        = string
  default     = "inference"
}

variable "loadtest_namespace" {
  description = "Namespace where k6 load-test Jobs run (allowed through the NetworkPolicy)."
  type        = string
  default     = "loadtest"
}

variable "monitoring_namespace" {
  description = "Namespace where Grafana's dashboard sidecar picks up the dashboard ConfigMap."
  type        = string
}

variable "otel_endpoint" {
  description = "OTLP/HTTP endpoint of the OpenTelemetry Collector."
  type        = string
}

variable "otel_namespace" {
  description = "Namespace of the OpenTelemetry Collector (NetworkPolicy egress)."
  type        = string
}

variable "chart_path" {
  description = "Path to the inference-service Helm chart."
  type        = string
}

variable "image_repository" {
  description = "Container image repository."
  type        = string
  default     = "inference-service"
}

variable "image_tag" {
  description = "Immutable image tag (CI uses the git SHA)."
  type        = string

  validation {
    condition     = var.image_tag != "latest" && length(var.image_tag) > 0
    error_message = "Use an immutable image tag, not 'latest'."
  }
}

variable "kind_cluster_name" {
  description = "If set, side-load the local image into this kind cluster before deploying."
  type        = string
  default     = null
}

variable "chart_values" {
  description = "Extra Helm values (YAML strings) merged after the module defaults, e.g. resource or HPA overrides."
  type        = list(string)
  default     = []
}
