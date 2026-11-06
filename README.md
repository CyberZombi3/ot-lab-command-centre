# OT Lab Command Centre

A hands-on OT security course and control panel built on top of
[GRFICSv3](https://github.com/Fortiphyd/GRFICSv3), the open-source ICS training range from
[Fortiphyd Logic](https://fortiphyd.com).

GRFICSv3 gives you a simulated chemical plant with a real PLC (OpenPLC), an operator HMI,
a firewall, a Kali attacker and security monitoring (Wazuh and Zeek). I built this layer on
top of it to turn it into a guided course:

- **Command Centre**: a local web page that shows plant status (pressure, valves, E-stop,
  PLC state), lights for every system, one-click restarts, and a split-screen workspace with
  the HMI, Kali, the 3D plant and the SIEM side by side.
- **8 missions** with objectives, ⚑ flag questions, XP and medals, from passive discovery
  through to attacking the PLC, detecting it, defending it, and writing a factory acceptance
  test (FAT) security report in IEC 62443-3-3 terms.
- **[EXERCISES.md](EXERCISES.md)**: the course itself. Every step says where to run it, what to
  type, what's happening and what you should see.
- **Kali scripts** (`kali-tools/`) for reading the analyser, watching the PLC, writing valves
  and taking manual control, plus a Zeek helper (`tools/zeek-talkers.sh`).

> ⚠️ **This lab is deliberately vulnerable.** Run it on your own machine only. Everything
> listens on localhost; don't expose it to a network, and never point the scripts at real
> equipment. Writing to a real PLC can hurt people.

This is a personal project, not an official Fortiphyd product. All credit for the plant,
PLC, HMI and range goes to the GRFICS team.

## What you need

- **Docker** with Compose. Tested on macOS (Apple silicon) with
  [Colima](https://github.com/abiosoft/colima). Native Linux should work the same way.
  Docker Desktop runs everything except Zeek's traffic mirror (the Zeek steps won't show data).
- **About 16 GB of RAM free** for the lab, and plenty of free disk space (the images are large).
- `git`, `python3` (standard library only), `curl` and `jq`.

On a Mac:

```
brew install colima docker docker-compose jq
```

Keep this folder somewhere inside your home folder: Colima only shares your home folder with
its virtual machine, and Zeek's mirror script runs from there.

## Setup (once)

```
git clone https://github.com/CyberZombi3/ot-lab-command-centre.git ot-lab
cd ot-lab
./lab.sh setup
```

`setup` downloads GRFICSv3 from Fortiphyd's GitHub into `./GRFICSv3` (pinned to the version
the course was written against) and pulls its images. On a Mac it also creates the Colima VM
with 6 CPUs and 16 GB of RAM (change with `LAB_CPUS` and `LAB_MEM_GB`).

Already have GRFICSv3 somewhere else? Point at it instead: `export GRFICS_DIR=/path/to/GRFICSv3`.

## Use

```
./lab.sh start     # starts the lab and opens the Command Centre at http://localhost:4900
./lab.sh kali      # a terminal inside the Kali attacker
./lab.sh stop      # frees the RAM when you're done
```

Then open **Mission 1** in the Command Centre (or [EXERCISES.md](EXERCISES.md)) and follow along.
Your progress is saved in `command-centre/progress.json`.

Other commands: `status`, `restart <system>`, `estop-release`, `reset` (factory defaults,
keeps your progress). Most of these are buttons in the Command Centre too.

## How it works

- `lab.sh` wraps `docker compose --profile siem` in the GRFICSv3 folder, sets up Zeek's
  traffic mirror (needs root on the Docker host, via `colima ssh` on a Mac or `sudo` on
  Linux) and copies the Kali scripts into the attacker.
- `command-centre/server.py` is a small Python server (standard library only) on
  `127.0.0.1:4900`. It reads container status from Docker, plant values from the simulator's
  web endpoint and alerts from Wazuh's log file, so the dashboard itself never adds Modbus
  traffic to what you're analysing.
- The HMI and Wazuh refuse to be shown inside another page, so the server runs two local
  relays (ports 4981 and 4951) that pass them through without that header. They also only
  listen on localhost.
- Buttons can only run a fixed list of `lab.sh` actions, and requests from other websites are
  blocked.

## Credits and licence

- **GRFICSv3** © Fortiphyd Logic, GPLv3. Not included in this repository; `./lab.sh setup`
  downloads it from [github.com/Fortiphyd/GRFICSv3](https://github.com/Fortiphyd/GRFICSv3).
  Fortiphyd also offers commercial ICS training: [fortiphyd.com](https://fortiphyd.com).
- Everything in this repository (Command Centre, course, scripts) is MIT licensed. See
  [LICENSE](LICENSE).
