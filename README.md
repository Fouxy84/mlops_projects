# Projet MLOps - Rakuten Multimodal Classification

Ce dépôt a été recentré sur la stack réellement utilisée pour la démo et la CI:

- `gateway` comme point d’entrée
- `predict-text-api` pour le modèle texte `TF-IDF + Linear SVM`
- `predict-image-api` pour le modèle image `CNN`
- `training-api` pour le réentraînement
- `Airflow + DockerOperator + DVC`
- `Prometheus + Grafana`
- `DagsHub / MLflow` pour le versionning et le tracking

Les anciens composants et expérimentations ont été déplacés dans `old/`.

## Architecture

```text
[ Client / Swagger ]
        |
        v
    [ Gateway ]
     /   |    \
    /    |     \
   v     v      v
[Text API] [Image API] [Training API]
    \        /           |
     \      /            v
      +----/-------> [DagsHub / MLflow]
                        ^
                        |
                    [Airflow]
                        |
                        v
                 [DockerOperator]
                        |
                        v
                    [DVC Runner]

Monitoring:
Prometheus scrape gateway + APIs
Grafana visualise les métriques
```

## Structure utile

```text
mlops_projects/
├── airflow/
│   ├── dags/
│   │   └── mlops_orchestration.py
│   ├── dvc/
│   │   └── Dockerfile
│   └── requirements.txt
├── data/
├── gateway/
│   ├── dockerfile
│   ├── gateway_main.py
│   └── requirements.txt
├── models/
├── monitoring/
│   ├── grafana/
│   └── prometheus.yml
├── old/
├── src/
│   ├── gateway/
│   ├── inference/
│   ├── mlflow/
│   ├── preprocessing/
│   ├── train_models/
│   └── training/
├── tests/
│   ├── conftest.py
│   ├── requirements_dev.txt
│   └── test_api_gateway.py
├── .github/workflows/ci.yml
├── docker-compose.yml
└── README.md
```

## Dossier `old`

Le dossier `old/` contient les éléments archivés mais non utilisés par la stack active:

- anciens DAGs Airflow
- ancienne API locale `api/`
- anciens manifests `k8s/`
- anciens fichiers de monitoring K8s
- ancienne app `streamlit/`
- anciens scripts PowerShell
- anciens tests et artefacts de tests
- ancienne documentation de production

## Services exposés

Avec le `docker-compose.yml` principal:

- `gateway`: `http://localhost:8000`
- `predict-text-api`: `http://localhost:8001`
- `training-api`: `http://localhost:8002`
- `auth-api`: `http://localhost:8003`
- `predict-image-api`: `http://localhost:8004`
- `mlflow`: `http://localhost:5000`
- `airflow`: `http://localhost:8080`
- `prometheus`: `http://localhost:9090`
- `grafana`: `http://localhost:3000`

## Gateway

Fichier principal: [gateway/gateway_main.py](./gateway/gateway_main.py)

Le gateway garde uniquement les endpoints utiles.

### Authentification

Le gateway fonctionne en session mémoire simple pour la démo:

- `admin / admin` -> accès à tout
- `user / user` -> prédiction uniquement

Endpoints:

- `POST /login`
- `POST /logout`
- `GET /me`

### Prédiction

- `POST /predict/svm`
- `POST /predict/cnn`
- `POST /predict/multimodal`

### Admin uniquement

- `POST /train/svm`
- `POST /train/cnn`
- `POST /reload/svm`
- `POST /reload/cnn`
- `GET /data/check-updates`
- `POST /data/check-updates/baseline`
- `POST /data/check-updates/retrain`

### Consultation

- `GET /health`
- `GET /metrics`
- `GET /info`
- `GET /`

## APIs de prédiction

Fichier principal: [src/inference/main.py](./src/inference/main.py)

Les deux conteneurs utilisent le même code avec une variable d’environnement:

- `MODEL_TYPE=svm`
- `MODEL_TYPE=cnn`

### Texte

Le service texte utilise:

- `models/text/tfidf.joblib`
- `models/text/svm.joblib`

avec fallback MLflow si besoin.

### Image

Le service image utilise:

- `models/images/cnn.pt`

avec fallback MLflow si besoin.

## Training

Fichier principal: [src/training/main.py](./src/training/main.py)

Endpoints:

- `GET /health`
- `GET /metrics`
- `POST /train/svm`
- `POST /train/cnn`

Le training envoie les runs et artefacts vers DagsHub / MLflow si les variables sont présentes.

## Airflow + DVC

Le DAG actif est: [airflow/dags/mlops_orchestration.py](./airflow/dags/mlops_orchestration.py)

Il orchestre:

1. `dvc pull` dans un conteneur dédié via `DockerOperator`
2. entraînement `svm`
3. entraînement `cnn`
4. reload des APIs

Le lien DVC / DockerOperator repose sur:

- [airflow/dags/mlops_orchestration.py](./airflow/dags/mlops_orchestration.py)
- [airflow/dvc/Dockerfile](./airflow/dvc/Dockerfile)
- `DVC_RUNNER_IMAGE` dans [docker-compose.yml](./docker-compose.yml)

## Monitoring

Prometheus scrape:

- `gateway`
- `predict-text-api`
- `predict-image-api`
- `training-api`

Fichiers:

- [monitoring/prometheus.yml](./monitoring/prometheus.yml)
- [monitoring/grafana/provisioning/datasources/prometheus.yml](./monitoring/grafana/provisioning/datasources/prometheus.yml)

Exemples de métriques à montrer dans Grafana:

```promql
sum by (path, status) (mlops_gateway_requests_total)
sum by (model_type) (mlops_predictions_total)
sum by (model_type) (mlops_training_runs_total)
```

## Lancement local

### Variables d’environnement

Créer un fichier `.env` à la racine:

```env
DAGSHUB_USER=Fouxy84
DAGSHUB_TOKEN=xxx
GIT_REPO_URL=https://github.com/Fouxy84/mlops_projects.git
DAGSHUB_REPO_URL=https://dagshub.com/Fouxy84/mlops_projects
PROJECT_ROOT_HOST=c:/Users/coach/Desktop/datascientest/Projet DATASCIENTEST/projet_MLops/mlops_projects
```

### Démarrage

```powershell
docker compose up --build -d
```

### Vérification

```powershell
docker compose ps
docker compose logs gateway
docker compose logs predict-text-api
docker compose logs predict-image-api
docker compose logs training-api
```

## Démo Swagger

Ouvrir:

- Gateway Swagger: `http://localhost:8000/docs`
- Text API Swagger: `http://localhost:8001/docs`
- Training API Swagger: `http://localhost:8002/docs`
- Image API Swagger: `http://localhost:8004/docs`

### Séquence recommandée

1. `POST /login` avec `admin/admin`
2. `GET /me`
3. `POST /predict/svm`
4. `POST /predict/cnn`
5. `POST /predict/multimodal`
6. `GET /info`
7. `POST /data/check-updates/baseline`
8. `GET /data/check-updates`
9. `POST /train/svm`
10. `POST /reload/svm`
11. `POST /logout`

### Exemple texte

```json
{
  "text": "le tableau de chat est tres joli"
}
```

### Exemple image

```json
{
  "image_path": "image_528113_product_923222.jpg"
}
```

### Exemple multimodal

```json
{
  "text": "le tableau de chat est tres joli",
  "image_path": "image_528113_product_923222.jpg"
}
```

## DagsHub

DagsHub est utilisé pour:

- versionner les données et artefacts avec DVC
- suivre les runs MLflow
- centraliser les modèles

### Mettre à jour les artefacts DVC

```powershell
dvc status
dvc add data/raw
dvc add data/processed
dvc add models/text/svm.joblib
git add data models .dvc .gitignore
git commit -m "Update DVC tracked data and models"
dvc push
git push origin master
```

### Relancer un entraînement

Depuis Swagger:

- `POST /train/svm`
- `POST /train/cnn`

Puis:

- `POST /reload/svm`
- `POST /reload/cnn`

## CI/CD

Workflow: [.github/workflows/ci.yml](./.github/workflows/ci.yml)

Pipeline actuel:

1. tests unitaires
2. validation du DAG Airflow actif
3. build Docker
4. push DockerHub uniquement sur `push` vers `master`

Images construites:

- `mlops-gateway`
- `mlops-auth-api`
- `mlops-predict-text-api`
- `mlops-predict-image-api`
- `mlops-training-api`
- `mlops-mlflow`
- `mlops-dvc-runner`

## Tests

Tests actifs:

```powershell
python -m pytest tests -q
```

Validation Docker Compose:

```powershell
docker compose config
```

## Références

- GitHub: `https://github.com/Fouxy84/mlops_projects`
- DagsHub: `https://dagshub.com/Fouxy84/mlops_projects`
