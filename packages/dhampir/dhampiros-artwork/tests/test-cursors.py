#!/usr/bin/python3
# Copyright (C) 2026 potemkin666
# See the file COPYING for copying conditions.
# AI-Assisted

"""Check actual Xcursor frame tables, not just filenames or image previews."""

from collections import defaultdict
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[1] / 'assets/source-rootfs/usr/share'
for theme, animated in [('DhampirOS-Cursors', True), ('DhampirOS-Cursors-Still', False)]:
    for role in ('default', 'pointer', 'text', 'wait', 'progress', 'watch', 'left_ptr_watch'):
        data = (ROOT / f'icons/{theme}/cursors/{role}').read_bytes()
        magic, header, version, count = struct.unpack_from('<4sIII', data)
        assert magic == b'Xcur' and version == 65536
        frames = defaultdict(list)
        for index in range(count):
            kind, size, offset = struct.unpack_from('<III', data, header + index * 12)
            if kind == 0xfffd0002:
                fields = struct.unpack_from('<9I', data, offset)
                assert fields[4] > 0 and fields[5] > 0
                frames[size].append(fields[8])
        assert frames
        for size, delays in frames.items():
            busy = role in ('wait', 'progress', 'watch', 'left_ptr_watch')
            assert (len(delays) > 1) == (animated and busy), (theme, role, size, len(delays))
            if animated and busy:
                assert all(delay > 0 for delay in delays)

theme = ROOT / 'plymouth/themes/dhampiros'
assert len(list(theme.glob('throbber-*.png'))) == 36
for name in ('bullet.png', 'capslock.png', 'entry.png', 'keyboard.png', 'lock.png'):
    assert (theme / name).read_bytes().startswith(b'\x89PNG\r\n\x1a\n')
assert 'ModuleName=two-step' in (theme / 'dhampiros.plymouth').read_text()
print('Xcursor: busy roles animate only in Full; ordinary pointers and Still roles have one frame per size. Plymouth: 36 existing ring frames and native prompt assets.')
