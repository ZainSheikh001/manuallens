"""Download every manual listed in data/manifest.csv into data/raw/.

Usage:  uv run python -m assistant.ingest.download

Already-downloaded files are skipped, so the script is safe to re-run.
"""

import csv
import sys
from pathlib import Path

import httpx

from assistant.config import settings

REQUIRED_COLUMNS = {"manual_id", "title", "source_url"}


def read_manifest(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        missing = REQUIRED_COLUMNS - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"manifest is missing columns: {sorted(missing)}")
        rows = [row for row in reader if row.get("manual_id")]
    ids = [row["manual_id"] for row in rows]
    duplicates = {i for i in ids if ids.count(i) > 1}
    if duplicates:
        raise ValueError(f"duplicate manual_id values: {sorted(duplicates)}")
    return rows


def download_manual(client: httpx.Client, url: str, dest: Path) -> None:
    """Stream one PDF to disk, writing to a temp file first so a failed
    download never leaves a half-written PDF behind."""
    tmp = dest.with_suffix(".part")
    with client.stream("GET", url) as response:
        response.raise_for_status()
        with tmp.open("wb") as f:
            for chunk in response.iter_bytes():
                f.write(chunk)
    with tmp.open("rb") as f:
        if f.read(5) != b"%PDF-":
            tmp.unlink()
            raise ValueError("downloaded file is not a PDF")
    tmp.rename(dest)


def main() -> int:
    rows = read_manifest(settings.manifest_path)
    if not rows:
        print(f"No manuals listed in {settings.manifest_path}. Add rows first.")
        return 1

    settings.raw_dir.mkdir(parents=True, exist_ok=True)
    failures = 0
    with httpx.Client(follow_redirects=True, timeout=60) as client:
        for row in rows:
            dest = settings.raw_dir / f"{row['manual_id']}.pdf"
            if dest.exists():
                print(f"skip   {row['manual_id']} (already downloaded)")
                continue
            try:
                download_manual(client, row["source_url"], dest)
                print(f"ok     {row['manual_id']}")
            except (httpx.HTTPError, ValueError) as exc:
                failures += 1
                print(f"FAILED {row['manual_id']}: {exc}")

    print(f"\n{len(rows) - failures}/{len(rows)} manuals available in {settings.raw_dir}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
