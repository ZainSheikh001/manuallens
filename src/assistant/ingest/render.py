"""Render every page of every manual to a PNG image plus a metadata record.

Usage:  uv run python -m assistant.ingest.render

Output:
    data/pages/<manual_id>/page_0001.png, page_0002.png, ...
    data/pages/pages.jsonl      one JSON line per page (a PageRecord)
"""

import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import fitz  # PyMuPDF

from assistant.config import settings

# A page with fewer extractable characters than this is treated as a scan
# (an image of text with no text layer underneath).
MIN_TEXT_CHARS = 20


@dataclass
class PageRecord:
    manual_id: str
    page_number: int  # 1-based, matching what a PDF viewer shows
    image_path: str
    text: str
    width: int  # pixels
    height: int  # pixels
    has_text_layer: bool


def render_manual(pdf_path: Path, manual_id: str, out_dir: Path, dpi: int = 150) -> list[PageRecord]:
    """Render each page of one PDF to a PNG and reference it in a PageRecord.

    WEEK 1 EXERCISE: implement this function. `uv run pytest` tells you when it works.

    Steps:
      1. Create the folder out_dir/<manual_id>/ if it does not exist.
      2. Open the PDF with fitz.open(pdf_path) and loop over its pages.
         PyMuPDF counts pages from 0; PageRecord.page_number counts from 1.
      3. For each page:
           a. Render it:      pixmap = page.get_pixmap(dpi=dpi)
           b. Save it as      out_dir/<manual_id>/page_0001.png  (4-digit, zero-padded)
           c. Extract text:   page.get_text(), with surrounding whitespace stripped
           d. Decide has_text_layer: True when the text has at least MIN_TEXT_CHARS characters
           e. Append a PageRecord (width and height come from the pixmap)
      4. Return the list of records in page order.

    Before you run it, predict: how many pixels wide is an A4 page (595 points,
    72 points per inch) at 150 DPI? The tests check your answer.
    """
    raise NotImplementedError("Week 1 exercise: implement render_manual")


def write_metadata(records: list[PageRecord], out_path: Path) -> None:
    """Write one JSON object per line. JSONL is easy to append to and to stream."""
    with out_path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")


def main() -> int:
    pdfs = sorted(settings.raw_dir.glob("*.pdf"))
    if not pdfs:
        print(f"No PDFs in {settings.raw_dir}. Run the download step first.")
        return 1

    settings.pages_dir.mkdir(parents=True, exist_ok=True)
    all_records: list[PageRecord] = []
    for pdf_path in pdfs:
        records = render_manual(pdf_path, pdf_path.stem, settings.pages_dir, settings.render_dpi)
        scans = sum(1 for r in records if not r.has_text_layer)
        print(f"{pdf_path.stem}: {len(records)} pages ({scans} without a text layer)")
        all_records.extend(records)

    write_metadata(all_records, settings.pages_dir / "pages.jsonl")
    print(f"\nTotal: {len(all_records)} pages from {len(pdfs)} manuals")
    return 0


if __name__ == "__main__":
    sys.exit(main())
