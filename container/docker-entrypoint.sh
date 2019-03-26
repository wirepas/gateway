#!/usr/bin/env bash
# Wirepas Oy

set -e
env | grep WM_

TARGET="${1}"

if [ "${TARGET}" == "sink" ] || [ "${TARGET}" == "transport" ]
then
    echo "Executing ${TARGET}"
    if [ "${TARGET}" = 'transport' ]; then
        echo "connecting to ${WM_SERVICES_HOST}"

        # certificate chain
        if [ ! -z "${WM_SERVICES_CERTIFICATE_CHAIN}" ]
        then
            CMD_SERVICES_CERTIFICATE_CHAIN="-t ${WM_SERVICES_CERTIFICATE_CHAIN}"
        else
            CMD_SERVICES_CERTIFICATE_CHAIN=""

        fi

        # gateway id
        if [ ! -z "${WM_SERVICES_GATEWAY_ID}" ]
        then
            CMD_SERVICES_GATEWAY_ID="-i ${WM_SERVICES_GATEWAY_ID}"
        else
            CMD_SERVICES_GATEWAY_ID=""
        fi

        # unsecure connection
        if [ ! -z "${WM_SERVICES_ALLOW_UNSECURE}" ] && [ "${WM_SERVICES_ALLOW_UNSECURE}"  == "true" ]
        then
            CMD_SERVICES_ALLOW_UNSECURE="-ua"
        else
            CMD_SERVICES_ALLOW_UNSECURE=""
        fi

        # gateway model
        if [ ! -z "${WM_SERVICES_GATEWAY_MODEL}" ]
        then
            CMD_SERVICES_GATEWAY_MODEL="-gm ${WM_SERVICES_GATEWAY_MODEL}"
        else
            CMD_SERVICES_GATEWAY_MODEL=""
        fi

        # gateway version
        if [ ! -z "${WM_SERVICES_GATEWAY_VERSION}" ]
        then
            CMD_SERVICES_GATEWAY_VERSION="-gv ${WM_SERVICES_GATEWAY_VERSION}"
        else
            CMD_SERVICES_GATEWAY_VERSION=""
        fi

        # endpoints to filter at the gateway
        if [ ! -z "${WM_SERVICES_GATEWAY_IGNORED_ENDPOINTS_FILTER}" ]
        then
            CMD_SERVICES_GATEWAY_IGNORED_ENDPOINTS_FILTER="-iepf ${WM_SERVICES_GATEWAY_IGNORED_ENDPOINTS_FILTER}"
        else
            CMD_SERVICES_GATEWAY_IGNORED_ENDPOINTS_FILTER=""
        fi

        # endpoints to whiten at the gateway
        if [ ! -z "${WM_SERVICES_GATEWAY_WHITENED_ENDPOINTS_FILTER}" ]
        then
            CMD_SERVICES_GATEWAY_WHITENED_ENDPOINTS_FILTER="-wepf ${WM_SERVICES_GATEWAY_WHITENED_ENDPOINTS_FILTER}"
        else
            CMD_SERVICES_GATEWAY_WHITENED_ENDPOINTS_FILTER=""
        fi

        TARGET="${EXEC_TRANSPORT} \
                 -s ${WM_SERVICES_HOST} \
                 -p ${WM_SERVICES_MQTT_PORT} \
                 -u ${WM_SERVICES_MQTT_USER} \
                 -pw ${WM_SERVICES_MQTT_PASSWORD} \
                 ${CMD_SERVICES_CERTIFICATE_CHAIN} \
                 ${CMD_SERVICES_GATEWAY_ID} \
                 ${CMD_SERVICES_ALLOW_UNSECURE} \
                 ${CMD_SERVICES_GATEWAY_MODEL} \
                 ${CMD_SERVICES_GATEWAY_VERSION} \
                 ${CMD_SERVICES_GATEWAY_IGNORED_ENDPOINTS_FILTER} \
                 ${CMD_SERVICES_GATEWAY_WHITENED_ENDPOINTS_FILTER}"
    fi

    if [ "${TARGET}" = 'sink' ]; then
       TARGET="${EXEC_SINK} \
                -p ${WM_SINK_UART_PORT}
                -b ${WM_SINK_UART_BITRATE} \
                -i ${WM_SINK_ID}"
    fi

    echo "running ${TARGET}"
    exec ${TARGET}
else
    echo "executing ${@}"
    exec "${@}"
fi

echo "exiting"
