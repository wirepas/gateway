#!/usr/bin/env bash
# Wirepas Oy

trap 'echo "Aborting due to errexit on line $LINENO. Exit code: $?" >&2' ERR

set -o nounset
set -o errexit
set -o errtrace

_ME=$(basename "${0}")
WM_RPI_CFG_TEMPLATE_PATH="."

_print_help() {
  cat <<HEREDOC
Builder and application flasher for Wirepas

Usage:
  ${_ME} [<arguments>]
  ${_ME} -h | --help
  ${_ME} --docker --build --flash --log

Options:
  -h --help        Show this screen
  --device         String of devices to setup, eg, "/dev/ttyACM0 /dev/ttyACM1" (default: ${DEVICE_ARRAY})
  --device_type    String of devices types to look up eg, "/dev/ttyACM /dev/ttyUSB" (default: ${DEVICE_TYPE})
  --image          Docker image name to use (default: ${WM_LXGW_IMAGE})
  --version        Docker tag version to use (default: ${WM_LXGW_VERSION})
  --recreate       Forces the containers to be recreated from scratch (default: ${RECREATE})
  --skip_pull      Skips the aws login and pull action (default: ${SKIP_PULL})
HEREDOC
}

# _defaults
#  Sets default value for parameters, cmd line setters will take precedence
_defaults()
{
    WM_RPI_CUSTOM_ENV="settings.env"
    DEVICE_TYPE=( "/dev/ttyACM" "/dev/ttyUSB" )
    DEVICE_ARRAY=(" ")
    RECREATE=""

    set -o allexport

    set +e
    dos2unix ${WM_RPI_CUSTOM_ENV}
    set -e

    source ${WM_RPI_CUSTOM_ENV}

    set +o allexport
}


# _template_copy
# Evaluates the template into the desired target file
function _template_copy
{
    # input name is basename
    TEMPLATE_NAME=${1:-"defaults"}
    OUTPUT_PATH=${2:-"template.output"}

    # if set, changes the output filename
    TEMPLATE=${WM_RPI_CFG_TEMPLATE_PATH}/${TEMPLATE_NAME}.template

    echo "generating ${OUTPUT_PATH} based on ${TEMPLATE}"
    rm -f ${OUTPUT_PATH} ${OUTPUT_PATH}.tmp
    ( echo "cat <<EOF >${OUTPUT_PATH}";
      cat ${TEMPLATE};
      echo "EOF";
    ) > ${OUTPUT_PATH}.tmp
    . ${OUTPUT_PATH}.tmp
    rm ${OUTPUT_PATH}.tmp
}

# _template_append
# Evaluates the template but instead of overwriting the output the contents
# are appended to it
function _template_append
{
    # input name is basename
    TEMPLATE_NAME=${1:-"defaults"}
    OUTPUT_PATH=${2:-"template.output"}

    # if set, changes the output filename
    TEMPLATE=${WM_RPI_CFG_TEMPLATE_PATH}/${TEMPLATE_NAME}.template

    echo "generating ${OUTPUT_PATH} based on ${TEMPLATE}"
    rm -f  ${OUTPUT_PATH}.tmp
    ( echo "cat <<EOF >>${OUTPUT_PATH}";
      cat ${TEMPLATE};
      echo "EOF";
    ) > ${OUTPUT_PATH}.tmp
    . ${OUTPUT_PATH}.tmp
    rm ${OUTPUT_PATH}.tmp
}



# _parse
#  Evaluates command line parameters
_parse()
{
    # Gather commands
    POSITIONAL=()
    while [[ $# -gt 0 ]]
    do
    key="$1"

    case $key in
        --device)
        echo "setting device: ${2}"
        DEVICE_ARRAY=(${2})
        shift # past argument
        shift
        ;;
        --device_type)
        echo "setting device_type: ${2}"
        DEVICE_TYPE=(${2})
        shift # past argument
        shift
        ;;
        --version)
        echo "setting version: ${2}"
        WM_LXGW_VERSION=${2}
        shift # past argument
        shift
        ;;
        --image)
        echo "setting image: ${2}"
        WM_LXGW_IMAGE=${2}
        shift # past argument
        shift
        ;;
        --recreate)
        echo "setting force recreate"
        RECREATE="--force-recreate"
        shift # past argument
        ;;
        --skip_pull)
        echo "setting skip_pull=true"
        SKIP_PULL=true
        shift # past argument
        ;;
        --help|-h)
        _print_help
        exit 0
        ;;
        *)
        echo "unknown parameter: ${1}"
        exit 1
    esac
    done
}

# _lookup_devices
#  Iterates local devices
_generate_device_service()
{
    PORT_RULE=${1}

    echo "Looking up devices ${PORT_RULE} ...";
    PORTS=($(ls ${PORT_RULE})) || true
    PORTS=${PORTS:-""}

    if [ ! -z ${PORTS} ]
    then
        echo "found ${PORTS} ...";
        for DEVICE in ${PORTS[@]}
        do
            if [ ! -z ${DEVICE_ARRAY} ]
            then
                for ALLOW_DEVICE in  ${DEVICE_ARRAY[@]}
                do
                    if [ ${ALLOW_DEVICE} == ${DEVICE} ]
                    then
                        echo "Found sink and device match (${ALLOW_DEVICE} == ${DEVICE})"
                        break
                    fi
                done
                echo "Skipping ${DEVICE} as it is not allowed (set sinks)"
                continue
            fi

            # apply filter based on input
            DEVICE_ID="${DEVICE//[!0-9]/}"

            WM_SINK_UART_PORT_SERVICE_NAME=$(echo ${PORT_RULE}| sed -e "s#/dev/##" | sed 's/[0-9]//g')
            WM_SINK_UART_PORT=${DEVICE}
            WM_SINK_UART_BITRATE=125000
            WM_SINK_ID=${DEVICE_ID}

            _template_append sink docker-compose.yml

        done
    fi
}


# _launch_services
#  Starts the transport and sink services
_launch_services()
{

    if [ ${SKIP_PULL} == "false" ]
    then
        echo "pulling latest changes for ${WM_LXGW_IMAGE}:${WM_LXGW_VERSION}"
        aws ecr get-login --region eu-central-1 --no-include-email|sh
        docker pull ${WM_LXGW_IMAGE}:${WM_LXGW_VERSION}
    fi

    echo "starting gateway services"
    docker-compose up -d ${RECREATE} --remove-orphans
}


# _setup_services
#  Evaluates the templates and available devices
_setup_services()
{

    echo "setting up services"

    _template_copy transport docker-compose.yml

    for TYPE in ${DEVICE_TYPE[@]}
    do
        _generate_device_service "${TYPE}*"
    done
}



# _main
#  The main execution loop
_main()
{
    _defaults

    _parse "${@}"
    _setup_services
    _launch_services

    exit 0
}

# main call
_main "${@}"
