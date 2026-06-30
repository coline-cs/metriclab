#!/usr/bin/env python3
"""
Suivi temporel des publicités par marque.
Détecte : nouvelles pubs, pubs supprimées, pubs qui scalent, signaux de croissance.
"""
import json
from datetime import datetime, date
from pathlib import Path

HISTORY_DIR = Path(__file__).parent / "transcriptions" / "history"


def _brand_slug(brand_name: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in brand_name.lower()).strip("_")


def save_snapshot(brand_name: str, ads: list[dict]) -> Path:
    """Sauvegarde un snapshot des pubs d'une marque avec timestamp."""
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    slug = _brand_slug(brand_name)
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = HISTORY_DIR / f"{slug}_{ts}.json"
    snapshot = {
        "brand":     brand_name,
        "scraped_at": datetime.now().isoformat(),
        "ads":       ads,
    }
    path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_history(brand_name: str) -> list[dict]:
    """Charge tous les snapshots d'une marque, triés du plus ancien au plus récent."""
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    slug  = _brand_slug(brand_name)
    files = sorted(HISTORY_DIR.glob(f"{slug}_*.json"))
    snapshots = []
    for f in files:
        try:
            snapshots.append(json.loads(f.read_text(encoding="utf-8")))
        except Exception:
            pass
    return snapshots


def compute_diff(previous: dict, current: list[dict]) -> dict:
    """Compare deux snapshots et détecte les changements.

    Retourne:
      new_ads       : pubs présentes maintenant mais pas avant
      killed_ads    : pubs qui tournaient avant mais ont disparu
      continued_ads : pubs toujours actives (proven performers)
      reach_growth  : variation de reach pour les pubs continues
    """
    prev_ads  = previous.get("ads", []) if previous else []
    prev_ids  = {str(a.get("ad_id") or a.get("position")): a for a in prev_ads if a.get("ad_id") or a.get("position")}
    curr_ids  = {str(a.get("ad_id") or a.get("position")): a for a in current    if a.get("ad_id") or a.get("position")}

    new_ads       = [curr_ids[k] for k in curr_ids if k not in prev_ids]
    killed_ads    = [prev_ids[k] for k in prev_ids if k not in curr_ids]
    continued_ids = [k for k in curr_ids if k in prev_ids]

    continued_ads = []
    for k in continued_ids:
        prev_a = prev_ids[k]
        curr_a = curr_ids[k]
        prev_reach = prev_a.get("eu_reach") or 0
        curr_reach = curr_a.get("eu_reach") or 0
        delta_reach = curr_reach - prev_reach if prev_reach and curr_reach else None

        # Calcul de l'ancienneté totale depuis le premier scraping
        prev_date = previous.get("scraped_at", "")
        days_tracked = 0
        if prev_date:
            try:
                d0 = datetime.fromisoformat(prev_date).date()
                days_tracked = (date.today() - d0).days
            except Exception:
                pass

        continued_ads.append({
            **curr_a,
            "prev_reach":    prev_reach,
            "delta_reach":   delta_reach,
            "delta_reach_pct": round((delta_reach / prev_reach * 100), 1) if prev_reach and delta_reach else None,
            "days_tracked":  days_tracked,
            "signal":        _growth_signal(delta_reach, days_tracked),
        })

    return {
        "new_ads":       new_ads,
        "killed_ads":    killed_ads,
        "continued_ads": continued_ads,
        "summary": {
            "new":       len(new_ads),
            "killed":    len(killed_ads),
            "continued": len(continued_ads),
            "scaling":   sum(1 for a in continued_ads if a.get("signal") == "scaling"),
        }
    }


def _growth_signal(delta_reach: int | None, days_tracked: int) -> str:
    """Classe le signal de croissance d'une pub continue."""
    if delta_reach is None:
        return "unknown"
    if delta_reach > 500_000:
        return "scaling"      # Meta pousse fort cette pub
    if delta_reach > 50_000:
        return "growing"      # croissance régulière
    if delta_reach > 0:
        return "stable"       # toujours active, peu de croissance
    if delta_reach < -10_000:
        return "declining"    # Meta la ralentit
    return "stable"


def get_brand_intelligence(brand_name: str, current_ads: list[dict]) -> dict:
    """Point d'entrée principal : récupère l'historique, calcule le diff, retourne l'intelligence."""
    history = load_history(brand_name)

    if len(history) < 2:
        # Pas assez d'historique — juste sauvegarder et retourner base
        save_snapshot(brand_name, current_ads)
        return {
            "has_history": False,
            "snapshots_count": len(history),
            "message": "Premier scraping — historique initialisé. Re-scrape dans quelques jours pour voir l'évolution.",
        }

    previous = history[-1]  # snapshot le plus récent avant celui-ci
    diff     = compute_diff(previous, current_ads)

    # Sauvegarder le nouveau snapshot
    save_snapshot(brand_name, current_ads)

    # Signaux de croissance globaux
    total_prev_reach = sum(a.get("eu_reach") or 0 for a in previous.get("ads", []))
    total_curr_reach = sum(a.get("eu_reach") or 0 for a in current_ads)
    brand_growth_pct = round((total_curr_reach - total_prev_reach) / max(total_prev_reach, 1) * 100, 1) if total_prev_reach else None

    return {
        "has_history":      True,
        "snapshots_count":  len(history) + 1,
        "previous_date":    previous.get("scraped_at", "")[:10],
        "diff":             diff,
        "brand_growth_pct": brand_growth_pct,
        "brand_signal":     (
            "🚀 En forte croissance" if (brand_growth_pct or 0) > 50
            else "📈 En croissance"  if (brand_growth_pct or 0) > 10
            else "➡️ Stable"         if (brand_growth_pct or 0) >= -10
            else "📉 En recul"
        ),
    }
