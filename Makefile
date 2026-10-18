# Local workflow. Requires: docker, kind, kubectl, terraform >= 1.9, python3, envsubst, jq.
SHELL        := /usr/bin/env bash
CLUSTER_NAME ?= inference-slo
IMAGE_TAG    ?= $(shell git rev-parse --short=12 HEAD 2>/dev/null || echo dev)
TF_DIR       := terraform/environments/local
TF_VARS      := -var cluster_name=$(CLUSTER_NAME) -var image_tag=$(IMAGE_TAG)
SCENARIO     ?= steady
RESULTS      ?= results/local

.PHONY: help up image apply kubeconfig load load-all down test lint grafana prometheus

help: ## Show targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk -F':.*?## ' '{printf "  %-12s %s\n", $$1, $$2}'

up: image apply kubeconfig ## Build the image, create the cluster and deploy everything
	scripts/smoke.sh
	scripts/wait_for_metrics.sh

image: ## Build the inference-service image
	docker build -t inference-service:$(IMAGE_TAG) service

apply: ## terraform apply (kind cluster + platform + app)
	terraform -chdir=$(TF_DIR) init -input=false
	terraform -chdir=$(TF_DIR) apply -auto-approve $(TF_VARS)

kubeconfig: ## Point kubectl at the kind cluster
	kind export kubeconfig --name $(CLUSTER_NAME)

load: ## Run one k6 scenario in-cluster: make load SCENARIO=steady|ramp|spike|rollout
	scripts/wait_for_baseline.sh
	scripts/loadtest.sh $(SCENARIO) $(RESULTS)

load-all: ## Run all scenarios and print the summary table
	for s in steady ramp spike rollout; do scripts/wait_for_baseline.sh; scripts/loadtest.sh $$s $(RESULTS); done
	python3 scripts/summarize_results.py $(RESULTS)

grafana: ## Port-forward Grafana to http://localhost:3000 (admin / terraform output)
	@echo "password: $$(terraform -chdir=$(TF_DIR) output -raw grafana_admin_password)"
	kubectl -n monitoring port-forward svc/grafana 3000:80

prometheus: ## Port-forward Prometheus to http://localhost:9090
	kubectl -n monitoring port-forward svc/kps-prometheus 9090:9090

down: ## Destroy everything
	terraform -chdir=$(TF_DIR) destroy -auto-approve $(TF_VARS)

test: ## Service unit tests and SLO rule tests
	cd service && pytest
	promtool test rules charts/inference-service/tests-promtool/slo-rules.test.yaml

lint: ## Linters and static checks
	cd service && ruff check . && ruff format --check . && mypy app training tests
	terraform fmt -check -recursive terraform
	helm lint --strict charts/inference-service
