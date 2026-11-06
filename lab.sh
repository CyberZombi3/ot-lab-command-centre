#!/bin/bash
# OT lab helper
#   ./lab.sh setup            first time only: download GRFICSv3 and its images
#   ./lab.sh start            start everything and open the Command Centre
#   ./lab.sh stop             stop everything (frees the lab's RAM)
#   ./lab.sh status           show containers and addresses
#   ./lab.sh reset            wipe the lab back to defaults and start it
#   ./lab.sh restart <name>   restart one system (plc, hmi, zeek, ...)
#   ./lab.sh kali             open a terminal inside Kali
#   ./lab.sh estop-release    release the plant's emergency stop
#   ./lab.sh up | down | mirror   used by the Command Centre buttons
set -euo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
LAB="$(cd "$(dirname "$0")" && pwd)"
GRFICS_DIR="${GRFICS_DIR:-$LAB/GRFICSv3}"
GRFICS_REPO="https://github.com/Fortiphyd/GRFICSv3.git"
GRFICS_COMMIT="8d611b773fa74e3a82ff149c447cff8380eaa99a"   # the version this course was written against
CC_URL="http://localhost:4900"
CC_PID="$LAB/command-centre/server.pid"

# How Docker runs on this machine:
#   colima   macOS with Colima (recommended on a Mac; what this was built on)
#   linux    Docker installed directly on Linux
#   desktop  Docker Desktop (works, but Zeek's traffic mirror can't be set up)
if [ -n "${LAB_RUNTIME:-}" ]; then RUNTIME="$LAB_RUNTIME"
elif [ "$(uname)" = Darwin ] && command -v colima >/dev/null; then RUNTIME=colima
elif [ "$(uname)" = Linux ] && ! docker info 2>/dev/null | grep -q 'Docker Desktop'; then RUNTIME=linux
else RUNTIME=desktop; fi

compose() { (cd "$GRFICS_DIR" && docker compose --profile siem "$@"); }

need_grfics() {
  if [ ! -f "$GRFICS_DIR/docker-compose.yml" ]; then
    echo "GRFICSv3 isn't downloaded yet. Run: ./lab.sh setup" >&2
    exit 1
  fi
}

as_root() {
  # Zeek's mirror needs root on the Docker host
  case "$RUNTIME" in
    colima) colima ssh -- sudo bash "$@" ;;
    linux)  sudo -n bash "$@" ;;
    *)      return 1 ;;
  esac
}

centre_start() {
  if [ -f "$CC_PID" ] && kill -0 "$(cat "$CC_PID")" 2>/dev/null; then return; fi
  nohup python3 "$LAB/command-centre/server.py" >"$LAB/command-centre/server.log" 2>&1 &
  echo $! >"$CC_PID"
  sleep 1
}

centre_stop() {
  if [ -f "$CC_PID" ]; then kill "$(cat "$CC_PID")" 2>/dev/null || true; rm -f "$CC_PID"; fi
}

open_url() {
  if command -v open >/dev/null; then open "$1"
  elif command -v xdg-open >/dev/null; then xdg-open "$1" >/dev/null 2>&1 || true
  else echo "Open $1 in your browser"; fi
}

wait_healthy() {
  echo "Waiting for systems to report healthy..."
  for _ in $(seq 1 60); do
    compose ps --format '{{.Status}}' | grep -q starting || return 0
    sleep 5
  done
}

mirror_off() { as_root "$GRFICS_DIR/zeek/disable-mirror.sh" >/dev/null 2>&1 || true; }

mirror_on() {
  # Zeek's traffic mirror doesn't survive container restarts, so rebuild it
  if [ "$RUNTIME" = desktop ]; then
    echo "Note: Docker Desktop can't mirror traffic to Zeek. Everything else works; the Zeek steps won't show data."
    return 0
  fi
  mirror_off
  if ! as_root "$GRFICS_DIR/zeek/enable-mirror.sh"; then
    echo "Couldn't turn on Zeek's mirror. On Linux run this once, then try again:"
    echo "  sudo bash $GRFICS_DIR/zeek/enable-mirror.sh"
  fi
}

kali_tools() {
  # Copy the ready-made scripts into Kali (~/lab), so they survive a reset
  docker exec kali mkdir -p /home/kali/lab
  docker cp "$LAB/kali-tools/." kali:/home/kali/lab/ >/dev/null
  docker exec kali chown -R kali:kali /home/kali/lab
}

docker_up() {
  if [ "$RUNTIME" = colima ]; then
    # CPU/RAM only apply when Colima creates its VM for the first time
    colima status >/dev/null 2>&1 || colima start --cpu "${LAB_CPUS:-6}" --memory "${LAB_MEM_GB:-16}"
  fi
  docker info >/dev/null 2>&1 || { echo "Docker isn't running. Start it and try again." >&2; exit 1; }
}

setup() {
  if [ ! -d "$GRFICS_DIR/.git" ]; then
    git clone "$GRFICS_REPO" "$GRFICS_DIR"
    git -C "$GRFICS_DIR" checkout -q "$GRFICS_COMMIT" || echo "Pinned version not found; using the latest GRFICSv3."
  fi
  docker_up
  compose pull
  echo
  echo "Setup done ($RUNTIME). Start the lab with: ./lab.sh start"
}

up() {
  need_grfics
  docker_up
  compose up -d --no-build
  wait_healthy
  mirror_on
  kali_tools
  echo "Lab is up."
}

down() {
  need_grfics
  mirror_off
  compose stop
  [ "$RUNTIME" = colima ] && colima stop
  echo "Lab is powered down."
}

case "${1:-status}" in
  setup) setup ;;
  start)
    need_grfics
    centre_start
    open_url "$CC_URL"
    up
    ;;
  stop)
    down
    centre_stop
    ;;
  up) up ;;
  down) down ;;
  mirror) mirror_on ;;
  kali)
    # Open a terminal inside the Kali attacker machine (type exit to leave)
    exec docker exec -it -u kali -w /home/kali kali bash
    ;;
  estop-release)
    # The red E-stop button in the 3D plant (pressed with E) freezes every valve
    curl -s -X POST -H 'Content-Type: application/json' -d '{"e_stop":0}' http://localhost/data/index.php >/dev/null
    echo "E-stop released. The PLC is back in control of the valves."
    ;;
  restart)
    svc="${2:?usage: lab.sh restart <service>}"
    compose restart "$svc"
    wait_healthy
    if [ "$svc" = zeek ]; then mirror_on; fi
    if [ "$svc" = kali ]; then kali_tools; fi
    echo "$svc restarted."
    ;;
  reset)
    # Wipes PLC programs, HMI config and firewall rules back to defaults
    need_grfics
    mirror_off
    compose down --volumes
    up
    ;;
  status)
    need_grfics
    compose ps --format '{{.Name}}\t{{.Status}}'
    echo
    echo "Docker: $RUNTIME    Command Centre: $CC_URL"
    ;;
  *) sed -n 2,11p "$LAB/lab.sh"; exit 1 ;;
esac
