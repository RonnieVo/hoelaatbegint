"""De automatische pipeline van hoelaatbegint.nl.

Draait elke 15 minuten via GitHub Actions (.github/workflows/update.yml):
  1. haalt data op bij alle bronnen (API's + AI-controle)
  2. voegt samen met data/events.json
  3. vergelijkt bronnen: bij een conflict blijft de laatst bevestigde tijd staan en gaat er één mail uit
  4. schrijft data/events.json terug (daarna bouwt site/build.py de site)

Elke bron is optioneel: zonder API-sleutel wordt die bron overgeslagen.
"""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sources import f1, football, football_data, thesportsdb, ai_verify  # noqa: E402
from notify import send_mail  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
EVENTS = ROOT / "data" / "events.json"
STATE = ROOT / "data" / "pipeline_state.json"
TRUSTED_APIS = {"jolpica", "api-football", "football-data"}  # één bron is genoeg voor deze officiële data-API's
OFFICIAL = ("eurohandball.com", "ihf.info", "pdc.tv", "uefa.com", "fifa.com", "onsoranje.nl", "knvb.nl", "eredivisie.nl",
            "fih.hockey", "knhb.nl", "knsb.nl", "isu.org", "schaatsen.nl", "uci.org", "formula1.com", "fia.com",
            "nos.nl", "ziggo.nl", "viaplay.nl", "espn.nl")
AI_FIELDS = {"start", "date", "end_date", "time_known", "time_note", "venue", "city", "status", "result", "sources", "source", "participants"}


def official(ev):
    return any(any(d in (u or "") for d in OFFICIAL) for u in ev.get("sources", [ev.get("source")]))


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def merge(existing, candidates):
    """candidates: lijst van (bron, event). Geeft (events, changes, conflicts)."""
    by_id = {e["id"]: e for e in existing}
    # Hetzelfde evenement uit een andere bron (andere id) herkennen: zelfde starttijd + zelfde club/toernooi
    same = {(e.get("start"), c): e["id"] for e in existing if e.get("start") for c in (e.get("clubs") or [e.get("tournament")])}
    remapped = []
    for src, ev in candidates:
        if ev["id"] not in by_id and ev.get("start"):
            for c in ev.get("clubs") or [ev.get("tournament")]:
                if (ev["start"], c) in same:
                    ev = {**ev, "id": same[(ev["start"], c)]}
                    ev.pop("page", None)  # bestaande URL behouden
                    break
        remapped.append((src, ev))
    candidates = remapped
    grouped = {}
    for src, ev in candidates:
        grouped.setdefault(ev["id"], []).append((src, ev))
    changes, conflicts = [], []
    for eid, items in grouped.items():
        starts = {ev.get("start") or ev.get("date") for _, ev in items}
        srcs = {s for s, _ in items}
        confirmed = bool(srcs & TRUSTED_APIS) or len(srcs) >= 2 or any(len(ev.get("sources", [])) >= 2 for _, ev in items)
        if len(starts) > 1:
            conflicts.append({"id": eid, "values": [(s, ev.get("start") or ev.get("date")) for s, ev in items]})
            continue
        new = dict(items[0][1])
        new.setdefault("status", "gepland")
        new.setdefault("nl", True)
        new["checked_at"] = now_iso()
        new["confirmed_by"] = sorted(srcs)
        old = by_id.get(eid)
        if old is None:
            if confirmed:
                by_id[eid] = new
                changes.append(("nieuw", eid))
            continue
        if srcs == {"ai"}:  # AI mag bij bestaande evenementen alleen tijden en praktische gegevens bijwerken
            new = {k: v for k, v in new.items() if k in AI_FIELDS or k in ("id", "checked_at", "confirmed_by")}
        moved = (old.get("start") or old.get("date")) != (new.get("start") or new.get("date"))
        if moved and srcs == {"ai"} and old.get("start") and not official(items[0][1]):
            confirmed = False  # een bevestigde tijd verschuift alleen op gezag van een officiële bron
        if moved and not confirmed:
            conflicts.append({"id": eid, "values": [("huidig", old.get("start") or old.get("date"))] +
                              [(s, ev.get("start") or ev.get("date")) for s, ev in items]})
            continue
        merged = {**old, **{k: v for k, v in new.items() if v not in (None, "", [])}}
        if moved:
            merged["status"] = "verplaatst" if old.get("start") else merged.get("status", "gepland")
            if old.get("start") and new.get("date") and not new.get("start"):
                merged.pop("date", None)  # bevestigde tijd nooit vervangen door alleen een datum
            if new.get("start"):
                merged.pop("date", None)
                merged.pop("time_known", None)
            changes.append(("verplaatst" if old.get("start") else "tijd bekend", eid))
        elif {k: v for k, v in merged.items() if k != "checked_at"} != {k: v for k, v in old.items() if k != "checked_at"}:
            changes.append(("bijgewerkt", eid))
        by_id[eid] = merged
    return list(by_id.values()), changes, conflicts


def main():
    data = json.loads(EVENTS.read_text(encoding="utf-8"))
    existing = data["events"]
    candidates, errors = [], []
    for name, mod in [("jolpica", f1), ("football-data", football_data), ("api-football", football), ("thesportsdb", thesportsdb), ("ai", ai_verify)]:
        try:
            got = mod.fetch(existing)
            candidates += [(name, e) for e in got]
            print(f"{name}: {len(got)} evenementen")
        except mod.Skip as s:
            print(f"{name}: overgeslagen ({s})")
        except Exception as ex:  # een bron die faalt mag de rest niet stoppen
            errors.append(f"{name}: {ex!r}")
            print(f"{name}: FOUT {ex!r}")

    events, changes, conflicts = merge(existing, candidates)
    events.sort(key=lambda e: (e.get("start") or e.get("date") or "", e["id"]))
    data["events"] = events
    if changes:
        data["generated_at"] = now_iso()
        EVENTS.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(changes)} wijzigingen, {len(conflicts)} conflicten, {len(errors)} fouten")

    # Alleen mailen bij nieuwe conflicten/fouten (niet elke 15 minuten dezelfde)
    state = json.loads(STATE.read_text()) if STATE.exists() else {"mailed": []}
    keys = [f"c:{c['id']}:{c['values']}" for c in conflicts] + [f"e:{e}" for e in errors]
    fresh = [k for k in keys if k not in state["mailed"]]
    if fresh:
        body = ["Hallo,", "", "De pipeline van hoelaatbegint.nl heeft iets gevonden dat je even moet bekijken.", ""]
        for c in conflicts:
            body.append(f"- Bronnen oneens over {c['id']}: " + ", ".join(f"{s} = {v}" for s, v in c["values"]))
        for e in errors:
            body.append(f"- Bron werkt niet: {e}")
        body += ["", "Tot het is opgelost blijft de laatst bevestigde tijd op de site staan.",
                 "Oplossen: pas data/events.json aan in GitHub, of laat het zo als de huidige tijd klopt."]
        send_mail("hoelaatbegint.nl: controle nodig", "\n".join(body))
        state["mailed"] = (state["mailed"] + fresh)[-500:]
        STATE.write_text(json.dumps(state))
    # Publiceren alleen als het nodig is (Cloudflare gratis: 500 publicaties per maand)
    import hashlib
    from datetime import timedelta
    now = datetime.now(timezone.utc)
    content = b"".join((ROOT / "data" / f).read_bytes() for f in ("events.json", "tournaments.json", "broadcasters.json"))
    digest = hashlib.sha256(content).hexdigest()
    state = json.loads(STATE.read_text()) if STATE.exists() else {"mailed": []}
    soon = now + timedelta(hours=48)
    urgent = any((e.get("start") or e.get("date") or "9999") <= soon.strftime("%Y-%m-%dT%H:%M:%SZ")
                 for e in events if e["id"] in {c[1] for c in changes})
    slot = now.minute < 15 and now.hour % 2 == 0          # gewone wijzigingen: hooguit elke 2 uur
    daily = now.hour == 4 and now.minute < 15              # dagelijkse verversing (vandaag-pagina)
    forced = bool(os.environ.get("FORCE_DEPLOY"))
    deploy = forced or daily or (digest != state.get("deployed_hash") and (urgent or slot))
    if deploy:
        state["deployed_hash"] = digest
    STATE.write_text(json.dumps(state))
    print(f"publiceren: {'ja' if deploy else 'nee'} (urgent={urgent}, slot={slot}, dagelijks={daily})")
    # Voor de IndexNow-stap: welke pagina's zijn gewijzigd
    (ROOT / "data" / "changed.json").write_text(json.dumps([c[1] for c in changes]))
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            f.write(f"changed={'true' if changes else 'false'}\n")
            f.write(f"deploy={'true' if deploy else 'false'}\n")


if __name__ == "__main__":
    main()
