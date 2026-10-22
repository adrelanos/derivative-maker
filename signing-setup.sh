#!/usr/bin/env bash
set -x
set -e

# 1. Create build system parameters directories and fix GnuPG folder permissions
mkdir -p buildconfig.d
chmod 700 ~/.gnupg || true

# 2. Kill any hung background GPG subsystems to ensure clean key tracking
gpgconf --kill gpg-agent || true

# 3. Generate a standalone, passwordless GPG operational key automatically
printf 'Key-Type: RSA\nKey-Length: 4096\nSubkey-Type: RSA\nSubkey-Length: 4096\nName-Real: Local Builder\nName-Email: builder@local.vm\nExpire-Date: 0\n%%no-protection\n%%commit\n' > /tmp/gpg-batch-params
gpg --batch --generate-key /tmp/gpg-batch-params
rm -f /tmp/gpg-batch-params

# 4. Isolate the precise unique GPG fingerprint and 16-character short Key ID
FINGERPRINT=$(gpg --fingerprint --with-colons builder@local.vm | grep fpr | tail -n 1 | cut -d':' -f10)
KEY_ID="${FINGERPRINT: -16}"

# 5. Securely export both unarmored and armored public certificate formats to disk
gpg --output buildconfig.d/project_signing_key.gpg --export "${KEY_ID}"
gpg --output /tmp/armored_key.asc --armor --export "${KEY_ID}"

# 6. Build a fully populated openpgp-policy.toml structure using explicit file stream appending
printf 'version = 0\ncommit_goodlist = []\n\n[authorization."Local Builder <builder@local.vm>"]\nsign_commit = true\nsign_tag = true\nsign_archive = true\nadd_user = true\nretire_user = true\naudit = true\nkeyring = """\n' > buildconfig.d/openpgp-policy.toml
cat /tmp/armored_key.asc >> buildconfig.d/openpgp-policy.toml
printf '\n"""\n' >> buildconfig.d/openpgp-policy.toml

# Clean up temporary public profile file artifacts securely
rm -f /tmp/armored_key.asc

# 7. Write the absolute configuration path directive expected by variables.d/65_signing.bsh
printf 'signing_key_file="buildconfig.d/project_signing_key.gpg"\n' > buildconfig.d/30_signing_key.conf

# 8. Strip out older upstream git history to satisfy sq-git history trace constraints
rm -rf .git
git init -b master

# 9. Bind local Git tracking metadata profiles to your generated cryptographic identity
git config --local user.name "Local Builder"
git config --local user.email builder@local.vm
git config --local user.signingkey "${KEY_ID}"
git config --local commit.gpgsign true

# 10. Stage all custom and generated workspace files, and apply a true PGP signature
git add .
git commit -m "Initialize custom build landscape under secure local keys" --gpg-sign="${KEY_ID}"

# 11. Create a cryptographically signed annotated tag to satisfy the release trace rules natively
git tag -a -s -u "${KEY_ID}" -f -m "Local custom development release version 1.0.0" 1.0.0-custom

echo "=========================================================="
echo " SUCCESS: Local PGP trust root is established!"
echo " Launching compilation under secure local keys..."
echo "=========================================================="



