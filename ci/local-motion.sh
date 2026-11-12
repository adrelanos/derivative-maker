#!/bin/bash

## Copyright (C) 2026 potemkin666
## See the file COPYING for copying conditions.

## AI-Assisted

## Build from a clean Git archive and run the isolated native desktop smoke.

set -o errexit
set -o nounset
set -o pipefail
set -o errtrace
shopt -s inherit_errexit
shopt -s shift_verbose
export LC_ALL=C

if [ "${CI:-}" != 'true' ]; then
   printf '%s\n' 'This smoke extracts packages into its disposable CI container; refusing a developer host.' >&2
   exit 1
fi

motion_repo_root="$(pwd -P)"
motion_build_dir="$(mktemp --directory --tmpdir="${RUNNER_TEMP}" dhampiros-motion.XXXXXXXX)"
git -c safe.directory="${motion_repo_root}" archive HEAD packages/dhampir | tar --extract --directory "${motion_build_dir}"
for motion_package in dhampiros-artwork dhampiros-motion dhampir-meta-packages; do
   cd -- "${motion_build_dir}/packages/dhampir/${motion_package}"
   dpkg-buildpackage --no-sign --build=binary
done
cd -- "${motion_repo_root}"
install --directory --owner=nobody --group=nogroup --mode=0755 artifacts
cp -- "${motion_build_dir}"/packages/dhampir/*.deb artifacts/
for motion_deb in "${motion_build_dir}"/packages/dhampir/dhampiros-artwork_*.deb "${motion_build_dir}"/packages/dhampir/dhampiros-motion_*.deb; do
   dpkg-deb --extract "${motion_deb}" /
done
shellcheck ci/local-motion.sh
bash -n ci/local-motion.sh
./ci/check-showcase.py
runuser --user nobody -- dbus-run-session -- ./ci/motion-smoke.py "${motion_repo_root}/artifacts" > artifacts/motion-smoke.json
