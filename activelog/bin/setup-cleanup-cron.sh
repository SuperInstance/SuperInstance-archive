#!/bin/bash
# Setup automated cleanup cron jobs

PROJECT_ROOT="/home/activeloguser/activelog"
CLEANUP_SCRIPT="$PROJECT_ROOT/bin/cleanup-system.sh"

# Make sure the cleanup script is executable
chmod +x "$CLEANUP_SCRIPT"

# Create cron jobs
{
    echo "# ActiveLog Automated Cleanup Jobs"
    echo "# Run cleanup every 6 hours"
    echo "0 */6 * * * $CLEANUP_SCRIPT >/dev/null 2>&1"
    echo ""
    echo "# Run emergency cleanup check every hour"
    echo "0 * * * * $CLEANUP_SCRIPT --emergency >/dev/null 2>&1"
    echo ""
    echo "# Run full cleanup with reporting daily at 2 AM"
    echo "0 2 * * * $CLEANUP_SCRIPT > $PROJECT_ROOT/logs/daily-cleanup-$(date +\%Y\%m\%d).log 2>&1"
} > /tmp/cleanup-cron.txt

# Install cron jobs
echo "Setting up cleanup cron jobs..."
crontab -l 2>/dev/null | grep -v "ActiveLog Automated Cleanup" > /tmp/current-cron.txt || touch /tmp/current-cron.txt
cat /tmp/current-cron.txt /tmp/cleanup-cron.txt | crontab -

echo "Cleanup cron jobs installed successfully!"
echo "Current cron jobs:"
crontab -l

# Clean up temporary files
rm -f /tmp/cleanup-cron.txt /tmp/current-cron.txt