# Wirepas Linux Gateway

[![Codacy Badge](https://api.codacy.com/project/badge/Grade/ebb45a6a13ec4f2c88131ddf51a9579a)](https://www.codacy.com/manual/wirepas/gateway?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=wirepas/gateway&amp;utm_campaign=Badge_Grade) [![Build Status](https://travis-ci.com/wirepas/gateway.svg?branch=master)](https://travis-ci.com/wirepas/gateway)

<!-- MarkdownTOC levels="1,2" autolink="true"  -->

- [Installing a Gateway](#installing-a-gateway)
- [Option 1: native installation](#option-1-native-installation)
- [Option 2: Docker installation](#option-2-docker-installation)
- [Contributing](#contributing)
- [License](#license)

<!-- /MarkdownTOC -->

This repository contains Wirepas' reference gateway implementation, which
relies on a set of services to exchange data from/to a Wirepas Mesh network
from/to a MQTT broker or host device. The implemented API is described
[here][wirepas_gateway_to_backend_api].

The services will be known from now on as sink service and transport service.
The sink service is responsible to interface locally with a Wirepas device
running its Dual MCU API. The transport service packs network
messages on protobuffers and publishes them on top of MQTT according to
Wirepas Backend API.

Figure 1, provides an overview of the gateway implementation and the
apis involved at each step.

![Wirepas gateway architecture][here_img_overview]

**Figure 1 -** Gateway services overview.

## Installing a Gateway

Multiple options are available depending on your need.
They are all described in the following sections:

- [Option 1: native installation](#option-1-native-installation)
  - [Option 1.1](#option-11): from source code\
    This option should be used if you plan to do modification on this reference code
  - [Option 1.2](#option-12): from pre-built binaries\
    This option should be used if you want to use a standard gateway without modification
- [Option 2: Docker installation](#option-2-docker-installation)
  - [Option 2.1](#option-21): by building your own docker image\
    This option should be used if you plan to do modification and create your own docker images
  - [Option 2.2](#option-22): by using Wirepas docker hub images\
    This option should be used if you plan to use docker with Wirepas images from docker hub without modification

## Option 1: native installation

This section covers both option 1.1 and 1.2 and some sections are
only relevant for one of these options.

### Requirements

The implementation is based on DBus. The C binding used to access DBus is sdbus
from systemd library so even if systemd is not required to be running, the
libsystemd must be available.

Systemd version must be higher or equal to *221*. You can check it with:

```shell
    systemd --version
```

In order to build the sink service and the transport python wheel that contains C extensions, systemd headers are needed

```shell
    sudo apt install libsystemd-dev
```

Python 3 and a recent pip version (>= 18.1)

```shell
    sudo apt install python3 python3-dev python3-gi
    wget https://bootstrap.pypa.io/get-pip.py \
       && sudo python3 get-pip.py && rm get-pip.py \
       && sudo pip3 install --upgrade pip
```

### Getting the sources (option 1.1 only)

This repository depends on two other projects, [c-mesh-api][wirepas_c_mesh_api]
and [backend-apis][wirepas_backend_apis].

The [c-mesh-api][wirepas_c_mesh_api] contains the library used by the sink
service, which interfaces
with the sink devices. The backend-apis contains api and message wrapper
over the protocol buffers that are transmitted over MQTT.

We are currently using the [repo tool][repo_tool] to upkeep the project
dependencies and for that reason we recommend that you use it as well.

The manifest files are located in at the
[manifest repository][wirepas_manifest] and are organized inside the
gateway folder as follows:

-   dev.xml: points to the development branches, intended for collaborators
-   stable.xml: points to the latest release

If you wish to pull the latest release then use the following command:

```shell
    repo init -u https://github.com/wirepas/manifest.git \
              -m gateway/stable.xml \
              --no-clone-bundle
```

and if you wish to track the development branches, please use

```shell
    repo init -u https://github.com/wirepas/manifest.git \
              -m gateway/dev.xml \
              --no-clone-bundle
```

afterwards download the repositories with

```shell
    repo sync
```

To clone a particular version, vX.Y.Z, please specify the tag with the
 *-b* switch and use the stable manifest:

```shell
    repo init (...) -m gateway/stable.xml -b refs/tags/vX.Y.Z
```

Usage of repo is also documented in our
[ci build scripts][here_ci_docker_build]. Please read more on
the repo tool usage from [its official documentation][repo_tool].

### Installation

#### Sink service

The implementation uses system bus that has enforced security.
In order to obtain a service name on system bus, the user launching the sink
service must be previously declared to system.
Provided file *com.wirepas.sink.conf* inside sink_service folder
must be copied under */etc/dbus-1/system.d/* and edited with the user that will
launch the sink_service (and transport service).

To change the default wirepas user, please edit the following lines
from com.wirepas.sink.conf:

```xml
    <!-- Only wirepas user can own the service name -->
    <policy user="wirepas">
```

*It is recommended to restart your gateway once this file is copied.*

##### Option 1.1: from source code

Sink service is written in C and can be built with following command from
sink_service folder:

```shell
    make
```
##### Option 1.2: from pre-built binaries

Sink service prebuilt version is available on [this page][here_releases] from assets section.
Download the one for your architecture (Arm or x86)

#### Transport service

##### Option 1.1: from source code

To build the wheel yourself, please refer to the
[transport's service readme file][here_transport_readme].

##### Option 1.2: from pre-built binaries

Transport service is implemented in python 3 and is delivered as a
Python wheel, either through [PyPi][wirepas_gateway_pypi] or the
[release section of this repository][here_releases].

The library contains a c extension which will be compiled upon installation.
Please ensure that you have met all the build requirements prior to
attempting the installation with:

If you get the wheel from [release section of this repository][here_releases]:

```shell
    pip3 install wirepas_gateway-*.tar.gz
```

or from [PyPi][wirepas_gateway_pypi]

```shell
    pip3 install wirepas_gateway
```

### Configuration and starting services

#### Sink service configuration

A sink service must be started for each connected sink on Gateway:

```shell
    sink_service/build/sinkService -p <uart_port> -b <bitrate> -i <sink_id>
```

Parameters are:

-   **uart_port:** uart port path (*default:* /dev/ttyACM0)
-   **bitrate:** bitrate of sink uart (*default:* 125000)
-   **sink_id:** value between 0 and 9 (*default:* 0).

If multiple sinks are present, they must have a different *sink_id*.

#### Transport service configuration

Parameters can be set from command line or from a setting file in YAML format.
To get an the full list of parameters, please run:

```shell
    wm-gw --help
```

#### From command line

Here is an example to start the transport module from the command line:

```shell
    wm-gw \
          --mqtt_hostname "<server>" \
          --mqtt_port <port> \
          --mqtt_username <user> \
          --mqtt_password <password> \
          [--mqtt_force_unsecure] \
          --gateway_id <gwid> \
          [--ignored_endpoints_filter <ignored endpoints list>] \
          [--whitened_endpoints_filter <whitened endpoints list>]
```

where:

-   **mqtt_hostname:** Hostname or IP where the MQTT broker is located

-   **mqtt_port:** MQTT port

-   **mqtt_username:** MQTT user

-   **mqtt_password:** MQTT password

-   **mqtt_force_unsecure:** Toggle to disable TLS handshake.
Necessary to establish connections to unsecure port (default: 1883).

-   **gateway_id:** The desired gateway id, instead of a random generated one

    > It must be unique for each gateway reporting to same broker

-   **ignored_endpoints_filter:** destination endpoints list to ignore
                               (not published)

    *Example:*
        To filter out destination endpoints  1, 2, 10, 11, 12:

    ```shell
        --ignored_endpoints_filter "[1,2, 10-12]"
    ```

-   **whitened_endpoints_filter:** destination endpoints list to whiten
                                 (no payload content, only size)

    *Example:*
        To whiten destination ep 1, 2, 10, 11, 12
    ```shell
        --whitened_endpoints_filter "[1,2, 10-12]"
    ```

#### From configuration file

```shell
    wm-gw --settings=settings_files.yml
```

All parameters that are accepted by the transport service can be set
through the settings file. An example of a *settings_file.yml*
file is given below:

```yaml
    #
    # MQTT brocker Settings
    #
    mqtt_hostname: <IP or hostname where the MQTT broker is located>
    mqtt_port: <MQTT port (default: 8883 (secure) or 1883 (local))>
    mqtt_username: <MQTT user>
    mqtt_password: <MQTT password>
    mqtt_force_unsecure: <true | false>

    #
    # Gateway settings
    #
    gateway_id: <The desired gateway id, must be unique for each gateway>
    gateway_model: <Custom gateway model, can be omitted>
    gateway_version: <Custom gateway version, can be omitted>

    #
    # Filtering Destination Endpoints
    #
    ignored_endpoints_filter: <Endpoints to filter out. Ex: [1, 2, 10-12]>
    whitened_endpoints_filter: <Endpoints to whiten. Ex: [1, 2, 10-12]>
```

#### Optional

##### Start services with systemd

Please see this [Wiki entry][here wiki systemd]

##### See local messages on Dbus interface

Launch local gateway process to see messages received from sinks at Dbus
level. It can be launched from the command line with:

```shell
    wm-dbus-print
```

## Option 2: Docker installation

The Docker gateway approach of Wirepas is to have a single container able
to run one of the two services (sink service or transport service).
A docker container will be started for each service.
For example, if you have a gateway with two sinks and one transport
service, three containers will be started
(one for each sink and one for the transport service).
Communication between docker containers will happen on the host Dbus.

### Getting the docker image

#### Option 2.1: by building your own docker image

In the [container][here_container] folder you will find two folder,
dev and stable. The dev folder contains a composition file with a preset
of settings to build an image based on your local repository
(assumes the c-mesh-api project is cloned within sink_service).

The stable folder contains architecture specific folder, x86 and ARM.
Within the folder you will find a composition file which contains the
default relevant settings. In this case, the difference resides on the
path to the source files and the definition of the base image.

All of these composition files build the images based on the
same [Dockerfile][here_container_dockerfile].

If you have cloned the repository through the repo manifest, you can
make a development build with:

```bash
    [IMAGE_NAME=wirepas/gateway:edge] docker-compose -f container/dev/docker-compose.yml build
```

If you only have the gateway repository cloned locally, you can follow the
same build procedures as our ci. For that, run the
[.ci/build-images.sh][here_ci_docker_build] script from the root
of the repository.

#### Option 2.2: by using Wirepas docker hub images

Our pre-built images are available on docker hub under the
following registry:

-   [wirepas/gateway][dockerhub_wirepas]: multi architecture registry

### Starting docker services

When running the gateway over docker, the composition will mount your host's
system dbus inside each container. This is necessary to allow exchanging data
between both services. For that reason you will have to copy the
[dbus manifest][here_dbus_manifest] to your host's and change the policy
user to reflect what is used within the docker-compose.

After configuring your host's dbus, review the
[environment file][here_container_env] where you can define settings for the
sink and transport service.

The environment parameters will be evaluated by
the [container's entry point][here_container_entrypoint]
and passed on to the sink and transport service.

Please ensure that you define the correct password and MQTT credentials and
launch the services with:

```shell
    [IMAGE_NAME=wirepas/gateway-x86:edge] docker-compose -f container/dev/docker-compose.yml up [-d]
```

To view the logs, use

```shell
    docker-compose -f container/dev/docker-compose.yml logs
```

or specify which container you want to view the logs from with

```shell
    docker logs [container-name]
```

### Using custom TLS certificates within the container

You must ensure that your custom certificate file exists inside the container
where the transport service is running.

You can achieve this by mounting the file using the composition file. Edit
the docker-compose.yml file and add the following statement under the
transport service's volumes section:

```shell
    volumes:
      - (...)
      - /my-tls-file/:/etc/my-tls-file
```

The environment variable, WM_SERVICES_CERTIFICATE_CHAIN, must match
the container path that you picked (*/etc/my-tls-file*).

## Contributing

We welcome your contributions!

Please read the [instructions on how to do it][here_contribution]
and please review our [code of conduct][here_code_of_conduct].

## License

Copyright 2019 Wirepas Ltd licensed under Apache License, Version 2.0 See file
[LICENSE][here_license] for full license details.

[here_contribution]: CONTRIBUTING.md
[here_code_of_conduct]: CODE_OF_CONDUCT.md
[here_license]: LICENSE
[here_img_overview]: img/wm-gateway-overview.png?raw=true
[here_ci_docker_build]: .ci/build-images.sh
[here_releases]: https://github.com/wirepas/gateway/releases
[here_container]: container/
[here_container_dockerfile]: container/Dockerfile
[here_container_env]: container/wm_gateway.env
[here_dbus_manifest]: sink_service/com.wirepas.sink.conf
[here_container_entrypoint]: container/common/docker-entrypoint.sh
[here_transport_readme]: python_transport/README.md
[here wiki systemd]: https://github.com/wirepas/gateway/wiki/How-to-start-a-native-gateway-with-systemd

[repo_tool]: https://source.android.com/setup/develop/repo

[wirepas_manifest]: https://github.com/wirepas/manifest
[wirepas_c_mesh_api]: https://github.com/wirepas/c-mesh-api
[wirepas_backend_apis]: https://github.com/wirepas/backend-client
[wirepas_gateway_to_backend_api]: https://github.com/wirepas/backend-apis/blob/master/gateway_to_backend/README.md
[wirepas_gateway_pypi]: https://pypi.org/project/wirepas-gateway

[dockerhub_wirepas]: https://hub.docker.com/r/wirepas/gateway
