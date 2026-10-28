#!/usr/bin/env python3
"""Collecte les métadonnées des pubs de l'Ad Library (sans transcription) en lisant les réponses GraphQL.
Usage : python adlib_meta.py --out out.json --url URL --label L [--url URL --label L ...]
"""
import argparse, asyncio, json, os
from datetime import datetime
from playwright.async_api import async_playwright

SCROLLS = int(os.environ.get("SCROLL_COUNT_OVERRIDE", "8"))


def _day(ts):
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d") if isinstance(ts, (int, float)) and ts > 0 else None


def _walk(o, ads):
    if isinstance(o, dict):
        for item in o.get("collated_results") or []:
            if isinstance(item, dict) and item.get("ad_archive_id"):
                ads[str(item["ad_archive_id"])] = item
        for v in o.values():
            _walk(v, ads)
    elif isinstance(o, list):
        for v in o:
            _walk(v, ads)


def slim(a, label):
    s = a.get("snapshot") or {}
    vids = s.get("videos") or []
    return {
        "label": label, "ad_id": str(a.get("ad_archive_id")), "collation_id": a.get("collation_id"),
        "collation_count": a.get("collation_count"), "is_active": a.get("is_active"),
        "start_date": _day(a.get("start_date")), "end_date": _day(a.get("end_date")),
        "page_name": a.get("page_name") or s.get("page_name"), "page_id": a.get("page_id"),
        "body": ((s.get("body") or {}).get("text") if isinstance(s.get("body"), dict) else s.get("body")),
        "title": s.get("title"), "cta": s.get("cta_text"), "link_url": s.get("link_url"),
        "display_format": s.get("display_format"),
        "video_url": next((v.get("video_hd_url") or v.get("video_sd_url") for v in vids if v), None),
        "n_cards": len(s.get("cards") or []),
        "platforms": a.get("publisher_platform"),
    }


async def collect(url, label, page_ctx):
    ads = {}

    async def on_response(r):
        if "/api/graphql/" in r.url and r.request.method == "POST":
            try:
                txt = (await r.text()).lstrip("for (;;);").strip()
                for line in txt.split("\n"):
                    try: _walk(json.loads(line), ads)
                    except Exception: pass
            except Exception:
                pass

    page = await page_ctx.new_page()
    page.on("response", on_response)
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=60_000)
    except Exception as e:
        print("  avertissement :", e)
    await asyncio.sleep(4)
    last, stagnant = -1, 0
    for _ in range(SCROLLS):
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(3.5)
        stagnant = stagnant + 1 if len(ads) == last else 0
        if stagnant >= 3: break  # 3 scrolls sans nouvelle pub
        last = len(ads)
    await page.close()
    return [slim(a, label) for a in ads.values()]


async def main(pairs, out):
    res = []
    async with async_playwright() as p:
        b = await p.chromium.launch(headless=False, args=["--disable-blink-features=AutomationControlled"])
        ctx = await b.new_context(viewport={"width": 1280, "height": 900}, locale="fr-FR",
                                  user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
        for url, label in pairs:
            got = await collect(url, label, ctx)
            print(f"  {label}: {len(got)} pubs", flush=True)
            res += got
            json.dump(res, open(out, "w"), ensure_ascii=False, indent=1)  # sauvegarde au fil de l'eau
        await b.close()
    print(f"✓ {len(res)} pubs -> {out}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", action="append", required=True)
    ap.add_argument("--label", action="append", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    asyncio.run(main(list(zip(a.url, a.label)), a.out))
