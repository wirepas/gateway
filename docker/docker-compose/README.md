# Docker based gateway with docker-compose

docker-compose is a tool for defining and running multi-container Docker applications.
With the provided docker-compose.yml file, you can start a Wirepas gateway.

## Customize [the template file](docker-compose.yml)

[The template file](docker-compose.yml) requires some configuration to fit your environement.

### Transport service

The environment part contains multiples variable to customize. You can add any keys that the transport service support (wm-gw --help for the full list)

Example:

```yml
environment:
  WM_GW_ID: "my_gateway_01"
  WM_GW_MODEL: "gw_hardware_xx"
  WM_GW_VERSION: "docker_based_gw"
  WM_SERVICES_MQTT_HOSTNAME: "my_server.com"
  WM_SERVICES_MQTT_PORT: "8883"
  WM_SERVICES_MQTT_USERNAME: "username"
  WM_SERVICES_MQTT_PASSWORD: "password"
```

### Sink service

There are two things to modify in the sink-service container.

First you must specify the device to control (on which port your sink is attached in your host):

Example if your sink is on /dev/ttyACM0:

```yml
devices:
  - /dev/ttyACM0:/dev/mysink      
```

And environment must be customized too:

```yml
environment:
  # If baudrate is no specify, auto baudrate is used: ie testing successively 125000bps, 115200bps, 1000000bps
  WM_GW_SINK_BAUDRATE: "125000"
  WM_GW_SINK_ID: "1"
```

### Multiple sinks

If your gateway has multiple sinks attached, please duplicate the sink-service block and rename it.
The container_name must be renamed too and it must be customized as explained in [preicous_chapter](#sink_service).
Each sink must have a different sink id (WM_GW_SINK_ID).

### Multiple transports

You can start multiple transport service pointing to different MQTT broker.
Please duplicate the transport-service block and rename it.
The container_name must be changed and it must be customizeq with the new mqtt broker settings.

## How to start a gateway

In the folder where you stored the customized file, please run:

```bash
docker-compose up -d
```

You can see the logs with:

```bash
docker-compose logs
```
And stop the gateway with:

```bash
docker-compose down
```

## How to choose the gateway version

The tag to use for the gateway images can be chosen when invoking the docker-compose (by default it is latest tag).

```bash
GATEWAY_TAG=edge docker-compose up -d
```

