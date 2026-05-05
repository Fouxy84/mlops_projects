import os
import time

import requests
import streamlit as st


#GATEWAY_URL = os.getenv("GATEWAY_URL", "http://localhost:8000")
GATEWAY_URL = os.getenv("GATEWAY_URL", "http://127.0.0.1:8000") # fallback plus explicite pour localhost
#GATEWAY_URL = "http://127.0.0.1:8000"
GRAFANA_URL = os.getenv("GRAFANA_URL", "http://localhost:3000")
AIRFLOW_URL = os.getenv("AIRFLOW_URL", "http://airflow:8080")
PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://localhost:9090")

st.set_page_config(page_title="MLOps Dashboard", layout="wide", page_icon="🤖")

# ─────────────────────────────────────────────────────────────
# Session state
# ─────────────────────────────────────────────────────────────
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "role" not in st.session_state:
    st.session_state.role = None
if "username" not in st.session_state:
    st.session_state.username = None
if "session" not in st.session_state:
    st.session_state.session = requests.Session()
if "retrain_models" not in st.session_state:
    st.session_state.retrain_models = []
if "retrain_triggered_at" not in st.session_state:
    st.session_state.retrain_triggered_at = 0
if "done_models" not in st.session_state:
    # Mémorise les résultats des modèles terminés pour affichage côte à côte
    st.session_state.done_models = {}  # {"svm": {...state...}, "cnn": {...state...}}
if "retrain_models_check" not in st.session_state:
    st.session_state.retrain_models_check = []
if "done_models_check" not in st.session_state:
    st.session_state.done_models_check = {}

    
def gw_post(endpoint: str, payload=None, form_data=None):
    url = f"{GATEWAY_URL}{endpoint}"
    try:
        if form_data is not None:
            return st.session_state.session.post(url, data=form_data)
        return st.session_state.session.post(url, json=payload)
    except requests.exceptions.ConnectionError:
        st.error("🚨 Backend non accessible")
        return None

def gw_get(endpoint: str):
    try:
        return st.session_state.session.get(f"{GATEWAY_URL}{endpoint}")
    except requests.exceptions.ConnectionError:
        st.error("🚨 Backend non accessible")
        return None

def show_response(resp, success_code=200):
    if resp is None:
        st.error("Gateway inaccessible (connexion refusée)")
        return
    if resp.status_code == success_code or resp.ok:
        try:
            st.json(resp.json())
        except Exception:
            st.code(resp.text)
    elif resp.status_code == 401:
        st.warning("Non authentifié — connectez-vous dans la barre latérale")
    elif resp.status_code == 403:
        st.warning("Accès refusé (rôle admin requis)")
    else:
        st.error(f"Erreur {resp.status_code}: {resp.text}")


_STEP_LABELS_SVM = {
    "démarrage": "⏳ Démarrage",
    "preprocessing": "🔧 Preprocessing",
    "vectorization": "📐 Vectorisation TF-IDF",
    "training": "🤖 Entraînement SVM",
    "metrics": "📊 Sauvegarde métriques",
    "terminé": "✅ Terminé",
}
_STEP_LABELS_CNN = {
    "démarrage": "⏳ Démarrage",
    "preprocessing": "🔧 Preprocessing",
    "training": "🤖 Entraînement CNN (epochs)",
    "metrics": "📊 Sauvegarde métriques",
    "terminé": "✅ Terminé",
}


def _render_one_model(s: dict, model_key: str):
    """Affiche la progression d'un seul modèle dans sa colonne."""
    label = model_key.upper()
    step_labels = _STEP_LABELS_CNN if model_key == "cnn" else _STEP_LABELS_SVM
    train_status = s.get("status", "idle")

    st.markdown(f"### 🤖 {label}")

    if train_status == "idle":
        if model_key in (st.session_state.retrain_models or []):
            st.caption("⏳ Démarrage imminent...")
        else:
            st.info("En attente")

    elif train_status == "running":
        step = s.get("step", "—")
        step_index = s.get("step_index", 0)
        total_steps = s.get("total_steps", 1)
        st.progress(
            step_index / max(total_steps, 1),
            text=step_labels.get(step, f"Étape : {step}") + f"  ({step_index}/{total_steps})",
        )
        epoch = s.get("epoch")
        total_epochs = s.get("total_epochs")
        epoch_loss = s.get("epoch_loss")
        if epoch and total_epochs:
            st.progress(
                epoch / total_epochs,
                text=f"Epoch {epoch}/{total_epochs}" + (f" | Loss : {epoch_loss:.4f}" if epoch_loss else ""),
            )
        if s.get("started_at"):
            elapsed = time.time() - s["started_at"]
            st.caption(f"Durée : {int(elapsed // 60)}m {int(elapsed % 60)}s")

    elif train_status == "done":
        st.success(f"✅ {label} terminé !")
        metrics = s.get("metrics") or {}
        if metrics:
            c1, c2 = st.columns(2)
            with c1:
                acc = metrics.get("accuracy")
                if acc is not None:
                    st.metric("Accuracy", f"{float(acc):.1%}")
            with c2:
                f1 = metrics.get("f1_macro")
                if f1 is not None:
                    st.metric("F1 macro", f"{float(f1):.1%}")
            with st.expander("Détail métriques"):
                st.json(metrics)
        dagshub_url = s.get("dagshub_url", "https://dagshub.com/Fouxy84/mlops_projects.mlflow")
        run_id = (s.get("metrics") or {}).get("mlflow_run_id")
        if run_id:
            st.markdown(f"🔗 [Voir ce run]({dagshub_url}/#/experiments/1/runs/{run_id})")
        else:
            st.markdown(f"🔗 [DagsHub/MLflow]({dagshub_url})")

    elif train_status == "error":
        st.error(f"❌ Erreur : {s.get('error', 'inconnue')}")


def render_training_progress(pending_models: list | None = None):
    """Affiche la progression en direct des deux pipelines (SVM + CNN) côte à côte."""
    if pending_models:
        labels = " + ".join(m.upper() for m in pending_models)
        st.info(f"Modèles dans la file : **{labels}**")

    resp_status = gw_get("/train/status")
    if not resp_status or not resp_status.ok:
        st.warning("Training API inaccessible.")
        return

    state = resp_status.json()

    # ── Nouveau format : {"svm": {...}, "cnn": {...}} ──────────────
    if "svm" in state and "cnn" in state:
        svm_s = state["svm"]
        cnn_s = state["cnn"]
        any_active = any(s.get("status") in ("running", "done", "error") for s in [svm_s, cnn_s])
        any_running = any(s.get("status") == "running" for s in [svm_s, cnn_s])

        if not any_active and not pending_models:
            st.info("Aucun entraînement en cours.")
            return

        col_svm, col_cnn = st.columns(2)
        with col_svm:
            _render_one_model(svm_s, "svm")
        with col_cnn:
            _render_one_model(cnn_s, "cnn")

        for m in ["svm", "cnn"]:
            if state[m].get("status") == "done" and m in (st.session_state.retrain_models or []):
                st.session_state.retrain_models = [x for x in st.session_state.retrain_models if x != m]

        if any_running or (pending_models and not any_active):
            time.sleep(2)
            st.rerun()

    # ── Ancien format compat : {"status": ..., "model_type": ...} ──
    else:
        train_status = state.get("status", "idle")
        model_type = state.get("model_type", "svm")

        # Mémoriser les résultats terminés pour affichage persistant
        if train_status in ("done", "error") and model_type:
            st.session_state.done_models[model_type] = dict(state)
            if model_type in (st.session_state.retrain_models or []):
                st.session_state.retrain_models = [x for x in st.session_state.retrain_models if x != model_type]

        # Construire la vue {"svm": ..., "cnn": ...} depuis session_state + état courant
        view = {}
        for m in ["svm", "cnn"]:
            if train_status != "idle" and state.get("model_type") == m:
                view[m] = state  # modèle actuellement actif
            elif m in st.session_state.done_models:
                view[m] = st.session_state.done_models[m]  # résultat mémorisé
            elif m in (pending_models or []):
                view[m] = {"status": "idle"}  # en attente
            else:
                view[m] = None

        has_anything = any(v is not None for v in view.values())
        if not has_anything:
            if train_status == "idle" and pending_models:
                st.caption("⏳ Démarrage imminent...")
                time.sleep(1)
                st.rerun()
            else:
                st.info("Aucun entraînement en cours.")
            return

        col_svm, col_cnn = st.columns(2)
        with col_svm:
            if view["svm"] is not None:
                _render_one_model(view["svm"], "svm")
            else:
                st.markdown("### 🤖 SVM")
                st.info("En attente")
        with col_cnn:
            if view["cnn"] is not None:
                _render_one_model(view["cnn"], "cnn")
            else:
                st.markdown("### 🤖 CNN")
                st.info("En attente")

        if train_status == "running" or (train_status == "idle" and pending_models):
            time.sleep(2)
            st.rerun()


def render_training_progress_update(pending_models: list | None = None):
    """Variante de render_training_progress dédiée à l'onglet Check Update.
    Utilise done_models_check pour ne pas interférer avec l'onglet Train."""
    if pending_models:
        labels = " + ".join(m.upper() for m in pending_models)
        st.info(f"Modèles dans la file : **{labels}**")

    resp_status = gw_get("/train/status")
    if not resp_status or not resp_status.ok:
        st.warning("Training API inaccessible.")
        return

    state = resp_status.json()

    if "svm" in state and "cnn" in state:
        svm_s = state["svm"]
        cnn_s = state["cnn"]
        any_active = any(s.get("status") in ("running", "done", "error") for s in [svm_s, cnn_s])
        any_running = any(s.get("status") == "running" for s in [svm_s, cnn_s])

        if not any_active and not pending_models:
            st.info("Aucun entraînement en cours.")
            return

        col_svm, col_cnn = st.columns(2)
        with col_svm:
            _render_one_model(svm_s, "svm")
        with col_cnn:
            _render_one_model(cnn_s, "cnn")

        for m in ["svm", "cnn"]:
            if state[m].get("status") == "done" and m in (st.session_state.retrain_models_check or []):
                st.session_state.retrain_models_check = [x for x in st.session_state.retrain_models_check if x != m]

        if any_running or (pending_models and not any_active):
            time.sleep(2)
            st.rerun()
    else:
        train_status = state.get("status", "idle")
        model_type = state.get("model_type", "svm")

        if train_status in ("done", "error") and model_type:
            st.session_state.done_models_check[model_type] = dict(state)
            if model_type in (st.session_state.retrain_models_check or []):
                st.session_state.retrain_models_check = [x for x in st.session_state.retrain_models_check if x != model_type]

        view = {}
        for m in ["svm", "cnn"]:
            if train_status != "idle" and state.get("model_type") == m:
                view[m] = state
            elif m in st.session_state.done_models_check:
                view[m] = st.session_state.done_models_check[m]
            elif m in (pending_models or []):
                view[m] = {"status": "idle"}
            else:
                view[m] = None

        has_anything = any(v is not None for v in view.values())
        if not has_anything:
            if train_status == "idle" and pending_models:
                st.caption("⏳ Démarrage imminent...")
                time.sleep(1)
                st.rerun()
            else:
                st.info("Aucun entraînement en cours.")
            return

        col_svm, col_cnn = st.columns(2)
        with col_svm:
            if view["svm"] is not None:
                _render_one_model(view["svm"], "svm")
            else:
                st.markdown("### 🤖 SVM")
                st.info("En attente")
        with col_cnn:
            if view["cnn"] is not None:
                _render_one_model(view["cnn"], "cnn")
            else:
                st.markdown("### 🤖 CNN")
                st.info("En attente")

        if train_status == "running" or (train_status == "idle" and pending_models):
            time.sleep(2)
            st.rerun()


def is_admin():
    return st.session_state.role == "admin"


# ─────────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🤖 MLOps UI")
    st.divider()

    # Auth
    st.subheader("Authentification")
    if not st.session_state.logged_in:
        username_input = st.text_input("Utilisateur", value="admin")
        password_input = st.text_input("Mot de passe", value="admin", type="password")
        if st.button("Se connecter", use_container_width=True, type="primary"):
            resp = gw_post("/login", form_data={"username": username_input, "password": password_input})
            if resp and resp.ok:
                data = resp.json()
                st.session_state.logged_in = True
                st.session_state.username = data["username"]
                st.session_state.role = data["role"]
                st.rerun()
            else:
                st.error("Identifiants invalides")
    else:
        st.success(f"Connecté : **{st.session_state.username}**")
        st.caption(f"Rôle : `{st.session_state.role}`")
        if st.button("Se déconnecter", use_container_width=True):
            gw_post("/logout")
            st.session_state.logged_in = False
            st.session_state.username = None
            st.session_state.role = None
            st.session_state.session = requests.Session()
            st.rerun()

    st.divider()
    st.subheader("Liens externes")
    st.markdown(f"[Grafana]({GRAFANA_URL}) • [Airflow]({AIRFLOW_URL}) • [Prometheus]({PROMETHEUS_URL})")
    st.markdown(f"[Swagger UI]({GATEWAY_URL}/docs)")


# ─────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────
st.title("MLOps Dashboard")

tab_intro, tab_predict, tab_train, tab_check, tab_monitoring = st.tabs([
    "1 · Intro",
    "2 · Prédiction",
    "3 · Train & Retrain",
    "4 · Check Update",
    "📊 Monitoring",
])


# ═══════════════════════════════════════════════════════
# 1 · INTRO — health, me, info
# ═══════════════════════════════════════════════════════
with tab_intro:
    st.header("Intro — Santé & Informations système")

    col_h, col_me, col_info = st.columns(3)
    with col_h:
        if st.button("🔍 Gateway health", use_container_width=True):
            show_response(gw_get("/health"))
    with col_me:
        if st.button("👤 Qui suis-je ? (/me)", use_container_width=True):
            show_response(gw_get("/me"))
    with col_info:
        if st.button("ℹ️ Info système (/info)", use_container_width=True):
            show_response(gw_get("/info"))

    st.divider()
    st.subheader("Plan des endpoints")
    resp = gw_get("/")
    if resp and resp.ok:
        data = resp.json()
        sections = data.get("sections", {})
        cols = st.columns(len(sections))
        for col, (section_name, endpoints) in zip(cols, sections.items()):
            with col:
                st.markdown(f"**{section_name.replace('_', ' ').title()}**")
                for label, path in endpoints.items():
                    st.caption(f"`{path}`")
    else:
        st.info("Lancez le gateway pour afficher le plan des endpoints.")


# ═══════════════════════════════════════════════════════
# 2 · PREDICTION — SVM, CNN, Multimodal
# ═══════════════════════════════════════════════════════
with tab_predict:
    st.header("Prédiction")

    if not st.session_state.logged_in:
        st.warning("Connectez-vous pour effectuer des prédictions.")
    else:
        p_svm, p_cnn, p_multi = st.tabs(["SVM (texte)", "CNN (image)", "Multimodal"])

        with p_svm:
            st.subheader("Prédiction SVM — texte produit")
            text_val = st.text_area(
                "Texte du produit",
                "le tableau de chat est tres joli",
                key="svm_text",
            )
            if st.button("Prédire (SVM)", type="primary", key="btn_svm"):
                with st.spinner("Prédiction en cours..."):
                    resp = gw_post("/predict/svm", payload={"text": text_val})
                    if resp and resp.ok:
                        data = resp.json()
                        col_a, col_b = st.columns(2)
                        with col_a:
                            st.metric("Catégorie prédite", data.get("label_name", "—"))
                            st.caption(f"Label ID : `{data.get('predicted_label', '—')}`")
                        with col_b:
                            st.json(data)
                    else:
                        show_response(resp)

        with p_cnn:
            st.subheader("Prédiction CNN — image produit")
            img_val = st.text_input(
                "Nom du fichier image",
                "image_528113_product_923222.jpg",
                key="cnn_img",
            )
            if st.button("Prédire (CNN)", type="primary", key="btn_cnn"):
                with st.spinner("Prédiction en cours..."):
                    resp = gw_post("/predict/cnn", payload={"image_path": img_val})
                    if resp and resp.ok:
                        data = resp.json()
                        col_a, col_b = st.columns(2)
                        with col_a:
                            st.metric("Catégorie prédite", data.get("label_name", "—"))
                            st.caption(f"Label ID : `{data.get('predicted_label', '—')}`")
                        with col_b:
                            st.json(data)
                    else:
                        show_response(resp)

        with p_multi:
            st.subheader("Prédiction multimodale — texte + image")
            m_text = st.text_area(
                "Texte",
                "le tableau de chat est tres joli",
                key="multi_text",
            )
            m_img = st.text_input(
                "Image",
                "image_528113_product_923222.jpg",
                key="multi_img",
            )
            if st.button("Prédire (Multimodal)", type="primary", key="btn_multi"):
                with st.spinner("Prédiction en cours..."):
                    resp = gw_post("/predict/multimodal", payload={"text": m_text, "image_path": m_img})
                    if resp and resp.ok:
                        data = resp.json()
                        col_a, col_b = st.columns(2)
                        with col_a:
                            st.metric("Label prédit", data.get("label_name", "—"))
                            st.caption(f"Stratégie : `{data.get('fusion_strategy', '—')}`")
                        with col_b:
                            st.json(data)
                    else:
                        show_response(resp)


# ═══════════════════════════════════════════════════════
# 3 · TRAIN & RETRAIN — direct API + live progress
# ═══════════════════════════════════════════════════════
with tab_train:
    st.header("Train & Retrain — Suivi en direct")

    if not is_admin():
        st.warning("Section réservée aux administrateurs.")
    else:
        # ── Déclenchement ──────────────────────────────────
        st.subheader("Déclencher un entraînement")
        col_mode, col_model = st.columns(2)
        with col_mode:
            mode = st.radio("Mode", ["train", "retrain"], horizontal=True)
        with col_model:
            model_choice = st.radio("Modèle", ["svm", "cnn"], horizontal=True)

        if st.button(f"🚀 Lancer {mode.upper()} — {model_choice.upper()}", type="primary", use_container_width=True):
            endpoint = f"/{mode}/{model_choice}"
            resp = gw_post(endpoint)
            if resp and resp.ok:
                st.session_state.retrain_models = [model_choice]
                st.session_state.done_models = {}
                st.rerun()
            else:
                show_response(resp)

        st.divider()

        # ── Suivi en direct ────────────────────────────────
        st.subheader("Progression en direct")
        render_training_progress(pending_models=st.session_state.retrain_models or None)

        st.divider()

        # ── Reload ─────────────────────────────────────────
        st.subheader("Recharger les modèles en production")
        col_r1, col_r2 = st.columns(2)
        with col_r1:
            if st.button("🔄 Reload SVM", use_container_width=True):
                show_response(gw_post("/reload/svm"))
        with col_r2:
            if st.button("🔄 Reload CNN", use_container_width=True):
                show_response(gw_post("/reload/cnn"))


# ═══════════════════════════════════════════════════════
# 4 · CHECK UPDATE — scan, baseline, retrain auto
# ═══════════════════════════════════════════════════════
with tab_check:
    st.header("Check Update — Surveillance des données")

    if not is_admin():
        st.warning("Section réservée aux administrateurs.")
    else:
        st.caption("Scanne les répertoires `data/raw` pour détecter de nouveaux fichiers CSV ou images.")

        col_scan, col_base, col_retrain = st.columns(3)

        with col_scan:
            st.subheader("Scanner")
            st.write("Compare le répertoire data actuel avec la baseline sauvegardée.")
            if st.button("🔍 Scan des nouveautés", use_container_width=True, key="btn_scan"):
                with st.spinner("Scan en cours..."):
                    resp = gw_get("/data/check-updates")
                    if resp and resp.ok:
                        data = resp.json()
                        changes = data.get("changes", {})
                        img_ch = changes.get("image", {})
                        csv_ch = changes.get("csv", {})
                        csv_changes = csv_ch.get("changes", {})

                        # ── X_train_update.csv ───────────────────────
                        st.markdown("**📄 `X_train_update.csv`**")
                        if not csv_ch.get("current"):
                            st.warning("Fichier introuvable")
                        else:
                            cur = csv_ch.get("current", {})
                            rows_added = csv_changes.get("rows_added", 0)
                            col_r, col_h = st.columns(2)
                            with col_r:
                                st.metric(
                                    "Lignes",
                                    cur.get("row_count", "—"),
                                    delta=rows_added if rows_added != 0 else None,
                                )
                            with col_h:
                                hash_changed = csv_changes.get("hash_changed", False)
                                st.metric(
                                    "Hash MD5 modifié",
                                    "✅ Oui" if hash_changed else "✗ Non",
                                )
                            if csv_ch.get("has_changed"):
                                st.success("⚠️ Nouvelles lignes détectées — retrain SVM recommandé")
                            else:
                                st.info("Aucun changement dans le CSV")

                        # ── Nouvelles images ─────────────────────────
                        st.markdown("**🖼️ Images (`image_train/`)**")
                        new_img_count = img_ch.get("new_count", len(img_ch.get("new_files", [])))
                        cur_img_count = img_ch.get("current_count", "—")
                        prev_img_count = img_ch.get("previous_count")
                        st.metric(
                            "Images dans le dossier",
                            cur_img_count,
                            delta=new_img_count if new_img_count else None,
                        )
                        if new_img_count:
                            st.success(f"⚠️ {new_img_count} nouvelles images détectées — retrain CNN recommandé")
                        else:
                            st.info("Aucune nouvelle image")
                    else:
                        show_response(resp)

        with col_base:
            st.subheader("Baseline")
            st.write("Enregistre l'état actuel des données comme référence.")
            if st.button("💾 Sauvegarder la baseline", use_container_width=True, key="btn_base"):
                with st.spinner("Sauvegarde..."):
                    resp = gw_post("/data/check-updates/baseline")
                    if resp and resp.ok:
                        st.success("Baseline sauvegardée !")
                        st.json(resp.json())
                    else:
                        show_response(resp)

        with col_retrain:
            st.subheader("Retrain auto")
            st.write("Déclenche un retrain si de nouveaux fichiers ont été détectés.")
            if st.button("⚡ Retrain sur nouveaux fichiers", use_container_width=True, key="btn_retrain", type="primary"):
                with st.spinner("Analyse et déclenchement..."):
                    resp = gw_post("/data/check-updates/retrain")
                    if resp and resp.ok:
                        data = resp.json()
                        if data.get("status") in ("no_new_files", "no_change"):
                            st.info("Aucun nouveau fichier détecté — retrain non déclenché.")
                            st.session_state.retrain_models_check = []
                        else:
                            triggered = data.get("triggered_models", [])
                            st.session_state.retrain_models_check = triggered
                            st.session_state.done_models_check = {}
                            st.session_state.retrain_triggered_at = time.time()
                            st.success(f"✅ Retrain lancé pour : {' + '.join(m.upper() for m in triggered)}")
                        st.json(data)
                    else:
                        show_response(resp)

        st.divider()
        st.subheader("Progression du retrain en direct")
        render_training_progress_update(pending_models=st.session_state.retrain_models_check or None)


# ═══════════════════════════════════════════════════════
# MONITORING — Prometheus metrics + liens Grafana
# ═══════════════════════════════════════════════════════
with tab_monitoring:
    st.header("Monitoring")

    st.subheader("Grafana — Tableau de bord")
    st.markdown(
        f"""
        Le dashboard Grafana centralise :
        - État des services (`up`)
        - Requêtes par endpoint (`mlops_gateway_requests_total`)
        - Latence (`mlops_gateway_request_duration_seconds`)
        - Appels upstream (`mlops_gateway_upstream_calls_total`)

        👉 [Ouvrir Grafana]({GRAFANA_URL}/d/mlops-dashboard/mlops-pipeline-monitoring?orgId=1)
        """
    )
    st.components.v1.iframe(
        f"{GRAFANA_URL}/d/mlops-dashboard/mlops-pipeline-monitoring?orgId=1&refresh=10s&kiosk",
        height=800,
        scrolling=True,
    )

    st.divider()
    st.subheader("Métriques Prometheus (gateway)")
    if st.button("Actualiser les métriques", use_container_width=True, key="btn_metrics"):
        try:
            resp = st.session_state.session.get(f"{GATEWAY_URL}/metrics")
            if resp.ok:
                lines = [l for l in resp.text.splitlines() if not l.startswith("#") and l.strip()]
                mlops_lines = [l for l in lines if l.startswith("mlops_")]
                other_lines = [l for l in lines if not l.startswith("mlops_")]

                if mlops_lines:
                    st.markdown("**Métriques MLOps**")
                    st.code("\n".join(mlops_lines), language="text")
                if other_lines:
                    with st.expander("Métriques système (Python/FastAPI)"):
                        st.code("\n".join(other_lines[:40]), language="text")
            else:
                st.warning(f"Prometheus retourne {resp.status_code}")
        except Exception as e:
            st.error(f"Erreur : {e}")

    st.divider()
    st.subheader("Derive des données (Evidently)")
    st.info(
        "Pour générer un rapport de dérive, exécutez `python monitoring/check_data_drift.py` "
        "ou consultez les rapports HTML dans `monitoring/reports/`."
    )
    # Show last report if available
    import pathlib
    reports_dir = pathlib.Path(__file__).resolve().parents[2] / "monitoring" / "reports"
    html_reports = sorted(reports_dir.glob("*.html"), reverse=True) if reports_dir.exists() else []
    if html_reports:
        latest = html_reports[0]
        st.caption(f"Dernier rapport : `{latest.name}`")
        with st.expander("Afficher le rapport HTML"):
            st.components.v1.html(latest.read_text(encoding="utf-8"), height=1000, scrolling=True)
    else:
        st.caption("Aucun rapport disponible pour l'instant.")
