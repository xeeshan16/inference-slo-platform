terraform {
  required_version = ">= 1.9"

  required_providers {
    kind = {
      source  = "tehcyx/kind"
      version = "0.11.0"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "3.3.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "3.3.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.7"
    }
  }

  # Local state is fine for a throwaway kind cluster. For a shared environment
  # use a remote backend with locking, e.g.:
  #
  # backend "s3" {
  #   bucket       = "my-tfstate-bucket"
  #   key          = "inference-slo-platform/local/terraform.tfstate"
  #   region       = "eu-west-1"
  #   use_lockfile = true # S3-native state locking
  #   encrypt      = true
  # }
}
