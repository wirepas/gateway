# Docker based gateway with docker-compose

docker-compose is a tool for defining and running multi-container Docker applications.
With the provided docker-compose.yml file, you can start a Wirepas gateway.

## Customize the template file

We provide some gateway configuration examples. These are listed below:
 
| Configuration | Purpose | Link |
| ------------- | ----    | ---  |
|Single transport | A simple use case with a single sink and a single transport | [Single transport](./single_transport/docker-compose.yml) |
| Dual transport  | Use case with two transports to route traffic from selected endpoints to two distinct backends. This can be used for instance to route traffic from an application to a customer backend and diagnostic traffic to WNT | [Dual transport](./dual_transport/docker-compose.yml) |

All the example templates provided (docker-compose.yml) can be updated to fit your environment. 

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

The tag to use for the gateway's docker images can be chosen when invoking the docker-compose (by default it is latest tag).

```bash
GATEWAY_TAG=edge docker-compose up -d
```

## Transport service

Whilst the examples provided constitute a good starting point in setting up a gateway, there are additional parameters that can be used to configure the transport service and further customize it based on the needs of the application.

The list of all possible parameters to configure the transport service are given below:


| Parameter | Description | Default value | Possible value |
| ----- | ---------- | ---- | ---|
| WM_SERVICES_MQTT_HOSTNAME | MQTT broker hostname | None |Any string | |
| WM_SERVICES_MQTT_USERNAME | MQTT broker username | None |Any string | | 
| WM_SERVICES_MQTT_PASSWORD | MQTT broker password | None | Any string | | 
| WM_SERVICES_MQTT_PORT | MQTT broker port | 8883 |Any integer |
| WM_SERVICES_MQTT_CA_CERTS | Path to the Certificate Authority certificate files that are to be treated as trusted by this client | None | Any string|
| WM_SERVICES_MQTT_CLIENT_CRT | PAth to the PEM encoded client certificate. | None | Any string |
| WM_SERVICES_MQTT_CLIENT_KEY | Path to the PEM encoded client private keys respectively | None |Any string |
| WM_SERVICES_MQTT_CERT_REQS | Defines the certificate requirements that thte client imposes on the broker | CERT_REQUIRED |CERT_REQUIRED, CERT_OPTIONAL, CERT_NONE|
| WM_SERVICES_MQTT_TLS_VERSION | Specifies the version of the SSL / TLS protocol to be used | PROTOCOL_TLSv1_2 |PROTOCOL_TLS, PROTOCOL_TLS_CLIENT, PROTOCOL_TLS_SERVER, PROTOCOL_TLSv1, PROTOCOL_TLSv1_1, PROTOCOL_TLSv1_2 |
| WM_SERVICES_MQTT_CIPHERS | A string specifying which encryption ciphers are allowable for this connection | None | Any string |
| WM_SERVICES_MQTT_PERSIST_SESSION | When True the broker will buffer session packets between reconnection | false | "yes", "true", "t", "y",  "1","no", "false", "f", "n", "0", "" |
| WM_SERVICES_MQTT_FORCE_UNSECURE | When True the broker will skip the TLS handshake | false | "yes", "true", "t", "y",  "1","no", "false", "f", "n", "0", "" | 
| WM_SERVICES_MQTT_ALLOW_UNTRUSTED | When true the client will skip the certificate name check | false | "yes", "true", "t", "y",  "1","no", "false", "f", "n", "0", "" |
| WM_SERVICES_MQTT_RECONNECT_DELAY | Delay in seconds to try to reconnect when connection to broker is lost (0 to try forever) | 0 | Any integer |
| WM_SERVICES_MQTT_MAX_INFLIGHT_MESSAGES | Max inflight messages for messages with qos > 0 | 20 | Any integer |
| WM_SERVICES_MQTT_USE_WEBSOCKET | When true the mqtt client will use websocket instead of TCP for transport | false | "yes", "true", "t", "y",  "1","no", "false", "f", "n", "0", "" |
| WM_GW_BUFFERING_MAX_BUFFERED_PACKETS | Maximum number of messages to buffer before rising sink cost (0 will disable feature) | 0 | Any integer |
| WM_GW_BUFFERING_MAX_DELAY_WITHOUT_PUBLISH | Maximum time to wait in seconds without any successful publish with packet queued before rising sink cost (0 will disable feature) | 0 | Any integer |
| WM_GW_BUFFERING_MINIMAL_SINK_COST | Minimal sink cost for a sink on this gateway. Can be used to minimize traffic on a gateway, but it will reduce maximum number of hops for this gateway | 0 | Any integer |
| WM_GW_ID | Id of the gateway. It must be unique on same broker | None | Any string |
| WM_GW_MODEL | Model name of the gateway | None | Any string | 
| WM_GW_VERSION | Version of the gateway | None | Any string |
| WM_GW_IGNORED_ENDPOINTS_FILTER | Destination endpoints list to ignore (not published) | None | List of endpoints (i.e. [1,2,3]), a range of endpoints (i.e. [1-3]), or a combination of both |
| WM_GW_WHITENED_ENDPOINTS_FILTER | Destination endpoints list to whiten (no payload content, only size) | None | List of endpoints (i.e. [1,2,3]), a range of endpoints (i.e. [1-3]), or a combination of both |
| WM_DEBUG_LEVEL | Configure log level for the transport service. Please be aware that levels such as debug should not be used in a production system | info | debug, info, critical, fatal, error, warning |


Any of the parameters above can be added in the template file. For example: 
```bash
transport-service:
    image: wirepas/gateway_transport_service:${GATEWAY_TAG:-latest}
    container_name: transport-service
    environment:
      WM_SERVICES_MQTT_HOSTNAME: "aBroker"
```

