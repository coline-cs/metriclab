#!/usr/bin/env python3
"""
Gestionnaire de marques — sauvegarde les comptes Meta à scraper.
Toutes les opérations passent par db.py (Supabase ou JSON fallback).
"""
import json
from datetime import datetime
from pathlib import Path

import db as _db

BRANDS_FILE = Path(__file__).parent / "transcriptions" / "brands.json"


def load_brands() -> list[dict]:
    return _db.load_brands()


def save_brands(brands: list[dict]):
    _db.save_brands(brands)


NICHES = {
    "🐾 Animaux": "Compléments, alimentation, soins pour chiens, chats, animaux",
    "💊 Compléments humain": "Vitamines, probiotiques, adaptogens, suppléments santé",
    "🍵 Boissons santé": "Bonjour, Athletic Greens, matcha, functional drinks",
    "🛒 E-commerce similaire": "Autre marque DTC avec structure pub similaire",
}

SECTIONS_FILE = Path(__file__).parent / "transcriptions" / "sections.json"

DEFAULT_SECTIONS = ["Top Performers", "Nouvelles Créas"]


def load_sections() -> list[str]:
    return _db.load_sections()


def save_sections(sections: list[str]):
    _db.save_sections(sections)


def add_section(name: str) -> list[str]:
    return _db.add_section(name)


def remove_section(name: str) -> list[str]:
    return _db.remove_section(name)


def add_brand(name: str, url: str, label: str = "Top Performers", notes: str = "", niche: str = "🐾 Animaux") -> dict:
    brand = {
        "id": f"{name.lower().replace(' ', '_')}_{int(datetime.now().timestamp())}",
        "name": name.strip(),
        "url": url.strip(),
        "label": label.strip() or "Top Performers",
        "notes": notes.strip(),
        "niche": niche,
        "tags": [label.strip()] if label.strip() else [],
        "last_scraped": None,
        "ad_count": 0,
        "avg_score": None,
        "created_at": datetime.now().isoformat(),
    }
    # dédoublonnage par URL
    existing = load_brands()
    existing = [b for b in existing if b.get("url") != url.strip()]
    existing.append(brand)
    save_brands(existing)
    _db.upsert_brand(brand)
    return brand


def update_brand_stats(brand_id: str, ad_count: int, avg_score: float = None):
    fields = {
        "last_scraped": datetime.now().isoformat(),
        "ad_count": ad_count,
    }
    if avg_score is not None:
        fields["avg_score"] = round(avg_score, 1)
    _db.update_brand_fields(brand_id, fields)


def remove_brand(brand_id: str):
    _db.delete_brand(brand_id)


def get_brand_live_stats(brand: dict, transcriptions: list[dict]) -> dict:
    """Calcule les stats réelles depuis la base de transcriptions."""
    name_lower = brand["name"].lower()
    matching = [
        r for r in transcriptions
        if (r.get("page_name") or "").lower().find(name_lower) >= 0
        or brand["label"] == r.get("label")
    ]
    # Fallback : chercher par label
    by_label = [r for r in transcriptions if r.get("label") == brand["label"]]

    scored = [r for r in by_label if r.get("scoring") and r["scoring"].get("score_total") is not None]
    avg = round(sum(r["scoring"]["score_total"] for r in scored) / len(scored), 1) if scored else None
    return {
        "ad_count": brand.get("ad_count", 0),
        "scored_count": len(scored),
        "avg_score": avg,
        "last_scraped": brand.get("last_scraped"),
    }
