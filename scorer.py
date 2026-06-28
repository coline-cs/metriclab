#!/usr/bin/env python3
"""
Scoring intelligent de publicités vidéo Meta Ads.
Évalue 4 critères : force du hook, clarté éducative, qualité des mots, structure narrative.
Produit deux scores : générique (qualité absolue) + produit (pertinence pour ton objectif).
"""

import json
import re
from pathlib import Path

SCORING_CONTEXT_FILE = Path(__file__).parent / "transcriptions" / "scoring_context.json"

_PROMPT = """\
Tu es un analyste expert en publicité vidéo Meta Ads. Score cette transcription.

TRANSCRIPTION :
{transcript}
{product_block}
Réponds UNIQUEMENT avec du JSON valide, sans markdown ni texte autour :
{{
  "hook_strength": <entier 0-10 — pouvoir STOP-SCROLL des 3 premières secondes. Note sévèrement : 9-10 = impossible de scroller (choc, curiosité irrésistible, interpellation directe du problème vécu) ; 6-8 = intriguant mais zappable ; 0-5 = intro molle, générique ou auto-centrée que tout le monde scrolle>,
  "educational_clarity": <entier 0-10 — le message éduque-t-il clairement sur un problème ou une solution ?>,
  "words_quality": <entier 0-10 — vocabulaire émotionnel, précis, naturel à l'oral, sans jargon creux>,
  "narrative_structure": <entier 0-10 — suit-il problème → solution → preuve → CTA ?>,
  "score_generic": <float 0-10, pondération : hook 40 % + clarté 25 % + mots 15 % + structure 20 % — le hook pèse le plus lourd car sans arrêt du scroll dans les 3 premières secondes, le reste du script n'est jamais vu>,
  "score_product": <float 0-10 si contexte produit fourni sinon null — à quel point ce script est transposable à l'objectif décrit ?>,
  "hook_text": "<10 premiers mots exacts du script>",
  "top_words": ["<3 mots ou expressions clés qui font la force de ce script>"],
  "verdict": "<verdict brutal en 8 mots max>"
}}"""


def load_scoring_context() -> dict:
    if SCORING_CONTEXT_FILE.exists():
        try:
            return json.loads(SCORING_CONTEXT_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"objective": ""}


def save_scoring_context(data: dict):
    SCORING_CONTEXT_FILE.parent.mkdir(parents=True, exist_ok=True)
    SCORING_CONTEXT_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def score_ad(transcript: str, api_key: str, product_context: str = "", objective: str = "") -> dict:
    """
    Score une publicité via Claude Haiku (~$0.001 par pub).
    Retourne un dict avec :
      hook_strength, educational_clarity, words_quality, narrative_structure,
      score_generic, score_product (ou None), score_total, hook_text, top_words, verdict.
    """
    if not transcript.strip() or not api_key:
        return {}

    try:
        import anthropic as _ant
    except ImportError:
        return {}

    product_block = ""
    if objective.strip() or product_context.strip():
        lines = ["\nCONTEXTE PRODUIT / OBJECTIF ÉDUCATIF :"]
        if objective.strip():
            lines.append(f"Objectif : {objective.strip()}")
        if product_context.strip():
            lines.append(product_context.strip()[:500])
        product_block = "\n".join(lines) + "\n"

    prompt = _PROMPT.format(
        transcript=transcript[:1500],
        product_block=product_block,
    )

    try:
        client = _ant.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=450,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if not m:
            return {}
        result = json.loads(m.group())

        sg = result.get("score_generic") or 5.0
        sp = result.get("score_product")
        # score_total : si score_product dispo, pondéré 40 % générique / 60 % produit
        result["score_total"] = round((sg * 0.4 + sp * 0.6) if sp is not None else sg, 1)
        return result

    except Exception as e:
        print(f"    ⚠ Scoring : {e}")
        return {}
