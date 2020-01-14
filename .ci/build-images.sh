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
export GIT_MANIFEST_FILE
export GIT_MANIFEST_URL
export GIT_MANIFEST_BRANCH
export LXGW_C_MESH_API_HASH
export LXGW_SERVICES_HASH
export BUILD_TAG

SKIP_PULL=${1:-}

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
        DOCKER_BASE=ubuntu:19.04
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
    if [[ -z "${SKIP_PULL}" ]]
    then
        # pull repository dependency
        GIT_REPO_FOLDER=${1}
        GIT_MANIFEST_FILE=${GIT_MANIFEST_FILE:-"gateway/dev.xml"}
        GIT_MANIFEST_URL=${GIT_MANIFEST_URL:-"https://github.com/wirepas/manifest.git"}
        GIT_MANIFEST_BRANCH=${GIT_MANIFEST_BRANCH:-"master"}

        _ROOT_PATH=$(pwd)

        echo "fetching dependencies from: ${GIT_MANIFEST_URL}/${GIT_MANIFEST_FILE}/${GIT_MANIFEST_BRANCH}"
        _ROOT_PATH=$(pwd)
        rm -rf "${GIT_REPO_FOLDER}"
        mkdir "${GIT_REPO_FOLDER}"
        cd "${GIT_REPO_FOLDER}"
        git config --global color.ui true
        pipenv run --two repo init \
                   -u "${GIT_MANIFEST_URL}" \
                   -m "${GIT_MANIFEST_FILE}" \
                   -b "${GIT_MANIFEST_BRANCH}" \
                   --depth 2 \
                   --no-tags \
                   --no-clone-bundle
        pipenv --rm
        pipenv run --two repo sync
        cd "${_ROOT_PATH}"
    fi
}


##
## @brief      What this script will do when it is executed
##
function _main
{

    # builds x86 and arm images based on manifest files
    if [[ ! -z "${BUILD_TAG}" ]]
    then

        GIT_MANIFEST_FILE=gateway/stable.xml
        GIT_MANIFEST_BRANCH=refs/tags/gateway/${BUILD_TAG}

        REPO_STABLE=".ci/_repo_stable"
        _fetch_dependencies "${REPO_STABLE}"

        LXGW_SERVICES_HASH="$(git -C ${REPO_STABLE}/ log -n1 --pretty=%h)"
        LXGW_C_MESH_API_HASH="$(git -C ${REPO_STABLE}/sink_service/c-mesh-api log -n1 --pretty=%h)"

        _build "${DOCKERFILE_PATH}/stable/arm/docker-compose.yml" "arm" "--no-cache"
        _build "${DOCKERFILE_PATH}/stable/x86/docker-compose.yml" "x86" "--no-cache"
    else
        BUILD_TAG="edge"
        GIT_MANIFEST_BRANCH=master

        # builds x86 and arm images based on top of current revision
        REPO_EDGE=".ci/_repo_edge"
        _fetch_dependencies "${REPO_EDGE}"

        LXGW_SERVICES_HASH="$(git log -n1 --pretty=%h)"
        LXGW_C_MESH_API_HASH="$(git -C ${REPO_EDGE}/sink_service/c-mesh-api log -n1 --pretty=%h)"

        # we want to copy the current changes (not what is in cr)
        cp -vr "${GIT_REPO_FOLDER}/sink_service/c-mesh-api" "sink_service"
        _build "${DOCKERFILE_PATH}/dev/docker-compose.yml" "arm"
        _build "${DOCKERFILE_PATH}/dev/docker-compose.yml" "x86"
    fi


}


_main "${@}"
