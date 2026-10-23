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

# Force the framework's internal 'variables' loader
# to ingest your custom identity across all execution sub-shells.
mkdir -p buildconfig.d
printf 'signing_key_email="%s"\n' "${DEBEMAIL}" > buildconfig.d/40_signing_key.conf

echo "=========================================================="
echo " STEP 3: Executing Native Key & Policy Provisioning"
echo "=========================================================="
# This natively generates the key inside Sequoia and authorizes it in the policy
./help-steps/signing-key-create

echo "=========================================================="
echo " STEP 4: Configuring Native Local Git Identity"
echo "=========================================================="
git config --local user.name "${DEBFULLNAME}"
git config --local user.email "${DEBEMAIL}"

echo "=========================================================="
echo " STEP 5: Synchronizing Policy & Goodlisting the Handover Commit"
echo "=========================================================="
# Sync the derived policy into working tree
cp /home/malcolm/buildconfig.d/openpgp-policy.toml ./buildconfig.d/openpgp-policy.toml

# Stage the updated metadata configuration files
git add buildconfig.d/openpgp-policy.toml
git add buildconfig.d/40_signing_key.conf

# Create the standard baseline handover transition commit
git commit -m "Transfer project ownership to Local Builder under secure local keys" --allow-empty

# Capture the final commit hash ID
# and inject it cleanly into the trusted policy layout array.
FINAL_COMMIT_SHA="$(git rev-parse HEAD)"
sq-git policy goodlist \
  --policy-file buildconfig.d/openpgp-policy.toml \
  "${FINAL_COMMIT_SHA}"

echo "=========================================================="
echo " STEP 6: Resolving Version Tag & Executing Signing Loop"
echo "=========================================================="
# Dynamically extract the true branch semantic build target version string
if [ -f "dist_build_version" ]; then
    TARGET_VERSION="$(cat dist_build_version)"
elif [ -f "packages/kicksecure/kicksecure-base-files/usr/share/kicksecure/version" ]; then
    TARGET_VERSION="$(cat packages/kicksecure/kicksecure-base-files/usr/share/kicksecure/version)"
else
    # Isolate only the clean numerical dot sequence from the closest tag milestone
    RAW_VERSION="$(git describe --tags --abbrev=0 2>/dev/null || echo "18.2.1.9")"
    TARGET_VERSION="$(echo "${RAW_VERSION}" | grep -oE '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+' || echo "18.2.1.9")"
fi

echo "--> Target release version string resolved to: ${TARGET_VERSION}"

# Execute the native parent and submodule recursive cryptographical signing loops
./help-steps/sign-and-tag "${TARGET_VERSION}"

echo "=========================================================="
echo " SUCCESS: Native project handover complete!"
echo "=========================================================="
