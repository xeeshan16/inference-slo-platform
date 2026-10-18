variable "cluster_name" {
  description = "Name of the kind cluster."
  type        = string
  default     = "inference-slo"
}

variable "node_image" {
  description = "kindest/node image; null uses the kind provider's default."
  type        = string
  default     = null
}

variable "worker_count" {
  description = "Number of kind worker nodes."
  type        = number
  default     = 2
}

variable "image_tag" {
  description = "Tag of the locally built inference-service image (the Makefile passes the git SHA)."
  type        = string
}

variable "app_values_files" {
  description = "Extra Helm values files for the inference service (paths relative to this directory)."
  type        = list(string)
  default     = []
}
