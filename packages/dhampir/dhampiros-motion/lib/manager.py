#!/usr/bin/python3
# Copyright (C) 2026 potemkin666
# See the file COPYING for copying conditions.
# AI-Assisted

"""A session-owned desktop module. No service, network or restart daemon."""

import argparse
import json
import os
from pathlib import Path
import select
import signal
import socket
import subprocess
import sys
import time

from motionlib import (CONFIG, CONFIG_HOME, PROFILE, STILL, TRANSPARENT, VIDEOS,
                       SessionPolicy, atomic_text, ini_set, preferences,
                       prepare_profile, request, runtime_dir, select_cursor,
                       session_backend, take_lock, wallpaper)


def terminate(child):
    if child is None:
        return
    if child.poll() is None:
        try:
            os.killpg(child.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            child.wait(timeout=3)
        except subprocess.TimeoutExpired:
            os.killpg(child.pid, signal.SIGKILL)
            child.wait(timeout=2)
    # Reap any remaining plugin-scanner children in our own process group.
    try:
        os.killpg(child.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass


def desktop_identity(pid):
    if not isinstance(pid, int) or pid < 2:
        return None
    try:
        proc = Path(f'/proc/{pid}')
        fields = (proc / 'stat').read_text().rpartition(') ')[2].split()
        arguments = (proc / 'cmdline').read_bytes().split(b'\0')
        if (proc.stat().st_uid == os.getuid() and fields[0] != 'Z'
                and os.getpgid(pid) == pid and arguments[0] == b'/usr/bin/pcmanfm-qt'
                and b'--profile' in arguments and PROFILE.encode() in arguments):
            return fields[19]
    except (OSError, IndexError, ValueError):
        pass
    return None


class ExistingDesktop:
    """Reattach only to our surviving desktop, with PID reuse checks."""

    def __init__(self, pid, start):
        self.pid, self.start = pid, start

    def poll(self):
        return None if desktop_identity(self.pid) == self.start else 0

    def wait(self, timeout):
        deadline = time.monotonic() + timeout
        while self.poll() is None:
            if time.monotonic() >= deadline:
                raise subprocess.TimeoutExpired('owned desktop', timeout)
            time.sleep(.05)
        return 0


def existing_desktop():
    try:
        lease = json.loads((runtime_dir() / 'desktop.json').read_text())
        if lease.get('start') and desktop_identity(lease.get('pid')) == lease['start']:
            return ExistingDesktop(lease['pid'], lease['start'])
    except (OSError, ValueError, TypeError):
        pass
    return None


class Desktop:
    def __init__(self):
        self.player = self.desktop = None
        self.backend = session_backend()
        self.mode, self.quality = preferences()
        self.current_quality = None
        self.failed = set()
        self.reason = 'static'
        self.running = True
        self.cursor = None
        self.resource_sample = None
        self.hot_samples = 0
        self.cpu_percent = 0.0
        self.rss_mib = 0.0
        self.completed_loops = 0
        self.access_reduced = None
        try:
            self.policy = SessionPolicy()
        except Exception as error:
            print(f'dhampiros-motion: session visibility unavailable: {error}', file=sys.stderr)
            self.policy = None

    def status(self):
        return {'mode': self.mode, 'backend': self.backend, 'state': self.reason,
                'quality': self.current_quality, 'manager_pid': os.getpid(),
                'player_pid': self.player.pid if self.player and self.player.poll() is None else None,
                'desktop_pid': self.desktop.pid if self.desktop and self.desktop.poll() is None else None,
                'cpu_one_core_percent': round(self.cpu_percent, 2), 'rss_mib': round(self.rss_mib, 2),
                'completed_loops': self.completed_loops,
                'fallback': str(STILL)}

    def stop_player(self):
        if self.player:
            # Restore the opaque desktop before removing the layer underneath.
            try:
                wallpaper(STILL)
            except (OSError, subprocess.TimeoutExpired):
                pass
            try:
                self.player.stdin.write('stop\n')
                self.player.stdin.flush()
                self.player.wait(timeout=2)
            except (OSError, subprocess.TimeoutExpired):
                terminate(self.player)
            try:
                self.player.stdin.close()
            except OSError:
                pass
            self.player.stdout.close()
            self.player = None
        self.current_quality = None
        self.resource_sample = None
        self.hot_samples = 0

    def start_player(self, quality):
        child = subprocess.Popen([sys.executable, str(Path(__file__).with_name('player.py')), quality],
                                 stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1,
                                 start_new_session=True)
        try:
            ready, _, _ = select.select([child.stdout], [], [], 10)
            if not ready or child.stdout.readline().strip() != 'ready':
                raise RuntimeError('The native layer did not become ready')
            self.player = child
            self.completed_loops = 0
            self.current_quality = quality
            self.reason = 'playing'
            if self.desktop:
                if not wallpaper(TRANSPARENT):
                    raise RuntimeError('Could not select the transparent desktop layer')
                # Re-map only our desktop surface above the wallpaper, preserving icons.
                self.desktop_command('--desktop-off')
                self.desktop_command('--desktop')
            return True
        except (OSError, RuntimeError, subprocess.TimeoutExpired) as error:
            print(f'dhampiros-motion: {quality} fallback: {error}', file=sys.stderr)
            terminate(child)
            self.player = None
            self.current_quality = None
            self.failed.add(quality)
            return False

    def desktop_command(self, argument):
        subprocess.run(['/usr/bin/pcmanfm-qt', '--profile', PROFILE, argument], timeout=3,
                       stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    def resource_check(self):
        if not self.player or self.player.poll() is not None:
            return
        try:
            fields = Path(f'/proc/{self.player.pid}/stat').read_text().rpartition(') ')[2].split()
            ticks = int(fields[11]) + int(fields[12])
            self.rss_mib = int(fields[21]) * os.sysconf('SC_PAGE_SIZE') / (1024 * 1024)
            now = time.monotonic()
            if self.resource_sample:
                self.cpu_percent = 100 * (ticks - self.resource_sample[1]) / os.sysconf('SC_CLK_TCK') / (now - self.resource_sample[0])
                self.hot_samples = self.hot_samples + 1 if self.cpu_percent > 50 else 0
            self.resource_sample = now, ticks
            if self.rss_mib > 384 or (self.quality == 'auto' and self.hot_samples >= 3):
                self.failed.add(self.current_quality)
                self.reason = 'resource-fallback'
                self.stop_player()
        except (OSError, ValueError, IndexError):
            pass

    def reconcile(self):
        previous_mode, previous_quality = self.mode, self.quality
        self.mode, self.quality = preferences()
        if previous_mode != self.mode or previous_quality != self.quality:
            self.stop_player()
            self.failed.clear()
        visible, reduced = self.policy.read() if self.policy else (False, True)
        if self.access_reduced != reduced:
            self.failed.clear()
            self.access_reduced = reduced
        animated_cursor = self.mode == 'full' and not reduced
        if self.cursor != animated_cursor:
            try:
                select_cursor(animated_cursor)
                self.cursor = animated_cursor
            except (OSError, subprocess.TimeoutExpired) as error:
                print(f'dhampiros-motion: cursor selection unchanged: {error}', file=sys.stderr)
        allowed = self.mode == 'full' and not reduced and visible and self.backend != 'static'
        if not allowed:
            self.stop_player()
            self.reason = 'off' if self.mode == 'off' else 'reduced' if reduced or self.mode == 'reduced' else 'session-hidden' if not visible else 'unsupported-session'
            return
        if self.player and self.player.poll() is not None:
            self.failed.add(self.current_quality)
            self.stop_player()
        if not self.player:
            candidates = ['light'] if self.quality == 'light' else ['full', 'light']
            for quality in candidates:
                if quality not in self.failed and VIDEOS[quality].is_file() and self.start_player(quality):
                    break
            if not self.player:
                self.reason = 'backend-unavailable-static'

    def run(self):
        lock = take_lock('manager.lock')
        if lock is None:
            print('DhampirOS desktop motion is already running.')
            return 0
        prepare_profile()
        self.desktop = existing_desktop()
        if self.desktop:
            wallpaper(STILL)
        control_path = runtime_dir() / 'control.sock'
        control_path.unlink(missing_ok=True)
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(str(control_path))
        os.chmod(control_path, 0o600)
        server.listen(4)
        signal.signal(signal.SIGTERM, self.shutdown)
        signal.signal(signal.SIGINT, self.shutdown)
        signal.signal(signal.SIGHUP, self.shutdown)
        try:
            self.reconcile()
            if self.player:
                ini_set(CONFIG_HOME / 'pcmanfm-qt' / PROFILE / 'settings.conf', 'Desktop', 'Wallpaper', str(TRANSPARENT))
            if self.desktop is None:
                self.desktop = subprocess.Popen(['/usr/bin/pcmanfm-qt', '--profile', PROFILE, '--desktop', '--daemon-mode'],
                                                start_new_session=True, stdin=subprocess.DEVNULL)
                atomic_text(runtime_dir() / 'desktop.json', json.dumps({'pid': self.desktop.pid,
                                                                      'start': desktop_identity(self.desktop.pid)}))
            next_policy = time.monotonic() + 2
            while self.running and self.desktop.poll() is None:
                readers = [server] + ([self.player.stdout] if self.player else [])
                ready, _, _ = select.select(readers, [], [], .5)
                if server in ready:
                    connection, _ = server.accept()
                    with connection:
                        connection.settimeout(1)
                        try:
                            command = json.loads(connection.recv(4096)).get('action')
                            if command == 'restart':
                                self.stop_player()
                                self.failed.clear()
                            elif command == 'stop':
                                ini_set(CONFIG, 'Motion', 'Mode', 'off')
                            self.reconcile()
                            connection.sendall(json.dumps(self.status()).encode())
                        except (ValueError, OSError):
                            pass
                if self.player and self.player.stdout in ready:
                    message = self.player.stdout.readline().strip()
                    if message == 'looped':
                        self.completed_loops += 1
                    elif message != 'ready':
                        self.failed.add(self.current_quality)
                        self.stop_player()
                        self.reconcile()
                if time.monotonic() >= next_policy:
                    self.resource_check()
                    self.reconcile()
                    next_policy = time.monotonic() + 5
            return 0
        finally:
            self.stop_player()
            terminate(self.desktop)
            server.close()
            control_path.unlink(missing_ok=True)
            control_path.with_name('desktop.json').unlink(missing_ok=True)
            lock.close()

    def shutdown(self, _signal, _frame):
        self.running = False


def main():
    parser = argparse.ArgumentParser(description='Quiet local motion for the DhampirOS desktop.')
    parser.add_argument('action', choices=['desktop', 'status', 'mode', 'quality', 'restart', 'stop', 'enable'])
    parser.add_argument('value', nargs='?')
    args = parser.parse_args()
    if args.action == 'desktop':
        try:
            return Desktop().run()
        except Exception as error:
            print(f'dhampiros-motion: native static fallback: {error}', file=sys.stderr)
            os.execv('/usr/bin/pcmanfm-qt', ['pcmanfm-qt', '--desktop', '--profile', 'lxqt',
                                           '--set-wallpaper', str(STILL), '--wallpaper-mode', 'zoom'])
    if args.action in ('mode', 'quality'):
        choices = ('full', 'reduced', 'off') if args.action == 'mode' else ('auto', 'full', 'light')
        if args.value not in choices:
            parser.error(f'{args.action} requires one of: {", ".join(choices)}')
        ini_set(CONFIG, 'Motion', args.action.title(), args.value)
    elif args.action == 'enable':
        target = CONFIG_HOME / 'autostart/lxqt-desktop.desktop'
        template = Path('/usr/share/dhampiros/motion/lxqt-desktop.desktop').read_text(encoding='utf-8')
        if target.exists() and target.read_text(encoding='utf-8') != template:
            parser.error('An existing custom desktop loader is present; it was preserved.')
        atomic_text(target, template)
        print('DhampirOS desktop loader enabled. Log out and in to use it.')
        return 0
    try:
        print(json.dumps(request(args.action if args.action in ('restart', 'stop') else 'status'), indent=2))
    except (OSError, RuntimeError):
        print(json.dumps({'state': 'not-running', 'mode': preferences()[0], 'quality': preferences()[1],
                          'config': str(CONFIG), 'fallback': str(STILL)}, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
