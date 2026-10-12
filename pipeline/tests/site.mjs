// Release checks for the built site, in headless Chrome over CDP; exits 1 on any failure. Serves site/ with the
// headers from site/_headers (so the Content-Security-Policy is live) and checks: the release-baseline files and meta
// tags, that the CSP blocks nothing the page does, keyboard focus and screen-reader announcements, that bad stored
// settings can't break the page, and that the English and Chinese strings have the same keys.
import { spawn } from "node:child_process";
import crypto from "node:crypto";
import fs from "node:fs";
import http from "node:http";
import os from "node:os";
import path from "node:path";
import vm from "node:vm";
import { fileURLToPath } from "node:url";

const HERE = fileURLToPath(new URL(".", import.meta.url));
const ROOT = path.join(HERE, "..", "..");
const SITE = path.join(ROOT, "site");
const CHROME = process.env.CHROME || "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const PROFILE = fs.mkdtempSync(path.join(os.tmpdir(), "agamotto-"));
const PORT = 9363;
let failed = 0;
const check = (name, ok, info = "") => { console.log(`${ok ? "ok  " : "FAIL"} ${name}${info ? "  " + info : ""}`); if (!ok) failed++; };

// ---------------------------------------------------------------- files and tags
const page = fs.readFileSync(path.join(SITE, "index.html"), "utf8");
const headersFile = fs.readFileSync(path.join(SITE, "_headers"), "utf8");
const pngSize = (f) => { const b = fs.readFileSync(path.join(SITE, f)); return `${b.readUInt32BE(16)}x${b.readUInt32BE(20)}`; };
const files = ["favicon.ico", "favicon.svg", "favicon-16.png", "favicon-32.png", "apple-touch-icon.png", "og.png", "robots.txt", "sitemap.xml", "404.html", "_headers"];
const missing = files.filter((f) => !fs.existsSync(path.join(SITE, f)));
check("release files exist", !missing.length && fs.existsSync(path.join(ROOT, "LICENSE")), missing.join(", "));
check("icon and card sizes", pngSize("favicon-16.png") === "16x16" && pngSize("favicon-32.png") === "32x32" && pngSize("apple-touch-icon.png") === "180x180" && pngSize("og.png") === "1200x630");
const tags = ['name="description"', 'rel="canonical"', 'property="og:title"', 'property="og:description"', 'property="og:type"', 'property="og:url"', 'property="og:image"',
  'name="twitter:card"', 'name="twitter:title"', 'name="twitter:description"', 'name="twitter:image"', 'rel="apple-touch-icon"', 'charset="utf-8"', 'name="viewport"'];
const head = page.slice(0, page.indexOf("</head>"));
check("meta tags present", tags.every((t) => head.includes(t)), tags.filter((t) => !head.includes(t)).join(", "));
const site = (head.match(/rel="canonical" href="([^"]+)"/) || [])[1];
check("robots.txt and sitemap point at the canonical URL", fs.readFileSync(path.join(SITE, "robots.txt"), "utf8").includes(`${site}sitemap.xml`) && fs.readFileSync(path.join(SITE, "sitemap.xml"), "utf8").includes(`<loc>${site}</loc>`), site);
const inline = [...page.matchAll(/<script>([\s\S]*?)<\/script>/g)].map((m) => m[1]);
const hash = inline.length === 1 && crypto.createHash("sha256").update(inline[0]).digest("base64");
check("CSP hash matches the inline script", !!hash && headersFile.includes(`'sha256-${hash}'`));
check("IMDb's required credit line is on the page", page.includes('Information courtesy of IMDb (<a href="https://www.imdb.com"') && page.includes("). Used with permission.</p>"));
check("crawlers get the heading without scripts", /<h1 id="h1">Watch <span class="bar">Order<\/span><\/h1>/.test(page));

// the strings: same keys, same function arity, same list lengths in both languages
const src = fs.readFileSync(path.join(HERE, "..", "template.html"), "utf8");
const T = vm.runInNewContext("(" + src.slice(src.indexOf("const T = {") + 10, src.indexOf("\n  };\n", src.indexOf("const T = {")) + 4) + ")");
const diffs = [];
const walk = (a, b, at) => {
  for (const k of new Set([...Object.keys(a), ...Object.keys(b)])) {
    const x = a[k], y = b[k], p = at + "." + k;
    if (x === undefined || y === undefined) diffs.push(p + (x === undefined ? " missing in en" : " missing in zh"));
    else if (typeof x !== typeof y || Array.isArray(x) !== Array.isArray(y)) diffs.push(p + " type");
    else if (typeof x === "function" && x.length !== y.length) diffs.push(p + " arity");
    else if (Array.isArray(x) && x.length !== y.length) diffs.push(p + " length");
    else if (x && typeof x === "object" && !Array.isArray(x)) walk(x, y, p);
  }
};
walk(T.en, T.zh, "T");
check("English and Chinese strings match", !diffs.length, diffs.join(", "));
const dash = JSON.stringify(T).match(/[^"]*—[^"]*/g);
check("no em dashes in page strings", !dash, dash ? dash.join(" | ") : "");

// ---------------------------------------------------------------- the page, served with its headers
const block = headersFile.split(/\n(?=\/)/).find((b) => b.startsWith("/*\n"));
const sent = Object.fromEntries(block.split("\n").slice(1).filter((l) => /^\s+\S/.test(l)).map((l) => { const i = l.indexOf(":"); return [l.slice(0, i).trim(), l.slice(i + 1).trim()]; }));
const TYPES = { ".html": "text/html; charset=utf-8", ".webp": "image/webp", ".png": "image/png", ".svg": "image/svg+xml", ".ico": "image/x-icon", ".txt": "text/plain", ".xml": "application/xml" };
const server = http.createServer((req, res) => {
  const p = decodeURIComponent(new URL(req.url, "http://x").pathname);
  const file = path.join(SITE, p === "/" ? "index.html" : p);
  const ok = file.startsWith(SITE) && fs.existsSync(file) && fs.statSync(file).isFile();
  res.writeHead(ok ? 200 : 404, { ...sent, "Content-Type": TYPES[ok ? path.extname(file) : ".html"] || "application/octet-stream" });
  res.end(fs.readFileSync(ok ? file : path.join(SITE, "404.html")));
}).listen(0, "127.0.0.1");
await new Promise((r) => server.on("listening", r));
const BASE = `http://127.0.0.1:${server.address().port}/`;

const chrome = spawn(CHROME, ["--headless=new", "--disable-gpu", "--hide-scrollbars", `--remote-debugging-port=${PORT}`, `--user-data-dir=${PROFILE}`, "about:blank"], { stdio: "ignore" });
process.on("exit", () => { try { chrome.kill("SIGKILL"); } catch {} fs.rmSync(PROFILE, { recursive: true, force: true, maxRetries: 3 }); });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let ws;
for (let i = 0; i < 60 && !ws; i++) {
  try {
    const p = (await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json()).find((t) => t.type === "page");
    if (p) { ws = new WebSocket(p.webSocketDebuggerUrl); await new Promise((r, j) => { ws.onopen = r; ws.onerror = j; }); }
  } catch { ws = null; }
  if (!ws) await sleep(300);
}
let seq = 0;
const pending = new Map(), errors = [];
ws.onmessage = (e) => {
  const m = JSON.parse(e.data);
  if (m.method === "Runtime.exceptionThrown") errors.push(m.params.exceptionDetails.exception?.description || m.params.exceptionDetails.text);
  if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); }
};
const send = (method, params = {}) => new Promise((res) => { const id = ++seq; const t = setTimeout(() => res({}), 20000); pending.set(id, (m) => { clearTimeout(t); res(m); }); ws.send(JSON.stringify({ id, method, params })); });
const ev = async (x) => (await send("Runtime.evaluate", { expression: x, returnByValue: true, awaitPromise: true })).result?.result?.value;
// via about:blank, so a URL that differs only in its #hash still loads the page afresh
const go = async (url, ms = 1500) => { await send("Page.navigate", { url: "about:blank" }); await sleep(200); await send("Page.navigate", { url }); await sleep(ms); };
const KEYS = { Enter: [13, "\r"], Tab: [9, ""], Escape: [27, ""] };
const key = async (k) => {
  await send("Input.dispatchKeyEvent", { type: "keyDown", key: k, code: k, windowsVirtualKeyCode: KEYS[k][0], ...(KEYS[k][1] ? { text: KEYS[k][1] } : {}) });
  await send("Input.dispatchKeyEvent", { type: "keyUp", key: k, code: k, windowsVirtualKeyCode: KEYS[k][0] });
};
await send("Runtime.enable");
await send("Page.enable");
await send("Emulation.setDeviceMetricsOverride", { width: 1300, height: 900, deviceScaleFactor: 1, mobile: false });
// CDP-injected scripts aren't subject to the page's CSP, so this can watch for violations
await send("Page.addScriptToEvaluateOnNewDocument", { source: `window.__csp = []; document.addEventListener("securitypolicyviolation", (e) => window.__csp.push(e.violatedDirective + " " + e.blockedURI + " " + (e.sample || "")));` });

await go(BASE + "#all", 2500);
check("page renders under its CSP", (await ev(`document.querySelectorAll(".section").length`)) > 40 && (await ev(`document.title`)).startsWith("Agamotto"));
// things that inject markup with style attributes, SVG and the dialog
await ev(`document.getElementById("mine-open").click()`); await sleep(300);
await ev(`document.getElementById("mine").close()`);
for (const tab of ["westeros", "dc"]) {
  await ev(`document.querySelector('.chip[data-id="${tab}"]').click()`); await sleep(400);
  await ev(`(() => { const b = document.querySelector('.egg-pin[data-egg="${tab}"]'); b.scrollIntoView({ block: "center" }); b.click(); })()`); await sleep(800);
}
const csp = await ev(`window.__csp`);
check("CSP blocks nothing the page does", Array.isArray(csp) && !csp.length, JSON.stringify(csp));
await go(BASE + "nope/missing", 1200);
check("unknown paths get the 404 page", (await ev(`document.title`)) === "Not found · Agamotto");

// keyboard and screen readers
await go(BASE + "#all", 2000);
await key("Tab");
check("first Tab reaches the skip link", (await ev(`document.activeElement.id`)) === "skip");
await key("Enter"); await sleep(200);
check("skip link moves focus to the list", (await ev(`document.activeElement.id`)) === "main" && (await ev(`location.hash`)) === "#all");
await ev(`document.querySelector('.chip[data-id="xmen"]').focus()`);
await key("Enter"); await sleep(400);
check("a chip keeps focus after it re-renders the page", (await ev(`document.activeElement.dataset.id`)) === "xmen" && (await ev(`document.activeElement.getAttribute("aria-pressed")`)) === "true");
await sleep(200);
check("switching franchise is announced", /^Showing \d+ entr/.test(await ev(`document.getElementById("sr").textContent`)), await ev(`document.getElementById("sr").textContent`));
await ev(`document.querySelector('#toc a[data-sec="mcu-xmen"], #toc a').focus()`);
const sec = await ev(`document.activeElement.dataset.sec`);
await key("Enter"); await sleep(1800);
check("a section link moves focus to that section's heading", (await ev(`document.activeElement.id`)) === "h-" + sec, sec);
await ev(`(() => { const q = document.getElementById("q"); q.value = "zzzz"; q.dispatchEvent(new Event("input")); })()`); await sleep(500);
check("an empty search result is announced", (await ev(`document.getElementById("sr").textContent`)) === "Nothing matches these filters.");
await ev(`(() => { const q = document.getElementById("q"); q.value = ""; q.dispatchEvent(new Event("input")); })()`); await sleep(400);
await ev(`document.getElementById("lang-zh").click()`); await sleep(300);
check("the title and labels follow the language", (await ev(`document.title`)).includes("观影顺序") && (await ev(`document.getElementById("type").getAttribute("aria-label")`)) === "类型");
await ev(`document.getElementById("lang-en").click()`); await sleep(300);
await ev(`document.querySelector('.chip[data-id="alien"]').click()`); await sleep(400);
await ev(`(() => { const b = document.querySelector('.egg-pin[data-egg="alien"]'); b.scrollIntoView({ block: "center" }); b.click(); })()`); await sleep(500);
check("the Alien terminal is hidden from screen readers and announced once", (await ev(`document.querySelector(".egg-term").getAttribute("aria-hidden")`)) === "true");
await key("Escape"); await sleep(200);
check("Esc closes the terminal", !(await ev(`!!document.querySelector(".egg-term")`)));

// cards show vote counts and Certified Fresh; a poster opens the whole poster and gives focus back when closed
await go(BASE + "#xmen", 2000);
check("cards show vote counts and Certified Fresh", (await ev(`document.querySelectorAll(".sc.imdb .vn").length`)) > 10 && (await ev(`document.querySelectorAll(".sc.rt .cf").length`)) > 3);
await ev(`(() => { const b = document.querySelector(".thumb[data-zoom]"); b.focus(); b.click(); })()`); await sleep(900);
check("a poster opens the whole poster", await ev(`document.getElementById("zoom").open && document.querySelector("#zoom img").naturalWidth > 150`));
await key("Escape"); await sleep(300);
check("closing the poster returns focus to it", !(await ev(`document.getElementById("zoom").open`)) && (await ev(`!!document.activeElement.dataset.zoom`)));

// stored settings that a newer or older version, or a hand edit, could leave behind
await ev(`localStorage.setItem("wo:lang", "xx"); localStorage.setItem("wo:sort2", "zzz"); localStorage.setItem("wo:dir", "__proto__");
  localStorage.setItem("wo:mine", JSON.stringify({ imdb: true, douban: { user: ["x"], at: ["2020-01-01"], r: { "1": 9, "2": 3, "x": 4 } } }))`);
await go(BASE + "#all", 2000);
check("bad stored settings fall back", (await ev(`document.querySelectorAll(".section").length`)) > 40 && (await ev(`document.querySelector("#sort-story").getAttribute("aria-pressed")`)) === "true");
await ev(`document.getElementById("mine-open").click()`); await sleep(300);
check("bad stored ratings still open the dialog", await ev(`document.getElementById("mine").open && document.querySelector("#mine-body .state.on")?.textContent.includes("1 watched")`), await ev(`document.querySelector("#mine-body .state.on")?.textContent || ""`));
await ev(`document.getElementById("db-paste").value = JSON.stringify({ wo: 1, src: "douban", user: "a", at: ["2020-01-01"], r: { "3011091": 4 } })`);
await ev(`document.querySelector('[data-act="import-db"]').click()`); await sleep(300);
await ev(`document.getElementById("mine").close()`);
await ev(`document.getElementById("mine-open").click()`); await sleep(300);
check("a pasted date that isn't a string can't lock the dialog", await ev(`document.getElementById("mine").open && !!document.getElementById("db-msg")`));
await ev(`document.querySelector('[data-act="rm-db"]').focus(); document.querySelector('[data-act="rm-db"]').click()`); await sleep(300);
check("removing ratings hands focus to the import button", (await ev(`document.activeElement.dataset.act`)) === "import-db");
check("no page exceptions", !errors.length, errors.join(" | "));

server.close();
console.log(failed ? `\n${failed} failed` : "\nall site checks passed");
process.exit(failed ? 1 : 0);
