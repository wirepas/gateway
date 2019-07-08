#!/usr/bin/env bash
# Wirepas Oy

set -e

DOCKERFILE_PATH="./container"

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

    curl https://storage.googleapis.com/git-repo-downloads/repo > /usr/local/bin/repo
    chmod a+x /usr/local/bin/repo
    repo init -u "${GIT_MANIFEST_URL}" \
                 -m "${GIT_MANIFEST_FILE}" \
                 --no-clone-bundle
    repo sync
}


##
## @brief      What this script will do when it is executed
##
function _main
{
    # _build "rpi"
    # _build "x86"
    _build "dev"
}


_main "${@}"
