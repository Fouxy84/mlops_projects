from datetime import datetime, timedelta
import os

from docker.types import Mount
from airflow import DAG
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import PythonOperator
from airflow.providers.docker.operators.docker import DockerOperator
import requests


GATEWAY_BASE_URL = os.getenv("GATEWAY_BASE_URL", "http://gateway:8000")
TRAINING_BASE_URL = os.getenv("TRAINING_BASE_URL", "http://training-api:8000")
API_TOKEN = os.getenv("API_TOKEN", "mlops-secret-token")
DVC_RUNNER_IMAGE = os.getenv("DVC_RUNNER_IMAGE", "mlops-dvc-runner:local")
PROJECT_ROOT_HOST = os.getenv(
    "PROJECT_ROOT_HOST",
    "c:/Users/coach/Desktop/datascientest/Projet DATASCIENTEST/projet_MLops/mlops_projects",
)

default_args = {
    "owner": "mlops",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="mlops_orchestration",
    start_date=datetime(2026, 4, 1),
    schedule="0 2 * * *",
    catchup=False,
    default_args=default_args,
    tags=["mlops", "airflow", "dvc"],
    params={"mode": "train", "model": "all"},
) as dag:
    start = EmptyOperator(task_id="start")
    end = EmptyOperator(task_id="end")

    def post_to_gateway(endpoint: str):
        response = requests.post(
            f"{GATEWAY_BASE_URL}{endpoint}",
            headers={"Authorization": f"Bearer {API_TOKEN}"},
            timeout=300,
        )
        response.raise_for_status()
        return response.json()

    def post_to_training(endpoint: str):
        response = requests.post(
            f"{TRAINING_BASE_URL}{endpoint}",
            headers={"Authorization": f"Bearer {API_TOKEN}"},
            timeout=300,
        )
        response.raise_for_status()
        return response.json()

    def should_run_model(model_filter: str, target: str) -> bool:
        return model_filter in ("all", target)

    def train_or_retrain_svm(**context):
        model = context["params"].get("model", "all")
        if not should_run_model(model, "svm"):
            return {"status": "skipped", "model": "svm"}
        mode = context["params"].get("mode", "train")
        endpoint = "/retrain/svm" if mode == "retrain" else "/train/svm"
        return post_to_training(endpoint)

    def train_or_retrain_cnn(**context):
        model = context["params"].get("model", "all")
        if not should_run_model(model, "cnn"):
            return {"status": "skipped", "model": "cnn"}
        mode = context["params"].get("mode", "train")
        endpoint = "/retrain/cnn" if mode == "retrain" else "/train/cnn"
        return post_to_training(endpoint)

    def reload_svm_task(**context):
        model = context["params"].get("model", "all")
        if not should_run_model(model, "svm"):
            return {"status": "skipped", "model": "svm"}
        return post_to_gateway("/reload/svm")

    def reload_cnn_task(**context):
        model = context["params"].get("model", "all")
        if not should_run_model(model, "cnn"):
            return {"status": "skipped", "model": "cnn"}
        return post_to_gateway("/reload/cnn")

    dvc_pull = DockerOperator(
        task_id="dvc_pull_artifacts",
        image=DVC_RUNNER_IMAGE,
        api_version="auto",
        auto_remove="success",
        docker_url="unix://var/run/docker.sock",
        network_mode="bridge",
        mount_tmp_dir=False,
        working_dir="/workspace",
        command=["sh", "-c", "dvc pull --force data/raw.dvc data/processed.dvc models/text/svm.joblib.dvc || dvc pull --force"],
        environment={
            "DAGSHUB_USER": "{{ var.value.dagshub_user }}",
            "DAGSHUB_TOKEN": "{{ var.value.dagshub_token }}",
            "AWS_ACCESS_KEY_ID": "{{ var.value.dagshub_token }}",
            "AWS_SECRET_ACCESS_KEY": "{{ var.value.dagshub_token }}",
        },
        mounts=[Mount(source=PROJECT_ROOT_HOST, target="/workspace", type="bind")],
    )

    train_svm = PythonOperator(
        task_id="train_svm",
        python_callable=train_or_retrain_svm,
    )

    train_cnn = PythonOperator(
        task_id="train_cnn",
        python_callable=train_or_retrain_cnn,
    )

    reload_svm = PythonOperator(
        task_id="reload_svm",
        python_callable=reload_svm_task,
    )

    reload_cnn = PythonOperator(
        task_id="reload_cnn",
        python_callable=reload_cnn_task,
    )

    start >> dvc_pull >> [train_svm, train_cnn]
    train_svm >> reload_svm >> end
    train_cnn >> reload_cnn >> end
