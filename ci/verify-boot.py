#!/usr/bin/python3
"""AI-Assisted. Capture network-isolated BIOS/UEFI boots without root backdoors."""

from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import threading
import time

from PIL import Image

image = Path(sys.argv[1]).resolve()
target = sys.argv[2]
report = Path(sys.argv[3]).resolve()
resources = {"memory_mib": 4096, "processors": 2}
if target == "virtualbox":
    resources = json.loads((report / "ova-audit.json").read_text())

# Probe acceleration without booting any guest or requiring elevated access.
# A runner without usable KVM keeps the slower software-emulation lane.
accelerator = "tcg"
cpu = "max"
probe_error = ""
try:
    probe = subprocess.run([
        "qemu-system-x86_64", "-machine", "q35,accel=kvm", "-cpu", "host",
        "-m", "128", "-nodefaults", "-nic", "none", "-display", "none", "-S", "-qmp", "stdio",
    ], input='{"execute":"qmp_capabilities"}\n{"execute":"quit"}\n',
        text=True, capture_output=True, timeout=15, check=False)
    if probe.returncode == 0:
        accelerator, cpu = "kvm", "host"
    else:
        probe_error = probe.stderr[-2000:]
except subprocess.TimeoutExpired:
    probe_error = "KVM startup probe timed out"
captures = (20, 90, 240) if accelerator == "kvm" else (
    (20, 90, 240, 480, 720) if target == "iso" else (20, 90, 240, 480))
physical_mib = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") // 1024**2
workers = 2 if (os.cpu_count() or 1) >= 4 and physical_mib >= 2 * resources["memory_mib"] + 4096 else 1
stop = threading.Event()
(report / "boot-environment.json").write_text(json.dumps({
    "accelerator": accelerator, "cpu_model": cpu, "capture_seconds": captures,
    "memory_mib": resources["memory_mib"], "processors": resources["processors"],
    "parallel_firmwares": workers,
    "kvm_probe_error": probe_error,
    "network": "disabled", "disk_writes": "disposable snapshot",
}, indent=2) + "\n")

def capture_boot(firmware):
    evidence = report / firmware
    evidence.mkdir()
    if Path("/dev/kvm").exists():
        device = Path("/dev/kvm").stat()
        (evidence / "kvm-device.json").write_text(json.dumps({
            "device_uid": device.st_uid, "device_gid": device.st_gid,
            "device_mode": oct(device.st_mode & 0o7777), "process_uid": os.getuid(),
            "process_groups": os.getgroups(),
        }, indent=2) + "\n")
    qmp_path = evidence / "qmp.sock"
    command = ["qemu-system-x86_64", "-machine", f"q35,accel={accelerator}", "-cpu", cpu,
               "-m", str(resources["memory_mib"]), "-smp", str(resources["processors"]),
               "-nic", "none", "-display", "none",
               "-qmp", f"unix:{qmp_path},server=on,wait=off", "-no-reboot", "-snapshot",
               "-serial", f"file:{evidence / 'serial.log'}"]
    if firmware == "uefi":
        code = Path("/usr/share/OVMF/OVMF_CODE_4M.fd")
        variables = evidence / "OVMF_VARS.fd"
        shutil.copyfile("/usr/share/OVMF/OVMF_VARS_4M.fd", variables)
        command += ["-drive", f"if=pflash,format=raw,unit=0,readonly=on,file={code}",
                    "-drive", f"if=pflash,format=raw,unit=1,file={variables}"]
    if target == "iso":
        command += ["-cdrom", str(image), "-boot", "order=d"]
    else:
        command += ["-drive", f"file={image},format=vmdk,if=virtio"]
    with (evidence / "qemu.log").open("wb") as log:
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
        connection = socket.socket(socket.AF_UNIX)
        connection.settimeout(20)
        try:
            for _ in range(40):
                if process.poll() is not None:
                    raise RuntimeError("QEMU exited before startup")
                if qmp_path.exists():
                    break
                time.sleep(0.5)
            connection.connect(str(qmp_path))
            stream = connection.makefile("rwb", buffering=0)
            json.loads(stream.readline())

            def qmp(execute, arguments=None):
                stream.write((json.dumps({"execute": execute, "arguments": arguments or {}}) + "\n").encode())
                while True:
                    response = json.loads(stream.readline())
                    if "error" in response:
                        raise RuntimeError(str(response["error"]))
                    if "return" in response:
                        return response["return"]

            def screenshot(name):
                ppm = evidence / f"{name}.ppm"
                qmp("screendump", {"filename": str(ppm)})
                with Image.open(ppm) as frame:
                    frame.save(evidence / f"{name}.png")
                ppm.unlink()

            def key(value):
                qmp("human-monitor-command", {"command-line": f"sendkey {value} 40"})

            def type_command(command):
                codes = {" ": "spc", "-": "minus", "/": "slash", ".": "dot", "|": "shift-backslash"}
                for character in command:
                    key(codes.get(character, character))
                    time.sleep(.08)
                key("ret")

            qmp("qmp_capabilities")
            start = time.monotonic()
            for elapsed in captures:
                if stop.wait(max(0, start + elapsed - time.monotonic())):
                    raise RuntimeError("Boot capture cancelled")
                screenshot(f"boot-{elapsed}")
                if elapsed == 20:
                    qmp("human-monitor-command", {"command-line": "sendkey ret"})
                else:
                    qmp("human-monitor-command", {"command-line": "sendkey shift"})
            shutil.copyfile(evidence / f"boot-{captures[-1]}.png", evidence / "desktop-capture.png")
            # Normal unprivileged GUI interaction after the unchanged boot
            # evidence. No root shell, serial login or image policy override.
            key("meta_l-ret")
            stop.wait(12)
            key("alt-f10")
            stop.wait(3)
            for name, command in (
                ("motion-status", "dhampiros-motion status"),
                ("user-services", "systemctl --user --failed --no-pager"),
                ("desktop-processes", "pgrep -afu user lxqt"),
                ("desktop-log", "journalctl --user -b -n 16 --no-pager"),
            ):
                key("ctrl-l")
                type_command(command)
                stop.wait(6)
                screenshot(name)
            key("ctrl-alt-f2")
            stop.wait(4)
            screenshot("console-state")
            qmp("quit")
        finally:
            connection.close()
            if process.poll() is None:
                process.terminate()
            process.wait(timeout=20)


pool = ThreadPoolExecutor(max_workers=workers)
try:
    for completed in pool.map(capture_boot, ("bios", "uefi")):
        pass
finally:
    stop.set()
    pool.shutdown(wait=True, cancel_futures=True)
