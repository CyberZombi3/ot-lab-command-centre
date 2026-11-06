#!/usr/bin/env python3
"""OT Lab Command Centre: a small local web server that shows lab status and
runs lab.sh actions. Listens on 127.0.0.1 only. Standard library only."""

import http.client
import json
import os
import select
import socket
import subprocess
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PORT = 4900
HERE = Path(__file__).resolve().parent
LAB = HERE.parent
LAB_SH = LAB / "lab.sh"
COMPOSE_DIR = Path(os.environ.get("GRFICS_DIR", LAB / "GRFICSv3"))
PROGRESS = HERE / "progress.json"
os.environ["PATH"] = "/opt/homebrew/bin:/usr/local/bin:" + os.environ.get("PATH", "")

SERVICES = ["simulation", "plc", "ews", "hmi", "router", "kali", "caldera", "wazuh", "zeek"]
ACTIONS = {"up", "down", "mirror", "reset", "restart", "estop-release"}

job = {"name": None, "running": False, "ok": None, "log": [], "started": 0, "finished": 0}
job_lock = threading.Lock()
status_cache = {"t": 0, "data": None}


def run(cmd, timeout=20):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=COMPOSE_DIR)
        return p.returncode, p.stdout
    except Exception as e:  # docker not running, timeout, etc.
        return 1, str(e)


def get_status():
    # Cache briefly: the page polls every few seconds
    if time.time() - status_cache["t"] < 2 and status_cache["data"]:
        return status_cache["data"]
    # Is Docker reachable? (Colima, Docker Desktop or native Linux)
    vm_up = run(["docker", "info", "--format", "{{.ServerVersion}}"], 10)[0] == 0
    containers = {}
    mirror = False
    if vm_up:
        rc, out = run(["docker", "compose", "--profile", "siem", "ps", "-a", "--format", "json"])
        if rc == 0:
            for line in out.splitlines():
                try:
                    c = json.loads(line)
                except json.JSONDecodeError:
                    continue
                containers[c["Service"]] = {
                    "state": c.get("State"),
                    "health": c.get("Health") or "",
                    "status": c.get("Status"),
                }
        if containers.get("zeek", {}).get("state") == "running":
            mirror = run(["docker", "exec", "zeek", "ip", "link", "show", "mirror0"], 10)[0] == 0
    data = {"vm": vm_up, "containers": containers, "mirror": mirror}
    status_cache.update(t=time.time(), data=data)
    return data


def get_plant():
    """Plant state straight from the physics simulator's web endpoint, plus whether
    the PLC's control program is running. Generates no Modbus traffic, so it never
    shows up in the Zeek logs you're analysing."""
    out = {"ok": False}
    try:
        with urllib.request.urlopen("http://127.0.0.1/data/index.php", timeout=3) as r:
            d = json.loads(r.read())
        s, m = d["state"], d["measured"]
        out = {
            "ok": True,
            "e_stop": bool(s.get("e_stop")),
            "pressure": round(m["pressure"]),
            "level": round(m["liquid_level"], 1),
            "valves": {k: round(s[f"{k}_valve_pos"]) for k in ("f1", "f2", "purge", "product")},
            "analyser": [round(m[f"{x}_in_purge"] * 100, 1) for x in "ABC"],
            "faults": any(v for k, v in s.items()
                          if (k.endswith("_stuck") and v) or (k.endswith("_fault_mode") and v)),
        }
    except Exception:
        pass
    # OpenPLC's control program listens on Modbus 502 only while it's running
    rc, tcp = run(["docker", "exec", "plc", "cat", "/proc/net/tcp"], 10)
    out["plc_running"] = rc == 0 and any(
        f[1].endswith(":01F6") and f[3] == "0A" for f in (l.split() for l in tcp.splitlines()[1:]) if len(f) > 3)
    return out


def get_alerts():
    """Recent IDS / network-sensor alerts from Wazuh (reads its log file, no network traffic)."""
    rc, out = run(["docker", "exec", "wazuh", "tail", "-n", "4000",
                   "/var/ossec/logs/alerts/alerts.json"], 15)
    if rc != 0:
        return []
    alerts = []
    for line in out.splitlines():
        try:
            a = json.loads(line)
        except json.JSONDecodeError:
            continue
        rule = a.get("rule", {})
        groups = rule.get("groups", [])
        if not any(g in groups for g in ("zeek", "suricata", "ids", "ics")):
            continue
        alerts.append({"ts": a.get("timestamp", "")[:19].replace("T", " "),
                       "level": rule.get("level", 0),
                       "desc": rule.get("description", ""),
                       "agent": a.get("agent", {}).get("name", "")})
    return alerts[-40:][::-1]


def start_job(action, service=None):
    with job_lock:
        if job["running"]:
            return False
        args = [str(LAB_SH), action] + ([service] if service else [])
        job.update(name=" ".join(args[1:]), running=True, ok=None, log=[], started=time.time())

    def worker():
        try:
            p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            for line in p.stdout:
                job["log"] = (job["log"] + [line.rstrip()])[-60:]
            ok = p.wait() == 0
        except Exception as e:
            job["log"].append(str(e))
            ok = False
        status_cache["t"] = 0
        job.update(running=False, ok=ok, finished=time.time())

    threading.Thread(target=worker, daemon=True).start()
    return True


# The HMI and Wazuh send "X-Frame-Options: SAMEORIGIN", which stops them showing inside
# the Command Centre's workspace. These relays pass everything through unchanged except
# that header, so they can be embedded. Local only, like the rest of this server.
FRAME_PROXIES = {4981: 6081, 4951: 5601}
HOP = {"connection", "keep-alive", "transfer-encoding", "te", "trailer", "upgrade",
       "proxy-authorization", "proxy-authenticate", "content-length"}


def make_proxy(listen, target):
    class Proxy(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *a):
            pass

        def _fix(self, value):
            # Point the backend's own address back at the relay
            return value.replace(f"localhost:{target}", f"localhost:{listen}").replace(
                f"127.0.0.1:{target}", f"localhost:{listen}")

        def _tunnel(self):
            # WebSocket upgrade: replay the request, then pipe bytes both ways
            up = socket.create_connection(("127.0.0.1", target), timeout=10)
            lines = [f"{self.command} {self.path} HTTP/1.1"]
            for k, v in self.headers.items():
                if k.lower() == "host":
                    v = f"localhost:{target}"
                elif k.lower() == "origin":
                    v = f"http://localhost:{target}"
                lines.append(f"{k}: {v}")
            up.sendall(("\r\n".join(lines) + "\r\n\r\n").encode())
            down = self.connection
            up.settimeout(None)
            down.settimeout(None)
            try:
                while True:
                    r, _, _ = select.select([up, down], [], [], 300)
                    if not r:
                        break
                    for src in r:
                        data = src.recv(65536)
                        if not data:
                            return
                        (down if src is up else up).sendall(data)
            finally:
                up.close()
                self.close_connection = True

        def _relay(self):
            if (self.headers.get("Host") or "").split(":")[0] not in ("localhost", "127.0.0.1"):
                self.send_error(403)
                return
            if "websocket" in (self.headers.get("Upgrade") or "").lower():
                return self._tunnel()
            length = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(length) if length else None
            headers = {}
            for k, v in self.headers.items():
                kl = k.lower()
                if kl in HOP:
                    continue
                if kl == "host":
                    v = f"localhost:{target}"
                elif kl in ("origin", "referer"):
                    v = v.replace(f"localhost:{listen}", f"localhost:{target}")
                headers[k] = v
            try:
                conn = http.client.HTTPConnection("127.0.0.1", target, timeout=60)
                conn.request(self.command, self.path, body=body, headers=headers)
                resp = conn.getresponse()
                data = resp.read()
            except Exception:
                self.send_error(502, "System not reachable (is the lab up?)")
                return
            self.send_response(resp.status, resp.reason)
            for k, v in resp.getheaders():
                kl = k.lower()
                if kl in HOP or kl == "x-frame-options":
                    continue
                if kl == "content-security-policy":
                    v = ";".join(d for d in v.split(";") if "frame-ancestors" not in d)
                if kl == "location":
                    v = self._fix(v)
                self.send_header(k, v)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(data)
            conn.close()

        do_GET = do_POST = do_PUT = do_DELETE = do_PATCH = do_HEAD = do_OPTIONS = _relay

    return Proxy


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _safe_origin(self):
        # Block DNS-rebinding and other websites poking the API
        host = (self.headers.get("Host") or "").split(":")[0]
        return host in ("localhost", "127.0.0.1")

    def _send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if not self._safe_origin():
            return self._send(403, {"error": "forbidden"})
        if self.path in ("/", "/index.html"):
            return self._send(200, (HERE / "index.html").read_bytes(), "text/html; charset=utf-8")
        if self.path.split("#")[0] == "/guide":
            return self._send(200, (HERE / "guide.html").read_bytes(), "text/html; charset=utf-8")
        if self.path == "/EXERCISES.md":
            return self._send(200, (LAB / "EXERCISES.md").read_bytes(), "text/markdown; charset=utf-8")
        if self.path == "/api/status":
            return self._send(200, {**get_status(), "job": job})
        if self.path == "/api/plant":
            return self._send(200, get_plant())
        if self.path == "/api/alerts":
            return self._send(200, get_alerts())
        if self.path == "/api/progress":
            p = json.loads(PROGRESS.read_text()) if PROGRESS.exists() else {}
            return self._send(200, p)
        self._send(404, {"error": "not found"})

    def do_POST(self):
        # The custom header forces a CORS preflight, which we never approve,
        # so other websites can't trigger actions from your browser.
        if not self._safe_origin() or self.headers.get("X-Lab") != "1":
            return self._send(403, {"error": "forbidden"})
        length = int(self.headers.get("Content-Length") or 0)
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            return self._send(400, {"error": "bad json"})
        if self.path == "/api/progress":
            # Whenever progress goes down (a reset, or an unticked box), keep the version
            # before it in progress.prev.json, so a reset can be undone
            done = lambda p: sum(bool(v) for k in ("obj", "flags") for v in (p.get(k) or {}).values())
            if PROGRESS.exists():
                old = json.loads(PROGRESS.read_text() or "{}")
                if done(body) < done(old):
                    (HERE / "progress.prev.json").write_text(json.dumps(old))
            PROGRESS.write_text(json.dumps(body))
            return self._send(200, {"ok": True})
        if self.path == "/api/action":
            action, service = body.get("action"), body.get("service")
            if action not in ACTIONS or (action == "restart" and service not in SERVICES):
                return self._send(400, {"error": "unknown action"})
            if not start_job(action, service if action == "restart" else None):
                return self._send(409, {"error": "another action is running"})
            return self._send(200, {"ok": True})
        self._send(404, {"error": "not found"})


if __name__ == "__main__":
    print(f"Command Centre on http://localhost:{PORT}")
    for listen, target in FRAME_PROXIES.items():
        srv = ThreadingHTTPServer(("127.0.0.1", listen), make_proxy(listen, target))
        srv.daemon_threads = True
        threading.Thread(target=srv.serve_forever, daemon=True).start()
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
