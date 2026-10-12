// node brand.mjs : renders brand/ into site/ through headless Chrome: favicon.svg (a copy), favicon-16/32.png,
// favicon.ico (16, 32 and 48 px PNGs), apple-touch-icon.png (180, opaque) and og.png (1200x630), plus GitHub's social
// preview at ../.github/social-preview.png (1280x640, uploaded by hand in the repo's settings). The cards need network
// for their Google Fonts. Run it after editing anything in brand/; the outputs are committed.
import { spawn } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const HERE = fileURLToPath(new URL(".", import.meta.url));
const BRAND = path.join(HERE, "brand");
const SITE = path.join(HERE, "..", "site");
const CHROME = process.env.CHROME || "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const PROFILE = fs.mkdtempSync(path.join(os.tmpdir(), "agamotto-"));
const PORT = 9357;
const chrome = spawn(CHROME, ["--headless=new", "--disable-gpu", "--hide-scrollbars", `--remote-debugging-port=${PORT}`,
  `--user-data-dir=${PROFILE}`, "--allow-file-access-from-files", "about:blank"], { stdio: "ignore" });
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
if (!ws) { console.error("chrome did not start"); process.exit(1); }
let seq = 0;
const pending = new Map();
ws.onmessage = (e) => { const m = JSON.parse(e.data); if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); } };
const send = (method, params = {}) => new Promise((res) => { const id = ++seq; pending.set(id, res); ws.send(JSON.stringify({ id, method, params })); });
await send("Page.enable");

// one render: the page at url, w x h CSS px, transparent where the page paints nothing
async function render(url, w, h) {
  await send("Emulation.setDeviceMetricsOverride", { width: w, height: h, deviceScaleFactor: 1, mobile: false });
  await send("Emulation.setDefaultBackgroundColorOverride", { color: { r: 0, g: 0, b: 0, a: 0 } });
  await send("Page.navigate", { url });
  for (let i = 0; i < 100; i++) {
    const r = await send("Runtime.evaluate", { expression: "document.readyState === 'complete' && (!document.fonts || document.fonts.status === 'loaded')", returnByValue: true });
    if (r.result?.result?.value) break;
    await sleep(100);
  }
  await sleep(300);
  const shot = await send("Page.captureScreenshot", { format: "png", clip: { x: 0, y: 0, width: w, height: h, scale: 1 } });
  return Buffer.from(shot.result.data, "base64");
}
// an SVG document without width/height fills the viewport, so the viewport size is the icon size
const svgPage = (file) => pathToFileURL(path.join(BRAND, file)).href;

const png = {};
for (const px of [16, 32, 48]) png[px] = await render(svgPage("icon.svg"), px, px);
fs.copyFileSync(path.join(BRAND, "icon.svg"), path.join(SITE, "favicon.svg"));
fs.writeFileSync(path.join(SITE, "favicon-16.png"), png[16]);
fs.writeFileSync(path.join(SITE, "favicon-32.png"), png[32]);
fs.writeFileSync(path.join(SITE, "apple-touch-icon.png"), await render(svgPage("touch.svg"), 180, 180));
fs.writeFileSync(path.join(SITE, "og.png"), await render(pathToFileURL(path.join(BRAND, "og.html")).href, 1200, 630));
fs.mkdirSync(path.join(HERE, "..", ".github"), { recursive: true });
fs.writeFileSync(path.join(HERE, "..", ".github", "social-preview.png"), await render(pathToFileURL(path.join(BRAND, "og.html")).href, 1280, 640));

// favicon.ico: a directory of PNG images (supported by every current browser)
const sizes = [16, 32, 48];
const head = Buffer.alloc(6 + 16 * sizes.length);
head.writeUInt16LE(0, 0); head.writeUInt16LE(1, 2); head.writeUInt16LE(sizes.length, 4);
let offset = head.length;
sizes.forEach((px, i) => {
  const e = 6 + 16 * i;
  head.writeUInt8(px, e); head.writeUInt8(px, e + 1); head.writeUInt8(0, e + 2); head.writeUInt8(0, e + 3);
  head.writeUInt16LE(1, e + 4); head.writeUInt16LE(32, e + 6);
  head.writeUInt32LE(png[px].length, e + 8); head.writeUInt32LE(offset, e + 12);
  offset += png[px].length;
});
fs.writeFileSync(path.join(SITE, "favicon.ico"), Buffer.concat([head, ...sizes.map((px) => png[px])]));
console.log("wrote favicon.svg, favicon-16/32.png, favicon.ico, apple-touch-icon.png and og.png to site/, and .github/social-preview.png");
process.exit(0);
