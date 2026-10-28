<div align="center">

<img src="packages/dhampir/dhampiros-artwork/assets/source-rootfs/usr/share/backgrounds/dhampiros/dhampiros-minimal.svg" alt="DhampirOS Nocturne wallpaper" width="100%" />

<br>

<img src="packages/dhampir/dhampiros-artwork/assets/source-rootfs/usr/share/dhampiros/brand/dhampiros-sigil.svg" alt="DhampirOS sigil" width="118" />

# DhampirOS

**A hardened Kicksecure derivative dressed for the night.**

<a href="https://potemkin666.github.io/DhampirOS/"><img src="branding/readme/visual-preview-button.svg" alt="Open visual preview" width="300" /></a>

<br>
<br>

<img src="branding/readme/status-badges.svg" alt="Debian, Kicksecure, LXQt, VirtualBox, pre-alpha unverified image" width="92%" />

</div>

---

<div align="center">

## Visual direction

<img src="branding/readme/desktop-preview.svg" alt="DhampirOS Nocturne desktop design preview" width="96%" />

<sub>Design preview only. Not a runtime screenshot.</sub>

<br><br>

<img src="branding/readme/palette-strip.svg" alt="DhampirOS Nocturne colour palette" width="96%" />

</div>

---

<div align="center">

## Architecture

<img src="branding/readme/architecture.svg" alt="DhampirOS architecture from Debian through Kicksecure to Dhampir ISO and OVA" width="96%" />

</div>

---

<table>
<tr>
<td align="center" width="33%"><b>HARDENED BASE</b><br><br>Kicksecure security packages and hardening remain the foundation.</td>
<td align="center" width="33%"><b>DHAMPIR LXQt</b><br><br>Nocturne LXQt defaults, icon identity and QTerminal styling.</td>
<td align="center" width="33%"><b>CUSTOM ARTWORK</b><br><br>Dhampir wallpaper, sigil, GRUB theme and visual system.</td>
</tr>
</table>

---

### Current state

| | Component | State |
|---|---|---|
| ✓ | `dhampir-lxqt` derivative flavour | wired |
| ✓ | `dhampiros-artwork` Debian package | wired |
| ✓ | LXQt / icon / wallpaper / terminal defaults | implemented for new users |
| ◇ | GRUB theme | shipped, not yet enabled by default |
| ◇ | `Dhampir.ova` | not yet built |
| ◇ | `Dhampir.iso` | not yet built |
| ◇ | custom Dhampir kernel | not started |

> **Pre-alpha:** no complete Dhampir ISO or OVA has yet been built and runtime-verified end to end.

### Build

Build notes and exact commands live in [`agents/BUILD.md`](agents/BUILD.md).

DhampirOS preserves Kicksecure's security layer and adds its own derivative, packaging, defaults and visual identity on top. It is an independent project and is not made by or endorsed by the Kicksecure or Whonix developers.

### Licence

See [`COPYING`](COPYING). Upstream files retain their original licences and notices.
