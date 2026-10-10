// Render story.html to an MP4 (1920x1080, 30 fps, H.264): node docs/render-story.mjs [out.mp4]
//
// Each frame is drawn by the film's own renderAt in headless Chromium and
// exported as a JPEG. K pages (default 3) render consecutive slices in
// parallel, each piped into its own ffmpeg; the slices are then concatenated
// without re-encoding. Needs ffmpeg and Playwright: set PLAYWRIGHT to the
// module's path if it is not installed here, and CHROME to a browser binary
// if Playwright's own is missing. The fonts load from Google Fonts. On any
// failure the other encoders are stopped and the temporary files removed.
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
const encoders = new Set();
const t0 = Date.now();

// Start ffmpeg; `done` settles when it exits, and `failed` holds the error once it does so badly.
function ffmpeg(args, input) {
  const ff = spawn('ffmpeg', ['-loglevel', 'error', '-y', ...args], { stdio: [input ? 'pipe' : 'ignore', 'inherit', 'inherit'] });
  encoders.add(ff);
  const job = { ff, failed: null };
  job.done = new Promise((ok, fail) => {
    ff.on('error', fail);
    ff.on('close', (code, signal) => { encoders.delete(ff); code === 0 ? ok() : fail(new Error(`ffmpeg exited with ${code ?? signal}`)); });
  });
  job.done.catch((err) => { job.failed = err; });
  if (input) ff.stdin.on('error', () => {});   // a write after ffmpeg died; `done` reports why
  return job;
}

async function open(browser) {
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
  await page.goto(PAGE);
  await page.waitForFunction(() => window.filmReady === true, null, { timeout: 30000 });
  return page;
}

async function slice(browser, k, from, to) {
  const page = await open(browser);
  const job = ffmpeg(['-f', 'image2pipe', '-c:v', 'mjpeg', '-framerate', String(FPS), '-i', '-',
    '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p', join(work, `seg_${k}.mp4`)], true);
  for (let i = from; i < to; i++) {
    if (job.failed) throw job.failed;
    const jpeg = await page.evaluate((s) => {
      window.drawFrame(s);
      return document.getElementById('film').toDataURL('image/jpeg', 0.94).split(',')[1];
    }, i / FPS);
    if (!job.ff.stdin.write(Buffer.from(jpeg, 'base64'))) await Promise.race([new Promise((r) => job.ff.stdin.once('drain', r)), job.done]);
    if ((i - from) % 600 === 0) console.log(`slice ${k}: frame ${i - from}/${to - from} after ${((Date.now() - t0) / 1000).toFixed(0)} s`);
  }
  job.ff.stdin.end();
  await job.done;
  await page.close();
}

let browser = null;
try {
  browser = await chromium.launch({ executablePath: process.env.CHROME });
  const probe = await open(browser);
  const frames = Math.round((await probe.evaluate(() => window.DURATION)) * FPS);
  await probe.close();
  const per = Math.ceil(frames / K);
  await Promise.all(Array.from({ length: K }, (_, k) => slice(browser, k, k * per, Math.min(frames, (k + 1) * per))));
  const list = join(work, 'slices.txt');
  writeFileSync(list, Array.from({ length: K }, (_, k) => `file '${join(work, `seg_${k}.mp4`)}'`).join('\n') + '\n');
  await ffmpeg(['-f', 'concat', '-safe', '0', '-i', list, '-c', 'copy', '-movflags', '+faststart', OUT]).done;
  console.log(`${frames} frames in ${((Date.now() - t0) / 1000).toFixed(0)} s -> ${OUT}`);
} finally {
  for (const ff of encoders) ff.kill('SIGKILL');
  if (browser) await browser.close().catch(() => {});
  rmSync(work, { recursive: true, force: true });
}
