#!/bin/bash
# Simple deployment script for the novel generation system
# This script builds Docker images, pushes them to a registry, and deploys to Kubernetes.

set -e  # Exit on any error

# Configuration (customize for your environment)
REGISTRY="your-registry/novel"
TAG="latest"
NAMESPACE="novel-system"
INGRESS_HOST="novel.example.com"

# Ensure namespace exists
kubectl create namespace ${NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -

# Build and push backend image
echo "Building backend image..."
docker build -t ${REGISTRY}-backend:${TAG} ./src/backend
docker push ${REGISTRY}-backend:${TAG}

# Build and push frontend image
echo "Building frontend image..."
docker build -t ${REGISTRY}-frontend:${TAG} ./streamlit_app
docker push ${REGISTRY}-frontend:${TAG}

# Deploy backend
echo "Deploying backend..."
kubectl set image deployment/novel-backend -n ${NAMESPACE} novel-backend=${REGISTRY}-backend:${TAG}
kubectl rollout status deployment/novel-backend -n ${NAMESPACE}

# Deploy frontend
echo "Deploying frontend..."
kubectl set image deployment/novel-frontend -n ${NAMESPACE} novel-frontend=${REGISTRY}-frontend:${TAG}
kubectl rollout status deployment/novel-frontend -n ${NAMESPACE}

# Apply ingress if not exists
if ! kubectl get ingress novel-ingress -n ${NAMESPACE} > /dev/null 2>&1; then
    echo "Creating ingress..."
    kubectl apply -f k8s/ingress.yaml -n ${NAMESPACE}
fi

# Patch ingress with host
kubectl patch ingress novel-ingress -n ${NAMESPACE} -p "{\"spec\":{\"rules\":[{\"host\":\"${INGRESS_HOST}\",\"http\":{\"paths\":[{\"path\":\"/\",\"pathType\":\"Prefix\",\"backend\":{\"service\":{\"name\":\"novel-frontend-svc\",\"port\":{\"number\":80}}}}]}}]}" --type=merge

echo "Deployment completed successfully!"