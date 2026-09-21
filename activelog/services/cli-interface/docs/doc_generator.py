#!/usr/bin/env python3
"""
Documentation Generator - Generates comprehensive CLI documentation
Supports multiple output formats including Markdown, HTML, JSON, and man pages
"""

import json
import os
import sys
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from pathlib import Path
import logging
import subprocess
import tempfile
import shutil

logger = logging.getLogger(__name__)


class DocumentationGenerator:
    """Generates CLI documentation in multiple formats"""
    
    def __init__(self, config):
        self.config = config
        self.cli_root = Path("/home/activeloguser/activelog/services/cli-interface")
        self.docs_dir = self.cli_root / "docs"
        self.docs_dir.mkdir(exist_ok=True)
        
        # Command documentation structure
        self.command_docs = self._initialize_command_docs()
        
        logger.info("Documentation Generator initialized")

    def generate_documentation(self, doc_type: str = "markdown", 
                             target_platform: str = "all") -> Dict[str, Any]:
        """Generate CLI documentation in specified format"""
        try:
            if doc_type == "markdown":
                return self._generate_markdown(target_platform)
            elif doc_type == "html":
                return self._generate_html(target_platform)
            elif doc_type == "json":
                return self._generate_json(target_platform)
            elif doc_type == "man":
                return self._generate_man_pages(target_platform)
            elif doc_type == "pdf":
                return self._generate_pdf(target_platform)
            elif doc_type == "all":
                return self._generate_all_formats(target_platform)
            else:
                raise ValueError(f"Unsupported documentation type: {doc_type}")
                
        except Exception as e:
            logger.error(f"Failed to generate {doc_type} documentation: {e}")
            raise

    def _generate_markdown(self, platform: str) -> Dict[str, Any]:
        """Generate Markdown documentation"""
        try:
            output_files = []
            
            # Generate main README
            readme_path = self.docs_dir / "README.md"
            readme_content = self._create_main_readme(platform)
            
            with open(readme_path, 'w') as f:
                f.write(readme_content)
            output_files.append(str(readme_path))
            
            # Generate command reference
            commands_path = self.docs_dir / "COMMANDS.md"
            commands_content = self._create_commands_reference(platform)
            
            with open(commands_path, 'w') as f:
                f.write(commands_content)
            output_files.append(str(commands_path))
            
            # Generate installation guide
            install_path = self.docs_dir / "INSTALLATION.md"
            install_content = self._create_installation_guide(platform)
            
            with open(install_path, 'w') as f:
                f.write(install_content)
            output_files.append(str(install_path))
            
            # Generate examples
            examples_path = self.docs_dir / "EXAMPLES.md"
            examples_content = self._create_examples_guide(platform)
            
            with open(examples_path, 'w') as f:
                f.write(examples_content)
            output_files.append(str(examples_path))
            
            # Generate API reference
            api_path = self.docs_dir / "API.md"
            api_content = self._create_api_reference(platform)
            
            with open(api_path, 'w') as f:
                f.write(api_content)
            output_files.append(str(api_path))
            
            return {
                'format': 'markdown',
                'platform': platform,
                'files': output_files,
                'generated_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to generate Markdown documentation: {e}")
            raise

    def _generate_html(self, platform: str) -> Dict[str, Any]:
        """Generate HTML documentation"""
        try:
            # First generate markdown
            md_result = self._generate_markdown(platform)
            
            output_files = []
            html_dir = self.docs_dir / "html"
            html_dir.mkdir(exist_ok=True)
            
            # Convert each markdown file to HTML
            for md_file in md_result['files']:
                md_path = Path(md_file)
                html_path = html_dir / f"{md_path.stem}.html"
                
                html_content = self._markdown_to_html(md_path)
                
                with open(html_path, 'w') as f:
                    f.write(html_content)
                
                output_files.append(str(html_path))
            
            # Generate index page
            index_path = html_dir / "index.html"
            index_content = self._create_html_index(output_files)
            
            with open(index_path, 'w') as f:
                f.write(index_content)
            output_files.insert(0, str(index_path))
            
            # Copy CSS
            css_path = html_dir / "style.css"
            css_content = self._create_documentation_css()
            
            with open(css_path, 'w') as f:
                f.write(css_content)
            
            return {
                'format': 'html',
                'platform': platform,
                'files': output_files,
                'index_file': str(index_path),
                'generated_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to generate HTML documentation: {e}")
            raise

    def _generate_json(self, platform: str) -> Dict[str, Any]:
        """Generate JSON documentation"""
        try:
            json_path = self.docs_dir / "cli-docs.json"
            
            doc_data = {
                'metadata': {
                    'title': 'ActiveLog CLI Documentation',
                    'version': '1.0.0',
                    'platform': platform,
                    'generated_at': datetime.utcnow().isoformat(),
                    'generator': 'ActiveLog CLI Documentation Generator'
                },
                'commands': self._get_platform_commands(platform),
                'installation': self._get_installation_data(platform),
                'examples': self._get_examples_data(platform),
                'api': self._get_api_data(platform)
            }
            
            with open(json_path, 'w') as f:
                json.dump(doc_data, f, indent=2)
            
            return {
                'format': 'json',
                'platform': platform,
                'files': [str(json_path)],
                'data': doc_data,
                'generated_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to generate JSON documentation: {e}")
            raise

    def _generate_man_pages(self, platform: str) -> Dict[str, Any]:
        """Generate man pages for commands"""
        try:
            man_dir = self.docs_dir / "man"
            man_dir.mkdir(exist_ok=True)
            
            output_files = []
            
            # Generate main man page
            main_man = self._create_main_man_page(platform)
            main_man_path = man_dir / "activelog.1"
            
            with open(main_man_path, 'w') as f:
                f.write(main_man)
            output_files.append(str(main_man_path))
            
            # Generate man pages for subcommands
            commands = self._get_platform_commands(platform)
            
            for cmd_name, cmd_data in commands.items():
                if cmd_name == 'bash':  # Focus on bash commands for man pages
                    for subcmd_name, subcmd_data in cmd_data.items():
                        man_content = self._create_command_man_page(subcmd_name, subcmd_data)
                        man_path = man_dir / f"activelog-{subcmd_name}.1"
                        
                        with open(man_path, 'w') as f:
                            f.write(man_content)
                        output_files.append(str(man_path))
            
            return {
                'format': 'man',
                'platform': platform,
                'files': output_files,
                'generated_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to generate man pages: {e}")
            raise

    def _generate_pdf(self, platform: str) -> Dict[str, Any]:
        """Generate PDF documentation"""
        try:
            # First generate HTML
            html_result = self._generate_html(platform)
            
            pdf_path = self.docs_dir / "activelog-cli-docs.pdf"
            
            # Try to use wkhtmltopdf if available
            try:
                # Combine all HTML files into one
                combined_html = self._combine_html_files(html_result['files'])
                
                with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as tmp_html:
                    tmp_html.write(combined_html)
                    tmp_html_path = tmp_html.name
                
                # Convert to PDF
                subprocess.run([
                    'wkhtmltopdf',
                    '--page-size', 'A4',
                    '--margin-top', '20mm',
                    '--margin-bottom', '20mm',
                    '--margin-left', '15mm',
                    '--margin-right', '15mm',
                    tmp_html_path,
                    str(pdf_path)
                ], check=True)
                
                os.unlink(tmp_html_path)
                
            except (subprocess.CalledProcessError, FileNotFoundError):
                # Fallback: create a simple PDF using reportlab if available
                try:
                    pdf_content = self._create_simple_pdf(platform)
                    with open(pdf_path, 'wb') as f:
                        f.write(pdf_content)
                except ImportError:
                    # No PDF generation available
                    return {
                        'format': 'pdf',
                        'platform': platform,
                        'files': [],
                        'error': 'PDF generation not available (missing wkhtmltopdf or reportlab)',
                        'generated_at': datetime.utcnow().isoformat()
                    }
            
            return {
                'format': 'pdf',
                'platform': platform,
                'files': [str(pdf_path)],
                'generated_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to generate PDF documentation: {e}")
            raise

    def _generate_all_formats(self, platform: str) -> Dict[str, Any]:
        """Generate documentation in all available formats"""
        try:
            results = {}
            
            formats = ['markdown', 'html', 'json', 'man']
            # Only include PDF if tools are available
            if shutil.which('wkhtmltopdf'):
                formats.append('pdf')
            
            for fmt in formats:
                try:
                    results[fmt] = self.generate_documentation(fmt, platform)
                except Exception as e:
                    results[fmt] = {'error': str(e)}
            
            return {
                'format': 'all',
                'platform': platform,
                'results': results,
                'generated_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to generate all documentation formats: {e}")
            raise

    def _create_main_readme(self, platform: str) -> str:
        """Create main README.md content"""
        content = f"""# ActiveLog CLI Documentation

The ActiveLog CLI provides a comprehensive command-line interface for interacting with ActiveLog services, managing data, and automating workflows.

## Installation

### Bash/Zsh
```bash
curl -fsSL https://activelog.com/install.sh | bash
```

### PowerShell
```powershell
Install-Module -Name ActiveLog
```

### Python SDK
```bash
pip install activelog-sdk
```

### Node.js
```bash
npm install activelog-client
```

## Quick Start

1. **Authentication**
   ```bash
   activelog auth login
   ```

2. **List entries**
   ```bash
   activelog entries list --limit 10
   ```

3. **Search entries**
   ```bash
   activelog search semantic "important meeting"
   ```

4. **Export data**
   ```bash
   activelog export json output.json
   ```

## Platform Support

This documentation covers the following platforms:
{self._get_platform_list(platform)}

## Commands Overview

### Authentication
- `activelog auth login` - Login to ActiveLog
- `activelog auth logout` - Logout
- `activelog auth status` - Check authentication status

### Entry Management
- `activelog entries list` - List entries
- `activelog entries create` - Create new entry
- `activelog entries update` - Update existing entry
- `activelog entries delete` - Delete entry

### Search Operations
- `activelog search semantic` - Semantic search
- `activelog search similarity` - Similarity search
- `activelog search tags` - Search by tags
- `activelog search date-range` - Search by date range

### Data Export
- `activelog export json` - Export as JSON
- `activelog export csv` - Export as CSV
- `activelog export markdown` - Export as Markdown
- `activelog export pdf` - Export as PDF

### Pipeline Operations
- `activelog pipeline create` - Create data pipeline
- `activelog pipeline run` - Execute pipeline
- `activelog pipeline status` - Check pipeline status
- `activelog pipeline logs` - View pipeline logs

### Webhook Management
- `activelog webhook register` - Register webhook
- `activelog webhook list` - List webhooks
- `activelog webhook delete` - Remove webhook
- `activelog webhook test` - Test webhook

### Configuration
- `activelog config get` - Get configuration value
- `activelog config set` - Set configuration value
- `activelog config list` - List all configurations
- `activelog config reset` - Reset to defaults

## Documentation Structure

- [Commands Reference](COMMANDS.md) - Detailed command documentation
- [Installation Guide](INSTALLATION.md) - Platform-specific installation
- [Examples](EXAMPLES.md) - Usage examples and tutorials
- [API Reference](API.md) - REST API and SDK documentation

## Support

For help and support:
- Use `activelog help` for command-specific help
- Visit our documentation at https://docs.activelog.com
- Report issues at https://github.com/activelog/cli/issues

## Version Information

- CLI Version: 1.0.0
- Documentation Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}
- Target Platform: {platform}
"""
        return content

    def _create_commands_reference(self, platform: str) -> str:
        """Create commands reference documentation"""
        content = """# ActiveLog CLI Commands Reference

This document provides detailed information about all available ActiveLog CLI commands.

"""
        
        commands = self._get_platform_commands(platform)
        
        for platform_name, platform_commands in commands.items():
            content += f"## {platform_name.title()} Commands\n\n"
            
            if platform_name == 'bash':
                for cmd_name, cmd_data in platform_commands.items():
                    content += f"### activelog {cmd_name}\n\n"
                    content += f"{cmd_data.get('description', 'No description available')}\n\n"
                    
                    content += "**Usage:**\n"
                    content += f"```bash\n{cmd_data.get('usage', f'activelog {cmd_name}')}\n```\n\n"
                    
                    if 'subcommands' in cmd_data:
                        content += "**Subcommands:**\n"
                        for subcmd in cmd_data['subcommands']:
                            content += f"- `{subcmd}` - {self._get_subcommand_description(cmd_name, subcmd)}\n"
                        content += "\n"
                    
                    content += "**Examples:**\n"
                    examples = self._get_command_examples(cmd_name)
                    for example in examples:
                        content += f"```bash\n{example}\n```\n"
                    content += "\n"
            
            elif platform_name == 'powershell':
                for cmd_name, cmd_data in platform_commands.items():
                    content += f"### {cmd_name}\n\n"
                    content += f"{cmd_data.get('description', 'No description available')}\n\n"
                    
                    content += "**Usage:**\n"
                    content += f"```powershell\n{cmd_data.get('usage', cmd_name)}\n```\n\n"
                    
                    if 'parameters' in cmd_data:
                        content += "**Parameters:**\n"
                        for param in cmd_data['parameters']:
                            content += f"- `{param}` - Parameter description\n"
                        content += "\n"
            
            elif platform_name in ['python', 'nodejs']:
                content += f"See the {platform_name.title()} SDK section in the API documentation.\n\n"
        
        return content

    def _create_installation_guide(self, platform: str) -> str:
        """Create installation guide"""
        content = f"""# ActiveLog CLI Installation Guide

This guide covers installation methods for different platforms and environments.

## System Requirements

- Operating System: Linux, macOS, Windows
- Python 3.8+ (for Python SDK)
- Node.js 16+ (for Node.js client)
- PowerShell 5.1+ (for PowerShell module)

## Installation Methods

### Bash/Zsh (Linux/macOS)

#### Quick Install
```bash
curl -fsSL https://activelog.com/install.sh | bash
```

#### Manual Install
1. Download the CLI binary:
   ```bash
   wget https://github.com/activelog/cli/releases/latest/download/activelog-linux-amd64
   chmod +x activelog-linux-amd64
   sudo mv activelog-linux-amd64 /usr/local/bin/activelog
   ```

2. Verify installation:
   ```bash
   activelog --version
   ```

3. Set up shell completion:
   ```bash
   activelog completion bash > /etc/bash_completion.d/activelog
   ```

### PowerShell (Windows/Cross-platform)

#### Install from PowerShell Gallery
```powershell
Install-Module -Name ActiveLog -Scope CurrentUser
```

#### Manual Install
1. Download the module:
   ```powershell
   Save-Module -Name ActiveLog -Path $env:USERPROFILE\\Documents\\WindowsPowerShell\\Modules
   ```

2. Import the module:
   ```powershell
   Import-Module ActiveLog
   ```

3. Verify installation:
   ```powershell
   Get-Command -Module ActiveLog
   ```

### Python SDK

#### Install from PyPI
```bash
pip install activelog-sdk
```

#### Install from source
```bash
git clone https://github.com/activelog/python-sdk.git
cd python-sdk
pip install -e .
```

#### Usage
```python
from activelog_sdk import ActiveLogClient

client = ActiveLogClient(api_key="your_api_key")
entries = client.entries.list(limit=10)
```

### Node.js Client

#### Install from npm
```bash
npm install activelog-client
```

#### Install globally
```bash
npm install -g activelog-client
```

#### Usage
```javascript
const {{ ActiveLogClient }} = require('activelog-client');

const client = new ActiveLogClient({{ apiKey: 'your_api_key' }});
const entries = await client.getEntries({{ limit: 10 }});
```

## Configuration

### Authentication
After installation, authenticate with your ActiveLog account:

```bash
activelog auth login
```

### Configuration File
The CLI stores configuration in:
- Linux/macOS: `~/.config/activelog/config.json`
- Windows: `%APPDATA%\\ActiveLog\\config.json`

### Environment Variables
You can also configure using environment variables:
- `ACTIVELOG_API_KEY` - Your API key
- `ACTIVELOG_BASE_URL` - API base URL (default: https://api.activelog.com)
- `ACTIVELOG_CONFIG_DIR` - Custom config directory

## Verification

Test your installation:

```bash
# Check version
activelog --version

# Check authentication
activelog auth status

# Test basic functionality
activelog entries list --limit 5
```

## Troubleshooting

### Common Issues

1. **Command not found**
   - Ensure the binary is in your PATH
   - Try restarting your shell

2. **Permission denied**
   - Check file permissions: `chmod +x /usr/local/bin/activelog`
   - Try installing to a user directory

3. **Authentication failed**
   - Verify your API key: `activelog auth status`
   - Try logging in again: `activelog auth login`

4. **Network errors**
   - Check internet connection
   - Verify API endpoint: `activelog config get base_url`

### Getting Help

- Use `activelog help` for command help
- Use `activelog <command> --help` for specific command help
- Check logs: `activelog config get log_file`
- Visit our documentation: https://docs.activelog.com

## Uninstallation

### Bash/Zsh
```bash
sudo rm /usr/local/bin/activelog
rm -rf ~/.config/activelog
```

### PowerShell
```powershell
Uninstall-Module -Name ActiveLog
```

### Python SDK
```bash
pip uninstall activelog-sdk
```

### Node.js Client
```bash
npm uninstall activelog-client
# or globally:
npm uninstall -g activelog-client
```

## Build from Source

For developers who want to build from source:

```bash
git clone https://github.com/activelog/cli.git
cd cli
make build
sudo make install
```

Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}
"""
        return content

    def _create_examples_guide(self, platform: str) -> str:
        """Create examples and tutorials"""
        content = """# ActiveLog CLI Examples

This guide provides practical examples of using the ActiveLog CLI for common tasks.

## Getting Started

### Initial Setup
```bash
# Install the CLI (if not already done)
curl -fsSL https://activelog.com/install.sh | bash

# Login to your account
activelog auth login

# Verify authentication
activelog auth status
```

## Basic Operations

### Managing Entries

#### Create a new entry
```bash
# Simple entry
activelog entries create --title "Meeting Notes" --content "Discussed project timeline"

# Entry with tags
activelog entries create \\
  --title "Project Update" \\
  --content "Milestone 1 completed" \\
  --tags "project,milestone,completed"

# Entry with category
activelog entries create \\
  --title "Bug Report" \\
  --content "Found issue in authentication flow" \\
  --category "bugs"
```

#### List entries
```bash
# List recent entries
activelog entries list

# List with limit
activelog entries list --limit 20

# List entries by user
activelog entries list --user-id "user123"

# List entries with specific tags
activelog entries list --tags "project,important"
```

#### Update entries
```bash
# Update entry content
activelog entries update ENTRY_ID --content "Updated content"

# Add tags to existing entry
activelog entries update ENTRY_ID --tags "urgent,review"

# Change entry category
activelog entries update ENTRY_ID --category "completed"
```

### Search Operations

#### Semantic Search
```bash
# Basic semantic search
activelog search semantic "team meeting"

# Semantic search with limit
activelog search semantic "project deadline" --limit 10

# Search for specific user
activelog search semantic "bug fix" --user-id "developer1"
```

#### Similarity Search
```bash
# Find similar entries
activelog search similarity "database optimization"

# Similarity search with threshold
activelog search similarity "performance issues" --threshold 0.8
```

#### Tag-based Search
```bash
# Search by single tag
activelog search tags "urgent"

# Search by multiple tags (AND)
activelog search tags "project,milestone"

# Search by tags (OR)
activelog search tags "bug,issue" --match-any
```

#### Date Range Search
```bash
# Search last week
activelog search date-range --from "2024-01-01" --to "2024-01-07"

# Search last 30 days
activelog search date-range --days 30

# Search specific month
activelog search date-range --from "2024-01-01" --to "2024-01-31"
```

## Data Export

### Export Formats

#### JSON Export
```bash
# Export all data
activelog export json all_data.json

# Export specific user data
activelog export json user_data.json --user-id "user123"

# Export date range
activelog export json recent_data.json --from "2024-01-01"
```

#### CSV Export
```bash
# Export to CSV
activelog export csv entries.csv

# Export with custom columns
activelog export csv entries.csv --columns "title,content,created_at"

# Export filtered data
activelog export csv filtered.csv --tags "important"
```

#### Markdown Export
```bash
# Export as markdown
activelog export markdown entries.md

# Export with custom template
activelog export markdown entries.md --template "detailed"

# Export specific entries
activelog export markdown selected.md --entry-ids "id1,id2,id3"
```

## Pipeline Operations

### Creating Pipelines

#### Simple Data Pipeline
```bash
# Create a basic pipeline
activelog pipeline create --name "Daily Backup" \\
  --config pipeline-config.json
```

Example pipeline configuration (`pipeline-config.json`):
```json
{
  "name": "Daily Backup",
  "description": "Export data daily",
  "steps": [
    {
      "name": "Export Data",
      "step_type": "command",
      "config": {
        "command": "activelog",
        "args": ["export", "json", "/backup/daily.json"]
      }
    },
    {
      "name": "Upload to Cloud",
      "step_type": "command",
      "config": {
        "command": "aws",
        "args": ["s3", "cp", "/backup/daily.json", "s3://backups/"]
      },
      "depends_on": ["Export Data"]
    }
  ],
  "triggers": [
    {
      "type": "schedule",
      "schedule": "0 2 * * *"
    }
  ]
}
```

#### Execute Pipeline
```bash
# Run pipeline immediately
activelog pipeline run "Daily Backup"

# Run with input data
activelog pipeline run "Data Processing" \\
  --input '{"source": "/data/input.csv", "format": "csv"}'
```

#### Monitor Pipeline
```bash
# Check pipeline status
activelog pipeline status PIPELINE_ID

# View pipeline logs
activelog pipeline logs PIPELINE_ID

# List all pipelines
activelog pipeline list
```

## Webhook Integration

### Register Webhooks

#### Basic Webhook
```bash
# Register webhook for entry events
activelog webhook register \\
  --url "https://myapp.com/webhooks/activelog" \\
  --events "entry.created,entry.updated"
```

#### Webhook with Secret
```bash
# Register secure webhook
activelog webhook register \\
  --url "https://myapp.com/webhooks/activelog" \\
  --events "entry.created,entry.updated,entry.deleted" \\
  --secret "your_webhook_secret"
```

#### Test Webhook
```bash
# Test webhook delivery
activelog webhook test WEBHOOK_ID

# List all webhooks
activelog webhook list

# Delete webhook
activelog webhook delete WEBHOOK_ID
```

## Batch Operations

### Bulk Data Processing

#### Batch Import
```bash
# Submit batch import job
activelog batch submit \\
  --job-type "data_import" \\
  --command "python" \\
  --args "import_script.py,/data/source.csv" \\
  --priority "high"
```

#### Monitor Batch Jobs
```bash
# Check job status
activelog batch status JOB_ID

# List all jobs
activelog batch list

# Get job logs
activelog batch logs JOB_ID
```

## Advanced Usage

### Configuration Management

#### View Configuration
```bash
# List all configuration
activelog config list

# Get specific value
activelog config get api_key

# Get nested value
activelog config get output.format
```

#### Update Configuration
```bash
# Set configuration value
activelog config set output.format json

# Set nested configuration
activelog config set auth.auto_refresh true

# Reset to defaults
activelog config reset
```

### Using with Scripts

#### Bash Script Example
```bash
#!/bin/bash

# Daily report script
DATE=$(date +%Y-%m-%d)
REPORT_FILE="report_$DATE.json"

echo "Generating daily report for $DATE"

# Export today's entries
activelog search date-range --days 1 | \\
  activelog export json "$REPORT_FILE"

# Send summary
ENTRY_COUNT=$(jq '.entries | length' "$REPORT_FILE")
echo "Processed $ENTRY_COUNT entries for $DATE"

# Upload to storage
aws s3 cp "$REPORT_FILE" "s3://reports/daily/"

echo "Report uploaded successfully"
```

#### Python Script Example
```python
#!/usr/bin/env python3

from activelog_sdk import ActiveLogClient
import json
from datetime import datetime, timedelta

# Initialize client
client = ActiveLogClient(api_key="your_api_key")

# Get recent entries
yesterday = datetime.now() - timedelta(days=1)
entries = client.entries.list(
    date_from=yesterday.isoformat(),
    limit=100
)

# Process entries
important_entries = [
    entry for entry in entries 
    if 'important' in entry.get('tags', [])
]

print(f"Found {len(important_entries)} important entries")

# Generate report
report = {
    'date': datetime.now().isoformat(),
    'total_entries': len(entries),
    'important_entries': len(important_entries),
    'entries': important_entries
}

# Save report
with open('daily_important.json', 'w') as f:
    json.dump(report, f, indent=2)

print("Report saved to daily_important.json")
```

## Troubleshooting

### Common Issues and Solutions

#### Authentication Problems
```bash
# Check current auth status
activelog auth status

# Re-authenticate
activelog auth logout
activelog auth login

# Check API connectivity
activelog entries list --limit 1
```

#### Performance Optimization
```bash
# Use pagination for large datasets
activelog entries list --limit 50 --offset 0

# Filter results to reduce data transfer
activelog entries list --tags "important" --limit 10

# Use specific date ranges
activelog search date-range --from "2024-01-01" --to "2024-01-31"
```

#### Debugging Commands
```bash
# Enable verbose output
activelog --verbose entries list

# Check configuration
activelog config get

# View logs
tail -f ~/.config/activelog/activelog.log
```

## Best Practices

### Security
- Store API keys in environment variables, not scripts
- Use webhook secrets for secure integrations
- Regularly rotate authentication tokens
- Limit API key permissions to minimum required

### Performance
- Use appropriate pagination for large datasets
- Implement caching for frequently accessed data
- Use batch operations for bulk processing
- Monitor rate limits and implement backoff

### Automation
- Use pipelines for complex workflows
- Implement error handling in scripts
- Log operations for debugging
- Test automation in development environments

Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}
"""
        return content

    def _create_api_reference(self, platform: str) -> str:
        """Create API reference documentation"""
        content = """# ActiveLog CLI API Reference

This document provides detailed information about the ActiveLog CLI REST API and SDKs.

## Base URL

```
https://api.activelog.com/v1
```

## Authentication

All API requests require authentication using an API key:

```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \\
     https://api.activelog.com/v1/entries
```

## REST API Endpoints

### Entries

#### GET /entries
List entries with optional filtering.

**Parameters:**
- `limit` (integer) - Maximum number of entries to return (default: 10, max: 100)
- `offset` (integer) - Number of entries to skip (default: 0)
- `user_id` (string) - Filter by user ID
- `tags` (string) - Comma-separated list of tags
- `category` (string) - Filter by category
- `date_from` (string) - ISO 8601 date string
- `date_to` (string) - ISO 8601 date string

**Example:**
```bash
curl "https://api.activelog.com/v1/entries?limit=10&tags=important"
```

#### POST /entries
Create a new entry.

**Request Body:**
```json
{
  "title": "Entry title",
  "content": "Entry content",
  "tags": ["tag1", "tag2"],
  "category": "work"
}
```

#### PUT /entries/{id}
Update an existing entry.

#### DELETE /entries/{id}
Delete an entry.

### Search

#### POST /search
Perform advanced search operations.

**Request Body:**
```json
{
  "query": "search terms",
  "type": "semantic|similarity|tags|date-range",
  "limit": 10,
  "user_id": "optional_user_id"
}
```

### Export

#### POST /export
Export data in various formats.

**Request Body:**
```json
{
  "format": "json|csv|markdown|pdf",
  "filters": {
    "user_id": "user123",
    "tags": ["important"],
    "date_from": "2024-01-01"
  }
}
```

### Pipelines

#### GET /pipelines
List data pipelines.

#### POST /pipelines
Create a new pipeline.

#### POST /pipelines/{id}/execute
Execute a pipeline.

#### GET /pipelines/{id}/status
Get pipeline execution status.

### Webhooks

#### GET /webhooks
List registered webhooks.

#### POST /webhooks
Register a new webhook.

#### DELETE /webhooks/{id}
Delete a webhook.

## Python SDK

### Installation
```bash
pip install activelog-sdk
```

### Basic Usage

```python
from activelog_sdk import ActiveLogClient

# Initialize client
client = ActiveLogClient(api_key="your_api_key")

# List entries
entries = client.entries.list(limit=10)

# Create entry
new_entry = client.entries.create(
    title="New Entry",
    content="Entry content",
    tags=["python", "sdk"]
)

# Search entries
results = client.search.semantic("important meeting")

# Export data
export_result = client.export.json("export.json")
```

### Async Usage

```python
import asyncio
from activelog_sdk import ActiveLogClient

async def main():
    client = ActiveLogClient(api_key="your_api_key")
    
    # Async operations
    entries = await client.entries.list_async(limit=10)
    results = await client.search.semantic_async("query")

asyncio.run(main())
```

### Error Handling

```python
from activelog_sdk import ActiveLogClient, ActiveLogError

client = ActiveLogClient(api_key="your_api_key")

try:
    entries = client.entries.list()
except ActiveLogError as e:
    print(f"API Error: {e}")
    print(f"Status Code: {e.status_code}")
```

## Node.js Client

### Installation
```bash
npm install activelog-client
```

### Basic Usage

```javascript
const { ActiveLogClient } = require('activelog-client');

// Initialize client
const client = new ActiveLogClient({
    apiKey: 'your_api_key'
});

// List entries
const entries = await client.getEntries({ limit: 10 });

// Create entry
const newEntry = await client.createEntry({
    title: 'New Entry',
    content: 'Entry content',
    tags: ['nodejs', 'client']
});

// Search entries
const results = await client.searchSemantic('important meeting');

// Export data
const exportResult = await client.exportData('json', 'export.json');
```

### Error Handling

```javascript
const { ActiveLogClient, ActiveLogError } = require('activelog-client');

const client = new ActiveLogClient({ apiKey: 'your_api_key' });

try {
    const entries = await client.getEntries();
} catch (error) {
    if (error instanceof ActiveLogError) {
        console.log(`API Error: ${error.message}`);
        console.log(`Status Code: ${error.statusCode}`);
    } else {
        console.log(`Unexpected error: ${error.message}`);
    }
}
```

### Streaming

```javascript
// Real-time event streaming
const stream = client.createEventStream({
    events: ['entry.created', 'entry.updated']
});

stream.on('message', (event) => {
    console.log('Received event:', event);
});

stream.on('error', (error) => {
    console.error('Stream error:', error);
});

// Close stream when done
stream.close();
```

## PowerShell Module

### Installation
```powershell
Install-Module -Name ActiveLog
```

### Basic Usage

```powershell
# Connect to ActiveLog
Connect-ActiveLog -ApiKey "your_api_key"

# List entries
$entries = Get-ActiveLogEntries -Limit 10

# Create entry
$newEntry = New-ActiveLogEntry -Title "New Entry" -Content "Entry content"

# Search entries
$results = Search-ActiveLog -Query "important meeting" -Type semantic

# Export data
Export-ActiveLogData -Format JSON -Output "export.json"
```

## Rate Limits

The API implements rate limiting to ensure fair usage:

- **Global Rate Limit:** 1000 requests per hour
- **Command Execution:** 60 requests per minute
- **Search Operations:** 30 requests per minute
- **File Uploads:** 20 requests per hour

Rate limit information is included in response headers:
- `X-RateLimit-Limit` - Request limit for the time window
- `X-RateLimit-Remaining` - Remaining requests in current window
- `X-RateLimit-Reset` - Time when the current window resets

## Response Formats

### Success Response
```json
{
  "success": true,
  "data": {
    // Response data
  },
  "metadata": {
    "total": 100,
    "offset": 0,
    "limit": 10
  }
}
```

### Error Response
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid request parameters",
    "details": {
      // Error details
    }
  }
}
```

## Status Codes

- `200` - Success
- `201` - Created
- `400` - Bad Request
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not Found
- `429` - Rate Limit Exceeded
- `500` - Internal Server Error

## Webhooks

### Webhook Events

- `entry.created` - New entry created
- `entry.updated` - Entry updated
- `entry.deleted` - Entry deleted
- `search.completed` - Search operation completed
- `export.completed` - Export operation completed
- `pipeline.started` - Pipeline execution started
- `pipeline.completed` - Pipeline execution completed
- `pipeline.failed` - Pipeline execution failed

### Webhook Payload

```json
{
  "event_id": "uuid",
  "event_type": "entry.created",
  "timestamp": "2024-01-01T12:00:00Z",
  "data": {
    // Event-specific data
  },
  "source": "activelog-api"
}
```

### Webhook Security

Webhooks include a signature for verification:

```python
import hmac
import hashlib

def verify_webhook(payload, signature, secret):
    expected = hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(f"sha256={expected}", signature)
```

Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}
"""
        return content

    def _initialize_command_docs(self) -> Dict[str, Any]:
        """Initialize command documentation structure"""
        return {
            'bash': {
                'auth': {
                    'description': 'Authentication management',
                    'usage': 'activelog auth <subcommand>',
                    'subcommands': ['login', 'logout', 'status', 'refresh']
                },
                'entries': {
                    'description': 'Entry management operations',
                    'usage': 'activelog entries <subcommand>',
                    'subcommands': ['list', 'create', 'update', 'delete', 'search']
                },
                'search': {
                    'description': 'Advanced search operations',
                    'usage': 'activelog search <subcommand>',
                    'subcommands': ['semantic', 'similarity', 'tags', 'date-range']
                },
                'export': {
                    'description': 'Data export operations',
                    'usage': 'activelog export <format>',
                    'subcommands': ['json', 'csv', 'markdown', 'pdf']
                },
                'pipeline': {
                    'description': 'Data pipeline management',
                    'usage': 'activelog pipeline <subcommand>',
                    'subcommands': ['create', 'run', 'status', 'logs']
                },
                'webhook': {
                    'description': 'Webhook management',
                    'usage': 'activelog webhook <subcommand>',
                    'subcommands': ['register', 'list', 'delete', 'test']
                },
                'config': {
                    'description': 'Configuration management',
                    'usage': 'activelog config <subcommand>',
                    'subcommands': ['get', 'set', 'list', 'reset']
                }
            },
            'powershell': {
                'Get-ActiveLogEntries': {
                    'description': 'Retrieve ActiveLog entries',
                    'parameters': ['-UserId', '-Limit', '-Tags', '-DateFrom', '-DateTo'],
                    'usage': 'Get-ActiveLogEntries -UserId "user123" -Limit 10'
                },
                'New-ActiveLogEntry': {
                    'description': 'Create new ActiveLog entry',
                    'parameters': ['-Title', '-Content', '-Tags', '-Category'],
                    'usage': 'New-ActiveLogEntry -Title "My Entry" -Content "Content here"'
                }
            }
        }

    def _get_platform_commands(self, platform: str) -> Dict[str, Any]:
        """Get commands for specific platform"""
        if platform == "all":
            return self.command_docs
        else:
            return {k: v for k, v in self.command_docs.items() if k == platform or platform == "all"}

    def _get_platform_list(self, platform: str) -> str:
        """Get formatted platform list"""
        if platform == "all":
            platforms = ["Bash/Zsh", "PowerShell", "Python SDK", "Node.js Client"]
        elif platform == "bash":
            platforms = ["Bash/Zsh"]
        elif platform == "powershell":
            platforms = ["PowerShell"]
        elif platform == "python":
            platforms = ["Python SDK"]
        elif platform == "nodejs":
            platforms = ["Node.js Client"]
        else:
            platforms = [platform.title()]
        
        return "\n".join(f"- {p}" for p in platforms)

    def _get_subcommand_description(self, cmd_name: str, subcmd: str) -> str:
        """Get description for subcommand"""
        descriptions = {
            'auth': {
                'login': 'Authenticate with ActiveLog',
                'logout': 'Sign out of ActiveLog',
                'status': 'Check authentication status',
                'refresh': 'Refresh authentication token'
            },
            'entries': {
                'list': 'List entries with optional filtering',
                'create': 'Create a new entry',
                'update': 'Update an existing entry',
                'delete': 'Delete an entry',
                'search': 'Search entries'
            },
            'search': {
                'semantic': 'Perform semantic search',
                'similarity': 'Find similar entries',
                'tags': 'Search by tags',
                'date-range': 'Search by date range'
            }
        }
        
        return descriptions.get(cmd_name, {}).get(subcmd, 'Command description')

    def _get_command_examples(self, cmd_name: str) -> List[str]:
        """Get examples for command"""
        examples = {
            'auth': [
                'activelog auth login',
                'activelog auth status',
                'activelog auth logout'
            ],
            'entries': [
                'activelog entries list --limit 10',
                'activelog entries create --title "New Entry" --content "Content"',
                'activelog entries update ENTRY_ID --tags "important"'
            ],
            'search': [
                'activelog search semantic "meeting notes"',
                'activelog search tags "important,urgent"',
                'activelog search date-range --days 7'
            ]
        }
        
        return examples.get(cmd_name, [f'activelog {cmd_name}'])

    def _get_installation_data(self, platform: str) -> Dict[str, Any]:
        """Get installation data for documentation"""
        return {
            'bash': {
                'quick_install': 'curl -fsSL https://activelog.com/install.sh | bash',
                'manual_steps': [
                    'Download binary',
                    'Make executable',
                    'Move to PATH',
                    'Set up completion'
                ]
            },
            'powershell': {
                'install_command': 'Install-Module -Name ActiveLog',
                'requirements': ['PowerShell 5.1+']
            }
        }

    def _get_examples_data(self, platform: str) -> Dict[str, Any]:
        """Get examples data for documentation"""
        return {
            'basic_usage': [
                'activelog auth login',
                'activelog entries list',
                'activelog search semantic "query"'
            ],
            'advanced_usage': [
                'Pipeline creation',
                'Webhook integration',
                'Batch processing'
            ]
        }

    def _get_api_data(self, platform: str) -> Dict[str, Any]:
        """Get API data for documentation"""
        return {
            'base_url': 'https://api.activelog.com/v1',
            'authentication': 'Bearer token',
            'endpoints': [
                '/entries',
                '/search',
                '/export',
                '/pipelines',
                '/webhooks'
            ]
        }

    def _markdown_to_html(self, md_path: Path) -> str:
        """Convert markdown to HTML"""
        try:
            # Try using markdown library if available
            try:
                import markdown
                with open(md_path, 'r') as f:
                    md_content = f.read()
                
                html_content = markdown.markdown(md_content, extensions=['codehilite', 'toc'])
                
                # Wrap in HTML template
                return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{md_path.stem.replace('_', ' ').title()} - ActiveLog CLI</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <header>
        <h1>ActiveLog CLI Documentation</h1>
        <nav>
            <a href="index.html">Home</a>
            <a href="README.html">Overview</a>
            <a href="COMMANDS.html">Commands</a>
            <a href="INSTALLATION.html">Installation</a>
            <a href="EXAMPLES.html">Examples</a>
            <a href="API.html">API</a>
        </nav>
    </header>
    <main>
        {html_content}
    </main>
    <footer>
        <p>Generated by ActiveLog CLI Documentation Generator</p>
    </footer>
</body>
</html>"""
                
            except ImportError:
                # Fallback: simple conversion
                with open(md_path, 'r') as f:
                    content = f.read()
                
                # Basic markdown to HTML conversion
                html_content = content.replace('\n# ', '\n<h1>').replace('\n## ', '\n<h2>').replace('\n### ', '\n<h3>')
                html_content = html_content.replace('```', '<pre><code>').replace('```', '</code></pre>')
                
                return f"""<!DOCTYPE html>
<html>
<head><title>{md_path.stem}</title><link rel="stylesheet" href="style.css"></head>
<body>{html_content}</body>
</html>"""
                
        except Exception as e:
            logger.error(f"Failed to convert {md_path} to HTML: {e}")
            return f"<html><body><h1>Error</h1><p>Failed to convert markdown: {e}</p></body></html>"

    def _create_html_index(self, html_files: List[str]) -> str:
        """Create HTML index page"""
        file_links = []
        for file_path in html_files:
            if file_path.endswith('index.html'):
                continue
            
            path = Path(file_path)
            name = path.stem.replace('_', ' ').replace('-', ' ').title()
            file_links.append(f'<li><a href="{path.name}">{name}</a></li>')
        
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ActiveLog CLI Documentation</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <header>
        <h1>ActiveLog CLI Documentation</h1>
    </header>
    <main>
        <h2>Documentation Contents</h2>
        <ul class="doc-index">
            {''.join(file_links)}
        </ul>
        
        <h2>About ActiveLog CLI</h2>
        <p>The ActiveLog CLI provides a comprehensive command-line interface for interacting with ActiveLog services.</p>
        
        <h2>Quick Links</h2>
        <ul>
            <li><a href="README.html">Getting Started</a></li>
            <li><a href="INSTALLATION.html">Installation Guide</a></li>
            <li><a href="COMMANDS.html">Command Reference</a></li>
            <li><a href="EXAMPLES.html">Examples and Tutorials</a></li>
            <li><a href="API.html">API Reference</a></li>
        </ul>
    </main>
    <footer>
        <p>Generated on {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
    </footer>
</body>
</html>"""

    def _create_documentation_css(self) -> str:
        """Create CSS for HTML documentation"""
        return """
/* ActiveLog CLI Documentation Styles */

* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
    line-height: 1.6;
    color: #333;
    background-color: #fff;
    padding: 0;
    margin: 0;
}

header {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 2rem 0;
    margin-bottom: 2rem;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
}

header h1 {
    text-align: center;
    font-size: 2.5rem;
    margin-bottom: 1rem;
}

nav {
    text-align: center;
}

nav a {
    color: white;
    text-decoration: none;
    margin: 0 1rem;
    padding: 0.5rem 1rem;
    border-radius: 4px;
    transition: background-color 0.3s;
}

nav a:hover {
    background-color: rgba(255,255,255,0.2);
}

main {
    max-width: 1200px;
    margin: 0 auto;
    padding: 0 2rem 4rem;
}

h1, h2, h3, h4 {
    margin: 2rem 0 1rem;
    color: #2c3e50;
}

h1 {
    font-size: 2.5rem;
    border-bottom: 3px solid #667eea;
    padding-bottom: 0.5rem;
}

h2 {
    font-size: 2rem;
    border-bottom: 2px solid #ecf0f1;
    padding-bottom: 0.3rem;
}

h3 {
    font-size: 1.5rem;
    color: #34495e;
}

p {
    margin: 1rem 0;
    text-align: justify;
}

ul, ol {
    margin: 1rem 0;
    padding-left: 2rem;
}

li {
    margin: 0.5rem 0;
}

.doc-index {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 1rem;
    margin: 2rem 0;
}

.doc-index li {
    list-style: none;
    background: #f8f9fa;
    border: 1px solid #e9ecef;
    border-radius: 8px;
    padding: 1rem;
    transition: transform 0.2s, box-shadow 0.2s;
}

.doc-index li:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}

.doc-index a {
    text-decoration: none;
    color: #667eea;
    font-weight: 600;
    font-size: 1.1rem;
}

code {
    background: #f1f3f4;
    padding: 0.2rem 0.4rem;
    border-radius: 3px;
    font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
    font-size: 0.9em;
}

pre {
    background: #2d3748;
    color: #e2e8f0;
    padding: 1.5rem;
    border-radius: 8px;
    overflow-x: auto;
    margin: 1.5rem 0;
    border-left: 4px solid #667eea;
}

pre code {
    background: none;
    padding: 0;
    color: inherit;
}

blockquote {
    border-left: 4px solid #667eea;
    background: #f8f9fa;
    padding: 1rem 1.5rem;
    margin: 1.5rem 0;
    border-radius: 0 4px 4px 0;
}

table {
    width: 100%;
    border-collapse: collapse;
    margin: 1.5rem 0;
    background: white;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    border-radius: 8px;
    overflow: hidden;
}

th, td {
    padding: 1rem;
    text-align: left;
    border-bottom: 1px solid #e9ecef;
}

th {
    background: #667eea;
    color: white;
    font-weight: 600;
}

tr:hover {
    background: #f8f9fa;
}

footer {
    background: #2c3e50;
    color: white;
    text-align: center;
    padding: 2rem;
    margin-top: 4rem;
}

/* Responsive design */
@media (max-width: 768px) {
    header h1 {
        font-size: 2rem;
    }
    
    nav a {
        display: block;
        margin: 0.5rem 0;
    }
    
    main {
        padding: 0 1rem 2rem;
    }
    
    .doc-index {
        grid-template-columns: 1fr;
    }
    
    pre {
        padding: 1rem;
        font-size: 0.9rem;
    }
}

/* Code highlighting */
.highlight {
    background: #2d3748;
    color: #e2e8f0;
}

.highlight .k { color: #f7fafc; }
.highlight .s { color: #68d391; }
.highlight .c { color: #a0aec0; }
.highlight .n { color: #e2e8f0; }
"""

    def _create_main_man_page(self, platform: str) -> str:
        """Create main man page"""
        return f'''.TH ACTIVELOG 1 "{datetime.now().strftime('%B %Y')}" "ActiveLog CLI 1.0.0" "User Commands"
.SH NAME
activelog \\- ActiveLog command-line interface
.SH SYNOPSIS
.B activelog
[\\fIOPTIONS\\fR] \\fICOMMAND\\fR [\\fIARGS\\fR...]
.SH DESCRIPTION
The ActiveLog CLI provides a comprehensive command-line interface for interacting with ActiveLog services, managing data, and automating workflows.
.SH OPTIONS
.TP
.BR \\-h ", " \\-\\-help
Show help information and exit.
.TP
.BR \\-v ", " \\-\\-version
Show version information and exit.
.TP
.BR \\-\\-verbose
Enable verbose output.
.TP
.BR \\-\\-config =\\fIFILE\\fR
Use alternative configuration file.
.SH COMMANDS
.TP
.BR auth
Authentication management (login, logout, status)
.TP
.BR entries
Entry management operations (list, create, update, delete)
.TP
.BR search
Advanced search operations (semantic, similarity, tags, date-range)
.TP
.BR export
Data export operations (json, csv, markdown, pdf)
.TP
.BR pipeline
Data pipeline management (create, run, status, logs)
.TP
.BR webhook
Webhook management (register, list, delete, test)
.TP
.BR config
Configuration management (get, set, list, reset)
.SH EXAMPLES
.TP
Login to ActiveLog:
.B activelog auth login
.TP
List recent entries:
.B activelog entries list --limit 10
.TP
Search entries semantically:
.B activelog search semantic "important meeting"
.TP
Export data as JSON:
.B activelog export json output.json
.SH FILES
.TP
.I ~/.config/activelog/config.json
User configuration file
.TP
.I ~/.config/activelog/credentials
Authentication credentials
.TP
.I ~/.config/activelog/activelog.log
Log file
.SH ENVIRONMENT
.TP
.BR ACTIVELOG_API_KEY
API key for authentication
.TP
.BR ACTIVELOG_BASE_URL
Base URL for API endpoints
.TP
.BR ACTIVELOG_CONFIG_DIR
Alternative configuration directory
.SH SEE ALSO
For detailed documentation, visit https://docs.activelog.com
.SH AUTHORS
ActiveLog Development Team
.SH BUGS
Report bugs to https://github.com/activelog/cli/issues
'''

    def _create_command_man_page(self, cmd_name: str, cmd_data: Dict[str, Any]) -> str:
        """Create man page for specific command"""
        return f'''.TH ACTIVELOG-{cmd_name.upper()} 1 "{datetime.now().strftime('%B %Y')}" "ActiveLog CLI 1.0.0" "User Commands"
.SH NAME
activelog-{cmd_name} \\- {cmd_data.get('description', f'ActiveLog {cmd_name} operations')}
.SH SYNOPSIS
.B activelog {cmd_name}
[\\fIOPTIONS\\fR] \\fISUBCOMMAND\\fR [\\fIARGS\\fR...]
.SH DESCRIPTION
{cmd_data.get('description', f'Manage {cmd_name} operations in ActiveLog.')}
.SH SUBCOMMANDS
{self._format_man_subcommands(cmd_data.get('subcommands', []))}
.SH EXAMPLES
{self._format_man_examples(cmd_name)}
.SH SEE ALSO
.BR activelog (1)
'''

    def _format_man_subcommands(self, subcommands: List[str]) -> str:
        """Format subcommands for man page"""
        if not subcommands:
            return "No subcommands available."
        
        return "\n".join(f".TP\n.BR {subcmd}\nSubcommand description" for subcmd in subcommands)

    def _format_man_examples(self, cmd_name: str) -> str:
        """Format examples for man page"""
        examples = self._get_command_examples(cmd_name)
        if not examples:
            return f".B activelog {cmd_name}"
        
        return "\n".join(f".TP\n.B {example}" for example in examples[:3])

    def _combine_html_files(self, html_files: List[str]) -> str:
        """Combine multiple HTML files into one for PDF generation"""
        combined = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>ActiveLog CLI Documentation</title>
    <style>
""" + self._create_documentation_css() + """
    </style>
</head>
<body>
"""
        
        for file_path in html_files:
            if 'index.html' in file_path:
                continue
                
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                
                # Extract content between <main> tags
                import re
                main_match = re.search(r'<main>(.*?)</main>', content, re.DOTALL)
                if main_match:
                    combined += f'<div class="page-break">{main_match.group(1)}</div>'
                
            except Exception as e:
                logger.warning(f"Failed to include {file_path} in combined HTML: {e}")
        
        combined += """
</body>
</html>"""
        
        return combined

    def _create_simple_pdf(self, platform: str) -> bytes:
        """Create simple PDF using reportlab (fallback)"""
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet
            from io import BytesIO
            
            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter)
            styles = getSampleStyleSheet()
            content = []
            
            # Title
            content.append(Paragraph("ActiveLog CLI Documentation", styles['Title']))
            content.append(Spacer(1, 12))
            
            # Content sections
            sections = [
                ("Overview", "The ActiveLog CLI provides comprehensive command-line tools."),
                ("Installation", "Install using curl, pip, npm, or PowerShell."),
                ("Commands", "Available commands include auth, entries, search, export."),
                ("Examples", "Common usage examples and tutorials.")
            ]
            
            for title, text in sections:
                content.append(Paragraph(title, styles['Heading1']))
                content.append(Paragraph(text, styles['Normal']))
                content.append(Spacer(1, 12))
            
            doc.build(content)
            return buffer.getvalue()
            
        except ImportError:
            raise ImportError("reportlab not available for PDF generation")

    def shutdown(self):
        """Shutdown documentation generator"""
        logger.info("Documentation Generator shut down")