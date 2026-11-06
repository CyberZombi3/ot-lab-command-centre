#!/usr/bin/env python3
"""Undo manual_takeover.py: put the PLC back in automatic control.
Run in Kali:  python3 ~/lab/back_to_auto.py
"""
from pymodbus.client import ModbusTcpClient

c = ModbusTcpClient("192.168.95.2", port=502, timeout=3)
c.connect()
c.write_coil(0, False, slave=1)                      # manual_mode off
c.write_registers(10, [0, 0, 65535, 65535], slave=1)  # restore the program's default manual setpoints
c.close()
print("PLC back in AUTO. The control loops will bring pressure back to ~2700 kPa.")
