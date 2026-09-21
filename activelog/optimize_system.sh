#!/bin/bash

# ActiveLog System Performance Optimizer
# This script optimizes the system for better performance

echo "🚀 ActiveLog System Performance Optimizer"
echo "=========================================="

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to optimize Python services
optimize_python_services() {
    echo "🐍 Optimizing Python Services..."
    
    # Find and optimize Python imports
    find ./services -name "*.py" -exec grep -l "^import.*\*" {} \; | while read -r file; do
        echo "Warning: Found wildcard import in $file"
    done
    
    # Check for unused imports (requires pyflakes)
    if command_exists pyflakes; then
        echo "Checking for unused imports..."
        find ./services -name "*.py" -exec pyflakes {} \; 2>/dev/null | grep "imported but unused" | head -10
    fi
    
    echo "✅ Python services optimization check complete"
}

# Function to optimize database operations
optimize_databases() {
    echo "🗄️  Optimizing Database Operations..."
    
    # Find services with many SQLite connections
    local sqlite_connections=$(find ./services -name "*.py" -exec grep -l "sqlite3.connect" {} \; | wc -l)
    echo "Found $sqlite_connections services using direct SQLite connections"
    
    # Recommend connection pooling for high-usage services
    find ./services -name "*.py" -exec grep -c "sqlite3.connect" {} \; | sort -nr | head -5 | while read -r count file; do
        if [ "$count" -gt 5 ]; then
            echo "⚠️  High DB usage in $file ($count connections) - Consider connection pooling"
        fi
    done
    
    echo "✅ Database optimization analysis complete"
}

# Function to optimize frontend bundles
optimize_frontend() {
    echo "🎨 Optimizing Frontend Applications..."
    
    # Check for large dependencies in package.json files
    find . -name "package.json" -not -path "./node_modules/*" | while read -r package_file; do
        local dir=$(dirname "$package_file")
        local name=$(basename "$dir")
        
        if [ -f "$package_file" ]; then
            local dep_count=$(jq '.dependencies | length' "$package_file" 2>/dev/null || echo "0")
            local dev_dep_count=$(jq '.devDependencies | length' "$package_file" 2>/dev/null || echo "0")
            
            echo "📦 $name: $dep_count dependencies, $dev_dep_count dev dependencies"
            
            # Check for common heavy dependencies
            if grep -q '"react"' "$package_file"; then
                echo "  - Using React (consider code splitting)"
            fi
            if grep -q '"lodash"' "$package_file"; then
                echo "  - Using Lodash (consider tree shaking)"
            fi
        fi
    done
    
    echo "✅ Frontend optimization analysis complete"
}

# Function to clean up processes
cleanup_processes() {
    echo "🧹 Cleaning Up Processes..."
    
    # Find and report zombie processes
    local zombie_count=$(ps aux | grep -c '[Zz]ombie' || echo "0")
    if [ "$zombie_count" -gt 0 ]; then
        echo "⚠️  Found $zombie_count zombie processes"
    fi
    
    # Clean up old Python processes
    pkill -f "python.*main.py" 2>/dev/null || true
    
    # Clean up old PID files
    find ./pids -name "*.pid" -type f | while read -r pid_file; do
        if [ -f "$pid_file" ]; then
            local pid=$(cat "$pid_file")
            if ! kill -0 "$pid" 2>/dev/null; then
                echo "🗑️  Removing stale PID file: $pid_file"
                rm -f "$pid_file"
            fi
        fi
    done
    
    echo "✅ Process cleanup complete"
}

# Function to optimize system resources
optimize_system_resources() {
    echo "⚙️  Optimizing System Resources..."
    
    # Check memory usage
    local mem_usage=$(free | grep Mem | awk '{printf "%.1f", $3/$2 * 100.0}')
    echo "Memory usage: ${mem_usage}%"
    
    # Check disk usage
    local disk_usage=$(df . | tail -1 | awk '{print $5}' | sed 's/%//')
    echo "Disk usage: ${disk_usage}%"
    
    if [ "$disk_usage" -gt 80 ]; then
        echo "⚠️  High disk usage - cleaning temporary files..."
        find ./services -name "*.log" -type f -mtime +7 -delete 2>/dev/null || true
        find ./services -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    fi
    
    # Optimize Python bytecode
    python3 -m compileall ./services >/dev/null 2>&1 || true
    
    echo "✅ System resource optimization complete"
}

# Function to generate performance report
generate_performance_report() {
    echo "📊 Generating Performance Report..."
    
    local report_file="performance_report_$(date +%Y%m%d_%H%M%S).txt"
    
    {
        echo "ActiveLog Performance Report"
        echo "Generated: $(date)"
        echo "=========================="
        echo
        
        echo "System Information:"
        echo "- OS: $(uname -s)"
        echo "- Architecture: $(uname -m)"
        echo "- Python Version: $(python3 --version)"
        echo "- Node Version: $(node --version 2>/dev/null || echo 'Not installed')"
        echo
        
        echo "Service Count Analysis:"
        echo "- Total Python Services: $(find ./services -name "main.py" | wc -l)"
        echo "- Frontend Applications: $(find . -name "package.json" -not -path "./node_modules/*" | wc -l)"
        echo "- SQLite Connections: $(find ./services -name "*.py" -exec grep -l "sqlite3.connect" {} \; | wc -l)"
        echo "- Blocking Sleep Calls: $(find ./services -name "*.py" -exec grep -l "time\.sleep" {} \; | wc -l)"
        echo
        
        echo "Recommendations:"
        echo "- ✅ Use connection pooling for database-heavy services"
        echo "- ✅ Replace time.sleep with asyncio.sleep in async contexts"
        echo "- ✅ Implement caching for frequently accessed data"
        echo "- ✅ Use lazy loading for frontend components"
        echo "- ✅ Monitor and limit concurrent service starts"
        
    } > "$report_file"
    
    echo "📄 Performance report saved to: $report_file"
}

# Main execution
main() {
    cd "$(dirname "$0")" || exit 1
    
    echo "Starting system optimization..."
    echo
    
    optimize_python_services
    echo
    
    optimize_databases
    echo
    
    optimize_frontend
    echo
    
    cleanup_processes
    echo
    
    optimize_system_resources
    echo
    
    generate_performance_report
    echo
    
    echo "🎉 System optimization complete!"
    echo
    echo "Next Steps:"
    echo "1. Review the performance report"
    echo "2. Consider implementing recommended optimizations"
    echo "3. Monitor system performance after changes"
    echo "4. Run this optimizer regularly for maintenance"
}

# Run main function
main "$@"