#!/usr/bin/env python3
"""
Gestionnaire de marques — sauvegarde les comptes Meta à scraper.
"""
import json
from datetime import datetime
from pathlib import Path

BRANDS_FILE = Path(__file__).parent / "transcriptions" / "brands.json"


def load_brands() -> list[dict]:
    if BRANDS_FILE.exists():
        try:
            return json.loads(BRANDS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []


def save_brands(brands: list[dict]):
    BRANDS_FILE.parent.mkdir(parents=True, exist_ok=True)
    BRANDS_FILE.write_text(json.dumps(brands, ensure_ascii=False, indent=2), encoding="utf-8")


NICHES = {
    "🐾 Animaux": "Compléments, alimentation, soins pour chiens, chats, animaux",
    "💊 Compléments humain": "Vitamines, probiotiques, adaptogens, suppléments santé",
    "🍵 Boissons santé": "Bonjour, Athletic Greens, matcha, functional drinks",
    "🛒 E-commerce similaire": "Autre marque DTC avec structure pub similaire",
}


def add_brand(name: str, url: str, label: str = "Top Performers", notes: str = "", niche: str = "🐾 Animaux") -> dict:
    brand = {
        "id": f"{name.lower().replace(' ', '_')}_{int(datetime.now().timestamp())}",
        "name": name.strip(),
        "url": url.strip(),
        "label": label.strip() or "Top Performers",
        "notes": notes.strip(),
        "niche": niche,
        "last_scraped": None,
        "ad_count": 0,
        "avg_score": None,
    }
    brands = load_brands()
    brands = [b for b in brands if b.get("url") != url.strip()]  # dédoublonnage
    brands.append(brand)
    save_brands(brands)
    return brand


def update_brand_stats(brand_id: str, ad_count: int, avg_score: float = None):
    brands = load_brands()
    for b in brands:
        if b.get("id") == brand_id:
            b["last_scraped"] = datetime.now().strftime("%d/%m/%Y %H:%M")
            b["ad_count"] = ad_count
            if avg_score is not None:
                b["avg_score"] = round(avg_score, 1)
    save_brands(brands)


def remove_brand(brand_id: str):
    brands = [b for b in load_brands() if b.get("id") != brand_id]
    save_brands(brands)


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
