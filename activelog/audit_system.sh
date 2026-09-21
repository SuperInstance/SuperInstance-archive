#!/bin/bash

# ActiveLog System Audit Script
# Comprehensive system analysis and health check

set -e

ACTIVELOG_ROOT="/home/activeloguser/activelog"
AUDIT_DATE=$(date '+%Y-%m-%d %H:%M:%S')
TEMP_DIR="/tmp/activelog_audit_$$"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=================================="
echo -e "ActiveLog System Audit Report"
echo -e "Generated: $AUDIT_DATE"
echo -e "==================================${NC}"

mkdir -p "$TEMP_DIR"
cd "$ACTIVELOG_ROOT"

# 1. Services with ports and status
echo -e "\n${GREEN}=== 1. SERVICES ANALYSIS ===${NC}"
echo "SERVICE_ANALYSIS_START"

# Check for running processes
echo "RUNNING_PROCESSES:"
ps aux | grep -i activelog | grep -v grep || echo "No ActiveLog processes found"

# Check for listening ports
echo -e "\nLISTENING_PORTS:"
netstat -tlnp 2>/dev/null | grep -E ":3000|:8000|:5000|:9000|:4000" || echo "No standard ActiveLog ports found"

# Check service directories
echo -e "\nSERVICE_DIRECTORIES:"
find services -maxdepth 1 -type d | sort

# Check for service configuration files
echo -e "\nSERVICE_CONFIGS:"
find . -name "package.json" -o -name "requirements.txt" -o -name "Dockerfile" -o -name "docker-compose.yml" | sort

echo "SERVICE_ANALYSIS_END"

# 2. Dependencies check
echo -e "\n${GREEN}=== 2. DEPENDENCIES ANALYSIS ===${NC}"
echo "DEPENDENCIES_ANALYSIS_START"

# Node.js dependencies
echo "NODE_DEPENDENCIES:"
find . -name "package.json" -exec echo "=== {} ===" \; -exec cat {} \; 2>/dev/null

# Python dependencies  
echo -e "\nPYTHON_DEPENDENCIES:"
find . -name "requirements.txt" -exec echo "=== {} ===" \; -exec cat {} \; 2>/dev/null

# Check for Python imports in services
echo -e "\nPYTHON_IMPORTS_BY_SERVICE:"
for service_dir in services/*/; do
    if [ -d "$service_dir" ]; then
        service_name=$(basename "$service_dir")
        echo "=== $service_name ==="
        find "$service_dir" -name "*.py" -exec grep -h "^import\|^from.*import" {} \; 2>/dev/null | sort -u | head -20
    fi
done

echo "DEPENDENCIES_ANALYSIS_END"

# 3. Lines of code per service
echo -e "\n${GREEN}=== 3. CODE METRICS ===${NC}"
echo "CODE_METRICS_START"

echo "LINES_OF_CODE_BY_SERVICE:"
for service_dir in services/*/; do
    if [ -d "$service_dir" ]; then
        service_name=$(basename "$service_dir")
        echo "=== $service_name ==="
        
        # Count different file types
        py_lines=$(find "$service_dir" -name "*.py" -exec wc -l {} + 2>/dev/null | tail -1 | awk '{print $1}' || echo "0")
        js_lines=$(find "$service_dir" -name "*.js" -o -name "*.ts" -o -name "*.jsx" -o -name "*.tsx" -exec wc -l {} + 2>/dev/null | tail -1 | awk '{print $1}' || echo "0")
        json_lines=$(find "$service_dir" -name "*.json" -exec wc -l {} + 2>/dev/null | tail -1 | awk '{print $1}' || echo "0")
        
        echo "Python: $py_lines lines"
        echo "JavaScript/TypeScript: $js_lines lines"
        echo "JSON: $json_lines lines"
        
        total_lines=$(find "$service_dir" -type f \( -name "*.py" -o -name "*.js" -o -name "*.ts" -o -name "*.jsx" -o -name "*.tsx" -o -name "*.json" \) -exec wc -l {} + 2>/dev/null | tail -1 | awk '{print $1}' || echo "0")
        echo "Total: $total_lines lines"
        echo ""
    fi
done

# Overall project stats
echo "OVERALL_PROJECT_STATS:"
total_py=$(find . -name "*.py" -exec wc -l {} + 2>/dev/null | tail -1 | awk '{print $1}' || echo "0")
total_js=$(find . -name "*.js" -o -name "*.ts" -o -name "*.jsx" -o -name "*.tsx" -exec wc -l {} + 2>/dev/null | tail -1 | awk '{print $1}' || echo "0")
total_files=$(find . -type f \( -name "*.py" -o -name "*.js" -o -name "*.ts" -o -name "*.jsx" -o -name "*.tsx" \) | wc -l)

echo "Total Python lines: $total_py"
echo "Total JavaScript/TypeScript lines: $total_js"
echo "Total code files: $total_files"

echo "CODE_METRICS_END"

# 4. API endpoints
echo -e "\n${GREEN}=== 4. API ENDPOINTS ===${NC}"
echo "API_ENDPOINTS_START"

echo "DETECTED_API_ROUTES:"
# Search for Express routes
find . -name "*.js" -o -name "*.ts" -exec grep -l "app\.\|router\.\|express\(\)" {} \; | while read file; do
    echo "=== $file ==="
    grep -n "app\.get\|app\.post\|app\.put\|app\.delete\|router\.get\|router\.post\|router\.put\|router\.delete" "$file" 2>/dev/null | head -10
done

# Search for Python Flask/FastAPI routes
echo -e "\nPYTHON_API_ROUTES:"
find . -name "*.py" -exec grep -l "@app\.\|@router\.\|Flask\|FastAPI" {} \; | while read file; do
    echo "=== $file ==="
    grep -n "@app\.\|@router\.\|@.*route\|def.*api" "$file" 2>/dev/null | head -10
done

echo "API_ENDPOINTS_END"

# 5. Database schemas
echo -e "\n${GREEN}=== 5. DATABASE ANALYSIS ===${NC}"
echo "DATABASE_ANALYSIS_START"

echo "DATABASE_FILES:"
find . -name "*.sql" -o -name "*schema*" -o -name "*migration*" -o -name "*.db" | sort

echo -e "\nDATABASE_CONFIGURATIONS:"
find . -name "*.json" -o -name "*.env*" -o -name "config*" | xargs grep -l -i "database\|db_\|mongo\|postgres\|mysql" 2>/dev/null | head -10

echo -e "\nDATABASE_MODELS:"
find . -name "*.py" -exec grep -l "class.*Model\|SQLAlchemy\|mongoose\|@Entity" {} \; | head -10

echo "DATABASE_ANALYSIS_END"

# 6. Docker containers
echo -e "\n${GREEN}=== 6. DOCKER ANALYSIS ===${NC}"
echo "DOCKER_ANALYSIS_START"

echo "DOCKER_FILES:"
find . -name "Dockerfile*" -o -name "docker-compose*" | sort

echo -e "\nDOCKER_COMPOSE_SERVICES:"
if [ -f "docker-compose.yml" ]; then
    echo "=== docker-compose.yml ==="
    grep -A 5 "services:" docker-compose.yml 2>/dev/null || echo "No services section found"
fi

echo -e "\nRUNNING_CONTAINERS:"
docker ps 2>/dev/null || echo "Docker not available or no containers running"

echo -e "\nDOCKER_IMAGES:"
docker images | grep activelog 2>/dev/null || echo "No ActiveLog Docker images found"

echo "DOCKER_ANALYSIS_END"

# 7. Configuration files
echo -e "\n${GREEN}=== 7. CONFIGURATION FILES ===${NC}"
echo "CONFIG_ANALYSIS_START"

echo "CONFIGURATION_FILES:"
find . \( -name "*.json" -o -name "*.yml" -o -name "*.yaml" -o -name "*.env*" -o -name "config*" -o -name "settings*" \) | sort

echo -e "\nENVIRONMENT_FILES:"
find . -name ".env*" | sort

echo -e "\nCONFIG_FILE_SIZES:"
find . \( -name "*.json" -o -name "*.yml" -o -name "*.yaml" \) -exec ls -lh {} \; | sort -k5 -rh | head -20

echo "CONFIG_ANALYSIS_END"

# 8. Environment variables check
echo -e "\n${GREEN}=== 8. ENVIRONMENT VARIABLES ===${NC}"
echo "ENV_ANALYSIS_START"

echo "ENVIRONMENT_VARIABLE_USAGE:"
find . -name "*.js" -o -name "*.ts" -o -name "*.py" | head -50 | xargs grep -h "process\.env\|os\.environ\|getenv" 2>/dev/null | sort -u | head -20

echo -e "\nENV_FILE_VARIABLES:"
if [ -f ".env" ]; then
    echo "=== .env ==="
    grep "^[A-Z]" .env 2>/dev/null | head -10 || echo "No .env file or variables found"
fi

echo -e "\nMISSING_ENV_REFERENCES:"
# Check for undefined env vars in code
find . -name "*.js" -o -name "*.ts" -o -name "*.py" | head -20 | xargs grep -n "process\.env\.\|os\.environ\[" 2>/dev/null | head -10

echo "ENV_ANALYSIS_END"

# 9. Disk usage
echo -e "\n${GREEN}=== 9. DISK USAGE ANALYSIS ===${NC}"
echo "DISK_USAGE_START"

echo "SERVICE_DIRECTORY_SIZES:"
du -sh services/* 2>/dev/null | sort -rh

echo -e "\nLARGEST_FILES:"
find . -type f -size +1M -exec ls -lh {} \; 2>/dev/null | sort -k5 -rh | head -10

echo -e "\nDISK_USAGE_BY_TYPE:"
echo "Python files:"
find . -name "*.py" -exec ls -l {} \; 2>/dev/null | awk '{sum += $5} END {print "Total: " sum/1024/1024 " MB"}'

echo "JavaScript files:"
find . -name "*.js" -o -name "*.ts" -o -name "*.jsx" -o -name "*.tsx" -exec ls -l {} \; 2>/dev/null | awk '{sum += $5} END {print "Total: " sum/1024/1024 " MB"}'

echo "JSON files:"
find . -name "*.json" -exec ls -l {} \; 2>/dev/null | awk '{sum += $5} END {print "Total: " sum/1024/1024 " MB"}'

echo "DISK_USAGE_END"

# 10. Project tree
echo -e "\n${GREEN}=== 10. PROJECT STRUCTURE ===${NC}"
echo "PROJECT_TREE_START"

echo "PROJECT_TREE:"
if command -v tree >/dev/null 2>&1; then
    tree -L 3 -I 'node_modules|__pycache__|*.pyc|.git' 2>/dev/null || echo "Tree command failed"
else
    find . -type d | head -50 | sort
fi

echo -e "\nDIRECTORY_STRUCTURE:"
find . -maxdepth 3 -type d | sort

echo "PROJECT_TREE_END"

# 11. Log files
echo -e "\n${GREEN}=== 11. LOG FILES ANALYSIS ===${NC}"
echo "LOG_ANALYSIS_START"

echo "LOG_FILES:"
find . -name "*.log" -o -name "*log*" | head -20 | xargs ls -lh 2>/dev/null || echo "No log files found"

echo -e "\nLOG_DIRECTORIES:"
find . -name "logs" -o -name "log" -type d | head -10

echo -e "\nRECENT_LOG_ACTIVITY:"
find . -name "*.log" -mtime -7 2>/dev/null | head -10 | xargs ls -lt || echo "No recent log activity"

echo "LOG_ANALYSIS_END"

# 12. Running processes
echo -e "\n${GREEN}=== 12. PROCESS ANALYSIS ===${NC}"
echo "PROCESS_ANALYSIS_START"

echo "ACTIVELOG_PROCESSES:"
ps aux | grep -i activelog | grep -v grep || echo "No ActiveLog processes found"

echo -e "\nNODE_PROCESSES:"
ps aux | grep node | grep -v grep || echo "No Node.js processes found"

echo -e "\nPYTHON_PROCESSES:"
ps aux | grep python | grep -v grep || echo "No Python processes found"

echo -e "\nPORT_USAGE:"
netstat -tlnp 2>/dev/null | grep -E ":300[0-9]|:800[0-9]|:500[0-9]|:900[0-9]|:400[0-9]" || echo "No development ports in use"

echo -e "\nSYSTEM_RESOURCES:"
echo "CPU Usage:"
top -bn1 | grep "Cpu(s)" | head -1

echo "Memory Usage:"
free -h

echo "Disk Usage:"
df -h . | tail -1

echo "PROCESS_ANALYSIS_END"

# Cleanup
rm -rf "$TEMP_DIR"

echo -e "\n${BLUE}=================================="
echo -e "Audit completed at $(date '+%Y-%m-%d %H:%M:%S')"
echo -e "==================================${NC}"