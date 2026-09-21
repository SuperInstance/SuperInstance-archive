#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}ActiveLog System Backup Starting...${NC}"

# Step 1: Stop all services gracefully
echo -e "${YELLOW}Stopping services...${NC}"
pkill -SIGTERM -f "python3.*main.py"
sleep 5
pkill -SIGTERM -f "node"
docker-compose -f ~/activelog/docker-compose.yml stop 2>/dev/null
sleep 3

# Step 2: Create backup with progress
BACKUP_DATE=$(date +%Y%m%d-%H%M)
BACKUP_NAME="activelog-backup-${BACKUP_DATE}.tar.gz"
BACKUP_PATH="$HOME/${BACKUP_NAME}"

echo -e "${YELLOW}Creating backup: ${BACKUP_NAME}${NC}"

# Calculate size for progress bar
SIZE=$(du -sb ~/activelog --exclude='node_modules' --exclude='__pycache__' --exclude='.git' --exclude='*.log' 2>/dev/null | awk '{print $1}')
SIZE_MB=$((SIZE / 1048576))

echo "Estimated size: ${SIZE_MB}MB"

# Create backup with progress using pv (pipe viewer)
if command -v pv &> /dev/null; then
    tar czf - \
        --exclude='activelog/node_modules' \
        --exclude='activelog/__pycache__' \
        --exclude='activelog/.git' \
        --exclude='activelog/logs/*' \
        --exclude='*.log' \
        -C "$HOME" activelog | pv -s $SIZE > "${BACKUP_PATH}"
else
    # Fallback without progress bar
    tar czf "${BACKUP_PATH}" \
        --exclude='activelog/node_modules' \
        --exclude='activelog/__pycache__' \
        --exclude='activelog/.git' \
        --exclude='activelog/logs/*' \
        --exclude='*.log' \
        -C "$HOME" activelog &
    
    # Show simple progress
    PID=$!
    while kill -0 $PID 2>/dev/null; do
        echo -n "."
        sleep 1
    done
    echo ""
fi

# Step 3: Upload to S3
echo -e "${YELLOW}Uploading to S3...${NC}"
aws s3 cp "${BACKUP_PATH}" s3://activelog-backup-activeloguser-20250823/ --no-progress
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Backup uploaded successfully${NC}"
    # Remove local backup to save space
    rm "${BACKUP_PATH}"
else
    echo -e "${RED}✗ Upload failed, keeping local backup${NC}"
fi

# Step 4: Restart services
echo -e "${YELLOW}Restarting services...${NC}"
cd ~/activelog
docker-compose up -d
sleep 5
~/activelog/start_activelog.sh

echo -e "${GREEN}Backup complete! System restarted.${NC}"
