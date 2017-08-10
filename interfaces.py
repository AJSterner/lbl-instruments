"""
TODO: MAKE THIS MORE CLEAR
device interfaces
This module attempts to simplify communication with various devices by providing
interfaces for each mode of communication and generalizing interaction

for example say you have two spectrum analyzers which take the same scipy commands
but you want to talk to one through prologix ethernet gpib adapter and another through ethernet

These interfaces allow you to write a shell "device class" which provides standard scipy commands
and easily merge that with built in classes which talk directly to the devices

"""
import time
import socket
import select
import warnings

def check_interface(interface):
    """
    checks if interface is a BaseInterface child or has correct functions
    TODO: test
    """
    if not isinstance(interface, BaseInterface):
        warnings.warn("{} is not a child of BaseInterface".format(type(interface)))
        getattr(interface, "write_raw")
        getattr(interface, "read_raw")
        getattr(interface, "timeout")

class InterfaceTimeoutError(Exception):
    """ raised when a read or write times out """
    pass

class BaseInterface(object):
    """ provides the declarations for basic functions needed for a interface class """
    chunk_size = 4096

    def write_raw(self, message):
        """ write message, return bytes written """
        raise NotImplementedError

    def read_raw(self, size=None):
        """ read size bytes, return read bytes """
        raise NotImplementedError

    @property
    def timeout(self):
        """ timeout for I/O operations in ms"""
        raise NotImplementedError

    @timeout.setter
    def timeout(self, value):
        """ set timeout for I/O operations """
        raise NotImplementedError



class SocketInterface(BaseInterface):
    """
    Interface to talk through a socket
    """
    def __init__(self, addr, timeout=10000, source_address=None):
        self._sock = socket.create_connection(addr, timeout/1E3, source_address)

    def write_raw(self, message):
        try:
            bytes_sent = self._sock.send(message)
        except socket.timeout as err:
            raise InterfaceTimeoutError(err)

        return bytes_sent

    def read_raw(self, size=None):
        size = self.chunk_size if size is None else size
        ret = bytes()
        try:
            chunk = self._sock.recv(size)
            ret += chunk

            while len(chunk) == size:
                sock, _, _ = select.select([self._sock], [], [], 0.5)
                if sock:
                    assert False
                    assert sock == self._sock
                    chunk = self._sock.recv(size)
                    ret += chunk
        except socket.timeout as err:
            raise InterfaceTimeoutError(err)

        return ret

    @property
    def timeout(self):
        """ returns socket timeout in ms"""
        return self._sock.gettimeout() * 1000.0

    @timeout.setter
    def timeout(self, value):
        """ sets socket timeout in ms """
        self._sock.settimeout(value / 1000.0)


class PrologixEnetController(SocketInterface):
    """ used to control multiple devices on a Prologix Ethernet controller """
    _PORT = 1234
    _eos = {'\r\n':0, '\r':1, '\n':2, '':3} # gpib termination chars
    def __init__(self, ip, timeout=10000, source_address=None):
        super(PrologixEnetController, self).__init__((ip, self._PORT),
                                                     timeout=timeout,
                                                     source_address=source_address)
        self._interfaces = set()
        self._active = None
        """
        for more info see prologix.biz manual
        mode 1 - sets controller mode
        auto 1 - automatically read
        lon 0 - disable listen only mode
        """
        init_msg = "++mode 1\n" + "++auto 1\n" + "++lon 0\n"
        self.write_raw(init_msg)

    def open(self, gpib_addr, **kwargs):
        """ returns a new PrologixEnetInterface """
        check_gpib(gpib_addr)
        
        # TODO: better error 
        if gpib_addr in self._interfaces:
            raise ValueError("GPIB interface already active")
        plx_interface = PrologixEnetInterface(self, gpib_addr)
        for key, value in kwargs.items():
            getattr(plx_interface, key)
            setattr(plx_interface, key, value)
        self._interfaces.update(gpib_addr)
        return plx_interface

    def close(self, plx_interface):
        pass

    def activate(self, plx_interface):
        pass

    def interface_write_raw(self, plx_interface, message):
        pass

    def interface_read_raw(self, plx_interface, size):
        pass


class PrologixEnetInterface(BaseInterface):
    """ device interface returned by PrologixEnetController """
    read_termination = None
    write_termination = "\r\n"
    timeout = 30000

    def __init__(self, controller, gpib_addr):
        self._controller = controller
        self._gpib_addr = gpib_addr

    @property
    def gpib_addr(self):
        return self._gpib_addr

MAV = 0x10
ERR = 0x4
class TempPrologixEnetInterface(SocketInterface):
    """ works for only one device at a time """
    def __init__(self, gpib_addr, addr, timeout=10000, source_address=None):
        check_gpib(gpib_addr)
        super(TempPrologixEnetInterface, self).__init__(addr, 1000, source_address)
        self.write_raw("++mode 1\n++auto 0\n++addr " + str(gpib_addr) + '\n'+ '++eos 0\n*CLS;*WAI;*SRE 32\n')
        # TODO: see about removing this test
        try:
            while True:
                print("TRY")
                print("READ:" + self._read_raw())
        except InterfaceTimeoutError:
            print("DONE")
            self.timeout = timeout

    def read_raw(self, size=None):
        timeout = self.timeout
        self.timeout = 50
        runs = int(timeout // 50 + 1)
        for i in range(runs):
            try:
                stb = self.serial_poll()
                if (stb & MAV) == MAV:
                    self.timeout = timeout
                    self.write_raw("++read {:d}\n".format(ord('\n')))
                    return self._read_raw()
                time.sleep(.05)
            except InterfaceTimeoutError:
                pass
        self.timeout = timeout
        raise InterfaceTimeoutError

    def _read_raw(self, size=None):
        return super(TempPrologixEnetInterface, self).read_raw(size)

    def serial_poll(self):
        self.write_raw("++spoll\n")
        stb = int(self._read_raw().rstrip('\r\n'))
        
        if (stb & ERR) == ERR:
            warnings.warn("Device has error bit set")
        return stb

    # def __del__(self):
    #     self.write_raw("++rst\n")


def check_gpib(gpib_addr):
    """
    checks if valid gpib_addr and returns it
    if not valid, raises proper exception
    """
    if isinstance(gpib_addr, tuple):
        if len(gpib_addr) <= 2:
            for addr in gpib_addr:
                check_gpib(addr)
            return gpib_addr
        raise TypeError("gpib address must be an int PAD or (PAD, SAD) tuple")

    if isinstance(gpib_addr, int) or (isinstance(gpib_addr, float) and gpib_addr.is_integer()):
        if 0 <= gpib_addr <= 30:
            return int(gpib_addr)
        else:
            raise ValueError("gpib address must be between 0 and 30 inclusive")
    else:
        raise TypeError("gpib address must be integer")
