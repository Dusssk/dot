#!/bin/bash

# For a running process:
pid=$(pidof $1)

if [[ ! $# -eq 1 ]]; then
  echo "Usage: process.sh 'running process name'"
  exit 1
fi

echo ""
echo "=== Process Tree ==="
pstree -p $pid

echo ""
echo "=== Memory and Libraries ==="
cat /proc/$pid/maps | head -30

echo ""
echo "=== Open Files ==="
ls -la /proc/$pid/fd/

echo ""
echo "=== Network Connections ==="
ss -anp | grep $pid
