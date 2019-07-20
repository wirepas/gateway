#!/usr/bin/env bash
# Wirepas Oy

ARTIFACT_PATH=${1:-"./dist/*"}

TWINE_USERNAME=${TWINE_USERNAME:-"Wirepas"}
TWINE_PASSWORD=${TWINE_PASSWORD:-${PYPI_PWD}}
TWINE_REPOSITORY=${TWINE_REPOSITORY}
TWINE_REPOSITORY_URL=${TWINE_REPOSITORY_URL}

twine check "${ARTIFACT_PATH}"
twine upload "${ARTIFACT_PATH}"