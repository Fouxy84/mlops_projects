# -*- coding: utf-8 -*-
"""
Gestionnaire d'authentification pour Streamlit
"""
import streamlit as st
import hashlib
import json
from datetime import datetime
from pathlib import Path

# Fichier de stockage des sessions
USERS_FILE = Path(__file__).parent / "users_db.json"

# Données d'authentification en dur (production: utiliser une vraie BD)
DEFAULT_USERS = {
    "admin": {
        "password_hash": hashlib.sha256("admin123".encode()).hexdigest(),
        "role": "admin",
        "permissions": ["view_all", "train", "inference", "upload_data", "ci_cd", "monitoring"]
    },
    "user": {
        "password_hash": hashlib.sha256("user123".encode()).hexdigest(),
        "role": "user",
        "permissions": ["inference", "view_tests", "view_monitoring"]
    },
    "scientist": {
        "password_hash": hashlib.sha256("scientist123".encode()).hexdigest(),
        "role": "scientist",
        "permissions": ["inference", "train", "view_all", "monitoring", "upload_data"]
    }
}

def hash_password(password: str) -> str:
    """Hash un mot de passe."""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, password_hash: str) -> bool:
    """Vérifie un mot de passe contre son hash."""
    return hash_password(password) == password_hash

def load_users():
    """Charge les utilisateurs depuis le fichier ou utilise les données par défaut."""
    if USERS_FILE.exists():
        try:
            with open(USERS_FILE, 'r') as f:
                return json.load(f)
        except:
            return DEFAULT_USERS.copy()
    return DEFAULT_USERS.copy()

def save_users(users):
    """Sauvegarde les utilisateurs dans le fichier."""
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=2)

def init_session_state():
    """Initialise l'état de session pour l'authentification."""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "username" not in st.session_state:
        st.session_state.username = None
    if "role" not in st.session_state:
        st.session_state.role = None
    if "permissions" not in st.session_state:
        st.session_state.permissions = []
    if "login_time" not in st.session_state:
        st.session_state.login_time = None

def authenticate(username: str, password: str) -> bool:
    """Authentifie un utilisateur."""
    users = load_users()
    
    if username not in users:
        return False
    
    user = users[username]
    if verify_password(password, user["password_hash"]):
        st.session_state.authenticated = True
        st.session_state.username = username
        st.session_state.role = user["role"]
        st.session_state.permissions = user["permissions"]
        st.session_state.login_time = datetime.now().isoformat()
        return True
    
    return False

def logout():
    """Déconnecte l'utilisateur."""
    st.session_state.authenticated = False
    st.session_state.username = None
    st.session_state.role = None
    st.session_state.permissions = []
    st.session_state.login_time = None

def has_permission(permission: str) -> bool:
    """Vérifie si l'utilisateur a une permission."""
    return permission in st.session_state.get("permissions", [])

def check_permission(permission: str, error_message: str = "Permission refusée"):
    """Vérifie une permission et affiche une erreur si nécessaire."""
    if not has_permission(permission):
        st.error(f"❌ {error_message}")
        return False
    return True

def render_login_page():
    """Affiche la page de connexion."""
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.title("🔐 Authentification")
        st.markdown("---")
        
        st.markdown("### Connexion au Dashboard MLOps")
        
        username = st.text_input(
            "Nom d'utilisateur",
            placeholder="Entrez votre identifiant",
            key="login_username"
        )
        
        password = st.text_input(
            "Mot de passe",
            type="password",
            placeholder="Entrez votre mot de passe",
            key="login_password"
        )
        
        col_login, col_demo = st.columns(2)
        
        with col_login:
            if st.button("🔓 Connexion", use_container_width=True):
                if not username or not password:
                    st.error("❌ Veuillez remplir tous les champs")
                elif authenticate(username, password):
                    st.success(f"✅ Bienvenue {username}!")
                    st.balloons()
                    st.rerun()
                else:
                    st.error("❌ Identifiant ou mot de passe incorrect")
        
        with col_demo:
            if st.button("👁️ Comptes démo", use_container_width=True):
                st.info("""
                **Comptes de démonstration:**
                
                👤 **Admin**
                - ID: `admin` | MDP: `admin123`
                - Accès: Tous les modules
                
                👤 **Scientifique**
                - ID: `scientist` | MDP: `scientist123`
                - Accès: Train, Inference, Upload données
                
                👤 **Utilisateur**
                - ID: `user` | MDP: `user123`
                - Accès: Inference, Tests, Monitoring
                """)
        
        st.markdown("---")
        st.markdown("""
        <div style="text-align: center; color: #666;">
        <small>Dashboard MLOps - Rakuten Challenge | Phase 3 Deployment</small>
        </div>
        """, unsafe_allow_html=True)

def render_auth_header():
    """Affiche l'en-tête avec les infos d'authentification."""
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.markdown(f"### 👤 Connecté: **{st.session_state.username}** | Rôle: **{st.session_state.role.upper()}**")
    
    with col3:
        if st.button("🚪 Déconnexion", use_container_width=True):
            logout()
            st.rerun()
