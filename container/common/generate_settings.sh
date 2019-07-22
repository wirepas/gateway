#!/usr/bin/env bash
# Copyright 2019 Wirepas Ltd

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
