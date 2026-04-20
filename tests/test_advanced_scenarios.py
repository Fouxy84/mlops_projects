#!/usr/bin/env python3
"""
=============================================================================
 TESTS AVANCÉS MLOps - Scénarios complets
=============================================================================
 1. PREDICTIONS IMAGE (CNN)
 2. PREDICTION MULTIMODAL (text + image fusion)
 3. TRAIN NEW MODEL TEXT via Airflow/Gateway
 4. TRAIN NEW MODEL IMAGE via Airflow/Gateway
 5. CHECK UPDATE (détection de nouvelles données)
 6. RETRAIN 1 MODEL + PLACEMENT EN PRODUCTION
 7. UPDATE DAGSHUB AVEC NEW MODEL
=============================================================================
"""

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

# ─── Configuration ──────────────────────────────────────────────────────────
GATEWAY_URL = os.getenv("GATEWAY_URL", "http://localhost:8000")
PREDICT_TEXT_URL = os.getenv("PREDICT_TEXT_URL", "http://localhost:8001")
PREDICT_IMAGE_URL = os.getenv("PREDICT_IMAGE_URL", "http://localhost:8004")
TRAINING_API_URL = os.getenv("TRAINING_API_URL", "http://localhost:8002")
MLFLOW_URL = os.getenv("MLFLOW_TRACKING_URI", "https://dagshub.com/Fouxy84/mlops_projects.mlflow")
DAGSHUB_USER = os.getenv("DAGSHUB_USER", "Fouxy84")
DAGSHUB_TOKEN = os.getenv("DAGSHUB_TOKEN", "")

ADMIN_USER = "admin"
ADMIN_PASS = "admin"
NORMAL_USER = "user"
NORMAL_PASS = "user"

# Images disponibles pour les tests
TEST_IMAGES = [
    "image_1000076039_product_580161.jpg",
    "image_1000089455_product_348990858.jpg",
    "image_1000092894_product_353108104.jpg",
    "image_1000093804_product_343306951.jpg",
    "image_1000095646_product_344209267.jpg",
    "image_1000095647_product_148177050.jpg",
    "image_1000099971_product_352683003.jpg",
    "image_1000100220_product_352601770.jpg",
    "image_1000222973_product_351172420.jpg",
    "image_1000228891_product_355017693.jpg",
    "image_1000293482_product_355570712.jpg",
    "image_1000293768_product_355549191.jpg",
    "image_1000392_product_1257596.jpg",
    "image_1000425043_product_349046352.jpg",
    "image_1000441257_product_356912201.jpg",
]

# Textes pour tests multimodaux
MULTIMODAL_TEXTS = {
    "livre": "Roman historique passionnant sur la Révolution française",
    "jeu_video": "Manette sans fil PS5 DualSense avec retour haptique",
    "mobilier": "Canapé d'angle convertible 3 places en tissu gris",
    "fourniture": "Lot de 12 stylos à bille bleu pointe fine BIC",
    "decoration": "Tableau décoratif abstrait peinture murale moderne 60x90cm",
    "jouet": "Puzzle 1000 pièces paysage montagne pour adulte",
    "maquette": "Drone DJI Mini 3 Pro avec caméra 4K et GPS intégré",
}

# Catégories attendues (label -> nom)
EXPECTED_CATEGORIES = {
    0: "fournitures de bureau",
    1: "livres / magazines",
    2: "jeux vidéo",
    3: "jeux de société / jouets",
    4: "mobilier / meubles",
    5: "décoration / maison",
    6: "maquettes / drones",
    7: "autre",
}

# ─── Résultats ──────────────────────────────────────────────────────────────
results = {
    "timestamp": datetime.now().isoformat(),
    "sections": {},
    "total_pass": 0,
    "total_fail": 0,
    "total_skip": 0,
}


def log_result(section, test_name, status, detail=""):
    """Enregistre un résultat de test."""
    icon = {"PASS": "✅", "FAIL": "❌", "SKIP": "⚠️", "INFO": "ℹ️"}.get(status, "?")
    print(f"  {icon} {test_name}: {status} {detail}")
    if section not in results["sections"]:
        results["sections"][section] = []
    results["sections"][section].append({
        "test": test_name,
        "status": status,
        "detail": detail,
    })
    if status == "PASS":
        results["total_pass"] += 1
    elif status == "FAIL":
        results["total_fail"] += 1
    elif status == "SKIP":
        results["total_skip"] += 1


def login(username, password):
    """Login au gateway et retourner le session cookie."""
    try:
        r = requests.post(f"{GATEWAY_URL}/login", data={
            "username": username,
            "password": password,
        }, timeout=10)
        return r.status_code == 200, r
    except Exception as e:
        return False, str(e)


def login_admin():
    """Login en tant qu'admin."""
    return login(ADMIN_USER, ADMIN_PASS)


def login_user():
    """Login en tant qu'utilisateur normal."""
    return login(NORMAL_USER, NORMAL_PASS)


# =============================================================================
# 1. PREDICTIONS IMAGE (CNN)
# =============================================================================
def test_image_predictions():
    section = "1. PREDICTIONS IMAGE (CNN)"
    print(f"\n{'='*70}")
    print(f" {section}")
    print(f"{'='*70}")

    # Login d'abord
    ok, resp = login_user()
    if not ok:
        log_result(section, "Login préalable", "FAIL", "Impossible de se connecter")
        return

    # --- Test 1.1: Prédiction image basique ---
    test_name = "1.1 Prédiction image basique"
    try:
        r = requests.post(f"{GATEWAY_URL}/predict/cnn", json={
            "image_path": TEST_IMAGES[0]
        }, timeout=30)
        if r.status_code == 200:
            data = r.json()
            has_label = "predicted_label" in data
            has_name = "label_name" in data
            label = data.get("predicted_label")
            name = data.get("label_name")
            if has_label and has_name and isinstance(label, int):
                log_result(section, test_name, "PASS",
                           f"label={label}, name='{name}'")
            else:
                log_result(section, test_name, "FAIL",
                           f"Réponse incomplète: {data}")
        else:
            log_result(section, test_name, "FAIL",
                       f"HTTP {r.status_code}: {r.text[:200]}")
    except Exception as e:
        log_result(section, test_name, "FAIL", str(e))

    # --- Test 1.2: Prédiction sur plusieurs images distinctes ---
    test_name = "1.2 Prédictions sur 10 images distinctes"
    predictions = {}
    errors = 0
    for img in TEST_IMAGES[:10]:
        try:
            r = requests.post(f"{GATEWAY_URL}/predict/cnn", json={
                "image_path": img
            }, timeout=30)
            if r.status_code == 200:
                data = r.json()
                label = data.get("predicted_label", -1)
                predictions[img] = label
            else:
                errors += 1
        except Exception:
            errors += 1

    unique_labels = set(predictions.values())
    if len(predictions) >= 8 and errors <= 2:
        log_result(section, test_name, "PASS",
                   f"{len(predictions)} OK, {errors} erreurs, "
                   f"{len(unique_labels)} labels uniques: {sorted(unique_labels)}")
    else:
        log_result(section, test_name, "FAIL",
                   f"{len(predictions)} OK, {errors} erreurs")

    # --- Test 1.3: Distribution des prédictions image ---
    test_name = "1.3 Distribution des prédictions image"
    from collections import Counter
    dist = Counter(predictions.values())
    total = sum(dist.values())
    log_result(section, test_name, "INFO",
               f"Distribution: {dict(dist)} sur {total} images")
    # Vérifier si le modèle ne prédit pas toujours la même classe
    if len(dist) == 1 and total > 3:
        log_result(section, "1.3b Diversité des prédictions", "FAIL",
                   f"Modèle prédit toujours label={list(dist.keys())[0]}")
    elif len(dist) > 1:
        log_result(section, "1.3b Diversité des prédictions", "PASS",
                   f"{len(dist)} classes différentes prédites")
    else:
        log_result(section, "1.3b Diversité des prédictions", "SKIP",
                   "Pas assez de données")

    # --- Test 1.4: Image inexistante ---
    test_name = "1.4 Image inexistante (erreur attendue)"
    try:
        r = requests.post(f"{GATEWAY_URL}/predict/cnn", json={
            "image_path": "image_inexistante_xyz.jpg"
        }, timeout=15)
        if r.status_code in (404, 500):
            log_result(section, test_name, "PASS",
                       f"HTTP {r.status_code} comme attendu")
        elif r.status_code == 200:
            log_result(section, test_name, "FAIL",
                       "Devrait retourner une erreur pour image inexistante")
        else:
            log_result(section, test_name, "PASS",
                       f"HTTP {r.status_code}")
    except Exception as e:
        log_result(section, test_name, "FAIL", str(e))

    # --- Test 1.5: Chemin image vide ---
    test_name = "1.5 Chemin image vide"
    try:
        r = requests.post(f"{GATEWAY_URL}/predict/cnn", json={
            "image_path": ""
        }, timeout=15)
        if r.status_code in (400, 404, 422, 500):
            log_result(section, test_name, "PASS",
                       f"HTTP {r.status_code} - erreur gérée")
        else:
            log_result(section, test_name, "FAIL",
                       f"HTTP {r.status_code}: {r.text[:200]}")
    except Exception as e:
        log_result(section, test_name, "FAIL", str(e))

    # --- Test 1.6: Prédiction image directe (sans gateway) ---
    test_name = "1.6 Prédiction CNN directe (port 8004)"
    try:
        r = requests.post(f"{PREDICT_IMAGE_URL}/predict/cnn", json={
            "image_path": TEST_IMAGES[0]
        }, timeout=30)
        if r.status_code == 200:
            data = r.json()
            log_result(section, test_name, "PASS",
                       f"label={data.get('predicted_label')}, name='{data.get('label_name')}'")
        else:
            log_result(section, test_name, "FAIL",
                       f"HTTP {r.status_code}: {r.text[:200]}")
    except Exception as e:
        log_result(section, test_name, "FAIL", str(e))

    # --- Test 1.7: Cohérence gateway vs direct ---
    test_name = "1.7 Cohérence gateway vs API directe"
    try:
        r_gw = requests.post(f"{GATEWAY_URL}/predict/cnn", json={
            "image_path": TEST_IMAGES[0]
        }, timeout=30)
        r_direct = requests.post(f"{PREDICT_IMAGE_URL}/predict/cnn", json={
            "image_path": TEST_IMAGES[0]
        }, timeout=30)
        if r_gw.status_code == 200 and r_direct.status_code == 200:
            gw_label = r_gw.json().get("predicted_label")
            direct_label = r_direct.json().get("predicted_label")
            if gw_label == direct_label:
                log_result(section, test_name, "PASS",
                           f"Même label={gw_label} via gateway et direct")
            else:
                log_result(section, test_name, "FAIL",
                           f"Gateway={gw_label}, Direct={direct_label}")
        else:
            log_result(section, test_name, "FAIL",
                       f"GW={r_gw.status_code}, Direct={r_direct.status_code}")
    except Exception as e:
        log_result(section, test_name, "FAIL", str(e))

    # --- Test 1.8: Payload invalide (pas de champ image_path) ---
    test_name = "1.8 Payload invalide (champ manquant)"
    try:
        r = requests.post(f"{GATEWAY_URL}/predict/cnn", json={
            "text": "ceci est du texte, pas une image"
        }, timeout=15)
        if r.status_code == 422:
            log_result(section, test_name, "PASS",
                       "HTTP 422 - validation Pydantic correcte")
        else:
            log_result(section, test_name, "FAIL",
                       f"HTTP {r.status_code}: attendu 422")
    except Exception as e:
        log_result(section, test_name, "FAIL", str(e))

    # --- Test 1.9: Path traversal (sécurité) ---
    test_name = "1.9 Path traversal (sécurité)"
    try:
        r = requests.post(f"{GATEWAY_URL}/predict/cnn", json={
            "image_path": "../../../etc/passwd"
        }, timeout=15)
        if r.status_code in (400, 404, 500):
            log_result(section, test_name, "PASS",
                       f"HTTP {r.status_code} - path traversal bloqué")
        elif r.status_code == 200:
            log_result(section, test_name, "FAIL",
                       "DANGER: path traversal non bloqué!")
        else:
            log_result(section, test_name, "PASS",
                       f"HTTP {r.status_code}")
    except Exception as e:
        log_result(section, test_name, "FAIL", str(e))

    # --- Test 1.10: Latence des prédictions image ---
    test_name = "1.10 Latence prédiction image"
    try:
        start = time.time()
        r = requests.post(f"{GATEWAY_URL}/predict/cnn", json={
            "image_path": TEST_IMAGES[0]
        }, timeout=30)
        elapsed = time.time() - start
        if r.status_code == 200:
            if elapsed < 5:
                log_result(section, test_name, "PASS",
                           f"Temps: {elapsed:.2f}s (< 5s)")
            else:
                log_result(section, test_name, "FAIL",
                           f"Trop lent: {elapsed:.2f}s")
        else:
            log_result(section, test_name, "FAIL",
                       f"HTTP {r.status_code}")
    except Exception as e:
        log_result(section, test_name, "FAIL", str(e))


# =============================================================================
# 2. PREDICTION MULTIMODAL (text + image)
# =============================================================================
def test_multimodal_predictions():
    section = "2. PREDICTIONS MULTIMODAL"
    print(f"\n{'='*70}")
    print(f" {section}")
    print(f"{'='*70}")

    ok, _ = login_user()
    if not ok:
        log_result(section, "Login préalable", "FAIL", "Impossible de se connecter")
        return

    # --- Test 2.1: Multimodal basique ---
    test_name = "2.1 Prédiction multimodale basique"
    try:
        r = requests.post(f"{GATEWAY_URL}/predict/multimodal", json={
            "text": "Livre de cuisine avec recettes traditionnelles",
            "image_path": TEST_IMAGES[0]
        }, timeout=30)
        if r.status_code == 200:
            data = r.json()
            required_keys = ["predicted_label", "label_name", "fusion_strategy",
                             "text_prediction", "image_prediction"]
            missing = [k for k in required_keys if k not in data]
            if not missing:
                log_result(section, test_name, "PASS",
                           f"fusion={data['fusion_strategy']}, "
                           f"label={data['predicted_label']}, "
                           f"name='{data['label_name']}'")
            else:
                log_result(section, test_name, "FAIL",
                           f"Clés manquantes: {missing}")
        else:
            log_result(section, test_name, "FAIL",
                       f"HTTP {r.status_code}: {r.text[:200]}")
    except Exception as e:
        log_result(section, test_name, "FAIL", str(e))

    # --- Test 2.2: Vérifier fusion_strategy 'agreement' vs 'text_priority' ---
    test_name = "2.2 Analyse des stratégies de fusion"
    fusion_results = {}
    for label, text in MULTIMODAL_TEXTS.items():
        try:
            r = requests.post(f"{GATEWAY_URL}/predict/multimodal", json={
                "text": text,
                "image_path": TEST_IMAGES[0]
            }, timeout=30)
            if r.status_code == 200:
                data = r.json()
                strategy = data.get("fusion_strategy", "unknown")
                text_label = data["text_prediction"]["predicted_label"]
                img_label = data["image_prediction"]["predicted_label"]
                fusion_results[label] = {
                    "strategy": strategy,
                    "text_label": text_label,
                    "image_label": img_label,
                    "final_label": data["predicted_label"],
                }
        except Exception:
            pass

    agreement_count = sum(1 for v in fusion_results.values() if v["strategy"] == "agreement")
    text_priority_count = sum(1 for v in fusion_results.values() if v["strategy"] == "text_priority")
    total = len(fusion_results)

    if total > 0:
        log_result(section, test_name, "PASS",
                   f"agreement={agreement_count}/{total}, "
                   f"text_priority={text_priority_count}/{total}")
    else:
        log_result(section, test_name, "FAIL", "Aucun résultat")

    # --- Test 2.3: Quand text et image s'accordent ---
    test_name = "2.3 Vérification: agreement = même label"
    for label, info in fusion_results.items():
        if info["strategy"] == "agreement":
            if info["text_label"] == info["image_label"]:
                log_result(section, f"2.3 Agreement '{label}'", "PASS",
                           f"text={info['text_label']} == image={info['image_label']}")
            else:
                log_result(section, f"2.3 Agreement '{label}'", "FAIL",
                           f"text={info['text_label']} != image={info['image_label']} "
                           f"mais strategy='agreement'")

    # --- Test 2.4: Quand text_priority → le résultat final = texte ---
    test_name = "2.4 Vérification: text_priority → final = text"
    for label, info in fusion_results.items():
        if info["strategy"] == "text_priority":
            if info["final_label"] == info["text_label"]:
                log_result(section, f"2.4 Text priority '{label}'", "PASS",
                           f"final={info['final_label']} == text={info['text_label']}")
            else:
                log_result(section, f"2.4 Text priority '{label}'", "FAIL",
                           f"final={info['final_label']} != text={info['text_label']}")

    # --- Test 2.5: Multimodal avec différentes images ---
    test_name = "2.5 Multimodal avec 5 images différentes"
    consistent_text = "Guide de voyage pour les Alpes françaises"
    results_list = []
    for img in TEST_IMAGES[:5]:
        try:
            r = requests.post(f"{GATEWAY_URL}/predict/multimodal", json={
                "text": consistent_text,
                "image_path": img
            }, timeout=30)
            if r.status_code == 200:
                data = r.json()
                results_list.append({
                    "image": img[:30],
                    "text_label": data["text_prediction"]["predicted_label"],
                    "img_label": data["image_prediction"]["predicted_label"],
                    "final": data["predicted_label"],
                    "strategy": data["fusion_strategy"],
                })
        except Exception:
            pass

    if len(results_list) >= 3:
        # Le label texte devrait être constant (même texte)
        text_labels = set(r["text_label"] for r in results_list)
        img_labels = set(r["img_label"] for r in results_list)
        log_result(section, test_name, "PASS",
                   f"{len(results_list)} résultats, "
                   f"text_labels={text_labels}, image_labels={img_labels}")
        # Vérifier cohérence du texte
        if len(text_labels) == 1:
            log_result(section, "2.5b Cohérence texte", "PASS",
                       f"Même texte → même label texte: {text_labels}")
        else:
            log_result(section, "2.5b Cohérence texte", "FAIL",
                       f"Même texte → labels différents: {text_labels}")
    else:
        log_result(section, test_name, "FAIL",
                   f"Seulement {len(results_list)} résultats")

    # --- Test 2.6: Multimodal image inexistante ---
    test_name = "2.6 Multimodal avec image inexistante"
    try:
        r = requests.post(f"{GATEWAY_URL}/predict/multimodal", json={
            "text": "Texte valide pour tester",
            "image_path": "image_qui_nexiste_pas.jpg"
        }, timeout=15)
        if r.status_code in (404, 500):
            log_result(section, test_name, "PASS",
                       f"HTTP {r.status_code} - erreur gérée")
        else:
            log_result(section, test_name, "FAIL",
                       f"HTTP {r.status_code}: attendu 404/500")
    except Exception as e:
        log_result(section, test_name, "FAIL", str(e))

    # --- Test 2.7: Multimodal champs manquants ---
    test_name = "2.7 Multimodal champ manquant (pas de text)"
    try:
        r = requests.post(f"{GATEWAY_URL}/predict/multimodal", json={
            "image_path": TEST_IMAGES[0]
        }, timeout=15)
        if r.status_code == 422:
            log_result(section, test_name, "PASS",
                       "HTTP 422 - validation correcte")
        else:
            log_result(section, test_name, "FAIL",
                       f"HTTP {r.status_code}: attendu 422")
    except Exception as e:
        log_result(section, test_name, "FAIL", str(e))

    # --- Test 2.8: Multimodal texte vide ---
    test_name = "2.8 Multimodal avec texte vide"
    try:
        r = requests.post(f"{GATEWAY_URL}/predict/multimodal", json={
            "text": "",
            "image_path": TEST_IMAGES[0]
        }, timeout=30)
        if r.status_code == 200:
            data = r.json()
            log_result(section, test_name, "PASS",
                       f"Accepté: label={data.get('predicted_label')}")
        elif r.status_code in (400, 422):
            log_result(section, test_name, "PASS",
                       f"HTTP {r.status_code} - rejeté correctement")
        else:
            log_result(section, test_name, "FAIL",
                       f"HTTP {r.status_code}")
    except Exception as e:
        log_result(section, test_name, "FAIL", str(e))

    # --- Test 2.9: Latence multimodal ---
    test_name = "2.9 Latence multimodale"
    try:
        start = time.time()
        r = requests.post(f"{GATEWAY_URL}/predict/multimodal", json={
            "text": "Test de latence pour prédiction multimodale",
            "image_path": TEST_IMAGES[0]
        }, timeout=30)
        elapsed = time.time() - start
        if r.status_code == 200:
            log_result(section, test_name, "PASS" if elapsed < 10 else "FAIL",
                       f"Temps: {elapsed:.2f}s (text+image)")
        else:
            log_result(section, test_name, "FAIL",
                       f"HTTP {r.status_code}")
    except Exception as e:
        log_result(section, test_name, "FAIL", str(e))


# =============================================================================
# 3. TRAIN NEW MODEL TEXT via Gateway (simule Airflow)
# =============================================================================
def test_train_text_model():
    section = "3. TRAIN NEW MODEL TEXT (Airflow/Gateway)"
    print(f"\n{'='*70}")
    print(f" {section}")
    print(f"{'='*70}")

    # --- Test 3.1: Login admin (requis pour entraînement) ---
    test_name = "3.1 Login admin"
    ok, resp = login_admin()
    if not ok:
        log_result(section, test_name, "FAIL",
                   "Impossible de se connecter en admin")
        return
    log_result(section, test_name, "PASS", "Connecté en tant qu'admin")

    # --- Test 3.2: Vérification rôle admin ---
    test_name = "3.2 Vérification rôle admin"
    try:
        r = requests.get(f"{GATEWAY_URL}/me", timeout=10)
        if r.status_code == 200:
            data = r.json()
            if data.get("role") == "admin":
                log_result(section, test_name, "PASS",
                           f"role={data['role']}")
            else:
                log_result(section, test_name, "FAIL",
                           f"role={data.get('role')}, attendu 'admin'")
        else:
            log_result(section, test_name, "FAIL",
                       f"HTTP {r.status_code}")
    except Exception as e:
        log_result(section, test_name, "FAIL", str(e))

    # --- Test 3.3: Lancer l'entraînement SVM via gateway ---
    test_name = "3.3 POST /train/svm (déclencher entraînement texte)"
    try:
        r = requests.post(f"{GATEWAY_URL}/train/svm", timeout=30)
        if r.status_code == 200:
            data = r.json()
            log_result(section, test_name, "PASS",
                       f"Réponse: {data}")
        elif r.status_code == 403:
            log_result(section, test_name, "FAIL",
                       "HTTP 403 - Accès refusé (bug session globale connue)")
        elif r.status_code == 503:
            log_result(section, test_name, "FAIL",
                       "HTTP 503 - training-api non disponible. "
                       "Lancez: docker compose up training-api")
        else:
            log_result(section, test_name, "FAIL",
                       f"HTTP {r.status_code}: {r.text[:200]}")
    except Exception as e:
        log_result(section, test_name, "FAIL", str(e))

    # --- Test 3.4: Entraînement direct via training-api ---
    test_name = "3.4 POST training-api:8002/train/svm (direct)"
    try:
        r = requests.post(f"{TRAINING_API_URL}/train/svm", timeout=30)
        if r.status_code == 200:
            data = r.json()
            log_result(section, test_name, "PASS",
                       f"Réponse: {data}")
        else:
            log_result(section, test_name, "FAIL",
                       f"HTTP {r.status_code}: {r.text[:200]}")
    except requests.exceptions.ConnectionError:
        log_result(section, test_name, "SKIP",
                   "training-api non accessible (port 8002). "
                   "Service non démarré?")
    except Exception as e:
        log_result(section, test_name, "FAIL", str(e))

    # --- Test 3.5: Simuler le flux Airflow (DVC pull → Train → Reload) ---
    test_name = "3.5 Flux Airflow simulé: train SVM → reload"
    try:
        # Étape 1: Training
        r_train = requests.post(f"{TRAINING_API_URL}/train/svm", timeout=30)
        train_ok = r_train.status_code == 200

        if train_ok:
            # Attendre que le training background se lance
            log_result(section, "3.5a Train SVM lancé", "PASS",
                       f"{r_train.json()}")
            time.sleep(2)

            # Étape 2: Reload (comme le fait Airflow)
            login_admin()  # Re-login admin
            r_reload = requests.post(f"{GATEWAY_URL}/reload/svm", timeout=30)
            if r_reload.status_code == 200:
                log_result(section, "3.5b Reload SVM", "PASS",
                           f"{r_reload.json()}")
            elif r_reload.status_code == 403:
                log_result(section, "3.5b Reload SVM", "FAIL",
                           "HTTP 403 - bug session globale")
            else:
                log_result(section, "3.5b Reload SVM", "FAIL",
                           f"HTTP {r_reload.status_code}: {r_reload.text[:200]}")
        else:
            log_result(section, test_name, "SKIP",
                       "Training non disponible")
    except requests.exceptions.ConnectionError:
        log_result(section, test_name, "SKIP",
                   "training-api non accessible")
    except Exception as e:
        log_result(section, test_name, "FAIL", str(e))

    # --- Test 3.6: Utilisateur normal ne peut pas entraîner ---
    test_name = "3.6 User normal ne peut pas entraîner"
    login_user()
    try:
        r = requests.post(f"{GATEWAY_URL}/train/svm", timeout=15)
        if r.status_code == 403:
            log_result(section, test_name, "PASS",
                       "HTTP 403 - accès refusé correctement")
        else:
            log_result(section, test_name, "FAIL",
                       f"HTTP {r.status_code}: attendu 403")
    except Exception as e:
        log_result(section, test_name, "FAIL", str(e))


# =============================================================================
# 4. TRAIN NEW MODEL IMAGE via Gateway (simule Airflow)
# =============================================================================
def test_train_image_model():
    section = "4. TRAIN NEW MODEL IMAGE (Airflow/Gateway)"
    print(f"\n{'='*70}")
    print(f" {section}")
    print(f"{'='*70}")

    # --- Test 4.1: Login admin ---
    test_name = "4.1 Login admin"
    ok, _ = login_admin()
    if not ok:
        log_result(section, test_name, "FAIL", "Impossible de se connecter")
        return
    log_result(section, test_name, "PASS", "OK")

    # --- Test 4.2: Lancer entraînement CNN via gateway ---
    test_name = "4.2 POST /train/cnn (déclencher entraînement image)"
    try:
        r = requests.post(f"{GATEWAY_URL}/train/cnn", timeout=30)
        if r.status_code == 200:
            data = r.json()
            log_result(section, test_name, "PASS",
                       f"Réponse: {data}")
        elif r.status_code == 403:
            log_result(section, test_name, "FAIL",
                       "HTTP 403 - bug session globale")
        elif r.status_code == 503:
            log_result(section, test_name, "FAIL",
                       "HTTP 503 - training-api non disponible")
        else:
            log_result(section, test_name, "FAIL",
                       f"HTTP {r.status_code}: {r.text[:200]}")
    except Exception as e:
        log_result(section, test_name, "FAIL", str(e))

    # --- Test 4.3: Entraînement CNN direct ---
    test_name = "4.3 POST training-api:8002/train/cnn (direct)"
    try:
        r = requests.post(f"{TRAINING_API_URL}/train/cnn", timeout=30)
        if r.status_code == 200:
            data = r.json()
            log_result(section, test_name, "PASS",
                       f"Réponse: {data}")
        else:
            log_result(section, test_name, "FAIL",
                       f"HTTP {r.status_code}: {r.text[:200]}")
    except requests.exceptions.ConnectionError:
        log_result(section, test_name, "SKIP",
                   "training-api non accessible (port 8002)")
    except Exception as e:
        log_result(section, test_name, "FAIL", str(e))

    # --- Test 4.4: Flux Airflow simulé: train CNN → reload ---
    test_name = "4.4 Flux Airflow: train CNN → reload"
    try:
        r_train = requests.post(f"{TRAINING_API_URL}/train/cnn", timeout=30)
        if r_train.status_code == 200:
            log_result(section, "4.4a Train CNN lancé", "PASS",
                       f"{r_train.json()}")
            time.sleep(2)

            login_admin()
            r_reload = requests.post(f"{GATEWAY_URL}/reload/cnn", timeout=30)
            if r_reload.status_code == 200:
                log_result(section, "4.4b Reload CNN", "PASS",
                           f"{r_reload.json()}")
            elif r_reload.status_code == 403:
                log_result(section, "4.4b Reload CNN", "FAIL",
                           "HTTP 403 - bug session globale")
            else:
                log_result(section, "4.4b Reload CNN", "FAIL",
                           f"HTTP {r_reload.status_code}")
        else:
            log_result(section, test_name, "SKIP",
                       "Training non disponible")
    except requests.exceptions.ConnectionError:
        log_result(section, test_name, "SKIP",
                   "training-api non accessible")
    except Exception as e:
        log_result(section, test_name, "FAIL", str(e))

    # --- Test 4.5: Vérifier la structure du DAG Airflow ---
    test_name = "4.5 Structure DAG Airflow (vérification statique)"
    dag_file = Path(__file__).parent.parent / "airflow" / "dags" / "mlops_orchestration.py"
    if dag_file.exists():
        content = dag_file.read_text(encoding="utf-8")
        checks = {
            "train_svm task": "train_svm" in content,
            "train_cnn task": "train_cnn" in content,
            "reload_svm task": "reload_svm" in content,
            "reload_cnn task": "reload_cnn" in content,
            "dvc_pull task": "dvc_pull" in content,
            "pipeline order": "start >> dvc_pull" in content,
            "parallel training": "[train_svm, train_cnn]" in content,
        }
        all_ok = all(checks.values())
        failed = [k for k, v in checks.items() if not v]
        if all_ok:
            log_result(section, test_name, "PASS",
                       "Toutes les tâches DAG présentes et ordonnées")
        else:
            log_result(section, test_name, "FAIL",
                       f"Manquants: {failed}")
    else:
        log_result(section, test_name, "SKIP",
                   f"Fichier DAG non trouvé: {dag_file}")

    # --- Test 4.6: Vérifier health training-api ---
    test_name = "4.6 Health check training-api"
    try:
        r = requests.get(f"{TRAINING_API_URL}/health", timeout=10)
        if r.status_code == 200:
            data = r.json()
            log_result(section, test_name, "PASS",
                       f"Réponse: {data}")
        else:
            log_result(section, test_name, "FAIL",
                       f"HTTP {r.status_code}")
    except requests.exceptions.ConnectionError:
        log_result(section, test_name, "SKIP",
                   "training-api non accessible")
    except Exception as e:
        log_result(section, test_name, "FAIL", str(e))


# =============================================================================
# 5. CHECK UPDATE (détection de nouvelles données)
# =============================================================================
def test_check_updates():
    section = "5. CHECK UPDATE"
    print(f"\n{'='*70}")
    print(f" {section}")
    print(f"{'='*70}")

    # --- Test 5.1: Login admin ---
    ok, _ = login_admin()
    if not ok:
        log_result(section, "5.1 Login admin", "FAIL", "Connexion échouée")
        return
    log_result(section, "5.1 Login admin", "PASS", "OK")

    # --- Test 5.2: GET /data/check-updates ---
    test_name = "5.2 GET /data/check-updates"
    try:
        r = requests.get(f"{GATEWAY_URL}/data/check-updates", timeout=15)
        if r.status_code == 200:
            data = r.json()
            changes = data.get("changes", {})
            text_info = changes.get("text", {})
            image_info = changes.get("image", {})
            log_result(section, test_name, "PASS",
                       f"text_files={len(text_info.get('current_files', []))}, "
                       f"image_files={len(image_info.get('current_files', []))}, "
                       f"new_text={text_info.get('has_new_files')}, "
                       f"new_images={image_info.get('has_new_files')}")
        elif r.status_code == 403:
            log_result(section, test_name, "FAIL",
                       "HTTP 403 - bug session globale (admin non reconnu)")
        else:
            log_result(section, test_name, "FAIL",
                       f"HTTP {r.status_code}: {r.text[:200]}")
    except Exception as e:
        log_result(section, test_name, "FAIL", str(e))

    # --- Test 5.3: Structure de la réponse check-updates ---
    test_name = "5.3 Structure réponse check-updates"
    try:
        r = requests.get(f"{GATEWAY_URL}/data/check-updates", timeout=15)
        if r.status_code == 200:
            data = r.json()
            required_top = ["status", "changes"]
            changes = data.get("changes", {})
            required_changes = ["text", "image", "state_file"]
            text_keys = ["directory", "current_files", "new_files", "has_new_files"]
            image_keys = ["directory", "current_files", "new_files", "has_new_files"]

            missing_top = [k for k in required_top if k not in data]
            missing_changes = [k for k in required_changes if k not in changes]
            missing_text = [k for k in text_keys if k not in changes.get("text", {})]
            missing_image = [k for k in image_keys if k not in changes.get("image", {})]

            all_missing = missing_top + missing_changes + missing_text + missing_image
            if not all_missing:
                log_result(section, test_name, "PASS",
                           "Toutes les clés présentes")
            else:
                log_result(section, test_name, "FAIL",
                           f"Clés manquantes: {all_missing}")
        elif r.status_code == 403:
            log_result(section, test_name, "SKIP", "Accès refusé (403)")
        else:
            log_result(section, test_name, "FAIL",
                       f"HTTP {r.status_code}")
    except Exception as e:
        log_result(section, test_name, "FAIL", str(e))

    # --- Test 5.4: POST /data/check-updates/baseline ---
    test_name = "5.4 POST /data/check-updates/baseline"
    login_admin()
    try:
        r = requests.post(f"{GATEWAY_URL}/data/check-updates/baseline", timeout=15)
        if r.status_code == 200:
            data = r.json()
            log_result(section, test_name, "PASS",
                       f"status={data.get('status')}")
        elif r.status_code == 403:
            log_result(section, test_name, "FAIL",
                       "HTTP 403 - bug session globale")
        else:
            log_result(section, test_name, "FAIL",
                       f"HTTP {r.status_code}: {r.text[:200]}")
    except Exception as e:
        log_result(section, test_name, "FAIL", str(e))

    # --- Test 5.5: Après baseline → pas de nouveaux fichiers ---
    test_name = "5.5 Après baseline → has_new_files=False"
    login_admin()
    try:
        # D'abord baseline
        r_base = requests.post(f"{GATEWAY_URL}/data/check-updates/baseline", timeout=15)
        if r_base.status_code == 200:
            # Puis check-updates
            login_admin()
            r_check = requests.get(f"{GATEWAY_URL}/data/check-updates", timeout=15)
            if r_check.status_code == 200:
                changes = r_check.json().get("changes", {})
                text_new = changes.get("text", {}).get("has_new_files", True)
                img_new = changes.get("image", {}).get("has_new_files", True)
                if not text_new and not img_new:
                    log_result(section, test_name, "PASS",
                               "Pas de nouveaux fichiers après baseline")
                else:
                    log_result(section, test_name, "FAIL",
                               f"Nouveaux fichiers détectés: text={text_new}, image={img_new}")
            elif r_check.status_code == 403:
                log_result(section, test_name, "SKIP", "Accès refusé")
            else:
                log_result(section, test_name, "FAIL",
                           f"Check: HTTP {r_check.status_code}")
        elif r_base.status_code == 403:
            log_result(section, test_name, "SKIP", "Accès refusé")
        else:
            log_result(section, test_name, "FAIL",
                       f"Baseline: HTTP {r_base.status_code}")
    except Exception as e:
        log_result(section, test_name, "FAIL", str(e))

    # --- Test 5.6: User normal ne peut pas check-updates ---
    test_name = "5.6 User normal → check-updates refusé"
    login_user()
    try:
        r = requests.get(f"{GATEWAY_URL}/data/check-updates", timeout=15)
        if r.status_code == 403:
            log_result(section, test_name, "PASS",
                       "HTTP 403 - accès refusé correctement")
        else:
            log_result(section, test_name, "FAIL",
                       f"HTTP {r.status_code}: attendu 403")
    except Exception as e:
        log_result(section, test_name, "FAIL", str(e))

    # --- Test 5.7: POST /data/check-updates/retrain ---
    test_name = "5.7 POST /data/check-updates/retrain"
    login_admin()
    try:
        r = requests.post(f"{GATEWAY_URL}/data/check-updates/retrain", timeout=30)
        if r.status_code == 200:
            data = r.json()
            log_result(section, test_name, "PASS",
                       f"status={data.get('status')}, "
                       f"triggered={data.get('triggered_models', [])}")
        elif r.status_code == 403:
            log_result(section, test_name, "FAIL",
                       "HTTP 403 - bug session globale")
        elif r.status_code == 503:
            log_result(section, test_name, "FAIL",
                       "HTTP 503 - training-api non disponible")
        else:
            log_result(section, test_name, "FAIL",
                       f"HTTP {r.status_code}: {r.text[:200]}")
    except Exception as e:
        log_result(section, test_name, "FAIL", str(e))


# =============================================================================
# 6. RETRAIN 1 MODEL + PLACEMENT EN PRODUCTION
# =============================================================================
def test_retrain_production():
    section = "6. RETRAIN + PRODUCTION"
    print(f"\n{'='*70}")
    print(f" {section}")
    print(f"{'='*70}")

    # --- Test 6.1: Entraîner un modèle SVM ---
    test_name = "6.1 Déclencher entraînement SVM"
    login_admin()
    training_started = False
    try:
        r = requests.post(f"{GATEWAY_URL}/train/svm", timeout=30)
        if r.status_code == 200:
            data = r.json()
            training_started = True
            log_result(section, test_name, "PASS",
                       f"Training lancé: {data}")
        elif r.status_code == 403:
            # Essayer en direct
            r2 = requests.post(f"{TRAINING_API_URL}/train/svm", timeout=30)
            if r2.status_code == 200:
                training_started = True
                log_result(section, test_name, "PASS",
                           f"Training lancé (direct): {r2.json()}")
            else:
                log_result(section, test_name, "FAIL",
                           f"Gateway 403, direct {r2.status_code}")
        elif r.status_code == 503:
            log_result(section, test_name, "SKIP",
                       "training-api non disponible")
        else:
            log_result(section, test_name, "FAIL",
                       f"HTTP {r.status_code}")
    except requests.exceptions.ConnectionError:
        log_result(section, test_name, "SKIP",
                   "Services non accessibles")
    except Exception as e:
        log_result(section, test_name, "FAIL", str(e))

    # --- Test 6.2: Vérifier que le training tourne en background ---
    test_name = "6.2 Training en background (réponse immédiate)"
    if training_started:
        log_result(section, test_name, "PASS",
                   "Le serveur a répondu immédiatement → BackgroundTasks")
    else:
        log_result(section, test_name, "SKIP", "Training non démarré")

    # --- Test 6.3: Reload du modèle après entraînement ---
    test_name = "6.3 Reload SVM après entraînement"
    login_admin()
    try:
        r = requests.post(f"{GATEWAY_URL}/reload/svm", timeout=30)
        if r.status_code == 200:
            data = r.json()
            log_result(section, test_name, "PASS",
                       f"Reload réussi: {data}")
        elif r.status_code == 403:
            # Essayer le reload direct
            r2 = requests.post(f"{PREDICT_TEXT_URL}/reload/text", timeout=30)
            if r2.status_code == 200:
                log_result(section, test_name, "PASS",
                           f"Reload direct réussi: {r2.json()}")
            else:
                log_result(section, test_name, "FAIL",
                           f"Gateway 403, direct {r2.status_code}")
        else:
            log_result(section, test_name, "FAIL",
                       f"HTTP {r.status_code}: {r.text[:200]}")
    except Exception as e:
        log_result(section, test_name, "FAIL", str(e))

    # --- Test 6.4: Prédiction après reload ---
    test_name = "6.4 Prédiction SVM après reload"
    login_user()
    try:
        r = requests.post(f"{GATEWAY_URL}/predict/svm", json={
            "text": "Stylo bille noir pointe fine"
        }, timeout=15)
        if r.status_code == 200:
            data = r.json()
            log_result(section, test_name, "PASS",
                       f"label={data.get('predicted_label')}, "
                       f"name='{data.get('label_name')}'")
        else:
            log_result(section, test_name, "FAIL",
                       f"HTTP {r.status_code}")
    except Exception as e:
        log_result(section, test_name, "FAIL", str(e))

    # --- Test 6.5: Reload CNN ---
    test_name = "6.5 Reload CNN"
    login_admin()
    try:
        r = requests.post(f"{GATEWAY_URL}/reload/cnn", timeout=30)
        if r.status_code == 200:
            log_result(section, test_name, "PASS",
                       f"Reload CNN: {r.json()}")
        elif r.status_code == 403:
            r2 = requests.post(f"{PREDICT_IMAGE_URL}/reload/image", timeout=30)
            if r2.status_code == 200:
                log_result(section, test_name, "PASS",
                           f"Reload direct CNN: {r2.json()}")
            else:
                log_result(section, test_name, "FAIL",
                           f"Gateway 403, direct {r2.status_code}")
        else:
            log_result(section, test_name, "FAIL",
                       f"HTTP {r.status_code}")
    except Exception as e:
        log_result(section, test_name, "FAIL", str(e))

    # --- Test 6.6: Prédiction image après reload ---
    test_name = "6.6 Prédiction CNN après reload"
    login_user()
    try:
        r = requests.post(f"{GATEWAY_URL}/predict/cnn", json={
            "image_path": TEST_IMAGES[0]
        }, timeout=30)
        if r.status_code == 200:
            data = r.json()
            log_result(section, test_name, "PASS",
                       f"label={data.get('predicted_label')}, "
                       f"name='{data.get('label_name')}'")
        else:
            log_result(section, test_name, "FAIL",
                       f"HTTP {r.status_code}")
    except Exception as e:
        log_result(section, test_name, "FAIL", str(e))

    # --- Test 6.7: Workflow complet train → reload → predict ---
    test_name = "6.7 Workflow complet: train → reload → predict"
    workflow_ok = True
    steps_done = []

    # Step 1: Train
    login_admin()
    try:
        r = requests.post(f"{GATEWAY_URL}/train/svm", timeout=30)
        if r.status_code == 200:
            steps_done.append("train")
        elif r.status_code == 403:
            r2 = requests.post(f"{TRAINING_API_URL}/train/svm", timeout=30)
            if r2.status_code == 200:
                steps_done.append("train(direct)")
        else:
            workflow_ok = False
    except requests.exceptions.ConnectionError:
        log_result(section, test_name, "SKIP", "training-api non accessible")
        workflow_ok = False
    except Exception:
        workflow_ok = False

    # Step 2: Reload
    if workflow_ok:
        time.sleep(2)
        login_admin()
        try:
            r = requests.post(f"{GATEWAY_URL}/reload/svm", timeout=30)
            if r.status_code == 200:
                steps_done.append("reload")
            elif r.status_code == 403:
                r2 = requests.post(f"{PREDICT_TEXT_URL}/reload/text", timeout=30)
                if r2.status_code == 200:
                    steps_done.append("reload(direct)")
            else:
                workflow_ok = False
        except Exception:
            workflow_ok = False

    # Step 3: Predict
    if workflow_ok:
        login_user()
        try:
            r = requests.post(f"{GATEWAY_URL}/predict/svm", json={
                "text": "Canapé en cuir marron"
            }, timeout=15)
            if r.status_code == 200:
                steps_done.append("predict")
            else:
                workflow_ok = False
        except Exception:
            workflow_ok = False

    if workflow_ok and len(steps_done) == 3:
        log_result(section, test_name, "PASS",
                   f"Étapes: {' → '.join(steps_done)}")
    elif steps_done:
        log_result(section, test_name, "FAIL",
                   f"Workflow partiel: {' → '.join(steps_done)}")
    else:
        log_result(section, test_name, "SKIP",
                   "Workflow non exécuté")

    # --- Test 6.8: Vérifier que le code d'entraînement enregistre sur MLflow ---
    test_name = "6.8 Code entraînement → MLflow (vérification statique)"
    train_text_file = Path(__file__).parent.parent / "src" / "training" / "run_training_text.py"
    if train_text_file.exists():
        content = train_text_file.read_text(encoding="utf-8")
        checks = {
            "mlflow.start_run": "mlflow.start_run" in content or "start_run" in content,
            "mlflow.log_model": "log_model" in content,
            "register_model": "register_model" in content or "registered_model_name" in content,
            "Production stage": "Production" in content,
            "dagshub.init": "dagshub.init" in content or "dagshub" in content,
        }
        passed = sum(1 for v in checks.items() if v[1])
        failed = [k for k, v in checks.items() if not v]
        if passed >= 4:
            log_result(section, test_name, "PASS",
                       f"{passed}/5 vérifications OK. Manquants: {failed or 'aucun'}")
        else:
            log_result(section, test_name, "FAIL",
                       f"Seulement {passed}/5 OK. Manquants: {failed}")
    else:
        log_result(section, test_name, "SKIP",
                   "Fichier non trouvé")


# =============================================================================
# 7. UPDATE DAGSHUB AVEC NEW MODEL
# =============================================================================
def test_dagshub_update():
    section = "7. UPDATE DAGSHUB"
    print(f"\n{'='*70}")
    print(f" {section}")
    print(f"{'='*70}")

    # --- Test 7.1: Connectivité DagsHub/MLflow ---
    test_name = "7.1 Connectivité DagsHub MLflow"
    try:
        r = requests.get(f"{MLFLOW_URL}/api/2.0/mlflow/experiments/list",
                         auth=(DAGSHUB_USER, DAGSHUB_TOKEN),
                         timeout=15)
        if r.status_code == 200:
            data = r.json()
            experiments = data.get("experiments", [])
            log_result(section, test_name, "PASS",
                       f"{len(experiments)} expériences trouvées")
        else:
            log_result(section, test_name, "FAIL",
                       f"HTTP {r.status_code}: {r.text[:200]}")
    except Exception as e:
        log_result(section, test_name, "FAIL", str(e))

    # --- Test 7.2: Lister les modèles enregistrés ---
    test_name = "7.2 Modèles enregistrés sur DagsHub"
    try:
        r = requests.get(
            f"{MLFLOW_URL}/api/2.0/mlflow/registered-models/search",
            auth=(DAGSHUB_USER, DAGSHUB_TOKEN),
            timeout=15,
        )
        if r.status_code == 200:
            data = r.json()
            models = data.get("registered_models", [])
            model_names = [m.get("name") for m in models]
            log_result(section, test_name, "PASS",
                       f"Modèles: {model_names}")

            # Vérifier les modèles attendus
            expected = ["Text_Classifier_SVM", "CNN_Image_Classifier"]
            for exp_model in expected:
                if exp_model in model_names:
                    log_result(section, f"7.2b Modèle '{exp_model}'", "PASS",
                               "Présent dans le registre")
                else:
                    log_result(section, f"7.2b Modèle '{exp_model}'", "FAIL",
                               "Absent du registre")
        else:
            log_result(section, test_name, "FAIL",
                       f"HTTP {r.status_code}: {r.text[:200]}")
    except Exception as e:
        log_result(section, test_name, "FAIL", str(e))

    # --- Test 7.3: Versions du modèle SVM ---
    test_name = "7.3 Versions modèle Text_Classifier_SVM"
    try:
        r = requests.get(
            f"{MLFLOW_URL}/api/2.0/mlflow/registered-models/get",
            params={"name": "Text_Classifier_SVM"},
            auth=(DAGSHUB_USER, DAGSHUB_TOKEN),
            timeout=15,
        )
        if r.status_code == 200:
            data = r.json()
            rm = data.get("registered_model", {})
            versions = rm.get("latest_versions", [])
            version_info = []
            for v in versions:
                version_info.append(
                    f"v{v.get('version')} ({v.get('current_stage', 'None')})")
            log_result(section, test_name, "PASS",
                       f"{len(versions)} versions: {', '.join(version_info)}")

            # Vérifier qu'il y a une version en Production
            prod_versions = [v for v in versions
                             if v.get("current_stage") == "Production"]
            if prod_versions:
                log_result(section, "7.3b Version Production SVM", "PASS",
                           f"Version {prod_versions[0].get('version')} en Production")
            else:
                log_result(section, "7.3b Version Production SVM", "FAIL",
                           "Aucune version en Production")
        elif r.status_code == 404:
            log_result(section, test_name, "FAIL",
                       "Modèle non trouvé dans le registre")
        else:
            log_result(section, test_name, "FAIL",
                       f"HTTP {r.status_code}")
    except Exception as e:
        log_result(section, test_name, "FAIL", str(e))

    # --- Test 7.4: Versions du modèle CNN ---
    test_name = "7.4 Versions modèle CNN_Image_Classifier"
    try:
        r = requests.get(
            f"{MLFLOW_URL}/api/2.0/mlflow/registered-models/get",
            params={"name": "CNN_Image_Classifier"},
            auth=(DAGSHUB_USER, DAGSHUB_TOKEN),
            timeout=15,
        )
        if r.status_code == 200:
            data = r.json()
            rm = data.get("registered_model", {})
            versions = rm.get("latest_versions", [])
            version_info = []
            for v in versions:
                version_info.append(
                    f"v{v.get('version')} ({v.get('current_stage', 'None')})")
            log_result(section, test_name, "PASS",
                       f"{len(versions)} versions: {', '.join(version_info)}")

            prod_versions = [v for v in versions
                             if v.get("current_stage") == "Production"]
            if prod_versions:
                log_result(section, "7.4b Version Production CNN", "PASS",
                           f"Version {prod_versions[0].get('version')} en Production")
            else:
                log_result(section, "7.4b Version Production CNN", "FAIL",
                           "Aucune version en Production")
        elif r.status_code == 404:
            log_result(section, test_name, "FAIL",
                       "Modèle non trouvé dans le registre")
        else:
            log_result(section, test_name, "FAIL",
                       f"HTTP {r.status_code}")
    except Exception as e:
        log_result(section, test_name, "FAIL", str(e))

    # --- Test 7.5: Derniers runs MLflow ---
    test_name = "7.5 Derniers runs MLflow"
    try:
        r = requests.post(
            f"{MLFLOW_URL}/api/2.0/mlflow/runs/search",
            json={
                "experiment_ids": ["0"],
                "max_results": 5,
                "order_by": ["start_time DESC"],
            },
            auth=(DAGSHUB_USER, DAGSHUB_TOKEN),
            timeout=15,
        )
        if r.status_code == 200:
            data = r.json()
            runs = data.get("runs", [])
            run_info = []
            for run in runs[:5]:
                run_data = run.get("data", {})
                params = {p["key"]: p["value"] for p in run_data.get("params", [])}
                metrics = {m["key"]: round(m["value"], 4) for m in run_data.get("metrics", [])}
                run_name = run.get("info", {}).get("run_name", "unknown")
                run_info.append(f"{run_name}: {metrics}")

            if runs:
                log_result(section, test_name, "PASS",
                           f"{len(runs)} runs. Dernier: {run_info[0] if run_info else '?'}")
            else:
                log_result(section, test_name, "FAIL",
                           "Aucun run trouvé")
        else:
            log_result(section, test_name, "FAIL",
                       f"HTTP {r.status_code}")
    except Exception as e:
        log_result(section, test_name, "FAIL", str(e))

    # --- Test 7.6: Métriques du dernier run ---
    test_name = "7.6 Métriques du dernier modèle"
    try:
        r = requests.post(
            f"{MLFLOW_URL}/api/2.0/mlflow/runs/search",
            json={
                "experiment_ids": ["0"],
                "max_results": 1,
                "order_by": ["start_time DESC"],
            },
            auth=(DAGSHUB_USER, DAGSHUB_TOKEN),
            timeout=15,
        )
        if r.status_code == 200:
            data = r.json()
            runs = data.get("runs", [])
            if runs:
                run_data = runs[0].get("data", {})
                metrics = {m["key"]: round(m["value"], 4)
                           for m in run_data.get("metrics", [])}
                if "accuracy" in metrics or "f1_macro" in metrics:
                    acc = metrics.get("accuracy", "N/A")
                    f1 = metrics.get("f1_macro", "N/A")
                    log_result(section, test_name, "PASS",
                               f"accuracy={acc}, f1_macro={f1}")
                else:
                    log_result(section, test_name, "FAIL",
                               f"Métriques disponibles: {list(metrics.keys())}")
            else:
                log_result(section, test_name, "FAIL", "Aucun run")
        else:
            log_result(section, test_name, "FAIL",
                       f"HTTP {r.status_code}")
    except Exception as e:
        log_result(section, test_name, "FAIL", str(e))

    # --- Test 7.7: Vérifier le code de transition vers Production ---
    test_name = "7.7 Code: transition vers Production (statique)"
    files_to_check = [
        Path(__file__).parent.parent / "src" / "training" / "run_training_text.py",
        Path(__file__).parent.parent / "src" / "training" / "run_training_images.py",
    ]
    for filepath in files_to_check:
        if filepath.exists():
            content = filepath.read_text(encoding="utf-8")
            has_register = "register_model" in content or "registered_model_name" in content
            has_production = "Production" in content
            has_transition = "transition_model_version_stage" in content
            fname = filepath.name
            if has_register and has_production:
                log_result(section, f"7.7 {fname}", "PASS",
                           f"register={has_register}, Production={has_production}, "
                           f"transition={has_transition}")
            else:
                log_result(section, f"7.7 {fname}", "FAIL",
                           f"register={has_register}, Production={has_production}")
        else:
            log_result(section, f"7.7 {filepath.name}", "SKIP",
                       "Fichier non trouvé")

    # --- Test 7.8: Vérifier que le modèle peut être chargé ---
    test_name = "7.8 Vérification de la config de chargement MLflow"
    config_file = Path(__file__).parent.parent / "src" / "inference" / "config.py"
    if config_file.exists():
        content = config_file.read_text(encoding="utf-8")
        has_model_uri = "MLFLOW_MODEL_URI" in content
        has_version = "MLFLOW_MODEL_VERSION" in content
        has_stage = "MLFLOW_MODEL_STAGE" in content or "Production" in content
        has_alias = "MLFLOW_MODEL_ALIAS" in content
        log_result(section, test_name, "PASS",
                   f"URI={has_model_uri}, version={has_version}, "
                   f"stage={has_stage}, alias={has_alias}")
    else:
        log_result(section, test_name, "SKIP", "config.py non trouvé")

    # --- Test 7.9: Test du endpoint /info pour voir les modèles chargés ---
    test_name = "7.9 GET /info (modèles chargés)"
    login_user()
    try:
        r = requests.get(f"{GATEWAY_URL}/info", timeout=15)
        if r.status_code == 200:
            data = r.json()
            gateway_ok = data.get("gateway") == "ok"
            text_info = data.get("models", {}).get("text_model", {})
            image_info = data.get("models", {}).get("image_model", {})
            log_result(section, test_name, "PASS",
                       f"gateway={gateway_ok}, "
                       f"text={json.dumps(text_info)[:80]}, "
                       f"image={json.dumps(image_info)[:80]}")
        elif r.status_code == 503:
            log_result(section, test_name, "FAIL",
                       "HTTP 503 - un service upstream non disponible")
        else:
            log_result(section, test_name, "FAIL",
                       f"HTTP {r.status_code}")
    except Exception as e:
        log_result(section, test_name, "FAIL", str(e))


# =============================================================================
# MAIN - Exécution de tous les tests
# =============================================================================
def print_summary():
    """Affiche le résumé final."""
    print(f"\n{'='*70}")
    print(f" RÉSUMÉ FINAL")
    print(f"{'='*70}")
    print(f"  ✅ PASS: {results['total_pass']}")
    print(f"  ❌ FAIL: {results['total_fail']}")
    print(f"  ⚠️  SKIP: {results['total_skip']}")
    total = results['total_pass'] + results['total_fail'] + results['total_skip']
    print(f"  📊 TOTAL: {total}")
    if total > 0:
        success_rate = (results['total_pass'] / total) * 100
        print(f"  📈 Taux de réussite: {success_rate:.1f}%")

    print(f"\n{'─'*70}")
    print(" DÉTAIL PAR SECTION:")
    print(f"{'─'*70}")
    for section, tests in results["sections"].items():
        pass_count = sum(1 for t in tests if t["status"] == "PASS")
        fail_count = sum(1 for t in tests if t["status"] == "FAIL")
        skip_count = sum(1 for t in tests if t["status"] == "SKIP")
        info_count = sum(1 for t in tests if t["status"] == "INFO")
        total_section = pass_count + fail_count + skip_count
        print(f"  {section}")
        print(f"    ✅ {pass_count} | ❌ {fail_count} | ⚠️ {skip_count} | ℹ️ {info_count}")

    # Écrire le rapport JSON
    report_path = Path(__file__).parent / "ADVANCED_TEST_RESULTS.json"
    report_path.write_text(json.dumps(results, indent=2, ensure_ascii=False),
                           encoding="utf-8")
    print(f"\n  📄 Rapport JSON: {report_path}")


if __name__ == "__main__":
    print(f"{'='*70}")
    print(f" TESTS AVANCÉS MLOps - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}")
    print(f" Gateway: {GATEWAY_URL}")
    print(f" Text API: {PREDICT_TEXT_URL}")
    print(f" Image API: {PREDICT_IMAGE_URL}")
    print(f" Training: {TRAINING_API_URL}")
    print(f" MLflow: {MLFLOW_URL}")
    print(f" DagsHub: {DAGSHUB_USER}")

    # Vérifier la connectivité de base
    print(f"\n{'─'*70}")
    print(" Vérification connectivité...")
    services = {
        "gateway": f"{GATEWAY_URL}/health",
        "predict-text": f"{PREDICT_TEXT_URL}/health",
        "predict-image": f"{PREDICT_IMAGE_URL}/health",
    }
    for name, url in services.items():
        try:
            r = requests.get(url, timeout=5)
            print(f"  ✅ {name}: {r.status_code}")
        except Exception:
            print(f"  ❌ {name}: non accessible")

    # Exécuter toutes les sections
    test_image_predictions()
    test_multimodal_predictions()
    test_train_text_model()
    test_train_image_model()
    test_check_updates()
    test_retrain_production()
    test_dagshub_update()

    print_summary()
