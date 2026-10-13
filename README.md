# Agamotto

[![License](https://img.shields.io/badge/license-CC%20BY--NC--SA%204.0-lightgrey.svg)](LICENSE)
[![Dependencies](https://img.shields.io/badge/dependencies-none-brightgreen.svg)](#building)

A watch-order guide to every film and series in eleven franchises: Marvel, X-Men, DC, Star Wars, Alien & Predator, Godzilla & the MonsterVerse, Planet of the Apes, Dune, Middle-earth, the Wizarding World and Westeros. In English and Chinese.

**Live**: [timeline.luminoid.dev](https://timeline.luminoid.dev) (EN · 中文 from the language switch)

## Features

- **One section per continuity.** The MCU, Sony's Spider-Man Universe, Toho's Shōwa era and the rest each get their own section on a vertical timeline.
- **Story or release order.** Either can run in both directions.
  - Story order follows the official timeline where one exists: Marvel's Disney+ order, StarWars.com, and the years in Tolkien's appendices.
  - Elsewhere it follows each continuity's own chronology.
- **Details on every card.** Runtime, seasons and episodes, plus IMDb and Douban scores with their vote counts and Rotten Tomatoes' Tomatometer, Certified Fresh and audience score, with links to each site and to JustWatch. Tap a poster to see it whole.
- **Links to any franchise or section.**
  - `#xmen` opens a franchise.
  - `#xmen/fox-xmen`, or just `#fox-xmen`, also scrolls to that section.
- **My ratings.** Import your IMDb ratings (their CSV export) and your Douban watched list (a bookmarklet) to see your scores next to the site's.
  - They stay in your browser and are never uploaded.
- **A few hidden extras.**

## Layout

```
site/            the built site: index.html, posters/, icons, 404.html, _headers, robots.txt, sitemap.xml.
                 Deploy this folder as is.
pipeline/        the scripts, template and data that build it
  brand/         sources for the icons and the social card
  tests/         headless Chrome checks and a screenshot tool
```

## Building

You need:
- Python 3 with Pillow (`pip install -r requirements.txt`)
- curl
- Node 22 or later, for the built-in `fetch` and `WebSocket`
- Google Chrome, for the Douban scripts, the icons and the tests. The scripts look in the macOS location; set `CHROME` to the browser's path elsewhere.

Common tasks have make targets (`make` lists them):

```sh
make build       # rebuild site/ from the template and data (seconds, offline)
make serve       # build, then serve site/ at http://localhost:8000 (PORT=... to change)
make test        # easter eggs, links, rating imports and release checks in headless Chrome, offline
make test-live   # the same, plus the Douban bookmarklet on a public profile
make icons       # redraw the favicons, touch icon and social card from pipeline/brand/
make data        # full refresh: fetch, douban, enrich, build (slow, needs network)
```

The steps behind `make data`, run from `pipeline/`. The fetch, Douban and enrich scripts are not in the repository: they drive third-party sites and stay on the maintainer's machine under `pipeline/local/`, so a clone can edit titles and rebuild the site from the committed JSON, but not refresh the data.

| Step | Command | Writes |
|---|---|---|
| Edit titles, story order and settings | `seed.py`; Chinese names in `zh_titles.py` | |
| Resolve titles on Wikipedia and Wikidata, download posters (a 200×300 card crop and the whole poster for the zoom) | `python3 local/fetch.py` | `data.json`, `../site/posters/` |
| Queue Douban lookups for new titles | `python3 local/douban_add_jobs.py` | `douban_jobs.json`, `douban_split.json` |
| Match films through their Douban pages | `node local/douban_subj.mjs` | `douban_subj.json` |
| Match series seasons, and films without a Douban ID | `node local/douban_m.mjs` | `douban_m.json` |
| Read every later-season page those found, to check its IMDb ID and votes | `node local/douban_check.mjs` | `douban_check.json` |
| Add ratings, runtimes and seasons, and cross-check sources | `python3 local/enrich.py` | `data_enriched.json`, `report.txt`, `rt.json`, `wiki_infobox.json`, `imdb/subset.json` |
| Build the site | `python3 build.py` | `../site/index.html`, `404.html`, `_headers`, `robots.txt`, `sitemap.xml` |

A Douban match counts only when the Douban page lists the title's IMDb ID; a later season counts when its page lists the series or one of its episodes. `report.txt` lists every place where the sources disagree.

### Caches and refreshing ratings

Nothing here expires, so a rerun reuses everything it already has.

Not committed:
- **`pipeline/local/`**: `fetch.py`, `enrich.py` and the `douban_*` scripts (see above).
- **`pipeline/cache/`** holds every HTTP response, named by a hash of its URL. Files starting with `c_` are Rotten Tomatoes pages (and Douban responses from an older version of the scripts); the rest are Wikipedia, Wikidata, TMDB and poster downloads.
- **`pipeline/imdb/`** holds IMDb's `title.basics`, `title.episode` and `title.ratings` files, downloaded by hand from https://datasets.imdbws.com/, and `subset.json`, the slice of them the site uses (rebuilt when it lacks an ID).

Committed, and reused the same way:
- **`douban_subj.json`, `douban_m.json` and `douban_check.json`**: the Douban scripts skip any title or page that already has an entry.
- **`rt.json`**: Rotten Tomatoes scores; `enrich.py` fetches only titles missing from it.
- **`wiki_infobox.json`**: runtimes, seasons and episode counts parsed from Wikipedia infoboxes.

To refresh:
- **IMDb:** download the three files again, delete `imdb/subset.json`, then `make enrich build`.
- **Rotten Tomatoes:** `REFRESH_RT=1 make enrich`, then `make build`. It refetches every page.
- **Douban:** remove the titles you want refreshed from `douban_subj.json` and `douban_m.json` (and their season pages from `douban_check.json`), then `make douban enrich build`. Each title takes a few seconds, and Douban throttles long runs.
- **Wikipedia counts:** delete `wiki_infobox.json` and the files in `cache/` whose names don't start with `c_`, then `make enrich build`. The next `make fetch` downloads Wikidata and posters again too.

### Checks

`make test` runs the three check scripts in `pipeline/tests/`. Each prints one line per check and exits non-zero on a failure:

- `eggs.mjs` covers the hidden extras.
- `ratings.mjs` covers links, history, the Douban bookmarklet and both rating imports. With `OFFLINE=1` it only parses the bookmarklet; without it, it runs the bookmarklet on a public Douban profile.
- `site.mjs` serves `site/` with its `_headers` and covers the release files and meta tags, the Content-Security-Policy, keyboard focus and screen-reader announcements, recovery from bad stored settings, and the English and Chinese strings.

Screenshots of any view:

```sh
node pipeline/tests/shot.mjs out.png 1300 900 "file://$PWD/site/index.html#dune"
```

## Data sources

- **Wikipedia and Wikidata:** titles, release dates, runtimes, episode counts and most posters.
- **TMDB:** posters where Wikipedia has none.
- **IMDb:** ratings, runtimes and episodes, from IMDb's non-commercial datasets, which IMDb licenses for personal, non-commercial use only. Information courtesy of IMDb (https://www.imdb.com). Used with permission.
- **Douban:** ratings and Chinese titles. Every match is checked against the IMDb ID shown on the Douban page.
- **Rotten Tomatoes:** Tomatometer and audience scores, per season where they exist.

This is an unofficial fan index, not affiliated with any studio or rights holder. Posters belong to their owners.

## Deploying

`site/` is a static site with no build step at serve time, made for Cloudflare Pages (output directory `site`, no build command). Links use URL fragments, so the host needs no rewrite rules.

- `_headers` carries the security headers and a Content-Security-Policy that allows the page's one inline script by its hash. `make build` rewrites both files, so deploy `index.html` and `_headers` together.
- Poster URLs carry a version, so `_headers` lets browsers keep posters for a year.
- On Cloudflare, set the zone's Caching → Browser Cache TTL to "Respect Existing Headers". Otherwise its four-hour default overrides the page's revalidation and visitors can see a stale page.

## License

[CC BY-NC-SA 4.0](LICENSE) for the code, the design, the watch-order compilation and the original text. Ratings, titles and posters belong to their sources and owners; [LICENSE](LICENSE) lists them.
