# # src/training/run_training_text.py

from pathlib import Path
import json
import mlflow
from mlflow.tracking import MlflowClient

from src.preprocessing.text_cleaning import preprocess_training_data
from src.preprocessing.train_tfidf import train_tfidf_vectorizer
from src.train_models.train_linearsvm import train_and_evaluate_svm
import logging
import dagshub
import os


def _init_dagshub():
    os.environ.setdefault("MLFLOW_TRACKING_USERNAME", "Fouxy84")
    os.environ.setdefault("MLFLOW_TRACKING_PASSWORD", "fac5946f410149a81a7c5f4dc3402f1c7a4a1147")
    dagshub.init(repo_owner='Fouxy84', repo_name='mlops_projects', mlflow=True)
    mlflow.set_tracking_uri("https://dagshub.com/Fouxy84/mlops_projects.mlflow")

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =========================
# PATHS (CORRIGÉS)
# =========================
DATA_RAW_DIR = Path("data/raw")
DATA_PROCESSED_DIR = Path("data/processed")
MODELS_DIR = Path("models/text")  # Chemin corrigé

X_TRAIN_PATH = DATA_RAW_DIR / "X_train_update.csv"
Y_TRAIN_PATH = DATA_RAW_DIR / "Y_train_CVw08PX.csv"
TRAIN_CLEAN_PATH = DATA_PROCESSED_DIR / "train_clean.csv"


# =========================
# UTILITAIRES
# =========================
def make_json_serializable(obj):
    """Rend un objet JSON-sérialisable."""
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, dict):
        return {k: make_json_serializable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [make_json_serializable(v) for v in obj]
    return obj


# =========================
# PIPELINE COMPLET
# =========================
def main_texte(state_callback=None):
    _init_dagshub()
    mlflow.set_experiment("Text_Pipeline")
    with mlflow.start_run(run_name="Full_Text_Pipeline"):
        try:
            # 1. Préprocessing
            mlflow.set_tag("step", "preprocessing")
            if state_callback:
                state_callback("preprocessing", 1, 4)
            logger.info("1. Préprocessing du dataset...")
            preprocess_training_data(
                x_path=X_TRAIN_PATH,
                y_path=Y_TRAIN_PATH,
                output_path=TRAIN_CLEAN_PATH,
                detect_lang=True,
            )
            mlflow.log_artifact(TRAIN_CLEAN_PATH, "preprocessed_data")
            logger.info(f"✅ Dataset préprocessé: {TRAIN_CLEAN_PATH}")

            # 2. Vectorisation TF-IDF
            mlflow.set_tag("step", "vectorization")
            if state_callback:
                state_callback("vectorization", 2, 4)
            logger.info("2. Entraînement du vectorizer TF-IDF...")
            X_vec, vectorizer = train_tfidf_vectorizer(
                data_path=TRAIN_CLEAN_PATH,
                artifacts_dir=MODELS_DIR,
                text_column="text_clean",
                max_features=50000,
                ngram_range=(1, 2),
            )
            mlflow.log_artifact(MODELS_DIR / "tfidf.joblib", "preprocessing")
            logger.info("✅ Vectorizer TF-IDF entraîné et sauvegardé")

            # 3. Entraînement SVM
            mlflow.set_tag("step", "training")
            if state_callback:
                state_callback("training", 3, 4)
            logger.info("3. Entraînement du modèle SVM...")
            metrics = train_and_evaluate_svm(
                data_path=TRAIN_CLEAN_PATH,
                artifacts_dir=MODELS_DIR,
                test_size=0.2,
                svm_params={"C": 1.0},
            )

            # 4. Enregistrement du modèle dans le registry MLflow
            mlflow.sklearn.log_model(
                sk_model=metrics["svm_model"],
                artifact_path="model",
                registered_model_name="Text_Classifier_SVM",
            )

            # Transition vers le stage "Production"
            client = MlflowClient()
            all_versions = client.search_model_versions("name='Text_Classifier_SVM'")
            latest_version = max(all_versions, key=lambda mv: int(mv.version))

            client.transition_model_version_stage(
                name="Text_Classifier_SVM",
                stage="Production",
                version=latest_version.version,
            )
            logger.info(
                f"✅ Modèle Text_Classifier_SVM v{latest_version.version} passé en Production"
            )

            # 5. Sauvegarde des métriques
            mlflow.set_tag("step", "metrics")
            if state_callback:
                state_callback("metrics", 4, 4)
            logger.info("4. Sauvegarde des métriques...")
            metrics_path = MODELS_DIR / "metrics_svm.json"
            # Retirer le modèle des métriques avant JSON
            metrics_for_json = {k: v for k, v in metrics.items() if k != "svm_model"}
            metrics_serializable = make_json_serializable(metrics_for_json)
            with open(metrics_path, "w", encoding="utf-8") as f:
                json.dump(metrics_serializable, f, indent=2)
            mlflow.log_artifact(metrics_path, "metrics")
            mlflow.log_metrics(
                {
                    "accuracy": metrics_for_json["accuracy"],
                    "f1_macro": metrics_for_json["f1_macro"],
                }
            )

            # Tags finaux
            mlflow.set_tag("status", "success")
            mlflow.set_tag("pipeline", "text_classification")

            logger.info("\n===============================")
            logger.info("🎯 Pipeline texte terminé avec succès!")
            logger.info(f"   - Modèle SVM: {MODELS_DIR.resolve()}/svm.joblib")
            logger.info(f"   - Métriques: {metrics_path.resolve()}")
            logger.info(f"   - Run MLflow: {mlflow.active_run().info.run_id}")
            logger.info("===============================\n")

            return metrics_serializable

        except Exception as e:
            logger.error(f"❌ Erreur dans le pipeline texte: {e}", exc_info=True)
            mlflow.set_tag("status", "failed")
            raise


# =========================
# ENTRY POINT
# =========================
if __name__ == "__main__":
    main_texte()
    print(">>> MLFLOW_TRACKING_URI =", mlflow.get_tracking_uri())
