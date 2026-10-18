output "name" {
  description = "Cluster name."
  value       = kind_cluster.this.name
}

output "endpoint" {
  description = "Kubernetes API server endpoint."
  value       = kind_cluster.this.endpoint
}

output "client_certificate" {
  description = "Client certificate (PEM) for the cluster admin."
  value       = kind_cluster.this.client_certificate
}

output "client_key" {
  description = "Client key (PEM) for the cluster admin."
  value       = kind_cluster.this.client_key
  sensitive   = true
}

output "cluster_ca_certificate" {
  description = "Cluster CA certificate (PEM)."
  value       = kind_cluster.this.cluster_ca_certificate
}

output "kubeconfig_path" {
  description = "Path of the kubeconfig file written by the provider."
  value       = kind_cluster.this.kubeconfig_path
}
