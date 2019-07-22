#!/usr/bin/env bash
# Copyright 2019 Wirepas Ltd


function _instructions
{
cat << EOF
    Please ensure the following software is installed on your host:
        - clang-format-7
        - shellcheck
        - Python +3.6
        - Pip

    Install pre-commit and other linters with:
        pip install -r dev-requirements.txt
EOF
}
set -e

CLONE_TARGET="./.ci/manifest"

# clone manifest and tools
rm -rf "${CLONE_TARGET}"
git clone https://github.com/wirepas/manifest.git "${CLONE_TARGET}"

# copy . files
_dot_files=(.clang-format .pre-commit-config.yaml .flake8 dev-requirements.txt)

for _file in "${_dot_files[@]}"
do
    echo "copying ${CLONE_TARGET}/${_file}"
    cp "${CLONE_TARGET}/${_file}" .
done

_instructions
