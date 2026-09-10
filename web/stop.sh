#!/bin/bash
cd "$(dirname "$0")"
pids=$(pgrep -f "server.py 8321" 2>/dev/null)
if [ -n "$pids" ]; then kill $pids && echo "stopped pids: $pids"; else echo "no server.py 8321 process"; fi

