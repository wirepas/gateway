#!/bin/sh

if [ -f '/var/run/dbus.pid' ]; then
    rm -f '/var/run/dbus.pid'
fi

exec dbus-daemon --system --nofork --print-address
