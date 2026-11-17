#!/bin/bash
# Initial EC2 Setup Script
# Run this after first SSH connection to EC2

set -e

echo "==> Updating system packages..."
sudo dnf update -y

echo "==> Installing Docker..."
sudo dnf install -y docker git
sudo systemctl enable --now docker
sudo usermod -aG docker ec2-user

echo "==> Installing Python 3.11 and pip..."
sudo dnf install -y python3.11 python3.11-pip

echo "==> Installing PostgreSQL client..."
sudo dnf install -y nmap-ncat postgresql16

echo "==> Installing Python dependencies for MLflow..."
python3.11 -m pip install --user mlflow psycopg2-binary boto3

echo "==> Creating working directory..."
mkdir -p ~/mlops
cd ~/mlops

echo "==> Verifying IAM role..."
aws sts get-caller-identity

echo ""
echo "======================================"
echo "Setup complete!"
echo ""
echo "IMPORTANT: Exit and reconnect to apply Docker group membership:"
echo "  exit"
echo "  ssh -i mlops-key.pem ec2-user@YOUR_EC2_IP"
echo ""
echo "After reconnecting, verify Docker:"
echo "  docker run hello-world"
echo "======================================"
