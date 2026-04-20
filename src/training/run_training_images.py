import logging
from pathlib import Path
import json
import mlflow
from src.preprocessing.text_cleaning import preprocess_training_data
from src.train_models.train_cnn import train_cnn
import dagshub
import os

logger = logging.getLogger(__name__)


def _init_dagshub():
    os.environ.setdefault("MLFLOW_TRACKING_USERNAME", "Fouxy84")
    os.environ.setdefault("MLFLOW_TRACKING_PASSWORD", "fac5946f410149a81a7c5f4dc3402f1c7a4a1147")
    dagshub.init(repo_owner='Fouxy84', repo_name='mlops_projects', mlflow=True)
    mlflow.set_tracking_uri("https://dagshub.com/Fouxy84/mlops_projects.mlflow")

# =========================
# PATHS
# =========================
DATA_RAW_DIR = Path("data/raw")
DATA_PROCESSED_DIR = Path("data/processed")
MODELS_DIR = Path("models/images")

X_TRAIN_PATH = DATA_RAW_DIR / "X_train_update.csv"
Y_TRAIN_PATH = DATA_RAW_DIR / "Y_train_CVw08PX.csv"
TRAIN_CLEAN_PATH = DATA_PROCESSED_DIR / "train_clean.csv"


# =========================
# UTILS
# =========================
def make_json_serializable(obj):
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, dict):
        return {k: make_json_serializable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [make_json_serializable(v) for v in obj]
    return obj


# =========================
# PIPELINE
# =========================
def main_image():
    _init_dagshub()
    mlflow.set_experiment("Image_Pipeline")
    with mlflow.start_run(run_name="Full_Image_Pipeline", nested=True):
        mlflow.set_tag("step", "preprocessing")
        print("\n")
        print("1. Preprocessing dataset (text + image)")
        preprocess_training_data(
            x_path=X_TRAIN_PATH,
            y_path=Y_TRAIN_PATH,
            output_path=TRAIN_CLEAN_PATH,
            detect_lang=True,
        )
        mlflow.log_artifact(TRAIN_CLEAN_PATH, "preprocessed_data")
        print(f"Dataset préprocessé sauvegardé: {TRAIN_CLEAN_PATH}")

        mlflow.set_tag("step", "training")
        print("\n")
        print("2. Training CNN from scratch")
        model, metrics = train_cnn(
            data_path=TRAIN_CLEAN_PATH,
            artifacts_dir=MODELS_DIR,
        )

        # 4. Enregistrement du modèle dans le registry MLflow
        mlflow.pytorch.log_model(
            pytorch_model=model,
            artifact_path="model_cnn",
            registered_model_name="CNN_Image_Classifier",
        )

        # Transition vers le stage "Production"
        client = mlflow.MlflowClient()
        all_versions = client.search_model_versions("name='CNN_Image_Classifier'")
        latest_version = max(all_versions, key=lambda mv: int(mv.version))

        client.transition_model_version_stage(
            name="CNN_Image_Classifier",
            stage="Production",
            version=latest_version.version,
        )
        logger.info(
            f"✅ Modèle CNN_Image_Classifier v{latest_version.version} passé en Production"
        )

        mlflow.set_tag("step", "metrics")
        print("\n")
        print("3. Save global metrics")
        metrics_path = MODELS_DIR / "metrics_cnn_pipeline.json"
        metrics = make_json_serializable(metrics)
        mlflow.log_metric("image_pipeline_accuracy", metrics["accuracy"])
        mlflow.log_metric("image_pipeline_f1", metrics["f1_macro"])

        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        with open(metrics_path, "w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2)
        mlflow.log_artifact(metrics_path, "image_pipeline_metrics")

        mlflow.set_tag("status", "success")
        mlflow.set_tag("pipeline", "image_classification")

        print("\n===============================")
        print(" Pipeline image terminé avec succès!")
        print(f"   - Modèle CNN: {MODELS_DIR.resolve()}/cnn.pt")
        print(f"   - Métriques_CNN: {metrics_path.resolve()}")
        print(f"   - Run MLflow: {metrics['mlflow_run_id']}")
        print("===============================\n")


# =========================
# ENTRY POINT
# =========================
if __name__ == "__main__":
    main_image()
    print(">>> MLFLOW_TRACKING_URI =", mlflow.get_tracking_uri())
