# Image release engineering notes (AI-Assisted)

No downloadable images had been published when this work started on
2026-10-28. The website catalogue deliberately remains `building/pending`
until real release assets and their verification evidence exist. Never set
`published/passed` merely because scripts parse, packages build or an Actions
job is green.

## Build and trust boundary

`local-images.yml` first checks all four isolated Dhampir source packages with
the full builder's lintian flags, rejecting any diagnostic output, including
informational and pedantic tags. The full `dhampir-lxqt` ISO and
VirtualBox targets then run on disposable amd64 Linux runners, using the
upstream pinned Docker build environment and pinned submodules. Guest APT
freshness is `current`; signed upstream update repositories remain enabled.
There is no SMBIOS debug reader, serial-login test backdoor, unsigned-source
verification bypass, tiny CI flavor or dry-run image.

The upstream EOF-newline checker mistakes binary artwork for text. The
tracked `patches/dhampir-binary-eof.patch` corrects only that binary handling;
the Unicode, modeline, whitespace and clean-source checks remain active.
The patch is applied in the disposable build checkout before signing and is
recorded with the original commit, original submodule pins and patch digest.
It does not change the checked-in upstream gitlink.

The upstream CI signing helpers mint an ephemeral build identity and amend
their disposable checkout. These are internal consistency signatures, not
official Kicksecure release signatures or a long-term offline Dhampir key.
GitHub OIDC image attestations independently identify this repository,
workflow and original source commit. Attestations establish origin, not the
absence of vulnerabilities. Never upload private CI signing keys.

Package-specific lintian overrides cover exact `/etc/skel` visual defaults
for newly created distribution accounts. They do not modify existing homes.
Other packaging findings still fail closed. The full builder's existing
suppression of manual-page checks is retained; end-user feature documentation
remains part of the human wiki process.

The upstream package builder publishes its local APT repository only after
all packages build, so there are no cross-component build dependencies. Motion
policy tests remain self-contained; installed artwork paths are checked by
the native runtime integration and independently in both finished images.

## Independent verification

`local-image-verification.yml` waits for a successful owner-repository image
run, verifies its workflow identity and source ancestry, downloads the exact
artifacts and checks their SHA-256 and size before inspecting them.

The verifier executes no tools from the guest filesystem. It inspects ISO
squashfs or read-only libguestfs mounts, validates the OVA tar paths and
manifest, and checks NAT with clipboard, drag/drop, host shares and remote
display disabled. The offline report checks required security packages,
authenticated APT updates, inherited GRUB hardening, no debug root shell,
cloned host keys, unique builder identifiers and builder credentials. Debian's vulnerability
report is retained and available security fixes block release.

The first real-image audit exposed incorrect verifier assumptions. The ISO's
`config.cfg` sets up GRUB; kernel arguments live in `grub.cfg`. Check every
live kernel entry there. `dist-base-files` at `056f49a680adeefac` deliberately
ships the shared privacy ID `b08dfa6083e7567a1921a715000001fb` for both system
and D-Bus. Require that exact value rather than claiming ID regeneration.
`repository-dist` at `911537d7e1b0143d` generates authenticated public sources
on first boot. Verify its enabled service, exact stable-codename arguments,
unconsumed initializer marker, and pinned initializer/generator/key bytes.
Do not mistake the missing pre-boot sources file for disabled updates.

The first successful image candidates are not a release: their initial
accounts retained upstream visual defaults. The image-only
`4305_apply-dhampir-visual-defaults` step runs after account setup and changes
only named visual INI keys and the desktop-module autostart entry. It is not
a package maintainer script and never runs during installed-system upgrades.
The finished-image audit now requires the initial account profiles as well as
the installed theme resources. Both `user` and `sysmaint` retain upstream
authentication and session policy.

Debsecan compares Tor's vendor revision `0.4.9.14-1~d13.trixie+1` with sid's
`0.4.9.14-1`. The upstream 0.4.9.14 changelog explicitly fixes
TROVE-2026-062, TROVE-2026-064 and TROVE-2026-067. The narrow assessment requires
that exact installed version, exactly those three fixable findings, and the
installed upstream changelog proof. New findings, older versions and missing
proof remain blocked. Raw tracker findings are always retained; other upstream
findings are not silently waived. This is an isolated-VM experimental alpha,
not a production-security claim.

Boot captures probe unprivileged KVM and otherwise use TCG. Independent BIOS
and UEFI guests may run concurrently only within the runner memory guard.
Software-emulated live ISO boots get a longer observation window and 4 GiB
RAM; appliance tests retain the declared appliance resources. Review the
actual `desktop-capture.png` and `boot-environment.json`; a completed capture
command alone does not prove a working desktop.

BIOS and UEFI QEMU boots have no network, use snapshot disks and capture
screens without enabling root serial login. The screenshots require actual
review. `review-status.json` explicitly says this; it is not a release
approval. Physical hardware and actual VirtualBox runtime compatibility
remain separate checks. Debian tracker coverage does not cover every custom
package or guarantee safety.

## Publication requirements

Publish only actual reviewed images, as an experimental prerelease, with
SHA-256 sums, exact source/build links, package inventories, vulnerability
findings, bounded verification results and remaining limitations. GitHub
Release assets must be below its per-file limit; inspect actual sizes before
choosing delivery. Keep binaries out of Git. Enable the website catalogue
only after both public assets and report/checksum links work.

The catalogue validates all metadata before enabling either image link;
missing metadata or an unexpected download host leaves both disabled.
Local browser checks covered desktop and mobile layouts, pending catalogue,
valid catalogue, unsafe URL rejection and the existing interactive preview.
Use a static server with correct MIME types and byte-range support for the
video preview. The Windows Python stock server produced incomplete image
loads; a Node static/range server passed with the same unchanged images.

## First reviewed full image pair

Build `40751365822`, source `db5152d816559ed2365f81486c4106b17f20af83`,
produced the actual 0.1.0-alpha.1 AMD64 pair. Verification `40762495912`
passed 70 ISO and 64 appliance filesystem checks, the appliance archive
checks, origin attestations and the current available-security-fix gate.
The final scan required no vulnerability exclusions. All four original KVM
desktop captures were viewed and show the Dhampir artwork. The original ISO
BIOS capture is copied byte-for-byte into the website's expandable preview.

TCG caused severe guest CPU stalls and misleading blank captures. KVM
availability alone was insufficient: device permissions changed after the
initial probe. The disposable verifier now uses a runner-owned KVM node and
a scoped udev rule; no guest security setting is changed. Normal-user GUI
diagnostics are captured after the untouched boot evidence. Their first typed
command can lose a prefix while the terminal maximizes; that automation
artifact is not evidence of a missing installed command.

## Subsequent actual VirtualBox runtime review

On 2026-10-29, the original captures from successful run `40782455595`
were visually reviewed. Verifier source `c778b0cd1a2a3f33023a7348aeb79726c489a357`
downloaded the exact public alpha OVA, checked its existing reviewed hash,
archive manifest, source ancestry and GitHub build attestation, then imported
it into actual VirtualBox `7.2.22r175245` on disposable Linux hosted runners.
Both BIOS and EFI reached the LXQt desktop with the original Dhampir artwork
and the upstream setup-wizard completion message. Declared resources remained
2 GiB RAM and 3 vCPUs. No image bytes or guest authentication policy changed.

Before guest execution, all eight network adapters, clipboard, drag/drop,
USB, audio and remote display were disabled. No shared folder was present.
Guest writes went to fresh disposable imports. The host had kernel
`7.0.0-1017-azure`; its Ubuntu VirtualBox 7.0.16 DKMS package could not build,
so the verifier uses the pinned authenticated Oracle host package documented
in `github-actions-security.md`. The first import attempt only displayed its
license requirement; the completed unattended import explicitly accepts it.

`release-reviews/v0.1.0-alpha.1-virtualbox.json` records the exact image,
environments, original final capture hashes and all evidence file hashes.
The public release adds `virtualbox-runtime-report.json`,
`DhampirOS-VirtualBox-review.zip` and `VIRTUALBOX-SHA256SUMS`; their anonymous
URLs and sizes were checked, and public JSON/checksum bytes matched locally.
The original report, checksum file, images and original review remain intact
as their historical verification snapshot. This supplement supersedes only
the original report's statement that actual VirtualBox runtime was untested.

This does not verify Windows/macOS VirtualBox hosts, physical hardware,
Secure Boot, network/update operation, complete application use or the full
login/lock lifecycle. It is not a fresh vulnerability scan. Original unresolved
tracker findings, coverage limits and experimental-alpha restrictions remain.
