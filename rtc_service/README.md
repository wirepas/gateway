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

| Parameter | Type | Number of bytes | Description |
| ------------- | ----    | ---  | ---  |
| version | unsigned int | 1 | Version of the library |
| rtc timestamp | unsigned long long | 8 | Timestamp of the current rtc time in the UTC timezone |
| timezone offset | long | 4 | Local timezone offset in seconds |


### TLV encoding

To encode messages with TLV, the type(id) of each parameter must be given as follow :

RTC_ID_VERSION = 0
RTC_ID_TIMER = 1
RTC_ID_TIMEZONE_OFFSET = 2

Then the length of the value is coded in hexadecimal.
And finally the value itself is encoded in hexadecimal.

For example, a message containing :

| Parameter | type | number of bytes | value |
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

Due to the multiple steps, the RTC time might lose some precision:

Time is taken from a distant ntp server. The estimated latency may be inaccurate as it is calculate from the round-trip of the asymmetrical exchange. This is similar for all system relying on NTP but it must be acknowledged for better understanding of the time precision.

RTC time is taken at a gateway service level while the travel time calculation starts at a sink device level. From gateway to sink device, we lose about 10ms precision on RTC time to send the time data.

As devices use their own clock to stay synchronous,
a drift might happen between the expected RTC time and the real one from the ntp server.
It is empirically estimated to be a 1ms shift at the node level every 40s in a Low Latency mode. It was tested with a gateway sending RTC time every minute to a single node in a low latency. The node was displaying the time difference between the estimated value and the value. A simple graph shows the time difference shifting.

A latency may also occur when transferring the messages between nodes, but it hasn’t been tested yet.

## Test the time difference

As devices use their own clock to stay synchronous,
a drift might happen between the expected rtc time and the real one from the ntp server.
A python script [test_time_difference][test_time_difference] getting the expected rtc time from the nodes.

### Use conditions

Nodes need to send periodically their expected rtc time to the sinks.
The time difference between the expectation and the real time are then stored in a local file. 


[test_time_difference]: https://github.com/gateway/rtc_service/script_analyse/script_rtc_time_difference.py
