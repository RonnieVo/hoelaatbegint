"""'De kijk van Ronald': een korte persoonlijke voorbeschouwing per Nederlandse wedstrijd in de komende 7 dagen.

Geschreven door Claude in de stijl van Ronald (eigenaar), op basis van alleen de feiten in events.json.
Regels: geen gokken, odds of uitslagvoorspellingen in cijfers; geen feiten die niet in de data staan
(geen blessures, vorm of standen). Draait één keer per dag; maximaal MAX nieuwe teksten per run.
Uitzetten: variabele AI_OPINION=0.
"""
import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
EVENTS = ROOT / "data" / "events.json"
MAX = int(os.environ.get("AI_OPINION_MAX", "12"))
STYLE = ("Je bent Ronald Voorbergen uit Woerden, oprichter van hoelaatbegint.nl: een nuchtere, enthousiaste "
         "Nederlandse sportliefhebber. Je schrijft kort, in de ik-vorm, met een droge knipoog.")


def main():
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key or os.environ.get("AI_OPINION") == "0":
        print("ai_opinion overgeslagen")
        return
    data = json.loads(EVENTS.read_text(encoding="utf-8"))
    now = datetime.now(timezone.utc)
    horizon = (now + timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
    todo = [e for e in data["events"] if e.get("nl") and e.get("start") and not e.get("opinion")
            and now.strftime("%Y-%m-%dT%H:%M:%SZ") < e["start"] <= horizon]
    todo.sort(key=lambda e: e["start"])
    done = 0
    for e in todo[:MAX]:
        facts = {k: e.get(k) for k in ("title", "sport", "round", "city", "venue", "note", "participants", "tv_detail")}
        prompt = (f"{STYLE}\n\nSchrijf 2 korte zinnen (samen maximaal 45 woorden) als jouw kijk op dit evenement: waarom "
                  "het leuk is om te kijken of waar je naar uitkijkt. Regels: geen gokken, odds of uitslag in cijfers; "
                  "noem GEEN feiten die hieronder niet staan (geen blessures, vorm, standen of spelers die niet genoemd "
                  "worden); geen tijden of data; geen hashtags of emoji. Alleen de twee zinnen teruggeven.\n\n"
                  + json.dumps(facts, ensure_ascii=False))
        r = requests.post("https://api.anthropic.com/v1/messages", timeout=60, headers={
            "x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model": os.environ.get("CLAUDE_MODEL", "claude-sonnet-5-5"), "max_tokens": 200,
                  "messages": [{"role": "user", "content": prompt}]})
        if r.status_code != 200:
            print("fout", r.status_code)
            continue
        text = "".join(b.get("text", "") for b in r.json()["content"] if b.get("type") == "text").strip().strip('"')
        allowed = set(re.findall(r"\d+", json.dumps(facts)))
        if set(re.findall(r"\d+", text)) <= allowed and 20 < len(text) < 400 and not re.search(r"\bodds?\b|wedden|gok", text, re.I):
            e["opinion"] = text
            done += 1
    if done:
        EVENTS.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{done} keer 'de kijk van Ronald' geschreven")


if __name__ == "__main__":
    main()
