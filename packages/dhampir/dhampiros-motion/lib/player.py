#!/usr/bin/python3
# Copyright (C) 2026 potemkin666
# See the file COPYING for copying conditions.
# AI-Assisted

"""Input-transparent Wayland underlay, with one bounded local video decoder."""

import os
import signal
import sys
import threading
import time

from motionlib import STILL, VIDEOS, take_lock, wallpaper


def main():
    lock = take_lock('player.lock')
    if lock is None or len(sys.argv) != 2 or sys.argv[1] not in VIDEOS:
        return 1
    import gi
    gi.require_version('Gtk', '3.0')
    gi.require_version('Gdk', '3.0')
    gi.require_version('GdkPixbuf', '2.0')
    gi.require_version('Gst', '1.0')
    gi.require_version('GtkLayerShell', '0.1')
    gi.require_foreign('cairo')
    from gi.repository import Gdk, GdkPixbuf, GLib, Gst, Gtk, GtkLayerShell

    if not Gtk.init_check()[0] or not GtkLayerShell.is_supported():
        return 1
    Gst.init(None)
    os.nice(10)
    pipeline = Gst.Pipeline.new('dhampiros-local-wallpaper')
    windows, areas = [], []
    frame_times = {}
    paused_hidden = announced = repaint_pending = False
    still = GdkPixbuf.Pixbuf.new_from_file(str(STILL))
    frame = still
    latest_sample = None
    sample_lock = threading.Lock()

    def element(name):
        result = Gst.ElementFactory.make(name)
        if result is None:
            raise RuntimeError(f'Missing GStreamer element: {name}')
        pipeline.add(result)
        return result

    def quit_player(*_arguments):
        pipeline.set_state(Gst.State.NULL)
        Gtk.main_quit()
        return GLib.SOURCE_REMOVE

    def orphaned():
        try:
            wallpaper(STILL)
        finally:
            quit_player()

    def command(_stream, condition):
        if condition & (GLib.IO_HUP | GLib.IO_ERR) or not sys.stdin.readline():
            orphaned()
        else:
            quit_player()
        return GLib.SOURCE_REMOVE

    def draw(area, context):
        allocation = area.get_allocation()
        ratio = max(allocation.width / frame.get_width(), allocation.height / frame.get_height())
        context.save()
        context.translate((allocation.width - frame.get_width() * ratio) / 2,
                          (allocation.height - frame.get_height() * ratio) / 2)
        context.scale(ratio, ratio)
        Gdk.cairo_set_source_pixbuf(context, frame, 0, 0)
        context.paint()
        context.restore()
        return False

    def present_latest():
        nonlocal latest_sample, repaint_pending, frame, announced
        with sample_lock:
            sample, latest_sample = latest_sample, None
            repaint_pending = False
        if sample is None or paused_hidden:
            return GLib.SOURCE_REMOVE
        structure = sample.get_caps().get_structure(0)
        width, height = structure.get_value('width'), structure.get_value('height')
        stride = (width * 3 + 3) & ~3
        buffer = sample.get_buffer()
        if not (0 < width <= 3840 and 0 < height <= 2160 and buffer.get_size() >= stride * height):
            print('failed', flush=True)
            return GLib.SOURCE_REMOVE
        pixels = GLib.Bytes.new(buffer.extract_dup(0, stride * height))
        frame = GdkPixbuf.Pixbuf.new_from_bytes(pixels, GdkPixbuf.Colorspace.RGB, False,
                                               8, width, height, stride)
        for area in areas:
            area.queue_draw()
        if not announced:
            announced = True
            print('ready', flush=True)
        return GLib.SOURCE_REMOVE

    def new_sample(sink):
        nonlocal latest_sample, repaint_pending
        sample = sink.emit('pull-sample')
        if sample is None:
            return Gst.FlowReturn.ERROR
        with sample_lock:
            latest_sample = sample
            if not repaint_pending:
                repaint_pending = True
                GLib.idle_add(present_latest)
        return Gst.FlowReturn.OK

    def message(_bus, event):
        nonlocal frame
        if event.type == Gst.MessageType.EOS:
            if pipeline.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT, 0):
                print('looped', flush=True)
            else:
                print('failed', flush=True)
                quit_player()
        elif event.type == Gst.MessageType.ERROR:
            frame = still
            for area in areas:
                area.queue_draw()
            print(f'dhampiros-motion: decoder error: {event.parse_error()[0]}', file=sys.stderr)
            print('failed', flush=True)
            pipeline.set_state(Gst.State.NULL)

    def resume_visible():
        pipeline.set_state(Gst.State.PLAYING)
        return GLib.SOURCE_REMOVE

    def painted(clock):
        nonlocal paused_hidden
        frame_times[clock] = time.monotonic()
        if paused_hidden:
            paused_hidden = False
            GLib.idle_add(resume_visible)

    def visibility_probe():
        nonlocal paused_hidden, frame
        if frame_times and time.monotonic() - max(frame_times.values()) > 5 and not paused_hidden:
            paused_hidden = True
            pipeline.set_state(Gst.State.NULL)
            frame = still
        for area in areas:
            area.queue_draw()
        if os.environ.get('DHAMPIROS_MOTION_DEBUG') == '1':
            _result, current, pending = pipeline.get_state(0)
            _ok, position = pipeline.query_position(Gst.Format.TIME)
            print(f'dhampiros-motion: pipeline={current.value_nick} pending={pending.value_nick} position={position} hidden={paused_hidden}', file=sys.stderr)
        return GLib.SOURCE_CONTINUE

    source = element('filesrc')
    source.set_property('location', str(VIDEOS[sys.argv[1]]))
    demux = element('matroskademux')
    decoder = element('vp9dec')
    decoder.set_property('threads', 2)
    convert = element('videoconvert')
    caps = element('capsfilter')
    caps.set_property('caps', Gst.Caps.from_string('video/x-raw,format=RGB'))
    sink = element('appsink')
    sink.set_property('emit-signals', True)
    sink.set_property('max-buffers', 1)
    sink.set_property('drop', True)
    sink.set_property('wait-on-eos', False)
    sink.connect('new-sample', new_sample)
    assert source.link(demux) and decoder.link(convert) and convert.link(caps) and caps.link(sink)

    def video_pad(_demux, pad):
        video_caps = pad.get_current_caps()
        if video_caps and video_caps.to_string().startswith('video/x-vp9'):
            pad.link(decoder.get_static_pad('sink'))

    demux.connect('pad-added', video_pad)
    display = Gdk.Display.get_default()
    if display.get_n_monitors() > 4:
        raise RuntimeError('More than four outputs: retaining the native still wallpaper')
    for index in range(display.get_n_monitors()):
        window = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
        window.set_accept_focus(False)
        window.set_focus_on_map(False)
        GtkLayerShell.init_for_window(window)
        GtkLayerShell.set_namespace(window, 'dhampiros-motion')
        GtkLayerShell.set_layer(window, GtkLayerShell.Layer.BACKGROUND)
        GtkLayerShell.set_monitor(window, display.get_monitor(index))
        GtkLayerShell.set_keyboard_mode(window, GtkLayerShell.KeyboardMode.NONE)
        GtkLayerShell.set_exclusive_zone(window, -1)
        for edge in (GtkLayerShell.Edge.TOP, GtkLayerShell.Edge.BOTTOM, GtkLayerShell.Edge.LEFT, GtkLayerShell.Edge.RIGHT):
            GtkLayerShell.set_anchor(window, edge, True)
        area = Gtk.DrawingArea()
        area.connect('draw', draw)
        window.add(area)
        window.connect('destroy', quit_player)
        window.show_all()
        window.get_window().set_pass_through(True)
        clock = window.get_frame_clock()
        frame_times[clock] = time.monotonic()
        clock.connect('after-paint', painted)
        windows.append(window)
        areas.append(area)
    if not windows:
        return 1
    display.connect('monitor-added', lambda *_: quit_player())
    display.connect('monitor-removed', lambda *_: quit_player())
    settings = Gtk.Settings.get_default()
    if not settings.get_property('gtk-enable-animations'):
        return 1
    settings.connect('notify::gtk-enable-animations', lambda *_: quit_player() if not settings.get_property('gtk-enable-animations') else None)
    bus = pipeline.get_bus()
    bus.add_signal_watch()
    bus.connect('message', message)
    GLib.timeout_add_seconds(2, visibility_probe)
    GLib.io_add_watch(sys.stdin, GLib.IO_IN | GLib.IO_HUP | GLib.IO_ERR, command)
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGTERM, quit_player)
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGINT, quit_player)
    if pipeline.set_state(Gst.State.PLAYING) == Gst.StateChangeReturn.FAILURE:
        return 1
    try:
        Gtk.main()
    finally:
        pipeline.set_state(Gst.State.NULL)
        lock.close()
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as error:
        print(f'dhampiros-motion: player unavailable: {error}', file=sys.stderr)
        sys.exit(1)
