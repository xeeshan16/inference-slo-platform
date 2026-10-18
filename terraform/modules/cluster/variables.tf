variable "name" {
  description = "Name of the kind cluster."
  type        = string
}

variable "node_image" {
  description = "kindest/node image (pin by tag and digest). null uses the provider's default image."
  type        = string
  default     = null
}

variable "worker_count" {
  description = "Number of worker nodes in addition to the control-plane node."
  type        = number
  default     = 2

  validation {
    condition     = var.worker_count >= 1 && var.worker_count <= 5
    error_message = "worker_count must be between 1 and 5."
  }
}
