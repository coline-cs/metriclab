#!/usr/bin/env python3
"""
Authentification Supabase Auth — login / signup / logout.
"""
import os
import streamlit as st
from supabase import create_client, Client

_auth_client: Client | None = None


def _get_client() -> Client | None:
    global _auth_client
    if _auth_client:
        return _auth_client
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_KEY", "")
    if not url or not key:
        return None
    _auth_client = create_client(url, key)
    return _auth_client


def get_current_user() -> dict | None:
    """Retourne l'utilisateur connecté depuis session_state, ou None."""
    return st.session_state.get("_auth_user")


def get_current_user_id() -> str | None:
    user = get_current_user()
    return user["id"] if user else None


def sign_up(email: str, password: str) -> tuple[bool, str]:
    client = _get_client()
    if not client:
        return False, "Supabase non configuré."
    try:
        res = client.auth.sign_up({"email": email, "password": password})
        if res.user:
            st.session_state["_auth_user"] = {
                "id": res.user.id,
                "email": res.user.email,
            }
            st.session_state["_auth_session"] = res.session
            return True, ""
        return False, "Inscription échouée."
    except Exception as e:
        msg = str(e)
        if "already registered" in msg or "already been registered" in msg:
            return False, "Cet email est déjà utilisé."
        return False, msg


def sign_in(email: str, password: str) -> tuple[bool, str]:
    client = _get_client()
    if not client:
        return False, "Supabase non configuré."
    try:
        res = client.auth.sign_in_with_password({"email": email, "password": password})
        if res.user:
            st.session_state["_auth_user"] = {
                "id": res.user.id,
                "email": res.user.email,
            }
            st.session_state["_auth_session"] = res.session
            return True, ""
        return False, "Email ou mot de passe incorrect."
    except Exception as e:
        msg = str(e)
        if "Invalid login" in msg or "invalid_credentials" in msg:
            return False, "Email ou mot de passe incorrect."
        return False, msg


def sign_out():
    client = _get_client()
    if client:
        try:
            client.auth.sign_out()
        except Exception:
            pass
    st.session_state.pop("_auth_user", None)
    st.session_state.pop("_auth_session", None)


def render_login_page():
    """Affiche la page de connexion / inscription et bloque le reste de l'app."""
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=League+Spartan:wght@700;800;900&display=swap');
    [data-testid="stAppViewContainer"] { background: #0a0a0a !important; }
    [data-testid="stHeader"] { background: transparent !important; }
    [data-testid="stMainBlockContainer"] { padding-top: 0 !important; }

    .auth-wrap {
        min-height: 100vh;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 40px 16px;
    }
    .auth-logo {
        font-family: 'League Spartan', sans-serif;
        font-weight: 900;
        font-size: 2rem;
        letter-spacing: -0.04em;
        color: #fff;
        margin-bottom: 4px;
        text-align: center;
    }
    .auth-tagline {
        text-align: center;
        color: #444;
        font-size: 0.72rem;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        margin-bottom: 32px;
    }

    /* Override Streamlit tab underline bleu */
    .stTabs [data-baseweb="tab-list"] {
        background: #1a1a1a !important;
        border-radius: 8px !important;
        padding: 3px !important;
        gap: 2px !important;
        box-shadow: none !important;
    }
    .stTabs [data-baseweb="tab"] {
        background: transparent !important;
        color: #555 !important;
        border-radius: 6px !important;
        font-size: 0.82rem !important;
        padding: 6px 14px !important;
    }
    .stTabs [aria-selected="true"] {
        background: #2a2a2a !important;
        color: #fff !important;
    }

    /* Inputs dark */
    .stTextInput input {
        background: #1a1a1a !important;
        color: #e0e0e0 !important;
        border: 1px solid #2a2a2a !important;
        border-radius: 8px !important;
    }
    .stTextInput input:focus {
        border-color: #fff !important;
        box-shadow: none !important;
    }
    .stTextInput label {
        color: #555 !important;
        font-size: 0.78rem !important;
    }

    /* Bouton primaire blanc sur noir */
    .stButton > button[kind="primary"] {
        background: #ffffff !important;
        color: #0a0a0a !important;
        font-weight: 700 !important;
        border: none !important;
        border-radius: 8px !important;
        font-size: 0.88rem !important;
        letter-spacing: -0.01em !important;
    }
    .stButton > button[kind="primary"]:hover {
        background: #e0e0e0 !important;
        transform: translateY(-1px) !important;
    }
    </style>
    """, unsafe_allow_html=True)

    col = st.columns([1, 2, 1])[1]
    with col:
        st.markdown('<div class="auth-logo">metric lab</div>', unsafe_allow_html=True)
        st.markdown('<div class="auth-tagline">Intelligence · Analyse · Prédiction</div>', unsafe_allow_html=True)

        tab_login, tab_signup = st.tabs(["Connexion", "Créer un compte"])

        with tab_login:
            email = st.text_input("Email", key="_login_email", placeholder="ton@email.com")
            password = st.text_input("Mot de passe", type="password", key="_login_pass", placeholder="••••••••")
            if st.button("Se connecter", use_container_width=True, type="primary"):
                if not email or not password:
                    st.error("Remplis les deux champs.")
                else:
                    ok, err = sign_in(email.strip(), password)
                    if ok:
                        st.rerun()
                    else:
                        st.error(err)

        with tab_signup:
            email2 = st.text_input("Email", key="_signup_email", placeholder="ton@email.com")
            password2 = st.text_input("Mot de passe", type="password", key="_signup_pass", placeholder="8 caractères minimum")
            password2b = st.text_input("Confirme le mot de passe", type="password", key="_signup_pass2", placeholder="••••••••")
            if st.button("Créer mon compte", use_container_width=True, type="primary"):
                if not email2 or not password2:
                    st.error("Remplis les deux champs.")
                elif password2 != password2b:
                    st.error("Les mots de passe ne correspondent pas.")
                elif len(password2) < 8:
                    st.error("Le mot de passe doit faire au moins 8 caractères.")
                else:
                    ok, err = sign_up(email2.strip(), password2)
                    if ok:
                        st.success("Compte créé ! Bienvenue.")
                        st.rerun()
                    else:
                        st.error(err)
    st.stop()
