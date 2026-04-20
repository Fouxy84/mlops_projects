import logging
import os
import time

import dagshub
import mlflow
from fastapi import BackgroundTasks, FastAPI, Request
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

from src.training.run_training_images import main_image
from src.training.run_training_text import main_texte


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Training Service")

if os.getenv("MLFLOW_TRACKING_USERNAME") and os.getenv("MLFLOW_TRACKING_PASSWORD"):
    try:
        dagshub.init(repo_owner="Fouxy84", repo_name="mlops_projects", mlflow=True)
    except Exception:
        logger.warning("dagshub.init() failed at startup, will retry at training time")

mlflow.set_tracking_uri(
    os.getenv("MLFLOW_TRACKING_URI", "https://dagshub.com/Fouxy84/mlops_projects.mlflow")
)

REQUEST_COUNT = Counter(
    "mlops_training_requests_total",
    "Total requests handled by the training API",
    ["method", "path", "status"],
)
REQUEST_LATENCY = Histogram(
    "mlops_training_request_duration_seconds",
    "Training API request latency",
    ["method", "path"],
)
TRAINING_RUNS = Counter(
    "mlops_training_runs_total",
    "Total training jobs started",
    ["model_type"],
)


@app.middleware("http")
async def prometheus_middleware(request: Request, call_next):
    start_time = time.perf_counter()
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    finally:
        REQUEST_COUNT.labels(
            method=request.method,
            path=request.url.path,
            status=str(status_code),
        ).inc()
        REQUEST_LATENCY.labels(
            method=request.method,
            path=request.url.path,
        ).observe(time.perf_counter() - start_time)


@app.get("/health")
def health():
    return {"status": "ok", "service": "training-api"}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


def train_text_pipeline():
    main_texte()
    logger.info("Text model training completed successfully.")


def train_image_pipeline():
    main_image()
    logger.info("Image model training completed successfully.")


@app.post("/train/svm")
def train_svm(background_tasks: BackgroundTasks):
    TRAINING_RUNS.labels(model_type="svm").inc()
    background_tasks.add_task(train_text_pipeline)
    return {"status": "svm_training_started"}


@app.post("/train/cnn")
def train_cnn(background_tasks: BackgroundTasks):
    TRAINING_RUNS.labels(model_type="cnn").inc()
    background_tasks.add_task(train_image_pipeline)
    return {"status": "cnn_training_started"}


@app.post("/retrain/svm")
def retrain_svm(background_tasks: BackgroundTasks):
    """Full retrain: preprocessing raw data + SVM training."""
    TRAINING_RUNS.labels(model_type="retrain_svm").inc()
    background_tasks.add_task(main_texte)
    return {"status": "retrain_svm_started", "steps": ["preprocessing", "training"]}


@app.post("/retrain/cnn")
def retrain_cnn(background_tasks: BackgroundTasks):
    """Full retrain: preprocessing raw data + CNN training."""
    TRAINING_RUNS.labels(model_type="retrain_cnn").inc()
    background_tasks.add_task(main_image)
    return {"status": "retrain_cnn_started", "steps": ["preprocessing", "training"]}
