#!/usr/bin/env bash
# Wirepas Oy


##
## @brief      Parses automation options for the lxgw project
##
function lxgw_parser
{
    # Gather commands
    while [[ "${#}" -gt 0 ]]
    do
    key="${1}"
    case "${key}" in
        --architecture)
        ENV_DISTRO="${2}"
        shift
        shift
        ;;
        --image|--name)
        ENV_DOCKER_IMG="${2}"
        shift
        shift
        ;;
        --skip-clone)
        ENV_GIT_PULL_REPO="false"
        shift
        ;;
        --no-cache)
        ENV_DOCKER_CACHE="--no-cache"
        shift
        ;;
        --version|--tag)
        ENV_DOCKER_TAG="${2}"
        shift
        shift
        ;;
        --debug)
        set -x
        shift
        ;;
        *)
        echo "Unknown argument : ${1}"
        _print_help
        exit 1
    esac
    done
}



##
## @brief      generated wheel files from the repos
##
function lxgw_generate_wheels
{
    _output_path=${1:-"./release/ńative"}

    echo "fetching from repo"

    cd "public-apis/python"
    ./utils/generate_wheel.sh
    cd ..

    cd "python_transport"
    ./utils/generate_wheel.sh
    cd ..

    lxgw_copy_transport_service
}



##
## @brief      copies the sink service files
##
function lxgw_copy_sink_service
{
    rsync -av  sink_service ${LXGW_DOCKER_DELIVERABLE_PATH}/ \
          --exclude sink_service/.git \
          --exclude sink_service/build \
          --exclude sink_service/c-mesh-api/.git \
          --exclude sink_service/c-mesh-api/build \
          --exclude sink_service/c-mesh-api@tmp
}


##
## @brief      copy the transport service wheel and its dependencies
##
function lxgw_copy_transport_service
{
    _output_path=${1:-"./release/ńative"}

    cp ./public-apis/python/dist/* ${_output_path}/transport_service/
    cp ./python_transport/dist/* ${_output_path}/transport_service/
}


##
## @brief      fetches deliverables from x86 builds
##
function lxgw_deliverables
{
    LXGW_DOCKER_DELIVERABLE_PATH=${1:-"$(pwd)/deliverable"}

    rm -rf ${ENV_RELEASE_PATH}

    # docker part
    # it will handle the wheel and tar fetching
    lxgw_docker_deliverable ${LXGW_DOCKER_DELIVERABLE_PATH}

    # native part
    # Copy the sink service code and ensures
    mkdir -p ${ENV_RELEASE_PATH}/native/transport_service
    cp -r  ${LXGW_DOCKER_DELIVERABLE_PATH}/transport_service ${ENV_RELEASE_PATH}/native/
    cp -r  ${LXGW_DOCKER_DELIVERABLE_PATH}/sink_service ${ENV_RELEASE_PATH}/native
    rm -fr  ${LXGW_DOCKER_DELIVERABLE_PATH}/native/sink_service/build


    # Copy the proto files
    mkdir ${ENV_RELEASE_PATH}/protocol_buffers_files
    cp -r public-apis/gateway_to_backend/protocol_buffers_files ${ENV_RELEASE_PATH}/

    # copy documentation folder
    if [[ ${LXGW_INCLUDE_DOCS} == "true" ]]
    then
        ./utils/fetch_docs.sh
    fi

    # generates intruction files
    rst2pdf deliverable/instructions.rst -o ${ENV_RELEASE_PATH}/docker/README.pdf
    md2pdf README.md ${ENV_RELEASE_PATH}/native/README.pdf


    # generate archive with release
    rm -f ${ENV_DOCKER_IMG}_${ENV_DOCKER_TAG}.7z
    7z a -t7z ${ENV_DOCKER_IMG}_${ENV_DOCKER_TAG}.7z ${ENV_RELEASE_PATH}/*

}

