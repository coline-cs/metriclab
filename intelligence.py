#!/usr/bin/env python3
"""
Intelligence compétitive cross-marque.
Détecte les formats vidéo, analyse les patterns structurels gagnants,
génère des templates adaptables au produit cible.
"""

import json
import re
from typing import Generator

# ── Formats vidéo reconnus ────────────────────────────────────────────────────
AD_FORMATS = {
    "ugc": {
        "name": "📱 UGC / Témoignage",
        "description": "Particulier filmé par lui-même, parle à la 1ère personne",
        "color": "#4CAF50",
        "signals": ["j'ai essayé", "ça fait", "depuis que j'utilise", "je te jure",
                    "j'étais", "moi j'avais", "j'ai vu la différence", "en vrai"],
    },
    "founder": {
        "name": "👤 Founder / Créateur",
        "description": "Fondateur ou équipe explique la genèse du produit",
        "color": "#2196F3",
        "signals": ["on a créé", "j'ai créé", "on a développé", "notre formule",
                    "c'est pour ça qu'on a", "on a mis", "on a bossé"],
    },
    "trottoir": {
        "name": "🎤 Interview trottoir",
        "description": "Interview de personnes dans la rue, format micro-trottoir",
        "color": "#FF9800",
        "signals": ["qu'est-ce que vous pensez", "avez-vous entendu parler",
                    "pourriez-vous me dire", "excusez-moi", "on est dans la rue"],
    },
    "explicatif": {
        "name": "🎓 Éducatif / Explicatif",
        "description": "Vulgarisation scientifique, mécanisme produit expliqué",
        "color": "#9C27B0",
        "signals": ["c'est pour ça que", "voici pourquoi", "le problème c'est que",
                    "grâce à", "ce que peu de gens savent", "la science"],
    },
    "ai_video": {
        "name": "🤖 Vidéo IA / Avatar",
        "description": "Vidéo générée ou augmentée par IA, avatar numérique",
        "color": "#00BCD4",
        "signals": [],
    },
    "animated": {
        "name": "🎨 Animation / BD",
        "description": "Dessin animé, style BD, motion design",
        "color": "#E91E63",
        "signals": [],
    },
    "demo": {
        "name": "🧪 Démo produit",
        "description": "Démonstration du produit en action, avant/après visuel",
        "color": "#FF5722",
        "signals": ["regarde", "voilà comment", "il suffit de", "tu vois ici",
                    "avant / après", "comparaison"],
    },
    "talking_head": {
        "name": "🗣 Talking head / Expert",
        "description": "Expert ou prescripteur face caméra, format TV/YouTube",
        "color": "#607D8B",
        "signals": ["en tant que", "selon mes recherches", "les études montrent",
                    "je suis médecin", "je suis nutritionniste", "en tant qu'expert"],
    },
    "pov_dog": {
        "name": "🐾 POV Personnage / Animal",
        "description": "Le produit ou un personnage parle à la 1ère personne",
        "color": "#795548",
        "signals": ["je suis", "mon propriétaire", "je cours", "je saute",
                    "tu peux pas me dire", "je suis ton"],
    },
}


def detect_format(transcript: str, visual_analysis: dict = None) -> str:
    """Détecte le format le plus probable d'une pub."""
    if not transcript:
        return "ugc"

    t = transcript.lower()
    scores = {fmt: 0 for fmt in AD_FORMATS}

    for fmt, data in AD_FORMATS.items():
        for signal in data.get("signals", []):
            if signal.lower() in t:
                scores[fmt] += 1

    # Indices visuels
    if visual_analysis:
        desc = str(visual_analysis).lower()
        if any(w in desc for w in ["animation", "dessin", "cartoon", "bd", "illustr"]):
            scores["animated"] += 3
        if any(w in desc for w in ["avatar", "ia", "généré", "synthétique"]):
            scores["ai_video"] += 3

    best = max(scores, key=scores.get)
    if scores[best] > 0:
        return best

    # Fallback heuristique
    if any(w in t for w in ["j'ai", "j'étais", "depuis que", "moi j'avais"]):
        return "ugc"
    if any(w in t for w in ["on a créé", "c'est pour ça qu'on", "notre produit"]):
        return "founder"
    if any(w in t for w in ["grâce à", "ce que peu de gens", "voici pourquoi"]):
        return "explicatif"
    return "ugc"


def classify_all(transcriptions: list[dict]) -> list[dict]:
    """Ajoute le champ ad_format à toutes les transcriptions qui n'en ont pas."""
    changed = 0
    for r in transcriptions:
        if not r.get("ad_format"):
            r["ad_format"] = detect_format(
                r.get("transcript", ""),
                r.get("visual_analysis"),
            )
            changed += 1
    return transcriptions, changed


# ── Analyse de patterns cross-marque ─────────────────────────────────────────
_PATTERN_PROMPT = """\
Tu es un expert en creative strategy Meta Ads 2026. Analyse ces transcriptions de publicités performantes issues de marques différentes dans le secteur compléments/santé/bien-être animal et humain.

TRANSCRIPTIONS ({n_ads} pubs · {n_brands} marques · {n_formats} formats différents) :
{transcriptions_block}

Ta mission : extraire les PATTERNS STRUCTURELS universels — ce qui est reproductible indépendamment du produit.

Réponds UNIQUEMENT avec du JSON valide (sans markdown) :
{{
  "hook_patterns": [
    {{
      "type": "Nom court du pattern",
      "description": "Comment ça fonctionne",
      "exemple": "Exemple générique adaptable à n'importe quel produit",
      "pourquoi_ca_marche": "Mécanisme psychologique",
      "frequence_pct": 0
    }}
  ],
  "body_structures": [
    {{
      "type": "Nom court",
      "etapes": ["étape 1", "étape 2", "étape 3"],
      "exemple": "Exemple générique",
      "formats_associes": ["ugc", "explicatif"],
      "frequence_pct": 0
    }}
  ],
  "cta_patterns": [
    {{
      "type": "Nom court",
      "description": "Description",
      "exemple": "Exemple générique",
      "frequence_pct": 0
    }}
  ],
  "winning_elements": [
    "Élément 1 — explication courte",
    "Élément 2 — explication courte"
  ],
  "format_insights": {{
    "ugc": "Ce qui marche dans ce format",
    "explicatif": "Ce qui marche dans ce format",
    "founder": "Ce qui marche dans ce format"
  }},
  "top_3_insights": [
    "Insight 1 — actionnable immédiatement",
    "Insight 2",
    "Insight 3"
  ]
}}"""


def analyze_patterns(transcriptions: list[dict], api_key: str, max_ads: int = 25) -> dict:
    """
    Analyse cross-marque des patterns structurels dans les top performers.
    Retourne un dict structuré avec hook patterns, body structures, CTA patterns.
    """
    try:
        import anthropic as _ant
    except ImportError:
        return {"error": "Module anthropic non disponible"}

    tops = [r for r in transcriptions if r.get("label") == "Top Performers"]
    if not tops:
        tops = transcriptions
    selection = tops[:max_ads]

    lines = []
    brands_seen = set()
    formats_seen = set()

    for i, r in enumerate(selection, 1):
        brand = r.get("page_name") or f"Marque {i}"
        brands_seen.add(brand)
        fmt = r.get("ad_format") or detect_format(r.get("transcript", ""), r.get("visual_analysis"))
        formats_seen.add(fmt)
        score = (r.get("scoring") or {}).get("score_total")
        score_str = f" · ⭐{score}/10" if score else ""
        fmt_name = AD_FORMATS.get(fmt, {}).get("name", fmt)
        lines.append(
            f"---\n[{brand} · {fmt_name}{score_str}]\n"
            f"{r.get('transcript', '')[:350].strip()}"
        )

    prompt = _PATTERN_PROMPT.format(
        n_ads=len(selection),
        n_brands=len(brands_seen),
        n_formats=len(formats_seen),
        transcriptions_block="\n".join(lines),
    )

    try:
        client = _ant.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2500,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            return json.loads(m.group())
    except Exception as e:
        return {"error": str(e)}

    return {}


# ── Génération de script depuis un pattern ────────────────────────────────────
_ADAPT_PATTERN_PROMPT = """\
Tu es un expert en creative strategy Meta Ads. Utilise ce pattern structurel identifié dans les meilleures pubs du secteur et génère 2 scripts qui l'appliquent à ce produit spécifique.

PATTERN STRUCTUREL :
Type : {pattern_type}
Description : {pattern_description}
Exemple générique : {pattern_exemple}
Pourquoi ça marche : {pattern_why}

PRODUIT CIBLE :
{product_context}

{awareness_rules}

Génère 2 variantes qui appliquent ce pattern exactement à ce produit.

Format :
---
**VARIANTE 1**
[HOOK 0-3s] : <hook — applique le pattern>
[CORPS 3-30s] : <corps oral naturel>
[CTA] : <CTA>
[DURÉE] : <X secondes>
[FORCE] : <pourquoi ce pattern marche ici>
---
**VARIANTE 2**
[HOOK 0-3s] : <hook différent — même pattern>
[CORPS 3-30s] : <corps différent>
[CTA] : <CTA>
[DURÉE] : <X secondes>
[FORCE] : <pourquoi>
---"""


def generate_from_pattern_stream(
    pattern: dict,
    product_context: str,
    api_key: str,
    awareness: str = "cold",
) -> Generator[str, None, None]:
    """Génère 2 scripts en appliquant un pattern structurel au produit cible."""
    try:
        import anthropic as _ant
    except ImportError:
        yield "❌ Module anthropic non disponible."
        return

    try:
        from script_deck import AWARENESS_LEVELS, _SYSTEM_BASE
    except ImportError:
        yield "❌ Module script_deck non disponible."
        return

    aw = AWARENESS_LEVELS.get(awareness, AWARENESS_LEVELS["cold"])
    system = _SYSTEM_BASE.format(awareness_rules=aw["rules"])

    prompt = _ADAPT_PATTERN_PROMPT.format(
        pattern_type=pattern.get("type", ""),
        pattern_description=pattern.get("description", pattern.get("etapes", "")),
        pattern_exemple=pattern.get("exemple", ""),
        pattern_why=pattern.get("pourquoi_ca_marche", ""),
        product_context=product_context[:1500] if product_context else "Non défini.",
        awareness_rules=aw["rules"],
    )

    try:
        client = _ant.Anthropic(api_key=api_key)
        with client.messages.stream(
            model="claude-sonnet-4-6",
            max_tokens=1800,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            for text in stream.text_stream:
                yield text
    except Exception as e:
        yield f"\n⚠ Erreur : {e}\n"
