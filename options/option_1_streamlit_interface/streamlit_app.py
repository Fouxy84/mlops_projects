import os

import requests
import streamlit as st


GATEWAY_URL = os.getenv("GATEWAY_URL", "http://localhost:8000")
GRAFANA_URL = os.getenv("GRAFANA_URL", "http://localhost:3000")
AIRFLOW_URL = os.getenv("AIRFLOW_URL", "http://localhost:8080")
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


def gw_post(endpoint: str, payload=None, form_data=None):
    url = f"{GATEWAY_URL}{endpoint}"
    try:
        if form_data is not None:
            return st.session_state.session.post(url, data=form_data, timeout=30)
        return st.session_state.session.post(url, json=payload, timeout=30)
    except requests.exceptions.ConnectionError:
        return None


def gw_get(endpoint: str):
    try:
        return st.session_state.session.get(f"{GATEWAY_URL}{endpoint}", timeout=15)
    except requests.exceptions.ConnectionError:
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
                    show_response(gw_post("/predict/svm", payload={"text": text_val}))

        with p_cnn:
            st.subheader("Prédiction CNN — image produit")
            img_val = st.text_input(
                "Nom du fichier image",
                "image_528113_product_923222.jpg",
                key="cnn_img",
            )
            if st.button("Prédire (CNN)", type="primary", key="btn_cnn"):
                with st.spinner("Prédiction en cours..."):
                    show_response(gw_post("/predict/cnn", payload={"image_path": img_val}))

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
# 3 · TRAIN & RETRAIN — Airflow, status, reload
# ═══════════════════════════════════════════════════════
with tab_train:
    st.header("Train & Retrain — Orchestration Airflow")

    if not is_admin():
        st.warning("Section réservée aux administrateurs.")
    else:
        st.caption("Chaque action déclenche le DAG Airflow `mlops_orchestration` avec le mode et le modèle choisis.")

        # Trigger
        st.subheader("Déclencher un entraînement")
        col_mode, col_model = st.columns(2)
        with col_mode:
            mode = st.radio("Mode", ["train", "retrain"], horizontal=True)
        with col_model:
            model = st.radio("Modèle", ["svm", "cnn"], horizontal=True)

        if st.button(f"🚀 Lancer {mode.upper()} — {model.upper()}", type="primary", use_container_width=True):
            with st.spinner(f"Déclenchement du DAG ({mode}/{model})..."):
                resp = gw_post(f"/orchestrate/{mode}/{model}")
                if resp and resp.ok:
                    data = resp.json()
                    st.success(f"DAG déclenché ! `dag_run_id` : `{data.get('dag_run_id')}`")
                    st.session_state["last_dag_run_id"] = data.get("dag_run_id")
                    st.json(data)
                else:
                    show_response(resp)

        st.divider()

        # Status
        st.subheader("Vérifier le statut d'un DAG run")
        dag_run_id = st.text_input(
            "dag_run_id",
            value=st.session_state.get("last_dag_run_id", ""),
            placeholder="scheduled__2026-04-20T00:00:00+00:00",
        )
        if st.button("Vérifier le statut", use_container_width=True):
            if dag_run_id:
                with st.spinner("Interrogation Airflow..."):
                    resp = gw_get(f"/orchestrate/status/{dag_run_id}")
                    if resp and resp.ok:
                        data = resp.json()
                        state = data.get("state", "unknown")
                        state_color = {"success": "✅", "failed": "❌", "running": "⏳", "queued": "🕐"}.get(state, "❓")
                        st.metric("État", f"{state_color} {state}")
                        st.json(data)
                    else:
                        show_response(resp)
            else:
                st.info("Entrez un dag_run_id.")

        st.divider()

        # Reload
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
                        text_ch = changes.get("text", {})
                        img_ch = changes.get("image", {})
                        col_t, col_i = st.columns(2)
                        with col_t:
                            st.metric("Nouveaux CSV", len(text_ch.get("new_files", [])))
                            if text_ch.get("new_files"):
                                st.write(text_ch["new_files"])
                        with col_i:
                            st.metric("Nouvelles images", len(img_ch.get("new_files", [])))
                            if img_ch.get("new_files"):
                                st.write(img_ch["new_files"])
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
                        if data.get("status") == "no_new_files":
                            st.info("Aucun nouveau fichier détecté — retrain non déclenché.")
                        else:
                            st.success(f"Retrain lancé pour : {data.get('triggered_models', [])}")
                        st.json(data)
                    else:
                        show_response(resp)


# ═══════════════════════════════════════════════════════
# MONITORING — Prometheus metrics + liens Grafana
# ═══════════════════════════════════════════════════════
with tab_monitoring:
    st.header("Monitoring")

    col_prom, col_graf = st.columns([1, 1])

    with col_prom:
        st.subheader("Métriques Prometheus (gateway)")
        if st.button("Actualiser les métriques", use_container_width=True, key="btn_metrics"):
            try:
                resp = st.session_state.session.get(f"{GATEWAY_URL}/metrics", timeout=10)
                if resp.ok:
                    lines = [l for l in resp.text.splitlines() if not l.startswith("#") and l.strip()]
                    # Group by metric family
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

    with col_graf:
        st.subheader("Grafana — Tableau de bord")
        st.markdown(
            f"""
            Le dashboard Grafana centralise :
            - État des services (`up`)
            - Requêtes par endpoint (`mlops_gateway_requests_total`)
            - Latence (`mlops_gateway_request_duration_seconds`)
            - Appels upstream (`mlops_gateway_upstream_calls_total`)

            👉 [Ouvrir Grafana]({GRAFANA_URL})
            """
        )
        st.components.v1.iframe(
            f"{GRAFANA_URL}/d/mlops/mlops-dashboard?orgId=1&refresh=10s&kiosk",
            height=420,
            scrolling=True,
        )

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
            st.components.v1.html(latest.read_text(encoding="utf-8"), height=600, scrolling=True)
    else:
        st.caption("Aucun rapport disponible pour l'instant.")
