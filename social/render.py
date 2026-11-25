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
        "f1": "#f1 #formule1", "hockey": "#hockey #proleague", "schaatsen": "#schaatsen", "veldrijden": "#veldrijden #cyclocross", "clubs": "#eredivisie #ajax #feyenoord #psv"}

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
.big{{position:absolute;left:72px;right:72px;top:{{list_top}}px;font:500 36px/1.4 I;color:#dfe5ee}}
.big b{{color:#fff}}
.grid{{position:absolute;left:72px;right:72px;top:{{list_top}}px;display:grid;grid-template-columns:1fr 1fr;gap:14px}}
.grid div{{background:#F6F4EF;color:#0E1A2B;border-radius:14px;padding:10px 18px;font:700 26px/1.1 I}}
.grid div span{{display:block;font:500 19px I;color:#5E6A7A;margin-top:3px}}
"""


def page(kicker, title, inner, list_top=470, foot_left="Alle tijden in Nederlandse tijd"):
    css = CSS.replace("{list_top}", str(list_top))
    return (f"<html><head><style>{css}</style></head><body><div class='ring'></div>"
            f"<div class='top'>{LOGO}<span>hoelaatbegint<i>.nl</i></span></div>"
            f"<div class='kicker'>{escape(kicker)}</div><h1>{title}</h1>{inner}"
            f"<div class='foot'><span>{escape(foot_left)}</span><span>Link in bio · <b>hoelaatbegint.nl</b></span></div></body></html>")


def rows(evs, show_day=False):
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
    return f"<div class='list{' compact' if len(evs) > 4 else ''}'>" + "".join(out) + "</div>"


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
    html = page(build.d_label(day).capitalize(), "Sport<br>vandaag", rows(evs))
    lines = [f"Vandaag, {build.d_label(day)}:", ""]
    for e in evs:
        lines.append(f"{e['time'] or 'tijd volgt'} · {e['title']}" + (f" ({e['tv']})" if e.get("tv") else ""))
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
