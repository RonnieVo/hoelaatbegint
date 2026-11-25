"""Schrijft per Nederlandse wedstrijd een korte, unieke inleiding (2-3 zinnen) met Claude.

Veiligheidsregel: de tekst mag alleen getallen bevatten die ook in de feiten staan. Zo niet, dan
wordt de tekst weggegooid en blijft het sjabloon staan. Draait één keer per dag (zie update.yml).
"""
import json
import os
import re
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
EVENTS = ROOT / "data" / "events.json"


def main():
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key or os.environ.get("AI_WRITE") != "1":  # standaard uit in de goedkope teststand
        print("ai_write overgeslagen (uit of geen sleutel)")
        return
    data = json.loads(EVENTS.read_text(encoding="utf-8"))
    done = 0
    for e in data["events"]:
        if not (e.get("nl") and e.get("start") and (e.get("page") or " – " in e["title"])) or e.get("ai_intro"):
            continue
        facts = {k: e.get(k) for k in ("title", "start", "round", "city", "venue", "note", "participants", "home", "away")}
        prompt = ("Schrijf 2 of 3 korte Nederlandse zinnen als inleiding op een pagina over deze wedstrijd. Feitelijk, "
                  "geen superlatieven, geen voorspellingen, geen gokken of odds, geen tijden (die staan al op de pagina). "
                  "Gebruik ALLEEN deze feiten:\n" + json.dumps(facts, ensure_ascii=False))
        r = requests.post("https://api.anthropic.com/v1/messages", timeout=60, headers={
            "x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model": os.environ.get("CLAUDE_MODEL", "claude-sonnet-5-5"), "max_tokens": 300,
                  "messages": [{"role": "user", "content": prompt}]})
        if r.status_code != 200:
            continue
        text = "".join(b.get("text", "") for b in r.json()["content"] if b.get("type") == "text").strip()
        allowed = set(re.findall(r"\d+", json.dumps(facts)))
        if set(re.findall(r"\d+", text)) <= allowed and 40 < len(text) < 600:
            e["ai_intro"] = text
            done += 1
        if done >= 20:  # kosten begrenzen per run
            break
    if done:
        EVENTS.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{done} inleidingen geschreven")


if __name__ == "__main__":
    main()
