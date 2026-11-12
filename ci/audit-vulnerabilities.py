#!/usr/bin/python3
"""AI-Assisted. Retain Debian findings and assess an exact vendor-version mismatch."""

import gzip
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

root, report = (Path(value) for value in sys.argv[1:3])


def scan(*options):
    return subprocess.check_output(["debsecan", "--suite", "trixie", "--status",
                                    str(root / "var/lib/dpkg/status"), *options], text=True)


detail = scan("--format", "detail")
(report / "debian-vulnerability-report.txt").write_text(detail)
fixed_detail = scan("--format", "detail", "--only-fixed")
(report / "debian-fixable-findings.txt").write_text(fixed_detail)
fixable = scan("--format", "packages", "--only-fixed").splitlines()
effective = list(fixable)
assessments = []
version = json.loads((report / "packages.json").read_text()).get("tor")
advisories = {"TROVE-2026-062", "TROVE-2026-064", "TROVE-2026-067"}
blocks = [block.strip() for block in fixed_detail.split("\n\n") if block.strip()]
found = [set(re.findall(r"TROVE-2026-\d+", block)) for block in blocks]

# Debian's scanner compares the vendor's -1~d13.trixie+1 revision with sid's
# -1 revision. Only these three already-fixed advisories in this exact vendor
# build may be assessed as false positives. Any new issue/package still fails.
if (fixable == ["tor"] and version == "0.4.9.14-1~d13.trixie+1" and len(blocks) == 3 and
        set().union(*found) == advisories and all(len(ids) == 1 for ids in found) and
        all(f"installed: tor {version}" in block for block in blocks)):
    document = root
    safe_document = True
    for part in ("usr", "share", "doc", "tor", "changelog.gz"):
        document /= part
        if document.is_symlink():
            safe_document = False
            break
    if safe_document and document.is_file():
        with gzip.open(document, "rt", encoding="utf-8", errors="strict") as source:
            release = source.read(256_000).split("Changes in version 0.4.9.13", 1)[0]
        if release.startswith("Changes in version 0.4.9.14") and all(issue in release for issue in advisories):
            effective = []
            assessments.append({
                "package": "tor", "installed_version": version, "advisories": sorted(advisories),
                "decision": "vendor revision comparison false positive; upstream fixes present",
                "evidence": "Installed upstream 0.4.9.14 changelog names all three fixes",
                "changelog_sha256": hashlib.sha256(document.read_bytes()).hexdigest(),
                "primary_source": "https://forum.torproject.org/t/security-release-0-4-9-14/22241",
                "upstream_source": "https://dist.torproject.org/tor-0.4.9.14.tar.gz",
            })

(report / "security-update-gate.json").write_text(json.dumps({
    "suite": "trixie", "packages_with_security_fixes_available": effective,
    "raw_packages_reported_by_debsecan": fixable, "reviewed_false_positives": assessments,
    "status": "failed" if effective else "passed",
    "scope": "Debian tracker coverage; raw findings retained; custom packages and unfixed findings need review",
}, indent=2) + "\n")
print(f"Security update gate: {len(effective)} unresolved packages; {len(assessments)} exact vendor assessment")
sys.exit(1 if effective else 0)
