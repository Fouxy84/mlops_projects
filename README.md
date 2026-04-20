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
- `POST /reload/svm` ou `POST /reload/text`
- `POST /reload/cnn` ou `POST /reload/image`
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

Les modèles sont chargés depuis DagsHub / MLflow, sans fallback local, pour garder le versioning et permettre un rollback.

Priorité de sélection du modèle:

1. `MLFLOW_MODEL_URI`
2. `MLFLOW_MODEL_VERSION`
3. `MLFLOW_MODEL_ALIAS`
4. `MLFLOW_MODEL_STAGE` (`Production` par défaut)

### Texte

Modèle MLflow par défaut:

- `Text_Classifier_SVM`

Variables `.env` possibles via Docker Compose:

- `TEXT_MLFLOW_MODEL_VERSION=3`
- `TEXT_MLFLOW_MODEL_STAGE=Production`
- `TEXT_MLFLOW_MODEL_URI=models:/Text_Classifier_SVM/3`
- `TEXT_MLFLOW_VECTORIZER_ARTIFACT_PATH=preprocessing/tfidf.joblib`

Le modèle texte enregistré dans MLflow est le classifieur SVM. L'API charge aussi le vectorizer TF-IDF depuis les artefacts MLflow du même run, sinon le SVM reçoit du texte brut et renvoie une erreur du type `could not convert string to float`.

### Image

Modèle MLflow par défaut:

- `CNN_Image_Classifier`

Variables `.env` possibles via Docker Compose:

- `IMAGE_MLFLOW_MODEL_VERSION=2`
- `IMAGE_MLFLOW_MODEL_STAGE=Production`
- `IMAGE_MLFLOW_MODEL_URI=models:/CNN_Image_Classifier/2`

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

### Utiliser Grafana

1. Démarrer la stack:

```powershell
docker compose up -d --build
```

2. Ouvrir Grafana:

```text
http://localhost:3000
```

3. Se connecter avec `admin / admin`.

4. Aller dans `Connections` puis `Data sources` et vérifier que `Prometheus` est présent.

5. Aller dans `Explore`, choisir la datasource `Prometheus`, puis tester:

```promql
up
```

6. Créer un dashboard:

- `Dashboards`
- `New`
- `New dashboard`
- `Add visualization`
- datasource `Prometheus`
- coller une requête PromQL
- `Run queries`
- choisir le type de panel: `Time series`, `Stat`, `Table`, `Bar gauge`
- `Apply`
- `Save dashboard`

### Panels Prometheus recommandés

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

### Monitoring du drift

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

### Démo monitoring

1. Ouvrir Swagger gateway: `http://localhost:8000/docs`.
2. Faire `POST /login` avec `admin/admin`.
3. Lancer plusieurs prédictions:

```text
POST /predict/svm
POST /predict/cnn
POST /predict/multimodal
```

4. Ouvrir Grafana: `http://localhost:3000`.
5. Dans `Explore`, tester les requêtes PromQL ci-dessus.
6. Créer un dashboard avec au minimum:

- santé des services
- trafic gateway
- erreurs gateway
- volume de prédictions par modèle
- latence p95 des prédictions
- lancements de training

## Lancement local

### Variables d’environnement

Créer un fichier `.env` à la racine:

```env
DAGSHUB_USER=Fouxy84
DAGSHUB_TOKEN=xxx
GIT_REPO_URL=https://github.com/Fouxy84/mlops_projects.git
DAGSHUB_REPO_URL=https://dagshub.com/Fouxy84/mlops_projects
PROJECT_ROOT_HOST=c:/Users/coach/Desktop/datascientest/Projet DATASCIENTEST/projet_MLops/mlops_projects

# optionnel: forcer une version MLflow précise
TEXT_MLFLOW_MODEL_VERSION=
IMAGE_MLFLOW_MODEL_VERSION=
TEXT_MLFLOW_VECTORIZER_ARTIFACT_PATH=preprocessing/tfidf.joblib
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

- versionner les données avec DVC
- suivre les runs MLflow
- centraliser les modèles

### Mettre à jour les artefacts DVC

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

### Relancer un entraînement

Depuis Swagger:

- `POST /train/svm`
- `POST /train/cnn`

Puis:

- `POST /reload/svm`
- `POST /reload/cnn`

## Procédure optionnelle - Si la prod est cassée

Deux stratégies peuvent être appliquées selon le niveau d’urgence.

### Cas 1. Reprendre une expérience DagsHub datant d’il y a 7 jours

Objectif:

- restaurer rapidement des modèles déjà entraînés
- repartir d’un état connu sans refaire tout le pipeline

Principe:

- retrouver un commit Git cohérent datant d’environ 7 jours
- restaurer les pointeurs DVC de ce commit
- récupérer les artefacts correspondants depuis DagsHub
- recharger les modèles dans les APIs

Étapes:

1. retrouver un commit de référence datant d’environ 7 jours:

```powershell
git log --since="10 days ago" --until="7 days ago" --oneline
```

2. créer une branche de reprise:

```powershell
git checkout -b rollback-prod-7j <SHA_COMMIT>
```

3. restaurer les données versionnées:

```powershell
dvc pull data/raw.dvc data/processed.dvc
dvc checkout
```

4. relancer les services utiles:

```powershell
docker compose up -d --build gateway predict-text-api predict-image-api training-api
```

5. se connecter sur Swagger du gateway:

- `POST /login` avec `admin/admin`

6. recharger les modèles en production locale:

- `POST /reload/svm`
- `POST /reload/cnn`

7. vérifier:

- `GET /info`
- `POST /predict/svm`
- `POST /predict/cnn`
- `POST /predict/multimodal`

Usage recommandé:

- si l’objectif est de remettre rapidement un service stable
- si les modèles d’il y a 7 jours sont déjà validés

### Cas 2. Refaire entièrement l’entraînement des 2 modèles avec des données d’il y a 14 jours

Objectif:

- rejouer complètement la chaîne d’entraînement
- reconstruire les artefacts à partir d’un snapshot de données plus ancien

Principe:

- revenir au repo et aux pointeurs DVC d’environ 14 jours
- récupérer les données correspondantes via DVC
- relancer le training des 2 modèles
- recharger les modèles dans les APIs

Étapes:

1. retrouver un commit de référence datant d’environ 14 jours:

```powershell
git log --since="17 days ago" --until="14 days ago" --oneline
```

2. créer une branche dédiée:

```powershell
git checkout -b retrain-prod-14j <SHA_COMMIT>
```

3. restaurer les données de cette période:

```powershell
dvc pull data/raw.dvc data/processed.dvc
dvc checkout
```

4. relancer la stack:

```powershell
docker compose up -d --build gateway training-api predict-text-api predict-image-api airflow
```

5. choisir un mode de relance:

Option A - via Swagger du gateway:

- `POST /login` avec `admin/admin`
- `POST /train/svm`
- `POST /train/cnn`
- `POST /reload/svm`
- `POST /reload/cnn`

Option B - via Airflow:

- ouvrir `http://localhost:8080`
- lancer le DAG `mlops_orchestration`
- laisser tourner:
  - `dvc_pull_artifacts`
  - `train_svm`
  - `train_cnn`
  - `reload_svm`
  - `reload_cnn`

6. vérifier que les runs sont remontés dans DagsHub / MLflow:

- `https://dagshub.com/Fouxy84/mlops_projects`
- `https://dagshub.com/Fouxy84/mlops_projects.mlflow`

7. valider le résultat via les endpoints:

- `GET /info`
- `POST /predict/svm`
- `POST /predict/cnn`
- `POST /predict/multimodal`

Usage recommandé:

- si tu veux reconstruire complètement les modèles
- si tu soupçonnes une corruption ou une dérive récente des données ou modèles

### Choix rapide

Utiliser le cas 1 si:

- il faut restaurer vite
- tu fais confiance aux modèles déjà entraînés

Utiliser le cas 2 si:

- il faut recalculer proprement toute la chaîne
- tu veux repartir d’un historique de données plus ancien et stable

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

## Options d'evolution

Le dossier `options/` propose deux evolutions possibles pour ouvrir la reflexion vers un projet plus complet, sans remplacer la stack de reference basee sur `docker-compose.yml`.

### Option 1 - Interface Streamlit

Dossier: [options/option_1_streamlit_interface/](./options/option_1_streamlit_interface/)

Cette option ajoute une interface metier legere qui consomme uniquement le gateway existant.

Ce que cela apporte:

- une interface plus simple que Swagger pour la demo
- une experience utilisateur plus accessible pour la prediction texte, image et multimodale
- aucun changement structurel sur les APIs existantes

Ce que cela ne change pas:

- le gateway reste le point d'entree principal
- Docker Compose reste le mode de lancement de reference
- la securite et la logique MLOps actuelles restent identiques

### Option 2 - Scalabilite avec K3s

Dossier: [options/option_2_k3s_scalability/](./options/option_2_k3s_scalability/)

Cette option prepare une migration progressive vers Kubernetes en choisissant `K3s`, plus leger qu'un cluster Kubernetes complet et plus adapte a un petit projet ou une soutenance.

Ce que cela apporte:

- replication plus simple des APIs
- base pour l'auto-healing et le scaling horizontal
- exposition centralisee via Ingress
- possibilite d'ajouter Streamlit comme front metier dans une architecture plus industrielle

Ce que cela ne change pas:

- la stack actuelle reste la reference pour la demo, la CI et le developpement
- K3s est une projection d'evolution, pas un remplacement impose

### Positionnement recommande

Utiliser l'option Streamlit si l'objectif est d'ameliorer l'experience de demo sans complexifier le projet.

Utiliser l'option K3s si l'objectif est de montrer qu'une evolution vers une architecture plus scalable est deja pensee, tout en gardant une cible legere et realiste.
