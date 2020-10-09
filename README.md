# Wirepas Linux Gateway

[![Codacy Badge](https://api.codacy.com/project/badge/Grade/ebb45a6a13ec4f2c88131ddf51a9579a)](https://www.codacy.com/manual/wirepas/gateway?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=wirepas/gateway&amp;utm_campaign=Badge_Grade) [![Build Status](https://travis-ci.com/wirepas/gateway.svg?branch=master)](https://travis-ci.com/wirepas/gateway)

<!-- MarkdownTOC levels="1,2" autolink="true"  -->

- [Gateway overview](#gateway-overview)
- [Option 1: native installation](#option-1-native-installation)
- [Option 2: Docker installation](#option-2-docker-installation)
- [Contributing](#contributing)
- [License](#license)

<!-- /MarkdownTOC -->

## Gateway overview 

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

## Option 1: native installation

### Requirements

The implementation is based on DBus. The C binding used to access DBus is sdbus
from systemd library so even if systemd is not required to be running, the
libsystemd must be available.

Systemd version must be higher or equal to *221*. You can check it with:

```shell
systemd --version
```

In order to build the sink service or the transport python wheel that contains C extensions, systemd headers are needed

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

### Installation

The implementation uses system bus that has enforced security.
In order to obtain a service name on system bus, the user launching the sink
service must be previously declared to system.
Provided file [*com.wirepas.sink.conf*](sink_service/com.wirepas.sink.conf)
must be copied under */etc/dbus-1/system.d/* and edited with the user that will
launch the sink_service (and transport service).

To change the default wirepas user, please edit the following lines
from com.wirepas.sink.conf:

```xml
    <!-- Only wirepas user can own the service name -->
    <policy user="wirepas">
```

*It is recommended to restart your gateway once this file is copied.*

#### Sink service

You can either build yourself the sink service by foolowing instructions from [sink_service folder](sink_service)
or you can use prebuilt version available for each release on [release section of this repository][here_releases].
Download the one for your architecture (Arm or Amd64)

#### Transport service

To build the wheel yourself, please refer to the
[transport's service readme file][here_transport_readme].

Alternatively, you can use prebuilt Python wheels.
You can either get it through [PyPi][wirepas_gateway_pypi] or from the
[release section of this repository][here_releases].

The library contains a c extension which will be compiled upon installation (even with prebuilt wheel).
Please ensure that you have met all the build requirements prior to
attempting the installation.

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
-   **bitrate:** bitrate of sink uart (*default:* auto baudrate. 125000, 115200 and 1000000 bps are tested)
-   **sink_id:** value between 0 and 9 (*default:* 0).

If multiple sinks are present, they must have a different *sink_id*.

#### Transport service configuration

Parameters can be set from command line or from a setting file in YAML format.
To get the full list of parameters, please run:

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

##### Configure a sink locally

There is a script installed along the Wirepas Transport wheel that allow the configuration of sinks locally

Please see its help page for more information.

```shell
wm-node-config --help
```

## Option 2: Docker installation

In order to ease the installation in a Docker environment, please see the instruction in [docker folder](docker).
The Docker files under [container folder](conainer) are still used for our internal CI but must no be used for other purposes.
They will be removed at some point.

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

[wirepas_backend_apis]: https://github.com/wirepas/backend-client
[wirepas_gateway_to_backend_api]: https://github.com/wirepas/backend-apis/blob/master/gateway_to_backend/README.md
[wirepas_gateway_pypi]: https://pypi.org/project/wirepas-gateway

[dockerhub_wirepas]: https://hub.docker.com/r/wirepas/gateway
