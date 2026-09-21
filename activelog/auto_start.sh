#!/bin/bash

# Wait for network
sleep 30

# Log startup
echo "$(date): Auto-starting ActiveLog after power outage" >> ~/activelog/logs/autostart.log

# Start Docker
sudo systemctl start docker
sleep 10

# Start ActiveLog services
cd ~/activelog
docker-compose up -d
sleep 10

# Start main services
~/activelog/start_activelog.sh

# Start improvement bots if they were running
if [ -f ~/activelog/pids/improve_backend.pid ]; then
    ~/activelog/improvement_bot_v2.sh backend
fi

echo "$(date): ActiveLog started successfully" >> ~/activelog/logs/autostart.log
