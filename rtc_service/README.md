# Wirepas Gateway RTC Service

## Overview
This service allows Wirepas gateway to send a global clock to the devices in the network with a good precision and accuracy without having specific hardware.

This service gets the global time in UTC timezone from an ntp server and spreads the value to the network.


## RTC configuration
The RTC service needs four parameters to start.
| Parameter | Purpose | Note |
| ------------- | ----    | ---  |
| WM_RTC_SYNCHRONIZATION_PERIOD_S | Period of time before sending a new rtc time in the network | The default value is 20 minutes (1200 seconds). This value should take into account the existing congestion in the network. |
| WM_RTC_TIMEZONE_FROM_GATEWAY_CLOCK | A boolean to assert whether the timezone offset should be taken directly from the gateway clock or from the the parameter WM_RTC_TIMEZONE_OFFSET_S | The default value is False |
| WM_RTC_TIMEZONE_OFFSET_S | Timezone offset in seconds of the local time. | It is taken in account only if WM_RTC_TIMEZONE_FROM_GATEWAY_CLOCK is False. |
| WM_RTC_GET_TIME_FROM_LOCAL | Asserts if the rtc time is sent from local time or from a ntp server time | If set to True, it is assumed that gateways are synchronize. The default value is False |
| WM_RTC_NTP_SERVER_ADDRESS | Address of the ntp server to query the time if it is taken from an ntp server. | WM_RTC_GET_TIME_FROM_LOCAL must be set to False for that option to be taken into account |
| WM_RTC_RETRY_PERIOD_S | Period in seconds of the retries sending the rtc time when it couldn't be sent to the network. | It might take additional 5 seconds to know that the rtc time can't be retrieved. |

RTC service is available as a docker image to ease the integration.

## How does it work

This service gets the global time in UTC timezone from a ntp server. It then directly spreads the value to the network through specific downlink broadcast data messages.


## Messages format

TLV encoding is used to allow extension in future.
The messages are composed of:

A version on 2 bytes to ensure the content will be well parsed by the RTC library.

And the content is encoded with TLV with the following content:

| Parameter | Type | Number of bytes | Description |
| ------------- | ----    | ---  | ---  |
| rtc timestamp | unsigned long long | 8 | Timestamp of the current rtc time in the UTC timezone |
| timezone offset | long | 4 | Local timezone offset in seconds |


### TLV encoding

To encode messages with TLV, the type(id) of each parameter must be given as follow:

RTC_ID_TIMESTAMP = 0,  
RTC_ID_TIMEZONE_OFFSET = 1  

Then the length of the value is coded in hexadecimal.
And finally the value itself is encoded in hexadecimal.

For example, a message containing:

The RTC version equal to 1: 0x0001 which is not encoded.
And the TLV encoded content with:

| Parameter | Type | Number of bytes | Value |
| ------------- | ----    | ---  | ---  |
| rtc timestamp | 1 | 8 | 0x000001850aeb3964 |
| timezone offset | 2 | 4 | 0x1c20 (7200s = 2h) |

Each parameter is encoded with TLV as byte(type)(1 byte) - byte(length)(1 byte) - byte(value)(length bytes) individually and their bytes are concatenated.

The message is therefore encoded with TLV in little-endian as:
b'\x01\x00\x00\x08\x64\x39\xeb\x0a\x85\x01\x00\x00\x01\x04\x20\x1c\x00\x00'


## Time accuracy

Due to the multiple steps, the RTC time might lose some precision:

Time is taken from a distant ntp server. The estimated latency may be inaccurate as it is calculated from the round-trip of the asymmetrical exchange. This is similar for all systems relying on NTP, but it must be acknowledged for a better understanding of the time precision.

RTC time is taken at a gateway service level while the travel time calculation starts at the sink device level. From the gateway service to the sink device, we lose some accuracy.
An uncalculated latency may also occur when delivering the RTC data payloads to the nodes.

All together, the RTC service gives the time to the nodes in the network with 1 second accuracy.
