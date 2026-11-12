#!/usr/bin/python3
# Copyright (C) 2026 potemkin666
# See the file COPYING for copying conditions.
# AI-Assisted

"""Local paths and policy shared by the Dhampir desktop and preference helper."""

import configparser
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile

SHARE = Path('/usr/share/dhampiros')
STILL = Path('/usr/share/backgrounds/dhampiros/nocturne-rider.jpg')
TRANSPARENT = SHARE / 'motion/transparent.png'
VIDEOS = {'full': SHARE / 'motion/nocturne-rider-1080p.webm',
          'light': SHARE / 'motion/nocturne-rider-720p-light.webm'}
PROFILE = 'dhampiros-motion'
CONFIG_HOME = Path(os.environ.get('XDG_CONFIG_HOME', str(Path.home() / '.config')))
CONFIG = CONFIG_HOME / 'dhampiros/motion.conf'


def atomic_text(path, text):
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix='.dhampiros-', dir=path.parent)
    try:
        with os.fdopen(descriptor, 'w', encoding='utf-8') as output:
            output.write(text)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def ini_set(path, section, key, value):
    """Change one visual key without discarding comments or unrelated settings."""
    lines = path.read_text(encoding='utf-8').splitlines() if path.exists() else []
    inside = False
    found_section = False
    for index, line in enumerate(lines):
        if line.strip().startswith('['):
            if inside:
                lines.insert(index, f'{key}={value}')
                break
            inside = line.strip() == f'[{section}]'
            found_section = found_section or inside
        elif inside and line.partition('=')[0].strip() == key:
            lines[index] = f'{key}={value}'
            break
    else:
        if not found_section:
            lines.extend(['', f'[{section}]'])
        lines.append(f'{key}={value}')
    atomic_text(path, '\n'.join(lines).lstrip('\n') + '\n')


def preferences():
    parser = configparser.ConfigParser(interpolation=None)
    try:
        parser.read(CONFIG, encoding='utf-8')
        mode = parser.get('Motion', 'Mode', fallback='full').lower()
        quality = parser.get('Motion', 'Quality', fallback='auto').lower()
        if mode not in ('full', 'reduced', 'off') or quality not in ('auto', 'full', 'light'):
            raise ValueError('Invalid motion preference')
        return mode, quality
    except (OSError, ValueError, configparser.Error):
        return 'off', 'light'


def session_backend(environment=None):
    env = os.environ if environment is None else environment
    desktop = env.get('XDG_CURRENT_DESKTOP', '').lower().split(':')
    if env.get('XDG_SESSION_TYPE') == 'wayland' and env.get('WAYLAND_DISPLAY') and 'labwc' in desktop:
        return 'wayland-layer-shell'
    return 'static'


def runtime_dir():
    base = Path(os.environ.get('XDG_RUNTIME_DIR', ''))
    if not base.is_absolute() or not base.is_dir() or base.stat().st_uid != os.getuid():
        raise RuntimeError('A user-owned XDG_RUNTIME_DIR is required')
    display = os.environ.get('WAYLAND_DISPLAY', os.environ.get('DISPLAY', 'none'))
    suffix = hashlib.sha256(display.encode()).hexdigest()[:12]
    path = base / f'dhampiros-motion-{suffix}'
    path.mkdir(mode=0o700, exist_ok=True)
    info = path.stat()
    if path.is_symlink() or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise RuntimeError('Unsafe motion runtime directory')
    return path


def take_lock(name):
    descriptor = os.open(runtime_dir() / name, os.O_RDWR | os.O_CREAT | os.O_CLOEXEC | os.O_NOFOLLOW, 0o600)
    stream = os.fdopen(descriptor, 'w')
    try:
        fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        stream.close()
        return None
    return stream


def request(action):
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.settimeout(3)
        client.connect(str(runtime_dir() / 'control.sock'))
        client.sendall(json.dumps({'action': action}).encode() + b'\n')
        return json.loads(client.recv(8192))


def wallpaper(path):
    return subprocess.run(['/usr/bin/pcmanfm-qt', '--profile', PROFILE,
                           '--set-wallpaper', str(path), '--wallpaper-mode', 'stretch' if path == TRANSPARENT else 'zoom'],
                          stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                          timeout=3, check=False).returncode == 0


def prepare_profile():
    target = CONFIG_HOME / 'pcmanfm-qt' / PROFILE / 'settings.conf'
    if not target.exists():
        source = CONFIG_HOME / 'pcmanfm-qt/lxqt/settings.conf'
        atomic_text(target, source.read_text(encoding='utf-8') if source.exists() else '[Desktop]\n')
        for layout in source.parent.glob('desktop-items*.conf'):
            shutil.copy2(layout, target.parent / layout.name)
    ini_set(target, 'Desktop', 'Wallpaper', str(STILL))
    ini_set(target, 'Desktop', 'WallpaperMode', 'zoom')


def select_cursor(animated):
    theme = 'DhampirOS-Cursors' if animated else 'DhampirOS-Cursors-Still'
    ini_set(CONFIG_HOME / 'lxqt/session.conf', 'Mouse', 'cursor_theme', theme)
    atomic_text(CONFIG_HOME / 'labwc/environment.d/90-dhampiros-motion.env', f'XCURSOR_THEME={theme}\n')
    # This reloads visual configuration, not the compositor or login session.
    if session_backend() != 'static' and os.environ.get('LABWC_PID', '').isdigit():
        subprocess.run(['/usr/bin/labwc', '--reconfigure'], timeout=3, check=False,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


class SessionPolicy:
    """Read existing logind and accessibility state; never change either."""

    def __init__(self):
        import gi
        gi.require_version('Gio', '2.0')
        from gi.repository import Gio, GLib
        self.Gio, self.GLib = Gio, GLib
        self.system = Gio.bus_get_sync(Gio.BusType.SYSTEM, None)
        self.user = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        result = self.system.call_sync('org.freedesktop.login1', '/org/freedesktop/login1',
                                      'org.freedesktop.login1.Manager', 'GetSessionByPID',
                                      GLib.Variant('(u)', (os.getpid(),)), None,
                                      Gio.DBusCallFlags.NONE, 1000, None)
        self.path = result.unpack()[0]
        source = Gio.SettingsSchemaSource.get_default()
        schema = source.lookup('org.gnome.desktop.interface', True) if source else None
        self.accessibility = Gio.Settings.new_full(schema, None, None) if schema and schema.has_key('enable-animations') else None

    def read(self):
        Gio, GLib = self.Gio, self.GLib
        context = GLib.MainContext.default()
        for _ in range(16):
            if not context.pending():
                break
            context.iteration(False)
        try:
            result = self.system.call_sync('org.freedesktop.login1', self.path,
                                          'org.freedesktop.DBus.Properties', 'GetAll',
                                          GLib.Variant('(s)', ('org.freedesktop.login1.Session',)), None,
                                          Gio.DBusCallFlags.NONE, 1000, None).unpack()[0]
            visible = result.get('Active') is True and result.get('LockedHint') is False and result.get('Remote') is False
        except GLib.Error:
            return False, True
        reduced = self.accessibility is not None and not self.accessibility.get_boolean('enable-animations')
        try:
            portal = self.user.call_sync('org.freedesktop.portal.Desktop', '/org/freedesktop/portal/desktop',
                                        'org.freedesktop.portal.Settings', 'Read',
                                        GLib.Variant('(ss)', ('org.freedesktop.appearance', 'reduced-motion')), None,
                                        Gio.DBusCallFlags.NO_AUTO_START, 500, None).unpack()[0]
            reduced = reduced or portal == 1
        except GLib.Error:
            pass  # Older portals do not expose reduced-motion.
        return visible, reduced
