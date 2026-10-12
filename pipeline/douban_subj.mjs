// Douban title pages (movie.douban.com/subject/ID) for films whose Douban id Wikidata gives. Separate host
// from the throttled search; each page lists Douban's IMDb id, so a match with ours verifies the title.
import { spawn } from "node:child_process";
import fs from "node:fs";
import { fileURLToPath } from "node:url";

const HERE = fileURLToPath(new URL(".", import.meta.url));
const CHROME = process.env.CHROME || "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const OUT = HERE + "douban_subj.json";
const PORT = 9341, PACE_MS = 4000;
const jobs = Object.fromEntries(JSON.parse(fs.readFileSync(HERE + "douban_jobs.json", "utf8")).map((j) => [j.key, j]));
const imdb = Object.fromEntries(JSON.parse(fs.readFileSync(HERE + "data.json", "utf8")).titles.map((t) => [t.key, t.imdb]));
const keys = JSON.parse(fs.readFileSync(HERE + "douban_split.json", "utf8")).subject;
const out = fs.existsSync(OUT) ? JSON.parse(fs.readFileSync(OUT, "utf8")) : {};
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const chrome = spawn(CHROME, ["--headless=new", "--disable-gpu",
  `--remote-debugging-port=${PORT}`, `--user-data-dir=${HERE}chrome-profile2`, "--blink-settings=imagesEnabled=false", "about:blank"], { stdio: "ignore" });
process.on("exit", () => { try { chrome.kill("SIGKILL"); } catch {} });
let ws, seq = 0;
const pending = new Map(), listeners = new Set();
for (let i = 0; i < 60 && !ws; i++) {
  try {
    const p = (await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json()).find((t) => t.type === "page");
    if (p) { ws = new WebSocket(p.webSocketDebuggerUrl); await new Promise((r, j) => { ws.onopen = r; ws.onerror = j; }); }
  } catch { ws = null; }
  if (!ws) await sleep(500);
}
ws.onmessage = (e) => { const m = JSON.parse(e.data); if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); } else for (const l of listeners) l(m); };
const send = (method, params = {}) => new Promise((res) => {
  const id = ++seq; const t = setTimeout(() => { pending.delete(id); res({}); }, 30000);
  pending.set(id, (m) => { clearTimeout(t); res(m); }); ws.send(JSON.stringify({ id, method, params }));
});
listeners.add((m) => { if (m.method === "Page.javascriptDialogOpening") send("Page.handleJavaScriptDialog", { accept: true }); });
const evaluate = async (x) => (await send("Runtime.evaluate", { expression: x, returnByValue: true })).result?.result?.value;
await send("Page.enable");

const EXTRACT = `JSON.stringify((() => {
  const q = (s) => document.querySelector(s); const info = q('#info') ? q('#info').innerText : '';
  return { zh: document.title.replace(/\\s*\\(豆瓣\\)\\s*$/, '').trim(), r: (q('[property="v:average"]') || {}).textContent || null,
    n: (q('[property="v:votes"]') || {}).textContent || null, year: ((q('.year') || {}).textContent || '').replace(/[()]/g, ''),
    imdb: (info.match(/IMDb:\\s*(tt\\d+)/) || [])[1] || null, runtime: q('[property="v:runtime"]') ? q('[property="v:runtime"]').getAttribute('content') : null, hasInfo: !!info };
})())`;
let done = 0;
for (const key of keys) {
  if (out[key]) continue;
  const id = jobs[key].wd;
  let rec = null;
  for (let attempt = 0; attempt < 8 && !rec; attempt++) {
    const loaded = new Promise((res) => { const t = setTimeout(() => { listeners.delete(l); res(); }, 25000);
      const l = (m) => { if (m.method === "Page.loadEventFired") { clearTimeout(t); listeners.delete(l); res(); } }; listeners.add(l); });
    await send("Page.navigate", { url: `https://movie.douban.com/subject/${id}/` });
    await loaded;
    for (let i = 0; i < 15 && String(await evaluate("location.hostname")).startsWith("sec."); i++) await sleep(1000);
    // the title arrives before the rest of the page; give #info a moment before calling it a failed load
    let p = {};
    for (let i = 0; i < 12; i++) { p = JSON.parse((await evaluate(EXTRACT)) || "{}"); if (p.hasInfo) break; await sleep(1000); }
    // a real, fully loaded title page (rated or not); a page without its #info block loaded only partway
    if (p.hasInfo && p.zh && !/错误|异常|禁止|Error|登录|douban\.com$/.test(p.zh) && p.zh !== "豆瓣电影") {
      rec = { id, zh: p.zh, r: p.r ? +p.r : null, n: p.n ? +p.n : 0, year: p.year ? +p.year : null, imdb: p.imdb,
              runtime: p.runtime ? +p.runtime : null, verified: !!p.imdb && p.imdb === imdb[key] };
    } else {
      console.log(`  ${key}: no data (${p.zh}) at ${new Date().toTimeString().slice(0, 8)}; waiting 5 min`);
      await sleep(300000);
    }
    await sleep(PACE_MS);
  }
  out[key] = rec || { id, failed: true };
  fs.writeFileSync(OUT, JSON.stringify(out, null, 1));
  console.log(`${++done} ${key}: ${rec ? `${rec.zh} ${rec.r} (${rec.n}) imdb ${rec.imdb} ${rec.verified ? "verified" : "MISMATCH vs " + imdb[key]}` : "FAILED"}`);
}
console.log("SUBJ DONE");
process.exit(0);
