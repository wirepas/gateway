#!/usr/bin/env bash

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

    COMPOSE_CMD="$1"
    _TIMEOUT="${2:-10}"

    timeout --preserve-status "${_TIMEOUT}" docker-compose \
            -f tests/services/docker-compose.yml up \
            --abort-on-container-exit \
            --exit-code-from wm-transport
}


pull_dependencies

run_test "$@"
