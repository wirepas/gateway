#!/usr/bin/env bash
# Copyright 2019 Wirepas Ltd

set -e

export VERSION
export BUILD_DATE
export IMAGE_NAME
export REGISTRY_NAME
export DOCKER_BASE
export CROSS_BUILD_START_CMD
export CROSS_BUILD_END_CMD
export LXGW_C_MESH_API_HASH
export LXGW_SERVICES_HASH
export BUILD_TAG

VERSION=$(< python_transport/wirepas_gateway/__about__.py awk '/__version__/{print $NF}'| tr -d '\"')
BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
REGISTRY_NAME="wirepas"

DOCKERFILE_PATH="./container"
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
        DOCKER_BASE=balenalib/raspberrypi3
        CROSS_BUILD_START_CMD=cross-build-start
        CROSS_BUILD_END_CMD=cross-build-end
    else
        DOCKER_BASE=ubuntu:20.04
        CROSS_BUILD_START_CMD=:
        CROSS_BUILD_END_CMD=:
    fi

    echo "building ${_PATH}: ${IMAGE_NAME} (from: ${DOCKER_BASE})"

    # to speed up builds
    docker pull "${IMAGE_NAME}" || true

    #shellcheck disable=SC2086
    docker-compose -f "${_PATH}" \
                   build ${_CACHE} \
                   --compress \
                   --parallel \

}


function _fetch_dependencies
{
	# Only dependency is c-mesh-api managed by git submodule
	git submodule update --init
}


##
## @brief      What this script will do when it is executed
##
function _main
{
    if [[ -z "${BUILD_TAG}" ]]
    then
        BUILD_TAG="edge"
    fi

    # builds x86 and arm images based on current repository version
    _fetch_dependencies

    LXGW_SERVICES_HASH="$(git log -n1 --pretty=%h)"
    LXGW_C_MESH_API_HASH="$(git -C sink_service/c-mesh-api log -n1 --pretty=%h)"

    _build "${DOCKERFILE_PATH}/dev/docker-compose.yml" "arm"
    _build "${DOCKERFILE_PATH}/dev/docker-compose.yml" "x86"

}


_main "${@}"
