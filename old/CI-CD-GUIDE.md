# CI/CD MLOPS GUIDE
# Pipeline Complet : Code → Tests → Build → Deploy

## 🔄 ARCHITECTURE CI/CD GLOBALE

```
┌─────────────────────────────────────────────────────────────┐
│                   DÉVELOPPEUR                               │
│         (Push code sur GitHub/GitLab)                       │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ↓
        ┌────────────────────────────┐
        │  GITHUB ACTIONS / GITLAB CI│ ← CI (Continuous Integration)
        │  1. Tests (pytest)         │
        │  2. Lint (pylint)          │
        │  3. Build images           │
        │  4. Push registry          │
        └────────────┬───────────────┘
                     │
        ✓ Tous tests passent?
                     │
                     ↓
        ┌────────────────────────────┐
        │   AIRFLOW ORCHESTRATION    │ ← Scheduling automática
        │ (Déclenche entraînement)   │
        │  • Préprocessing           │
        │  • Training SVM            │
        │  • Training CNN            │
        │  • Evaluation              │
        └────────────┬───────────────┘
                     │
                     ↓
        ┌────────────────────────────┐
        │   MLFLOW TRACKING          │
        │ • Métriques enregistrées   │
        │ • Modèles versionnés       │
        │ • Artifacts archivés       │
        └────────────┬───────────────┘
                     │
        Modèle meilleur que l'ancien?
                     │
                     ↓
        ┌────────────────────────────────┐
        │  KUBERNETES DEPLOYMENT (CD)    │ ← CD (Continuous Deployment)
        │  1. Mise à jour image          │
        │  2. Rolling update pods        │
        │  3. Health checks              │
        │  4. Smoke tests                │
        └────────────────────────────────┘
                     │
                     ↓
        ┌────────────────────────────────┐
        │  MONITORING & ALERTING         │
        │  • Prometheus + Grafana        │
        │  • PagerDuty/Slack alerts      │
        │  • Performance tracking        │
        └────────────────────────────────┘
```

---

## 📋 ÉTAPES DU PIPELINE CI/CD

### **PHASE 1 : CI (Continuous Integration) - Tests & Build**

```yaml
# .github/workflows/ci-pipeline.yml
name: CI Pipeline

on:
  push:
    branches: [main, develop]
    paths:
      - 'src/**'
      - 'tests/**'
      - '*.py'

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      # 1. Tests unitaires
      - name: Run Tests
        run: |
          pip install pytest pytest-cov
          pytest tests/ --cov=src --cov-report=xml
      
      # 2. Lint & Code Quality
      - name: Lint Code
        run: |
          pip install pylint
          pylint src/
      
      # 3. Build images Docker
      - name: Build Docker Images
        run: docker-compose build --no-cache
      
      # 4. Push vers registre (DockerHub/ECR/GCR)
      - name: Push to Registry
        run: |
          docker tag mlops_gateway:latest myregistry/gateway:latest
          docker push myregistry/gateway:latest
```

---

### **PHASE 2 : Airflow Orchestration - Entraînement Automatique**

**Quand : Chaque nuit à 2h du matin (cron: 0 2 * * *)**

```python
# airflow/dags/mlops_training_pipeline.py

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator

default_args = {
    'start_date': datetime(2024, 1, 1),
    'retries': 2,
}

dag = DAG(
    'mlops_training_pipeline',
    default_args=default_args,
    schedule_interval='0 2 * * *',  # Chaque jour à 2h du matin
)

# Task 1: Charger données
load_data = PythonOperator(
    task_id='load_data',
    python_callable=load_training_data,
    dag=dag,
)

# Task 2: Prétraiter
preprocess = PythonOperator(
    task_id='preprocess',
    python_callable=preprocess_data,
    upstream_list=[load_data],
    dag=dag,
)

# Task 3: Entraîner SVM + CNN en parallèle
train_svm = PythonOperator(
    task_id='train_svm',
    python_callable=train_svm_model,
    upstream_list=[preprocess],
    dag=dag,
)

train_cnn = PythonOperator(
    task_id='train_cnn',
    python_callable=train_cnn_model,
    upstream_list=[preprocess],
    dag=dag,
)

# Task 4: Évaluer modèles
evaluate = PythonOperator(
    task_id='evaluate_models',
    python_callable=evaluate_models,
    upstream_list=[train_svm, train_cnn],
    dag=dag,
)

# Task 5: Si meilleur que baseline → enregistrer
register_models = PythonOperator(
    task_id='register_models',
    python_callable=register_to_mlflow,
    upstream_list=[evaluate],
    dag=dag,
)

# Définir dépendances
load_data >> preprocess >> [train_svm, train_cnn] >> evaluate >> register_models
```

---

### **PHASE 3 : CD (Continuous Deployment) - Déploiement K8s**

**Déclenché quand : Nouveau modèle en production dans MLflow**

```yaml
# .github/workflows/deploy-k8s.yml
name: Deploy to Kubernetes

on:
  workflow_run:
    workflows: [CI Pipeline]
    types: [completed]

jobs:
  deploy:
    if: ${{ github.event.workflow_run.conclusion == 'success' }}
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      # 1. Pull des images depuis registre
      - name: Pull Docker Images
        run: |
          docker pull myregistry/gateway:latest
          docker pull myregistry/inference:latest
      
      # 2. Push vers Docker Desktop K8s
      - name: Load Images to K8s
        run: |
          kind load docker-image myregistry/gateway:latest
          kind load docker-image myregistry/inference:latest
      
      # 3. Déployer sur K8s
      - name: Deploy to Kubernetes
        run: |
          kubectl apply -f k8s/
          kubectl rollout status deployment/inference -n mlops
      
      # 4. Tests de santé (Smoke Tests)
      - name: Health Checks
        run: |
          kubectl get pods -n mlops
          curl http://localhost:8000/health
          curl http://localhost:8001/health
      
      # 5. Alerter en cas d'erreur
      - name: Notify on Slack
        if: failure()
        run: |
          curl -X POST -H 'Content-type: application/json' \
            --data '{"text":"Deployment failed!"}' \
            ${{ secrets.SLACK_WEBHOOK }}
```

---

## 🔄 FLUX COMPLET : EXEMPLE RÉEL

### **Scénario : Un dev améliore l'accuracy du CNN**

```
JOUR 1 - 16:00
  Dev améliore le code du CNN
  → git push origin improve-cnn-accuracy

JOUR 1 - 16:05
  GitHub Actions déclenché
  ✓ pytest tests/test_model_training2.py PASS
  ✓ pylint src/ PASS
  ✓ docker-compose build PASS
  ✓ Images poussées vers registry PASS
  → PR Approved & Merged to main

JOUR 2 - 02:00 (Nuit)
  Airflow déclenche le DAG 'mlops_training_pipeline'
  ✓ Charge données (train_clean.csv)
  ✓ Prétraite données
  ✓ Entraîne SVM (nouveaux params) - accuracy: 0.92
  ✓ Entraîne CNN (nouvelle architecture) - accuracy: 0.95 ⭐ MEILLEUR!
  → Évalue vs modèle en prod (0.91)
  → 0.95 > 0.91 ? OUI!
  → Enregistre dans MLflow avec tag "production"

JOUR 2 - 02:30
  GitHub Actions déclenché
  
  ✓ Récupère nouvelle image de registre
  ✓ Déploie sur K8s
  ✓ Rolling update inference pods
    - Pod 1: Stop ancien → Start nouveau ✓
    - Pod 2: Stop ancien → Start nouveau ✓
  ✓ Health checks: 200 OK
  ✓ Smoke tests: Prédiction fonctionne ✓

JOUR 2 - 02:35
  Utilisateurs commencent à utiliser le nouveau modèle
  Automatiquement avec 95% d'accuracy! 🎉
  
MONITORING EN TEMPS RÉEL
  Grafana affiche:
  - Latence des requêtes
  - Taux d'erreurs: 0%
  - Utilisation CPU: 45%
```

---

## 🎯 VARIABLES D'ENVIRONNEMENT / SECRETS CI/CD

```bash
# GitHub Secrets (pour .github/workflows/)
REGISTRY_USERNAME=coach
REGISTRY_PASSWORD=xxx
SLACK_WEBHOOK=https://hooks.slack.com/...
KUBERNETES_CONFIG=base64-encoded-kubeconfig
MLflow_TRACKING_URI=http://mlflow:5000

# Airflow Variables (pour DAGs)
DATA_PATH=/data/raw
MODELS_PATH=/models
MIN_ACCURACY=0.90  # Ne déployer que si accuracy >= 90%
```

---

## 📊 STATUS CHECKS / GATING

Avant déploiement en production:

```python
# mlflow/model_registry.py

def should_promote_to_production(new_model_metrics):
    """
    Décider si le nouveau modèle doit remplacer l'ancien
    """
    
    # 1. Comparaison vs modèle en prod
    prod_model = mlflow.pyfunc.load_model("models:/cnn/production")
    prod_metrics = mlflow.get_run(prod_model.run_id).data.metrics
    
    # 2. Tests de régression
    if new_model_metrics['accuracy'] < prod_metrics['accuracy']:
        return False, "Accuracy decreased"
    
    # 3. Tests de latence
    if new_model_metrics['latency_p95'] > 200:  # ms
        return False, "Latency too high"
    
    # 4. Tests de robustesse
    if new_model_metrics['drift_score'] > 0.8:
        return False, "Data drift detected"
    
    # 5. Tous les checks passent
    return True, "Ready for production"
```

---

## 🚨 MONITORING CONTINU POST-DÉPLOIEMENT

```yaml
# Alertes Grafana/Prometheus

Alertes:
  - ModelAccuracyDrop:
      condition: current_accuracy < previous_accuracy * 0.95
      severity: CRITICAL
      action: Rollback à ancien modèle
  
  - HighLatency:
      condition: p95_latency > 500ms
      severity: WARNING
      action: Scale up pods
  
  - OutOfMemory:
      condition: memory_usage > 90%
      severity: CRITICAL
      action: Restart pod
```

---

## 📈 MÉTRIQUES À TRACKER

```
Performance Metrics:
  - Model accuracy (train/test)
  - Precision, Recall, F1-score
  - Latency (p50, p95, p99)
  - Throughput (requêtes/sec)

Business Metrics:
  - Prédictions correctes
  - Taux de confiance moyen
  - Erreurs non détectées

Système Metrics:
  - CPU/Memory usage
  - Network I/O
  - Error rates
  - Pod restart count
```

---

## ✅ CHECKLIST DÉPLOIEMENT

```
Avant de déployer en production:

☐ Code review & tests PASS
☐ Image Docker buildée sans erreurs
☐ Health checks OK
☐ Modèle evaluation PASS
☐ Accuracy >= threshold
☐ Latency acceptable
☐ Pas de data drift
☐ Logs configurés
☐ Monitoring actif
☐ Team notifiée
☐ Rollback plan prêt
```

---

## 🎓 CONCLUSION: CI/CD EN 3 PHASES

1. **CI** (GitHub Actions)
   - Tests + Lint + Build images
   - Rapide (< 10 min)

2. **Orchestration** (Airflow)
   - Entraîne modèles la nuit
   - Évalue & enregistre dans MLflow
   - Peut prendre heures

3. **CD** (Kubernetes)
   - Déploie nouveau modèle si meilleur
   - Monitore en temps réel
   - Rollback automatique en cas d'erreur
