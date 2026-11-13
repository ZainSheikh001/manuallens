"""Tests for the page renderer. Run with:  uv run pytest

These build a tiny PDF on the fly, so no manuals are needed.
"""

import json
from pathlib import Path

import pymupdf
import pytest
from PIL import Image

from assistant.ingest.render import PageRecord, render_manual, write_metadata

A4_WIDTH_PT, A4_HEIGHT_PT = 595, 842  # PDF points; 72 points = 1 inch


@pytest.fixture
def sample_pdf(tmp_path: Path) -> Path:
    """Three A4 pages: two with text, one blank (stands in for a scanned page)."""
    doc = pymupdf.open()
    page1 = doc.new_page(width=A4_WIDTH_PT, height=A4_HEIGHT_PT)
    page1.insert_text((72, 100), "Cylinder head bolt torque: 25 Nm. Tighten in sequence.")
    page2 = doc.new_page(width=A4_WIDTH_PT, height=A4_HEIGHT_PT)
    page2.insert_text((72, 100), "Error E24: drain pump blocked. Check the filter first.")
    doc.new_page(width=A4_WIDTH_PT, height=A4_HEIGHT_PT)
    path = tmp_path / "sample.pdf"
    doc.save(path)
    doc.close()
    return path


def test_one_record_per_page(sample_pdf: Path, tmp_path: Path) -> None:
    records = render_manual(sample_pdf, "sample", tmp_path / "pages")
    assert len(records) == 3
    assert all(isinstance(r, PageRecord) for r in records)
    assert all(r.manual_id == "sample" for r in records)


def test_page_numbers_are_one_based(sample_pdf: Path, tmp_path: Path) -> None:
    records = render_manual(sample_pdf, "sample", tmp_path / "pages")
    assert [r.page_number for r in records] == [1, 2, 3]


def test_images_are_saved_with_padded_names(sample_pdf: Path, tmp_path: Path) -> None:
    out_dir = tmp_path / "pages"
    records = render_manual(sample_pdf, "sample", out_dir)
    assert Path(records[0].image_path) == out_dir / "sample" / "page_0001.png"
    assert Path(records[2].image_path) == out_dir / "sample" / "page_0003.png"
    for record in records:
        with Image.open(record.image_path) as image:
            assert image.format == "PNG"
            assert image.size == (record.width, record.height)


@pytest.mark.parametrize("dpi", [72, 150, 200])
def test_dpi_controls_pixel_size(sample_pdf: Path, tmp_path: Path, dpi: int) -> None:
    records = render_manual(sample_pdf, "sample", tmp_path / "pages", dpi=dpi)
    expected_width = A4_WIDTH_PT * dpi / 72
    expected_height = A4_HEIGHT_PT * dpi / 72
    assert abs(records[0].width - expected_width) <= 2
    assert abs(records[0].height - expected_height) <= 2


def test_text_is_extracted(sample_pdf: Path, tmp_path: Path) -> None:
    records = render_manual(sample_pdf, "sample", tmp_path / "pages")
    assert "25 Nm" in records[0].text
    assert "E24" in records[1].text
    assert records[0].text == records[0].text.strip()


def test_blank_page_has_no_text_layer(sample_pdf: Path, tmp_path: Path) -> None:
    records = render_manual(sample_pdf, "sample", tmp_path / "pages")
    assert records[0].has_text_layer is True
    assert records[1].has_text_layer is True
    assert records[2].has_text_layer is False
    assert records[2].text == ""


def test_metadata_roundtrip(sample_pdf: Path, tmp_path: Path) -> None:
    records = render_manual(sample_pdf, "sample", tmp_path / "pages")
    out_path = tmp_path / "pages.jsonl"
    write_metadata(records, out_path)
    lines = out_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 3
    first = json.loads(lines[0])
    assert first["manual_id"] == "sample"
    assert first["page_number"] == 1
    assert "25 Nm" in first["text"]
