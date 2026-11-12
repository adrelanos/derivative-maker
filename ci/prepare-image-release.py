#!/usr/bin/python3
"""AI-Assisted. Prepare release files only after reviewed image verification.

This never publishes a release or enables website links. The caller must still
verify the actual public asset URLs before copying the catalogue proposal.
"""

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import zipfile

parser = argparse.ArgumentParser()
parser.add_argument("--candidates", type=Path, required=True)
parser.add_argument("--verification", type=Path, required=True)
parser.add_argument("--review", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
review = json.loads(args.review.read_text())
version = "0.1.0-alpha.1"
release_url = f"https://github.com/potemkin666/DhampirOS/releases/download/v{version}/"
source_commit = review["source_commit"]
if not re.fullmatch(r"[0-9a-f]{40}", source_commit):
    raise SystemExit("Invalid reviewed source commit")
if review.get("vulnerability_findings_reviewed") is not True:
    raise SystemExit("Vulnerability findings have not been reviewed")


def digest(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def load_report(root, name):
    return json.loads((root / name).read_text())


assets = {}
tracker_summaries = {}
validated = []
for kind, target in (("iso", "iso"), ("ova", "virtualbox")):
    candidate = args.candidates / f"dhampiros-{target}-candidate"
    evidence = args.verification / f"dhampiros-{target}-verification"
    metadata = load_report(candidate, "candidate.json")
    provenance = load_report(evidence, "candidate-provenance.json")
    filename = f"DhampirOS-{version}-amd64.{kind}"
    image = candidate / filename
    actual_digest = digest(image)
    if (metadata["source_commit"] != source_commit or provenance["source_commit"] != source_commit or
            metadata["file"] != filename or provenance["file"] != filename or
            metadata["sha256"] != actual_digest or provenance["sha256"] != actual_digest or
            review[kind]["sha256"] != actual_digest or image.stat().st_size != metadata["bytes"]):
        raise SystemExit(f"{kind}: source, size or digest mismatch")
    if image.stat().st_size >= 2**31:
        raise SystemExit(f"{kind}: image exceeds GitHub's direct release asset limit; choose a delivery method")
    for report_name in ("rootfs-audit.json", "security-update-gate.json"):
        if load_report(evidence, report_name)["status"] != "passed":
            raise SystemExit(f"{kind}: failed {report_name}")
    if not load_report(evidence, "attestation-verification.json"):
        raise SystemExit(f"{kind}: no verified attestation")
    raw_findings = (evidence / "debian-vulnerability-report.txt").read_text()
    records = [block for block in raw_findings.split("\n\n") if re.match(r"(?:CVE|TEMP)-", block)]
    flagged_packages = {match.group(1) for block in records
                        if (match := re.search(r"installed: (\S+)", block))}
    tracker_summaries[kind] = {
        "raw_finding_records": len(records),
        "unique_tracker_advisories": len({block.splitlines()[0].split()[0] for block in records}),
        "packages_flagged_by_tracker": len(flagged_packages),
        "interpretation": "Version/source tracker findings; applicability is not proven for every record",
        "available_fix_assessment": load_report(evidence, "security-update-gate.json"),
    }
    if kind == "ova" and load_report(evidence, "ova-audit.json")["status"] != "passed":
        raise SystemExit("OVA settings/manifest audit failed")
    boot_review = {}
    for firmware in ("bios", "uefi"):
        screenshot = evidence / firmware / "desktop-capture.png"
        accepted = review[kind][firmware]
        if accepted["outcome"] != "desktop" or accepted["sha256"] != digest(screenshot):
            raise SystemExit(f"{kind}/{firmware}: desktop capture has not been reviewed")
        boot_review[firmware] = accepted
    assets[kind] = {"url": release_url + filename, "bytes": image.stat().st_size,
                    "sha256": actual_digest}
    validated.append((image, evidence, target, provenance, boot_review))

args.output.mkdir(parents=True, exist_ok=False)
for image, _, _, _, _ in validated:
    shutil.copyfile(image, args.output / image.name)
with zipfile.ZipFile(args.output / "DhampirOS-verification.zip", "w", zipfile.ZIP_DEFLATED) as archive:
    for _, evidence, target, _, _ in validated:
        for file in evidence.rglob("*"):
            if file.is_file() and not file.is_symlink() and file.suffix in (".json", ".txt", ".png", ".log", ".cfg"):
                archive.write(file, f"{target}/{file.relative_to(evidence).as_posix()}")
report = {
    "version": version, "source_commit": source_commit, "status": "reviewed-experimental-alpha",
    "images": assets, "review": review,
    "vulnerability_tracker_summary": tracker_summaries,
    "builds": [entry[3] for entry in validated],
    "checks": ["exact source and image digest", "GitHub workflow attestation",
               "offline package, update, hardening and credential checks",
               "OVA manifest and host integration", "Debian available-security-fix gate",
               "network-isolated QEMU BIOS and UEFI desktop captures reviewed"],
    "limitations": ["Not a security certification or guarantee of safety",
                    "Custom packages are not fully covered by Debian's vulnerability tracker",
                    "See vulnerability report for any unfixed findings and review rationale",
                    "Physical hardware, Secure Boot and actual VirtualBox runtime are unverified"],
}
(args.output / "verification-report.json").write_text(json.dumps(report, indent=2) + "\n")
catalogue = {"schema": 1, "status": "published", "audit": "passed", "version": version,
             "source_commit": source_commit, "assets": assets,
             "checksums": release_url + "SHA256SUMS", "report": release_url + "verification-report.json"}
catalogue["tracker_findings_present"] = any(item["raw_finding_records"] for item in tracker_summaries.values())
(args.output / "catalogue-proposal.json").write_text(json.dumps(catalogue, indent=2) + "\n")
published_files = [path for path in args.output.iterdir() if path.name != "catalogue-proposal.json"]
(args.output / "SHA256SUMS").write_text("".join(
    f"{digest(path)}  {path.name}\n" for path in sorted(published_files)
), encoding="ascii")
print(f"Prepared reviewed alpha files in {args.output}. Public URL verification is still required.")
