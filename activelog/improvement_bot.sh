#!/bin/bash

# Configuration
CHECKPOINT_DIR="~/activelog/checkpoints"
IMPROVEMENT_LOG="~/activelog/improvements.log"
MAX_CHECKPOINTS=10

# Functions
create_checkpoint() {
    local name=${1:-"auto_$(date +%Y%m%d_%H%M%S)"}
    echo "Creating lightweight git checkpoint: $name"
    
    cd ~/activelog || exit 1
    
    # Create git commit instead of copying files
    git add -A
    git commit -m "Checkpoint: $name" || {
        echo "No changes to commit for checkpoint: $name"
        return 0
    }
    
    # Tag the commit for easy reference
    git tag "checkpoint-$name" || echo "Warning: Could not create tag"
    
    # Clean up old checkpoints directory if it exists
    if [ -d "$CHECKPOINT_DIR" ]; then
        echo "Cleaning up old checkpoint directories to save space..."
        rm -rf "$CHECKPOINT_DIR"
        mkdir -p "$CHECKPOINT_DIR"
        echo "Old checkpoints cleaned" > "$CHECKPOINT_DIR/migration_notice.txt"
    fi
    
    echo "Git checkpoint created: $name (commit: $(git rev-parse --short HEAD))" >> "$IMPROVEMENT_LOG"
}

rollback_checkpoint() {
    local name=$1
    echo "Rolling back to git checkpoint: $name"
    
    cd ~/activelog || exit 1
    
    # Check if tag exists
    if git tag -l "checkpoint-$name" | grep -q "checkpoint-$name"; then
        # Create a backup branch of current state
        local backup_branch="backup-before-rollback-$(date +%Y%m%d_%H%M%S)"
        git branch "$backup_branch" 2>/dev/null || true
        
        # Reset to the checkpoint tag
        git reset --hard "checkpoint-$name"
        echo "Rolled back to git checkpoint: $name" >> "$IMPROVEMENT_LOG"
        echo "Created backup branch: $backup_branch for current state"
    else
        echo "Error: Checkpoint tag 'checkpoint-$name' not found"
        echo "Available checkpoint tags:"
        git tag -l "checkpoint-*"
        return 1
    fi
}

list_checkpoints() {
    echo "Available git checkpoints:"
    cd ~/activelog || exit 1
    git tag -l "checkpoint-*" --sort=-creatordate | head -20
    echo ""
    echo "Git repository size: $(du -sh .git | cut -f1)"
}

cleanup_old_checkpoints() {
    echo "Cleaning up old checkpoint tags (keeping latest $MAX_CHECKPOINTS)..."
    cd ~/activelog || exit 1
    
    # Get all checkpoint tags sorted by creation date (newest first)
    local checkpoints=$(git tag -l "checkpoint-*" --sort=-creatordate)
    local count=0
    
    for tag in $checkpoints; do
        count=$((count + 1))
        if [ $count -gt $MAX_CHECKPOINTS ]; then
            git tag -d "$tag"
            echo "Deleted old checkpoint: $tag"
        fi
    done
}

estimate_cost() {
    local hours=$1
    local bots=$2
    
    # Rough estimate: $0.10 per bot-hour
    local cost=$(echo "$hours * $bots * 0.10" | bc 2>/dev/null || echo "N/A")
    echo "Estimated CC cost: $cost"
}

# Main loop for improvements
run_improvement_bot() {
    local type=$1  # backend|frontend|game
    
    while true; do
        # Clean up old checkpoints first
        cleanup_old_checkpoints
        
        # Create checkpoint every hour
        create_checkpoint
        
        # Run improvements (placeholder for Claude integration)
        echo "Running $type improvements..."
        
        # Sleep for 4 hours (reduced frequency for better performance)
        sleep 14400
    done
}

# Command interface
case "$1" in
    start-backend)
        run_improvement_bot backend &
        echo $! > ~/activelog/pids/improvement_backend.pid
        ;;
    start-frontend)
        run_improvement_bot frontend &
        echo $! > ~/activelog/pids/improvement_frontend.pid
        ;;
    stop)
        kill $(cat ~/activelog/pids/improvement_*.pid 2>/dev/null) 2>/dev/null || echo "No improvement bots running"
        ;;
    checkpoint)
        create_checkpoint "$2"
        ;;
    rollback)
        rollback_checkpoint "$2"
        ;;
    list)
        list_checkpoints
        ;;
    cleanup)
        cleanup_old_checkpoints
        ;;
    estimate)
        estimate_cost "$2" "$3"
        ;;
    *)
        echo "Usage: $0 {start-backend|start-frontend|stop|checkpoint|rollback|list|cleanup|estimate}"
        echo "  start-backend    - Start backend improvement bot"
        echo "  start-frontend   - Start frontend improvement bot"  
        echo "  stop            - Stop all improvement bots"
        echo "  checkpoint [name] - Create a git checkpoint"
        echo "  rollback <name>  - Rollback to a specific checkpoint"
        echo "  list            - List available checkpoints"
        echo "  cleanup         - Clean up old checkpoints"
        echo "  estimate <hours> <bots> - Estimate costs"
        ;;
esac
