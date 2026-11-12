#!/bin/bash

## Copyright (C) 2026 potemkin666
## See the file COPYING for copying conditions.
## AI-Assisted

## Full desktop image candidates, built only on a disposable Linux runner.

set -o errexit
set -o nounset
set -o pipefail
set -o errtrace
shopt -s inherit_errexit
shopt -s shift_verbose
export LC_ALL=C

if [ "${CI:-}" != true ] || [ "${GITHUB_REPOSITORY:-}" != potemkin666/DhampirOS ]; then
   printf '%s\n' 'This entry point requires the disposable DhampirOS Actions runner.' >&2
   exit 1
fi

case "${1:-}" in
   prepare)
      ./ci/free-disk
      git submodule update --init --recursive --jobs 8
      mkdir --parents -- "${RUNNER_TEMP}/dhampiros-image-evidence"
      git rev-parse HEAD > "${RUNNER_TEMP}/dhampiros-image-evidence/source-commit.txt"
      git submodule status --recursive > "${RUNNER_TEMP}/dhampiros-image-evidence/source-submodules.txt"
      sha256sum -- patches/dhampir-binary-eof.patch > "${RUNNER_TEMP}/dhampiros-image-evidence/source-patches.txt"
      ;;
   build)
      case "${IMAGE_TARGET:-}" in
         iso|virtualbox) ;;
         *) printf '%s\n' 'Unsupported image target.' >&2; exit 1 ;;
      esac
      ./docker/derivative-maker-docker-run -- ./ci/image-container.sh "${IMAGE_TARGET}"
      mkdir --parents -- artifacts
      cp -- "${RUNNER_TEMP}/dhampiros-image-evidence/source-commit.txt" artifacts/
      cp -- "${RUNNER_TEMP}/dhampiros-image-evidence/source-submodules.txt" artifacts/
      cp -- "${RUNNER_TEMP}/dhampiros-image-evidence/source-patches.txt" artifacts/
      find "${HOME}/binary_mnt" -type f \( -name '*.iso' -o -name '*.ova' -o -name '*buildinfo*' -o -name 'dm-source-state' -o -name '*packages*' \) -print
      ./ci/image-collect.py "${HOME}/binary_mnt" "${IMAGE_TARGET}"
      ;;
   *) printf '%s\n' 'Expected prepare or build.' >&2; exit 1 ;;
esac
