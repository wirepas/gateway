#!/usr/bin/env bash
# Wirepas Oy

set -e

echo "Image source manifest"
cat "${SERVICE_HOME}/manifest"

echo "Available WM variables"
env | grep WM_

TARGET=${1}

WM_SINK_UART_PORT=${WM_SINK_UART_PORT:-"/dev/ttyACM0"}
WM_SINK_UART_BITRATE=${WM_SINK_UART_BITRATE:-"125000"}
WM_SINK_ID=${WM_SINK_ID:-"0"}

function generate_settings
{
    TEMPLATE=${1}
    OUTPUT_PATH=${2}

    if [[ -f "${OUTPUT_PATH}" ]]
    then
        rm -f "${OUTPUT_PATH}" "${OUTPUT_PATH}.tmp"
    fi

    ( echo "cat <<EOF >${OUTPUT_PATH}";
      cat "${TEMPLATE}";
      echo "EOF";
    ) > "${OUTPUT_PATH}.tmp"
    # shellcheck source=/dev/null
    . "${OUTPUT_PATH}.tmp"
    rm "${OUTPUT_PATH}.tmp"

    sed -i "/NOTSET/d" "${OUTPUT_PATH}"
}

generate_settings "${TRANSPORT_SERVICE}/transport.template" "${TRANSPORT_SERVICE}/transport.yaml"

if [[ "${TARGET}" == "sink" || "${TARGET}" == "transport" ]]
then
    if [[ "${TARGET}" == "transport" ]]
    then
        echo "connecting to ${WM_SERVICES_HOST}"
        TARGET="wm-gw --settings ${TRANSPORT_SERVICE}/transport.yaml"
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
