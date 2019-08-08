# Wirepas Linux Gateway

[![Build Status](https://travis-ci.com/wirepas/gateway.svg?branch=master)](https://travis-ci.com/wirepas/gateway)

This repository contains Wirepas' reference gateway implementation, which
relies on a set of services to exchange data from/to a Wirepas Mesh network
from/to a MQTT broker or host device.

The services will be known from now on as sink service and transport service.
The sink service is responsible to interface locally with a Wirepas device
running its Dual MCU API. The transport service packs network
messages on protobuffers and publishes them on top of MQTT according to
Wirepas Backend API.

Figure 1, provides an overview of the gateway implementation and the
apis involved at each step.

![Wirepas gateway architecture][here_img_overview]

**Figure 1 -** Gateway services overview.

## Cloning this repository

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

Usage of repo is also documented in the release
Dockerfiles (see [Dockerfile][here_container_dockerfile]).

Please read more on the repo tool usage from
[its official documentation][repo_tool].

## Linux Requirements

The implementation is based on DBus. The C binding used to access DBus is sdbus
from systemd library so even if systemd is not required to be running, the
libsystemd must be available.

Systemd version must be higher or equal to *221*. You can check it with:

```shell
    systemd --version
```

In order to build the sink service, systemd headers are needed

```shell
    sudo apt install libsystemd-dev
```

Python 3 and a recent pip version (>= 18.1)

```shell
    sudo apt install libsystemd-dev python3 python3-dev python3-gi
    wget https://bootstrap.pypa.io/get-pip.py \
       && sudo python3 get-pip.py && rm get-pip.py \
       && sudo pip3 install --upgrade pip
```

## Installation

### Sink service

Sink service is written in C and can be built with following command from
sink_service folder:

```shell
    make
```

This implementation uses system bus that has enforced security.
In order to obtain a service name on system bus, the user launching the sink
service must be previously declared to system.
Provided file com.wirepas.sink.conf inside sink_service folder
must be copied under /etc/dbus-1/system.d/ and edited with the user that will
launch sink_service (and transport service).

To change the default wirepas user, please edit the following lines
from com.wirepas.sink.conf:

```xml
    <!-- Only wirepas user can own the service name -->
    <policy user="wirepas">
```

*It is recommended to restart your gateway once this file is copied.*

### Transport service

Transport service is implemented in python 3 and is delivered as a
Python wheel, either through [PyPi][wirepas_gateway_pypi] or the
[release section of this repository][here_releases].

The library contains a c extension which will be compile upon installation.
Please ensure that you have met all the build requirements prior to
attempting the installation with:

```shell
    pip3 install wirepas_messaging-*.whl
```
or

```shell
    pip3 install wirepas_gateway-*.tar.gz
```

If you wish to build the wheel yourself, please refer to the
[transport's service readme file][here_transport_readme].

## Configuration and starting services

### Sink service configuration

A sink service must be started for each connected sink on Gateway:

```shell
    sink_service/build/sinkService -p <uart_port> -b <bitrate> -i <sink_id>
```

Parameters are:

-   **uart_port:** uart port path (*default:* /dev/ttyACM0)
-   **bitrate:** bitrate of sink uart (*default:* 125000)
-   **sink_id:** value between 0 and 9 (*default:* 0).

If multiple sinks are present, they must have a different *sink_id*.

### Transport service configuration

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
          --gateway_id <gwid> \
          [--ignored_endpoints_filter <ignored endpoints list>] \
          [--whitened_endpoints_filter <whitened endpoints list>]
```

where:

-   **mqtt_hostname:** Hostname or IP where the MQTT broker is located

-   **mqtt_port:** MQTT port

-   **mqtt_username:** MQTT user

-   **mqtt_password:** MQTT password

-   **gateway_id:** the desired gateway id, instead of a random generated one.

    > It must be unique for each gateway reporting to same broker.

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

    #
    # Gateway settings
    #
    gateway_id: <the desired gateway id, must be unique for each gateway>
    gateway_model: <Custom gateway model, can be omitted>
    gateway_version: <Custom gateway version, can be omitted>

    #
    # Filtering Destination Endpoints
    #
    ignored_endpoints_filter: <Endpoints to filter out. Ex: [1, 2, 10-12]>
    whitened_endpoints_filter: <Endpoints to whiten. Ex: [1, 2, 10-12]>
```

### Optional

Launch local gateway process to see messages received from sinks at Dbus
level. It can be launched from the command line with:

```shell
    wm-dbus-print
```

## Building and running with Docker

In the container folder you will find three folders, one for
[development][here_container]
purposes and two other for architecture images, x86 and arm.

The development folder builds an image based on the contents of the repository,
whereas the other two folder will provide you a build for what is specified
in the repo tool's manifest.

To make a development build type:

```bash
    [IMAGE_NAME=wirepas/gateway-x86:edge] docker-compose -f container/dev/docker-compose.yml build
```

If you want to build a stable image for x86 type:

```bash
    docker-compose -f container/stable/x86/docker-compose.yml build
```

Alternatively you can use our [ci tool][here_ci_docker_build].

We also have pre-built images available from docker hub under the
following registries:

-   [wirepas/gateway][dockerhub_wirepas]: multi architecture registry
-   [wirepas/gateway-x86][dockerhub_wirepas_x86]: x86 architecture registry
-   [wirepas/gateway-arm][dockerhub_wirepas_arm]: arm architecture registry

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

[here_contribution]: https://github.com/wirepas/gateway/blob/master/CONTRIBUTING.md
[here_code_of_conduct]: https://github.com/wirepas/gateway/blob/master/CODE_OF_CONDUCT.md
[here_license]: https://github.com/wirepas/gateway/blob/master/LICENSE
[here_img_overview]: https://github.com/wirepas/gateway/blob/master/img/wm-gateway-overview.png?raw=true
[here_ci_docker_build]: https://github.com/wirepas/gateway/blob/master/.ci/build-images.sh
[here_releases]: https://github.com/wirepas/gateway/releases
[here_container]: https://github.com/wirepas/gateway/tree/master/container/
[here_container_dockerfile]: https://github.com/wirepas/gateway/tree/master/container/Dockerfile
[here_container_env]: https://github.com/wirepas/gateway/tree/master/container/wm_gateway.env
[here_dbus_manifest]: https://github.com/wirepas/gateway/blob/master/sink_service/com.wirepas.sink.conf
[here_container_entrypoint]: https://github.com/wirepas/gateway/blob/master/container/common/docker-entrypoint.sh
[here_transport_readme]: https://github.com/wirepas/gateway/blob/master/python_transport/README.md

[repo_tool]: https://source.android.com/setup/develop/repo

[wirepas_manifest]: https://github.com/wirepas/manifest
[wirepas_c_mesh_api]: https://github.com/wirepas/c-mesh-api
[wirepas_backend_apis]: https://github.com/wirepas/backend-client
[wirepas_gateway_pypi]: https://pypi.org/project/wirepas-gateway

[dockerhub_wirepas]: https://hub.docker.com/r/wirepas/gateway
[dockerhub_wirepas_x86]: https://hub.docker.com/r/wirepas/gateway-x86
[dockerhub_wirepas_arm]: https://hub.docker.com/r/wirepas/gateway-arm
