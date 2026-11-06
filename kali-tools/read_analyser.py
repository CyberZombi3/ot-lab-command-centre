#!/usr/bin/env python3
"""Read the gas analyser directly, bypassing the PLC. No login needed: Modbus has none.
Run in Kali:  python3 ~/lab/read_analyser.py      (Ctrl+C to stop)

The analyser at 192.168.95.15 (unit ID 247) has 3 input registers starting at
address 1: the % of component A, B and C in the purge gas, scaled 0-65535 = 0-100%.
"""
import sys
import time
from pymodbus.client import ModbusTcpClient

ANALYSER = "192.168.95.15"

c = ModbusTcpClient(ANALYSER, port=502, timeout=3)
if not c.connect():
    sys.exit(f"Can't reach the analyser at {ANALYSER}:502 (blocked by the firewall?)")
try:
    while True:
        raw = c.read_input_registers(1, count=3, slave=247).registers
        a, b, cc = (r * 100 / 65535 for r in raw)
        print(time.strftime("%H:%M:%S"), f"raw {raw}  ->  A {a:5.1f}%   B {b:5.1f}%   C {cc:5.1f}%")
        time.sleep(1)
except KeyboardInterrupt:
    pass
finally:
    c.close()
