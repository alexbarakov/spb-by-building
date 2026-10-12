/*
  A 15-second promo of the Petersburg map, 1920×1080 MP4, into out-video/.

    cd ../stop-token && node ../spb-by-building/scripts/promo-video.mjs [http://localhost:8643]

  Uses stop-token's Playwright and ffmpeg-static. Headless Chromium films the local dev server (which exposes
  window.__dbg) with a CDP screencast; a drawn cursor makes the clicks visible. Frames keep their own timestamps
  and go to ffmpeg as a variable-frame-rate list, so a slow frame stays on screen as long as it really did.
*/
import { createRequire } from "node:module";
import { execFileSync } from "node:child_process";
import { mkdirSync, writeFileSync, rmSync } from "node:fs";
import { resolve, join } from "node:path";

const require = createRequire(resolve("package.json"));
const { chromium } = require("playwright");
const ffmpeg = require("ffmpeg-static");

const base = process.argv[2] || "http://localhost:8643";
// size as WxH in the third argument: 1920x1080 by default, 1080x1350 for a LinkedIn feed post
const [W, H] = (process.argv[3] || "1920x1080").split("x").map(Number);
const suffix = W === 1920 && H === 1080 ? "" : `-${W}x${H}`;
const outDir = resolve("out-video");
const tmp = join(outDir, ".spb-promo");
rmSync(tmp, { recursive: true, force: true });
mkdirSync(tmp, { recursive: true });

const browser = await chromium.launch({ args: ["--use-angle=metal", "--enable-gpu", "--ignore-gpu-blocklist"] });
const ctx = await browser.newContext({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
const page = await ctx.newPage();

// a cursor the screencast can see
await page.addInitScript(() => {
  addEventListener("DOMContentLoaded", () => {
    const c = document.createElement("div");
    c.id = "fake-cursor";
    c.style.cssText = "position:fixed;left:0;top:0;width:26px;height:26px;margin:-13px 0 0 -13px;border-radius:50%;" +
      "background:rgba(236,0,0,.85);box-shadow:0 0 0 4px rgba(255,255,255,.9);z-index:99999;pointer-events:none;" +
      "transition:transform .12s;transform:translate(-100px,-100px)";
    document.body.appendChild(c);
    // the film shows clicks, not hovers: only a pinned card appears
    const st = document.createElement("style");
    st.textContent = "#card:not(.pinned){display:none!important}";
    document.head.appendChild(st);
    addEventListener("mousemove", e => { c.style.transform = `translate(${e.clientX}px,${e.clientY}px)`; }, true);
    addEventListener("mousedown", () => { c.style.boxShadow = "0 0 0 10px rgba(255,255,255,.6)"; }, true);
    addEventListener("mouseup", () => { c.style.boxShadow = "0 0 0 4px rgba(255,255,255,.9)"; }, true);
  });
});

const cdp = await ctx.newCDPSession(page);
const frames = [];
let k = 0, filming = true;
cdp.on("Page.screencastFrame", ({ data, metadata, sessionId }) => {
  if (!filming) return;
  const file = join(tmp, `${String(k++).padStart(5, "0")}.jpg`);
  writeFileSync(file, Buffer.from(data, "base64"));
  frames.push({ file, t: metadata.timestamp * 1000 });
  cdp.send("Page.screencastFrameAck", { sessionId }).catch(() => {});
});

await page.goto(`${base}/?film=3.5`);
await page.evaluate(() => document.fonts.ready);
// the cursor waits by the play button, off the buildings, so no hover card appears on its way
const playBox = await page.locator("#play").boundingBox();
await page.mouse.move(playBox.x + playBox.width / 2 + 60, playBox.y - 40);
// start filming as the first tiles drop in
await page.waitForFunction(() => +document.getElementById("progress").textContent >= 2, null, { timeout: 60000 });
await cdp.send("Page.startScreencast", { format: "jpeg", quality: 92, maxWidth: W, maxHeight: H, everyNthFrame: 1 });
const t0 = Date.now();
await page.waitForFunction(() => document.getElementById("loading").hidden, null, { timeout: 60000 });
await page.waitForTimeout(400);

const move = async (x, y, steps = 18) => { await page.mouse.move(x, y, { steps }); };
const click = async (sel) => {
  const el = page.locator(sel).first();
  await el.scrollIntoViewIfNeeded();
  const b = await el.boundingBox();
  await move(b.x + b.width / 2, b.y + b.height / 2);
  await page.waitForTimeout(150);
  await page.mouse.down(); await page.waitForTimeout(90); await page.mouse.up();
};

// 1. the film: seven centuries in three and a half seconds
await click("#play");
await page.waitForTimeout(3900);

// 2. a context layer rises
await click('.modes [data-mode="2"]');
await page.waitForTimeout(500);
await click('.layer[data-id="silver"]');
await page.waitForTimeout(1000);

// 3. a building's card
await page.evaluate(() => window.__dbg.flyTo(1896.0, -306.1, () => {})); // Дом Мурузи
await page.waitForTimeout(1450);
// a real click on the Muruzi House pins its card: find its pixel near the centre with the picking pass
const [cx, cy] = await page.evaluate(([w, h]) => {
  const d = window.__dbg, target = d.gidOf("-946930");
  for (let r = 0; r < 260; r += 6)
    for (let a = 0; a < 6.283; a += 0.35) {
      const x = Math.round(w / 2 + r * Math.cos(a)), y = Math.round(h / 2 + r * Math.sin(a));
      if (d.pick(x, y) === target) return [x, y];
    }
  return [w / 2, h / 2];
}, [W, H]);
await page.mouse.move(cx, cy, { steps: 14 });
await page.mouse.down(); await page.waitForTimeout(80); await page.mouse.up();
await page.waitForTimeout(2500); // long enough to see the photo and read the name

// 4. close the card, back to the list, a second context layer over the whole city
await page.keyboard.press("Escape");
await click(".back");
await page.waitForTimeout(350);
await page.evaluate(() => window.__dbg.flyTo(-600, -300, null, 9000));
await click('.layer[data-id="bombing"]');
await page.waitForTimeout(2100);

filming = false;
await cdp.send("Page.stopScreencast");
const end = Date.now();
await browser.close();

const startAt = frames.find(f => f.t >= t0)?.t ?? frames[0].t;
const kept = frames.filter(f => f.t >= startAt);
const list = [];
for (let j = 0; j < kept.length; j++) {
  const d = Math.max(0.001, ((j + 1 < kept.length ? kept[j + 1].t : end) - kept[j].t) / 1000);
  list.push(`file '${kept[j].file}'`, `duration ${d.toFixed(4)}`);
}
list.push(`file '${kept[kept.length - 1].file}'`);
writeFileSync(join(tmp, "list.txt"), list.join("\n") + "\n");
const out = join(outDir, `spb-promo${suffix}.mp4`);
execFileSync(ffmpeg, ["-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", join(tmp, "list.txt"),
  "-vf", "fps=30,format=yuv420p", "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-movflags", "+faststart", out]);
console.log(out, ((end - startAt) / 1000).toFixed(1), "s,", kept.length, "frames");
