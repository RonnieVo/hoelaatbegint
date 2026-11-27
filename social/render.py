"""Maakt Instagram-afbeeldingen (1080x1350, JPEG) uit data/events.json.

  python social/render.py daily [YYYY-MM-DD]   -> dist/social/<datum>.jpg + caption.txt (dagprogramma)
  python social/render.py week  [YYYY-MM-DD]   -> weekoverzicht vanaf maandag
Wordt elke ochtend automatisch gedraaid door .github/workflows/daily-post.yml.
"""
import json
import sys
from datetime import date, datetime, timedelta, timezone
from html import escape
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "site"))
import build  # noqa: E402  (hergebruik van de helpers)

NL = ZoneInfo("Europe/Amsterdam")
OUT = ROOT / "dist" / "social"
FONTS = (ROOT / "site" / "assets" / "fonts").as_uri()
LOGO = (ROOT / "site" / "assets" / "logo.svg").read_text()
TAGS = {"darts": "#wkdarts #darts", "voetbal": "#oranje #nederlandselftal", "handbal": "#handbal #ekhandbal",
        "f1": "#f1 #formule1", "hockey": "#hockey #proleague", "schaatsen": "#schaatsen", "veldrijden": "#veldrijden #cyclocross", "clubs": "#voetbal #eredivisie #europeesvoetbal", "leeuwinnen": "#oranjeleeuwinnen #leeuwinnen"}

CSS = f"""
@font-face{{font-family:B;font-weight:800;src:url({FONTS}/barlow-condensed-latin-800-normal.woff2)}}
@font-face{{font-family:B;font-weight:700;src:url({FONTS}/barlow-condensed-latin-700-normal.woff2)}}
@font-face{{font-family:I;font-weight:500;src:url({FONTS}/inter-latin-500-normal.woff2)}}
@font-face{{font-family:I;font-weight:700;src:url({FONTS}/inter-latin-700-normal.woff2)}}
*{{box-sizing:border-box}}
body{{margin:0;width:1080px;height:1350px;background:#0E1A2B;color:#F6F4EF;font-family:I;position:relative;overflow:hidden}}
.ring{{position:absolute;right:-220px;top:-220px;width:700px;height:700px;border-radius:50%;border:56px solid rgba(255,106,19,.14)}}
.top{{position:absolute;left:72px;top:64px;display:flex;align-items:center;gap:16px;font:800 38px B}}
.top svg{{width:60px;height:60px}} .top i{{font-style:normal;color:#FF6A13}}
.kicker{{position:absolute;left:72px;top:186px;font:700 34px B;letter-spacing:3px;text-transform:uppercase;color:#FF6A13}}
h1{{position:absolute;left:72px;right:72px;top:226px;margin:0;font:800 112px/.92 B;text-transform:uppercase}}
.list{{position:absolute;left:72px;right:72px;top:{{list_top}}px;bottom:170px;display:flex;flex-direction:column;justify-content:safe center;gap:20px}}
.list.compact{{gap:14px}} .list.compact .row{{padding:16px 26px}} .list.compact .row .t{{font-size:62px}} .list.compact .row .n{{font-size:31px}} .list.compact .row .t.small{{font-size:34px}}
.row{{display:grid;grid-template-columns:190px 1fr;gap:22px;align-items:center;background:#F6F4EF;color:#0E1A2B;border-radius:22px;padding:22px 28px}}
.row .t{{font:800 76px/1 B;color:#FF6A13}} .row .t.small{{font-size:40px;line-height:1.05;color:#5E6A7A}}
.row .n{{font:700 34px/1.15 I}} .row .m{{font:500 26px/1.3 I;color:#5E6A7A;margin-top:6px}}
.foot{{position:absolute;left:72px;right:72px;bottom:60px;display:flex;justify-content:space-between;font:700 30px B;letter-spacing:1px;color:#9fb0c4;text-transform:uppercase}}
.foot b{{color:#FF6A13}}
.sub{{font:700 34px B;letter-spacing:3px;text-transform:uppercase;color:#FF6A13;margin-top:18px}}
.row.soon{{background:#1A2A40;color:#F6F4EF}} .row.soon .m{{color:#9fb0c4}} .row.soon .t{{font-size:60px}}
.ronde{{position:absolute;left:72px;right:72px;top:{{list_top}}px;bottom:140px;display:flex;flex-direction:column;justify-content:safe center;gap:8px}}
.rd{{font:700 30px B;letter-spacing:2.5px;text-transform:uppercase;color:#FF6A13;margin-top:10px}}
.rm{{display:grid;grid-template-columns:120px 1fr auto;gap:18px;align-items:center;background:#F6F4EF;color:#0E1A2B;border-radius:14px;padding:9px 22px}}
.rm b{{font:800 46px/1 B;color:#C2410C}} .rm span{{font:700 29px/1.15 I}} .rm i{{font:500 22px I;font-style:normal;color:#5E6A7A}}
.rm.hl{{background:#FF6A13}} .rm.hl b{{color:#0E1A2B}} .rm.hl i{{color:#0E1A2B}}
.big{{position:absolute;left:72px;right:72px;top:{{list_top}}px;font:500 36px/1.4 I;color:#dfe5ee}}
.big b{{color:#fff}}
.grid{{position:absolute;left:72px;right:72px;top:{{list_top}}px;display:grid;grid-template-columns:1fr 1fr;gap:14px}}
.grid div{{background:#F6F4EF;color:#0E1A2B;border-radius:14px;padding:10px 18px;font:700 26px/1.1 I}}
.grid div span{{display:block;font:500 19px I;color:#5E6A7A;margin-top:3px}}
"""


def page(kicker, title, inner, list_top=470, foot_left="Alle tijden in Nederlandse tijd"):
    css = CSS.replace("{list_top}", str(list_top))
    return (f"<html><head><meta charset=\"utf-8\"><style>{css}</style></head><body><div class='ring'></div>"
            f"<div class='top'>{LOGO}<span>hoelaatbegint<i>.nl</i></span></div>"
            f"<div class='kicker'>{escape(kicker)}</div><h1>{title}</h1>{inner}"
            f"<div class='foot'><span>{escape(foot_left)}</span><span>Link in bio · <b>hoelaatbegint.nl</b></span></div></body></html>")


def rows(evs, show_day=False, soon=()):
    out = []
    for e in evs:
        if e["time"]:
            t = f"<div class='t'>{e['time']}</div>"
        elif e["is_range"]:
            t = f"<div class='t small'>{e['day'].day}–{e['end_day'].day}<br>{build.MONTHS[e['end_day'].month - 1][:3]}</div>"
        else:
            t = "<div class='t small'>tijd<br>volgt</div>"
        meta = " · ".join(x for x in [e["day_label"] if show_day else None, e.get("tv_detail"), e.get("city")] if x)
        out.append(f"<div class='row'>{t}<div><div class='n'>{escape(e['title'])}</div><div class='m'>{escape(meta)}</div></div></div>")
    if soon:  # rustige dag: vul aan met wat er de komende dagen aankomt
        out.append("<div class='sub'>Binnenkort</div>")
        for e in soon:
            meta = " · ".join(x for x in [e["day_label"].capitalize(), e.get("tv")] if x)
            out.append(f"<div class='row soon'><div class='t'>{e['time']}</div><div><div class='n'>{escape(e['title'])}</div><div class='m'>{escape(meta)}</div></div></div>")
    return f"<div class='list{' compact' if len(evs) + len(soon) > 4 else ''}'>" + "".join(out) + "</div>"


def load():
    now = datetime.now(timezone.utc)
    raw = json.loads((ROOT / "data" / "events.json").read_text(encoding="utf-8"))["events"]
    b = json.loads((ROOT / "data" / "broadcasters.json").read_text(encoding="utf-8"))
    return sorted((build.prep(e, b, now - timedelta(days=400)) for e in raw), key=lambda e: e["dt"])


def daily(day):
    evs = [e for e in load() if e["nl"] and e["day"] == day and (e.get("start") or not e["is_range"])]
    if not evs:
        return None, None
    evs = evs[:6]
    soon = []
    if len(evs) < 3:
        seen = set()
        for e in load():
            if e["nl"] and e.get("start") and day < e["day"] <= day + timedelta(days=7) and e["title"] not in seen:
                seen.add(e["title"]); soon.append(e)
            if len(soon) >= 4 - len(evs):
                break
    html = page(build.d_label(day).capitalize(), "Sport<br>vandaag", rows(evs, soon=soon))
    lines = [f"Vandaag, {build.d_label(day)}:", ""]
    for e in evs:
        lines.append(f"{e['time'] or 'tijd volgt'} · {e['title']}" + (f" ({e['tv']})" if e.get("tv") else ""))
    if soon:
        lines += ["", "Binnenkort:"] + [f"{e['day_label']} {e['time']} · {e['title']}" for e in soon]
    lines += ["", "Alle tijden in Nederlandse tijd. Countdown en agenda-knop via de link in bio.", "",
              " ".join(dict.fromkeys(TAGS[e["sport"]] for e in evs)) + " #sportoptv #hoelaatbegint"]
    return html, "\n".join(lines)


def week(monday):
    sunday = monday + timedelta(days=6)
    evs = [e for e in load() if e["nl"] and e.get("start") and monday <= e["day"] <= sunday][:7]
    if not evs:
        return None, None
    html = page(f"{monday.day} t/m {build.range_label(monday, sunday).split(' t/m ')[1]}", "Sportweek", rows(evs, True))
    cap = "\n".join([f"De sportweek van {build.range_label(monday, sunday)}:", ""] +
                    [f"{e['day_label']} {e['time']} · {e['title']}" for e in evs] + ["", "#sportoptv #hoelaatbegint"])
    return html, cap


def ronde(day):
    """Eredivisie-speelronde: alleen op de dag van de eerste wedstrijd van een ronde. Geeft (naam, html, caption)."""
    rounds = build.eredivisie_rounds(load())
    for n, evs in rounds.items():
        if evs[0]["day"] != day:
            continue
        rows_html, cur = [], None
        for e in evs:
            if e["day_label"] != cur:
                cur = e["day_label"]
                rows_html.append(f"<div class='rd'>{escape(cur)}</div>")
            ch = e.get("tv_detail") or "ESPN"
            rows_html.append(f"<div class='rm{' hl' if e.get('clubs') and len(e['clubs']) >= 2 else ''}'><b>{e['time'] or '–'}</b>"
                             f"<span>{escape(e['title'])}</span><i>{escape(ch)}</i></div>")
        span = build.range_label(evs[0]["day"], evs[-1]["day"]) if evs[0]["day"] != evs[-1]["day"] else build.d_label(day)
        html = page(f"Eredivisie · {span}", f"Speelronde {n}", f"<div class='ronde'>{''.join(rows_html)}</div>", list_top=350,
                    foot_left="Alles live op ESPN")
        lines = [f"Eredivisie speelronde {n} ({span}):", ""]
        cur = None
        for e in evs:
            if e["day_label"] != cur:
                cur = e["day_label"]
                lines += ["", cur.capitalize()] if len(lines) > 2 else [cur.capitalize()]
            lines.append(f"{e['time'] or 'tijd volgt'} · {e['title']}")
        lines += ["", "Alle wedstrijden live op ESPN. Alle tijden in Nederlandse tijd; per wedstrijd een countdown via de link in bio.", "",
                  "#eredivisie #voetbal #espn #speelronde" + str(n) + " #hoelaatbegint"]
        return f"eredivisie-speelronde-{n}", html, "\n".join(lines)
    return None, None, None


MULTI = {"darts", "schaatsen", "handbal", "f1"}  # sporten met meerdaagse toernooien/weekenden


def toernooien(day):
    """Extra post per toernooi op de eerste dag van een blok (bv. F1-weekend, darts-major, schaatsweekend).
    Geeft lijst van (naam, html, caption)."""
    evs = [e for e in load() if e["nl"] and e.get("start") and e["sport"] in MULTI]
    out = []
    for slug in dict.fromkeys(e["tournament"] for e in evs):
        mine = [e for e in evs if e["tournament"] == slug]
        block = [e for e in mine if day <= e["day"] <= day + timedelta(days=3)]
        before = [e for e in mine if day - timedelta(days=3) <= e["day"] < day]
        if len(block) < 2 or block[0]["day"] != day or before:
            continue
        t = json.loads((ROOT / "data" / "tournaments.json").read_text(encoding="utf-8")).get(slug, {"name": slug})
        name_t = t.get("name", slug)
        rounds = [e.get("round") for e in block]
        use_round = block[0]["sport"] == "darts" and all(rounds) and len(set(rounds)) == len(rounds)  # darts: sessies heten naar de ronde
        label = (lambda e: e["round"]) if use_round else (lambda e: e["title"])
        short = [{**e, "title": label(e)} for e in block][:6]
        uniform = rounds[0] if all(rounds) and len(set(rounds)) == 1 else None
        kicker = " · ".join(x for x in [uniform, block[0].get("city"), block[0].get("tv")] if x)
        if len(name_t) <= 14:
            title, top = name_t, 400
        else:
            words = name_t.split()
            cut = min(range(1, len(words)), key=lambda i: abs(len(" ".join(words[:i])) - len(" ".join(words[i:]))))
            title, top = f"<span style='font-size:86px'>{' '.join(words[:cut])}<br>{' '.join(words[cut:])}</span>", 470
        html = page(kicker or build.d_label(day), title, rows(short, True), list_top=top,
                    foot_left=build.range_label(block[0]["day"], block[-1]["day"]) if block[0]["day"] != block[-1]["day"] else build.d_label(day))
        lines = [f"{name_t}: het programma{' van het weekend' if block[-1]['day'] != day else ''}.", ""]
        lines += [f"{e['day_label']} {e['time']} · {label(e)}" + (f" ({e['tv']})" if e.get("tv") else "") for e in block]
        lines += ["", "Alle tijden in Nederlandse tijd. Countdown en agenda-knop via de link in bio.", "", TAGS.get(block[0]["sport"], "") + " #hoelaatbegint"]
        out.append((f"toernooi-{slug}-{day.isoformat()}", html, "\n".join(lines)))
    return out


def shoot(html, path):
    from playwright.sync_api import sync_playwright
    path.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1080, "height": 1350})
        tmp = path.with_suffix(".html")
        tmp.write_text(html, encoding="utf-8")
        pg.goto(tmp.as_uri())
        pg.wait_for_timeout(400)
        tmp.unlink()
        pg.screenshot(path=str(path), type="jpeg", quality=92)
        b.close()


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "daily"
    day = date.fromisoformat(sys.argv[2]) if len(sys.argv) > 2 else datetime.now(NL).date()
    if mode == "ronde":  # schrijft direct naar social/posts (alleen als de ronde vandaag begint en nog niet gepost is)
        name, html, cap = ronde(day)
        posts = ROOT / "social" / "posts"
        if not name or (posts / f"{name}.jpg").exists():
            print("Geen nieuwe Eredivisie-speelronde vandaag.")
            return
        posts.mkdir(parents=True, exist_ok=True)
        shoot(html, posts / f"{name}.jpg")
        (posts / f"{name}.txt").write_text(cap, encoding="utf-8")
        (posts / f"{name}.ts").write_text(str(int(datetime.now().timestamp()) + 5))
        print(f"Gemaakt: {name}")
        return
    if mode == "toernooien":  # extra posts, direct naar social/posts
        posts = ROOT / "social" / "posts"
        for i, (name, html, cap) in enumerate(toernooien(day)):
            if (posts / f"{name}.jpg").exists():
                continue
            posts.mkdir(parents=True, exist_ok=True)
            shoot(html, posts / f"{name}.jpg")
            (posts / f"{name}.txt").write_text(cap, encoding="utf-8")
            (posts / f"{name}.ts").write_text(str(int(datetime.now().timestamp()) + 10 + i))
            print(f"Gemaakt: {name}")
        return
    if mode == "week":
        day = day - timedelta(days=day.weekday())
        html, cap = week(day)
    else:
        html, cap = daily(day)
    if not html:
        print("Geen Nederlandse sport op deze dag: geen post.")
        return
    name = f"{mode}-{day.isoformat()}"
    shoot(html, OUT / f"{name}.jpg")
    (OUT / f"{name}.txt").write_text(cap, encoding="utf-8")
    print(f"Gemaakt: {OUT / name}.jpg")


if __name__ == "__main__":
    main()
