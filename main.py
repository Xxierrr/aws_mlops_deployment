"""Validated inference with a startup-pinned MLflow champion."""

import logging
import os
from contextlib import asynccontextmanager
from typing import Literal

import mlflow
import mlflow.sklearn
import pandas as pd
from fastapi import FastAPI, HTTPException, Request
from mlflow import MlflowClient
from pydantic import BaseModel, ConfigDict, Field

MODEL_NAME = "telco-churn-model"
logger = logging.getLogger(__name__)
YesNo = Literal["Yes", "No"]
InternetOption = Literal["Yes", "No", "No internet service"]


class Customer(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)

    gender: Literal["Female", "Male"]
    SeniorCitizen: int = Field(ge=0, le=1)
    Partner: YesNo
    Dependents: YesNo
    tenure: int = Field(ge=0, le=100)
    PhoneService: YesNo
    MultipleLines: Literal["Yes", "No", "No phone service"]
    InternetService: Literal["DSL", "Fiber optic", "No"]
    OnlineSecurity: InternetOption
    OnlineBackup: InternetOption
    DeviceProtection: InternetOption
    TechSupport: InternetOption
    StreamingTV: InternetOption
    StreamingMovies: InternetOption
    Contract: Literal["Month-to-month", "One year", "Two year"]
    PaperlessBilling: YesNo
    PaymentMethod: Literal[
        "Electronic check", "Mailed check",
        "Bank transfer (automatic)", "Credit card (automatic)",
    ]
    MonthlyCharges: float = Field(ge=0, le=200)
    TotalCharges: float = Field(ge=0)


class Prediction(BaseModel):
    prediction: Literal[0, 1]
    label: Literal["Churn", "No Churn"]
    churn_probability: float = Field(ge=0, le=1, allow_inf_nan=False)
    model_version: str


def load_champion():
    mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "sqlite:///mlflow.db"))
    version = MlflowClient().get_model_version_by_alias(MODEL_NAME, "champion")
    # Resolve models:/telco-churn-model@champion, then pin the version so
    # metadata and predictions cannot disagree if the alias changes mid-load.
    model = mlflow.sklearn.load_model(f"models:/{MODEL_NAME}/{version.version}")
    if list(model.classes_) != [0, 1]:
        raise ValueError("Champion must have binary classes [0, 1]")
    return model, str(version.version)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.model = None
    app.state.model_version = None
    try:
        app.state.model, app.state.model_version = load_champion()
    except Exception:
        logger.exception("Champion could not be loaded; endpoints will return 503")
    yield
    app.state.model = None
    app.state.model_version = None


app = FastAPI(title="Telco Churn API", version="1.0.0", lifespan=lifespan)


def require_model(request: Request):
    model = getattr(request.app.state, "model", None)
    version = getattr(request.app.state, "model_version", None)
    if model is None or version is None:
        raise HTTPException(status_code=503, detail="Model is not loaded")
    return model, version


@app.get("/health")
def health(request: Request):
    _, version = require_model(request)
    return {"status": "ok", "model_name": MODEL_NAME, "model_version": version}


@app.post("/predict", response_model=Prediction)
def predict(customer: Customer, request: Request):
    model, version = require_model(request)
    frame = pd.DataFrame([customer.model_dump()])
    probability = float(model.predict_proba(frame)[0, list(model.classes_).index(1)])
    prediction = int(probability >= 0.5)
    return Prediction(
        prediction=prediction,
        label="Churn" if prediction else "No Churn",
        churn_probability=probability,
        model_version=version,
    )
