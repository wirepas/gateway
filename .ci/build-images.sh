#!/usr/bin/env bash
# Wirepas Oy

set -e

export VERSION
export BUILD_DATE
export IMAGE_NAME
export REGISTRY_NAME
export DOCKER_BASE
export CROSS_BUILD_START_CMD
export CROSS_BUILD_END_CMD
export GIT_MANIFEST_FILE
export GIT_MANIFEST_URL
export GIT_MANIFEST_BRANCH
export LXGW_C_MESH_API_HASH
export LXGW_SERVICES_HASH

SKIP_PULL=${1:-}

VERSION=$(< python_transport/wirepas_gateway/__about__.py awk '/__version__/{print $NF}'| tr -d '\"')
BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
REGISTRY_NAME="wirepas"

DOCKERFILE_PATH="./container"
GIT_REPO_FOLDER="./.ci/_repo"
BUILD_TAG=${BUILD_TAG:-$TRAVIS_TAG}

##
## @brief      Changes to the corresponding target and builds the image
##
function _build
{
    _PATH=${1:-"${DOCKERFILE_PATH}/x86"}
    _ARCH=${2:-"x86"}
    _CACHE=${3:-}

    # build based on architecture
    IMAGE_NAME="${REGISTRY_NAME}/gateway-${_ARCH}:${BUILD_TAG}"

    if [[ ${_ARCH} == "arm" ]]
    then
        DOCKER_BASE=wirepas/base:1.1-raspbian
        CROSS_BUILD_START_CMD=cross-build-start
        CROSS_BUILD_END_CMD=cross-build-end
    else
        DOCKER_BASE=wirepas/base:1.1-ubuntu
        CROSS_BUILD_START_CMD=:
        CROSS_BUILD_END_CMD=:
    fi

    echo "building ${_PATH}: ${IMAGE_NAME} (from: ${DOCKER_BASE})"
    #shellcheck disable=SC2086
    docker-compose -f "${_PATH}" \
                   build ${_CACHE} \
                   --compress \
                   --parallel \

}


function _fetch_dependencies
{
    # pull repository dependency
    GIT_MANIFEST_FILE=gateway.xml
    GIT_MANIFEST_URL=https://github.com/wirepas/manifest.git
    GIT_MANIFEST_BRANCH=master
    _ROOT_PATH=$(pwd)

    LXGW_SERVICES_HASH="$(git log -n1 --pretty=%h)"

    rm -rf "${GIT_REPO_FOLDER}"
    mkdir "${GIT_REPO_FOLDER}"
    cd "${GIT_REPO_FOLDER}"
    pipenv run --two repo init \
               -u "${GIT_MANIFEST_URL}" \
               -m "${GIT_MANIFEST_FILE}" \
               -b "${GIT_MANIFEST_BRANCH}" \
               --no-clone-bundle
    pipenv --rm
    pipenv run --two repo sync
    cd "sink_service/"
    LXGW_C_MESH_API_HASH="$(git log -n1 --pretty=%h)"
    cd "${_ROOT_PATH}"
    cp -r "${GIT_REPO_FOLDER}/sink_service/" .
}


##
## @brief      What this script will do when it is executed
##
function _main
{

    # builds x86 and arm images based on manifest files
    if [[ ! -z ${BUILD_TAG} ]]
    then
        GIT_MANIFEST_BRANCH=${BUILD_TAG}
        _build "${DOCKERFILE_PATH}/stable/arm/docker-compose.yml" "arm" "--no-cache"
        _build "${DOCKERFILE_PATH}/stable/x86/docker-compose.yml" "x86" "--no-cache"
    else
        BUILD_TAG="edge"
    fi

    # builds x86 and arm images based on top of current revision
    if [[ -z ${SKIP_PULL} ]]
    then
        _fetch_dependencies
    fi
    _build "${DOCKERFILE_PATH}/dev/docker-compose.yml" "arm"
    _build "${DOCKERFILE_PATH}/dev/docker-compose.yml" "x86"
}


_main "${@}"
