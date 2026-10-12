// Plays every easter egg the way a visitor would, checks it played, and screenshots it mid-effect. Exits 1 on any
// failure.
import { spawn } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
const CHROME = process.env.CHROME || "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const PROFILE = fs.mkdtempSync(path.join(os.tmpdir(), "agamotto-"));  // a fresh browser profile per run, removed on exit
const HERE = fileURLToPath(new URL(".", import.meta.url));
const SITE = new URL("../../site/index.html", import.meta.url).href;
const PORT = 9362;
const chrome = spawn(CHROME, ["--headless=new", "--disable-gpu", "--hide-scrollbars",
  `--remote-debugging-port=${PORT}`, `--user-data-dir=${PROFILE}`, "about:blank"], { stdio: "ignore" });
process.on("exit", () => { try { chrome.kill("SIGKILL"); } catch {} fs.rmSync(PROFILE, { recursive: true, force: true, maxRetries: 3 }); });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let ws;
for (let i = 0; i < 60 && !ws; i++) {
  try { const p = (await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json()).find((t) => t.type === "page");
    if (p) { ws = new WebSocket(p.webSocketDebuggerUrl); await new Promise((r, j) => { ws.onopen = r; ws.onerror = j; }); } } catch { ws = null; }
  if (!ws) await sleep(300);
}
let seq = 0; const pending = new Map(); const logs = [];
ws.onmessage = (e) => { const m = JSON.parse(e.data);
  if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); }
  else if (m.method === "Runtime.exceptionThrown") logs.push("EXC " + JSON.stringify(m.params.exceptionDetails).slice(0, 500)); };
const send = (method, params = {}) => new Promise((res) => { const id = ++seq; setTimeout(() => res({ timeout: true }), 30000); pending.set(id, res); ws.send(JSON.stringify({ id, method, params })); });
const ev = async (expression) => { const r = await send("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true }); return r.result?.exceptionDetails ? "EXC:" + JSON.stringify(r.result.exceptionDetails).slice(0, 300) : r.result?.result?.value; };
const shot = async (file) => { const r = await send("Page.captureScreenshot", { format: "png" }); fs.writeFileSync(HERE + file, Buffer.from(r.result.data, "base64")); };
await send("Page.enable"); await send("Runtime.enable");
await send("Emulation.setDeviceMetricsOverride", { width: 1300, height: 900, deviceScaleFactor: 1, mobile: false });
// tap a hidden icon the way a visitor would: scroll it into view, then click it
const tap = async (egg) => { await ev(`document.querySelector('.egg-pin[data-egg="${egg}"]').scrollIntoView({ block: "center" })`); await sleep(250); return ev(`document.querySelector('.egg-pin[data-egg="${egg}"]').click()`); };
const page = async (f) => { await send("Page.navigate", { url: "about:blank" }); await sleep(200); await send("Page.navigate", { url: SITE + "#" + f }); await sleep(1500); };
const state = () => ev(`JSON.stringify({ egg: document.getElementById("egg").innerHTML.length, toast: document.querySelector(".egg-toast")?.textContent || null, hint: document.getElementById("foot-egg").textContent })`);

const fails = [];
const check = (name, ok, detail = "") => { console.log(`${ok ? "ok  " : "FAIL"} ${name}${detail ? "  " + detail : ""}`); if (!ok) fails.push(name); };
const toastHas = (t) => `(document.querySelector(".egg-toast")?.textContent || "").includes(${JSON.stringify(t)})`;

// [page, trigger, wait before checking, expression that is true when the egg played]
const cases = [
  ["xmen", () => tap("xmen"), 900, `document.querySelectorAll(".egg-ring").length === 3 && ${toastHas("20")}`],
  ["dc", () => tap("dc"), 1600, `!!document.querySelector(".egg-signal svg path")`],
  ["starwars", () => tap("starwars"), 1200, `document.getElementById("main").classList.contains("saber")`],
  ["alien", () => tap("alien"), 4200, `(document.querySelector(".egg-term")?.textContent || "").includes("SPECIAL ORDER 937")`],
  ["godzilla", () => tap("godzilla"), 2300, toastHas("ゴジラ")],
  ["middleearth", () => tap("middleearth"), 2600, `!!document.querySelector(".egg-doors")`],
  ["wizarding", async () => { await tap("wizarding"); await send("Input.dispatchMouseEvent", { type: "mouseMoved", x: 700, y: 500 }); }, 800, `!!document.querySelector(".egg-dark")`],
  ["westeros", () => tap("westeros"), 3000, `document.querySelectorAll(".egg-snow i").length >= 50`],
  ["dune", async () => { for (let i = 0; i < 4; i++) { await ev(`document.querySelector(".sec-meta").click()`); await sleep(500); } }, 1500, `!!document.querySelector(".egg-worm")`],
  ["apes", async () => { await ev(`document.querySelector(".liberty").scrollIntoView({block:"center"})`); await sleep(300); await ev(`document.querySelector(".liberty").click()`); }, 600, toastHas("maniacs")],
  ["all", () => tap("agamotto"), 1300, `!!document.querySelector(".egg-mandala") && document.getElementById("dir").textContent.startsWith("↑")`],
];
for (const [f, trigger, wait, played] of cases) {
  await page(f);
  await trigger();
  await sleep(wait);
  check(`${f} egg plays`, (await ev(played)) === true, await state());
  await shot(`egg-${f}.png`);
}
// icons appear only on their own franchise (and All); the wand toggles Lumos off again; three taps on the hint line
// play the page's egg too
await page("dune");
check("no other franchise's icons on Dune", (await ev(`document.querySelectorAll(".egg-pin").length`)) === 0);
await page("all");
check("All carries every icon", (await ev(`document.querySelectorAll(".egg-pin").length`)) === 9);
await page("wizarding"); await tap("wizarding"); await sleep(300); await tap("wizarding"); await sleep(400);
check("second wand tap ends Lumos", (await ev(`!document.querySelector(".egg-dark")`)) === true);
await page("westeros"); await ev(`const h = document.getElementById("foot-egg"); h.click(); h.click(); h.click();`); await sleep(500);
check("hint triple-tap plays the egg", (await ev(toastHas("Winter is here"))) === true);
// Marvel: scroll to the end and wait through the credits
await page("marvel");
await ev(`scrollTo(0, document.body.scrollHeight)`); await sleep(3400);
check("marvel post-credits stinger", ((await ev(`document.querySelector(".egg-stinger")?.textContent || ""`)) || "").includes("Avengers"));
await shot("egg-marvel.png");
await ev(`document.getElementById("lang-zh").click()`); await sleep(300);
check("Chinese hint line", /[一-鿿]/.test(await ev(`document.getElementById("foot-egg").textContent`)));
check("no page exceptions", logs.length === 0, logs.join("\n"));
console.log(fails.length ? `\n${fails.length} failed` : "\nall egg checks passed");
process.exit(fails.length ? 1 : 0);
