# EKS variant of environments/local. It reuses the platform and app modules;
# only the cluster differs. This root is checked with `terraform validate` in CI
# but has never been applied (it would create billable AWS resources).

data "aws_availability_zones" "available" {
  state = "available"
}

locals {
  azs = slice(data.aws_availability_zones.available.names, 0, 3)
}

module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "6.7.3"

  name            = var.name
  cidr            = "10.0.0.0/16"
  azs             = local.azs
  private_subnets = ["10.0.0.0/19", "10.0.32.0/19", "10.0.64.0/19"]
  public_subnets  = ["10.0.96.0/22", "10.0.100.0/22", "10.0.104.0/22"]

  enable_nat_gateway = true
  single_nat_gateway = true

  public_subnet_tags  = { "kubernetes.io/role/elb" = 1 }
  private_subnet_tags = { "kubernetes.io/role/internal-elb" = 1 }
}

module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "21.29.0"

  name               = var.name
  kubernetes_version = var.kubernetes_version

  endpoint_public_access                   = true
  enable_cluster_creator_admin_permissions = true

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets

  addons = {
    coredns                = {}
    kube-proxy             = {}
    eks-pod-identity-agent = { before_compute = true }
    vpc-cni                = { before_compute = true }
    metrics-server         = {}
  }

  eks_managed_node_groups = {
    default = {
      ami_type       = "AL2023_x86_64_STANDARD"
      instance_types = var.node_instance_types
      min_size       = 2
      max_size       = 4
      desired_size   = 2
    }
  }
}

module "platform" {
  source = "../../modules/platform"

  # metrics-server comes from the EKS add-on above.
  install_metrics_server = false

  depends_on = [module.eks]
}

module "app" {
  source = "../../modules/app"

  chart_path           = "${path.module}/../../../charts/inference-service"
  image_repository     = var.image_repository
  image_tag            = var.image_tag
  monitoring_namespace = module.platform.monitoring_namespace
  otel_namespace       = module.platform.observability_namespace
  otel_endpoint        = module.platform.otel_collector_otlp_http_endpoint

  depends_on = [module.platform]
}
