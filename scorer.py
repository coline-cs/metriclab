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


_HOOK_PROMPT = """\
Tu es expert en creative strategy Meta Ads. Analyse UNIQUEMENT cette accroche (hook) de publicité vidéo — les premières secondes qui décident si le spectateur continue à regarder ou scrolle.

HOOK (0-3 secondes) :
\"\"\"{hook}\"\"\"

Contexte produit (optionnel) : {product_context}

Réponds UNIQUEMENT avec du JSON valide, sans markdown :
{{
  "stop_scroll_score": <entier 0-10 — 10 = impossible de scroller, 0 = on scrolle immédiatement>,
  "mechanism": "<mécanisme psychologique principal parmi : culpabilite_proprio | curiosite_scientifique | douleur_identification | transformation_before_after | autorite_expert | peur_perte | humor_surprise | social_proof | contradiction_choc | question_directe | stat_choc | story_personnelle>",
  "mechanism_label": "<nom lisible du mécanisme en français, ex: Culpabilité du propriétaire>",
  "hook_format": "<structure du hook parmi : question | affirmation_choc | stat | story | identification_probleme | contradiction | interpellation_directe | promesse>",
  "emotional_trigger": "<émotion principale déclenchée : peur | curiosite | culpabilite | espoir | empathie | surprise | honte | fierté>",
  "force_words": ["<2-3 mots ou expressions qui font toute la puissance>"],
  "target_persona": "<qui est visé exactement en 1 phrase>",
  "weakness": "<ce qui pourrait faire scroller quand même, null si parfait>",
  "improved_version": "<version améliorée du hook qui conserve le mécanisme mais maximise le stop-scroll>",
  "benchmark": "<comparaison avec des hooks similaires qu'on voit dans le secteur>"
}}"""


_BODY_PROMPT = """\
Tu es expert en structure narrative de publicités vidéo Meta Ads. Analyse cette transcription complète section par section.

TRANSCRIPTION :
\"\"\"{transcript}\"\"\"

Réponds UNIQUEMENT en JSON valide :
{{
  "hook": {{
    "text": "<texte exact du hook, 0-3s>",
    "score": <0-10>,
    "verdict": "<verdict 5 mots>"
  }},
  "problem": {{
    "text": "<comment le problème est présenté>",
    "score": <0-10 — 10 = douleur viscérale, spécifique, que le viewer ressent immédiatement>,
    "present": <true|false>,
    "verdict": "<verdict 5 mots>"
  }},
  "proof": {{
    "text": "<élément de preuve utilisé : chiffre, témoignage, étude, expert>",
    "score": <0-10 — 10 = preuve béton vérifiable, 0 = aucune preuve>,
    "proof_type": "<testimonial | stat | expert | before_after | demo | none>",
    "present": <true|false>
  }},
  "solution": {{
    "text": "<comment la solution est présentée>",
    "score": <0-10 — 10 = solution claire, mécanisme expliqué, différenciation évidente>,
    "present": <true|false>,
    "verdict": "<verdict 5 mots>"
  }},
  "cta": {{
    "text": "<texte exact du CTA>",
    "score": <0-10 — 10 = urgence + bénéfice immédiat + action claire>,
    "cta_type": "<link_bio | swipe_up | click_here | comment | dm | none>",
    "present": <true|false>
  }},
  "overall_structure_score": <float 0-10 — moyenne pondérée : hook 30% + problème 20% + preuve 20% + solution 20% + cta 10%>,
  "drop_risk": "<où le viewer risque de décrocher : after_hook | after_problem | middle | cta | none>",
  "missing_elements": ["<éléments manquants ou faibles qui pénalisent la conversion>"],
  "structure_verdict": "<verdict global de la structure narrative en 10 mots>"
}}"""


def score_body(transcript: str, api_key: str) -> dict:
    """Analyse la structure narrative complète : hook / problème / preuve / solution / CTA.
    Retourne un score par section + score global structure.
    """
    if not transcript.strip() or not api_key:
        return {}
    try:
        import anthropic as _ant
        client = _ant.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=800,
            messages=[{"role": "user", "content": _BODY_PROMPT.format(transcript=transcript[:2000])}],
        )
        text = response.content[0].text.strip()
        m = re.search(r"\{.*\}", text, re.DOTALL)
        return json.loads(m.group()) if m else {}
    except Exception as e:
        print(f"    ⚠ Body scoring : {e}")
        return {}


def score_hook(hook_3s: str, api_key: str, product_context: str = "") -> dict:
    """Score spécifique du hook (0-3s) — mécanisme psychologique, force, amélioration.
    Appelé en plus du score_ad global pour une analyse fine de l'accroche.
    """
    if not hook_3s.strip() or not api_key:
        return {}
    try:
        import anthropic as _ant
        client = _ant.Anthropic(api_key=api_key)
        prompt = _HOOK_PROMPT.format(
            hook=hook_3s[:300],
            product_context=product_context[:200] if product_context else "non fourni"
        )
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=600,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()
        m = re.search(r"\{.*\}", text, re.DOTALL)
        return json.loads(m.group()) if m else {}
    except Exception as e:
        print(f"    ⚠ Hook scoring : {e}")
        return {}


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
