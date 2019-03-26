.. Wirepas Gateway Transport Service documentation master file, created by
   sphinx-quickstart on Thu Feb 15 13:55:58 2018.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Wirepas Gateway Transport Service
=================================

Wirepas Gateway Transport Service (WGTS) is a Python package which gathers messages
and events sent by the WM sink service in a local system bus (dbus).

Requirements
------------
* Python 2.X, 3.X

Installation is recommended through pip as

.. code-block:: bash

   pip install wirepas_gateway.whl

For source distributions, you might whish to install the package in development
mode through,

.. code-block:: bash

   pip install -e .


Usage
------
When installed as a system package, (WGTS) exposes the following console commands:

* wm-gw - launches the transport service

* wm-dbus-print - attaches a service to the dbus which prints inbound/outbound messages in the WM bus

License
--------
Copyright 2018 Wirepas Ltd. All Rights Reserved. See file LICENSE.txt for
full license details.


Source documentation
--------------------
.. toctree::
   :maxdepth: 2

   wirepas_gateway

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
