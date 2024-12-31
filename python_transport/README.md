# Wirepas Gateway Transport Service
[![Documentation Status](https://readthedocs.org/projects/wirepas-gateway/badge/?version=latest)](https://wirepas-gateway.readthedocs.io/en/latest/?badge=latest)

## Building the wheel

To build the source distribution and wheel file, make sure you have the
build package installed

```shell
   pip install build
```
and then run

```shell
   python3 -m build .
```

A convenience script is available from the [utils folder][here_utils_wheel].

## Installation

Before you attempt to build and install this package, please ensure that
you have [all the requirements met][wm_gateway_requirements].

We highly recommend that you make your installation under a python virtual
environment such as [virtualenv][virtualenv] or [pipenv][pipenv].

To install this package run (use -e for development mode)

```shell
   pip install [-e] .
```

## Running inside a virtual environment

When running inside a virtual environment you will need to provide access
to system libraries. You can achieve this by using *--system-site-packages*
when setting up your environment or through [vext][vext].

If you opt to install [vext][vext], please install the
[PyGObject][pygobject] module with:

```shell
   pip install vext vext.gi
```

You also need to ensure that the following packages are installed inside
the virtual environment (as well as their system dependencies):

```shell
   pip install pygobject gobject
```

## Starting the service

Please read on
[how to configure and start the transport service][wm_gateway_transport_conf]

[wm_gateway_transport_conf]: https://github.com/wirepas/gateway/blob/master/README.md#transport-service-configuration
[wm_gateway_requirements]: https://github.com/wirepas/gateway/blob/master/README.md#linux-requirements
[here_utils_wheel]: https://github.com/wirepas/gateway/blob/master/python_transport/utils/generate_wheel.sh

[virtualenv]: https://docs.python.org/3/tutorial/venv.html
[pipenv]: https://github.com/pypa/pipenv
[vext]: https://github.com/stuaxo/vext

[pygobject]: https://pygobject.readthedocs.io/en/latest/index.html
