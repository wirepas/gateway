# Wirepas Gateway RTC Service

## Overview
This service allows Wirepas gateway to send a synchronous time to the devices in the network with a good precision and accuracy without having specific hardware.

This service gets the global time in UTC timezone from an ntp server and spread the value to the network.


## RTC configuration
The RTC service has three optional parameters to be started.
| Parameter | Purpose | Note |
| ------------- | ----    | ---  |
| WM_RTC_SYNCHRONIZATION_PERIOD_S | Period of time before sending a new rtc time in the network |  |
| WM_RTC_TIMEZONE_FROM_GATEWAY_CLOCK | A boolean to assert whether the timezone offset should be taken directly from the gateway clock or from the the parameter WM_RTC_TIMEZONE_OFFSET_S | The default value is False |
| WM_RTC_TIMEZONE_OFFSET_S | Timezone offset in seconds of the local time. | It is taken in account only if WM_RTC_TIMEZONE_FROM_GATEWAY_CLOCK is False. |

RTC service is available as a docker image to ease the integration.

## How does it works

This service gets the global time in UTC timezone from an ntp server. It then directly spread the value to the network though specific downlink broadcast data messages.


## Message formats

All the messages concerning rtc are encoded thanks to CBOR library for backward compatibility.
They are composed of:

| Parameter | type | number of bits | description |
| ------------- | ----    | ---  | ---  |
| rtc timestamp | unsigned long long | 8 | Timestamp of the current rtc time in the UTC timezone |
| timezone offset | long | 4 | Local timezone offset in seconds |

## Time precision

Due to the multiple steps, the rtc time might not be precize enough:

Time is taken from a distant ntp server. The estimated latency may be unaccurate as it is calculate from the round-trip of the assymetrical exchange.

RTC time is taken at rtc level while the travel time calculation starts at a sink service level. From RTC to sink service, we lose 10ms precision on rtc time.

As devices use their own clock to stay synchronous,
a drift might happen between the expected rtc time and the real one from the ntp server. 
It is empirically estimated to be a 1ms shift at the node level every 40s in a Low Latency mode.


## Test the time difference

As devices use their own clock to stay synchronous,
a drift might happen between the expected rtc time and the real one from the ntp server.
A python script [test_time_difference][test_time_difference] getting the expected rtc time from the nodes.

### Use conditions

Nodes need to send periodically their expected rtc time to the sinks.
The time difference between the expectation and the real time are then stored in a local file. 


[test_time_difference]: https://github.com/gateway/rtc_service/script/script_rtc_time_difference.py
