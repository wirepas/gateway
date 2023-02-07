#!/bin/sh

if [ -f '/run/dbus/dbus.pid' ]; then
    rm -f '/run/dbus/dbus.pid'
fi

exec dbus-daemon --system --nofork --print-address