SHELL := /bin/bash -o pipefail -o errexit

# The port on which to run Tilt
TILT_PORT := 10350

# The namespace in which to deploy the resources
NAMESPACE := lembas

# Conda-related paths
CONDA_ENV_DIR := ./env
CONDA_ENV_FILE := environment.yml
CONDA_ENV_MARKER := $(CONDA_ENV_DIR)/.mark-environment-created

# Marker files
MARKER_DIR := .mark
CLUSTER_UP_MARKER := cluster-up

# Commands
CONDA_EXE ?= conda
conda_run := $(CONDA_EXE) run --live-stream --prefix $(CONDA_ENV_DIR)

help:  ## Display help for the Makefile targets
	@@grep -h '^[a-zA-Z]' $(MAKEFILE_LIST) | awk -F ':.*?## ' 'NF==2 {printf "   %-20s%s\n", $$1, $$2}' | sort

# Command to create or update a conda environment.
# Uses a marker file to only perform the action if the $(CONDA_ENV_FILE) is changed.
$(CONDA_ENV_MARKER): $(CONDA_ENV_FILE)
	$(CONDA_EXE) env \
		$(shell [ -d $(CONDA_ENV_DIR) ] && echo update || echo create) \
		--prefix $(CONDA_ENV_DIR) \
		--file $(CONDA_ENV_FILE)
	touch $(CONDA_ENV_MARKER)

$(MARKER_DIR):
	mkdir -p $@

# Spin up the cluster and create a marker file
$(MARKER_DIR)/$(CLUSTER_UP_MARKER): $(MARKER_DIR)
	./infra/scripts/create-cluster.sh
	touch $@

cluster-up: $(CLUSTER_UP_MARKER)  ## Create a new Kubernetes cluster using k3d

cluster-down:  ## Tear down the k3d Kubernetes cluster
	k3d cluster delete anaconda-one
	rm -f $(CLUSTER_UP_MARKER)

destroy: cluster-down  ## Alias for cluster-down

scale-cluster:  ## Scale the cluster to a number of nodes (e.g. `make scale-cluster replicas=2`)
	k3d node create new-agent --cluster anaconda-one --role agent --replicas $(replicas)

install-hooks:  ## Download + install all pre-commit hooks
	pre-commit install-hooks

pre-commit:  ## Run pre-commit on all files
	pre-commit run --all-files

# A list of all resources to start when running Tilt.
# This allows us to have a CI pipeline for testing where not all services are yet able to pass.
# TODO: We may want this to go away eventually, but putting in to allow testing while
# 		also allowing local manual development.
RESOURCES ?=

up: cluster-up  ## Run Tilt, deploying all its managed components
	tilt up $(RESOURCES) --namespace $(NAMESPACE) --port $(TILT_PORT)

down:  ## Remove Tilt managed resources
	tilt down --namespace $(NAMESPACE) --delete-namespaces

ci: cluster-up-ci init-submodules helm-dependencies  ## Run Tilt in CI mode
	tilt ci $(RESOURCES) --namespace $(NAMESPACE) --port $(TILT_PORT)

setup: $(CONDA_ENV_MARKER)  ## Create or update local conda environment for testing

test: setup  ## Run integration tests against the dev environment
	$(conda_run) pytest

.PHONY: $(MAKECMDGOALS)
