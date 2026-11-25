"""Startdata voor hoelaatbegint.nl.

Eenmalig gebruikt om data/events.json te vullen met bevestigde evenementen
(stand 25 november 2026). Daarna houdt de pipeline (pipeline/run.py) het bestand
automatisch bij. Tijden worden hier in Nederlandse tijd ingevoerd en als UTC opgeslagen.
"""
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

NL = ZoneInfo("Europe/Amsterdam")
CHECKED = "2026-11-25T15:30:00Z"


def utc(local: str) -> str:
    """'2026-12-03 20:30' (NL-tijd) -> '2026-12-03T19:30:00Z'"""
    dt = datetime.strptime(local, "%Y-%m-%d %H:%M").replace(tzinfo=NL)
    return dt.astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%dT%H:%M:%SZ")


SRC = {
    "darts": "https://wkwedstrijdschema.nl/darts/wk-2027-schema",
    "darts_field": "https://dartsking.nl/pdc/wk-darts/",
    "hand": "https://www.ziggo.nl/entertainment/sport/handbal/ek-handbal/kijken",
    "hand_ehf": "https://ehfec.eurohandball.com/news/en/ehf-confirms-throw-off-times-for-women-s-ehf-euro-2026/",
    "oranje": "https://www.voetbalnieuws.nl/nieuws/2159736/wanneer-speelt-oranje-weer-programma-nederland-in-2027.html",
    "loting": "https://www.bet-experts.nl/nieuws/loting-ek-2028-kwalificatie-potindeling-oranje",
    "f1_ad": "https://www.ziggo.nl/entertainment/sport/formule-1/f1-grand-prix-abu-dhabi",
    "f1_27": "https://sporza.be/nl/2026/09/16/met-een-sprintrace-in-monaco-en-spa-op-25-juli-dit-is-de-f1-kalender-voor-2027~1789550978381/",
    "hockey": "https://www.hockey.org.au/news/kookaburras-and-hockeyroos-discover-2026-27-fih-pro-league-venues-and-dates",
    "knsb": "https://knsb.nl/documents/1171/Wedstrijdkalender_Langebaan_versie_160626.pdf",
    "cx": "https://sporza.be/nl/2026/01/30/met-tsjechische-opener-bij-kunstlicht-op-oude-mijnsite-ontdek-de-wereldbeker-kalender-veldrijden-van-volgend-seizoen~1769798773077/",
}

E = []


def ev(**kw):
    kw.setdefault("status", "gepland")
    kw.setdefault("checked_at", CHECKED)
    kw.setdefault("nl", True)
    E.append(kw)


# ---------------- DARTS: WK 2027 (Alexandra Palace) ----------------
T = "wk-darts"
ev(id="wkd-loting", sport="darts", tournament=T, title="Loting WK darts 2027",
   date="2026-11-30", time_known=False, round="Loting",
   note="Na de loting staan alle wedstrijden en sessies vast.", source=SRC["darts"])
ev(id="wkd-opening", sport="darts", tournament=T, title="Openingsavond WK darts",
   start=utc("2026-12-11 20:00"), round="Ronde 1", venue="Alexandra Palace", city="Londen",
   broadcaster="viaplay", note="Alleen een avondsessie, 4 wedstrijden.", source=SRC["darts"])
ev(id="wkd-r1", sport="darts", tournament=T, title="WK darts: ronde 1 (laatste 128)",
   date="2026-12-11", end_date="2026-12-19", time_known=False, round="Ronde 1",
   time_note="Middag 13:30, avond 20:00 (11 en 14 december alleen avond)",
   format="Best of 5 sets", broadcaster="viaplay", source=SRC["darts"])
ev(id="wkd-r2", sport="darts", tournament=T, title="WK darts: ronde 2 (laatste 64)",
   date="2026-12-20", end_date="2026-12-23", time_known=False, round="Ronde 2",
   time_note="Middag- en avondsessies", format="Best of 5 sets", broadcaster="viaplay", source=SRC["darts"])
ev(id="wkd-r3", sport="darts", tournament=T, title="WK darts: ronde 3 (laatste 32)",
   date="2026-12-27", end_date="2026-12-29", time_known=False, round="Ronde 3",
   time_note="Middag- en avondsessies, 3 wedstrijden per sessie", format="Best of 7 sets",
   broadcaster="viaplay", source=SRC["darts"])
ev(id="wkd-r4", sport="darts", tournament=T, title="WK darts: ronde 4 (laatste 16)",
   date="2026-12-29", end_date="2026-12-30", time_known=False, round="Ronde 4",
   format="Best of 7 sets", broadcaster="viaplay", source=SRC["darts"])
ev(id="wkd-kf", sport="darts", tournament=T, title="WK darts: kwartfinales",
   date="2027-01-01", time_known=False, round="Kwartfinale",
   time_note="Twee sessies met elk 2 wedstrijden", format="Best of 9 sets", broadcaster="viaplay", source=SRC["darts"])
ev(id="wkd-hf", sport="darts", tournament=T, title="WK darts: halve finales",
   start=utc("2027-01-02 20:30"), round="Halve finale", format="Best of 11 sets",
   venue="Alexandra Palace", city="Londen", broadcaster="viaplay", source=SRC["darts"])
ev(id="wkd-finale", sport="darts", tournament=T, title="Finale WK darts 2027",
   start=utc("2027-01-03 21:00"), round="Finale", format="Best of 13 sets",
   venue="Alexandra Palace", city="Londen", broadcaster="viaplay", source=SRC["darts"])

# ---------------- HANDBAL: EK vrouwen 2026 ----------------
T = "ek-handbal-vrouwen"
for i, (d, opp, tv, slugopp) in enumerate([
    ("2026-12-04 20:30", "Tsjechië", "Ziggo Sport 1 en Ziggo Sport 4", "tsjechie"),
    ("2026-12-06 20:30", "Oostenrijk", "Ziggo Sport 4", "oostenrijk"),
    ("2026-12-08 20:30", "Kroatië", "Ziggo Sport (kanaal volgt)", "kroatie")]):
    ev(id=f"ekh-nl-{slugopp}", sport="handbal", tournament=T, title=f"Nederland – {opp}",
       home="Nederland", away=opp, start=utc(d), round=f"Poule D, speeldag {i + 1}",
       venue="Brno", city="Brno (Tsjechië)", broadcaster="ziggo", tv_detail=tv,
       page=f"nederland-{slugopp}-handbal-{d[:10]}", source=SRC["hand"])
ev(id="ekh-hoofdronde", sport="handbal", tournament=T, title="EK handbal: hoofdronde (als Nederland doorgaat)",
   date="2026-12-10", end_date="2026-12-15", time_known=False, round="Hoofdronde",
   city="Katowice (Polen)", note="De beste twee van poule D gaan door naar de hoofdronde in Katowice.",
   broadcaster="ziggo", source="https://lex.dk/EM_i_h%C3%A5ndbold_for_kvinder_2026")
ev(id="ekh-hf", sport="handbal", tournament=T, title="EK handbal: halve finales",
   start=utc("2026-12-18 17:45"), round="Halve finale", city="Katowice (Polen)",
   note="Tweede halve finale om 20:30.", broadcaster="ziggo", source=SRC["hand_ehf"], nl=False)
ev(id="ekh-finale", sport="handbal", tournament=T, title="Finale EK handbal vrouwen",
   start=utc("2026-12-20 18:00"), round="Finale", city="Katowice (Polen)",
   note="Bronzen finale om 15:15.", broadcaster="ziggo", source=SRC["hand_ehf"], nl=False)

# ---------------- VOETBAL: Oranje ----------------
T = "nederlands-elftal"
ev(id="oranje-loting-ek", sport="voetbal", tournament=T, title="Loting EK 2028-kwalificatie",
   start=utc("2026-12-06 18:00"), round="Loting", venue="ICC", city="Belfast",
   note="Nederland zit in pot 1. Door de Nations League-kwartfinales begint Oranje pas in september 2027.",
   source=SRC["loting"])
ev(id="oranje-nl-kf", sport="voetbal", tournament=T, title="Nations League-kwartfinale (heen en terug)",
   date="2027-03-25", end_date="2027-03-30", time_known=False, round="Kwartfinale Nations League",
   note="Tegenstander volgt via loting.", source=SRC["oranje"])

# ---------------- FORMULE 1 ----------------
T = "formule-1"
ev(id="f1-2026-24", sport="f1", tournament=T, title="GP van Abu Dhabi 2026", h1="Hoe laat begint de GP van Abu Dhabi?",
   start=utc("2026-12-06 14:00"), round="Slotrace, race 24 van 24",
   note="De laatste Grand Prix van het seizoen 2026, verreden op het Yas Marina Circuit. Het raceweekend loopt van vrijdag 4 tot en met zondag 6 december.", venue="Yas Marina Circuit", city="Abu Dhabi",
   broadcaster="viaplay", page="gp-abu-dhabi-2026", source=SRC["f1_ad"])
cal27 = [("03-14", "Bahrein", "Sakhir", 1), ("03-21", "Saudi-Arabië", "Jeddah", 0), ("04-04", "Australië", "Melbourne", 1),
         ("04-11", "Japan", "Suzuka", 1), ("04-18", "China", "Shanghai", 0), ("05-02", "Miami", "Miami", 0),
         ("05-23", "Canada", "Montréal", 1), ("06-06", "Monaco", "Monaco", 1), ("06-20", "Portugal", "Portimão", 0),
         ("07-04", "Groot-Brittannië", "Silverstone", 1), ("07-11", "Oostenrijk", "Spielberg", 0), ("07-25", "België", "Spa", 0),
         ("08-01", "Hongarije", "Boedapest", 0), ("09-05", "Italië", "Monza", 1), ("09-12", "Spanje", "Madrid", 0),
         ("09-26", "Azerbeidzjan", "Bakoe", 0), ("10-03", "Turkije", "Istanbul", 0), ("10-10", "Singapore", "Singapore", 0),
         ("10-24", "Verenigde Staten", "Austin", 0), ("10-31", "Mexico", "Mexico-Stad", 0), ("11-07", "Brazilië", "São Paulo", 1),
         ("11-20", "Las Vegas", "Las Vegas", 0), ("12-05", "Qatar", "Lusail", 1), ("12-12", "Abu Dhabi", "Yas Island", 1)]
for n, (md, gp, city, sprint) in enumerate(cal27, 1):
    ev(id=f"f1-2027-{n:02d}", sport="f1", tournament=T, title=f"GP van {gp}" if gp not in ("Miami", "Las Vegas") else f"GP {gp}",
       date=f"2027-{md}", time_known=False, round=f"Race {n} van 24", city=city, sprint=bool(sprint),
       broadcaster="viaplay", time_note="Tijden volgen zodra de FIA het tijdschema publiceert", source=SRC["f1_27"])

# ---------------- HOCKEY: FIH Pro League ----------------
T = "hockey"
ev(id="hockey-pl-valencia", sport="hockey", tournament=T, title="Pro League in Valencia",
   date="2026-12-14", end_date="2026-12-22", time_known=False, round="Pro League 2026-27",
   city="Valencia (Spanje)", note="Nederland tegen Spanje, België en Duitsland.", source=SRC["hockey"])
ev(id="hockey-pl-goldcoast", sport="hockey", tournament=T, title="Pro League op de Gold Coast",
   date="2027-02-13", end_date="2027-02-21", time_known=False, round="Pro League 2026-27",
   city="Gold Coast (Australië)", note="Nederland tegen Australië, België, China (vrouwen) en Frankrijk (mannen).", source=SRC["hockey"])
ev(id="hockey-pl-thuis", sport="hockey", tournament=T, title="Pro League in Nederland",
   date="2027-06-15", end_date="2027-06-27", time_known=False, round="Pro League 2026-27",
   city="Nederland (locatie volgt)", note="Nederland tegen Argentinië, Groot-Brittannië, India en Spanje.", source=SRC["hockey"])

# ---------------- SCHAATSEN ----------------
T = "schaatsen"
ev(id="nk-allround-sprint", sport="schaatsen", tournament=T, title="NK allround & sprint",
   date="2026-12-27", end_date="2026-12-28", time_known=False, round="NK", city="Nederland (locatie volgt)", source=SRC["knsb"])
ev(id="ek-allround-sprint", sport="schaatsen", tournament=T, title="EK allround & sprint",
   date="2027-01-08", end_date="2027-01-10", time_known=False, round="EK", venue="Thialf", city="Heerenveen", source=SRC["knsb"])

# ---------------- VELDRIJDEN: Wereldbeker ----------------
T = "veldrijden"
for d, place in [("2026-11-27", "Ostrava (Tsjechië)"), ("2026-11-29", "Tábor (Tsjechië)"), ("2026-12-19", "Antwerpen"),
                 ("2026-12-20", "Koksijde"), ("2026-12-26", "Gavere"), ("2026-12-27", "Namen"),
                 ("2026-12-29", "Besançon (Frankrijk)"), ("2027-01-03", "Zonhoven"), ("2027-01-17", "Benidorm (Spanje)"),
                 ("2027-01-23", "Hamme")]:
    ev(id=f"cx-wb-{d}", sport="veldrijden", tournament=T, title=f"Wereldbeker veldrijden {place.split(' (')[0]}",
       date=d, time_known=False, round="Wereldbeker 2026-27", city=place,
       time_note="Starttijden volgen in de week van de wedstrijd", source=SRC["cx"])

# ---------------- CLUBS: Ajax, Feyenoord, PSV (Eredivisie) ----------------
ERE = "https://www.ziggo.nl/entertainment/sport/voetbal/eredivisie/programma"
for d, home, away, tv in [
    ("2026-11-28 18:45", "PSV", "Go Ahead Eagles", "ESPN 1"),
    ("2026-11-29 14:30", "Feyenoord", "Ajax", "ESPN 1"),
    ("2026-12-05 16:30", "Willem II", "Feyenoord", "ESPN 1"),
    ("2026-12-05 20:00", "AZ", "PSV", "ESPN 2"),
    ("2026-12-06 14:30", "Ajax", "FC Utrecht", "ESPN 3"),
    ("2026-12-13 12:15", "PSV", "Telstar", None),
    ("2026-12-13 14:30", "FC Groningen", "Feyenoord", None),
    ("2026-12-13 20:00", "Ajax", "Cambuur", None),
    ("2026-12-20 14:30", "Feyenoord", "FC Twente", None),
    ("2026-12-20 16:45", "Go Ahead Eagles", "Ajax", None),
    ("2026-12-20 20:00", "PSV", "PEC Zwolle", None)]:
    clubs = [c for c in ("ajax", "feyenoord", "psv") if c in (home + away).lower()]
    import re as _re
    sl = lambda x: _re.sub(r"[^a-z0-9]+", "-", x.lower()).strip("-")
    ev(id=f"ere-{d[:10]}-{sl(home)}-{sl(away)}", sport="clubs", tournament=clubs[0], clubs=clubs,
       title=f"{home} – {away}", home=home, away=away, start=utc(d), round="Eredivisie",
       broadcaster="espn", tv_detail=tv or "ESPN (kanaal volgt)", page=f"{sl(home)}-{sl(away)}-{d[:10]}", source=ERE)

out = Path(__file__).with_name("events.json")
out.write_text(json.dumps({"generated_at": CHECKED, "events": E}, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"{len(E)} evenementen geschreven naar {out}")
