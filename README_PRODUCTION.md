# Services

Ce dépôt a été recentré sur la stack suivante:

- `gateway` comme point d’entrée
- `predict-text-api` pour le modèle texte `TF-IDF + Linear SVM`
- `predict-image-api` pour le modèle image `CNN`
- `training-api` pour le réentraînement avec - `Airflow + DockerOperator + DVC`
- `Prometheus + Grafana` pour le monitoring
- `DagsHub / MLflow` pour le versionning et le tracking
- `streamlit-ui` pour l'interface de démonstration (option)

```text
[ Client / Swagger ]
        |
        v
[ Streamlit UI ]
        |
        v
    [ Gateway ] <----> [ Auth API ]
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
## Architecture

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
│   ├── common/
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

## Services exposés

Avec le `docker-compose.yml` principal:
```powershell
docker-compose up -d --build
```

- `gateway`: `http://localhost:8000`
- `predict-text-api`: `http://localhost:8001`
- `training-api`: `http://localhost:8002`
- `auth-api`: `http://localhost:8003`
- `predict-image-api`: `http://localhost:8004`
- `mlflow`: `http://localhost:5000`
- `airflow`: `http://localhost:8080`
- `prometheus`: `http://localhost:9090`
- `grafana`: `http://localhost:3000`

Avec Streamlit (surcharge optionnelle):
- `streamlit-ui`: `http://localhost:8501`

```powershell
docker compose -f docker-compose.yml -f options/option_1_streamlit_interface/docker-compose.streamlit.yml up -d --build
```

### Gateway

Fichier principal: [gateway/gateway_main.py](./gateway/gateway_main.py)

Le gateway garde uniquement les endpoints utiles.

#### Authentification

Le gateway fonctionne en session mémoire simple pour la démo:

- `admin / admin` -> accès à tout
- `user / user` -> prédiction uniquement

Endpoints:

- `POST /login`
- `POST /logout`
- `GET /me`

#### Prédiction

- `POST /predict/svm`
- `POST /predict/cnn`
- `POST /predict/multimodal`

#### Admin uniquement

- `POST /orchestrate/train/svm`
- `POST /orchestrate/train/cnn`
- `POST /orchestrate/retrain/svm`
- `POST /orchestrate/retrain/cnn`
- `GET /orchestrate/status/{dag_run_id}`
- `POST /reload/svm`
- `POST /reload/cnn`
- `GET /data/check-updates`
- `POST /data/check-updates/baseline`
- `POST /data/check-updates/retrain`

#### Consultation

- `GET /health`
- `GET /metrics`
- `GET /info`
- `GET /`

### APIs de prédiction

Fichier principal: [src/inference/main.py](./src/inference/main.py)

Les deux conteneurs utilisent le même code avec une variable d’environnement:

- `MODEL_TYPE=svm`
- `MODEL_TYPE=cnn`

Les modèles sont chargés depuis DagsHub / MLflow, sans fallback local, pour garder le versioning et permettre un rollback.

Priorité de sélection du modèle:

1. `MLFLOW_MODEL_URI`
2. `MLFLOW_MODEL_VERSION`
3. `MLFLOW_MODEL_ALIAS`
4. `MLFLOW_MODEL_STAGE` (`Production` par défaut)

#### Texte

Modèle MLflow par défaut:

- `Text_Classifier_SVM`

Variables `.env` possibles via Docker Compose:

- `TEXT_MLFLOW_MODEL_VERSION=3`
- `TEXT_MLFLOW_MODEL_STAGE=Production`
- `TEXT_MLFLOW_MODEL_URI=models:/Text_Classifier_SVM/3`
- `TEXT_MLFLOW_VECTORIZER_ARTIFACT_PATH=preprocessing/tfidf.joblib`

Le modèle texte enregistré dans MLflow est le classifieur SVM. L'API charge aussi le vectorizer TF-IDF depuis les artefacts MLflow du même run, sinon le SVM reçoit du texte brut et renvoie une erreur du type `could not convert string to float`.

#### Image

Modèle MLflow par défaut:

- `CNN_Image_Classifier`

Variables `.env` possibles via Docker Compose:

- `IMAGE_MLFLOW_MODEL_VERSION=2`
- `IMAGE_MLFLOW_MODEL_STAGE=Production`
- `IMAGE_MLFLOW_MODEL_URI=models:/CNN_Image_Classifier/2`

### Training

Fichier principal: [src/training/main.py](./src/training/main.py)

Endpoints:

- `GET /health`
- `GET /metrics`
- `POST /train/svm`
- `POST /train/cnn`

Le training envoie les runs et artefacts vers DagsHub / MLflow si les variables sont présentes.

### Airflow + DVC

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

### Monitoring

Prometheus collecte les métriques exposées par les APIs, puis Grafana les affiche sous forme de dashboards.

Prometheus scrape:

- `gateway`
- `predict-text-api`
- `predict-image-api`
- `training-api`

Fichiers:

- [monitoring/prometheus.yml](./monitoring/prometheus.yml)
- [monitoring/grafana/provisioning/datasources/prometheus.yml](./monitoring/grafana/provisioning/datasources/prometheus.yml)

La datasource Grafana est provisionnée automatiquement:

- nom: `Prometheus`
- URL interne Docker: `http://prometheus:9090`
- accès local Grafana: `http://localhost:3000`
- identifiants par défaut: `admin / admin`

#### Utiliser Grafana

1. Ouvrir Grafana:

```text
http://localhost:3000
```

2. Se connecter avec `admin / admin`.

4. Aller dans `Dashboards` puis choisir `MLOps pipeline Monitoring`

#### Panels Prometheus recommandés

Santé des services:

```promql
up{job=~"gateway|predict_text_api|predict_image_api|training_api"}
```

Trafic gateway par endpoint:

```promql
sum by (path, status) (rate(mlops_gateway_requests_total[5m]))
```

Erreurs gateway:

```promql
sum by (path, status) (rate(mlops_gateway_requests_total{status=~"4..|5.."}[5m]))
```

Latence p95 du gateway:

```promql
histogram_quantile(
  0.95,
  sum by (le, path) (rate(mlops_gateway_request_duration_seconds_bucket[5m]))
)
```

Volume de prédictions par modèle:

```promql
sum by (model_type) (rate(mlops_predictions_total[5m]))
```

Latence p95 des prédictions:

```promql
histogram_quantile(
  0.95,
  sum by (le, model_type) (rate(mlops_prediction_duration_seconds_bucket[5m]))
)
```

Erreurs des APIs de prédiction:

```promql
sum by (model_type, status) (
  rate(mlops_inference_requests_total{status=~"4..|5.."}[5m])
)
```

Lancements de training sur 24h:

```promql
increase(mlops_training_runs_total[24h])
```

#### Monitoring du drift

Dans cette stack, le drift est surveillé à deux niveaux.

Drift statistique avec Evidently:

Le script [monitoring/check_data_drift.py](./monitoring/check_data_drift.py) récupère les données depuis DagsHub avec DVC, puis compare un dataset de référence et un dataset courant avec Evidently.

Par défaut:

- repo DagsHub: `https://dagshub.com/Fouxy84/mlops_projects`
- référence DVC: `data/raw/X_train_update.csv`
- courant DVC: `data/raw_test/X_test_update.csv`
- cache local temporaire: `monitoring/dagshub_data/`
- sorties: `monitoring/reports/data_drift.html`, `monitoring/reports/data_drift.json`, `monitoring/reports/data_drift_status.json`

Installation si besoin:

```powershell
pip install evidently "dvc[s3]"
```

Variables nécessaires pour accéder au remote DagsHub / DVC:

```env
DAGSHUB_USER=Fouxy84
DAGSHUB_TOKEN=xxx
DAGSHUB_REPO_URL=https://dagshub.com/Fouxy84/mlops_projects
```

Lancer le check:

```powershell
python monitoring/check_data_drift.py
```

Forcer un échec de pipeline si Evidently détecte un drift dataset:

```powershell
python monitoring/check_data_drift.py --fail-on-drift
```

Comparer deux fichiers spécifiques:

```powershell
python monitoring/check_data_drift.py `
  --reference data/raw/X_train_update.csv `
  --current data/raw_test/X_test_update.csv
```

Lire une version précise des données DagsHub:

```powershell
python monitoring/check_data_drift.py --dagshub-rev <SHA_COMMIT_OU_TAG>
```

Utiliser les fichiers locaux sans télécharger depuis DagsHub:

```powershell
python monitoring/check_data_drift.py --data-source local
```

Ajouter des colonnes source au rapport, en plus des variables d'état dérivées:

```powershell
python monitoring/check_data_drift.py --columns designation,description
```

Le script génère des variables d'état simples pour éviter de comparer directement les IDs ou les images:

- longueur de `designation`
- longueur de `description`
- présence ou absence de `description`
- longueur texte combinée
- label si disponible

Ouvrir le rapport HTML:

```powershell
start monitoring/reports/data_drift.html
```

Drift opérationnel visible dans Grafana:

- hausse anormale du trafic sur `/predict/svm`, `/predict/cnn` ou `/predict/multimodal`
- hausse des erreurs `4xx` ou `5xx`
- hausse de la latence de prédiction
- déséquilibre entre les volumes texte et image
- relances fréquentes de training

Exemple de signal de drift de trafic:

```promql
sum by (model_type) (rate(mlops_predictions_total[1h]))
```

Comparaison avec la même fenêtre 7 jours avant:

```promql
sum by (model_type) (rate(mlops_predictions_total[1h]))
/
sum by (model_type) (rate(mlops_predictions_total[1h] offset 7d))
```

Drift de données via le gateway:

```text
GET /data/check-updates
POST /data/check-updates/baseline
POST /data/check-updates/retrain
```

Usage:

1. Après un jeu de données de référence, appeler `POST /data/check-updates/baseline`.
2. Quand de nouvelles données arrivent dans `data/raw`, appeler `GET /data/check-updates`.
3. Si `has_new_files=true`, le gateway indique les nouveaux fichiers détectés.
4. Pour relancer automatiquement le training adapté:

```text
POST /data/check-updates/retrain
```

Ce monitoring détecte l'arrivée de nouvelles données et les symptômes de drift côté production. Le script Evidently complète ce suivi avec un rapport statistique offline. Pour l'intégrer dans Grafana, il faut ensuite exposer le résultat du script sous forme de métrique Prometheus.

Métrique recommandée à ajouter ensuite:

```text
mlops_data_drift_detected{dataset="raw_test"}
mlops_prediction_label_total{model_type, predicted_label}
```

Exemple de panel une fois cette métrique ajoutée:

```promql
mlops_data_drift_detected
sum by (model_type, predicted_label) (rate(mlops_prediction_label_total[1h]))
```

### DagsHub

DagsHub est utilisé pour:

- versionner les données avec DVC
- suivre les runs MLflow
- centraliser les modèles

#### Mettre à jour les artefacts DVC

```powershell
dvc status
dvc add data/raw
dvc add data/processed
git add data .dvc .gitignore
git commit -m "Update DVC tracked data"
dvc push
git push origin master
```

Les modèles servis par les APIs de prédiction viennent de MLflow. Pour revenir à une version précédente, utiliser `TEXT_MLFLOW_MODEL_VERSION`, `IMAGE_MLFLOW_MODEL_VERSION` ou un `MLFLOW_MODEL_URI`.

#### Relancer un entraînement

Depuis Swagger:

- `POST /orchestrate/train/svm`
- `POST /orchestrate/train/cnn`

Puis:

- `POST /reload/svm`
- `POST /reload/cnn`

