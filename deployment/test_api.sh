#!/bin/bash
# API Testing Script

set -e

# Configuration
API_URL="${1:-http://localhost:8000}"

echo "Testing API at: ${API_URL}"
echo ""

# Test health endpoint
echo "==> Testing /health endpoint..."
curl -s -f "${API_URL}/health" | python3 -m json.tool
echo ""

# Test prediction endpoint
echo "==> Testing /predict endpoint..."
curl -s -X POST "${API_URL}/predict" \
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
  }' | python3 -m json.tool

echo ""
echo "==> API tests passed!"
