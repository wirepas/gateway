# Single transport with local MQTT broker example

This example is based on the [single transport example](../single_transport/README.md).
The configuration instructions from single transport can be followed. In this
example, the MQTT broker is added to the docker compose file as a container, so
you don't have to set up and configure an MQTT broker separately.

The MQTT broker is configured insecurely, therefore this example is mainly
intended for quickly setting up a gateway for development purposes. The broker
can be reached from TCP port 1883 and via websockets on port 9001.

