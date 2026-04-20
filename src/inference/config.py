import os


def build_model_uri(model_name: str) -> str:
    configured_uri = os.getenv("MLFLOW_MODEL_URI", "").strip()
    if configured_uri:
        return configured_uri

    configured_version = os.getenv("MLFLOW_MODEL_VERSION", "").strip()
    if configured_version:
        return f"models:/{model_name}/{configured_version}"

    configured_alias = os.getenv("MLFLOW_MODEL_ALIAS", "").strip()
    if configured_alias:
        return f"models:/{model_name}@{configured_alias}"

    configured_stage = os.getenv("MLFLOW_MODEL_STAGE", "Production").strip()
    return f"models:/{model_name}/{configured_stage}"
