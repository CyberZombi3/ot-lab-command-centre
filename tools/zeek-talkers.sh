#!/bin/bash
# Who is talking Modbus to whom, and what are they doing?
# Run on the host:  ./tools/zeek-talkers.sh  (from the project folder)
# Reads the Zeek sensor's modbus.log (Zeek watches a mirrored copy of all lab traffic).
set -euo pipefail
export PATH="/opt/homebrew/bin:$PATH"

# Zeek starts a new file every hour (modbus.<date>.log), so read them all
docker exec zeek sh -c 'cat /usr/local/zeek/logs/modbus.*log' |
  jq -r 'select(.pdu_type=="REQ") | [."id.orig_h", ."id.resp_h", .func] | @tsv' |
  sort | uniq -c | sort -rn |
  awk 'BEGIN{printf "%8s  %-16s %-16s %s\n","REQUESTS","FROM (master)","TO (slave)","FUNCTION"}
       {printf "%8s  %-16s %-16s %s\n",$1,$2,$3,$4}'
