# Phase 6 native motion

## Session evidence and scope

The master's pinned Kicksecure sources select LXQt on Wayland with labwc:

- `kicksecure-meta-packages` 56c753dd79f2713a7bffcce4fac6d11e451c57e0:
  `dist-nonqubes-gui-all` depends on labwc; `dist-nonqubes-gui-lxqt`
  depends on lxqt-wayland-session, greetd, wlgreet and swaylock.
- `desktop-config-dist` a6b8e62dc13119840df6d6a127c1fbbca40c9f9c:
  `start-lxqt-session` runs startlxqtwayland and its LXQt session config
  selects `compositor=labwc`.
- `lxqt-wayland-session` 85cdf13c661453913e1d501b4815567f3214aec9:
  startlxqtwayland runs `labwc -m -S lxqt-session` and exports
  `XDG_CURRENT_DESKTOP=LXQt:labwc:wlroots`.

These are source-level findings, not evidence of a booted DhampirOS image.
X11 is deliberately a static fallback rather than an untested xwinwrap hack.

## Runtime

`dhampiros-motion` is separate from the artwork package and is a dependency
of both Dhampir GUI meta packages. New-user XDG autostart overrides only
the standard LXQt desktop module, preserving the upstream session launcher.
Existing custom desktop loaders are never overwritten by the enable helper.

The session-owned manager starts one GTK3 layer-shell background process
before PCManFM creates its desktop surface. GStreamer uses an explicit
`filesrc -> matroskademux -> vp9dec -> videoconvert -> appsink` pipeline.
Its one-sample sink and one pending GTK redraw share the newest RGB frame
across outputs, with no growing frame queue. GTK/Cairo draws that frame on
the background surface. There are no URL inputs,
network sources, audio elements, ambient sound or user-supplied commands.
GTK layer-shell is packaged by Debian trixie; no new compositor is introduced.

PCManFM 2.1 or newer supports a transparent wallpaper over another Wayland
background app. A dedicated `dhampiros-motion` profile starts from the user's
LXQt settings and desktop icon layouts and keeps its own later changes.
The regular `lxqt` profile is preserved. The underlay never takes keyboard
or pointer input. When
starting motion after the desktop exists, only its desktop surface is
re-mapped above the video; file-manager windows remain in the same process.
Qt Wayland, SVG and layer-shell plugins are explicit runtime dependencies.
The transparent underlay is a PNG, so its alpha does not depend on SVG loading.

Backend detection requires Wayland, a Wayland display and the labwc desktop
identity. The child also checks actual layer-shell support. Other sessions,
missing support, missing media and playback errors select the rider still.
1080p is attempted first, followed by the existing lighter 720p loop, then
static. A failed quality is not retried until an explicit preference/restart
change. There is no automatic service restart policy or crash loop.

## Control and lifetime

`~/.config/dhampiros/motion.conf` is an INI file, never sourced or evaluated:

```ini
[Motion]
Mode=full
Quality=auto
```

The local helper accepts `mode full`, `mode reduced`, `mode off`,
`quality auto|full|light`, `status`, `restart`, `stop`, and `enable`.
`enable` installs the user desktop-loader override; it takes effect on the
next login. It preserves an existing unrelated override. `mode off` disables
motion without removing the functioning PCManFM desktop.

Full selects the video and busy cursor frames. Reduced/Off use the native
still and the still cursor theme. Existing accessibility takes precedence:
the XDG portal reduced-motion preference, GNOME's enable-animations setting
when its schema exists, and GTK's enable-animations flag are read. No
accessibility or authentication setting is changed. LXQt/labwc have no
general clean fade/transition setting here, so existing static feedback is
retained rather than adding effects or another compositor.

The manager reads logind Active/LockedHint/Remote values. Unknown visibility,
inactive and locked sessions retain the still and stop the player. GTK frame
callback inactivity also releases the decoder when all outputs are obscured;
occasional still redraws let it restart when visible, outside the GTK paint
callback. The headless protocol-lock test exercises this separately from
the logind fixture. Real greetd/PAM lock and physical outputs remain separate
validation targets.

Locks in the user-owned XDG runtime directory prevent duplicate managers and
players. The controller owns only its own child process groups. SIGTERM and
logout close them; the player watches its control pipe and restores the
native still if the manager dies abruptly. A replacement controller can reattach to its surviving
PCManFM process using a user-private lease checked against UID, command line,
process group and process start time, preserving open file-manager windows.
Decoder thread count is two, priority is lowered, and auto mode falls back
after sustained CPU use over
half one core or RSS over 384 MiB. A light player exceeding the same budget
falls back to static. These are conservative runtime guardrails, not measured
hardware guarantees.

## Cursor, boot, login and sound

The helper updates only the LXQt Mouse/cursor_theme visual key and a
Dhampir user labwc environment fragment. New/reloaded clients use the
selected animated or still theme. Existing clients can retain a cached
cursor until restart/login. Ordinary pointers have one frame per size;
wait/progress/watch aliases animate only in the animated theme.

The existing 36-frame boot ring is packaged as a Plymouth two-step theme.
Prompt images are unmodified Debian Plymouth assets with copyright tracked
in `source-meta/phase6-motion.json` and the installed Plymouth-copyright.
The standard two-step plugin remains responsible for prompt presentation.
There are no Plymouth activation hooks, kernel command-line changes or
initramfs rebuilds. The pinned desktop dependencies do not establish safe
Plymouth activation on the encrypted boot path, so activation remains pending.

greetd/wlgreet configuration and session-selection logic stay untouched.
Login/lock visuals remain static. Existing event sounds remain unchanged
and are never triggered by wallpaper lifecycle or preference polling.

## Validation boundary

Basic policy, path, configuration-preservation, duplicate-lock, Xcursor frame
and boot-resource tests are in the two packages. `local-motion.yml` builds
artwork, motion and meta packages from a clean Git archive and extracts the
two runtime payloads into a disposable Debian container. Its unprivileged
headless labwc smoke uses actual GTK layer-shell, GStreamer, PCManFM and
screenshots, with an explicitly labelled private-bus logind fixture.

Reference run [40683699961](https://github.com/potemkin666/DhampirOS/actions/runs/40683699961)
passed on 2026-10-28 at runtime commit `bc9191c`:

- All three changed Debian source packages built from a clean Git archive,
  producing artwork, motion and two GUI meta-package binaries.
- Native screenshots changed while playing and stayed identical in Reduced.
  A complete 24-second loop finished; Off left no wallpaper player.
- Duplicate launches retained one owner/player. Lock and inactive logind
  hints stopped it. Existing GNOME accessibility reduction stopped playback
  and restoring that preference restarted it.
- An actual ext-session-lock surface on headless labwc stopped decoding;
  native screenshots changed again after unlock. This is a compositor
  protocol test, not a PAM or greetd authentication test.
- Killing the owner restored the still and removed its player. A replacement
  owner reattached to the same PCManFM PID; normal shutdown cleaned up.
- Auto quality selected the 720p fallback under the software-rendering CPU
  budget. After a completed loop, one sample was 14.71% of one CPU core and
  87.63 MiB player RSS. The three-second locked sample used 0.0% of one core.
  These are CI observations, not promises about physical hardware.

The workflow artifact contains the four Debian packages, raw resource JSON
and native screenshots. Xcursor frame tables and mode-driven theme selection
are checked; application-specific cursor refresh still needs real LXQt testing.
No actual DhampirOS boot, encrypted boot, greetd login/logout, physical GPU,
monitor hotplug or real authentication-based screen lock has been verified.
GitHub Pages remains a browser simulation and is unchanged by Phase 6.

References:

- https://github.com/lxqt/pcmanfm-qt/wiki#using-desktop-under-wayland
- https://packages.debian.org/trixie/gir1.2-gtklayershell-0.1
- https://gstreamer.freedesktop.org/documentation/app/appsink.html
- https://flatpak.github.io/xdg-desktop-portal/docs/doc-org.freedesktop.portal.Settings.html
- https://labwc.github.io/labwc-config.5.html
