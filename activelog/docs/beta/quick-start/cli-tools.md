# CLI Tools Quick Start

Master the ActiveLog command-line interface tools for automation, administration, and advanced workflows. Perfect for developers, system administrators, and power users.

## 🎯 What You'll Learn
- Install and configure ActiveLog CLI tools
- Authenticate and connect to beta services
- Execute common administrative tasks
- Automate workflows with scripts
- Troubleshoot CLI issues

## ⏱️ Estimated Time: 20-30 minutes

## 📋 Prerequisites

Before starting, ensure you have:
- ✅ ActiveLog beta account with API access
- ✅ Terminal or command prompt access
- ✅ Node.js 16+ or Python 3.8+ installed
- ✅ Git installed (for some tools)
- ✅ Administrative/sudo access (for global installation)

## 🛠️ Available CLI Tools

### Primary Tools
- **ActiveLog CLI** - Main command-line interface for all operations
- **Beta Management CLI** - Tools for managing beta users and features
- **Migration CLI** - Data migration and backup utilities
- **Developer CLI** - Development and debugging tools

### Specialized Tools
- **Feedback CLI** - Collect and analyze feedback data
- **Analytics CLI** - Generate reports and insights
- **Deployment CLI** - Deploy and manage ActiveLog instances
- **Integration CLI** - Manage external service connections

## 🚀 Step 1: Installation

### 1.1 Choose Your Installation Method

**Method A: NPM (Recommended)**
```bash
# Install globally
npm install -g @activelog/cli

# Verify installation
activelog --version
```

**Method B: Python pip**
```bash
# Install globally
pip install activelog-cli

# Verify installation
activelog --version
```

**Method C: Direct Download**
```bash
# Download for your platform
curl -L https://releases.activelog.dev/cli/latest/activelog-linux -o activelog
chmod +x activelog
sudo mv activelog /usr/local/bin/

# Verify installation
activelog --version
```

**Method D: Docker (Isolated)**
```bash
# Run in container
docker run --rm activelog/cli --version

# Create alias for easier use
alias activelog='docker run --rm -v $(pwd):/workspace activelog/cli'
```

### 1.2 Platform-Specific Instructions

**Windows**
```powershell
# Using Chocolatey
choco install activelog-cli

# Using Scoop
scoop install activelog-cli

# Manual installation
# Download activelog.exe from releases page
# Add to PATH
```

**macOS**
```bash
# Using Homebrew
brew install activelog/tap/activelog-cli

# Using MacPorts
sudo port install activelog-cli
```

**Linux**
```bash
# Ubuntu/Debian
curl -s https://packagecloud.io/install/repositories/activelog/cli/script.deb.sh | sudo bash
sudo apt-get install activelog-cli

# CentOS/RHEL
curl -s https://packagecloud.io/install/repositories/activelog/cli/script.rpm.sh | sudo bash
sudo yum install activelog-cli

# Arch Linux
yay -S activelog-cli
```

### 1.3 Verify Installation
```bash
# Check version and available commands
activelog --version
activelog --help

# List all available sub-commands
activelog help

# Check system requirements
activelog doctor
```

## 🔐 Step 2: Authentication

### 2.1 Initial Authentication
```bash
# Start authentication flow
activelog auth login

# You'll be prompted for:
# - Email address
# - Password
# - Two-factor code (if enabled)
```

### 2.2 API Token Authentication (Recommended)
```bash
# Generate API token from web interface
# Settings → API Keys → Generate New Key

# Configure CLI with token
activelog auth token YOUR_API_TOKEN_HERE

# Verify authentication
activelog auth status
```

### 2.3 Environment Configuration
```bash
# Set beta environment (default for beta users)
activelog config set environment beta

# Set custom API endpoint if needed
activelog config set api-url https://beta-api.activelog.dev

# View current configuration
activelog config list
```

### 2.4 Multiple Account Management
```bash
# Add additional account
activelog auth add --name production

# Switch between accounts
activelog auth use beta
activelog auth use production

# List configured accounts
activelog auth list
```

## 🏠 Step 3: Basic Operations

### 3.1 Account Information
```bash
# View account details
activelog account info

# Check beta program status
activelog beta status

# View usage statistics
activelog account usage
```

### 3.2 File Management
```bash
# List files
activelog files list

# Upload a file
activelog files upload /path/to/file.txt

# Download a file
activelog files download file-id /path/to/destination

# Share a file
activelog files share file-id --public
```

### 3.3 Project Management
```bash
# List projects
activelog projects list

# Create a new project
activelog projects create "My CLI Project"

# Get project details
activelog projects show project-id

# Delete a project
activelog projects delete project-id --confirm
```

## 🧪 Step 4: Beta-Specific Features

### 4.1 Beta Management Tools
```bash
# Install beta management CLI
npm install -g @activelog/beta-cli

# List beta users
beta users list

# Invite new beta user
beta users invite user@example.com --tier premium

# View beta statistics
beta stats summary
```

### 4.2 Feature Flag Management
```bash
# List feature flags
activelog features list

# Get feature flag status
activelog features get ai_powered_search

# Enable feature for your account
activelog features enable new_dashboard_ui

# Disable feature
activelog features disable experimental_feature
```

### 4.3 Feedback Operations
```bash
# Submit feedback
activelog feedback submit \
  --category "bug_report" \
  --subject "CLI authentication issue" \
  --message "Detailed description..." \
  --rating 3

# List your feedback
activelog feedback list --mine

# View feedback status
activelog feedback show feedback-id
```

## 🔧 Step 5: Advanced Features

### 5.1 Bulk Operations
```bash
# Bulk file upload
activelog files upload --directory /path/to/folder --recursive

# Bulk user operations (admin only)
activelog users import users.csv

# Bulk project creation
activelog projects create-batch projects.json
```

### 5.2 Data Migration
```bash
# Export all data
activelog export --format json --output backup.json

# Import data
activelog import --file backup.json --merge

# Migrate from another platform
activelog migrate --from notion --config notion-config.json
```

### 5.3 Analytics and Reporting
```bash
# Generate usage report
activelog analytics usage --period 30d --format pdf

# Export activity logs
activelog logs export --since "2024-01-01" --format csv

# Generate beta testing report
activelog beta report --weeks 4
```

### 5.4 Automation Scripts
```bash
# Create automated backup script
activelog scripts create-backup \
  --schedule "0 2 * * *" \
  --destination s3://my-backups/

# Set up monitoring alerts
activelog alerts create \
  --name "High API Usage" \
  --condition "api_calls > 1000" \
  --action email

# Create deployment pipeline
activelog deploy setup \
  --source github:username/repo \
  --branch main \
  --auto-deploy
```

## 📝 Step 6: Configuration and Customization

### 6.1 Configuration File
```bash
# View configuration file location
activelog config path

# Edit configuration directly
activelog config edit

# Reset to defaults
activelog config reset
```

**Sample Configuration** (`~/.activelog/config.yaml`):
```yaml
# ActiveLog CLI Configuration
default_environment: beta
api_url: https://beta-api.activelog.dev
output_format: json
timeout: 30
retry_attempts: 3

# Authentication
auth:
  method: token
  auto_refresh: true

# Features
features:
  auto_update: true
  analytics: true
  color_output: true
  progress_bars: true

# Beta settings
beta:
  feedback_prompts: true
  experimental_features: true
  usage_tracking: true
```

### 6.2 Custom Commands
```bash
# Create alias for common operations
activelog alias create daily-backup "export --format json"

# Create custom script
activelog scripts create my-workflow <<EOF
#!/bin/bash
activelog files upload daily-report.pdf
activelog projects share current --team
activelog feedback prompt --context "daily-workflow"
EOF

# Make script executable
chmod +x ~/.activelog/scripts/my-workflow

# Run custom script
activelog run my-workflow
```

### 6.3 Plugin System
```bash
# List available plugins
activelog plugins list

# Install plugin
activelog plugins install @activelog/notion-sync

# Enable plugin
activelog plugins enable notion-sync

# Configure plugin
activelog plugins configure notion-sync
```

## 🎯 Step 7: Common Workflows

### 7.1 Daily Beta Testing Routine
```bash
#!/bin/bash
# daily-beta-test.sh

echo "Starting daily beta testing routine..."

# Check for updates
activelog update check

# Pull latest feature flags
activelog features sync

# Upload test data
activelog files upload test-data/ --tag daily-test

# Run health check
activelog health check --verbose

# Submit daily feedback
activelog feedback quick-survey

echo "Daily routine completed!"
```

### 7.2 Project Setup Automation
```bash
#!/bin/bash
# setup-project.sh

PROJECT_NAME="$1"

if [ -z "$PROJECT_NAME" ]; then
  echo "Usage: $0 <project-name>"
  exit 1
fi

# Create project
PROJECT_ID=$(activelog projects create "$PROJECT_NAME" --output json | jq -r '.id')

# Set up initial structure
activelog projects setup-template $PROJECT_ID --template beta-testing

# Configure integrations
activelog integrations enable github --project $PROJECT_ID
activelog integrations enable slack --project $PROJECT_ID

# Invite team members
activelog projects invite $PROJECT_ID --users team-members.txt

echo "Project $PROJECT_NAME created with ID: $PROJECT_ID"
```

### 7.3 Data Backup Automation
```bash
#!/bin/bash
# backup-data.sh

DATE=$(date +%Y%m%d)
BACKUP_DIR="/backups/activelog/$DATE"

mkdir -p "$BACKUP_DIR"

# Export all data
activelog export \
  --format json \
  --include-files \
  --output "$BACKUP_DIR/full-backup-$DATE.json"

# Export specific project
activelog projects export important-project \
  --output "$BACKUP_DIR/important-project-$DATE.json"

# Verify backup
activelog backup verify "$BACKUP_DIR/full-backup-$DATE.json"

# Upload to cloud storage
activelog storage upload "$BACKUP_DIR" --destination s3://my-backups/

echo "Backup completed: $BACKUP_DIR"
```

## 🔍 Step 8: Troubleshooting

### 8.1 Common Issues

**Authentication Failures**
```bash
# Clear cached credentials
activelog auth logout
activelog auth clear-cache

# Re-authenticate
activelog auth login --force

# Check token validity
activelog auth validate
```

**Connection Issues**
```bash
# Test connectivity
activelog connectivity test

# Check network settings
activelog network diagnose

# Use custom endpoint
activelog config set api-url https://backup-api.activelog.dev
```

**Performance Problems**
```bash
# Enable verbose logging
activelog --verbose command-name

# Check system resources
activelog system check

# Profile command execution
activelog --profile command-name
```

### 8.2 Debug Mode
```bash
# Enable debug output
export ACTIVELOG_DEBUG=1
activelog command-name

# Enable API tracing
export ACTIVELOG_TRACE_API=1
activelog command-name

# Log to file
activelog --log-file debug.log command-name
```

### 8.3 Getting Help
```bash
# General help
activelog help

# Command-specific help
activelog help <command>

# Show examples
activelog examples <command>

# Check system status
activelog status
```

## 📊 Step 9: Monitoring and Analytics

### 9.1 Usage Analytics
```bash
# View personal usage
activelog analytics personal --period 30d

# Team usage (if admin)
activelog analytics team --format chart

# API usage breakdown
activelog analytics api --detailed
```

### 9.2 Performance Monitoring
```bash
# Monitor command performance
activelog monitor start

# View performance history
activelog monitor history

# Set up alerts
activelog alerts create \
  --name "CLI Performance" \
  --condition "avg_response_time > 5s"
```

### 9.3 Error Tracking
```bash
# View recent errors
activelog errors list

# Report error
activelog errors report --id error-123

# Auto-report errors
activelog config set auto_report_errors true
```

## ⚡ Performance Tips

### Optimization Strategies
```bash
# Enable caching
activelog config set enable_cache true

# Increase timeout for slow connections
activelog config set timeout 60

# Use compression
activelog config set compression true

# Parallel operations
activelog files upload *.pdf --parallel 4
```

### Bash Completion
```bash
# Enable bash completion
activelog completion bash > ~/.activelog-completion
echo 'source ~/.activelog-completion' >> ~/.bashrc

# Zsh completion
activelog completion zsh > ~/.activelog-completion.zsh
echo 'source ~/.activelog-completion.zsh' >> ~/.zshrc
```

## 🎉 Success Verification

You've successfully set up the CLI tools when you can:

✅ **Install and authenticate** - CLI tools installed and connected  
✅ **Execute basic commands** - List files, projects, account info  
✅ **Access beta features** - Use beta-specific CLI functions  
✅ **Run automation** - Execute scripts and workflows  
✅ **Troubleshoot issues** - Diagnose and resolve problems  

## 🔄 Next Steps

### Immediate Actions
1. **Set up daily automation** - Create scripts for routine tasks
2. **Configure integrations** - Connect with your existing tools
3. **Customize environment** - Adjust CLI settings for your workflow
4. **Create backup routine** - Automate data protection

### Advanced Usage
1. **Plugin development** - Create custom CLI extensions  
2. **CI/CD integration** - Add ActiveLog to your deployment pipeline
3. **Monitoring setup** - Implement comprehensive monitoring
4. **Team workflows** - Share scripts and configurations

### Community Engagement
1. **Share scripts** - Contribute useful automation to community
2. **Report CLI bugs** - Help improve tools for everyone
3. **Feature requests** - Suggest CLI enhancements
4. **Documentation** - Help improve CLI documentation

## 📚 Additional Resources

### Documentation
- [CLI Command Reference](../api/cli-reference.md)
- [Automation Scripts](../developer/automation.md)
- [Integration Examples](../developer/integrations.md)

### Community
- [CLI Tools Forum](https://community.activelog.dev/cli)
- [Script Repository](https://github.com/activelog/cli-scripts)
- [Best Practices](../best-practices/cli-usage.md)

### Support
- **CLI Issues**: cli-support@activelog.dev
- **Feature Requests**: cli-features@activelog.dev
- **Community**: [Discord CLI Channel](https://discord.gg/activelog-cli)

---

**Ready to automate everything?** The CLI tools unlock the full power of ActiveLog for developers and power users. Start with basic operations and gradually build more sophisticated workflows.

*Last Updated: [Current Date] | CLI Version: Beta 2.1*