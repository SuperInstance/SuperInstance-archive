#!/bin/bash

# Create checkpoint directory
mkdir -p ~/activelog/checkpoints
mkdir -p ~/activelog/logs

# Function to create checkpoint
create_checkpoint() {
    local name=${1:-"auto_$(date +%Y%m%d_%H%M%S)"}
    echo "Creating checkpoint: $name"
    
    cd ~
    tar -czf ~/activelog/checkpoints/${name}.tar.gz \
        --exclude='node_modules' \
        --exclude='__pycache__' \
        --exclude='*.log' \
        activelog/
    
    echo "$(date): Checkpoint created: $name" >> ~/activelog/logs/checkpoints.log
}

# Function to run improvement loop
run_improvements() {
    echo "Starting improvement bot for: $1"
    
    while true; do
        # Create hourly checkpoint
        create_checkpoint "hourly_$(date +%Y%m%d_%H)"
        
        # Log activity
        echo "$(date): Improvement cycle for $1" >> ~/activelog/logs/improvements.log
        
        # TODO: Add actual Claude API calls here
        
        # Sleep for 1 hour
        sleep 3600
    done
}

case "$1" in
    backend)
        run_improvements "backend" &
        echo $! > ~/activelog/pids/improve_backend.pid
        echo "Backend improvement bot started (PID: $!)"
        ;;
    frontend)
        run_improvements "frontend" &
        echo $! > ~/activelog/pids/improve_frontend.pid
        echo "Frontend improvement bot started (PID: $!)"
        ;;
    stop)
        if [ -f ~/activelog/pids/improve_backend.pid ]; then
            kill $(cat ~/activelog/pids/improve_backend.pid)
            rm ~/activelog/pids/improve_backend.pid
        fi
        if [ -f ~/activelog/pids/improve_frontend.pid ]; then
            kill $(cat ~/activelog/pids/improve_frontend.pid)
            rm ~/activelog/pids/improve_frontend.pid
        fi
        echo "Improvement bots stopped"
        ;;
    status)
        echo "Improvement bot status:"
        if [ -f ~/activelog/pids/improve_backend.pid ]; then
            pid=$(cat ~/activelog/pids/improve_backend.pid)
            if ps -p $pid > /dev/null; then
                echo "  Backend bot: Running (PID: $pid)"
            else
                echo "  Backend bot: Stopped"
            fi
        else
            echo "  Backend bot: Not started"
        fi
        
        if [ -f ~/activelog/pids/improve_frontend.pid ]; then
            pid=$(cat ~/activelog/pids/improve_frontend.pid)
            if ps -p $pid > /dev/null; then
                echo "  Frontend bot: Running (PID: $pid)"
            else
                echo "  Frontend bot: Stopped"
            fi
        else
            echo "  Frontend bot: Not started"
        fi
        ;;
    *)
        echo "Usage: $0 {backend|frontend|stop|status}"
        ;;
esac
