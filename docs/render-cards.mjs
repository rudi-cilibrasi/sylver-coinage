// Render the social-preview cards in docs/media (1200x630 JPEGs): node docs/render-cards.mjs
//
// story-og.jpg is the film's title frame (story.html at 6.5 s, the frame the
// page opens on), scaled to 1200 wide and cropped to 630 high; mint-og.jpg is a
// screenshot of media/mint-card.html. Needs ffmpeg and Playwright, with
// PLAYWRIGHT and CHROME set as for render-story.mjs. The fonts load from
// Google Fonts; without them (offline, say) it stops rather than draw a card
// in fallback fonts.
import { createRequire } from 'module';
import { execFileSync } from 'child_process';
import { mkdtempSync, rmSync, writeFileSync } from 'fs';
import { tmpdir } from 'os';
import { dirname, join } from 'path';
import { fileURLToPath, pathToFileURL } from 'url';

const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PLAYWRIGHT || 'playwright');
const DOCS = dirname(fileURLToPath(import.meta.url));
const work = mkdtempSync(join(tmpdir(), 'cards-'));
const jpeg = (input, name, ...filters) => execFileSync('ffmpeg', ['-loglevel', 'error', '-y', '-i', input, ...filters,
  '-frames:v', '1', '-q:v', '2', join(DOCS, 'media', name)], { stdio: 'inherit' });

const FAMILIES = ['Cinzel', 'Spectral', 'IBM Plex Mono'];   // the film's and the card's typefaces
async function requireFonts(page) {
  const missing = await page.evaluate((names) => names.filter((name) =>
    ![...document.fonts].some((f) => f.family.replace(/"/g, '') === name && f.status === 'loaded')), FAMILIES);
  if (missing.length) throw new Error(`fonts not loaded on ${page.url()}: ${missing.join(', ')}`);
}

let browser = null;
try {
  browser = await chromium.launch({ executablePath: process.env.CHROME });
  const film = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
  await film.goto(pathToFileURL(join(DOCS, 'story.html')).href + '#render');
  await film.waitForFunction(() => window.filmReady === true, null, { timeout: 30000 });
  await requireFonts(film);
  const png = await film.evaluate(() => {
    window.drawFrame(6.5);
    return document.getElementById('film').toDataURL('image/png').split(',')[1];
  });
  writeFileSync(join(work, 'story.png'), Buffer.from(png, 'base64'));
  const card = await browser.newPage({ viewport: { width: 1200, height: 630 } });
  await card.goto(pathToFileURL(join(DOCS, 'media', 'mint-card.html')).href, { waitUntil: 'networkidle' });
  await card.evaluate(async () => { await document.fonts.ready; });
  await requireFonts(card);
  await card.screenshot({ path: join(work, 'mint.png') });
  jpeg(join(work, 'story.png'), 'story-og.jpg', '-vf', 'scale=1200:-1,crop=1200:630');
  jpeg(join(work, 'mint.png'), 'mint-og.jpg');
  console.log('wrote docs/media/story-og.jpg and docs/media/mint-og.jpg');
} finally {
  if (browser) await browser.close().catch(() => {});
  rmSync(work, { recursive: true, force: true });
}
