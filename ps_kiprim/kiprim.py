"""
Kiprim DC310S Power Supply Library.

This library is part of ONE ITest framework.

@author:  jgonzalezsosa@one.com
@version: 1.0.0

@change: JGonzalez - 6/21/23 - Draft initial control power supply

"""

import serial

class KiPrim_PowerSupply(object):
    """
    KiPrim Power Supply

    Serial decoding commands information:
    https://github.com/maximweb/kiprim-dc310s/blob/main/README.md

    This class manages the KiPrim Power supply.
    """

    def __init__(self, com_port):

        try:
            self.power_supply = serial.Serial(
            port = com_port,
            baudrate = 115200,
            parity = serial.PARITY_NONE,
            stopbits = serial.STOPBITS_ONE,
            bytesize = serial.EIGHTBITS,
            timeout = 1
        )
        except Exception as e:
            print(f'Unable to configure port {com_port}, please check is the right port. ')

        self.config_port()

    def config_port ( self ):
        try:
            self.power_supply.close()
            self.power_supply.open()
        except Exception as e:
            print( f"Error open serial port: {str(e)}" )
            exit()

    def send_command(self, command):
        self.power_supply.write(command.encode())
        response = self.power_supply.readline().decode().strip()
        return response

    def get_instrument_id(self):
        return self.send_command("*IDN?\n")

    def get_instrument_protection(self):
        return self.send_command("INT:PRO?\n")

    def get_measured_voltage(self):
        return self.send_command("MEAS:VOLT?\n")

    def get_measured_current(self):
        return self.send_command("MEAS:CURR?\n")

    def get_output_status(self):
        return self.send_command("OUTP?\n")

    def get_voltage_setting(self):
        return self.send_command("VOLT?\n")

    def get_current_setting(self):
        return self.send_command("CURR?\n")

    def get_voltage_limit(self):
        return self.send_command("VOLT:LIM?\n")

    def get_current_limit(self):
        return self.send_command("CURR:LIM?\n")

    def set_remote_mode(self):
        self.send_command("SYST:REM\n")

    def get_updated_voltage_limit(self):
        return self.send_command("VOLT:LIM?\n")

    def get_updated_current_limit(self):
        return self.send_command("CURR:LIM?\n")

    def get_max_voltage_limit(self):
        return self.send_command("VOLT:LIM? MAX\n")

    def get_min_voltage_limit(self):
        return self.send_command("VOLT:LIM? MIN\n")

    def get_max_voltage(self):
        return self.send_command("VOLT? MAX\n")

    def get_min_voltage(self):
        return self.send_command("VOLT? MIN\n")

    def get_max_current_limit(self):
        return self.send_command("CURR:LIM? MAX\n")

    def get_min_current_limit(self):
        return self.send_command("CURR:LIM? MIN\n")

    def get_max_current(self):
        return self.send_command("CURR? MAX\n")

    def set_voltage(self, value):
        command = f"voltage {value}\n"
        self.send_command(command)

    def set_current(self, value):
        command = f"current {value}\n"
        self.send_command(command)

    def set_output_on(self):
        self.send_command("output 1\n")

    def set_output_off(self):
        self.send_command("output 0\n")

if __name__ == '__main__':
    # execute only if run as the entry point into the program
    a = KiPrim_PowerSupply('COM4')
    print('helo')
