#!/usr/bin/env bash
# Wirepas Ltd 2019

set -e

# Call to register a failure
failure()
{
    NB_FAIL=$((NB_FAIL + 1))
    return 1
}

# Call to register a pass
success()
{
    NB_PASS=$((NB_PASS + 1))
    return 0
}

# Searches for a specific content in the file
function content_in_file
{
    _RULE="${1}"
    _FILE="${2}"

    echo "CONTENT SEARCH: ${_RULE}"
    if ! grep -q -c  "${_RULE}" "${_FILE}"
    then
        failure
        return "${?}"
    fi

    success
    return "${?}"
}

# Ensures that the sink service environment acquisition is performed correctly
function test_env_acquisition
{
    set -e
    ${EXEC} | tee "${LOGFILE}"
    set +e

    _RULE="WM_GW_SINK_ID: ${WM_GW_SINK_ID}"
    content_in_file "${_RULE}" "${LOGFILE}"

    _RULE="WM_GW_SINK_BAUDRATE: ${WM_GW_SINK_BAUDRATE}"
    content_in_file "${_RULE}" "${LOGFILE}"

    _RULE="WM_GW_SINK_MAX_POLL_FAIL_DURATION: ${WM_GW_SINK_MAX_POLL_FAIL_DURATION}"
    content_in_file "${_RULE}" "${LOGFILE}"

    _RULE="WM_GW_SINK_UART_PORT: ${WM_GW_SINK_UART_PORT}"
    content_in_file "${_RULE}" "${LOGFILE}"

    return "${?}"
}

# Tests excessive input in environment argument
function test_env_overflow
{
    WM_GW_SINK_BAUDRATE=190909123198273981273916396721389612836198263891253761537512735173578123518723568712635126358126358135812653812653817357182635871537812531862316235715238713581537815236152736518723517826538712537815238716523815231361823581725371852387152378125387125387125387152387153
    WM_GW_SINK_MAX_POLL_FAIL_DURATION=190909123198273981273916396721389612836198263891253761537512735173578123518723568712635126358126358135812653812653817357182635871537812531862316235715238713581537815236152736518723517826538712537815238716523815231361823581725371852387152378125387125387125387152387153
    WM_GW_SINK_UART_PORT=190909123198273981273916396721389612836198263891253761537512735173578123518723568712635126358126358135812653812653817357182635871537812531862316235715238713581537815236152736518723517826538712537815238716523815231361823581725371852387152378125387125387125387152387153

    set +e
    ${EXEC}

    if (( "${?}" > 1  ))
    then
        failure
        return "${?}"
    fi
    set -e

    success
    return "$?"
}

# Fills in the sink environment variables
generate_sink_service_env_args()
{
    export WM_GW_SINK_ID
    export WM_GW_SINK_BAUDRATE
    export WM_GW_SINK_MAX_POLL_FAIL_DURATION
    export WM_GW_SINK_UART_PORT

    WM_GW_SINK_ID=$(shuf -i 0-9 -n 1)
    WM_GW_SINK_BAUDRATE=$(shuf -i 12500-100000 -n 1)
    WM_GW_SINK_MAX_POLL_FAIL_DURATION=$(shuf -i 0-9 -n 1)
    WM_GW_SINK_UART_PORT=/dev/ttyAAAA
}

# Provides a summary of the pass and fail tests
_summary()
{
    echo "PASS: ${NB_PASS}"
    echo "FAILURES: ${NB_FAIL}"

    if ((NB_FAIL > 0))
    then
        return 1
    else
        return 0
    fi

    rm -fv "${LOGFILE:?}"
}

# Defines the default arguments and which tests to run
_main()
{
    export EXEC
    export LOGFILE
    export NB_FAIL=0
    export NB_PASS=0

    EXEC="sink_service/build/sinkService"
    LOGFILE=sink_service.log

    if [[ -n "$(command -v "sinkService")" ]]
    then
        EXEC="sinkService"
    elif [[ ! -f "${EXEC}" ]]
    then
        echo "please build the sink service"
        exit 1
    fi

    generate_sink_service_env_args

    test_env_acquisition "$@"
    test_env_overflow "$@"

    _summary

    exit "${?}"
}

_main "$@"
