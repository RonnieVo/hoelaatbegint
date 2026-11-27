"""Voorbeschouwing per evenement: feitelijk, met bronnen (favorieten, parcours/stadion, wat er op het spel staat).

Vervangt 'De kijk van Ronald' (op verzoek van Ronald, 27-11-2026): geen ik-vorm, geen verzonnen meningen of
sfeerbeelden. Claude zoekt op het web (max. 3 zoekopdrachten) en schrijft alleen wat in de bronnen staat.
Eén keer per evenement, alleen voor evenementen met Nederlanders in de komende 3 dagen, max MAX per run.
Uitzetten: variabele AI_PREVIEW=0.
"""
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
EVENTS = ROOT / "data" / "events.json"
MAX = int(os.environ.get("AI_PREVIEW_MAX", "6"))
sys.path.insert(0, str(ROOT / "pipeline" / "sources"))
from ai_verify import MODEL  # noqa: E402

BANNED = re.compile(r"\b(ik|mij|mijn|me|wij|we|ons|onze)\b|odds|wedden|gokken|bookmaker|koffie|bank|hijg", re.I)
FOCUS = {
    "veldrijden": "de favorieten bij de elitevrouwen en -mannen (wie won hier eerder, wie leidt in de wereldbeker) en het parcours (zand, modder, trappen, kenmerkende stroken)",
    "schaatsen": "welke Nederlanders op welke afstanden rijden, de favorieten en de baan (ijsbaan, hoogteligging, records)",
    "darts": "wie er in deze sessie spelen, met nadruk op de Nederlanders, en wat er op het spel staat",
    "f1": "de stand in het WK, het circuit (lengte, kenmerken) en hoe Max Verstappen en zijn team ervoor staan",
}
DEFAULT_FOCUS = "de vorm en de stand van beide ploegen, eerdere onderlinge duels en wat er op het spel staat"


def ask(key, e):
    facts = {k: e.get(k) for k in ("title", "sport", "round", "start", "city", "venue", "participants")}
    focus = FOCUS.get(e["sport"], DEFAULT_FOCUS)
    prompt = (
        f"Datum vandaag: {datetime.now(timezone.utc):%Y-%m-%d}. Schrijf voor hoelaatbegint.nl een korte, feitelijke "
        f"voorbeschouwing (2 tot 3 zinnen, samen maximaal 70 woorden, Nederlands) op dit evenement:\n"
        f"{json.dumps(facts, ensure_ascii=False)}\n\nBehandel: {focus}.\n"
        "Zoek dit op het web op (betrouwbare sportmedia of de organisator). Regels: schrijf in de derde persoon, "
        "NOOIT in de ik- of wij-vorm; geen meningen, sfeerbeelden of verzonnen details; alleen feiten die in je bronnen "
        "staan; geen odds, gokken of uitslagvoorspellingen; geen aanvangstijden (die staan al op de pagina); "
        "niet negatief over sporters. Kun je het niet met bronnen onderbouwen, geef dan een lege tekst.\n"
        'Antwoord ALLEEN met JSON: {"text": "...", "sources": ["https://...", "https://..."]}'
    )
    r = requests.post("https://api.anthropic.com/v1/messages", timeout=180, headers={
        "x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
        json={"model": MODEL, "max_tokens": 1500,
              "tools": [{"type": "web_search_20250305", "name": "web_search", "max_uses": 3}],
              "messages": [{"role": "user", "content": prompt}]})
    r.raise_for_status()
    text = "".join(b.get("text", "") for b in r.json()["content"] if b.get("type") == "text")
    m = re.search(r"\{[\s\S]*\}", text)
    return json.loads(m.group(0)) if m else {}


def ok(out):
    t = (out.get("text") or "").strip()
    srcs = [s for s in out.get("sources", []) if isinstance(s, str) and s.startswith("http")]
    return t and srcs and 40 < len(t) < 600 and not BANNED.search(t) and not re.search(r"\b\d{1,2}[:.]\d{2}\b", t)


def main():
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key or os.environ.get("AI_PREVIEW") == "0":
        print("ai_preview overgeslagen")
        return
    data = json.loads(EVENTS.read_text(encoding="utf-8"))
    now = datetime.now(timezone.utc)
    lo, hi = now.strftime("%Y-%m-%dT%H:%M:%SZ"), (now + timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%SZ")
    todo = [e for e in data["events"] if e.get("nl") and e.get("start") and "preview" not in e and lo < e["start"] <= hi
            and ":" not in e["title"].split("–")[-1]]  # geen losse F1-sessies (kwalificatie e.d.)
    seen, done = set(), 0
    for e in sorted(todo, key=lambda x: x["start"]):
        group = (e["sport"], e["start"][:10], e.get("city"))  # één tekst per wedstrijddag/locatie (bv. vrouwen + mannen)
        if done >= MAX or group in seen:
            continue
        seen.add(group)
        try:
            out = ask(key, e)
        except Exception as exc:
            print("fout", type(exc).__name__)
            continue
        if not ok(out):
            e["preview"] = ""  # niet opnieuw proberen
            continue
        for x in data["events"]:
            if (x["sport"], (x.get("start") or "")[:10], x.get("city")) == group and "preview" not in x:
                x["preview"], x["preview_sources"] = out["text"].strip(), out["sources"][:3]
        done += 1
    EVENTS.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{done} voorbeschouwing(en) geschreven")


if __name__ == "__main__":
    main()
