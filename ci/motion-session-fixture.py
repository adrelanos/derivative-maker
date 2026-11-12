#!/usr/bin/python3
# Copyright (C) 2026 potemkin666
# See the file COPYING for copying conditions.
# AI-Assisted

"""Private-bus logind fixture for the headless test; never installed."""

from gi.repository import Gio, GLib

XML = '''<node>
<interface name="org.freedesktop.login1.Manager">
 <method name="GetSessionByPID"><arg type="u" direction="in"/><arg type="o" direction="out"/></method>
</interface>
<interface name="org.freedesktop.login1.Session">
 <property name="Active" type="b" access="read"/>
 <property name="LockedHint" type="b" access="read"/>
 <property name="Remote" type="b" access="read"/>
</interface>
<interface name="org.dhampiros.MotionTest">
 <method name="SetState"><arg type="b" direction="in"/><arg type="b" direction="in"/></method>
</interface></node>'''
state = {'Active': True, 'LockedHint': False, 'Remote': False}
connection = Gio.bus_get_sync(Gio.BusType.SESSION, None)
interfaces = Gio.DBusNodeInfo.new_for_xml(XML).interfaces
path = '/org/freedesktop/login1/session/motiontest'


def method(_connection, _sender, _path, _interface, name, parameters, invocation):
    if name == 'GetSessionByPID':
        invocation.return_value(GLib.Variant('(o)', (path,)))
    else:
        state['Active'], state['LockedHint'] = parameters.unpack()
        invocation.return_value(None)


def property_value(_connection, _sender, _path, _interface, name):
    return GLib.Variant('b', state[name])


connection.register_object('/org/freedesktop/login1', interfaces[0], method, None, None)
connection.register_object(path, interfaces[1], None, property_value, None)
connection.register_object(path, interfaces[2], method, None, None)
Gio.bus_own_name_on_connection(connection, 'org.freedesktop.login1', Gio.BusNameOwnerFlags.NONE, None, None)
GLib.MainLoop().run()
