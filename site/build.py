"""Bouwt de complete statische site van hoelaatbegint.nl uit data/*.json.

Gebruik:  python site/build.py            -> bouwt naar dist/
          python site/build.py --og       -> maakt ook de deelafbeeldingen (Playwright nodig)

Wordt elke 15 minuten automatisch gedraaid door .github/workflows/update.yml.
"""
import hashlib
import json
import os
import re
import shutil
import sys
import unicodedata
from datetime import date, datetime, timedelta, timezone
from html import escape
from pathlib import Path
from zoneinfo import ZoneInfo

from jinja2 import Environment, BaseLoader

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
NL = ZoneInfo("Europe/Amsterdam")
UTC = timezone.utc
CONFIG = json.loads((ROOT / "site" / "config.json").read_text(encoding="utf-8"))
BASE = CONFIG["base_url"].rstrip("/")

DAYS = ["maandag", "dinsdag", "woensdag", "donderdag", "vrijdag", "zaterdag", "zondag"]
MONTHS = ["januari", "februari", "maart", "april", "mei", "juni", "juli", "augustus",
          "september", "oktober", "november", "december"]
# Volgorde op zoekvolume (DataForSEO, NL, nov 2026; zie data/keywords.json):
# F1 657k > clubvoetbal 311k > darts 217k > schaatsen 157k > Oranje 49k > veldrijden 31k > handbal 24k > Leeuwinnen 14k > hockey 7k
SPORTS = {
    "f1": {"name": "Formule 1", "page": "formule-1", "minutes": 120},
    "clubs": {"name": "Clubs", "page": "clubs", "minutes": 120},
    "darts": {"name": "Darts", "page": "wk-darts", "minutes": 240},
    "schaatsen": {"name": "Schaatsen", "page": "schaatsen", "minutes": 240},
    "voetbal": {"name": "Oranje", "page": "nederlands-elftal", "minutes": 120},
    "veldrijden": {"name": "Veldrijden", "page": "veldrijden", "minutes": 75},
    "handbal": {"name": "Handbal", "page": "ek-handbal-vrouwen", "minutes": 100},
    "leeuwinnen": {"name": "Leeuwinnen", "page": "oranje-leeuwinnen", "minutes": 120},
    "hockey": {"name": "Hockey", "page": "hockey", "minutes": 90},
}
# Hoofdmenu: per sport een uitklapmenu met de subpagina's waar zoekvolume op zit. De rest onder "Meer sporten".
NAV = [
    ("f1", "Formule 1", [("Alle F1-tijden", "/formule-1/"), ("Formule 1 vandaag", "/formule-1/vandaag/"),
                         ("F1 kalender 2027", "/formule-1/kalender/"), ("F1 stand", "/formule-1/stand/"), ("Formule 1 op tv", "/formule-1/op-tv/")]),
    ("clubs", "Voetbal", [("Voetbal vandaag", "/voetbal/vandaag/"), ("Voetbal op tv", "/voetbal/op-tv/"),
                          ("Eredivisie programma", "/eredivisie/"), ("Ajax", "/ajax/"), ("Feyenoord", "/feyenoord/"), ("PSV", "/psv/")]),
    ("darts", "Darts", [("WK darts schema", "/wk-darts/"), ("Darts vandaag", "/darts/vandaag/"),
                        ("Darts op tv", "/darts/op-tv/"), ("Nederlanders op het WK", "/wk-darts/#nederlanders")]),
    ("schaatsen", "Schaatsen", [("Schaatsprogramma", "/schaatsen/"), ("Schaatsen vandaag", "/schaatsen/vandaag/"),
                                ("Schaatsen op tv", "/schaatsen/op-tv/")]),
    ("voetbal", "Oranje", [("Programma Oranje", "/nederlands-elftal/"), ("EK 2028", "/ek-2028/"),
                           ("Oranje Leeuwinnen", "/oranje-leeuwinnen/")]),
]
MORE_NAV = [("veldrijden", "Veldrijden", "/veldrijden/"), ("handbal", "Handbal", "/ek-handbal-vrouwen/"), ("hockey", "Hockey", "/hockey/")]
ICONS = {
    "darts": '<svg viewBox="0 0 24 24" fill="none" stroke="#F6F4EF" stroke-width="2"><circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1.5" fill="#FF6A13" stroke="none"/></svg>',
    "voetbal": '<svg viewBox="0 0 24 24" fill="none" stroke="#F6F4EF" stroke-width="2"><circle cx="12" cy="12" r="9"/><path d="M12 7l4 3-1.5 4.5h-5L8 10z" fill="#FF6A13" stroke="none"/></svg>',
    "leeuwinnen": '<svg viewBox="0 0 24 24" fill="none" stroke="#F6F4EF" stroke-width="2"><circle cx="12" cy="12" r="9"/><path d="M12 7l4 3-1.5 4.5h-5L8 10z" fill="#FF6A13" stroke="none"/><path d="M17 3.5l1.5 1.5M19.5 7.5h1.5" stroke="#FF6A13"/></svg>',
    "clubs": '<svg viewBox="0 0 24 24" fill="none" stroke="#F6F4EF" stroke-width="2"><path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z"/><path d="M8 12h8" stroke="#FF6A13"/></svg>',
    "handbal": '<svg viewBox="0 0 24 24" fill="none" stroke="#F6F4EF" stroke-width="2"><circle cx="12" cy="12" r="9"/><path d="M3.5 9c5 2 12 2 17 0M3.5 15c5-2 12-2 17 0" stroke="#FF6A13"/></svg>',
    "f1": '<svg viewBox="0 0 24 24" fill="none" stroke="#F6F4EF" stroke-width="2"><path d="M5 21V4"/><path d="M5 4h14v9H5" /><path d="M5 4h4v3H5zM13 4h4v3h-4zM9 7h4v3H9zM5 10h4v3H5zM13 10h4v3h-4z" fill="#FF6A13" stroke="none"/></svg>',
    "hockey": '<svg viewBox="0 0 24 24" fill="none" stroke="#F6F4EF" stroke-width="2" stroke-linecap="round"><path d="M15 3l-6 14c-.6 1.4-2 2-3.5 1.6"/><circle cx="17" cy="18" r="2.2" fill="#FF6A13" stroke="none"/></svg>',
    "schaatsen": '<svg viewBox="0 0 24 24" fill="none" stroke="#F6F4EF" stroke-width="2" stroke-linecap="round"><path d="M6 4h5v6l6 2c1.5.5 2 1.5 2 3H6z"/><path d="M4 19h16" stroke="#FF6A13"/></svg>',
    "veldrijden": '<svg viewBox="0 0 24 24" fill="none" stroke="#F6F4EF" stroke-width="2" stroke-linecap="round"><circle cx="6" cy="16" r="4"/><circle cx="18" cy="16" r="4"/><path d="M6 16l4-8h5l3 8M10 8l2 8" stroke="#FF6A13"/></svg>',
}
for _k, _v in SPORTS.items():
    _v["key"] = _k
CAL_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/></svg>'
BELL_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 8a6 6 0 1 1 12 0c0 7 3 8 3 8H3s3-1 3-8M10 20a2 2 0 0 0 4 0"/></svg>'
IG_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="5"/><circle cx="12" cy="12" r="4"/><circle cx="17.5" cy="6.5" r="1" fill="currentColor" stroke="none"/></svg>'
SHARE_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><path d="M8.6 13.5l6.8 4M15.4 6.5l-6.8 4"/></svg>'


# ------------------------------------------------------------------ helpers
def slugify(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def d_label(d, year=False):
    s = f"{DAYS[d.weekday()]} {d.day} {MONTHS[d.month - 1]}"
    return s + (f" {d.year}" if year else "")


def range_label(a, b):
    if a == b:
        return d_label(a)
    if a.month == b.month:
        return f"{a.day} t/m {b.day} {MONTHS[a.month - 1]}"
    return f"{a.day} {MONTHS[a.month - 1]} t/m {b.day} {MONTHS[b.month - 1]}"


def prep(e, broadcasters, now):
    e = dict(e)
    if e.get("start"):
        dt = datetime.fromisoformat(e["start"].replace("Z", "+00:00"))
        loc = dt.astimezone(NL)
        e["dt"], e["local"] = dt, loc
        e["time"] = loc.strftime("%H:%M")
        e["day"] = loc.date()
        e["day_label"] = d_label(loc.date())
        e["end_day"] = loc.date()
        e["end_dt"] = dt + timedelta(minutes=SPORTS[e["sport"]]["minutes"])
    else:
        a = date.fromisoformat(e["date"])
        b = date.fromisoformat(e.get("end_date", e["date"]))
        e["day"], e["end_day"] = a, b
        e["dt"] = datetime(a.year, a.month, a.day, tzinfo=NL).astimezone(UTC)
        e["end_dt"] = datetime(b.year, b.month, b.day, 23, 59, tzinfo=NL).astimezone(UTC)
        e["time"] = None
        e["day_label"] = range_label(a, b) if b != a else d_label(a)
    e["is_range"] = e["end_day"] != e["day"]
    # Automatische wedstrijdpagina voor elke Nederlandse wedstrijd met een vaste tijd en tegenstander
    if not e.get("page") and e.get("start") and e.get("nl") and (e.get("away") or e.get("participants")) and " – " in e["title"]:
        e["page"] = f"{slugify(e['title'])}-{e['day'].isoformat()}"
    if not e.get("page") and e["sport"] == "f1" and e.get("start") and e["title"].startswith("GP") and ":" not in e["title"]:
        e["page"] = f"{slugify(e['title'])}-{e['day'].year}"
        e.setdefault("h1", f"Hoe laat begint de {e['title']} {e['day'].year}?")
    if not e.get("h1") and e["sport"] == "clubs" and {_t.strip() for _t in e["title"].split("–")} == {"Feyenoord", "Ajax"}:
        e["h1"] = f"Hoe laat begint de Klassieker {e['title']}?"
    e["tv"] = broadcasters.get(e.get("broadcaster", ""), {}).get("name")
    e["tv_detail"] = e.get("tv_detail") or e["tv"]
    e["url"] = f"/wedstrijd/{e['page']}/" if e.get("page") else f"/{SPORTS[e['sport']]['page']}/"
    e["sport_name"] = SPORTS[e["sport"]]["name"]
    e["upcoming"] = e["end_dt"] >= now - timedelta(hours=3)
    e["meta"] = " · ".join(x for x in [e.get("round"), e.get("city"), e["tv_detail"]] if x)
    return e


ORGANIZERS = {"f1": ("Formula 1", "https://www.formula1.com"), "darts": ("PDC", "https://www.pdc.tv"),
              "schaatsen": ("ISU", "https://www.isu.org"), "veldrijden": ("UCI", "https://www.uci.org"),
              "handbal": ("EHF", "https://www.eurohandball.com"), "hockey": ("FIH", "https://www.fih.hockey"),
              "voetbal": ("UEFA", "https://www.uefa.com"), "leeuwinnen": ("UEFA", "https://www.uefa.com")}


def organizer(e):
    rnd = (e.get("round") or "").lower()
    if e["sport"] == "clubs":
        if "league" in rnd:
            return ("UEFA", "https://www.uefa.com")
        if "beker" in rnd:
            return ("KNVB", "https://www.knvb.nl")
        return ("Eredivisie", "https://eredivisie.nl")
    if "loting" in rnd or "kwalificatie" in rnd:
        return ("UEFA", "https://www.uefa.com")
    return ORGANIZERS.get(e["sport"])


TOP_CLUBS = {"ajax", "feyenoord", "psv", "az", "fc twente", "twente"}
WEEKDAYS_SHORT = ["ma", "di", "wo", "do", "vr", "za", "zo"]
MONTHS_SHORT = ["jan", "feb", "mrt", "apr", "mei", "jun", "jul", "aug", "sep", "okt", "nov", "dec"]


def short_day(d):
    return f"{WEEKDAYS_SHORT[d.weekday()]} {d.day} {MONTHS_SHORT[d.month - 1]}"


def indexable(e):
    """Alleen wedstrijden waar echt op gezocht wordt krijgen een indexeerbare pagina (rest: noindex, wel bruikbaar)."""
    if "index" in e:
        return bool(e["index"])
    rnd = (e.get("round") or "").lower()
    if e["sport"] in ("voetbal", "leeuwinnen", "handbal"):
        return True  # Oranje, Leeuwinnen, handbalsters, lotingen
    if e["sport"] == "f1":
        return ":" not in e["title"]  # de race zelf, niet elke sessie
    if e["sport"] == "clubs":
        if "champions league" in rnd or "finale" in rnd:
            return True
        teams = {(e.get("home") or "").lower(), (e.get("away") or "").lower()}
        if not e.get("home"):
            teams = {x.strip().lower() for x in e["title"].split("–")}
        return len(teams & TOP_CLUBS) == 2  # topduels zoals de Klassieker
    return "finale" in rnd


def timeline(evs, day):
    """Tv-gids-tijdlijn: per zender een rij met blokken op tijd (alleen tijden met zender)."""
    evs = [e for e in evs if e.get("start") and e.get("tv") and e["day"] == day]
    if not evs:
        return None
    first = min(e["local"].hour for e in evs)
    last = max(min(24, e["local"].hour + (SPORTS[e["sport"]]["minutes"] + e["local"].minute + 59) // 60) for e in evs)
    start_h = max(0, first - 1)
    end_h = min(24, max(last, start_h + 6))
    span = (end_h - start_h) * 60
    rows = {}
    for e in evs:
        ch = re.split(r" en |, ", e["tv_detail"])[0]
        m0 = (e["local"].hour - start_h) * 60 + e["local"].minute
        dur = min(SPORTS[e["sport"]]["minutes"], span - m0)
        rows.setdefault(ch, []).append({"e": e, "left": round(m0 / span * 100, 2), "width": round(max(dur, 30) / span * 100 - 0.4, 2)})
    hours = [{"label": f"{h:02d}:00", "left": round((h - start_h) * 60 / span * 100, 2)} for h in range(start_h, end_h, 1 if end_h - start_h <= 8 else 2)]
    start_iso = datetime(day.year, day.month, day.day, start_h, tzinfo=NL).isoformat()
    return {"rows": [{"name": k, "blocks": v} for k, v in sorted(rows.items(), key=lambda kv: kv[1][0]["e"]["dt"])],
            "hours": hours, "span": span, "start_iso": start_iso}


_sf = ROOT / "data" / "f1_standings.json"
F1_DRIVERS = json.loads(_sf.read_text(encoding="utf-8")).get("drivers", []) if _sf.exists() else []


def jsonld_event(e):
    if not e.get("start"):
        return None
    og = e.get("tournament") if (ROOT / "site" / "og" / f"{e.get('tournament')}.png").exists() else "default"
    desc = (f"{e['title']} begint {e['day_label']} om {e['time']} Nederlandse tijd"
            + (f" in {e['city']}" if e.get("city") else "") + (f", live op {e['tv_detail']}" if e.get("tv") else "") + ".")
    address = {"@type": "PostalAddress", "addressLocality": e.get("city") or e.get("venue") or "Onbekend"}
    data = {
        "@context": "https://schema.org", "@type": "SportsEvent", "name": e["title"],
        "startDate": e["local"].isoformat(), "endDate": e["end_dt"].astimezone(NL).isoformat(),
        "eventStatus": {"gepland": "https://schema.org/EventScheduled", "verplaatst": "https://schema.org/EventRescheduled",
                        "afgelast": "https://schema.org/EventCancelled"}.get(e.get("status", "gepland"), "https://schema.org/EventScheduled"),
        "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
        "sport": {"clubs": "Voetbal", "voetbal": "Voetbal", "leeuwinnen": "Voetbal"}.get(e["sport"], e["sport_name"]),
        "location": {"@type": "Place", "name": e.get("venue") or e.get("city") or e["title"], "address": address},
        "image": [f"{BASE}/assets/og/{og}.png"],
        "description": desc,
        "url": BASE + e["url"],
        "inLanguage": "nl-NL",
    }
    org = organizer(e)
    if org:
        data["organizer"] = {"@type": "Organization", "name": org[0], "url": org[1]}
    if not e.get("home") and " – " in e["title"] and e["sport"] in ("clubs", "voetbal", "leeuwinnen", "handbal", "hockey"):
        e = {**e, "home": e["title"].split(" – ")[0].strip(), "away": e["title"].split(" – ")[1].split(":")[0].strip()}
    if e.get("home") and e.get("away"):
        data["homeTeam"] = {"@type": "SportsTeam", "name": e["home"]}
        data["awayTeam"] = {"@type": "SportsTeam", "name": e["away"]}
        data["competitor"] = [data["homeTeam"], data["awayTeam"]]
        data["performer"] = data["competitor"]
    elif e.get("participants"):
        data["performer"] = [{"@type": "Person", "name": p} for p in e["participants"]]
    elif e["sport"] == "f1" and F1_DRIVERS:  # coureurs van dit seizoen (uit de WK-stand)
        data["performer"] = [{"@type": "Person", "name": d["name"]} for d in F1_DRIVERS]
    # Geen geneste superEvent/subEvent: Google ziet die als losse evenementen zonder location/startDate (kritieke fout).
    # De tv-zender staat in de description; het toernooi in de naam van de wedstrijdpagina.
    if e.get("round"):
        data["description"] = desc.rstrip(".") + f" ({e['round']})."
    return data


# ------------------------------------------------------------------ ICS
def ics_escape(s):
    return s.replace("\\", "\\\\").replace(",", "\\,").replace(";", "\\;").replace("\n", "\\n")


def ics(events, name):
    out = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//hoelaatbegint.nl//NL", "CALSCALE:GREGORIAN",
           "METHOD:PUBLISH", f"X-WR-CALNAME:{ics_escape(name)}", "X-WR-TIMEZONE:Europe/Amsterdam",
           "REFRESH-INTERVAL;VALUE=DURATION:PT6H", "X-PUBLISHED-TTL:PT6H"]
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    for e in events:
        out += ["BEGIN:VEVENT", f"UID:{e['id']}@hoelaatbegint.nl", f"DTSTAMP:{stamp}"]
        if e.get("start"):
            out.append("DTSTART:" + e["dt"].strftime("%Y%m%dT%H%M%SZ"))
            out.append("DTEND:" + e["end_dt"].strftime("%Y%m%dT%H%M%SZ"))
        else:
            out.append("DTSTART;VALUE=DATE:" + e["day"].strftime("%Y%m%d"))
            out.append("DTEND;VALUE=DATE:" + (e["end_day"] + timedelta(days=1)).strftime("%Y%m%d"))
        summary = e["title"] + (f" ({e['tv']})" if e.get("tv") else "")
        out.append("SUMMARY:" + ics_escape(summary))
        desc = " · ".join(x for x in [e.get("round"), e.get("time_note"), e.get("note"),
                                       f"Meer info: {BASE}{e['url']}"] if x)
        out.append("DESCRIPTION:" + ics_escape(desc))
        if e.get("city"):
            out.append("LOCATION:" + ics_escape(", ".join(x for x in [e.get("venue"), e.get("city")] if x)))
        out.append(f"URL:{BASE}{e['url']}")
        if e.get("start"):
            out += ["BEGIN:VALARM", "TRIGGER:-PT30M", "ACTION:DISPLAY", "DESCRIPTION:" + ics_escape(e["title"] + " begint over 30 minuten"), "END:VALARM"]
        out.append("END:VEVENT")
    out.append("END:VCALENDAR")
    lines = []
    for line in out:  # vouwen op 75 octets
        b = line.encode()
        while len(b) > 74:
            cut = 74
            while (b[cut] & 0xC0) == 0x80:
                cut -= 1
            lines.append(b[:cut].decode())
            b = b" " + b[cut:]
        lines.append(b.decode())
    return "\r\n".join(lines) + "\r\n"


# ------------------------------------------------------------------ templates
BASE_TPL = r"""<!doctype html>
<html lang="nl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{{ title }}</title>
<meta name="description" content="{{ description }}">
<link rel="canonical" href="{{ base }}{{ path }}">
<meta name="robots" content="{{ 'index' if index else 'noindex' }},follow,max-image-preview:large">
<meta property="og:type" content="website"><meta property="og:locale" content="nl_NL">
<meta property="og:site_name" content="hoelaatbegint.nl"><meta property="og:title" content="{{ title }}">
<meta property="og:description" content="{{ description }}"><meta property="og:url" content="{{ base }}{{ path }}">
<meta property="og:image" content="{{ base }}/assets/og/{{ og }}.png"><meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#0E1A2B">
<link rel="icon" href="/assets/logo.svg" type="image/svg+xml">
<link rel="preload" href="/assets/fonts/barlow-condensed-latin-800-normal.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="/assets/fonts/barlow-condensed-latin-800-normal.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="/assets/fonts/inter-latin-400-normal.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="/assets/style.css?v={{ version }}">
{% for ld in jsonld %}<script type="application/ld+json">{{ ld|safe }}</script>
{% endfor %}{% if cfg.cloudflare_analytics_token %}<script defer src="https://static.cloudflareinsights.com/beacon.min.js" data-cf-beacon='{"token": "{{ cfg.cloudflare_analytics_token }}"}'></script>{% endif %}
{% if cfg.plausible_domain %}<script defer data-domain="{{ cfg.plausible_domain }}" src="https://plausible.io/js/script.outbound-links.tagged-events.js"></script>{% endif %}
{% if cfg.onesignal_app_id %}<script src="https://cdn.onesignal.com/sdks/web/v16/OneSignalSDK.page.js" defer></script>
<script>window.OneSignalDeferred=window.OneSignalDeferred||[];OneSignalDeferred.push(async function(O){await O.init({appId:"{{ cfg.onesignal_app_id }}"});});</script>{% endif %}
</head>
<body>
<a class="skip" href="#main">Naar de inhoud</a>
<header class="site-head"><div class="wrap">
<a class="brand" href="/" aria-label="hoelaatbegint.nl, naar de homepage">{{ logo|safe }}<span>hoelaat<b>begint</b><i>.nl</i></span></a>
<nav class="nav" aria-label="Sporten">
<a class="today" href="/vandaag/">Vandaag</a>
{% for key, label, subs in nav %}{% set here = active_path in subs|map(attribute=1)|list %}<details class="more dd"><summary{% if here %} aria-current="page"{% endif %}>{{ label }}</summary>
<div class="more-panel">{% for n, u in subs %}<a href="{{ u }}"{% if u == active_path %} aria-current="page"{% endif %}>{% if loop.first %}<span class="mi">{{ icons[key]|safe }}</span>{% endif %}{{ n }}</a>{% endfor %}</div></details>
{% endfor %}<details class="more dd plain"><summary{% if active_path in more_nav|map(attribute=2)|list %} aria-current="page"{% endif %}>Meer</summary>
<div class="more-panel">{% for key, n, u in more_nav %}<a href="{{ u }}"{% if u == active_path %} aria-current="page"{% endif %}><span class="mi">{{ icons[key]|safe }}</span>{{ n }}</a>{% endfor %}</div></details>
</nav>{% if cfg.instagram_url %}<a class="ig" href="{{ cfg.instagram_url }}" rel="noopener" target="_blank" aria-label="Volg ons op Instagram">{{ ig|safe }}</a>{% endif %}</div></header>
<main id="main">
{{ body|safe }}
{% if author %}<section class="author-sec"><div class="wrap"><aside class="author" aria-label="Over de auteur">
<img src="{{ cfg.owner_photo }}" alt="{{ cfg.owner }}" width="88" height="88" loading="lazy">
<div><div class="author-k">Over de auteur</div>
<div class="author-n"><a href="/over/">{{ cfg.owner }}</a></div>
<p>{{ cfg.owner }} is SEO-specialist en de maker van hoelaatbegint.nl. Hij bepaalt welke bronnen we gebruiken en hoe tijden worden gecontroleerd. Aanvangstijden worden automatisch opgehaald bij de organisatoren en zenders, elke 15 minuten bijgewerkt en bij twee bronnen vergeleken.</p>
<p class="author-l"><a href="/over/">Zo werken we</a> · <a href="mailto:{{ cfg.contact_email }}?subject=Correctie">Fout gezien?</a></p></div>
</aside></div></section>{% endif %}
</main>
<footer class="site-foot"><div class="wrap">
<div class="cols">
<div><a class="brand" href="/">{{ logo|safe }}<span>hoelaat<b>begint</b><i>.nl</i></span></a>
<p>Elke aftrap, elke start. In Nederlandse tijd. Tijden worden elke 15 minuten automatisch gecontroleerd bij twee bronnen.</p>
{% if cfg.instagram_url %}<p><a class="ig-foot" href="{{ cfg.instagram_url }}" rel="noopener" target="_blank">{{ ig|safe }} Elke ochtend om 07:00 het sportprogramma: volg @hoelaatbegint</a></p>{% endif %}</div>
<div><p class="foot-h">Sporten</p><ul>{% for key, s in sports.items() %}<li><a href="/{{ s.page }}/">{{ s.name }}</a></li>{% endfor %}</ul></div>
<div><p class="foot-h">Handig</p><ul><li><a href="/vandaag/">Sport op tv vandaag</a></li><li><a href="/formule-1/kalender/">F1 kalender 2027</a></li><li><a href="/formule-1/stand/">F1 stand</a></li><li><a href="/voetbal/op-tv/">Voetbal op tv</a></li><li><a href="/eredivisie/">Eredivisie programma</a></li><li><a href="/agenda/">Agenda-abonnement</a></li><li><a href="/wk-darts/#nederlanders">Nederlanders op het WK darts</a></li><li><a href="/ajax/">Hoe laat speelt Ajax?</a></li><li><a href="/feyenoord/">Hoe laat speelt Feyenoord?</a></li><li><a href="/psv/">Hoe laat speelt PSV?</a></li></ul></div>
<div><p class="foot-h">Over</p><ul><li><a href="/over/">Over ons &amp; werkwijze</a></li><li><a href="/privacy/">Privacy</a></li><li><a href="mailto:{{ cfg.contact_email }}?subject=Correctie">Klopt er iets niet?</a></li></ul></div>
</div>
<div class="legal"><span>© {{ year }} hoelaatbegint.nl · Tijden onder voorbehoud van wijzigingen door organisatoren en zenders.</span><span>Bijgewerkt: {{ built }}</span></div>
</div></footer>
<script src="/assets/app.js?v={{ version }}" defer></script>
</body></html>"""

MACROS = r"""
{% macro evrow(e, show_day=False) -%}
<li class="ev" {% if e.start %}data-start="{{ e.start }}" data-sport="{{ e.sport }}"{% else %}data-end-date="{{ e.end_day.isoformat() }}"{% endif %}>
  {% if e.time %}<div class="t">{{ e.time }}</div>{% else %}<div class="t na">{% if e.is_range %}{{ e.day.day }}–{{ e.end_day.day }} {{ months[e.end_day.month-1][:3] }}{% else %}tijd<br>volgt{% endif %}</div>{% endif %}
  <div><div class="n"><a href="{{ e.url }}">{{ e.title }}</a></div>
  <div class="m">{% if show_day %}{{ e.day_label }} · {% endif %}{{ e.meta }}{% if e.time_note %} · {{ e.time_note }}{% endif %}</div></div>
  <div class="r"><span class="tag">{{ e.sport_name }}</span>{% if e.start %}<span class="countdown"></span>{% endif %}</div>
</li>
{%- endmacro %}
{% macro schedule(events, show_day=False) -%}
{% set ns = namespace(day=None) %}
<ul class="events">
{% for e in events %}{% if not show_day and e.day_label != ns.day %}{% set ns.day = e.day_label %}</ul><div class="day">{{ e.day_label }}</div><ul class="events">{% endif %}{{ evrow(e, show_day) }}{% endfor %}
</ul>
{%- endmacro %}
{% macro answer(e, label) -%}
<div class="answer" data-start="{{ e.start }}" data-sport="{{ e.sport }}">
  <div><div class="label">{{ label }} <span class="badge">{{ e.sport_name }}</span></div>
  <div class="what">{{ e.title }}</div>
  <div class="when">{{ e.day_label|capitalize }}{% if e.tv %} · live op <strong>{{ e.tv_detail }}</strong>{% endif %}</div></div>
  <div class="time">{{ e.time }}<small class="countdown"></small></div>
  <div class="actions">
    <a class="btn primary" href="/agenda/{{ e.id }}.ics" data-event="agenda">{{ cal|safe }} Zet in mijn agenda</a>
    <button class="btn" type="button" data-push="{{ e.sport }}">{{ bell|safe }} Melding 30 min vooraf</button>
    <a class="btn" href="#" data-share="{{ e.title }}: {{ e.day_label }} om {{ e.time }}{% if e.tv %} op {{ e.tv }}{% endif %}">{{ share|safe }} Deel</a>
  </div>
</div>
{%- endmacro %}
{% macro opinion(e) -%}
{% if e.opinion %}<aside class="kijk" aria-label="De kijk van {{ cfg.owner }}">
<img class="kijk-foto" src="{{ cfg.owner_photo }}" alt="{{ cfg.owner }}" width="76" height="76" loading="lazy">
<div class="kijk-body"><div class="kijk-naam"><span>De kijk van</span> <a href="/over/">{{ cfg.owner }}</a></div>
<blockquote>{{ e.opinion }}</blockquote></div>
</aside>{% endif %}
{%- endmacro %}
{% macro faqblock(faq) -%}
<section id="faq"><div class="wrap"><h2>Veelgestelde vragen</h2>
{% for q, a in faq %}<details{% if loop.first %} open{% endif %}><summary>{{ q }}</summary><p>{{ a }}</p></details>{% endfor %}
</div></section>
{%- endmacro %}
"""

HOME = MACROS + r"""
<section class="hero"><div class="wrap">
<h1>Hoe laat begint het?</h1>
<p class="lede">Alle sport met Nederlanders, in Nederlandse tijd. Met zender, countdown en wat er gebeurt als ze doorgaan. Automatisch bijgewerkt, elke 15 minuten.</p>
<div class="byline"><img src="/assets/ronald-64.jpg" alt="" width="28" height="28"><span>Door <a href="/over/">{{ cfg.owner }}</a></span><span class="checked">Laatst gecontroleerd: {{ built }}</span></div>
</div></section>
<div class="wrap">{{ answer(next, "Eerstvolgende met Nederlanders") }}{{ opinion(next) }}</div>
<section><div class="wrap"><h2>Sporten</h2>
<div class="grid sports">
{% for key, s in sports.items() %}<a class="card sport-card" href="/{{ s.page }}/"><div class="ico">{{ icons[key]|safe }}</div><h3>{{ s.name }}</h3><p class="next">{{ nexts[key] }}</p></a>{% endfor %}
</div></div></section>
<section><div class="wrap"><h2>Binnenkort</h2>
{{ schedule(upcoming) }}
<p style="margin-top:18px"><a class="btn primary" href="/agenda/">{{ cal|safe }} Alles in je agenda</a></p>
</div></section>
"""

VANDAAG = MACROS + r"""
<section class="hero"><div class="wrap">
<div class="crumbs"><a href="/">Home</a> › Vandaag</div>
<h1>Sport op tv vandaag</h1>
<p class="lede">Alle sport met Nederlanders van <strong>{{ today_label }}</strong>, met aanvangstijd en zender.</p>
<div class="byline"><img src="/assets/ronald-64.jpg" alt="" width="28" height="28"><span>Door <a href="/over/">{{ cfg.owner }}</a></span><span class="checked">Laatst gecontroleerd: {{ built }}</span></div>
</div></section>
<section><div class="wrap">
{% if tl %}<h2>Tv-gids van vandaag</h2>
<div class="tl" data-tl-start="{{ tl.start_iso }}" data-tl-span="{{ tl.span }}"><div class="tl-in">
<div class="tl-head"><div class="tl-ch">Zender</div><div class="tl-axis">{% for h in tl.hours %}<span style="left:{{ h.left }}%">{{ h.label }}</span>{% endfor %}</div></div>
{% for ch in tl.rows %}<div class="tl-row"><div class="tl-ch">{{ ch.name }}</div><div class="tl-track">{% for b in ch.blocks %}<a class="tl-b" href="{{ b.e.url }}" data-start="{{ b.e.start }}" data-sport="{{ b.e.sport }}" style="left:{{ b.left }}%;width:{{ b.width }}%" title="{{ b.e.time }} {{ b.e.title }}"><b>{{ b.e.time }}</b> {{ b.e.title }}</a>{% endfor %}</div></div>{% endfor %}
<div class="tl-now" hidden></div></div></div>
<p class="note">Oranje = begint als eerstvolgende. Tik op een blok voor countdown en agenda-knop.</p>
<h2 style="margin-top:32px">Alles van vandaag</h2>{% endif %}
{% if today %}{{ schedule(today, True) }}{% else %}<div class="card"><h3>Vandaag geen Nederlandse topsport</h3><p class="muted">Hieronder zie je wat er de komende dagen aankomt.</p></div>{% endif %}
<h2 style="margin-top:36px">De komende dagen</h2>
{{ schedule(soon) }}
</div></section>
"""

TOURNAMENT = MACROS + r"""
<section class="hero"><div class="wrap">
<div class="crumbs"><a href="/">Home</a> › {{ t.name }}</div>
<h1>{{ t.h1 }}</h1>
<p class="lede">{% if t.sport == "clubs" and next and t.slug != "clubs" %}{{ t.name }} speelt <strong>{{ next.day_label }} om {{ next.time }}</strong>: {{ next.title }}{% if next.tv %}, live op <strong>{{ next.tv_detail }}</strong>{% endif %}. Hieronder het hele programma, in Nederlandse tijd.{% else %}{{ t.answer|safe }}{% endif %}</p>
<div class="byline"><img src="/assets/ronald-64.jpg" alt="" width="28" height="28"><span>Door <a href="/over/">{{ cfg.owner }}</a></span><span class="checked">Laatst gecontroleerd: {{ built }}</span></div>
</div></section>
{% if next %}<div class="wrap">{{ answer(next, "Eerstvolgende") }}{{ opinion(next) }}</div>{% endif %}
<section><div class="wrap two">
<div class="prose"><h2>In het kort</h2><p>{{ t.intro }}</p></div>
<table class="facts">{% for k, v in t.facts %}<tr><th>{{ k }}</th><td>{{ v }}</td></tr>{% endfor %}</table>
</div></section>
<section><div class="wrap"><h2>Schema</h2>
<p class="note">Alle tijden in Nederlandse tijd.</p>
{% if events %}{{ schedule(events) }}{% else %}<div class="card"><h3>Het programma wordt automatisch geladen</h3><p class="muted">Zodra de eerstvolgende wedstrijden zijn opgehaald, staan ze hier met tijd en zender.</p></div>{% endif %}
{% if t.clubs %}<div class="grid sports" style="margin-top:16px">{% for n, s in t.clubs %}<a class="card sport-card" href="/{{ s }}/"><div class="ico">{{ icons['clubs']|safe }}</div><h3>{{ n }}</h3><p class="next">Programma en zender</p></a>{% endfor %}</div>{% endif %}
<p style="margin-top:16px"><a class="btn primary" href="/agenda/{{ t.slug }}.ics" data-event="agenda">{{ cal|safe }} Abonneer op dit schema</a></p>
</div></section>
{% if t.scenario %}<section><div class="wrap"><h2>{{ t.scenario_title }}</h2>
<ol class="scenario">{% for a, b in t.scenario %}<li><b>{{ a }}</b>{{ b }}</li>{% endfor %}</ol>
<p class="note">{{ t.scenario_note }}</p></div></section>{% endif %}
{% if t.players %}<section id="nederlanders"><div class="wrap"><h2>{{ t.players_title }}</h2>
<div class="players">{% for p, how in t.players %}<a href="/darts/{{ slug(p) }}/"><b>{{ p }}</b><span>{{ how }}</span></a>{% endfor %}</div>
<p class="note">{{ t.players_note }}</p></div></section>{% endif %}
{% if related %}<section><div class="wrap"><h2>Ook handig</h2><p>{% for n, u in related %}<a class="btn" href="{{ u }}" style="margin:0 8px 8px 0">{{ n }}</a>{% endfor %}</p></div></section>{% endif %}
{{ faqblock(t.faq) }}
<section><div class="wrap sources"><h2>Bronnen</h2><ul>{% for n, u in t.sources %}<li><a href="{{ u }}" rel="nofollow noopener" target="_blank">{{ n }}</a></li>{% endfor %}</ul></div></section>
"""

PLAYER = MACROS + r"""
<section class="hero"><div class="wrap">
<div class="crumbs"><a href="/">Home</a> › <a href="/wk-darts/">WK darts</a> › {{ p }}</div>
<h1>Hoe laat speelt {{ p }}?</h1>
<p class="lede">{% if mine %}{{ p }} speelt zijn volgende WK-wedstrijd op <strong>{{ mine[0].day_label }}{% if mine[0].time %} om {{ mine[0].time }}{% endif %}</strong>.{% else %}{{ p }} staat op de deelnemerslijst van het <strong>WK darts 2027</strong> (11 december – 3 januari, Alexandra Palace). Tegen wie en hoe laat hij zijn eerste wedstrijd speelt, wordt bepaald bij de <strong>loting op maandag 30 november</strong>; daarna staat het hier automatisch.{% endif %}</p>
<div class="byline"><img src="/assets/ronald-64.jpg" alt="" width="28" height="28"><span>Door <a href="/over/">{{ cfg.owner }}</a></span><span class="checked">Laatst gecontroleerd: {{ built }}</span></div>
</div></section>
{% if mine %}<div class="wrap">{% if mine[0].start %}{{ answer(mine[0], "Volgende wedstrijd") }}{% endif %}</div>{% endif %}
<section><div class="wrap two">
<div class="prose"><h2>{{ p }} op het WK</h2>
<p>{{ p }} plaatste zich via de {{ how }}. Alle 128 spelers beginnen in ronde 1, die loopt van vrijdag 11 tot en met zaterdag 19 december. Er zijn middagsessies vanaf 13:30 en avondsessies vanaf 20:00 Nederlandse tijd. Je kijkt live op Viaplay.</p></div>
<table class="facts"><tr><th>Toernooi</th><td><a href="/wk-darts/">WK darts 2027</a></td></tr><tr><th>Gekwalificeerd via</th><td>{{ how }}</td></tr><tr><th>Ronde 1</th><td>11 t/m 19 december</td></tr><tr><th>Op tv</th><td>Viaplay</td></tr></table>
</div></section>
<section><div class="wrap"><h2>Wanneer speelt {{ p.split(' ')[0] }} als hij doorgaat?</h2>
<ol class="scenario">{% for a, b in t.scenario %}<li><b>{{ a }}</b>{{ b }}</li>{% endfor %}</ol>
<p class="note">{{ t.scenario_note }}</p></div></section>
<section><div class="wrap"><h2>Andere Nederlanders op het WK</h2>
<div class="players">{% for q, h in t.players if q != p %}<a href="/darts/{{ slug(q) }}/"><b>{{ q }}</b><span>{{ h }}</span></a>{% endfor %}</div></div></section>
{{ faqblock(faq) }}
"""

MATCH = MACROS + r"""
<section class="hero"><div class="wrap">
<div class="crumbs"><a href="/">Home</a> › <a href="/{{ t.slug }}/">{{ t.name }}</a> › {{ e.title }}</div>
<h1>{{ e.h1 or "Hoe laat begint " ~ e.title ~ "?" }}</h1>
<p class="lede">{{ e.title }} begint <strong>{{ e.day_label }} om {{ e.time }}</strong> Nederlandse tijd{% if e.city %} in {{ e.city }}{% endif %}.{% if e.tv %} Je kijkt live op <strong>{{ e.tv_detail }}</strong>.{% endif %}</p>
<div class="byline"><img src="/assets/ronald-64.jpg" alt="" width="28" height="28"><span>Door <a href="/over/">{{ cfg.owner }}</a></span><span class="checked">Laatst gecontroleerd: {{ built }}</span></div>
</div></section>
<div class="wrap">{{ answer(e, e.round or "Wedstrijd") }}{{ opinion(e) }}</div>
<section><div class="wrap two">
<div class="prose"><h2>Wat je moet weten</h2><p>{{ e.ai_intro or e.note or t.intro }}</p>
{% if e.tv %}<p><a class="btn" href="{{ tvlink }}" rel="nofollow sponsored noopener" target="_blank" data-event="zender">Kijk live op {{ e.tv }}</a></p>{% if aff %}<p class="aff">Via deze link verdienen we mogelijk een kleine vergoeding.</p>{% endif %}{% endif %}</div>
<table class="facts">
<tr><th>Datum</th><td>{{ e.day_label|capitalize }} {{ e.day.year }}</td></tr>
<tr><th>Aanvang</th><td>{{ e.time }} (Nederlandse tijd)</td></tr>
{% if e.round %}<tr><th>Ronde</th><td>{{ e.round }}</td></tr>{% endif %}
{% if e.city %}<tr><th>Plaats</th><td>{{ e.venue ~ ', ' if e.venue and e.venue != e.city else '' }}{{ e.city }}</td></tr>{% endif %}
{% if e.tv %}<tr><th>Op tv</th><td>{{ e.tv_detail }}</td></tr>{% endif %}
<tr><th>Bron</th><td><a href="{{ e.source }}" rel="nofollow noopener" target="_blank">Bekijk bron</a></td></tr>
</table></div></section>
{% if t.scenario %}<section><div class="wrap"><h2>{{ t.scenario_title }}</h2>
<ol class="scenario">{% for a, b in t.scenario %}<li><b>{{ a }}</b>{{ b }}</li>{% endfor %}</ol></div></section>{% endif %}
<section><div class="wrap"><h2>Meer van {{ t.name }}</h2>{{ schedule(more) }}</div></section>
"""

VIEW = MACROS + r"""
<section class="hero"><div class="wrap">
<div class="crumbs"><a href="/">Home</a> › <a href="{{ parent }}">{{ v.name }}</a> › {{ v.h1 }}</div>
<h1>{{ v.h1 }}</h1>
<p class="lede">{{ lede|safe }}</p>
<div class="byline"><img src="/assets/ronald-64.jpg" alt="" width="28" height="28"><span>Door <a href="/over/">{{ cfg.owner }}</a></span><span class="checked">Laatst gecontroleerd: {{ built }}</span></div>
</div></section>
{% if nx %}<div class="wrap">{{ answer(nx, label) }}{{ opinion(nx) }}</div>{% endif %}
<section><div class="wrap">
{% if v.mode == "kalender" %}<div class="prose"><p>{{ v.intro }}</p></div>
<h2>Alle races</h2><p class="note">Tijden in Nederlandse tijd. Staat er 'tijd volgt', dan is de starttijd nog niet bekendgemaakt.</p>{{ schedule(list, True) }}
{% elif v.mode == "vandaag" %}<h2>{{ today_label|capitalize }}</h2>
{% if list %}{{ schedule(list, True) }}{% else %}<div class="card"><h3>Vandaag geen {{ v.name }}</h3><p class="muted">Hieronder zie je wat er de komende dagen aankomt.</p></div>{% endif %}
<h2 style="margin-top:36px">De komende dagen</h2>{% if soon %}{{ schedule(soon) }}{% else %}<p class="muted">Nog niets gepland.</p>{% endif %}
{% else %}<h2>De komende uitzendingen</h2><p class="note">Alle tijden in Nederlandse tijd.</p>
{% if list %}{{ schedule(list) }}{% else %}<div class="card"><h3>Nog geen uitzendingen gepland</h3><p class="muted">Zodra er tijden bekend zijn, staan ze hier.</p></div>{% endif %}
{% if channels %}<h2 style="margin-top:36px">Op welke zender?</h2><table class="facts">{% for n, what in channels %}<tr><th>{{ n }}</th><td>{{ what }}</td></tr>{% endfor %}</table>{% endif %}
{% endif %}
<p style="margin-top:20px">{% for n, u in related %}<a class="btn" href="{{ u }}" style="margin:0 8px 8px 0">{{ n }}</a>{% endfor %}</p>
</div></section>
{{ faqblock(faq) }}
"""

STAND = MACROS + r"""
<section class="hero"><div class="wrap">
<div class="crumbs"><a href="/">Home</a> › <a href="/formule-1/">Formule 1</a> › F1 stand</div>
<h1>F1 stand {{ st.season }}</h1>
<p class="lede">{{ lede|safe }}</p>
<div class="byline"><img src="/assets/ronald-64.jpg" alt="" width="28" height="28"><span>Door <a href="/over/">{{ cfg.owner }}</a></span><span class="checked">Stand na race {{ st.round }} · bijgewerkt {{ fetched }}</span></div>
</div></section>
{% if nx %}<div class="wrap">{{ answer(nx, "Volgende sessie") }}</div>{% endif %}
<section><div class="wrap">
<h2>Coureurs</h2>
<div class="table-wrap"><table class="stand"><thead><tr><th scope="col">#</th><th scope="col">Coureur</th><th scope="col">Team</th><th scope="col" class="num">Zeges</th><th scope="col" class="num">Punten</th></tr></thead><tbody>
{% for r in st.drivers %}<tr{% if r.nationality == "Dutch" %} class="nl"{% endif %}><td>{{ r.pos }}</td><td>{{ r.name }}</td><td>{{ r.team }}</td><td class="num">{{ r.wins }}</td><td class="num"><b>{{ (r.points|int) if r.points == r.points|int else (r.points|string).replace(".", ",") }}</b></td></tr>{% endfor %}
</tbody></table></div>
<h2 style="margin-top:36px">Constructeurs</h2>
<div class="table-wrap"><table class="stand"><thead><tr><th scope="col">#</th><th scope="col">Team</th><th scope="col" class="num">Zeges</th><th scope="col" class="num">Punten</th></tr></thead><tbody>
{% for r in st.constructors %}<tr><td>{{ r.pos }}</td><td>{{ r.name }}</td><td class="num">{{ r.wins }}</td><td class="num"><b>{{ (r.points|int) if r.points == r.points|int else (r.points|string).replace(".", ",") }}</b></td></tr>{% endfor %}
</tbody></table></div>
<p class="note">Bron: <a href="https://www.formula1.com/en/results" rel="noopener" target="_blank">Formula 1</a> via de open Jolpica-database. Automatisch bijgewerkt na elke sessie.</p>
<p style="margin-top:20px"><a class="btn" href="/formule-1/" style="margin:0 8px 8px 0">Alle F1-tijden</a><a class="btn" href="/formule-1/kalender/" style="margin:0 8px 8px 0">F1 kalender 2027</a><a class="btn" href="/formule-1/vandaag/" style="margin:0 8px 8px 0">Formule 1 vandaag</a></p>
</div></section>
{{ faqblock(faq) }}
"""

AGENDA = MACROS + r"""
<section class="hero"><div class="wrap">
<div class="crumbs"><a href="/">Home</a> › Agenda</div>
<h1>Sport in je eigen agenda</h1>
<p class="lede">Abonneer je één keer, en elke Nederlandse wedstrijd staat vanzelf in je agenda, met een herinnering 30 minuten vooraf. Wijzigt een tijd, dan past je agenda zich automatisch aan.</p>
</div></section>
<section><div class="wrap"><div class="grid sports">
<a class="card sport-card" href="webcal://{{ host }}/agenda/alles.ics" data-event="agenda"><div class="ico">{{ cal|safe }}</div><h3>Alles</h3><p class="next">Alle sporten met Nederlanders</p></a>
{% for key, s in sports.items() %}<a class="card sport-card" href="webcal://{{ host }}/agenda/{{ s.page }}.ics" data-event="agenda"><div class="ico">{{ icons[key]|safe }}</div><h3>{{ s.name }}</h3><p class="next">Abonneren</p></a>{% endfor %}
</div>
<div class="prose" style="margin-top:28px"><h2>Zo werkt het</h2>
<p><b>iPhone:</b> tik op een sport en kies <i>Abonneer</i>. <b>Android / Google Agenda:</b> kopieer de link (bijvoorbeeld <code>{{ base }}/agenda/alles.ics</code>) en kies in Google Agenda <i>Andere agenda's › Via URL</i>. <b>Outlook:</b> <i>Agenda toevoegen › Abonneren vanaf internet</i>.</p></div>
</div></section>
"""

PAGE = r"""
<section class="hero"><div class="wrap"><div class="crumbs"><a href="/">Home</a> › {{ h1 }}</div><h1>{{ h1 }}</h1></div></section>
<section><div class="wrap prose">{{ content|safe }}</div></section>
"""

OVER = """<p class="lead">Bij elke grote wedstrijd zoeken honderdduizenden Nederlanders hetzelfde: <b>hoe laat begint het, en waar kan ik het zien?</b> hoelaatbegint.nl geeft dat antwoord in één oogopslag. Voor alle sport met Nederlanders, altijd in Nederlandse tijd.</p>
<div class="about-stats"><div><b>{n_sports}</b><span>sporten en competities</span></div><div><b>{n_events}</b><span>wedstrijden en sessies in de planning</span></div><div><b>15 min</b><span>tussen twee controles</span></div><div><b>07:00</b><span>elke ochtend het programma op Instagram</span></div></div>
<h2>Wat je hier vindt</h2>
<ul><li><b>De aanvangstijd</b> van elke wedstrijd, race of sessie met Nederlanders, met een countdown.</li>
<li><b>De zender</b>: op welk kanaal of welke streamingdienst je het ziet.</li>
<li><b>Wat er gebeurt als ze doorgaan</b>: wanneer de volgende ronde dan is.</li>
<li><b>Een tv-gids van vandaag</b>, per zender op een tijdlijn.</li>
<li><b>Agenda-abonnementen</b> per sport of club, zodat elke wedstrijd vanzelf in je agenda staat.</li></ul>
<h2>Zo werkt het</h2>
<ol class="about-steps"><li><b>Verzamelen.</b> Elke 15 minuten halen we speelschema's op bij sportdatabronnen en officiële organisatoren.</li>
<li><b>Controleren.</b> Een nieuwe of gewijzigde tijd verschijnt pas als een officiële bron hem bevestigt. Spreken bronnen elkaar tegen, dan blijft de laatst bevestigde tijd staan en kijken we het na.</li>
<li><b>Publiceren.</b> Elke pagina laat zien wanneer hij voor het laatst is gecontroleerd en welke bron is gebruikt.</li></ol>
<p>Een voorbeeld: op 25 november 2026 stond Nederland – Tsjechië (EK handbal) bij een tv-aanbieder op donderdag 3 december. De officiële EHF-pagina zei vrijdag 4 december om 20:30. Wij tonen de officiële tijd.</p>
<h2>Welke sporten</h2>
<p>{sport_links}</p>
<h2>Hoe we AI gebruiken</h2>
<p>AI helpt ons officiële bronnen te doorzoeken en schrijft de korte voorbeschouwing bij wedstrijden ("De kijk van Ronald"). Tijden, data en zenders komen altijd uit gecontroleerde bronnen, nooit uit een AI.</p>
<h2>Klopt er iets niet?</h2>
<p>Mail naar <a href="mailto:{email}?subject=Correctie">{email}</a>. We passen het zo snel mogelijk aan; de pagina toont daarna de nieuwe controletijd.</p>
<h2>Advertenties en links</h2>
<p>Bij sommige zenders gebruiken we een partnerlink. Neem je via zo'n link een abonnement, dan krijgen we mogelijk een kleine vergoeding. Dat heeft geen invloed op de informatie die we tonen. We maken geen reclame voor gokken en tonen geen odds.</p>
<h2>Wie zit erachter</h2>
<div class="about-who"><img src="{photo}" alt="{owner}" width="64" height="64" loading="lazy" onerror="this.style.display='none'"><p>hoelaatbegint.nl is een project van <b>{owner}</b>, SEO-specialist en sportliefhebber. Volg de site op <a href="{instagram}" rel="noopener" target="_blank">Instagram @hoelaatbegint</a> of mail naar <a href="mailto:{email}">{email}</a>.</p></div>"""

PRIVACY = """<p>hoelaatbegint.nl verzamelt zo weinig mogelijk gegevens.</p>
<h2>Bezoekstatistieken</h2><p>We meten bezoeken met Cloudflare Web Analytics. Dat gebeurt zonder cookies en zonder persoonsgegevens te bewaren. Daarom vragen we geen toestemming en tonen we geen cookiebanner.</p>
<h2>Pushmeldingen</h2><p>Als je meldingen aanzet, krijg je een anonieme abonnements-ID via OneSignal. Je kunt meldingen altijd uitzetten in je browser.</p>
<h2>Agenda-abonnementen</h2><p>Een agenda-abonnement is een openbaar bestand dat je agenda zelf ophaalt. We weten niet wie zich abonneert.</p>
<h2>Contact</h2><p>Een mail naar ons bewaren we maximaal 12 maanden. Vragen over privacy: <a href="mailto:{email}">{email}</a>.</p>
<h2>Verwerkers</h2><p>Cloudflare (hosting en statistieken), OneSignal (pushmeldingen).</p>"""


# ------------------------------------------------------------------ build
def main():
    now = datetime.fromisoformat(os.environ["BUILD_NOW"]) if os.environ.get("BUILD_NOW") else datetime.now(UTC)  # BUILD_NOW alleen om te testen
    events_raw = json.loads((ROOT / "data" / "events.json").read_text(encoding="utf-8"))["events"]
    tournaments = json.loads((ROOT / "data" / "tournaments.json").read_text(encoding="utf-8"))
    broadcasters = json.loads((ROOT / "data" / "broadcasters.json").read_text(encoding="utf-8"))
    tournaments_known = json.loads((ROOT / "data" / "tournaments.json").read_text(encoding="utf-8"))
    # Vangnet: onbekende sport of pagina nooit de hele build laten breken
    events_raw = [e for e in events_raw if e.get("sport") in SPORTS]
    for e in events_raw:
        if e.get("tournament") not in tournaments_known:
            e["tournament"] = SPORTS[e["sport"]]["page"] if SPORTS[e["sport"]]["page"] in tournaments_known else next(iter(tournaments_known))
    for e in events_raw:  # clubwedstrijden uit de AI-controle aan de juiste clubpagina koppelen
        if e["sport"] == "clubs" and not e.get("clubs"):
            txt = slugify(e["title"] + " " + " ".join(e.get("participants", [])))
            e["clubs"] = [c for c in ("ajax", "feyenoord", "psv") if c in txt]
    events = sorted((prep(e, broadcasters, now) for e in events_raw), key=lambda e: (e["dt"], e["id"]))
    upcoming_all = [e for e in events if e["upcoming"]]
    upcoming = [e for e in upcoming_all if e["nl"]]  # home/vandaag: alleen sport met Nederlanders
    built = now.astimezone(NL)
    built_label = f"{d_label(built.date())}, {built.strftime('%H:%M')}"
    version = built.strftime("%Y%m%d%H%M")
    logo = (ROOT / "site" / "assets" / "logo.svg").read_text().replace('role="img" aria-label="hoelaatbegint.nl"', 'aria-hidden="true"')

    env = Environment(loader=BaseLoader(), autoescape=True)
    env.globals.update(nav=NAV, more_nav=MORE_NAV, months=MONTHS, ig=IG_ICON, cal=CAL_ICON, bell=BELL_ICON, share=SHARE_ICON, slug=slugify,
                       icons=ICONS, sports=SPORTS, built=built_label, base=BASE, cfg=CONFIG)
    base_tpl = env.from_string(BASE_TPL)

    if DIST.exists():
        shutil.rmtree(DIST)
    shutil.copytree(ROOT / "site" / "assets", DIST / "assets")
    (DIST / "agenda").mkdir(parents=True)
    pages = []

    overrides_file = ROOT / "data" / "title_overrides.json"
    overrides = json.loads(overrides_file.read_text(encoding="utf-8")) if overrides_file.exists() else {}

    lastmod_file = ROOT / "data" / "lastmod.json"
    lastmods = json.loads(lastmod_file.read_text(encoding="utf-8")) if lastmod_file.exists() else {}
    stamp = now.strftime("%Y-%m-%dT%H:%M:%SZ")

    def write(path, title, description, body, og="default", active=None, jsonld=(), priority="0.7", index=True):
        if not (ROOT / "site" / "og" / f"{og}.png").exists():
            og = "default"
        title = overrides.get(path, {}).get("title", title)
        description = overrides.get(path, {}).get("description", description)
        if len(title) > 60 and title.endswith(" | hoelaatbegint.nl"):
            title = title[: -len(" | hoelaatbegint.nl")]  # merknaam weg als de titel anders wordt afgekapt
        # lastmod alleen bij echte inhoudswijziging (tijdstempels tellen niet mee)
        digest = hashlib.sha1((title + description + body.replace(built_label, "")).encode()).hexdigest()[:16]
        prev = lastmods.get(path)
        if not prev or prev[0] != digest:
            lastmods[path] = [digest, stamp]
        html = base_tpl.render(title=title, description=description, path=path, active_path=path, author=path not in ("/over/", "/privacy/", "/agenda/"), body=body, og=og, active=active,
                               jsonld=[json.dumps(x, ensure_ascii=False).replace("</", "<\\/") for x in list(jsonld) + [webpage(path, title)] if x], logo=logo,
                               version=version, year=built.year, index=index)
        out = DIST / path.strip("/") / "index.html" if path != "/" else DIST / "index.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(html, encoding="utf-8")
        pages.append((path, priority, index))

    def webpage(path, title):
        if path in ("/over/", "/privacy/", "/agenda/"):
            return None
        return {"@context": "https://schema.org", "@type": "WebPage", "url": BASE + path, "name": title.split(" | ")[0],
                "inLanguage": "nl-NL", "dateModified": lastmods.get(path, [None, stamp])[1],
                "author": {"@type": "Person", "name": CONFIG["owner"], "url": BASE + "/over/", "jobTitle": "SEO-specialist",
                           "image": BASE + CONFIG.get("owner_photo", ""),
                           "sameAs": [x for x in (CONFIG.get("owner_linkedin"), CONFIG["owner_url"]) if x]},
                "publisher": {"@type": "Organization", "name": "hoelaatbegint.nl", "url": BASE}}

    org = {"@context": "https://schema.org", "@type": "Organization", "name": "hoelaatbegint.nl", "url": BASE,
           "logo": BASE + "/assets/logo.svg", "sameAs": CONFIG.get("same_as", [])}

    def crumbs(*items):
        return {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": n, "item": BASE + u} for i, (n, u) in enumerate(items)]}

    def faq_ld(faq):
        return {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]}

    views = json.loads((ROOT / "data" / "pages.json").read_text(encoding="utf-8"))["views"]
    timed_nl = [e for e in upcoming if e.get("start") and e["nl"] and e["dt"] > now]

    # --- home
    nexts = {}
    for key in SPORTS:
        nx = next((e for e in upcoming if e["sport"] == key), None)
        nexts[key] = (f"{nx['day_label']}{', ' + nx['time'] if nx['time'] else ''}" if nx else "Binnenkort")
    body = env.from_string(HOME).render(next=timed_nl[0], upcoming=upcoming[:14], nexts=nexts)
    write("/", "Hoe laat begint het? Sport met Nederlanders in Nederlandse tijd | hoelaatbegint.nl",
          "Hoe laat speelt Nederland? Aanvangstijden, zender en countdown voor darts, schaatsen, Oranje, handbal, F1, veldrijden en hockey. Elke 15 minuten bijgewerkt.",
          body, jsonld=[org, {"@context": "https://schema.org", "@type": "WebSite", "name": "hoelaatbegint.nl", "url": BASE + "/",
                       "inLanguage": "nl-NL", "description": "Aanvangstijden van sport met Nederlanders, in Nederlandse tijd, met zender."}], priority="1.0")

    # --- vandaag
    today = built.date()
    todays = [e for e in upcoming if e["day"] <= today <= e["end_day"]]
    soon = [e for e in upcoming if e["day"] > today][:10]
    body = env.from_string(VANDAAG).render(today=todays, soon=soon, today_label=d_label(today), tl=timeline(todays, today))
    write("/vandaag/", f"Sport op tv vandaag ({d_label(today)}) | hoelaatbegint.nl",
          f"Welke sport is er vandaag op tv? Alle wedstrijden met Nederlanders van {d_label(today)}, met aanvangstijd en zender.",
          body, jsonld=[crumbs(("Home", "/"), ("Vandaag", "/vandaag/"))], priority="0.9")

    # --- toernooien
    for slug, t in tournaments.items():
        if slug == "clubs":
            tev = [e for e in events if e["sport"] == "clubs" and e["nl"]]
        elif slug == "ek-2028":
            tev = [e for e in events if e["tournament"] == slug or ("EK" in e["title"] and "2028" in e["title"])]
        elif slug == "eredivisie":
            tev = [e for e in events if e["sport"] == "clubs" and "eredivisie" in (e.get("round") or "").lower()]
        else:
            tev = [e for e in events if e["tournament"] == slug or slug in e.get("clubs", [])]
        tup = [e for e in tev if e["upcoming"]] or tev
        nx = next((e for e in tup if e.get("start") and e["dt"] > now and e["nl"]), None)
        related = [(x["h1"], x["path"]) for x in views if x.get("club") == slug or (not x.get("club") and t.get("sport") in x.get("sports", []) and slug != "clubs")]
        related += [tuple(x) for x in t.get("related", [])]
        body = env.from_string(TOURNAMENT).render(t=t, events=tup, next=nx, related=related)
        lds = [crumbs(("Home", "/"), (t["name"], f"/{slug}/")), faq_ld(t["faq"])] + [jsonld_event(e) for e in tup if e.get("start")]
        write(f"/{slug}/", f"{t['title']} | hoelaatbegint.nl", t["description"], body, og=slug,
              active=slug, jsonld=lds, priority="0.9")
        (DIST / "agenda" / f"{slug}.ics").write_text(ics(tev, f"{t['name']} · hoelaatbegint.nl"), encoding="utf-8")

        # spelerspagina's
        for p, how in t.get("players", []):
            mine = [e for e in tup if p in e.get("participants", [])]
            faq = [[f"Hoe laat speelt {p} op het WK darts?", f"Dat wordt bekend na de loting op maandag 30 november. Daarna staat de exacte dag en tijd op deze pagina."],
                   [f"Waar kan ik {p} live zien?", "Het WK darts is in Nederland live te zien op Viaplay."],
                   [f"Wanneer is de finale?", "Zondag 3 januari 2027 om 21:00 Nederlandse tijd."]]
            body = env.from_string(PLAYER).render(p=p, how=how, t=t, mine=mine, faq=faq)
            write(f"/darts/{slugify(p)}/", f"Hoe laat speelt {p} op het WK darts 2027? | hoelaatbegint.nl",
                  f"Wanneer en hoe laat speelt {p} op het WK darts 2027? Datum, tijd, tegenstander, zender en wanneer hij speelt als hij doorgaat.",
                  body, og=slug, active=slug,
                  jsonld=[crumbs(("Home", "/"), ("WK darts", "/wk-darts/"), (p, f"/darts/{slugify(p)}/")), faq_ld(faq)], priority="0.6")

    # --- wedstrijdpagina's (kleine duels: noindex; 3 dagen na afloop: 301 naar de sport-/clubpagina)
    redirects = []
    for e in events:
        if not (e.get("page") and e.get("start")):
            continue
        t = tournaments[e["tournament"]]
        if e["end_dt"] < now - timedelta(days=3):
            if e["end_dt"] > now - timedelta(days=400):
                redirects.append(f"{e['url']} /{t['slug']}/ 301")
            continue
        more = [x for x in events if x["tournament"] == e["tournament"] and x["id"] != e["id"] and x["upcoming"]][:6]
        b = broadcasters.get(e.get("broadcaster", ""), {})
        body = env.from_string(MATCH).render(e=e, t=t, more=more, tvlink=b.get("affiliate_url") or b.get("url", "#"), aff=bool(b.get("affiliate_url")))
        write(e["url"], f"{e.get('h1') or 'Hoe laat begint ' + e['title'] + '?'} {short_day(e['day'])}, {e['time']} | hoelaatbegint.nl",
              f"{e['title']} begint {e['day_label']} om {e['time']} Nederlandse tijd{', live op ' + e['tv_detail'] if e.get('tv') else ''}. Met countdown en agenda-knop.",
              body, og=e["tournament"], active=e["tournament"],
              jsonld=[jsonld_event(e), crumbs(("Home", "/"), (t["name"], f"/{t['slug']}/"), (e["title"], e["url"]))], priority="0.8",
              index=indexable(e))
    (DIST / "_redirects").write_text("\n".join(redirects) + "\n", encoding="utf-8")

    # --- F1-stand (data/f1_standings.json, gevuld door pipeline/sources/f1.py)
    sf = ROOT / "data" / "f1_standings.json"
    if sf.exists():
        st = json.loads(sf.read_text(encoding="utf-8"))
        dr = st["drivers"]
        lead, second = dr[0], dr[1]
        fmt = lambda p: str(int(p)) if p == int(p) else str(p).replace('.', ',')
        lede = (f"Na race {st['round']} leidt <strong>{lead['name']}</strong> ({lead['team']}) met <strong>{fmt(lead['points'])} punten</strong>, "
                f"{fmt(lead['points'] - second['points'])} punten voor {second['name']}.")
        nl = [r for r in dr if r.get("nationality") == "Dutch"]
        for r in nl:
            lede += f" {r['name']} staat <strong>{r['pos']}e</strong> met {fmt(r['points'])} punten."
        f1fut = [e for e in events if e["sport"] == "f1" and e["upcoming"] and e.get("start")]
        nx = next((e for e in f1fut if e["dt"] > now), None)
        faq = [[f"Wie staat er bovenaan in de F1 stand {st['season']}?", f"{lead['name']} met {fmt(lead['points'])} punten, na race {st['round']}."]]
        faq += [[f"Hoeveel punten heeft {r['name']}?", f"{r['name']} staat {r['pos']}e met {fmt(r['points'])} punten en {r['wins']} overwinning(en)."] for r in nl]
        faq += [["Welk team leidt bij de constructeurs?", f"{st['constructors'][0]['name']} met {fmt(st['constructors'][0]['points'])} punten."]]
        fetched = datetime.fromisoformat(st["fetched_at"]).astimezone(NL)
        body = env.from_string(STAND).render(st=st, lede=lede, nx=nx, faq=faq, fetched=f"{d_label(fetched.date())}, {fetched.strftime('%H:%M')}")
        write("/formule-1/stand/", f"F1 stand {st['season']}: WK-stand coureurs en constructeurs",
              f"De actuele F1 stand {st['season']} na race {st['round']}: {lead['name']} leidt met {fmt(lead['points'])} punten. "
              "Alle coureurs en constructeurs, met zeges en punten.",
              body, og="formule-1", active="formule-1", priority="0.9",
              jsonld=[crumbs(("Home", "/"), ("Formule 1", "/formule-1/"), ("F1 stand", "/formule-1/stand/")), faq_ld(faq)])

    # --- overzichtspagina's op zoekvolume (data/pages.json): vandaag, op tv, kalender
    nav_parent = {u: subs[0][1] for _, _, subs in NAV for _, u in subs}
    for v in views:
        if v.get("club"):
            pool = [e for e in events if v["club"] in e.get("clubs", [])]
            parent = f"/{v['club']}/"
        else:
            pool = [e for e in events if e["sport"] in v["sports"]]
            parent = nav_parent.get(v["path"], f"/{SPORTS[v['sports'][0]]['page']}/")
        fut = [e for e in pool if e["upcoming"]]
        if v["mode"] == "kalender":
            lst = [e for e in pool if e["day"].year >= today.year + (1 if today.month == 12 and today.day > 7 else 0)
                   and (e.get("round") or "").startswith("Race") and "," not in (e.get("round") or "")] or fut
            lst = [e for e in lst if e["day"].year == 2027] or lst
        elif v["mode"] == "vandaag":
            lst = [e for e in fut if e["day"] <= today <= e["end_day"]]
        else:
            lst = [e for e in fut if e.get("start") and e.get("tv")][:40]
        soon = [e for e in fut if e["day"] > today][:12]
        nx = next((e for e in fut if e.get("start") and e["dt"] > now), None)
        tvs = sorted({e["tv"] for e in fut if e.get("tv")})
        name_l = v["name"] if v["name"] in ("Formule 1", "Ajax", "Feyenoord", "PSV") else v["name"].lower()
        if v["mode"] == "vandaag":
            todays_t = [e for e in lst if e.get("start")]
            if todays_t:
                f = todays_t[0]
                lede = (f"Ja, er {'is' if len(lst) == 1 else 'zijn'} vandaag <strong>{len(lst)}</strong> "
                        f"{'wedstrijd' if len(lst) == 1 else 'wedstrijden/sessies'}. Als eerste: <strong>{f['title']}</strong> om "
                        f"<strong>{f['time']}</strong>{', live op <strong>' + f['tv_detail'] + '</strong>' if f.get('tv') else ''}.")
            elif lst:
                lede = f"Ja, vandaag staat <strong>{lst[0]['title']}</strong> op het programma. De exacte tijd volgt zodra die bekend is."
            elif nx:
                lede = (f"Nee, vandaag ({d_label(today)}) is er geen {name_l}. De eerstvolgende: <strong>{nx['title']}</strong>, "
                        f"<strong>{nx['day_label']} om {nx['time']}</strong>{', op ' + nx['tv_detail'] if nx.get('tv') else ''}.")
            else:
                lede = f"Nee, vandaag ({d_label(today)}) is er geen {name_l}."
            label = "Eerstvolgende"
        elif v["mode"] == "optv":
            lede = (f"{name_l} zie je in Nederland op <strong>{' en '.join(tvs)}</strong>. " if tvs else "") + (
                f"De eerstvolgende uitzending: <strong>{nx['title']}</strong>, {nx['day_label']} om <strong>{nx['time']}</strong>." if nx else "")
            label = "Eerstvolgende uitzending"
        else:
            lede = v.get("intro", "")
            label = "Eerstvolgende sessie"
        channels = []
        for key in sorted({e.get("broadcaster") for e in fut if e.get("tv")}):
            what = sorted({e.get("round") or e["sport_name"] for e in fut if e.get("broadcaster") == key})
            channels.append((broadcasters[key]["name"], ", ".join(what[:4])))
        if v["mode"] == "vandaag":
            faq = [[f"Is er vandaag {name_l}?", re.sub(r"<[^>]+>", "", lede)],
                   [f"Hoe laat begint {name_l} de volgende keer?", f"{nx['title']} begint {nx['day_label']} om {nx['time']} Nederlandse tijd." if nx else "Dat is nog niet bekend."]]
        elif v["mode"] == "optv":
            faq = [[f"Op welke zender is {name_l} te zien?", f"In Nederland op {' en '.join(tvs)}." if tvs else "Dat staat bij elke wedstrijd zodra het bekend is."],
                   [f"Hoe laat is {name_l} op tv?", f"De eerstvolgende uitzending is {nx['title']}, {nx['day_label']} om {nx['time']}." if nx else "Zodra de tijden bekend zijn, staan ze hier."]]
        else:
            faq = [["Wanneer begint het F1-seizoen 2027?", "Op zondag 14 maart 2027 met de GP van Bahrein."],
                   ["Hoeveel races telt de F1-kalender 2027?", "24 Grands Prix, waarvan 10 met een sprintrace."],
                   ["Wanneer is de laatste race van 2027?", "Op 12 december 2027 in Abu Dhabi."]]
        related = [(x["h1"], x["path"]) for x in views if x["path"] != v["path"] and x["path"].split("/")[1] == v["path"].split("/")[1]]
        related.append((f"Alles over {name_l}", parent))
        body = env.from_string(VIEW).render(v=v, list=lst, soon=soon, nx=nx, lede=lede, label=label, channels=channels,
                                            faq=faq, related=related, parent=parent, today_label=d_label(today))
        lds = [crumbs(("Home", "/"), (name_l, parent), (v["h1"], v["path"])), faq_ld(faq)] + [jsonld_event(e) for e in lst[:20] if e.get("start")]
        title = v["title"] + (f" ({short_day(today)})" if v["mode"] == "vandaag" else "")
        write(v["path"], f"{title} | hoelaatbegint.nl", v["description"], body, active=parent.strip("/"), jsonld=lds, priority="0.9")

    # --- agenda's
    nl_events = [e for e in events if e["nl"]]
    (DIST / "agenda" / "alles.ics").write_text(ics(nl_events, "Sport met Nederlanders · hoelaatbegint.nl"), encoding="utf-8")
    for key, s in SPORTS.items():
        f = DIST / "agenda" / f"{s['page']}.ics"
        if not f.exists():
            f.write_text(ics([e for e in events if e["sport"] == key], f"{s['name']} · hoelaatbegint.nl"), encoding="utf-8")
    for e in events:
        (DIST / "agenda" / f"{e['id']}.ics").write_text(ics([e], e["title"]), encoding="utf-8")
    host = BASE.split("://", 1)[1]
    write("/agenda/", "Sportagenda abonneren: alle wedstrijden in je agenda | hoelaatbegint.nl",
          "Abonneer je gratis op de sportagenda van hoelaatbegint.nl. Alle wedstrijden met Nederlanders vanzelf in je iPhone-, Google- of Outlook-agenda.",
          env.from_string(AGENDA).render(host=host), priority="0.6")

    # --- vaste pagina's
    fill = dict(owner=CONFIG["owner"], owner_first=CONFIG["owner"].split()[0], owner_url=CONFIG["owner_url"],
                photo=CONFIG.get("owner_photo", ""), linkedin=CONFIG.get("owner_linkedin", ""), instagram=CONFIG.get("instagram_url", ""),
                email=CONFIG["contact_email"], n_sports=len(SPORTS), n_events=len([e for e in upcoming_all if e.get("start") or e["day"] >= today]),
                sport_links=" · ".join(f'<a href="/{t_slug}/">{t["name"]}</a>' for t_slug, t in tournaments.items() if t_slug != "clubs"))
    write("/over/", "Over hoelaatbegint.nl: zo controleren we elke aanvangstijd", "Wat hoelaatbegint.nl is, hoe we aanvangstijden en zenders controleren, hoe we AI gebruiken en hoe je een fout meldt.",
          env.from_string(PAGE).render(h1="Over hoelaatbegint.nl", content=OVER.format(**fill)), priority="0.5",
          jsonld=[{"@context": "https://schema.org", "@type": "AboutPage", "url": BASE + "/over/", "mainEntity": {
              "@type": "Organization", "name": "hoelaatbegint.nl", "url": BASE, "logo": BASE + "/assets/logo.svg",
              "email": CONFIG["contact_email"], "sameAs": CONFIG.get("same_as", []),
              "founder": {"@type": "Person", "name": CONFIG["owner"], "url": CONFIG["owner_url"], "jobTitle": "SEO-specialist",
                          "sameAs": [x for x in (CONFIG.get("owner_linkedin"), CONFIG["owner_url"]) if x]}}}])
    write("/privacy/", "Privacy | hoelaatbegint.nl", "Privacyverklaring van hoelaatbegint.nl: geen cookies, geen tracking.",
          env.from_string(PAGE).render(h1="Privacy", content=PRIVACY.format(**fill)), priority="0.2")
    nf = base_tpl.render(title="Pagina niet gevonden | hoelaatbegint.nl", description="", path="/404", og="default", logo=logo, jsonld=[],
                         version=version, year=built.year, active=None, active_path="",
                         body='<section class="hero"><div class="wrap"><h1>Deze pagina begint nooit</h1><p class="lede">Hij bestaat niet (meer). Kijk bij <a href="/vandaag/">sport vandaag</a>.</p></div></section>')
    (DIST / "404.html").write_text(nf, encoding="utf-8")

    # --- sitemap, robots, llms.txt, data-export
    lastmod_file.write_text(json.dumps({p: v for p, v in lastmods.items() if any(p == x[0] for x in pages)}, indent=0), encoding="utf-8")
    groups = {"paginas": [p for p in pages if p[2] and not p[0].startswith("/wedstrijd/")],
              "wedstrijden": [p for p in pages if p[2] and p[0].startswith("/wedstrijd/")]}
    index_xml = ['<?xml version="1.0" encoding="UTF-8"?>', '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for name, items in groups.items():
        sm = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
        sm += [f"<url><loc>{BASE}{p}</loc><lastmod>{lastmods[p][1]}</lastmod></url>" for p, _, _ in items]
        sm.append("</urlset>")
        (DIST / f"sitemap-{name}.xml").write_text("\n".join(sm), encoding="utf-8")
        newest = max((lastmods[p][1] for p, _, _ in items), default=stamp)
        index_xml.append(f"<sitemap><loc>{BASE}/sitemap-{name}.xml</loc><lastmod>{newest}</lastmod></sitemap>")
    index_xml.append("</sitemapindex>")
    (DIST / "sitemap.xml").write_text("\n".join(index_xml), encoding="utf-8")
    (DIST / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {BASE}/sitemap.xml\n", encoding="utf-8")
    llms = ["# hoelaatbegint.nl", "", "> Aanvangstijden van sport met Nederlanders, in Nederlandse tijd (Europe/Amsterdam), met zender en scenario's. Elke 15 minuten bijgewerkt en bij twee bronnen gecontroleerd.", "", "## Sporten"]
    llms += [f"- [{t['name']}]({BASE}/{s}/): {t['description']}" for s, t in tournaments.items()]
    llms += ["", "## Data", f"- [Alle evenementen als JSON]({BASE}/data/events.json)", f"- [Agenda (iCal)]({BASE}/agenda/alles.ics)", f"- [Sport vandaag]({BASE}/vandaag/)"]
    (DIST / "llms.txt").write_text("\n".join(llms) + "\n", encoding="utf-8")
    (DIST / "data").mkdir()
    shutil.copy(ROOT / "data" / "events.json", DIST / "data" / "events.json")
    # --- Instagram: afbeeldingen + RSS-feed die Zapier elke ochtend uitleest (social/posts/ wordt door daily-post.yml gevuld)
    from email.utils import format_datetime
    from xml.sax.saxutils import escape as xesc
    soc = DIST / "social"
    for sub in ("launch", "posts"):
        src = ROOT / "social" / sub
        if src.exists():
            (soc / sub).mkdir(parents=True, exist_ok=True)
            for f in src.glob("*.jpg"):
                shutil.copy(f, soc / sub / f.name)
    posts = sorted((ROOT / "social" / "posts").glob("*.jpg"), reverse=True)[:10] if (ROOT / "social" / "posts").exists() else []
    items = []
    for f in posts:
        cap = f.with_suffix(".txt").read_text(encoding="utf-8") if f.with_suffix(".txt").exists() else ""
        when = datetime.fromtimestamp(int(f.with_suffix(".ts").read_text()) if f.with_suffix(".ts").exists() else f.stat().st_mtime, UTC)
        url = f"https://hoelaatbegint.pages.dev/social/posts/{f.name}"
        items.append(f"<item><title>{xesc(f.stem)}</title><link>{url}</link><guid isPermaLink=\"false\">{xesc(f.stem)}</guid>"
                     f"<pubDate>{format_datetime(when)}</pubDate><description>{xesc(cap)}</description>"
                     f"<enclosure url=\"{url}\" type=\"image/jpeg\" length=\"{f.stat().st_size}\"/></item>")
    soc.mkdir(exist_ok=True)
    (soc / "feed.xml").write_text('<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>hoelaatbegint Instagram</title>'
                                  f'<link>{BASE}</link><description>Instagram-posts van hoelaatbegint.nl</description>{"".join(items)}</channel></rss>', encoding="utf-8")
    if os.environ.get("INDEXNOW_KEY"):
        (DIST / f"{os.environ['INDEXNOW_KEY'].strip()}.txt").write_text(os.environ["INDEXNOW_KEY"].strip())
    (DIST / "_headers").write_text("/agenda/*\n  Content-Type: text/calendar; charset=utf-8\n  Cache-Control: public, max-age=900\n/assets/*\n  Cache-Control: public, max-age=31536000, immutable\n/*\n  X-Content-Type-Options: nosniff\n  Referrer-Policy: strict-origin-when-cross-origin\n"
        "https://hoelaatbegint.pages.dev/*\n  X-Robots-Tag: noindex\nhttps://:hash.hoelaatbegint.pages.dev/*\n  X-Robots-Tag: noindex\n"
        "https://www.hoelaatbegint.nl/*\n  X-Robots-Tag: noindex\n", encoding="utf-8")
    print(f"{len(pages)} pagina's gebouwd in {DIST}")

    if "--og" in sys.argv:
        make_og(tournaments)
    else:
        og_src = ROOT / "site" / "og"
        if og_src.exists():
            shutil.copytree(og_src, DIST / "assets" / "og", dirs_exist_ok=True)


def make_og(tournaments):
    """Deelafbeeldingen (1200x630) per toernooi + standaard. Worden in site/og/ bewaard."""
    from playwright.sync_api import sync_playwright
    out = ROOT / "site" / "og"
    out.mkdir(exist_ok=True)
    fonts = (ROOT / "site" / "assets" / "fonts").as_uri()
    logo = (ROOT / "site" / "assets" / "logo.svg").read_text()
    items = {"default": ("Hoe laat begint het?", "Alle sport met Nederlanders, in Nederlandse tijd")}
    for s, t in tournaments.items():
        items[s] = (t["h1"], t["facts"][0][1])
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1200, "height": 630})
        for key, (h, sub) in items.items():
            tmp = out / "_tmp.html"
            tmp.write_text(f"""<html><head><style>
@font-face{{font-family:B;font-weight:800;src:url({fonts}/barlow-condensed-latin-800-normal.woff2)}}
@font-face{{font-family:I;font-weight:500;src:url({fonts}/inter-latin-500-normal.woff2)}}
body{{margin:0;width:1200px;height:630px;background:#0E1A2B;color:#F6F4EF;font-family:I;position:relative;overflow:hidden}}
.ring{{position:absolute;right:-160px;top:-160px;width:620px;height:620px;border-radius:50%;border:44px solid rgba(255,106,19,.16)}}
.logo{{position:absolute;left:72px;top:64px;display:flex;align-items:center;gap:16px;font:800 40px B}}
.logo svg{{width:64px;height:64px}} .logo i{{font-style:normal;color:#FF6A13}}
h1{{position:absolute;left:72px;right:120px;top:190px;margin:0;font:800 96px/0.95 B;text-transform:uppercase}}
p{{position:absolute;left:72px;bottom:70px;margin:0;font-size:34px;color:#FF6A13}}
</style></head><body><div class="ring"></div><div class="logo">{logo}<span>hoelaatbegint<i>.nl</i></span></div><h1>{escape(h)}</h1><p>{escape(sub)}</p></body></html>""", encoding="utf-8")
            pg.goto(tmp.as_uri())
            pg.wait_for_timeout(400)
            pg.screenshot(path=str(out / f"{key}.png"))
        b.close()
    (out / "_tmp.html").unlink(missing_ok=True)
    shutil.copytree(out, DIST / "assets" / "og", dirs_exist_ok=True)
    print(f"{len(items)} deelafbeeldingen gemaakt")


if __name__ == "__main__":
    main()
