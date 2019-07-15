#!/usr/bin/env bash
# Wirepas Oy

set -e

# shellcheck source=/dev/null
source "${TRANSPORT_SERVICE}/generate_settings.sh"

echo "Image source manifest"
cat "${SERVICE_HOME}/manifest"

echo "Available WM variables"
env | grep WM_

TARGET=${1}

WM_SINK_UART_PORT=${WM_SINK_UART_PORT:-"/dev/ttyACM0"}
WM_SINK_UART_BITRATE=${WM_SINK_UART_BITRATE:-"125000"}
WM_SINK_ID=${WM_SINK_ID:-"0"}

generate_settings "${TRANSPORT_SERVICE}/wm_transport_service.template" "${TRANSPORT_SERVICE}/wm_transport_service.yml"

if [[ "${TARGET}" == "sink" || "${TARGET}" == "transport" ]]
then
    if [[ "${TARGET}" == "transport" ]]
    then
        echo "connecting to ${WM_SERVICES_HOST}"
        TARGET="wm-gw --settings ${TRANSPORT_SERVICE}/wm_transport_service.yml"
        cat "${TRANSPORT_SERVICE}/transport.yaml"
    fi

    if [[ "${TARGET}" == "sink" ]]
    then
       TARGET="sinkService \
                -p ${WM_SINK_UART_PORT} \
                -b ${WM_SINK_UART_BITRATE} \
                -i ${WM_SINK_ID}"
    fi

    echo "Starting service: ${TARGET}"
    #shellcheck disable=SC2086
    exec ${TARGET}
else
    exec "$@"
fi

echo "exiting"
