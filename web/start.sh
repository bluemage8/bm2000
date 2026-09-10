#!/bin/bash
# Bridge Master 2000 (web) -- nohup launcher.  Binds 0.0.0.0:<port>.
cd "$(dirname "$0")"
PORT="${1:-8321}"
export BM2000_HOST=0.0.0.0
export BM2000_PORT="$PORT"
nohup python3 server.py "$PORT" >> server.out 2>> server.err &
echo "started BM2000 web on 0.0.0.0:$PORT  pid=$!"

