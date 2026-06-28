#!/usr/bin/env python3
"""
Agent expert en scripts vidéo Meta Ads.
Alimenté par les transcriptions + analyses visuelles + contexte produit.
"""

import json
import os
from pathlib import Path
from typing import Generator

import anthropic

TRANSCRIPTIONS_FILE = Path(__file__).parent / "transcriptions" / "all_transcriptions.json"

EXPERT_SYSTEM_BASE = """Tu es un directeur créatif expert en publicité vidéo Meta Ads (Facebook/Instagram) pour l'e-commerce de produits physiques.

Tu maîtrises tous les formats : UGC authentique, VSL courte (15-60s), storytelling (60-180s), pattern interrupts tendance TikTok/Reels.

## Tes règles absolues
- Les 3 premières secondes font tout — le hook est un hameçon, pas une introduction
- Jamais de "Bonjour je m'appelle..." — on entre dans le vif immédiatement
- Le bénéfice avant le produit, toujours
- Un script UGC se lit à voix haute — tu testes mentalement la fluidité orale
- Le CTA est une permission, pas un ordre ("si ça t'intéresse", "t'as qu'à")
- Zéro jargon publicitaire creux : "révolutionnaire", "incroyable", "game-changer" sont interdits

## Ce que tu produis

**Demande de hooks** → toujours 6 à 10 variantes, classées par mécanique :
- Choc / pattern interrupt visuel
- Question rhétorique douloureuse
- Affirmation contre-intuitive
- Stat ou preuve sociale chiffrée
- "POV / Si tu..." / identification directe
- Problème articulé mieux que le client lui-même
- "Behind the scenes / proof of concept accidentel"

**Demande d'analyse de script** → structure ta réponse en 3 blocs :
1. Score /10 + une phrase de verdict
2. Le vrai problème identifié (pas juste "le hook est faible" — dis POURQUOI et COMMENT)
3. Réécriture ciblée uniquement de ce qui cloche

**Demande de script complet** → format :
- [FORMAT] : UGC / VSL / Storytelling / Pattern Interrupt
- [HOOK 0-3s] : texte exact
- [CORPS] : script complet oral
- [CTA] : call to action
- [DURÉE ESTIMÉE] : X secondes
- [MÉCANIQUE] : explication de la stratégie

**Demande de patterns** → analyse transversale des données, bullet points actionnables, pas de généralités.

Tu t'appuies sur les données réelles (transcriptions + visuels) disponibles dans ton contexte. Quand tu génères quelque chose, ancre-le dans des exemples de la base."""


def load_transcriptions() -> list[dict]:
    if not TRANSCRIPTIONS_FILE.exists():
        return []
    try:
        return json.loads(TRANSCRIPTIONS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def build_transcription_context(transcriptions: list[dict]) -> str:
    if not transcriptions:
        return ""

    tops = sorted(
        [r for r in transcriptions if r.get("label") == "Top Performers"],
        key=lambda r: r.get("position", 999),
    )
    news = sorted(
        [r for r in transcriptions if r.get("label") != "Top Performers"],
        key=lambda r: r.get("position", 999),
    )

    parts = [f"## Base de données : {len(transcriptions)} publicités analysées\n"]

    if tops:
        parts.append(f"### TOP PERFORMERS ({len(tops)} ads — classés par impressions décroissantes)\n")
        for r in tops[:18]:
            line = f"**#{r.get('position')}**"
            if r.get("page_name"):
                line += f" [{r['page_name']}]"
            line += f" ({r.get('lang', '?')})"
            parts.append(line)
            parts.append(f"> {r['transcript'][:400].strip()}")

            va = r.get("visual_analysis") or {}
            if isinstance(va, dict) and va:
                visual_parts = []
                if va.get("scene_type"):
                    visual_parts.append(f"Format: {va['scene_type']}")
                if va.get("hook_visual"):
                    visual_parts.append(f"Visuel hook: {va['hook_visual']}")
                if va.get("text_overlays"):
                    overlays = [t for t in (va["text_overlays"] or []) if t][:3]
                    if overlays:
                        visual_parts.append(f"Textes écran: {' / '.join(overlays)}")
                if va.get("visual_style"):
                    visual_parts.append(f"Style: {va['visual_style']}")
                if va.get("setting"):
                    visual_parts.append(f"Lieu: {va['setting']}")
                if visual_parts:
                    parts.append(f"  📷 {' | '.join(visual_parts)}")
            parts.append("")

    if news:
        parts.append(f"\n### NOUVELLES CRÉAS ({len(news)} ads)\n")
        for r in news[:8]:
            parts.append(f"**#{r.get('position')}** ({r.get('lang', '?')}) > {r['transcript'][:250].strip()}\n")

    return "\n".join(parts)


class ScriptExpertAgent:
    def __init__(self, api_key: str, product_context_str: str = ""):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.history: list[dict] = []
        self.product_context_str = product_context_str
        self._refresh_context()

    def _refresh_context(self):
        self._transcription_context = build_transcription_context(load_transcriptions())

    def _build_system(self) -> str:
        system = EXPERT_SYSTEM_BASE
        if self._transcription_context:
            system += f"\n\n---\n\n{self._transcription_context}"
        if self.product_context_str.strip():
            system += f"\n\n---\n\n## CONTEXTE PRODUIT / MARQUE\n\n{self.product_context_str}"
        return system

    def reload(self, product_context_str: str = ""):
        self.product_context_str = product_context_str
        self._refresh_context()

    def reset_history(self):
        self.history = []

    def chat_stream(self, user_message: str) -> Generator[str, None, None]:
        self.history.append({"role": "user", "content": user_message})

        full_response = ""
        with self.client.messages.stream(
            model="claude-sonnet-4-6",
            max_tokens=2500,
            system=self._build_system(),
            messages=self.history,
        ) as stream:
            for text in stream.text_stream:
                full_response += text
                yield text

        self.history.append({"role": "assistant", "content": full_response})
