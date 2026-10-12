// Checks hash routing, the Douban bookmarklet and both rating imports in headless Chrome over CDP; exits 1 on any
// failure. OFFLINE=1 only parses the bookmarklet; otherwise it runs it on a public Douban profile (needs network).
// Screenshots land next to this file.
import { spawn } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
const CHROME = process.env.CHROME || "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const PROFILE = fs.mkdtempSync(path.join(os.tmpdir(), "agamotto-"));  // a fresh browser profile per run, removed on exit
const HERE = fileURLToPath(new URL(".", import.meta.url));
const SITE = new URL("../../site/index.html", import.meta.url).href;
const PORT = 9361;
const chrome = spawn(CHROME, ["--headless=new", "--disable-gpu", "--hide-scrollbars",
  `--remote-debugging-port=${PORT}`, `--user-data-dir=${PROFILE}`, "about:blank"], { stdio: "ignore" });
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
let seq = 0; const pending = new Map(); const logs = [];
ws.onmessage = (e) => { const m = JSON.parse(e.data);
  if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); }
  else if (m.method === "Runtime.exceptionThrown") logs.push("EXC " + JSON.stringify(m.params.exceptionDetails).slice(0, 400));
  else if (m.method === "Runtime.consoleAPICalled" && m.params.type === "error") logs.push("ERR " + JSON.stringify(m.params.args).slice(0, 300));
  else if (m.method === "Page.javascriptDialogOpening") { logs.push("DIALOG " + m.params.message); send("Page.handleJavaScriptDialog", { accept: true }); } };
const send = (method, params = {}) => new Promise((res) => { const id = ++seq; setTimeout(() => res({ timeout: true }), 60000); pending.set(id, res); ws.send(JSON.stringify({ id, method, params })); });
const ev = async (expression) => { const r = await send("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true }); return r.result?.exceptionDetails ? "EXC:" + JSON.stringify(r.result.exceptionDetails).slice(0, 300) : r.result?.result?.value; };
const go = async (url, wait = 1800) => { await send("Page.navigate", { url }); await sleep(wait); };
const shot = async (file, w = 1300, h = 900) => {
  await send("Emulation.setDeviceMetricsOverride", { width: w, height: h, deviceScaleFactor: 1, mobile: false });
  await sleep(500);
  const r = await send("Page.captureScreenshot", { format: "png" });
  fs.writeFileSync(HERE + file, Buffer.from(r.result.data, "base64"));
};
await send("Page.enable"); await send("Runtime.enable"); await send("DOM.enable");
await send("Emulation.setDeviceMetricsOverride", { width: 1300, height: 900, deviceScaleFactor: 1, mobile: false });
const view = `JSON.stringify({ hash: location.hash, tab: (document.querySelector('.chip[aria-pressed="true"]')||{}).dataset?.id, y: Math.round(scrollY), sections: document.querySelectorAll('.section').length })`;
const secTop = (c) => `Math.round(document.getElementById('sec-${c}')?.getBoundingClientRect().top) + ' bar=' + getComputedStyle(document.documentElement).getPropertyValue('--bar-h')`;

const OFFLINE = !!process.env.OFFLINE;
const fails = [];
const check = (name, ok, detail = "") => { console.log(`${ok ? "ok  " : "FAIL"} ${name}${detail ? "  " + detail : ""}`); if (!ok) fails.push(name); };
const V = async () => JSON.parse(await ev(view));
// the section's top should sit just under the sticky bar (scroll-margin-top is bar height + 20px)
const atTop = async (c) => { const top = await ev(`Math.round(document.getElementById('sec-${c}').getBoundingClientRect().top)`);
  const bar = await ev(`parseInt(getComputedStyle(document.documentElement).getPropertyValue('--bar-h'))`); return top >= bar && top <= bar + 40; };

// A: links and history
await go(SITE, 1800);
let v = await V(); check("plain load opens All and writes #all", v.hash === "#all" && v.tab === "all" && v.sections > 40, JSON.stringify(v));
await go("about:blank", 300); await go(SITE + "#xmen/fox-xmen", 2500);
v = await V(); check("#xmen/fox-xmen opens X-Men at that section", v.tab === "xmen" && await atTop("fox-xmen"), JSON.stringify(v));
await go("about:blank", 300); await go(SITE + "#sw-legends", 2500);
v = await V(); check("bare #sw-legends opens Star Wars", v.tab === "starwars" && v.y > 1000, JSON.stringify(v));
await go("about:blank", 300); await go(SITE + "#alien", 2000);
v = await V(); check("#alien prefers the franchise over the same-named section", v.tab === "alien" && v.y === 0, JSON.stringify(v));
await ev(`document.querySelector('.chip[data-id="dune"]').click()`); await sleep(400);
v = await V(); check("chip click pushes #dune", v.hash === "#dune" && v.tab === "dune");
await ev("history.back()"); await sleep(800);
v = await V(); check("Back returns to Alien", v.hash === "#alien" && v.tab === "alien");
await ev(`location.hash = "#all/westeros"`); await sleep(1200);
v = await V(); check("edited hash #all/westeros scrolls in All", v.tab === "all" && await atTop("westeros"), JSON.stringify(v));
await go("about:blank", 300); await go(SITE + "#constructor", 2000);
v = await V(); check("junk hash falls back safely", v.tab === "all" && v.hash === "#all", JSON.stringify(v));
await go("about:blank", 300); await go(SITE + "#godzilla", 1500);
await ev(`document.querySelector('#toc a[data-sec="gz-showa"]').click()`); await sleep(1500);
v = await V(); check("section index click scrolls and replaces the hash", v.hash === "#godzilla/gz-showa" && await atTop("gz-showa"), JSON.stringify(v));

// B: the Douban bookmarklet. Offline it is only parsed; live it runs on a public profile (阿北, 200+ titles).
await ev(`document.getElementById('mine-open').click()`); await sleep(300);
const bm = await ev(`document.querySelector('.bm').href`);
const bmSrc = decodeURIComponent(bm.slice("javascript:".length));
let parses = true; try { new Function(bmSrc); } catch { parses = false; }
check("bookmarklet is a valid javascript: URL", bm.startsWith("javascript:") && parses, `${bm.length} chars`);
let data = JSON.stringify({ wo: 1, src: "douban", user: "test", at: "2026-10-11", r: { "3016187": 5, "26235354": 2, "1293792": 0 } });
if (!OFFLINE) {
  await go("https://movie.douban.com/people/ahbei/collect", 6000);
  await send("Runtime.evaluate", { expression: bmSrc });
  let live = null;
  for (let i = 0; i < 120 && !live; i++) { await sleep(1000); live = await ev(`(document.querySelector('#wo-export textarea')||{}).value || null`); }
  const parsed = live && JSON.parse(live);
  check("bookmarklet reads a public Douban list", !!parsed && parsed.user === "ahbei" && Object.keys(parsed.r).length >= 100, parsed ? `${Object.keys(parsed.r).length} titles` : "no data");
  await shot("test-douban-overlay.png");
  if (parsed) data = live;
}

// C: both imports
await go(SITE + "#all", 2000);
await ev(`document.getElementById('mine-open').click()`); await sleep(300);
await ev(`document.getElementById('db-paste').value = "not json"; document.querySelector('[data-act="import-db"]').click()`); await sleep(200);
check("bad Douban paste is rejected", (await ev(`document.getElementById('db-msg').className`)).includes("err"));
await ev(`document.getElementById('db-paste').value = ${JSON.stringify(data)}; document.querySelector('[data-act="import-db"]').click()`); await sleep(400);
check("Douban import", (await ev(`document.getElementById('db-msg').className`)).includes("ok"), await ev(`document.querySelector('#db-h .state').textContent`));
const doc = await send("DOM.getDocument", { depth: -1 });
const node = await send("DOM.querySelector", { nodeId: doc.result.root.nodeId, selector: "#imdb-file" });
await send("DOM.setFileInputFiles", { nodeId: node.result.nodeId, files: [HERE + "imdb-sample.csv"] }); await sleep(800);
check("IMDb CSV import (quoted fields included)", (await ev(`document.getElementById('imdb-msg').textContent`)) === "Imported 7 titles.", await ev(`document.querySelector('#imdb-h .state').textContent`));
await shot("test-dialog.png", 1300, 1000);
await ev(`document.getElementById('mine').close()`);
check("personal scores appear on cards", (await ev(`document.querySelectorAll('.sc .me').length`)) >= 6);
await go(SITE + "#dune", 1500);
check("IMDb score shown on Dune (2021)", (await ev(`[...document.querySelectorAll('.sc.imdb')].some(a => a.title.includes('Your rating 9/10'))`)) === true);
check("section shows a seen count", /Seen \d+\/\d+/.test(await ev(`document.querySelector('.seen-n')?.textContent || ''`)));
await shot("test-dune.png");
if (OFFLINE) {
  await go(SITE + "#westeros", 1500);
  await ev(`document.querySelectorAll('details.seasons').forEach(d => d.open = true)`); await sleep(200);
  check("season table gets a Mine column with stars", (await ev(`[...document.querySelectorAll('.st th')].some(th => th.textContent === 'Mine') && document.querySelectorAll('.st .stars').length >= 2`)) === true);
  await go(SITE + "#alien", 1500);
  check("watched but unrated shows a check", (await ev(`!!document.querySelector('.sc .me.seen')`)) === true);
  await shot("test-westeros.png");
}
check("no page exceptions", logs.filter((l) => !l.startsWith("DIALOG")).length === 0, logs.join("\n"));
console.log(fails.length ? `\n${fails.length} failed` : "\nall link and rating checks passed");
process.exit(fails.length ? 1 : 0);
