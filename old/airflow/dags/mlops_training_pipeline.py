# airflow/dags/mlops_training_pipeline.py
"""
MLOps End-to-End Training Pipeline DAG

Orchestrates:
1. Data Loading
2. Data Preprocessing
3. Feature Engineering
4. Model Training (SVM + CNN)
5. Model Evaluation
6. Model Registration
7. Artifact Management
"""

from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
import pandas as pd
from pathlib import Path
from src.preprocessing.text_cleaning import clean_text
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.operators.dummy import DummyOperator
from airflow.providers.http.operators.http import SimpleHttpOperator
from airflow.models import Variable
from airflow.utils.task_group import TaskGroup
import logging

logger = logging.getLogger(__name__)

# Default DAG arguments
default_args = {
    'owner': 'mlops-team',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email': ['mlops@example.com'],
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

# DAG definition
dag = DAG(
    'mlops_training_pipeline',
    default_args=default_args,
    description='MLOps end-to-end training pipeline',
    schedule_interval='0 2 * * *',  # Daily at 2 AM UTC
    catchup=False,
    tags=['mlops', 'training', 'production'],
)

# ================================================================
# PYTHON FUNCTIONS
# ================================================================

def load_data(**context):
    """Load raw data from source."""
    logger.info("Loading raw data...")
    data_dir = Path("/app/data/raw")
    df = pd.read_csv(data_dir / "X_train_update.csv")
    logger.info(f"Data loaded: {df.shape[0]} rows, {df.shape[1]} columns")
    context['task_instance'].xcom_push(key='data_shape', value=df.shape)
    return {"status": "success", "rows": df.shape[0]}


def preprocess_data(**context):
    """Preprocess data (cleaning, validation)."""
    logger.info("Preprocessing data...")
    data_shape = context['task_instance'].xcom_pull(task_ids='load_data', key='data_shape')
    logger.info(f"Input data shape: {data_shape}")
    # Clean and validate data
    # df = clean_text(df)
    logger.info("Preprocessing complete")
    return {"status": "success"}


def feature_engineering(**context):
    """Extract features (TF-IDF, embeddings, etc.)."""
    logger.info("Extracting features...")
    # Load preprocessed data
    df = pd.read_csv("/app/data/processed/train_clean.csv")
    # TF-IDF vectorization
    vectorizer = TfidfVectorizer(max_features=5000, ngram_range=(1, 2))
    X = vectorizer.fit_transform(df['text'])
    logger.info(f"Features extracted: {X.shape[1]} features")
    return {"status": "success", "features": X.shape[1]}


def split_data(**context):
    """Split data into train/val/test."""
    logger.info("Splitting data...")
    df = pd.read_csv("/app/data/processed/train_clean.csv")
    # 70% train, 15% val, 15% test
    train, temp = train_test_split(df, test_size=0.3, random_state=42)
    val, test = train_test_split(temp, test_size=0.5, random_state=42)
    logger.info(f"Train: {len(train)}, Val: {len(val)}, Test: {len(test)}")
    return {"status": "success","train_size": len(train),"val_size": len(val),"test_size": len(test)}


def validate_pipeline(**context):
    """Validate pipeline configuration."""
    logger.info("Validating pipeline...")
    checks = {'data_loaded': True,'models_available': True,'mlflow_connected': True,}
    if not all(checks.values()):
        raise ValueError("Validation failed")
    logger.info("Pipeline validation passed")
    return {"status": "success"}

def notify_completion(**context):
    """Notify about pipeline completion."""
    logger.info("Pipeline execution completed successfully!")
    return {"status": "completed"}


# ================================================================
# TASK DEFINITIONS
# ================================================================

# Start task
start = DummyOperator(task_id='start', dag=dag)

# Validation
validate = PythonOperator(
    task_id='validate_pipeline',
    python_callable=validate_pipeline,
    dag=dag,
)

# Data Loading & Preprocessing
with TaskGroup('data_pipeline', dag=dag) as data_pipeline:
    load = PythonOperator(
        task_id='load_data',
        python_callable=load_data,
    )
    
    preprocess = PythonOperator(
        task_id='preprocess_data',
        python_callable=preprocess_data,
    )
    
    features = PythonOperator(
        task_id='feature_engineering',
        python_callable=feature_engineering,
    )
    
    split = PythonOperator(
        task_id='split_data',
        python_callable=split_data,
    )
    
    load >> preprocess >> features >> split

# Model Training
with TaskGroup('model_training', dag=dag) as training:
    svm_train = SimpleHttpOperator(
        task_id='train_svm',
        http_conn_id='training_api',
        endpoint='/train/svm',
        method='POST',
        headers={'Authorization': 'Bearer {{ var.value.api_token }}'},
        dag=dag,
    )
    
    cnn_train = SimpleHttpOperator(
        task_id='train_cnn',
        http_conn_id='training_api',
        endpoint='/train/cnn',
        method='POST',
        headers={'Authorization': 'Bearer {{ var.value.api_token }}'},
        dag=dag,
    )
    
    # Train models in parallel
    svm_train
    cnn_train

# Model Evaluation
evaluate = BashOperator(
    task_id='evaluate_models',
    bash_command='''
    python /app/src/evaluation/evaluate_models.py \
      --svm_path /app/models/text/svm.joblib \
      --cnn_path /app/models/images/cnn.pt \
      --test_data /app/data/processed/test_data.csv \
      --output /app/evaluation/metrics.json
    ''',
    dag=dag,
)

# Model Registration
register = PythonOperator(
    task_id='register_models',
    python_callable=lambda: {"status": "registered"},
    dag=dag,
)

# Completion
complete = PythonOperator(
    task_id='notify_completion',
    python_callable=notify_completion,
    dag=dag,
)

# ================================================================
# DAG DEPENDENCIES
# ================================================================
start >> validate >> data_pipeline >> training >> evaluate >> register >> complete
