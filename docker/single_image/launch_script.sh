#!/bin/bash

# Start the first process
if [ -f '/var/run/dbus.pid' ]; then
    rm -f '/var/run/dbus.pid'
fi

dbus-daemon --system --fork --print-address
status=$?
if [ $status -ne 0 ]; then
  echo "Failed to start dbus-daemon: $status"
  exit $status
fi

# Start the sink_service
su wirepas -c /home/wirepas/sinkService &
status=$?
if [ $status -ne 0 ]; then
  echo "Failed to start sink_service: $status"
  exit $status
fi

# Start the transport
su wirepas -c "wm-gw --settings /home/wirepas/setting.yml &"
status=$?
if [ $status -ne 0 ]; then
  echo "Failed to start transport_service: $status"
  exit $status
fi

# Naive check runs checks once every 30s to see if either of the processes exited.
# This illustrates part of the heavy lifting you need to do if you want to run
# more than one service in a container. The container exits with an error
# if it detects that either of the processes has exited.
# Otherwise it loops forever, waking up every 30 seconds

while sleep 30; do
  ps aux |grep dbus-daemon |grep -q -v grep
  PROCESS_1_STATUS=$?
  ps aux |grep sinkService |grep -q -v grep
  PROCESS_2_STATUS=$?
  ps aux |grep wm-gw |grep -q -v grep
  PROCESS_3_STATUS=$?
  # If the greps above find anything, they exit with 0 status
  # If they are not both 0, then something is wrong
  if [ $PROCESS_1_STATUS -ne 0 -o $PROCESS_2_STATUS -ne 0 -o $PROCESS_3_STATUS -ne 0 ]; then
    echo "One of the processes has already exited."
    exit 1
  fi
done
