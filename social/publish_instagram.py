"""Plaatst een afbeelding + caption op Instagram via de Instagram Graph API.

  python social/publish_instagram.py daily-2026-12-06

Verwacht dat de afbeelding al online staat op https://hoelaatbegint.nl/social/<naam>.jpg
(de workflow deployt eerst de site en publiceert daarna).
Omgevingsvariabelen: IG_USER_ID, IG_ACCESS_TOKEN, optioneel GRAPH_VERSION en ANTHROPIC_API_KEY
(dan schrijft Claude een levendigere caption op basis van dezelfde feiten).
"""
import json
import os
import re
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
BASE = json.loads((ROOT / "site" / "config.json").read_text())["base_url"].rstrip("/")
GRAPH = f"https://graph.facebook.com/{os.environ.get('GRAPH_VERSION', 'v24.0')}"


def polish(caption):
    """Laat Claude de caption iets levendiger maken. Tijden en namen moeten exact gelijk blijven."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key or os.environ.get("AI_CAPTIONS") != "1":  # standaard uit: de sjabloon-caption is gratis
        return caption, False
    r = requests.post("https://api.anthropic.com/v1/messages", timeout=60, headers={
        "x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
        json={"model": os.environ.get("CLAUDE_MODEL", "claude-sonnet-5-5"), "max_tokens": 600, "messages": [{"role": "user", "content":
              "Herschrijf deze Instagram-caption voor @hoelaatbegint: één korte, sportieve openingszin erbij, verder "
              "alle regels met tijden en namen EXACT laten staan, hashtags onderaan houden. Geen gokken, geen odds. "
              "Geef alleen de caption terug.\n\n" + caption}]})
    r.raise_for_status()
    new = "".join(b.get("text", "") for b in r.json()["content"] if b.get("type") == "text").strip()
    # Controle: elke tijd uit het origineel moet er nog in staan
    if all(t in new for t in re.findall(r"\b\d{1,2}:\d{2}\b", caption)):
        return new, True
    return caption, False


def main():
    name = sys.argv[1]
    if not (os.environ.get("IG_USER_ID") and os.environ.get("IG_ACCESS_TOKEN")):
        print("Instagram niet ingesteld: overgeslagen")
        return
    cap_file = ROOT / "dist" / "social" / f"{name}.txt"
    if not cap_file.exists():
        print("Geen post voor vandaag")
        return
    caption, ai = polish(cap_file.read_text(encoding="utf-8"))
    token, uid = os.environ["IG_ACCESS_TOKEN"], os.environ["IG_USER_ID"]
    payload = {"image_url": f"{BASE}/social/{name}.jpg", "caption": caption, "access_token": token}
    if ai:
        payload["is_ai_generated"] = "true"  # AI-label voor de caption (Instagram-API, sinds september 2026)
    r = requests.post(f"{GRAPH}/{uid}/media", data=payload, timeout=60)
    r.raise_for_status()
    container = r.json()["id"]
    for _ in range(20):  # wachten tot Instagram de afbeelding verwerkt heeft
        s = requests.get(f"{GRAPH}/{container}", params={"fields": "status_code", "access_token": token}, timeout=30).json()
        if s.get("status_code") == "FINISHED":
            break
        if s.get("status_code") == "ERROR":
            raise SystemExit(f"Instagram weigerde de afbeelding: {s}")
        time.sleep(5)
    r = requests.post(f"{GRAPH}/{uid}/media_publish", data={"creation_id": container, "access_token": token}, timeout=60)
    r.raise_for_status()
    print("Geplaatst op Instagram:", r.json())


if __name__ == "__main__":
    main()
