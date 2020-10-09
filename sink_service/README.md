# Sink service

The sink service is in charge of doing the interface between a physical device attached to a gateway through a uart port and the Dbus internal API.

## Getting the sources

The sink service depends on [c-mesh-api](https://github.com/wirepas/c-mesh-api) repository.
It contains the low level library that implements the DualMCU API to communicate through an UART to a Wirepas node.

[Git submodule](https://git-scm.com/book/en/v2/Git-Tools-Submodules) is used to upkeep the project
dependency with the c-mesh-api library.

Once this repository is cloned, please synchronize it to get the c-mesh-api
code at the right place.

```shell
git submodule update --init
```
## Building the sink service

From current folder, execute this command to build the sinkService

```shell
make
```
Built sinkService will be generated under build/ folder. 


