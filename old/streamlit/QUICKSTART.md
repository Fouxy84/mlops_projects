# 📖 Guide d'Utilisation - Dashboard Streamlit

## 🚀 Démarrage Rapide (2 minutes)

### 1. Installation
```bash
# Option A: Locale
cd streamlit
pip install -r ../requirements.txt
streamlit run streamlit_rakuten.py

# Option B: Docker
docker-compose up streamlit
```

### 2. Se Connecter
- **URL**: http://localhost:8501
- **Compte démo**: 
  - ID: `admin`
  - MDP: `admin123`

### 3. Naviguer
- Utilisez la barre latérale pour changer de page
- Cliquez sur "Déconnexion" pour quitter

---

## 📊 Pages Disponibles

### Page 1: 🏠 Tableau de Bord
**Qu'est-ce que c'est?** Vue d'ensemble du système MLOps

**Que voir?**
- État des 4 services (Gateway, Inference, Training, MLflow)
- Statistiques clés (84,921 produits, 24 tests, 90.4% couverture)
- Liens vers ressources

**À faire:**
- Cliquez "Rafraîchir État" pour mettre à jour
- Cliquez "Ouvrir Grafana" pour voir les métriques

---

### Page 2: 📈 Essais & Tests (MLflow)
**Qu'est-ce que c'est?** Historique de tous les entraînements

**Que voir?**
- Liste des 3 derniers runs (SVM, CNN, Multimodal)
- Accuracy, F1-score, status
- Graphique comparatif des modèles

**À faire:**
- Cliquez "Récupérer depuis MLflow" pour actualiser
- Comparez les métriques des modèles

---

### Page 3: 🏗️ Architecture du Repo
**Qu'est-ce que c'est?** Visualisation complète du projet

**Que voir?**
- Structure des dossiers (16 répertoires)
- Stack technologique (Python, FastAPI, PyTorch, Docker, K8s)
- Diagramme du flux de données

**À faire:**
- Scrollez pour voir l'architecture complète
- Consultez la structure pour trouver un fichier

---

### Page 4: ✅ Tests & Couverture
**Qu'est-ce que c'est?** Rapports de tests et couverture code

**Que voir?**
- 46 tests répartis en 6 fichiers
- Taux de réussite: 100%
- Coverage par module (88-95%)

**À faire:**
- Cliquez sur les expandeurs pour voir le code des tests
- Consultez le graphique de couverture

---

### Page 5: 📊 Monitoring Grafana
**Qu'est-ce que c'est?** Dashboards de monitoring en temps réel

**Que voir?**
- 5 dashboards: Service Health, API Metrics, Model Performance, Infrastructure, Data Quality
- 15 alertes actives
- Latence P95: 450ms, Erreurs: 2/min, Throughput: 1200 req/min

**À faire:**
- Cliquez le lien pour ouvrir Grafana
- Explorez les 5 dashboards
- Consultez les règles d'alerte

---

### Page 6: 🔍 Drift Detection (Evidently)
**Qu'est-ce que c'est?** Détection de dérives dans les données

**Que voir?**
- Data Drift Analysis (4 features)
- Model Drift Metrics (accuracy, predictions, labels)
- Timeline des dérives sur 30 jours
- Distribution des features

**À faire:**
- Consultez les scores de drift
- Vérifiez les alertes (seuil = 0.3)
- Regardez les graphiques de distribution

---

### Page 7: 🤖 Inference (Texte/Image)
**Qu'est-ce que c'est?** Effectuer des prédictions

**Options:**

#### 📝 Texte (SVM + TF-IDF)
1. Entrez une description de produit
2. Cliquez "Prédire Catégorie"
3. Recevez la catégorie + confiance

**Exemple:** "iPhone 13 Pro - écran OLED 6.1 pouces..."
**Résultat:** Électronique (92.5% confiance)

#### 🖼️ Image (CNN PyTorch)
1. Upload/URL/Exemple d'image
2. Cliquez "Prédire Catégorie"
3. Recevez la catégorie + confiance

**Formats:** JPG, PNG (128x128px recommandé)
**Latence:** ~850ms

#### 📦 Multimodal
1. Entrez texte + image
2. Cliquez "Prédire (Multimodal)"
3. Prédiction combinée (94.2% confiance)

---

### Page 8: 🔄 CI/CD & Upload Données
**Qu'est-ce que c'est?** Gérer les données et pipelines

**3 Onglets:**

#### 📊 Upload Données
- **CSV Textes**: Upload fichier avec colonnes (imageid, productid, designation, description, label)
- **Images**: Upload multiple (JPG, PNG)
- **Archive**: ZIP complet avec données + images + metadata

#### 🔄 Pipeline CI/CD
- Voir les 3 derniers workflows (SVM, CNN, Upload)
- Tous les status = ✅ SUCCESS
- Durations: 15m, 45m, 5m

#### 📦 Gestion Modèles
- 3 modèles: SVM (87%), CNN (92%), Multimodal (89%)
- Versions et tailles (45MB, 128MB, 185MB)
- Status: 2 en PROD, 1 en TEST

---

### Page 9: 📉 Monitoring MLflow
**Qu'est-ce que c'est?** Suivi des expériences d'entraînement

**Que voir?**
- 5 expériences actives (48 runs total)
- Best Accuracy: 92% (CNN v2)
- Graphique de métriques (Accuracy, F1) par run
- Artifacts (modèles, datasets, configs, plots)

**À faire:**
- Consultez les 48 runs
- Comparez les métriques des différents runs
- Téléchargez les artifacts

---

### Page 10: ⚙️ Paramètres
**Qu'est-ce que c'est?** Configuration du système (Admin uniquement)

**3 Sections:**

#### 📍 URLs des Services
- Modifier les URLs (Gateway, Inference, Training, MLflow, Grafana)
- Cliquez "Sauvegarder"

#### 🔐 Authentification
- Ajouter/modifier utilisateurs
- Réinitialiser mots de passe

#### 📊 Préférences Monitoring
- Intervalle de refresh (5-60 secondes)
- Activer/désactiver notifications
- Export des métriques

---

## 🔐 Gestion de l'Authentification

### Comptes de Test

```
┌─────────────────┬────────────┬──────────────────────────────┐
│ Rôle            │ ID         │ Mot de passe                 │
├─────────────────┼────────────┼──────────────────────────────┤
│ Admin           │ admin      │ admin123                     │
│ Scientifique    │ scientist  │ scientist123                 │
│ Utilisateur     │ user       │ user123                      │
└─────────────────┴────────────┴──────────────────────────────┘
```

### Permissions par Rôle

| Permission | Admin | Scientist | User |
|-----------|-------|-----------|------|
| view_all | ✅ | ❌ | ❌ |
| train | ✅ | ✅ | ❌ |
| inference | ✅ | ✅ | ✅ |
| upload_data | ✅ | ✅ | ❌ |
| ci_cd | ✅ | ✅ | ❌ |
| monitoring | ✅ | ✅ | ✅ |
| view_tests | ✅ | ✅ | ✅ |

### Ajouter un Nouvel Utilisateur

1. Connectez-vous avec **admin**
2. Allez à **Paramètres → Authentification**
3. Cliquez "Ajouter Utilisateur"
4. Remplissez le formulaire

---

## 🎯 Cas d'Usage Courants

### Cas 1: Je veux faire une prédiction rapide
1. Allez à **🤖 Inference**
2. Sélectionnez **Texte** ou **Image**
3. Entrez/uploadez votre donnée
4. Cliquez **Prédire**

### Cas 2: Je veux entraîner un nouveau modèle
1. Allez à **🔄 CI/CD & Upload Données**
2. Uploadez vos données (CSV/Images)
3. Cliquez "Lancer Pipeline Manuelle"
4. Attendez ~45 min (CNN) ou ~15 min (SVM)
5. Consultez les résultats dans **📈 MLflow**

### Cas 3: Je veux monitorer la dérive des données
1. Allez à **🔍 Drift Detection**
2. Consultez les scores de dérive
3. Regardez la timeline (30 jours)
4. Vérifiez les alertes (seuil 0.3)

### Cas 4: Je veux consulter les tests
1. Allez à **✅ Tests & Couverture**
2. Consultez la suite (46 tests, 100% pass rate)
3. Cliquez les expandeurs pour voir le code
4. Vérifiez la couverture (90.4% moyen)

### Cas 5: Je veux modifier la configuration
1. **Admin uniquement**
2. Allez à **⚙️ Paramètres**
3. Modifiez les URLs/config
4. Cliquez "Sauvegarder"

---

## 🐛 Dépannage

### Problème: Page blanche / erreur de connexion
**Solution**: 
1. Rafraîchissez la page
2. Videz le cache (Ctrl+Shift+Del)
3. Reconnectez-vous

### Problème: Service DOWN (❌ DOWN au dashboard)
**Solution**:
```bash
# Vérifier l'état
docker-compose ps

# Redémarrer le service
docker-compose up -d <service_name>
```

### Problème: Inférence ne marche pas
**Solution**:
1. Vérifiez que l'API est UP (Tableau de Bord)
2. Vérifiez le format de l'entrée
3. Pour les images: JPG/PNG, 128x128px
4. Pour le texte: min 1 caractère

### Problème: MLflow introuvable
**Solution**:
1. Démarrez MLflow: `docker-compose up mlflow`
2. Accédez à http://localhost:5000
3. Rafraîchissez le dashboard

---

## 💡 Astuces Utiles

### Astuces pour l'Inférence
- Texte long = meilleure confiance
- Images nettes = meilleures prédictions
- Multimodal = combinaison texte+image (meilleure accuracy)

### Astuces pour le Monitoring
- Latence idéale: <500ms
- Drift score idéal: <0.3
- Accuracy idéale: >85%

### Astuces pour l'Upload
- CSV max 100MB
- Images max 10MB chacune
- Archive max 500MB
- Format CSV: (imageid, productid, designation, description, label)

---

## 📞 Support

### En cas de problème:
1. **Logs**: Regardez la console Streamlit
2. **Docs**: Consultez [README.md](./README.md)
3. **Code**: Vérifiez les fichiers:
   - `streamlit_rakuten.py` (app principale)
   - `auth_manager.py` (authentification)
   - `users_db.json` (base utilisateurs)

### Commandes utiles:
```bash
# Lancer avec debug
streamlit run streamlit_rakuten.py --logger.level=debug

# Changer le port
streamlit run streamlit_rakuten.py --server.port 8502

# Voir les logs
docker logs -f mlops_streamlit
```

---

## 📊 Métriques de Référence

| Métrique | Valeur |
|----------|--------|
| **Inférence Texte** | 45ms |
| **Inférence Image** | 850ms |
| **Inférence Multimodal** | 1200ms |
| **Accuracy SVM** | 87% |
| **Accuracy CNN** | 92% |
| **Accuracy Multimodal** | 89% |
| **Tests Passés** | 46/46 (100%) |
| **Code Coverage** | 90.4% |
| **Uptime** | 99.8% |
| **Latence P95** | 450ms |
| **Throughput** | 1200 req/min |

---

**Dernière mise à jour**: Janvier 2026  
**Version**: 3.0 - Dashboard MLOps Complet
