#!/usr/bin/python3
# Copyright (C) 2026 potemkin666
# See the file COPYING for copying conditions.
# AI-Assisted

"""CI-only protocol lock on a disposable headless compositor. No PAM changes."""

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
gi.require_version('GtkSessionLock', '0.1')
from gi.repository import Gdk, GLib, Gtk, GtkSessionLock

Gtk.init(None)
assert GtkSessionLock.is_supported()
lock = GtkSessionLock.prepare_lock()
lock.connect('locked', lambda *_: print('locked', flush=True))
lock.connect('finished', lambda *_: Gtk.main_quit())
lock.lock_lock()
display = Gdk.Display.get_default()
windows = []
for index in range(display.get_n_monitors()):
    window = Gtk.Window()
    window.add(Gtk.Label(label='DhampirOS headless protocol-lock test'))
    lock.new_surface(window, display.get_monitor(index))
    window.show_all()
    windows.append(window)


def unlock():
    lock.unlock_and_destroy()
    display.sync()
    Gtk.main_quit()
    return GLib.SOURCE_REMOVE


GLib.timeout_add_seconds(14, unlock)
Gtk.main()
