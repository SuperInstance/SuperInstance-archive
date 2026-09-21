#!/bin/bash

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}Safe Backup Starting...${NC}"

# Show current size
SIZE=$(du -sh ~/activelog | awk '{print $1}')
echo "ActiveLog size: $SIZE"

# Stop services
echo -e "${YELLOW}Stopping services...${NC}"
pkill -f "python3.*main.py" 2>/dev/null
docker-compose -f ~/activelog/docker-compose.yml stop 2>/dev/null
sleep 3

# Create backup
BACKUP_DATE=$(date +%Y%m%d-%H%M)
BACKUP_NAME="activelog-backup-${BACKUP_DATE}.tar.gz"

echo -e "${YELLOW}Creating backup: ${BACKUP_NAME}${NC}"

tar czf ~/${BACKUP_NAME} \
    --exclude='*.log' \
    --exclude='node_modules' \
    --exclude='__pycache__' \
    --exclude='.git' \
    --exclude='docker/volumes' \
    -C ~ activelog

echo -e "${GREEN}Backup created!${NC}"
ls -lh ~/${BACKUP_NAME}

# Upload to S3
echo "Uploading to S3..."
aws s3 cp ~/${BACKUP_NAME} s3://activelog-backup-activeloguser-20250823/

# Restart services
echo "Restarting services..."
~/activelog/start_activelog.sh

echo -e "${GREEN}Complete!${NC}"
