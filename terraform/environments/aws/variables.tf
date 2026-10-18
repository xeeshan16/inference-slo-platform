variable "region" {
  description = "AWS region."
  type        = string
  default     = "eu-west-1"
}

variable "name" {
  description = "Name for the VPC and EKS cluster."
  type        = string
  default     = "inference-slo"
}

variable "kubernetes_version" {
  description = "EKS Kubernetes version."
  type        = string
  default     = "1.34"
}

variable "node_instance_types" {
  description = "Instance types for the managed node group."
  type        = list(string)
  default     = ["m6i.large"]
}

variable "image_repository" {
  description = "ECR repository URI of the inference-service image."
  type        = string
  default     = "123456789012.dkr.ecr.eu-west-1.amazonaws.com/inference-service"
}

variable "image_tag" {
  description = "Immutable image tag to deploy (e.g. the git SHA)."
  type        = string
  default     = "replace-me"
}
