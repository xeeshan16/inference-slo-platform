output "namespace" {
  description = "Namespace of the inference service."
  value       = kubernetes_namespace_v1.app.metadata[0].name
}

output "service_url" {
  description = "In-cluster URL of the inference service."
  value       = "http://inference-service.${kubernetes_namespace_v1.app.metadata[0].name}.svc.cluster.local:8080"
}

output "image" {
  description = "Deployed image reference."
  value       = local.image
}
