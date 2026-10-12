// Opens every linked Douban title page that no earlier script has read (in practice the later seasons, which
// douban_m.mjs takes from search rows sharing the show's name) and records what the page says: Chinese title, IMDb id,
// rating, votes, year and episode count. enrich.py then keeps a season only when its page points at the same show on
// IMDb (the series id, or an episode of it), and takes its votes from here. Results go to douban_check.json and the
// run resumes from it; ALL=1 also rechecks pages the matching scripts already read.
import { spawn } from "node:child_process";
import fs from "node:fs";
import { fileURLToPath } from "node:url";

const HERE = fileURLToPath(new URL(".", import.meta.url));
const CHROME = process.env.CHROME || "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const OUT = HERE + "douban_check.json";
const PORT = 9345, PACE_MS = 4000;
const read = (f) => (fs.existsSync(HERE + f) ? JSON.parse(fs.readFileSync(HERE + f, "utf8")) : {});
const subj = read("douban_subj.json"), m = read("douban_m.json");
const out = read("douban_check.json");
// pages already read while matching: their IMDb id is on record
const known = new Set([
  ...Object.values(subj).filter((r) => r.id && !r.failed).map((r) => String(r.id)),
  ...Object.values(m).flatMap((r) => (r.tried || []).map((t) => t.split(":")[0])),
]);
const todo = [];
for (const [key, r] of Object.entries(m)) for (const s of r.subjects || []) todo.push({ key, season: s.season, id: String(s.id) });
for (const [key, r] of Object.entries(subj)) if (r.id && !r.failed) todo.push({ key, season: null, id: String(r.id) });
const jobs = todo.filter((j) => !out[j.id] && (process.env.ALL || !known.has(j.id)));
console.log(`${jobs.length} pages to read`);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const chrome = spawn(CHROME, ["--headless=new", "--disable-gpu", `--remote-debugging-port=${PORT}`, `--user-data-dir=${HERE}chrome-profile2`,
  "--blink-settings=imagesEnabled=false", "about:blank"], { stdio: "ignore" });
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
if (!ws) { console.error("chrome did not start"); process.exit(1); }
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
    imdb: (info.match(/IMDb:\\s*(tt\\d+)/) || [])[1] || null, eps: (info.match(/集数:\\s*(\\d+)/) || [])[1] || null, hasInfo: !!info };
})())`;
let done = 0;
for (const j of jobs) {
  let rec = null;
  for (let attempt = 0; attempt < 6 && !rec; attempt++) {
    const loaded = new Promise((res) => { const t = setTimeout(() => { listeners.delete(l); res(); }, 25000);
      const l = (m) => { if (m.method === "Page.loadEventFired") { clearTimeout(t); listeners.delete(l); res(); } }; listeners.add(l); });
    await send("Page.navigate", { url: `https://movie.douban.com/subject/${j.id}/` });
    await loaded;
    for (let i = 0; i < 15 && String(await evaluate("location.hostname")).startsWith("sec."); i++) await sleep(1000);
    let p = {};
    for (let i = 0; i < 12; i++) { p = JSON.parse((await evaluate(EXTRACT)) || "{}"); if (p.hasInfo) break; await sleep(1000); }
    if (p.hasInfo && p.zh && !/错误|异常|禁止|Error|登录|douban\.com$/.test(p.zh) && p.zh !== "豆瓣电影") {
      rec = { key: j.key, season: j.season, zh: p.zh, imdb: p.imdb, r: p.r ? +p.r : null, n: p.n ? +p.n : 0,
              year: p.year ? +p.year : null, eps: p.eps ? +p.eps : null };
    } else {
      console.log(`  ${j.id}: no data (${p.zh}) at ${new Date().toTimeString().slice(0, 8)}; waiting 5 min`);
      await sleep(300000);
    }
    await sleep(PACE_MS);
  }
  out[j.id] = rec || { key: j.key, season: j.season, failed: true };
  fs.writeFileSync(OUT, JSON.stringify(out, null, 1));
  console.log(`${++done}/${jobs.length} ${j.key} S${j.season ?? "-"} ${j.id}: ${rec ? `${rec.zh} imdb ${rec.imdb} ${rec.r ?? "-"} (${rec.n})` : "FAILED"}`);
}
console.log("CHECK DONE");
process.exit(0);
