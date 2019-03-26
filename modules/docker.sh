#!/usr/bin/env bash
# Wirepas Oy

##
## @brief      copies the sink service files
##
function lxgw_fetch_transport_service
{
    _host_path=${1}

    ENV_DOCKER_IMG=${ENV_DOCKER_IMG:-"gateway"}
    ENV_DOCKER_TAG=${ENV_DOCKER_TAG:-"latest"}

    _copy_path="/home/wirepas/dist/transport_service"

    docker run \
        --rm  \
        --user root \
        -w /home/wirepas \
        -v ${_host_path}:/home/wirepas/dist \
        --entrypoint /bin/bash \
        ${ENV_DOCKER_IMG}:${ENV_DOCKER_TAG} \
        -c " set +e; \
             set -x; \
             mkdir ${_copy_path}
             cp -vr /home/wirepas/dependencies/*whl ${_copy_path};\
             cp -vr /home/wirepas/dependencies/*tar* ${_copy_path};\
             cp -vr /home/wirepas/gateway/transport_service/*whl ${_copy_path}; \
             cp -vr /home/wirepas/gateway/transport_service/*tar* ${_copy_path}; \
             chown wirepas:wirepas -R /home/wirepas/dist"

}


##
## @brief      prepares the docker deliverable
##
function lxgw_docker_deliverable
{
    REMOVE_ARCH_WHEEL=${REMOVE_ARCH_WHEEL:-"true"}

    rm -fr ${LXGW_DOCKER_DELIVERABLE_PATH}/sink_service/
    rm -fr ${LXGW_DOCKER_DELIVERABLE_PATH}/transport_service/
    rm -fr ${LXGW_DOCKER_DELIVERABLE_PATH}/utils/

    mkdir -p ${ENV_RELEASE_PATH}/docker

    lxgw_copy_sink_service
    lxgw_fetch_transport_service ${LXGW_DOCKER_DELIVERABLE_PATH}
    lxgw_copy_docker_deliverable_utils


    if [[ ${REMOVE_ARCH_WHEEL} == "true" ]]
    then
        rm -f ${LXGW_DOCKER_DELIVERABLE_PATH}/transport_service/*86_64*
        rm -f ${LXGW_DOCKER_DELIVERABLE_PATH}/transport_service/*arm*
    fi

    pack_docker_deliverable
    mv ${TAR_ARCHIVE_NAME} ${ENV_RELEASE_PATH}/docker

}


##
## @brief      copies utilities necessary for the docker deliverable
##
function lxgw_copy_docker_deliverable_utils
{
    mkdir -p ${LXGW_DOCKER_DELIVERABLE_PATH}/utils/
    cp ./python_transport/wirepas_gateway/wirepas_certs/extwirepas.pem ${LXGW_DOCKER_DELIVERABLE_PATH}/utils/
    cp ./sink_service/com.wirepas.sink.conf ${LXGW_DOCKER_DELIVERABLE_PATH}/utils/
    cp ./container/docker-entrypoint.sh ${LXGW_DOCKER_DELIVERABLE_PATH}/utils/

    sed -i "s#user=\"wirepas\"#user=\"root\"#" ${LXGW_DOCKER_DELIVERABLE_PATH}/utils/com.wirepas.sink.conf
}


##
## @brief      creates a tar ball with the docker deliverable
##
function pack_docker_deliverable
{
    TAR_EXCLUDE_RULES=${TAR_EXCLUDE_RULES:-".tarignore"}
    TAR_ARCHIVE_NAME=${TAR_ARCHIVE_NAME:-"build-with-docker.tar.gz"}
    TAR_TARGET=${TAR_TARGET:-"deliverable/"}

    echo "Creating ${TAR_ARCHIVE_NAME} with contents from ${TAR_TARGET} (excluding ${TAR_EXCLUDE_RULES})"

    rm -rf ${TAR_ARCHIVE_NAME}
    tar -zcvf ${TAR_ARCHIVE_NAME} -C ${TAR_TARGET} .
}


##
## @brief      Prepares a lxgw build for ARMv7l architectures (rpi)
##
function lxgw_arm_build
{
       echo "building arm ${ENV_DOCKER_CACHE}"
    ./container/docker-build.sh --build-defaults container/build_defaults.env \
                                --arm \
                                --build-target wm-lxgw-rpi \
                                --image ${ENV_DOCKER_IMG}-rpi \
                                --tag ${ENV_DOCKER_TAG} \
                                ${ENV_DOCKER_CACHE}
}

##
## @brief      Prepares a lxgw build for x86 architectures
##
function lxgw_x86_build
{
        echo "building x86 ${ENV_DOCKER_CACHE}"
        ./container/docker-build.sh --build-defaults container/build_defaults.env \
                                    --build-target wm-lxgw \
                                    --image ${ENV_DOCKER_IMG} \
                                    --tag ${ENV_DOCKER_TAG} \
                                    ${ENV_DOCKER_CACHE}
}


##
## @brief      Wrapper to make builds for several platforms
##
function lxgw_build_services
{

    export DOCKER_BUILD_ARGS="--build-arg WM_MESSAGING_PKG=wirepas_messaging-${ENV_DOCKER_TAG}* \
                   --build-arg WM_TRANSPORT_PKG=wirepas_gateway-${ENV_DOCKER_TAG}*"

    if [[ ${ENV_DISTRO} == "arm*" ]]
    then
        lxgw_arm_build
    elif [[ ${ENV_DISTRO} == "x86" ]]
    then
        lxgw_x86_build
    else
        lxgw_x86_build
        lxgw_arm_build
    fi
}

