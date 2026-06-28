#!/usr/bin/env python3
"""
Meta Ads Library - Outil de transcription vidéo + analyse visuelle
Usage:
  python transcriber.py --url "URL" --label "Top Performers"
  python transcriber.py --url "URL1" --label "Top Performers" --url "URL2" --label "Nouvelles Créas"
"""

import argparse
import asyncio
import base64
import json
import os
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

import requests
import whisper
from playwright.async_api import async_playwright

OUTPUT_DIR = Path("transcriptions")
SCROLL_COUNT = 5
SCROLL_PAUSE = 2.5
WHISPER_MODEL = "base"

LANG_FLAG = {
    "fr": "🇫🇷", "en": "🇬🇧", "es": "🇪🇸", "de": "🇩🇪",
    "it": "🇮🇹", "pt": "🇵🇹", "nl": "🇳🇱", "ar": "🇸🇦",
}


# ──────────────────────────────────────────────────────────────
# 1. SCRAPING
# ──────────────────────────────────────────────────────────────

JS_EXTRACT_ADS = """
() => {
    const ads = [];
    const cards = document.querySelectorAll('[data-testid="ad-archive-item"], [class*="x1dr75xp"]');
    cards.forEach(card => {
        const idMatch = card.innerText.match(/ID[^:]*:\\s*(\\d{10,})/);
        const pageEl = card.querySelector('[class*="x1i10hfl"] span, a[href*="facebook.com"]');
        const bodyEl = card.querySelectorAll('div[class*="x1iorvi4"], div[class*="_7jyg"]');
        ads.push({
            ad_id: idMatch ? idMatch[1] : null,
            page_name: pageEl ? pageEl.innerText.trim().split('\\n')[0] : null,
            body: bodyEl.length ? bodyEl[0].innerText.trim().substring(0, 200) : null,
        });
    });
    if (ads.filter(a => a.ad_id).length === 0) {
        const allText = document.body.innerText;
        const ids = [...allText.matchAll(/ID[^\\n]*?:\\s*(\\d{10,})/g)].map(m => m[1]);
        ids.forEach(id => ads.push({ ad_id: id, page_name: null, body: null }));
    }
    return ads;
}
"""

JS_EXTRACT_VIDEOS_FROM_DOM = """
() => {
    const sources = [];
    document.querySelectorAll('video').forEach(v => {
        if (v.src) sources.push(v.src);
        v.querySelectorAll('source').forEach(s => { if (s.src) sources.push(s.src); });
    });
    return sources;
}
"""


async def scrape_video_urls(ads_library_url: str, label: str) -> list[dict]:
    video_items: list[dict] = []
    seen_urls: set[str] = set()

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = await browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
            locale="fr-FR",
        )
        page = await context.new_page()

        ad_data_map: dict[str, dict] = {}

        async def on_response(response):
            url = response.url
            if "ads/library/async" in url or ("graphql" in url and "AdsQuery" in url):
                try:
                    text = await response.text()
                    clean = text.lstrip("for (;;);").strip()
                    data = json.loads(clean)
                    _parse_api_response(data, ad_data_map)
                except Exception:
                    pass
            if (
                ".mp4" in url
                or ("fbcdn.net" in url and "video" in url.lower())
                or ("cdninstagram.com" in url and ".mp4" in url)
            ):
                if url not in seen_urls:
                    seen_urls.add(url)
                    position = len(video_items) + 1
                    extra = ad_data_map.get(url, {})
                    video_items.append({
                        "url": url,
                        "position": position,
                        "label": label,
                        "ad_id": extra.get("ad_id"),
                        "page_name": extra.get("page_name"),
                        "ad_body": extra.get("body"),
                        "eu_reach": extra.get("eu_reach"),
                        "start_date": extra.get("start_date"),
                    })
                    print(f"  [vidéo #{position}] {url[:80]}...")

        page.on("response", on_response)

        print(f"\n→ [{label}] Chargement...")
        try:
            await page.goto(ads_library_url, wait_until="domcontentloaded", timeout=60_000)
        except Exception as e:
            print(f"  Avertissement : {e}")

        await asyncio.sleep(3)

        print(f"  Scrolling ({SCROLL_COUNT} fois)...")
        for i in range(SCROLL_COUNT):
            await page.evaluate("window.scrollBy(0, window.innerHeight * 1.5)")
            await asyncio.sleep(SCROLL_PAUSE)

        dom_sources = await page.evaluate(JS_EXTRACT_VIDEOS_FROM_DOM)
        for src in dom_sources:
            if src and src not in seen_urls:
                seen_urls.add(src)
                video_items.append({
                    "url": src, "position": len(video_items) + 1,
                    "label": label, "ad_id": None, "page_name": None, "ad_body": None,
                })

        ad_cards = await page.evaluate(JS_EXTRACT_ADS)
        no_id_items = [v for v in video_items if v["ad_id"] is None]
        for i, item in enumerate(no_id_items):
            if i < len(ad_cards) and ad_cards[i].get("ad_id"):
                item["ad_id"] = ad_cards[i]["ad_id"]
                item["page_name"] = item["page_name"] or ad_cards[i].get("page_name")
                item["ad_body"] = item["ad_body"] or ad_cards[i].get("body")

        await asyncio.sleep(2)
        await browser.close()

    return video_items


def _parse_api_response(obj, result_map: dict, depth=0):
    if depth > 10:
        return
    if isinstance(obj, dict):
        ad_id = str(obj.get("adid") or obj.get("ad_archive_id") or "")
        page_name = obj.get("page_name") or obj.get("advertiser_name")
        bodies = obj.get("ad_creative_bodies") or []
        body = bodies[0] if bodies else None
        # Transparence UE (DSA) : couverture réelle de la pub
        eu_reach = obj.get("eu_total_reach")
        if eu_reach is None:
            eu_reach = (obj.get("aaa_info") or {}).get("eu_total_reach")
        start_date = obj.get("start_date") or obj.get("ad_delivery_start_time")
        videos = []
        snap = obj.get("snapshot") or {}
        for v in snap.get("videos") or []:
            for key in ("video_hd_url", "video_sd_url", "video_url"):
                if v.get(key):
                    videos.append(v[key])
        if ad_id and videos:
            for vurl in videos:
                result_map[vurl] = {
                    "ad_id": ad_id, "page_name": page_name, "body": body,
                    "eu_reach": eu_reach, "start_date": start_date,
                }
        for v in obj.values():
            _parse_api_response(v, result_map, depth + 1)
    elif isinstance(obj, list):
        for item in obj:
            _parse_api_response(item, result_map, depth + 1)


# ──────────────────────────────────────────────────────────────
# 2. TÉLÉCHARGEMENT
# ──────────────────────────────────────────────────────────────

def download_video(url: str, output_path: Path) -> bool:
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Referer": "https://www.facebook.com/",
        }
        with requests.get(url, headers=headers, stream=True, timeout=60) as r:
            r.raise_for_status()
            with open(output_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=65_536):
                    f.write(chunk)
        size_kb = output_path.stat().st_size // 1024
        print(f"    Téléchargé ({size_kb} Ko)")
        return True
    except Exception as e:
        print(f"    ✗ Erreur téléchargement : {e}")
        return False


# ──────────────────────────────────────────────────────────────
# 3. TRANSCRIPTION
# ──────────────────────────────────────────────────────────────

def transcribe_video(video_path: Path, model) -> tuple[str, str]:
    result = model.transcribe(str(video_path), fp16=False)
    lang = result.get("language", "?")
    text = result["text"].strip()
    return text, lang


# ──────────────────────────────────────────────────────────────
# 3b. EXTRACTION DE FRAMES + ANALYSE VISUELLE
# ──────────────────────────────────────────────────────────────

def _ffmpeg_available() -> bool:
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=5, check=True)
        return True
    except Exception:
        return False


def extract_frames(video_path: Path, output_dir: Path) -> list[Path]:
    """Extrait 3 frames clés (0s, 1s, 3s) via ffmpeg pour analyser le hook visuel."""
    if not _ffmpeg_available():
        return []

    frame_dir = output_dir / "frames"
    frame_dir.mkdir(exist_ok=True)
    stem = video_path.stem
    frames = []

    for ts in [0, 1, 3]:
        out = frame_dir / f"{stem}_t{ts}.jpg"
        if out.exists() and out.stat().st_size > 0:
            frames.append(out)
            continue
        try:
            subprocess.run(
                [
                    "ffmpeg", "-ss", str(ts), "-i", str(video_path),
                    "-vframes", "1", "-q:v", "3", "-f", "image2", str(out), "-y",
                ],
                capture_output=True,
                timeout=30,
            )
            if out.exists() and out.stat().st_size > 0:
                frames.append(out)
        except Exception:
            pass

    return frames


def analyze_frames_visually(frames: list[Path], api_key: str) -> dict:
    """Analyse les frames avec Claude Vision (Haiku pour le coût) et retourne un dict structuré."""
    if not frames or not api_key:
        return {}

    try:
        import anthropic as _ant
    except ImportError:
        return {}

    content = []
    for frame in frames[:3]:
        try:
            img_data = base64.standard_b64encode(frame.read_bytes()).decode()
            content.append({
                "type": "image",
                "source": {"type": "base64", "media_type": "image/jpeg", "data": img_data},
            })
        except Exception:
            pass

    if not content:
        return {}

    content.append({
        "type": "text",
        "text": (
            "Analyse ces frames d'une publicité vidéo Meta Ads (Facebook/Instagram). "
            "Réponds UNIQUEMENT avec du JSON valide sans markdown ni explication :\n"
            '{"scene_type":"UGC/studio/lifestyle/talking_head/animation/screen_recording",'
            '"hook_visual":"description précise de ce qu on voit dans les 1ères secondes",'
            '"text_overlays":["textes lisibles à l écran, [] si aucun"],'
            '"setting":"lieu ou environnement filmé",'
            '"product_visible":true,'
            '"product_presentation":"comment et quand le produit apparaît, null si absent",'
            '"visual_style":"description du style visuel global en 10 mots max",'
            '"color_palette":["2-3 couleurs dominantes"],'
            '"actors":"description des personnes présentes"}'
        ),
    })

    try:
        client = _ant.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=500,
            messages=[{"role": "user", "content": content}],
        )
        text = response.content[0].text.strip()
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group())
    except Exception as e:
        print(f"    ⚠ Vision : {e}")

    return {}


# ──────────────────────────────────────────────────────────────
# 4. RAPPORT HTML INTERACTIF
# ──────────────────────────────────────────────────────────────

def top_keywords(results: list[dict], n=20) -> list[tuple[str, int]]:
    stopwords = {
        "le","la","les","de","du","des","un","une","et","en","à","au","aux",
        "est","son","sa","ses","ce","qui","que","quand","dans","sur","par",
        "je","tu","il","elle","nous","vous","ils","elles","me","te","se",
        "mon","ma","mes","ton","ta","tes","si","mais","ou","donc","or","ni","car",
        "plus","pas","ne","très","bien","tout","tous","toute","toutes","même",
        "for","the","and","is","of","to","a","in","that","it","as","on","with",
        "c'est","j'ai","j'","qu'","n'","l'","d'","m'","t'","s'","ça","c'",
    }
    words = []
    for r in results:
        tokens = re.findall(r"\b[a-záàâäéèêëîïôöùûüç]{4,}\b", r["transcript"].lower())
        words.extend(t for t in tokens if t not in stopwords)
    return Counter(words).most_common(n)


def generate_html_report(all_results: list[dict], output_path: Path):
    labels = list(dict.fromkeys(r["label"] for r in all_results))
    date_str = datetime.now().strftime("%d/%m/%Y %H:%M")
    keywords = top_keywords(all_results)
    kw_html = " ".join(
        f'<span class="kw" style="font-size:{min(1.6, 0.8 + c/15):.2f}rem;opacity:{min(1, 0.5+c/20):.2f}" '
        f'data-kw="{w}" onclick="filterByKw(this)">{w}</span>'
        for w, c in keywords
    )

    label_cfg = {
        "Top Performers": {"bg": "#fff8e6", "border": "#f0ad4e", "badge_bg": "#f0ad4e", "badge_fg": "#5a3e00", "icon": "🏆"},
        "Nouvelles Créas": {"bg": "#e8f7fb", "border": "#17a2b8", "badge_bg": "#17a2b8", "badge_fg": "#fff", "icon": "🆕"},
    }
    default_cfg = {"bg": "#f8f9fa", "border": "#adb5bd", "badge_bg": "#6c757d", "badge_fg": "#fff", "icon": "📌"}

    cards_json = json.dumps(all_results, ensure_ascii=False)

    tabs_html = '<button class="tab active" onclick="filterLabel(\'all\')">Toutes (' + str(len(all_results)) + ')</button>'
    for label in labels:
        cfg = label_cfg.get(label, default_cfg)
        count = sum(1 for r in all_results if r["label"] == label)
        border = cfg["border"]
        icon = cfg["icon"]
        tabs_html += f'<button class="tab" onclick="filterLabel(\'{label}\')" style="--tab-color:{border}">{icon} {label} ({count})</button>'

    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Meta Ads — Rapport</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f0f2f5;color:#1c1e21}}
header{{background:linear-gradient(135deg,#1877f2,#0a58ca);color:#fff;padding:20px 32px;display:flex;justify-content:space-between;align-items:center;box-shadow:0 2px 8px rgba(0,0,0,.2)}}
header h1{{font-size:1.3rem;font-weight:700}}
header small{{opacity:.8;font-size:.82rem}}
.toolbar{{background:#fff;border-bottom:1px solid #dde1e7;padding:12px 24px;display:flex;gap:12px;align-items:center;flex-wrap:wrap;position:sticky;top:0;z-index:100;box-shadow:0 2px 6px rgba(0,0,0,.06)}}
.search-wrap{{position:relative;flex:1;min-width:200px}}
.search-wrap input{{width:100%;padding:9px 12px 9px 36px;border:1px solid #d0d5dd;border-radius:8px;font-size:.9rem;outline:none;transition:.2s}}
.search-wrap input:focus{{border-color:#1877f2;box-shadow:0 0 0 3px rgba(24,119,242,.15)}}
.search-wrap::before{{content:"🔍";position:absolute;left:10px;top:50%;transform:translateY(-50%);font-size:.85rem}}
.tabs{{display:flex;gap:6px;flex-wrap:wrap}}
.tab{{border:none;background:#f0f2f5;border-radius:20px;padding:6px 14px;font-size:.82rem;cursor:pointer;transition:.2s;font-weight:500;color:#444}}
.tab:hover{{background:#dde1e7}}
.tab.active{{background:var(--tab-color,#1877f2);color:#fff}}
.sort-select{{padding:7px 10px;border:1px solid #d0d5dd;border-radius:8px;font-size:.82rem;background:#fff;cursor:pointer}}
main{{max-width:1440px;margin:0 auto;padding:24px 16px}}
.stats{{display:flex;gap:12px;margin-bottom:24px;flex-wrap:wrap}}
.stat{{background:#fff;border-radius:10px;padding:14px 20px;box-shadow:0 1px 4px rgba(0,0,0,.08);min-width:120px}}
.stat .n{{font-size:1.8rem;font-weight:800;color:#1877f2}}
.stat .l{{font-size:.78rem;color:#65676b;margin-top:2px}}
.kw-cloud{{background:#fff;border-radius:10px;padding:16px 20px;margin-bottom:24px;box-shadow:0 1px 4px rgba(0,0,0,.08)}}
.kw-cloud h3{{font-size:.85rem;color:#65676b;margin-bottom:10px;font-weight:600;text-transform:uppercase;letter-spacing:.05em}}
.kw{{cursor:pointer;padding:2px 4px;border-radius:4px;margin:2px;display:inline-block;color:#1877f2;font-weight:500;transition:.15s}}
.kw:hover,.kw.active{{background:#1877f2;color:#fff}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:14px}}
.card{{background:#fff;border-radius:10px;border-left:4px solid #adb5bd;padding:16px;box-shadow:0 1px 4px rgba(0,0,0,.08);transition:.2s;display:flex;flex-direction:column;gap:10px}}
.card:hover{{box-shadow:0 4px 16px rgba(0,0,0,.12);transform:translateY(-1px)}}
.card.hidden{{display:none}}
.card-top{{display:flex;align-items:center;gap:8px;flex-wrap:wrap}}
.badge{{border-radius:4px;padding:3px 8px;font-size:.72rem;font-weight:700;white-space:nowrap}}
.pos{{font-size:.78rem;color:#65676b;font-weight:600}}
.meta-link{{margin-left:auto;font-size:.78rem;color:#1877f2;text-decoration:none;padding:3px 8px;border:1px solid #1877f2;border-radius:4px;white-space:nowrap;transition:.15s}}
.meta-link:hover{{background:#1877f2;color:#fff}}
.meta-link.disabled{{color:#adb5bd;border-color:#adb5bd;pointer-events:none}}
.page-name{{font-size:.8rem;color:#444;font-weight:600}}
.reach-badge{{display:inline-block;font-size:.78rem;font-weight:700;color:#0d6e4f;background:#e6f7f0;border-radius:4px;padding:3px 8px;margin:4px 0}}
.ad-body{{font-size:.78rem;color:#65676b;font-style:italic;border-left:3px solid #e4e6ea;padding-left:8px;line-height:1.4}}
.visual-info{{display:flex;flex-wrap:wrap;gap:4px;margin-top:2px}}
.vtag{{background:#eef4ff;color:#1877f2;border-radius:4px;padding:2px 7px;font-size:.7rem;font-weight:600}}
.vtag.style{{background:#f0fff4;color:#2d7a47}}
.vtag.text{{background:#fff8e6;color:#7a5a00}}
.transcript-preview{{font-size:.87rem;line-height:1.55;color:#1c1e21}}
.card-footer{{display:flex;align-items:center;gap:8px;margin-top:4px}}
.lang-badge{{font-size:.75rem;background:#f0f2f5;padding:2px 7px;border-radius:10px;color:#444}}
.word-count{{font-size:.75rem;color:#65676b}}
.copy-btn{{margin-left:auto;background:none;border:1px solid #dde1e7;border-radius:6px;padding:4px 10px;font-size:.75rem;cursor:pointer;color:#444;transition:.15s}}
.copy-btn:hover{{background:#1877f2;color:#fff;border-color:#1877f2}}
.copy-btn.copied{{background:#28a745;color:#fff;border-color:#28a745}}
.adapt-btn{{background:#1877f2;color:#fff;border:none;border-radius:6px;padding:7px 14px;font-size:.8rem;cursor:pointer;font-weight:600;transition:.15s;width:100%;margin-top:6px;text-align:center}}
.adapt-btn:hover{{background:#0a58ca}}
.score-badge{{border-radius:4px;padding:3px 8px;font-size:.78rem;font-weight:700;white-space:nowrap;cursor:default}}
.score-g{{background:#d4edda;color:#155724}}
.score-o{{background:#fff3cd;color:#856404}}
.score-r{{background:#f8d7da;color:#721c24}}
.score-detail{{font-size:.72rem;color:#65676b;margin-top:4px}}
details{{margin-top:4px}}
summary{{font-size:.78rem;color:#1877f2;cursor:pointer;user-select:none}}
pre{{font-size:.82rem;line-height:1.6;white-space:pre-wrap;background:#f8f9fa;padding:10px;border-radius:6px;margin-top:6px;max-height:200px;overflow-y:auto}}
.empty-state{{text-align:center;padding:60px;color:#65676b;font-size:1rem}}
mark{{background:#fff3cd;border-radius:2px}}
@media(max-width:600px){{.grid{{grid-template-columns:1fr}}.stats{{gap:8px}}}}
</style>
</head>
<body>
<header>
  <h1>📊 Meta Ads — Rapport de transcription</h1>
  <small>Généré le {date_str}</small>
</header>

<div class="toolbar">
  <div class="search-wrap">
    <input type="text" id="search" placeholder="Rechercher dans les transcriptions..." oninput="applyFilters()">
  </div>
  <div class="tabs" id="tabs">{tabs_html}</div>
  <select class="sort-select" id="sort" onchange="applyFilters()">
    <option value="position">Trier par position</option>
    <option value="reach_desc">📡 Plus grosse couverture UE en premier</option>
    <option value="score_desc">⭐ Meilleur score en premier</option>
    <option value="score_asc">Score le plus bas en premier</option>
    <option value="words_desc">Plus de mots en premier</option>
    <option value="words_asc">Moins de mots en premier</option>
  </select>
</div>

<main>
  <div class="stats" id="stats-bar"></div>

  <div class="kw-cloud">
    <h3>Mots-clés fréquents — cliquer pour filtrer</h3>
    <div>{kw_html}</div>
  </div>

  <div class="grid" id="grid"></div>
  <div class="empty-state hidden" id="empty">Aucune transcription ne correspond à ta recherche.</div>
</main>

<script>
const DATA = {cards_json};
const LABEL_CFG = {{
  "Top Performers": {{bg:"#fff8e6",border:"#f0ad4e",badge_bg:"#f0ad4e",badge_fg:"#5a3e00",icon:"🏆"}},
  "Nouvelles Créas": {{bg:"#e8f7fb",border:"#17a2b8",badge_bg:"#17a2b8",badge_fg:"#fff",icon:"🆕"}},
}};
const DEFAULT_CFG = {{bg:"#f8f9fa",border:"#adb5bd",badge_bg:"#6c757d",badge_fg:"#fff",icon:"📌"}};

let currentLabel = "all";
let currentKw = null;

function cfg(label){{ return LABEL_CFG[label] || DEFAULT_CFG; }}
function wordCount(t){{ return t.trim().split(/\\s+/).length; }}

function highlight(text, query){{
  if(!query) return text;
  const re = new RegExp("(" + query.replace(/[.*+?^${{}}()|[\\]\\\\]/g,"\\\\$&") + ")", "gi");
  return text.replace(re, "<mark>$1</mark>");
}}

function buildVisualInfo(va){{
  if(!va || !Object.keys(va).length) return "";
  let tags = "";
  if(va.scene_type) tags += `<span class="vtag">📷 ${{va.scene_type}}</span>`;
  if(va.visual_style) tags += `<span class="vtag style">🎨 ${{va.visual_style}}</span>`;
  if(va.hook_visual) tags += `<span class="vtag">👁 ${{va.hook_visual.substring(0,60)}}</span>`;
  if(va.text_overlays && va.text_overlays.length)
    tags += `<span class="vtag text">💬 ${{va.text_overlays.slice(0,2).join(" · ")}}</span>`;
  return tags ? `<div class="visual-info">${{tags}}</div>` : "";
}}

function buildScoreBadge(sc) {{
  if(!sc || sc.score_total == null) return "";
  const t = sc.score_total;
  const cls = t >= 8 ? "score-g" : t >= 5 ? "score-o" : "score-r";
  const tip = [
    sc.score_generic  != null ? `Générique: ${{sc.score_generic}}/10` : "",
    sc.score_product  != null ? `Produit: ${{sc.score_product}}/10` : "",
    sc.verdict ? `"${{sc.verdict}}"` : "",
    sc.top_words && sc.top_words.length ? `Mots clés: ${{sc.top_words.join(", ")}}` : ""
  ].filter(Boolean).join(" · ");
  const critera = sc.hook_strength != null
    ? `<span class="score-detail">Hook ${{sc.hook_strength}} · Clarté ${{sc.educational_clarity}} · Mots ${{sc.words_quality}} · Structure ${{sc.narrative_structure}}</span>`
    : "";
  return `<span class="score-badge ${{cls}}" title="${{tip}}">${{t.toFixed ? t.toFixed(1) : t}} ⭐</span>${{critera}}`;
}}

function adaptScript(idx) {{
  try {{
    var url = new URL(window.top.location.href);
    url.searchParams.set('adapt_idx', String(idx));
    window.top.location.href = url.toString();
  }} catch(e) {{
    console.warn('Navigation parent impossible:', e);
  }}
}}

function fmtReach(n){{
  if(n >= 1000000) return (n/1000000).toFixed(1).replace('.0','') + ' M';
  if(n >= 1000) return (n/1000).toFixed(1).replace('.0','') + ' k';
  return String(n);
}}

function buildCard(r, query, dataIdx){{
  const c = cfg(r.label);
  const wc = wordCount(r.transcript);
  const flag = {{"fr":"🇫🇷","en":"🇬🇧","es":"🇪🇸","de":"🇩🇪","it":"🇮🇹","pt":"🇵🇹","nl":"🇳🇱","ar":"🇸🇦"}}[r.lang] || "🌐";
  const metaUrl = r.ad_id ? `https://www.facebook.com/ads/library/?id=${{r.ad_id}}` : null;
  const metaBtn = metaUrl
    ? `<a class="meta-link" href="${{metaUrl}}" target="_blank" rel="noopener">Voir sur Meta ↗</a>`
    : `<span class="meta-link disabled">ID non disponible</span>`;
  const preview = highlight((r.transcript.substring(0,280) + (r.transcript.length>280?"...":"")), query);
  const fullText = r.transcript.replace(/</g,"&lt;");
  const pageHtml = r.page_name ? `<span class="page-name">📄 ${{r.page_name}}</span>` : "";
  const reachHtml = r.eu_reach
    ? `<span class="reach-badge" title="Couverture totale UE (donnée officielle Meta)">📡 ${{fmtReach(r.eu_reach)}} personnes</span>`
    : "";
  const bodyHtml = r.ad_body ? `<div class="ad-body">${{r.ad_body}}</div>` : "";
  const vaHtml = buildVisualInfo(r.visual_analysis);
  const scoreBadge = buildScoreBadge(r.scoring);
  const scoreVal = (r.scoring || {{}}).score_total || 0;
  return `
<div class="card" data-label="${{r.label}}" data-pos="${{r.position}}" data-words="${{wc}}" data-score="${{scoreVal}}"
     data-text="${{r.transcript.toLowerCase().replace(/"/g,'&quot;')}}"
     style="border-left-color:${{c.border}};background:${{c.bg}}">
  <div class="card-top">
    <span class="badge" style="background:${{c.badge_bg}};color:${{c.badge_fg}}">${{c.icon}} ${{r.label}}</span>
    <span class="pos">#${{r.position}}</span>
    ${{scoreBadge}}
    ${{metaBtn}}
  </div>
  ${{pageHtml}}
  ${{reachHtml}}
  ${{bodyHtml}}
  ${{vaHtml}}
  <div class="transcript-preview">${{preview}}</div>
  <div class="card-footer">
    <span class="lang-badge">${{flag}} ${{r.lang || "?"}}</span>
    <span class="word-count">${{wc}} mots</span>
    <button class="copy-btn" onclick="copyTranscript(this, \`${{fullText}}\`)">Copier</button>
  </div>
  <details>
    <summary>Transcription complète</summary>
    <pre>${{fullText}}</pre>
  </details>
  <button class="adapt-btn" onclick="adaptScript(${{dataIdx}})">🎯 Adapter à mon produit</button>
</div>`;
}}

function applyFilters(){{
  const query = document.getElementById("search").value.trim().toLowerCase();
  const sort = document.getElementById("sort").value;
  const grid = document.getElementById("grid");

  let filtered = DATA.filter(r => {{
    if(currentLabel !== "all" && r.label !== currentLabel) return false;
    if(currentKw && !r.transcript.toLowerCase().includes(currentKw)) return false;
    if(query && !r.transcript.toLowerCase().includes(query)
             && !(r.page_name||"").toLowerCase().includes(query)
             && !(r.ad_body||"").toLowerCase().includes(query)) return false;
    return true;
  }});

  const sc = r => (r.scoring || {{}}).score_total || 0;
  const rch = r => r.eu_reach || 0;
  if(sort === "score_desc") filtered.sort((a,b) => sc(b) - sc(a));
  else if(sort === "score_asc") filtered.sort((a,b) => sc(a) - sc(b));
  else if(sort === "reach_desc") filtered.sort((a,b) => rch(b) - rch(a));
  else if(sort === "words_desc") filtered.sort((a,b) => wordCount(b.transcript) - wordCount(a.transcript));
  else if(sort === "words_asc") filtered.sort((a,b) => wordCount(a.transcript) - wordCount(b.transcript));
  else filtered.sort((a,b) => a.position - b.position);

  grid.innerHTML = filtered.map(r => buildCard(r, query, DATA.indexOf(r))).join("");
  document.getElementById("empty").classList.toggle("hidden", filtered.length > 0);
  updateStats(filtered);
}}

function filterLabel(label){{
  currentLabel = label;
  document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
  event.target.classList.add("active");
  applyFilters();
}}

function filterByKw(el){{
  const kw = el.dataset.kw;
  if(currentKw === kw){{
    currentKw = null;
    document.querySelectorAll(".kw").forEach(k => k.classList.remove("active"));
  }} else {{
    currentKw = kw;
    document.querySelectorAll(".kw").forEach(k => k.classList.toggle("active", k.dataset.kw === kw));
  }}
  applyFilters();
}}

function updateStats(filtered){{
  const labels = [...new Set(filtered.map(r => r.label))];
  let html = `<div class="stat"><div class="n">${{filtered.length}}</div><div class="l">résultats</div></div>`;
  labels.forEach(l => {{
    const c = cfg(l);
    const n = filtered.filter(r => r.label === l).length;
    html += `<div class="stat"><div class="n" style="color:${{c.border}}">${{n}}</div><div class="l">${{c.icon}} ${{l}}</div></div>`;
  }});
  const withId = filtered.filter(r => r.ad_id).length;
  const withVision = filtered.filter(r => r.visual_analysis && Object.keys(r.visual_analysis).length).length;
  const withScore = filtered.filter(r => r.scoring && r.scoring.score_total != null);
  html += `<div class="stat"><div class="n">${{withId}}</div><div class="l">liens Meta dispo</div></div>`;
  if(withVision) html += `<div class="stat"><div class="n" style="color:#7c3aed">${{withVision}}</div><div class="l">📷 Analysés visuel</div></div>`;
  if(withScore.length) {{
    const avg = (withScore.reduce((s,r) => s + r.scoring.score_total, 0) / withScore.length).toFixed(1);
    const avgCls = avg >= 8 ? "#155724" : avg >= 5 ? "#856404" : "#721c24";
    html += `<div class="stat"><div class="n" style="color:${{avgCls}}">${{avg}}</div><div class="l">⭐ Score moyen (${{withScore.length}} pubs)</div></div>`;
  }}
  document.getElementById("stats-bar").innerHTML = html;
}}

function copyTranscript(btn, text){{
  navigator.clipboard.writeText(text).then(() => {{
    btn.textContent = "✓ Copié";
    btn.classList.add("copied");
    setTimeout(() => {{ btn.textContent = "Copier"; btn.classList.remove("copied"); }}, 2000);
  }});
}}

applyFilters();
</script>
</body>
</html>"""

    output_path.write_text(html, encoding="utf-8")
    print(f"\n  Rapport HTML : {output_path}")


# ──────────────────────────────────────────────────────────────
# 5. PROGRAMME PRINCIPAL
# ──────────────────────────────────────────────────────────────

async def main(url_label_pairs: list[tuple[str, str]]):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("\n╔══════════════════════════════════════════════╗")
    print("║   Meta Ads Library — Transcription vidéo    ║")
    print("╚══════════════════════════════════════════════╝")

    all_video_items: list[dict] = []
    for url, label in url_label_pairs:
        print(f"\n[SCRAPING] {label}")
        items = await scrape_video_urls(url, label)
        all_video_items.extend(items)
        print(f"  → {len(items)} vidéo(s) trouvée(s) pour « {label} »")

    if not all_video_items:
        print("\n⚠ Aucune vidéo trouvée.")
        return

    print(f"\nTotal : {len(all_video_items)} vidéo(s)")

    api_key = (os.environ.get("ANTHROPIC_API_KEY") or "").strip()
    ffmpeg_ok = _ffmpeg_available()
    if ffmpeg_ok and api_key:
        print("  ✓ Analyse visuelle activée (ffmpeg + Claude Vision)")
    elif ffmpeg_ok:
        print("  ℹ ffmpeg disponible mais pas de clé API → frames extraites, analyse visuelle désactivée")
    else:
        print("  ℹ ffmpeg non trouvé → analyse visuelle désactivée")

    print(f"\n[WHISPER] Chargement du modèle « {WHISPER_MODEL} »...")
    model = whisper.load_model(WHISPER_MODEL)

    print(f"\n[TRANSCRIPTION] Traitement...\n")
    results = []

    # Charger les transcriptions existantes pour les fusionner
    existing_json = OUTPUT_DIR / "all_transcriptions.json"
    existing_map: dict[str, dict] = {}
    if existing_json.exists():
        try:
            for entry in json.loads(existing_json.read_text(encoding="utf-8")):
                key = f"{entry.get('label')}_{entry.get('position')}"
                existing_map[key] = entry
        except Exception:
            pass

    for i, item in enumerate(all_video_items, 1):
        print(f"  ── {item['label']} #{item['position']} ({i}/{len(all_video_items)}) ──")
        safe_label = item["label"].replace(" ", "_").lower()
        video_path = OUTPUT_DIR / f"{safe_label}_{item['position']:02d}.mp4"
        transcript_path = OUTPUT_DIR / f"{safe_label}_{item['position']:02d}.txt"

        if transcript_path.exists():
            print(f"    ↩ Déjà transcrit, ignoré.")
            try:
                existing = json.loads(transcript_path.read_text(encoding="utf-8"))
                results.append(existing)
            except Exception:
                pass
            continue

        if not download_video(item["url"], video_path):
            continue

        # Extraire les frames avant de supprimer la vidéo
        frames = []
        if ffmpeg_ok:
            frames = extract_frames(video_path, OUTPUT_DIR)
            if frames:
                print(f"    📷 {len(frames)} frame(s) extraite(s)")

        print(f"    Transcription...")
        try:
            transcript, lang = transcribe_video(video_path, model)

            # Analyse visuelle si possible
            visual = {}
            if frames and api_key:
                print(f"    🔍 Analyse visuelle...")
                visual = analyze_frames_visually(frames, api_key)
                if visual:
                    print(f"    ✓ {visual.get('scene_type', '?')} — {visual.get('hook_visual', '')[:60]}")

            # Scoring intelligent
            scoring = {}
            if api_key:
                try:
                    from scorer import score_ad, load_scoring_context
                    from product_context import load_context, format_for_prompt as _fmt_prod
                    _sc_ctx = load_scoring_context()
                    _prod_str = _fmt_prod(load_context())
                    print(f"    🎯 Scoring...")
                    scoring = score_ad(transcript, api_key, _prod_str, _sc_ctx.get("objective", ""))
                    if scoring:
                        print(f"    ⭐ {scoring.get('score_total', '?')}/10 — {scoring.get('verdict', '')}")
                except Exception as _se:
                    print(f"    ⚠ Scoring ignoré : {_se}")

            entry = {
                "label": item["label"],
                "position": item["position"],
                "lang": lang,
                "transcript": transcript,
                "url": item["url"],
                "ad_id": item.get("ad_id"),
                "page_name": item.get("page_name"),
                "ad_body": item.get("ad_body"),
                "eu_reach": item.get("eu_reach"),
                "start_date": item.get("start_date"),
                "visual_analysis": visual,
                "frames": [str(f.name) for f in frames],
                "scoring": scoring,
            }
            transcript_path.write_text(json.dumps(entry, ensure_ascii=False, indent=2), encoding="utf-8")
            flag = LANG_FLAG.get(lang, "🌐")
            print(f"    {flag} [{lang}] {transcript[:100]}...")
            results.append(entry)
        except Exception as e:
            print(f"    ✗ Erreur : {e}")
        finally:
            video_path.unlink(missing_ok=True)

    if results:
        json_path = OUTPUT_DIR / "all_transcriptions.json"
        json_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        html_path = OUTPUT_DIR / "rapport.html"
        generate_html_report(results, html_path)
        print(f"\n✓ {len(results)} transcription(s) sauvegardée(s)")
        print(f"  → Ouvre : open \"{html_path}\"")
    else:
        print("\n✗ Aucune transcription produite.")


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", action="append", dest="urls", metavar="URL")
    parser.add_argument("--label", action="append", dest="labels", metavar="LABEL")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if not args.urls:
        print("Usage:")
        print('  python transcriber.py --url "URL" --label "Top Performers"')
        sys.exit(1)
    labels = args.labels or []
    while len(labels) < len(args.urls):
        labels.append(f"Catégorie {len(labels)+1}")

    # Paramètres overridables depuis Streamlit
    if os.environ.get("WHISPER_MODEL_OVERRIDE"):
        WHISPER_MODEL = os.environ["WHISPER_MODEL_OVERRIDE"]
    if os.environ.get("SCROLL_COUNT_OVERRIDE"):
        try:
            SCROLL_COUNT = int(os.environ["SCROLL_COUNT_OVERRIDE"])
        except ValueError:
            pass

    asyncio.run(main(list(zip(args.urls, labels))))
