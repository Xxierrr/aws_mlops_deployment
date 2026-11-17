#!/bin/bash
# Model Training Script
# Trains model and registers it to MLflow

set -e

cd ~/mlops

# Configuration
export MLFLOW_TRACKING_URI="http://localhost:5000"
export DATA_PATH="telco_churn.csv"

echo "==> MLflow Tracking URI: ${MLFLOW_TRACKING_URI}"
echo "==> Dataset: ${DATA_PATH}"

if [ ! -f "${DATA_PATH}" ]; then
    echo "ERROR: Dataset not found at ${DATA_PATH}"
    echo "Upload it with: scp -i mlops-key.pem data/WA_Fn-UseC_-Telco-Customer-Churn.csv ec2-user@YOUR_IP:~/mlops/telco_churn.csv"
    exit 1
fi

if [ ! -f "create_model.py" ]; then
    echo "ERROR: create_model.py not found"
    echo "Upload it with: scp -i mlops-key.pem create_model.py ec2-user@YOUR_IP:~/mlops/"
    exit 1
fi

echo "==> Installing Python dependencies..."
python3.11 -m pip install --user -r requirements.txt

echo "==> Starting training..."
python3.11 create_model.py

echo ""
echo "======================================"
echo "Training complete!"
echo ""
echo "View results in MLflow UI:"
echo "  1. Open SSH tunnel: ssh -i mlops-key.pem -L 5000:localhost:5000 ec2-user@YOUR_IP"
echo "  2. Browse to: http://localhost:5000"
echo "======================================"
