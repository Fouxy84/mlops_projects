# Projet MLOps - Rakuten Multimodal Classification

Ce projet met en place une architecture MLOps pour classifier des produits Rakuten à partir du texte et des images, avec deux modèles séparés:

- un modèle texte `TF-IDF + Linear SVM`
- un modèle image `CNN PyTorch`

L’architecture actuelle suit une logique microservices avec:

- un `gateway` sécurisé en entrée
- une API de prédiction texte dédiée
- une API de prédiction image dédiée
- une API de training
- Airflow pour l’orchestration
- DVC pour la gestion des données et artefacts
- DagsHub / MLflow pour le tracking d’expériences et le registry
- Prometheus + Grafana pour le monitoring

## Architecture

```text
[ Client / Reverse proxy ]
            |
            v
       [ Gateway ]
        /   |    \
       /    |     \
      v     v      v
[Predict Text] [Predict Image] [Training API]
      \          /                |
       \        /                 v
        +------/----------> [DagsHub / MLflow]
                              ^
                              |
                         [Airflow DAG]
                              |
                              v
                        [DVC Runner]
                              |
                              v
                        [Data / Models]

Monitoring:
Prometheus scrape Gateway + APIs
Grafana visualise les métriques
```

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

## Structure du dépôt

```text
mlops_projects/
├── airflow/
│   ├── dags/
│   │   └── mlops_orchestration.py
│   ├── dvc/
│   │   └── Dockerfile
│   └── requirements.txt
├── api/
├── data/
├── gateway/
│   ├── dockerfile
│   ├── gateway_main.py
│   └── requirements.txt
├── monitoring/
│   ├── prometheus.yml
│   ├── 01-prometheus.yaml
│   └── grafana/
├── models/
├── src/
│   ├── common/
│   ├── gateway/
│   ├── inference/
│   ├── mlflow/
│   ├── preprocessing/
│   ├── train_models/
│   └── training/
├── streamlit/
├── tests/
├── .github/workflows/ci.yml
├── docker-compose.yml
└── README.md
```

## APIs métier

### Gateway

Le gateway est le point d’entrée principal. Il route vers les services internes et expose aussi les métriques Prometheus.

Routes principales:

- `POST /token`
- `GET /health`
- `GET /metrics`
- `POST /predict/text`
- `POST /predict/image`
- `POST /predict/svm`
- `POST /predict/cnn`
- `POST /train/svm`
- `POST /train/cnn`
- `POST /reload/svm`
- `POST /reload/cnn`
- `GET /data/check-updates`
- `POST /data/check-updates/baseline`
- `POST /data/check-updates/retrain`
- `GET /info`

Fichier principal: [gateway/gateway_main.py](./gateway/gateway_main.py)

Le gateway expose aussi une API de surveillance des nouveaux fichiers de données:

- scan des CSV présents dans `data/raw/`
- scan des images présentes dans `data/raw/image_train/`
- comparaison avec un état précédent stocké dans `data/.gateway_retrain_state.json`
- déclenchement automatique du réentraînement SVM et/ou CNN si de nouveaux fichiers sont détectés

### API de prédiction texte

Service dédié au modèle SVM. Le conteneur est construit à partir de `src/inference`, avec `MODEL_TYPE=svm`.

Routes:

- `GET /health`
- `GET /metrics`
- `POST /predict`
- `POST /predict/svm`
- `POST /reload`
- `POST /reload/text`
- `GET /info`

Fichier principal: [src/inference/main.py](./src/inference/main.py)

### API de prédiction image

Service dédié au modèle CNN. Le conteneur est construit à partir du même code, avec `MODEL_TYPE=cnn`.

Routes:

- `GET /health`
- `GET /metrics`
- `POST /predict`
- `POST /predict/cnn`
- `POST /reload`
- `POST /reload/image`
- `GET /info`

Fichier principal: [src/inference/main.py](./src/inference/main.py)

### API de training

Déclenche les pipelines d’entraînement SVM et CNN, logue les runs dans MLflow/DagsHub, et expose aussi `/metrics`.

Routes:

- `GET /health`
- `GET /metrics`
- `POST /train/svm`
- `POST /train/cnn`

Fichier principal: [src/training/main.py](./src/training/main.py)

## Orchestration Airflow

Le DAG principal est: [airflow/dags/mlops_orchestration.py](./airflow/dags/mlops_orchestration.py)

Il réalise:

1. `dvc pull` dans un conteneur dédié via `DockerOperator`
2. déclenchement du training SVM
3. déclenchement du training CNN
4. reload des APIs de prédiction après entraînement

Variables Airflow attendues:

- `api_token`
- `dagshub_user`
- `dagshub_token`

## Monitoring

Le monitoring minimum demandé est en place sur le gateway et les APIs.

Prometheus scrape:

- `gateway`
- `predict-text-api`
- `predict-image-api`
- `training-api`

Fichiers:

- [monitoring/prometheus.yml](./monitoring/prometheus.yml)
- [monitoring/01-prometheus.yaml](./monitoring/01-prometheus.yaml)

Grafana est préconfiguré avec Prometheus comme datasource:

- [monitoring/grafana/provisioning/datasources/prometheus.yml](./monitoring/grafana/provisioning/datasources/prometheus.yml)

## Lancement local

### 1. Définir les variables d’environnement

Créer un fichier `.env` à la racine ou exporter les variables suivantes:

```env
DAGSHUB_USER=Fouxy84
DAGSHUB_TOKEN=xxx
GIT_REPO_URL=https://github.com/Fouxy84/mlops_projects.git
DAGSHUB_REPO_URL=https://dagshub.com/Fouxy84/mlops_projects
PROJECT_ROOT_HOST=c:/Users/coach/Desktop/datascientest/Projet DATASCIENTEST/projet_MLops/mlops_projects
```

### 2. Lancer la stack

```powershell
docker compose up --build -d
```

### 3. Vérifier les services

```powershell
docker compose ps
docker compose logs gateway
docker compose logs predict-text-api
docker compose logs predict-image-api
docker compose logs training-api
```

## Démo rapide

Voici une séquence simple pour une démo demain matin avec Swagger, monitoring et orchestration.

### 1. Démarrer toute la stack

```powershell
docker compose up --build -d
```

### 2. Vérifier que les services sont bien démarrés

```powershell
docker compose ps
docker compose logs gateway
docker compose logs predict-text-api
docker compose logs predict-image-api
docker compose logs training-api
```

### 3. Ouvrir les interfaces web

À montrer dans le navigateur:

- Swagger Gateway: `http://localhost:8000/docs`
- Swagger Predict Text API: `http://localhost:8001/docs`
- Swagger Training API: `http://localhost:8002/docs`
- Swagger Auth API: `http://localhost:8003/docs`
- Swagger Predict Image API: `http://localhost:8004/docs`
- MLflow local: `http://localhost:5000`
- Airflow: `http://localhost:8080`
- Prometheus: `http://localhost:9090`
- Grafana: `http://localhost:3000`

### 4. Générer un token depuis Swagger

Dans `http://localhost:8000/docs`:

1. ouvrir `POST /token`
2. utiliser par exemple:

```text
username=admin
password=admin123
```

3. récupérer `access_token`
4. cliquer sur `Authorize`
5. coller `Bearer <access_token>`

### 5. Faire une prédiction texte dans Swagger

Depuis le Swagger du gateway:

- `POST /predict/svm`

Payload:

```json
{
  "text": "Ordinateur portable 15 pouces, 8GB RAM, SSD 256GB"
}
```

### 6. Faire une prédiction image dans Swagger

Depuis le Swagger du gateway:

- `POST /predict/cnn`

Payload:

```json
{
  "image_path": "image_528113_product_923222.jpg"
}
```

### 7. Montrer l’état global du système

Depuis le Swagger du gateway:

- `GET /health`
- `GET /info`
- `GET /metrics`

### 7bis. Montrer la détection de nouvelles données

Depuis le Swagger du gateway:

1. appeler `POST /data/check-updates/baseline` pour enregistrer l’état initial
2. ajouter ensuite un nouveau CSV dans `data/raw/` et/ou une nouvelle image dans `data/raw/image_train/`
3. appeler `GET /data/check-updates` pour visualiser les nouveaux fichiers détectés
4. appeler `POST /data/check-updates/retrain` pour déclencher le réentraînement des modèles impactés

Comportement attendu:

- nouveau CSV détecté => déclenchement `train/svm`
- nouvelle image détectée => déclenchement `train/cnn`
- nouveaux fichiers des deux côtés => déclenchement des deux entraînements

### 8. Montrer Grafana

Ouvrir:

- `http://localhost:3000`

Connexion par défaut si non modifiée:

```text
login: admin
password: admin
```

Puis:

1. vérifier que la datasource Prometheus est présente
2. aller dans `Explore`
3. lancer quelques requêtes PromQL

Exemples utiles:

```text
mlops_gateway_requests_total
mlops_inference_requests_total
mlops_predictions_total
mlops_training_requests_total
```

### 9. Montrer Prometheus

Ouvrir:

- `http://localhost:9090`

Requêtes utiles:

```text
mlops_gateway_requests_total
mlops_inference_request_duration_seconds_count
mlops_predictions_total
mlops_training_runs_total
```

### 10. Montrer Airflow

Ouvrir:

- `http://localhost:8080`

Compte créé au démarrage:

```text
username: admin
password: admin
```

Puis:

1. ouvrir le DAG `mlops_orchestration`
2. montrer les tâches `dvc_pull_artifacts`, `train_svm`, `train_cnn`, `reload_svm`, `reload_cnn`
3. lancer un run manuel si les variables Airflow sont déjà renseignées

### 11. Déclencher la démo en ligne de commande si besoin

Obtenir un token:

```powershell
curl -X POST "http://127.0.0.1:8000/token" -H "Content-Type: application/x-www-form-urlencoded" -d "username=admin&password=admin123"
```

Prédiction texte:

```powershell
curl -X POST "http://127.0.0.1:8000/predict/svm" -H "Authorization: Bearer <TOKEN>" -H "Content-Type: application/json" -d "{\"text\":\"Ordinateur portable 15 pouces, 8GB RAM, SSD 256GB\"}"
```

Prédiction image:

```powershell
curl -X POST "http://127.0.0.1:8000/predict/cnn" -H "Authorization: Bearer <TOKEN>" -H "Content-Type: application/json" -d "{\"image_path\":\"image_528113_product_923222.jpg\"}"
```

## Exemples d’utilisation

### Obtenir un token

```bash
curl -X POST "http://127.0.0.1:8000/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123"
```

### Prédiction texte

```bash
curl -X POST "http://127.0.0.1:8000/predict/svm" \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Ordinateur portable 15 pouces, 8GB RAM, SSD 256GB"
  }'
```

### Prédiction image

```bash
curl -X POST "http://127.0.0.1:8000/predict/cnn" \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "image_path": "image_528113_product_923222.jpg"
  }'
```

### Déclencher un entraînement

```bash
curl -X POST "http://127.0.0.1:8000/train/svm" \
  -H "Authorization: Bearer <TOKEN>"

curl -X POST "http://127.0.0.1:8000/train/cnn" \
  -H "Authorization: Bearer <TOKEN>"
```

## Actualiser DagsHub

Cette partie est importante pour que DagsHub reflète bien les nouvelles données, les runs MLflow et les artefacts versionnés par DVC.

### Cas 1. Actualiser les données/artefacts DVC vers DagsHub

Si tu modifies des données ou des artefacts suivis par DVC:

```powershell
dvc status
dvc add data/raw
dvc add data/processed
dvc add models/text/svm.joblib
git add data models .dvc .gitignore
git commit -m "Update DVC tracked data and models"
dvc push
git push origin main
```

À adapter selon les fichiers réellement modifiés. Le plus important est:

- `dvc add` pour mettre à jour les fichiers `.dvc`
- `dvc push` pour envoyer les artefacts vers le remote DagsHub
- `git push` pour envoyer le code et les métadonnées DVC

### Cas 2. Actualiser les runs MLflow sur DagsHub

Les services `training-api`, `predict-text-api` et `predict-image-api` utilisent:

- `MLFLOW_TRACKING_URI=https://dagshub.com/Fouxy84/mlops_projects.mlflow`
- `MLFLOW_TRACKING_USERNAME`
- `MLFLOW_TRACKING_PASSWORD`

Donc dès qu’un entraînement est relancé avec les bons secrets, les runs remontent dans DagsHub.

Exemple:

```bash
curl -X POST "http://127.0.0.1:8000/train/svm" \
  -H "Authorization: Bearer <TOKEN>"
```

Puis vérifier sur:

- GitHub: `https://github.com/Fouxy84/mlops_projects`
- DagsHub: `https://dagshub.com/Fouxy84/mlops_projects`
- MLflow DagsHub: `https://dagshub.com/Fouxy84/mlops_projects.mlflow`

### Cas 3. Actualiser via Airflow

Le DAG `mlops_orchestration` peut être utilisé pour rejouer le flux:

1. `dvc pull` dans le conteneur `dvc-runner`
2. entraînement SVM
3. entraînement CNN
4. reload des APIs

Pour que cela fonctionne, il faut renseigner dans Airflow:

- Variable `api_token`
- Variable `dagshub_user`
- Variable `dagshub_token`

Ensuite lancer le DAG depuis l’UI Airflow.

### Cas 4. Forcer le rechargement des modèles en production locale

Après une mise à jour de modèle déjà poussée dans DagsHub/MLflow:

```bash
curl -X POST "http://127.0.0.1:8000/reload/svm" \
  -H "Authorization: Bearer <TOKEN>"

curl -X POST "http://127.0.0.1:8000/reload/cnn" \
  -H "Authorization: Bearer <TOKEN>"
```

### Cas 5. Détecter de nouvelles données puis réentraîner

Initialiser le baseline:

```bash
curl -X POST "http://127.0.0.1:8000/data/check-updates/baseline" \
  -H "Authorization: Bearer <TOKEN>"
```

Vérifier les nouveaux fichiers:

```bash
curl -X GET "http://127.0.0.1:8000/data/check-updates" \
  -H "Authorization: Bearer <TOKEN>"
```

Déclencher le réentraînement si de nouvelles données sont trouvées:

```bash
curl -X POST "http://127.0.0.1:8000/data/check-updates/retrain" \
  -H "Authorization: Bearer <TOKEN>"
```

Cette API surveille:

- les fichiers `.csv` directement dans `data/raw/`
- les fichiers image dans `data/raw/image_train/`

Le fichier d’état utilisé par le gateway est:

- `data/.gateway_retrain_state.json`

## CI/CD

Le workflow GitHub Actions est dans:

- [.github/workflows/ci.yml](./.github/workflows/ci.yml)

Pipeline actuel:

1. tests unitaires
2. validation des DAGs Airflow
3. build Docker
4. push Docker Hub sur `push` vers `develop` ou `main`

Images construites:

- `mlops-gateway`
- `mlops-auth-api`
- `mlops-predict-text-api`
- `mlops-predict-image-api`
- `mlops-training-api`
- `mlops-mlflow`
- `mlops-dvc-runner`

## Tests

Tests Python:

```powershell
python -m pytest tests -q
```

Validation de la configuration Docker Compose:

```powershell
docker compose config
```

## Références

- GitHub: `https://github.com/Fouxy84/mlops_projects`
- DagsHub: `https://dagshub.com/Fouxy84/mlops_projects`
- Image d’architecture souhaitée: `c:/Users/coach/Pictures/architecture_mlops.png`
