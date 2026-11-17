# AWS Deployment Progress Tracker
**Project**: Telco Churn MLOps Deployment
**Date Started**: November 17, 2026
**Region**: Asia Pacific (Mumbai) - ap-south-1
**AWS Account ID**: 35582719126

---

## ✅ COMPLETED STEPS

### 1. S3 Bucket for MLflow Artifacts ✅
- **Bucket Name**: `mlops-telco-churn-artifacts-gpt123`
- **Region**: ap-south-1
- **Versioning**: Enabled
- **Public Access**: Blocked
- **Encryption**: SSE-S3
- **Purpose**: Store MLflow model artifacts and experiment files
- **Status**: ✅ Created and verified

### 2. RDS PostgreSQL Database ✅
- **Instance Identifier**: `mlops-postgres`
- **Engine**: PostgreSQL (latest version)
- **Instance Type**: db.t3.micro
- **Master Username**: `mlopsadmin`
- **Master Password**: ⚠️ SAVED SECURELY (not in this file)
- **Database Name**: `mlflow`
- **Port**: 5432
- **Public Access**: No
- **Security Group**: `mlops-rds-sg` (auto-created)
- **Storage**: 20 GiB gp3
- **Backup Retention**: 1 day
- **Purpose**: Store MLflow experiment metadata and model registry
- **Status**: ✅ Available
- **Endpoint**: `mlops-postgres.czey408qqsni.ap-south-1.rds.amazonaws.com`

### 3. IAM Policy for S3 Access ✅
- **Policy Name**: `MLOpsArtifactBucketAccess`
- **Type**: Customer managed
- **Purpose**: Grant EC2 instance permissions to read/write S3 artifacts
- **Permissions**:
  - ListBucket, GetBucketLocation on bucket
  - GetObject, PutObject, DeleteObject on objects
- **Resource ARN**: `arn:aws:s3:::mlops-telco-churn-artifacts-gpt123`
- **Status**: ✅ Created

### 4. IAM Role for EC2 ✅
- **Role Name**: `mlops-ec2-role`
- **Trusted Entity**: AWS Service - EC2
- **Attached Policies**:
  1. `AmazonEC2ContainerRegistryReadOnly` (AWS managed)
  2. `MLOpsArtifactBucketAccess` (Custom)
- **Purpose**: Allow EC2 to pull Docker images from ECR and access S3 artifacts
- **Status**: ✅ Created

---

### 5. Security Groups Configuration ✅
**a) mlops-ec2-sg (for EC2 instance)** ✅
- Security Group ID: sg-0d7c2273ef4409adc
- Inbound Rules:
  - SSH (22) from My IP ✅
  - Custom TCP (8000) from My IP ✅
- Outbound: All traffic ✅

**b) mlops-rds-sg (for RDS)** ✅
- Security Group ID: sg-05cd919a2f01be958
- Inbound Rules:
  - PostgreSQL (5432) from mlops-ec2-sg ✅
- Outbound: All traffic ✅

### 6. EC2 Instance Launch ✅
- **Instance ID**: i-0afc15b0bcce57492e
- **Name**: `mlops-server`
- **AMI**: Amazon Linux 2023 ✅
- **Instance Type**: t3.small ✅
- **IAM Role**: `mlops-ec2-role` ✅
- **Security Group**: `mlops-ec2-sg` ✅
- **Key Pair**: `mlops-key.pem` (downloaded) ✅
- **Storage**: 20 GiB gp3 ✅
- **Metadata hop limit**: 2 ✅
- **Public IPv4**: 13.204.46.214
- **Status**: Running ✅

### 7. Amazon ECR Repository ✅
- **Repository Name**: `telco-churn-api`
- **Visibility**: Private ✅
- **Tag Mutability**: Mutable ✅
- **Repository URI**: `355827191267.dkr.ecr.ap-south-1.amazonaws.com/telco-churn-api`
- **Status**: Created ✅

---

## ⏳ PENDING STEPS

### 8. GitHub Actions IAM Configuration
**a) mlops-ec2-sg (for EC2 instance)**
- Inbound Rules:
  - SSH (22) from My IP
  - Custom TCP (8000) from My IP (for FastAPI)
- Outbound: All traffic

**b) mlops-rds-sg (for RDS)**
- Inbound Rules:
  - PostgreSQL (5432) from mlops-ec2-sg only
- Remove any auto-created IP-based rules

### 6. EC2 Instance Launch
- **Name**: `mlops-server`
- **AMI**: Amazon Linux 2023
- **Instance Type**: t3.small
- **IAM Role**: `mlops-ec2-role`
- **Security Group**: `mlops-ec2-sg`
- **Key Pair**: Create `mlops-key.pem` (download and save)
- **Storage**: 20 GiB gp3
- **Advanced Settings**:
  - Metadata hop limit: 2 (critical for Docker containers)

### 7. Amazon ECR Repository
- **Repository Name**: `telco-churn-api`
- **Visibility**: Private
- **Tag Mutability**: Mutable
- **Scan on Push**: Enabled

### 8. GitHub Actions IAM Configuration
**a) OIDC Identity Provider**
- Provider URL: `https://token.actions.githubusercontent.com`
- Audience: `sts.amazonaws.com`

**b) ECR Push Policy**
- Name: `MLOpsECRPushPolicy`
- Permissions: ECR authentication and push operations

**c) GitHub Actions Role**
- Name: `github-actions-ecr-push-role`
- Trust policy: Restrict to your GitHub repo and main branch

### 9. GitHub Repository Configuration
Add these variables in Settings → Secrets and variables → Actions:
- `AWS_REGION`: ap-south-1
- `AWS_ROLE_ARN`: (ARN of github-actions-ecr-push-role)
- `ECR_REPOSITORY`: telco-churn-api

### 10. EC2 Setup and Configuration
- Connect via SSH
- Install Docker
- Install Python 3.11 and MLflow dependencies
- Verify IAM role, S3, and RDS connectivity
- Authenticate with ECR

### 11. MLflow Server Deployment
- Create startup script with RDS connection
- Start MLflow server on port 5000
- Set up systemd service (optional)

### 12. Model Training
- Upload dataset to EC2
- Upload create_model.py script
- Run training and register model

### 13. FastAPI Container Deployment
- Pull Docker image from ECR
- Run container on port 8000
- Configure to connect to MLflow server

### 14. Testing and Verification
- Test /health endpoint
- Test /predict endpoint
- Verify model loading from MLflow

---

## 📝 IMPORTANT INFORMATION TO SAVE

### Connection Details (to be filled after creation)
```bash
# S3 Bucket
BUCKET_NAME="mlops-telco-churn-artifacts-gpt123"

# RDS PostgreSQL
RDS_ENDPOINT="<to-be-filled-after-creation>"
RDS_PORT="5432"
RDS_USERNAME="mlopsadmin"
RDS_PASSWORD="<saved-securely>"
RDS_DATABASE="mlflow"

# EC2 Instance
EC2_PUBLIC_IP="<to-be-filled-after-launch>"
EC2_PRIVATE_IP="<to-be-filled-after-launch>"

# ECR Repository
ECR_REPOSITORY_URI="<to-be-filled-after-creation>"

# IAM Role ARNs
EC2_ROLE_ARN="arn:aws:iam::35582719126:role/mlops-ec2-role"
GITHUB_ROLE_ARN="<to-be-filled-after-creation>"
```

### MLflow Connection String (for EC2)
```bash
export MLFLOW_BACKEND_URI="postgresql://mlopsadmin:<PASSWORD>@<RDS_ENDPOINT>:5432/mlflow?sslmode=require"
export MLFLOW_ARTIFACT_ROOT="s3://mlops-telco-churn-artifacts-gpt123/mlflow-artifacts"
```

### Docker Run Command (for EC2)
```bash
docker run -d \
  --name telco-api \
  -p 8000:8000 \
  -e MLFLOW_TRACKING_URI="http://172.17.0.1:5000" \
  --restart unless-stopped \
  <ECR_REPOSITORY_URI>:latest
```

---

## 🚨 CRITICAL REMINDERS

1. ⚠️ **RDS Password**: Must be saved securely - cannot be recovered later
2. ⚠️ **EC2 Key Pair**: Download .pem file only once during creation - cannot be re-downloaded
3. ⚠️ **Initial Database Name**: Must be set to "mlflow" during RDS creation - cannot be changed later
4. ⚠️ **Security Groups**: Never allow 0.0.0.0/0 access to RDS (port 5432)
5. ⚠️ **Metadata Hop Limit**: Must be set to 2 on EC2 for Docker containers to access IAM role
6. ⚠️ **Cost Management**: Stop/delete resources when not in use to avoid charges

---

## 💰 ESTIMATED COSTS (Mumbai Region)

- **EC2 t3.small**: ~$0.0208/hour (~$15/month if running 24/7)
- **RDS db.t3.micro**: ~$0.018/hour (~$13/month)
- **EBS Storage (40 GiB total)**: ~$4/month
- **S3 Storage**: ~$0.025/GB/month (minimal for artifacts)
- **ECR Storage**: First 500MB free, then $0.10/GB/month
- **Public IPv4**: ~$3.60/month (if instance is running)

**Estimated Total**: ~$35-40/month if running continuously
**To Minimize Costs**: Stop EC2 and RDS when not actively using

---

## 🔗 USEFUL AWS CONSOLE LINKS

- **S3 Buckets**: https://s3.console.aws.amazon.com/s3/buckets?region=ap-south-1
- **RDS Databases**: https://ap-south-1.console.aws.amazon.com/rds/home?region=ap-south-1#databases:
- **EC2 Instances**: https://ap-south-1.console.aws.amazon.com/ec2/home?region=ap-south-1#Instances:
- **IAM Roles**: https://console.aws.amazon.com/iam/home#/roles
- **ECR Repositories**: https://ap-south-1.console.aws.amazon.com/ecr/repositories?region=ap-south-1

---

**Last Updated**: Step 4 completed - IAM role for EC2 created
**Next Step**: Wait for RDS to become available, then configure security groups
