#!/usr/bin/python3
"""AI-Assisted. Select only this repository's full-image workflow candidates."""

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

REPOSITORY = "potemkin666/DhampirOS"


def gh(*args):
    return subprocess.check_output(["gh", *args], text=True)


run_id = os.environ.get("CANDIDATE_RUN", "")
if not run_id:
    runs = json.loads(gh("run", "list", "--repo", REPOSITORY, "--workflow", "local-images.yml",
                         "--branch", os.environ["GITHUB_REF_NAME"], "--limit", "1", "--json", "databaseId"))
    if not runs:
        raise SystemExit("No image build exists on this branch")
    run_id = str(runs[0]["databaseId"])
if not re.fullmatch(r"[0-9]{1,20}", run_id):
    raise SystemExit("Invalid candidate run ID")
run = json.loads(gh("api", f"repos/{REPOSITORY}/actions/runs/{run_id}"))
if (run["repository"]["full_name"] != REPOSITORY or
        run["head_repository"]["full_name"] != REPOSITORY or
        run["path"] != ".github/workflows/local-images.yml" or
        run["event"] not in ("push", "workflow_dispatch")):
    raise SystemExit("Not an authorized full-image workflow run")
subprocess.run(["git", "merge-base", "--is-ancestor", run["head_sha"], "HEAD"], check=True)

if sys.argv[1] == "wait":
    subprocess.run(["gh", "run", "watch", run_id, "--repo", REPOSITORY,
                    "--exit-status", "--interval", "60"], check=True)
    with Path(os.environ["GITHUB_OUTPUT"]).open("a") as output:
        output.write(f"run_id={run_id}\n")
elif sys.argv[1] == "download":
    if run["conclusion"] != "success":
        raise SystemExit("Candidate build did not succeed")
    target = os.environ["IMAGE_TARGET"]
    extension = {"iso": "iso", "virtualbox": "ova"}[target]
    subprocess.run(["gh", "run", "download", run_id, "--repo", REPOSITORY,
                    "--name", f"dhampiros-{target}-candidate", "--dir", "candidate"], check=True)
    root = Path("candidate")
    metadata = json.loads((root / "candidate.json").read_text())
    name = f"DhampirOS-0.1.0-alpha.1-amd64.{extension}"
    if metadata["source_commit"] != run["head_sha"] or metadata["file"] != name:
        raise SystemExit("Candidate source or filename mismatch")
    image = root / name
    with image.open("rb") as source:
        digest = hashlib.file_digest(source, "sha256").hexdigest()
    if digest != metadata["sha256"] or image.stat().st_size != metadata["bytes"]:
        raise SystemExit("Candidate digest/size mismatch")
    verification = Path("verification")
    verification.mkdir()
    attestation = json.loads(gh(
        "attestation", "verify", str(image), "--repo", REPOSITORY,
        "--signer-workflow", f"{REPOSITORY}/.github/workflows/local-images.yml",
        "--source-digest", run["head_sha"], "--format", "json",
    ))
    (verification / "attestation-verification.json").write_text(json.dumps(attestation, indent=2) + "\n")
    (verification / "candidate-provenance.json").write_text(json.dumps({
        "run_id": run_id, "source_commit": run["head_sha"], "file": name,
        "sha256": digest, "bytes": image.stat().st_size, "build_url": run["html_url"],
    }, indent=2) + "\n")
else:
    raise SystemExit("Expected wait or download")
