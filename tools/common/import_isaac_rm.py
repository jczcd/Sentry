#!/usr/bin/env python3
"""Safely import the relevant parts of the uploaded Isaac-RM archive."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path, PurePosixPath
import shutil
import zipfile


ALLOWED_ROOT_FILE = "RMUC2024.usd"
ALLOWED_PREFIX = "RMUC_sim_nav/"
SKIP_PARTS = {".git", "__MACOSX"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--workspace", default=Path.cwd(), type=Path)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def wanted(name: str) -> bool:
    if "\\" in name:
        raise ValueError(f"unsafe archive member: {name}")
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"unsafe archive member: {name}")
    if any(part in SKIP_PARTS or part.lower() == ".thumbs" for part in path.parts):
        return False
    return name == ALLOWED_ROOT_FILE or name.startswith(ALLOWED_PREFIX)


def main() -> int:
    args = parse_args()
    archive = args.archive.expanduser().resolve()
    workspace = args.workspace.expanduser().resolve()
    target = workspace / "isaac_sim" / "assets" / "legacy_4_1"
    if not archive.is_file():
        raise SystemExit(f"archive not found: {archive}")
    target.mkdir(parents=True, exist_ok=True)

    extracted = 0
    total_bytes = 0
    with zipfile.ZipFile(archive) as source:
        for info in source.infolist():
            if not wanted(info.filename) or info.is_dir():
                continue
            relative = PurePosixPath(info.filename)
            destination = target.joinpath(*relative.parts).resolve()
            if target.resolve() not in destination.parents:
                raise ValueError(f"archive member escapes target: {info.filename}")
            destination.parent.mkdir(parents=True, exist_ok=True)
            if destination.exists() and not args.force:
                continue
            with source.open(info) as src, destination.open("wb") as dst:
                shutil.copyfileobj(src, dst, length=1024 * 1024)
            extracted += 1
            total_bytes += info.file_size

    marker = {
        "source_archive": archive.name,
        "imported_at_utc": datetime.now(timezone.utc).isoformat(),
        "extracted_files": extracted,
        "uncompressed_bytes": total_bytes,
        "note": "Isaac-RM v1.0 asset import; preserve the upstream non-commercial terms.",
    }
    (target / "IMPORT.json").write_text(
        json.dumps(marker, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"imported {extracted} files ({total_bytes} bytes) into {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
