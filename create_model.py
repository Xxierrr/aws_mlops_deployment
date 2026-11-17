"""Train, compare, and conditionally promote Telco churn pipelines."""

import hashlib
import os
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import mlflow
import mlflow.sklearn
import numpy as np
import pandas as pd
from mlflow import MlflowClient
from mlflow.exceptions import MlflowException
from mlflow.models import infer_signature
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    ConfusionMatrixDisplay,
    RocCurveDisplay,
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

MODEL_NAME = "telco-churn-model"
RANDOM_STATE = 42
TEST_SIZE = 0.2
SELECTION_METRIC = "roc_auc"
NUMERIC_FEATURES = ["SeniorCitizen", "tenure", "MonthlyCharges", "TotalCharges"]
CATEGORICAL_FEATURES = [
    "gender", "Partner", "Dependents", "PhoneService", "MultipleLines",
    "InternetService", "OnlineSecurity", "OnlineBackup", "DeviceProtection",
    "TechSupport", "StreamingTV", "StreamingMovies", "Contract",
    "PaperlessBilling", "PaymentMethod",
]
FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES


def build_pipeline(classifier):
    numeric = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
    ])
    categorical = Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("encoder", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
    ])
    # Dense output is small for this dataset and supports gradient boosting.
    preprocessing = ColumnTransformer([
        ("numeric", numeric, NUMERIC_FEATURES),
        ("categorical", categorical, CATEGORICAL_FEATURES),
    ])
    return Pipeline([("preprocessing", preprocessing), ("classifier", classifier)])


def read_dataset(path):
    frame = pd.read_csv(path, dtype={"TotalCharges": "string"})
    expected = set(FEATURES + ["customerID", "Churn"])
    if set(frame.columns) != expected:
        raise ValueError(f"Expected exactly these columns: {sorted(expected)}")
    if frame["Churn"].isna().any() or not frame["Churn"].isin(["Yes", "No"]).all():
        raise ValueError("Churn must contain only Yes and No, without missing values")
    frame["TotalCharges"] = pd.to_numeric(
        frame["TotalCharges"], errors="coerce"
    ).astype("float64")
    features = frame.drop(columns=["customerID", "Churn"])[FEATURES].copy()
    target = frame["Churn"].map({"No": 0, "Yes": 1}).astype("int64")
    return features, target


def positive_probability(model, features):
    index = list(model.classes_).index(1)
    return model.predict_proba(features)[:, index]


def evaluate(model, features, target):
    probability = positive_probability(model, features)
    prediction = (probability >= 0.5).astype(int)
    return {
        "accuracy": float(accuracy_score(target, prediction)),
        "precision": float(precision_score(target, prediction, zero_division=0)),
        "recall": float(recall_score(target, prediction, zero_division=0)),
        "f1": float(f1_score(target, prediction, zero_division=0)),
        "roc_auc": float(roc_auc_score(target, probability)),
    }, prediction, probability


def get_champion(client):
    try:
        registered = client.get_registered_model(MODEL_NAME)
    except MlflowException as exc:
        if exc.error_code == "RESOURCE_DOES_NOT_EXIST":
            return None
        # Authentication, database, and network failures must not mean "absent".
        raise
    # Inspect aliases explicitly: MLflow 3.5 reports a missing alias as
    # INVALID_PARAMETER_VALUE, which must not be broadly treated as absence.
    version = registered.aliases.get("champion")
    return client.get_model_version(MODEL_NAME, version) if version else None


def main():
    data_path = Path(os.getenv("DATA_PATH", "data/telco_churn.csv"))
    mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "sqlite:///mlflow.db"))
    mlflow.set_experiment("telco-churn")
    client = MlflowClient()
    features, target = read_dataset(data_path)
    x_train, x_test, y_train, y_test = train_test_split(
        features, target, test_size=TEST_SIZE,
        stratify=target, random_state=RANDOM_STATE,
    )
    data_hash = hashlib.sha256(data_path.read_bytes()).hexdigest()
    candidates = {
        "logistic_regression": LogisticRegression(
            class_weight="balanced", max_iter=2000, random_state=RANDOM_STATE,
        ),
        "gradient_boosting": GradientBoostingClassifier(
            n_estimators=150, learning_rate=0.05, max_depth=3,
            random_state=RANDOM_STATE,
        ),
    }
    results = []
    for name, classifier in candidates.items():
        with mlflow.start_run(run_name=name) as run:
            mlflow.set_tags({"dataset_sha256": data_hash, "selection_metric": SELECTION_METRIC})
            mlflow.log_params({
                "classifier": name, "random_state": RANDOM_STATE,
                "test_size": TEST_SIZE, "threshold": 0.5,
                "numeric_imputer": "median", "categorical_imputer": "most_frequent",
                "encoder_handle_unknown": "ignore", "numeric_scaler": "StandardScaler",
                **{f"classifier__{key}": value for key, value in classifier.get_params().items()},
            })
            pipeline = build_pipeline(classifier)
            pipeline.fit(x_train, y_train)
            metrics, prediction, probability = evaluate(pipeline, x_test, y_test)
            mlflow.log_metrics(metrics)
            for filename, display in (
                ("confusion_matrix.png", ConfusionMatrixDisplay.from_predictions(
                    y_test, prediction, labels=[0, 1], display_labels=["No Churn", "Churn"],
                )),
                ("roc_curve.png", RocCurveDisplay.from_predictions(y_test, probability)),
            ):
                mlflow.log_figure(display.figure_, filename)
                plt.close(display.figure_)
            # Float64 TotalCharges retains NaN; the pipeline handles imputation.
            example = x_train.head(5)
            info = mlflow.sklearn.log_model(
                sk_model=pipeline, name="model",
                signature=infer_signature(x_train, pipeline.predict(x_train)),
                input_example=example,
                pip_requirements=str(Path(__file__).with_name("requirements.txt")),
            )
            results.append({
                "name": name, "run_id": run.info.run_id,
                "model_uri": info.model_uri, "metrics": metrics,
            })

    best = max(results, key=lambda result: result["metrics"][SELECTION_METRIC])
    incumbent = get_champion(client)
    incumbent_score = None
    if incumbent is not None:
        incumbent_model = mlflow.sklearn.load_model(
            f"models:/{MODEL_NAME}/{incumbent.version}"
        )
        incumbent_score = float(roc_auc_score(
            y_test, positive_probability(incumbent_model, x_test)
        ))
        if not np.isfinite(incumbent_score):
            raise ValueError("Current champion has an invalid ROC-AUC; refusing promotion")
        client.log_metric(best["run_id"], "incumbent_roc_auc", incumbent_score)

    version = mlflow.register_model(best["model_uri"], MODEL_NAME, await_registration_for=300)
    if version.status != "READY":
        raise RuntimeError(f"Model registration is not ready: {version.status}")
    client.set_model_version_tag(MODEL_NAME, version.version, "selection_metric", SELECTION_METRIC)
    client.set_model_version_tag(MODEL_NAME, version.version, "dataset_sha256", data_hash)
    promoted = incumbent_score is None or best["metrics"][SELECTION_METRIC] > incumbent_score
    if promoted:
        # Detect most races; serialize trainers because alias writes are not CAS.
        latest = get_champion(client)
        if (latest.version if latest else None) != (incumbent.version if incumbent else None):
            raise RuntimeError("Champion changed during training; rerun with a single trainer")
        client.set_registered_model_alias(MODEL_NAME, "champion", version.version)

    print("\nTest metrics (threshold=0.5; selection=ROC-AUC):")
    rows = [{"model": item["name"], **item["metrics"]} for item in results]
    print(pd.DataFrame(rows).to_string(index=False))
    print(f"Dataset: {len(features)} rows, {len(features.columns)} features; churn={target.mean():.2%}")
    print(f"Registered: {MODEL_NAME} version {version.version}; best={best['name']}")
    if incumbent_score is not None:
        print(f"Previous champion ROC-AUC on this holdout: {incumbent_score:.6f}")
    active_version = version.version if promoted else incumbent.version
    print(f"Champion {'promoted' if promoted else 'unchanged'}: version {active_version}")


if __name__ == "__main__":
    main()
