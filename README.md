# Wirepas Linux Gateway

This repository contains the Wirepas reference implementation for a gateway
device which offloads Wirepas Mesh data to a host.

## Cloning this repository

This repository has a hard dependency on [c-mesh-api](https://github.com/wirepas/c-mesh-api)
and a soft dependency on the [backend-apis](https://github.com/wirepas/backend-client).

When cloning this repository and its dependencies you can opt for:

-   Using [repo tool](https://source.android.com/setup/develop/repo)
    and the [manifest repository](https://github.com/wirepas/manifest)

    > repo init -u https://github.com/wirepas/manifest.git
    or 
    > repo init -u git@github.com:wirepas/manifest.git
    
    afterwards download the repositories with
    
    > repo sync

-   Clone each repo separately (see [pull_repos.sh](./utils/pull_repos.sh))

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

*It is recommended to restart your gateway once this file is copied*

### Transport service

Transport service is implemented in python 3 and
is delivered as a Python wheel and a python tar.gz archive.
tar.gz is used for the gateway part as it includes Python c extension that must
be built at installation time.

```shell
    pip3 install wirepas_messaging-*.whl

    pip3 install wirepas_gateway-*.tar.gz
```

## Configuration and starting services

### Sink service configuration

A sink service must be started for each connected sink on Gateway:

sink_service/build/sinkService -p <uart_port> -b <bitrate> -i <sink_id>

Parameters are:

- **uart_port:** uart port path (default /dev/ttyACM0)
- **bitrate:** bitrate of sink uart (default 125000)
- **sink_id:** value between 0 and 9 (default 0).

If multiple sinks are present, they must have a different sink_id

### Transport service configuration

Parameters can be set from cmd line or from a setting file in YAML format.
To get an exhausted list of parameters, please run:

```shell
    wm-gw --help
```


#### From cmd line

Here is an example to start the transport module from cmd line:

```shell
    wm-gw --mqtt_hostname "<server>" --mqtt_port <port> --mqtt_username <user> --mqtt_password <password> \
     --gateway_id <gwid> [--ignored_endpoints_filter <ignored endpoints list>] \
     [--whitened_endpoints_filter <whitened endpoints list>]
```

where:

-   **server:** IP or hostname where the MQTT broker is located

-   **port:** MQTT port (default: 8883 (secure) or 1883 (local))

-   **user:** MQTT user

-   **password:** MQTT password

-   **gwid:** the desired gateway id, instead of a random generated one.

    > It must be unique for each gateway reporting to same broker.

-   **ignored endpoints list:** Destination endpoints list to ignore (not published)

    *Example:*

    > --ignored_endpoints_filter "\[1,2, 10-12\]" to filter out destination ep 1, 2, 10, 11, 12

-   **whitened endpoints list:** Destination endpoints list to whiten
              (no payload content, only size)

    *Example:*

    > --whitened_endpoints_filter "\[1,2, 10-12\]" to whiten destination ep 1, 2, 10, 11, 12

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

Launch local gateway process to see messages received from sinks at Dbus level
It can be launched from command line:

```shell
    wm-dbus-print
```

## Docker build instructions

To build locally for x86_64 go to the root of the repository and type:

```shell
    ./container/docker-build.sh --build-defaults container/build_defaults.env
```

This command will build you the gateway with the default settings found
in build_defaults.env.

If you wish to build ARM images, please use the ARM switches and update
the image name with the name you desire:

```shell
    ./container/docker-build.sh --build-defaults container/build_defaults.env \
                            --arm \
                            --image wm-lxgw-rpi
```

In case you wish to push the image to a docker registry, you can do so with:

```shell
    ./container/docker-build.sh --build-defaults container/build_defaults.env \
                              --arm \
                              --image wm-lxgw-rpi \
                              --push \
                              --repo <path_to_your_repo>
```

The image will be tagged with

> *path_to_your_repo*/*image name*:*image tag*.

## Starting docker services

In the container folder, you will find the wm_gateway.env file, where you
need to place the MQTT credentials for your gateway user.

Beside the MQTT credentials, you need to define the ip or hostname where
to connect the transport service to.

Once the settings are correct, you can launch the services with:

```shell
    docker-compose up [-d]
```

To view the logs, use

```shell
    docker-compose logs
```

or specify which container you want to view the logs from with

```shell
    docker logs [container-name]
```

## License

Wirepas Oy licensed under Apache License, Version 2.0 See file LICENSE for
full license details.
