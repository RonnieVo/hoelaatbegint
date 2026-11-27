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
NAMES = {"Atleti": "Atlético Madrid", "Club Atlético de Madrid": "Atlético Madrid", "AFC Ajax": "Ajax", "Ajax": "Ajax", "PSV": "PSV", "PSV Eindhoven": "PSV", "Feyenoord": "Feyenoord",
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
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    out, seen = [], set()
    for team_id, club in TEAMS.items():
        r = requests.get(f"https://api.football-data.org/v4/teams/{team_id}/matches",
                         params={"status": "SCHEDULED,TIMED,POSTPONED", "dateFrom": now.strftime("%Y-%m-%d"),
                                 "dateTo": (now + timedelta(days=60)).strftime("%Y-%m-%d")},
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
            ev = dict(id=f"fd-{m['id']}", sport="clubs", tournament=clubs[0] if clubs else club, clubs=clubs or [club],
                      nl=True, title=f"{home} – {away}", home=home, away=away, round=comp, broadcaster=tv, matchday=m.get("matchday"),
                      status=STATUS.get(m["status"], "gepland"), page=f"{slug(home)}-{slug(away)}-{day}",
                      source="https://www.football-data.org")
            if m["status"] == "SCHEDULED":  # aanvangstijd nog niet vastgesteld: alleen de datum
                ev.update(date=day, time_known=False, time_note="Aanvangstijd volgt")
            else:
                ev["start"] = m["utcDate"].replace("+00:00", "Z")
            out.append(ev)
    # Volledig Eredivisie-programma (alle clubs) voor de pagina /eredivisie/
    r = requests.get("https://api.football-data.org/v4/competitions/DED/matches",
                     params={"dateFrom": now.strftime("%Y-%m-%d"), "dateTo": (now + timedelta(days=45)).strftime("%Y-%m-%d")},
                     headers={"X-Auth-Token": key}, timeout=20)
    if r.status_code == 200:
        for m in r.json().get("matches", []):
            if m["id"] in seen:
                continue
            seen.add(m["id"])
            home, away = name(m["homeTeam"]), name(m["awayTeam"])
            day = m["utcDate"][:10]
            clubs = [c for c in ("ajax", "feyenoord", "psv") if c in slug(home + " " + away)]
            ev = dict(id=f"fd-{m['id']}", sport="clubs", tournament=clubs[0] if clubs else "eredivisie", clubs=clubs,
                      nl=bool(clubs), title=f"{home} – {away}", home=home, away=away, round="Eredivisie", matchday=m.get("matchday"),
                      broadcaster="espn", status=STATUS.get(m["status"], "gepland"), source="https://www.football-data.org")
            if clubs:
                ev["page"] = f"{slug(home)}-{slug(away)}-{day}"
            if m["status"] == "SCHEDULED":
                ev.update(date=day, time_known=False, time_note="Aanvangstijd volgt")
            else:
                ev["start"] = m["utcDate"].replace("+00:00", "Z")
            out.append(ev)
    return out
