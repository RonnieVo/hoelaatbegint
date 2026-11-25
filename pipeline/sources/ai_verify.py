"""AI-controle: Claude zoekt officiële bronnen en levert strikte JSON met bevestigde tijden.

Voor sporten zonder goede API (darts, handbal, hockey, schaatsen, veldrijden, Leeuwinnen).
Sleutel: ANTHROPIC_API_KEY. Zuinige stand (standaard):
- elk toernooi met een evenement in de komende 14 dagen: 1 controle per dag (06:00 UTC);
- toernooien met een Nederlandse wedstrijd vandaag of morgen: extra controle om 16:00 UTC;
- toernooien zonder evenementen binnen 14 dagen: 1 keer per week (maandag).
Kosten bij deze stand: grofweg 5 tot 8 controles per dag. Zet AI_VERIFY_MODE=intensief voor 5 keer per dag.

Regels voor het model:
- alleen tijden die op minimaal één officiële bron staan (organisator, bond, rechthebbende zender);
- per evenement de bron-URL's meegeven; met twee onafhankelijke bronnen geldt het als bevestigd;
- nooit gokken: onbekende tijd = alleen datum.
"""
import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

from . import Skip

MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-5-5")
INTENSIVE_HOURS = {5, 9, 13, 17, 21}  # UTC, alleen bij AI_VERIFY_MODE=intensief
MAX_SEARCHES = int(os.environ.get("AI_MAX_SEARCHES", "4"))
ROOT = Path(__file__).resolve().parents[2]

TASKS = {
    "wk-darts": "PDC WK darts 2027 (Alexandra Palace, 11 dec 2026 – 3 jan 2027). Na de loting: alle wedstrijden met een Nederlandse speler, met sessie, dag, starttijd van de sessie en tegenstander. Bronnen: pdc.tv, viaplay.nl, dartsnieuws.com.",
    "ek-handbal-vrouwen": "EK handbal vrouwen 2026, wedstrijden van Nederland (poule D in Brno, daarna hoofdronde Katowice). Bronnen: eurohandball.com, handbal.nl, ziggo.nl.",
    "hockey": "FIH Pro League 2026-27, alle wedstrijden van de Nederlandse mannen en vrouwen met aanvangstijd. Bronnen: fih.hockey, knhb.nl.",
    "schaatsen": "Langebaanschaatsen 2026-27: wereldbekers, NK en EK, met starttijden per dag. Bronnen: isu.org, knsb.nl, schaatsen.nl, nos.nl.",
    "veldrijden": "UCI Wereldbeker veldrijden 2026-27: starttijden van de elitewedstrijden (mannen en vrouwen). Bronnen: uci.org, sporza.be, nos.nl.",
    "nederlands-elftal": "Oranje (mannen en vrouwen): eerstvolgende wedstrijden, lotingen en zender. Bronnen: onsoranje.nl, uefa.com, nos.nl.",
}

ALLOWED_SPORTS = {"darts", "handbal", "hockey", "schaatsen", "veldrijden", "voetbal", "f1", "clubs"}
TASK_SPORT = {"wk-darts": "darts", "ek-handbal-vrouwen": "handbal", "hockey": "hockey", "schaatsen": "schaatsen",
              "veldrijden": "veldrijden", "nederlands-elftal": "voetbal"}

SCHEMA = """Geef als antwoord ALLEEN één codeblok ```json ... ``` met een JSON-array, zonder uitleg of bronvermelding erbuiten.
Gebruik in tekstwaarden geen dubbele aanhalingstekens. Elk element:
{"id": "<stabiele id, hergebruik bestaande id als het hetzelfde evenement is>",
 "sport": "darts|handbal|hockey|schaatsen|veldrijden|voetbal", "tournament": "<slug>",
 "title": "<Nederlandse titel, bijv. 'Nederland – Kroatië' of 'Michael van Gerwen – Luke Woodhouse'>",
 "start": "<ISO-8601 in UTC met Z, alleen als de tijd officieel bevestigd is>",
 "date": "<YYYY-MM-DD als de tijd nog niet bekend is>", "end_date": "<optioneel>",
 "round": "...", "city": "...", "venue": "...", "participants": ["<Nederlandse deelnemers>"],
 "home": "...", "away": "...", "broadcaster": "viaplay|ziggo|nos|espn",
 "nl": true, "sources": ["<url>", "<url>"]}"""


def due(known, now):
    """Bepaalt per toernooi of er nu een controle moet draaien (zuinige stand)."""
    if os.environ.get("AI_VERIFY_FORCE"):
        return True
    if now.minute >= 15:  # één keer per uur-slot, niet elke 15 minuten
        return False
    if os.environ.get("AI_VERIFY_MODE") == "intensief":
        return now.hour in INTENSIVE_HOURS
    def day(e):
        return (e.get("start") or e.get("date") or "")[:10]
    soon = [e for e in known if day(e) <= (now + timedelta(days=14)).strftime("%Y-%m-%d")]
    hot = [e for e in known if e.get("nl") and day(e) in (now.strftime("%Y-%m-%d"), (now + timedelta(days=1)).strftime("%Y-%m-%d"))]
    if now.hour == 6 and (soon or now.weekday() == 0):
        return True
    return now.hour == 16 and bool(hot)


def ask(task, known):
    key = os.environ.get("ANTHROPIC_API_KEY")
    prompt = (f"Je controleert sportdata voor hoelaatbegint.nl. Datum vandaag: {datetime.now(timezone.utc):%Y-%m-%d}.\n"
              f"Opdracht: {task}\n\nWat we nu hebben (JSON):\n{json.dumps(known, ensure_ascii=False)[:12000]}\n\n"
              f"Zoek op het web naar de actuele, officiële informatie. Neem bestaande evenementen over als ze kloppen "
              f"(met dezelfde id), corrigeer ze als een officiële bron iets anders zegt, en voeg nieuwe toe.\n{SCHEMA}")
    r = requests.post("https://api.anthropic.com/v1/messages", timeout=300, headers={
        "x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
        json={"model": MODEL, "max_tokens": 8000,
              "tools": [{"type": "web_search_20250305", "name": "web_search", "max_uses": MAX_SEARCHES}],
              "messages": [{"role": "user", "content": prompt}]})
    r.raise_for_status()
    text = "".join(b.get("text", "") for b in r.json()["content"] if b.get("type") == "text")
    return parse_array(text)


def parse_array(text):
    """Haalt de JSON-array uit het antwoord, ook als er tekst of citaties omheen staan."""
    fenced = re.findall(r"```(?:json)?\s*([\s\S]*?)```", text)
    candidates = fenced + [text]
    dec = json.JSONDecoder()
    for c in candidates:
        for i, ch in enumerate(c):
            if ch != "[":
                continue
            try:
                val, _ = dec.raw_decode(c[i:])
            except ValueError:
                continue
            if isinstance(val, list) and (not val or isinstance(val[0], dict)):
                return val
    raise ValueError("geen geldige JSON-array in het AI-antwoord")


def valid(e):
    if not e.get("id") or not e.get("title") or not (e.get("start") or e.get("date")):
        return False
    if e.get("start") and not re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d(:\d\d)?Z", e["start"]):
        return False
    return bool(e.get("sources"))


def fetch(existing):
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise Skip("geen ANTHROPIC_API_KEY")
    now = datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")
    out, ran = [], 0
    for slug, task in TASKS.items():
        known = [e for e in existing if e.get("tournament") == slug and (e.get("end_date") or e.get("date") or e.get("start", ""))[:10] >= today]
        if not due(known, now):
            continue
        ran += 1
        try:
            answer = ask(task, known)
        except Exception as ex:  # één toernooi dat faalt mag de rest niet stoppen
            print(f"  ai {slug}: overgeslagen ({ex!r})")
            continue
        print(f"  ai {slug}: {len(answer)} evenementen")
        for e in answer:
            if valid(e):
                e["tournament"] = slug  # AI mag geen eigen paginanamen verzinnen
                if e.get("sport") not in ALLOWED_SPORTS:
                    e["sport"] = TASK_SPORT[slug]
                e["source"] = e["sources"][0]
                out.append(e)
    if not ran:
        raise Skip("geen controle gepland op dit moment")
    return out
