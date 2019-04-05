# Wirepas Linux Gateway


This repository contains the Wirepas reference implementation for a gateway
device which offloads Wirepas Mesh data to a host.

The data is acquired from a serial UART interface, put on DBUS and published
to MQTT per the Wirepas Mesh MQTT API definition.


## Linux Requirements

- The implementation is based on DBus. The C binding used to access DBus is sdbus
  from systemd library so even if systemd is not required to be running, the
  libsystemd must be available.
  Systemd version must be higher or equal to 221. You can check it with:
```shell
    systemd --version
```
  In order to build the sink service, systemd headers are needed

    sudo apt install libsystemd-dev

- Python 3 and a recent pip version (>= 18.1)

```shell
    sudo apt install libsystemd-dev python3 python3-dev python3-gi
    wget https://bootstrap.pypa.io/get-pip.py \
       && sudo python3 get-pip.py && rm get-pip.py \
       && sudo pip3 install --upgrade pip
```

## Installation

Sink service
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

  ::

    <!-- Only wirepas user can own the service name -->
    <policy user="wirepas">

  *It is recommanded to restart your gateway once this file is copied*


Transport service
  Transport service is implemented in python 3 and
  is delivered as a Python wheel and a python tar.gz archive.
  tar.gz is used for the gateway part as it includes Python c extension that must
  be built at installation time.

  ::

    pip3 install wirepas_messaging-*.whl

    pip3 install wirepas_gateway-*.tar.gz

Configuration and starting services
-----------------------------------

- A sink service must be started for each connected sink on Gateway:

  ::

    sink_service/build/sinkService -p <uart_port> -b <bitrate> -i <sink_id>

  Parameters are:

  - **uart_port:** uart port path (default /dev/ttyACM0)
  - **bitrate:** bitrate of sink uart (default 125000)
  - **sink_id:** value between 0 and 9 (default 0).
    If multiple sinks are present, they must have a different sink_id

- A transport service must be launched.
  Parameters can be set from cmd line of from a setting file in YAML format:

  - From cmd line

    ::

      wm-gw -s "<server>" -p <port> -u <user> -pw <password> \
            -i <gwid> [-t <tls_cert_file>] [-fp] [-ua] [-iepf <endpoints list>] \
            [-wepf <endpoints list>]


    where:

    - **server:** IP or hostname where the MQTT broker is located
    - **port:** MQTT port (default: 8883 (secure) or 1883 (local))
    - **user:** MQTT user
    - **password:** MQTT password
    - **gwid:** the desired gateway id, instead of a random generated one.
      It must be unique for each gateway reporting to same broker.
    - **tls_cert_file:** filepath to the root certificate to overide system one.
      Cannot be used with -ua
    - **ua:** Disable TLS secure authentication
    - **fp:** Do not use the C extension (full python version)
    - **iepf:** Destination endpoints list to ignore (not published)
      Example: -iepf "[1,2, 10-12]" to filter out destination ep 1, 2, 10, 11, 12
    - **wepf:** Destination endpoints list to whiten (no payload content, only size)
      Example: -wepf "[1,2, 10-12]" to whiten destination ep 1, 2, 10, 11, 12

  - From configuration file

    ::

      wm-gw --settings=settings_files.yml


    Here is a file template for *settings_files.yml*.
    All parameters from above can be set from the file

    ::

      #
      # MQTT brocker Settings
      #
      host: <IP or hostname where the MQTT broker is located>
      port: <MQTT port (default: 8883 (secure) or 1883 (local))>
      username: <MQTT user>
      password: <MQTT password>
      unsecure_authentication: <True to disable TLS secure authentication>

      #
      # Gateway settings
      #
      gwid: <the desired gateway id, must be unique for each gateway>
      gateway_model: <Custom gateway model, can be omitted>
      gateway_version: <Custom gateway version, can be omitted>

      #
      # Implementation options
      #
      full_python: <Set to true to not use the C extension>

      #
      # Filtering Destination Endpoints
      #
      ignored_endpoints_filter: <Endpoints to filter out. Ex: [1, 2, 10-12]>
      whitened_endpoints_filter: <Endpoints to whiten. Ex: [1, 2, 10-12]>


Optional
--------
Launch local gateway process to see messages received from sinks at Dbus level
It can be launched from command line:

::

  wm-dbus-print



Docker build instructions
-------------------------
To build locally for x86_64 go to the root of the repository and type:

::

  ./container/docker-build.sh --build-defaults container/build_defaults.env


This command will build you the gateway with the default settings found
in build_defaults.env.


If you wish to build ARM images, please use the ARM switches and update
the image name with the name you desire:

::

  ./container/docker-build.sh --build-defaults container/build_defaults.env \
                              --arm \
                              --image wm-lxgw-rpi

In case you wish to push the image to a docker registry, you can do so with:

::

  ./container/docker-build.sh --build-defaults container/build_defaults.env \
                              --arm \
                              --image wm-lxgw-rpi \
                              --push \
                              --repo <path_to_your_repo>

The image will be tagged with <path_to_your_repo>/<image name>:<image tag>.



Starting dockerized services
-----------------------------
In the container folder, you will find the wm_gateway.env file, where you
need to place the MQTT credentials for your gateway user.

Beside the MQTT credentials, you need to define the ip or hostname where
to connect the transport service to.

Once the settings are correct, you can launch the services with:

::

  docker-compose up [-d]


To view the logs, use

::

  docker-compose logs

or specify which container you want to view the logs from with

::

  docker logs [container-name]





License
~~~~~~~
Wirepas Oy licensed under Apache License, Version 2.0 See file LICENSE for
full license details.

