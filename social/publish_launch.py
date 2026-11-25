"""Plaatst de vier startposts (eenmalig), in de juiste volgorde: de lanceringspost komt bovenaan.

Draait via de workflow "Startposts plaatsen" (handmatig starten). De afbeeldingen worden eerst met de site
gepubliceerd op /social/launch/, omdat Instagram ze via een openbare URL ophaalt.
"""
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from publish_instagram import publish, BASE  # noqa: E402

LAUNCH = Path(__file__).resolve().parent / "launch"
ORDER = ["04-ek-handbal", "03-nederlanders-wk-darts", "02-wk-darts-schema", "01-lancering"]


def captions():
    text = (LAUNCH / "captions.md").read_text(encoding="utf-8")
    parts = re.split(r"^## ", text, flags=re.M)[1:]
    return {p.split("\n", 1)[0].strip(): p.split("\n", 1)[1].strip() for p in parts}


def main():
    caps = captions()
    for name in ORDER:
        publish(f"{BASE}/social/launch/{name}.jpg", caps[name])
        time.sleep(20)
    print("Startposts geplaatst. Zet '01-lancering' in de app vast bovenaan je profiel.")


if __name__ == "__main__":
    main()
