import base64
import json
import os
import time
from pathlib import Path

import httpx
from fastapi import Depends, FastAPI, Form, HTTPException, Request, status
from fastapi.responses import Response as FastAPIResponse
from pydantic import BaseModel, Field
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest


DEFAULT_PREDICT_API_URL = os.getenv("PREDICT_API_URL", "http://predict-text-api:8000")
PREDICT_TEXT_API_URL = os.getenv("PREDICT_TEXT_API_URL", DEFAULT_PREDICT_API_URL)
PREDICT_IMAGE_API_URL = os.getenv("PREDICT_IMAGE_API_URL", "http://predict-image-api:8000")
TRAIN_API_URL = os.getenv("TRAIN_API_URL", "http://training-api:8000")
API_TOKEN = os.getenv("API_TOKEN", "mlops-secret-token")
AIRFLOW_API_URL = os.getenv("AIRFLOW_API_URL", "http://airflow:8080")
AIRFLOW_USER = os.getenv("AIRFLOW_USER", "admin")
AIRFLOW_PASSWORD = os.getenv("AIRFLOW_PASSWORD", "admin")

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.getenv("GATEWAY_DATA_DIR", "/app/data" if Path("/app/data").exists() else BASE_DIR / "data"))
RAW_DATA_DIR = DATA_DIR / "raw"
RAW_IMAGE_DIR = RAW_DATA_DIR / "image_train"
STATE_FILE = DATA_DIR / ".gateway_retrain_state.json"
TEXT_EXTENSIONS = {".csv"}
IMAGE_EXTENSIONS = {".jpg"}

USERS = {
    "admin": {"username": "admin", "password": "admin", "role": "admin"},
    "user": {"username": "user", "password": "user", "role": "user"},
}
CURRENT_SESSION: dict | None = None

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
    description="Gateway with session-based access control for prediction, training and retraining",
    version="5.0.0",
)


class PredictTextRequest(BaseModel):
    text: str


class PredictImageRequest(BaseModel):
    image_path: str


class PredictMultimodalRequest(BaseModel):
    text: str
    image_path: str


_LABEL_NAMES = {
    0: "jeux vidéo",
    1: "livres / magazines",
    2: "jeux de société",
    3: "maquettes / drones",
    4: "mobilier",
    5: "déco maison",
    6: "fournitures",
    7: "jardin / piscine",
}
_LABELS_DOC = "  \n".join(f"- `{k}` → {v}" for k, v in _LABEL_NAMES.items())


class PredictResponse(BaseModel):
    predicted_label: int = Field(
        ...,
        description=f"Identifiant numérique du label prédit.\n\nValeurs possibles :\n{_LABELS_DOC}",
        examples=[0],
    )
    label_name: str = Field(
        ...,
        description="Nom lisible du label prédit.",
        examples=["jeux vidéo"],
    )
    decision_score: list[float] | None = Field(
        None,
        description="Scores de décision par classe (SVM uniquement).",
    )


class PredictMultimodalResponse(BaseModel):
    predicted_label: int = Field(
        ...,
        description=f"Identifiant numérique du label prédit.\n\nValeurs possibles :\n{_LABELS_DOC}",
        examples=[0],
    )
    label_name: str = Field(
        ...,
        description="Nom lisible du label prédit.",
        examples=["jeux vidéo"],
    )
    fusion_strategy: str = Field(
        ...,
        description="Stratégie de fusion utilisée : `agreement` (texte et image d'accord) ou `text_priority` (priorité au texte).",
        examples=["agreement"],
    )
    text_prediction: PredictResponse
    image_prediction: PredictResponse


def upstream_url(base_url: str, path: str) -> str:
    return f"{base_url.rstrip('/')}/{path.lstrip('/')}"


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

    return {
        "text": {
            "directory": str(RAW_DATA_DIR),
            "current_files": current_text_files,
            "new_files": sorted(current_text - previous_text),
            "has_new_files": bool(current_text - previous_text),
        },
        "image": {
            "directory": str(RAW_IMAGE_DIR),
            "current_files": current_image_files,
            "new_files": sorted(current_images - previous_images),
            "has_new_files": bool(current_images - previous_images),
        },
        "state_file": str(STATE_FILE),
    }


def authenticate(username: str, password: str) -> dict | None:
    user = USERS.get(username)
    if not user or user["password"] != password:
        return None
    return {"username": user["username"], "role": user["role"]}


def get_current_user(request: Request) -> dict:
    # Bearer token auth (Airflow / service-to-service)
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        if token and token == API_TOKEN:
            return {"username": "api-service", "role": "admin"}
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API token",
        )
    # Session-based auth
    if CURRENT_SESSION is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Login required",
        )
    return CURRENT_SESSION


def require_user(current_user: dict = Depends(get_current_user)) -> dict:
    if current_user["role"] not in {"user", "admin"}:
        raise HTTPException(status_code=403, detail="User access required")
    return current_user


def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


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


async def proxy_request(method: str, url: str, json_body: dict | None = None):
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            if method.upper() == "GET":
                response = await client.get(url)
            elif method.upper() == "POST":
                response = await client.post(url, json=json_body)
            else:
                response = await client.request(method=method, url=url, json=json_body)
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


async def trigger_retraining_for_changes(changes: dict) -> dict:
    triggered_models = []

    if changes["text"]["has_new_files"]:
        await proxy_request("POST", upstream_url(TRAIN_API_URL, "/train/svm"))
        triggered_models.append("svm")

    if changes["image"]["has_new_files"]:
        await proxy_request("POST", upstream_url(TRAIN_API_URL, "/train/cnn"))
        triggered_models.append("cnn")

    save_retrain_state(
        {
            "text_files": changes["text"]["current_files"],
            "image_files": changes["image"]["current_files"],
        }
    )

    return {
        "status": "retraining_triggered" if triggered_models else "no_new_files",
        "triggered_models": triggered_models,
        "changes": changes,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 1. INTRO — health, auth, system info
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/health")
async def health():
    return {"status": "ok", "service": "gateway"}


@app.get("/")
async def root():
    return {
        "service": "gateway",
        "docs": "/docs",
        "sections": {
            "intro": {
                "health": "/health",
                "metrics": "/metrics",
                "login": "/login",
                "me": "/me",
                "info": "/info",
                "logout": "/logout",
            },
            "prediction": {
                "svm": "/predict/svm",
                "cnn": "/predict/cnn",
                "multimodal": "/predict/multimodal",
            },
            "train_retrain": {
                "train_svm": "/orchestrate/train/svm",
                "train_cnn": "/orchestrate/train/cnn",
                "retrain_svm": "/orchestrate/retrain/svm",
                "retrain_cnn": "/orchestrate/retrain/cnn",
                "status": "/orchestrate/status/{dag_run_id}",
                "reload_svm": "/reload/svm",
                "reload_cnn": "/reload/cnn",
            },
            "check_update": {
                "scan": "/data/check-updates",
                "retrain": "/data/check-updates/retrain",
                "baseline": "/data/check-updates/baseline",
            },
        },
    }


@app.get("/metrics")
async def metrics():
    return FastAPIResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/login")
async def login(username: str = Form(...), password: str = Form(...)):
    global CURRENT_SESSION
    user = authenticate(username, password)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    CURRENT_SESSION = user
    return {
        "status": "logged_in",
        "username": user["username"],
        "role": user["role"],
        "message": "Session initialized in gateway memory",
    }


@app.get("/me")
async def me(current_user: dict = Depends(get_current_user)):
    return current_user


@app.get("/info")
async def get_info(current_user: dict = Depends(require_user)):
    text_health = await proxy_request("GET", upstream_url(PREDICT_TEXT_API_URL, "/health"))
    image_health = await proxy_request("GET", upstream_url(PREDICT_IMAGE_API_URL, "/health"))
    text_info = await proxy_request("GET", upstream_url(PREDICT_TEXT_API_URL, "/info/text"))
    image_info = await proxy_request("GET", upstream_url(PREDICT_IMAGE_API_URL, "/info/image"))
    train_health = await proxy_request("GET", upstream_url(TRAIN_API_URL, "/health"))

    return {
        "gateway": "ok",
        "current_user": current_user,
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


@app.post("/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    global CURRENT_SESSION
    CURRENT_SESSION = None
    return {"status": "logged_out", "username": current_user["username"]}


# ═══════════════════════════════════════════════════════════════════════════════
# 2. PREDICTION — SVM (text), CNN (image), multimodal
# ═══════════════════════════════════════════════════════════════════════════════

@app.post("/predict/svm", response_model=PredictResponse)
async def predict_svm(request: PredictTextRequest, current_user: dict = Depends(require_user)):
    """
    Prédit la catégorie Rakuten d'un produit à partir de son **texte** (TF-IDF + Linear SVM).

    Catégories possibles :
    - `0` → jeux vidéo
    - `1` → livres / magazines
    - `2` → jeux de société
    - `3` → maquettes / drones
    - `4` → mobilier
    - `5` → déco maison
    - `6` → fournitures
    - `7` → jardin / piscine
    """
    return await proxy_request(
        "POST",
        upstream_url(PREDICT_TEXT_API_URL, "/predict/svm"),
        json_body=request.model_dump(),
    )


@app.post("/predict/cnn", response_model=PredictResponse)
async def predict_cnn(request: PredictImageRequest, current_user: dict = Depends(require_user)):
    """
    Prédit la catégorie Rakuten d'un produit à partir du **nom du fichier image** (CNN).

    Catégories possibles :
    - `0` → jeux vidéo
    - `1` → livres / magazines
    - `2` → jeux de société
    - `3` → maquettes / drones
    - `4` → mobilier
    - `5` → déco maison
    - `6` → fournitures
    - `7` → jardin / piscine
    """
    return await proxy_request(
        "POST",
        upstream_url(PREDICT_IMAGE_API_URL, "/predict/cnn"),
        json_body=request.model_dump(),
    )


@app.post("/predict/multimodal", response_model=PredictMultimodalResponse)
async def predict_multimodal(request: PredictMultimodalRequest, current_user: dict = Depends(require_user)):
    """
    Prédit la catégorie Rakuten d'un produit à partir du **texte ET de l’image** (fusion SVM + CNN).

    Stratégie de fusion :
    - `agreement` : les deux modèles prédisent la même catégorie → consensus
    - `text_priority` : les modèles divergent → priorité donnée au SVM texte

    Catégories possibles :
    - `0` → jeux vidéo
    - `1` → livres / magazines
    - `2` → jeux de société
    - `3` → maquettes / drones
    - `4` → mobilier
    - `5` → déco maison
    - `6` → fournitures
    - `7` → jardin / piscine
    """
    text_result = await proxy_request(
        "POST",
        upstream_url(PREDICT_TEXT_API_URL, "/predict/svm"),
        json_body={"text": request.text},
    )
    image_result = await proxy_request(
        "POST",
        upstream_url(PREDICT_IMAGE_API_URL, "/predict/cnn"),
        json_body={"image_path": request.image_path},
    )

    same_prediction = text_result["predicted_label"] == image_result["predicted_label"]
    final_result = text_result if same_prediction else text_result

    return {
        "predicted_label": final_result["predicted_label"],
        "label_name": final_result["label_name"],
        "fusion_strategy": "agreement" if same_prediction else "text_priority",
        "text_prediction": text_result,
        "image_prediction": image_result,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 3. TRAIN & RETRAIN — Airflow orchestration + model reload
# ═══════════════════════════════════════════════════════════════════════════════

async def trigger_airflow_dag(mode: str = "train", model: str = "all") -> dict:
    """Trigger the Airflow mlops_orchestration DAG via REST API."""
    url = f"{AIRFLOW_API_URL}/api/v1/dags/mlops_orchestration/dagRuns"
    credentials = base64.b64encode(
        f"{AIRFLOW_USER}:{AIRFLOW_PASSWORD}".encode()
    ).decode()
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                url,
                json={"conf": {"mode": mode, "model": model}},
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Basic {credentials}",
                },
            )
        response.raise_for_status()
        data = response.json()
        dag_run_id = data.get("dag_run_id")
        return {
            "status": "dag_triggered",
            "mode": mode,
            "model": model,
            "dag_run_id": dag_run_id,
            "execution_date": data.get("execution_date"),
            "check_status": f"/orchestrate/status/{dag_run_id}",
        }
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=exc.response.status_code,
            detail=f"Airflow error: {exc.response.text}",
        ) from exc
    except httpx.RequestError as exc:
        raise HTTPException(status_code=503, detail="Airflow service unavailable") from exc


@app.post("/orchestrate/train/svm")
async def orchestrate_train_svm(current_user: dict = Depends(require_admin)):
    """Trigger Airflow DAG: dvc pull → train SVM → reload SVM."""
    return await trigger_airflow_dag(mode="train", model="svm")


@app.post("/orchestrate/train/cnn")
async def orchestrate_train_cnn(current_user: dict = Depends(require_admin)):
    """Trigger Airflow DAG: dvc pull → train CNN → reload CNN."""
    return await trigger_airflow_dag(mode="train", model="cnn")


@app.post("/orchestrate/retrain/svm")
async def orchestrate_retrain_svm(current_user: dict = Depends(require_admin)):
    """Trigger Airflow DAG: dvc pull → retrain SVM (preprocessing + training) → reload SVM."""
    return await trigger_airflow_dag(mode="retrain", model="svm")


@app.post("/orchestrate/retrain/cnn")
async def orchestrate_retrain_cnn(current_user: dict = Depends(require_admin)):
    """Trigger Airflow DAG: dvc pull → retrain CNN (preprocessing + training) → reload CNN."""
    return await trigger_airflow_dag(mode="retrain", model="cnn")


# ─── Routes directes training API (suivi état en temps réel) ────────────────

@app.post("/train/svm")
async def direct_train_svm(current_user: dict = Depends(require_admin)):
    """Lance l'entraînement SVM directement sur la training API (suivi /train/status disponible)."""
    return await proxy_request("POST", upstream_url(TRAIN_API_URL, "/train/svm"))


@app.post("/train/cnn")
async def direct_train_cnn(current_user: dict = Depends(require_admin)):
    """Lance l'entraînement CNN directement sur la training API (suivi /train/status disponible)."""
    return await proxy_request("POST", upstream_url(TRAIN_API_URL, "/train/cnn"))


@app.post("/retrain/svm")
async def direct_retrain_svm(current_user: dict = Depends(require_admin)):
    """Lance le retrain SVM (preprocessing + training) directement sur la training API."""
    return await proxy_request("POST", upstream_url(TRAIN_API_URL, "/retrain/svm"))


@app.post("/retrain/cnn")
async def direct_retrain_cnn(current_user: dict = Depends(require_admin)):
    """Lance le retrain CNN (preprocessing + training) directement sur la training API."""
    return await proxy_request("POST", upstream_url(TRAIN_API_URL, "/retrain/cnn"))


@app.get("/orchestrate/status/{dag_run_id}")
async def get_dag_run_status(dag_run_id: str, current_user: dict = Depends(require_admin)):
    """Check the status of an Airflow DAG run (queued, running, success, failed)."""
    url = f"{AIRFLOW_API_URL}/api/v1/dags/mlops_orchestration/dagRuns/{dag_run_id}"
    credentials = base64.b64encode(
        f"{AIRFLOW_USER}:{AIRFLOW_PASSWORD}".encode()
    ).decode()
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                url,
                headers={"Authorization": f"Basic {credentials}"},
            )
        response.raise_for_status()
        data = response.json()
        state = data.get("state", "unknown")
        result = {
            "dag_run_id": dag_run_id,
            "state": state,
            "start_date": data.get("start_date"),
            "end_date": data.get("end_date"),
        }
        if state == "success":
            result["message"] = "Training terminé avec succès"
        elif state == "failed":
            result["message"] = "Le DAG a échoué, vérifiez les logs Airflow"
        elif state in ("running", "queued"):
            result["message"] = "En cours d'exécution..."
        return result
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=exc.response.status_code,
            detail=f"Airflow error: {exc.response.text}",
        ) from exc
    except httpx.RequestError as exc:
        raise HTTPException(status_code=503, detail="Airflow service unavailable") from exc


@app.post("/reload/svm")
async def reload_svm_model(current_user: dict = Depends(require_admin)):
    return await proxy_request("POST", upstream_url(PREDICT_TEXT_API_URL, "/reload/text"))


@app.post("/reload/cnn")
async def reload_cnn_model(current_user: dict = Depends(require_admin)):
    return await proxy_request("POST", upstream_url(PREDICT_IMAGE_API_URL, "/reload/image"))


@app.get("/train/status")
async def training_status(current_user: dict = Depends(require_user)):
    """Retourne l'état en temps réel du pipeline d'entraînement en cours (step, epoch, métriques)."""
    return await proxy_request("GET", upstream_url(TRAIN_API_URL, "/train/status"))


# ═══════════════════════════════════════════════════════════════════════════════
# 4. CHECK UPDATE — data scan, baseline, auto-retrain
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/data/check-updates")
async def check_data_updates(current_user: dict = Depends(require_admin)):
    return {"status": "scan_completed", "changes": compute_data_changes()}


@app.post("/data/check-updates/retrain")
async def check_data_updates_and_retrain(current_user: dict = Depends(require_admin)):
    return await trigger_retraining_for_changes(compute_data_changes())


@app.post("/data/check-updates/baseline")
async def baseline_data_updates(current_user: dict = Depends(require_admin)):
    changes = compute_data_changes()
    save_retrain_state(
        {
            "text_files": changes["text"]["current_files"],
            "image_files": changes["image"]["current_files"],
        }
    )
    return {"status": "baseline_saved", "changes": changes}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("gateway_main:app", host="0.0.0.0", port=8000, reload=False)
