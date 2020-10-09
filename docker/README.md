# Docker based Gateway

This folder contains all the necessary part to build and execute a docker based gateway.
A minimal gateway is composed of a sink service and a transport service (but can have multiple sink services and multiple transport services).
All are connected through DBus.

Our Docker approach is to isolate each services and DBus in their own container. Isolating the dbus daemon in its own container compare of using the host one improves the security of the system.
A minimal docker based gateway will run three containers. 

## Prerequisites

 In order to run a Docker based gateway you need to install Docker engine:
 
 * Recommanded version is 19.03.0+
 * [Installation guide](https://docs.docker.com/engine/install/)
 
 And optionnaly you can use docker-compose to ease the setup:
 
 * Recommanded version is 1.26.0+
 * [Installation guide](https://docs.docker.com/compose/install/)
 
Installation is only tested on Linux but could work on Mac and Windows. For Windows and Docker desktop using WSL2, it will not work as devices cannot be mapped to a container yet.

## Docker images

The different docker images are automatically built on each release or commit to master branch and published to Docker Hub.
All images are multi-arch images and support Arm-v7 and Amd64 architectures.

### Main images

The following images are the three ones mentionned above to create a minimal gateway.

Image | Description | Docker Hub Link
----- | ----------- | --------------- 
[Dbus](dbus_service) | This image runs a dbus daemon and exports its unix socket to other containers | [gateway_dbus_service](https://hub.docker.com/r/wirepas/gateway_dbus_service)
[Sink Service](sink_service) | This image handles the communication with a sink and exposes its services through on dbus through the dbus_service container | [gateway_sink_service](https://hub.docker.com/r/wirepas/gateway_sink_service)
[Transport service](transport_service) | This image handles the communication with the different sinks through dbus and implements the Wirepas backend protocol | [gateway_transport_service](https://hub.docker.com/r/wirepas/gateway_transport_service)

All these images have the following tags available:
* __edge__: built from top of master
* __latest__: built from latest release
* __vx.x.x__: built from each release

### Internal images
Image | Description | Docker Hub Link | Tags
----- | ----------- | --------------- | ----
[base_builder](base_builder) | This image is used to speed up build of other images. It contains the part that are common to all images | [gateway_base_builder](https://hub.docker.com/r/wirepas/gateway_base_builder) | It is tagged and push manually only when needed and tag is used in other Dockerfiles 

## How to start a Docker based gateway

The [docker-compose](docker-compose) folder contains a reference docker compose file to start a docker based gateway.

## How to build your own images

If you want to test a change you made or add new features in your own service, you can build your own images.
How to publish them in your own registry is out of scope for this document.

All the dockerfiles are available in this directory and can be built directly from root folder of this repository.

Example to build a custom sink service tagged local/my_sink_service:tag1 in your PC:
```bash
docker build -f docker/dbus-service/Dockerfile -t local/my_sink_service:tag1
```
You can then use this image in the docker-compose template instead of the Wirepas Docker Hub ones.
