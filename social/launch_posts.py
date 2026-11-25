"""Vier startposts voor de lancering van het Instagram-account (eenmalig).

python social/launch_posts.py -> social/launch/*.jpg + captions.md
"""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import render
from render import page, rows, shoot, escape

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(__file__).resolve().parent / "launch"
T = json.loads((ROOT / "data" / "tournaments.json").read_text(encoding="utf-8"))
evs = render.load()

posts = []

# 1. Lancering
inner = ("<div class='big'><b>Hoe laat speelt Nederland?</b> Hoe laat begint het WK darts? Op welke zender is het schaatsen?"
         "<br><br>Wij zoeken het elke dag voor je uit. Elke ochtend om 07:00 het Nederlandse sportprogramma van de dag, "
         "met tijden en zenders.<br><br><b>Volg ons en mis nooit meer een aftrap.</b></div>")
posts.append(("01-lancering", page("Nieuw", "Hoe laat<br>begint het?", inner, list_top=500, foot_left="Darts · schaatsen · Oranje · F1 · handbal"),
              "Hoe laat speelt Nederland? Hoe laat begint het darts? Op welke zender?\n\nVanaf nu zoeken wij het voor je uit. Elke ochtend om 07:00 het Nederlandse sportprogramma van de dag, met tijd en zender.\n\nVolg @hoelaatbegint en zet je meldingen aan.\n\n#sportoptv #hoelaatbegint #wkdarts #oranje #schaatsen #f1"))

# 2. WK darts schema
dart = [e for e in evs if e["tournament"] == "wk-darts" and e["id"] in ("wkd-opening", "wkd-r2", "wkd-r3", "wkd-kf", "wkd-hf", "wkd-finale")]
posts.append(("02-wk-darts-schema", page("11 december – 3 januari", "WK darts<br>schema", rows(dart, True), foot_left="Live op Viaplay"),
              "Het WK darts 2027 begint vrijdag 11 december om 20:00. De finale is zondag 3 januari om 21:00.\n\nSessies elke dag om 13:30 en 20:00, behalve met Kerst (24, 25, 26 december) en op oudejaarsdag.\n\nHet hele schema in je agenda? Link in bio.\n\n#wkdarts #darts #allypally #hoelaatbegint"))

# 3. 17 Nederlanders
players = T["wk-darts"]["players"]
grid = "<div class='grid'>" + "".join(f"<div>{escape(p)}<span>{escape(h)}</span></div>" for p, h in players[:16]) + "</div>"
posts.append(("03-nederlanders-wk-darts", page("WK darts 2027 · voorlopig", "17 Nederlanders<br>op Ally Pally", grid, list_top=450,
                                               foot_left=f"+ {players[16][0]}"),
              "17 Nederlanders op het WK darts 2027 (voorlopige lijst):\n\n" + "\n".join(f"• {p}" for p, _ in players) +
              "\n\nNa de loting op 30 november zie je per speler hoe laat hij speelt. Link in bio.\n\n#wkdarts #darts #vangerwen #gianvanveen #hoelaatbegint"))

# 4. EK handbal
hb = [e for e in evs if e["tournament"] == "ek-handbal-vrouwen" and e.get("home") == "Nederland"]
posts.append(("04-ek-handbal", page("EK handbal vrouwen", "Zo laat spelen<br>de handbalsters", rows(hb, True), foot_left="Live op Ziggo Sport"),
              "De handbalsters spelen het EK in Brno:\n\n" + "\n".join(f"{e['day_label']} {e['time']} · {e['title']} ({e['tv_detail']})" for e in hb) +
              "\n\nBij de beste twee: hoofdronde in Katowice vanaf 10 december.\n\n#handbal #ekhandbal #oranje #hoelaatbegint"))

OUT.mkdir(exist_ok=True)
md = ["# Startposts hoelaatbegint.nl", ""]
for name, html, cap in posts:
    shoot(html, OUT / f"{name}.jpg")
    md += [f"## {name}", "", cap, ""]
(OUT / "captions.md").write_text("\n".join(md), encoding="utf-8")
print(f"{len(posts)} startposts gemaakt in {OUT}")
