"""Formule 1 via de Jolpica F1 API (open, opvolger van Ergast, geen sleutel nodig).

Levert per Grand Prix: de race, en (indien bekend) kwalificatie en sprint met exacte tijden.
"""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

from . import Skip  # noqa: F401  (gedeelde interface)

API = "https://api.jolpi.ca/ergast/f1/{season}.json?limit=100"
NAMES = {  # Engelse namen -> Nederlandse paginatitels
    "Bahrain": "Bahrein", "Saudi Arabia": "Saudi-Arabië", "Australia": "Australië", "Japan": "Japan", "China": "China",
    "USA": "Verenigde Staten", "Canada": "Canada", "Monaco": "Monaco", "Spain": "Spanje", "Austria": "Oostenrijk",
    "UK": "Groot-Brittannië", "Belgium": "België", "Hungary": "Hongarije", "Netherlands": "Nederland", "Italy": "Italië",
    "Azerbaijan": "Azerbeidzjan", "Singapore": "Singapore", "Mexico": "Mexico", "Brazil": "Brazilië", "Qatar": "Qatar",
    "UAE": "Abu Dhabi", "Portugal": "Portugal", "Turkey": "Turkije",
}


def _iso(d, t):
    if not t:
        return None
    return datetime.fromisoformat(f"{d}T{t.replace('Z', '+00:00')}").astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


STANDINGS = "https://api.jolpi.ca/ergast/f1/current/{kind}Standings.json?limit=100"
STANDINGS_FILE = Path(__file__).resolve().parents[2] / "data" / "f1_standings.json"


def standings():
    """WK-stand coureurs en constructeurs naar data/f1_standings.json (hoogstens elke 3 uur opnieuw)."""
    try:
        old = json.loads(STANDINGS_FILE.read_text()) if STANDINGS_FILE.exists() else {}
        if old.get("fetched_at") and datetime.now(timezone.utc) - datetime.fromisoformat(old["fetched_at"]) < timedelta(hours=3):
            return
        out = {"fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "source": "https://api.jolpi.ca/ergast/f1/current/"}
        for kind in ("driver", "constructor"):
            r = requests.get(STANDINGS.format(kind=kind), timeout=20)
            r.raise_for_status()
            lst = r.json()["MRData"]["StandingsTable"]["StandingsLists"]
            if not lst:
                return
            st = lst[0]
            out["season"], out["round"] = int(st["season"]), int(st["round"])
            rows = []
            for x in st[f"{'Driver' if kind == 'driver' else 'Constructor'}Standings"]:
                row = {"pos": int(x.get("position") or x.get("positionText") or 0), "points": float(x["points"]), "wins": int(x["wins"])}
                if kind == "driver":
                    d = x["Driver"]
                    row.update(name=f"{d['givenName']} {d['familyName']}", nationality=d.get("nationality", ""),
                               team=", ".join(c["name"] for c in x.get("Constructors", [])))
                else:
                    row.update(name=x["Constructor"]["name"], nationality=x["Constructor"].get("nationality", ""))
                rows.append(row)
            out[f"{kind}s"] = rows
        if out.get("drivers") and out.get("constructors"):
            STANDINGS_FILE.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    except Exception as exc:  # de stand mag het ophalen van het programma nooit blokkeren
        print(f"F1-stand overgeslagen: {exc}")


def fetch(existing):
    standings()
    year = datetime.now(timezone.utc).year
    out = []
    for season in (year, year + 1):
        r = requests.get(API.format(season=season), timeout=20)
        if r.status_code != 200:
            continue
        races = r.json()["MRData"]["RaceTable"]["Races"]
        for race in races:
            n = int(race["round"])
            country = race["Circuit"]["Location"]["country"]
            locality = race["Circuit"]["Location"]["locality"]
            gp = NAMES.get(country, country)
            if country == "USA" and locality in ("Miami", "Las Vegas"):
                gp = locality
            title = f"GP {gp}" if gp in ("Miami", "Las Vegas") else f"GP van {gp}"
            base = dict(sport="f1", tournament="formule-1", city=locality, venue=race["Circuit"]["circuitName"],
                        broadcaster="viaplay", nl=True, source=race.get("url") or API.format(season=season))
            start = _iso(race["date"], race.get("time"))
            ev = dict(base, id=f"f1-{season}-{n:02d}", title=title, round=f"Race {n} van {len(races)}")
            if start:
                ev["start"] = start
            else:
                ev.update(date=race["date"], time_known=False)
            out.append(ev)
            for key, label in (("Qualifying", "kwalificatie"), ("Sprint", "sprintrace")):
                s = race.get(key)
                if s and s.get("time"):
                    out.append(dict(base, id=f"f1-{season}-{n:02d}-{label}", title=f"{title}: {label}",
                                    round=f"Race {n}, {label}", start=_iso(s["date"], s["time"])))
    return out
