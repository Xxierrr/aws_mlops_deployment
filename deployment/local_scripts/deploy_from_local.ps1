# PowerShell Script to Deploy from Local Machine to EC2
# Run this from your project root directory

param(
    [Parameter(Mandatory=$true)]
    [string]$EC2_IP,
    
    [Parameter(Mandatory=$true)]
    [string]$KEY_PATH = "mlops-key.pem"
)

$ErrorActionPreference = "Stop"

Write-Host "==> Deploying to EC2: $EC2_IP" -ForegroundColor Green

# Upload dataset
Write-Host "`n==> Uploading dataset..." -ForegroundColor Cyan
scp -i $KEY_PATH .\data\WA_Fn-UseC_-Telco-Customer-Churn.csv ec2-user@${EC2_IP}:~/mlops/telco_churn.csv

# Upload training script
Write-Host "`n==> Uploading training scripts..." -ForegroundColor Cyan
scp -i $KEY_PATH .\create_model.py ec2-user@${EC2_IP}:~/mlops/
scp -i $KEY_PATH .\requirements.txt ec2-user@${EC2_IP}:~/mlops/

# Upload deployment scripts
Write-Host "`n==> Uploading deployment scripts..." -ForegroundColor Cyan
scp -i $KEY_PATH .\deployment\ec2_scripts\*.sh ec2-user@${EC2_IP}:~/mlops/

Write-Host "`n==> Making scripts executable..." -ForegroundColor Cyan
ssh -i $KEY_PATH ec2-user@${EC2_IP} "chmod +x ~/mlops/*.sh"

Write-Host "`n======================================"  -ForegroundColor Green
Write-Host "Deployment files uploaded successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. SSH to EC2: ssh -i $KEY_PATH ec2-user@${EC2_IP}" -ForegroundColor White
Write-Host "2. Configure start_mlflow.sh with your RDS credentials" -ForegroundColor White
Write-Host "3. Start MLflow: ~/mlops/start_mlflow.sh" -ForegroundColor White
Write-Host "4. Train model: ~/mlops/train_model.sh" -ForegroundColor White
Write-Host "5. Deploy API: ~/mlops/update_api.sh" -ForegroundColor White
Write-Host "======================================" -ForegroundColor Green
