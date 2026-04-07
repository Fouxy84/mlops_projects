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


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


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


def test_missing_session_cookie():
    gateway_main.CURRENT_SESSION = None
    response = client.post("/predict/svm", json={"text": "hello"})
    assert response.status_code == 401


@patch("httpx.AsyncClient.post")
def test_predict_text_as_user(mock_post):
    mock_post.return_value = AsyncMock(json=lambda: {"prediction": "spam"}, status_code=200)
    mock_post.return_value.raise_for_status = lambda: None

    login_as("user", "user")
    response = client.post("/predict/svm", json={"text": "hello"})

    assert response.status_code == 200
    assert "prediction" in response.json()


@patch("httpx.AsyncClient.post")
def test_predict_image_as_user(mock_post):
    mock_post.return_value = AsyncMock(json=lambda: {"prediction": "cat"}, status_code=200)
    mock_post.return_value.raise_for_status = lambda: None

    login_as("user", "user")
    response = client.post("/predict/cnn", json={"image_path": "img.jpg"})

    assert response.status_code == 200


@patch("httpx.AsyncClient.post")
def test_train_text_as_admin(mock_post):
    mock_post.return_value = AsyncMock(json=lambda: {"status": "ok"}, status_code=200)
    mock_post.return_value.raise_for_status = lambda: None

    login_as("admin", "admin")
    response = client.post("/train/svm")

    assert response.status_code == 200
    assert response.json()["model"] == "text"


def test_train_text_forbidden_for_user():
    login_as("user", "user")
    response = client.post("/train/svm")
    assert response.status_code == 403


@patch("httpx.AsyncClient.post")
def test_reload_text_as_admin(mock_post):
    mock_post.return_value = AsyncMock(json=lambda: {"status": "reloaded"}, status_code=200)
    mock_post.return_value.raise_for_status = lambda: None

    login_as("admin", "admin")
    response = client.post("/reload/svm")

    assert response.status_code == 200


def test_data_check_forbidden_for_user():
    login_as("user", "user")
    response = client.get("/data/check-updates")
    assert response.status_code == 403


@patch("httpx.AsyncClient.get")
def test_info_as_user(mock_get):
    mock_get.return_value = AsyncMock(json=lambda: {"status": "ok"}, status_code=200)
    mock_get.return_value.raise_for_status = lambda: None

    login_as("user", "user")
    response = client.get("/info")

    assert response.status_code == 200
    data = response.json()
    assert "models" in data
