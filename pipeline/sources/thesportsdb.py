"""Overige sporten via TheSportsDB (gratis sleutel '3' voor testen; premiumsleutel aanbevolen).

Wordt gebruikt als tweede bron naast de AI-controle (darts, handbal, hockey). Alleen evenementen
met een Nederlandse deelnemer worden doorgegeven.
"""
import os

import requests

from . import Skip

LEAGUES = {  # TheSportsDB league-id -> (sport, tournament-pagina)
    "4554": ("darts", "wk-darts"),  # PDC Darts
}
DUTCH = {"Netherlands", "Michael van Gerwen", "Gian van Veen", "Wessel Nijman", "Danny Noppert", "Kevin Doets",
         "Dirk van Duijvenbode", "Jermaine Wattimena", "Niels Zonneveld", "Maik Kuivenhoven", "Richard Veenstra",
         "Christian Kist", "Jimmy van Schie", "Raymond van Barneveld", "Alexander Merkx", "Jurjen van der Velde",
         "Jamai van den Herik", "Stef Kosters"}


def fetch(existing):
    key = os.environ.get("THESPORTSDB_KEY")
    if not key:
        raise Skip("geen THESPORTSDB_KEY")
    out = []
    for lid, (sport, tournament) in LEAGUES.items():
        r = requests.get(f"https://www.thesportsdb.com/api/v1/json/{key}/eventsnextleague.php", params={"id": lid}, timeout=20)
        r.raise_for_status()
        for e in r.json().get("events") or []:
            name = e.get("strEvent", "")
            players = [p for p in DUTCH if p in name]
            if not players or not e.get("strTimestamp"):
                continue
            out.append(dict(id=f"tsdb-{e['idEvent']}", sport=sport, tournament=tournament, nl=True,
                            title=name.replace(" vs ", " – "), participants=players,
                            start=e["strTimestamp"].replace("+00:00", "") + "Z" if "Z" not in e["strTimestamp"] else e["strTimestamp"],
                            round=e.get("strRound") or e.get("intRound"), broadcaster="viaplay",
                            source="https://www.thesportsdb.com/event/" + e["idEvent"]))
    return out
