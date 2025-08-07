# Sink service

The sink service is in charge of doing the interface between a physical device attached to a gateway through a uart port and the Dbus internal API.

## Requirements

On Debian 12, the following packages are needed to build:
```
cmake
git
libsystemd-dev
pkg-config
```

The sink service depends on [c-mesh-api](https://github.com/wirepas/c-mesh-api) repository.
It contains the low level library that implements the DualMCU API to communicate through an UART to a Wirepas node.

c-mesh-api is fetched automatically from git by CMake when the project is configured.

## Building the sink service

From current folder, execute following commands to build the sinkService

```shell
cmake -S . -B build
cmake --build build
```
Built sinkService will be generated under build/ folder. 


