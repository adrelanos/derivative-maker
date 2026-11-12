# DhampirOS theme asset integration

## Tracked payload

`packages/dhampir/dhampiros-artwork/assets/source-rootfs/` is the complete
canonical payload as of 2026-10-28. A binary overlay archive is no longer
needed to build the package. It includes original generated fan artwork,
110 full-colour icons, 78 panel symbols, animated and still cursor themes,
LXQt/labwc resources, GRUB resources, Cinzel with its OFL, event sounds,
and 1080p/720p Nocturne motion loops. Source prompts, asset indices and
motion provenance are in `source-meta/`. Movie reference frames are excluded.

The optional legacy `rootfs-overlay.tar.gz` importer remains supported.
Installation extracts that first, then applies tracked files so an old
archive cannot replace the current defaults. The two Dhampir LXQt GUI
meta packages already depend on `dhampiros-artwork`.

## Desktop defaults and limits

New-user `/etc/skel` settings select the DhampirOS LXQt/icon themes,
Rainbound Hunter wallpaper in zoom mode, and DhampirNocturne QTerminal
colours. Existing user settings are not rewritten.

Phase 6 adds the separate `dhampiros-motion` runtime to both Dhampir GUI
meta packages. The pinned session is LXQt/Wayland/labwc. Its new-user LXQt
desktop loader places a local GTK layer-shell/GStreamer wallpaper below
PCManFM icons, with Full/Reduced/Off modes, visibility/accessibility checks,
cursor selection and the native rider still as fallback. X11 stays static.
See [MOTION.md](MOTION.md) for architecture, controls and validation limits.

The existing 36-frame boot ring is packaged as a Plymouth two-step theme,
with standard upstream prompt assets and their copyright. Activation is
pending encrypted/native boot validation; no boot hooks are added. GRUB
selection, greetd/wlgreet visuals and labwc effect settings remain static.
Authentication, hardening, session policy and kernel/network settings
remain upstream-controlled.

## Website

GitHub Pages serves the root on `master`. `index.html`, `pages.css`,
`showcase.css` and `showcase.js` provide a standalone browser preview at
`#icons`, with desktop windows, file browsing, a demonstration terminal,
appearance controls, login/setup studies and the full icon browser.
`showcase/visuals.json` indexes artwork shared with the Linux package.
There are no remote scripts, real shell execution or password collection.
The browser preview does not establish native boot or installation success.

## Basic validation

`python3 ci/check-showcase.py` checks local website references, matching
web/native icons, SVG parsing, cursor file headers and required resources.
`tests/test-theme-paths.sh` checks the package defaults and terminal palette
during the Debian build. `bash ci/check-artwork.sh` also checks JavaScript
syntax and builds this artwork package on Debian with debhelper installed;
the focused `local-artwork.yml` workflow runs it without building an ISO.
`local-motion.yml` builds all three changed packages from a clean Git archive
and runs the native headless compositor smoke. Its logind fixture is explicitly
separate from real login/logout and physical-device validation.
