Pre-requisites
===============
- docker
- python
- pip
- docker-compose (python package)


Installing docker
==================
Download the script at https://get.docker.com/ and run it from
your host. The Docker engine CE will be setup for you.

::

    curl https://get.docker.com/ | sh


If you want, add your user to the docker group once the installation
is over (read script output for instruction).

Please reboot if you added your user to the docker group. If not, then run all docker commands with sudo.


Installing pip & docker-compose
===============================

Install and upgrade through your distro package manager or go with
the official script found at

::

    curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py

and then

::

    python get-pip.py

In the end, verify you have at least

::

    pip --version
    pip 18.0 from <PYTHON_PATH>/pythonX.Y/dist-packages/pip (python X.Y)

Afterwards, install docker-compose with

::

    pip install docker-compose


.. raw:: pdf

   PageBreak


Installing the WM Gateway over Docker
=====================================

These instructions assume a Raspberry Pi host with the pre-requisites met.

1. copy the archive to target host

::

    scp docker-wm-gateway.tar.gz


2. untar the archive with

::

   mkdir -p lxgw
   tar -xf docker-wm-gateway.tar.gz -C lxgw


3. enter the folder created by the unzip operation

::

    cd lxgw/

4. copy the dbus policy to your local host

::

    sudo cp utils/com.wirepas.sink.conf /etc/dbus-1/system.d/com.wirepas.sink.conf
    sudo reboot



4. update the wm_gateway.env with your sink and connection details

::

    nano -wE wm_gateway.env


5. Build and start the gateway (as a daemon -d) with

::

    [sudo] docker-compose up -d

    <please wait>

    docker-compose logs -ft # will show you the gateway logs

    #This step will pull down the base image for rpi3 and build the wm-lxgw image.

    # The wm-lxgw image is used in the composition (docker-compose.yml)
    # of the sink and transport services.
    # The sink and connection details are taken from wm_gateway.env.


6. Congratulations, your gateway is up and running!


