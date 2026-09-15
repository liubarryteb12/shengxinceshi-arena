#!/usr/bin/env python3
"""Download a GEO series and record file checksums.

This is intentionally a small standard-library-only downloader so it can run
inside GitHub Actions without a project-specific Python environment.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import shutil
import time
import urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo

LOCAL_TZ = ZoneInfo("Asia/Shanghai")


def bucket_for(dataset_id: str) -> str:
    digits = dataset_id.upper().removeprefix("GSE")
    if not digits.isdigit() or len(digits) < 4:
        raise ValueError(f"Unsupported GEO series id: {dataset_id}")
    return digits[:-3] + "nnn"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def download(url: str, target: Path, retries: int = 3) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and target.stat().st_size > 0:
        return
    temporary = target.with_suffix(target.suffix + ".partial")
    for attempt in range(1, retries + 1):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "shengxinceshi-arena/0.1"})
            with urllib.request.urlopen(request, timeout=60) as response, temporary.open("wb") as out:
                shutil.copyfileobj(response, out, length=1024 * 1024)
            temporary.replace(target)
            return
        except Exception:
            temporary.unlink(missing_ok=True)
            if attempt == retries:
                raise
            time.sleep(attempt * 2)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True, help="GEO series id, e.g. GSE7451")
    parser.add_argument("--output", type=Path, required=True, help="inputs/raw directory")
    parser.add_argument("--include-raw", action="store_true", default=True)
    args = parser.parse_args()

    dataset = args.dataset.upper()
    bucket = bucket_for(dataset)
    base = f"https://ftp.ncbi.nlm.nih.gov/geo/series/GSE{bucket}/{dataset}"
    dataset_dir = args.output / dataset
    metadata_dir = dataset_dir / "metadata"
    manifest = {
        "schema_version": "1.0",
        "dataset_id": dataset,
        "source_root": base + "/",
        "downloaded_at": dt.datetime.now(LOCAL_TZ).date().isoformat(),
        "files": [],
    }
    specs = [
        (f"{base}/suppl/{dataset}_RAW.tar", dataset_dir / f"{dataset}_RAW.tar"),
        (f"{base}/matrix/{dataset}_series_matrix.txt.gz", metadata_dir / f"{dataset}_series_matrix.txt.gz"),
        (f"{base}/suppl/filelist.txt", metadata_dir / f"{dataset}_filelist.txt"),
    ]
    for url, target in specs:
        download(url, target)
        manifest["files"].append({
            "url": url,
            "path": str(target),
            "size_bytes": target.stat().st_size,
            "sha256": sha256(target),
        })
    (metadata_dir / "download_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
