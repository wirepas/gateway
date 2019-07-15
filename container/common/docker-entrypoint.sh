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

_TEMPLATE_PATH=${TRANSPORT_SERVICE}/wm_transport_service.template
_SETTINGS_PATH=${TRANSPORT_SERVICE}/wm_transport_service.yml

generate_settings "${_TEMPLATE_PATH}" "${_SETTINGS_PATH}"

if [[ "${TARGET}" == "sink" || "${TARGET}" == "transport" ]]
then
    if [[ "${TARGET}" == "transport" ]]
    then
        echo "connecting to ${WM_SERVICES_HOST}"
        TARGET="wm-gw --settings ${_SETTINGS_PATH}"
        cat "${_SETTINGS_PATH}"
    fi

    if [[ "${TARGET}" == "sink" ]]
    then
       TARGET="/usr/local/bin/sinkService \
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
