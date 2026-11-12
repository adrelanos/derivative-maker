<div align="center">

<img src="showcase/assets/wallpapers/rider.webp" alt="Rainbound Hunter, original DhampirOS artwork" width="100%" />

<br>

<img src="showcase/assets/dhampiros-sigil.svg" alt="DhampirOS sigil" width="104" />

# DhampirOS

**A hardened Kicksecure derivative dressed for the night.**

<a href="https://potemkin666.github.io/DhampirOS/#icons"><b>✦ EXPLORE THE INTERACTIVE DESKTOP ✦</b></a>

<sub>Move windows, browse Files, change the wallpaper and explore the login, setup and icon previews. Original project artwork with a quiet 24-second motion loop. Interactive visual study; experimental alpha images are now available.</sub>

<br><br>

<img src="showcase/assets/hunter-crest.svg" alt="Hunter crest" width="82" />&nbsp;&nbsp;&nbsp;&nbsp;
<img src="showcase/assets/d-sword-monogram.svg" alt="D sword monogram" width="82" />&nbsp;&nbsp;&nbsp;&nbsp;
<img src="showcase/assets/avatar-hunter.svg" alt="Hunter avatar" width="82" />

</div>

---

<div align="center">

## Boot identity

<img src="showcase/assets/nocturne-boot-concept.svg" alt="DhampirOS Nocturne boot concept" width="96%" />

<sub>Supplied design asset. Concept artwork, not a runtime screenshot.</sub>

<br><br>

<img src="showcase/assets/unlock-panel.svg" alt="DhampirOS unlock panel artwork" width="62%" />

</div>

---

<div align="center">

## System icon language

<img src="showcase/assets/icon-browser.svg" alt="Browser icon" width="92" />
<img src="showcase/assets/icon-terminal.svg" alt="Terminal icon" width="92" />
<img src="showcase/assets/icon-files.svg" alt="Files icon" width="92" />
<img src="showcase/assets/icon-settings.svg" alt="Settings icon" width="92" />
<img src="showcase/assets/icon-lock.svg" alt="Lock icon" width="92" />
<img src="showcase/assets/icon-power.svg" alt="Power icon" width="92" />
<img src="showcase/assets/icon-disk.svg" alt="Disk icon" width="92" />
<img src="showcase/assets/icon-wifi.svg" alt="Wi-Fi icon" width="92" />

<sub>Examples from the supplied DhampirOS icon theme.</sub>

</div>

---

<div align="center">

## Cursor set

<img src="showcase/assets/cursor-default.svg" alt="Default cursor" width="54" />&nbsp;&nbsp;
<img src="showcase/assets/cursor-pointer.svg" alt="Pointer cursor" width="54" />&nbsp;&nbsp;
<img src="showcase/assets/cursor-text.svg" alt="Text cursor" width="54" />&nbsp;&nbsp;
<img src="showcase/assets/cursor-crosshair.svg" alt="Crosshair cursor" width="54" />&nbsp;&nbsp;
<img src="showcase/assets/cursor-grab.svg" alt="Grab cursor" width="54" />&nbsp;&nbsp;
<img src="showcase/assets/cursor-progress.svg" alt="Progress cursor" width="54" />&nbsp;&nbsp;
<img src="showcase/assets/cursor-wait.svg" alt="Wait cursor" width="54" />&nbsp;&nbsp;
<img src="showcase/assets/cursor-not-allowed.svg" alt="Not allowed cursor" width="54" />

</div>

---

<div align="center">

## Session language

<img src="showcase/assets/session-user.svg" alt="User session badge" width="208" />
<img src="showcase/assets/session-maintenance.svg" alt="Maintenance session badge" width="208" />
<br>
<img src="showcase/assets/session-live.svg" alt="Live session badge" width="208" />
<img src="showcase/assets/session-persistent.svg" alt="Persistent session badge" width="208" />

</div>

---

<div align="center">

## Installer stages

<table>
<tr>
<td align="center"><img src="showcase/assets/stage-welcome.svg" width="38" alt="Welcome"><br><sub>WELCOME</sub></td>
<td align="center">→</td>
<td align="center"><img src="showcase/assets/stage-storage.svg" width="38" alt="Storage"><br><sub>STORAGE</sub></td>
<td align="center">→</td>
<td align="center"><img src="showcase/assets/stage-users.svg" width="38" alt="Users"><br><sub>USERS</sub></td>
<td align="center">→</td>
<td align="center"><img src="showcase/assets/stage-install.svg" width="38" alt="Install"><br><sub>INSTALL</sub></td>
<td align="center">→</td>
<td align="center"><img src="showcase/assets/stage-finished.svg" width="38" alt="Finished"><br><sub>FINISHED</sub></td>
</tr>
</table>

</div>

---

<div align="center">

## System states

<img src="showcase/assets/state-no-network.svg" alt="No network state" width="170" />
<img src="showcase/assets/state-permission-denied.svg" alt="Permission denied state" width="170" />
<img src="showcase/assets/state-update-available.svg" alt="Update available state" width="170" />
<img src="showcase/assets/state-recovery.svg" alt="Recovery state" width="170" />

</div>

---

### Current state

| | Component | State |
|---|---|---|
| ✓ | `dhampir-lxqt` derivative flavour | wired |
| ✓ | `dhampiros-artwork` Debian package | builds |
| ✓ | LXQt / icon / wallpaper / QTerminal defaults | initialized in the image accounts |
| ✓ | runtime visual smoke test | native motion CI; real desktop captures reviewed |
| ◇ | GRUB theme enabled by default | pending runtime verification |
| ✓ | AMD64 ISO / OVA | built and checked for alpha 0.1.0 |
| ◇ | custom Dhampir kernel | not started |

> **Experimental alpha.** The full ISO and OVA reached the Dhampir desktop in network-isolated BIOS and UEFI KVM tests. The exact public OVA also passed reviewed BIOS/UEFI boots in VirtualBox 7.2.22 on Linux ([runtime evidence](https://github.com/potemkin666/DhampirOS/releases/download/v0.1.0-alpha.1/virtualbox-runtime-report.json)). These images are for isolated VM testing. Unresolved upstream tracker findings and other verification limits remain; this is not a security certification or a production-ready release.

Build details live in [`agents/BUILD.md`](agents/BUILD.md). DhampirOS is an independent project based on Kicksecure/Debian and is not endorsed by the Kicksecure or Whonix developers.

See [`COPYING`](COPYING) for licensing; individual bundled assets retain their applicable notices and provenance.
