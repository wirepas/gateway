#!/usr/bin/env bash
# Wirepas Oy

set -e


# _import_modules
#
# fetch fucntions from the modules folder
function _import_modules
{
        for CFILE in $(ls ${ENV_BASH_MODULES_PATH}/*.sh)
        do
            echo "importing module ${CFILE}"
            source ${CFILE} || true
        done
}


function _defaults
{

    ENV_MAKE_BUILD=${ENV_MAKE_BUILD:-"true"}
    ENV_BASH_MODULES_PATH=${ENV_BASH_MODULES_PATH:-"./modules"}

    export ENV_DISTRO=${ENV_DISTRO:-"all"}
    export ENV_GIT_PULL_REPO=${ENV_GIT_PULL_REPO:-"true"}
    export ENV_DOCKER_IMG=${ENV_DOCKER_IMG:-"wm-gateway"}
    export ENV_DOCKER_TAG=${ENV_DOCKER_TAG:-"1.1.0"}
    export ENV_DOCKER_CACHE=${ENV_DOCKER_CACHE:-" "}
    export ENV_RELEASE_PATH=$(pwd)/release

    export TAR_EXCLUDE_RULES=${TAR_EXCLUDE_RULES:-"$(pwd)/.tarignore"}
    export TAR_ARCHIVE_NAME=${TAR_ARCHIVE_NAME:-"docker-wm-gateway.tar.gz"}
}


function _prepare_environment
{
    # prepares script environment
    mkdir -p ${ENV_RELEASE_PATH}
    rm -f ${TAR_ARCHIVE_NAME}
}


##
## @brief      What this script will do when it is executed
##
function _main
{
    _defaults
    _import_modules

    lxgw_parser "${@}"

    _prepare_environment

    if [[ ${ENV_MAKE_BUILD} == "true" ]]
    then

        if [[ ${ENV_GIT_PULL_REPO} == "true" ]]
        then
            git_clone_repo "c-mesh-api" "sink_service/c-mesh-api"
            git_clone_repo "backend-apis" "public-apis"
        else
            echo "skipping repo pull"
        fi

        git_commit_info
        lxgw_build_services
    fi

    lxgw_deliverables
}


_main "${@}"

