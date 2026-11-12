# dhampir-branding

The visible DhampirOS identity: login banner and welcome text.

## What is here

| File | What it does |
|---|---|
| `etc/issue.dhampir` | Text shown on the login screen. |
| `etc/motd.dhampir` | Short message shown after login. |
| `etc/dhampir_version` | Version string for DhampirOS. |
| `debian/dhampir-branding.displace` | List of files that take the `.dhampir` version in place of the upstream one. |
| `debian/dhampir-branding.displace-extension` | The suffix (`.dhampir`) used by the displace list. |
| `debian/` | Debian packaging (control, rules, changelog, copyright, install). |

## How it fits

Kicksecure's `kicksecure-base-files` ships `/etc/issue.kicksecure` and `/etc/motd.kicksecure`. Its `debian/*.displace` list and `debian/*.displace-extension` (`.kicksecure`) say which files take the variant. We use the same mechanism with `.dhampir`. We do not delete, replace, or rename any Kicksecure package. This package depends on `kicksecure-base-files`.

## Not yet verified

- The swap is done by the Debian helper `config-package-dev` (`dh --with=config-package`), which is not in this repository.
- Whonix replaces `kicksecure-base-files` entirely to do this. We do not. Kicksecure and Dhampir both want `/etc/issue` and `/etc/motd`, so a conflict is possible. Must be tested before any build claim.
- The package has not been built or installed. Nothing here is verified to work.
- The GRUB boot menu and ISO splash are changed by the flavour settings, not by this package.
