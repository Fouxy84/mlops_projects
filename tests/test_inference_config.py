from src.inference.config import build_model_uri


def clear_model_env(monkeypatch):
    for env_var in (
        "MLFLOW_MODEL_URI",
        "MLFLOW_MODEL_VERSION",
        "MLFLOW_MODEL_ALIAS",
        "MLFLOW_MODEL_STAGE",
    ):
        monkeypatch.delenv(env_var, raising=False)


def test_model_uri_defaults_to_production_stage(monkeypatch):
    clear_model_env(monkeypatch)

    assert build_model_uri("Demo_Model") == "models:/Demo_Model/Production"


def test_model_uri_prefers_version_over_stage(monkeypatch):
    clear_model_env(monkeypatch)
    monkeypatch.setenv("MLFLOW_MODEL_STAGE", "Staging")
    monkeypatch.setenv("MLFLOW_MODEL_VERSION", "7")

    assert build_model_uri("Demo_Model") == "models:/Demo_Model/7"


def test_model_uri_prefers_explicit_uri(monkeypatch):
    clear_model_env(monkeypatch)
    monkeypatch.setenv("MLFLOW_MODEL_VERSION", "7")
    monkeypatch.setenv("MLFLOW_MODEL_URI", "runs:/abc123/model")

    assert build_model_uri("Demo_Model") == "runs:/abc123/model"
