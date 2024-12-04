#!/bin/bash

set -o errtrace -o nounset -o pipefail -o errexit

# renovate: datasource=github-releases depName=k3s-io/k3s
K3S_VERSION="v1.30.2+k3s1"

# Create k3d cluster
k3d cluster create \
    --image "rancher/k3s:${K3S_VERSION/+/-}" \
    --config infra/k3d/k3d_config.yaml

# Wait until the Traefik CRDs are installed. We need to do this before any
# services which depend on them are attempted to be installed.
# Wait max of 10 minutes, which really should never happen
printf "Waiting for Traefik CRDs to be installed into the cluster"
kubectl wait \
    -n kube-system \
    --for=condition=complete \
    --timeout=600s \
    job/helm-install-traefik-crd
