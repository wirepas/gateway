#!/usr/bin/env bash
# Wirepas Oy

set -e

DOCKERFILE_PATH="./container"
GIT_REPO_FOLDER="_repo"

##
## @brief      Changes to the corresponding target and builds the image
##
function _build
{
    TARGET=${1:-"dev"}

    if [[ ${TARGET} == "dev" ]]
    then
        _pull_dev_dependencies
    fi

    cd "${DOCKERFILE_PATH}/${TARGET}"
    docker-compose build
}

##
## @brief      Setup repo and syncs the repositories
##
function _pull_dev_dependencies
{
    GIT_MANIFEST_FILE=${GIT_MANIFEST_FILE:-"gateway.xml"}
    GIT_MANIFEST_URL=${GIT_MANIFEST_URL:-"https://github.com/wirepas/manifest.git"}

    rm -rf "${GIT_REPO_FOLDER}"
    mkdir "${GIT_REPO_FOLDER}"
    cd "${GIT_REPO_FOLDER}"
    pipenv run --two repo init -u "${GIT_MANIFEST_URL}" \
                 -m "${GIT_MANIFEST_FILE}" \
                 --no-clone-bundle
    pipenv --rm
    pipenv run --two repo sync

    cd ..
    cp -r "${GIT_REPO_FOLDER}/sink_service/" .
}


##
## @brief      What this script will do when it is executed
##
function _main
{
    #_build "arm"
    #_build "x86"
    _build "dev"
}


_main "${@}"
