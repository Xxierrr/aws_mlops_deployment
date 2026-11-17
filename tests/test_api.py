from unittest.mock import Mock

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from mlflow import MlflowClient
from mlflow.exceptions import MlflowException
from sklearn.linear_model import LogisticRegression

import main as api
from create_model import FEATURES, MODEL_NAME, build_pipeline, get_champion


@pytest.fixture
def customer():
    return {
        "gender": "Female", "SeniorCitizen": 0, "Partner": "Yes",
        "Dependents": "No", "tenure": 12, "PhoneService": "Yes",
        "MultipleLines": "No", "InternetService": "Fiber optic",
        "OnlineSecurity": "No", "OnlineBackup": "Yes",
        "DeviceProtection": "No", "TechSupport": "No",
        "StreamingTV": "Yes", "StreamingMovies": "No",
        "Contract": "Month-to-month", "PaperlessBilling": "Yes",
        "PaymentMethod": "Electronic check", "MonthlyCharges": 85.5,
        "TotalCharges": 1026.0,
    }


@pytest.fixture
def tiny_model(customer):
    records = []
    for index in range(16):
        row = customer.copy()
        row.update({
            "tenure": index * 4, "SeniorCitizen": index % 2,
            "MonthlyCharges": 25.0 + index * 5,
            "TotalCharges": np.nan if index == 0 else float(index * 200),
            "Contract": "Month-to-month" if index % 2 else "Two year",
        })
        records.append(row)
    model = build_pipeline(LogisticRegression(class_weight="balanced", random_state=42))
    model.fit(pd.DataFrame(records)[FEATURES], np.array([index % 2 for index in range(16)]))
    return model


@pytest.fixture
def client(monkeypatch, tiny_model):
    # Lifespan is exercised, but registry/network/dataset access is impossible.
    monkeypatch.setattr(api, "load_champion", lambda: (tiny_model, "test-1"))
    with TestClient(api.app) as test_client:
        yield test_client


def test_valid_prediction(client, customer):
    response = client.post("/predict", json=customer)
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"prediction", "label", "churn_probability", "model_version"}
    assert type(body["prediction"]) is int
    assert body["prediction"] in (0, 1)
    assert isinstance(body["churn_probability"], float)
    assert 0 <= body["churn_probability"] <= 1
    assert body["prediction"] == int(body["churn_probability"] >= 0.5)
    assert body["label"] == ("Churn" if body["prediction"] else "No Churn")
    assert body["model_version"] == "test-1"


def test_missing_field(client, customer):
    del customer["TotalCharges"]
    response = client.post("/predict", json=customer)
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "TotalCharges"]


@pytest.mark.parametrize("field,value", [
    ("tenure", "twelve"), ("tenure", "12"), ("tenure", -1), ("tenure", 101),
    ("Contract", "Weekly"), ("SeniorCitizen", 2), ("SeniorCitizen", True),
    ("MonthlyCharges", -0.1), ("MonthlyCharges", 201.0), ("TotalCharges", -1.0),
    ("TotalCharges", None), ("customerID", "not-a-feature"),
])
def test_invalid_input(client, customer, field, value):
    customer[field] = value
    response = client.post("/predict", json=customer)
    assert response.status_code == 422
    assert any(error["loc"] == ["body", field] for error in response.json()["detail"])


def test_service_absence_categories(client, customer):
    customer.update({
        "PhoneService": "No", "MultipleLines": "No phone service", "InternetService": "No",
    })
    for field in (
        "OnlineSecurity", "OnlineBackup", "DeviceProtection",
        "TechSupport", "StreamingTV", "StreamingMovies",
    ):
        customer[field] = "No internet service"
    assert client.post("/predict", json=customer).status_code == 200


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok", "model_name": "telco-churn-model", "model_version": "test-1",
    }


def test_unavailable_model(monkeypatch, customer):
    def fail_loader():
        raise RuntimeError("Synthetic registry outage")

    monkeypatch.setattr(api, "load_champion", fail_loader)
    with TestClient(api.app) as client:
        for response in (client.get("/health"), client.post("/predict", json=customer)):
            assert response.status_code == 503
            assert response.json() == {"detail": "Model is not loaded"}


def test_feature_schema():
    assert len(api.Customer.model_fields) == 19
    assert set(api.Customer.model_fields) == set(FEATURES)


def test_registry_champion_lookup(tmp_path):
    uri = f"sqlite:///{(tmp_path / 'registry.db').as_posix()}"
    client = MlflowClient(tracking_uri=uri, registry_uri=uri)
    assert get_champion(client) is None
    client.create_registered_model(MODEL_NAME)
    assert get_champion(client) is None
    version = client.create_model_version(MODEL_NAME, source=tmp_path.as_uri())
    client.set_registered_model_alias(MODEL_NAME, "champion", version.version)
    assert get_champion(client).version == version.version


def test_registry_errors_are_not_absence():
    client = Mock()
    client.get_registered_model.side_effect = MlflowException("Registry unavailable")
    with pytest.raises(MlflowException, match="Registry unavailable"):
        get_champion(client)
