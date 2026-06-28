#!/usr/bin/env python3
"""Régénère le rapport HTML depuis les transcriptions existantes."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from transcriber import generate_html_report, OUTPUT_DIR


def load_results() -> list[dict]:
    results = []

    # 1. Essayer all_transcriptions.json (peut être ancien ou nouveau format)
    json_path = OUTPUT_DIR / "all_transcriptions.json"
    if json_path.exists():
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
            if isinstance(data, list) and data:
                for i, item in enumerate(data):
                    if "transcript" not in item:
                        continue
                    # Normaliser vers le nouveau format
                    results.append({
                        "label":     item.get("label", "Top Performers"),
                        "position":  item.get("position", item.get("index", i + 1)),
                        "lang":      item.get("lang", "fr"),
                        "transcript": item["transcript"],
                        "url":       item.get("url", ""),
                        "ad_id":     item.get("ad_id"),
                        "page_name": item.get("page_name"),
                        "ad_body":   item.get("ad_body"),
                        "eu_reach":  item.get("eu_reach"),
                        "start_date": item.get("start_date"),
                        "visual_analysis": item.get("visual_analysis", {}),
                        "scoring":   item.get("scoring", {}),
                    })
                if results:
                    print(f"  {len(results)} entrées chargées depuis all_transcriptions.json")
                    return results
        except Exception as e:
            print(f"  Impossible de lire all_transcriptions.json : {e}")

    # 2. Lire les fichiers .txt individuels (nouveau format JSON par fichier)
    txt_files = sorted(OUTPUT_DIR.glob("*.txt"))
    for f in txt_files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            if isinstance(data, dict) and "transcript" in data:
                results.append({
                    "label":     data.get("label", "Top Performers"),
                    "position":  data.get("position", 0),
                    "lang":      data.get("lang", "fr"),
                    "transcript": data["transcript"],
                    "url":       data.get("url", ""),
                    "ad_id":     data.get("ad_id"),
                    "page_name": data.get("page_name"),
                    "ad_body":   data.get("ad_body"),
                })
        except Exception:
            # 3. Ancien format texte brut :
            #    URL source:\nhttps://...\n\nTRANSCRIPTION:\ntexte...
            try:
                text = f.read_text(encoding="utf-8")
                parts = text.split("\n\nTRANSCRIPTION:\n", 1)
                transcript = parts[1].strip() if len(parts) == 2 else text.strip()
                url_line = parts[0].replace("URL source:\n", "").strip() if parts else ""
                # Deviner le label depuis le nom du fichier
                name = f.stem  # ex: top_performers_01 ou nouvelles_créas_01
                if "nouvelle" in name.lower():
                    label = "Nouvelles Créas"
                else:
                    label = "Top Performers"
                results.append({
                    "label":     label,
                    "position":  len(results) + 1,
                    "lang":      "fr",
                    "transcript": transcript,
                    "url":       url_line,
                    "ad_id":     None,
                    "page_name": None,
                    "ad_body":   None,
                })
            except Exception:
                pass

    return results


def main():
    results = load_results()
    if not results:
        print(f"Aucune transcription trouvée dans {OUTPUT_DIR}/")
        sys.exit(1)

    html_path = OUTPUT_DIR / "rapport.html"
    generate_html_report(results, html_path)
    print(f"✓ Rapport régénéré avec {len(results)} transcriptions.")
    print(f'  → open "{html_path}"')


if __name__ == "__main__":
    main()
