#!/usr/bin/python3
# Copyright (C) 2026 potemkin666
# See the file COPYING for copying conditions.
# AI-Assisted

"""Small policy/path checks; the native compositor smoke test runs in CI."""

import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import unittest

PACKAGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE / 'lib'))
import motionlib


class PolicyTests(unittest.TestCase):
    def test_session_detection(self):
        self.assertEqual(motionlib.session_backend({'XDG_SESSION_TYPE': 'wayland', 'WAYLAND_DISPLAY': 'wayland-1', 'XDG_CURRENT_DESKTOP': 'LXQt:labwc:wlroots'}), 'wayland-layer-shell')
        for env in ({'DISPLAY': ':0'}, {'XDG_SESSION_TYPE': 'x11', 'WAYLAND_DISPLAY': 'wayland-1'}, {'XDG_SESSION_TYPE': 'wayland', 'WAYLAND_DISPLAY': 'wayland-1', 'XDG_CURRENT_DESKTOP': 'GNOME'}):
            self.assertEqual(motionlib.session_backend(env), 'static')

    def test_preferences_are_data_and_invalid_is_off(self):
        with tempfile.TemporaryDirectory() as temporary:
            previous = motionlib.CONFIG
            motionlib.CONFIG = Path(temporary) / 'motion.conf'
            try:
                for mode in ('full', 'reduced', 'off'):
                    motionlib.ini_set(motionlib.CONFIG, 'Motion', 'Mode', mode)
                    self.assertEqual(motionlib.preferences()[0], mode)
                motionlib.CONFIG.write_text('[Motion]\nMode=$(touch bad)\n')
                self.assertEqual(motionlib.preferences(), ('off', 'light'))
                self.assertFalse((Path(temporary) / 'bad').exists())
            finally:
                motionlib.CONFIG = previous

    def test_visual_key_preserves_session_settings(self):
        with tempfile.TemporaryDirectory() as temporary:
            file = Path(temporary) / 'session.conf'
            file.write_text('[General]\ncompositor=labwc\n# keep me\n[Mouse]\ncursor_size=32\n')
            motionlib.ini_set(file, 'Mouse', 'cursor_theme', 'DhampirOS-Cursors-Still')
            self.assertIn('compositor=labwc\n# keep me', file.read_text())
            self.assertIn('cursor_size=32', file.read_text())
            self.assertIn('cursor_theme=DhampirOS-Cursors-Still', file.read_text())

    def test_singleton_lock_releases(self):
        with tempfile.TemporaryDirectory() as temporary:
            previous = os.environ.get('XDG_RUNTIME_DIR')
            os.environ['XDG_RUNTIME_DIR'] = temporary
            try:
                first = motionlib.take_lock('test.lock')
                self.assertIsNotNone(first)
                self.assertIsNone(motionlib.take_lock('test.lock'))
                first.close()
                again = motionlib.take_lock('test.lock')
                self.assertIsNotNone(again)
                again.close()
            finally:
                if previous is None:
                    os.environ.pop('XDG_RUNTIME_DIR', None)
                else:
                    os.environ['XDG_RUNTIME_DIR'] = previous

    def test_loader_contract(self):
        self.assertIn('X-LXQt-Module=true', (PACKAGE / 'data/lxqt-desktop.desktop').read_text())
        self.assertNotIn('Restart=', (PACKAGE / 'data/lxqt-desktop.desktop').read_text())


if __name__ == '__main__':
    unittest.main()
