# How to assign a symlink to your sink:

1.  Connect sink first time to get an automatically assigned port (<port_name>):

```shell
    /dev/ttyACM0, /dev/ttyUSB1,...
```

2.  udevadm info --name=<port_name> --attribute-walk

3.  get following attributes:

````shell
    ATTRS{serial} <serial>
    ATTRS{idProduct} <idProduct>
    ATTRS{idVendor} <idVendor>
```

4.  create a file in /etc/udev/rules.d/99-usb-serial.rules containing:

```shell
     SUBSYSTEM=="tty", ATTRS{idVendor}=="<idVendor>", ATTRS{idProduct}=="<idProduct>", ATTRS{serial}=="<serial>", SYMLINK+="your_sink_name"
```

5.  sudo udevadm trigger

Your sink will now always the name _/dev/"your_sink_name"_
````
