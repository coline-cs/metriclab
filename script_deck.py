#!/usr/bin/env python3
"""
Générateur de deck de scripts multi-angles pour Meta Ads.
7 angles × 3 variantes — basé sur les top performers scrapés + contexte produit.
"""

import re
from typing import Generator

ANGLES = {
    "educational": {
        "name": "🎓 Éducatif",
        "description": "Révèle un problème méconnu que le client ne savait pas avoir",
        "mechanic": "Le script COMMENCE par une information surprenante ou contre-intuitive sur le problème. Le produit n'est mentionné qu'après 10 secondes.",
    },
    "transformation": {
        "name": "✨ Transformation",
        "description": "Avant / après — le voyage de la douleur à la solution",
        "mechanic": "On vit le problème avec le client (frustration, honte, fatigue), puis on montre la vie après la solution. Le produit est le pont.",
    },
    "social_proof": {
        "name": "💬 Preuve sociale",
        "description": "Témoignage authentique à la 1ère personne",
        "mechanic": "Format UGC : 'Depuis que j'utilise X...' ou 'J'aurais aimé que quelqu'un me dise ça plus tôt...'. Concret, chiffré si possible.",
    },
    "problem_articulated": {
        "name": "🎯 Problème articulé",
        "description": "Décrit le problème mieux que le client lui-même",
        "mechanic": "Lister les micro-symptômes que le client ressent mais n'arrive pas à nommer. Quand il se reconnaît, le produit arrive comme une évidence.",
    },
    "behind_scenes": {
        "name": "🎬 Behind-the-scenes",
        "description": "Coulisses authentiques — proof of concept accidentel",
        "mechanic": "Quelqu'un filmé en train d'utiliser le produit sans 'jouer', ou les coulisses de fabrication/formulation. L'authenticité fait tout.",
    },
    "pattern_interrupt": {
        "name": "⚡ Pattern Interrupt",
        "description": "Accroche contre-intuitive ou choc visuel",
        "mechanic": "L'affirmation de départ va à l'encontre de la sagesse populaire : 'Arrête de faire X' / 'Ce que tu crois sur X est faux'. Provocateur mais bienveillant.",
    },
    "pov": {
        "name": "👁 POV / Identification",
        "description": "Le spectateur EST le personnage — immersion totale",
        "mechanic": "Format 'POV : tu découvres enfin pourquoi tu as [symptôme]' ou 'Si tu fais partie de ceux qui...'. Identification immédiate.",
    },
}

AWARENESS_LEVELS = {
    "cold": {
        "name": "🧊 Audience froide — ils ne nous connaissent pas",
        "description": "Ils ne connaissent ni la marque, ni le produit, ni ses bienfaits — parfois même pas leur propre problème.",
        "rules": """\
NIVEAU DE CONSCIENCE DE L'AUDIENCE : FROIDE — règles non négociables :
- Le spectateur ne connaît PAS la marque. Interdiction absolue de commencer par le nom de la marque ou du produit.
- Il ne connaît pas les bienfaits du produit : chaque bénéfice doit être DÉMONTRÉ (mécanisme, cause→effet, preuve concrète), jamais simplement affirmé.
- Il ne sait pas pourquoi il devrait acheter : le script construit le "pourquoi" depuis zéro — problème vécu → coût caché de ce problème → mécanisme de la solution → produit comme conclusion logique.
- Le hook accroche sur le PROBLÈME ou une vérité surprenante, jamais sur l'offre ou la marque.
- Le produit n'apparaît qu'après que le spectateur s'est reconnu dans le problème (pas avant 30-40% du script).
- Vocabulaire du quotidien : les mots que le client utilise pour décrire son problème, pas ceux de la fiche produit.
- Une seule idée par script : une audience froide ne retient qu'un message.""",
    },
    "warm": {
        "name": "🌤 Audience tiède — ils cherchent une solution",
        "description": "Ils connaissent leur problème et comparent des solutions, mais ne connaissent pas la marque.",
        "rules": """\
NIVEAU DE CONSCIENCE DE L'AUDIENCE : TIÈDE — règles :
- Le spectateur connaît son problème et compare des solutions : le script doit DIFFÉRENCIER (pourquoi cette approche et pas les alternatives qu'il a déjà essayées).
- Évoquer ce qu'il a déjà tenté et pourquoi ça n'a pas marché ("si tu as déjà essayé X sans résultat...").
- La marque peut apparaître plus tôt, mais le mécanisme différenciant reste le cœur du script.""",
    },
    "hot": {
        "name": "🔥 Audience chaude — retargeting",
        "description": "Ils connaissent déjà la marque — il faut lever les dernières objections.",
        "rules": """\
NIVEAU DE CONSCIENCE DE L'AUDIENCE : CHAUDE (retargeting) — règles :
- Le spectateur connaît déjà le produit : lever les objections (prix, doute sur l'efficacité, "est-ce pour moi ?").
- Preuve sociale concrète, garantie, urgence honnête.
- Aller droit au but : ne pas réexpliquer le problème.""",
    },
}

_SYSTEM_BASE = """Tu es un directeur créatif expert en publicité vidéo Meta Ads pour l'e-commerce de produits physiques.

Tes règles absolues :
- Les 3 premières secondes font tout — le hook est un hameçon, pas une intro
- Jamais de "Bonjour je m'appelle..."
- Le bénéfice avant le produit, toujours
- Un script UGC se lit à voix haute — tu testes mentalement la fluidité orale
- Zéro jargon creux : "révolutionnaire", "incroyable", "game-changer" sont interdits
- Le CTA est une permission, pas un ordre ("si ça t'intéresse", "t'as qu'à")

{awareness_rules}"""

_VERDICT_PROMPT = """\
Voici un deck de scripts publicitaires générés pour ce produit :

CONTEXTE PRODUIT :
{product_context}

{awareness_rules}

DECK COMPLET :
{deck}

SCORES CALCULÉS — même grille d'évaluation que les vraies pubs scrapées qui performent :
{scores_table}

Ta mission : agis comme un media buyer senior qui doit choisir quoi tourner EN PREMIER avec un budget limité.

1. Classe les 3 MEILLEURS scripts du deck pour cette audience (cite l'angle + le numéro de variante + le hook exact).
2. Appuie ton classement sur les SCORES CALCULÉS ci-dessus ET ton jugement de media buyer. Si tu t'écartes du score, justifie pourquoi.
3. Pour chacun : pourquoi il va marcher sur CETTE audience précise (2-3 phrases max, concret).
4. Désigne LE script à tourner en premier ("🥇 À tourner en premier") et explique en quoi il construit le "pourquoi acheter" pour des gens qui ne connaissent ni la marque ni les bienfaits du produit.
5. Termine par 1 conseil de production concret pour ce script gagnant (casting, lieu, ton).

Sois tranchant. Pas de "tous sont bons". Un classement clair."""


def _parse_variants(angle_text: str) -> list[dict]:
    """Extrait les variantes (hook / corps / cta) d'un bloc d'angle généré."""
    variants = []
    for m in re.finditer(
        r"\*\*VARIANTE\s*([0-9A-Za-z]+)\*\*(.*?)(?=\*\*VARIANTE|\Z)",
        angle_text, re.DOTALL,
    ):
        num, block = m.group(1), m.group(2)

        def _field(name: str) -> str:
            fm = re.search(
                rf"\[{name}[^\]]*\]\s*:?\s*(.+?)(?=\n\[|\n---|\Z)",
                block, re.DOTALL,
            )
            return fm.group(1).strip() if fm else ""

        hook = _field("HOOK")
        corps = _field("CORPS")
        cta = _field("CTA")
        script = "\n".join(p for p in [hook, corps, cta] if p) or block.strip()[:1200]
        variants.append({"num": num, "hook": (hook or script)[:70], "script": script})
    return variants

_ANGLE_PROMPT = """\
CONTEXTE PRODUIT / MARQUE :
{product_context}

TOP PERFORMERS DE RÉFÉRENCE (pour t'inspirer des mécaniques qui fonctionnent) :
{reference_scripts}

ANGLE : {angle_name}
MÉCANIQUE : {mechanic}
DESCRIPTION : {angle_description}

Génère exactement 3 variantes de script pour cet angle appliqué à ce produit.

Pour chaque variante, utilise ce format EXACT :

---
**VARIANTE {n}**
[HOOK 0-3s] : <texte exact du hook — ce qui est dit ou vu dans les 3 premières secondes>
[CORPS 3-30s] : <script complet, oral, naturel — écrit comme on parle>
[CTA] : <call to action naturel>
[DURÉE] : <X secondes>
[FORCE] : <en 1 phrase : pourquoi cette variante marche>
---

Les 3 variantes doivent être distinctes : différents angles d'attaque du même sujet, pas des reformulations."""


def build_reference_scripts(transcriptions: list[dict], max_refs: int = 8) -> str:
    """
    Sélectionne les meilleurs scripts de référence depuis la base.
    Priorité : couverture UE réelle (donnée Meta) > score IA > position.
    """
    tops = [r for r in transcriptions if r.get("label") == "Top Performers"]

    def _rank(r):
        reach = r.get("eu_reach") or 0
        score = (r.get("scoring") or {}).get("score_total") or 0
        return (reach, score)

    selection = sorted(tops, key=_rank, reverse=True)[:max_refs]

    lines = []
    for r in selection:
        tags = []
        if r.get("eu_reach"):
            tags.append(f"couverture UE réelle : {r['eu_reach']:,} personnes".replace(",", " "))
        if r.get("scoring") and r["scoring"].get("score_total"):
            tags.append(f"score {r['scoring']['score_total']}/10")
        tag_str = f" [{' · '.join(tags)}]" if tags else ""
        lines.append(f"#{r.get('position')}{tag_str} : {r.get('transcript', '')[:300].strip()}")
        lines.append("")
    return "\n".join(lines) or "Aucune transcription disponible — génère à partir du contexte produit uniquement."


def generate_deck_stream(
    angles: list[str],
    product_context: str,
    transcriptions: list[dict],
    api_key: str,
    awareness: str = "cold",
) -> Generator[str, None, None]:
    """
    Génère les scripts pour chaque angle sélectionné en streaming,
    puis un verdict final qui classe les meilleurs scripts pour l'audience.
    Yields du texte au fur et à mesure.
    """
    try:
        import anthropic as _ant
    except ImportError:
        yield "❌ Module anthropic non disponible."
        return

    client = _ant.Anthropic(api_key=api_key)
    reference_scripts = build_reference_scripts(transcriptions)
    aw = AWARENESS_LEVELS.get(awareness, AWARENESS_LEVELS["cold"])
    system = _SYSTEM_BASE.format(awareness_rules=aw["rules"])

    yield f"# 📝 Deck de Scripts — {len(angles)} angle(s) × 3 variantes\n\n"
    yield f"*Basé sur {len(transcriptions)} transcriptions scrapées · Audience : {aw['name']}*\n\n---\n\n"

    deck_text = ""        # accumulé pour le verdict final
    angle_outputs = {}    # texte généré par angle, pour le scoring

    for i, angle_key in enumerate(angles, 1):
        angle = ANGLES.get(angle_key)
        if not angle:
            continue

        header = f"## {angle['name']} ({i}/{len(angles)})\n*{angle['description']}*\n\n"
        deck_text += header
        yield header

        prompt = _ANGLE_PROMPT.format(
            product_context=product_context[:2000] if product_context else "Produit non défini — génère des scripts génériques.",
            reference_scripts=reference_scripts,
            angle_name=angle["name"],
            mechanic=angle["mechanic"],
            angle_description=angle["description"],
            n="{n}",  # sera remplacé dans le modèle
        ).replace("{n}", "N")

        angle_text = ""
        try:
            with client.messages.stream(
                model="claude-sonnet-4-6",
                max_tokens=2000,
                system=system,
                messages=[{"role": "user", "content": prompt}],
            ) as stream:
                for text in stream.text_stream:
                    angle_text += text
                    deck_text += text
                    yield text
        except Exception as e:
            yield f"\n⚠ Erreur pour cet angle : {e}\n"

        angle_outputs[angle_key] = angle_text
        yield "\n\n---\n\n"
        deck_text += "\n\n---\n\n"

    # ── Scoring du deck — même grille que les pubs scrapées ──
    scores_table_lines = []
    if deck_text.strip():
        try:
            from scorer import score_ad, load_scoring_context
            _objective = load_scoring_context().get("objective", "")
        except ImportError:
            score_ad = None
            _objective = ""

        if score_ad:
            yield "\n## 📊 Scores des scripts générés\n"
            yield "*Même grille d'évaluation que tes pubs scrapées — les scores sont directement comparables.*\n\n"

            ref_scores = [
                r["scoring"]["score_total"] for r in transcriptions
                if r.get("scoring") and r["scoring"].get("score_total") is not None
            ]
            ref_avg = round(sum(ref_scores) / len(ref_scores), 1) if ref_scores else None
            if ref_avg is not None:
                yield (
                    f"**Référence terrain** : tes pubs scrapées scorent en moyenne "
                    f"**{ref_avg}/10** (max {max(ref_scores)}/10). "
                    f"Un script généré doit viser au moins ce niveau.\n\n"
                )

            _tbl_header = "| Angle | Var. | 🏆 Total | Hook | Clarté | Mots | Structure | Verdict |\n|---|---|---|---|---|---|---|---|"
            scores_table_lines.append(_tbl_header)
            yield _tbl_header + "\n"

            scored_variants = []
            for angle_key, angle_text in angle_outputs.items():
                _ang_name = ANGLES.get(angle_key, {}).get("name", angle_key)
                for v in _parse_variants(angle_text):
                    sc = score_ad(v["script"], api_key, product_context[:500], _objective)
                    total = sc.get("score_total")
                    row = (
                        f"| {_ang_name} | V{v['num']} | **{total if total is not None else '—'}** "
                        f"| {sc.get('hook_strength', '—')} | {sc.get('educational_clarity', '—')} "
                        f"| {sc.get('words_quality', '—')} | {sc.get('narrative_structure', '—')} "
                        f"| {sc.get('verdict', '')} |"
                    )
                    scores_table_lines.append(row)
                    yield row + "\n"
                    if total is not None:
                        scored_variants.append((total, _ang_name, v["num"], v["hook"]))

            if scored_variants:
                scored_variants.sort(reverse=True)
                _best = scored_variants[0]
                _comp = ""
                if ref_avg is not None:
                    _diff = round(_best[0] - ref_avg, 1)
                    _comp = f" — {'+' if _diff >= 0 else ''}{_diff} point(s) vs la moyenne de tes pubs scrapées"
                yield (
                    f"\n**🥇 Meilleur score : {_best[1]} V{_best[2]} à {_best[0]}/10**{_comp}\n"
                    f"> « {_best[3]}... »\n"
                )

    # ── Verdict final : quel script tourner en premier ──
    if deck_text.strip():
        yield "\n## 🏆 Verdict — quoi tourner en premier\n\n"
        verdict_prompt = _VERDICT_PROMPT.format(
            product_context=product_context[:1500] if product_context else "Produit non défini.",
            awareness_rules=aw["rules"],
            deck=deck_text[:25000],
            scores_table="\n".join(scores_table_lines) or "Scores non disponibles — classe selon ton jugement.",
        )
        try:
            with client.messages.stream(
                model="claude-sonnet-4-6",
                max_tokens=1500,
                system="Tu es un media buyer senior, direct et tranchant. Tu réponds en français.",
                messages=[{"role": "user", "content": verdict_prompt}],
            ) as stream:
                for text in stream.text_stream:
                    yield text
        except Exception as e:
            yield f"\n⚠ Erreur verdict : {e}\n"


# ── Prompt pour génération rapide ciblée ──────────────────────────────────────
_QUICK_SCRIPT_PROMPT = """\
BRIEF VIDÉO :
{brief}

CONTEXTE PRODUIT / MARQUE :
{product_context}

TOP PERFORMERS DE RÉFÉRENCE (mécaniques qui fonctionnent sur cette audience) :
{reference_scripts}

Ta mission :
1. Choisis le meilleur angle pour ce brief parmi : Éducatif, Transformation, Preuve sociale, Problème articulé, Behind-the-scenes, Pattern Interrupt, POV.
2. Génère exactement 3 variantes de script pour cet angle, directement inspirées des top performers.

Commence par une ligne : **Angle choisi : [nom] — [raison en 1 phrase max]**

Puis pour chaque variante, utilise ce format EXACT :

---
**VARIANTE N**
[HOOK 0-3s] : <texte exact — ce qui est dit dans les 3 premières secondes>
[CORPS 3-30s] : <script complet, oral, naturel — écrit comme on parle>
[CTA] : <call to action naturel>
[DURÉE] : <X secondes>
[FORCE] : <pourquoi cette variante marche en 1 phrase>
---

Les 3 variantes doivent avoir des hooks distincts — pas des reformulations."""


def generate_quick_script_stream(
    brief: str,
    product_context: str,
    transcriptions: list[dict],
    api_key: str,
    awareness: str = "cold",
) -> Generator[str, None, None]:
    """
    Génère 3 variantes de scripts ciblés sur un brief en 1 seul appel.
    Plus rapide que generate_deck_stream — angle optimal auto-sélectionné + scoring immédiat.
    """
    try:
        import anthropic as _ant
    except ImportError:
        yield "❌ Module anthropic non disponible."
        return

    client = _ant.Anthropic(api_key=api_key)
    reference_scripts = build_reference_scripts(transcriptions)
    aw = AWARENESS_LEVELS.get(awareness, AWARENESS_LEVELS["cold"])
    system = _SYSTEM_BASE.format(awareness_rules=aw["rules"])

    yield f"*Audience : {aw['name']} · {len(transcriptions)} transcriptions de référence*\n\n---\n\n"

    prompt = _QUICK_SCRIPT_PROMPT.format(
        brief=brief[:1000],
        product_context=product_context[:1500] if product_context else "Non défini — génère à partir du brief uniquement.",
        reference_scripts=reference_scripts,
    )

    angle_text = ""
    try:
        with client.messages.stream(
            model="claude-sonnet-4-6",
            max_tokens=2200,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            for text in stream.text_stream:
                angle_text += text
                yield text
    except Exception as e:
        yield f"\n⚠ Erreur génération : {e}\n"
        return

    yield "\n\n---\n\n"

    # ── Scoring automatique — même grille que les pubs scrapées ──
    if not angle_text.strip():
        return

    try:
        from scorer import score_ad, load_scoring_context
        _objective = load_scoring_context().get("objective", "")
    except ImportError:
        return

    yield "## 📊 Scores automatiques\n"
    yield "*Même grille que tes pubs scrapées — directement comparables.*\n\n"

    ref_scores = [
        r["scoring"]["score_total"] for r in transcriptions
        if r.get("scoring") and r["scoring"].get("score_total") is not None
    ]
    ref_avg = round(sum(ref_scores) / len(ref_scores), 1) if ref_scores else None
    if ref_avg is not None:
        yield (
            f"**Référence terrain :** tes pubs scrapées scorent en moyenne "
            f"**{ref_avg}/10** (max {max(ref_scores)}/10)\n\n"
        )

    yield "| Var. | 🏆 Total | 🪝 Hook | 🎓 Clarté | 💬 Mots | 📐 Structure | Verdict |\n"
    yield "|---|---|---|---|---|---|---|\n"

    scored = []
    for v in _parse_variants(angle_text):
        sc = score_ad(v["script"], api_key, product_context[:500], _objective)
        total = sc.get("score_total")
        row = (
            f"| **V{v['num']}** | **{total if total is not None else '—'}** "
            f"| {sc.get('hook_strength', '—')} | {sc.get('educational_clarity', '—')} "
            f"| {sc.get('words_quality', '—')} | {sc.get('narrative_structure', '—')} "
            f"| *{sc.get('verdict', '')}* |"
        )
        yield row + "\n"
        if total is not None:
            scored.append((total, v["num"], v["hook"]))

    if scored:
        scored.sort(reverse=True)
        best = scored[0]
        comp = ""
        if ref_avg is not None:
            diff = round(best[0] - ref_avg, 1)
            comp = f" — {'+' if diff >= 0 else ''}{diff} pt vs tes pubs scrapées"
        yield (
            f"\n**🥇 Meilleur script : V{best[1]} · {best[0]}/10**{comp}\n"
            f"> « {best[2]}... »\n"
        )
