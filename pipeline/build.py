"""template.html + data_enriched.json -> the site (site/index.html, 404.html, _headers, robots.txt, sitemap.xml)
and artifact.html (the head-less fragment for the claude.ai preview)."""
import base64, hashlib, html as htmllib, json, os, re, urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(os.path.dirname(HERE), "site")
SITE_URL = "https://timeline.luminoid.dev"  # canonical, og:url, og:image, sitemap and robots.txt
src = os.path.join(HERE, "data_enriched.json")
data = json.load(open(src if os.path.exists(src) else os.path.join(HERE, "data.json")))
template = open(os.path.join(HERE, "template.html")).read()

# These values go into URLs, ids and attributes without escaping, so the build refuses anything outside these shapes.
SHAPES = {"key": r"[a-z0-9-]+", "imdb": r"tt\d+", "douban": r"\d+", "rt": r"(m|tv)/[a-z0-9_-]+"}
for c in data["continuities"]:
    assert re.fullmatch(SHAPES["key"], c), f"continuity key {c!r}"
for t in data["titles"]:
    for f, shape in SHAPES.items():
        assert t.get(f) is None or re.fullmatch(shape, str(t[f])), f"{t['key']}: {f} {t.get(f)!r}"
    for s in t.get("season_list") or []:
        assert isinstance(s["s"], int) and all(s.get(f) is None or isinstance(s[f], int) for f in ("year", "eps", "rt")), f"{t['key']} season {s}"
        assert not s.get("db") or re.fullmatch(SHAPES["douban"], str(s["db"]["id"])), f"{t['key']} season {s['s']} douban id"

# Strip what the page never reads. Posters are always posters/<key>.webp at 200x300 plus the uncropped
# posters/full/<key>.webp that the zoom opens at its own size, pw x ph (fetch.py), so only a missing one is marked.
data.pop("generated", None)
for t in data["titles"]:
    for f in ("wiki", "qid", "poster_from", "date_wikidata", "zh_curated"):
        t.pop(f, None)
    poster = t.pop("poster", None)
    if not poster:
        t["nop"] = True
    else:
        assert poster == f"posters/{t['key']}.webp" and os.path.exists(os.path.join(SITE, poster)), f"{t['key']}: poster {poster}"
        assert os.path.exists(os.path.join(SITE, "posters", "full", t["key"] + ".webp")), f"{t['key']}: no full-size poster"
    if t.get("db_r"):
        t["db_r"].pop("season", None)
    if t.get("rt_r"):
        t["rt_r"].pop("n", None)
# one version for all posters: when any of them changes, every URL changes, so a year-long browser cache stays correct
digest = hashlib.sha1()
for folder in ("posters", "posters/full"):
    for name in sorted(n for n in os.listdir(os.path.join(SITE, folder)) if n.endswith(".webp")):
        digest.update(f"{folder}/{name}".encode() + open(os.path.join(SITE, folder, name), "rb").read())
poster_v = digest.hexdigest()[:8]

# The two dark-mode token blocks (system preference, and the host's data-theme) must stay identical.
dark = re.findall(r'(?:prefers-color-scheme: dark\) \{\s*:root:not\(\[data-theme="light"\]\)|:root\[data-theme="dark"\]) \{([^}]*)\}', template)
assert len(dark) == 2 and dark[0].split() == dark[1].split(), "the two dark token blocks in template.html differ"

# glyphs the Chinese display face renders: the masthead, continuity headings and the Marvel stinger
first = lambda pattern: re.search(pattern, template).group(1)
zh_block = template[template.index("    zh: {"):]
zh_display = re.sub(r"<[^>]+>", "", re.search(r"h1: '([^']+)'", zh_block).group(1)) + re.search(r'stinger: "([^"]+)"', zh_block).group(1)
zh_display += "0123456789" + "".join(c["zh"] for c in data["continuities"].values())
text = urllib.parse.quote("".join(sorted(set(zh_display))))

payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")  # no "</script" or "<!--"
html = template.replace("__ZH_DISPLAY_TEXT__", text).replace("__POSTER_V__", poster_v).replace("__DATA__", payload)
site_html = html.replace("__CARD_DIR__", "posters")

# The template is a fragment: the claude.ai artifact host wraps it in its own document, so the preview gets the
# fragment. The site gets a full document; without the charset meta a plain server's "text/html" decodes as
# windows-1252 and every Chinese string turns to mojibake. An artifact version holds at most 511 files, too few for
# both poster sets, so the preview's cards use the full posters too.
open(os.path.join(HERE, "artifact.html"), "w").write(html.replace("__CARD_DIR__", "posters/full"))
html = site_html

# ---------------------------------------------------------------- the full document
TITLE = first(r'title: "([^"]+)"')  # T.en.title, the same one the page sets at runtime
DESCRIPTION = ("Watch order for every film and series from Marvel, X-Men, DC, Star Wars, Alien & Predator, Godzilla, "
               "Planet of the Apes, Dune, Middle-earth, the Wizarding World and Westeros, with IMDb, Douban and "
               "Rotten Tomatoes ratings.")
OG_ALT = "Agamotto: watch order for eleven film franchises, from Marvel to Westeros"
a = lambda s: htmllib.escape(s, quote=True)
ld = json.dumps({"@context": "https://schema.org", "@type": "WebSite", "name": "Agamotto", "url": SITE_URL + "/",
                 "description": DESCRIPTION, "inLanguage": ["en", "zh-Hans"]}, ensure_ascii=False).replace("<", "\\u003c")
meta = f"""<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<meta name="theme-color" content="#f2f3f6" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#0c0e13" media="(prefers-color-scheme: dark)">
<title>{a(TITLE)}</title>
<meta name="description" content="{a(DESCRIPTION)}">
<link rel="canonical" href="{SITE_URL}/">
<link rel="icon" href="favicon.ico" sizes="32x32">
<link rel="icon" href="favicon.svg" type="image/svg+xml">
<link rel="icon" href="favicon-32.png" type="image/png" sizes="32x32">
<link rel="icon" href="favicon-16.png" type="image/png" sizes="16x16">
<link rel="apple-touch-icon" href="apple-touch-icon.png">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Agamotto">
<meta property="og:title" content="{a(TITLE)}">
<meta property="og:description" content="{a(DESCRIPTION)}">
<meta property="og:url" content="{SITE_URL}/">
<meta property="og:image" content="{SITE_URL}/og.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="{a(OG_ALT)}">
<meta property="og:locale" content="en_US">
<meta property="og:locale:alternate" content="zh_CN">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{a(TITLE)}">
<meta name="twitter:description" content="{a(DESCRIPTION)}">
<meta name="twitter:image" content="{SITE_URL}/og.png">
<meta name="twitter:image:alt" content="{a(OG_ALT)}">
<script type="application/ld+json">{ld}</script>"""

assert html.count("<title>Agamotto</title>") == 1 and html.count('<div id="app"') == 1, "template markers moved"
head, body = html.replace("<title>Agamotto</title>\n", "").split('<div id="app"', 1)
# crawlers and link previews that don't run scripts still get the English heading and intro (T.en comes first)
h1_en, intro_en = first(r"h1: '([^']+)'"), first(r'intro: "([^"]+)"')
body = body.replace('<h1 id="h1"></h1>', f'<h1 id="h1">{h1_en}</h1>', 1).replace('<p id="intro"></p>', f'<p id="intro">{a(intro_en)}</p>', 1)
page = f"""<!doctype html>
<html lang="en">
<head>
{meta}
{head.strip()}
</head>
<body>
<div id="app"{body.rstrip()}
</body>
</html>
"""
out = os.path.join(SITE, "index.html")
open(out, "w").write(page)

# ---------------------------------------------------------------- Cloudflare Pages files
scripts = re.findall(r"<script>(.*?)</script>", page, re.S)
assert len(scripts) == 1, "expected exactly one inline script (the JSON blocks have a type)"
script_hash = base64.b64encode(hashlib.sha256(scripts[0].encode()).digest()).decode()
CSP = "; ".join([
    "default-src 'self'",
    f"script-src 'sha256-{script_hash}'",
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",  # the inline <style> and style attributes
    "font-src https://fonts.gstatic.com",
    "img-src 'self'",
    "connect-src 'none'",
    "object-src 'none'",
    "base-uri 'none'",
    "form-action 'none'",
    "frame-ancestors 'none'",
])
ICONS = ("og.png", "favicon.ico", "favicon.svg", "favicon-16.png", "favicon-32.png", "apple-touch-icon.png")
headers = f"""# Written by pipeline/build.py on every build: the CSP carries the hash of the page's one inline script.
/*
  Content-Security-Policy: {CSP}
  X-Content-Type-Options: nosniff
  X-Frame-Options: DENY
  Referrer-Policy: strict-origin-when-cross-origin
  Strict-Transport-Security: max-age=63072000; includeSubDomains
  Permissions-Policy: camera=(), microphone=(), geolocation=(), payment=(), usb=()
  Cross-Origin-Opener-Policy: same-origin

# poster URLs carry a version (?v=), so browsers may keep them for a year
/posters/*
  Cache-Control: public, max-age=31536000, immutable
""" + "".join(f"\n/{name}\n  Cache-Control: public, max-age=86400\n" for name in ICONS)
open(os.path.join(SITE, "_headers"), "w").write(headers)
open(os.path.join(SITE, "robots.txt"), "w").write(f"User-agent: *\nAllow: /\n\nSitemap: {SITE_URL}/sitemap.xml\n")
open(os.path.join(SITE, "sitemap.xml"), "w").write(f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>{SITE_URL}/</loc><lastmod>{data["ratings_date"]}</lastmod></url>
</urlset>
""")
open(os.path.join(SITE, "404.html"), "w").write("""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<meta name="robots" content="noindex">
<title>Not found · Agamotto</title>
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<style>
:root { --bg: #f2f3f6; --fg: #141821; --muted: #5a6273; --accent: #3b3f8f; }
@media (prefers-color-scheme: dark) { :root { --bg: #0c0e13; --fg: #e8ebf1; --muted: #98a1b3; --accent: #a9adff; } }
body { margin: 0; min-height: 100vh; display: grid; place-items: center; background: var(--bg); color: var(--fg); font: 400 16px/1.5 system-ui, "PingFang SC", "Microsoft YaHei", sans-serif; }
main { padding: 24px 16px; text-align: center; }
.code { margin: 0; font: 400 96px/1 Impact, "Arial Narrow", sans-serif; color: var(--accent); }
h1 { margin: 8px 0 4px; font-size: 22px; }
p { margin: 0 0 6px; color: var(--muted); }
a { color: var(--fg); font-weight: 600; text-underline-offset: 3px; }
</style>
</head>
<body>
<main>
<p class="code">404</p>
<h1>This page isn't here</h1>
<p lang="zh-Hans">这个页面不存在</p>
<p><a href="/">Go to the watch order</a> · <a href="/" lang="zh-Hans">前往观影顺序</a></p>
</main>
</body>
</html>
""")
missing = [n for n in ICONS if not os.path.exists(os.path.join(SITE, n))]
print(f"wrote {out}: {len(page.encode()) / 1024:.0f} KB, {len(data['titles'])} titles, plus 404.html, _headers, robots.txt, "
      f"sitemap.xml and the artifact fragment" + (f"; missing icons (run make icons): {', '.join(missing)}" if missing else ""))
