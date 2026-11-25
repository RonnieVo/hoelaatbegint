"""Maandagrapport + zelflerende titels.

1. Haalt bezoekers (Plausible) en zoekdata (Google Search Console) van de afgelopen 7 dagen op.
2. Zoekt pagina's met veel vertoningen maar een lage CTR, laat Claude een betere titel schrijven
   en zet die in data/title_overrides.json (build.py gebruikt die automatisch).
   Na 14 dagen wordt vergeleken: werd de CTR niet beter, dan gaat de oude titel terug.
3. Mailt alles in één overzicht.

Omgevingsvariabelen: PLAUSIBLE_API_KEY, GSC_SERVICE_ACCOUNT_JSON (inhoud van het sleutelbestand),
ANTHROPIC_API_KEY, plus de SMTP-instellingen uit notify.py.
"""
import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from notify import send_mail  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CFG = json.loads((ROOT / "site" / "config.json").read_text())
SITE = CFG["base_url"].rstrip("/")
OVR = ROOT / "data" / "title_overrides.json"


def plausible():
    key = os.environ.get("PLAUSIBLE_API_KEY")
    if not key:
        return None
    r = requests.post("https://plausible.io/api/v2/query", timeout=30, headers={"Authorization": f"Bearer {key}"},
                      json={"site_id": CFG["plausible_domain"], "metrics": ["visitors", "pageviews"], "date_range": "7d"})
    r.raise_for_status()
    v, pv = r.json()["results"][0]["metrics"]
    return {"bezoekers": v, "paginaweergaven": pv}


def gsc_pages():
    raw = os.environ.get("GSC_SERVICE_ACCOUNT_JSON")
    if not raw:
        return []
    from google.oauth2 import service_account
    from google.auth.transport.requests import AuthorizedSession
    creds = service_account.Credentials.from_service_account_info(
        json.loads(raw), scopes=["https://www.googleapis.com/auth/webmasters.readonly"])
    s = AuthorizedSession(creds)
    end, start = date.today() - timedelta(days=2), date.today() - timedelta(days=9)
    url = f"https://www.googleapis.com/webmasters/v3/sites/{requests.utils.quote('sc-domain:' + SITE.split('://')[1], safe='')}/searchAnalytics/query"
    r = s.post(url, json={"startDate": str(start), "endDate": str(end), "dimensions": ["page"], "rowLimit": 200})
    r.raise_for_status()
    return r.json().get("rows", [])


def new_title(path, old):
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return None
    r = requests.post("https://api.anthropic.com/v1/messages", timeout=60, headers={
        "x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
        json={"model": os.environ.get("CLAUDE_MODEL", "claude-sonnet-5-5"), "max_tokens": 100, "messages": [{"role": "user", "content":
              f"Deze pagina ({path}) wordt vaak getoond in Google maar weinig aangeklikt. Huidige titel: '{old}'. "
              "Schrijf één betere Nederlandse paginatitel van maximaal 60 tekens die de zoekvraag 'hoe laat' direct "
              "beantwoordt en eindigt op ' | hoelaatbegint.nl'. Alleen de titel teruggeven."}]})
    r.raise_for_status()
    t = "".join(b.get("text", "") for b in r.json()["content"] if b.get("type") == "text").strip().strip('"')
    return t if 15 < len(t) <= 80 else None


def main():
    lines = ["Goedemorgen,", "", "Zo ging het afgelopen week met hoelaatbegint.nl:", ""]
    p = plausible()
    if p:
        lines.append(f"Bezoekers: {p['bezoekers']:,} · paginaweergaven: {p['paginaweergaven']:,}".replace(",", "."))
    rows = gsc_pages()
    if rows:
        clicks = sum(r["clicks"] for r in rows)
        impr = sum(r["impressions"] for r in rows)
        lines += [f"Google: {clicks:,} klikken uit {impr:,} vertoningen".replace(",", "."), "", "Top 5 pagina's:"]
        for r in sorted(rows, key=lambda r: -r["clicks"])[:5]:
            lines.append(f"  {r['clicks']:>5} klikken · {r['keys'][0].replace(SITE, '')}")
    overrides = json.loads(OVR.read_text()) if OVR.exists() else {}
    tested = 0
    for r in sorted(rows, key=lambda r: -r["impressions"]):
        path = r["keys"][0].replace(SITE, "")
        if r["impressions"] < 500 or r["ctr"] > 0.03 or tested >= 3:
            continue
        cur = overrides.get(path)
        if cur and (date.today() - date.fromisoformat(cur["since"])).days < 14:
            continue
        if cur and r["ctr"] <= cur.get("ctr_before", 0):
            overrides.pop(path)  # nieuwe titel werkte niet: terug naar het origineel
            lines.append(f"Titeltest teruggedraaid: {path}")
            continue
        html = (ROOT / "dist" / path.strip("/") / "index.html")
        old = html.read_text().split("<title>")[1].split("</title>")[0] if html.exists() else path
        t = new_title(path, old)
        if t:
            overrides[path] = {"title": t, "since": str(date.today()), "ctr_before": r["ctr"]}
            lines.append(f"Nieuwe titeltest op {path}: '{t}' (CTR was {r['ctr']:.1%})")
            tested += 1
    OVR.write_text(json.dumps(overrides, ensure_ascii=False, indent=1))
    lines += ["", "Je hoeft niets te doen. Fouten of conflicten had je al per mail gekregen.", "", "Groet, de pipeline"]
    send_mail("hoelaatbegint.nl: weekrapport", "\n".join(lines))


if __name__ == "__main__":
    main()
