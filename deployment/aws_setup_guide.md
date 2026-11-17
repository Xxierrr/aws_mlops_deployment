# AWS Deployment Guide for Telco Churn MLOps

## Current Status
✅ GitHub Actions workflow configured for ECR
✅ FastAPI application with MLflow integration
✅ Dockerfile ready

## Required AWS Resources

### 1. S3 Bucket Configuration
**Bucket Name**: `mlops-telco-churn-artifacts-<your-suffix>`
- Region: ap-south-1 (Mumbai)
- Block all public access: ✅
- Versioning: Enabled
- Encryption: SSE-S3

### 2. RDS PostgreSQL Configuration
**Instance ID**: `mlops-postgres`
- Engine: PostgreSQL (latest)
- Instance: db.t4g.micro (or db.t3.micro)
- Username: `mlopsadmin`
- Database name: `mlflow` (IMPORTANT!)
- Storage: 20 GiB gp3
- Public access: No
- Security group: `mlops-rds-sg`

### 3. EC2 Configuration
**Instance Name**: `mlops-server`
- AMI: Amazon Linux 2023
- Type: t3.small
- Key pair: `mlops-key` (create and download .pem)
- Security group: `mlops-ec2-sg`
- IAM role: `mlops-ec2-role`
- Metadata hop limit: 2

### 4. ECR Repository
**Repository**: `iris-ml-api` (or `telco-churn-api`)
- Visibility: Private
- Tag mutability: Mutable
- Scan on push: Enabled

### 5. GitHub Variables to Add
In your GitHub repo → Settings → Secrets and variables → Actions → Variables:

| Variable Name | Value |
|---------------|-------|
| AWS_REGION | ap-south-1 |
| AWS_ROLE_ARN | arn:aws:iam::YOUR_ACCOUNT_ID:role/github-actions-ecr-push-role |
| ECR_REPOSITORY | telco-churn-api |

## Step-by-Step Deployment

### Phase 1: AWS Infrastructure Setup (Manual via Console)

#### 1.1 Create S3 Bucket
```bash
# Note your bucket name for later
BUCKET_NAME="mlops-telco-churn-artifacts-xyz"
```

#### 1.2 Create RDS PostgreSQL
- Wait until status shows "Available"
- Copy the endpoint (e.g., `mlops-postgres.abc123.ap-south-1.rds.amazonaws.com`)
- Save master password securely

#### 1.3 Create IAM Policy for S3 Access
Policy name: `MLOpsArtifactBucketAccess`

See: `aws_iam_policies/s3_bucket_access.json`

#### 1.4 Create IAM Role for EC2
Role name: `mlops-ec2-role`
Attach policies:
- AmazonEC2ContainerRegistryReadOnly (AWS managed)
- MLOpsArtifactBucketAccess (custom)

#### 1.5 Create Security Groups

**mlops-ec2-sg** (for EC2):
- Inbound: SSH (22) from My IP
- Inbound: Custom TCP (8000) from My IP
- Outbound: All traffic

**mlops-rds-sg** (for RDS):
- Inbound: PostgreSQL (5432) from mlops-ec2-sg
- Remove any auto-created IP rules

#### 1.6 Launch EC2 Instance
- Select `mlops-ec2-role` as IAM instance profile
- Download `mlops-key.pem` and keep it secure

#### 1.7 Create ECR Repository
Repository name: `telco-churn-api`

#### 1.8 Create GitHub Actions IAM Role
Policy name: `MLOpsECRPushPolicy`
Role name: `github-actions-ecr-push-role`

See: `aws_iam_policies/ecr_push_policy.json` and `aws_iam_policies/github_trust_policy.json`

### Phase 2: EC2 Setup (via SSH)

#### 2.1 Connect to EC2
```powershell
# Windows PowerShell
cd $HOME\Downloads
ssh -i .\mlops-key.pem ec2-user@YOUR_EC2_PUBLIC_IP
```

#### 2.2 Verify IAM Role
```bash
aws sts get-caller-identity
# Should show mlops-ec2-role
```

#### 2.3 Test S3 Access
```bash
aws s3 ls s3://YOUR_BUCKET_NAME/
```

#### 2.4 Test RDS Connectivity
```bash
sudo dnf install -y nmap-ncat postgresql16

# Network test
nc -vz YOUR_RDS_ENDPOINT 5432

# Database test
psql "host=YOUR_RDS_ENDPOINT port=5432 dbname=mlflow user=mlopsadmin sslmode=require"
# Enter password when prompted
# Run: SELECT version();
# Exit: \q
```

#### 2.5 Install Docker
```bash
sudo dnf update -y
sudo dnf install -y docker git
sudo systemctl enable --now docker
sudo usermod -aG docker ec2-user
exit
```

Reconnect to apply group membership:
```powershell
ssh -i .\mlops-key.pem ec2-user@YOUR_EC2_PUBLIC_IP
```

Test Docker:
```bash
docker run hello-world
```

#### 2.6 Authenticate with ECR
```bash
aws ecr get-login-password --region ap-south-1 \
  | docker login --username AWS \
    --password-stdin YOUR_ACCOUNT_ID.dkr.ecr.ap-south-1.amazonaws.com
```

#### 2.7 Install Python and MLflow Dependencies
```bash
sudo dnf install -y python3.11 python3.11-pip
python3.11 -m pip install --user mlflow psycopg2-binary boto3
```

### Phase 3: Deploy MLflow Server

#### 3.1 Create MLflow Startup Script
```bash
mkdir -p ~/mlops
cd ~/mlops
```

Create `start_mlflow.sh`:
```bash
#!/bin/bash
export MLFLOW_BACKEND_URI="postgresql://mlopsadmin:YOUR_PASSWORD@YOUR_RDS_ENDPOINT:5432/mlflow?sslmode=require"
export MLFLOW_ARTIFACT_ROOT="s3://YOUR_BUCKET_NAME/mlflow-artifacts"

python3.11 -m mlflow server \
  --backend-store-uri "$MLFLOW_BACKEND_URI" \
  --artifacts-destination "$MLFLOW_ARTIFACT_ROOT" \
  --host 0.0.0.0 \
  --port 5000
```

Make it executable:
```bash
chmod +x start_mlflow.sh
```

#### 3.2 Create systemd Service (Optional but Recommended)
```bash
sudo tee /etc/systemd/system/mlflow.service > /dev/null <<'EOF'
[Unit]
Description=MLflow Tracking Server
After=network.target

[Service]
Type=simple
User=ec2-user
WorkingDirectory=/home/ec2-user/mlops
ExecStart=/home/ec2-user/mlops/start_mlflow.sh
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable mlflow
sudo systemctl start mlflow
sudo systemctl status mlflow
```

#### 3.3 Access MLflow UI (SSH Tunnel)
From your local machine:
```powershell
ssh -i .\mlops-key.pem -L 5000:localhost:5000 ec2-user@YOUR_EC2_PUBLIC_IP
```

Open browser: `http://localhost:5000`

### Phase 4: Train and Register Model

#### 4.1 Upload Dataset to EC2
From your local machine:
```powershell
scp -i .\mlops-key.pem .\data\WA_Fn-UseC_-Telco-Customer-Churn.csv ec2-user@YOUR_EC2_PUBLIC_IP:~/mlops/telco_churn.csv
```

#### 4.2 Upload Training Script
```powershell
scp -i .\mlops-key.pem .\create_model.py ec2-user@YOUR_EC2_PUBLIC_IP:~/mlops/
scp -i .\mlops-key.pem .\requirements.txt ec2-user@YOUR_EC2_PUBLIC_IP:~/mlops/
```

#### 4.3 Install Requirements and Train
On EC2:
```bash
cd ~/mlops
python3.11 -m pip install --user -r requirements.txt

export MLFLOW_TRACKING_URI="http://localhost:5000"
export DATA_PATH="telco_churn.csv"

python3.11 create_model.py
```

### Phase 5: Deploy FastAPI Application

#### 5.1 Pull Docker Image from ECR
```bash
docker pull YOUR_ACCOUNT_ID.dkr.ecr.ap-south-1.amazonaws.com/telco-churn-api:latest
```

#### 5.2 Run FastAPI Container
```bash
docker run -d \
  --name telco-api \
  -p 8000:8000 \
  -e MLFLOW_TRACKING_URI="http://172.17.0.1:5000" \
  --restart unless-stopped \
  YOUR_ACCOUNT_ID.dkr.ecr.ap-south-1.amazonaws.com/telco-churn-api:latest
```

**Note**: `172.17.0.1` is the Docker bridge gateway IP that allows the container to reach the host's MLflow server.

#### 5.3 Test the API
```bash
# Health check
curl http://localhost:8000/health

# Make prediction
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "gender": "Female",
    "SeniorCitizen": 0,
    "Partner": "Yes",
    "Dependents": "No",
    "tenure": 24,
    "PhoneService": "Yes",
    "MultipleLines": "No",
    "InternetService": "DSL",
    "OnlineSecurity": "Yes",
    "OnlineBackup": "Yes",
    "DeviceProtection": "No",
    "TechSupport": "Yes",
    "StreamingTV": "No",
    "StreamingMovies": "No",
    "Contract": "One year",
    "PaperlessBilling": "Yes",
    "PaymentMethod": "Electronic check",
    "MonthlyCharges": 65.5,
    "TotalCharges": 1572.0
  }'
```

From your local machine (if port 8000 is open in security group):
```powershell
curl http://YOUR_EC2_PUBLIC_IP:8000/health
```

### Phase 6: Automation Scripts

#### 6.1 Create Update Script
```bash
cat > ~/mlops/update_api.sh <<'EOF'
#!/bin/bash
set -e

# ECR login
aws ecr get-login-password --region ap-south-1 \
  | docker login --username AWS \
    --password-stdin YOUR_ACCOUNT_ID.dkr.ecr.ap-south-1.amazonaws.com

# Pull latest image
docker pull YOUR_ACCOUNT_ID.dkr.ecr.ap-south-1.amazonaws.com/telco-churn-api:latest

# Stop and remove old container
docker stop telco-api || true
docker rm telco-api || true

# Start new container
docker run -d \
  --name telco-api \
  -p 8000:8000 \
  -e MLFLOW_TRACKING_URI="http://172.17.0.1:5000" \
  --restart unless-stopped \
  YOUR_ACCOUNT_ID.dkr.ecr.ap-south-1.amazonaws.com/telco-churn-api:latest

echo "API updated successfully"
docker ps | grep telco-api
EOF

chmod +x ~/mlops/update_api.sh
```

## Verification Checklist

- [ ] S3 bucket created and accessible from EC2
- [ ] RDS PostgreSQL running and connectable from EC2
- [ ] EC2 instance running with Docker installed
- [ ] ECR repository created
- [ ] GitHub Actions workflow has AWS variables configured
- [ ] GitHub Actions can push to ECR (check Actions tab after push)
- [ ] MLflow server running on EC2:5000
- [ ] Model trained and registered in MLflow
- [ ] FastAPI container running on EC2:8000
- [ ] Health endpoint returns 200 OK
- [ ] Predict endpoint returns valid predictions

## Maintenance Commands

### Check MLflow Server
```bash
sudo systemctl status mlflow
sudo journalctl -u mlflow -f
```

### Check FastAPI Container
```bash
docker ps
docker logs telco-api
docker logs -f telco-api  # Follow logs
```

### Update Application
```bash
~/mlops/update_api.sh
```

### Retrain Model
```bash
cd ~/mlops
python3.11 create_model.py
```

## Troubleshooting

### MLflow can't connect to RDS
- Check security group rules
- Verify RDS endpoint and password
- Test with psql command

### FastAPI can't load model
- Check MLflow server is running
- Verify model is registered with "champion" alias
- Check Docker container logs

### Docker can't reach MLflow
- Use `172.17.0.1:5000` not `localhost:5000`
- Verify MLflow is listening on 0.0.0.0

### ECR authentication expires
```bash
aws ecr get-login-password --region ap-south-1 \
  | docker login --username AWS \
    --password-stdin YOUR_ACCOUNT_ID.dkr.ecr.ap-south-1.amazonaws.com
```

## Cost Management

### Stop Resources (Pausing)
```bash
# On EC2
docker stop telco-api
sudo systemctl stop mlflow
```

In AWS Console:
- EC2: Stop instance
- RDS: Actions → Stop temporarily (auto-restarts after 7 days)

### Full Cleanup (Delete Everything)
See `cleanup_guide.md`
