#!/usr/bin/python3
"""AI-Assisted. Stage reviewed files in an owner-created release draft.

No guest image programs execute in this job. Write permission is isolated from
the source builder and VM verifier; this job copies and hashes reviewed data.
"""

import hashlib
import json
from pathlib import Path
import re
import subprocess

REPOSITORY = "potemkin666/DhampirOS"
TAG = "v0.1.0-alpha.1"
review_file = Path("release-reviews") / f"{TAG}.json"
review = json.loads(review_file.read_text())


def execute(*args):
    subprocess.run([str(arg) for arg in args], check=True)


def gh_json(*args):
    return json.loads(subprocess.check_output(["gh", *args], text=True))


def source_run(field, workflow):
    run_id = str(review[field])
    if not re.fullmatch(r"[0-9]{1,20}", run_id):
        raise SystemExit("Invalid reviewed Actions run")
    run = gh_json("api", f"repos/{REPOSITORY}/actions/runs/{run_id}")
    if (run["repository"]["full_name"] != REPOSITORY or
            run["head_repository"]["full_name"] != REPOSITORY or
            run["path"] != f".github/workflows/{workflow}" or run["conclusion"] != "success" or
            run["event"] not in ("push", "workflow_dispatch")):
        raise SystemExit("Reviewed run is not a successful authorized workflow")
    execute("git", "merge-base", "--is-ancestor", run["head_sha"], "HEAD")
    return run_id, run


build_id, build = source_run("candidate_run", "local-images.yml")
verification_id, verification = source_run("verification_run", "local-image-verification.yml")
if build["head_sha"] != review["source_commit"]:
    raise SystemExit("Reviewed source differs from the image build")
execute("git", "merge-base", "--is-ancestor", build["head_sha"], verification["head_sha"])
execute("gh", "run", "download", build_id, "--repo", REPOSITORY,
        "--pattern", "dhampiros-*-candidate", "--dir", "candidates")
execute("gh", "run", "download", verification_id, "--repo", REPOSITORY,
        "--pattern", "dhampiros-*-verification", "--dir", "verified")
for image in Path("candidates").rglob("DhampirOS-*.iso"):
    execute("gh", "attestation", "verify", image, "--repo", REPOSITORY,
            "--signer-workflow", f"{REPOSITORY}/.github/workflows/local-images.yml",
            "--source-digest", build["head_sha"])
for image in Path("candidates").rglob("DhampirOS-*.ova"):
    execute("gh", "attestation", "verify", image, "--repo", REPOSITORY,
            "--signer-workflow", f"{REPOSITORY}/.github/workflows/local-images.yml",
            "--source-digest", build["head_sha"])
execute("./ci/prepare-image-release.py", "--candidates", "candidates", "--verification", "verified",
        "--review", review_file, "--output", "prepared-release")

existing = subprocess.run(["gh", "release", "view", TAG, "--repo", REPOSITORY,
                           "--json", "apiUrl,isDraft,targetCommitish"], capture_output=True, text=True)
if existing.returncode == 0:
    state = json.loads(existing.stdout)
    if not state["isDraft"] or state["targetCommitish"] != build["head_sha"]:
        raise SystemExit("Refusing to replace an existing public or differently sourced release")
else:
    raise SystemExit("The repository owner must create the exact-source draft before staging assets")
release_id = state["apiUrl"].rsplit("/", 1)[-1]
if not re.fullmatch(r"[0-9]+", release_id):
    raise SystemExit("Invalid draft release identity")
files = sorted(path for path in Path("prepared-release").iterdir() if path.name != "catalogue-proposal.json")
release = gh_json("api", f"repos/{REPOSITORY}/releases/{release_id}")
remote = {asset["name"]: asset for asset in release["assets"]}
pending = []
for file in files:
    with file.open("rb") as payload:
        expected = "sha256:" + hashlib.file_digest(payload, "sha256").hexdigest()
    if remote.get(file.name, {}).get("digest") != expected or remote[file.name]["size"] != file.stat().st_size:
        pending.append(file)
if pending:
    execute("gh", "release", "upload", TAG, "--repo", REPOSITORY, "--clobber", *pending)
release = gh_json("api", f"repos/{REPOSITORY}/releases/{release_id}")
remote = {asset["name"]: asset for asset in release["assets"]}
for file in files:
    with file.open("rb") as payload:
        expected = "sha256:" + hashlib.file_digest(payload, "sha256").hexdigest()
    if remote.get(file.name, {}).get("digest") != expected or remote[file.name]["size"] != file.stat().st_size:
        raise SystemExit(f"Uploaded release asset integrity mismatch: {file.name}")
print(f"Staged and hash-verified the reviewed experimental files for {TAG}.")
print("The repository owner publishes release metadata; then public URL verification is required before enabling the catalogue.")
