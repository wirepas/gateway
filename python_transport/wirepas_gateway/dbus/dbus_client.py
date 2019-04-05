# Wirepas Oy licensed under Apache License, Version 2.0
#
# See file LICENSE for full license details.
#
from pydbus import SystemBus
from gi.repository import GLib, GObject
from .sink_manager import SinkManager
from threading import Thread, enumerate, currentThread
from time import sleep
import logging
import sys
import dbusCExtension


class DBusWatchdog(Thread):
    """
    Watchdog to monitor DBus infinite loop managed by GLib
    """

    def __init__(self, logger, watchdog_period_s=1):
        """
        Init function
        :param watchdog_period_s: period to reset the watchdog
                from the GLIB loop
        """
        Thread.__init__(self)

        # logger
        self.logger = logger

        # Period to check for watchdog on this thread.
        # It means that if the watchdog was not reseted
        # during 3 watchdog period from GLIB loop
        # the deadlock is detected
        self.check_watchdog_period = 3 * watchdog_period_s

        # Daemonize this thread to be exited with the process
        self.daemon = True
        self.running = False
        self.watchdog = False

        # Schedule the reset function to be scheduled every watchdog_period_s
        # from GLIB loop. If loop is locked (that should never happen in normal
        # situation), the watchdog will not be reseted anymore.
        GObject.timeout_add_seconds(watchdog_period_s, self._reset_watchdog)

    def run(self) -> None:
        """
        Thread infinite loop to periodicaly check the watchdog status
        :return:
        """
        self.running = True
        while self.running:
            sleep(self.check_watchdog_period)
            if self.watchdog:
                # Watchdog was not reseted by GLIB loop
                self.logger.error("Deadlock detected")

                # Add more traces to understand what other threads are doing
                for thread in enumerate():
                    if thread.name is self.name:
                        # Skip current Thread
                        continue

                    self._print_thread_info(thread)

            # Re-arm the watchdog
            self.watchdog = True

    def _print_thread_info(self, thread) -> None:
        self.logger.error(
            " Thread name: {} -  Alive={} ".format(thread.name, thread.is_alive())
        )
        frame = sys._current_frames().get(thread.ident, None)
        if frame:
            self.logger.error(
                "\t{} {} {}".format(
                    frame.f_code.co_filename,
                    frame.f_code.co_name,
                    frame.f_code.co_firstlineno,
                )
            )
        else:
            self.logger.error("\tNo frame available")

    def _reset_watchdog(self):
        self.watchdog = False
        # Return true to reschedule the callback from GLib loop
        return True

    def stop(self):
        self.running = False


class DbusEventHandler(Thread):
    """
    Dedicated Thread to manage DBUS messages signals in C
    The thread is created in Python world but its real execution is
    delegated to C through a Python C extension
    """

    def __init__(self, cb, logger):
        """
        Initialize the C module wrapper
        :param cb: Python Callback to call from C on packet reception
        """
        Thread.__init__(self)

        # logger
        self.logger = logger

        dbusCExtension.setCallback(cb)
        self.daemon = True  # Daemonize thread

    def run(self) -> None:
        """
        Delegate the execution to C Extension
        :return: None, as it is an infinite loop in C
        """
        while True:
            dbusCExtension.infiniteEventLoop()
            self.logger.error("C extension loop has exited")


class BusClient(object):
    """
    Base class to use to implement a DbusClient using the sink services
    It automatically manage sink connection/disconnection and offers some abstraction
    of dbus
    """

    def __init__(self, logger=None, c_extension=True, ignored_ep_filter=None, **kwargs):

        # logger
        self.logger = logger or logging.getLogger(__name__)

        # watchdog
        self.watchdog = DBusWatchdog(self.logger)
        self.watchdog.start()

        # Main loop for events
        self.loop = GLib.MainLoop()

        # Connect to session bus
        self.bus = SystemBus()

        # Manage sink list
        self.sink_manager = SinkManager(
            bus=self.bus,
            on_new_sink_cb=self.on_sink_connected,
            on_sink_removal_cb=self.on_sink_disconnected,
            on_stack_started=self.on_stack_started,
            logger=self.logger,
        )

        self.ignore_ep_filter = ignored_ep_filter

        # Register for packet on Dbus
        if c_extension:
            self.logger.info("Starting c extension")
            self.c_extension_thread = DbusEventHandler(
                self._on_data_received_c, self.logger
            )
        else:
            # Subscribe to all massages received from any sink (no need for
            # connected sink for that)
            self.bus.subscribe(
                signal="MessageReceived",
                object="/com/wirepas/sink",
                signal_fired=self._on_data_received,
            )

            self.c_extension_thread = None

    def _on_data_received_c(
        self,
        sender,
        timestamp,
        src,
        dst,
        src_ep,
        dst_ep,
        travel_time,
        qos,
        hop_count,
        data,
    ):

        # Could be done in C extension if needed by providing list to extension
        if self.ignore_ep_filter is not None and dst_ep in self.ignore_ep_filter:
            self.logger.debug("Message received on ep {} filtered out".format(dst_ep))
            return

        # Get sink name from sender unique name
        name = self.sink_manager.get_sink_name(sender)
        self.on_data_received(
            sink_id=name,
            timestamp=timestamp,
            src=src,
            dst=dst,
            src_ep=src_ep,
            dst_ep=dst_ep,
            travel_time=travel_time,
            qos=qos,
            hop_count=hop_count,
            data=data,
        )

    def _on_data_received(self, sender, object, iface, signal, params):
        # filter out endpoint
        if params[4] in self.ignore_ep_filter:
            self.logger.debug(
                "Message received on ep {} filtered out".format(params[4])
            )
            return

        # Get sink name from sender unique name
        name = self.sink_manager.get_sink_name(sender)
        self.on_data_received(
            sink_id=name,
            timestamp=params[0],
            src=params[1],
            dst=params[2],
            src_ep=params[3],
            dst_ep=params[4],
            travel_time=params[5],
            qos=params[6],
            hop_count=params[7],
            data=bytearray(params[8]),
        )

    def run(self):
        self.on_start_client()

        # If needed start C extension thread
        if self.c_extension_thread is not None:
            self.c_extension_thread.start()

        # For now, start the GLib loop for even if C extension is
        # in use as some signals are still handled on it. But should not be
        # the case in future. Even without handling signals, this thread takes
        # 30% of one CPU on a rpi3.
        try:
            self.loop.run()
        except KeyboardInterrupt:
            self.loop.quit()
            self.watchdog.stop()

        self.on_stop_client()

    def stop_dbus_client(self):
        """
        Explicitly stop the dbus client
        """
        self.loop.quit()

    # Method should be overwritten by child class
    def on_data_received(
        self,
        sink_id,
        timestamp,
        src,
        dst,
        src_ep,
        dst_ep,
        travel_time,
        qos,
        hop_count,
        data,
    ):
        pass

    def on_sink_connected(self, name):
        pass

    def on_sink_disconnected(self, name):
        pass

    def on_stack_started(self, name):
        pass

    def on_start_client(self):
        pass

    def on_stop_client(self):
        pass
