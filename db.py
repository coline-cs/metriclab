#!/usr/bin/env python3
"""
Couche d'accès aux données — Supabase avec fallback JSON local.
Si SUPABASE_URL et SUPABASE_KEY sont définis : utilise Supabase.
Sinon : lit/écrit dans transcriptions/*.json (comportement actuel).

Toutes les opérations Supabase sont filtrées par user_id.
"""
import json
import os
from pathlib import Path
from datetime import datetime

BASE_DIR   = Path(__file__).parent
DATA_DIR   = BASE_DIR / "transcriptions"
BRANDS_FILE = DATA_DIR / "brands.json"
TRANS_FILE  = DATA_DIR / "all_transcriptions.json"
SECTIONS_FILE = DATA_DIR / "sections.json"

_supa_client = None


def _get_client():
    global _supa_client
    if _supa_client is not None:
        return _supa_client
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_KEY", "")
    if not url or not key:
        return None
    try:
        from supabase import create_client
        _supa_client = create_client(url, key)
        return _supa_client
    except Exception:
        return None


def _get_authed_client():
    """Client Supabase authentifié avec le JWT de l'utilisateur courant (requis pour RLS)."""
    client = _get_client()
    if not client:
        return None
    try:
        import streamlit as st
        session = st.session_state.get("_auth_session")
        if session and hasattr(session, "access_token") and session.access_token:
            client.postgrest.auth(session.access_token)
        elif session and isinstance(session, dict) and session.get("access_token"):
            client.postgrest.auth(session["access_token"])
    except Exception:
        pass
    return client


def _use_supabase() -> bool:
    return _get_client() is not None


def _uid() -> str | None:
    """Retourne le user_id depuis session_state Streamlit, ou None."""
    try:
        import streamlit as st
        user = st.session_state.get("_auth_user")
        return user["id"] if user else None
    except Exception:
        return None


# ── Marques ──────────────────────────────────────────────────────────────────

def load_brands() -> list[dict]:
    client = _get_authed_client()
    uid = _uid()
    if client and uid:
        try:
            res = client.table("brands").select("*").eq("user_id", uid).order("created_at").execute()
            return res.data or []
        except Exception as e:
            print(f"[db] Supabase brands fallback JSON: {e}")
    if BRANDS_FILE.exists():
        try:
            return json.loads(BRANDS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []


def save_brands(brands: list[dict]):
    client = _get_authed_client()
    if client:
        return  # géré par upsert_brand
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    BRANDS_FILE.write_text(json.dumps(brands, ensure_ascii=False, indent=2), encoding="utf-8")


def upsert_brand(brand: dict) -> dict:
    client = _get_authed_client()
    uid = _uid()
    if client and uid:
        try:
            brand["user_id"] = uid
            res = client.table("brands").upsert(brand).execute()
            return (res.data or [brand])[0]
        except Exception as e:
            print(f"[db] Supabase upsert_brand error: {e}")
    # Fallback JSON
    brands = load_brands()
    brands = [b for b in brands if b.get("id") != brand.get("id")]
    brands.append(brand)
    save_brands(brands)
    return brand


def delete_brand(brand_id: str):
    client = _get_authed_client()
    uid = _uid()
    if client and uid:
        try:
            client.table("brands").delete().eq("id", brand_id).eq("user_id", uid).execute()
            return
        except Exception as e:
            print(f"[db] Supabase delete_brand error: {e}")
    brands = [b for b in load_brands() if b.get("id") != brand_id]
    save_brands(brands)


def update_brand_fields(brand_id: str, fields: dict):
    client = _get_authed_client()
    uid = _uid()
    if client and uid:
        try:
            client.table("brands").update(fields).eq("id", brand_id).eq("user_id", uid).execute()
            return
        except Exception as e:
            print(f"[db] Supabase update_brand error: {e}")
    brands = load_brands()
    for b in brands:
        if b.get("id") == brand_id:
            b.update(fields)
    save_brands(brands)


# ── Sections ─────────────────────────────────────────────────────────────────

def load_sections() -> list[str]:
    client = _get_authed_client()
    uid = _uid()
    if client and uid:
        try:
            res = client.table("sections").select("name").eq("user_id", uid).order("created_at").execute()
            names = [r["name"] for r in (res.data or [])]
            return names if names else ["Top Performers", "Nouvelles Créas"]
        except Exception as e:
            print(f"[db] Supabase sections fallback: {e}")
    if SECTIONS_FILE.exists():
        try:
            return json.loads(SECTIONS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return ["Top Performers", "Nouvelles Créas"]


def save_sections(sections: list[str]):
    client = _get_authed_client()
    uid = _uid()
    if client and uid:
        try:
            client.table("sections").delete().eq("user_id", uid).execute()
            rows = [{"name": s, "user_id": uid, "created_at": datetime.now().isoformat()} for s in sections]
            if rows:
                client.table("sections").insert(rows).execute()
            return
        except Exception as e:
            print(f"[db] Supabase save_sections error: {e}")
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SECTIONS_FILE.write_text(json.dumps(sections, ensure_ascii=False, indent=2), encoding="utf-8")


def add_section(name: str) -> list[str]:
    sections = load_sections()
    if name and name not in sections:
        sections.append(name)
        save_sections(sections)
    return sections


def remove_section(name: str) -> list[str]:
    sections = [s for s in load_sections() if s != name]
    save_sections(sections)
    return sections


# ── Transcriptions ────────────────────────────────────────────────────────────

def load_transcriptions() -> list[dict]:
    client = _get_authed_client()
    uid = _uid()
    if client and uid:
        try:
            res = client.table("transcriptions").select("*").eq("user_id", uid).order("scraped_at", desc=True).execute()
            return res.data or []
        except Exception as e:
            print(f"[db] Supabase transcriptions fallback JSON: {e}")
    if TRANS_FILE.exists():
        try:
            return json.loads(TRANS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []


def save_transcriptions(entries: list[dict]):
    client = _get_authed_client()
    if client:
        try:
            for entry in entries:
                _supa_upsert_transcription(entry)
            return
        except Exception as e:
            print(f"[db] Supabase save_transcriptions error: {e}")
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    TRANS_FILE.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")


def _supa_upsert_transcription(entry: dict):
    client = _get_authed_client()
    uid = _uid()
    if not client or not uid:
        return
    row = {k: (json.dumps(v) if isinstance(v, (dict, list)) else v) for k, v in entry.items()}
    row["user_id"] = uid
    if entry.get("ad_id"):
        client.table("transcriptions").upsert(row, on_conflict="ad_id,user_id").execute()
    else:
        client.table("transcriptions").insert(row).execute()


def append_transcription(entry: dict):
    client = _get_client()
    if client:
        try:
            _supa_upsert_transcription(entry)
            return
        except Exception as e:
            print(f"[db] Supabase append_transcription error: {e}")
    entries = load_transcriptions()
    entries.append(entry)
    save_transcriptions(entries)


# ── Snapshots tracker ─────────────────────────────────────────────────────────

def save_brand_snapshot(brand_name: str, ads: list[dict]):
    client = _get_authed_client()
    uid = _uid()
    if client and uid:
        try:
            client.table("brand_history").insert({
                "brand_name": brand_name,
                "user_id": uid,
                "scraped_at": datetime.now().isoformat(),
                "ads": json.dumps(ads),
            }).execute()
            return
        except Exception as e:
            print(f"[db] Supabase save_brand_snapshot error: {e}")


def load_brand_snapshots(brand_name: str) -> list[dict]:
    client = _get_authed_client()
    uid = _uid()
    if client and uid:
        try:
            res = client.table("brand_history").select("*").eq("brand_name", brand_name).eq("user_id", uid).order("scraped_at").execute()
            snapshots = []
            for row in (res.data or []):
                ads = row.get("ads")
                if isinstance(ads, str):
                    ads = json.loads(ads)
                snapshots.append({"brand": brand_name, "scraped_at": row["scraped_at"], "ads": ads})
            return snapshots
        except Exception as e:
            print(f"[db] Supabase load_brand_snapshots fallback: {e}")
    return []
