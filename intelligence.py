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


# ── Clustering sémantique des hooks ──────────────────────────────────────────

_HOOK_CLUSTER_PROMPT = """\
Tu es expert en psychologie de la persuasion appliquée à la publicité vidéo Meta Ads.

Voici {n} hooks (accroches des 3 premières secondes) issus de pubs dans le secteur compléments/santé/bien-être :

{hooks_block}

Ta mission : regrouper ces hooks par MÉCANISME PSYCHOLOGIQUE sous-jacent — pas par sujet, mais par la mécanique émotionnelle qui pousse à continuer de regarder.

Réponds UNIQUEMENT en JSON valide :
{{
  "clusters": [
    {{
      "mechanism": "nom_technique_court",
      "label": "Nom lisible (ex: Culpabilité du propriétaire)",
      "description": "Comment ce mécanisme fonctionne psychologiquement",
      "why_it_works": "Pourquoi le cerveau répond à ce déclencheur",
      "best_contexts": "Dans quels cas l'utiliser (produit, audience, funnel stage)",
      "hook_ids": [1, 3, 7],
      "strength_avg": 7.5,
      "template": "Template générique réutilisable : [Élément A] → [Élément B]"
    }}
  ],
  "dominant_mechanism": "mécanisme le plus utilisé dans ce dataset",
  "underused_opportunity": "mécanisme peu ou pas utilisé mais qui fonctionnerait bien dans ce secteur",
  "recommendation": "Conseil stratégique en 2 phrases sur ce qu'on devrait tester en priorité"
}}"""


def cluster_hooks(transcriptions: list[dict], api_key: str) -> dict:
    """Regroupe les hooks par mécanisme psychologique sous-jacent.

    Utilise hook_3s si disponible, sinon les 120 premiers caractères du transcript.
    Retourne des clusters avec mécanisme, template réutilisable et recommandation.
    """
    if not api_key:
        return {"error": "Clé API manquante"}

    ads_with_hooks = []
    for r in transcriptions:
        hook = r.get("hook_3s") or r.get("transcript", "")[:120]
        if hook.strip():
            hook_score = (r.get("hook_scoring") or {}).get("stop_scroll_score")
            ads_with_hooks.append({
                "id": r.get("position", len(ads_with_hooks) + 1),
                "hook": hook.strip(),
                "hook_score": hook_score,
                "brand": r.get("page_name") or "?",
                "reach": r.get("eu_reach"),
                "format": r.get("ad_format") or "?",
            })

    if not ads_with_hooks:
        return {"error": "Aucun hook disponible"}

    hooks_block = "\n".join(
        f"[{a['id']}] {a['brand']} · {a['format']}"
        + (f" · score {a['hook_score']}/10" if a['hook_score'] else "")
        + (f" · {a['reach']:,} reach" if a['reach'] else "")
        + f"\n\"{a['hook']}\""
        for a in ads_with_hooks
    )

    try:
        import anthropic as _ant
        client = _ant.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2000,
            messages=[{"role": "user", "content": _HOOK_CLUSTER_PROMPT.format(
                n=len(ads_with_hooks),
                hooks_block=hooks_block,
            )}],
        )
        text = response.content[0].text.strip()
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            result = json.loads(m.group())
            result["_ads_analyzed"] = len(ads_with_hooks)
            return result
    except Exception as e:
        return {"error": str(e)}

    return {}


# ── Générateur de brief vidéo ─────────────────────────────────────────────────

_BRIEF_PROMPT = """\
Tu es creative strategist Meta Ads senior. Génère un brief de production vidéo complet basé sur les patterns gagnants identifiés dans ce dataset.

DONNÉES DISPONIBLES :
- Patterns hooks dominants : {hook_mechanisms}
- Format le plus performant : {top_format}
- Score hook moyen dataset : {avg_hook_score}/10
- Mécanisme hook le plus utilisé : {dominant_mechanism}
- Top performers (reach + longévité) :
{top_ads_block}

PRODUIT CIBLE :
{product_context}

OBJECTIF DU BRIEF : {brief_objective}

Génère un brief vidéo complet en JSON :
{{
  "concept": "<concept créatif en 1 phrase — ce dont parle la vidéo>",
  "hook": {{
    "mechanism": "<mécanisme psychologique>",
    "script": "<script exact du hook 0-3s — 15 mots max>",
    "visual": "<ce qu'on voit à l'écran pendant le hook>",
    "why": "<pourquoi ce hook va stopper le scroll>"
  }},
  "structure": [
    {{
      "section": "Problème (3-8s)",
      "script": "<script>",
      "visual": "<direction visuelle>"
    }},
    {{
      "section": "Agitation (8-15s)",
      "script": "<script>",
      "visual": "<direction visuelle>"
    }},
    {{
      "section": "Solution (15-25s)",
      "script": "<script>",
      "visual": "<direction visuelle>"
    }},
    {{
      "section": "Preuve (25-35s)",
      "script": "<script>",
      "visual": "<direction visuelle>"
    }},
    {{
      "section": "CTA (35-45s)",
      "script": "<script>",
      "visual": "<direction visuelle>"
    }}
  ],
  "format": "<ugc | founder | animated | voiceover | ugc_text>",
  "format_reason": "<pourquoi ce format pour ce concept>",
  "casting": "<profil exact du talent si applicable : âge, genre, énergie, style>",
  "music_mood": "<ambiance musicale recommandée>",
  "text_overlays": ["<3-4 overlays texte clés à afficher à l'écran>"],
  "duration": "<durée cible en secondes>",
  "kpis_target": {{
    "hook_rate_target": "<% de rétention à 3s visé>",
    "estimated_hook_score": <int 0-10>,
    "why_it_will_work": "<analyse en 2 phrases>"
  }}
}}"""


def generate_video_brief(
    transcriptions: list[dict],
    api_key: str,
    product_context: str = "",
    brief_objective: str = "Acquérir de nouveaux clients",
) -> dict:
    """Génère un brief vidéo complet basé sur les patterns gagnants du dataset."""
    if not api_key:
        return {"error": "Clé API manquante"}

    # Extraire les top performers
    tops = sorted(
        [r for r in transcriptions if r.get("eu_reach") or r.get("scoring")],
        key=lambda r: (r.get("eu_reach") or 0),
        reverse=True,
    )[:5]

    # Mécanismes hooks dominants
    mech_counts: dict[str, int] = {}
    hook_scores = []
    for r in transcriptions:
        hs = r.get("hook_scoring") or {}
        if hs.get("mechanism_label"):
            m = hs["mechanism_label"]
            mech_counts[m] = mech_counts.get(m, 0) + 1
        if hs.get("stop_scroll_score"):
            hook_scores.append(hs["stop_scroll_score"])

    dominant_mechanism = max(mech_counts, key=mech_counts.get) if mech_counts else "Non déterminé"
    avg_hook_score = round(sum(hook_scores) / len(hook_scores), 1) if hook_scores else "?"

    # Format le plus performant
    fmt_reach: dict[str, int] = {}
    for r in transcriptions:
        fmt = r.get("ad_format") or "unknown"
        fmt_reach[fmt] = fmt_reach.get(fmt, 0) + (r.get("eu_reach") or 0)
    top_format = max(fmt_reach, key=fmt_reach.get) if fmt_reach else "ugc"

    # Bloc top ads
    top_ads_lines = []
    for r in tops:
        reach = r.get("eu_reach")
        hook = r.get("hook_3s") or r.get("transcript", "")[:80]
        top_ads_lines.append(
            f"• [{r.get('page_name','?')} · {r.get('ad_format','?')}]"
            + (f" {reach:,} reach" if reach else "")
            + f"\n  Hook: \"{hook.strip()[:100]}\""
        )

    try:
        import anthropic as _ant
        client = _ant.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2500,
            messages=[{"role": "user", "content": _BRIEF_PROMPT.format(
                hook_mechanisms=", ".join(f"{m}({c})" for m, c in sorted(mech_counts.items(), key=lambda x: -x[1])[:5]),
                top_format=top_format,
                avg_hook_score=avg_hook_score,
                dominant_mechanism=dominant_mechanism,
                top_ads_block="\n".join(top_ads_lines) or "Aucun top performer disponible",
                product_context=product_context[:500] if product_context else "Non défini",
                brief_objective=brief_objective,
            )}],
        )
        text = response.content[0].text.strip()
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            return json.loads(m.group())
    except Exception as e:
        return {"error": str(e)}

    return {}


# ── Comparaison cross-sections ────────────────────────────────────────────────

def compare_sections(transcriptions: list[dict]) -> dict:
    """Compare les performances entre sections (Top Performers, Nouvelles Créas, etc.).
    Retourne stats par section : reach moyen, score hook moyen, format dominant.
    """
    sections: dict[str, dict] = {}

    for r in transcriptions:
        label = r.get("label") or "Non classé"
        if label not in sections:
            sections[label] = {
                "ads": [], "reaches": [], "hook_scores": [],
                "formats": {}, "mechanisms": {},
            }
        s = sections[label]
        s["ads"].append(r)
        if r.get("eu_reach"):
            s["reaches"].append(r["eu_reach"])
        hs = r.get("hook_scoring") or {}
        if hs.get("stop_scroll_score"):
            s["hook_scores"].append(hs["stop_scroll_score"])
        fmt = r.get("ad_format") or "unknown"
        s["formats"][fmt] = s["formats"].get(fmt, 0) + 1
        mech = hs.get("mechanism_label") or "?"
        if mech != "?":
            s["mechanisms"][mech] = s["mechanisms"].get(mech, 0) + 1

    result = {}
    for label, data in sections.items():
        reaches = data["reaches"]
        hook_scores = data["hook_scores"]
        fmts = data["formats"]
        mechs = data["mechanisms"]
        result[label] = {
            "ad_count":          len(data["ads"]),
            "avg_reach":         int(sum(reaches) / len(reaches)) if reaches else None,
            "max_reach":         max(reaches) if reaches else None,
            "avg_hook_score":    round(sum(hook_scores) / len(hook_scores), 1) if hook_scores else None,
            "top_format":        max(fmts, key=fmts.get) if fmts else None,
            "top_mechanism":     max(mechs, key=mechs.get) if mechs else None,
            "formats_breakdown": fmts,
            "mechanisms_breakdown": mechs,
        }
    return result
