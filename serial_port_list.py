# This file is part of the BVM-run Ventilator suite, it's based on 
# Printrun.
#
# BVM-run and Printrun is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Printrun is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a c seopy of the GNU General Public License
# along with Printrun.  If not,e <http://www.gnu.org/licenses/>.

import serial.tools.list_ports
ports = serial.tools.list_ports.comports()

for port, desc, hwid in sorted(ports):
        print("{}: {} [{}]".format(port, desc, hwid))


"""
Linux/RaspBerry
$python3 serial_port_list.py

    example list
    /dev/ttyACM0: ttyACM0 [USB VID:PID=2341:0042 SER=5573631333735151F001 LOCATION=1-1.2:1.0]
    /dev/ttyAMA0: ttyAMA0 [fe201000.serial]
    /dev/ttyUSB0: USB Serial [USB VID:PID=1A86:7523 LOCATION=1-1.1]

    ==> /dev/ttyACM0  [connect to Adruino Mega RAMP1.4 for BVM-run Ventilator]
    ==> /dev/ttyUSB0  [connect to Adruino Nano Air Flow Meter & Pressure Sensor]


Windows
>python serial_port_list.py

    example list
    COM5: USB 序列裝置 (COM5) [USB VID:PID=2341:0042 SER=5573631333735151F001 LOCATION=1-3]
    COM6: USB-SERIAL CH340 (COM6) [USB VID:PID=1A86:7523 SER=5 LOCATION=1-2]

    ==> COM5  [connect to Adruino Mega RAMP1.4 for BVM-run Ventilator]
    ==> COM6  [...CH340... connect to Adruino Nano Air Flow Meter & Pressure Sensor]
"""