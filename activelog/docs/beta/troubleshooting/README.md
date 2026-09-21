# Troubleshooting Guide

Comprehensive troubleshooting guide for ActiveLog beta users. Diagnose and resolve common issues quickly with step-by-step solutions and diagnostic tools.

## 🚨 Emergency Support

### Critical Issues (Data Loss/Security)
- **Emergency Email**: critical@activelog.dev
- **Response Time**: < 1 hour
- **24/7 Support**: Available for critical issues

### Standard Issues
- **Beta Support**: beta-support@activelog.dev
- **Response Time**: < 4 hours
- **Live Chat**: Available in-app during business hours

## 🔍 Quick Diagnostics

### Self-Diagnostic Tool
```bash
# Run comprehensive system check
activelog diagnose --full --beta

# Check specific components
activelog diagnose auth
activelog diagnose sync
activelog diagnose performance
```

### Browser Diagnostic
```javascript
// Paste in browser console for instant diagnostics
(function() {
  const diagnostics = {
    browser: navigator.userAgent,
    connection: navigator.connection?.effectiveType || 'unknown',
    storage: localStorage.getItem('activelog-config'),
    errors: JSON.parse(localStorage.getItem('activelog-errors') || '[]')
  };
  console.table(diagnostics);
  return diagnostics;
})();
```

## 🔐 Authentication Issues

### Cannot Login

#### Symptoms
- Login form rejects valid credentials
- "Invalid username/password" error
- Redirect loops after login attempt

#### Diagnostic Steps
```bash
# Check account status
activelog auth status --email your.email@domain.com

# Verify beta access
activelog beta verify-access --user-id [USER_ID]

# Test authentication endpoint
curl -X POST https://beta-api.activelog.dev/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test"}'
```

#### Solutions

**Account Locked (Error: AUTH_001)**
```bash
# Wait 15 minutes or request unlock
activelog auth unlock --email your.email@domain.com
```

**Beta Access Expired**
- Check email for extension notice
- Contact beta-support@activelog.dev
- Verify NDA status is current

**Browser Issues**
1. Clear browser cache and cookies
2. Try incognito/private mode
3. Disable browser extensions
4. Use different browser (Chrome/Firefox recommended)

**Password Issues**
1. Use password reset: https://beta.activelog.dev/reset
2. Check for caps lock
3. Try typing password in text field to verify
4. Ensure password meets requirements (8+ chars)

### Session Expires Quickly

#### Symptoms
- Logged out after 5-10 minutes
- Have to re-login frequently
- "Session expired" errors

#### Diagnostic Steps
```bash
# Check session configuration
activelog config get session.timeout
activelog config get session.sliding_expiry

# Monitor session activity
activelog session monitor --verbose
```

#### Solutions
```bash
# Extend session timeout (beta users)
activelog config set session.timeout 480  # 8 hours
activelog config set session.remember_me true

# Enable persistent sessions
activelog config set session.persistent true
```

### Two-Factor Authentication Problems

#### Symptoms
- 2FA codes not working
- "Invalid verification code" error
- Can't access authenticator app

#### Solutions

**Authenticator App Issues**
```bash
# Generate backup codes
activelog auth backup-codes --generate

# Reset 2FA (requires email verification)
activelog auth reset-2fa --email your.email@domain.com
```

**Time Sync Issues**
```bash
# Check system time synchronization
timedatectl status

# Manual time sync (Linux/Mac)
sudo ntpdate -s time.nist.gov
```

## 📁 File Management Issues

### Upload Failures

#### Symptoms
- Files won't upload
- Upload progress stalls at X%
- "Upload failed" error messages

#### Diagnostic Steps
```bash
# Check file constraints
activelog files check-constraints --file path/to/file.ext

# Test upload endpoint
curl -X POST https://beta-api.activelog.dev/v1/files/upload \
  -H "Authorization: Bearer [TOKEN]" \
  -F "file=@test.txt"

# Check storage quota
activelog storage usage --detailed
```

#### Common Solutions

**File Size Limits (Error: UPLOAD_003)**
- Beta limit: 1GB per file
- Compress large files
- Split large files into parts
- Contact support for enterprise limits

**Network Issues**
```bash
# Test connection stability
ping -c 10 beta.activelog.dev

# Check upload bandwidth
speedtest-cli

# Try different network connection
```

**File Type Restrictions**
```bash
# Check allowed file types
activelog files allowed-types --list

# Verify file isn't corrupted
file path/to/your/file.ext
md5sum path/to/your/file.ext
```

### Sync Problems

#### Symptoms
- Files not syncing between devices
- Old versions showing
- Sync status shows "error"

#### Diagnostic Commands
```bash
# Check sync status
activelog sync status --verbose

# Force sync
activelog sync force --all

# Check for conflicts
activelog sync conflicts --list
```

#### Resolution Steps

**Conflict Resolution**
```bash
# List conflicts
activelog sync conflicts --detailed

# Resolve conflicts (keep local)
activelog sync resolve --strategy local

# Resolve conflicts (keep remote)
activelog sync resolve --strategy remote

# Resolve conflicts (manual merge)
activelog sync resolve --strategy manual --file [FILE_ID]
```

**Sync Service Issues**
```bash
# Restart sync service
activelog service restart sync

# Reset sync state
activelog sync reset --confirm

# Check sync logs
activelog logs sync --tail 100
```

### File Corruption

#### Symptoms
- Files won't open
- Garbled content
- "File corrupted" messages

#### Recovery Steps
```bash
# Check file integrity
activelog files verify --file [FILE_ID]

# Restore from backup
activelog backup restore --file [FILE_ID] --version [VERSION]

# Download fresh copy
activelog files download --file [FILE_ID] --force-refresh
```

## ⚡ Performance Issues

### Slow Loading

#### Symptoms
- Pages take >5 seconds to load
- Timeouts during operations
- Unresponsive interface

#### Performance Diagnostics
```bash
# Run performance analysis
activelog perf analyze --full

# Check resource usage
activelog perf resources --monitor 60

# Test API response times
activelog perf api-test --endpoints all
```

#### Browser Optimization
```javascript
// Check performance metrics in browser console
performance.getEntriesByType('navigation').map(entry => ({
  domContentLoaded: entry.domContentLoadedEventEnd - entry.domContentLoadedEventStart,
  loadComplete: entry.loadEventEnd - entry.loadEventStart,
  dns: entry.domainLookupEnd - entry.domainLookupStart,
  server: entry.responseEnd - entry.requestStart
}));
```

#### Solutions

**Browser Performance**
1. Close unnecessary tabs (keep <10 active)
2. Clear browser cache and cookies
3. Disable unused browser extensions
4. Switch to Chrome or Firefox
5. Increase browser memory limit

**Network Optimization**
```bash
# Test connection speed
speedtest-cli

# Check DNS resolution
nslookup beta.activelog.dev
dig beta.activelog.dev

# Try different DNS servers
# Set DNS to 1.1.1.1 or 8.8.8.8
```

**App Settings Optimization**
```bash
# Enable performance mode
activelog config set performance.mode optimized

# Reduce preview quality
activelog config set preview.quality medium

# Disable unused features
activelog features disable real_time_sync
activelog features disable ai_insights
```

### Memory Issues

#### Symptoms
- Browser crashes
- "Out of memory" errors
- System becomes unresponsive

#### Diagnostic Steps
```bash
# Check memory usage
activelog perf memory --detailed

# Monitor memory over time
activelog perf memory --monitor --interval 30
```

#### Solutions
```bash
# Clear application cache
activelog cache clear --all

# Reduce concurrent operations
activelog config set sync.max_concurrent 3
activelog config set upload.batch_size 5

# Enable memory-saving mode
activelog config set memory.optimization aggressive
```

## 🔗 Integration Issues

### Google Workspace Integration

#### Common Problems

**Authentication Failures**
```bash
# Re-authenticate with Google
activelog integrations auth google --reauth

# Check OAuth scopes
activelog integrations scopes google --verify

# Test Google API access
activelog integrations test google --endpoint drive
```

**Sync Not Working**
```bash
# Check Google Drive permissions
activelog integrations permissions google --check

# Reset Google integration
activelog integrations reset google --confirm

# Manual sync trigger
activelog integrations sync google --force
```

### Slack Integration

#### Setup Issues
```bash
# Verify Slack webhook URL
activelog integrations test slack --webhook [URL]

# Check Slack permissions
activelog integrations permissions slack --verify

# Test notification delivery
activelog integrations test slack --send-test
```

### API Integration Problems

#### Common Error Codes

**API_401: Unauthorized**
```bash
# Check API key validity
activelog api key-status --key [KEY_ID]

# Regenerate API key
activelog api key-regenerate --key [KEY_ID]
```

**API_429: Rate Limited**
```bash
# Check rate limit status
activelog api rate-limits --current

# Wait and retry with backoff
sleep 60 && activelog api retry [REQUEST_ID]
```

**API_500: Server Error**
```bash
# Check API service status
activelog api status --detailed

# Report server error
activelog api report-error --request-id [REQUEST_ID]
```

## 🖥️ System-Specific Issues

### Windows Issues

#### Common Problems
- PowerShell execution policy
- Windows Defender blocking
- Path length limitations

#### Solutions
```powershell
# Set execution policy
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Add Windows Defender exclusion
Add-MpPreference -ExclusionPath "C:\Users\[Username]\ActiveLog"

# Enable long path support (Windows 10+)
New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" -Name "LongPathsEnabled" -Value 1 -PropertyType DWORD -Force
```

### macOS Issues

#### Common Problems
- Gatekeeper blocking downloads
- Keychain access issues
- Permission problems

#### Solutions
```bash
# Allow app through Gatekeeper
sudo spctl --master-disable

# Fix keychain access
security unlock-keychain ~/Library/Keychains/login.keychain

# Fix permissions
sudo chown -R $USER:staff ~/ActiveLog
chmod -R 755 ~/ActiveLog
```

### Linux Issues

#### Common Problems
- Missing dependencies
- Permission issues
- Service management

#### Solutions
```bash
# Install common dependencies (Ubuntu/Debian)
sudo apt update
sudo apt install -y curl wget git nodejs npm python3 python3-pip

# Install common dependencies (RHEL/CentOS)
sudo yum install -y curl wget git nodejs npm python3 python3-pip

# Fix permissions
sudo usermod -aG docker $USER
sudo systemctl enable activelog
sudo systemctl start activelog
```

## 🔄 Data Issues

### Data Loss Prevention

#### Immediate Actions
```bash
# Stop all sync operations
activelog sync pause --all

# Create emergency backup
activelog backup create --emergency --verify

# Check data integrity
activelog data verify --comprehensive
```

#### Recovery Procedures
```bash
# List available backups
activelog backup list --detailed

# Restore from specific backup
activelog backup restore --backup-id [BACKUP_ID] --verify

# Restore specific files/folders
activelog backup restore --selective --path "/projects/important"
```

### Data Corruption

#### Detection
```bash
# Run data integrity check
activelog data integrity-check --deep-scan

# Check for corrupted files
activelog files verify --all --repair-attempt
```

#### Repair
```bash
# Attempt automatic repair
activelog data repair --auto --backup-first

# Manual repair process
activelog data repair --interactive --file [FILE_ID]
```

## 📱 Mobile Issues

### iOS App Issues

#### Common Problems
- App crashes on startup
- Sync not working
- Push notifications missing

#### Solutions
```bash
# Check iOS app logs
activelog mobile logs ios --recent

# Reset app data
activelog mobile reset ios --confirm

# Re-register for push notifications
activelog mobile push-notifications ios --register
```

### Android App Issues

#### Common Problems
- Battery optimization blocking
- Background sync disabled
- Storage permissions

#### Solutions
```bash
# Check Android app status
activelog mobile status android --detailed

# Fix battery optimization
activelog mobile battery-optimize android --disable

# Request permissions
activelog mobile permissions android --request-all
```

## 🤖 AI Features Issues

### AI Insights Not Working

#### Diagnostic Steps
```bash
# Check AI service status
activelog ai status --detailed

# Test AI endpoint
activelog ai test --feature insights

# Check AI processing queue
activelog ai queue status --verbose
```

#### Solutions
```bash
# Reset AI models
activelog ai reset --models --confirm

# Clear AI cache
activelog ai cache clear --all

# Re-enable AI features
activelog features enable ai_powered_insights --force
```

### AI Processing Slow

#### Optimization
```bash
# Check AI processing capacity
activelog ai capacity --current

# Optimize AI settings
activelog ai optimize --performance-mode

# Request priority processing (beta users)
activelog ai priority --enable
```

## 📊 Monitoring & Logging

### Enable Debug Logging

#### Application Logs
```bash
# Enable verbose logging
activelog config set logging.level debug
activelog config set logging.verbose true

# View live logs
activelog logs tail --filter error,warning
activelog logs tail --service sync --verbose
```

#### Browser Debug Console
```javascript
// Enable debug mode in browser
localStorage.setItem('activelog-debug', 'true');
localStorage.setItem('activelog-log-level', 'debug');

// View stored logs
console.log(JSON.parse(localStorage.getItem('activelog-logs') || '[]'));
```

### Performance Monitoring

#### Real-time Monitoring
```bash
# Monitor system resources
activelog monitor --realtime --metrics cpu,memory,network

# Monitor API performance
activelog monitor api --endpoints --response-times

# Monitor sync performance
activelog monitor sync --throughput --errors
```

#### Generate Performance Reports
```bash
# Create performance report
activelog report performance --last-24h --format json

# Create detailed diagnostic report
activelog report diagnostic --full --include-logs
```

## 🛠️ Advanced Troubleshooting

### Network Debugging

#### Connection Tests
```bash
# Test all endpoints
activelog network test-endpoints --verbose

# Check SSL/TLS configuration
openssl s_client -connect beta.activelog.dev:443

# Trace network route
traceroute beta.activelog.dev
```

#### Proxy Configuration
```bash
# Configure proxy settings
activelog config set proxy.http "http://proxy.company.com:8080"
activelog config set proxy.https "https://proxy.company.com:8080"

# Test proxy connection
activelog network test-proxy --verbose
```

### Database Issues

#### Local Database Repair
```bash
# Check local database integrity
activelog db check --local --verbose

# Repair local database
activelog db repair --local --backup-first

# Reset local database (nuclear option)
activelog db reset --local --confirm --backup-remote
```

#### Sync Database Issues
```bash
# Check sync database status
activelog db sync-status --detailed

# Force database sync
activelog db sync --force --verify

# Resolve sync conflicts
activelog db conflicts --resolve-strategy manual
```

## 📞 Escalation Procedures

### When to Escalate

**Immediate Escalation (Critical)**
- Data loss or corruption
- Security breaches
- System-wide outages
- NDA violations

**Standard Escalation**
- Unable to resolve after 1 hour
- Issues affecting multiple users
- API functionality broken
- Sync completely failing

### Escalation Process

1. **Gather Information**
   ```bash
   # Create diagnostic package
   activelog support create-package --issue-type [TYPE] --include-logs
   ```

2. **Contact Support**
   - Email: beta-support@activelog.dev
   - Include diagnostic package
   - Specify urgency level
   - Provide reproduction steps

3. **Follow-up**
   - Monitor ticket status
   - Provide additional information promptly
   - Test proposed solutions
   - Confirm resolution

## 📈 Issue Prevention

### Proactive Monitoring

#### Health Checks
```bash
# Setup automated health checks
activelog health setup-monitor --interval 300 --alert-email your@email.com

# Monitor key metrics
activelog monitor setup --metrics sync,auth,performance --threshold-alerts
```

#### Backup Strategy
```bash
# Setup automated backups
activelog backup schedule --daily --time "02:00" --verify

# Test backup restoration
activelog backup test-restore --backup-id recent --dry-run
```

### Best Practices

1. **Regular Updates**
   - Keep browser updated
   - Update ActiveLog client regularly
   - Monitor changelog for issues

2. **System Maintenance**
   - Clear cache weekly
   - Monitor disk space
   - Check for conflicting software

3. **Data Safety**
   - Enable automatic backups
   - Verify sync regularly
   - Export important data monthly

---

## 🔄 Quick Reference

### Common Commands
```bash
# Emergency stops
activelog stop --all --emergency
activelog sync pause --immediate

# Quick diagnostics
activelog diagnose --quick
activelog health check --essential

# Quick fixes
activelog cache clear --all
activelog sync restart
activelog auth refresh
```

### Error Code Reference
- **AUTH_001**: Invalid credentials → Reset password
- **UPLOAD_003**: File too large → Check size limits  
- **SYNC_005**: Connection timeout → Check network
- **API_429**: Rate limited → Wait and retry
- **BETA_007**: Feature unavailable → Check feature flags

### Emergency Contacts
- **Critical Issues**: critical@activelog.dev
- **Beta Support**: beta-support@activelog.dev
- **Migration Help**: migration-support@activelog.dev

*Remember: When in doubt, create a backup first, then contact support with detailed error information and reproduction steps.*

**Last Updated**: [Current Date]  
**Troubleshooting Guide Version**: 2.1.0