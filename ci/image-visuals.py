#!/usr/bin/python3
"""AI-Assisted. Initialize visual keys only in a newly constructed OS image.

The image builder invokes this after all upstream account setup. Package
upgrades never run it and no authentication or session policy is changed.
"""

import os
from pathlib import Path
import pwd
import shutil
import sys

sys.path.insert(0, "/usr/libexec/dhampiros-motion")
from motionlib import ini_set

visuals = {
    "lxqt/lxqt.conf": {"General": {
        "theme": "DhampirOS", "icon_theme": "DhampirOS", "icon_follow_color_scheme": "false",
    }},
    "pcmanfm-qt/lxqt/settings.conf": {"Desktop": {
        "Wallpaper": "/usr/share/backgrounds/dhampiros/nocturne-rider.jpg", "WallpaperMode": "zoom",
    }},
    "qterminal.org/qterminal.ini": {"General": {"colorScheme": "DhampirNocturne"}},
}

for name in ("user", "sysmaint"):
    account = pwd.getpwnam(name)
    home = Path(account.pw_dir)
    if account.pw_uid < 1000 or home != Path("/home") / name or home.is_symlink():
        raise SystemExit("Unexpected initial-account identity or home")
    config = home / ".config"
    files = []
    for relative, sections in visuals.items():
        path = config / relative
        # Do not follow a config link into a shared upstream or system file.
        for component in (config, *path.parents):
            if component == home.parent:
                break
            if component.is_symlink():
                raise SystemExit(f"Unexpected initial-profile symlink: {component}")
        if path.is_symlink():
            raise SystemExit(f"Unexpected initial-profile symlink: {path}")
        for section, values in sections.items():
            for key, value in values.items():
                ini_set(path, section, key, value)
        files.append(path)
    for relative in ("autostart/lxqt-desktop.desktop", "dhampiros/motion.conf"):
        source = Path("/etc/skel/.config") / relative
        target = config / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.is_symlink() or target.parent.is_symlink():
            raise SystemExit("Unexpected initial motion-profile symlink")
        shutil.copyfile(source, target)
        files.append(target)
    for path in files:
        os.chmod(path, 0o644)
        os.chown(path, account.pw_uid, account.pw_gid)
        for parent in path.parents:
            if parent == home:
                break
            os.chown(parent, account.pw_uid, account.pw_gid)
    print(f"Initialized Dhampir visual keys for image account {name}")
