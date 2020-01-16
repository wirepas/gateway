#!/usr/bin/env bash
# Copyright 2019 Wirepas Ltd

set -e

export WM_GW_SINK_UART_PORT
export WM_GW_SINK_UART_BITRATE
export WM_GW_ID
export WM_GW_MODEL
export WM_GW_VERSION
export WM_GW_IGNORED_ENDPOINTS_FILTER
export WM_GW_WHITENED_ENDPOINTS_FILTER

export WM_SERVICES_MQTT_HOSTNAME
export WM_SERVICES_MQTT_USERNAME
export WM_SERVICES_MQTT_FORCE_UNSECURE
export WM_SERVICES_MQTT_ALLOW_UNTRUSTED

TARGET=${1}

echo "Image source manifest"
cat "${SERVICE_HOME}/manifest"

WM_GW_SINK_UART_PORT="${WM_GW_SINK_UART_PORT:-${WM_SINK_UART_PORT}}"
WM_GW_SINK_UART_BITRATE="${WM_GW_SINK_UART_BITRATE:-${WM_SINK_UART_BITRATE}}"
WM_GW_ID="${WM_GW_ID:-${WM_SERVICES_GATEWAY_ID}}"
WM_GW_MODEL="${WM_GW_MODEL:-${WM_SERVICES_GATEWAY_MODEL}}"
WM_GW_VERSION="${WM_GW_VERSION:-${WM_SERVICES_GATEWAY_VERSION}}"
WM_GW_IGNORED_ENDPOINTS_FILTER="${WM_GW_IGNORED_ENDPOINTS_FILTER:-${WM_SERVICES_GATEWAY_IGNORED_ENDPOINTS_FILTER}}"
WM_GW_WHITENED_ENDPOINTS_FILTER="${WM_GW_WHITENED_ENDPOINTS_FILTER:-${WM_SERVICES_GATEWAY_WHITENED_ENDPOINTS_FILTER}}"

WM_SERVICES_MQTT_HOSTNAME="${WM_SERVICES_MQTT_HOSTNAME:-${WM_SERVICES_HOST}}"
WM_SERVICES_MQTT_USERNAME="${WM_SERVICES_MQTT_USERNAME:-${WM_SERVICES_MQTT_USER}}"
WM_SERVICES_MQTT_ALLOW_UNTRUSTED="${WM_SERVICES_MQTT_ALLOW_UNTRUSTED:-${WM_SERVICES_ALLOW_UNSECURE}}"
WM_SERVICES_MQTT_FORCE_UNSECURE="${WM_SERVICES_MQTT_FORCE_UNSECURE:-${WM_SERVICES_ALLOW_UNSECURE}}"
WM_SERVICES_MQTT_CA_CERTS="${WM_SERVICES_MQTT_CA_CERTS:-${WM_SERVICES_CERTIFICATE_CHAIN}}"

if [[ "${TARGET}" == "sink" || "${TARGET}" == "transport" ]]
then
    if [[ "${TARGET}" == "transport" ]]
    then
        echo "connecting to ${WM_SERVICES_HOST}"
        TARGET="wm-gw"
    fi

    if [[ "${TARGET}" == "sink" ]]
    then
       TARGET="/usr/local/bin/sinkService \
                -p ${WM_SINK_UART_PORT} \
                -b ${WM_SINK_UART_BITRATE} \
                -i ${WM_SINK_ID}"
    fi

    echo "Starting service: ${TARGET}"
    exec "${TARGET}"
else
    exec "$@"
fi

echo "exiting"
