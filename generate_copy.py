#!/usr/bin/env python3
"""
Générateur de copy Meta Ads — propulsé par Claude
Analyse les top performers et génère des scripts pour ta marque.

Usage:
  python generate_copy.py
  python generate_copy.py --brand "MaBrand" --product "Mon produit" --benefits "B1,B2" --tone "direct"
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

try:
    import anthropic
except ImportError:
    print("❌ Package manquant. Lance : pip install anthropic")
    sys.exit(1)

OUTPUT_DIR = Path("transcriptions")
GENERATED_DIR = Path("generated_copy")
MODEL = "claude-sonnet-4-6"
TOP_N = 15   # Nombre de top performers envoyés à Claude comme exemples


# ──────────────────────────────────────────────────────────────
# CHARGEMENT DES TRANSCRIPTIONS
# ──────────────────────────────────────────────────────────────

def load_transcriptions() -> tuple[list[dict], list[dict]]:
    """Retourne (top_performers, nouvelles_creas) depuis le JSON."""
    json_path = OUTPUT_DIR / "all_transcriptions.json"
    if not json_path.exists():
        print(f"❌ Fichier introuvable : {json_path}")
        print("   Lance d'abord : python transcriber.py --url ... --label ...")
        sys.exit(1)

    data = json.loads(json_path.read_text(encoding="utf-8"))

    tops = [r for r in data if r.get("label") == "Top Performers"]
    news = [r for r in data if r.get("label") == "Nouvelles Créas"]

    # Trier par position (position 1 = meilleur)
    tops.sort(key=lambda r: r.get("position", 999))
    news.sort(key=lambda r: r.get("position", 999))

    return tops, news


# ──────────────────────────────────────────────────────────────
# ANALYSE DE PATTERNS
# ──────────────────────────────────────────────────────────────

def extract_word_patterns(transcripts: list[dict], n=30) -> str:
    """Extrait les mots les plus fréquents pour donner du contexte à Claude."""
    from collections import Counter
    stopwords = {
        "le","la","les","de","du","des","un","une","et","en","à","au","aux",
        "est","son","sa","ses","ce","qui","que","quand","dans","sur","par",
        "je","tu","il","elle","nous","vous","ils","elles","me","te","se",
        "mon","ma","mes","ton","ta","tes","si","mais","ou","donc","or","ni","car",
        "plus","pas","ne","très","bien","tout","tous","toute","c'est","j'ai",
        "ça","avec","pour","cette","cela","dont","même","aussi","comme","fait",
    }
    words = []
    for r in transcripts:
        tokens = re.findall(r"\b[a-záàâäéèêëîïôöùûüç]{4,}\b", r["transcript"].lower())
        words.extend(t for t in tokens if t not in stopwords)
    top = Counter(words).most_common(n)
    return ", ".join(f"{w} ({c}x)" for w, c in top)


# ──────────────────────────────────────────────────────────────
# PROMPT CLAUDE
# ──────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """Tu es un expert en création de contenus publicitaires vidéo pour Meta (Facebook/Instagram).
Tu analyses des scripts d'annonces qui ont généré un maximum d'impressions et tu en extrais les formules gagnantes
pour créer de nouveaux scripts sur mesure.

Tes scripts doivent être :
- Naturels, parlés (pas trop écrits)
- Adaptés au format vidéo courte (15-60 secondes)
- Calibrés pour la niches analysée
- Directs, émotionnels, avec un hook fort dès les premières secondes
"""

def build_prompt(
    brand: str,
    product: str,
    benefits: str,
    tone: str,
    top_transcripts: list[dict],
    keywords: str,
    nb_scripts: int = 3,
) -> str:
    examples = ""
    for i, t in enumerate(top_transcripts[:TOP_N], 1):
        pos = t.get("position", i)
        page = f" — {t['page_name']}" if t.get("page_name") else ""
        examples += f"\n\n### Script Top Performer #{pos}{page}\n{t['transcript'].strip()}"

    return f"""## CONTEXTE — Scripts qui performent le mieux dans cette niche

Voici les {min(TOP_N, len(top_transcripts))} meilleurs scripts Meta Ads classés par nombre d'impressions décroissant.
Ces scripts ont prouvé leur efficacité auprès d'une large audience.

{examples}

---

## MOTS-CLÉS LES PLUS FRÉQUENTS dans ces top performers
{keywords}

---

## TA MISSION

Analyse profondément ces scripts et identifie :
1. **Les hooks** : comment ils accrochent dès la 1ère seconde
2. **La structure narrative** : comment l'histoire est construite
3. **Les déclencheurs émotionnels** : peur, espoir, curiosité, urgence…
4. **Le vocabulaire de la niche** : termes spécifiques qui résonnent
5. **Les CTAs** : comment ils poussent à l'action

Puis génère **{nb_scripts} scripts originaux** pour la marque suivante,
EN T'INSPIRANT des formules gagnantes sans les copier mot pour mot :

- **Marque** : {brand}
- **Produit / offre** : {product}
- **Bénéfices clés** : {benefits}
- **Ton souhaité** : {tone}

### FORMAT DE RÉPONSE ATTENDU

Pour chaque script :

---
**SCRIPT [N] — [Titre court décrivant l'angle]**

*Hook (0-3 sec)* : [les premières paroles]

[Script complet, tel qu'il serait dit à l'oral]

*Durée estimée* : ~XX secondes
*Angle* : [explication courte de la stratégie utilisée]

---

Après les {nb_scripts} scripts, ajoute une section :

## ANALYSE DES PATTERNS DÉTECTÉS
(3-5 bullet points sur ce qui fait marcher ces ads dans cette niche)
"""


# ──────────────────────────────────────────────────────────────
# GÉNÉRATION
# ──────────────────────────────────────────────────────────────

def generate(
    brand: str,
    product: str,
    benefits: str,
    tone: str,
    nb_scripts: int = 3,
) -> str:
    api_key = (os.environ.get("ANTHROPIC_API_KEY") or "").strip()
    if not api_key:
        print("\n❌ Clé API manquante.")
        print("   Définis-la avec : export ANTHROPIC_API_KEY=sk-ant-...")
        sys.exit(1)

    tops, _ = load_transcriptions()
    if not tops:
        print("❌ Aucun Top Performer trouvé dans all_transcriptions.json")
        sys.exit(1)

    print(f"  {len(tops)} Top Performers chargés (utilisation des {min(TOP_N, len(tops))} premiers)")

    keywords = extract_word_patterns(tops)
    prompt = build_prompt(brand, product, benefits, tone, tops, keywords, nb_scripts)

    print(f"  Appel à Claude ({MODEL})...")
    client = anthropic.Anthropic(api_key=api_key)

    response = client.messages.create(
        model=MODEL,
        max_tokens=4000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    return response.content[0].text


# ──────────────────────────────────────────────────────────────
# INTERFACE CLI INTERACTIVE
# ──────────────────────────────────────────────────────────────

def ask(question: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    answer = input(f"  {question}{suffix} : ").strip()
    return answer or default


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--brand",    help="Nom de ta marque")
    parser.add_argument("--product",  help="Description du produit")
    parser.add_argument("--benefits", help="Bénéfices clés (séparés par des virgules)")
    parser.add_argument("--tone",     help="Ton souhaité (ex: direct, bienveillant, scientifique)")
    parser.add_argument("--n",        type=int, default=3, help="Nombre de scripts à générer (défaut: 3)")
    args = parser.parse_args()

    print("\n╔══════════════════════════════════════════════════╗")
    print("║   Générateur de Copy Meta Ads — Claude AI       ║")
    print("╚══════════════════════════════════════════════════╝\n")

    # Infos marque (interactif si non passé en args)
    brand    = args.brand    or ask("Nom de ta marque")
    product  = args.product  or ask("Décris ton produit / offre en une phrase")
    benefits = args.benefits or ask("Bénéfices clés (ex: réduit les ballonnements, 100% naturel, livré en 48h)")
    tone     = args.tone     or ask("Ton souhaité", default="direct et authentique")
    nb       = args.n

    print(f"\n[1/3] Chargement des transcriptions...")
    print(f"[2/3] Génération de {nb} scripts pour « {brand} »...")

    result = generate(brand, product, benefits, tone, nb)

    # Afficher
    print("\n" + "═" * 60)
    print(result)
    print("═" * 60)

    # Sauvegarder
    GENERATED_DIR.mkdir(exist_ok=True)
    safe_brand = re.sub(r"[^\w\-]", "_", brand.lower())
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    output_path = GENERATED_DIR / f"{safe_brand}_{timestamp}.txt"
    output_path.write_text(
        f"Marque : {brand}\nProduit : {product}\nBénéfices : {benefits}\nTon : {tone}\n\n{result}",
        encoding="utf-8",
    )

    print(f"\n[3/3] ✓ Scripts sauvegardés dans : {output_path}")


if __name__ == "__main__":
    main()
