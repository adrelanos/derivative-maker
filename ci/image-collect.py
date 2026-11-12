#!/usr/bin/python3
"""AI-Assisted. Collect real image candidates; publication requires a later audit."""

import hashlib
import json
from pathlib import Path
import shutil
import sys

build_root = Path(sys.argv[1]).resolve(strict=True)
target = sys.argv[2]
extension = {"iso": "iso", "virtualbox": "ova"}[target]
candidates = list(build_root.rglob(f"Dhampir.{extension}"))
if len(candidates) != 1:
    raise SystemExit(f"Expected one Dhampir {extension}, found {len(candidates)}")
source = candidates[0]
if source.stat().st_size < 300_000_000:
    raise SystemExit("Image is too small to be a full desktop; refusing placeholder")
output = Path("artifacts")
destination = output / f"DhampirOS-0.1.0-alpha.1-amd64.{extension}"
shutil.copyfile(source, destination)
digest = hashlib.file_digest(destination.open("rb"), "sha256").hexdigest()
(output / f"{destination.name}.sha256").write_text(
    f"{digest}  {destination.name}\n", encoding="ascii"
)
for evidence in build_root.rglob("dm-source-state"):
    shutil.copyfile(evidence, output / "build-source-state.txt")
(output / "candidate.json").write_text(json.dumps({
    "file": destination.name, "bytes": destination.stat().st_size,
    "sha256": digest, "status": "candidate-awaiting-boot-and-security-audit",
    "source_commit": (output / "source-commit.txt").read_text().strip(),
    "flavor": "dhampir-lxqt", "target": target, "apt_freshness": "current",
    "smbios_debug_reader": False, "serial_console": False,
    "source_signatures": "build-local ephemeral CI identity; not official Kicksecure release signatures",
}, indent=2) + "\n", encoding="utf-8")
