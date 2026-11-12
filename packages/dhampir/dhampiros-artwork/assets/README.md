# DhampirOS artwork payload

`source-rootfs/` contains the full tracked artwork payload. It builds
without downloading an asset pack or providing a binary overlay archive.
The Rainbound Hunter still is the PCManFM-Qt default; the Nocturne WebM
loops are optional resources under `/usr/share/dhampiros/motion/`.

The legacy `rootfs-overlay.tar.gz` importer remains compatible with the
original pack (SHA256
`24def36263c99f32f57ba90e00efbb2292522972af928fce357c0ff2abb4da22`).
An optional archive is extracted first; tracked files are always applied
after it to preserve the current assets and new-user defaults.

Provenance and generation prompts are in `../source-meta/`; Cinzel's OFL
and the artwork notice are installed under `/usr/share/doc/dhampiros-artwork/`.
The loose movie-reference JPEGs are excluded from this package.
