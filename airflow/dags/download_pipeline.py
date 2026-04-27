from datetime import datetime, timedelta
import os

from docker.types import Mount
from airflow import DAG
from airflow.models import Param
from airflow.operators.trigger_dagrun import TriggerDagRunOperator
from airflow.providers.docker.operators.docker import DockerOperator


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

DOCKER_BASE = dict(
    image=DVC_RUNNER_IMAGE,
    api_version="auto",
    auto_remove="success",
    docker_url="unix://var/run/docker.sock",
    network_mode="bridge",
    mount_tmp_dir=False,
    working_dir="/workspace",
    mounts=[Mount(source=PROJECT_ROOT_HOST, target="/workspace", type="bind")],
)

with DAG(
    dag_id="download_pipeline",
    start_date=datetime(2026, 4, 1),
    schedule=None,
    catchup=False,
    default_args=default_args,
    tags=["mlops", "data", "download"],
    params={"download_date": Param("", type=["string", "null"], minLength=0)},
) as dag:

    download_raw = DockerOperator(
        task_id="download_raw",
        command=["python", "-u", "src/preprocessing/download.py"],
        environment={
            "CHALLENGEDATA_USERNAME": "{{ var.value.challengedata_username }}",
            "CHALLENGEDATA_PASSWORD": "{{ var.value.challengedata_password }}",
            "DATA_RAW_DIR": "/workspace/data/raw",
            "DOWNLOAD_DATE": "{{ dag_run.conf.get('download_date') or '' }}",
        },
        **DOCKER_BASE,
    )

    dvc_push_raw = DockerOperator(
        task_id="dvc_push_raw",
        command=["sh", "-c", "dvc add data/raw && dvc push"],
        environment={
            "AWS_ACCESS_KEY_ID": "{{ var.value.dagshub_token }}",
            "AWS_SECRET_ACCESS_KEY": "{{ var.value.dagshub_token }}",
        },
        **DOCKER_BASE,
    )

    trigger_training = TriggerDagRunOperator(
        task_id="trigger_training",
        trigger_dag_id="mlops_orchestration",
        wait_for_completion=False,
        conf={"mode": "retrain", "model": "all"},
    )

    download_raw >> dvc_push_raw >> trigger_training
