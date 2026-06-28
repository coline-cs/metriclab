#!/usr/bin/env python3
"""
Gestionnaire de contexte produit pour l'agent expert.
Scrape un site web (multi-pages) + analyse les images produit via Claude Vision.
"""

import base64
import json
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests

CONTEXT_FILE = Path(__file__).parent / "transcriptions" / "product_context.json"

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}


# ──────────────────────────────────────────────────────────────
# SCRAPING TEXTE (simple + deep)
# ──────────────────────────────────────────────────────────────

def _parse_page(url: str, html: str) -> dict:
    """Parse une page HTML et extrait le contenu utile."""
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "head", "header"]):
            tag.decompose()

        title_tag = soup.find("title")
        meta_desc = soup.find("meta", {"name": "description"}) or soup.find(
            "meta", {"property": "og:description"}
        )
        headings = [
            h.get_text(" ", strip=True)
            for h in soup.find_all(["h1", "h2", "h3"])
            if h.get_text(strip=True)
        ][:30]
        paragraphs = [
            p.get_text(" ", strip=True)
            for p in soup.find_all("p")
            if len(p.get_text(strip=True)) > 40
        ][:50]

        # Collecter les liens internes pour deep scan
        base = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
        internal_links = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            full = urljoin(url, href)
            if full.startswith(base) and full != url and "#" not in full:
                clean = full.split("?")[0].rstrip("/")
                if clean not in internal_links:
                    internal_links.append(clean)

        # Collecter les images
        images = []
        for img in soup.find_all("img", src=True):
            src = urljoin(url, img["src"])
            alt = img.get("alt", "")
            if src.startswith("http") and any(ext in src.lower() for ext in [".jpg", ".jpeg", ".png", ".webp"]):
                images.append({"src": src, "alt": alt})

        return {
            "url": url,
            "title": title_tag.get_text(strip=True) if title_tag else url,
            "meta_description": meta_desc.get("content", "") if meta_desc else "",
            "headings": headings,
            "paragraphs": paragraphs,
            "internal_links": internal_links[:40],
            "images": images[:30],
        }
    except ImportError:
        text = re.sub(r"<[^>]+>", " ", html)
        text = re.sub(r"\s+", " ", text).strip()
        return {
            "url": url, "title": url, "meta_description": "",
            "headings": [], "paragraphs": [text[:4000]],
            "internal_links": [], "images": [],
        }


def scrape_website(url: str) -> dict:
    """Scrape simple d'une page (compatibilité avec le code existant)."""
    try:
        r = requests.get(url, headers=_HEADERS, timeout=30)
        r.raise_for_status()
    except Exception as e:
        raise RuntimeError(f"Impossible de charger {url} : {e}")
    result = _parse_page(url, r.text)
    result.pop("internal_links", None)
    return result


def scrape_website_deep(url: str, max_pages: int = 5) -> dict:
    """
    Scrape multi-pages : homepage + pages clés détectées automatiquement.
    Retourne un dict enrichi avec toutes les pages fusionnées.
    """
    try:
        r = requests.get(url, headers=_HEADERS, timeout=30)
        r.raise_for_status()
    except Exception as e:
        raise RuntimeError(f"Impossible de charger {url} : {e}")

    home = _parse_page(url, r.text)
    base_domain = f"{urlparse(url).scheme}://{urlparse(url).netloc}"

    # Prioriser les pages "produit / à propos / faq / témoignages"
    priority_keywords = ["produit", "product", "about", "qui-sommes", "faq", "avis", "temoignage",
                         "review", "ingredient", "ingredient", "solution", "shop", "boutique"]
    candidate_links = home.get("internal_links", [])
    priority_links = [l for l in candidate_links if any(k in l.lower() for k in priority_keywords)]
    other_links = [l for l in candidate_links if l not in priority_links]
    to_crawl = (priority_links + other_links)[:max_pages - 1]

    all_pages = [home]
    for link in to_crawl:
        try:
            rp = requests.get(link, headers=_HEADERS, timeout=20)
            if rp.status_code == 200:
                page_data = _parse_page(link, rp.text)
                page_data.pop("internal_links", None)
                all_pages.append(page_data)
        except Exception:
            pass

    # Fusionner tous les contenus
    all_headings = []
    all_paragraphs = []
    all_images = []
    for p in all_pages:
        all_headings.extend(p.get("headings", []))
        all_paragraphs.extend(p.get("paragraphs", []))
        all_images.extend(p.get("images", []))

    # Dédoublonner
    seen_h, seen_p = set(), set()
    unique_headings = [h for h in all_headings if h not in seen_h and not seen_h.add(h)]
    unique_paragraphs = [p for p in all_paragraphs if p not in seen_p and not seen_p.add(p)]
    seen_img = set()
    unique_images = [i for i in all_images if i["src"] not in seen_img and not seen_img.add(i["src"])]

    return {
        "url": url,
        "title": home.get("title", url),
        "meta_description": home.get("meta_description", ""),
        "headings": unique_headings[:40],
        "paragraphs": unique_paragraphs[:60],
        "images": unique_images[:20],
        "pages_scraped": [p["url"] for p in all_pages],
        "deep": True,
    }


# ──────────────────────────────────────────────────────────────
# ANALYSE DES IMAGES PRODUIT VIA CLAUDE VISION
# ──────────────────────────────────────────────────────────────

def analyze_product_images(images: list[dict], api_key: str, max_images: int = 6) -> dict:
    """
    Télécharge et analyse les images produit d'un site via Claude Vision.
    Retourne des insights visuels pour enrichir les scripts.
    """
    if not images or not api_key:
        return {}

    try:
        import anthropic as _ant
    except ImportError:
        return {}

    content = []
    downloaded = 0
    for img in images:
        if downloaded >= max_images:
            break
        try:
            resp = requests.get(img["src"], headers=_HEADERS, timeout=15, stream=True)
            if resp.status_code != 200:
                continue
            # Vérifier que c'est une vraie image
            ct = resp.headers.get("content-type", "")
            if not any(t in ct for t in ["image/jpeg", "image/jpg", "image/png", "image/webp"]):
                continue
            data = resp.content
            if len(data) < 5000:  # ignorer les icônes minuscules
                continue
            media_type = "image/jpeg" if "jpeg" in ct or "jpg" in ct else "image/png" if "png" in ct else "image/webp"
            b64 = base64.standard_b64encode(data).decode()
            content.append({
                "type": "image",
                "source": {"type": "base64", "media_type": media_type, "data": b64},
            })
            if img.get("alt"):
                content.append({"type": "text", "text": f"(alt: {img['alt']})"})
            downloaded += 1
        except Exception:
            pass

    if not content:
        return {}

    content.append({
        "type": "text",
        "text": (
            "Analyse ces images d'un site e-commerce de produits physiques. "
            "Réponds UNIQUEMENT en JSON valide :\n"
            '{"product_type":"type de produit identifié",'
            '"visual_identity":"description de l\'identité visuelle en 15 mots",'
            '"color_palette":["couleur1","couleur2"],'
            '"target_audience":"profil de la cible déduit des visuels",'
            '"product_claims":["promesse ou claim visible sur packaging/site"],'
            '"lifestyle_context":"contexte d\'usage montré dans les images",'
            '"differentiators":["éléments visuels distinctifs vs concurrents"],'
            '"mood":"ambiance générale en 5 mots"}'
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
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            return json.loads(m.group())
    except Exception as e:
        print(f"  ⚠ Analyse images : {e}")

    return {}


# ──────────────────────────────────────────────────────────────
# PERSISTANCE
# ──────────────────────────────────────────────────────────────

def load_context() -> dict:
    if CONTEXT_FILE.exists():
        try:
            return json.loads(CONTEXT_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"scraped": [], "manual": ""}


def save_context(data: dict):
    CONTEXT_FILE.parent.mkdir(parents=True, exist_ok=True)
    CONTEXT_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def format_for_prompt(context: dict) -> str:
    """Formatte le contexte produit pour injection dans le system prompt."""
    parts = []

    for site in context.get("scraped", []):
        pages_info = f" ({len(site.get('pages_scraped', []))} pages)" if site.get("deep") else ""
        parts.append(f"### Site importé{pages_info} : {site.get('url', '')}")
        if site.get("title"):
            parts.append(f"Titre : {site['title']}")
        if site.get("meta_description"):
            parts.append(f"Description : {site['meta_description']}")
        if site.get("headings"):
            parts.append("Titres / sections : " + " | ".join(site["headings"][:20]))
        if site.get("paragraphs"):
            parts.append("Contenu clé :")
            for p in site["paragraphs"][:25]:
                parts.append(f"  {p}")
        # Insights visuels
        vi = site.get("visual_insights") or {}
        if vi:
            parts.append("Identité visuelle :")
            if vi.get("product_type"):
                parts.append(f"  Produit : {vi['product_type']}")
            if vi.get("visual_identity"):
                parts.append(f"  Style : {vi['visual_identity']}")
            if vi.get("target_audience"):
                parts.append(f"  Cible déduite : {vi['target_audience']}")
            if vi.get("product_claims"):
                parts.append(f"  Claims : {' | '.join(vi['product_claims'][:5])}")
            if vi.get("differentiators"):
                parts.append(f"  Différenciateurs : {' | '.join(vi['differentiators'][:4])}")
            if vi.get("mood"):
                parts.append(f"  Mood : {vi['mood']}")

    if context.get("manual", "").strip():
        parts.append(f"\n### Notes manuelles\n{context['manual'].strip()}")

    return "\n".join(parts)
