# environments/aws (validated, not applied)

An EKS variant of `environments/local`: VPC + EKS (community modules) and the
same `platform` and `app` modules. CI runs `terraform init -backend=false` and
`terraform validate` on it. It has **not** been applied: doing so creates
billable resources (EKS control plane, NAT gateway, EC2 nodes).

Differences from the kind environment:

- metrics-server comes from the EKS add-on, so the platform module skips it.
- The image must be pushed to ECR (`image_repository`, `image_tag`).
- The NetworkPolicy is only enforced if the VPC CNI network policy agent is enabled.
