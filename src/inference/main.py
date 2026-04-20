import logging
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import joblib
import mlflow
import pandas as pd
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response
from PIL import Image
from pydantic import BaseModel
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from torchvision import transforms

from src.inference.config import build_model_uri


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MODEL_TYPE = os.getenv("MODEL_TYPE", "svm").strip().lower()
DEFAULT_MODEL_NAME = "Text_Classifier_SVM" if MODEL_TYPE == "svm" else "CNN_Image_Classifier"
MODEL_NAME = os.getenv("MLFLOW_MODEL_NAME", DEFAULT_MODEL_NAME).strip()
SERVICE_NAME = f"predict-{MODEL_TYPE}-api"
MLFLOW_URI = os.getenv("MLFLOW_TRACKING_URI", "https://dagshub.com/Fouxy84/mlops_projects.mlflow")
TEXT_VECTORIZER_ARTIFACT_PATH = os.getenv(
    "MLFLOW_TEXT_VECTORIZER_ARTIFACT_PATH",
    "preprocessing/tfidf.joblib",
).strip()

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

IMAGE_SIZE = 128
IMAGE_TRANSFORM = transforms.Compose(
    [
        transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.5] * 3, std=[0.5] * 3),
    ]
)

model = None


@dataclass
class TextModelBundle:
    classifier: Any
    vectorizer: Any | None
    model_uri: str
    vectorizer_artifact_path: str | None = None

    def predict_label(self, text: str):
        if self.vectorizer is not None:
            features = self.vectorizer.transform([text])
            return self.classifier.predict(features)[0]

        try:
            return self.classifier.predict([text])[0]
        except Exception:
            return self.classifier.predict(pd.DataFrame({"text": [text]}))[0]

    def decision_score(self, text: str) -> Optional[list[float]]:
        if not hasattr(self.classifier, "decision_function"):
            return None
        if self.vectorizer is None:
            return None

        score = self.classifier.decision_function(self.vectorizer.transform([text]))[0]
        if hasattr(score, "tolist"):
            return score.tolist()
        return list(score)


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


def build_prediction_response(predicted_label: int, decision_score: Optional[list[float]] = None):
    payload = {
        "predicted_label": int(predicted_label),
        "label_name": LABEL_ID_TO_NAME.get(int(predicted_label), "unknown"),
    }
    if decision_score is not None:
        payload["decision_score"] = decision_score
    return payload


def get_model_uri() -> str:
    return build_model_uri(MODEL_NAME)


def get_model_run_id(model_uri: str) -> str | None:
    if model_uri.startswith("runs:/"):
        parts = model_uri.split("/")
        if len(parts) >= 2:
            return parts[1]

    try:
        model_info = mlflow.models.get_model_info(model_uri)
        return getattr(model_info, "run_id", None)
    except Exception as exc:
        logger.warning("Could not resolve MLflow run id for %s: %s", model_uri, exc)
        return None


def load_text_vectorizer(model_uri: str):
    if not TEXT_VECTORIZER_ARTIFACT_PATH:
        return None

    run_id = get_model_run_id(model_uri)
    if not run_id:
        logger.warning("No MLflow run id found for %s; text vectorizer not loaded", model_uri)
        return None

    try:
        vectorizer_path = mlflow.artifacts.download_artifacts(
            run_id=run_id,
            artifact_path=TEXT_VECTORIZER_ARTIFACT_PATH,
        )
        vectorizer = joblib.load(vectorizer_path)
        logger.info(
            "Loaded text vectorizer from MLflow run %s artifact %s",
            run_id,
            TEXT_VECTORIZER_ARTIFACT_PATH,
        )
        return vectorizer
    except Exception as exc:
        logger.warning(
            "Could not load text vectorizer artifact %s for %s: %s",
            TEXT_VECTORIZER_ARTIFACT_PATH,
            model_uri,
            exc,
        )
        return None


def load_text_model():
    model_uri = get_model_uri()
    try:
        classifier = mlflow.sklearn.load_model(model_uri=model_uri)
        vectorizer = load_text_vectorizer(model_uri)
        logger.info(
            "Loaded text classifier from MLflow: %s (vectorizer loaded: %s)",
            model_uri,
            vectorizer is not None,
        )
        return TextModelBundle(
            classifier=classifier,
            vectorizer=vectorizer,
            model_uri=model_uri,
            vectorizer_artifact_path=TEXT_VECTORIZER_ARTIFACT_PATH if vectorizer is not None else None,
        )
    except Exception as exc:
        logger.error("MLflow text model load failed from %s: %s", model_uri, exc)
        return None


def load_pyfunc_model():
    model_uri = get_model_uri()
    try:
        loaded_model = mlflow.pyfunc.load_model(model_uri=model_uri)
        logger.info("Loaded %s model from MLflow: %s", MODEL_TYPE, model_uri)
        return loaded_model
    except Exception as exc:
        logger.warning("MLflow %s model load failed from %s: %s", MODEL_TYPE, model_uri, exc)
        
        # Try to load local model as fallback
        if MODEL_TYPE == "cnn":
            try:
                import torch
                import torch.nn as nn
                
                local_model_path = BASE_DIR / "models" / "images" / "cnn.pt"
                if local_model_path.exists():
                    # Define the model architecture (same as in training)
                    class SimpleCNN(nn.Module):
                        def __init__(self, num_classes):
                            super().__init__()
                            self.features = nn.Sequential(
                                nn.Conv2d(3, 32, 3, padding=1),
                                nn.ReLU(),
                                nn.MaxPool2d(2),
                                nn.Conv2d(32, 64, 3, padding=1),
                                nn.ReLU(),
                                nn.MaxPool2d(2),
                                nn.Conv2d(64, 128, 3, padding=1),
                                nn.ReLU(),
                                nn.MaxPool2d(2),
                            )
                            self.classifier = nn.Sequential(
                                nn.Flatten(),
                                nn.Linear(128 * (IMAGE_SIZE // 8) * (IMAGE_SIZE // 8), 256),
                                nn.ReLU(),
                                nn.Dropout(0.5),
                                nn.Linear(256, num_classes),
                            )

                        def forward(self, x):
                            x = self.features(x)
                            return self.classifier(x)
                    
                    # Create model and load state dict
                    model = SimpleCNN(num_classes=8)
                    state_dict = torch.load(local_model_path, map_location=torch.device('cpu'))
                    model.load_state_dict(state_dict)
                    model.eval()
                    
                    logger.info("Loaded local CNN model from %s", local_model_path)
                    return model
                else:
                    logger.warning("Local CNN model not found at %s", local_model_path)
            except Exception as local_exc:
                logger.error("Failed to load local CNN model: %s", local_exc)
        
        return None


def load_model():
    if MODEL_TYPE == "svm":
        return load_text_model()
    return load_pyfunc_model()


def predict_text_payload(request: PredictTextRequest):
    if model is None:
        raise HTTPException(status_code=503, detail="Text model not loaded")

    started_at = time.perf_counter()
    try:
        if isinstance(model, TextModelBundle):
            prediction = model.predict_label(request.text)
            decision_score = model.decision_score(request.text)
        else:
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

        # Support both local torch fallback and MLflow pyfunc interfaces.
        import torch

        if isinstance(model, torch.nn.Module):
            with torch.no_grad():
                outputs = model(tensor)
                prediction = outputs.argmax(dim=1).item()
        else:
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
        if model is None:
            raise RuntimeError("Model could not be loaded")
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
    payload = {
        "model": MODEL_NAME,
        "model_type": MODEL_TYPE,
        "model_uri": get_model_uri(),
        "source": "mlflow",
        "tracking_uri": MLFLOW_URI,
    }
    if MODEL_TYPE == "svm":
        payload["text_vectorizer_artifact_path"] = TEXT_VECTORIZER_ARTIFACT_PATH or None
        payload["text_vectorizer_loaded"] = isinstance(model, TextModelBundle) and model.vectorizer is not None
    return payload


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
