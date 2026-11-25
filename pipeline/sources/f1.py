"""Formule 1 via de Jolpica F1 API (open, opvolger van Ergast, geen sleutel nodig).

Levert per Grand Prix: de race, en (indien bekend) kwalificatie en sprint met exacte tijden.
"""
from datetime import datetime, timezone

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


def fetch(existing):
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
