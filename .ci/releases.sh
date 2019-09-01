#!/usr/bin/env bash
# Copyright 2019 Wirepas Ltd

set -e

ROOT_DIR=$(pwd)
cd "${PYTHON_PKG_PATH}"

set -a
GH_RELEASE_PYTHON_VERSION=$(< "${PYTHON_PKG_NAME}"/__about__.py  \
                     awk '/__version__/{print $NF}' | \
                     tr -d "\"")

GH_RELEASE_CANDIDATE="false"
GH_RELEASE_DRAFT="false"
GH_RELEASE_NAME="\"Release ${GH_RELEASE_PYTHON_VERSION}\""
GH_RELEASE_BODY="\"Please see attached CHANGELOG.md\""
set +a

if [[ ${GH_RELEASE_PYTHON_VERSION} =~ "rc" ]]
then
    echo "Release candidate"
    GH_RELEASE_CANDIDATE="true"
    GH_RELEASE_DRAFT="true"
    GH_RELEASE_NAME="\"Release candidate ${GH_RELEASE_PYTHON_VERSION}\""

elif [[ ${GH_RELEASE_PYTHON_VERSION} =~ "dev" ]]
then
    echo "Development version"
    GH_RELEASE_DRAFT="true"
    GH_RELEASE_NAME="\"Development version ${GH_RELEASE_PYTHON_VERSION}\""
fi

echo "version=${GH_RELEASE_PYTHON_VERSION},name=${GH_RELEASE_NAME}, body=${GH_RELEASE_BODY}, draft=${GH_RELEASE_DRAFT}, rc=${GH_RELEASE_CANDIDATE}"

set +e
github_changelog_generator -t "${GH_TOKEN}"
if [[ $? -eq 1 ]]
then
    echo "failed to authenticate, fallback to git log"
    git log -2 --pretty="%h >> %s" > CHANGELOG.md
fi
set -e

cd "${ROOT_DIR}"
env | grep "GH_" > releases.env
