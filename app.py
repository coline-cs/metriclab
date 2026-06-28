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
    from brands import load_brands, save_brands, add_brand, remove_brand, update_brand_stats
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
    page_title="Meta Ads Intelligence",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
/* ── Base ── */
html, body, [data-testid="stAppViewContainer"] {
    background: #f0f2f5 !important;
    color: #1c1e21 !important;
}
[data-testid="stHeader"] { background: transparent !important; }

/* ── Labels des inputs ── */
label, .stTextInput label, .stTextArea label,
.stSelectbox label, .stSlider label,
div[data-testid="stWidgetLabel"] p,
div[data-testid="stWidgetLabel"] {
    color: #1c1e21 !important;
    font-weight: 600 !important;
    font-size: .92rem !important;
}

/* ── Champs de saisie ── */
input, textarea, .stTextInput input, .stTextArea textarea {
    background: #ffffff !important;
    color: #1c1e21 !important;
    border: 1.5px solid #d0d5dd !important;
    border-radius: 8px !important;
}
input:focus, textarea:focus {
    border-color: #1877f2 !important;
    box-shadow: 0 0 0 3px rgba(24,119,242,.15) !important;
}
input::placeholder, textarea::placeholder { color: #9ca3af !important; }

/* ── Selectbox ── */
.stSelectbox div[data-baseweb="select"] > div {
    background: #ffffff !important;
    color: #1c1e21 !important;
    border: 1.5px solid #d0d5dd !important;
}

/* ── Onglets ── */
.stTabs [data-baseweb="tab-list"] {
    background: #ffffff !important;
    border-radius: 10px !important;
    padding: 4px !important;
    box-shadow: 0 1px 4px rgba(0,0,0,.08) !important;
    gap: 4px !important;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    color: #444 !important;
    border-radius: 7px !important;
    font-weight: 500 !important;
    padding: 8px 16px !important;
}
.stTabs [aria-selected="true"] {
    background: #1877f2 !important;
    color: #ffffff !important;
}

/* ── Navigation principale (segmented control) ── */
div[data-testid="stSegmentedControl"] {
    background: #ffffff;
    border-radius: 12px;
    padding: 4px 6px;
    box-shadow: 0 1px 6px rgba(0,0,0,.09);
    gap: 2px !important;
    overflow-x: auto;
}
div[data-testid="stSegmentedControl"] button,
div[data-testid="stButtonGroup"] button {
    border-radius: 8px !important;
    font-weight: 500 !important;
    font-size: .82rem !important;
    border: none !important;
    color: #5a5f6b !important;
    background: transparent !important;
    transition: all 0.15s ease !important;
    white-space: nowrap !important;
}
div[data-testid="stSegmentedControl"] button:hover,
div[data-testid="stButtonGroup"] button:hover {
    background: #f0f4ff !important;
    color: #1877f2 !important;
}
div[data-testid="stSegmentedControl"] button[aria-checked="true"],
div[data-testid="stButtonGroup"] button[aria-checked="true"],
div[data-testid="stSegmentedControl"] button[kind="segmented_controlActive"],
div[data-testid="stButtonGroup"] button[kind="segmented_controlActive"] {
    background: #1877f2 !important;
    color: #ffffff !important;
    box-shadow: 0 2px 8px rgba(24,119,242,.30) !important;
}

/* ── Download button ── */
.stDownloadButton > button {
    border-radius: 8px !important;
    font-weight: 600 !important;
    background: #f0f4ff !important;
    color: #1877f2 !important;
    border: 1.5px solid #1877f2 !important;
    transition: all 0.15s ease !important;
}
.stDownloadButton > button:hover {
    background: #1877f2 !important;
    color: #fff !important;
    transform: translateY(-1px) !important;
}

/* ── Expander ── */
.streamlit-expanderHeader {
    background: #ffffff !important;
    color: #1c1e21 !important;
    border: 1px solid #e4e6ea !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    transition: background 0.15s ease !important;
}
.streamlit-expanderHeader:hover {
    background: #f7f9fc !important;
}

/* ── Boutons ── */
.stButton > button {
    border-radius: 8px !important;
    font-weight: 600 !important;
    border: none !important;
    transition: all 0.15s ease !important;
    cursor: pointer !important;
}
.stButton > button[kind="primary"] {
    background: #1877f2 !important;
    color: white !important;
    box-shadow: 0 1px 3px rgba(24,119,242,.3) !important;
}
.stButton > button[kind="primary"]:hover {
    background: #0d5fd8 !important;
    box-shadow: 0 4px 14px rgba(24,119,242,.4) !important;
    transform: translateY(-1px) !important;
}
.stButton > button[kind="primary"]:active {
    transform: translateY(0px) !important;
    box-shadow: 0 1px 3px rgba(24,119,242,.3) !important;
}
.stButton > button:not([kind="primary"]) {
    background: #ffffff !important;
    color: #1877f2 !important;
    border: 1.5px solid #1877f2 !important;
}
.stButton > button:not([kind="primary"]):hover {
    background: #eef4ff !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 2px 8px rgba(24,119,242,.15) !important;
}
.stButton > button:disabled {
    opacity: 0.45 !important;
    cursor: not-allowed !important;
    transform: none !important;
    box-shadow: none !important;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: #ffffff !important;
    border-right: 1px solid #e4e6ea !important;
}
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] div {
    color: #1c1e21 !important;
}

/* ── Cards stats ── */
.main-header {
    background: linear-gradient(135deg, #1877f2, #0a58ca);
    color: white; padding: 20px 28px; border-radius: 14px;
    margin-bottom: 20px; display: flex; align-items: center; gap: 16px;
    box-shadow: 0 4px 20px rgba(24,119,242,.25);
}
.main-header h1 { font-size: 1.4rem; margin: 0; color: white !important; }
.main-header p  { margin: 4px 0 0; opacity: .85; font-size: .85rem; color: white !important; }
.stat-card {
    background: white; border-radius: 12px; padding: 16px 20px;
    box-shadow: 0 1px 4px rgba(0,0,0,.07); text-align: center;
    transition: all 0.18s ease; cursor: default;
    border: 1px solid #f0f0f0;
}
.stat-card:hover {
    box-shadow: 0 4px 16px rgba(0,0,0,.10);
    transform: translateY(-2px);
}
.stat-card .n { font-size: 2rem; font-weight: 800; color: #1877f2; line-height: 1; }
.stat-card .l { font-size: .75rem; color: #65676b; margin-top: 4px; }

/* ── Expander ── */
.streamlit-expanderHeader {
    background: #ffffff !important;
    color: #1c1e21 !important;
    border: 1px solid #e4e6ea !important;
    border-radius: 8px !important;
}

/* ── Slider ── */
.stSlider div[data-testid="stTickBarMin"],
.stSlider div[data-testid="stTickBarMax"] { color: #65676b !important; }

/* ── Markdown h3 ── */
h3 { color: #1c1e21 !important; }

/* ── Chat ── */
[data-testid="stChatMessage"] {
    background: #ffffff !important;
    border-radius: 12px !important;
    border: 1px solid #e8eaf0 !important;
    margin-bottom: 10px !important;
    box-shadow: 0 1px 3px rgba(0,0,0,.05) !important;
}
[data-testid="stChatMessage"][data-testid*="user"] {
    background: #eef4ff !important;
}
[data-testid="stChatInput"] textarea {
    background: #ffffff !important;
    color: #1c1e21 !important;
    border: 1.5px solid #d0d5dd !important;
    border-radius: 10px !important;
}
[data-testid="stChatInput"] textarea:focus {
    border-color: #1877f2 !important;
    box-shadow: 0 0 0 3px rgba(24,119,242,.12) !important;
}
.context-pill {
    display: inline-flex; align-items: center; gap: 5px;
    background: #eef4ff; color: #1877f2; border-radius: 20px;
    padding: 4px 12px; font-size: .76rem; font-weight: 600; margin: 3px;
    border: 1px solid #c8d9ff;
}
.context-pill.green { background: #f0fff4; color: #2d7a47; border-color: #b2e8c5; }
.context-pill.orange { background: #fff8e6; color: #7a5a00; border-color: #ffd88a; }
.context-pill.grey { background: #f5f5f5; color: #65676b; border-color: #e0e0e0; }

/* ── Suggestion pill buttons ── */
.suggestion-pill {
    display: inline-block; padding: 7px 14px; margin: 3px;
    background: #ffffff; border: 1.5px solid #d0d5dd;
    border-radius: 20px; font-size: .82rem; color: #1c1e21;
    cursor: pointer; transition: all 0.15s ease;
    user-select: none;
}
.suggestion-pill:hover {
    border-color: #1877f2; color: #1877f2;
    background: #eef4ff;
    transform: translateY(-1px);
}

/* ── Workflow steps ── */
.wf-bar {
    display:flex; align-items:center; gap:0;
    background:white; border-radius:12px;
    padding:12px 20px; margin-bottom:20px;
    box-shadow:0 1px 4px rgba(0,0,0,.08);
}
.wf-step {
    flex:1; text-align:center; padding:8px 6px;
    border-radius:8px; font-size:.82rem; font-weight:500;
    color:#adb5bd; background:transparent; transition:.2s;
}
.wf-step .wf-n {
    display:inline-flex; align-items:center; justify-content:center;
    width:22px; height:22px; border-radius:50%; font-size:.72rem;
    font-weight:700; margin-right:6px;
    background:#e4e6ea; color:#65676b;
}
.wf-step.wf-done { color:#2d7a47; }
.wf-step.wf-done .wf-n { background:#d4edda; color:#155724; }
.wf-step.wf-active { color:#1877f2; font-weight:700; }
.wf-step.wf-active .wf-n { background:#1877f2; color:white; }
.wf-arrow { color:#d0d5dd; font-size:1.2rem; padding:0 4px; }

/* ── Brand row ── */
.brand-row {
    background:white; border-radius:10px; border-left:4px solid #1877f2;
    padding:14px 18px; box-shadow:0 1px 4px rgba(0,0,0,.07);
}
.brand-row-name { font-size:.98rem; font-weight:700; color:#1c1e21; margin-bottom:5px; }
.brand-row-meta { display:flex; gap:14px; font-size:.78rem; color:#65676b; flex-wrap:wrap; }
.brand-row-meta span { display:inline-flex; align-items:center; gap:3px; }

/* ── Empty state ── */
.empty-state-box {
    text-align:center; padding:48px 24px; background:white;
    border-radius:12px; border:2px dashed #d0d5dd; color:#65676b;
    margin-top:8px;
}
.ebox-icon { font-size:2.5rem; margin-bottom:12px; }
.ebox-title { font-size:1.05rem; font-weight:700; color:#1c1e21; margin-bottom:6px; }
.ebox-sub { font-size:.85rem; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="main-header">
  <span style="font-size:2rem">📊</span>
  <div>
    <h1>Meta Ads Intelligence</h1>
    <p>Scrape · Transcrit · Analyse visuellement · Génère du copy expert</p>
  </div>
</div>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────
# SIDEBAR — clé API + options
# ──────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Configuration")
    api_key_input = st.text_input(
        "Clé Anthropic API",
        type="password",
        value=os.environ.get("ANTHROPIC_API_KEY", ""),
        help="Obtiens ta clé sur console.anthropic.com",
    )
    if api_key_input:
        # Nettoyage agressif : espaces, retours ligne, guillemets, caractères invisibles
        _clean_key = "".join(api_key_input.split()).strip('"').strip("'").strip()
        os.environ["ANTHROPIC_API_KEY"] = _clean_key

        if _clean_key.startswith("sk-ant-admin"):
            st.error("❌ C'est une clé ADMIN — elle ne peut pas appeler les modèles. Crée une clé API standard sur console.anthropic.com → API Keys.")
        elif not _clean_key.startswith("sk-ant-"):
            st.warning("⚠️ Format inattendu — une clé Anthropic commence par `sk-ant-api...`")
        else:
            st.success(f"Clé enregistrée ✓ (…{_clean_key[-4:]})")

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
        index=1, label_visibility="collapsed",
        help="Plus grand = plus précis mais plus lent",
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
    st.markdown(f'<div class="stat-card"><div class="n" style="color:#f0ad4e">{tops_count}</div><div class="l">🏆 Top Performers</div></div>', unsafe_allow_html=True)
with col3:
    st.markdown(f'<div class="stat-card"><div class="n" style="color:#17a2b8">{new_count}</div><div class="l">🆕 Nouvelles Créas</div></div>', unsafe_allow_html=True)
with col4:
    st.markdown(f'<div class="stat-card"><div class="n" style="color:#7c3aed">{vision_count}</div><div class="l">📷 Analysés visuel</div></div>', unsafe_allow_html=True)
with col5:
    score_color = "#28a745" if avg_score and avg_score >= 7 else "#f0ad4e" if avg_score else "#adb5bd"
    score_val = str(avg_score) if avg_score else "—"
    st.markdown(f'<div class="stat-card"><div class="n" style="color:{score_color}">{score_val}</div><div class="l">⭐ Score moyen</div></div>', unsafe_allow_html=True)
with col6:
    st.markdown(f'<div class="stat-card"><div class="n" style="color:#28a745">{len(gen_files)}</div><div class="l">✍️ Scripts générés</div></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

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

            with st.expander("Ajouter une marque", expanded=_open_form or len(brands_list) == 0):
                _fa, _fb = st.columns([2, 5])
                _new_name  = _fa.text_input("Nom", placeholder="ex: Bonjour", key="bn")
                _new_url   = _fb.text_input("URL Meta Ads Library", placeholder="https://www.facebook.com/ads/library/?...", key="bu")
                _fc, _fd = st.columns([2, 3])
                _new_label = _fc.selectbox("Label", ["Top Performers", "Nouvelles Créas"], key="bl")
                try:
                    from brands import NICHES
                    _new_niche = _fd.selectbox("Niche", list(NICHES.keys()), key="bniche")
                except Exception:
                    _new_niche = "🐾 Animaux"
                if st.button("✅ Sauvegarder cette marque", type="primary", key="add_brand",
                             disabled=not (_new_name.strip() and _new_url.strip())):
                    add_brand(_new_name, _new_url, _new_label, niche=_new_niche)
                    st.success(f"✅ **{_new_name}** ajoutée !")
                    st.rerun()
                st.caption("💡 Copie l'URL depuis la Bibliothèque publicitaire Meta après avoir recherché la marque.")

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

                for _brand in brands_list:
                    _last  = _brand.get("last_scraped") or "Jamais scrapée"
                    _ads_n = _brand.get("ad_count", 0)
                    _avg   = _brand.get("avg_score")
                    if _avg:
                        _sc_html = f'<span style="color:{"#155724" if _avg>=7 else "#856404"};font-weight:700">⭐ {_avg}/10</span>'
                    else:
                        _sc_html = '<span style="color:#adb5bd">Non scorée</span>'

                    _cinfo, _cbtn = st.columns([5, 2])
                    _cinfo.markdown(f"""
                    <div class="brand-row">
                      <div class="brand-row-name">🏢 {_brand['name']}</div>
                      <div class="brand-row-meta">
                        <span>🏷️ {_brand.get('label','')}</span>
                        <span>📅 {_last}</span>
                        <span>📺 {_ads_n} pub{"s" if _ads_n != 1 else ""}</span>
                        <span>{_sc_html}</span>
                      </div>
                    </div>
                    """, unsafe_allow_html=True)

                    with _cbtn:
                        _b1, _b2 = st.columns([3, 1])
                        if _b1.button("▶ Scraper", key=f"sc_{_brand['id']}",
                                      use_container_width=True, type="primary"):
                            st.session_state["_pending_scrape"] = _brand
                            st.rerun()
                        if _b2.button("✕", key=f"dl_{_brand['id']}",
                                      use_container_width=True, help="Supprimer cette marque"):
                            remove_brand(_brand["id"])
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
        st.components.v1.html(html_content, height=820, scrolling=True)  # noqa: ignore deprecation — st.iframe uses srcdoc (null origin) which breaks window.top navigation
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
        from intelligence import AD_FORMATS, classify_all, analyze_patterns, generate_from_pattern_stream, detect_format
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
