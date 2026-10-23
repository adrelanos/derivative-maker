#!/usr/bin/env bash
set -e

# Automatically fall back to native runner path if GITHUB_WORKSPACE environment variable is populated
WORKSPACE_DIR="${GITHUB_WORKSPACE:-$(pwd)}"

# Ensure workspace locations exist cleanly
rm -rf "${WORKSPACE_DIR}/extracted-binaries" "${WORKSPACE_DIR}/release-staging"
mkdir -p "${WORKSPACE_DIR}/extracted-binaries" "${WORKSPACE_DIR}/release-staging"

echo "=== 2. Streaming build artifacts out of QEMU guest ==="
ssh -i ./id_ed25519 -p 2222 -o StrictHostKeyChecking=no debian@127.0.0.1 "tar -cf - -C /home/debian/binary_mnt ." | tar -xf - -C "${WORKSPACE_DIR}/extracted-binaries"

cd "${WORKSPACE_DIR}/extracted-binaries"

echo "=== Fix ownership of container-created build artifacts ==="
sudo chown -R runner:runner .

echo "=== 3. Filtering and Staging Core Release Images ==="
find . -type f  -name "Kicksecure*.xz" -o -name "Whonix*.xz" -o -name "*.iso" -o -name "*.raw" -o -name "*.qcow2" -o -name "*.ova" -o -name "*.asc" -o -name "*.sig" -o -name "*.torrent"  | while read -r FILE; do
  echo "Staging core asset: $(basename "$FILE")"
  mv "$FILE" "${WORKSPACE_DIR}/release-staging/"
done

cd "${WORKSPACE_DIR}/release-staging"

echo "=== 4. Generating Cryptographic Checksums ==="
sha256sum * > SHA256SUMS || true
cat SHA256SUMS

echo "=== 5. Dynamic Asset Inspection and Splitting Loop ==="
find . -maxdepth 1 -type f ! -name "SHA256SUMS" | while read -r ASSET; do
  FILE_SIZE_MB=$(du -m "$ASSET" | cut -f1)
  
  if [ "$FILE_SIZE_MB" -gt 2000 ]; then
    echo "Asset '$ASSET' ($FILE_SIZE_MB MB) crosses the 2GB endpoint threshold."
    echo "Dynamically splitting into safe 1500M chunks..."
    split -b 1500M "$ASSET" "${ASSET}.part_"
    rm "$ASSET"
  else
    echo "Asset '$ASSET' ($FILE_SIZE_MB MB) is safely below the 2GB threshold. Leaving whole."
  fi
done

echo "=== 6. Establishing Dynamic Release Tags and Notes Matrix ==="
case "$BUILD_FLAVOR" in
  "kicksecure-lxqt") FLAVOR_NAME="Kicksecure-LXQt" ;;
  "kicksecure-cli")  FLAVOR_NAME="Kicksecure-CLI" ;;
  "whonix-gateway-xfce") FLAVOR_NAME="Whonix-Gateway-XFCE" ;;
  "whonix-workstation-xfce") FLAVOR_NAME="Whonix-Workstation-XFCE" ;;
  *) FLAVOR_NAME="Derivative-Image" ;;
esac

if [ "$BUILD_ARCH" = "amd64" ]; then
  ARCH_NAME="Intel_AMD64"
else
  ARCH_NAME="$BUILD_ARCH"
fi

# Map dynamic table true/false configurations with requested color indicators
if [ "$ALLOW_UNCOMMITTED" = "true" ]; then
  GIT_CLEAN_STR="⚠️ Allowing Uncommitted"
else
  GIT_CLEAN_STR="✅ Clean Tree"
fi

if [ "$ALLOW_UNFROZEN" = "true" ]; then
  FROZEN_SRC_STR="⚠️ False (Using Unfrozen Repo)"
else
  FROZEN_SRC_STR="✅ True (Using Safe Frozen Repo)"
fi

# Clean up tags and safe presentation fallbacks
RELEASE_TAG="${FLAVOR_NAME}-${CHOSEN_VERSION}.${ARCH_NAME}.${BUILD_TARGET}.${BUILD_TYPE}"
echo "Target Release Tag Resolved: $RELEASE_TAG"

[ -n "$FLAVOR_META_PACKAGES" ] && META_ROW="| **Custom Meta Packages Added** | \`$FLAVOR_META_PACKAGES\` |"
[ -n "$INSTALL_PACKAGE_LIST" ] && PKG_ROW="| **Appended Package List** | \`$INSTALL_PACKAGE_LIST\` |"
[ -n "$DERIVATIVE_APT_OPTS" ] && APT_ROW="| **Custom APT Repository Flags** | \`$DERIVATIVE_APT_OPTS\` |"

{
  echo "### 🛠️ Build Manifest"
  echo ""
  echo "| Parameter | Build Option |"
  echo "| :--- | :--- |"
  echo "| **Flavor Configuration** | \`$BUILD_FLAVOR\` |"
  echo "| **Target Architecture** | \`$BUILD_ARCH\` |"
  echo "| **Output Format Target** | \`$BUILD_TARGET\` |"
  echo "| **System Footprint Type** | \`$BUILD_TYPE\` |"
  echo "| **Repository Freshness** | \`$BUILD_FRESHNESS\` |"
  echo "| **Container Build Engine** | \`$ENGINE\` |"  
  echo "| **Frozen Sources Status** | $FROZEN_SRC_STR |"
  echo "| **Enforcing Clean Git** | $GIT_CLEAN_STR |"
  echo "| **Release Version Tag** | \`$CHOSEN_VERSION\` |"
  [ -n "$META_ROW" ] && echo "$META_ROW"
  [ -n "$PKG_ROW" ] && echo "$PKG_ROW"
  [ -n "$APT_ROW" ] && echo "$APT_ROW"
  echo ""
  echo "---"
  echo "Automated system deployment binaries generated successfully. Verify your downloads using the attached SHA256SUMS file."
} > release_notes.md

echo "=== Final Layout Verification ==="
ls -lh

echo "=== 7. Publishing Clean Master Release Bundle via GitHub API ==="
gh release create "$RELEASE_TAG" \
  --title "$RELEASE_TAG" \
  --notes-file release_notes.md \
  --draft=false \
  --prerelease=false \
  ./*
