// Render story.html to an MP4 (1920x1080, 30 fps, H.264): node docs/render-story.mjs [out.mp4]
//
// Each frame is drawn by the film's own renderAt in headless Chromium and
// exported as a JPEG. K pages (default 3) render consecutive slices in
// parallel, each piped into its own ffmpeg; the slices are then concatenated
// without re-encoding. Needs ffmpeg and Playwright: set PLAYWRIGHT to the
// module's path if it is not installed here, and CHROME to a browser binary
// if Playwright's own is missing. The fonts load from Google Fonts.
import { createRequire } from 'module';
import { spawn } from 'child_process';
import { mkdtempSync, rmSync, writeFileSync } from 'fs';
import { tmpdir } from 'os';
import { dirname, join, resolve } from 'path';
import { fileURLToPath, pathToFileURL } from 'url';

const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PLAYWRIGHT || 'playwright');
const FPS = 30, K = Number(process.env.K || 3);
const OUT = resolve(process.argv[2] || 'sylver-coinage-story.mp4');
const PAGE = pathToFileURL(join(dirname(fileURLToPath(import.meta.url)), 'story.html')).href + '#render';
const work = mkdtempSync(join(tmpdir(), 'story-'));
const t0 = Date.now();

function run(args, stdin) {
  const ff = spawn('ffmpeg', ['-loglevel', 'error', '-y', ...args], { stdio: [stdin ? 'pipe' : 'ignore', 'inherit', 'inherit'] });
  const done = new Promise((ok, fail) => ff.on('close', (code) => (code === 0 ? ok() : fail(new Error(`ffmpeg exited ${code}`)))));
  return { ff, done };
}

async function open(browser) {
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
  await page.goto(PAGE);
  await page.waitForFunction(() => window.filmReady === true, null, { timeout: 30000 });
  return page;
}

async function slice(browser, k, from, to) {
  const page = await open(browser);
  const { ff, done } = run(['-f', 'image2pipe', '-c:v', 'mjpeg', '-framerate', String(FPS), '-i', '-',
    '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p', join(work, `seg_${k}.mp4`)], true);
  for (let i = from; i < to; i++) {
    const jpeg = await page.evaluate((s) => {
      window.drawFrame(s);
      return document.getElementById('film').toDataURL('image/jpeg', 0.94).split(',')[1];
    }, i / FPS);
    if (!ff.stdin.write(Buffer.from(jpeg, 'base64'))) await new Promise((r) => ff.stdin.once('drain', r));
    if ((i - from) % 600 === 0) console.log(`slice ${k}: frame ${i - from}/${to - from} after ${((Date.now() - t0) / 1000).toFixed(0)} s`);
  }
  ff.stdin.end();
  await done;
  await page.close();
}

const browser = await chromium.launch({ executablePath: process.env.CHROME });
try {
  const probe = await open(browser);
  const frames = Math.round((await probe.evaluate(() => window.DURATION)) * FPS);
  await probe.close();
  const per = Math.ceil(frames / K);
  await Promise.all(Array.from({ length: K }, (_, k) => slice(browser, k, k * per, Math.min(frames, (k + 1) * per))));
  const list = join(work, 'slices.txt');
  writeFileSync(list, Array.from({ length: K }, (_, k) => `file '${join(work, `seg_${k}.mp4`)}'`).join('\n') + '\n');
  await run(['-f', 'concat', '-safe', '0', '-i', list, '-c', 'copy', '-movflags', '+faststart', OUT]).done;
  console.log(`${frames} frames in ${((Date.now() - t0) / 1000).toFixed(0)} s -> ${OUT}`);
} finally {
  await browser.close();
  rmSync(work, { recursive: true, force: true });
}
