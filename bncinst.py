""" contains methods to interface with signal generators """
from signalgenerator import SignalGenerator

MHZ = 1E6

class ValueSetException(Exception):
    """
    An instrument value couldn't be set. This usually happens when you set a
    value outside of the instruments range.
    """
    pass


class BNC845(SignalGenerator):
    """
    class which represents a BNC845 signal generator
    (https://www.berkeleynucleonics.com/microwave-signal-generators)
    """

    @property
    def raw_frequency(self):
        return self.get_freq()

    @raw_frequency.setter
    def raw_frequency(self, value):
        self.set_freq(value / 1E6)


    def set_freq(self, new_freq, check=True):
        """
        sets frequency to freq (MHZ)
        if check is True then asks instrument if frequency was properly set
        Error to pass no frequency
        Raise ValueSetException if frequency could not be set
        """
        assert new_freq is not None
        self.write(':FREQ ' + str(new_freq) + 'MHZ')

        if check and abs(self.get_freq() / MHZ - new_freq) > 1E-5:
            raise ValueSetException(
                "Frequency could not be set {0:>.2}".format(new_freq))

    def get_freq(self):
        """ returns the frequency on the front panel of the instrument in MHZ """
        return float(self.query(':FREQ?'))

    @property
    def raw_power(self):
        return self.get_power()

    @raw_power.setter
    def raw_power(self, value):
        self.set_power(value)


    def set_power(self, new_power, check=True):
        """
        set power to power in dbm
        if check is True then asks instrument if power was properly set
        Error to pass no power
        Raise ValueSetException if power could not be set
        """
        assert new_power is not None
        self.write(':POW ' + str(new_power))

        if check and abs(self.get_power() - new_power) > 1E-5:
            raise ValueSetException(
                "Power could not be set {0:>.2}".format(new_power))

    def get_power(self):
        """ returns the power on the front panel of the instrument in dbm """
        return float(self.query(':POW?'))

    @property
    def signal_on(self):
        return bool(int(self.query(":OUTP?")))

    @signal_on.setter
    def signal_on(self, value):
        if value:
            self.rf_on()
        else:
            self.rf_off()

    def rf_on(self):
        """ Tells instrument to turn on rf signal """
        self.write(':OUTP ON')

    def rf_off(self):
        """ Tells instrument to turn off rf signal """
        self.write(':OUTP OFF')
