import pandas as pd
from pathlib import Path
from PIL import Image
import numpy as np
import torch
import json
from src.train_models.train_linearsvm import train_and_evaluate_svm
from src.train_models.train_cnn import train_cnn
from src.preprocessing.train_tfidf import train_tfidf_vectorizer

IMAGE_SIZE =     128        
BATCH_SIZE = 2            
EPOCHS = 1                 
LR = 1e-3
NUM_CLASSES = 8

# ======================================================
# TEXT MODEL TFIDF + SVM
# =====================================================
def test_training_pipeline_creates_artifacts(tmp_path):
    # --- Fake dataset (3 classes) ---
    df = pd.DataFrame({
        "text_clean": [
            "console de jeu",
            "jeu video pc",
            "livre de cuisine",
            "roman policier",
            "chaise de bureau",
            "table en bois"
        ],
        "label": [0, 0, 1, 1, 2, 2]
    })

    data_path = tmp_path / "train_clean.csv"
    df.to_csv(data_path, index=False)

    artifacts_dir = tmp_path / "artefacts"
    artifacts_dir.mkdir()

    # Train TF-IDF FIRST
    train_tfidf_vectorizer(
        data_path=data_path,
        artifacts_dir=artifacts_dir,
        max_features=50,
        ngram_range=(1, 1),
    )

    # --- Force safe split for CI ---
    metrics = train_and_evaluate_svm(
       data_path=data_path,
       artifacts_dir=artifacts_dir,
       svm_params={"C": 1.0},
       test_size=0.5)

    assert (artifacts_dir / "tfidf.joblib").exists()
    assert (artifacts_dir / "svm.joblib").exists()
    assert isinstance(metrics["f1_macro"], float)
    
# ======================================================
# IMAGE MODEL (CNN)
# ======================================================
def test_training_cnn_pipeline_creates_artifacts(tmp_path):
    # ----------------------------
    # Create fake image dataset
    # ----------------------------
    image_dir = tmp_path / "images"
    image_dir.mkdir()

    labels = []
    image_paths = []

    for i in range(10):
        label = i % 2
        img = Image.fromarray(
            np.random.randint(0, 255, (64, 64, 3), dtype=np.uint8)
        )

        img_path = image_dir / f"image_{i}_product_{i}.jpg"
        img.save(img_path)

        image_paths.append(str(img_path))
        labels.append(label)

    df = pd.DataFrame({
        "image_path": image_paths,
        "label": labels
    })

    data_path = tmp_path / "train_images.csv"
    df.to_csv(data_path, index=False)

    artifacts_dir = tmp_path / "models" / "images"
    artifacts_dir.mkdir(parents=True)

    # ----------------------------
    # Train CNN
    # ----------------------------
   #metrics = 
    train_cnn(data_path=data_path,
        artifacts_dir = artifacts_dir)

    # ----------------------------
    # Assertions
    # ----------------------------
    model_path = artifacts_dir / "cnn.pt"
    metrics_path = artifacts_dir / "metrics_cnn.json"

    assert model_path.exists()
    assert metrics_path.exists()

    with open(metrics_path) as f:
        saved_metrics = json.load(f)

    #assert "accuracy" in saved_metrics or "loss" in saved_metrics
    assert "f1_macro" in saved_metrics
    assert isinstance(saved_metrics["f1_macro"], float)
    
    # Model can be loaded
    model = torch.load(model_path, map_location="cpu")
    assert model is not None
    assert isinstance(model, dict)
    assert len(model) > 0
