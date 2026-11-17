#!/bin/bash
# MLflow Server Startup Script
# Replace placeholders before running!

set -e

# Configuration - REPLACE THESE VALUES
RDS_PASSWORD="YOUR_RDS_PASSWORD"
RDS_ENDPOINT="YOUR_RDS_ENDPOINT"  # e.g., mlops-postgres.abc123.ap-south-1.rds.amazonaws.com
BUCKET_NAME="YOUR_BUCKET_NAME"    # e.g., mlops-telco-churn-artifacts-xyz

# MLflow Configuration
export MLFLOW_BACKEND_URI="postgresql://mlopsadmin:${RDS_PASSWORD}@${RDS_ENDPOINT}:5432/mlflow?sslmode=require"
export MLFLOW_ARTIFACT_ROOT="s3://${BUCKET_NAME}/mlflow-artifacts"

echo "Starting MLflow server..."
echo "Backend: RDS PostgreSQL at ${RDS_ENDPOINT}"
echo "Artifacts: S3 bucket ${BUCKET_NAME}"

# Add Python user packages to PATH
export PATH="$HOME/.local/bin:$PATH"

# Start MLflow server
python3.11 -m mlflow server \
  --backend-store-uri "$MLFLOW_BACKEND_URI" \
  --artifacts-destination "$MLFLOW_ARTIFACT_ROOT" \
  --host 0.0.0.0 \
  --port 5000
