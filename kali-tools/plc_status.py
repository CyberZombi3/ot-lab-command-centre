#!/usr/bin/env python3
"""Live view of the plant, read from the PLC over Modbus (no login needed).
Run in Kali:  python3 ~/lab/plc_status.py      (Ctrl+C to stop)

Modbus addresses on an OpenPLC:
  %IW100+  -> input registers 100+     (sensor values the PLC reads)
  %QW100+  -> holding registers 100+   (valve commands the PLC sends)
  %QW10+   -> holding registers 10+    (manual-mode valve setpoints)
  %MW0+    -> holding registers 1024+  (setpoints in the PLC program)
  %QX0.0   -> coil 0 (manual_mode)     %QX5.0 -> coil 40 (run_bit)
Raw values are 0-65535 and scaled to engineering units below.
"""
import sys
import time
from pymodbus.client import ModbusTcpClient

PLC = "192.168.95.2"
pct = lambda raw: raw * 100 / 65535


def show(c):
    ir = c.read_input_registers(100, count=13, slave=1).registers
    valve_cmd = c.read_holding_registers(100, count=4, slave=1).registers
    sp = c.read_holding_registers(1024, count=5, slave=1).registers
    manual = c.read_coils(0, count=1, slave=1).bits[0]
    run = c.read_coils(40, count=1, slave=1).bits[0]
    print(time.strftime("%H:%M:%S"),
          f"| pressure {ir[8]*3200/65535:6.0f} kPa (setpoint {sp[2]*3200/65535:.0f})",
          f"| level {pct(ir[9]):4.1f}%",
          f"| valves F1 {pct(ir[0]):3.0f}% F2 {pct(ir[2]):3.0f}% purge {pct(ir[4]):3.0f}% product {pct(ir[6]):3.0f}%",
          f"| analyser A {pct(ir[10]):4.1f}% B {pct(ir[11]):4.1f}% C {pct(ir[12]):4.1f}%",
          f"| mode {'MANUAL' if manual else 'auto'}{'' if run else ' STOPPED'}")


c = ModbusTcpClient(PLC, port=502, timeout=3)
if not c.connect():
    sys.exit(f"Can't reach the PLC at {PLC}:502 (firewall blocking it, or the PLC is stopped?)")
try:
    while True:
        show(c)
        time.sleep(2)
except KeyboardInterrupt:
    pass
finally:
    c.close()
