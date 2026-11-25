"""Stuurt 30 minuten voor elke Nederlandse wedstrijd een pushmelding via OneSignal.

Draait mee in elke 15-minutenrun. Alleen abonnees met de tag van die sport (bijv. 'darts') krijgen hem.
Omgevingsvariabelen: ONESIGNAL_APP_ID, ONESIGNAL_API_KEY.
"""
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "data" / "pipeline_state.json"
BASE = json.loads((ROOT / "site" / "config.json").read_text())["base_url"].rstrip("/")


def main():
    app, key = os.environ.get("ONESIGNAL_APP_ID"), os.environ.get("ONESIGNAL_API_KEY")
    if not (app and key):
        print("push overgeslagen (OneSignal niet ingesteld)")
        return
    now = datetime.now(timezone.utc)
    state = json.loads(STATE.read_text()) if STATE.exists() else {"mailed": []}
    sent = set(state.get("pushed", []))
    for e in json.loads((ROOT / "data" / "events.json").read_text(encoding="utf-8"))["events"]:
        if not (e.get("nl") and e.get("start")) or e["id"] in sent:
            continue
        start = datetime.fromisoformat(e["start"].replace("Z", "+00:00"))
        if timedelta(minutes=20) <= start - now <= timedelta(minutes=40):
            t = start.astimezone(ZoneInfo("Europe/Amsterdam")).strftime("%H:%M")
            url = f"{BASE}/wedstrijd/{e['page']}/" if e.get("page") else BASE + "/vandaag/"
            r = requests.post("https://api.onesignal.com/notifications", timeout=20,
                              headers={"Authorization": f"Key {key}", "Content-Type": "application/json"},
                              json={"app_id": app, "target_channel": "push", "url": url,
                                    "filters": [{"field": "tag", "key": e["sport"], "relation": "=", "value": "1"}],
                                    "headings": {"nl": "Over 30 minuten", "en": "In 30 minutes"},
                                    "contents": {"nl": f"{e['title']} begint om {t}", "en": f"{e['title']} starts at {t}"}})
            print("push", e["id"], r.status_code)
            sent.add(e["id"])
    state["pushed"] = sorted(sent)[-1000:]
    STATE.write_text(json.dumps(state))


if __name__ == "__main__":
    main()
