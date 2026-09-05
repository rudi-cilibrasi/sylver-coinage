"""Extract attributed claims from Blok DOCX files without accepting them.

Private source material stays in the caller-selected output directory.
Rectangular tables with explicit numeric row/column headers are parsed;
ambiguous headers/cells are logged, never guessed. All claims require
separate verification against the proof graph or an exact evaluator.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import ZipFile

NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
EXPLICIT = re.compile(r"\{([\d,\s]+)\}\s*:?\s*\[\s*(\d+)")
PROSE = {
    "colon": re.compile(r"\{([\d,\s]+)\}\s*:\s*(\d+)\b"),
    "move": re.compile(r"\{([\d,\s]+)\}\s+(?:moves? to|is answered by|has a winning move of)\s+(\d+)\b", re.I),
    "parenthetical": re.compile(r"\{([\d,\s]+)\}\s*\(winning move\s+(\d+)\b", re.I),
}


def prose_claims(text, source):
    """Literal attributed assertions; no inferred section-level generators.

    Keep original explicit locations stable when adding supported syntax.
    """
    for label, pattern in [("explicit", EXPLICIT), *[(f"prose-{k}", v) for k, v in PROSE.items()]]:
        for index, match in enumerate(pattern.finditer(text), 1):
            yield {"position": list(numbers(match[1])), "reply": int(match[2]),
                   "kind": "winning-reply", "source": source,
                   "location": f"{label}:{index}", "text_offset": match.start()}


def numbers(value):
    value = value.strip().strip("{}[]").strip()
    if not value:
        return ()
    if not re.fullmatch(r"\d+(?:\s*,\s*\d+)*", value):
        raise ValueError(value)
    return tuple(map(int, value.split(",")))


def extract(archive):
    claims, skipped, sources = [], [], {}
    for path in sorted((archive / "g=2").rglob("*.docx")):
        source = str(path.relative_to(archive))
        sources[source] = hashlib.sha256(path.read_bytes()).hexdigest()
        text = subprocess.check_output(
            ["pandoc", "-t", "plain", "--wrap=none", str(path)], text=True)
        claims.extend(prose_claims(text, source))
        with ZipFile(path) as document:
            root = ET.fromstring(document.read("word/document.xml"))
        for ti, table in enumerate(root.findall(".//w:tbl", NS), 1):
            rows = [["".join(t.text or "" for t in cell.findall(".//w:t", NS))
                     for cell in row.findall("./w:tc", NS)]
                    for row in table.findall("./w:tr", NS)]
            try:
                base = numbers(rows[0][0])
                if not base:
                    raise ValueError("empty base")
                headers = [numbers(cell) for cell in rows[0][1:]]
            except (ValueError, IndexError):
                skipped.append({"source": source, "location": f"table:{ti}",
                                "reason": "ambiguous header"})
                continue
            for ri, row in enumerate(rows[1:], 1):
                try:
                    rowbase = numbers(row[0])
                    if len(row) != len(headers) + 1:
                        raise ValueError("nonrectangular row")
                except (ValueError, IndexError):
                    skipped.append({"source": source, "location": f"table:{ti}/row:{ri}",
                                    "reason": "ambiguous row header"})
                    continue
                for ci, (colbase, cell) in enumerate(zip(headers, row[1:]), 1):
                    where = f"table:{ti}/row:{ri}/column:{ci}"
                    common = {"position": sorted(set(base + rowbase + colbase)),
                              "source": source, "location": where}
                    cell = cell.strip()
                    if cell in ("X", "", "?"):
                        continue
                    if cell in ("P", "𝓟", "℘"):
                        claims.append({**common, "kind": "P-position"})
                        continue
                    try:
                        replies = numbers(cell)
                        if not replies:
                            raise ValueError("empty reply")
                    except ValueError:
                        skipped.append({"source": source, "location": where,
                                        "reason": "ambiguous cell", "cell": cell})
                        continue
                    claims.extend({**common, "kind": "winning-reply", "reply": r}
                                  for r in replies)
    return {"privacy": "private unpublished source-derived data; do not publish",
            "sources": sources, "claims": claims, "skipped": skipped}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.write_text(json.dumps(extract(args.archive), indent=2) + "\n")


if __name__ == "__main__":
    main()
