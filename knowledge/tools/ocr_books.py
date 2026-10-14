"""Re-OCR the reference books into plain text, one file per PDF page.

The scans' embedded text layer was produced with a Devanagari OCR model, so the
English translation is unreadable in it. This renders every page and runs the
macOS Vision recogniser (knowledge/tools/ocr.swift) over it in English.

    swiftc -O knowledge/tools/ocr.swift -o knowledge/tools/ocr
    python knowledge/tools/ocr_books.py

Output goes to knowledge/ocr/<book>/p<pdf page, 1-based>.txt and is not committed
(it is the copyrighted text of the books). <book> comes from OUT_DIRS, so adding a PDF
never renames the folders of the others.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[1]
BOOKS = sorted((ROOT / "books").glob("*.pdf"))
OCR_BIN = ROOT / "tools" / "ocr"
BATCH = 25
OUT_DIRS = {"Volume 1": "vol1", "Volume 2": "vol2", "Phaladeepika": "phaladeepika"}


def out_dir(pdf: Path) -> str:
    return next((d for key, d in OUT_DIRS.items() if key in pdf.name), pdf.stem.lower().replace(" ", "_"))


def ocr_batch(job: tuple[str, int, int, str]) -> int:
    pdf, start, stop, out_dir = job
    out = Path(out_dir)
    doc = fitz.open(pdf)
    with tempfile.TemporaryDirectory() as tmp:
        images = []
        for i in range(start, stop):
            if (out / f"p{i + 1:04d}.txt").exists():
                continue
            img = Path(tmp) / f"p{i + 1:04d}.png"
            doc[i].get_pixmap(dpi=200).save(img)
            images.append(img)
        if images:
            subprocess.run([str(OCR_BIN), *map(str, images)], check=True)
        for img in images:
            txt = Path(str(img) + ".txt")
            (out / f"{img.stem}.txt").write_text(txt.read_text() if txt.exists() else "")
    return len(images)


def main() -> None:
    if not OCR_BIN.exists():
        sys.exit(f"build the OCR helper first: swiftc -O {OCR_BIN}.swift -o {OCR_BIN}")
    jobs = []
    for pdf in BOOKS:
        out = ROOT / "ocr" / out_dir(pdf)
        out.mkdir(parents=True, exist_ok=True)
        pages = fitz.open(pdf).page_count
        jobs += [(str(pdf), s, min(s + BATCH, pages), str(out)) for s in range(0, pages, BATCH)]
    with ProcessPoolExecutor(max_workers=6) as pool:
        done = sum(pool.map(ocr_batch, jobs))
    print(f"OCR'd {done} pages")


if __name__ == "__main__":
    main()
