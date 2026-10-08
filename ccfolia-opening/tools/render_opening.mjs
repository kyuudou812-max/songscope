// opening/index.html を Chromium で開き、1コマずつ PNG に書き出す。
//
// 使い方:
//   node tools/render_opening.mjs --ep 1 --layer all            → build/frames_all_ep1/
//   node tools/render_opening.mjs --ep 1 --layer title --from 8 --to 15
// layer=all 以外は透明背景で書き出す（ココフォリア用の層）。
import { createRequire } from "node:module";
import { mkdirSync, readFileSync, rmSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const require = createRequire(import.meta.url);
let playwright;
try { playwright = require("playwright"); } catch { playwright = require("/opt/node22/lib/node_modules/playwright"); }

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const args = Object.fromEntries(process.argv.slice(2).reduce((acc, v, i, a) =>
  v.startsWith("--") ? [...acc, [v.slice(2), a[i + 1]]] : acc, []));
const ep = args.ep ?? "1";
const layer = args.layer ?? "all";
const fps = Number(args.fps ?? 24);
const from = Number(args.from ?? 0);
const timing = JSON.parse(readFileSync(join(ROOT, "opening", "timing.json"), "utf8"));
const to = Number(args.to ?? timing.duration);
const out = join(ROOT, "build", args.out ?? `frames_${layer}_ep${ep}`);

const episodes = JSON.parse(readFileSync(join(ROOT, "episodes.local.json"), "utf8"));
rmSync(out, { recursive: true, force: true });
mkdirSync(out, { recursive: true });

const browser = await playwright.chromium.launch({ args: ["--allow-file-access-from-files"] });
const page = await browser.newPage({ viewport: { width: 1280, height: 720 }, deviceScaleFactor: 1 });
await page.goto(pathToFileURL(join(ROOT, "opening", "index.html")).href + `?layer=${layer}`);
await page.evaluate(async ([e, tm]) => { await document.fonts.ready; window.setTiming(tm); window.setEpisode(e); }, [episodes[ep], timing]);
await page.waitForLoadState("networkidle");

const first = Math.round(from * fps), last = Math.round(to * fps);
for (let f = first; f < last; f++) {
  await page.evaluate(([t, f]) => window.setTime(t, f), [f / fps, f]);
  await page.screenshot({ path: join(out, `f${String(f - first).padStart(4, "0")}.png`),
                          omitBackground: layer !== "all" });
}
await browser.close();
console.log(`${last - first} frames → ${out}`);
