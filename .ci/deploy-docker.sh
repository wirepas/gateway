#!/usr/bin/env bash
# Wirepas Oy

export DOCKER_CLI_EXPERIMENTAL=enabled

DOCKER_TAG=${TRAVIS_TAG:-"edge"}
IS_RELEASE=${TRAVIS_TAG:-"false"}

DOCKER_USERNAME=${DOCKER_USERNAME}
DOCKER_PASSWORD=${DOCKER_PASSWORD}
DOCKER_ORG=${DOCKER_ORG:-"wirepas"}
DOCKER_IMAGE=${DOCKER_IMAGE:-"gateway"}


function _remove_manifest()
{
    rm -rf ~/.docker/manifests/docker.io_wirepas_gateway*/ || true
}

function _push
{
    _TAG=${1}

    # push images and manifest
    docker push wirepas/gateway-x86:"${_TAG}"
    docker push wirepas/gateway-arm:"${_TAG}"
    docker push wirepas/gateway:"${_TAG}"
}

function _create_manifest()
{
    _TAG=${1}

    # creates the manifest for x86 and ARM
    docker manifest create wirepas/gateway:"${_TAG}" \
                           wirepas/gateway-x86:"${_TAG}" \
                           wirepas/gateway-arm:"${_TAG}"

    # sets the correct platform for rpi
    docker manifest annotate wirepas/gateway:"${_TAG}" \
                             wirepas/gateway-arm:"${_TAG}" \
                             --arch arm
}

function _tag_latest()
{
    docker tag wirepas/gateway-x86:"${_TAG}" wirepas/gateway-x86:latest
    docker tag wirepas/gateway-arm:"${_TAG}" wirepas/gateway-arm:latest
}


function _main()
{
    echo "${DOCKER_PASSWORD}" | docker login -u "${DOCKER_USERNAME}" --password-stdin

    _remove_manifest
    _create_manifest "${DOCKER_TAG}"
    _push "${DOCKER_TAG}"

    if [[ "${IS_RELEASE}" != "false" ]]
    then
        _remove_manifest
        _tag_latest
        _create_manifest "latest"
        _push "latest"
    fi
}

_main "$@"
