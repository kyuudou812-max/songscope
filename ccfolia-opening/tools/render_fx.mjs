// lab/fx.html の演出を1つずつ書き出す。
// 使い方: node tools/render_fx.mjs [演出名 ...]   （省略時は全部）
// 出力: build/fx/<演出名>/f0000.png …
// ES モジュール（Three.js / GSAP）は file:// では読めないため、簡易サーバーを立てて開く。
import { createRequire } from "node:module";
import { createServer } from "node:http";
import { mkdirSync, readFileSync, rmSync, existsSync } from "node:fs";
import { dirname, extname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
let playwright;
try { playwright = require("playwright"); } catch { playwright = require("/opt/node22/lib/node_modules/playwright"); }

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const FPS = 24, SEC = 2.5;
const TYPES = { ".html": "text/html", ".js": "text/javascript", ".mjs": "text/javascript", ".png": "image/png",
                ".ttf": "font/ttf", ".json": "application/json" };

const server = createServer((req, res) => {
  const p = join(ROOT, decodeURIComponent(new URL(req.url, "http://x").pathname));
  if (!p.startsWith(ROOT) || !existsSync(p)) { res.writeHead(404); return res.end(); }
  res.writeHead(200, { "content-type": TYPES[extname(p)] ?? "application/octet-stream" });
  res.end(readFileSync(p));
}).listen(0);
const port = server.address().port;

const browser = await playwright.chromium.launch();
const page = await browser.newPage({ viewport: { width: 1280, height: 720 } });
page.on("pageerror", e => console.error("pageerror:", e.message));

await page.goto(`http://localhost:${port}/lab/fx.html?fx=ink`);
await page.waitForFunction(() => window.ready, null, { polling: 100 });
const names = process.argv.length > 2 ? process.argv.slice(2) : await page.evaluate(() => window.FX_NAMES);

for (const name of names) {
  const out = join(ROOT, "build", "fx", name);
  rmSync(out, { recursive: true, force: true }); mkdirSync(out, { recursive: true });
  await page.goto(`http://localhost:${port}/lab/fx.html?fx=${name}`);
  await page.waitForFunction(() => window.ready, null, { polling: 100, timeout: 60000 });
  for (let f = 0; f < FPS * SEC; f++) {
    await page.evaluate(([t, f]) => window.setTime(t, f), [f / FPS, f]);
    await page.screenshot({ path: join(out, `f${String(f).padStart(4, "0")}.png`) });
  }
  console.log("done", name);
}
await browser.close();
server.close();
