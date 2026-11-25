# hoelaatbegint.nl – onderhoudsnotities voor Claude

Eigenaar: Ronald Voorbergen (GitHub RonnieVo). Hij wil dat Claude alles onderhoudt; hij doet zelf zo min mogelijk.

- Alles is automatisch: `.github/workflows/update.yml` (elke 15 min), `daily-post.yml` (Instagram 07:00 NL), `weekly.yml` (maandag).
- Data: `data/events.json` wordt door `pipeline/run.py` bijgehouden. Startdata stond in `data/seed.py` (stand 25-11-2026); draai seed.py NIET opnieuw zonder reden, het overschrijft de bijgehouden data.
- Teksten per toernooi/club: `data/tournaments.json`. Zenders: `data/broadcasters.json`.
- Site: `python site/build.py` -> `dist/` (Cloudflare Pages-project `hoelaatbegint`).
- Zuinige teststand: AI-controle 1x per dag per actief toernooi (`pipeline/sources/ai_verify.py`), AI-captions en AI-inleidingen uit, API-Football gratis laag (elke 2 uur). Maandlimiet Anthropic ~€30.
- Geen gokreclame of odds op de site (Ksa-leidraad 18 maart 2026).
- Tijden altijd in Nederlandse tijd tonen; opslaan in UTC.
- Bij fouten: kijk eerst naar de laatste run in GitHub Actions.
