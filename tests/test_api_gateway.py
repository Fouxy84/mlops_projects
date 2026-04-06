from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from gateway.gateway_main import app


client = TestClient(app)


def login_as(username: str, password: str) -> TestClient:
    session_client = TestClient(app)
    response = session_client.post(
        "/login",
        data={"username": username, "password": password},
    )
    assert response.status_code == 200
    return session_client


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_login_admin():
    response = client.post("/login", data={"username": "admin", "password": "admin"})
    assert response.status_code == 200
    assert response.json()["role"] == "admin"


def test_login_user():
    response = client.post("/login", data={"username": "user", "password": "user"})
    assert response.status_code == 200
    assert response.json()["role"] == "user"


def test_missing_session_cookie():
    response = client.post("/predict/text", json={"text": "hello"})
    assert response.status_code == 401


@patch("httpx.AsyncClient.post")
def test_predict_text_as_user(mock_post):
    mock_post.return_value = AsyncMock(json=lambda: {"prediction": "spam"}, status_code=200)
    mock_post.return_value.raise_for_status = lambda: None

    session_client = login_as("user", "user")
    response = session_client.post("/predict/text", json={"text": "hello"})

    assert response.status_code == 200
    assert "prediction" in response.json()


@patch("httpx.AsyncClient.post")
def test_predict_image_as_user(mock_post):
    mock_post.return_value = AsyncMock(json=lambda: {"prediction": "cat"}, status_code=200)
    mock_post.return_value.raise_for_status = lambda: None

    session_client = login_as("user", "user")
    response = session_client.post("/predict/image", json={"image_path": "img.jpg"})

    assert response.status_code == 200


@patch("httpx.AsyncClient.post")
def test_train_text_as_admin(mock_post):
    mock_post.return_value = AsyncMock(json=lambda: {"status": "ok"}, status_code=200)
    mock_post.return_value.raise_for_status = lambda: None

    session_client = login_as("admin", "admin")
    response = session_client.post("/train/text")

    assert response.status_code == 200
    assert response.json()["model"] == "text"


def test_train_text_forbidden_for_user():
    session_client = login_as("user", "user")
    response = session_client.post("/train/text")
    assert response.status_code == 403


@patch("httpx.AsyncClient.post")
def test_reload_text_as_admin(mock_post):
    mock_post.return_value = AsyncMock(json=lambda: {"status": "reloaded"}, status_code=200)
    mock_post.return_value.raise_for_status = lambda: None

    session_client = login_as("admin", "admin")
    response = session_client.post("/reload/text")

    assert response.status_code == 200


def test_data_check_forbidden_for_user():
    session_client = login_as("user", "user")
    response = session_client.get("/data/check-updates")
    assert response.status_code == 403


@patch("httpx.AsyncClient.get")
def test_info_as_user(mock_get):
    mock_get.return_value = AsyncMock(json=lambda: {"status": "ok"}, status_code=200)
    mock_get.return_value.raise_for_status = lambda: None

    session_client = login_as("user", "user")
    response = session_client.get("/info")

    assert response.status_code == 200
    data = response.json()
    assert "models" in data


def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert "routes" in response.json()
