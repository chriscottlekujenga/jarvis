#!/bin/bash

cd /home/chris/jarvis || exit

echo "Killing existing bridge processes..."
pkill -f "chatgpt_to_daemon.py" 2>/dev/null
pkill -f "bridge_daemon.py" 2>/dev/null
pkill -f "daemon_to_chatgpt.py" 2>/dev/null

sleep 1

echo "Starting bridge_daemon..."
nohup python bridge/bridge_daemon.py > bridge_daemon.log 2>&1 &

echo "Starting chatgpt_to_daemon..."
nohup python bridge/chatgpt_to_daemon.py > chatgpt_to_daemon.log 2>&1 &

echo "Starting daemon_to_chatgpt..."
nohup python bridge/daemon_to_chatgpt.py > daemon_to_chatgpt.log 2>&1 &

echo "All bridge processes started"
