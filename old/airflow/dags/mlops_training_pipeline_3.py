"""
MLOps Training Pipeline V2 (Production-Ready)

Flow:
1. Data preparation
2. Trigger training via Gateway
3. Evaluate models
4. Register models
5. Reload models via Gateway
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.empty import EmptyOperator
from airflow.providers.http.operators.http import SimpleHttpOperator
from airflow.utils.task_group import TaskGroup
import pandas as pd
import logging

# ==========================================================
# CONFIG
# ==========================================================
DAG_ID = "mlops_training_pipeline_v2"

DEFAULT_ARGS = {
    "owner": "mlops",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

SCHEDULE = "0 2 * * *"

GATEWAY_CONN_ID = "gateway_api"

AUTH_HEADERS = {
    "Authorization": "Bearer {{ var.value.api_token }}"
}

logger = logging.getLogger(__name__)

# ==========================================================
# DAG
# ==========================================================
with DAG(
    dag_id=DAG_ID,
    default_args=DEFAULT_ARGS,
    start_date=datetime(2024, 1, 1),
    schedule_interval=SCHEDULE,
    catchup=False,
    tags=["mlops", "pipeline", "v2"],
) as dag:

    # =========================
    # START / END
    # =========================
    start = EmptyOperator(task_id="start")
    end = EmptyOperator(task_id="end")

    # ======================================================
    # DATA PIPELINE
    # ======================================================
    def load_data():
        logger.info("Loading raw data...")
        df = pd.read_csv("/app/data/raw/X_train_update.csv")
        logger.info(f"{len(df)} rows loaded")

    def preprocess_data():
        logger.info("Preprocessing data...")
        # TODO: clean_text integration
        pass

    def validate_data():
        logger.info("Validating dataset...")
        df = pd.read_csv("/app/data/processed/train_clean.csv")
        if df.empty:
            raise ValueError("Dataset vide")
        logger.info("Dataset valid")

    with TaskGroup("data_pipeline") as data_pipeline:

        load = PythonOperator(
            task_id="load_data",
            python_callable=load_data,
        )

        preprocess = PythonOperator(
            task_id="preprocess_data",
            python_callable=preprocess_data,
        )

        validate = PythonOperator(
            task_id="validate_data",
            python_callable=validate_data,
        )

        load >> preprocess >> validate

    # ======================================================
    # TRAINING (via Gateway)
    # ======================================================
    with TaskGroup("training") as training:

        train_text = SimpleHttpOperator(
            task_id="train_text_model",
            http_conn_id=GATEWAY_CONN_ID,
            endpoint="/train/text",
            method="POST",
            headers=AUTH_HEADERS,
            log_response=True,
        )

        train_image = SimpleHttpOperator(
            task_id="train_image_model",
            http_conn_id=GATEWAY_CONN_ID,
            endpoint="/train/image",
            method="POST",
            headers=AUTH_HEADERS,
            log_response=True,
        )

        [train_text, train_image]

    # ======================================================
    # EVALUATION
    # ======================================================
    def evaluate_models():
        logger.info("Evaluating models...")
        # 👉 brancher MLflow ici plus tard
        return {"status": "evaluated"}

    evaluate = PythonOperator(
        task_id="evaluate_models",
        python_callable=evaluate_models,
    )

    # ======================================================
    # REGISTER
    # ======================================================
    def register_models():
        logger.info("Registering models...")
        # 👉 MLflow registry plus tard
        return {"status": "registered"}

    register = PythonOperator(
        task_id="register_models",
        python_callable=register_models,
    )

    # ======================================================
    # RELOAD (via Gateway)
    # ======================================================
    with TaskGroup("reload") as reload_group:

        reload_text = SimpleHttpOperator(
            task_id="reload_text_model",
            http_conn_id=GATEWAY_CONN_ID,
            endpoint="/reload/text",
            method="POST",
            headers=AUTH_HEADERS,
            log_response=True,
        )

        reload_image = SimpleHttpOperator(
            task_id="reload_image_model",
            http_conn_id=GATEWAY_CONN_ID,
            endpoint="/reload/image",
            method="POST",
            headers=AUTH_HEADERS,
            log_response=True,
        )

        [reload_text, reload_image]

    # ======================================================
    # MONITORING (OPTIONNEL)
    # ======================================================
    def log_metrics():
        logger.info("Logging pipeline metrics...")
        return {"status": "logged"}

    metrics = PythonOperator(
        task_id="log_metrics",
        python_callable=log_metrics,
    )

    # ======================================================
    # PIPELINE FLOW
    # ======================================================
    start >> data_pipeline >> training >> evaluate >> register >> reload_group >> metrics >> end