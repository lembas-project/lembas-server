SHELL := /bin/bash -o pipefail -o errexit

# The port on which to run Tilt
TILT_PORT := 10350

# The path of the k3d config file
K3D_CONFIG_FILE := infra/k3d/k3d_config.yaml

# The namespace in which to deploy the resources
NAMESPACE := lembas

# Marker files
MARKER_DIR := .mark
CLUSTER_UP_MARKER := $(MARKER_DIR)/cluster-up

help:  ## Display help for the Makefile targets
	@@grep -h '^[a-zA-Z]' $(MAKEFILE_LIST) | awk -F ':.*?## ' 'NF==2 {printf "   %-20s%s\n", $$1, $$2}' | sort

$(MARKER_DIR):
	mkdir -p $@

# Spin up the cluster and create a marker file
$(CLUSTER_UP_MARKER): $(MARKER_DIR)
	./infra/scripts/create-cluster.sh
	touch $@

cluster: $(CLUSTER_UP_MARKER)  ## Create a new Kubernetes cluster using k3d

destroy:  ## Tear down the k3d Kubernetes cluster
	k3d cluster delete --config $(K3D_CONFIG_FILE)
	rm -f $(CLUSTER_UP_MARKER)

scale-cluster:  ## Scale the cluster to a number of nodes (e.g. `make scale-cluster replicas=2`)
	k3d node create new-agent --config $(K3D_CONFIG_FILE) --role agent --replicas $(replicas)

install-hooks:  ## Download + install all pre-commit hooks
	pre-commit install-hooks

pre-commit:  ## Run pre-commit on all files
	pre-commit run --all-files

# A list of all resources to start when running Tilt.
RESOURCES ?=

up: cluster  ## Run Tilt, deploying all its managed components
	tilt up $(RESOURCES) --namespace $(NAMESPACE) --port $(TILT_PORT)

down:  ## Remove Tilt managed resources
	tilt down --namespace $(NAMESPACE) --delete-namespaces

ci: cluster  ## Run Tilt in CI mode
	tilt ci $(RESOURCES) --namespace $(NAMESPACE) --port $(TILT_PORT)

.PHONY: $(MAKECMDGOALS)
