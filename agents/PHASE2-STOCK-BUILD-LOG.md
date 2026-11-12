# Phase 2 stock Kicksecure build log

AI reference record. Not end-user documentation.

## Environment

- Host: Ubuntu 24.04.3, x86_64, 2 CPUs, 7 GB RAM.
- Disk: `/dev/vdb` 19 GB, about 8.6 GB free.
- Docker daemon running.
- Repo: `derivative-maker` submodules all initialised with
  `git submodule update --init --recursive --progress --jobs=4` (exit 0).

## Chosen target

- Flavour: `kicksecure-lxqt` (GUI, VirtualBox). Defined in
  `variables.d/20_flavor-resolve.bsh` (lines 161-181).
- Command used:

  ```
  ./docker/derivative-maker-docker-run -- ./derivative-maker --flavor kicksecure-lxqt --target virtualbox
  ```

## Attempt 1 (failed during Docker image build, before any Kicksecure build step)

The Docker image build step failed at `apt-get update` inside `docker/Dockerfile`:

```
Ign:1 https://snapshot.debian.org/archive/debian/20261002T104754Z trixie InRelease
Err:1 https://snapshot.debian.org/archive/debian/20261002T104754Z trixie InRelease
  Temporary failure resolving 'snapshot.debian.org'
W: Failed to fetch .../trixie/InRelease  Temporary failure resolving 'snapshot.debian.org'
E: Unable to locate package ...
ERROR: failed to build: ... exit code: 100
```

Cause: the Dockerfile pins apt to `snapshot.debian.org`
(`build_sources/debian_stable_frozen_direct_clearnet.sources.in`). The
host cannot resolve that name:

- `getent hosts snapshot.debian.org` returns nothing.
- `curl https://snapshot.debian.org/archive/debian/` returns HTTP 000.
- `getent hosts deb.debian.org` resolves fine.

Status: not worked around. Changing the pinned apt source would alter the
upstream build inputs. Needs a decision from the user.

## Not yet reached

- Free-space gate: `build-steps.d/1100_sanity-tests` `check-sufficient-disk`
  requires `dist_build_min_free_gib` (20 GiB). About 8.6 GiB is free, so the
  build is expected to stop there too.
- ISO target: not attempted.
