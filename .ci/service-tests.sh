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

function run_test()
{
    export COMPOSE_CMD
    export SINK_SERVICE_TEST

    COMPOSE_CMD="$1"
    _TIMEOUT="${2:-10}"

    SINK_SERVICE_TEST="test_sink_env_params.sh"
    docker-compose -f tests/services/sink-service.yml up --exit-code-from wm-sink

    timeout --preserve-status "${_TIMEOUT}" docker-compose \
            -f tests/services/transport-service.yml up \
            --abort-on-container-exit \
            --exit-code-from wm-transport
}


pull_dependencies

run_test "$@"
