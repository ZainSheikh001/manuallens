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

import pymupdf

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


def render_manual(
    pdf_path: Path, manual_id: str, out_dir: Path, dpi: int = 150
) -> list[PageRecord]:
    """Render each page of one PDF to a PNG and describe it in a PageRecord.

    Returns the records in page order. Page numbers are 1-based.
    """
    manual_dir = out_dir / manual_id
    manual_dir.mkdir(parents=True, exist_ok=True)

    records: list[PageRecord] = []
    with pymupdf.open(pdf_path) as doc:
        for page_number, page in enumerate(doc, start=1):
            pixmap = page.get_pixmap(dpi=dpi)
            image_path = manual_dir / f"page_{page_number:04d}.png"
            pixmap.save(image_path)

            text = page.get_text().strip()
            records.append(
                PageRecord(
                    manual_id=manual_id,
                    page_number=page_number,
                    image_path=str(image_path),
                    text=text,
                    width=pixmap.width,
                    height=pixmap.height,
                    has_text_layer=len(text) >= MIN_TEXT_CHARS,
                )
            )
    return records


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
