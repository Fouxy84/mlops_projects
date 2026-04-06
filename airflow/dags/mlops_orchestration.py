from datetime import datetime, timedelta
import os

from docker.types import Mount
from airflow import DAG
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import PythonOperator
from airflow.providers.docker.operators.docker import DockerOperator
import requests


GATEWAY_BASE_URL = os.getenv("GATEWAY_BASE_URL", "http://gateway:8000")
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
    start_date=datetime(2024, 1, 1),
    schedule="0 2 * * *",
    catchup=False,
    default_args=default_args,
    tags=["mlops", "airflow", "dvc"],
) as dag:
    start = EmptyOperator(task_id="start")
    end = EmptyOperator(task_id="end")

    def post_to_gateway(endpoint: str, token: str):
        response = requests.post(
            f"{GATEWAY_BASE_URL}{endpoint}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    dvc_pull = DockerOperator(
        task_id="dvc_pull_artifacts",
        image=DVC_RUNNER_IMAGE,
        api_version="auto",
        auto_remove="success",
        docker_url="unix://var/run/docker.sock",
        network_mode="bridge",
        mount_tmp_dir=False,
        working_dir="/workspace",
        command="dvc pull data/raw.dvc data/processed.dvc models/text/svm.joblib.dvc || dvc pull",
        environment={
            "DAGSHUB_USER": "{{ var.value.dagshub_user }}",
            "DAGSHUB_TOKEN": "{{ var.value.dagshub_token }}",
        },
        mounts=[Mount(source=PROJECT_ROOT_HOST, target="/workspace", type="bind")],
    )

    train_svm = PythonOperator(
        task_id="train_svm",
        python_callable=post_to_gateway,
        op_kwargs={"endpoint": "/train/svm", "token": "{{ var.value.api_token }}"},
    )

    train_cnn = PythonOperator(
        task_id="train_cnn",
        python_callable=post_to_gateway,
        op_kwargs={"endpoint": "/train/cnn", "token": "{{ var.value.api_token }}"},
    )

    reload_svm = PythonOperator(
        task_id="reload_svm",
        python_callable=post_to_gateway,
        op_kwargs={"endpoint": "/reload/svm", "token": "{{ var.value.api_token }}"},
    )

    reload_cnn = PythonOperator(
        task_id="reload_cnn",
        python_callable=post_to_gateway,
        op_kwargs={"endpoint": "/reload/cnn", "token": "{{ var.value.api_token }}"},
    )

    start >> dvc_pull >> [train_svm, train_cnn]
    train_svm >> reload_svm >> end
    train_cnn >> reload_cnn >> end
