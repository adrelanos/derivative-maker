#!/usr/bin/python3
"""AI-Assisted. Validate an OVA's paths, manifest and host integration settings."""

import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys
import tarfile
import xml.etree.ElementTree as ET

appliance = Path(sys.argv[1])
output = Path(sys.argv[2])
output.mkdir(parents=True, exist_ok=True)
checks = []


def check(name, passed):
    checks.append({"check": name, "passed": bool(passed)})
    if not passed:
        (output / "ova-audit.json").write_text(json.dumps({"status": "failed", "checks": checks}, indent=2))
        raise SystemExit(name)


with tarfile.open(appliance, "r:") as archive:
    members = archive.getmembers()
    names = [member.name for member in members]
    check("unique archive paths", len(set(names)) == len(names))
    check("only safe regular files", all(
        member.isfile() and not PurePosixPath(member.name).is_absolute() and
        ".." not in PurePosixPath(member.name).parts and "\\" not in member.name and
        ":" not in member.name and member.size < 100 * 1024**3 for member in members
    ))
    descriptors = [name for name in names if name.endswith(".ovf")]
    manifests = [name for name in names if name.endswith(".mf")]
    disks = [name for name in names if name.endswith(".vmdk")]
    check("single VM descriptor and manifest", len(descriptors) == len(manifests) == 1 and len(disks) == 1)
    check("only descriptor, disk and manifest packaged", len(members) == 3)
    descriptor_bytes = archive.extractfile(descriptors[0]).read()
    check("bounded XML descriptor", len(descriptor_bytes) < 2_000_000 and b"<!DOCTYPE" not in descriptor_bytes.upper())
    descriptor = ET.fromstring(descriptor_bytes)
    local_name = lambda element: element.tag.rsplit("}", 1)[-1]
    check("one virtual system", sum(local_name(el) == "VirtualSystem" for el in descriptor.iter()) == 1)
    memory = [int(el.attrib["RAMSize"]) for el in descriptor.iter() if local_name(el) == "Memory"]
    processors = [int(el.attrib.get("count", "1")) for el in descriptor.iter() if local_name(el) == "CPU"]
    check("bounded declared VM resources", len(memory) == len(processors) == 1 and
          1024 <= memory[0] <= 8192 and 1 <= processors[0] <= 8)
    manifest = archive.extractfile(manifests[0]).read().decode("ascii")
    entries = re.findall(r"^(SHA1|SHA256|SHA512)\s*\((.+)\)\s*=\s*([0-9a-fA-F]+)\s*$", manifest, re.M)
    check("manifest covers descriptor and disk", {entry[1] for entry in entries} == {descriptors[0], disks[0]})
    for algorithm, name, expected in entries:
        actual = hashlib.file_digest(archive.extractfile(name), algorithm.lower()).hexdigest()
        check(f"manifest digest: {name}", actual == expected.lower())
    check("no host shared folders", not any(local_name(el) == "SharedFolder" for el in descriptor.iter()))
    check("no host device passthrough or automatic USB filters", not any(
        local_name(el) == "HostDrive" or
        (local_name(el) == "DeviceFilter" and el.attrib.get("active", "false").lower() == "true")
        for el in descriptor.iter()
    ))
    adapters = [el for el in descriptor.iter() if local_name(el) == "Adapter"
                and el.attrib.get("enabled", "false").lower() == "true"]
    # VirtualBox preserves inactive alternatives inside DisabledModes. Only a
    # direct mode child of an enabled adapter selects its active connection.
    active_modes = [el for adapter in adapters for el in adapter
                    if local_name(el) != "DisabledModes"]
    check("one enabled NAT adapter", len(adapters) == len(active_modes) == 1 and
          local_name(active_modes[0]) == "NAT")
    check("no active port forwarding", not any(
        local_name(el) == "Forwarding" for mode in active_modes for el in mode.iter()
    ))
    for feature in ("Clipboard", "DragAndDrop"):
        nodes = [el for el in descriptor.iter() if local_name(el) == feature]
        check(f"{feature} disabled", all(el.attrib.get("mode", "Disabled").lower() == "disabled" for el in nodes))
    check("remote display disabled", all(
        el.attrib.get("enabled", "false").lower() == "false" for el in descriptor.iter()
        if local_name(el) == "RemoteDisplay"
    ))
    for el in descriptor.iter():
        if local_name(el) in ("File", "Disk"):
            for key, value in el.attrib.items():
                if key.rsplit("}", 1)[-1] == "href":
                    check("disk reference is packaged locally", value in disks)
    # Extract only the already validated disk. No tar extraction of guest paths.
    with archive.extractfile(disks[0]) as source, (output / "guest.vmdk").open("wb") as destination:
        import shutil
        shutil.copyfileobj(source, destination)

(output / "ova-audit.json").write_text(json.dumps({
    "status": "passed", "checks": checks, "memory_mib": memory[0], "processors": processors[0],
}, indent=2) + "\n")
print(f"OVA archive and integration checks passed ({len(checks)} checks)")
