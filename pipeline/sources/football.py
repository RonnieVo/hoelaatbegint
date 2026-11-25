"""Voetbal via API-Football (api-sports.io). Sleutel: omgevingsvariabele API_FOOTBALL_KEY.

Volgt de teams in TEAMS (Oranje mannen en vrouwen; clubs toevoegen in fase 3).
Team-ID's controleren met: GET /teams?search=Netherlands
"""
import os

import requests

from . import Skip

API = "https://v3.football.api-sports.io/fixtures"
TEAMS = {  # team-id -> (sport, paginanaam / tournament). ID's controleren met GET /teams?search=<naam>
    int(os.environ.get("AF_TEAM_NL_MEN", "1118")): ("voetbal", "nederlands-elftal"),
    int(os.environ.get("AF_TEAM_AJAX", "194")): ("clubs", "ajax"),
    int(os.environ.get("AF_TEAM_FEYENOORD", "209")): ("clubs", "feyenoord"),
    int(os.environ.get("AF_TEAM_PSV", "197")): ("clubs", "psv"),
}
if os.environ.get("AF_TEAM_NL_WOMEN"):
    TEAMS[int(os.environ["AF_TEAM_NL_WOMEN"])] = ("voetbal", "nederlands-elftal")

NL_NAMES = {"Netherlands": "Nederland", "Germany": "Duitsland", "Belgium": "België", "France": "Frankrijk", "Spain": "Spanje",
            "England": "Engeland", "Italy": "Italië", "Portugal": "Portugal", "Croatia": "Kroatië", "Austria": "Oostenrijk",
            "Poland": "Polen", "Czech Republic": "Tsjechië", "Denmark": "Denemarken", "Sweden": "Zweden", "Norway": "Noorwegen",
            "Switzerland": "Zwitserland", "Scotland": "Schotland", "Wales": "Wales", "Ireland": "Ierland", "Turkey": "Turkije",
            "Hungary": "Hongarije", "Greece": "Griekenland", "Serbia": "Servië", "Romania": "Roemenië"}
STATUS = {"PST": "verplaatst", "CANC": "afgelast", "ABD": "afgelast", "FT": "afgelopen", "AET": "afgelopen", "PEN": "afgelopen"}
TV = {"nederlands-elftal": "nos"}  # Oranje-interlands: NOS. De AI-controle checkt dit per seizoen.
LEAGUE_TV = {88: "espn", 2: "ziggo", 3: "ziggo", 848: "ziggo"}  # Eredivisie -> ESPN; CL/EL/Conference League -> Ziggo Sport


def nl(name):
    return NL_NAMES.get(name, name)


def slug(s):
    import re, unicodedata
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def fetch(existing):
    from datetime import datetime, timezone
    key = os.environ.get("API_FOOTBALL_KEY")
    if not key:
        raise Skip("geen API_FOOTBALL_KEY")
    now = datetime.now(timezone.utc)
    if not os.environ.get("AF_FORCE") and not (now.minute < 15 and now.hour % 2 == 0):
        raise Skip("alleen elke 2 uur (gratis laag: 100 verzoeken per dag)")
    out, seen = [], set()
    for team_id, (sport, tournament) in TEAMS.items():
        from datetime import timedelta
        season = now.year if (sport == "voetbal" or now.month >= 7) else now.year - 1
        params = {"team": team_id, "season": season, "from": now.strftime("%Y-%m-%d"),
                  "to": (now + timedelta(days=45)).strftime("%Y-%m-%d"), "timezone": "UTC"}
        r = requests.get(API, params=params, headers={"x-apisports-key": key}, timeout=20)
        r.raise_for_status()
        body = r.json()
        if body.get("errors"):
            if "plan" in body["errors"]:
                raise Skip("gratis plan geeft geen actuele seizoenen; football-data.org wordt gebruikt")
            raise RuntimeError(f"API-Football weigert: {body['errors']}")
        for fx in body.get("response", []):
            f, t, lg = fx["fixture"], fx["teams"], fx["league"]
            if f["id"] in seen:  # bijv. Ajax – PSV: één evenement
                continue
            seen.add(f["id"])
            home, away = nl(t["home"]["name"]), nl(t["away"]["name"])
            day = f["date"][:10]
            ev = dict(id=f"af-{f['id']}", sport=sport, tournament=tournament, nl=True,
                      title=f"{home} – {away}", home=home, away=away,
                      start=f["date"].replace("+00:00", "Z") if f["date"].endswith("+00:00") else f["date"],
                      round=f"{lg['name']} · {lg.get('round', '')}".strip(" ·"),
                      venue=(f.get("venue") or {}).get("name"), city=(f.get("venue") or {}).get("city"),
                      broadcaster=TV.get(tournament) or LEAGUE_TV.get(lg.get("id")), status=STATUS.get(f["status"]["short"], "gepland"),
                      page=f"{slug(home)}-{slug(away)}-{day}", source="https://www.api-football.com")
            if sport == "clubs":
                ev["clubs"] = [c for c in ("ajax", "feyenoord", "psv") if c in (slug(t["home"]["name"]) + slug(t["away"]["name"]))]
            if f["status"]["short"] in ("FT", "AET", "PEN"):
                ev["result"] = f"{fx['goals']['home']}-{fx['goals']['away']}"
            out.append(ev)
    return out
