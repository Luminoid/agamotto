// Remaining Douban titles (series, and films without a Douban id) via the mobile search page
// (m.douban.com/search, its own quota) plus title pages (movie.douban.com/subject). A candidate is
// accepted only when its title page lists our IMDb id; seasons are the search rows sharing its name.
import { spawn } from "node:child_process";
import fs from "node:fs";
import { fileURLToPath } from "node:url";

const HERE = fileURLToPath(new URL(".", import.meta.url));
const CHROME = process.env.CHROME || "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const OUT = HERE + "douban_m.json";
const PORT = 9343, PACE_MS = 5000;
const jobs = Object.fromEntries(JSON.parse(fs.readFileSync(HERE + "douban_jobs.json", "utf8")).map((j) => [j.key, j]));
const imdb = Object.fromEntries(JSON.parse(fs.readFileSync(HERE + "data.json", "utf8")).titles.map((t) => [t.key, t.imdb]));
// retry mode: node douban_m.mjs "key=query one|query two" ... (re-runs those keys with the given queries)
const retry = Object.fromEntries(process.argv.slice(2).map((a) => { const [k, q] = a.split("="); return [k, q ? q.split("|") : null]; }));
const keys = Object.keys(retry).length ? Object.keys(retry) : JSON.parse(fs.readFileSync(HERE + "douban_split.json", "utf8")).search;
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
async function open(url) {
  const loaded = new Promise((res) => { const t = setTimeout(() => { listeners.delete(l); res(); }, 25000);
    const l = (m) => { if (m.method === "Page.loadEventFired") { clearTimeout(t); listeners.delete(l); res(); } }; listeners.add(l); });
  await send("Page.navigate", { url });
  await loaded;
  for (let i = 0; i < 15 && String(await evaluate("location.hostname")).startsWith("sec."); i++) await sleep(1000);
  await sleep(PACE_MS);
}

const D = "一二三四五六七八九";
const cn = (s) => /^\d+$/.test(s) ? +s : s === "十" ? 10 : s[0] === "十" ? 10 + D.indexOf(s[1]) + 1
  : s.endsWith("十") ? (D.indexOf(s[0]) + 1) * 10 : s.includes("十") ? (D.indexOf(s.split("十")[0]) + 1) * 10 + D.indexOf(s.split("十")[1]) + 1 : D.indexOf(s) + 1;
const seasonOf = (zh) => { const m = (zh || "").match(/第([一二三四五六七八九十\d]+)季/); return m ? cn(m[1]) : null; };
const baseOf = (zh) => (zh || "").replace(/\s*第[一二三四五六七八九十\d]+季\s*$/, "").replace(/\s+/g, " ").trim();

async function search(q) {
  for (let attempt = 0; attempt < 8; attempt++) {
    await open(`https://m.douban.com/search/?query=${encodeURIComponent(q)}&type=1002`);
    const title = String(await evaluate("document.title"));
    if (title.startsWith("豆瓣")) {
      const rows = JSON.parse(await evaluate(`JSON.stringify([...document.querySelectorAll('a[href*="/movie/subject/"]')].map((a) => {
        const id = (a.getAttribute('href').match(/subject\\/(\\d+)/) || [])[1];
        const t = a.innerText.replace(/\\s+/g, ' ').trim();
        const m = t.match(/^(.*?)\\s+(\\d+(?:\\.\\d)?)$/);
        return { id, zh: (m ? m[1] : t).trim(), r: m ? +m[2] : null };
      }).filter((x) => x.id))`) || "[]");
      return rows;
    }
    console.log(`  search throttled (${title}) ${new Date().toTimeString().slice(0, 8)}; waiting 5 min`);
    await sleep(300000);
  }
  return [];
}
async function subject(id) {
  for (let attempt = 0; attempt < 6; attempt++) {
    await open(`https://movie.douban.com/subject/${id}/`);
    const p = JSON.parse((await evaluate(`JSON.stringify((() => { const q = (s) => document.querySelector(s); const info = q('#info') ? q('#info').innerText : '';
      return { zh: document.title.replace(/\\s*\\(豆瓣\\)\\s*$/, '').trim(), r: (q('[property="v:average"]') || {}).textContent || null,
        n: (q('[property="v:votes"]') || {}).textContent || null, year: ((q('.year') || {}).textContent || '').replace(/[()]/g, ''),
        imdb: (info.match(/IMDb:\\s*(tt\\d+)/) || [])[1] || null, eps: (info.match(/集数:\\s*(\\d+)/) || [])[1] || null, hasInfo: !!info }; })())`)) || "{}");
    if (p.hasInfo) return p;
    if (attempt === 0) { await sleep(6000); continue; }  // usually just still parsing
    console.log(`  subject ${id} not loaded (${p.zh}); waiting 3 min`);
    await sleep(180000);
  }
  return null;
}

let done = 0;
for (const key of keys) {
  if (out[key] && !(retry[key] !== undefined && !out[key].subjects.length)) continue;
  const j = jobs[key];
  const rec = { subjects: [], via: null, tried: [] };
  let verified = null, rows = [];
  for (const q of [...new Set(retry[key] || [j.en, j.zh].filter(Boolean))]) {
    rows = await search(q);
    const cands = rows.filter((x) => j.kind === "series" ? (seasonOf(x.zh) || 1) === 1 : !seasonOf(x.zh)).slice(0, retry[key] ? 5 : 3);
    if (j.wd && !cands.some((c) => c.id === j.wd)) cands.unshift({ id: j.wd, zh: null });
    for (const c of cands.slice(0, retry[key] ? 5 : 3)) {
      const p = await subject(c.id);
      rec.tried.push(`${c.id}:${p && p.zh}:${p && p.imdb}`);
      if (p && p.imdb === imdb[key]) { verified = { id: c.id, ...p }; break; }
    }
    if (verified) break;
  }
  if (verified) {
    rec.via = "subject-page+imdb";
    const s1 = { id: verified.id, title: verified.zh, r: verified.r ? +verified.r : null, n: verified.n ? +verified.n : 0,
                 year: verified.year ? +verified.year : null, eps: verified.eps ? +verified.eps : null, season: j.kind === "series" ? (seasonOf(verified.zh) || 1) : null };
    rec.subjects.push(s1);
    if (j.kind === "series") {
      const base = baseOf(verified.zh);
      // a verified "第一季" means every other season carries a marker too; unmarked rows are same-named films
      const sameShow = (x) => baseOf(x.zh) === base && x.id !== verified.id && (!seasonOf(verified.zh) || seasonOf(x.zh));
      let more = rows.filter(sameShow);
      if (!more.length && base !== j.zh && base !== j.en) more = (await search(base)).filter(sameShow);
      for (const x of more) rec.subjects.push({ id: x.id, title: x.zh, r: x.r, n: 0, year: null, season: seasonOf(x.zh) || 1 });
      rec.subjects.sort((a, b) => a.season - b.season);
    }
  }
  out[key] = rec;
  fs.writeFileSync(OUT, JSON.stringify(out, null, 1));
  console.log(`${++done} ${key}: ${rec.via || "NONE"} ${rec.subjects.map((s) => `${s.title} ${s.r ?? "-"}`).join(" | ")}${verified ? "" : "  tried " + rec.tried.join(", ")}`);
}
console.log("M DONE");
process.exit(0);
