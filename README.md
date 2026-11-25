# hoelaatbegint.nl

Sport met Nederlanders, in Nederlandse tijd. Volledig automatisch: data ophalen, controleren, site bouwen,
Instagram-posts, pushmeldingen en een weekrapport. Na de eenmalige installatie hoef je niets meer te doen.

## Wat er automatisch gebeurt

| Wanneer | Wat | Bestand |
| --- | --- | --- |
| Elke 15 minuten | Data ophalen (API's + AI-controle), conflicten mailen, site bouwen en publiceren, IndexNow | `.github/workflows/update.yml` |
| 30 min voor elke Nederlandse wedstrijd | Pushmelding aan abonnees van die sport | `pipeline/push.py` |
| Elke dag 06:00 UTC | AI schrijft korte inleidingen voor nieuwe wedstrijdpagina's | `pipeline/ai_write.py` |
| Elke dag 07:00 (NL) | Instagram-post met het Nederlandse dagprogramma (geen sport = geen post) | `.github/workflows/daily-post.yml` |
| Maandag 08:00 (NL) | Instagram-weekoverzicht | idem |
| Maandag 07:30 (UTC) | Weekrapport per mail + automatische titeltests op pagina's met lage CTR | `.github/workflows/weekly.yml` |

Je krijgt alleen mail als (1) bronnen het oneens zijn over een tijd, (2) een bron niet werkt of (3) een run mislukt.
De laatst bevestigde tijd blijft dan gewoon op de site staan.

## Goedkoop testen (standaardinstelling)

Het pakket staat standaard op de zuinigste stand die nog volledig automatisch is:

| Onderdeel | Instelling | Kosten |
| --- | --- | --- |
| GitHub-repository | **Openbaar** maken (Actions is dan gratis en onbeperkt) | €0 |
| Hosting | Cloudflare Pages | €0 |
| Bezoekersstatistieken | Cloudflare Web Analytics (cookieloos), plus Search Console | €0 |
| AI-controle | 1 keer per dag per actief toernooi, extra op wedstrijddagen, max. 4 zoekopdrachten per controle | ~€15–25 per maand |
| AI-captions en AI-inleidingen | Uit (sjabloonteksten) | €0 |
| API-Football | Gratis laag (100 verzoeken per dag); clubs en Oranje worden elke 2 uur opgehaald, ongeveer 50 verzoeken per dag | €0 |
| TheSportsDB | Geen sleutel invullen (optioneel) | €0 |
| Instagram, OneSignal, mail | Gratis lagen | €0 |
| Domein | Eenmalig | ~€10 per jaar |

Zet in de Anthropic Console een maandlimiet (bijvoorbeeld €30), dan kan het nooit duurder worden.
Later opschalen: zet de variabelen (Settings › Variables) `AI_VERIFY_MODE=intensief`, `AI_CAPTIONS=1` of `AI_WRITE=1`, of een `plausible_domain` in `site/config.json`.

## Eenmalige installatie (ongeveer 2 uur)

1. **Domein**: registreer `hoelaatbegint.nl`.
2. **GitHub**: maak een **openbare** repository en upload deze map (je API-sleutels blijven geheim in Secrets). Zet onder *Settings › Actions › General* de
   workflow-rechten op *Read and write*.
3. **Cloudflare Pages**: maak een gratis account, maak een Pages-project met de naam `hoelaatbegint`
   (Direct Upload), koppel het domein. Maak een API-token met het recht *Cloudflare Pages: Edit*.
4. **API-sleutels** (allemaal als *Secrets* in GitHub: *Settings › Secrets and variables › Actions*):

| Secret | Waar je hem haalt | Nodig voor |
| --- | --- | --- |
| `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID` | Cloudflare-dashboard | Publiceren |
| `ANTHROPIC_API_KEY` | console.anthropic.com | AI-controle, captions, inleidingen, titels |
| `API_FOOTBALL_KEY` | api-football.com (gratis laag volstaat) | Ajax, Feyenoord, PSV en Oranje. Team-ID's (194, 209, 197, 1118) eenmalig controleren via `/teams?search=` |
| `THESPORTSDB_KEY` | thesportsdb.com (Patreon-sleutel aanbevolen) | Tweede bron darts |
| `INDEXNOW_KEY` | zelf verzinnen: 32 willekeurige letters/cijfers | Snelle indexering Bing |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `MAIL_TO` | je mailprovider (bijv. Gmail met app-wachtwoord) | Meldingen en weekrapport |
| `IG_USER_ID`, `IG_ACCESS_TOKEN` | zie stap 5 | Instagram |
| `ONESIGNAL_APP_ID`, `ONESIGNAL_API_KEY` | onesignal.com (gratis) | Pushmeldingen; zet de app-ID ook in `site/config.json` |
| `PLAUSIBLE_API_KEY` | plausible.io (optioneel, betaald) | Extra bezoekcijfers in het weekrapport |
| `GSC_SERVICE_ACCOUNT_JSON` | Google Cloud service-account, toegevoegd als gebruiker in Search Console | Weekrapport en titeltests |

F1-data (Jolpica) heeft geen sleutel nodig.

5. **Instagram**: maak het account `@hoelaatbegint`, zet het om naar een *zakelijk* account en koppel het aan
   een Facebook-pagina. Maak op developers.facebook.com een app met *Instagram API*, vraag de rechten
   `instagram_business_basic` en `instagram_business_content_publish` aan, en maak een langlevend toegangstoken.
   Zet het Instagram-gebruikers-ID en het token als secrets. Het token is 60 dagen geldig: zet een herinnering
   of gebruik een systeemgebruiker-token in Meta Business Suite (verloopt niet).
6. **Search Console en Bing Webmaster Tools**: domein toevoegen, sitemap `https://hoelaatbegint.nl/sitemap.xml` indienen.
7. **Cloudflare Web Analytics**: zet het aan voor het domein en plak de token in `site/config.json` (`cloudflare_analytics_token`).
8. Vul `site/config.json` aan (KvK-nummer, e-mail, OneSignal-ID) en start de workflow *Data bijwerken* één keer handmatig.

## Mappen

- `data/` – `events.json` (alle evenementen, door de pipeline bijgehouden), `tournaments.json` (teksten per toernooi),
  `broadcasters.json` (zenders + affiliatelinks), `seed.py` (startdata van 25 november 2026).
- `pipeline/` – ophalen, samenvoegen, controleren, mailen, push, IndexNow, weekrapport.
- `site/` – `build.py` bouwt alle pagina's, agenda's (.ics), sitemap, `llms.txt` en deelafbeeldingen.
- `social/` – `render.py` (dag- en weekposts), `publish_instagram.py`, `launch/` (vier startposts + captions).

## Lokaal testen

```bash
pip install -r requirements.txt && python -m playwright install chromium
python pipeline/run.py          # data bijwerken (bronnen zonder sleutel worden overgeslagen)
python site/build.py --og       # site bouwen in dist/
python -m http.server -d dist   # bekijken op http://localhost:8000
python social/render.py daily 2026-12-06
```

## Uitbreiden

- **Nieuwe sport of toernooi**: voeg een blok toe in `data/tournaments.json`, een taak in `pipeline/sources/ai_verify.py`
  (of een API-bron in `pipeline/sources/`) en de sport in `SPORTS` in `site/build.py`.
- **Meer clubs**: voeg team-ID's toe in `TEAMS` in `pipeline/sources/football.py` en een blok in `data/tournaments.json`. Let op de gratis limiet van 100 verzoeken per dag.
- **Affiliatelinks**: vul `affiliate_url` in `data/broadcasters.json`; de knoppen en de vermelding verschijnen vanzelf.
