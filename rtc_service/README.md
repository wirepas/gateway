# Wirepas Gateway RTC Service

## Overview
This service allows Wirepas gateway to send a global clock to the devices in the network with a good precision and accuracy without having specific hardware.

This service gets the global time in UTC timezone from an ntp server and spread the value to the network.


## RTC configuration
The RTC service has three parameters to be started.
| Parameter | Purpose | Note |
| ------------- | ----    | ---  |
| WM_RTC_SYNCHRONIZATION_PERIOD_S | Period of time before sending a new rtc time in the network | The default value is 20 minutes (1200 seoncds). This value should take into account the existing congestion in the network. |
| WM_RTC_TIMEZONE_FROM_GATEWAY_CLOCK | A boolean to assert whether the timezone offset should be taken directly from the gateway clock or from the the parameter WM_RTC_TIMEZONE_OFFSET_S | The default value is False |
| WM_RTC_TIMEZONE_OFFSET_S | Timezone offset in seconds of the local time. | It is taken in account only if WM_RTC_TIMEZONE_FROM_GATEWAY_CLOCK is False. |

RTC service is available as a docker image to ease the integration.

## How does it works

This service gets the global time in UTC timezone from an ntp server. It then directly spread the value to the network though specific downlink broadcast data messages.


## Message formats

After trying CBOR encoding, it was seen that the library was taken too much space.
It was therefore decided to use TLV encoding for the library to be backward compatible.

The messages are composed of:

| Parameter | type | number of bits | description |
| ------------- | ----    | ---  | ---  |
| version | unsigned int | 1 | Version of the library |
| rtc timestamp | unsigned long long | 8 | Timestamp of the current rtc time in the UTC timezone |
| timezone offset | long | 4 | Local timezone offset in seconds |


### TLV encoding

To encode messages with TLV, the type(id) of each parameter must be given as follow :

RTC_ID_VERSION = 0
RTC_ID_TIMER = 1
RTC_ID_TIMEZONE_OFFSET = 2

Then the length of the value is coded in hex.
And finally the value itself is encoded in hex.

For example, a message containing :

| Parameter | type | number of bits | value |
| ------------- | ----    | ---  | ---  |
| version | 0 | 1 | 0x01 |
| rtc timestamp | 1 | 8 | 0x000001850aeb3964 |
| timezone offset | 2 | 4 | 0x1c20 (7200s = 2h) |

Each parameter are encoded as byte(type)(1 byte) - byte(length)(1 byte) - byte(value)(length bytes) individually and their bytes are concatenated.

The message is therefore encoded with TLV as :
b'\x00\x01\x00\x01\x08d9\xeb\n\x85\x01\x00\x00\x02\x04 \x1c\x00\x00'


### Parameter ids

To encode messages, the type(id) of each parameter must be given as follow :

RTC_ID_VERSION = 0
RTC_ID_TIMER = 1
RTC_ID_TIMEZONE_OFFSET = 2


## Time precision

Due to the multiple steps, the rtc time might not be precize enough:

Time is taken from a distant ntp server. The estimated latency may be unaccurate as it is calculate from the round-trip of the assymetrical exchange.

RTC time is taken at rtc level while the travel time calculation starts at a sink service level. From RTC to sink service, we lose 10ms precision on rtc time.

As devices use their own clock to stay synchronous,
a drift might happen between the expected rtc time and the real one from the ntp server. 
It is empirically estimated to be a 1ms shift at the node level every 40s in a Low Latency mode.

A latency may also occur when transfering the messages between nodes.

## Test the time difference

As devices use their own clock to stay synchronous,
a drift might happen between the expected rtc time and the real one from the ntp server.
A python script [test_time_difference][test_time_difference] getting the expected rtc time from the nodes.

### Use conditions

Nodes need to send periodically their expected rtc time to the sinks.
The time difference between the expectation and the real time are then stored in a local file. 


[test_time_difference]: https://github.com/gateway/rtc_service/script/script_rtc_time_difference.py
