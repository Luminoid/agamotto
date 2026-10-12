"""Add runtime, seasons/episodes and ratings to data.json, and cross-check every title across sources.

Sources: IMDb public datasets (ratings, runtime, episodes), Wikipedia infoboxes (runtime, seasons,
episodes, release dates), Douban title pages verified by IMDb id (douban_subj.json, douban_m.json:
ratings, mainland titles, per-season subjects), Rotten Tomatoes scorecards (Tomatometer, audience
score, per season).
Writes data_enriched.json and report.txt (every disagreement between sources).
REFRESH_RT=1 refetches every Rotten Tomatoes page instead of reusing rt.json and the cache.
"""
import gzip, hashlib, html as htmllib, json, os, re, subprocess, sys, time

from fetch import BROWSER_UA, api, chunks

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "cache")
TODAY = "2026-10-10"
data = json.load(open(os.path.join(HERE, "data.json")))
titles = data["titles"]
report = []
# RT pages Wikidata lacks (verified by name and year on the page itself)
RT_FIX = {
    "fns-spider-man": "tv/your_friendly_neighborhood_spider_man",
    "jlu": "tv/justice_league_unlimited",  # RT folds JLU into its Justice League (2001) page
    "wonder-woman-tv": "tv/wonder_woman",
    "skull-island-tv": "tv/skull_island",
    "planet-of-monsters": "m/godzilla_planet_of_the_monsters",
    "kong-vs-godzilla": "m/king_kong_vs_godzilla",
    "return-apes": "tv/return_to_the_planet_of_the_apes",
    "dune-2000": "tv/dune",  # RT lists the 2000 miniseries as plain "Dune"
    "return-of-godzilla": "m/the_return_of_godzilla",  # Wikidata points at the 1985 US re-edit, Godzilla 1985
}
for _t in titles:
    _t["rt"] = RT_FIX.get(_t["key"], _t["rt"])


def flag(key, msg):
    report.append(f"{key:24} {msg}")


def curl(url, headers=(), delay=1.2, tries=4, fresh=False):
    """Cached GET through curl (RT accepts curl's TLS fingerprint). fresh=True skips and overwrites the cached copy."""
    path = os.path.join(CACHE, "c_" + hashlib.sha1(url.encode()).hexdigest())
    if os.path.exists(path) and not fresh:
        return open(path, "rb").read().decode("utf-8", "replace")
    cmd = ["curl", "-s", "-L", "-m", "30", "-A", BROWSER_UA, "-w", "\n%{http_code}"]
    for h in headers:
        cmd += ["-H", h]
    for attempt in range(tries):
        out = subprocess.run(cmd + [url], capture_output=True).stdout.decode("utf-8", "replace")
        body, _, code = out.rpartition("\n")
        if code == "200":
            open(path, "w").write(body)
            time.sleep(delay)
            return body
        if code == "404":
            time.sleep(delay)
            return None
        print(f"  {code} retry {attempt} {url[:100]}", file=sys.stderr)
        time.sleep(5 + attempt * 10)
    return None


def norm(s):
    s = (s or "").lower().replace("&", "and")
    s = re.sub(r"^(marvel's|marvel|star wars:|the)\s+", "", s)
    s = re.sub(r"\bseason\s*\d+\b|\(.*?\)", "", s)
    return re.sub(r"[^a-z0-9]", "", s)


def year_of(t):
    return int(t["date"][:4]) if t.get("date") else None


# ------------------------------------------------------------------ IMDb datasets
def stage_imdb(extra=()):
    """extra: more ids to look up in title.basics (the IMDb ids Douban pages list), so a wrong one can be named."""
    out_path = os.path.join(HERE, "imdb", "subset.json")
    ids = {t["imdb"] for t in titles if t["imdb"]} | set(extra)
    if os.path.exists(out_path):
        cached = json.load(open(out_path))
        if ids <= set(cached.get("ids", [])):
            return cached
    series = {t["imdb"] for t in titles if t["imdb"] and t["kind"] == "series"}
    ratings, eps, basics = {}, {}, {}
    with gzip.open(os.path.join(HERE, "imdb", "title.ratings.tsv.gz"), "rt") as f:
        next(f)
        for line in f:
            tc, avg, votes = line.rstrip("\n").split("\t")
            if tc in ids:
                ratings[tc] = [float(avg), int(votes)]
    with gzip.open(os.path.join(HERE, "imdb", "title.episode.tsv.gz"), "rt") as f:
        next(f)
        for line in f:
            tc, parent, season, ep = line.rstrip("\n").split("\t")
            if parent in series:
                eps[tc] = [parent, season, ep]
    want = ids | set(eps)
    with gzip.open(os.path.join(HERE, "imdb", "title.basics.tsv.gz"), "rt") as f:
        next(f)
        for line in f:
            tc = line[: line.index("\t")]
            if tc in want:
                p = line.rstrip("\n").split("\t")
                basics[tc] = dict(type=p[1], title=p[2], orig=p[3], start=p[5], end=p[6], runtime=p[7])
    out = dict(ratings=ratings, episodes=eps, basics=basics, ids=sorted(ids))
    json.dump(out, open(out_path, "w"))
    return out


def douban_pages():
    """Douban id -> the IMDb id its page lists (None when it lists none), from every page the Douban scripts read."""
    read = lambda f: json.load(open(os.path.join(HERE, f))) if os.path.exists(os.path.join(HERE, f)) else {}
    pages, checked = {}, {}
    for r in read("douban_subj.json").values():
        if r.get("id") and not r.get("failed"):
            pages[str(r["id"])] = r.get("imdb")
    for r in read("douban_m.json").values():
        for tried in r.get("tried", []):
            parts = tried.split(":")
            pages.setdefault(parts[0], parts[-1] if re.fullmatch(r"tt\d+", parts[-1]) else None)
    for i, c in read("douban_check.json").items():
        if not c.get("failed"):
            pages[i], checked[i] = c.get("imdb"), c
    return pages, checked


# ------------------------------------------------------------------ Wikipedia infoboxes
def clean(v):
    v = re.sub(r"<ref[^>]*/>|<ref.*?</ref>|<!--.*?-->", "", v, flags=re.S)
    return v.strip()


def infobox_field(text, *names):
    for n in names:
        m = re.search(r"^\s*\|\s*%s\s*=(.*?)(?=^\s*\||^\}\})" % n, text, re.M | re.S)
        if m and clean(m.group(1)):
            return clean(m.group(1))
    return None


def first_int(v):
    m = re.search(r"\d+", (v or "").replace(",", ""))
    return int(m.group()) if m else None


def parse_dates(v):
    """{{Film date|2008|04|14|Sydney|2008|05|02|United States}} -> [(date, place)]"""
    out = []
    if not v:
        return out
    for m in re.finditer(r"\{\{\s*(?:film date|start date(?: and age)?|release date)\s*\|([^{}]*)\}\}", v, re.I):
        parts = [p.strip() for p in m.group(1).split("|") if "=" not in p]
        i = 0
        while i < len(parts):
            if re.fullmatch(r"\d{4}", parts[i]):
                y = parts[i]
                mo = parts[i + 1] if i + 1 < len(parts) and parts[i + 1].isdigit() else None
                d = parts[i + 2] if mo and i + 2 < len(parts) and parts[i + 2].isdigit() else None
                step = 1 + (1 if mo else 0) + (1 if d else 0)
                place = parts[i + step] if i + step < len(parts) and not re.fullmatch(r"\d{4}", parts[i + step]) else ""
                date = y + (f"-{int(mo):02d}" if mo else "") + (f"-{int(d):02d}" if d else "")
                place = re.sub(r"\[\[|\]\]", "", place).replace("&nbsp;", " ")
                out.append((date, place))
                i += step + (1 if place else 0)
            else:
                i += 1
    return out


def stage_wiki():
    path = os.path.join(HERE, "wiki_infobox.json")
    out = json.load(open(path)) if os.path.exists(path) else {}
    pages = sorted({t["wiki"] for t in titles} - set(out))  # only pages not parsed yet
    for b in chunks(pages, 50):
        r = api("en.wikipedia.org", action="query", titles="|".join(b), prop="revisions", rvprop="content",
                rvslots="main", rvsection="0")
        for p in r["query"]["pages"]:
            text = p["revisions"][0]["slots"]["main"]["content"] if p.get("revisions") else ""
            rt = infobox_field(text, "runtime")
            out[p["title"]] = dict(
                runtime=first_int(re.sub(r"\(.*?\)", "", rt)) if rt and re.search(r"min", rt) else first_int(rt),
                runtime_raw=rt,
                seasons=first_int(infobox_field(text, "num_seasons", "num_series")),
                episodes=first_int(infobox_field(text, "num_episodes")),
                released=parse_dates(infobox_field(text, "released", "first_aired", "release_date", "premiere")),
            )
    json.dump(out, open(path, "w"), ensure_ascii=False, indent=1)
    return out


OFFLINE = os.environ.get("OFFLINE") == "1"  # merge from whatever is cached, fetch nothing
REFRESH_RT = os.environ.get("REFRESH_RT") == "1"


# ------------------------------------------------------------------ Rotten Tomatoes
def rt_scores(page):
    if not page:
        return None
    m = re.search(r'<script[^>]*id="media-scorecard-json"[^>]*>(.*?)</script>', page, re.S)
    if not m:
        return None
    sc = json.loads(m.group(1))
    c, a = sc.get("criticsScore") or {}, sc.get("audienceScore") or {}
    name = year = seasons = None
    for j in re.finditer(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', page, re.S):
        try:
            d = json.loads(j.group(1))
        except ValueError:
            continue
        if isinstance(d, dict) and d.get("@type") in ("Movie", "TVSeries", "TVSeason"):
            name = htmllib.unescape(d.get("name") or "")
            year = (d.get("dateCreated") or d.get("startDate") or "")[:4]
            seasons = d.get("numberOfSeasons")
    num = lambda v: int(v) if v not in (None, "") else None
    return dict(c=num(c.get("score")), cn=c.get("reviewCount"), cert=bool(c.get("certified")),
                a=num(a.get("score")), name=name, year=year, seasons=seasons)


def stage_rt(seasons_by_key):
    path = os.path.join(HERE, "rt.json")
    out = {} if REFRESH_RT else json.load(open(path)) if os.path.exists(path) else {}
    if OFFLINE:
        return out
    for t in titles:
        if t["key"] in out or not t["rt"]:
            continue
        res = dict(main=rt_scores(curl(f"https://www.rottentomatoes.com/{t['rt']}", fresh=REFRESH_RT)), seasons={})
        if t["kind"] == "series" and t["rt"].startswith("tv/"):
            for s in seasons_by_key.get(t["key"], []):
                sc = rt_scores(curl(f"https://www.rottentomatoes.com/{t['rt']}/s{s:02d}", fresh=REFRESH_RT))
                if sc:
                    res["seasons"][str(s)] = sc
        out[t["key"]] = res
        json.dump(out, open(path, "w"), ensure_ascii=False, indent=1)
    return out


JAPAN_FIRST = {"gz-showa", "gz-heisei", "gz-millennium", "gz-reiwa"}


# ------------------------------------------------------------------ manual corrections after review
OVERRIDES = {
    "green-lantern": {"runtime": 114},  # Wikipedia infobox gives the 123-minute extended cut
    "rohirrim": {"date": "2024-12-13"},  # infobox carries only an unlabeled premiere date; US release per Wikidata
    # unaired: the article's Release section gives season 1 as eight episodes; the infobox has no count yet
    "hp-hbo": {"seasons": 1, "episodes": 8, "zh": "哈利·波特"},  # Douban names the series after its first season
}


# ------------------------------------------------------------------ merge + cross-check
def imdb_seasons(imdb, tc):
    """season -> [episode count, first year] for aired seasons (episodes with a year up to this year)."""
    seasons = {}
    for ep, (parent, s, _) in imdb["episodes"].items():
        if parent != tc or not s.isdigit():
            continue
        b = imdb["basics"].get(ep)
        yr = b and b["start"]
        rec = seasons.setdefault(int(s), [0, None])
        if yr and yr.isdigit() and int(yr) <= int(TODAY[:4]):
            rec[0] += 1
            rec[1] = min(rec[1] or 9999, int(yr))
    return {s: v for s, v in sorted(seasons.items()) if v[0]}


def main():
    pages, checked = douban_pages()
    imdb = stage_imdb(i for i in pages.values() if i)
    wiki = stage_wiki()
    seasons_by_key = {t["key"]: list(imdb_seasons(imdb, t["imdb"]).keys()) for t in titles if t["kind"] == "series" and t["imdb"]}
    douban = {}
    # films with a Wikidata Douban id: the title page itself (douban_subj.mjs), verified by Douban's IMDb id
    subj_path = os.path.join(HERE, "douban_subj.json")
    for k, r in (json.load(open(subj_path)) if os.path.exists(subj_path) else {}).items():
        if r.get("failed"):
            continue
        if r.get("imdb") and not r.get("verified"):
            flag(k, f"Wikidata Douban id {r['id']} is a different title on Douban ({r['zh']}, {r['imdb']})")
            continue
        douban[k] = dict(via="subject-page" + ("+imdb" if r.get("verified") else ""),
                         subjects=[dict(id=r["id"], title=r["zh"], r=r["r"], n=r["n"], year=r["year"], season=None)])
    # series and id-less films: mobile search + title page verified by IMDb id (douban_m.mjs)
    m_path = os.path.join(HERE, "douban_m.json")
    for k, r in (json.load(open(m_path)) if os.path.exists(m_path) else {}).items():
        if r.get("subjects"):
            douban[k] = r
    for v in douban.values():
        for s_ in v.get("subjects", []):
            s_["title"] = re.sub(r"\s+", " ", s_.get("title") or s_.get("zh") or "").strip()
            s_["id"] = str(s_["id"])
    # Every Douban page a script read records the IMDb id it lists (douban_check.mjs reads the later seasons, which come
    # from search rows sharing the show's name). A subject stays only when that id is this show or one of its episodes
    # (season pages usually list their first episode); one that names another IMDb title is dropped. Checked pages also
    # give the season's votes and year. Manual matches skip this (Singular Point's page lists a typo).
    by_key = {t["key"]: t for t in titles}
    for k, v in douban.items():
        tc, keep = by_key[k]["imdb"], []
        for s_ in v.get("subjects", []):
            listed = pages.get(s_["id"], "unread")
            ep = imdb["episodes"].get(listed or "")
            if "+manual" in (v.get("via") or "") or listed == tc or (ep and ep[0] == tc):
                if ep and ep[1].isdigit() and s_.get("season") and int(ep[1]) != s_["season"]:
                    flag(k, f"Douban {s_['id']} is season {s_['season']}, but its IMDb id {listed} is an episode of season {ep[1]}")
            elif listed == "unread":
                if s_.get("season") and s_["season"] > 1:
                    flag(k, f"Douban {s_['id']} (season {s_['season']}) not read yet; run douban_check.mjs")
            elif listed is None:
                flag(k, f"Douban {s_['id']} ({s_['title']}) lists no IMDb id")
            elif listed in imdb["basics"]:
                b = imdb["basics"][listed]
                flag(k, f"Douban {s_['id']} ({s_['title']}) is IMDb {listed}, {b['title']} ({b['start']}); dropped")
                continue
            else:
                flag(k, f"Douban {s_['id']} ({s_['title']}) lists IMDb {listed}, which IMDb's datasets don't have")
            if s_["id"] in checked:
                c = checked[s_["id"]]
                s_.update(r=c["r"], n=c["n"], year=c["year"] or s_.get("year"))
            keep.append(s_)
        v["subjects"] = keep
    rt = stage_rt(seasons_by_key)

    type_ok = {"movie": {"movie", "tvMovie", "video", "tvSpecial"}, "special": {"tvSpecial", "tvMovie", "movie", "tvShort"},
               "series": {"tvSeries", "tvMiniSeries"}}
    for t in titles:
        k, y = t["key"], year_of(t)
        upcoming = bool(t["date"] and t["date"] > TODAY)
        b = imdb["basics"].get(t["imdb"] or "")
        shared = sum(1 for x in titles if x["wiki"] == t["wiki"]) > 1  # anthology article covering several titles
        w = {} if shared else wiki.get(t["wiki"], {})
        # --- IMDb identity
        if not b:
            flag(k, f"IMDb id {t['imdb']} not in dataset")
        else:
            if b["type"] not in type_ok[t["kind"]]:
                flag(k, f"IMDb type {b['type']} vs kind {t['kind']}")
            if norm(b["title"]) != norm(t["en"]) and norm(b["orig"]) != norm(t["en"]):
                flag(k, f"IMDb title '{b['title']}' vs '{t['en']}'")
            if y and b["start"].isdigit() and abs(int(b["start"]) - y) > 0:
                flag(k, f"IMDb year {b['start']} vs date {t['date']}")
        # --- release date vs Wikipedia infobox
        wd = w.get("released") or []
        if wd:
            us = [d for d, pl in wd if "united states" in pl.lower() or pl.lower() in ("us", "u.s.")]
            wdate = (us or [min(d for d, _ in wd)])[0]
            if t["kind"] == "series":
                wdate = min(d for d, _ in wd)
            # Toho films: the Japanese release (their US dates trail by years); Wikidata often holds only the US one
            if any(p["c"] in JAPAN_FIRST for p in t["places"]):
                jp = [d for d, pl in wd if "japan" in pl.lower()]
                wdate = min(jp or [d for d, _ in wd])
            if t["date"] and wdate[:len(t["date"])] != t["date"][:len(wdate)]:
                flag(k, f"date {t['date']} (Wikidata) vs {wdate} (Wikipedia infobox {wd})")
                if len(wdate) >= len(t["date"]):
                    t["date_wikidata"] = t["date"]
                    t["date"] = wdate
        # --- runtime
        if t["kind"] != "series":
            rw, ri = w.get("runtime"), (int(b["runtime"]) if b and b["runtime"].isdigit() else None)
            t["runtime"] = rw or (None if upcoming else ri)  # IMDb runtimes for unreleased films are placeholders
            if rw and ri and abs(rw - ri) > 3:
                flag(k, f"runtime Wikipedia {rw} vs IMDb {ri} ({w.get('runtime_raw')!r})")
            if not t["runtime"] and not upcoming:
                flag(k, "no runtime")
        # --- seasons / episodes
        if t["kind"] == "series":
            iseas = imdb_seasons(imdb, t["imdb"]) if t["imdb"] else {}
            ws, we = w.get("seasons"), w.get("episodes")
            is_, ie = len(iseas), sum(v[0] for v in iseas.values())
            # unaired shows: IMDb's episode list is placeholders, so only Wikipedia's announced numbers count
            t["seasons"] = ws or (None if upcoming else is_ or None)
            t["episodes"] = we or (None if upcoming else ie or None)
            if ws and is_ and ws != is_:
                flag(k, f"seasons Wikipedia {ws} vs IMDb {is_}")
            if we and ie and we != ie:
                flag(k, f"episodes Wikipedia {we} vs IMDb {ie}")
            # IMDb lists placeholder episodes for announced seasons; keep only the seasons Wikipedia counts as aired
            sl = [dict(s=s, eps=v[0], year=v[1]) for s, v in iseas.items() if (not ws and not upcoming) or (ws and s <= ws)]
            if sl and y:
                sl[0]["year"] = y if sl[0]["s"] == 1 else sl[0]["year"]
            # when IMDb splits seasons differently from Wikipedia, per-season numbers would mislead
            if ws and we and (len(sl) != ws or abs(sum(x["eps"] for x in sl) - we) > 0.1 * we):
                flag(k, f"IMDb season split {[(x['s'], x['eps']) for x in sl]} disagrees with Wikipedia {ws}/{we}; per-season episodes dropped")
                for x in sl:
                    x["eps"] = None
            t["season_list"] = sl
        # --- ratings
        r = imdb["ratings"].get(t["imdb"] or "")
        t["imdb_r"] = dict(r=r[0], n=r[1]) if r else None
        dbr = douban.get(k, {})
        subs = dbr.get("subjects") or []
        if k not in douban:
            flag(k, "Douban pending")
        elif not subs and not upcoming:
            flag(k, f"no Douban match; candidates {dbr.get('candidates')}")
        elif subs and t["douban"] and t["douban"] not in {s_["id"] for s_ in subs}:
            flag(k, f"Wikidata Douban id {t['douban']} differs from verified match {[s_['id'] + ' ' + s_['title'] for s_ in subs][:2]}")
        if dbr.get("via") == "api-search-year":
            flag(k, f"Douban matched by title+year only (no original-title check): {[s_['id'] + ' ' + s_['title'] + ' ' + str(s_['year']) for s_ in subs][:4]}")
        if t["kind"] != "series":
            s0 = subs[0] if subs else None
            t["douban"] = s0["id"] if s0 else None
            t["db_r"] = dict(r=s0["r"], n=s0["n"]) if s0 and s0["r"] else None
            if s0 and s0["title"] and s0["title"] != t["zh"]:
                flag(k, f"zh title curated '{t['zh']}' vs Douban '{s0['title']}'")
                t["zh_curated"], t["zh"] = t["zh"], s0["title"]

        else:
            by_season = {}
            for s in subs:
                sn = s["season"] or 1
                # Douban already lists announced seasons; skip anything not yet aired
                if (s["year"] and int(s["year"]) > int(TODAY[:4])) or (t.get("seasons") and sn > t["seasons"] and not upcoming):
                    continue
                by_season.setdefault(sn, s)
            if subs:
                first = by_season.get(1) or subs[0]
                t["douban"] = first["id"]
                base = re.sub(r"\s*第[一二三四五六七八九十\d]+季$", "", first["title"])
                if base != t["zh"]:
                    flag(k, f"zh title curated '{t['zh']}' vs Douban '{base}'")
                    t["zh_curated"], t["zh"] = t["zh"], base
            else:
                t["douban"] = None
            sl = {x["s"]: x for x in t["season_list"]}
            for sn, s in by_season.items():
                rec = sl.setdefault(sn, dict(s=sn, eps=None, year=int(s["year"]) if s["year"] else None))
                rec["db"] = dict(id=s["id"], r=s["r"], n=s["n"])
            t["season_list"] = [sl[s] for s in sorted(sl)]
            s1 = by_season.get(1)
            t["db_r"] = dict(r=s1["r"], n=s1["n"], season=1) if s1 and s1["r"] else None
        rr = (rt.get(k) or {}).get("main")
        if t["rt"] and not rr:
            flag(k, f"RT page {t['rt']} missing or without scorecard")
        if rr:
            if rr["name"] and norm(rr["name"]) != norm(t["en"]):
                flag(k, f"RT name '{rr['name']}' vs '{t['en']}'")
            if rr["year"] and y and abs(int(rr["year"]) - y) > 1:
                flag(k, f"RT year {rr['year']} vs {t['date']}")
            t["rt_r"] = dict(c=rr["c"], a=rr["a"], cert=rr["cert"], n=rr["cn"]) if (rr["c"] is not None or rr["a"] is not None) else None
            for sn, sc in (rt.get(k) or {}).get("seasons", {}).items():
                for rec in t.get("season_list", []):
                    if rec["s"] == int(sn):
                        rec["rt"] = sc["c"]
        else:
            t["rt_r"] = None
        if not t["imdb_r"] and not upcoming:
            flag(k, "no IMDb rating")

    for t in titles:
        for f, v in OVERRIDES.get(t["key"], {}).items():
            t[f] = v
    data["ratings_date"] = TODAY
    json.dump(data, open(os.path.join(HERE, "data_enriched.json"), "w"), ensure_ascii=False, indent=1)
    open(os.path.join(HERE, "report.txt"), "w").write("\n".join(sorted(report)) + "\n")
    print(f"{len(report)} flags -> report.txt")


if __name__ == "__main__":
    main()
