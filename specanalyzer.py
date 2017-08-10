""" provides general spectrum analyzer classes """
from __future__ import print_function
from devices import BaseDevice

class SpectrumAnalyzer(BaseDevice):
    """ generic spectrum analyzer class """

    @property
    def center_frequency(self):
        """ get window center frequency """
        raise NotImplementedError

    @center_frequency.setter
    def center_frequency(self, value):
        """ center frequency setter """
        raise NotImplementedError

    @property
    def span(self):
        """ get window span """
        raise NotImplementedError

    @span.setter
    def span(self, value):
        """ set window span """
        raise NotImplementedError

    @property
    def reference_level(self):
        """ get reference level """
        raise NotImplementedError

    @reference_level.setter
    def reference_level(self, value):
        """ set reference level """
        raise NotImplementedError

    @property
    def continuous_sweep(self):
        """ return true if continuous sweep on """
        raise NotImplementedError

    @continuous_sweep.setter
    def continuous_sweep(self, value):
        """ set continuous sweep """
        raise NotImplementedError

    def set_window(self, freq=None, span=None, ref_lvl=None):
        """ sets window for given properties """
        if freq is not None:
            self.center_frequency = freq
        if span is not None:
            self.span = span
        if ref_lvl is not None:
            self.reference_level = ref_lvl

    def take_sweep(self):
        """ takes single sweep """
        raise NotImplementedError

    def peak_power(self):
        """ returns peak power in dBm """
        raise NotImplementedError

    def peak_frequency(self):
        """ returns peak frequency """
        raise NotImplementedError


class RandSFSP(SpectrumAnalyzer):
    """
    wrapper fo F&S FSP spectrum analyzer visa library control

    Parameters
    ----------
    addr : string
        pyvisa address string.
        https://pyvisa.readthedocs.io/en/stable/names.html

    enet_gpib_addr : int, None
        gpib address if using prologix.biz gpib ethernet controller

    Returns
    -------
    RandSFSP spectrum analyzer object
    """
    def __init__(self, interface):
        super(RandSFSP, self).__init__(interface)
        self.read_termination = '\n'
        self.timeout = 15000

    @property
    def center_frequency(self):
        """ get window center frequency (Hz)"""
        return float(self.query("*WAI;FREQ:CENT?"))

    @center_frequency.setter
    def center_frequency(self, value):
        """ center frequency setter (Hz) """
        self.write("*WAI;FREQ:CENT {0:.2f}MHz".format(value/1E6))

    @property
    def span(self):
        """ get window span (Hz)"""
        return float(self.query("*WAI;FREQ:SPAN?"))

    @span.setter
    def span(self, value):
        """ set window span (Hz) """
        self.write("*WAI;FREQ:SPAN {0:.2f}Hz".format(value))

    @property
    def reference_level(self):
        """ get reference level (dBm) """
        return float(self.query("*WAI;DISP:WIND:TRAC:Y:RLEV?"))

    @reference_level.setter
    def reference_level(self, value):
        """ set reference level (dBm) """
        self.write("*WAI;DISP:WIND:TRAC:Y:RLEV {0:.2f}dBm".format(value))

    @property
    def continuous_sweep(self):
        """ return true if continuous sweep on """
        return bool(int(self.query("INIT:CONT?")))

    @continuous_sweep.setter
    def continuous_sweep(self, value):
        """ set continuous sweep """
        arg = "ON" if value else "OFF"
        self.sync_cmd("*WAI;INIT:CONT " + arg)

    def take_sweep(self):
        """ takes a single sweep and waits for completion """
        self.sync_cmd("INIT")

    def peak_power(self):
        """ returns peak power """
        power = self.query("CALC:MARK:MAX;*WAI;CALC:MARK:Y?")
        return float(power)

    def get_peak(self):
        """ returns current peak power after adjusting reference level """
        self.auto_ref_lvl()
        return self.peak_power()

    def peak_frequency(self):
        """ returns the frequency of peak """
        freq = self.query("CALC:MARK:MAX;*WAI;CALC:MARK:X?")
        return float(freq)

    def display_on(self, disp_on=True):
        """ turns display on or off """
        arg = "ON" if disp_on else "OFF"
        self.write("SYST:DISP:UPD " + arg + ";*WAI")

    def auto_ref_lvl(self):
        """ """
        self.sync_cmd("SENS:POW:ACH:PRES:RLEV")

    def sync_cmd(self, cmd):
        """ queries operation complete after sending command """
        assert int(self.query(cmd + ";*OPC?")) == 1

    def syst_err(self):
        """ queries system err queue and returns result """
        err = self.query("SYST:ERR?")
        err = err.split(',')
        err_code = int(err[0])
        err_msg = str(err[1]).strip('"')
        return err_code, err_msg

    def rst(self):
        """ resets system """
        self.write("*RST;*WAI")

