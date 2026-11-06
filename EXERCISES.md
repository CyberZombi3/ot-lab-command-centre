# OT Security Foundations: a hands-on course

You're going to assess a small chemical plant the way you would at a real customer site.
You'll start by looking and listening, move on to attacking it, then switch sides to detect
and defend it, and finish by writing the kind of security test report an analyser or control
panel supplier hands to its customer.

**Who it's for:** someone who already knows IT security (networks, Linux, a bit of Python)
but is new to industrial control systems. Every OT idea is explained the first time it comes up.

**How long:** 8 missions, each sized for one evening (30-60 minutes). Do them in order; each
one uses what the last one taught you.

**How each mission works:**

1. **What you'll learn**: the point of the evening, in three or four bullets.
2. **Background**: the theory you need, in plain English. Read this first; it's short.
3. **Steps**: numbered. Every step tells you:
   - **Where**: which machine to type on (see below).
   - **Do**: exactly what to type or click.
   - **What's happening**: what that does behind the scenes.
   - **You should see**: the result, so you know it worked.
4. **Check yourself**: a couple of questions, with answers hidden until you click.
5. **In the real world**: how this applies on an actual site, and to a company that builds and ships control panels.
6. **Command Centre**: tick the objectives and answer the ⚑ questions to earn XP.

---

## Before you start

### Starting and stopping

First time only: follow **Setup** in the README (`./lab.sh setup` downloads GRFICSv3 and its
images). Every command below runs from this project's folder.

**Where:** 🖥 Host terminal

```
./lab.sh start
```

**What's happening:** this starts about a dozen containers (on a Mac, inside a Colima Linux
virtual machine): the plant simulator, the PLC, the operator's screen, a firewall, an attacker machine
and two security sensors. It wires up the network sensor, copies some helper scripts into the
attacker machine, and opens the **Command Centre** at http://localhost:4900.

**You should see:** the Command Centre opens straight away. Its lights turn green one by one
over 2-3 minutes. The Terminal finishes with `Lab is up.`

When you've finished for the evening, stop it to free up 16GB of RAM:

```
./lab.sh stop
```

Your mission progress is saved, so you can stop at any point and carry on next time.

### The Command Centre

Keep it open in a browser tab. From top to bottom:

- **Plant status**: is the emergency stop tripped, is the PLC running, the reactor pressure,
  the valve positions and the analyser reading. **If anything is red, fix it with the button on
  that tile before you carry on.**
- **Workspace**: every system runs inside the page.
  - The **bar of tiles** along the top lists them all, with live status (pressure, PLC state…).
    The two on screen are highlighted and tagged **L** and **R**.
  - **Click a tile** to show it in the highlighted panel (click a panel to highlight it).
    Hover a tile for **◧ left** / **◨ right** to choose the side directly.
  - Each panel has **⇄** (swap sides), **□** (show only this one; **◫** brings the pair back),
    **⟳** (reload) and **↗** (open in a new tab).
  - **⤢ Expand** fills the screen (Esc to exit).
  - Everything stays loaded in the background, so switching is instant and never logs you out.
  - **🎯 Missions** is a tile too: it opens your objectives, ⚑ questions and medals in a panel.
    Its tile shows your current mission, progress and XP. "Show Mission N" opens the guide
    beside it.
  - Good layouts: **Guide + Kali** while you follow the steps, **Missions + Kali** to tick
    objectives and enter answers as you go, **Kali + HMI** for Mission 5.
- **Systems**: one card per machine, with a status light, a **View** button (shows it in the
  workspace), **↗** (opens it in a new tab instead), its login (click
  🔑 to copy the password) and a **Restart** button.
- **Missions**: objectives to tick and ⚑ questions to answer. Each one links to its section of
  this guide.

### Where you type commands

Every command in this course is labelled with where it runs. Getting this wrong is the most
common reason something "does nothing".

- **🖥 Host terminal** is a normal terminal on your own computer, in this project's folder. You use it to read the sensor's logs
  and control the lab. Think of it as the **defender's / lab owner's** seat.
- **🐉 Kali** is a terminal *inside* the attacker machine, which sits on the plant's DMZ network.
  Think of it as a laptop **an attacker has plugged into the plant**. To open one, type this in a
  host terminal:

  ```
  ./lab.sh kali
  ```

  The prompt changes to `kali@kali:~$`. You're now "inside". Type `exit` to come back to your computer.
  Ready-made scripts are in `~/lab` inside Kali.

> 💡 Two Terminal windows side by side works well: host on the left, Kali on the right.

### When things go wrong

| Symptom | Cause | Fix |
|---|---|---|
| Nothing moves, valves frozen, HMI changes do nothing | **E-stop is tripped.** Pressing **E** next to the red button in the 3D plant trips it | Plant status → **Release E-stop** |
| PLC tile says **STOPPED** | The PLC program crashed or was stopped. OpenPLC can crash when a connection drops suddenly (a lesson in itself about fragile OT devices) | **Restart PLC** button on that tile |
| Pressure creeps up slowly after a restart | Normal start-up. It climbs to the 2700 kPa setpoint (about 10 minutes), then the purge valve opens | Wait |
| A Kali script says *Can't reach...* | Either you've already done Mission 7 (the firewall now blocks you, which is correct), or that system is down | Check the Systems lights. To undo Mission 7, use **Reset entire lab** |
| Anything else odd | | Danger zone → **Reset entire lab** (keeps your mission progress) |

---

## The plant

Read this once now and come back to it whenever you need an IP address.

**What it does:** a chemical reactor. Two gas feeds (**Feed 1** and **Feed 2**) go in. They react
inside a pressurised tank. Two streams come out: the **product** (what the plant sells) and a
**purge** (waste gas vented to stop pressure building up).

**How it's controlled:** a **PLC** (programmable logic controller, a small industrial computer)
reads every sensor and sets every valve, 10 times a second. Its main job is to hold the reactor
at **2700 kPa** by opening the purge valve more or less. It also reads the **analyser**, an
instrument that measures the mix of gases A, B and C in the purge, and adjusts the feeds to keep
the chemistry right. If pressure goes far above setpoint, the reactor is in danger.

| Zone | Address | What it is |
|---|---|---|
| ICS network | 192.168.95.10 / .11 | Feed 1 and Feed 2 valves (remote I/O boxes) |
| ICS network | 192.168.95.12 / .13 | Purge and Product valves |
| ICS network | 192.168.95.14 | Tank (pressure and level sensors) |
| ICS network | 192.168.95.15 | **Analyser** |
| ICS network | 192.168.95.2 | **PLC** (OpenPLC) |
| ICS network | 192.168.95.5 | Engineering workstation (EWS), where engineers edit the PLC program |
| DMZ | 192.168.90.107 | **HMI**, the operator's screen |
| DMZ | 192.168.90.6 | **Kali**: you, the attacker |
| Both | .95.200 and .90.200 | **Router / firewall** between the two zones |
| Sensor | (mirror) | **Zeek** gets a copy of all traffic, like a switch SPAN port |

---

## Mission 1: Walk the plant

⏱ 40 minutes

**What you'll learn**

- What the physical process is and what can go wrong with it.
- What the operator sees and how they control the plant.
- What a PLC is and where its weak points are.
- How OT networks are organised into levels (the Purdue model).

### Background

Before testing anything on a real site, you walk it with an engineer. In OT the goal is
different from IT. In IT, the worst case is usually stolen data. **In OT the worst case is
physical**: an explosion, a toxic release, a fire or an injury. So the priority order flips:

| | IT priority | OT priority |
|---|---|---|
| 1st | Confidentiality | **Safety**, then **Availability** |
| 2nd | Integrity | Integrity |
| 3rd | Availability | Confidentiality |

Keep that table in mind all course. Any test or fix that stops the plant is a failure, even
if it's "more secure".

There are three layers to get to know:

- **The process**: pipes, valves, tanks and sensors. (*Level 0*)
- **The controller (PLC)**: runs a program in a tight loop, called the **scan cycle**: read all
  inputs, run the logic, write all outputs, repeat. (*Level 1*)
- **Supervisory systems**: the **HMI** (Human-Machine Interface: the operator's screen) and the
  **EWS** (Engineering Workstation, used to change PLC programs). (*Level 2*)

### Step 1.1: Walk the 3D plant ✅ (you've done this)

**Where:** browser → Command Centre → Plant (3D) → **View**

**Do:** **WASD** to move, mouse to look, **E** to interact, **Esc** to get your mouse pointer back.
Find the 9 physical vulnerabilities.

**What's happening:** the 3D view is drawn from the same simulator the PLC controls, so the valves
and gauges you see are live.

> ⚠ The red button on the plant floor is the **emergency stop**. Pressing **E** on it freezes every
> valve in its safe position. If Plant status shows E-stop tripped, press **Release E-stop**.

### Step 1.2: Look at the HMI, the operator's screen

**Where:** browser → Command Centre → HMI → **View**. Log in **admin / admin**.

**Do:** don't change anything yet. Just find these on the reactor picture:

1. **Pressure** and **Level** in the middle of the tank.
2. Each valve's **% open** and each pipe's **flow** (in kMol/h).
3. **MANUAL MODE: OFF** at the top left, and **RUNNING** at the top right.
4. Four boxes such as **F1ManualSP** and **PurgeManualSP**.

**What's happening:** the HMI doesn't touch the plant itself. It asks the PLC for values a few
times a second over the network and draws them. When an operator types a value, the HMI sends
it to the PLC, and the PLC decides what to do with it.

**Why changing the ManualSP boxes did nothing:** "SP" means **setpoint**: the value you want
something held at. These four are the valve positions the PLC uses **only in manual mode**. In
normal (automatic) mode, the PLC's control loops calculate every valve position themselves and
ignore those boxes. You'll switch the PLC into manual mode yourself, from the attacker's
machine, in Mission 5.

**You should see:** a pressure close to **2700 kPa**. It should match the pressure on the
Command Centre's Plant status tile to within a few kPa.

### Step 1.3: Log in to the PLC

**Where:** browser → Command Centre → PLC → **View**. Log in **openplc / openplc**.

**What's happening:** OpenPLC is open-source PLC software. Real PLCs (Siemens, Allen-Bradley,
Schneider) have similar web or engineering interfaces. This one still has its **factory default
password**. That's your first finding: write it down.

**Do, and what you should see:**

1. **Dashboard**: Status **Running**, Program **Chemical Reactor**. Notice the **Stop PLC**
   button. Anyone with that password can stop the plant's controller with one click.
2. Left menu → **Slave Devices**. This is the list of field devices the PLC talks to, with their
   IP addresses. Count them, and compare them with the plant table above.
3. Left menu → **Programs**. This shows the control logic that's loaded. You'll read it in Mission 5.

Don't press Stop PLC. If you do by accident, use **Restart PLC** on the Command Centre.

### Step 1.4: Put each device on the Purdue model

**Background:** the **Purdue model** is the standard way of drawing an OT network as levels,
from the physical process at the bottom to the corporate IT network at the top. Traffic should
only pass between neighbouring levels, through controlled points.

| Level | Name | What lives there |
|---|---|---|
| 4-5 | Enterprise (IT) | Email, ERP, the internet |
| 3.5 | **DMZ** | The boundary between IT and OT |
| 3 | Site operations | Historians, site servers |
| 2 | Supervisory | HMI, EWS |
| 1 | Control | PLCs |
| 0 | Process | Sensors, valves, analysers |

**Do:** on paper, put every device from the plant table at its level.

**Check yourself**

<details><summary>Where should the HMI be, and where is it in this lab?</summary>

It's a Level 2 system, so it should be inside the control network. Here it sits in the DMZ,
which is common on real sites (operators want it reachable from the office) and is a risk:
the DMZ is easier for an attacker to reach.
</details>

<details><summary>Which single device sits between the DMZ and the ICS network?</summary>

The router/firewall (.90.200 / .95.200). If it's misconfigured, everything below it is exposed.
You'll look at its rules in Mission 7.
</details>

### In the real world

On a real job, this mission is the **site walk and document review**: drawings, network
diagrams, the PLC's I/O list and the HMI screens. Most findings in OT assessments come from
this stage, before anyone touches a keyboard.

### Command Centre

Tick the four objectives. **⚑** Answer: how many field devices the PLC polls, and whether it
normally runs in auto or manual.

---

## Mission 2: Passive discovery

⏱ 40 minutes

**What you'll learn**

- How Modbus, the most common OT protocol, works.
- How to map a network **without sending a single packet**.
- How to read a network sensor's logs.
- How to build an asset inventory.

### Background

**Why passive first?** OT devices can be old and fragile. A scan that an office PC wouldn't
notice can crash a PLC, and a crashed PLC can stop a plant. So on a real site, step one is
always to **listen**. The site gives you a **SPAN port** (a switch port that receives a copy of
all traffic), and you plug in a sensor.

**What's listening here?** **Zeek**, a free network sensor. The lab mirrors every packet on both
networks to Zeek. Zeek understands industrial protocols: for every Modbus request, it writes one
line to a log saying who asked, who answered and what was asked. You read those logs from your
computer. **You're not listening for sound**, you're reading a record of network conversations.

**Modbus in five minutes.** Modbus is from 1979 and still everywhere. It works like this:

- A **master** (here, the PLC or the HMI) asks; a **slave** (a field device or the PLC) answers.
  Slaves never speak first.
- It runs over TCP **port 502**.
- Each device has a **unit ID** (a number from 0 to 255) that says which device behind an
  address you mean.
- Data lives in four tables:

  | Table | Holds | Can a master write it? |
  |---|---|---|
  | **Coils** | on/off bits (e.g. "manual mode on") | Yes |
  | **Discrete inputs** | on/off bits (e.g. "door open") | No |
  | **Input registers** | 16-bit numbers (e.g. a sensor reading) | No |
  | **Holding registers** | 16-bit numbers (e.g. a setpoint) | Yes |

- Each request has a **function code** saying what to do, e.g. `READ_INPUT_REGISTERS` or
  `WRITE_MULTIPLE_REGISTERS`.
- **There is no login, no password and no encryption.** If you can reach port 502, the device
  does what you ask. Keep that in mind for the next three missions.

### Step 2.1: Look at a raw log line

**Where:** 🖥 Host terminal (not Kali: the sensor logs aren't visible from the attacker's machine)

**Do:**

```
docker exec zeek tail -n 2 /usr/local/zeek/logs/modbus.log
```

**What's happening:** `docker exec zeek` runs a command inside the Zeek container. `tail -n 2`
prints the last two lines of its Modbus log.

**You should see** two lines of JSON straight away, like this (trimmed):

```
{"id.orig_h":"192.168.95.2","id.resp_h":"192.168.95.15","id.resp_p":502,"unit":247,"func":"WRITE_MULTIPLE_REGISTERS","pdu_type":"REQ"}
{"id.orig_h":"192.168.95.2","id.resp_h":"192.168.95.15","id.resp_p":502,"unit":247,"func":"WRITE_MULTIPLE_REGISTERS","pdu_type":"RESP"}
```

How to read it:

| Field | Meaning | In this example |
|---|---|---|
| `id.orig_h` | Who started the conversation: the **master** | 192.168.95.2, the PLC |
| `id.resp_h` / `id.resp_p` | Who answered, and on which port: the **slave** | the analyser, port 502 |
| `unit` | Modbus unit ID | 247 |
| `func` | What was asked | writing some registers |
| `pdu_type` | `REQ` = the question, `RESP` = the answer | one of each |

Run the command a few times. It changes every time: that's the PLC's 10-times-a-second polling.

### Step 2.2: Summarise thousands of lines into a table

**Where:** 🖥 Host terminal

**Do:**

```
./tools/zeek-talkers.sh
```

**What's happening:** the log grows by thousands of lines a minute, which is too much to read.
This script takes every request in every hour's Modbus log, groups them by *from / to / function*,
and counts each group. (Open the script if you're curious: it's `docker exec`, `jq`, `sort` and `uniq -c`.)

**You should see** a table like this (your counts will be different):

```
REQUESTS  FROM (master)    TO (slave)       FUNCTION
    4726  192.168.95.2     192.168.95.15    WRITE_MULTIPLE_REGISTERS
    4726  192.168.95.2     192.168.95.15    READ_INPUT_REGISTERS
    4726  192.168.95.2     192.168.95.14    WRITE_MULTIPLE_REGISTERS
     ...  (the same pair of lines for .13, .12, .11 and .10)
     254  192.168.90.107   192.168.95.2     READ_INPUT_REGISTERS
     254  192.168.90.107   192.168.95.2     READ_HOLDING_REGISTERS
     254  192.168.90.107   192.168.95.2     READ_COILS
```

**How to read it:**

- The top block is the **PLC doing its job**: one read and one write to each of the six field
  devices, in equal numbers, all the time. Very regular traffic like this is normal in OT, and
  it's why anomaly detection works well here.
- The bottom block is a **DMZ machine reading the PLC**. Look it up in the plant table. Only
  READs: the operator is watching, not changing anything.
- **Anything not in the plant table** would be suspicious. Right now there shouldn't be any.
  After Mission 3 you'll see Kali (192.168.90.6) appear here.

### Step 2.3: Write an asset inventory

**Where:** any notepad, or a spreadsheet.

**Do:** one row per device you've seen in the table: **IP · what it is · protocol and port ·
talks to · reads, writes or both**.

**What's happening:** you've just built, passively, the **asset inventory**: the first deliverable
of every OT assessment and the foundation of IEC 62443 work. Many sites don't have an accurate one.

**Check yourself**

<details><summary>If you saw a WRITE from the HMI's address, would that be an attack?</summary>

Not necessarily. Writes from the HMI happen whenever an operator changes a setpoint. That's
exactly why they're a good hiding place for an attacker. You'd check it against the operator's
actions (shift log, HMI audit trail).
</details>

<details><summary>Why can't you see this traffic from Kali?</summary>

Kali is on a normal switched network: it only sees traffic addressed to it. Zeek is plugged into
a mirror that receives a copy of everything. That's the difference between a laptop on the
network and a sensor on a SPAN port.
</details>

### In the real world

A passive capture is the safest, highest-value thing you can do on a live site. Commercial OT
monitoring products (Nozomi, Claroty, Dragos) do exactly what you just did, at scale. Zeek is
the free version.

### Command Centre

Tick the objectives. **⚑** Answer: the IP that polls the field devices, the DMZ host that reads
the PLC, and the field devices' unit ID.

---

## Mission 3: Careful active scanning

⏱ 30 minutes

**What you'll learn**

- How to scan an OT network without breaking it.
- How to fingerprint an industrial device.
- What your scanning looks like to a defender.

### Background

Sometimes passive isn't enough: a device might never talk while you're listening. Then you scan
**actively**, but very differently from IT:

- **Written permission** from the asset owner, naming the exact targets and times.
- **Known targets only**: an agreed list of IPs, never a whole range "to see what's there".
- **Few ports**: just the industrial protocols you expect.
- **Slowly**: a delay between probes, one target at a time.
- **Full TCP connections**: half-open SYN scans leave connections dangling, which some old
  devices handle badly.
- Ideally against a **spare or test panel**, with an engineer standing by.

Common OT ports: **102** Siemens S7, **502** Modbus, **20000** DNP3, **44818** EtherNet/IP
(Allen-Bradley), and often **80/8080** for web interfaces.

### Step 3.1: Scan gently

**Where:** 🐉 Kali (open one with `./lab.sh kali` in a host terminal)

**Do:**

```
nmap -sT -Pn --scan-delay 500ms -p 102,502,20000,44818,8080 192.168.95.1-20
```

**What's happening:** you're now the attacker on the DMZ, probing the ICS network through the firewall.

- `-sT`: full TCP connect scan (complete handshakes, no half-open probes).
- `-Pn`: don't ping first; many OT devices ignore pings.
- `--scan-delay 500ms`: half a second between probes to each host.
- `-p ...`: only the five OT ports.
- `192.168.95.1-20`: only the 20 addresses where the plant's devices are.

**You should see** after about 10 seconds: port **502 open** (shown as `mbap`, the name of the
Modbus TCP header) on **.2** and **.10 to .15**, and **8080 open** on **.2** (the PLC's web page).

### Step 3.2: Ask the analyser what it is

**Where:** 🐉 Kali

**Do:**

```
nmap -sT -Pn -p 502 --script modbus-discover 192.168.95.15
```

**What's happening:** the `modbus-discover` script sends Modbus's own "who are you?" request
(*Read Device Identification*). Many real devices answer with their vendor, model and firmware
version, which is perfect for looking up known vulnerabilities.

**You should see** a few lines under `modbus-discover`. Look for **Device identification**: it
names the software running the analyser.

### Step 3.3: Find yourself in the sensor logs

**Where:** 🖥 Host terminal

**Do:**

```
./tools/zeek-talkers.sh
```

**You should see** new lines **from 192.168.90.6**: your Kali machine, talking Modbus to the
analyser. Now look at every connection Kali made, not just the Modbus ones:

```
docker exec zeek sh -c 'cat /usr/local/zeek/logs/conn.*log' | jq -r 'select(."id.orig_h"=="192.168.90.6") | [."id.resp_h", ."id.resp_p", .conn_state] | @tsv' | sort | uniq -c | sort -rn | head -20
```

**What's happening:** `conn.log` records every connection Zeek saw. This picks out the ones
Kali started and counts them by target, port and result. `conn_state` tells you how each one
ended: `SF` = normal finish, `REJ` = refused (port closed), `S0` = no answer at all.

**You should see** your scan as one line per address and port, mostly `REJ` (closed ports), with
real connections to port 502 on the devices that were open.

**Check yourself**

<details><summary>How obvious was your scan to a defender?</summary>

Very. A new IP that has never spoken Modbus suddenly touches 20 addresses on 5 ports. In OT,
where normal traffic is so regular, "a new talker" is one of the strongest signals there is.
</details>

### In the real world

You've already seen this lab's PLC crash from a dropped connection. Real incidents of scans
taking down PLCs are well documented. On a supplier's job you'd most likely scan a **panel in the
factory before it ships** (Mission 8), which is the safest moment to test anything.

### Command Centre

Tick the objectives. **⚑** Answer: what software the analyser identifies itself as.

---

## Mission 4: Read the analyser

⏱ 30 minutes

**What you'll learn**

- Why "no authentication" on Modbus is such a big deal.
- How OT values are stored as raw numbers and scaled to engineering units.
- How to read a whole plant's state from one PLC.

### Background

Field devices store values as raw 16-bit numbers from **0 to 65535**. Something has to turn
those into real units. For example, if a pressure sensor's range is 0-3200 kPa:

```
pressure = raw × 3200 ÷ 65535
raw 55295  →  55295 × 3200 ÷ 65535  =  2700 kPa
```

Percentages work the same way: 65535 = 100%.

### Step 4.1: Read the analyser directly

**Where:** 🐉 Kali

**Do:**

```
python3 ~/lab/read_analyser.py
```

**What's happening:** the script connects to the analyser (192.168.95.15, port 502, unit 247)
and reads its input registers once a second. No username, no password: Modbus doesn't have them.
It prints the raw values and the scaled percentages.

**You should see** one line a second, like:

```
14:02:11 raw [31995, 495, 33044]  ->  A  48.8%   B   0.8%   C  50.4%
```

Press **Ctrl+C** to stop. Then read the script: `cat ~/lab/read_analyser.py`. It's about 20 lines.
Find where it chooses which registers to read, and how many.

### Step 4.2: Read the whole plant from the PLC

**Where:** 🐉 Kali

**Do:**

```
python3 ~/lab/plc_status.py
```

**What's happening:** the PLC already holds a copy of every sensor value and every valve command,
because it needs them to run. So instead of polling six devices, an attacker can read **one**
device and get everything. The comment at the top of the script shows how OpenPLC lays out its
values as Modbus addresses. You'll use that table in Mission 5.

**You should see** one line every 2 seconds, like:

```
14:03:40 | pressure   2701 kPa (setpoint 2700) | level 61.2% | valves F1 52% F2 49% purge 38% product 44% | analyser A 48.8% B 0.8% C 50.4% | mode auto
```

### Step 4.3: Compare three views of the same plant

**Do:** put the HMI (browser), the Plant status tile (Command Centre) and `plc_status.py` (Kali)
side by side.

**You should see** the same pressure and valve positions in all three. You now see exactly
what the operator sees, from the attacker's laptop.

**Check yourself**

<details><summary>Reading data doesn't change anything. Why is it still a finding?</summary>

Three reasons. Process data can be commercially sensitive (recipes, production rates). It tells
an attacker exactly what to change and when. And in this plant, anything that can read port 502
can usually write to it too (Mission 5).
</details>

### In the real world

On a real analyser system, the readings often feed **emissions
reporting** (CEMS) or **product quality**. Tampered readings could mean false regulatory
reports or off-spec product, without any valve moving.

### Command Centre

Tick the objectives. **⚑** Answer: how many registers the analyser exposes, and the PLC's
pressure setpoint in kPa.

---

## Mission 5: Change the process

⏱ 45 minutes

**What you'll learn**

- Why writing to a field device usually fails, and why writing to the PLC doesn't.
- How to take control of a process away from the PLC's logic.
- How attackers find the right addresses: the PLC program.

### Background

The PLC runs its **scan cycle** every 100 ms: read all inputs, run the logic, **write all
outputs**. So any value the PLC writes gets written again 10 times a second. That shapes how
an attack has to work, as you'll see in step 5.1.

The program has a **manual mode**, a normal feature: during maintenance or start-up, an
operator takes over and sets each valve by hand. That's the feature an attacker abuses here.
This is typical of OT attacks: **they use the system's own legitimate functions**, not exploits.

> ⚠ This mission deliberately puts the simulated reactor in danger. Keep the Command Centre
> visible and run `back_to_auto.py` (step 5.2) when you've seen enough.

### Step 5.1: Write a valve directly

**Where:** 🐉 Kali

**Do:**

```
python3 ~/lab/write_valve.py
```

**What's happening:** the script tells the **purge valve's** I/O box (192.168.95.12) to open 100%,
then reads the value back as fast as it can for half a second, three times over.

**You should see:**

```
Attempt 1: wrote 65535 (100% open)
       0 ms  register = 65535  (100% open)
      51 ms  register =     0  (  0% open)
```

Your value lasted less than 100 ms. Why? Look back at Mission 2's table: the PLC writes to .12
ten times a second. It simply overwrote you. **Lesson: to change the process, attack the PLC,
not the valve.**

### Step 5.2: Take manual control of the PLC

**Do first:** open the **HMI** and the **Command Centre** side by side so you can watch.

**Where:** 🐉 Kali

**Do:**

```
python3 ~/lab/manual_takeover.py
```

**What's happening:** the script writes two things to the PLC (192.168.95.2), with no login:

1. Holding registers **10-13** (the four manual valve setpoints) = Feed 1 100%, Feed 2 100%,
   Purge 0%, Product 0%. Gas goes in; nothing comes out.
2. **Coil 0** (`manual_mode`) = ON. The PLC stops using its control loops and uses those setpoints.

Then it prints the pressure every 5 seconds.

**You should see:**

- In Kali: `PLC switched to MANUAL...` then a pressure line every 5 seconds, rising by about
  20-25 kPa each time.
- On the HMI: **MANUAL MODE: ON**, and the ManualSP boxes change to the attacker's values.
  Those small changes are the **only clue the operator gets** until the pressure gets high.
- On the Command Centre: the pressure bar climbs, and turns **red** above 3000 kPa (about 5 minutes).

**Undo it:** press **Ctrl+C** (that only stops the watching: the PLC stays in manual), then:

```
python3 ~/lab/back_to_auto.py
```

**You should see** `PLC back in AUTO`, the HMI says MANUAL MODE: OFF, and over the next few
minutes the pressure falls back to about 2700 kPa as the purge valve opens.

### Step 5.3: Where the addresses came from

**Background:** how did the script know that coil 0 means "manual mode"? It came from the **PLC
program**. OpenPLC programs are written in **Structured Text** (one of the IEC 61131-3 PLC
languages), and every variable is tied to a hardware address such as `%QX0.0`.

**Where:** 🖥 Host terminal

**Do:**

```
sed -n 109,165p ./GRFICSv3/plc/st_files/326339.st
```

**What's happening:** this prints the part of the PLC program that declares its variables. It's
the same file that's loaded on the PLC (PLC web page → **Programs**).

**You should see** lines like `manual_mode AT %QX0.0 : BOOL := FALSE;` and `pressure_sp AT %MW2 : UINT := 55295;`.
OpenPLC turns those into Modbus addresses like this:

| In the program | Modbus address | Here |
|---|---|---|
| `%QX0.0` | coil 0 | manual_mode |
| `%QW10` to `%QW13` | holding registers 10-13 | manual valve setpoints |
| `%MW2` | holding register 1024 + 2 = 1026 | pressure_sp (raw 55295 = 2700 kPa) |

**Check yourself**

<details><summary>What would an attacker do with write access to holding register 1026?</summary>

Change the pressure setpoint. The PLC would then hold the reactor at whatever pressure the
attacker chose, in **auto** mode, and the HMI wouldn't show "MANUAL". Far quieter than this
mission's attack.
</details>

<details><summary>Why are engineering workstations and project files called "crown jewels"?</summary>

They hold the PLC program, which is the map of what every address does. With it, an attacker
knows exactly what to write. Without it, they're guessing at a live plant.
</details>

### In the real world

This is the shape of real attacks on industrial sites: get onto the network, learn the process
from the engineering files, then use legitimate functions (mode changes, setpoint writes) to
cause harm. When you test a panel before it ships, the questions are: *can anyone on the network
change modes or setpoints, and would anyone notice?*

### Command Centre

Tick the objectives. **⚑** Answer: the PLC's polling interval in ms, the manual-mode coil
number, and the PLC's default password.

---

## Mission 6: Detect it

⏱ 45 minutes

**What you'll learn**

- What your attacks looked like to the sensors.
- Why simple threshold alerts misfire in OT, and what works better.
- How to hunt for an attacker who's already inside.

### Background

You now switch sides and become the plant's security analyst. You have two tools:

- **Zeek**: the network sensor from Mission 2. It writes logs, and **notices** when something
  matches a rule.
- **Wazuh**: a **SIEM** (Security Information and Event Management system) that collects
  alerts from Zeek and from the router's IDS (Suricata) into one searchable place. The
  Command Centre's **SOC feed** shows the newest ones.

### Step 6.1: Find your attack in the Modbus log

**Where:** 🖥 Host terminal

**Do:**

```
./tools/zeek-talkers.sh
```

**You should see** lines from **192.168.90.6** with `WRITE_SINGLE_COIL` and
`WRITE_MULTIPLE_REGISTERS` to 192.168.95.2. That's Mission 5. Compare them with the HMI's lines:
the HMI only ever reads.

**What this tells you:** a rule as simple as *"alert on any Modbus write to the PLC from
anything except the HMI"* would have caught you on your first packet.

### Step 6.2: See what the SIEM saw

**Where:** browser → Command Centre → **SOC feed** panel (it appears once you reach this mission).

For the full SIEM: Command Centre → Wazuh → **View**, log in **admin / admin**. Open the
menu (☰) → **Threat Hunting** → **Events**, and search:

```
rule.groups:zeek
```

**You should see** a list of alerts with times, levels and descriptions. You'll probably see lots
of **"Modbus write-rate anomaly"** alerts.

**What's happening:** that rule fires when Modbus writes go over a fixed number per minute. But
the PLC **legitimately** writes 60 times a second (6 devices × 10). So the rule fires on normal
operation: a **false positive**. Too many of those and the operators learn to ignore the alerts.
The rules are in `./GRFICSv3/wazuh/local_rules.xml` if you want to look.

**Do:** write **two detection rules in plain English** that would catch Mission 5 without ever
firing on normal operation.

<details><summary>Example answers</summary>

1. Any Modbus **write** to the PLC from an address other than the HMI.
2. The PLC's `manual_mode` coil changes, outside a planned maintenance window.

OT rules work best as **allow-lists of known-good behaviour**, because normal OT traffic is
so predictable.
</details>

### Step 6.3: The hunt

**Scenario:** before you arrived, one machine in this plant was compromised. It **calls home**
(beacons) every few seconds to an attacker's server. Your job: find **which host**, **where it
calls**, and **on what port**.

**Where:** 🖥 Host terminal

**Do:**

```
docker exec zeek sh -c 'cat /usr/local/zeek/logs/notice.*log' | jq -r '.msg' | sort | uniq -c
```

**What's happening:** `notice.log` is where Zeek writes the things its detection scripts flagged.
This prints each distinct message and how many times it appeared. Check the SOC feed too.

**Then think about it:** the firewall and the router's IDS (Suricata) never saw this traffic.
Look at the plant table: which zone are **both ends** in?

<details><summary>Why didn't the firewall see it?</summary>

Both ends are in the DMZ, so the traffic never crossed the router. It went straight across the
DMZ switch. Only a sensor on that switch's mirror (Zeek) could see it. That's why OT monitoring
needs sensors **inside** zones, not just at the boundary.
</details>

### In the real world

The compromised machine is one an operator looks at all day. Attackers who reach OT often
live on the HMI or EWS for weeks, because those machines are rarely patched or monitored.

### Command Centre

Tick the objectives. **⚑** Answer: the compromised host's IP and the port it calls home on.

---

## Mission 7: Defend it

⏱ 40 minutes

**What you'll learn**

- How to read and fix a firewall rule set between OT zones.
- How to make a change on a live plant without causing an outage.
- How to test a fix from both sides.

### Background

IEC 62443 (the main OT security standard family) divides a site into **zones** (groups of
systems with the same security needs) joined by **conduits** (the allowed communication paths
between them). The rule is **deny by default**: only traffic with a clear business reason crosses
a zone boundary.

What does this plant **need** to cross from the DMZ into the ICS network? From Mission 2: only
**the HMI reading the PLC over Modbus**. Nothing else.

And the OT priority again: **availability first**. If your firewall change stops the HMI seeing
the plant, the operators are blind, and that's an incident you caused.

### Step 7.1: Look at the firewall

The firewall's admin page is only reachable from inside the lab, so you use the browser
on the Kali desktop.

1. Command Centre → Kali → **View**. Kali's desktop appears in the workspace. Password **kali**
   if asked.
2. Open **Firefox** inside that desktop (in the taskbar or the applications menu).
3. Go to **http://192.168.90.200:5000** and log in **admin / password**. (Another default-style
   password: note it as a finding.)
4. Click **Firewall** in the menu.

**You should see** one rule: **Allow · any → any**, with the comment *"TEMP - allow all traffic
for troubleshooting - DO NOT LEAVE IN PRODUCTION"*.

**What it means:** someone opened the firewall completely for troubleshooting and never closed it.
Every DMZ machine, including Kali, can reach every PLC and valve. This is one of the most common
real findings in OT.

### Step 7.2: Fix it

Order matters. **Add the allow rule first**, then remove the allow-all. If you did it the other
way round, the HMI would lose its connection in between.

1. Click **➕ Add Rule** and fill in the form:
   - Protocol **tcp**
   - Source **192.168.90.107** (the HMI)
   - Destination **192.168.95.2** (the PLC)
   - Destination Port **502** (Modbus)
   - Action **Allow**
   - Comment *HMI to PLC Modbus*

   Click **Apply Rule**. It's added as a **pending** change. Nothing has happened yet.
2. On the TEMP allow-all row, click **Actions** → **🗑️ Delete**. Also pending.
3. Click **💾 Apply Changes** at the top. Both changes take effect together.

**What's happening:** the router already drops anything that isn't allowed, so you don't need a
"block everything" rule. Your one allow rule is the conduit between the two zones.

### Step 7.3: Test both sides

**Test 1, the attack is blocked.** **Where:** 🐉 Kali

```
python3 ~/lab/read_analyser.py
```

**You should see:** `Can't reach the analyser at 192.168.95.15:502 (blocked by the firewall?)`.

**Test 2, the plant still works.** **Where:** browser.

- HMI: are the values still changing every few seconds?
- Command Centre Plant status: all green, PLC running, pressure near 2700 kPa?

If both are yes, you've segmented a live plant **without an outage**. That's the skill.

> ⚠ Don't restart the router while the plant is running. A restart drops the HMI's connection,
> and this PLC has crashed from exactly that. If the PLC tile turns red, press **Restart PLC**. To put
> the firewall back to its insecure starting point for another go, use **Reset entire lab**.

**Check yourself**

<details><summary>Kali is blocked now. Is the plant secure?</summary>

No. The HMI can still reach the PLC, and the HMI is the compromised machine from Mission 6.
An attacker on the HMI can do everything you did in Mission 5. Segmentation reduces who can
reach the PLC; it doesn't fix a compromised machine that's allowed through.
</details>

### In the real world

Firewall rule reviews are one of the most valuable services in OT and one of the simplest. On
a supplier's panel, the equivalent is checking that the panel's own firewall or switch only allows the
connections listed in its design documents before it leaves the factory.

### Command Centre

Tick the objectives. **⚑** Answer: the port the HMI needs on the PLC.

---

## Mission 8: Write it up (FAT report)

⏱ 60 minutes

**What you'll learn**

- What a Factory Acceptance Test is and where security fits in it.
- How IEC 62443-3-3 is organised.
- How to turn technical findings into a report a customer can act on.

### Background

**FAT (Factory Acceptance Test):** before an analyser system or control panel ships, the
customer comes to the factory and watches it being tested against the specification. Then
there's a **SAT** (Site Acceptance Test) after installation. Customers in regulated industries
(oil and gas, water, power) increasingly want **security** tests in the FAT. That's usually what
"security testing" means in a supplier's contract.

**IEC 62443** is the family of OT security standards. The parts that matter for a supplier that builds panels or analyser systems:

| Part | What it covers | Who it's aimed at |
|---|---|---|
| **62443-2-4** | Security requirements for **service providers** (integrators) | The supplier as a company |
| **62443-3-3** | Security requirements for a **system** | The panels and systems the supplier delivers |
| **62443-4-2** | Security requirements for **components** (a PLC, an analyser) | The vendors the supplier buys from |

62443-3-3 is organised into 7 **foundational requirements (FRs)**, each broken into numbered
**system requirements (SRs)**:

| FR | Name | Example SR |
|---|---|---|
| 1 | Identification and authentication control | SR 1.1 Human user identification and authentication |
| 2 | Use control | SR 2.1 Authorisation enforcement |
| 3 | System integrity | SR 3.1 Communication integrity |
| 4 | Data confidentiality | SR 4.1 Information confidentiality |
| 5 | Restricted data flow | SR 5.1 Network segmentation |
| 6 | Timely response to events | SR 6.1 Audit log accessibility |
| 7 | Resource availability | SR 7.6 Network and security configuration settings |

Each system is given a target **Security Level (SL 1-4)**: SL1 protects against accidents and
SL4 against nation states. Most customer specs ask for SL1 or SL2.

### Step 8.1: Set the scene

**Do:** at the top of your report, write two or three sentences: what was tested (treat the
PLC plus analyser as an **analyser panel** about to ship), when, by whom, and how (passive
capture, then targeted active tests from the DMZ).

### Step 8.2: List the findings

**Do:** go back through your notes from every mission and list each finding in one line. You
should have at least: default PLC password, default firewall password, unauthenticated Modbus
reads, unauthenticated Modbus writes, network mode change, allow-all firewall rule, the
compromised HMI, and the 9 physical issues from the 3D walkthrough.

### Step 8.3: Map them to 62443-3-3 and recommend a fix

**Do:** turn the list into a test table. Here's a start; complete and correct it:

| Test | Result | IEC 62443-3-3 SR | Recommendation |
|---|---|---|---|
| Default credentials on PLC web interface (openplc/openplc) | Fail | SR 1.1, SR 1.5 (identification, authenticator management) | Unique password set at commissioning, recorded in handover pack |
| Unauthenticated Modbus reads and writes to the PLC | Fail | SR 1.1, SR 3.1 (communication integrity) | Restrict by firewall; consider a protocol with authentication (e.g. OPC UA) |
| PLC can be switched to manual over the network | Fail | SR 2.1 (authorisation enforcement) | Physical key switch or authenticated mode change |
| Field devices reachable from the DMZ | Fail → Pass after Mission 7 | SR 5.1, SR 5.2 (network segmentation, zone boundary protection) | Zone/conduit design with a deny-by-default boundary |
| Modbus writes logged and alerted | Pass | SR 2.8 (auditable events) | Tune thresholds to the plant's normal polling |
| Temporary "allow all" firewall rule left in place | Fail | SR 5.2, SR 7.6 (network and security configuration settings) | Change control; review rules at handover |

**Tips for writing it:**

- Write each recommendation so the panel builder can act on it **before shipping**.
- Rate each finding by what it could do to the **process**, not by a CVSS score.
- Keep it to one page. A customer's engineer should understand it without a security background.

### In the real world

That page is a sample of exactly what a supplier hands its customer at a FAT. If you work with
one, ask what their customers' specifications actually say. They'll usually quote
62443 parts and a target security level.

### Command Centre

Tick the three objectives. That's the course. 🎉

---

## Where next

- **CISA ICS300** (free, which you're doing): goes deeper on everything in Missions 1-7.
- **IEC 62443 overview**: ISA's free "Quick Start Guide" to the standard.
- **Do it again harder**: reset the lab and try Mission 5 using only the setpoint register
  (1026) instead of manual mode, then see if your Mission 6 rules would catch it.

---

## Cheat sheet

| What | Where | Command |
|---|---|---|
| Start / stop the lab | 🖥 Host | `./lab.sh start` / `stop` |
| Open a Kali terminal | 🖥 Host | `./lab.sh kali` |
| Who talks Modbus to whom | 🖥 Host | `./tools/zeek-talkers.sh` |
| List Zeek's log files | 🖥 Host | `docker exec zeek ls /usr/local/zeek/logs` (a new file every hour) |
| Live plant view | 🐉 Kali | `python3 ~/lab/plc_status.py` |
| Undo the manual takeover | 🐉 Kali | `python3 ~/lab/back_to_auto.py` |
| Release E-stop | 🖥 Host | Command Centre button, or `lab.sh estop-release` |
| Restart one system | 🖥 Host | Command Centre button, or `lab.sh restart plc` (names: simulation, plc, ews, hmi, router, kali, caldera, wazuh, zeek) |
| Back to factory defaults | 🖥 Host | Command Centre Danger zone, or `lab.sh reset` |
| Command Centre won't load | 🖥 Host | Check `./command-centre/server.log`, then `lab.sh stop` and `lab.sh start` |
