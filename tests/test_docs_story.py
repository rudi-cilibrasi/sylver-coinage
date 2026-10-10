import json
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / 'sylver/campaigns/o16-2026-10-09/audit.json'
R38 = ROOT / 'sylver/campaigns/r38-2026-10-09/audit.json'

# Draw the whole film at four frames a second on a recording 2D context: every
# call must have finite numeric arguments, and every string drawn is collected.
SCRIPT = r'''
const root = process.argv[process.argv.length - 1];
const film = require(root + "/docs/story.js");
const texts = new Set(), bad = [];
let frame = 0;
const state = { globalAlpha: 1, font: "10px sans-serif", fillStyle: "#000", strokeStyle: "#000", lineWidth: 1,
                textAlign: "start", textBaseline: "alphabetic", letterSpacing: "0px", lineCap: "butt",
                lineJoin: "miter", shadowBlur: 0, shadowColor: "transparent", globalCompositeOperation: "source-over" };
const stack = [];
const gradient = { addColorStop() {} };
const methods = {
  save() { stack.push({ ...state }); },
  restore() { Object.assign(state, stack.pop()); },
  measureText(s) { const px = Number((/([\d.]+)px/.exec(state.font) || [0, 10])[1]); return { width: String(s).length * px * 0.55 }; },
  fillText(s) { texts.add(String(s)); },
  strokeText(s) { texts.add(String(s)); },
  createLinearGradient() { return gradient; },
  createRadialGradient() { return gradient; },
};
const ctx = new Proxy(state, {
  get(target, prop) {
    if (prop in target) return target[prop];
    const impl = methods[prop];
    return (...args) => {
      for (const v of args) if (typeof v === "number" && !Number.isFinite(v)) bad.push(`${String(prop)} at frame ${frame}: ${args}`);
      return impl ? impl(...args) : undefined;
    };
  },
  set(target, prop, value) {
    if (typeof value === "number" && !Number.isFinite(value)) bad.push(`${String(prop)} = ${value} at frame ${frame}`);
    target[prop] = value;
    return true;
  },
  has(target, prop) { return prop in target || prop in methods; },
});
const frames = Math.ceil(film.DURATION * 4);
for (frame = 0; frame <= frames; frame++) film.renderAt(ctx, frame / 4);
console.log(JSON.stringify({
  duration: film.DURATION, frames,
  chapters: film.CHAPTERS.map((c) => ({ name: c.name, start: c.start, end: c.end, dur: c.dur })),
  answers: film.ANSWERS, ruledOut: film.RULED_OUT_38, texts: [...texts], bad: bad.slice(0, 20), stackDepth: stack.length,
}));
'''


class StoryFilmTests(unittest.TestCase):
    """docs/story.js must draw every frame cleanly and agree with the records."""

    @classmethod
    def setUpClass(cls):
        node = shutil.which('node')
        if node is None:
            raise unittest.SkipTest('node is not installed')
        out = subprocess.run([node, '-e', SCRIPT, str(ROOT)], capture_output=True, text=True, timeout=300, check=True)
        cls.report = json.loads(out.stdout)
        # Captions wrap at spaces, so join the drawn lines with spaces.
        cls.drawn = ' '.join(cls.report['texts'])

    def test_every_frame_draws_with_finite_coordinates(self):
        self.assertEqual(self.report['bad'], [])
        self.assertEqual(self.report['stackDepth'], 0)
        self.assertGreater(self.report['frames'], 1000)

    def test_chapters_tile_the_film(self):
        chapters = self.report['chapters']
        self.assertEqual(chapters[0]['start'], 0)
        for before, after in zip(chapters, chapters[1:]):
            self.assertEqual(before['end'], after['start'])
        self.assertEqual(chapters[-1]['end'], self.report['duration'])
        self.assertEqual(sum(c['dur'] for c in chapters), self.report['duration'])

    def test_answers_match_the_ledger(self):
        ledger = json.loads(LEDGER.read_text())['answers']
        film = {int(r): a for r, a in self.report['answers'].items()}
        expected = {int(r): row['answer'] for r, row in ledger.items() if int(r) <= 36}
        self.assertEqual(film, expected)

    def test_ruled_out_answers_to_38_match_the_audit(self):
        refuted = json.loads(R38.read_text())['refuted_answers_to_38']
        self.assertEqual(sorted(self.report['ruledOut']), sorted(int(m) for m in refuted))

    def test_key_facts_are_on_screen(self):
        for fact in ('1884', 'a·b − a − b', 'Winning Ways', 'GEORGE SICHERMAN', 'THOMAS BLOK', '403,200', '381,091',
                     '49,337', '633,734,956', '{16, 26, 54, 60, 62}', '{16, 28, 36, 38, 58}', 'OEIS A248380',
                     'Still open'):
            self.assertIn(fact, self.drawn, fact)


if __name__ == '__main__':
    unittest.main()
