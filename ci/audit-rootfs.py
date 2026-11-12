#!/usr/bin/python3
"""AI-Assisted. Read-only release gate for an extracted DhampirOS filesystem.

Run in a disposable Linux verifier, never by executing programs from the image.
This records bounded checks, not a claim of absence of vulnerabilities.
"""

import hashlib
import configparser
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit, urlunsplit

root = Path(sys.argv[1]).resolve(strict=True)
output = Path(sys.argv[2])
output.mkdir(parents=True, exist_ok=True)
checks = []


def check(name, passed):
    checks.append({"check": name, "passed": bool(passed)})


def guest_path(name):
    """Resolve absolute guest symlinks inside the guest, with a bounded walk."""
    parts = list(Path(name.lstrip("/")).parts)
    resolved = []
    links = 0
    while parts:
        part = parts.pop(0)
        if part in ("", "."):
            continue
        if part == "..":
            if not resolved:
                raise ValueError("Guest path escapes filesystem")
            resolved.pop()
            continue
        candidate = root.joinpath(*resolved, part)
        if candidate.is_symlink():
            links += 1
            if links > 40:
                raise ValueError("Guest symlink loop")
            target = candidate.readlink()
            if target.is_absolute():
                resolved = []
            parts = list(target.parts[1:] if target.is_absolute() else target.parts) + parts
        else:
            resolved.append(part)
    return root.joinpath(*resolved)


def read(name):
    path = guest_path(name)
    return path.read_text(encoding="utf-8", errors="replace") if path.is_file() else ""


def active(text):
    return "\n".join(line.split("#", 1)[0].strip() for line in text.splitlines())


def file_digest(name):
    path = guest_path(name)
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


status = read("/var/lib/dpkg/status")
packages = {}
for paragraph in status.split("\n\n"):
    fields = dict(re.findall(r"^([A-Za-z-]+): (.*)$", paragraph, re.M))
    if fields.get("Status") == "install ok installed":
        packages[fields["Package"]] = fields.get("Version", "unknown")
check("full desktop package inventory", len(packages) > 500)
for package in ("dhampir-branding", "dhampiros-artwork", "dhampiros-motion",
                "security-misc-shared", "security-misc-desktop", "apparmor",
                "apparmor-profile-dist", "user-sysmaint-split"):
    check(f"installed: {package}", package in packages)
check("Dhampir desktop meta package", any(
    name in packages for name in ("dhampir-vm-gui-lxqt", "dhampir-baremetal-gui-lxqt")
))
(output / "packages.json").write_text(json.dumps(packages, indent=2, sort_keys=True) + "\n")

for asset in ("/usr/share/backgrounds/dhampiros/nocturne-rider.jpg",
              "/usr/share/dhampiros/motion/transparent.png",
              "/usr/share/dhampiros/motion/nocturne-rider-1080p.webm",
              "/usr/share/dhampiros/motion/nocturne-rider-720p-light.webm"):
    check(f"installed visual resource: {asset}", guest_path(asset).is_file())

check("DhampirOS identity", "DhampirOS" in read("/etc/issue") and
      bool(read("/etc/dhampir_version").strip()))

for account in ("user", "sysmaint"):
    settings = configparser.ConfigParser(interpolation=None, strict=False)
    settings.read_string(read(f"/home/{account}/.config/lxqt/lxqt.conf"))
    check(f"initial {account} uses Dhampir LXQt and icons", settings.get("General", "theme", fallback="") == "DhampirOS" and
          settings.get("General", "icon_theme", fallback="") == "DhampirOS")
    desktop = configparser.ConfigParser(interpolation=None, strict=False)
    desktop.read_string(read(f"/home/{account}/.config/pcmanfm-qt/lxqt/settings.conf"))
    check(f"initial {account} has the original wallpaper", desktop.get("Desktop", "Wallpaper", fallback="") ==
          "/usr/share/backgrounds/dhampiros/nocturne-rider.jpg")
    check(f"initial {account} has the native desktop module", "Exec=/usr/bin/dhampiros-motion desktop" in
          read(f"/home/{account}/.config/autostart/lxqt-desktop.desktop"))
grub = active(read("/boot/grub/grub.cfg"))
check("bootloader configuration exists", "menuentry" in grub)
check("no SMBIOS command-line injection in bootloader", not re.search(
    r"dm-smbios|smbios.*--get-string|smbios.*--get-byte", grub, re.I
))
check("no debug root shell in boot entries", not re.search(
    r"(?:init|rdinit)=/(?:usr/)?(?:s?bin)/(?:ba)?sh|systemd.debug_shell|rd.break", grub
))
check("AppArmor not disabled at boot", not re.search(r"apparmor=0|security=none", grub))
for parameter in ("mitigations=auto,nosmt", "slab_nomerge", "init_on_alloc=1"):
    check(f"inherited boot hardening: {parameter}", parameter in grub)
if len(sys.argv) > 3:
    iso_directory = Path(sys.argv[3])
    iso_boot = active((iso_directory / "grub.cfg").read_text())
    iso_setup = active((iso_directory / "config.cfg").read_text())
    live_entries = re.findall(r"^linux /live/vmlinuz (.*)$", iso_boot, re.M)
    check("ISO has live kernel boot entries", len(live_entries) >= 3)
    check("ISO defaults to the user session", "set default=0" in iso_setup and bool(live_entries) and
          "boot-role=" not in live_entries[0] and "systemd.unit=" not in live_entries[0])
    check("ISO does not load SMBIOS debug arguments", "dm_smbios_extra" not in iso_boot + iso_setup)
    for parameter in ("mitigations=auto,nosmt", "slab_nomerge", "init_on_alloc=1"):
        check(f"ISO live boot hardening in every entry: {parameter}", bool(live_entries) and
              all(parameter in entry.split() for entry in live_entries))

apt_config = []
for path in guest_path("/etc/apt").rglob("*"):
    if path.is_file() and path.suffix in (".conf", ".list", ".sources", ""):
        apt_config.append(active(read("/" + str(path.relative_to(root)))))
apt_text = "\n".join(apt_config)
source_details = []
for path in guest_path("/etc/apt").rglob("*"):
    if path.is_file() and path.suffix in (".list", ".sources"):
        text = active(read("/" + str(path.relative_to(root))))
        uris = re.findall(r"(?:[A-Za-z+]+)://[^\s]+", text)
        public_uris = []
        for uri in uris:
            parsed = urlsplit(uri)
            public_uris.append(urlunsplit((parsed.scheme, parsed.netloc.rsplit("@", 1)[-1],
                                          parsed.path, "", "")))
        source_details.append({"file": str(path.relative_to(root)), "uris": public_uris,
                               "enabled": re.findall(r"^Enabled:\s*(.*)$", text, re.M),
                               "suites": re.findall(r"^Suites:\s*(.*)$", text, re.M)})
check("APT does not disable authentication", not re.search(
    r'AllowUnauthenticated\s+["\s]*true|AllowInsecureRepositories\s+["\s]*true|'
    r'trusted\s*=\s*yes|Trusted:\s*yes|Allow-Unauthenticated:\s*yes', apt_text, re.I
))
check("Debian security updates configured", "debian-security" in apt_text or "trixie-security" in apt_text)
# The upstream builder intentionally removes its temporary repository file.
# repository-dist recreates signed public sources on first boot. Verify the
# exact pinned initializer, generator, service and key instead of assuming a
# pre-boot sources file already exists (repository-dist 911537d7e1b0143).
repository_files = {
    "/usr/libexec/repository-dist/repository-dist-initializer":
        "5c07bf133b9c10f450ec095b8ab0bba499208637207a1f2c9aa9a654dec957a7",
    "/usr/lib/systemd/system/repository-dist-initializer.service":
        "aa2aae029124bd6542085b2d3b23ce6458a06276771877179586a1e5abb7f383",
    "/usr/bin/repository-dist":
        "043e54f729f8e22a431666797121a711a91f73cb79c452b4e98bf8d64b783691",
    "/usr/share/keyrings/derivative.asc":
        "e99b253bbb4a7b881bc394de4f6fbbe5f832a32137da8c61a0a603a22e71825f",
}
for name, expected in repository_files.items():
    check(f"pinned Kicksecure update component: {name}", file_digest(name) == expected)
check("Kicksecure repository enabled on first boot", read(
    "/var/lib/repository-dist/derivative_apt_repository_opts").split() == ["--enable", "--codename", "trixie"] and
    guest_path("/etc/systemd/system/multi-user.target.wants/repository-dist-initializer.service").is_file() and
    not guest_path("/var/lib/repository-dist/initializer.done").exists())

# dist-base-files 056f49a680adeefac intentionally ships a shared privacy ID.
# Reject unique builder IDs while retaining that upstream privacy policy.
privacy_id = "b08dfa6083e7567a1921a715000001fb"
check("Kicksecure shared privacy machine identifier", "dist-base-files" in packages and
      read("/etc/machine-id").strip() == privacy_id)
check("D-Bus shares the upstream privacy identifier", read("/var/lib/dbus/machine-id").strip() == privacy_id)
for seed in ("/var/lib/systemd/random-seed", "/var/lib/urandom/random-seed", "/var/lib/random-seed"):
    path = guest_path(seed)
    check(f"no cloned entropy seed: {seed}", not path.exists() or path.stat().st_size == 0)
ssh = guest_path("/etc/ssh")
check("no cloned SSH host private keys", not any(ssh.glob("ssh_host_*_key")))
check("no enabled SSH server socket", not guest_path(
    "/etc/systemd/system/sockets.target.wants/ssh.socket").exists())

accounts = []
for row in read("/etc/shadow").splitlines():
    fields = row.split(":")
    if len(fields) > 1:
        name, secret = fields[:2]
        state = "locked" if secret.startswith(("!", "*")) else "empty" if not secret else "password-set"
        accounts.append({"account": name, "password_state": state})
        if name == "root":
            check("root password locked", state == "locked")
check("shadow account policy readable", any(a["account"] == "root" for a in accounts))
for home in ("/root", "/home"):
    paths = list(guest_path(home).rglob("authorized_keys"))
    check(f"no pre-authorized SSH access in {home}", not any(
        read("/" + str(path.relative_to(root))).strip() for path in paths
    ))
    for credential in (".git-credentials", ".netrc", "id_rsa", "id_ed25519", "secring.gpg", "keyname.sec"):
        check(f"no builder credential {home}/{credential}", not any(
            guest_path(home).rglob(credential)
        ))
    for key_store in ("private-keys-v1.d", "sequoia/keystore", "sq/keystore"):
        stores = guest_path(home).rglob(key_store)
        check(f"no private signing-key store in {home}: {key_store}", not any(
            file.is_file() for store in stores for file in store.rglob("*")
        ))

report = {
    "status": "passed" if all(c["passed"] for c in checks) else "failed",
    "checks": checks, "accounts": accounts,
    "configuration_evidence": {
        "apt_sources": source_details,
        "machine_ids": {name: read(name).strip() for name in
                        ("/etc/machine-id", "/var/lib/dbus/machine-id")},
        "program_permissions": {name: {"mode": oct(guest_path(name).stat().st_mode & 0o7777),
                                       "uid": guest_path(name).stat().st_uid,
                                       "gid": guest_path(name).stat().st_gid}
                                for name in ("/usr/bin/dhampiros-motion", "/usr/bin/python3",
                                             "/usr/libexec/dhampiros-motion/manager.py",
                                             "/usr/libexec/dhampiros-motion/motionlib.py")},
    },
    "scope": "Offline package, update, boot configuration, host key and credential checks",
    "limitations": ["No guarantee of safety or absence of vulnerabilities",
                    "Boot and desktop interaction require separate verification",
                    "Standard upstream user autologin and account setup must be reviewed"],
}
(output / "rootfs-audit.json").write_text(json.dumps(report, indent=2) + "\n")
for item in checks:
    print(("PASS " if item["passed"] else "FAIL ") + item["check"])
sys.exit(0 if report["status"] == "passed" else 1)
