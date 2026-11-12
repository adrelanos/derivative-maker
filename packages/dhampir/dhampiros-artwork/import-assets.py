#!/usr/bin/env python3
"""Import the validated DhampirOS artwork payload from the supplied ZIP.

This deliberately imports only the purpose-built DhampirOS asset pack. The
loose `art/` reference images in the ZIP are ignored.
"""

from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import shutil
import sys
import tarfile
import zipfile

PACKAGE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = PACKAGE_DIR / "assets"
OUTPUT = ASSETS_DIR / "rootfs-overlay.tar.gz"

OVERLAY_SUFFIX = "DhampirOS-Linux-Assets/DhampirOS-rootfs-overlay.tar.gz"
VALIDATION_SUFFIX = "DhampirOS-Linux-Assets/VALIDATION.json"
PROVENANCE_SUFFIX = "DhampirOS-Linux-Assets/sources/provenance.json"


def die(message: str) -> "NoReturn":
    raise SystemExit(message)


def find_member(names: list[str], suffix: str) -> str:
    matches = [name for name in names if name.endswith(suffix)]
    if len(matches) != 1:
        die(f"Expected exactly one {suffix!r} in ZIP, found {len(matches)}")
    return matches[0]


def validate_tar(payload: bytes) -> None:
    with tarfile.open(fileobj=io.BytesIO(payload), mode="r:gz") as archive:
        members = archive.getmembers()
        if not members:
            die("Artwork overlay archive is empty")
        for member in members:
            path = Path(member.name)
            if path.is_absolute() or ".." in path.parts:
                die(f"Unsafe path in artwork overlay: {member.name}")
            if member.issym() or member.islnk():
                target = Path(member.linkname)
                if target.is_absolute() or ".." in target.parts:
                    die(f"Unsafe link in artwork overlay: {member.name} -> {member.linkname}")


def main() -> None:
    if len(sys.argv) != 2:
        die(f"Usage: {Path(sys.argv[0]).name} '/path/to/vampire hunter d.zip'")

    zip_path = Path(sys.argv[1]).expanduser().resolve()
    if not zip_path.is_file():
        die(f"ZIP not found: {zip_path}")

    with zipfile.ZipFile(zip_path) as source:
        names = source.namelist()
        overlay_member = find_member(names, OVERLAY_SUFFIX)
        validation_member = find_member(names, VALIDATION_SUFFIX)
        provenance_member = find_member(names, PROVENANCE_SUFFIX)

        validation = json.loads(source.read(validation_member))
        if validation.get("errors") != []:
            die("Asset pack validation reports errors; refusing to import")
        if validation.get("rootfs_overlay_archive_matches_files") is not True:
            die("Asset pack says rootfs overlay does not match source files")

        provenance = json.loads(source.read(provenance_member))
        if provenance.get("identity") != "DhampirOS by potemkin":
            die("Unexpected asset-pack identity; refusing to import")

        payload = source.read(overlay_member)

    validate_tar(payload)
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    tmp = OUTPUT.with_suffix(OUTPUT.suffix + ".tmp")
    tmp.write_bytes(payload)
    tmp.replace(OUTPUT)

    digest = hashlib.sha256(payload).hexdigest()
    print(f"Imported {OUTPUT.relative_to(PACKAGE_DIR)}")
    print(f"SHA256 {digest}")
    print("Loose reference images were intentionally not imported.")


if __name__ == "__main__":
    main()
