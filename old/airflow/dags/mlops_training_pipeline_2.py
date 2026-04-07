# /airflow/dags/mlops_training_pipeline_2.py
"""
MLOps Training Pipeline (Clean Version)

Orchestration:
1. Data pipeline (Python)
2. Training (via Gateway)
3. Evaluation
4. Registration
5. Reload models (via Gateway)
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.empty import EmptyOperator
from airflow.providers.http.operators.http import SimpleHttpOperator
from airflow.utils.task_group import TaskGroup

import pandas as pd
import logging

logger = logging.getLogger(__name__)

# ==========================================================
# CONFIGURATION
# ==========================================================
DEFAULT_ARGS = {
    "owner": "mlops",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

DAG_ID = "mlops_training_pipeline"
SCHEDULE = "0 2 * * *"  # daily

# Airflow connections
GATEWAY_CONN_ID = "gateway_api"

# JWT token stocké dans Airflow Variables
AUTH_HEADER = {
    "Authorization": "Bearer {{ var.value.api_token }}"
}

# ==========================================================
# DAG
# ==========================================================
with DAG(
    dag_id=DAG_ID,
    default_args=DEFAULT_ARGS,
    start_date=datetime(2024, 1, 1),
    schedule_interval=SCHEDULE,
    catchup=False,
    tags=["mlops", "training"],
) as dag:

    # ======================================================
    # START / END
    # ======================================================
    start = EmptyOperator(task_id="start")
    end = EmptyOperator(task_id="end")

    # ======================================================
    # DATA PIPELINE
    # ======================================================
    def load_data():
        logger.info("Loading raw data...")
        df = pd.read_csv("/app/data/raw/X_train_update.csv")
        logger.info(f"Loaded {len(df)} rows")

    def preprocess_data():
        logger.info("Preprocessing data...")
        # 👉 brancher ton clean_text ici si besoin
        pass

    def split_data():
        logger.info("Splitting dataset...")
        df = pd.read_csv("/app/data/processed/train_clean.csv")
        logger.info(f"Dataset ready: {len(df)} rows")

    with TaskGroup("data_pipeline") as data_pipeline:

        load = PythonOperator(
            task_id="load_data",
            python_callable=load_data,
        )

        preprocess = PythonOperator(
            task_id="preprocess_data",
            python_callable=preprocess_data,
        )

        split = PythonOperator(
            task_id="split_data",
            python_callable=split_data,
        )

        load >> preprocess >> split

    # ======================================================
    # TRAINING (via Gateway)
    # ======================================================
    with TaskGroup("training") as training:

        train_text = SimpleHttpOperator(
            task_id="train_text",
            http_conn_id=GATEWAY_CONN_ID,
            endpoint="/train/text",
            method="POST",
            headers=AUTH_HEADER,
            log_response=True,
        )

        train_image = SimpleHttpOperator(
            task_id="train_image",
            http_conn_id=GATEWAY_CONN_ID,
            endpoint="/train/image",
            method="POST",
            headers=AUTH_HEADER,
            log_response=True,
        )

        # parallèle
        [train_text, train_image]

    # ======================================================
    # EVALUATION
    # ======================================================
    def evaluate_models():
        logger.info("Evaluating models...")
        # 👉 brancher MLflow plus tard
        return {"status": "ok"}

    evaluate = PythonOperator(
        task_id="evaluate",
        python_callable=evaluate_models,
    )

    # ======================================================
    # REGISTER
    # ======================================================
    def register_models():
        logger.info("Registering models...")
        return {"status": "registered"}

    register = PythonOperator(
        task_id="register",
        python_callable=register_models,
    )

    # ======================================================
    # RELOAD MODELS (via Gateway)
    # ======================================================
    with TaskGroup("reload") as reload_group:

        reload_text = SimpleHttpOperator(
            task_id="reload_text",
            http_conn_id=GATEWAY_CONN_ID,
            endpoint="/reload/text",
            method="POST",
            headers=AUTH_HEADER,
            log_response=True,
        )

        reload_image = SimpleHttpOperator(
            task_id="reload_image",
            http_conn_id=GATEWAY_CONN_ID,
            endpoint="/reload/image",
            method="POST",
            headers=AUTH_HEADER,
            log_response=True,
        )

        [reload_text, reload_image]

    # ======================================================
    # FLOW
    # ======================================================
    start >> data_pipeline >> training >> evaluate >> register >> reload_group >> end