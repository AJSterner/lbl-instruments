from __future__ import print_function
from devices import BaseDevice
from interfaces import PrologixEnetController

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
        self.read_termination='\n'
        self.timeout=15000
    
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
        opc = self.query("INIT:CONT " + arg + ";*OPC?")
        assert int(opc) == 1

    def take_sweep(self):
        """ takes a single sweep and waits for completion """
        opc = self.query("INIT;*OPC?")
        assert int(opc) == 1

    def peak_power(self):
        """ returns peak power """
        power, opc = self.query("CALC:MARK:MAX;*WAI;CALC:MARK:Y?;*OPC?").split(';')
        assert int(opc) == 1
        return float(power)
    
    def get_peak(self):
        """ returns current peak power after adjusting reference level """
        self.auto_ref_lvl()
        return self.peak_power()

    def peak_frequency(self):
        """ returns the frequency of peak """ 
        freq, opc = self.query("CALC:MARK:MAX;*WAI;CALC:MARK:X?;*OPC?").split(';')
        assert int(opc) == 1

        return float(freq)

    def disp_on(self, on=True):
        """ turns display on or off """
        arg = "ON" if on else "OFF"
        self.write("SYST:DISP:UPD " + arg)
        self.sync_opc()

    def auto_ref_lvl(self):
        """ runs the """
        self.write("SENS:POW:ACH:PRES:RLEV;*OPC?")
        assert int(self.read()) == 1

    def sync_opc(self):
        """ queries operation complete? """
        assert int(self.query("*OPC?")) == 1
    
    def syst_err(self):
        """ queries system err queue and returns result """
        err = self.query("SYST:ERR?")
        err = err.split(',')
        err_code = int(err[0])
        err_msg = str(err[1]).strip('"')
        return err_code, err_msg

class EnetRandSFSP(RandSFSP):
    """
    wrapper class for RandSFSP which allows it to be used over prologix.biz gpib ethernet controller

    Parameters
    ----------
    ip_addr : string
        ip address of prologix.biz controller.

    gpib_addr : int
        gpib address of instrument

    Returns
    -------
    RandSFSP spectrum analyzer object
    """
    def __init__(self, ip_addr, gpib_addr):
        super(EnetRandSFSP, self).__init__("TCPIP::" + ip_addr +"::1234::SOCKET")
        self.write("++mode 1\n++auto 1\n++addr {0:d}".format(gpib_addr))

class HP8593E(SpectrumAnalyzer):
    """ wrapper for HP8593H visa library control """
    def __init__(self, addr):
        super(HP8593E, self).__init__(addr, read_termination='\n')
        
    def write(self, msg):
        self.inst.write(msg)

    def read(self):
        return self.inst.read()

    def query(self, msg, fix_skipping=False):
        ret_msg = self.inst.query(msg)
        while fix_skipping and not ret_msg:
            ret_msg = self.inst.query(msg)
        return ret_msg

    def single_sweep(self):
        self.write('SNGLS;')

    def take_sweep(self):
        self.write('TS;')

    def set_window(self, freq, span, amp):
        assert amp < 30
        cmd_str = 'CF ' + str(freq) + ' MHZ;'
        cmd_str += 'SP ' + str(span) + ' MHZ;'
        cmd_str += 'RL' + str(amp) + 'DB;'
        self.write(cmd_str)

    def peak_zoom(self):
        self.write('PKZOOM 1MHZ')
        # Check peak zoom found peak
        ok = self.query('PKZMOK?;')
        assert int(ok) != 0

    def marker_amp(self):
        return float(self.query('MKA?;'))

    def peak(self):
        return self.marker_amp()

    def marker_freq(self):
        """ returns marker frequency in MHZ """
        return float(self.query('MKF?;'))/1E6


    def get_peak(self):
        self.peak_zoom()
        return self.peak()

    def continuous_sweep(self):
        self.write('CONT;')
