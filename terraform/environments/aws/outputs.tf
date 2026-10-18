output "cluster_name" {
  description = "EKS cluster name (aws eks update-kubeconfig --name <this>)."
  value       = module.eks.cluster_name
}

output "inference_service_url" {
  description = "In-cluster URL of the inference service."
  value       = module.app.service_url
}
