"""Resolve seed titles against Wikipedia + Wikidata, download posters, write data.json."""
import hashlib, io, json, os, re, subprocess, sys, time, urllib.parse, urllib.request

from PIL import Image

from seed import CONTINUITIES, TITLES
from zh_titles import ZH

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "cache")
POSTERS = os.path.join(os.path.dirname(HERE), "site", "posters")
os.makedirs(CACHE, exist_ok=True)
os.makedirs(POSTERS, exist_ok=True)
UA = "Agamotto/1.0 (https://timeline.luminoid.dev; personal non-commercial fan index) python-urllib"
BROWSER_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36"
TODAY = "2026-10-10"


def get(url, binary=False, ua=UA):
    key = hashlib.sha1(url.encode()).hexdigest()
    path = os.path.join(CACHE, key)
    if os.path.exists(path):
        data = open(path, "rb").read()
    else:
        for attempt in range(6):
            try:
                if "themoviedb.org" in url:  # TMDB refuses urllib's TLS fingerprint; curl gets through
                    data = subprocess.run(["curl", "-sfL", "-m", "30", "-A", BROWSER_UA, url],
                                          capture_output=True, check=True).stdout
                else:
                    req = urllib.request.Request(url, headers={"User-Agent": ua})
                    data = urllib.request.urlopen(req, timeout=60).read()
                break
            except Exception as e:  # noqa: BLE001
                print("  retry", attempt, e, url[:120], file=sys.stderr)
                # Wikimedia answers bursts with 429; back off for real instead of hammering
                time.sleep(45 * (attempt + 1) if "429" in str(e) else 2 + attempt * 3)
        else:
            raise RuntimeError("failed " + url)
        open(path, "wb").write(data)
        time.sleep(1.0)
    return data if binary else json.loads(data)


def api(host, **params):
    params.setdefault("format", "json")
    params.setdefault("formatversion", "2")
    return get(f"https://{host}/w/api.php?" + urllib.parse.urlencode(params))


def chunks(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i : i + n]


def resolve_enwiki(titles):
    """title -> page dict (after normalization and redirects)."""
    out = {}
    for batch in chunks(titles, 50):
        r = api("en.wikipedia.org", action="query", titles="|".join(batch), redirects=1,
                prop="pageprops|pageimages", ppprop="wikibase_item|disambiguation",
                piprop="thumbnail|name", pithumbsize=500, pilicense="any")
        q = r["query"]
        alias = {t: t for t in batch}
        for n in q.get("normalized", []):
            for k, v in alias.items():
                if v == n["from"]:
                    alias[k] = n["to"]
        for rd in q.get("redirects", []):
            for k, v in alias.items():
                if v == rd["from"]:
                    alias[k] = rd["to"]
        pages = {p["title"]: p for p in q["pages"]}
        for k, v in alias.items():
            out[k] = pages.get(v)
    return out


def wd_entities(qids):
    out = {}
    for batch in chunks(qids, 50):
        r = api("www.wikidata.org", action="wbgetentities", ids="|".join(batch),
                props="claims|labels|sitelinks", languages="zh-cn|zh-hans|zh|en",
                sitefilter="zhwiki|enwiki")
        out.update(r["entities"])
    return out


def claim_values(ent, prop):
    vals = []
    for c in ent.get("claims", {}).get(prop, []):
        if c.get("rank") == "deprecated":
            continue
        dv = c["mainsnak"].get("datavalue")
        if dv:
            vals.append((dv["value"], c.get("qualifiers", {}), c.get("rank")))
    return vals


def parse_time(v):
    t, prec = v["time"], v["precision"]
    m = re.match(r"\+(\d{4})-(\d{2})-(\d{2})", t)
    if not m:
        return None
    y, mo, d = m.groups()
    if prec >= 11:
        return f"{y}-{mo}-{d}"
    if prec == 10:
        return f"{y}-{mo}"
    return y


def release_date(ent, series=False):
    """Films: the US release, else the earliest dated release. Series: the earliest premiere."""
    pubs = claim_values(ent, "P577")
    us, rest = [], []
    for v, quals, _ in pubs:
        d = parse_time(v)
        if not d:
            continue
        places = [q["datavalue"]["value"]["id"] for q in quals.get("P291", []) if q.get("datavalue")]
        (us if "Q30" in places else rest).append(d)
    # day-precision dates sort before coarser ones for the same year
    def best(ds):
        full = sorted(d for d in ds if len(d) == 10)
        return full[0] if full else (sorted(ds)[0] if ds else None)
    start = [parse_time(v) for v, _, _ in claim_values(ent, "P580")]
    start = [s for s in start if s]
    if series:
        return best(start + us + rest)
    return best(us) or best(rest) or best(start)


def first_string(ent, prop):
    vals = claim_values(ent, prop)
    pref = [v for v, _, rank in vals if rank == "preferred"]
    allv = pref + [v for v, _, _ in vals]
    return allv[0] if allv else None


def strip_disambig(t):
    return re.sub(r"\s*[（(][^（）()]*[）)]\s*$", "", t).strip()


def zh_titles(zh_wiki_titles):
    out = {}
    for batch in chunks(zh_wiki_titles, 50):
        r = api("zh.wikipedia.org", action="query", titles="|".join(batch), redirects=1,
                prop="info", inprop="varianttitles")
        q = r["query"]
        alias = {t: t for t in batch}
        for n in q.get("normalized", []) + q.get("redirects", []):
            for k, v in alias.items():
                if v == n["from"]:
                    alias[k] = n["to"]
        pages = {p["title"]: p for p in q["pages"]}
        for k, v in alias.items():
            p = pages.get(v) or {}
            vt = p.get("varianttitles", {})
            out[k] = strip_disambig(vt.get("zh-cn") or vt.get("zh-hans") or v)
    return out


def season_one_candidates(wiki):
    base = re.sub(r"\s*\((?:\d{4} )?(?:American )?TV series\)$", "", wiki)
    cands = [f"{base} season 1"]
    if base.startswith("Star Wars: "):
        cands.append(f"{base[len('Star Wars: '):]} season 1")
    else:
        cands.append(f"Star Wars: {base} season 1")
    return cands


# Cards show posters at 86 CSS px wide (70 on phones) in a 2:3 frame; 200x300 covers 2x screens and most 3x ones.
POSTER_W, POSTER_H = 200, 300
# Tapping a poster opens the whole, uncropped image at its own size (never enlarged, so it stays as sharp as the
# source): at most 500x750. Wikipedia keeps posters near 260 px wide, so most are their original size.
FULL_W, FULL_H = 500, 750


def save_poster(url, key):
    raw = get(url, binary=True)
    im = Image.open(io.BytesIO(raw)).convert("RGB")
    full = im.copy()
    full.thumbnail((FULL_W, FULL_H), Image.LANCZOS)  # shrinks only, keeps the aspect
    os.makedirs(os.path.join(POSTERS, "full"), exist_ok=True)
    full.save(os.path.join(POSTERS, "full", key + ".webp"), "WEBP", quality=88, method=6)  # close to the source JPEG
    w, h = im.size
    # scale to cover the frame, then centre-crop: the same crop the card's object-fit: cover would make
    scale = max(POSTER_W / w, POSTER_H / h)
    im = im.resize((max(POSTER_W, round(w * scale)), max(POSTER_H, round(h * scale))), Image.LANCZOS)
    left, top = (im.width - POSTER_W) // 2, (im.height - POSTER_H) // 2
    im = im.crop((left, top, left + POSTER_W, top + POSTER_H))
    path = os.path.join(POSTERS, key + ".webp")
    im.save(path, "WEBP", quality=80, method=6)
    return f"posters/{key}.webp", full.size  # pw/ph: the full poster's size, which the zoom opens at


def main():
    seeds = TITLES
    keys = [s["key"] for s in seeds]
    assert len(keys) == len(set(keys)), "duplicate keys"

    pages = resolve_enwiki([s["wiki"] for s in seeds])
    problems = []
    qids = {}
    for s in seeds:
        p = pages.get(s["wiki"])
        if not p or p.get("missing"):
            problems.append(f"MISSING  {s['key']}: {s['wiki']}")
            continue
        pp = p.get("pageprops", {})
        if "disambiguation" in pp:
            problems.append(f"DISAMBIG {s['key']}: {s['wiki']}")
            continue
        s["_page"] = p
        if s.get("qid"):
            qids[s["key"]] = s["qid"]
        elif "wikibase_item" in pp:
            qids[s["key"]] = pp["wikibase_item"]
        else:
            problems.append(f"NO QID   {s['key']}: {s['wiki']}")

    ents = wd_entities(sorted(set(qids.values())))

    zh_wiki = {}
    for s in seeds:
        e = ents.get(qids.get(s["key"], ""), {})
        sl = e.get("sitelinks", {}).get("zhwiki")
        if sl:
            zh_wiki[s["key"]] = sl["title"]
    zh_map = zh_titles(sorted(set(zh_wiki.values())))

    # season-one poster fallback for series whose infobox image is a wide title card or absent
    fallback_titles = {}
    for s in seeds:
        if s["kind"] != "series" or "_page" not in s or s.get("qid"):
            continue
        th = s["_page"].get("thumbnail")
        if not th or th["width"] > th["height"]:
            for c in season_one_candidates(s["_page"]["title"]):
                fallback_titles.setdefault(c, []).append(s["key"])
    fb_pages = resolve_enwiki(sorted(fallback_titles)) if fallback_titles else {}
    fb_thumb = {}
    for title, ks in fallback_titles.items():
        p = fb_pages.get(title)
        th = p and not p.get("missing") and p.get("thumbnail")
        if th and th["height"] > th["width"]:
            for k in ks:
                fb_thumb.setdefault(k, (th["source"], title))

    def tmdb_poster(ent, kind):
        tv, mv = first_string(ent, "P4983"), first_string(ent, "P4947")
        path = f"tv/{tv}" if tv and (kind == "series" or not mv) else (f"movie/{mv}" if mv else None)
        if not path:
            return None
        html = get(f"https://www.themoviedb.org/{path}", binary=True, ua=BROWSER_UA).decode("utf-8", "replace")
        m = re.search(r'<meta property="og:image" content="([^"]+/t/p/)w\d+(/[^"]+\.jpg)"', html)
        return m and (m.group(1) + "w342" + m.group(2))

    out = []
    for s in seeds:
        if "_page" not in s:
            continue
        e = ents.get(qids.get(s["key"], ""), {})
        labels = e.get("labels", {})
        zh = ZH.get(s["key"]) or zh_map.get(zh_wiki.get(s["key"], ""))
        if not zh:
            for lang in ("zh-cn", "zh-hans", "zh"):
                if lang in labels:
                    zh = labels[lang]["value"]
                    break
        th = None if s.get("qid") else s["_page"].get("thumbnail")
        poster_src, poster_from = None, None
        if s["key"] in fb_thumb:
            poster_src, poster_from = fb_thumb[s["key"]]
        elif th and th["height"] > th["width"]:
            poster_src, poster_from = th["source"], s["_page"]["title"]
        else:
            try:
                poster_src, poster_from = tmdb_poster(e, s["kind"]), "TMDB"
            except Exception as ex:  # noqa: BLE001
                problems.append(f"TMDB     {s['key']}: {ex}")
            if not poster_src and th:
                poster_src, poster_from = th["source"], s["_page"]["title"]
        poster, size = None, None
        if poster_src:
            try:
                poster, size = save_poster(poster_src, s["key"])
            except Exception as ex:  # noqa: BLE001
                problems.append(f"POSTER   {s['key']}: {ex}")
        else:
            problems.append(f"NO IMG   {s['key']}: {s['wiki']}")

        rt = first_string(e, "P1258")
        rec = dict(
            key=s["key"], kind=s["kind"], anim=s["anim"],
            en=s.get("en") or strip_disambig(s["_page"]["title"]),
            zh=zh or None,
            date=release_date(e, series=s["kind"] == "series"),
            imdb=first_string(e, "P345"),
            douban=first_string(e, "P4529"),
            rt=rt,
            wiki=s["_page"]["title"],
            qid=qids.get(s["key"]),
            poster=poster, poster_from=poster_from,
            pw=size[0] if size else None, ph=size[1] if size else None,
            places=[dict(c=c, n=n, se=se, sz=sz, s=sn) for c, n, se, sz, sn in s["places"]],
        )
        for f in ("zh", "date", "imdb"):
            if not rec[f]:
                problems.append(f"NO {f.upper():6}{s['key']}: {s['wiki']}")
        out.append(rec)

    data = dict(
        generated=TODAY,
        continuities={k: dict(f=v[0], en=v[1], zh=v[2], o=v[3]) for k, v in CONTINUITIES.items()},
        titles=out,
    )
    json.dump(data, open(os.path.join(HERE, "data.json"), "w"), ensure_ascii=False, indent=1)
    print(f"{len(out)} titles written, {sum(1 for r in out if r['poster'])} posters")
    print("\n".join(problems) or "no problems")


if __name__ == "__main__":
    main()
