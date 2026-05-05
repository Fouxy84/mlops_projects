# Projet MLOps - Rakuten Multimodal Classification

ce projet s'inscrit dans le cadre de la phase 3 du projet Challenge Rakuten.
cette phase utilise les methodes ML Engineering (MLOps) pour déployer en production les modèles de prediction de categories Rakuten. Des methodes MLOps sont utilisées pour industrialiser les modèles de machine learning (svm/tfidf + cnn), en intégrant des étapes comme le versionnage des données et des modèles, l’automatisation des pipelines et le monitoring en production.

## Services

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
une explication plus détaillée des services exposés sont dans README_PRODUCTION.md

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

## Installation from scratch

### Prérequis

- **Docker Desktop** installé et démarré
- **Git** installé
- **DVC** installé (`pip install "dvc[s3]"`)
- Un compte **DagsHub** avec accès au repo `Fouxy84/mlops_projects` (token d'accès requis)

### Étape 1 — Cloner le repo

```powershell
git clone https://github.com/Fouxy84/mlops_projects.git
cd mlops_projects
```

### Étape 2 — Créer le fichier `.env`

Créer un fichier `.env` à la racine du dossier cloné:

```env
DAGSHUB_USER=Fouxy84
DAGSHUB_TOKEN=<ton_token_dagshub>
GIT_REPO_URL=https://github.com/Fouxy84/mlops_projects.git
DAGSHUB_REPO_URL=https://dagshub.com/Fouxy84/mlops_projects
PROJECT_ROOT_HOST=<chemin_absolu_vers_le_dossier_cloné>

# Laisser vide = charge la version Production par défaut depuis MLflow
TEXT_MLFLOW_MODEL_VERSION=
IMAGE_MLFLOW_MODEL_VERSION=
TEXT_MLFLOW_VECTORIZER_ARTIFACT_PATH=preprocessing/tfidf.joblib
```

> Le `PROJECT_ROOT_HOST` doit être le chemin Windows absolu vers le dossier cloné, ex: `c:/Users/monnom/projets/mlops_projects`

#### En cas de problème de modèle

Si les APIs de prédiction ne trouvent pas de modèle en `Production`, forcer une version explicite dans le `.env`:

```env
TEXT_MLFLOW_MODEL_VERSION=3
IMAGE_MLFLOW_MODEL_VERSION=2
```
Puis redémarrer:

```powershell
docker compose up -d predict-text-api predict-image-api
```
> Les modèles ne sont pas dans le repo Git. Ils sont téléchargés depuis DagsHub / MLflow au démarrage des conteneurs. Sans `dvc pull`, les dossiers `data/raw/` et `data/processed/` seront vides mais la stack démarre quand même.

### Étape 3 — Récupérer les données DVC (optionnel pour la démo)

```powershell
dvc remote add -d dagshub https://dagshub.com/Fouxy84/mlops_projects.dvc
dvc remote modify dagshub --local auth basic
dvc remote modify dagshub --local user Fouxy84
dvc remote modify dagshub --local password <ton_token_dagshub>
dvc pull
```

### Étape 4 — Démarrer la stack Docker

```powershell
docker compose up --build -d
```

> La première fois le build prend plusieurs minutes (images Python, Torch, etc.).

### Étape 5 — Vérification des services

```powershell
docker compose ps
docker compose logs gateway
docker compose logs predict-text-api
docker compose logs predict-image-api
docker compose logs training-api
```

### Étape 6 — Tester via Swagger

Ouvrir `http://localhost:8000/docs`
1. `POST /login` avec `admin/admin`
2. `GET /me`
3. `POST /predict/svm`
4. `POST /predict/cnn`
5. `POST /predict/multimodal`
6. `GET /info`
7. `POST /data/check-updates/baseline`
8. `GET /data/check-updates`
9. `POST /orchestrate/train/svm`
10. `POST /reload/svm`
11. `POST /logout`

#### Exemple texte

```json
{
  "text": "le tableau de chat est tres joli"
}
```

#### Exemple image

```json
{
  "image_path": "image_528113_product_923222.jpg"
}
```

#### Exemple multimodal

```json
{
  "text": "le tableau de chat est tres joli",
  "image_path": "image_528113_product_923222.jpg"
}
```

### Démo Streamlit (Option)

Lancer Streamlit:

```powershell
streamlit run options/option_1_streamlit_interface/streamlit_app.py
```

Ouvrir `http://localhost:8501`, puis:

1. Se connecter avec `admin / admin`
2. Tester la prédiction texte, image et multimodale depuis l'interface
3. Consulter l'état des services (monitoring)



## CI/CD

Workflow: [.github/workflows/ci.yml](./.github/workflows/ci.yml)

Pipeline actuel:

1. tests unitaires
2. validation du DAG Airflow actif
3. build Docker
4. push DockerHub uniquement sur `push` vers `master`
5. Deploiement vers Dagshub

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
- `POST /orchestrate/train/svm`
- `POST /orchestrate/train/cnn`
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

## Options d'evolution

Le dossier `options/` propose deux evolutions possibles pour ouvrir la reflexion vers un projet plus complet, sans remplacer la stack de reference basee sur `docker-compose.yml`.

### Option 1 - Interface Streamlit (fortement recommandé)

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

