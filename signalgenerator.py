""" contains signal generator classes """

from __future__ import print_function
from time import sleep
import numpy as np
from scipy.interpolate import interp1d

from bncinst import BNC845

DEFAULT_ADDRESS = ('131.243.201.231', 18)

class SignalGenerator(BaseDevice):
    """
    Represents a signal generator. Provides methods to interface with the signal generator at
    a higher level.

    This representation includes support for using 'gain files' which map 'panel power outputs'
    (powers that a signal generator thinks it's outputting) to the gain at that panel power output.
    When a gain file is specified, every power that the user sees is 'real power output' which is
    then translated to 'panel power output' to be sent to the signal generator

    WARNING: these maps are approximate (especially with unstable signals) USE AT YOUR OWN RISK

    TODO: make signal generator generic. Currently only works with BNC845 class.

    Parameters
    ----------
    addr : tuple ('ip.address', port), optional
        address tuple to be passed to socket

    min_output : optional
        minimum real power output that the signal generator is allowed to output.

    max_output : optional
        maximum real power output that the signal generator is allowed to output.

    gain_file : str, optional
        name of the gain file to use

    Returns
    -------
    SignalGenerator object
    """
    def __init__(self, interface, min_output=None, max_output=None, gain_file=None):
        # initialize signal generator
        super(SignalGenerator, self).__init__(interface)
        self._gain_file = gain_file
        if self._gain_file is not None:
            raws, gains = np.loadtxt(self._gain_file, unpack=True)
            self._raw_to_real = interp1d(raws, raws + gains)
            self._real_to_raw = interp1d(raws + gains, raws)
            self.min_output = min_output if min_output is not None else self._raw_to_real(panels[0])
            self.max_output = max_output if max_output is not None else self._raw_to_real(panels[-1])
        else:
            self.min_output = min_output if min_output is not None else -1E99
            self.max_output = max_output if max_output is not None else 1E99

    @property
    def frequency(self):
        """ gets real signal frequency (currently alias as raw_frequency) """
        return self.raw_frequency

    @frequency.setter
    def frequency(self, value):
        """ set real signal frequency (currently alias for raw_frequency) """
        self.raw_frequency = value
    
    @property
    def power(self):
        """ returns current real output power """
        return self.raw_to_real(self.raw_power)
        
    @power.setter
    def power(self, value):
        """ sets real power """
        new_power = self.real_to_raw(value)
        assert min_power <= new_power <= max_power
        self.raw_power = new_power

    def power_sweep(self, output_powers, callback, state=None):
        """
        sets the power to each power in out_powers in order calling callback with each set power

        Parameters
        ----------
        out_powers : iterable
            the output powers to use
        callback : function(power, state)
            called on each set power with power and state as arguments
        state :
            passed to callback on each set power
        """
        self.signal_on = False
        self.power(output_powers[0])
        try:
            self.signal_on = True
            sleep(1)
            for power in output_powers:
                self.power = power
                callback(power, state)
        except:
            self.signal_on = False
            raise

        self.rf_off()

    def raw_to_real(self, raw_power):
        """ returns real output from raw output """
        if self._gain_file is not None:
            return self._raw_to_real(raw_power)
        else:
            return raw_power

    def real_to_raw(self, real_power):
        """ returns raw power from real power """
        if self._gain_file is not None:
            return self._real_to_raw(real_power)
        else:
            return real_power

    """ abstract functions """
    @property
    def raw_frequency(self):
        """ gets raw signal frequency """
        raise NotImplementedError
    
    @raw_frequency.setter
    def raw_frequency(self, value):
        """ sets raw signal frequency """
        raise NotImplementedError

    @property
    def raw_power(self):
        """ gets raw power """
        raise NotImplementedError

    @raw_power.setter
    def raw_power(self, value):
        """ sets raw power """
        raise NotImplementedError

    @property
    def signal_on(self):
        """ returns true if signal is currently active else false """
        raise NotImplementedError

    @signal_on.setter
    def signal_on(self, value):
        """ set signal on or off """
        raise NotImplementedError

