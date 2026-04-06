import logging
import os
import sys
import time
from pathlib import Path
from typing import Optional

import mlflow
import pandas as pd
import torch
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response
from PIL import Image
from pydantic import BaseModel
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from torchvision import transforms


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MODEL_TYPE = os.getenv("MODEL_TYPE", "svm").strip().lower()
MODEL_NAME = "Text_Classifier_SVM" if MODEL_TYPE == "svm" else "CNN_Image_Classifier"
SERVICE_NAME = f"predict-{MODEL_TYPE}-api"
MLFLOW_URI = os.getenv("MLFLOW_TRACKING_URI", "https://dagshub.com/Fouxy84/mlops_projects.mlflow")

mlflow.set_tracking_uri(MLFLOW_URI)

REQUEST_COUNT = Counter(
    "mlops_inference_requests_total",
    "Total inference HTTP requests",
    ["model_type", "method", "path", "status"],
)
REQUEST_LATENCY = Histogram(
    "mlops_inference_request_duration_seconds",
    "Inference request latency",
    ["model_type", "method", "path"],
)
PREDICTION_COUNT = Counter(
    "mlops_predictions_total",
    "Total predictions returned by inference services",
    ["model_type"],
)
PREDICTION_LATENCY = Histogram(
    "mlops_prediction_duration_seconds",
    "Prediction latency by model",
    ["model_type"],
)

IN_DOCKER = Path("/app").exists()
BASE_DIR = Path("/app") if IN_DOCKER else Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))
DATA_PROCESSED_DIR = BASE_DIR / "data" / "processed"
IMAGE_ROOT_DIR = BASE_DIR / "data" / "raw" / "image_train"

try:
    df_labels = pd.read_csv(DATA_PROCESSED_DIR / "train_clean.csv")
    label_mapping = (
        df_labels[["label", "label_name"]]
        .drop_duplicates()
        .set_index("label")["label_name"]
    )
    LABEL_ID_TO_NAME = label_mapping.to_dict()
except Exception as exc:
    logger.warning("Falling back to synthetic labels: %s", exc)
    LABEL_ID_TO_NAME = {idx: f"Label_{idx}" for idx in range(8)}

DEVICE = torch.device("cpu")
IMAGE_SIZE = 128
IMAGE_TRANSFORM = transforms.Compose(
    [
        transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.5] * 3, std=[0.5] * 3),
    ]
)
model = None

app = FastAPI(
    title=f"MLOps Inference API - {MODEL_TYPE.upper()}",
    description="Single-model inference service for the MLOps platform",
)


class PredictTextRequest(BaseModel):
    text: str


class PredictImageRequest(BaseModel):
    image_path: str


class PredictResponse(BaseModel):
    predicted_label: int
    label_name: str
    decision_score: Optional[list[float]] = None


def load_model():
    model_uri = f"models:/{MODEL_NAME}/Production"
    loaded_model = mlflow.pyfunc.load_model(model_uri=model_uri)
    logger.info("Loaded %s from %s", MODEL_NAME, model_uri)
    return loaded_model


def build_prediction_response(predicted_label: int, decision_score: Optional[list[float]] = None):
    payload = {
        "predicted_label": int(predicted_label),
        "label_name": LABEL_ID_TO_NAME.get(int(predicted_label), "unknown"),
    }
    if decision_score is not None:
        payload["decision_score"] = decision_score
    return payload


def predict_text_payload(request: PredictTextRequest):
    if model is None:
        raise HTTPException(status_code=503, detail="Text model not loaded")

    started_at = time.perf_counter()
    try:
        features = pd.DataFrame({"text": [request.text]})
        prediction = model.predict(features)[0]
        decision_score = None
        if hasattr(model, "predict_proba"):
            decision_score = model.predict_proba(features)[0].tolist()
        PREDICTION_COUNT.labels(model_type=MODEL_TYPE).inc()
        return build_prediction_response(prediction, decision_score)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("SVM prediction failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        PREDICTION_LATENCY.labels(model_type=MODEL_TYPE).observe(time.perf_counter() - started_at)


def resolve_image_path(image_path: str) -> Path:
    path = Path(image_path)
    if path.is_absolute():
        return path
    return IMAGE_ROOT_DIR / path.name


def predict_image_payload(request: PredictImageRequest):
    if model is None:
        raise HTTPException(status_code=503, detail="Image model not loaded")

    started_at = time.perf_counter()
    try:
        image_path = resolve_image_path(request.image_path)
        if not image_path.exists():
            raise HTTPException(status_code=404, detail=f"Image not found: {image_path}")

        image = Image.open(image_path).convert("RGB")
        tensor = IMAGE_TRANSFORM(image).unsqueeze(0)
        features = pd.DataFrame({"image": [tensor.numpy().tolist()]})
        prediction = model.predict(features)[0]
        PREDICTION_COUNT.labels(model_type=MODEL_TYPE).inc()
        return build_prediction_response(prediction)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("CNN prediction failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        PREDICTION_LATENCY.labels(model_type=MODEL_TYPE).observe(time.perf_counter() - started_at)


@app.middleware("http")
async def prometheus_middleware(request: Request, call_next):
    started_at = time.perf_counter()
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    finally:
        REQUEST_COUNT.labels(
            model_type=MODEL_TYPE,
            method=request.method,
            path=request.url.path,
            status=str(status_code),
        ).inc()
        REQUEST_LATENCY.labels(
            model_type=MODEL_TYPE,
            method=request.method,
            path=request.url.path,
        ).observe(time.perf_counter() - started_at)


@app.get("/health")
def health():
    return {"status": "ok", "service": SERVICE_NAME, "model_type": MODEL_TYPE}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/predict", response_model=PredictResponse)
def predict_default(request: PredictTextRequest | PredictImageRequest):
    if MODEL_TYPE == "svm":
        if not isinstance(request, PredictTextRequest):
            raise HTTPException(status_code=422, detail="Text payload expected")
        return predict_text_payload(request)

    if not isinstance(request, PredictImageRequest):
        raise HTTPException(status_code=422, detail="Image payload expected")
    return predict_image_payload(request)


@app.post("/predict/svm", response_model=PredictResponse)
def predict_svm(request: PredictTextRequest):
    if MODEL_TYPE != "svm":
        raise HTTPException(status_code=404, detail="SVM endpoint not available on this service")
    return predict_text_payload(request)


@app.post("/predict/cnn", response_model=PredictResponse)
def predict_cnn(request: PredictImageRequest):
    if MODEL_TYPE != "cnn":
        raise HTTPException(status_code=404, detail="CNN endpoint not available on this service")
    return predict_image_payload(request)


@app.post("/reload")
def reload_model():
    global model
    try:
        model = load_model()
        return {"status": "model_reloaded", "model_type": MODEL_TYPE}
    except Exception as exc:
        logger.exception("Reload failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/reload/text")
def reload_text():
    if MODEL_TYPE != "svm":
        raise HTTPException(status_code=404, detail="Text reload endpoint not available on this service")
    return reload_model()


@app.post("/reload/image")
def reload_image():
    if MODEL_TYPE != "cnn":
        raise HTTPException(status_code=404, detail="Image reload endpoint not available on this service")
    return reload_model()


@app.get("/info")
def info():
    return {
        "model": MODEL_NAME,
        "model_type": MODEL_TYPE,
        "source": "MLflow",
        "tracking_uri": MLFLOW_URI,
    }


@app.get("/info/text")
def info_text():
    if MODEL_TYPE != "svm":
        raise HTTPException(status_code=404, detail="Text info endpoint not available on this service")
    return info()


@app.get("/info/image")
def info_image():
    if MODEL_TYPE != "cnn":
        raise HTTPException(status_code=404, detail="Image info endpoint not available on this service")
    return info()


@app.on_event("startup")
def startup():
    global model
    try:
        model = load_model()
    except Exception as exc:
        logger.warning("Model failed to load at startup: %s", exc)
        model = None
