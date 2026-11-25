# hoelaatbegint.nl – onderhoudsnotities voor Claude

Eigenaar: Ronald Voorbergen (GitHub RonnieVo). Hij wil dat Claude alles onderhoudt; hij doet zelf zo min mogelijk.

- Alles is automatisch: `.github/workflows/update.yml` (elke 15 min), `daily-post.yml` (Instagram 07:00 NL), `weekly.yml` (maandag).
- Data: `data/events.json` wordt door `pipeline/run.py` bijgehouden. Startdata stond in `data/seed.py` (stand 25-11-2026); draai seed.py NIET opnieuw zonder reden, het overschrijft de bijgehouden data.
- Teksten per toernooi/club: `data/tournaments.json`. Zenders: `data/broadcasters.json`.
- Site: `python site/build.py` -> `dist/` (Cloudflare Pages-project `hoelaatbegint`).
- Zuinige teststand: AI-controle 1x per dag per actief toernooi (`pipeline/sources/ai_verify.py`), AI-captions en AI-inleidingen uit, Clubdata via football-data.org (gratis: Eredivisie + Champions League, secret FOOTBALL_DATA_KEY); Europa/Conference League en beker via de AI-controle. API-Football gratis laag geeft geen actuele seizoenen (alleen 2022–2024) en wordt overgeslagen; Pro-plan ($19/maand) zou het oplossen. Maandlimiet Anthropic ~€30.
- Geen gokreclame of odds op de site (Ksa-leidraad 18 maart 2026).
- Tijden altijd in Nederlandse tijd tonen; opslaan in UTC.
- Bij fouten: kijk eerst naar de laatste run in GitHub Actions.
- AI-regels (pipeline/run.py): de AI mag bij bestaande evenementen alleen tijd/locatie/status bijwerken, geen titels; een bevestigde tijd verschuift alleen bij een bron op de OFFICIAL-lijst. Les van 25-11: Ziggo had handbal NL–Tsjechië op 3/12, EHF zegt 4/12 20:30 (EHF klopt).
- Pagina's: Oranje (mannen, /nederlands-elftal/) en Leeuwinnen (/oranje-leeuwinnen/) zijn apart, op verzoek van Ronald. "De kijk van Ronald" (pipeline/ai_opinion.py) staat aan; Ronald gaf toestemming voor zijn naam en foto (site/assets/ronald.jpg).
- Handmatig testen: Actions › "Data bijwerken en site publiceren" › Run workflow met ai_force of af_force = true.
- Menu en pagina's op zoekvolume (DataForSEO, 25-11-2026; ruwe cijfers in `data/keywords.json`): F1 > clubvoetbal > darts > schaatsen > Oranje > rest onder "Meer". Menu staat in `NAV`/`MORE_NAV` in `site/build.py`.
- Overzichtspagina's (… vandaag, … op tv, F1 kalender) komen uit `data/pages.json` en vullen zich vanzelf uit events.json. Nieuwe pagina = regel toevoegen in pages.json (+ eventueel link in NAV).
- F1-races krijgen automatisch een pagina /wedstrijd/gp-…-jaar/ zodra de starttijd bekend is. Volledig Eredivisie-programma komt uit football-data.org (niet-Nederlandse-clubwedstrijden hebben nl=false en staan alleen op /eredivisie/ en /voetbal/…).
