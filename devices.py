"""
This module provides abstract Device classes which should be used as parent classes
to implement specific devices
"""
import warnings
import time
from interfaces import BaseInterface, check_interface



class BaseDevice(BaseInterface):
    """
    Base class for device interfaces

    arguments
    ---------
    interface : object
        interface used to read and write to device
        Should have read_raw, write_raw functions and timeout property
    """
    def __init__(self, interface, timeout=15000):
        check_interface(interface)
        self._interface = interface
        self.timeout = timeout

    _read_termination = None
    _write_termination = "\r\n"
    _encoding = 'ascii'

    query_delay = 0.0

    @property
    def timeout(self):
        """ I/O timeout """
        return self._interface.timeout

    @timeout.setter
    def timeout(self, value):
        """ timeout setter """
        self._interface.timeout = value

    @property
    def read_termination(self):
        """ read termination """
        return self._read_termination

    @read_termination.setter
    def read_termination(self, value):
        """ read termination setter """
        try:
            self._interface.read_termination = value
        except AttributeError:
            pass
        self._read_termination = value

    @property
    def write_termination(self):
        """Write termination character."""
        return self._write_termination

    @write_termination.setter
    def write_termination(self, value):
        """ write termination setter """
        try:
            self._interface.write_termination = value
        except AttributeError:
            pass
        self._write_termination = value

    def write_raw(self, message):
        """ write message through interface. returns bytes written """
        return self._interface.write_raw(message)

    def write(self, message, termination=None, encoding=None):
        """
        TODO: pyvisa

        write string to device
        """
        term = self._write_termination if termination is None else termination
        enco = self._encoding if encoding is None else encoding

        if term:
            if message.endswith(term):
                warnings.warn("write message already ends with termination characters")
            message += term

        return self.write_raw(message.encode(enco))

    def read_raw(self, size=None):
        """ returns raw data read through interface """
        return self._interface.read_raw(size)

    def read(self, termination=None, encoding=None):
        """
        TODO: pyvisa

        Read a string from the device using read_raw

        returns decoded string with termination characters stripped from end
        """

        termination = self._read_termination if termination is None else termination
        enco = self._encoding if encoding is None else encoding

        message = self.read_raw().decode(enco)

        if not termination:
            return message

        if not message.endswith(termination):
            warnings.warn("read string doesn't end with termination characters")
            return message

        return message[:-len(termination)]

    def query(self, message, delay=None):
        """
        TODO: pyvisa

        A combination of write(message) and read()

        :param message: the message to send.
        :type message: str
        :param delay: delay in seconds between write and read operations.
                      if None, defaults to self.query_delay
        :returns: the answer from the device.
        :rtype: str
        """

        self.write(message)

        delay = self.query_delay if delay is None else delay

        if delay > 0.0:
            time.sleep(delay)

        return self.read()

    def idn(self):
        return self.query("*IDN?")

    def rst(self):
        self.write("*RST")
