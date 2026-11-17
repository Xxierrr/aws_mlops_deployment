#!/bin/bash
# FastAPI Application Update Script
# Pulls latest image from ECR and restarts container

set -e

# Configuration - REPLACE THESE VALUES
AWS_ACCOUNT_ID="YOUR_AWS_ACCOUNT_ID"
AWS_REGION="ap-south-1"
ECR_REPOSITORY="telco-churn-api"
CONTAINER_NAME="telco-api"
MLFLOW_URI="http://172.17.0.1:5000"

ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
IMAGE_URI="${ECR_REGISTRY}/${ECR_REPOSITORY}:latest"

echo "==> Authenticating with ECR..."
aws ecr get-login-password --region ${AWS_REGION} \
  | docker login --username AWS --password-stdin ${ECR_REGISTRY}

echo "==> Pulling latest image: ${IMAGE_URI}"
docker pull ${IMAGE_URI}

echo "==> Stopping existing container..."
docker stop ${CONTAINER_NAME} 2>/dev/null || echo "Container not running"
docker rm ${CONTAINER_NAME} 2>/dev/null || echo "Container not found"

echo "==> Starting new container..."
docker run -d \
  --name ${CONTAINER_NAME} \
  -p 8000:8000 \
  -e MLFLOW_TRACKING_URI="${MLFLOW_URI}" \
  --restart unless-stopped \
  ${IMAGE_URI}

echo "==> Waiting for container to start..."
sleep 5

echo "==> Container status:"
docker ps | grep ${CONTAINER_NAME}

echo "==> Health check:"
curl -f http://localhost:8000/health && echo "" || echo "Health check failed!"

echo "==> Update complete!"
