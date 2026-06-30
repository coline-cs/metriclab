#!/usr/bin/env python3
"""
Meta Ads Intelligence — Interface web Streamlit
Lance avec : streamlit run app.py
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import streamlit as st

# Auth — doit être importé avant st.set_page_config
try:
    from auth import get_current_user, get_current_user_id, render_login_page, sign_out
    AUTH_AVAILABLE = True
except ImportError:
    AUTH_AVAILABLE = False

BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "transcriptions"
GENERATED_DIR = BASE_DIR / "generated_copy"
PYTHON = str(BASE_DIR / ".venv" / "bin" / "python")

OUTPUT_DIR.mkdir(exist_ok=True)
GENERATED_DIR.mkdir(exist_ok=True)

# Imports optionnels (nouveaux modules)
AGENT_AVAILABLE = False
SCORER_AVAILABLE = False
try:
    sys.path.insert(0, str(BASE_DIR))
    from product_context import load_context, save_context, scrape_website, format_for_prompt
    from agent import ScriptExpertAgent
    AGENT_AVAILABLE = True
except ImportError:
    pass
try:
    from scorer import load_scoring_context, save_scoring_context, score_ad
    SCORER_AVAILABLE = True
except ImportError:
    pass

BRANDS_AVAILABLE = False
try:
    from brands import load_brands, save_brands, add_brand, remove_brand, update_brand_stats, load_sections, save_sections, add_section, remove_section
    BRANDS_AVAILABLE = True
except ImportError:
    pass

DECK_AVAILABLE = False
try:
    from script_deck import ANGLES, AWARENESS_LEVELS, generate_deck_stream
    DECK_AVAILABLE = True
except ImportError:
    pass

# ──────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────
st.set_page_config(
    page_title="metric lab",
    page_icon="⬛",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Auth gate ────────────────────────────────
if AUTH_AVAILABLE:
    if not get_current_user():
        render_login_page()

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=League+Spartan:wght@400;600;700;800;900&display=swap');

/* ── Base ── */
html, body, [data-testid="stAppViewContainer"] {
    background: #f5f5f5 !important;
    color: #0a0a0a !important;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif !important;
}
[data-testid="stHeader"] { background: transparent !important; box-shadow: none !important; }
[data-testid="stMainBlockContainer"] { padding-top: 0 !important; }

/* ── Labels ── */
label, .stTextInput label, .stTextArea label,
.stSelectbox label, .stSlider label,
div[data-testid="stWidgetLabel"] p,
div[data-testid="stWidgetLabel"] {
    color: #0a0a0a !important;
    font-weight: 600 !important;
    font-size: .88rem !important;
    letter-spacing: .01em !important;
}

/* ── Inputs ── */
input, textarea, .stTextInput input, .stTextArea textarea {
    background: #ffffff !important;
    color: #0a0a0a !important;
    border: 1.5px solid #e0e0e0 !important;
    border-radius: 10px !important;
    font-size: .9rem !important;
}
input:focus, textarea:focus {
    border-color: #0a0a0a !important;
    box-shadow: 0 0 0 3px rgba(10,10,10,.08) !important;
}
input::placeholder, textarea::placeholder { color: #b0b0b0 !important; }

/* ── Selectbox ── */
.stSelectbox div[data-baseweb="select"] > div {
    background: #ffffff !important;
    color: #0a0a0a !important;
    border: 1.5px solid #e0e0e0 !important;
    border-radius: 10px !important;
}

/* ── Navigation principale ── */
div[data-testid="stSegmentedControl"],
div[data-testid="stButtonGroup"] {
    background: #ffffff !important;
    border-radius: 14px !important;
    padding: 5px 6px !important;
    box-shadow: 0 1px 3px rgba(0,0,0,.07), 0 0 0 1px rgba(0,0,0,.04) !important;
    gap: 2px !important;
    overflow-x: auto !important;
}
div[data-testid="stSegmentedControl"] button,
div[data-testid="stButtonGroup"] button {
    border-radius: 9px !important;
    font-weight: 500 !important;
    font-size: .81rem !important;
    border: none !important;
    color: #666 !important;
    background: transparent !important;
    transition: all 0.12s ease !important;
    white-space: nowrap !important;
    padding: 6px 12px !important;
}
div[data-testid="stSegmentedControl"] button:hover,
div[data-testid="stButtonGroup"] button:hover {
    background: #f0f0f0 !important;
    color: #0a0a0a !important;
}
div[data-testid="stSegmentedControl"] button[aria-checked="true"],
div[data-testid="stButtonGroup"] button[aria-checked="true"],
div[data-testid="stSegmentedControl"] button[kind="segmented_controlActive"],
div[data-testid="stButtonGroup"] button[kind="segmented_controlActive"] {
    background: #0a0a0a !important;
    color: #ffffff !important;
    box-shadow: 0 2px 6px rgba(0,0,0,.20) !important;
}

/* ── Onglets ── */
.stTabs [data-baseweb="tab-list"] {
    background: #ffffff !important;
    border-radius: 10px !important;
    padding: 4px !important;
    box-shadow: 0 1px 3px rgba(0,0,0,.07) !important;
    gap: 3px !important;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    color: #666 !important;
    border-radius: 7px !important;
    font-weight: 500 !important;
    padding: 7px 14px !important;
}
.stTabs [aria-selected="true"] {
    background: #0a0a0a !important;
    color: #ffffff !important;
}

/* ── Boutons primaires ── */
.stButton > button {
    border-radius: 10px !important;
    font-weight: 600 !important;
    font-size: .88rem !important;
    border: none !important;
    transition: all 0.12s ease !important;
    cursor: pointer !important;
    letter-spacing: .01em !important;
}
.stButton > button[kind="primary"] {
    background: #0a0a0a !important;
    color: #ffffff !important;
    box-shadow: 0 1px 3px rgba(0,0,0,.15) !important;
}
.stButton > button[kind="primary"]:hover {
    background: #222 !important;
    box-shadow: 0 4px 14px rgba(0,0,0,.22) !important;
    transform: translateY(-1px) !important;
}
.stButton > button[kind="primary"]:active { transform: translateY(0) !important; }
.stButton > button:not([kind="primary"]) {
    background: #ffffff !important;
    color: #0a0a0a !important;
    border: 1.5px solid #e0e0e0 !important;
}
.stButton > button:not([kind="primary"]):hover {
    background: #f5f5f5 !important;
    border-color: #0a0a0a !important;
    transform: translateY(-1px) !important;
}
.stButton > button:disabled {
    opacity: 0.35 !important;
    cursor: not-allowed !important;
    transform: none !important;
    box-shadow: none !important;
}

/* ── Download button ── */
.stDownloadButton > button {
    border-radius: 10px !important;
    font-weight: 600 !important;
    background: #ffffff !important;
    color: #0a0a0a !important;
    border: 1.5px solid #e0e0e0 !important;
    transition: all 0.12s ease !important;
}
.stDownloadButton > button:hover {
    background: #0a0a0a !important;
    color: #fff !important;
    border-color: #0a0a0a !important;
    transform: translateY(-1px) !important;
}

/* ── Expander ── */
.streamlit-expanderHeader {
    background: #ffffff !important;
    color: #0a0a0a !important;
    border: 1px solid #e8e8e8 !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    transition: background 0.12s ease !important;
}
.streamlit-expanderHeader:hover { background: #f9f9f9 !important; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: #ffffff !important;
    border-right: 1px solid #ebebeb !important;
}

/* ── Header metric lab ── */
.ml-header {
    display: flex; align-items: center; justify-content: space-between;
    padding: 18px 0 12px; margin-bottom: 4px;
    border-bottom: 1px solid #ebebeb;
}
.ml-logo {
    font-family: 'League Spartan', 'Helvetica Neue', Arial, sans-serif;
    font-weight: 900; font-size: 1.85rem; color: #0a0a0a;
    letter-spacing: -0.04em; line-height: 1;
    display: flex; align-items: center; gap: 10px;
}
.ml-plan-badge {
    font-size: 0.55rem; font-weight: 700; letter-spacing: .06em;
    background: #0a0a0a; color: #fff;
    padding: 3px 8px; border-radius: 20px;
    text-transform: uppercase; vertical-align: middle;
}
.ml-tagline { font-size: .72rem; color: #999; font-weight: 500; margin-top: 3px; letter-spacing: .06em; text-transform: uppercase; }

/* ── Titres h3 en League Spartan ── */
h1, h2, h3 {
    font-family: 'League Spartan', 'Helvetica Neue', Arial, sans-serif !important;
    letter-spacing: -0.02em !important;
}

/* ── Stat cards ── */
.stat-card {
    background: #ffffff; border-radius: 14px; padding: 18px 20px;
    box-shadow: 0 1px 3px rgba(0,0,0,.06), 0 0 0 1px rgba(0,0,0,.04);
    text-align: center; transition: all 0.15s ease; cursor: default;
}
.stat-card:hover {
    box-shadow: 0 6px 20px rgba(0,0,0,.09), 0 0 0 1px rgba(0,0,0,.06);
    transform: translateY(-2px);
}
.stat-card .n { font-size: 2rem; font-weight: 800; color: #0a0a0a; line-height: 1; }
.stat-card .l { font-size: .72rem; color: #999; margin-top: 5px; font-weight: 500; text-transform: uppercase; letter-spacing: .04em; }

/* ── Brand row ── */
.brand-row {
    background: #ffffff; border-radius: 12px; border-left: 3px solid #0a0a0a;
    padding: 14px 18px;
    box-shadow: 0 1px 3px rgba(0,0,0,.05), 0 0 0 1px rgba(0,0,0,.03);
}
.brand-row-name { font-size: .95rem; font-weight: 700; color: #0a0a0a; margin-bottom: 5px; }
.brand-row-meta { display: flex; gap: 12px; font-size: .76rem; color: #888; flex-wrap: wrap; }
.brand-row-meta span { display: inline-flex; align-items: center; gap: 3px; }

/* ── Workflow steps ── */
.wf-bar {
    display: flex; align-items: center; gap: 0;
    background: #ffffff; border-radius: 14px;
    padding: 12px 20px; margin-bottom: 16px;
    box-shadow: 0 1px 3px rgba(0,0,0,.06), 0 0 0 1px rgba(0,0,0,.04);
}
.wf-step {
    flex: 1; text-align: center; padding: 8px 6px;
    border-radius: 8px; font-size: .8rem; font-weight: 500;
    color: #bbb; background: transparent; transition: .15s;
}
.wf-step .wf-n {
    display: inline-flex; align-items: center; justify-content: center;
    width: 22px; height: 22px; border-radius: 50%; font-size: .7rem;
    font-weight: 700; margin-right: 6px;
    background: #ebebeb; color: #999;
}
.wf-step.wf-done { color: #2d7a47; }
.wf-step.wf-done .wf-n { background: #d4edda; color: #155724; }
.wf-step.wf-active { color: #0a0a0a; font-weight: 700; }
.wf-step.wf-active .wf-n { background: #0a0a0a; color: #fff; }
.wf-arrow { color: #d8d8d8; font-size: 1.1rem; padding: 0 4px; }

/* ── Context pills ── */
.context-pill {
    display: inline-flex; align-items: center; gap: 5px;
    background: #f0f0f0; color: #0a0a0a; border-radius: 20px;
    padding: 4px 12px; font-size: .74rem; font-weight: 600; margin: 3px;
    border: 1px solid #e0e0e0;
}
.context-pill.green { background: #f0fff4; color: #2d7a47; border-color: #b2e8c5; }
.context-pill.orange { background: #fff8e6; color: #7a5a00; border-color: #ffd88a; }
.context-pill.grey { background: #f5f5f5; color: #888; border-color: #e0e0e0; }

/* ── Suggestion pills ── */
.suggestion-pill {
    display: inline-block; padding: 7px 15px; margin: 3px;
    background: #fff; border: 1.5px solid #e0e0e0;
    border-radius: 20px; font-size: .81rem; color: #333;
    cursor: pointer; transition: all 0.12s ease; user-select: none;
}
.suggestion-pill:hover {
    border-color: #0a0a0a; color: #0a0a0a;
    background: #f5f5f5; transform: translateY(-1px);
}

/* ── Chat ── */
[data-testid="stChatMessage"] {
    background: #ffffff !important;
    border-radius: 12px !important;
    border: 1px solid #ebebeb !important;
    margin-bottom: 8px !important;
    box-shadow: 0 1px 3px rgba(0,0,0,.04) !important;
}
[data-testid="stChatInput"] textarea {
    background: #ffffff !important;
    color: #0a0a0a !important;
    border: 1.5px solid #e0e0e0 !important;
    border-radius: 10px !important;
}
[data-testid="stChatInput"] textarea:focus {
    border-color: #0a0a0a !important;
    box-shadow: 0 0 0 3px rgba(10,10,10,.08) !important;
}

/* ── Empty state ── */
.empty-state-box {
    text-align: center; padding: 52px 24px; background: #ffffff;
    border-radius: 14px; border: 2px dashed #e0e0e0; color: #888; margin-top: 8px;
}
.ebox-icon { font-size: 2.4rem; margin-bottom: 12px; }
.ebox-title { font-size: 1rem; font-weight: 700; color: #0a0a0a; margin-bottom: 6px; }
.ebox-sub { font-size: .84rem; }

/* ── Slider ── */
.stSlider div[data-testid="stTickBarMin"],
.stSlider div[data-testid="stTickBarMax"] { color: #999 !important; }

/* ── Mobile responsive ── */
@media (max-width: 768px) {
    /* Header plus compact */
    .ml-logo { font-size: 1.4rem !important; }
    .ml-tagline { font-size: .65rem !important; }
    .ml-header { padding: 12px 0 8px !important; }

    /* Stats : 3 colonnes sur 2 lignes */
    [data-testid="stHorizontalBlock"]:has(.stat-card) {
        flex-wrap: wrap !important;
    }
    [data-testid="stHorizontalBlock"]:has(.stat-card) > [data-testid="column"] {
        min-width: calc(33.33% - 8px) !important;
        flex: 0 0 calc(33.33% - 8px) !important;
    }
    .stat-card { padding: 12px 8px !important; }
    .stat-card .n { font-size: 1.5rem !important; }
    .stat-card .l { font-size: .62rem !important; }

    /* Navigation : scroll horizontal, texte compact */
    div[data-testid="stSegmentedControl"],
    div[data-testid="stButtonGroup"] {
        overflow-x: auto !important;
        flex-wrap: nowrap !important;
        padding: 4px !important;
    }
    div[data-testid="stSegmentedControl"] button,
    div[data-testid="stButtonGroup"] button {
        font-size: .75rem !important;
        padding: 5px 9px !important;
        white-space: nowrap !important;
    }

    /* Colonnes formulaires : stack vertical */
    [data-testid="stHorizontalBlock"]:not(:has(.stat-card)) {
        flex-wrap: wrap !important;
    }
    [data-testid="stHorizontalBlock"]:not(:has(.stat-card)) > [data-testid="column"] {
        min-width: 100% !important;
    }

    /* Onboarding : 3 colonnes maintenues */
    .ob-steps { gap: 6px !important; }

    /* Main container padding */
    [data-testid="stMainBlockContainer"] {
        padding-left: 12px !important;
        padding-right: 12px !important;
    }
}
</style>
""", unsafe_allow_html=True)

_header_user = get_current_user() if AUTH_AVAILABLE else None
_header_plan = "Admin" if (_header_user and _header_user.get("email") == "chantelouxc@gmail.com") else ("Pro" if _header_user else "")
_badge_html = f'<span class="ml-plan-badge">{_header_plan}</span>' if _header_plan else ""
st.markdown(f"""
<div class="ml-header">
  <div>
    <div class="ml-logo">metric lab {_badge_html}</div>
    <div class="ml-tagline">Intelligence · Analyse · Prédiction</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────
# SIDEBAR — clé API + options
# ──────────────────────────────────────────────
with st.sidebar:
    if AUTH_AVAILABLE:
        user = get_current_user()
        if user:
            _initiale = user["email"][0].upper()
            _email_short = user["email"][:22] + "…" if len(user["email"]) > 22 else user["email"]
            st.markdown(f"""
            <div style="display:flex;align-items:center;gap:10px;padding:8px 0 12px;">
                <div style="width:34px;height:34px;border-radius:50%;background:#0a0a0a;color:#fff;
                    display:flex;align-items:center;justify-content:center;font-weight:700;
                    font-size:13px;flex-shrink:0;">{_initiale}</div>
                <div>
                    <div style="font-size:12px;font-weight:600;color:#0a0a0a;line-height:1.2;">Mon espace</div>
                    <div style="font-size:11px;color:#999;">{_email_short}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Se déconnecter", use_container_width=True):
                sign_out()
                st.rerun()
            st.divider()

    st.markdown("### Configuration")
    _admin_email = "chantelouxc@gmail.com"
    _current_user = get_current_user() if AUTH_AVAILABLE else None
    _is_admin = _current_user and _current_user.get("email") == _admin_email
    _api_default = os.environ.get("ANTHROPIC_API_KEY", "") if _is_admin else st.session_state.get("_user_api_key", "")
    api_key_input = st.text_input(
        "Clé Anthropic API",
        type="password",
        value=_api_default,
        help="Obtiens ta clé sur console.anthropic.com",
    )
    if api_key_input:
        # Nettoyage agressif : espaces, retours ligne, guillemets, caractères invisibles
        _clean_key = "".join(api_key_input.split()).strip('"').strip("'").strip()
        st.session_state["_user_api_key"] = _clean_key
        if _is_admin:
            os.environ["ANTHROPIC_API_KEY"] = _clean_key
        else:
            os.environ["ANTHROPIC_API_KEY"] = _clean_key  # actif pour cette session uniquement

        if _clean_key.startswith("sk-ant-admin"):
            st.error("Clé ADMIN — elle ne peut pas appeler les modèles. Crée une clé standard sur console.anthropic.com → API Keys.")
        elif not _clean_key.startswith("sk-ant-"):
            st.warning("Format inattendu — une clé Anthropic commence par `sk-ant-api…`")
        else:
            st.markdown(f'<div style="font-size:11px;color:#059669;padding:4px 0;">Clé active ···{_clean_key[-4:]}</div>', unsafe_allow_html=True)

        if st.button("🔌 Tester la clé", key="test_api_key", use_container_width=True):
            try:
                import anthropic as _ant_test
                _ant_test.Anthropic(api_key=_clean_key).models.list(limit=1)
                st.success("✅ Clé valide — tout est bon !")
            except Exception as _e_test:
                _msg = str(_e_test)
                if "401" in _msg or "authentication" in _msg.lower():
                    st.error(
                        "❌ Clé INVALIDE — l'API la rejette.\n\n"
                        "1. Va sur **console.anthropic.com** → API Keys\n"
                        "2. Crée une **nouvelle clé**\n"
                        "3. Copie-la EN ENTIER (elle commence par `sk-ant-api...`)\n"
                        "4. Recolle-la ci-dessus"
                    )
                elif "credit" in _msg.lower() or "billing" in _msg.lower():
                    st.error("❌ Problème de crédit — vérifie ton solde sur console.anthropic.com → Billing.")
                else:
                    st.error(f"❌ {_msg[:300]}")
    st.markdown("---")
    st.markdown("**Modèle Whisper**")
    whisper_model = st.selectbox(
        "Modèle Whisper", ["tiny", "base", "small", "medium"],
        index=2,  # small par défaut — bien meilleur sur le français
        label_visibility="collapsed",
        help="small = bon équilibre précision/vitesse · medium = maximum · base = rapide mais imprécis",
    )
    st.markdown("**Scrolls par page**")
    scroll_count = st.slider("Scrolls", 3, 20, 5, label_visibility="collapsed")

# ──────────────────────────────────────────────
# STATS RAPIDES
# ──────────────────────────────────────────────
json_path = OUTPUT_DIR / "all_transcriptions.json"
transcriptions = []
if json_path.exists():
    try:
        transcriptions = json.loads(json_path.read_text(encoding="utf-8"))
    except Exception:
        pass

# ── Détection d'un script sélectionné depuis le bouton iframe ──
_raw_adapt = st.query_params.get("adapt_idx")
if _raw_adapt is not None:
    try:
        _adapt_val = int(_raw_adapt)
        if 0 <= _adapt_val < len(transcriptions):
            st.session_state["adapt_prefill"] = _adapt_val
            st.session_state["_nav_to"] = "📊 Rapport"
            st.toast("Script sélectionné ! Descends jusqu'à la section Adapter ↓", icon="🎯")
    except (ValueError, TypeError):
        pass
    st.query_params.clear()

tops_count = sum(1 for r in transcriptions if r.get("label") == "Top Performers")
new_count  = sum(1 for r in transcriptions if r.get("label") == "Nouvelles Créas")
vision_count = sum(1 for r in transcriptions if r.get("visual_analysis") and isinstance(r["visual_analysis"], dict) and r["visual_analysis"])
gen_files  = list(GENERATED_DIR.glob("*.txt"))
scored_entries = [r for r in transcriptions if r.get("scoring") and isinstance(r.get("scoring"), dict) and r["scoring"].get("score_total") is not None]
avg_score = round(sum(r["scoring"]["score_total"] for r in scored_entries) / len(scored_entries), 1) if scored_entries else None

col1, col2, col3, col4, col5, col6 = st.columns(6)
with col1:
    st.markdown(f'<div class="stat-card"><div class="n">{len(transcriptions)}</div><div class="l">Transcriptions</div></div>', unsafe_allow_html=True)
with col2:
    st.markdown(f'<div class="stat-card"><div class="n" style="color:#d97706">{tops_count}</div><div class="l">Top performers</div></div>', unsafe_allow_html=True)
with col3:
    st.markdown(f'<div class="stat-card"><div class="n" style="color:#0891b2">{new_count}</div><div class="l">Nouvelles créas</div></div>', unsafe_allow_html=True)
with col4:
    st.markdown(f'<div class="stat-card"><div class="n" style="color:#7c3aed">{vision_count}</div><div class="l">Analysés visuel</div></div>', unsafe_allow_html=True)
with col5:
    score_color = "#059669" if avg_score and avg_score >= 7 else "#d97706" if avg_score else "#d1d5db"
    score_val = str(avg_score) if avg_score else "—"
    st.markdown(f'<div class="stat-card"><div class="n" style="color:{score_color}">{score_val}</div><div class="l">Score moyen</div></div>', unsafe_allow_html=True)
with col6:
    st.markdown(f'<div class="stat-card"><div class="n" style="color:#059669">{len(gen_files)}</div><div class="l">Scripts générés</div></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Onboarding — affiché uniquement si compte vide sans clé API ──
_has_api_key = bool(os.environ.get("ANTHROPIC_API_KEY", "").strip())
_brands_for_onboarding = []
if BRANDS_AVAILABLE:
    try:
        from brands import load_brands as _lb
        _brands_for_onboarding = _lb()
    except Exception:
        pass
if not _has_api_key or len(_brands_for_onboarding) == 0:
    _step1_done = _has_api_key
    _step2_done = len(_brands_for_onboarding) > 0
    _step3_done = len(transcriptions) > 0
    def _step_style(done):
        if done:
            return "background:#f0fdf4;border:1px solid #bbf7d0;border-radius:10px;padding:12px;text-align:center;"
        return "background:#fff;border:1px solid #e5e7eb;border-radius:10px;padding:12px;text-align:center;"
    def _num_style(done):
        if done:
            return "width:22px;height:22px;border-radius:50%;background:#059669;color:#fff;display:inline-flex;align-items:center;justify-content:center;font-size:11px;font-weight:700;margin-bottom:6px;"
        return "width:22px;height:22px;border-radius:50%;background:#e5e7eb;color:#6b7280;display:inline-flex;align-items:center;justify-content:center;font-size:11px;font-weight:700;margin-bottom:6px;"
    _check = "✓" if True else ""
    st.markdown(f"""
    <div style="background:#fff;border:1px solid #e5e7eb;border-radius:12px;padding:16px 20px;margin-bottom:16px;">
        <div style="font-family:'League Spartan',sans-serif;font-weight:700;font-size:13px;color:#0a0a0a;margin-bottom:12px;">
            Démarrage rapide
        </div>
        <div style="display:flex;gap:10px;">
            <div style="{_step_style(_step1_done)}flex:1;">
                <div style="{_num_style(_step1_done)}">{"✓" if _step1_done else "1"}</div>
                <div style="font-size:11px;color:#374151;font-weight:500;line-height:1.4;">Ajouter ta clé<br>Anthropic API</div>
            </div>
            <div style="{_step_style(_step2_done)}flex:1;">
                <div style="{_num_style(_step2_done)}">{"✓" if _step2_done else "2"}</div>
                <div style="font-size:11px;color:#374151;font-weight:500;line-height:1.4;">Ajouter une<br>marque à surveiller</div>
            </div>
            <div style="{_step_style(_step3_done)}flex:1;">
                <div style="{_num_style(_step3_done)}">{"✓" if _step3_done else "3"}</div>
                <div style="font-size:11px;color:#374151;font-weight:500;line-height:1.4;">Scraper et<br>analyser les pubs</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ──────────────────────────────────────────────
# NAVIGATION — pilotable par programme (workflow, fin de scraping...)
# ──────────────────────────────────────────────
TAB_NAMES = [
    "🏢 Marques",
    "💬 Chat",
    "🔍 Scraper",
    "📊 Rapport",
    "⚡ Script Rapide",
    "🔬 Intelligence",
    "✍️ Générer du Copy",
    "📁 Historique",
    "🤖 Agent Expert",
    "📝 Deck Scripts",
]
if "_nav_to" in st.session_state:
    st.session_state["main_nav"] = st.session_state.pop("_nav_to")
if "main_nav" not in st.session_state:
    st.session_state["main_nav"] = TAB_NAMES[0]
_nav = st.segmented_control(
    "Navigation", TAB_NAMES, key="main_nav", label_visibility="collapsed"
)
if _nav is None:  # désélection — on reste sur la dernière page
    _nav = st.session_state.get("_nav_last", TAB_NAMES[0])
st.session_state["_nav_last"] = _nav


# ══════════════════════════════════════════════
# ONGLET 0 — MARQUES
# ══════════════════════════════════════════════
if _nav == "🏢 Marques":
    if not BRANDS_AVAILABLE:
        st.error("Module brands.py introuvable.")
    else:
        brands_list = load_brands()

        # ── Workflow — étapes CLIQUABLES ──────────────
        _has_brands = len(brands_list) > 0
        _has_trans   = len(transcriptions) > 0
        _ctx_loaded  = load_context() if AGENT_AVAILABLE else {}
        _has_product = bool(_ctx_loaded.get("scraped") or _ctx_loaded.get("manual"))

        _wf_steps = [
            ("1", "Ajouter & scraper", "🏢 Marques", _has_brands and _has_trans),
            ("2", "Visualiser les pubs", "📊 Rapport", _has_trans),
            ("3", "Importer mon produit", "🤖 Agent Expert", _has_product),
            ("4", "Générer le deck", "📝 Deck Scripts", False),
        ]
        # L'étape "courante" = la première non terminée
        _current_step = next((n for n, _, _, d in _wf_steps if not d), "4")
        _wf_cols = st.columns(4)
        for _col, (_num, _lbl, _target, _done) in zip(_wf_cols, _wf_steps):
            _icon = "✅" if _done else f"{_num}."
            _btn_type = "primary" if _num == _current_step else "secondary"
            if _col.button(f"{_icon} {_lbl}", key=f"wf_btn_{_num}",
                           use_container_width=True, type=_btn_type):
                st.session_state["_nav_to"] = _target
                st.rerun()
        st.caption("👆 Clique sur une étape pour y aller directement.")

        # ── SCRAPING EN COURS (prioritaire — remplace tout le reste) ────
        _pending = st.session_state.get("_pending_scrape")
        _batch_idx = st.session_state.get("_batch_idx")

        if _pending:
            st.info(f"⏳ Scraping **{_pending['name']}** en cours — ne ferme pas cette fenêtre...")
            _env = os.environ.copy()
            _env["WHISPER_MODEL_OVERRIDE"] = whisper_model
            _env["SCROLL_COUNT_OVERRIDE"] = str(scroll_count)
            _log_slot = st.empty()
            _logs = []
            _proc = subprocess.Popen(
                [PYTHON, "transcriber.py", "--url", _pending["url"], "--label", _pending["label"]],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, cwd=str(BASE_DIR), env=_env,
            )
            for _l in _proc.stdout:
                _logs.append(_l.rstrip())
                _log_slot.code("\n".join(_logs[-18:]), language=None)
            _proc.wait()
            del st.session_state["_pending_scrape"]
            if _proc.returncode == 0:
                _all_t = json.loads(json_path.read_text(encoding="utf-8")) if json_path.exists() else []
                _cnt = sum(1 for r in _all_t if r.get("label") == _pending["label"])
                _sc  = [r for r in _all_t if r.get("scoring") and r.get("label") == _pending["label"]]
                _avg_sc = round(sum(r["scoring"]["score_total"] for r in _sc) / len(_sc), 1) if _sc else None
                update_brand_stats(_pending["id"], _cnt, _avg_sc)
                # Suivi temporel — snapshot automatique après chaque scraping
                try:
                    from tracker import get_brand_intelligence
                    _brand_ads = [r for r in _all_t if r.get("page_name") == _pending.get("name") or True]
                    _intel = get_brand_intelligence(_pending["name"], _all_t)
                    if _intel.get("has_history") and _intel.get("diff"):
                        _diff = _intel["diff"]
                        _summary = _diff.get("summary", {})
                        if _summary.get("new"):
                            st.toast(f"🆕 {_summary['new']} nouvelle(s) pub(s) détectée(s) pour {_pending['name']}", icon="📊")
                        if _summary.get("killed"):
                            st.toast(f"❌ {_summary['killed']} pub(s) arrêtée(s) depuis le dernier scraping", icon="📉")
                        if _summary.get("scaling"):
                            st.toast(f"🚀 {_summary['scaling']} pub(s) en forte croissance de reach !", icon="🔥")
                        st.session_state[f"_tracker_{_pending['name']}"] = _intel
                except Exception as _te:
                    pass  # tracker optionnel
                st.toast(f"✅ {_pending['name']} — {_cnt} pubs récupérées ! Voici le rapport.", icon="🎉")
                st.session_state["_nav_to"] = "📊 Rapport"
                st.rerun()
            else:
                st.error("Erreur scraping — vérifie les logs ci-dessus.")
                if st.button("← Retour aux marques", key="back_after_fail"):
                    st.rerun()

        elif _batch_idx is not None:
            _all_brands = load_brands()
            if _batch_idx >= len(_all_brands):
                del st.session_state["_batch_idx"]
                st.toast(f"✅ {len(_all_brands)} marques scrapées ! Voici le rapport.", icon="🎉")
                st.session_state["_nav_to"] = "📊 Rapport"
                st.rerun()
            else:
                _b = _all_brands[_batch_idx]
                st.progress(
                    _batch_idx / len(_all_brands),
                    text=f"Marque {_batch_idx + 1}/{len(_all_brands)} : **{_b['name']}**"
                )
                _env = os.environ.copy()
                _env["WHISPER_MODEL_OVERRIDE"] = whisper_model
                _env["SCROLL_COUNT_OVERRIDE"] = str(scroll_count)
                _proc2 = subprocess.Popen(
                    [PYTHON, "transcriber.py", "--url", _b["url"], "--label", _b["label"]],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, cwd=str(BASE_DIR), env=_env,
                )
                for _ in _proc2.stdout: pass
                _proc2.wait()
                if _proc2.returncode == 0:
                    update_brand_stats(_b["id"], _b.get("ad_count", 0))
                st.session_state["_batch_idx"] = _batch_idx + 1
                st.rerun()

        else:
            # ── Dashboard normal ─────────────────────
            _col_title, _col_add = st.columns([4, 1])
            _col_title.markdown(f"### {len(brands_list)} marque(s) configurée(s)")
            _open_form = _col_add.button("➕ Ajouter", key="open_add_form", type="primary")

            # ── Gestion des catégories custom ───────────────────────────
            with st.expander("🗂 Mes catégories", expanded=False):
                _sections_list = load_sections()
                st.caption("Crée tes propres catégories pour regrouper les marques à scraper.")
                _sec_tags_html = ""
                _sec_tag_cols = st.columns(min(len(_sections_list), 4) or 1)
                for _si, _sec in enumerate(_sections_list):
                    with _sec_tag_cols[_si % 4]:
                        _sc1, _sc2 = st.columns([5, 1])
                        _sc1.markdown(f"<span style='font-weight:600'>{_sec}</span>", unsafe_allow_html=True)
                        if _sc2.button("✕", key=f"delsec_{_si}"):
                            remove_section(_sec)
                            st.rerun()
                st.markdown("---")
                _ns1, _ns2 = st.columns([5, 1])
                _new_sec_name = _ns1.text_input("Nom de la catégorie", placeholder="ex: 🐱 Chats · 🇫🇷 Concurrents FR · 🛒 Ecom US", key="new_sec", label_visibility="collapsed")
                if _ns2.button("Créer", key="add_sec", type="primary"):
                    if _new_sec_name.strip():
                        add_section(_new_sec_name.strip())
                        st.rerun()

            with st.expander("Ajouter une marque", expanded=_open_form or len(brands_list) == 0):
                _PERF_LEVELS_FORM = ["⭐ Top Performers", "🆕 Nouvelles Créas", "🧪 En test", "💡 Inspiration"]
                _fa, _fb = st.columns([2, 5])
                _new_name  = _fa.text_input("Nom", placeholder="ex: Nike, Sephora…", key="bn")
                _new_url   = _fb.text_input("URL Meta Ads Library", placeholder="https://www.facebook.com/ads/library/?...", key="bu")
                _sections_opts = load_sections()
                _fc, _fd = st.columns([1, 1])
                _add_perf   = _fc.multiselect("Niveau", _PERF_LEVELS_FORM, default=["⭐ Top Performers"], key="add_perf")
                _add_niches = _fd.multiselect("Catégories", _sections_opts, key="add_niches")
                if st.button("✅ Sauvegarder", type="primary", key="add_brand",
                             disabled=not (_new_name.strip() and _new_url.strip())):
                    _add_tags = _add_perf + _add_niches
                    _add_label = _add_perf[0] if _add_perf else (_add_niches[0] if _add_niches else "")
                    add_brand(_new_name, _new_url, _add_label)
                    # Sauvegarder les tags
                    _all_b = load_brands()
                    for _b in _all_b:
                        if _b["name"] == _new_name.strip():
                            _b["tags"] = _add_tags
                    save_brands(_all_b)
                    st.success(f"✅ **{_new_name}** ajoutée !")
                    st.rerun()

            st.markdown("<br>", unsafe_allow_html=True)

            if not brands_list:
                st.markdown("""
                <div class="empty-state-box">
                  <div class="ebox-icon">🏢</div>
                  <div class="ebox-title">Aucune marque configurée</div>
                  <div class="ebox-sub">Ajoute ta première marque concurrente pour commencer le scraping</div>
                </div>
                """, unsafe_allow_html=True)
            else:
                # Bouton Tout scraper
                _ca, _cb = st.columns([5, 2])
                _ca.caption(f"Clique ▶ pour scraper une marque, ou lance toutes en batch.")
                if _cb.button(f"🚀 Tout scraper ({len(brands_list)})", type="primary",
                              key="scrape_all", use_container_width=True):
                    st.session_state["_batch_idx"] = 0
                    st.rerun()

                st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

                # Niveaux de performance fixes
                _PERF_LEVELS = ["⭐ Top Performers", "🆕 Nouvelles Créas", "🧪 En test", "💡 Inspiration"]

                _editing_brand = st.session_state.get("_editing_brand_id")

                for _brand in brands_list:
                    _last  = _brand.get("last_scraped") or "Jamais scrapée"
                    _ads_n = _brand.get("ad_count", 0)
                    _avg   = _brand.get("avg_score")
                    _sc_html = f'<span style="color:{"#155724" if _avg>=7 else "#856404"};font-weight:700">⭐ {_avg}/10</span>' if _avg else '<span style="color:#adb5bd">Non scorée</span>'
                    _bid = _brand["id"]

                    # Compat : si l'ancien champ label existe, le convertir en tags
                    if "tags" not in _brand:
                        _old_label = _brand.get("label", "")
                        _brand["tags"] = [_old_label] if _old_label else []

                    # ── Mode édition inline ────────────────────────────
                    if _editing_brand == _bid:
                        with st.container():
                            st.markdown(f"**✏️ {_brand['name']}**")
                            _edit_cats = load_sections()
                            _cur_tags = _brand.get("tags", [])
                            _cur_perf = [t for t in _cur_tags if t in _PERF_LEVELS]
                            _cur_niches = [t for t in _cur_tags if t not in _PERF_LEVELS]
                            _ec1, _ec2 = st.columns([1, 1])
                            _sel_perf = _ec1.multiselect("Niveau de performance", _PERF_LEVELS, default=_cur_perf, key=f"edit_perf_{_bid}")
                            _sel_niches = _ec2.multiselect("Catégories", _edit_cats, default=[n for n in _cur_niches if n in _edit_cats], key=f"edit_niches_{_bid}")
                            _new_notes = st.text_input("Notes", value=_brand.get("notes", ""), placeholder="optionnel", key=f"edit_notes_{_bid}")
                            _es1, _es2 = st.columns([1, 1])
                            if _es1.button("💾 Sauvegarder", key=f"save_edit_{_bid}", type="primary", use_container_width=True):
                                _all_brands = load_brands()
                                for _b in _all_brands:
                                    if _b["id"] == _bid:
                                        _b["tags"] = _sel_perf + _sel_niches
                                        _b["label"] = _sel_perf[0] if _sel_perf else (_sel_niches[0] if _sel_niches else "")
                                        _b["notes"] = _new_notes
                                save_brands(_all_brands)
                                st.session_state.pop("_editing_brand_id", None)
                                st.rerun()
                            if _es2.button("Annuler", key=f"cancel_edit_{_bid}", use_container_width=True):
                                st.session_state.pop("_editing_brand_id", None)
                                st.rerun()
                        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
                        continue

                    # ── Affichage normal ───────────────────────────────
                    _tags = _brand.get("tags", [_brand.get("label", "")])
                    _tags_html = " ".join(
                        f'<span style="background:{"#fff3cd" if t in _PERF_LEVELS else "#e8f4fd"};border:1px solid {"#ffc107" if t in _PERF_LEVELS else "#90caf9"};border-radius:10px;padding:1px 8px;font-size:11px;font-weight:600">{t}</span>'
                        for t in _tags if t
                    )
                    _cinfo, _cbtn = st.columns([5, 2])
                    _cinfo.markdown(f"""
                    <div class="brand-row">
                      <div class="brand-row-name">🏢 {_brand['name']}</div>
                      <div class="brand-row-meta" style="gap:6px;flex-wrap:wrap">
                        {_tags_html}
                        <span>📅 {_last}</span>
                        <span>📺 {_ads_n} pub{"s" if _ads_n != 1 else ""}</span>
                        <span>{_sc_html}</span>
                      </div>
                    </div>
                    """, unsafe_allow_html=True)

                    with _cbtn:
                        _b1, _b2, _b3 = st.columns([3, 1, 1])
                        if _b1.button("▶ Scraper", key=f"sc_{_bid}", use_container_width=True, type="primary"):
                            st.session_state["_pending_scrape"] = _brand
                            st.rerun()
                        if _b2.button("✏️", key=f"ed_{_bid}", use_container_width=True, help="Modifier"):
                            st.session_state["_editing_brand_id"] = _bid
                            st.rerun()
                        if _b3.button("✕", key=f"dl_{_bid}", use_container_width=True, help="Supprimer"):
                            remove_brand(_bid)
                            st.rerun()
                    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════
# ONGLET 1 — SCRAPER
# ══════════════════════════════════════════════
if _nav == "🔍 Scraper":
    st.markdown("### 🔍 Scraper une marque")
    st.markdown("Entre une ou deux URLs de la Bibliothèque publicitaire Meta avec leurs labels.")

    c1, c2 = st.columns([3, 1])
    with c1:
        url1 = st.text_input("URL #1", placeholder="https://www.facebook.com/ads/library/?...")
    with c2:
        label1 = st.text_input("Label #1", value="Top Performers")

    with st.expander("+ Ajouter une 2e URL (ex: Nouvelles Créas)"):
        c3, c4 = st.columns([3, 1])
        with c3:
            url2 = st.text_input("URL #2", placeholder="https://www.facebook.com/ads/library/?...")
        with c4:
            label2 = st.text_input("Label #2", value="Nouvelles Créas")

    st.markdown("**💡 Astuce URLs :**")
    brand_hint = st.text_input("Nom de la marque à rechercher", placeholder="ex: raph_et_juliette")
    if brand_hint:
        base = "https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country=ALL&is_targeted_country=false&media_type=all"
        q = brand_hint.replace(" ", "_")
        st.code(f"{base}&q={q}&search_type=keyword_unordered&sort_data[mode]=total_impressions&sort_data[direction]=desc", language=None)
        st.caption("↑ Top Performers (desc) · Change `desc` en `asc` pour les Nouvelles Créas")

    api_key_set = bool(os.environ.get("ANTHROPIC_API_KEY"))
    if api_key_set:
        st.info("📷 Analyse visuelle automatique activée (Claude Vision + ffmpeg si disponible)", icon="✨")

    st.markdown("---")
    st.markdown("**🎯 Brief vidéo** *(optionnel — génère un script ciblé automatiquement après le scraping)*")
    video_brief = st.text_area(
        "Brief",
        value=st.session_state.get("video_brief", ""),
        placeholder="Ex : vidéo prévention pour proprio de chiens 3-7 ans, angle articulations, ton UGC authentique, offre membres à mettre en CTA...",
        height=80,
        key="video_brief_input",
        label_visibility="collapsed",
    )
    if video_brief != st.session_state.get("video_brief", ""):
        st.session_state["video_brief"] = video_brief

    if st.button("🚀 Lancer le scraping + transcription", type="primary", disabled=not url1):
        cmd = [PYTHON, "transcriber.py"]
        cmd += ["--url", url1, "--label", label1]
        if url2:
            cmd += ["--url", url2, "--label", label2]

        env = os.environ.copy()
        env["WHISPER_MODEL_OVERRIDE"] = whisper_model
        env["SCROLL_COUNT_OVERRIDE"] = str(scroll_count)

        st.info("Le navigateur Chromium va s'ouvrir — ne le ferme pas.")
        log_area = st.empty()
        logs = []

        with st.spinner("Scraping en cours..."):
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=str(BASE_DIR),
                env=env,
            )
            for line in proc.stdout:
                logs.append(line.rstrip())
                log_area.code("\n".join(logs[-40:]), language=None)
            proc.wait()

        if proc.returncode == 0:
            if st.session_state.get("video_brief", "").strip():
                st.success("✅ Scraping terminé ! Génération du script en cours...")
                st.session_state["_pending_quick_script"] = True
                st.session_state["_nav_to"] = "⚡ Script Rapide"
            else:
                st.success("✅ Transcription terminée ! Va dans l'onglet **Rapport** pour voir les résultats.")
                st.session_state["_nav_to"] = "📊 Rapport"
            st.rerun()
        else:
            st.error("Une erreur s'est produite. Vérifie les logs ci-dessus.")


# ══════════════════════════════════════════════
# ONGLET 2 — RAPPORT
# ══════════════════════════════════════════════
if _nav == "📊 Rapport":
    _rt1, _rt2 = st.columns([4, 2])
    _rt1.markdown("### 📊 Rapport interactif")
    if _rt2.button("Étape suivante : importer mon produit →", key="next_to_product",
                   use_container_width=True):
        st.session_state["_nav_to"] = "🤖 Agent Expert"
        st.rerun()

    html_path = OUTPUT_DIR / "rapport.html"

    # ── Toggle vue ──────────────────────────────
    _view_mode = st.radio(
        "Vue", ["📋 Pubs décortiquées", "📄 Rapport HTML"],
        horizontal=True, label_visibility="collapsed",
        key="rapport_view_mode"
    )

    # ── Vue pubs décortiquées ───────────────────
    if _view_mode == "📋 Pubs décortiquées":
        if not transcriptions:
            st.info("Lance d'abord un scraping pour voir les pubs.")
        else:
            from intelligence import AD_FORMATS, detect_format

            # ── Auto-détecter le format de chaque pub (local, gratuit) ──
            for _r in transcriptions:
                if not _r.get("ad_format"):
                    _r["ad_format"] = detect_format(
                        _r.get("transcript", ""),
                        _r.get("visual_analysis")
                    )

            # ── Distribution des formats ─────────────────────────────
            from collections import Counter
            _fmt_counts = Counter(r.get("ad_format", "ugc") for r in transcriptions)
            _dist_html = '<div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:16px;align-items:center">'
            _dist_html += '<span style="font-size:.75rem;font-weight:700;color:#888;text-transform:uppercase;letter-spacing:.05em;margin-right:4px">Formats</span>'
            for _fk, _fcount in sorted(_fmt_counts.items(), key=lambda x: -x[1]):
                _fname = AD_FORMATS.get(_fk, {}).get("name", _fk)
                _fcolor = AD_FORMATS.get(_fk, {}).get("color", "#888")
                _dist_html += f'<span style="background:{_fcolor}18;border:1.5px solid {_fcolor}55;border-radius:20px;padding:3px 11px;font-size:.76rem;font-weight:700;color:{_fcolor};cursor:pointer" title="Cliquer pour filtrer">{_fname} <b style=\'background:{_fcolor};color:#fff;border-radius:10px;padding:1px 6px;font-size:.7rem;margin-left:3px\'>{_fcount}</b></span>'
            _dist_html += '</div>'
            st.markdown(_dist_html, unsafe_allow_html=True)

            # ── Bouton classifier avec IA ───────────────────────────
            _clf_col1, _clf_col2 = st.columns([4, 1])
            with _clf_col2:
                if st.button("🧠 Classifier avec IA", key="classify_ai_btn",
                             help="Claude re-classifie chaque pub avec plus de précision"):
                    _api = os.environ.get("ANTHROPIC_API_KEY", "").strip()
                    if _api:
                        try:
                            from intelligence import classify_all
                            with st.spinner("Classification en cours..."):
                                _tc, _ = classify_all(transcriptions)
                            _save_transcriptions(_tc)
                            st.success("✅ Formats mis à jour !")
                            st.rerun()
                        except Exception as _e:
                            st.error(f"Erreur : {_e}")
                    else:
                        st.warning("Clé API manquante")

            # ── Filtres ─────────────────────────────────────────────
            _fc1, _fc2, _fc3, _fc4 = st.columns([3, 2, 2, 2])
            _search_r    = _fc1.text_input("Rechercher", placeholder="mot-clé...", key="rpt_search", label_visibility="collapsed")
            _labels_avail = sorted(set(r.get("label","") for r in transcriptions if r.get("label")))
            _label_filter = _fc2.selectbox("Catégorie", ["Toutes"] + _labels_avail, key="rpt_label", label_visibility="collapsed")
            _fmt_avail    = sorted(set(r.get("ad_format","ugc") for r in transcriptions))
            _fmt_names    = {k: AD_FORMATS.get(k,{}).get("name", k) for k in _fmt_avail}
            _fmt_filter   = _fc3.selectbox("Format", ["Tous"] + [_fmt_names[k] for k in _fmt_avail], key="rpt_fmt", label_visibility="collapsed")
            _sort_by      = _fc4.selectbox("Trier par", ["Position", "Reach EU", "Score", "Date"], key="rpt_sort", label_visibility="collapsed")

            _rpt_all = transcriptions[:]
            if _search_r:
                _rpt_all = [r for r in _rpt_all if _search_r.lower() in r.get("transcript","").lower()]
            if _label_filter != "Toutes":
                _rpt_all = [r for r in _rpt_all if r.get("label") == _label_filter]
            if _fmt_filter != "Tous":
                _rpt_all = [r for r in _rpt_all if _fmt_names.get(r.get("ad_format","ugc")) == _fmt_filter]
            if _sort_by == "Reach EU":
                _rpt_all = sorted(_rpt_all, key=lambda r: r.get("eu_reach") or 0, reverse=True)
            elif _sort_by == "Score":
                _rpt_all = sorted(_rpt_all, key=lambda r: (r.get("scoring") or {}).get("score_total") or 0, reverse=True)
            elif _sort_by == "Date":
                _rpt_all = sorted(_rpt_all, key=lambda r: r.get("start_date") or "", reverse=True)

            st.caption(f"{len(_rpt_all)} pub(s)")

            def _fmt_reach(v):
                if not v: return None
                if v >= 1_000_000: return f"{v/1_000_000:.1f}M"
                if v >= 1_000: return f"{v/1_000:.0f}K"
                return str(v)

            def _days_active(start_str):
                if not start_str: return None
                try:
                    from datetime import date
                    d = date.fromisoformat(start_str[:10])
                    return (date.today() - d).days
                except Exception:
                    return None

            def _deconstruct_ad(transcript: str, api_key: str):
                """Appelle Claude pour décomposer la pub en sections."""
                import anthropic, json as _json
                client = anthropic.Anthropic(api_key=api_key)
                prompt = f"""Tu es expert en analyse de publicités Meta.
Analyse cette transcription et extrais chaque section. Sois précis et cite le texte exact (extrait court).

Transcription :
\"\"\"
{transcript[:3000]}
\"\"\"

Réponds UNIQUEMENT en JSON valide avec ces clés :
{{
  "hook": "les 1-2 premières phrases — l'accroche exacte",
  "hook_type": "type (ex: question, stat choc, identification douleur, story, contradiction)",
  "contexte_probleme": "la mise en contexte du problème / douleur",
  "preuve": "preuves / social proof / chiffres / témoignage (ou null)",
  "solution": "la solution / bénéfice produit présenté",
  "cta": "l'appel à l'action final (ou null)",
  "ton": "le ton dominant (ex: conversationnel, urgence, autorité, empathie, humour)",
  "structure_resumee": "1 phrase résumant la structure (ex: Douleur → Identification → Preuve → Produit → CTA)"
}}"""
                msg = client.messages.create(
                    model="claude-sonnet-4-6",
                    max_tokens=1024,
                    messages=[{"role": "user", "content": prompt}]
                )
                raw = msg.content[0].text.strip()
                # extraire le JSON
                if "```" in raw:
                    raw = raw.split("```")[1]
                    if raw.startswith("json"): raw = raw[4:]
                return _json.loads(raw)

            _decon_cache = st.session_state.setdefault("_decon_cache", {})

            for _r in _rpt_all:
                _pos        = _r.get("position", "?")
                _label      = _r.get("label", "")
                _brand      = _r.get("page_name", "")
                _lang       = _r.get("lang", "")
                _words      = len((_r.get("transcript") or "").split())
                _reach      = _fmt_reach(_r.get("eu_reach"))
                _days       = _days_active(_r.get("start_date"))
                _score      = (_r.get("scoring") or {}).get("score_total")
                _ad_id      = _r.get("ad_id") or ""
                _transcript = _r.get("transcript", "")
                _hook_3s    = _r.get("hook_3s") or _transcript[:120]
                _card_key   = f"card_{_pos}_{_label}"

                # Perf composite
                _perf       = _r.get("performance") or {}
                _composite  = _perf.get("composite")
                _conf       = _perf.get("confidence", "low")
                _conf_icon  = {"high": "🟢", "medium": "🟡", "low": "🔴"}.get(_conf, "⚪")

                # Badge label
                _badge_color  = "#fff3cd" if "Top" in _label else "#f0f0f0"
                _badge_border = "#ffc107" if "Top" in _label else "#d0d0d0"
                _label_icon   = "⭐" if "Top" in _label else "🆕"

                # Format visuel
                _ad_fmt    = _r.get("ad_format", "ugc")
                _fmt_src   = _r.get("ad_format_source", "text_fallback")
                _fmt_info  = AD_FORMATS.get(_ad_fmt, {})
                _fmt_name  = _fmt_info.get("name", _ad_fmt)
                _fmt_color = _fmt_info.get("color", "#888")
                _fmt_src_icon = "👁" if _fmt_src == "vision" else "📝"
                _fmt_src_title = "Détecté par Vision IA (haute confiance)" if _fmt_src == "vision" else "Estimé depuis le texte"

                # Score composite badge
                if _composite is not None:
                    _sc_bg  = "#d4edda" if _composite >= 70 else ("#fff3cd" if _composite >= 40 else "#f8d7da")
                    _sc_col = "#155724" if _composite >= 70 else ("#856404" if _composite >= 40 else "#721c24")
                    _rs  = _perf.get("reach_score", 0)
                    _ls  = _perf.get("longevity_score", 0)
                    _qs  = _perf.get("quality_score", 0)
                    _tip = f"Score composite — reach:{_rs:.0f} longévité:{_ls:.0f} qualité:{_qs:.0f}"
                    _composite_badge = (
                        f'<span style="background:{_sc_bg};color:{_sc_col};border-radius:10px;'
                        f'padding:2px 10px;font-size:11px;font-weight:800" title="{_tip}">'
                        f'{_conf_icon} {_composite}/100</span>'
                    )
                else:
                    _composite_badge = ""

                # Hook score badge
                _hs_data = _r.get("hook_scoring") or {}
                _hs_val  = _hs_data.get("stop_scroll_score")
                _hs_mech = _hs_data.get("mechanism_label", "")
                if _hs_val is not None:
                    _hs_bg  = "#d4edda" if _hs_val >= 8 else ("#fff3cd" if _hs_val >= 6 else "#f8d7da")
                    _hs_col = "#155724" if _hs_val >= 8 else ("#856404" if _hs_val >= 6 else "#721c24")
                    _hook_badge = (f'<span style="background:{_hs_bg};color:{_hs_col};border-radius:10px;'
                                   f'padding:2px 10px;font-size:11px;font-weight:800" title="{_hs_mech}">'
                                   f'🎣 {_hs_val}/10</span>')
                else:
                    _hook_badge = ""

                # Body structure badge
                _bs_data   = _r.get("body_scoring") or {}
                _bs_val    = _bs_data.get("overall_structure_score")
                _drop_risk = _bs_data.get("drop_risk", "")
                if _bs_val is not None:
                    _bs_bg  = "#d4edda" if _bs_val >= 7 else ("#fff3cd" if _bs_val >= 5 else "#f8d7da")
                    _bs_col = "#155724" if _bs_val >= 7 else ("#856404" if _bs_val >= 5 else "#721c24")
                    _body_badge = (f'<span style="background:{_bs_bg};color:{_bs_col};border-radius:10px;'
                                   f'padding:2px 10px;font-size:11px;font-weight:800" title="Drop risk: {_drop_risk}">'
                                   f'📐 {_bs_val}/10</span>')
                else:
                    _body_badge = ""

                # Stats
                _stat_parts = []
                if _reach:           _stat_parts.append(f"📡 {_reach} reach EU")
                if _days is not None: _stat_parts.append(f"⏱ {_days}j actif")
                if _score:           _stat_parts.append(f"🤖 {_score}/10")
                if _brand:           _stat_parts.append(f"🏢 {_brand}")
                if _lang:            _stat_parts.append(f"🌐 {_lang}")
                _stat_parts.append(f"📝 {_words} mots")
                _stats_str = "  ·  ".join(_stat_parts)

                _lib_url = f"https://www.facebook.com/ads/library/?id={_ad_id}" if _ad_id else None

                with st.container():
                    st.markdown(f"""
<div style="border:1px solid #e8e8e8;border-radius:14px;padding:16px 18px;margin-bottom:10px;background:#ffffff;box-shadow:0 1px 3px rgba(0,0,0,.05)">
  <div style="display:flex;align-items:center;gap:7px;margin-bottom:10px;flex-wrap:wrap">
    <span style="background:{_badge_color};border:1px solid {_badge_border};border-radius:10px;padding:2px 10px;font-size:11px;font-weight:700">{_label_icon} {_label} #{_pos}</span>
    <span style="background:{_fmt_color}18;border:1.5px solid {_fmt_color}66;border-radius:10px;padding:2px 10px;font-size:11px;font-weight:700;color:{_fmt_color}" title="{_fmt_src_title}">{_fmt_src_icon} {_fmt_name}</span>
    {_composite_badge}{_hook_badge}{_body_badge}
    <span style="color:#bbb;font-size:11px">{_stats_str}</span>
    {"<a href='" + _lib_url + "' target='_blank' style='font-size:11px;color:#666;text-decoration:none'>🔗</a>" if _lib_url else ""}
  </div>
  <div style="margin-bottom:8px">
    <span style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.05em;color:#999">🎣 Hook 0-3s</span>
    <div style="color:#0a0a0a;font-size:14px;line-height:1.6;font-weight:600;margin-top:3px;border-left:3px solid {_fmt_color};padding-left:10px">{_hook_3s.replace(chr(10),' ')}</div>
  </div>
  <div style="color:#555;font-size:12.5px;line-height:1.55;margin-top:6px">{_transcript[len(_hook_3s):len(_hook_3s)+180].strip().replace(chr(10),' ')}{"..." if len(_transcript) > len(_hook_3s)+180 else ""}</div>
</div>
""", unsafe_allow_html=True)

                    _btn1, _btn2, _btn3 = st.columns([2, 2, 2])

                    # Bouton décortiquer
                    _is_deconstructed = _card_key in _decon_cache
                    if _btn1.button(
                        "✅ Décortiqué" if _is_deconstructed else "🔍 Décortiquer",
                        key=f"dec_{_card_key}",
                        use_container_width=True,
                        type="secondary"
                    ):
                        if not _is_deconstructed:
                            _api = os.environ.get("ANTHROPIC_API_KEY","").strip()
                            if not _api:
                                st.warning("Clé API manquante")
                            else:
                                with st.spinner("Analyse en cours..."):
                                    try:
                                        _decon_cache[_card_key] = _deconstruct_ad(_transcript, _api)
                                    except Exception as _e:
                                        st.error(f"Erreur : {_e}")
                                st.rerun()
                        else:
                            del _decon_cache[_card_key]
                            st.rerun()

                    if _btn2.button("📋 Copier", key=f"copy_{_card_key}", use_container_width=True):
                        st.session_state[f"_clipboard_{_card_key}"] = _transcript
                        st.toast("Transcription copiée !", icon="📋")

                    if _btn3.button("🎯 Adapter", key=f"adapt_{_card_key}", use_container_width=True, type="primary"):
                        idx = transcriptions.index(_r) if _r in transcriptions else None
                        if idx is not None:
                            st.session_state["adapt_prefill"] = idx
                        st.session_state["_nav_to"] = "📊 Rapport"
                        st.rerun()

                    # Affichage du décorticage
                    if _card_key in _decon_cache:
                        _d = _decon_cache[_card_key]
                        st.markdown(f"""
<div style="background:#f0f7ff;border-left:4px solid #1877f2;border-radius:0 8px 8px 0;padding:14px 18px;margin-bottom:16px">
  <div style="font-size:13px;color:#555;margin-bottom:10px;font-weight:600">📐 {_d.get('structure_resumee','')}</div>
  <div style="display:grid;gap:8px">
    <div><span style="background:#fff3cd;border-radius:6px;padding:2px 8px;font-size:11px;font-weight:700">🎣 HOOK · {_d.get('hook_type','')}</span><br><span style="font-size:13px;color:#333;margin-top:4px;display:block">"{_d.get('hook','')}"</span></div>
    <div><span style="background:#fce4ec;border-radius:6px;padding:2px 8px;font-size:11px;font-weight:700">😣 PROBLÈME</span><br><span style="font-size:13px;color:#333;display:block">"{_d.get('contexte_probleme','')}"</span></div>
    {"<div><span style='background:#e8f5e9;border-radius:6px;padding:2px 8px;font-size:11px;font-weight:700'>✅ PREUVE</span><br><span style='font-size:13px;color:#333;display:block'>" + '"' + str(_d.get('preuve','')) + '"' + "</span></div>" if _d.get('preuve') else ""}
    <div><span style="background:#e3f2fd;border-radius:6px;padding:2px 8px;font-size:11px;font-weight:700">💡 SOLUTION</span><br><span style="font-size:13px;color:#333;display:block">"{_d.get('solution','')}"</span></div>
    {"<div><span style='background:#f3e5f5;border-radius:6px;padding:2px 8px;font-size:11px;font-weight:700'>🎯 CTA</span><br><span style='font-size:13px;color:#333;display:block'>" + '"' + str(_d.get('cta','')) + '"' + "</span></div>" if _d.get('cta') else ""}
    <div style="margin-top:4px;font-size:12px;color:#888">Ton : <b>{_d.get('ton','')}</b></div>
  </div>
</div>
""", unsafe_allow_html=True)

                    # Transcription complète
                    with st.expander("📄 Transcription complète", expanded=False):
                        st.text(_transcript)
                        if _lib_url:
                            st.markdown(f"[🔗 Voir sur Facebook Ad Library]({_lib_url})")

    # ── Vue HTML ────────────────────────────────
    else:
        col_a, col_b = st.columns([1, 1])
        with col_a:
            if st.button("🔄 Régénérer le rapport HTML"):
                result = subprocess.run(
                    [PYTHON, "regenerate_report.py"],
                    capture_output=True, text=True, cwd=str(BASE_DIR),
                )
                if result.returncode == 0:
                    st.success("Rapport régénéré ✓")
                    st.rerun()
                else:
                    st.error(result.stdout + result.stderr)
        with col_b:
            if html_path.exists():
                st.download_button(
                    "⬇️ Télécharger rapport.html",
                    data=html_path.read_bytes(),
                    file_name="rapport_meta_ads.html",
                    mime="text/html",
                )
        if html_path.exists():
            html_content = html_path.read_text(encoding="utf-8")
            st.components.v1.html(html_content, height=820, scrolling=True)  # noqa: ignore deprecation
        else:
            st.info("Aucun rapport disponible. Lance d'abord un scraping dans l'onglet **Scraper**.")

    # ── Adaptateur de script ──────────────────
    st.markdown("---")
    st.markdown("### 🎯 Adapter un script à ma marque")
    st.caption("Sélectionne un script qui te plaît, ajoute tes notes, Claude l'adapte à ton produit.")

    if not transcriptions:
        st.info("Lance d'abord un scraping pour avoir des scripts à adapter.")
    else:
        def _fmt_option(r):
            icon = "🏆" if r.get("label") == "Top Performers" else "🆕"
            page = f" · {r['page_name']}" if r.get("page_name") else ""
            preview = r.get("transcript", "")[:60].replace("\n", " ")
            return f"{icon} #{r.get('position')}{page} — {preview}..."

        _adapt_prefill = st.session_state.get("adapt_prefill")
        if _adapt_prefill is not None and _adapt_prefill < len(transcriptions):
            _pf_r = transcriptions[_adapt_prefill]
            st.success(
                f"✅ Script #{_pf_r.get('position')}"
                + (f" · {_pf_r['page_name']}" if _pf_r.get("page_name") else "")
                + " importé depuis le rapport — prêt à adapter ci-dessous ↓",
                icon="🎯",
            )

        adapt_idx = st.selectbox(
            "Script à adapter",
            range(len(transcriptions)),
            index=_adapt_prefill if (_adapt_prefill is not None and _adapt_prefill < len(transcriptions)) else 0,
            format_func=lambda i: _fmt_option(transcriptions[i]),
            key="adapt_select",
        )
        # Consommer le prefill après affichage (le widget key garde la valeur)
        if "adapt_prefill" in st.session_state:
            del st.session_state["adapt_prefill"]

        sel = transcriptions[adapt_idx]

        col_t, col_v = st.columns([3, 1])
        with col_t:
            st.text_area(
                "Transcription complète",
                value=sel.get("transcript", ""),
                height=160,
                disabled=True,
                key="adapt_transcript_preview",
            )
        with col_v:
            va = sel.get("visual_analysis") or {}
            if isinstance(va, dict) and va:
                st.markdown("**Analyse visuelle**")
                if va.get("scene_type"):
                    st.markdown(f'<span class="context-pill">📷 {va["scene_type"]}</span>', unsafe_allow_html=True)
                if va.get("hook_visual"):
                    st.caption(f"👁 {va['hook_visual']}")
                if va.get("text_overlays"):
                    overlays = [t for t in (va["text_overlays"] or []) if t]
                    if overlays:
                        st.caption(f"💬 {' / '.join(overlays[:3])}")
                if va.get("visual_style"):
                    st.caption(f"🎨 {va['visual_style']}")
            frames_dir = OUTPUT_DIR / "frames"
            safe_lbl = sel.get("label", "").replace(" ", "_").lower()
            frame_0 = frames_dir / f"{safe_lbl}_{int(sel.get('position', 0)):02d}_t0.jpg"
            if frame_0.exists():
                st.image(str(frame_0), use_container_width=True, caption="Hook visuel (0s)")

        adapt_notes = st.text_area(
            "Tes notes / objectifs pour l'adaptation",
            height=110,
            placeholder=(
                "Ex : Focus uniquement sur mon produit digestion. Format UGC 30s max. "
                "Je parle à des femmes 30-50 ans. Garde la même mécanique de hook. "
                "Ton bienveillant mais direct, pas de jargon médical."
            ),
            key="adapt_notes_input",
        )

        adapt_cold = st.checkbox(
            "🧊 Mon audience ne connaît pas ma marque (audience froide)",
            value=True,
            help="Le script adapté construira le 'pourquoi acheter' depuis zéro : problème d'abord, bienfaits démontrés, marque en dernier.",
            key="adapt_cold_audience",
        )

        api_key_adapt = os.environ.get("ANTHROPIC_API_KEY", "").strip()
        adapt_btn = st.button(
            "🤖 Adapter ce script à ma marque",
            type="primary",
            key="adapt_btn",
            disabled=not api_key_adapt,
        )
        if not api_key_adapt:
            st.caption("⚠️ Entre ta clé Anthropic dans la barre latérale.")

        if adapt_btn:
            prompt = (
                f"Un script a performé en top position dans la bibliothèque publicitaire. "
                f"Adapte-le à ma marque/produit.\n\n"
                f"SCRIPT ORIGINAL :\n{sel.get('transcript', '')}\n\n"
            )
            if adapt_notes.strip():
                prompt += f"MES NOTES / OBJECTIFS :\n{adapt_notes.strip()}\n\n"
            else:
                prompt += "Adapte selon le contexte produit que tu connais déjà.\n\n"
            if adapt_cold:
                prompt += (
                    "CONTRAINTE AUDIENCE FROIDE — mon audience ne connaît ni ma marque, ni mon produit, "
                    "ni ses bienfaits, ni pourquoi elle devrait acheter :\n"
                    "- Ne jamais commencer par le nom de la marque ou du produit\n"
                    "- Chaque bénéfice doit être démontré (mécanisme, cause→effet), pas affirmé\n"
                    "- Construire le 'pourquoi acheter' depuis zéro : problème vécu → coût caché → mécanisme → produit en conclusion logique\n"
                    "- Le hook accroche sur le problème ou une vérité surprenante, jamais sur l'offre\n\n"
                )
            prompt += (
                "Ta mission :\n"
                "1. En 2 lignes : ce qui fait marcher ce script (hook, structure, déclencheur émotionnel)\n"
                "2. Version A — fidèle à la mécanique originale, contenu remplacé par mon produit\n"
                "3. Version B — même angle, ta touche créative en plus\n"
                "Pour chaque version : indique ce que tu as conservé et pourquoi."
            )

            if AGENT_AVAILABLE:
                if "agent" in st.session_state:
                    _agent = st.session_state.agent
                else:
                    _ctx_tmp = load_context()
                    _agent = ScriptExpertAgent(api_key_adapt, format_for_prompt(_ctx_tmp))

                st.markdown("**Adaptation générée :**")
                with st.chat_message("assistant"):
                    response = st.write_stream(_agent.chat_stream(prompt))
                st.success("✅ Continue la conversation dans l'onglet **Agent Expert**.")
            else:
                st.error("Module agent non disponible — vérifie que agent.py est présent.")


# ══════════════════════════════════════════════
# ONGLET 3 — SCRIPT RAPIDE
# ══════════════════════════════════════════════
if _nav == "⚡ Script Rapide":
    st.markdown("### ⚡ Script Rapide")
    st.caption("Décris le type de vidéo que tu veux créer — l'IA choisit l'angle optimal et génère 3 variantes scorées automatiquement.")

    if not DECK_AVAILABLE:
        st.error("Module script_deck.py introuvable.")
    else:
        from script_deck import generate_quick_script_stream

        # ── Brief ──
        _brief_val = st.session_state.get("video_brief", "")
        brief_input = st.text_area(
            "🎯 Brief vidéo",
            value=_brief_val,
            placeholder=(
                "Ex : vidéo prévention pour propriétaires de chiens 3-7 ans, "
                "angle articulations, ton UGC authentique, CTA offre membres -15% à vie..."
            ),
            height=100,
            key="quick_brief_input",
        )
        if brief_input != _brief_val:
            st.session_state["video_brief"] = brief_input

        # ── Awareness ──
        _aw_options = {v["name"]: k for k, v in AWARENESS_LEVELS.items()}
        _aw_label = st.radio(
            "Audience",
            list(_aw_options.keys()),
            horizontal=True,
            key="quick_awareness",
        )
        _aw_key = _aw_options[_aw_label]

        # ── Bouton + auto-trigger ──
        _auto = st.session_state.pop("_pending_quick_script", False)
        _generate = st.button(
            "⚡ Générer les scripts",
            type="primary",
            disabled=not brief_input.strip() or not api_key or not transcriptions,
            key="quick_generate_btn",
        ) or _auto

        if not api_key:
            st.warning("Clé API Anthropic manquante — configure-la dans la sidebar.")
        elif not transcriptions:
            st.info("Aucune transcription disponible — lance d'abord un scraping.")
        elif not brief_input.strip():
            st.info("Entre un brief vidéo pour générer les scripts.")

        if _generate and brief_input.strip() and api_key and transcriptions:
            _prod_ctx = format_for_prompt(load_context()) if AGENT_AVAILABLE else ""
            st.markdown("---")
            _output = st.empty()
            _full = ""
            with st.spinner("Génération en cours..."):
                for chunk in generate_quick_script_stream(
                    brief=brief_input,
                    product_context=_prod_ctx,
                    transcriptions=transcriptions,
                    api_key=api_key,
                    awareness=_aw_key,
                ):
                    _full += chunk
                    _output.markdown(_full)
            # Résultat final figé
            _output.markdown(_full)
            st.success("✅ Scripts générés et scorés !")

            # Bouton pour aller dans le deck complet
            if st.button("📝 Générer le deck complet (7 angles)", key="goto_deck_from_quick"):
                st.session_state["_nav_to"] = "📝 Deck Scripts"
                st.rerun()


# ══════════════════════════════════════════════
# ONGLET — INTELLIGENCE COMPÉTITIVE
# ══════════════════════════════════════════════
if _nav == "🔬 Intelligence":
    st.markdown("### 🔬 Intelligence compétitive")
    st.caption("Analyse cross-marque des patterns structurels gagnants — formats, hooks, structures, insights actionnables.")

    _intel_available = False
    try:
        from intelligence import AD_FORMATS, classify_all, analyze_patterns, generate_from_pattern_stream, detect_format, cluster_hooks, generate_video_brief, compare_sections
        _intel_available = True
    except ImportError:
        st.error("Module intelligence.py introuvable.")

    if _intel_available:
        # ── Stats formats ──────────────────────────────────────────────────
        st.markdown("#### 📊 Formats détectés dans ta base")

        if not transcriptions:
            st.info("Aucune transcription — scrape des marques d'abord.")
        else:
            # Classifier les entrées qui n'ont pas encore de format
            json_path = OUTPUT_DIR / "all_transcriptions.json"
            _unclassified = [r for r in transcriptions if not r.get("ad_format")]
            if _unclassified:
                _tc, _changed = classify_all(transcriptions)
                if _changed and json_path.exists():
                    json_path.write_text(
                        json.dumps(_tc, ensure_ascii=False, indent=2), encoding="utf-8"
                    )
                    transcriptions = _tc

            # Distribution par format
            _fmt_counts = {}
            for r in transcriptions:
                f = r.get("ad_format", "ugc")
                _fmt_counts[f] = _fmt_counts.get(f, 0) + 1

            _fmt_cols = st.columns(min(len(_fmt_counts), 4))
            for i, (fmt, count) in enumerate(sorted(_fmt_counts.items(), key=lambda x: -x[1])):
                _fmt_info = AD_FORMATS.get(fmt, {"name": fmt, "description": ""})
                _fmt_cols[i % 4].metric(_fmt_info["name"], f"{count} pub{'s' if count > 1 else ''}")

            # Niche breakdown si marques disponibles
            if BRANDS_AVAILABLE:
                _brands_all = load_brands()
                _niches = {}
                for b in _brands_all:
                    n = b.get("niche", "🐾 Animaux")
                    _niches[n] = _niches.get(n, 0) + 1
                if _niches:
                    st.caption("**Niches :** " + " · ".join(f"{n} ({c} marque{'s' if c > 1 else ''})" for n, c in _niches.items()))

            st.markdown("---")

            # ── Scores hooks ───────────────────────────────────────────────
            st.markdown("#### 🎣 Analyse des hooks")
            _hooks_scored = [r for r in transcriptions if r.get("hook_scoring")]
            _hooks_unscored = [r for r in transcriptions if not r.get("hook_scoring") and r.get("hook_3s")]

            if _hooks_scored:
                # Classement hooks par score stop-scroll
                _hooks_ranked = sorted(
                    _hooks_scored,
                    key=lambda r: (r.get("hook_scoring") or {}).get("stop_scroll_score", 0),
                    reverse=True
                )
                _mech_counts = {}
                for r in _hooks_scored:
                    m = (r.get("hook_scoring") or {}).get("mechanism_label", "?")
                    _mech_counts[m] = _mech_counts.get(m, 0) + 1

                _h1, _h2 = st.columns([3, 2])
                with _h1:
                    st.caption(f"**{len(_hooks_scored)} hooks scorés** · Mécanismes dominants : " +
                               " · ".join(f"{m} ({c})" for m, c in sorted(_mech_counts.items(), key=lambda x: -x[1])[:4]))
                with _h2:
                    if st.button("🎣 Scorer les hooks manquants", key="score_missing_hooks",
                                 disabled=not _hooks_unscored or not api_key):
                        from scorer import score_hook
                        from product_context import load_context, format_for_prompt as _fprod
                        _prod_str = _fprod(load_context())
                        _prog = st.progress(0)
                        for _i, _r in enumerate(_hooks_unscored):
                            _r["hook_scoring"] = score_hook(_r.get("hook_3s",""), api_key, _prod_str)
                            _prog.progress((_i+1)/len(_hooks_unscored))
                        _save_transcriptions(transcriptions)
                        st.rerun()

                for _r in _hooks_ranked[:5]:
                    _hs = _r.get("hook_scoring", {})
                    _ss = _hs.get("stop_scroll_score", "?")
                    _mech = _hs.get("mechanism_label", "?")
                    _trigger = _hs.get("emotional_trigger", "")
                    _hook_txt = _r.get("hook_3s") or ""
                    _ss_color = "#155724" if isinstance(_ss, (int,float)) and _ss >= 8 else ("#856404" if isinstance(_ss, (int,float)) and _ss >= 6 else "#721c24")
                    _ss_bg = "#d4edda" if isinstance(_ss, (int,float)) and _ss >= 8 else ("#fff3cd" if isinstance(_ss, (int,float)) and _ss >= 6 else "#f8d7da")
                    st.markdown(f"""
<div style="background:#fff;border:1px solid #e8e8e8;border-radius:12px;padding:12px 16px;margin-bottom:8px">
  <div style="display:flex;gap:8px;align-items:center;margin-bottom:8px;flex-wrap:wrap">
    <span style="background:{_ss_bg};color:{_ss_color};border-radius:8px;padding:2px 10px;font-size:12px;font-weight:800">🎣 {_ss}/10</span>
    <span style="background:#f0f0f0;border-radius:8px;padding:2px 10px;font-size:11px;font-weight:600">{_mech}</span>
    <span style="color:#aaa;font-size:11px">⚡ {_trigger}</span>
    <span style="color:#aaa;font-size:11px">🏢 {_r.get("page_name","?")}</span>
  </div>
  <div style="font-size:13.5px;font-weight:600;color:#0a0a0a;font-style:italic">"{_hook_txt[:150]}"</div>
  {f'<div style="font-size:11px;color:#666;margin-top:6px;padding:6px 10px;background:#f9f9f9;border-radius:6px">💡 {_hs.get("improved_version","")}</div>' if _hs.get("improved_version") else ""}
</div>
""", unsafe_allow_html=True)
            elif _hooks_unscored:
                st.info(f"{len(_hooks_unscored)} hooks à scorer — clique sur le bouton ci-dessus.")
                if st.button("🎣 Scorer tous les hooks", key="score_all_hooks", type="primary",
                             disabled=not api_key):
                    from scorer import score_hook
                    from product_context import load_context, format_for_prompt as _fprod
                    _prod_str = _fprod(load_context())
                    _prog = st.progress(0)
                    for _i, _r in enumerate(_hooks_unscored):
                        _r["hook_scoring"] = score_hook(_r.get("hook_3s",""), api_key, _prod_str)
                        _prog.progress((_i+1)/len(_hooks_unscored))
                    _save_transcriptions(transcriptions)
                    st.rerun()
            else:
                st.caption("Re-scrape pour obtenir les hooks 0-3s analysés.")

            # ── Clustering sémantique ──────────────────────────────────────
            st.markdown("---")
            st.markdown("#### 🧬 Clusters de mécanismes psychologiques")
            _cached_clusters = st.session_state.get("_hook_clusters")
            _cl1, _cl2 = st.columns([2, 3])
            _run_clusters = _cl1.button(
                "🧬 Identifier les mécanismes",
                type="primary",
                disabled=not api_key or len(transcriptions) < 3,
                key="run_cluster_analysis",
            )
            _cl2.caption("Claude regroupe tous tes hooks par mécanique psychologique sous-jacente — indépendamment des mots.")

            if _run_clusters:
                with st.spinner("Clustering sémantique en cours..."):
                    _cached_clusters = cluster_hooks(transcriptions, api_key)
                    st.session_state["_hook_clusters"] = _cached_clusters

            if _cached_clusters and "error" not in _cached_clusters:
                _clusters = _cached_clusters.get("clusters", [])
                _dominant = _cached_clusters.get("dominant_mechanism", "")
                _underused = _cached_clusters.get("underused_opportunity", "")
                _reco = _cached_clusters.get("recommendation", "")

                if _reco:
                    st.markdown(f"""<div style="background:#0a0a0a;color:#fff;border-radius:12px;padding:14px 18px;margin-bottom:16px;font-size:13.5px;line-height:1.6">
💡 <b>Recommandation stratégique</b><br>{_reco}
</div>""", unsafe_allow_html=True)

                if _underused:
                    st.markdown(f"""<div style="background:#fff3cd;border:1px solid #ffc107;border-radius:10px;padding:10px 14px;margin-bottom:14px;font-size:13px">
🎯 <b>Opportunité non exploitée</b> — {_underused}
</div>""", unsafe_allow_html=True)

                _cluster_cols = st.columns(min(len(_clusters), 2))
                for _ci, _cl in enumerate(_clusters):
                    with _cluster_cols[_ci % 2]:
                        _cl_ids = _cl.get("hook_ids", [])
                        _cl_avg = _cl.get("strength_avg")
                        st.markdown(f"""
<div style="background:#fff;border:1px solid #e8e8e8;border-radius:12px;padding:14px 16px;margin-bottom:10px">
  <div style="font-weight:800;font-size:14px;color:#0a0a0a">{_cl.get("label","")}</div>
  <div style="font-size:11px;color:#888;margin:4px 0">{len(_cl_ids)} pubs · avg {_cl_avg}/10</div>
  <div style="font-size:12.5px;color:#444;margin:6px 0;line-height:1.5">{_cl.get("why_it_works","")}</div>
  <div style="background:#f5f5f5;border-radius:8px;padding:8px 10px;font-size:12px;font-style:italic;color:#333;margin-top:6px">
    📋 {_cl.get("template","")}
  </div>
  <div style="font-size:11px;color:#888;margin-top:6px">🎯 {_cl.get("best_contexts","")}</div>
</div>
""", unsafe_allow_html=True)

            st.markdown("---")

            # ── Comparaison cross-sections ────────────────────────────────
            st.markdown("#### 📊 Comparaison par section")
            _sections_data = compare_sections(transcriptions)
            if _sections_data:
                _sec_cols = st.columns(min(len(_sections_data), 3))
                for _si, (_sec_name, _sec_stats) in enumerate(_sections_data.items()):
                    with _sec_cols[_si % 3]:
                        _avg_r = _sec_stats.get("avg_reach")
                        _avg_hs = _sec_stats.get("avg_hook_score")
                        _top_fmt = _sec_stats.get("top_format") or "?"
                        _top_mech = _sec_stats.get("top_mechanism") or "?"
                        _fmt_info = AD_FORMATS.get(_top_fmt, {})
                        st.markdown(f"""
<div style="background:#fff;border:2px solid #0a0a0a;border-radius:12px;padding:14px 16px;margin-bottom:10px">
  <div style="font-weight:800;font-size:14px;color:#0a0a0a;margin-bottom:10px">{_sec_name}</div>
  <div style="font-size:12px;color:#444;margin-bottom:4px">📢 <b>{_sec_stats['ad_count']}</b> pubs</div>
  <div style="font-size:12px;color:#444;margin-bottom:4px">👁 Reach moyen : <b>{f"{_avg_r:,}" if _avg_r else "N/A"}</b></div>
  <div style="font-size:12px;color:#444;margin-bottom:4px">🎣 Hook score moyen : <b>{_avg_hs or "N/A"}/10</b></div>
  <div style="font-size:12px;color:#444;margin-bottom:4px">🎬 Format dominant : <b>{_fmt_info.get("name", _top_fmt)}</b></div>
  <div style="font-size:12px;color:#444">🧠 Mécanisme : <b>{_top_mech}</b></div>
</div>
""", unsafe_allow_html=True)
            else:
                st.caption("Données insuffisantes — scrape plusieurs marques dans différentes sections.")

            st.markdown("---")

            # ── Générateur de brief vidéo ──────────────────────────────────
            st.markdown("#### 🎬 Générateur de brief vidéo")
            st.caption("Claude analyse tes top performers et génère un brief complet prêt pour ton équipe de production.")
            _brief_col1, _brief_col2 = st.columns([2, 2])
            _brief_objective = _brief_col1.text_input(
                "Objectif du brief",
                value="Acquérir de nouveaux clients pet supplement",
                key="brief_objective",
            )
            _run_brief = _brief_col2.button(
                "🎬 Générer le brief",
                type="primary",
                disabled=not api_key or len(transcriptions) < 2,
                key="run_brief_gen",
            )
            _cached_brief = st.session_state.get("_video_brief")

            if _run_brief:
                with st.spinner("Génération du brief en cours..."):
                    from product_context import load_context, format_for_prompt as _fprod
                    _prod_ctx = _fprod(load_context())
                    _cached_brief = generate_video_brief(transcriptions, api_key, _prod_ctx, _brief_objective)
                    st.session_state["_video_brief"] = _cached_brief

            if _cached_brief and "error" not in _cached_brief:
                _brief_concept = _cached_brief.get("concept", "")
                _brief_hook = _cached_brief.get("hook", {})
                _brief_struct = _cached_brief.get("structure", [])
                _brief_fmt = _cached_brief.get("format", "")
                _brief_casting = _cached_brief.get("casting", "")
                _brief_music = _cached_brief.get("music_mood", "")
                _brief_overlays = _cached_brief.get("text_overlays", [])
                _brief_duration = _cached_brief.get("duration", "")
                _brief_kpis = _cached_brief.get("kpis_target", {})

                st.markdown(f"""
<div style="background:#0a0a0a;color:#fff;border-radius:14px;padding:18px 22px;margin-bottom:16px">
  <div style="font-size:11px;font-weight:700;letter-spacing:2px;color:#888;margin-bottom:6px">CONCEPT</div>
  <div style="font-size:16px;font-weight:800;line-height:1.4">{_brief_concept}</div>
  <div style="font-size:12px;color:#888;margin-top:8px">Format : <b style="color:#fff">{_brief_fmt}</b> · Durée : <b style="color:#fff">{_brief_duration}</b> · {_cached_brief.get("format_reason","")}</div>
</div>
""", unsafe_allow_html=True)

                # Hook
                if _brief_hook:
                    st.markdown(f"""
<div style="background:#f0f8ff;border:2px solid #0a0a0a;border-radius:12px;padding:14px 18px;margin-bottom:12px">
  <div style="font-size:11px;font-weight:700;letter-spacing:2px;color:#888;margin-bottom:6px">🎣 HOOK (0-3s)</div>
  <div style="font-size:15px;font-weight:800;color:#0a0a0a;font-style:italic">"{_brief_hook.get('script','')}"</div>
  <div style="font-size:12px;color:#444;margin-top:6px">👁 Visuel : {_brief_hook.get('visual','')}</div>
  <div style="font-size:12px;color:#444;margin-top:4px">🧠 Mécanisme : {_brief_hook.get('mechanism','')} — {_brief_hook.get('why','')}</div>
</div>
""", unsafe_allow_html=True)

                # Structure
                if _brief_struct:
                    st.markdown("**📋 Structure narrative**")
                    for _section in _brief_struct:
                        with st.expander(_section.get("section", ""), expanded=True):
                            st.markdown(f"**Script** : *\"{_section.get('script','')}\"*")
                            st.markdown(f"**Visuel** : {_section.get('visual','')}")

                # Production notes
                _prod_c1, _prod_c2, _prod_c3 = st.columns(3)
                if _brief_casting:
                    _prod_c1.markdown(f"**🎭 Casting**\n\n{_brief_casting}")
                if _brief_music:
                    _prod_c2.markdown(f"**🎵 Musique**\n\n{_brief_music}")
                if _brief_overlays:
                    _prod_c3.markdown("**📝 Overlays texte**\n\n" + "\n".join(f"• {o}" for o in _brief_overlays))

                # KPIs
                if _brief_kpis:
                    est_score = _brief_kpis.get("estimated_hook_score", "?")
                    hook_rate = _brief_kpis.get("hook_rate_target", "?")
                    why_works = _brief_kpis.get("why_it_will_work", "")
                    st.markdown(f"""
<div style="background:#d4edda;border:1px solid #28a745;border-radius:10px;padding:12px 16px;margin-top:12px">
  🎯 <b>Objectifs prédits</b> — Hook score estimé : <b>{est_score}/10</b> · Rétention 3s cible : <b>{hook_rate}</b><br>
  <span style="font-size:12px;color:#155724">{why_works}</span>
</div>
""", unsafe_allow_html=True)

                # Export texte
                _brief_text = f"""BRIEF VIDÉO — METRIC LAB
========================
Concept : {_brief_concept}
Format : {_brief_fmt} | Durée : {_brief_duration}

HOOK (0-3s)
Script : "{_brief_hook.get('script','')}"
Visuel : {_brief_hook.get('visual','')}
Mécanisme : {_brief_hook.get('mechanism','')}

STRUCTURE
"""
                for _s in _brief_struct:
                    _brief_text += f"\n{_s.get('section','')}\nScript : {_s.get('script','')}\nVisuel : {_s.get('visual','')}\n"

                st.download_button(
                    "📥 Télécharger le brief",
                    data=_brief_text,
                    file_name="brief_video_metriclab.txt",
                    mime="text/plain",
                    key="dl_brief",
                )

            st.markdown("---")

            # ── Analyse de patterns ────────────────────────────────────────
            st.markdown("#### 🧠 Patterns structurels gagnants")
            st.caption("Claude analyse toutes tes pubs scrapées et extrait les mécaniques communes aux meilleures.")

            _cached_patterns = st.session_state.get("_intel_patterns")

            _col_btn, _col_info = st.columns([2, 3])
            _run_analysis = _col_btn.button(
                "🔍 Analyser les patterns",
                type="primary",
                disabled=not api_key or len(transcriptions) < 3,
                key="run_pattern_analysis",
            )
            if len(transcriptions) < 3:
                _col_info.caption("Il faut au moins 3 transcriptions pour l'analyse.")
            elif not api_key:
                _col_info.caption("Clé API requise.")
            else:
                _col_info.caption(f"{len([r for r in transcriptions if r.get('label') == 'Top Performers'])} top performers · {len(set(r.get('page_name') or '' for r in transcriptions))} marques")

            if _run_analysis:
                with st.spinner("Analyse cross-marque en cours (15-30s)..."):
                    _cached_patterns = analyze_patterns(transcriptions, api_key)
                    st.session_state["_intel_patterns"] = _cached_patterns
                    # Sauvegarder les ads utilisées pour l'affichage
                    _tops_used = [r for r in transcriptions if r.get("label") == "Top Performers"] or transcriptions
                    st.session_state["_intel_ads_used"] = _tops_used[:25]

            # ── Pubs utilisées pour l'analyse ──────────────────────────────
            _ads_used = st.session_state.get("_intel_ads_used", [])
            if _ads_used:
                with st.expander(f"📋 {len(_ads_used)} pubs analysées — stats & liens", expanded=False):
                    def _fmt_reach(v):
                        if not v:
                            return "—"
                        v = int(v)
                        if v >= 1_000_000:
                            return f"{v/1_000_000:.1f}M"
                        if v >= 1_000:
                            return f"{v//1_000}k"
                        return str(v)

                    for _au in _ads_used:
                        _au_id = _au.get("ad_id") or ""
                        _au_brand = _au.get("page_name") or "Marque inconnue"
                        _au_fmt = AD_FORMATS.get(_au.get("ad_format", ""), {}).get("name", "—")
                        _au_score = (_au.get("scoring") or {}).get("score_total")
                        _au_reach = _au.get("eu_reach")
                        _au_date = _au.get("start_date") or ""
                        _au_hook = (_au.get("transcript") or "")[:80].strip()

                        _lib_url = f"https://www.facebook.com/ads/library/?id={_au_id}" if _au_id else None

                        _parts = [f"**{_au_brand}**", _au_fmt]
                        if _au_score:
                            _parts.append(f"⭐ {_au_score}/10")
                        if _au_reach:
                            _parts.append(f"📡 {_fmt_reach(_au_reach)} reach EU")
                        if _au_date:
                            _parts.append(f"🗓 {_au_date[:10]}")

                        _col_a, _col_b = st.columns([5, 1])
                        _col_a.markdown(" · ".join(_parts))
                        if _au_hook:
                            _col_a.caption(f"*\"{_au_hook}...\"*")
                        if _lib_url:
                            _col_b.markdown(f"[Voir la pub ↗]({_lib_url})")
                        else:
                            _col_b.caption("Pas d'ID")
                        st.divider()

            if _cached_patterns and "error" not in _cached_patterns:
                # ── Top insights ─────────────────────────────────────
                _insights = _cached_patterns.get("top_3_insights", [])
                if _insights:
                    st.markdown("**💡 Top insights actionnables**")
                    for ins in _insights:
                        st.success(ins)

                # ── Winning elements ──────────────────────────────────
                _winning = _cached_patterns.get("winning_elements", [])
                if _winning:
                    with st.expander("✅ Éléments communs aux pubs gagnantes", expanded=True):
                        for el in _winning:
                            st.markdown(f"- {el}")

                st.markdown("---")

                # ── Hook patterns ─────────────────────────────────────
                _hooks = _cached_patterns.get("hook_patterns", [])
                if _hooks:
                    st.markdown("#### 🪝 Patterns de hooks")
                    _aw_intel = st.radio(
                        "Audience pour les scripts générés",
                        ["🧊 Audience froide — ils ne nous connaissent pas",
                         "🌤 Audience tiède — ils cherchent une solution",
                         "🔥 Audience chaude — retargeting"],
                        horizontal=True,
                        key="intel_awareness",
                        label_visibility="collapsed",
                    )
                    _aw_map = {
                        "🧊 Audience froide — ils ne nous connaissent pas": "cold",
                        "🌤 Audience tiède — ils cherchent une solution": "warm",
                        "🔥 Audience chaude — retargeting": "hot",
                    }
                    _aw_key_intel = _aw_map.get(_aw_intel, "cold")

                    for hi, hook in enumerate(_hooks):
                        with st.expander(
                            f"🪝 **{hook.get('type', 'Pattern')}** — {hook.get('frequence_pct', 0)}% des pubs",
                            expanded=hi == 0,
                        ):
                            st.markdown(f"**Comment ça marche :** {hook.get('description', '')}")
                            st.markdown(f"**Pourquoi :** {hook.get('pourquoi_ca_marche', '')}")
                            st.code(hook.get('exemple', ''), language=None)

                            if st.button(f"⚡ Générer 2 scripts avec ce hook", key=f"gen_hook_{hi}"):
                                st.session_state[f"_gen_hook_{hi}"] = True

                            if st.session_state.get(f"_gen_hook_{hi}"):
                                _prod_ctx = format_for_prompt(load_context()) if AGENT_AVAILABLE else ""
                                _out = st.empty()
                                _txt = ""
                                with st.spinner("Génération..."):
                                    for chunk in generate_from_pattern_stream(hook, _prod_ctx, api_key, _aw_key_intel):
                                        _txt += chunk
                                        _out.markdown(_txt)
                                _out.markdown(_txt)

                # ── Body structures ───────────────────────────────────
                _bodies = _cached_patterns.get("body_structures", [])
                if _bodies:
                    st.markdown("#### 📐 Structures de corps")
                    for bi, body in enumerate(_bodies):
                        with st.expander(f"📐 **{body.get('type', 'Structure')}** — {body.get('frequence_pct', 0)}%"):
                            etapes = body.get("etapes", [])
                            if etapes:
                                for j, e in enumerate(etapes, 1):
                                    st.markdown(f"{j}. {e}")
                            st.code(body.get("exemple", ""), language=None)
                            _fmts = body.get("formats_associes", [])
                            if _fmts:
                                st.caption("Formats : " + " · ".join(AD_FORMATS.get(f, {}).get("name", f) for f in _fmts))

                            if st.button(f"⚡ Générer avec cette structure", key=f"gen_body_{bi}"):
                                st.session_state[f"_gen_body_{bi}"] = True

                            if st.session_state.get(f"_gen_body_{bi}"):
                                _prod_ctx = format_for_prompt(load_context()) if AGENT_AVAILABLE else ""
                                _out2 = st.empty()
                                _txt2 = ""
                                with st.spinner("Génération..."):
                                    for chunk in generate_from_pattern_stream(body, _prod_ctx, api_key, _aw_key_intel):
                                        _txt2 += chunk
                                        _out2.markdown(_txt2)
                                _out2.markdown(_txt2)

                # ── CTA patterns ──────────────────────────────────────
                _ctas = _cached_patterns.get("cta_patterns", [])
                if _ctas:
                    st.markdown("#### 📣 Patterns de CTA")
                    for ci, cta in enumerate(_ctas):
                        st.markdown(f"**{cta.get('type', '')}** ({cta.get('frequence_pct', 0)}%) — {cta.get('description', '')}")
                        st.code(cta.get("exemple", ""), language=None)

                # ── Format insights ───────────────────────────────────
                _fmt_insights = _cached_patterns.get("format_insights", {})
                if _fmt_insights:
                    st.markdown("---")
                    st.markdown("#### 🎬 Ce qui marche par format")
                    for fmt_key, insight in _fmt_insights.items():
                        fmt_name = AD_FORMATS.get(fmt_key, {}).get("name", fmt_key)
                        st.markdown(f"**{fmt_name}** — {insight}")

            elif _cached_patterns and "error" in _cached_patterns:
                st.error(f"Erreur d'analyse : {_cached_patterns['error']}")


# ══════════════════════════════════════════════
# ONGLET 4 — GÉNÉRATEUR DE COPY
# ══════════════════════════════════════════════
if _nav == "✍️ Générer du Copy":
    st.markdown("### ✍️ Générer du copy inspiré des top performers")

    if not transcriptions:
        st.warning("Aucune transcription disponible. Lance d'abord un scraping.")
    else:
        tops = [r for r in transcriptions if r.get("label") == "Top Performers"]
        st.caption(f"{len(tops)} Top Performers disponibles comme source d'inspiration")

        c1, c2 = st.columns(2)
        with c1:
            brand   = st.text_input("🏷️ Nom de ta marque", placeholder="ex: Jacqueline's Lab")
            product = st.text_area("📦 Décris ton produit", placeholder="Compléments alimentaires pour chiens...", height=80)
        with c2:
            benefits = st.text_area("✨ Bénéfices clés", placeholder="Ingrédients lisibles, améliore la digestion...", height=80)
            tone     = st.text_input("🎙️ Ton souhaité", value="direct et authentique")

        nb_scripts = st.slider("Nombre de scripts à générer", 1, 5, 3)

        generate_btn = st.button(
            "🤖 Générer avec Claude",
            type="primary",
            disabled=not (brand and product and os.environ.get("ANTHROPIC_API_KEY")),
        )
        if not os.environ.get("ANTHROPIC_API_KEY"):
            st.caption("⚠️ Entre ta clé Anthropic dans la barre latérale pour activer ce bouton.")

        if generate_btn:
            with st.spinner(f"Claude génère {nb_scripts} scripts pour {brand}..."):
                result = subprocess.run(
                    [
                        PYTHON, "generate_copy.py",
                        "--brand", brand,
                        "--product", product,
                        "--benefits", benefits,
                        "--tone", tone,
                        "--n", str(nb_scripts),
                    ],
                    capture_output=True, text=True,
                    cwd=str(BASE_DIR),
                    env={**os.environ, "ANTHROPIC_API_KEY": os.environ.get("ANTHROPIC_API_KEY", "")},
                )

            if result.returncode == 0:
                gen_files_updated = sorted(GENERATED_DIR.glob("*.txt"), key=lambda f: f.stat().st_mtime, reverse=True)
                if gen_files_updated:
                    content = gen_files_updated[0].read_text(encoding="utf-8")
                    st.success("✅ Scripts générés !")
                    scripts_section = content.split("Ton :", 1)[-1].strip() if "Ton :" in content else content
                    st.markdown("---")
                    st.markdown(scripts_section)
                    st.markdown("---")
                    st.download_button(
                        "⬇️ Télécharger les scripts",
                        data=content.encode("utf-8"),
                        file_name=gen_files_updated[0].name,
                        mime="text/plain",
                    )
                    st.rerun()
            else:
                st.error("Erreur lors de la génération.")
                st.code(result.stdout + result.stderr)


# ══════════════════════════════════════════════
# ONGLET 4 — HISTORIQUE
# ══════════════════════════════════════════════
if _nav == "📁 Historique":
    st.markdown("### 📁 Scripts générés")

    gen_files_all = sorted(GENERATED_DIR.glob("*.txt"), key=lambda f: f.stat().st_mtime, reverse=True)
    if not gen_files_all:
        st.info("Aucun script généré pour l'instant.")
    else:
        for f in gen_files_all:
            with st.expander(f"📄 {f.stem}", expanded=False):
                content = f.read_text(encoding="utf-8")
                st.markdown(content)
                st.download_button(
                    "⬇️ Télécharger",
                    data=content.encode("utf-8"),
                    file_name=f.name,
                    mime="text/plain",
                    key=f"dl_{f.name}",
                )

    st.markdown("---")
    st.markdown("### 📄 Transcriptions récentes")
    if transcriptions:
        search = st.text_input("🔍 Rechercher dans les transcriptions", placeholder="Ex: ballonnements")
        filtered = [r for r in transcriptions if not search or search.lower() in r.get("transcript","").lower()]
        st.caption(f"{len(filtered)} résultats")
        for r in filtered[:20]:
            label = r.get("label","?")
            pos   = r.get("position","?")
            lang  = r.get("lang","?")
            icon  = "🏆" if label == "Top Performers" else "🆕"
            va = r.get("visual_analysis") or {}
            has_vision = isinstance(va, dict) and va
            vision_icon = " 📷" if has_vision else ""
            with st.expander(f"{icon} {label} #{pos} · {lang}{vision_icon}", expanded=False):
                if has_vision:
                    cols = st.columns(3)
                    if va.get("scene_type"):
                        cols[0].markdown(f'<span class="context-pill">📷 {va["scene_type"]}</span>', unsafe_allow_html=True)
                    if va.get("visual_style"):
                        cols[1].markdown(f'<span class="context-pill green">🎨 {va["visual_style"]}</span>', unsafe_allow_html=True)
                    if va.get("hook_visual"):
                        st.caption(f"👁 Hook visuel : {va['hook_visual']}")
                    if va.get("text_overlays"):
                        overlays = [t for t in va["text_overlays"] if t]
                        if overlays:
                            st.caption(f"💬 Textes à l'écran : {' / '.join(overlays[:4])}")

                # Miniature du hook (frame 0)
                frames_dir = OUTPUT_DIR / "frames"
                safe_label = label.replace(" ", "_").lower()
                frame_0 = frames_dir / f"{safe_label}_{int(pos):02d}_t0.jpg"
                if frame_0.exists():
                    st.image(str(frame_0), width=240, caption="Frame 0s (hook visuel)")

                st.write(r.get("transcript",""))
    else:
        st.info("Lance un scraping pour voir les transcriptions.")


# ══════════════════════════════════════════════
# ONGLET 5 — AGENT EXPERT
# ══════════════════════════════════════════════
if _nav == "🤖 Agent Expert":
    _at1, _at2 = st.columns([4, 2])
    _at1.markdown("### 🤖 Agent Expert — Scripts Vidéo Meta Ads")
    if _at2.button("Étape suivante : générer le deck →", key="next_to_deck",
                   use_container_width=True):
        st.session_state["_nav_to"] = "📝 Deck Scripts"
        st.rerun()

    if not AGENT_AVAILABLE:
        st.error("Modules agent.py / product_context.py introuvables. Vérifie que les fichiers sont présents.")
        st.stop()

    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        st.warning("⚠️ Entre ta clé Anthropic dans la barre latérale pour activer l'agent.")
        st.stop()

    # ── Contexte produit ──────────────────────
    current_ctx = load_context()

    with st.expander(
        "🏷️ Connaissance produit / marque",
        expanded=not (current_ctx.get("scraped") or current_ctx.get("manual")),
    ):
        col_url, col_btn = st.columns([4, 1])
        with col_url:
            website_url = st.text_input(
                "URL de ton site ou page produit",
                placeholder="https://tonsite.com ou https://tonsite.com/produit",
                key="product_url_input",
            )
        with col_btn:
            st.markdown("<div style='margin-top:28px'>", unsafe_allow_html=True)
            import_btn = st.button("⬇️ Importer", key="import_website_btn")
            st.markdown("</div>", unsafe_allow_html=True)

        if import_btn and website_url:
            with st.spinner(f"Import multi-pages + images de {website_url}..."):
                try:
                    from product_context import scrape_website_deep, analyze_product_images
                    scraped = scrape_website_deep(website_url, max_pages=5)
                    if scraped.get("images") and os.environ.get("ANTHROPIC_API_KEY"):
                        vis = analyze_product_images(scraped["images"], os.environ["ANTHROPIC_API_KEY"])
                        if vis:
                            scraped["visual_insights"] = vis
                            st.info(f"📷 Identité visuelle : {vis.get('product_type','')} · {vis.get('mood','')}")
                    existing = current_ctx.get("scraped", [])
                    existing = [s for s in existing if s.get("url") != website_url]
                    existing.insert(0, scraped)
                    current_ctx["scraped"] = existing
                    save_context(current_ctx)
                    pages_n = len(scraped.get("pages_scraped", []))
                    st.success(f"✅ Importé : {scraped.get('title', website_url)} ({pages_n} pages)")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erreur : {e}")

        manual_text = st.text_area(
            "Infos supplémentaires (persona cible, ton de marque, ingrédients, contraintes, ce qui différencie...)",
            value=current_ctx.get("manual", ""),
            height=130,
            placeholder=(
                "Ex : Notre cliente type a 35-50 ans, elle cherche des solutions naturelles pour ses animaux. "
                "Notre ton : bienveillant mais direct, jamais médical. "
                "Différenciateur : formules vétérinaires sans arômes artificiels."
            ),
            key="manual_info_input",
        )

        if st.button("💾 Sauvegarder", key="save_ctx_btn"):
            current_ctx["manual"] = manual_text
            save_context(current_ctx)
            st.success("Contexte sauvegardé ✓")
            if "agent" in st.session_state:
                del st.session_state["agent"]

        # Supprimer un site importé
        if current_ctx.get("scraped"):
            st.markdown("**Sites importés :**")
            for i, site in enumerate(current_ctx["scraped"]):
                col_s, col_d = st.columns([5, 1])
                col_s.markdown(f"🌐 [{site.get('title', site['url'])}]({site['url']})")
                if col_d.button("✕", key=f"del_site_{i}"):
                    current_ctx["scraped"].pop(i)
                    save_context(current_ctx)
                    if "agent" in st.session_state:
                        del st.session_state["agent"]
                    st.rerun()

    # ── Objectif éducatif & scoring ──────────
    if SCORER_AVAILABLE:
        _scoring_ctx = load_scoring_context()
        with st.expander(
            "🎯 Objectif éducatif & scoring automatique",
            expanded=not _scoring_ctx.get("objective"),
        ):
            st.caption("Décris ton objectif — Claude scorera chaque pub selon ces critères à chaque scraping.")
            _objective_text = st.text_area(
                "Objectif éducatif / profil d'ad idéal pour toi",
                value=_scoring_ctx.get("objective", ""),
                height=120,
                placeholder=(
                    "Ex : Je veux éduquer des femmes 35-55 ans sur les bienfaits des probiotiques "
                    "pour la digestion. L'ad idéale explique un problème concret, utilise un langage "
                    "simple et bienveillant, montre une vraie transformation et donne envie d'essayer "
                    "sans pression. Ton authentique, pas médical."
                ),
                key="scoring_objective_input",
            )
            _col_sv, _col_rs = st.columns([1, 2])
            with _col_sv:
                if st.button("💾 Sauvegarder l'objectif", key="save_scoring_obj"):
                    save_scoring_context({"objective": _objective_text})
                    st.success("Objectif sauvegardé ✓")
                    _scoring_ctx = {"objective": _objective_text}
            with _col_rs:
                _unscored = [r for r in transcriptions if not r.get("scoring")]
                _scored_n = len(transcriptions) - len(_unscored)
                _rescore_btn = st.button(
                    f"🤖 Scorer les pubs ({_scored_n}/{len(transcriptions)} déjà scorées)",
                    key="rescore_all_btn",
                    disabled=not api_key or not transcriptions,
                    type="primary",
                )

            if _rescore_btn:
                _prod_str = format_for_prompt(load_context()) if AGENT_AVAILABLE else ""
                _obj = _scoring_ctx.get("objective", _objective_text)
                _prog = st.progress(0)
                _status = st.empty()
                _n_new = 0
                for _i, _entry in enumerate(transcriptions):
                    if not _entry.get("scoring"):
                        _status.text(f"Scoring #{_entry.get('position', _i+1)} — {_entry.get('label', '')}…")
                        _s = score_ad(_entry.get("transcript", ""), api_key, _prod_str, _obj)
                        if _s:
                            _entry["scoring"] = _s
                            _n_new += 1
                    _prog.progress((_i + 1) / len(transcriptions))
                if _n_new > 0:
                    json_path.write_text(
                        json.dumps(transcriptions, ensure_ascii=False, indent=2), encoding="utf-8"
                    )
                    subprocess.run([PYTHON, "regenerate_report.py"], capture_output=True, cwd=str(BASE_DIR))
                    _status.success(f"✅ {_n_new} pub(s) scorée(s) ! Rapport régénéré.")
                    st.rerun()
                else:
                    _status.info("Toutes les pubs étaient déjà scorées.")

    # ── Status du contexte chargé ─────────────
    ctx_pills = []
    if transcriptions:
        tops_n = sum(1 for r in transcriptions if r.get("label") == "Top Performers")
        ctx_pills.append(f'<span class="context-pill">📊 {len(transcriptions)} transcriptions ({tops_n} top)</span>')
    if vision_count:
        ctx_pills.append(f'<span class="context-pill">📷 {vision_count} analyses visuelles</span>')
    if scored_entries:
        score_pill_cls = "green" if avg_score and avg_score >= 7 else "orange"
        ctx_pills.append(f'<span class="context-pill {score_pill_cls}">⭐ {len(scored_entries)} pubs scorées · moy. {avg_score}/10</span>')
    if current_ctx.get("scraped"):
        ctx_pills.append(f'<span class="context-pill green">🌐 {len(current_ctx["scraped"])} site(s) importé(s)</span>')
    if current_ctx.get("manual", "").strip():
        ctx_pills.append('<span class="context-pill orange">✏️ Notes manuelles</span>')

    if ctx_pills:
        st.markdown("**Contexte chargé :** " + " ".join(ctx_pills), unsafe_allow_html=True)
    else:
        st.info("Aucun contexte chargé — scrape des marques et importe ton site pour un agent plus précis.")

    st.markdown("---")

    # ── Initialisation de l'agent ─────────────
    product_ctx_str = format_for_prompt(current_ctx)
    agent_key = f"{api_key}_{len(transcriptions)}_{len(product_ctx_str)}"

    if "agent" not in st.session_state or st.session_state.get("agent_key") != agent_key:
        st.session_state.agent = ScriptExpertAgent(api_key, product_ctx_str)
        st.session_state.agent_key = agent_key
        if "agent_messages" not in st.session_state:
            st.session_state.agent_messages = []

    agent: ScriptExpertAgent = st.session_state.agent

    # ── Actions rapides ───────────────────────
    col_q1, col_q2, col_q3, col_q4 = st.columns(4)
    quick_prompt = None

    with col_q1:
        if st.button("📊 Patterns top performers", key="q1"):
            quick_prompt = (
                "Analyse en profondeur les patterns récurrents dans mes top performers. "
                "Je veux : les mécaniques de hook les plus utilisées, les structures narratives, "
                "les mots et tournures qui reviennent, et si tu as des données visuelles, "
                "le type de format qui domine. Donne-moi 5 insights actionnables numérotés."
            )
    with col_q2:
        if st.button("🎣 8 hooks pour mon produit", key="q2"):
            quick_prompt = (
                "Génère 8 hooks vidéo percutants pour mon produit en te basant sur les mécaniques "
                "de mes top performers. Classe-les par type (pattern interrupt, question, "
                "contre-intuitif, preuve sociale, POV, behind the scenes...). "
                "Chaque hook doit être prêt à être dit à l'oral."
            )
    with col_q3:
        if st.button("📝 Script UGC complet", key="q3"):
            quick_prompt = (
                "Crée un script UGC complet de 30-45 secondes pour mon produit. "
                "Format authentique, caméra à la main. Inclus : hook percutant (0-3s), "
                "développement avec preuve sociale ou transformation, CTA naturel. "
                "Base-toi sur les patterns de mes top performers."
            )
    with col_q4:
        if st.button("🔄 Reset conversation", key="q_reset"):
            st.session_state.agent_messages = []
            agent.reset_history()
            st.rerun()

    # ── Zone de script à analyser ─────────────
    with st.expander("🔬 Coller un script à analyser"):
        script_to_analyze = st.text_area(
            "Script ou transcription à critiquer",
            height=150,
            placeholder="Colle ici un script vidéo, une transcription de pub ou tes propres idées...",
            key="script_analyze_input",
        )
        if st.button("Analyser ce script", key="analyze_btn") and script_to_analyze.strip():
            quick_prompt = (
                f"Analyse ce script :\n\n---\n{script_to_analyze.strip()}\n---\n\n"
                "Donne : score /10, problème principal identifié, réécriture ciblée de ce qui cloche."
            )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Historique du chat ────────────────────
    for msg in st.session_state.agent_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # ── Traitement quick prompt ou input ──────
    def handle_chat(prompt: str):
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state.agent_messages.append({"role": "user", "content": prompt})

        with st.chat_message("assistant"):
            try:
                response = st.write_stream(agent.chat_stream(prompt))
            except Exception as e:
                response = f"Erreur : {e}"
                st.error(response)
        st.session_state.agent_messages.append({"role": "assistant", "content": response})

    if quick_prompt:
        handle_chat(quick_prompt)
        st.rerun()

    if user_input := st.chat_input("Pose ta question à l'expert script..."):
        handle_chat(user_input)
        st.rerun()


# ══════════════════════════════════════════════
# ONGLET 7 — DECK SCRIPTS
# ══════════════════════════════════════════════
if _nav == "📝 Deck Scripts":
    st.markdown("### 📝 Deck de Scripts — Multi-angles")
    st.caption("7 angles d'attaque × 3 variantes. L'app analyse ton produit et tes top performers pour générer un deck prêt à filmer.")

    if not DECK_AVAILABLE:
        st.error("Module script_deck.py introuvable.")
    elif not AGENT_AVAILABLE:
        st.error("Module agent.py introuvable.")
    else:
        _deck_api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
        if not _deck_api_key:
            st.warning("⚠️ Entre ta clé Anthropic dans la barre latérale.")
        else:
            # ── Contexte produit ──
            _deck_ctx = load_context()
            _deck_prod_str = format_for_prompt(_deck_ctx)
            if not _deck_prod_str.strip():
                st.warning("⚠️ Aucun contexte produit. Va dans **🤖 Agent Expert** → importe ton site.")
            else:
                st.success(f"✅ Contexte produit chargé ({len(_deck_prod_str)} caractères)", icon="🏷️")

            # ── Niveau de conscience de l'audience ──
            st.markdown("#### Qui va voir ces pubs ?")
            _aw_keys = list(AWARENESS_LEVELS.keys())
            _awareness = st.radio(
                "Niveau de conscience de ton audience",
                _aw_keys,
                index=0,
                format_func=lambda k: AWARENESS_LEVELS[k]["name"],
                horizontal=True,
                key="deck_awareness",
                label_visibility="collapsed",
            )
            st.caption(f"💡 {AWARENESS_LEVELS[_awareness]['description']}")

            st.markdown("---")

            # ── Sélection des angles ──
            st.markdown("#### Angles à couvrir")
            _selected_angles = []
            _angle_cols = st.columns(4)
            for i, (key, angle) in enumerate(ANGLES.items()):
                checked = _angle_cols[i % 4].checkbox(
                    f"{angle['name']}",
                    value=True,
                    help=angle["description"],
                    key=f"angle_{key}",
                )
                if checked:
                    _selected_angles.append(key)

            st.caption(f"{len(_selected_angles)} angle(s) sélectionné(s) → {len(_selected_angles) * 3} scripts générés")
            if _awareness == "cold":
                st.caption("🧊 Les plus efficaces sur audience froide : 🎓 Éducatif · 🎯 Problème articulé · ⚡ Pattern Interrupt · 👁 POV")
            elif _awareness == "hot":
                st.caption("🔥 Les plus efficaces en retargeting : 💬 Preuve sociale · ✨ Transformation · 🎬 Behind-the-scenes")

            # ── Site produit deep scan depuis ici ──
            with st.expander("🌐 Scanner mon site produit (multi-pages + images)", expanded=False):
                dc1, dc2 = st.columns([4, 1])
                with dc1:
                    _deep_url = st.text_input("URL de ton site", placeholder="https://monsite.com", key="deep_scan_url")
                with dc2:
                    st.markdown("<div style='margin-top:28px'>", unsafe_allow_html=True)
                    _deep_btn = st.button("🔍 Scanner", key="deep_scan_btn")
                    st.markdown("</div>", unsafe_allow_html=True)

                if _deep_btn and _deep_url:
                    with st.spinner("Scan multi-pages + analyse des images produit..."):
                        try:
                            from product_context import scrape_website_deep, analyze_product_images
                            _deep_data = scrape_website_deep(_deep_url, max_pages=5)
                            st.info(f"📄 {len(_deep_data.get('pages_scraped', []))} page(s) scrapée(s) · {len(_deep_data.get('images', []))} images trouvées")
                            # Analyse des images
                            if _deep_data.get("images") and _deck_api_key:
                                st.info("📷 Analyse des images produit par Claude Vision...")
                                _vis_insights = analyze_product_images(_deep_data["images"], _deck_api_key)
                                if _vis_insights:
                                    _deep_data["visual_insights"] = _vis_insights
                                    st.success(f"✅ Identité visuelle détectée : {_vis_insights.get('product_type', '')} · {_vis_insights.get('mood', '')}")
                            # Sauvegarder
                            _existing_ctx = load_context()
                            _existing_scraped = [s for s in _existing_ctx.get("scraped", []) if s.get("url") != _deep_url]
                            _existing_scraped.insert(0, _deep_data)
                            _existing_ctx["scraped"] = _existing_scraped
                            save_context(_existing_ctx)
                            _deck_prod_str = format_for_prompt(_existing_ctx)
                            st.success("✅ Contexte enrichi et sauvegardé !")
                            if "agent" in st.session_state:
                                del st.session_state["agent"]
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erreur : {e}")

            st.markdown("---")

            # ── Génération ──
            _gen_btn = st.button(
                f"🎬 Générer le deck ({len(_selected_angles)} angles × 3 = {len(_selected_angles)*3} scripts)",
                type="primary",
                key="generate_deck_btn",
                disabled=not _selected_angles or not transcriptions,
            )
            if not transcriptions:
                st.caption("⚠️ Lance d'abord un scraping pour avoir des références.")

            if _gen_btn and _selected_angles:
                st.markdown("---")
                _deck_container = st.empty()
                _full_deck = ""
                with st.spinner("Génération du deck en cours..."):
                    _output_area = st.empty()
                    _accumulated = ""
                    for _chunk in generate_deck_stream(
                        _selected_angles,
                        _deck_prod_str,
                        transcriptions,
                        _deck_api_key,
                        awareness=_awareness,
                    ):
                        _accumulated += _chunk
                        _output_area.markdown(_accumulated)

                # Sauvegarder le deck
                from datetime import datetime as _dt
                _deck_filename = f"deck_{_dt.now().strftime('%Y%m%d_%H%M')}.txt"
                _deck_path = GENERATED_DIR / _deck_filename
                _deck_path.write_text(_accumulated, encoding="utf-8")

                st.success(f"✅ Deck généré — {len(_selected_angles)*3} scripts sauvegardés")
                st.download_button(
                    "⬇️ Télécharger le deck",
                    data=_accumulated.encode("utf-8"),
                    file_name=_deck_filename,
                    mime="text/plain",
                    key="dl_deck",
                )


# ══════════════════════════════════════════════
# ONGLET CHAT — Conversation avec l'assistant
# ══════════════════════════════════════════════
if _nav == "💬 Chat":
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()

    # ── Contexte disponible pour le chat ────────────────────────────────
    _chat_tops = [r for r in transcriptions if r.get("label") == "Top Performers"]
    _chat_brands = list({r.get("page_name") for r in transcriptions if r.get("page_name")})
    _chat_patterns = st.session_state.get("_intel_patterns", {})
    _chat_ctx_raw = load_context() if AGENT_AVAILABLE else {}
    _chat_prod = format_for_prompt(_chat_ctx_raw) if AGENT_AVAILABLE and _chat_ctx_raw else ""
    _chat_scored = [r for r in transcriptions if (r.get("scoring") or {}).get("score_total")]

    # ── Pastilles de contexte ────────────────────────────────────────────
    _pills_html = ""
    if _chat_tops:
        _pills_html += f'<span class="context-pill green">✅ {len(_chat_tops)} top performers</span>'
    else:
        _pills_html += '<span class="context-pill grey">⚪ Aucune pub scrapée</span>'
    if _chat_brands:
        _pills_html += f'<span class="context-pill">🏢 {len(_chat_brands)} marque{"s" if len(_chat_brands)>1 else ""}</span>'
    if _chat_patterns and "error" not in _chat_patterns:
        _pills_html += '<span class="context-pill">🔬 Patterns analysés</span>'
    if _chat_prod:
        _pills_html += '<span class="context-pill orange">🏷️ Produit importé</span>'
    if _chat_scored:
        avg = round(sum(r["scoring"]["score_total"] for r in _chat_scored) / len(_chat_scored), 1)
        _pills_html += f'<span class="context-pill">⭐ Score moy. {avg}/10</span>'

    st.markdown(f'<div style="margin-bottom:16px">{_pills_html}</div>', unsafe_allow_html=True)

    if not api_key:
        st.warning("⚠️ Entre ta clé Anthropic dans la barre latérale pour activer le chat.")
        st.stop()

    # ── Suggestions rapides ──────────────────────────────────────────────
    if "chat_messages" not in st.session_state or len(st.session_state.chat_messages) == 0:
        st.markdown("**Par où commencer ?**")
        _suggestions = [
            "Quels sont les 3 hooks qui reviennent le plus dans mes top performers ?",
            "Génère-moi un script UGC pour Jacqueline's Lab en audience froide",
            "Quelles marques de ma base fonctionnent le mieux et pourquoi ?",
            "Explique-moi le pattern 'révélation silencieuse' avec un exemple concret",
            "Quel format vidéo dois-je tester en priorité cette semaine ?",
            "Écris-moi un CTA avec FOMO pour l'offre membres -15% à vie",
        ]
        _sug_cols = st.columns(2)
        for i, sug in enumerate(_suggestions):
            if _sug_cols[i % 2].button(sug, key=f"chat_sug_{i}", use_container_width=True):
                st.session_state.setdefault("chat_messages", [])
                st.session_state["chat_messages"].append({"role": "user", "content": sug})
                st.rerun()

        st.markdown("---")

    # ── Historique des messages ──────────────────────────────────────────
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []

    for _msg in st.session_state.chat_messages:
        with st.chat_message(_msg["role"]):
            st.markdown(_msg["content"])

    # ── Bouton reset ─────────────────────────────────────────────────────
    if st.session_state.chat_messages:
        if st.button("🗑 Nouvelle conversation", key="chat_reset"):
            st.session_state.chat_messages = []
            st.rerun()

    # ── Saisie utilisateur ───────────────────────────────────────────────
    _chat_input = st.chat_input("Pose ta question sur tes pubs, tes scripts, tes patterns...")

    if _chat_input:
        st.session_state.chat_messages.append({"role": "user", "content": _chat_input})
        with st.chat_message("user"):
            st.markdown(_chat_input)

        # ── Construire le system prompt avec contexte ─────────────────────
        _sys_parts = [
            "Tu es un expert en creative strategy Meta Ads pour compléments alimentaires pour animaux.",
            "Tu parles TOUJOURS en français. Tes réponses sont précises, actionnables, directes.",
            "",
        ]

        if _chat_tops:
            _sample = _chat_tops[:5]
            _sys_parts.append(f"BASE DE DONNÉES : {len(transcriptions)} pubs scrapées dont {len(_chat_tops)} top performers.")
            _sys_parts.append(f"Marques présentes : {', '.join(_chat_brands[:10])}.")
            _sys_parts.append("")
            _sys_parts.append("EXEMPLES DE TOP PERFORMERS (extrait) :")
            for r in _sample:
                _score_str = f" | Score {r['scoring']['score_total']}/10" if (r.get("scoring") or {}).get("score_total") else ""
                _reach_str = f" | {r['eu_reach']:,} reach EU" if r.get("eu_reach") else ""
                _sys_parts.append(
                    f"[{r.get('page_name','?')} · {r.get('ad_format','ugc')}{_score_str}{_reach_str}]\n"
                    f"{(r.get('transcript','')[:200]).strip()}..."
                )
            _sys_parts.append("")

        if _chat_patterns and "error" not in _chat_patterns:
            _hooks_summary = ", ".join(
                f"{h.get('type','')} ({h.get('frequence_pct',0)}%)"
                for h in _chat_patterns.get("hook_patterns", [])[:4]
            )
            if _hooks_summary:
                _sys_parts.append(f"PATTERNS ANALYSÉS — Hooks : {_hooks_summary}")
            _top_insights = _chat_patterns.get("top_3_insights", [])
            if _top_insights:
                _sys_parts.append("Top insights : " + " | ".join(_top_insights[:3]))
            _sys_parts.append("")

        if _chat_prod:
            _sys_parts.append("PRODUIT CIBLE :")
            _sys_parts.append(_chat_prod[:1200])
            _sys_parts.append("")

        _system_prompt = "\n".join(_sys_parts)

        # ── Streaming de la réponse ────────────────────────────────────────
        with st.chat_message("assistant"):
            _out = st.empty()
            _full_resp = ""
            try:
                import anthropic as _ant_chat
                _client_chat = _ant_chat.Anthropic(api_key=api_key)
                _history = [
                    {"role": m["role"], "content": m["content"]}
                    for m in st.session_state.chat_messages[:-1]
                ]
                _history.append({"role": "user", "content": _chat_input})
                with _client_chat.messages.stream(
                    model="claude-sonnet-4-6",
                    max_tokens=1500,
                    system=_system_prompt,
                    messages=_history,
                ) as _stream:
                    for _chunk in _stream.text_stream:
                        _full_resp += _chunk
                        _out.markdown(_full_resp + "▌")
                _out.markdown(_full_resp)
            except Exception as _e_chat:
                _full_resp = f"⚠️ Erreur : {_e_chat}"
                _out.markdown(_full_resp)

        st.session_state.chat_messages.append({"role": "assistant", "content": _full_resp})
