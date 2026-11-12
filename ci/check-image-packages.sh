#!/bin/bash

## Copyright (C) 2026 potemkin666
## See the file COPYING for copying conditions.
## AI-Assisted

## Exercise the same isolated source-package boundary as the full builder.

set -o errexit
set -o nounset
set -o pipefail
set -o errtrace
shopt -s inherit_errexit
shopt -s shift_verbose
export LC_ALL=C

[ "${CI:-}" = true ]
package_repo_root="$(pwd -P)"
package_scratch="$(mktemp --directory --tmpdir="${RUNNER_TEMP}" dhampiros-package-check.XXXXXXXX)"
mkdir --parents -- "${package_scratch}/apt/conf"
cp -- aptrepo_local/dhampir/conf/distributions "${package_scratch}/apt/conf/"
reprepro --basedir "${package_scratch}/apt" export local
git -c safe.directory="${package_repo_root}" archive HEAD packages/dhampir | tar --extract --directory "${package_scratch}"
for package_name in dhampir-branding dhampir-meta-packages dhampiros-artwork dhampiros-motion; do
   cd -- "${package_scratch}/packages/dhampir/${package_name}"
   package_version="$(dpkg-parsechangelog --show-field Version)"
   package_upstream="${package_version%-*}"
   package_isolated="${package_scratch}/isolated/${package_name}/${package_name}-${package_upstream}"
   mkdir --parents -- "${package_isolated}"
   cp --archive -- ./. "${package_isolated}/"
   cd -- "${package_isolated}"
   tar --create --xz --exclude=./debian --file="../${package_name}_${package_upstream}.orig.tar.xz" .
   dpkg-buildpackage --no-sign --build=full
   package_lint_status=0
   package_lint_output="$(lintian --allow-root --quiet --pedantic --info --display-info \
      --suppress-tags missing-tests-control \
      --suppress-tags systemd-service-file-missing-documentation-key \
      --suppress-tags orig-tarball-missing-upstream-signature \
      --suppress-tags no-manual-page \
      --suppress-tags maintainer-script-ignores-errors \
      "../${package_name}_${package_version}_amd64.changes" 2>&1)" || package_lint_status="$?"
   if [ "${package_lint_status}" -ne 0 ] || [ -n "${package_lint_output}" ]; then
      printf '%s\n' "${package_lint_output}" >&2
      exit 1
   fi
done
