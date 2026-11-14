// Screenshot the running app for review and for the README.
//   node scripts/shoot.mjs <out-dir> [url]
// Captures desktop and phone views, light and dark, plus the main interactions.
import { chromium } from "playwright";

const out = process.argv[2] ?? "shots";
const url = process.argv[3] ?? "http://localhost:5173/";
const only = process.env.SHOTS?.split(",");

const browser = await chromium.launch({ args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader"] });

async function page(viewport, scheme, scale = 2) {
  const ctx = await browser.newContext({ viewport, deviceScaleFactor: scale, colorScheme: scheme });
  const p = await ctx.newPage();
  p.on("pageerror", (e) => console.error("pageerror:", e.message));
  await p.goto(url);
  await p.waitForFunction(() => window.__map?.loaded() && window.__map.getLayer("unit-badge"), null, { timeout: 30000 });
  await p.waitForFunction(() => window.__map.areTilesLoaded(), null, { timeout: 30000 }).catch(() => {});
  await p.waitForTimeout(800);
  return p;
}

// headless Chromium draws map frames only on demand; nudge it so transitions finish
async function settle(p, ms = 1500) {
  for (let t = 0; t < ms; t += 100) {
    // test-only: render a frame now instead of waiting for requestAnimationFrame
    await p.evaluate(() => void window.__map._render(performance.now()));
    await p.waitForTimeout(100);
  }
}

const shots = {
  async desktop() {
    const p = await page({ width: 1440, height: 900 }, "light");
    await p.screenshot({ path: `${out}/desktop.png` });
    // open the lead case through search
    await p.fill('input[role="combobox"]', "砵蘭街100");
    await p.waitForTimeout(600);
    await p.screenshot({ path: `${out}/search.png` });
    await p.keyboard.press("Enter");
    await settle(p, 1800);
    await p.screenshot({ path: `${out}/panel.png` });
    await p.click("text=Pin to compare");
    await p.fill('input[role="combobox"]', "11A Hau Fook");
    await p.waitForTimeout(500);
    await p.keyboard.press("Enter");
    await p.waitForTimeout(1600);
    await p.click("text=Pin to compare");
    await p.click("button.close");
    await p.click("text=Compare");
    await p.waitForTimeout(800);
    await p.screenshot({ path: `${out}/compare.png` });
  },
  async heat() {
    // software WebGL at 2x skips frames during paint transitions; 1x renders them
    const p = await page({ width: 1440, height: 900 }, "light", 1);
    await p.evaluate(() => void window.__map.jumpTo({ zoom: 15.2, center: [114.1715, 22.3035] }));
    await p.click("text=Shop lifespan");
    await settle(p);
    await p.mouse.move(700, 450);
    await settle(p, 600);
    await p.screenshot({ path: `${out}/heat.png` });
  },
  async site() {
    const p = await page({ width: 1440, height: 900 }, "light", 1);
    await p.click("text=Places");
    await p.click("text=Site check");
    await p.selectOption(".site-field select", "japanese");
    await p.evaluate(() => void window.__map.jumpTo({ zoom: 16.4, center: [114.1722, 22.2985] }));
    await settle(p, 800);
    const box = await p.locator("#map").boundingBox();
    await p.mouse.click(box.x + box.width * 0.58, box.y + box.height * 0.5);
    await settle(p, 1500);
    await p.screenshot({ path: `${out}/site.png` });
    await p.evaluate(() => document.querySelector(".sitecard").scrollTo(0, 9999));
    await p.waitForTimeout(300);
    await p.screenshot({ path: `${out}/site-prices.png` });
  },
  async filters() {
    const p = await page({ width: 1440, height: 900 }, "light");
    await p.click("text=Filters");
    await p.waitForTimeout(400);
    await p.screenshot({ path: `${out}/filters.png` });
    // a brand: every branch lights up and the map frames them
    await p.fill(".ftext", "McDonald");
    await settle(p, 2200);
    await p.screenshot({ path: `${out}/brand.png` });
  },
  async share() {
    // a shared link opens straight on its shop, and a site check link on its spot
    const p = await page({ width: 1440, height: 900 }, "light", 1);
    await p.click(".examples button");
    await settle(p, 1800);
    const shop = await p.evaluate(() => location.hash);
    await p.goto(url + "#site=114.17220,22.29850,200,japanese&mode=lifespan");
    await p.reload();
    await p.waitForFunction(() => window.__map?.loaded() && window.__map.getLayer("unit-badge"), null, { timeout: 30000 });
    await settle(p, 2500);
    await p.screenshot({ path: `${out}/share-site.png` });
    await p.click("text=Show all");
    await p.waitForTimeout(300);
    await p.screenshot({ path: `${out}/site-all.png` });
    console.log("hash after example:", shop, "| after site link:", await p.evaluate(() => location.hash));
  },
  async dark() {
    const p = await page({ width: 1440, height: 900 }, "dark");
    await p.screenshot({ path: `${out}/dark.png` });
  },
  async phone() {
    const p = await page({ width: 390, height: 844 }, "light");
    await p.screenshot({ path: `${out}/phone.png` });
    await p.fill('input[role="combobox"]', "100 Portland");
    await p.waitForTimeout(500);
    await p.keyboard.press("Enter");
    await p.waitForTimeout(1600);
    await p.screenshot({ path: `${out}/phone-panel.png` });
  },
};

for (const [name, fn] of Object.entries(shots)) {
  if (only && !only.includes(name)) continue;
  try {
    await fn();
    console.log("shot", name);
  } catch (e) {
    console.error("failed", name, e.message);
  }
}
await browser.close();
