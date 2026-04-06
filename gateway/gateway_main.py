import os
import time
import json
from pathlib import Path

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import Response
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest


DEFAULT_PREDICT_API_URL = os.getenv("PREDICT_API_URL", "http://predict-text-api:8000")
PREDICT_TEXT_API_URL = os.getenv("PREDICT_TEXT_API_URL", DEFAULT_PREDICT_API_URL)
PREDICT_IMAGE_API_URL = os.getenv("PREDICT_IMAGE_API_URL", "http://predict-image-api:8000")
TRAIN_API_URL = os.getenv("TRAIN_API_URL", "http://training-api:8002")
AUTH_API_URL = os.getenv("AUTH_API_URL", "http://auth-api:8003")
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.getenv("GATEWAY_DATA_DIR", BASE_DIR / "data"))
RAW_DATA_DIR = DATA_DIR / "raw"
RAW_IMAGE_DIR = RAW_DATA_DIR / "image_train"
STATE_FILE = DATA_DIR / ".gateway_retrain_state.json"
TEXT_EXTENSIONS = {".csv"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

REQUEST_COUNT = Counter(
    "mlops_gateway_requests_total",
    "Total HTTP requests handled by the gateway",
    ["method", "path", "status"],
)
REQUEST_LATENCY = Histogram(
    "mlops_gateway_request_duration_seconds",
    "Gateway request latency in seconds",
    ["method", "path"],
)
UPSTREAM_CALLS = Counter(
    "mlops_gateway_upstream_calls_total",
    "Total upstream calls performed by the gateway",
    ["target", "status"],
)

app = FastAPI(
    title="MLOps API Gateway",
    description="Gateway routing auth, training and per-model inference services",
    version="4.0.0",
)


class PredictTextRequest(BaseModel):
    text: str


class PredictImageRequest(BaseModel):
    image_path: str


def list_text_csv_files() -> list[str]:
    if not RAW_DATA_DIR.exists():
        return []
    return sorted(
        str(path.relative_to(DATA_DIR)).replace("\\", "/")
        for path in RAW_DATA_DIR.iterdir()
        if path.is_file() and path.suffix.lower() in TEXT_EXTENSIONS
    )


def list_image_files() -> list[str]:
    if not RAW_IMAGE_DIR.exists():
        return []
    return sorted(
        str(path.relative_to(DATA_DIR)).replace("\\", "/")
        for path in RAW_IMAGE_DIR.rglob("*")
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    )


def load_retrain_state() -> dict:
    if not STATE_FILE.exists():
        return {"text_files": [], "image_files": []}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"text_files": [], "image_files": []}


def save_retrain_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def compute_data_changes() -> dict:
    current_text_files = list_text_csv_files()
    current_image_files = list_image_files()
    previous_state = load_retrain_state()

    previous_text = set(previous_state.get("text_files", []))
    previous_images = set(previous_state.get("image_files", []))
    current_text = set(current_text_files)
    current_images = set(current_image_files)

    new_text_files = sorted(current_text - previous_text)
    new_image_files = sorted(current_images - previous_images)

    return {
        "text": {
            "directory": str(RAW_DATA_DIR),
            "current_files": current_text_files,
            "new_files": new_text_files,
            "has_new_files": bool(new_text_files),
        },
        "image": {
            "directory": str(RAW_IMAGE_DIR),
            "current_files": current_image_files,
            "new_files": new_image_files,
            "has_new_files": bool(new_image_files),
        },
        "state_file": str(STATE_FILE),
    }


async def trigger_retraining_for_changes(authorization: str, changes: dict) -> dict:
    triggered_models = []

    if changes["text"]["has_new_files"]:
        await proxy_request("POST", f"{TRAIN_API_URL}/train/svm", authorization=authorization)
        triggered_models.append("svm")

    if changes["image"]["has_new_files"]:
        await proxy_request("POST", f"{TRAIN_API_URL}/train/cnn", authorization=authorization)
        triggered_models.append("cnn")

    current_state = {
        "text_files": changes["text"]["current_files"],
        "image_files": changes["image"]["current_files"],
    }
    save_retrain_state(current_state)

    return {
        "status": "retraining_triggered" if triggered_models else "no_new_files",
        "triggered_models": triggered_models,
        "changes": changes,
    }


async def get_token(authorization: str = Header(default=None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    return authorization


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


async def proxy_request(
    method: str,
    url: str,
    authorization: str | None = None,
    json_body: dict | None = None,
    data_body: dict | None = None,
):
    headers = {}
    if authorization:
        headers["Authorization"] = authorization

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            if method.upper() == "GET":
                response = await client.get(url, headers=headers)
            elif method.upper() == "POST":
                response = await client.post(url, headers=headers, json=json_body, data=data_body)
            else:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=json_body,
                    data=data_body,
                )
        UPSTREAM_CALLS.labels(target=url, status=str(response.status_code)).inc()
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=exc.response.status_code,
            detail=exc.response.text or "Upstream service error",
        ) from exc
    except httpx.RequestError as exc:
        raise HTTPException(status_code=503, detail="Upstream service unavailable") from exc


@app.get("/health")
async def health():
    return {"status": "ok", "service": "gateway"}


@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    return await proxy_request(
        "POST",
        f"{AUTH_API_URL}/token",
        data_body={
            "username": form_data.username,
            "password": form_data.password,
        },
    )


@app.get("/me")
async def me(authorization: str = Depends(get_token)):
    return await proxy_request("GET", f"{AUTH_API_URL}/me", authorization=authorization)


@app.post("/predict/text")
async def predict_text(
    request: PredictTextRequest,
    authorization: str = Depends(get_token),
):
    return await proxy_request(
        "POST",
        f"{PREDICT_TEXT_API_URL}/predict",
        authorization=authorization,
        json_body=request.dict(),
    )


@app.post("/predict/svm")
async def predict_svm(
    request: PredictTextRequest,
    authorization: str = Depends(get_token),
):
    return await predict_text(request, authorization)


@app.post("/predict/image")
async def predict_image(
    request: PredictImageRequest,
    authorization: str = Depends(get_token),
):
    return await proxy_request(
        "POST",
        f"{PREDICT_IMAGE_API_URL}/predict",
        authorization=authorization,
        json_body=request.dict(),
    )


@app.post("/predict/cnn")
async def predict_cnn(
    request: PredictImageRequest,
    authorization: str = Depends(get_token),
):
    return await predict_image(request, authorization)


@app.post("/train/text")
async def train_text(authorization: str = Depends(get_token)):
    await proxy_request("POST", f"{TRAIN_API_URL}/train/svm", authorization=authorization)
    return {"status": "training_started", "model": "text"}


@app.post("/train/svm")
async def train_svm(authorization: str = Depends(get_token)):
    return await train_text(authorization)


@app.post("/train/image")
async def train_image(authorization: str = Depends(get_token)):
    await proxy_request("POST", f"{TRAIN_API_URL}/train/cnn", authorization=authorization)
    return {"status": "training_started", "model": "image"}


@app.post("/train/cnn")
async def train_cnn(authorization: str = Depends(get_token)):
    return await train_image(authorization)


@app.post("/reload/text")
async def reload_text_model(authorization: str = Depends(get_token)):
    return await proxy_request("POST", f"{PREDICT_TEXT_API_URL}/reload", authorization=authorization)


@app.post("/reload/svm")
async def reload_svm_model(authorization: str = Depends(get_token)):
    return await reload_text_model(authorization)


@app.post("/reload/image")
async def reload_image_model(authorization: str = Depends(get_token)):
    return await proxy_request("POST", f"{PREDICT_IMAGE_API_URL}/reload", authorization=authorization)


@app.post("/reload/cnn")
async def reload_cnn_model(authorization: str = Depends(get_token)):
    return await reload_image_model(authorization)


@app.get("/info")
async def get_info(authorization: str = Depends(get_token)):
    text_health = await proxy_request("GET", f"{PREDICT_TEXT_API_URL}/health", authorization=authorization)
    image_health = await proxy_request("GET", f"{PREDICT_IMAGE_API_URL}/health", authorization=authorization)
    text_info = await proxy_request("GET", f"{PREDICT_TEXT_API_URL}/info", authorization=authorization)
    image_info = await proxy_request("GET", f"{PREDICT_IMAGE_API_URL}/info", authorization=authorization)
    train_health = await proxy_request("GET", f"{TRAIN_API_URL}/health", authorization=authorization)

    return {
        "gateway": "ok",
        "prediction_apis": {
            "text": {"health": text_health, "info": text_info},
            "image": {"health": image_health, "info": image_info},
        },
        "training_api": train_health,
        "models": {
            "text_model": text_info,
            "image_model": image_info,
        },
    }


@app.get("/data/check-updates")
async def check_data_updates(authorization: str = Depends(get_token)):
    changes = compute_data_changes()
    return {
        "status": "scan_completed",
        "changes": changes,
    }


@app.post("/data/check-updates/retrain")
async def check_data_updates_and_retrain(authorization: str = Depends(get_token)):
    changes = compute_data_changes()
    return await trigger_retraining_for_changes(authorization, changes)


@app.post("/data/check-updates/baseline")
async def baseline_data_updates(authorization: str = Depends(get_token)):
    changes = compute_data_changes()
    save_retrain_state(
        {
            "text_files": changes["text"]["current_files"],
            "image_files": changes["image"]["current_files"],
        }
    )
    return {
        "status": "baseline_saved",
        "changes": changes,
    }


@app.get("/")
async def root():
    return {
        "message": "MLOps Gateway",
        "routes": {
            "auth": "/token",
            "predict": {
                "text": "/predict/text",
                "image": "/predict/image",
                "svm": "/predict/svm",
                "cnn": "/predict/cnn",
            },
            "train": {
                "text": "/train/text",
                "image": "/train/image",
                "svm": "/train/svm",
                "cnn": "/train/cnn",
            },
            "reload": {
                "text": "/reload/text",
                "image": "/reload/image",
            },
            "info": "/info",
            "data_updates": {
                "check": "/data/check-updates",
                "retrain": "/data/check-updates/retrain",
                "baseline": "/data/check-updates/baseline",
            },
            "metrics": "/metrics",
        },
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("gateway_main:app", host="0.0.0.0", port=8000, reload=False)
