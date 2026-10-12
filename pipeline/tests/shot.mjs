// node shot.mjs out.png width height url [scrollY] [js-before-shot] : real device-metrics emulation via CDP
import { spawn } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
const CHROME = process.env.CHROME || "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const PROFILE = fs.mkdtempSync(path.join(os.tmpdir(), "agamotto-"));  // a fresh browser profile per run, removed on exit
const [out, w, h, url, scrollY = "0", js = ""] = process.argv.slice(2);
const PORT = 9355;
const chrome = spawn(CHROME, ["--headless=new", "--disable-gpu", "--hide-scrollbars",
  `--remote-debugging-port=${PORT}`, `--user-data-dir=${PROFILE}`, "about:blank"], { stdio: "ignore" });
const quit = () => { try { chrome.kill("SIGKILL"); } catch {} fs.rmSync(PROFILE, { recursive: true, force: true, maxRetries: 3 }); };
process.on("exit", quit);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let ws;
for (let i = 0; i < 60 && !ws; i++) {
  try {
    const p = (await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json()).find((t) => t.type === "page");
    if (p) { ws = new WebSocket(p.webSocketDebuggerUrl); await new Promise((r, j) => { ws.onopen = r; ws.onerror = j; }); }
  } catch { ws = null; }
  if (!ws) await sleep(300);
}
let seq = 0; const pending = new Map();
ws.onmessage = (e) => { const m = JSON.parse(e.data); if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); } };
const send = (method, params = {}) => new Promise((res) => { const id = ++seq; const t = setTimeout(() => res({}), 20000); pending.set(id, (m) => { clearTimeout(t); res(m); }); ws.send(JSON.stringify({ id, method, params })); });
const mobile = +w < 700;
await send("Emulation.setDeviceMetricsOverride", { width: +w, height: +h, deviceScaleFactor: mobile ? 2 : 1, mobile: false });  // the emulated width is the layout width, as the page's viewport meta asks
await send("Page.enable");
await send("Page.navigate", { url });
await sleep(2500);
if (process.env.LIGHT) await send("Emulation.setEmulatedMedia", { features: [{ name: "prefers-color-scheme", value: "light" }] });
if (js) { await send("Runtime.evaluate", { expression: js }); await sleep(2500); }
await sleep(400);
if (+scrollY) { await send("Runtime.evaluate", { expression: `window.scrollTo(0, ${scrollY})` }); await sleep(600); }
const ov = await send("Runtime.evaluate", { expression: "document.documentElement.scrollWidth + 'x' + innerWidth", returnByValue: true });
const shot = await send("Page.captureScreenshot", { format: "png" });
fs.writeFileSync(out, Buffer.from(shot.result.data, "base64"));
console.log(out, "scrollWidth x innerWidth =", ov.result?.result?.value);
quit(); process.exit(0);
