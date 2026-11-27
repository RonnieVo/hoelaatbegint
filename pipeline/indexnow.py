"""Meldt gewijzigde pagina's direct bij Bing (en daarmee ChatGPT-zoeken), Yandex en andere IndexNow-zoekmachines.

Sleutel: INDEXNOW_KEY (een willekeurige reeks van 32 tekens). build.py zet het sleutelbestand in dist/.
"""
import json
import os
import re
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
BASE = json.loads((ROOT / "site" / "config.json").read_text())["base_url"].rstrip("/")


def main():
    key = (os.environ.get("INDEXNOW_KEY") or "").strip()
    if not key:
        print("IndexNow overgeslagen (geen sleutel)")
        return
    urls = [f"{BASE}/", f"{BASE}/vandaag/"]
    sitemap = "".join(f.read_text() for f in (ROOT / "dist").glob("sitemap-*.xml"))  # alleen indexeerbare pagina's
    changed = json.loads((ROOT / "data" / "changed.json").read_text()) if (ROOT / "data" / "changed.json").exists() else []
    events = {e["id"]: e for e in json.loads((ROOT / "data" / "events.json").read_text())["events"]}
    tournaments = json.loads((ROOT / "data" / "tournaments.json").read_text())
    for eid in changed:
        e = events.get(eid)
        if not e:
            continue
        if e.get("page"):
            urls.append(f"{BASE}/wedstrijd/{e['page']}/")
        if e.get("tournament") in tournaments:
            urls.append(f"{BASE}/{e['tournament']}/")
    if os.environ.get("INDEXNOW_ALL") == "true":
        urls += re.findall(r"<loc>(.*?)</loc>", sitemap)
    urls = [u for u in dict.fromkeys(urls) if f"<loc>{u}</loc>" in sitemap]
    r = requests.post("https://api.indexnow.org/indexnow", timeout=20, json={
        "host": BASE.split("://")[1], "key": key, "keyLocation": f"{BASE}/{key}.txt", "urlList": urls})
    print(f"IndexNow: {len(urls)} url's, status {r.status_code} {r.text[:200]}")
    if r.status_code >= 400:  # diagnose zonder de sleutel te tonen
        try:
            k = requests.get(f"{BASE}/{key}.txt", timeout=15, headers={"User-Agent": "Mozilla/5.0 (compatible; bingbot/2.0)"})
            print(f"Sleutelbestand: status {k.status_code}, type {k.headers.get('content-type')}, klopt: {k.text.strip() == key}, "
                  f"lengte sleutel {len(key)}, alleen geldige tekens: {bool(re.fullmatch(r'[A-Za-z0-9-]{8,128}', key))}")
        except Exception as exc:
            print(f"Sleutelbestand niet op te halen: {exc}")


if __name__ == "__main__":
    main()
