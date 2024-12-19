# Docker based Gateway

This folder contains all the necessary part to build and execute a docker based gateway.
A minimal gateway is composed of a sink service and a transport service (but can have multiple sink services and multiple transport services).
All are connected through DBus.

Our Docker approach is to isolate each services and DBus in their own container. Isolating the dbus daemon in its own container compare of using the host one improves the security of the system.
A minimal docker based gateway will run three containers. 

## Prerequisites

 In order to run a Docker based gateway you need to install Docker engine:
 
 * Recommanded version is 20.10+
 * [Installation guide](https://docs.docker.com/engine/install/)
 
 And optionnaly you can use docker-compose to ease the setup:
 
 * Recommanded version is 1.26.0+
 * [Installation guide](https://docs.docker.com/compose/install/)
 
Installation is only tested on Linux but could work on Mac and Windows.  
For Windows and Docker desktop using WSL2, please follow the instructions given in [setup under WSL2](#setup-under-wsl2).

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

## How to start a Docker based gateway

The [docker-compose](docker-compose) folder contains a reference docker compose file to start a docker based gateway.

## How to build your own images

If you want to test a change you made or add new features in your own service, you can build your own images.
How to publish them in your own registry is out of scope for this document.

All the dockerfiles are available in this directory and can be built directly from root folder of this repository.

Example to build a custom sink service tagged local/my_sink_service:tag1 in your PC:
```bash
docker build -f docker/sink-service/Dockerfile -t local/my_sink_service:tag1
```
You can then use this image in the docker-compose template instead of the Wirepas Docker Hub ones.

## Setup under WSL2
The Wirepas gateway driver can be deployed under Windows Subsystem for Linux 2 aka WSL2. Its setup procedure is described in this section for the Ubuntu 22.04LTS distribution. It should work with any other but can require some adaptation to what is provided.  

### Prerequisites
* Windows 10 or 11 (Build 22000 or later) installed

### Flow
Install (or update) WSL v2 package. Its version must be \>= v1.0  
Install docker desktop for windows  
Install Ubuntu distribution with `wsl.exe --list --online` and `wsl --install <some name from the list>`  
Enable Docker desktop integration with your WSL distribution  
Follow the instructions given in [WSL: connect USB devices](https://learn.microsoft.com/en-us/windows/wsl/connect-usb).  
>
> :warning:
> 
> If you have Windows 10 you do not need to build a custom kernel to support usbipd. Please follow the Windows 11 path.
>
At this point, your should be able to attach a sink within WSL.
Once the sink is properly attached to your WSL system please change (if required) the device owner to your current user with `sudo -k chown <your username>:<your user group> /dev/<your sink device enumerated name>`  
Edit the _docker-compose.yml_ file accordingly:  
* Transport service and sink service configuration  
* container logging driver from **journald** to **local** , if systemd is not enabled on your WSL system (WSL default configuration. More information from [here](https://learn.microsoft.com/en-us/windows/wsl/systemd))  

Issue a `docker-compose up -d` command (where the docker-compose.yml file is located) to download and start the services
