# Single Transport example

The goal of this example is to setup a gateway which has a single sink and a single transport. The traffic from all endpoints is routed via the transport to the MQTT broker.

## Customize the template file

[The template file](docker-compose.yml) requires some configuration to fit your environement.

### Transport service

The environment part contains multiples variable to customize. You can [add any keys](../README.md#transport-service) that the transport service support.

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

There are two things to modify for the sink service.

First you must specify the device to control (the port on the host to which the sink is connected):

For example, if your sink is on /dev/ttyACM0, the configuration should be edited as follows:

```yml
devices:
  - /dev/ttyACM0:/dev/mysink      
```

The environment variables must be customized too:

```yml
environment:
  # If the baudrate is not specified, auto baudrate is used (i.e. testing successively 125000bps, 115200bps, 1000000bps)
  WM_GW_SINK_BAUDRATE: "125000"
  WM_GW_SINK_ID: "1"
```

