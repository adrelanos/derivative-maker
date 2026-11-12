#!/usr/bin/env python3

# Copyright (C) 2026 potemkin666
# See the file COPYING for copying conditions.
# AI-Assisted

"""Basic integrity check for the shared website and Linux artwork assets."""

import hashlib
import json
import re
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PACKAGE = REPO / "packages/dhampir/dhampiros-artwork"
ROOTFS = PACKAGE / "assets/source-rootfs"
manifest = json.loads((REPO / "showcase/visuals.json").read_text(encoding="utf-8"))


def asset_path(value):
    path = (REPO / value).resolve()
    if not path.is_relative_to(REPO) or not path.is_file() or not path.stat().st_size:
        raise ValueError(f"Missing or invalid local asset: {value}")
    return path


class PageAssets(HTMLParser):
    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if key in ("src", "data-src", "href") and value and not value.startswith(("#", "https://", "http://")):
                asset_path(value)


PageAssets().feed((REPO / "index.html").read_text(encoding="utf-8"))
assert len(manifest["wallpapers"]) == 4
assert len(manifest["icons"]) == 110
assert len({icon["id"] for icon in manifest["icons"]}) == 110
for scene in manifest["wallpapers"]:
    asset_path(scene["src"])
    asset_path(scene["thumb"])
for icon in manifest["icons"]:
    website = asset_path(icon["src"])
    installed = ROOTFS / f"usr/share/icons/DhampirOS/scalable/{icon['category']}/{icon['id']}.svg"
    assert installed.is_file(), f"Icon missing from Linux package: {icon['id']}"
    assert hashlib.sha256(website.read_bytes()).digest() == hashlib.sha256(installed.read_bytes()).digest(), icon["id"]
for name in ("webm", "mp4"):
    asset_path(manifest["motion"][name])
for css_file in ("pages.css", "showcase.css"):
    for value in re.findall(r"url\(['\"]?([^)'\"]+)", (REPO / css_file).read_text(encoding="utf-8")):
        if not value.startswith("data:"):
            asset_path(value)

svg_files = [*(REPO / "showcase/assets").rglob("*.svg"), *ROOTFS.rglob("*.svg")]
for path in svg_files:
    assert ET.parse(path).getroot().tag == "{http://www.w3.org/2000/svg}svg", path
for theme in ("DhampirOS-Cursors", "DhampirOS-Cursors-Still"):
    cursors = ROOTFS / f"usr/share/icons/{theme}/cursors"
    for role in ("default", "pointer", "text", "wait", "progress"):
        assert (cursors / role).read_bytes()[:4] == b"Xcur", f"Invalid cursor: {theme}/{role}"
for value in (
    "usr/share/backgrounds/dhampiros/nocturne-rider.jpg",
    "usr/share/dhampiros/motion/nocturne-rider-1080p.webm",
    "usr/share/dhampiros/motion/nocturne-rider-720p-light.webm",
    "usr/share/fonts/truetype/dhampiros/Cinzel.ttf",
    "usr/share/doc/dhampiros-artwork/Cinzel-OFL.txt",
):
    assert (ROOTFS / value).is_file(), f"Missing installed resource: {value}"

print(f"Artwork integrity: 110 matching Linux/web icons, 4 scenes, {len(svg_files)} valid SVGs, 2 cursor themes, motion and font assets.")
