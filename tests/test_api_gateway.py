from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

import gateway.gateway_main as gateway_main
from gateway.gateway_main import app


client = TestClient(app)


def login_as(username: str, password: str):
    gateway_main.CURRENT_SESSION = None
    response = client.post(
        "/login",
        data={"username": username, "password": password},
    )
    assert response.status_code == 200
    return response


def bearer_headers():
    return {"Authorization": f"Bearer {gateway_main.API_TOKEN}"}


# ══════════════════════════════════════════
# 1. INTRO — health, auth, system info
# ══════════════════════════════════════════

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_root_lists_sections():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    sections = data["sections"]
    assert sections["intro"]["health"] == "/health"
    assert sections["prediction"]["svm"] == "/predict/svm"
    assert sections["prediction"]["cnn"] == "/predict/cnn"
    assert sections["train_retrain"]["train_svm"] == "/orchestrate/train/svm"
    assert sections["check_update"]["scan"] == "/data/check-updates"


def test_metrics_endpoint():
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]


def test_upstream_url_normalizes_slashes():
    assert gateway_main.upstream_url("http://service:8000/", "/predict/svm") == "http://service:8000/predict/svm"

def test_login_admin():
    gateway_main.CURRENT_SESSION = None
    response = client.post("/login", data={"username": "admin", "password": "admin"})
    assert response.status_code == 200
    assert response.json()["role"] == "admin"


def test_login_user():
    gateway_main.CURRENT_SESSION = None
    response = client.post("/login", data={"username": "user", "password": "user"})
    assert response.status_code == 200
    assert response.json()["role"] == "user"


def test_login_invalid_credentials():
    gateway_main.CURRENT_SESSION = None
    response = client.post("/login", data={"username": "admin", "password": "wrong"})
    assert response.status_code == 401


def test_missing_session_returns_401():
    gateway_main.CURRENT_SESSION = None
    response = client.post("/predict/svm", json={"text": "hello"})
    assert response.status_code == 401


def test_me_as_logged_in_user():
    login_as("user", "user")
    response = client.get("/me")
    assert response.status_code == 200
    assert response.json()["username"] == "user"
    assert response.json()["role"] == "user"


def test_me_with_bearer_token():
    gateway_main.CURRENT_SESSION = None
    response = client.get("/me", headers=bearer_headers())
    assert response.status_code == 200
    assert response.json()["role"] == "admin"


def test_me_with_invalid_bearer_token():
    gateway_main.CURRENT_SESSION = None
    response = client.get("/me", headers={"Authorization": "Bearer wrong-token"})
    assert response.status_code == 401


def test_logout():
    login_as("admin", "admin")
    response = client.post("/logout")
    assert response.status_code == 200
    assert response.json()["status"] == "logged_out"
    response = client.get("/me")
    assert response.status_code == 401


# ══════════════════════════════════════════
# 2. PREDICTION — SVM (text), CNN (image), multimodal
# ══════════════════════════════════════════

@patch("httpx.AsyncClient.post")
def test_predict_svm_as_user(mock_post):
    mock_post.return_value = AsyncMock(json=lambda: {"predicted_label": 1, "label_name": "cat"}, status_code=200)
    mock_post.return_value.raise_for_status = lambda: None

    login_as("user", "user")
    response = client.post("/predict/svm", json={"text": "hello"})

    assert response.status_code == 200
    assert mock_post.call_args.args[0] == "http://predict-text-api:8000/predict/svm"


@patch("httpx.AsyncClient.post")
def test_predict_cnn_as_user(mock_post):
    mock_post.return_value = AsyncMock(json=lambda: {"predicted_label": 2, "label_name": "dog"}, status_code=200)
    mock_post.return_value.raise_for_status = lambda: None

    login_as("user", "user")
    response = client.post("/predict/cnn", json={"image_path": "img.jpg"})

    assert response.status_code == 200
    assert mock_post.call_args.args[0] == "http://predict-image-api:8000/predict/cnn"


@patch("httpx.AsyncClient.post")
def test_predict_multimodal_as_user(mock_post):
    mock_post.return_value = AsyncMock(
        json=lambda: {"predicted_label": 1, "label_name": "cat"},
        status_code=200,
    )
    mock_post.return_value.raise_for_status = lambda: None

    login_as("user", "user")
    response = client.post("/predict/multimodal", json={"text": "hello", "image_path": "img.jpg"})

    assert response.status_code == 200
    data = response.json()
    assert "predicted_label" in data
    assert "fusion_strategy" in data
    assert "text_prediction" in data
    assert "image_prediction" in data


def test_predict_text_old_alias_not_registered():
    response = client.post("/predict/text", json={"text": "hello"})
    assert response.status_code == 404


def test_predict_image_old_alias_not_registered():
    response = client.post("/predict/image", json={"image_path": "img.jpg"})
    assert response.status_code == 404


# ══════════════════════════════════════════
# 3. TRAIN & RETRAIN — Airflow orchestration + reload
# ══════════════════════════════════════════

@patch("httpx.AsyncClient.post")
def test_orchestrate_train_svm_as_admin(mock_post):
    mock_post.return_value = AsyncMock(
        json=lambda: {"dag_run_id": "run_123", "execution_date": "2026-04-20T00:00:00"},
        status_code=200,
    )
    mock_post.return_value.raise_for_status = lambda: None

    login_as("admin", "admin")
    response = client.post("/orchestrate/train/svm")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "dag_triggered"
    assert data["mode"] == "train"
    assert data["model"] == "svm"
    assert "dag_run_id" in data
    assert "check_status" in data


@patch("httpx.AsyncClient.post")
def test_orchestrate_train_cnn_as_admin(mock_post):
    mock_post.return_value = AsyncMock(
        json=lambda: {"dag_run_id": "run_456", "execution_date": "2026-04-20T00:00:00"},
        status_code=200,
    )
    mock_post.return_value.raise_for_status = lambda: None

    login_as("admin", "admin")
    response = client.post("/orchestrate/train/cnn")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "dag_triggered"
    assert data["model"] == "cnn"


@patch("httpx.AsyncClient.post")
def test_orchestrate_retrain_svm_as_admin(mock_post):
    mock_post.return_value = AsyncMock(
        json=lambda: {"dag_run_id": "run_789", "execution_date": "2026-04-20T00:00:00"},
        status_code=200,
    )
    mock_post.return_value.raise_for_status = lambda: None

    login_as("admin", "admin")
    response = client.post("/orchestrate/retrain/svm")

    assert response.status_code == 200
    data = response.json()
    assert data["mode"] == "retrain"
    assert data["model"] == "svm"


@patch("httpx.AsyncClient.post")
def test_orchestrate_retrain_cnn_as_admin(mock_post):
    mock_post.return_value = AsyncMock(
        json=lambda: {"dag_run_id": "run_000", "execution_date": "2026-04-20T00:00:00"},
        status_code=200,
    )
    mock_post.return_value.raise_for_status = lambda: None

    login_as("admin", "admin")
    response = client.post("/orchestrate/retrain/cnn")

    assert response.status_code == 200
    data = response.json()
    assert data["mode"] == "retrain"
    assert data["model"] == "cnn"


def test_orchestrate_forbidden_for_user():
    login_as("user", "user")
    response = client.post("/orchestrate/train/svm")
    assert response.status_code == 403


@patch("httpx.AsyncClient.post")
def test_orchestrate_with_bearer_token(mock_post):
    mock_post.return_value = AsyncMock(
        json=lambda: {"dag_run_id": "run_bearer", "execution_date": "2026-04-20T00:00:00"},
        status_code=200,
    )
    mock_post.return_value.raise_for_status = lambda: None

    gateway_main.CURRENT_SESSION = None
    response = client.post("/orchestrate/train/svm", headers=bearer_headers())

    assert response.status_code == 200
    assert response.json()["status"] == "dag_triggered"




@patch("httpx.AsyncClient.get")
def test_orchestrate_status_success(mock_get):
    mock_get.return_value = AsyncMock(
        json=lambda: {"state": "success", "start_date": "2026-04-20T00:00:00", "end_date": "2026-04-20T00:05:00"},
        status_code=200,
    )
    mock_get.return_value.raise_for_status = lambda: None

    login_as("admin", "admin")
    response = client.get("/orchestrate/status/run_123")

    assert response.status_code == 200
    data = response.json()
    assert data["state"] == "success"
    assert "terminé" in data["message"] or "succès" in data["message"]


@patch("httpx.AsyncClient.get")
def test_orchestrate_status_running(mock_get):
    mock_get.return_value = AsyncMock(
        json=lambda: {"state": "running", "start_date": "2026-04-20T00:00:00", "end_date": None},
        status_code=200,
    )
    mock_get.return_value.raise_for_status = lambda: None

    login_as("admin", "admin")
    response = client.get("/orchestrate/status/run_456")

    assert response.status_code == 200
    assert "cours" in response.json()["message"]


@patch("httpx.AsyncClient.get")
def test_orchestrate_status_failed(mock_get):
    mock_get.return_value = AsyncMock(
        json=lambda: {"state": "failed", "start_date": "2026-04-20T00:00:00", "end_date": "2026-04-20T00:03:00"},
        status_code=200,
    )
    mock_get.return_value.raise_for_status = lambda: None

    login_as("admin", "admin")
    response = client.get("/orchestrate/status/run_789")

    assert response.status_code == 200
    assert "échoué" in response.json()["message"] or "failed" in response.json()["message"].lower()


def test_orchestrate_status_forbidden_for_user():
    login_as("user", "user")
    response = client.get("/orchestrate/status/run_123")
    assert response.status_code == 403




@patch("httpx.AsyncClient.post")
def test_reload_svm_as_admin(mock_post):
    mock_post.return_value = AsyncMock(json=lambda: {"status": "reloaded"}, status_code=200)
    mock_post.return_value.raise_for_status = lambda: None

    login_as("admin", "admin")
    response = client.post("/reload/svm")
    assert response.status_code == 200
    assert mock_post.call_args.args[0] == "http://predict-text-api:8000/reload/text"


@patch("httpx.AsyncClient.post")
def test_reload_cnn_as_admin(mock_post):
    mock_post.return_value = AsyncMock(json=lambda: {"status": "reloaded"}, status_code=200)
    mock_post.return_value.raise_for_status = lambda: None

    login_as("admin", "admin")
    response = client.post("/reload/cnn")
    assert response.status_code == 200
    assert mock_post.call_args.args[0] == "http://predict-image-api:8000/reload/image"


def test_reload_old_alias_not_registered():
    response = client.post("/reload/text")
    assert response.status_code == 404


def test_reload_forbidden_for_user():
    login_as("user", "user")
    response = client.post("/reload/svm")
    assert response.status_code == 403


# ══════════════════════════════════════════
# 4. CHECK UPDATE — data scan, baseline, auto-retrain
# ══════════════════════════════════════════

def test_data_check_forbidden_for_user():
    login_as("user", "user")
    response = client.get("/data/check-updates")
    assert response.status_code == 403


def test_data_check_as_admin():
    login_as("admin", "admin")
    response = client.get("/data/check-updates")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "scan_completed"
    assert "changes" in data


def test_data_baseline_as_admin():
    login_as("admin", "admin")
    response = client.post("/data/check-updates/baseline")
    assert response.status_code == 200
    assert response.json()["status"] == "baseline_saved"


@patch("httpx.AsyncClient.post")
def test_data_retrain_as_admin(mock_post):
    mock_post.return_value = AsyncMock(json=lambda: {"status": "ok"}, status_code=200)
    mock_post.return_value.raise_for_status = lambda: None

    login_as("admin", "admin")
    response = client.post("/data/check-updates/retrain")
    assert response.status_code == 200
    assert response.json()["status"] in ("retraining_triggered", "no_new_files")




@patch("httpx.AsyncClient.get")
def test_info_as_user(mock_get):
    mock_get.return_value = AsyncMock(json=lambda: {"status": "ok"}, status_code=200)
    mock_get.return_value.raise_for_status = lambda: None

    login_as("user", "user")
    response = client.get("/info")

    assert response.status_code == 200
    data = response.json()
    assert "models" in data
    assert "prediction_apis" in data
    assert "training_api" in data
