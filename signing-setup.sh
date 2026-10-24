#!/usr/bin/env bash
set -x
set -e
set -o pipefail

echo "=========================================================="
echo " STEP 1: Installing Upstream Cryptographic Packages"
echo "=========================================================="
sudo apt update
sudo apt install -y sq sqop sequoia-git signify-openbsd moreutils git

echo "=========================================================="
echo " STEP 2: Instantiating Upstream Configuration Overrides"
echo "=========================================================="
export DEBFULLNAME="tabletseeker"
export DEBEMAIL="tabletseeker@github.com"
export CI="true"

mkdir -p buildconfig.d
printf 'signing_key_email="%s"\n' "${DEBEMAIL}" > buildconfig.d/40_signing_key.conf

echo "=========================================================="
echo " STEP 3: Executing Native Key & Policy Provisioning"
echo "=========================================================="
./help-steps/signing-key-create

echo "=========================================================="
echo " STEP 4: Configuring Native Local Git Identity"
echo "=========================================================="
git config --local user.name "${DEBFULLNAME}"
git config --local user.email "${DEBEMAIL}"

echo "=========================================================="
echo " STEP 5: Synchronizing Policy & Goodlisting Handover Target"
echo "=========================================================="
# FIX: Dynamically instantiate a fresh policy file if none exists yet
if [ ! -f "buildconfig.d/openpgp-policy.toml" ]; then
    touch buildconfig.d/openpgp-policy.toml
fi

# Stage current state (captures your modified configuration files)
git add buildconfig.d/openpgp-policy.toml
git add buildconfig.d/40_signing_key.conf

# NOTE: This commit will automatically include your pre-staged 'git add -A' changes
# (the 3 executable files and modified signing-setup.sh) into the handover timeline!
git commit -m "Transfer project ownership to ${DEBEMAIL} under secure local keys" --allow-empty

# Capture this SHA and inject it cleanly into the tracking policy
FINAL_COMMIT_SHA="$(git rev-parse HEAD)"
sq-git policy goodlist \
  --policy-file buildconfig.d/openpgp-policy.toml \
  "${FINAL_COMMIT_SHA}"

# Stage the modified policy and cleanly amend it directly into the handover commit
git add buildconfig.d/openpgp-policy.toml
git commit --amend --no-edit

# Recapture the finalized, amended SHA for strict policy alignment
FINAL_COMMIT_SHA="$(git rev-parse HEAD)"

echo "=========================================================="
echo " STEP 6: Resolving Version Tag & Executing Signing Loop"
echo "=========================================================="
if [ -f "dist_build_version" ]; then
    TARGET_VERSION="$(cat dist_build_version)"
else
    RAW_VERSION="$(git describe --tags --abbrev=0 2>/dev/null || echo "18.2.1.9")"
    TARGET_VERSION="$(echo "${RAW_VERSION}" | grep -oE '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+' || echo "18.2.1.9")"
fi

echo "--> Target release version string resolved to: ${TARGET_VERSION}"

# Execute signing loops over the complete, clean repository state
./help-steps/sign-and-tag "${TARGET_VERSION}"

echo "=========================================================="
echo " SUCCESS: Native project handover complete!"
echo "=========================================================="

