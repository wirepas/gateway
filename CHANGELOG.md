# Implementation of the Keep Alive thread in the transport service.

## What's Changed

A keep-alive mechanism has been added to periodically broadcast gateway messages to all devices in the network.
This feature is implemented as a dedicated thread in the transport service and can be enabled via environment variables.

The following environment variables are now parsed by the wirepas transport service:
* WM_KEEP_ALIVE_ACTIVATE (default: False)
    Activates the keep-alive service thread.
    Note: Gateway time is supposed to be synchronized with the NTP server before launching the service.
* WM_KEEP_ALIVE_INTERVAL_S (default: 300)
    The interval in seconds between keep-alive messages.
* WM_KEEP_ALIVE_TIMEZONE_NAME (Default: 'Etc/UTC')
    Timezone name used to set the timezone offset in the keep-alive message.
    Check https://en.wikipedia.org/wiki/List_of_tz_database_time_zones#List
    to see the list of timezone identifiers. Example value: "Asia/Kolkata"

**Full Changelog**: https://github.com/wirepas/gateway/compare/v1.6.1...rel/amiv2_v1.1.0
