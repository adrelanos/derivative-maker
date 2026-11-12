#!/bin/bash

## Copyright (C) 2026 potemkin666
## See the file COPYING for copying conditions.

## AI-Assisted

## Validate shared artwork and build only the small Debian artwork package.

set -o errexit
set -o nounset
set -o pipefail
set -o errtrace
shopt -s inherit_errexit
shopt -s shift_verbose
export LC_ALL=C

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd -- "${repo_root}"
python3 ci/check-showcase.py
node --check showcase.js
cd -- packages/dhampir/dhampiros-artwork
dpkg-buildpackage --no-sign --build=binary
artwork_version="$(dpkg-parsechangelog --show-field Version)"
dpkg-deb --field "../dhampiros-artwork_${artwork_version}_all.deb" Package Version Installed-Size
