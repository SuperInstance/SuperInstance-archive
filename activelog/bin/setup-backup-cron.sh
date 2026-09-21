#!/bin/bash
# Setup automated backup rotation cron jobs

PROJECT_ROOT="/home/activeloguser/activelog"
BACKUP_SCRIPT="$PROJECT_ROOT/bin/backup-rotation.sh"

# Make sure the backup script is executable
chmod +x "$BACKUP_SCRIPT"

# Create backup cron jobs
{
    echo "# ActiveLog Backup Rotation Jobs"
    echo "# Daily backup at 3 AM"
    echo "0 3 * * * $BACKUP_SCRIPT daily >> $PROJECT_ROOT/logs/backup-daily.log 2>&1"
    echo ""
    echo "# Weekly backup on Sunday at 4 AM" 
    echo "0 4 * * 0 $BACKUP_SCRIPT weekly >> $PROJECT_ROOT/logs/backup-weekly.log 2>&1"
    echo ""
    echo "# Monthly backup on 1st at 5 AM"
    echo "0 5 1 * * $BACKUP_SCRIPT monthly >> $PROJECT_ROOT/logs/backup-monthly.log 2>&1"
    echo ""
    echo "# Backup cleanup every week on Monday at 6 AM"
    echo "0 6 * * 1 $BACKUP_SCRIPT cleanup >> $PROJECT_ROOT/logs/backup-cleanup.log 2>&1"
    echo ""
    echo "# Backup report generation daily at 7 AM"
    echo "0 7 * * * $BACKUP_SCRIPT report >> $PROJECT_ROOT/logs/backup-report.log 2>&1"
} > /tmp/backup-cron.txt

# Install cron jobs
echo "Setting up backup rotation cron jobs..."
crontab -l 2>/dev/null | grep -v "ActiveLog Backup Rotation" > /tmp/current-cron.txt || touch /tmp/current-cron.txt
cat /tmp/current-cron.txt /tmp/backup-cron.txt | crontab -

echo "Backup rotation cron jobs installed successfully!"
echo ""
echo "Schedule summary:"
echo "- Daily backups: 3 AM (keeps 5)"
echo "- Weekly backups: Sunday 4 AM (keeps 4)" 
echo "- Monthly backups: 1st of month 5 AM (keeps 12)"
echo "- Cleanup: Monday 6 AM"
echo "- Reports: Daily 7 AM"
echo ""
echo "Current cron jobs:"
crontab -l

# Clean up temporary files
rm -f /tmp/backup-cron.txt /tmp/current-cron.txt

# Create initial backup directory
mkdir -p "$PROJECT_ROOT/backups"
echo "Created backups directory: $PROJECT_ROOT/backups"