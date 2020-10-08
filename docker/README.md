# Docker based Gateway

This folder contains all the necessary part to build and execute a docker based gateway.
A minimal gateway is composed of a sink service and a transport service (but can have multiple sink services and multiple transports).
All are connected through DBus.

Our Docker approach is to isolate each services and DBus in their own container.
So a minimal docker based gateway will run three containers. 

## Docker images

The different docker images are automatically built on each release or commit to master branch and published to Docker Hub.
All images are multi-arch images and support Arm-v7 and amd64 architectures

### Main images

The following images are the three ones mentionned above to create a minimal gateway.

Image | Description | Docker Hub Link
----- | ----------- | --------------- 
[Dbus](dbus_service) | This image run a dbus daemon and export its unix socket to other containers | [gateway_dbus_service](https://hub.docker.com/r/wirepas/gateway_dbus_service) | 

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

All the dockerfiles are available in this directory and can be build directly from root folder of this repository.

Example to build sink service tagged local/my_sink_service:tag1 :
```bash
docker build -f docker/dbus-service/Dockerfile -t local/my_sink_service:tag1
```
You can then use this image in the docker-compose template instead of the Wirepas Docker Hub ones.
