#!/usr/bin/python3
"""AI-Assisted. Import the exact public OVA and capture isolated VirtualBox boots."""

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
from urllib.parse import urlparse
from urllib.request import urlopen

REPOSITORY = "potemkin666/DhampirOS"
ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / "verification/virtualbox"
SCRATCH = Path(os.environ.get("RUNNER_TEMP", "/tmp")) / "dhampiros-virtualbox-runtime"
APPLIANCE = SCRATCH / "DhampirOS-0.1.0-alpha.1-amd64.ova"
CATALOGUE = ROOT / "showcase/downloads.json"


def run(*args, **options):
    try:
        return subprocess.run(args, check=True, text=True, capture_output=True, timeout=600, **options).stdout
    except subprocess.CalledProcessError as error:
        print(error.stdout[-8000:], file=sys.stderr)
        print(error.stderr[-8000:], file=sys.stderr)
        raise


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def require_disposable_runner():
    if os.environ.get("GITHUB_REPOSITORY") != REPOSITORY or os.environ.get("RUNNER_ENVIRONMENT") != "github-hosted":
        raise SystemExit("Host setup is limited to this repository's disposable hosted runner")


def setup():
    require_disposable_runner()
    REPORT.mkdir(parents=True, exist_ok=True)
    SCRATCH.mkdir(parents=True, exist_ok=True)
    # Ubuntu's 7.0.16 DKMS module cannot build against the hosted kernel 7.0.
    # Authenticate Oracle's scoped APT repository; never use trusted=yes.
    key = SCRATCH / "oracle.asc"
    with urlopen("https://www.virtualbox.org/download/oracle_vbox_2016.asc", timeout=60) as response:
        key.write_bytes(response.read(100_000))
    if hashlib.sha256(key.read_bytes()).hexdigest() != "49e6801d45f6536232c11be6cdb43fa8e0198538d29d1075a7e10165e1fbafe2":
        raise SystemExit("Oracle archive signing key changed; review required")
    key_home = SCRATCH / "key-check"
    key_home.mkdir(mode=0o700)
    key_data = run("gpg", "--batch", "--homedir", str(key_home), "--with-colons", "--show-keys", str(key))
    fingerprints = re.findall(r"^fpr:::::::::([A-F0-9]+):", key_data, re.M)
    if not fingerprints or fingerprints[0] != "B9F8D658297AF3EFC18D5CDFA2F683C52980AECF":
        raise SystemExit("Unexpected Oracle archive signing identity")
    keyring = SCRATCH / "oracle.gpg"
    run("gpg", "--batch", "--homedir", str(key_home), "--dearmor", "--output", str(keyring), str(key))
    installed_keyring = "/usr/share/keyrings/dhampiros-ci-oracle.gpg"
    run("sudo", "install", "-m", "0644", str(keyring), installed_keyring)
    source = SCRATCH / "oracle.sources"
    source.write_text(
        "Types: deb\nURIs: https://download.virtualbox.org/virtualbox/debian\n"
        f"Suites: noble\nComponents: contrib\nArchitectures: amd64\nSigned-By: {installed_keyring}\n")
    run("sudo", "install", "-m", "0644", str(source), "/etc/apt/sources.list.d/dhampiros-ci-oracle.sources")
    (REPORT / "host-apt-update.log").write_text(run("sudo", "apt-get", "update", "--error-on=any"))
    package_version = "7.2.22-175245~Ubuntu~noble"
    (REPORT / "host-install.log").write_text(run(
        "sudo", "apt-get", "install", "--yes", "--no-install-recommends", f"virtualbox-7.2={package_version}"))
    write_json(REPORT / "host-package.json", {
        "package": "virtualbox-7.2", "version": package_version,
        "repository": "https://download.virtualbox.org/virtualbox/debian",
        "archive_signing_fingerprint": fingerprints[0],
        "key_sha256": hashlib.sha256(key.read_bytes()).hexdigest(),
    })


def prepare():
    REPORT.mkdir(parents=True, exist_ok=True)
    SCRATCH.mkdir(parents=True, exist_ok=True)
    release = json.loads(CATALOGUE.read_text())
    review = json.loads((ROOT / "release-reviews/v0.1.0-alpha.1.json").read_text())
    asset = release["assets"]["ova"]
    url = urlparse(asset["url"])
    if (release["status"] != "published" or release["audit"] != "passed" or
            release["version"] != "0.1.0-alpha.1" or
            url.geturl() != f"https://github.com/{REPOSITORY}/releases/download/v0.1.0-alpha.1/{APPLIANCE.name}" or
            not re.fullmatch(r"[a-f0-9]{40}", release["source_commit"]) or
            review["source_commit"] != release["source_commit"] or
            review["ova"]["sha256"] != asset["sha256"]):
        raise SystemExit("Published appliance does not match the reviewed catalogue")
    run("git", "merge-base", "--is-ancestor", release["source_commit"], "HEAD")
    run("gh", "release", "download", "v0.1.0-alpha.1", "--repo", REPOSITORY,
        "--pattern", APPLIANCE.name, "--dir", str(SCRATCH))
    with APPLIANCE.open("rb") as image:
        digest = hashlib.file_digest(image, "sha256").hexdigest()
    if digest != asset["sha256"] or APPLIANCE.stat().st_size != asset["bytes"]:
        raise SystemExit("Published appliance digest or size mismatch")
    attestation = json.loads(run(
        "gh", "attestation", "verify", str(APPLIANCE), "--repo", REPOSITORY,
        "--signer-workflow", f"{REPOSITORY}/.github/workflows/local-images.yml",
        "--source-digest", release["source_commit"], "--format", "json"))
    write_json(REPORT / "attestation-verification.json", attestation)
    write_json(REPORT / "image-identity.json", {
        "url": asset["url"], "sha256": digest, "bytes": APPLIANCE.stat().st_size,
        "source_commit": release["source_commit"],
    })
    # Existing archive audit validates all members and manifests before import.
    # Its extracted disk stays in disposable scratch, outside uploaded evidence.
    audit = SCRATCH / "archive-audit"
    run(sys.executable, str(ROOT / "ci/audit-ova.py"), str(APPLIANCE), str(audit))
    shutil.copyfile(audit / "ova-audit.json", REPORT / "ova-audit.json")
    print("Authenticated the exact published OVA and its archive manifest", flush=True)


def boot():
    from PIL import Image, ImageStat

    firmware = os.environ["VM_FIRMWARE"]
    if firmware not in ("bios", "efi"):
        raise SystemExit("Unsupported firmware")
    if not (REPORT / "image-identity.json").is_file():
        raise SystemExit("Authenticate the public appliance first")
    # Only this owner-repository disposable hosted runner may change modules.
    require_disposable_runner()
    # A loaded KVM module can reserve VT-x even with no QEMU guest running.
    for module in ("kvm_intel", "kvm_amd", "kvm"):
        if (Path("/sys/module") / module).exists():
            run("sudo", "modprobe", "-r", module)
    run("sudo", "modprobe", "vboxdrv")
    run("sudo", "chown", str(os.getuid()), "/dev/vboxdrv")
    run("sudo", "chmod", "0600", "/dev/vboxdrv")
    os.environ["VBOX_USER_HOME"] = str(SCRATCH / "settings")
    name = f"dhampiros-runtime-{firmware}"
    version = run("VBoxManage", "--version").strip()
    (REPORT / "import.log").write_text(run(
        "VBoxManage", "import", str(APPLIANCE), "--vsys", "0", "--vmname", name,
        "--basefolder", str(SCRATCH / "machines"), "--eula", "accept",
        "--settingsfile", str(SCRATCH / "machines" / name / f"{name}.vbox")))
    started = False
    try:
        # Preserve declared CPU, RAM, graphics and storage. Disable host-facing
        # features before the imported guest can execute its first instruction.
        options = ["--firmware", firmware, "--clipboard-mode", "disabled",
                   "--draganddrop", "disabled", "--vrde", "off", "--audio-enabled", "off",
                   "--usb", "off", "--usbehci", "off", "--usbxhci", "off"]
        for number in range(1, 9):
            options += [f"--nic{number}", "none"]
        run("VBoxManage", "modifyvm", name, *options)
        information = run("VBoxManage", "showvminfo", name, "--machinereadable")
        (REPORT / "vm-before-boot.txt").write_text(information)
        config = {}
        for line in information.splitlines():
            key, separator, value = line.partition("=")
            if separator:
                config[key] = value.strip('"')
        declared = json.loads((REPORT / "ova-audit.json").read_text())
        if (config.get("memory") != str(declared["memory_mib"]) or
                config.get("cpus") != str(declared["processors"])):
            raise RuntimeError("Imported appliance resources changed")
        for number in range(1, 9):
            if config.get(f"nic{number}") != "none":
                raise RuntimeError("A network interface remains enabled")
        if (config.get("clipboard") != "disabled" or config.get("draganddrop") != "disabled" or
                config.get("vrde") != "off" or "SharedFolderName" in information):
            raise RuntimeError("A host integration feature remains enabled")
        write_json(REPORT / "boot-environment.json", {
            "virtualbox": version, "kernel": run("uname", "-r").strip(), "firmware": firmware,
            "network": "all adapters disabled", "clipboard": "disabled", "drag_and_drop": "disabled",
            "shared_folders": "none", "usb": "disabled", "remote_display": "disabled",
            "writes": "fresh disposable import; published bytes unchanged",
            "declared_memory_mib": config.get("memory"), "declared_cpus": config.get("cpus"),
        })
        run("VBoxManage", "startvm", name, "--type", "headless")
        started = True
        beginning = time.monotonic()
        for seconds in (20, 90, 240, 360):
            time.sleep(max(0, beginning + seconds - time.monotonic()))
            run("VBoxManage", "controlvm", name, "screenshotpng", str(REPORT / f"boot-{seconds}.png"))
            print(f"Captured actual VirtualBox {firmware} display at {seconds}s", flush=True)
        final = REPORT / "boot-360.png"
        with Image.open(final) as capture:
            variation = max(ImageStat.Stat(capture.convert("RGB")).stddev)
            width, height = capture.size
        write_json(REPORT / "capture-status.json", {
            "status": "manual-review-required", "width": width, "height": height,
            "variation": variation, "scope": "Captured display is not automatic proof of a working desktop",
        })
        if width < 640 or height < 400 or variation < 4:
            raise RuntimeError("Final VirtualBox capture is blank or undersized")
    finally:
        if started:
            subprocess.run(["VBoxManage", "controlvm", name, "poweroff"], capture_output=True, timeout=30)
        for log in (SCRATCH / "machines").glob("*/Logs/VBox.log*"):
            if log.is_file() and log.stat().st_size < 20_000_000:
                shutil.copyfile(log, REPORT / log.name)
        # Never unregister/delete any VM outside this isolated VBOX_USER_HOME.
        subprocess.run(["VBoxManage", "unregistervm", name, "--delete"], capture_output=True, timeout=60)


if __name__ == "__main__":
    {"setup": setup, "prepare": prepare, "boot": boot}[sys.argv[1]]()
