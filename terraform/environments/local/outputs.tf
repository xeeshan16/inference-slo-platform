output "cluster_name" {
  description = "kind cluster name (use with `kind export kubeconfig --name`)."
  value       = module.cluster.name
}

output "kubeconfig_path" {
  description = "Kubeconfig written by the kind provider."
  value       = module.cluster.kubeconfig_path
}

output "inference_service_url" {
  description = "In-cluster URL of the inference service."
  value       = module.app.service_url
}

output "prometheus_service" {
  description = "kubectl port-forward -n monitoring svc/kps-prometheus 9090"
  value       = module.platform.prometheus_service
}

output "grafana_service" {
  description = "kubectl port-forward -n monitoring svc/grafana 3000:80"
  value       = module.platform.grafana_service
}

output "grafana_admin_password" {
  description = "Grafana admin password (terraform output -raw grafana_admin_password)."
  value       = module.platform.grafana_admin_password
  sensitive   = true
}
