# 🚀 Dashboard MLOps Streamlit - Rakuten Challenge

Dashboard web complet pour la gestion du projet MLOps avec **authentification**, **monitoring**, **inférence**, et **gestion des données**.

## 📋 Fonctionnalités Principales

### 🔐 Authentification Sécurisée
- **Système d'authentification** avec gestion de rôles
- **Trois rôles** avec permissions différentes:
  - 👨‍💼 **Admin**: Accès complet
  - 👨‍🔬 **Scientist**: Train, upload données, monitoring
  - 👤 **User**: Inférence, consultation tests/monitoring
- **JWT tokens** pour sécuriser les sessions
- **Gestion des comptes de test** pré-configurés

### 📊 Tableau de Bord Complet
1. **🏠 Tableau de Bord** - Vue d'ensemble avec état des services
2. **📈 Essais & Tests MLflow** - Historique des entraînements
3. **🏗️ Architecture** - Visualisation du repo et du système
4. **✅ Tests & Couverture** - Coverage reports (90.4%)
5. **📊 Monitoring Grafana** - Dashboards et alertes
6. **🔍 Drift Detection** - Evidently data/model drift
7. **🤖 Inférence** - Texte, Image, Multimodal
8. **🔄 CI/CD** - Upload données, pipelines, gestion modèles
9. **📉 Monitoring MLflow** - Expériences et runs
10. **⚙️ Paramètres** - Configuration système

## 🚀 Installation

### 1. Prérequis
- Python 3.9+
- Docker (pour services backend)
- PostgreSQL (optionnel, pour MLflow)

### 2. Installation des dépendances

```bash
# Installer les packages
pip install -r requirements.txt

# Ou spécifiquement pour Streamlit
pip install streamlit>=1.28.0 plotly requests
```

### 3. Configuration

Créez un fichier `.env` dans le répertoire `streamlit/`:

```bash
# URLs des services
GATEWAY_URL=http://localhost:8000
INFERENCE_URL=http://localhost:8001
TRAINING_URL=http://localhost:8002
MLFLOW_URL=http://localhost:5000
GRAFANA_URL=http://localhost:3000

# Configuration Streamlit
STREAMLIT_SERVER_PORT=8501
STREAMLIT_SERVER_HEADLESS=true
```

## 🎯 Démarrage Rapide

### Option 1: Exécution Locale

```bash
# Aller au répertoire streamlit
cd streamlit/

# Lancer l'application
streamlit run streamlit_rakuten.py

# Accéder à l'application
# http://localhost:8501
```

### Option 2: Docker Compose

```bash
# Depuis la racine du projet
docker-compose up streamlit

# L'application est accessible à http://localhost:8501
```

### Option 3: Déploiement Kubernetes

```bash
# Créer une image Docker personnalisée
docker build -f streamlit/Dockerfile -t mlops/streamlit:latest .

# Pousser vers le registre (GHCR)
docker push ghcr.io/your-org/streamlit:latest

# Déployer avec K8s
kubectl apply -f k8s/05-streamlit.yaml
```

## 🔑 Comptes de Test

### Admin
- **ID**: `admin`
- **Mot de passe**: `admin123`
- **Permissions**: Accès complet à tous les modules

### Scientifique
- **ID**: `scientist`
- **Mot de passe**: `scientist123`
- **Permissions**: Entraînement, upload données, monitoring

### Utilisateur Standard
- **ID**: `user`
- **Mot de passe**: `user123`
- **Permissions**: Inférence, consultation tests/monitoring

## 📖 Guide des Pages

### 🏠 Tableau de Bord
**Description**: Vue d'ensemble du système  
**Accès**: Tous les utilisateurs  
**Contenu**:
- État des services (Gateway, Inference, Training, MLflow)
- Métriques clés (dataset, tests, modèles)
- Liens vers ressources

### 📈 Essais & Tests MLflow
**Description**: Historique d'entraînement depuis MLflow  
**Accès**: Admin, Scientist  
**Contenu**:
- Liste des runs avec paramètres et métriques
- Graphiques de comparaison (Accuracy, F1, etc.)
- Timeline des expériences

### 🏗️ Architecture
**Description**: Visualisation complète du système  
**Accès**: Tous  
**Contenu**:
- Structure du répertoire
- Stack technologique
- Diagrammes d'architecture
- Flux de données

### ✅ Tests & Couverture
**Description**: Rapports de tests et coverage  
**Accès**: Tous  
**Contenu**:
- Suite de tests (46 tests total)
- Coverage par module (90.4% moyen)
- Détails des tests
- Graphiques de couverture

### 📊 Monitoring Grafana
**Description**: Dashboards Grafana intégrés  
**Accès**: Admin, Scientist  
**Contenu**:
- 5 dashboards disponibles
- 15 alertes actives
- Métriques de performance (latence, throughput)
- Règles d'alerte

### 🔍 Drift Detection
**Description**: Détection de dérives (Evidently)  
**Accès**: Admin, Scientist  
**Contenu**:
- Data drift analysis
- Model drift metrics
- Timeline de dérives
- Distribution des features

### 🤖 Inférence
**Description**: Prédictions texte/image/multimodal  
**Accès**: Tous  
**Contenu**:
- **Texte**: SVM + TF-IDF (45ms)
- **Image**: CNN PyTorch (850ms)
- **Multimodal**: Combinaison texte+image
- Top 3 prédictions avec confiance

### 🔄 CI/CD & Données
**Description**: Pipeline CI/CD et gestion de données  
**Accès**: Admin, Scientist  
**Contenu**:
- Upload CSV/Images/Archives
- Historique des pipelines
- Gestion des modèles
- Actions rapides (déployer, rollback)

### 📉 Monitoring MLflow
**Description**: Suivi des expériences MLflow  
**Accès**: Admin, Scientist  
**Contenu**:
- 5 expériences actives (48 runs)
- Comparaison des métriques
- Artifacts (modèles, datasets, configs)
- Timeline des runs

### ⚙️ Paramètres
**Description**: Configuration système  
**Accès**: Admin  
**Contenu**:
- URLs des services
- Gestion utilisateurs
- Préférences monitoring
- Infos système

## 🔒 Système d'Authentification

### Architecture

```
Page de Connexion
    ↓
auth_manager.py → Vérification credentials (hash SHA-256)
    ↓
Session Streamlit (session_state)
    ↓
Dashboard (accès basé sur rôle)
```

### Fichiers clés

- **`auth_manager.py`**: Gestionnaire d'authentification
- **`users_db.json`**: Stockage des utilisateurs (créé automatiquement)
- **`streamlit_rakuten.py`**: Application principale

### Ajouter un nouvel utilisateur

```python
# Dans auth_manager.py, ajouter à DEFAULT_USERS:

DEFAULT_USERS = {
    "new_user": {
        "password_hash": hashlib.sha256("password123".encode()).hexdigest(),
        "role": "scientist",
        "permissions": ["inference", "train", "view_all", "monitoring"]
    }
}
```

## 📊 Intégration avec Services

### Gateway (Port 8000)
```python
# Appel d'inférence texte
POST {GATEWAY_URL}/predict/text
{
    "text": "Description du produit..."
}
```

### Inference (Port 8001)
```python
# Prédiction texte
POST {INFERENCE_URL}/predict/text
{
    "text": "..."
}

# Prédiction image
POST {INFERENCE_URL}/predict/image
{
    "image_path": "image_name.jpg"
}
```

### Training (Port 8002)
```python
# Entraîner SVM
POST {TRAINING_URL}/train/svm

# Entraîner CNN
POST {TRAINING_URL}/train/cnn
```

### MLflow (Port 5000)
```
UI: http://localhost:5000
API: Requêtes automatiques depuis le dashboard
```

### Grafana (Port 3000)
```
URL: http://localhost:3000
Credentials: admin/admin
Dashboards: 5 disponibles
```

## 🧪 Tests du Dashboard

```bash
# Test d'authentification
pytest streamlit/test_streamlit_auth.py

# Test des pages
streamlit run streamlit_rakuten.py --logger.level=debug

# Test manuel
# 1. Se connecter avec admin/admin123
# 2. Naviguer sur chaque page
# 3. Vérifier les permissions
# 4. Tester les requêtes API
```

## 🐛 Dépannage

### Erreur: "Connexion refusée" sur un service
```bash
# Vérifier que les services sont actifs
docker-compose ps

# Démarrer les services manquants
docker-compose up -d <service_name>
```

### Erreur: "Module not found" (streamlit, plotly, etc.)
```bash
# Réinstaller les dépendances
pip install -r requirements.txt --upgrade
```

### Erreur: Port 8501 déjà utilisé
```bash
# Changer le port Streamlit
streamlit run streamlit_rakuten.py --server.port 8502
```

### Authentification ne fonctionne pas
```bash
# Vérifier le fichier users_db.json
cat streamlit/users_db.json

# Supprimer et recréer
rm streamlit/users_db.json
streamlit run streamlit_rakuten.py
```

## 📁 Structure du Dossier Streamlit

```
streamlit/
├── streamlit_rakuten.py          # Application principale
├── auth_manager.py               # Gestionnaire authentification
├── users_db.json                 # BD utilisateurs (créée automatiquement)
├── requirements.txt              # Dépendances
├── Dockerfile                    # Image Docker
├── setup_run.bat                 # Script Windows de démarrage
└── README.md                     # Cette documentation
```

## 🚀 Déploiement en Production

### Checklist pré-déploiement
- [ ] Changer les mots de passe par défaut
- [ ] Configurer les URLs des services
- [ ] Sécuriser la BD des utilisateurs (permissions)
- [ ] Activer HTTPS/TLS
- [ ] Configurer le logging centralisé
- [ ] Mettre en place un backup des données
- [ ] Tester la récupération en cas de panne

### Scaling
```bash
# Déployer plusieurs instances avec LoadBalancer
kubectl apply -f k8s/05-streamlit-hpa.yaml

# Vérifier le scaling
kubectl get hpa
```

## 📈 Performances

| Métrique | Valeur |
|----------|--------|
| Latence Inférence Texte | 45ms |
| Latence Inférence Image | 850ms |
| Latence Dashboard | <500ms |
| Taux Réussite Tests | 100% (46/46) |
| Coverage Code | 90.4% |

## 📚 Ressources

- [Streamlit Docs](https://docs.streamlit.io/)
- [Plotly Docs](https://plotly.com/python/)
- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [MLflow Docs](https://mlflow.org/)
- [PHASE3_GUIDE.md](../PHASE3_GUIDE.md) - Guide complet Phase 3
- [DEPLOYMENT.md](../k8s/DEPLOYMENT.md) - Guide Kubernetes

## 🤝 Support

Pour des questions ou issues:
1. Consultez la [FAQ](./FAQ.md)
2. Vérifiez les logs: `streamlit run streamlit_rakuten.py --logger.level=debug`
3. Ouvrez une issue sur GitHub

## 📝 Licence

MIT License - Voir LICENSE.md

---

**Dernière mise à jour**: Janvier 2026  
**Version**: 3.0 - MLOps Complet avec Authentification  
**Auteur**: MLOps Team
