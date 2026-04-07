from fastapi.testclient import TestClient
from pathlib import Path
import numpy as np
from PIL import Image

from api.main import app

client = TestClient(app)


# ------------------------
# HEALTH
# ------------------------
def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


# ------------------------
# SVM PREDICTION
# ------------------------
def test_predict_endpoint_svm():
    payload = {
        "text": "console de jeu portable nintendo"
    }

    response = client.post("/predict/svm", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert "predicted_label" in data
    assert isinstance(data["predicted_label"], int)

    # optionnel : scores SVM
    if "decision_score" in data:
        assert isinstance(data["decision_score"], list)


# ------------------------
# CNN PREDICTION
# ------------------------
def test_predict_endpoint_cnn(tmp_path):
    # Create a fake image
    img = Image.fromarray(
        np.random.randint(0, 255, (128, 128, 3), dtype=np.uint8)
    )

    image_path = tmp_path / "image_0_product_0.jpg"
    img.save(image_path)

    payload = {
        "image_path": str(image_path)
    }

    response = client.post("/predict/cnn", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert "predicted_label" in data
    assert isinstance(data["predicted_label"], int)
