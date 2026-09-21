#!/bin/bash
# SuperInstance.AI System Cleanup & Optimization
# Removes build artifacts and optimizes disk usage

echo "🧹 SuperInstance.AI System Cleanup"
echo "=================================="

# Track space freed
initial_space=$(df /home/activeloguser/activelog --output=avail -h | tail -1)
echo "Initial available space: $initial_space"

# Clean node_modules (keep essential ones)
echo "Cleaning node_modules directories..."
essential_frontends=("frontend-unified" "frontend-activelog" "frontend-personallog")

find /home/activeloguser/activelog -name "node_modules" -type d | while read dir; do
    parent_dir=$(dirname "$dir")
    parent_name=$(basename "$parent_dir")
    
    # Keep essential frontends
    is_essential=false
    for essential in "${essential_frontends[@]}"; do
        if [[ "$parent_name" == "$essential" ]]; then
            is_essential=true
            break
        fi
    done
    
    if [ "$is_essential" = false ]; then
        echo "Removing: $dir"
        rm -rf "$dir"
    else
        echo "Keeping essential: $dir"
    fi
done

# Clean Python cache
echo "Cleaning Python cache..."
find /home/activeloguser/activelog -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null

# Clean build artifacts
echo "Cleaning build artifacts..."
find /home/activeloguser/activelog -name "dist" -type d -exec rm -rf {} + 2>/dev/null
find /home/activeloguser/activelog -name "build" -type d -exec rm -rf {} + 2>/dev/null
find /home/activeloguser/activelog -name ".next" -type d -exec rm -rf {} + 2>/dev/null

# Clean log files over 100MB
echo "Cleaning large log files..."
find /home/activeloguser/activelog -name "*.log" -size +100M -exec truncate -s 10M {} \;

# Clean temporary files
echo "Cleaning temporary files..."
find /home/activeloguser/activelog -name "*.tmp" -delete 2>/dev/null
find /home/activeloguser/activelog -name "*.temp" -delete 2>/dev/null

# Final space report
final_space=$(df /home/activeloguser/activelog --output=avail -h | tail -1)
echo "Final available space: $final_space"
echo "✅ System cleanup completed"