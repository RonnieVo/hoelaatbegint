"""Meldt gewijzigde pagina's direct bij Bing (en daarmee ChatGPT-zoeken), Yandex en andere IndexNow-zoekmachines.

Sleutel: INDEXNOW_KEY (een willekeurige reeks van 32 tekens). build.py zet het sleutelbestand in dist/.
"""
import json
import os
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
BASE = json.loads((ROOT / "site" / "config.json").read_text())["base_url"].rstrip("/")


def main():
    key = os.environ.get("INDEXNOW_KEY")
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
    urls = [u for u in dict.fromkeys(urls) if f"<loc>{u}</loc>" in sitemap]
    r = requests.post("https://api.indexnow.org/indexnow", timeout=20, json={
        "host": BASE.split("://")[1], "key": key, "keyLocation": f"{BASE}/{key}.txt", "urlList": urls})
    print(f"IndexNow: {len(urls)} url's, status {r.status_code}")


if __name__ == "__main__":
    main()
