#!/usr/bin/env bash

set -e

if [[ -f ".wnt-secrets" ]]
then
    set -a
    # shellcheck disable=SC1091
    source ".wnt-secrets"
    set +a
fi

function pull_dependencies()
{

    WAIT_FOR_IT_PATH=tests/services/wait-for-it

    if [[ ! -d "${WAIT_FOR_IT_PATH}" ]]
    then
        git clone https://github.com/vishnubob/wait-for-it.git "${WAIT_FOR_IT_PATH}"
    fi
}

function sink_service_tests()
{
    export SINK_SERVICE_TEST
    SINK_SERVICE_TEST="$1"
    docker-compose -f tests/services/sink-service.yml up --exit-code-from wm-sink
}

function transport_service_tests()
{
    export TRANSPORT_SERVICE_TEST
    local _TIMEOUT

    TRANSPORT_SERVICE_TEST="$1"
    _TIMEOUT="${2:-10}"

    timeout --preserve-status "${_TIMEOUT}" docker-compose \
            -f tests/services/transport-service.yml up \
            --abort-on-container-exit \
            --exit-code-from wm-transport
}

function main()
{
    pull_dependencies

    sink_service_tests "test_sink_env_params.sh"
    transport_service_tests "transport" "10"
}


main "${@}"
