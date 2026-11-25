"""Clubvoetbal via football-data.org (gratis laag: Eredivisie en Champions League, actuele seizoenen).

Sleutel: FOOTBALL_DATA_KEY (gratis aan te vragen op football-data.org). Limiet gratis laag: 10 verzoeken per minuut.
Europa League, Conference League en KNVB-beker zitten niet in de gratis laag; die vult de AI-controle aan.
Team-ID's controleren met: GET https://api.football-data.org/v4/competitions/DED/teams
"""
import os
import re
import unicodedata

import requests

from . import Skip

TEAMS = {  # football-data.org team-id -> club-slug
    int(os.environ.get("FD_TEAM_AJAX", "678")): "ajax",
    int(os.environ.get("FD_TEAM_PSV", "674")): "psv",
    int(os.environ.get("FD_TEAM_FEYENOORD", "675")): "feyenoord",
}
NAMES = {"AFC Ajax": "Ajax", "Ajax": "Ajax", "PSV": "PSV", "PSV Eindhoven": "PSV", "Feyenoord": "Feyenoord",
         "Feyenoord Rotterdam": "Feyenoord", "AZ": "AZ", "FC Utrecht": "FC Utrecht", "Utrecht": "FC Utrecht",
         "FC Twente": "FC Twente", "Twente": "FC Twente", "Go Ahead Eagles": "Go Ahead Eagles", "Willem II": "Willem II",
         "FC Groningen": "FC Groningen", "Groningen": "FC Groningen", "PEC Zwolle": "PEC Zwolle", "Telstar": "Telstar",
         "SC Cambuur": "Cambuur", "Cambuur": "Cambuur", "NEC": "NEC", "Sparta Rotterdam": "Sparta Rotterdam",
         "Excelsior": "Excelsior", "Heerenveen": "SC Heerenveen", "SC Heerenveen": "SC Heerenveen",
         "Fortuna Sittard": "Fortuna Sittard", "ADO Den Haag": "ADO Den Haag"}
COMP = {"DED": ("Eredivisie", "espn"), "CL": ("Champions League", "ziggo")}
STATUS = {"POSTPONED": "verplaatst", "CANCELLED": "afgelast", "FINISHED": "afgelopen", "IN_PLAY": "bezig", "PAUSED": "bezig"}


def slug(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def name(team):
    return NAMES.get(team.get("shortName")) or NAMES.get(team.get("name")) or team.get("shortName") or team.get("name")


def fetch(existing):
    key = os.environ.get("FOOTBALL_DATA_KEY")
    if not key:
        raise Skip("geen FOOTBALL_DATA_KEY")
    out, seen = [], set()
    for team_id, club in TEAMS.items():
        r = requests.get(f"https://api.football-data.org/v4/teams/{team_id}/matches",
                         params={"status": "SCHEDULED,TIMED,POSTPONED", "limit": 10},
                         headers={"X-Auth-Token": key}, timeout=20)
        if r.status_code == 429:
            break  # limiet bereikt; volgende run verder
        r.raise_for_status()
        for m in r.json().get("matches", []):
            if m["id"] in seen:
                continue
            seen.add(m["id"])
            home, away = name(m["homeTeam"]), name(m["awayTeam"])
            comp, tv = COMP.get(m["competition"].get("code"), (m["competition"].get("name"), None))
            day = m["utcDate"][:10]
            clubs = [c for c in ("ajax", "feyenoord", "psv") if c in slug(home + " " + away)]
            out.append(dict(id=f"fd-{m['id']}", sport="clubs", tournament=clubs[0] if clubs else club, clubs=clubs or [club],
                            nl=True, title=f"{home} – {away}", home=home, away=away,
                            start=m["utcDate"].replace("+00:00", "Z"), round=comp, broadcaster=tv,
                            status=STATUS.get(m["status"], "gepland"), page=f"{slug(home)}-{slug(away)}-{day}",
                            source="https://www.football-data.org"))
    return out
