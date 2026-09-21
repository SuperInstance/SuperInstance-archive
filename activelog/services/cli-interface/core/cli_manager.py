#!/usr/bin/env python3
"""
CLI Manager - Core component for managing CLI installations and command execution
Handles cross-platform CLI tool management, installation, and execution
"""

import os
import sys
import json
import shutil
import platform
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
import logging
import urllib.request
import tempfile
import zipfile
import tarfile

logger = logging.getLogger(__name__)


class CLIManager:
    """Manages CLI tool installations, updates, and command execution across platforms"""
    
    def __init__(self, config):
        self.config = config
        self.platform = platform.system().lower()
        self.architecture = platform.machine().lower()
        self.cli_root = Path("/home/activeloguser/activelog/services/cli-interface")
        self.bin_dir = self.cli_root / "bin"
        self.sdk_dir = self.cli_root / "sdks"
        self.templates_dir = self.cli_root / "templates"
        
        # Initialize directories
        self.bin_dir.mkdir(exist_ok=True)
        self.sdk_dir.mkdir(exist_ok=True)
        self.templates_dir.mkdir(exist_ok=True)
        
        # CLI installation registry
        self.installations = self._load_installation_registry()
        
        # Platform-specific CLI implementations
        self.platform_handlers = {
            'bash': self._handle_bash_command,
            'zsh': self._handle_zsh_command,
            'powershell': self._handle_powershell_command,
            'fish': self._handle_fish_command,
            'cmd': self._handle_cmd_command
        }
        
        logger.info(f"CLI Manager initialized for {self.platform} ({self.architecture})")

    def install_cli(self, platform: str, install_path: Optional[str] = None) -> Dict[str, Any]:
        """Install CLI tools for specified platform"""
        try:
            if platform == 'bash' or platform == 'zsh':
                return self._install_bash_cli(install_path)
            elif platform == 'powershell':
                return self._install_powershell_cli(install_path)
            elif platform == 'python':
                return self._install_python_sdk(install_path)
            elif platform == 'nodejs':
                return self._install_nodejs_package(install_path)
            else:
                raise ValueError(f"Unsupported platform: {platform}")
                
        except Exception as e:
            logger.error(f"Failed to install CLI for {platform}: {e}")
            return {
                'success': False,
                'error': str(e),
                'platform': platform
            }

    def _install_bash_cli(self, install_path: Optional[str] = None) -> Dict[str, Any]:
        """Install bash/zsh CLI tools"""
        try:
            # Source and target paths
            source_cli = self.bin_dir / "activelog"
            
            if install_path:
                target_path = Path(install_path) / "activelog"
            else:
                # Default installation paths
                if self.platform == 'darwin':  # macOS
                    target_path = Path("/usr/local/bin/activelog")
                else:  # Linux
                    target_path = Path("/usr/local/bin/activelog")
            
            # Copy CLI script
            if source_cli.exists():
                shutil.copy2(source_cli, target_path)
                os.chmod(target_path, 0o755)
            else:
                return {
                    'success': False,
                    'error': 'CLI script not found',
                    'platform': 'bash'
                }
            
            # Create shell completion files
            self._create_bash_completion(target_path.parent)
            
            # Update installation registry
            installation_info = {
                'platform': 'bash',
                'version': '1.0.0',
                'install_path': str(target_path),
                'installed_at': datetime.utcnow().isoformat(),
                'features': [
                    'Command execution',
                    'Auto-completion',
                    'Progress indicators',
                    'JSON output',
                    'Configuration management'
                ]
            }
            self.installations['bash'] = installation_info
            self._save_installation_registry()
            
            return {
                'success': True,
                'platform': 'bash',
                'install_path': str(target_path),
                'version': '1.0.0',
                'message': f'ActiveLog CLI installed successfully at {target_path}'
            }
            
        except Exception as e:
            logger.error(f"Failed to install bash CLI: {e}")
            raise

    def _install_powershell_cli(self, install_path: Optional[str] = None) -> Dict[str, Any]:
        """Install PowerShell cmdlets"""
        try:
            # Create PowerShell module structure
            if install_path:
                module_path = Path(install_path) / "ActiveLog"
            else:
                # Default PowerShell module path
                if self.platform == 'windows':
                    module_path = Path.home() / "Documents" / "WindowsPowerShell" / "Modules" / "ActiveLog"
                else:
                    module_path = Path.home() / ".local" / "share" / "powershell" / "Modules" / "ActiveLog"
            
            module_path.mkdir(parents=True, exist_ok=True)
            
            # Create PowerShell module files
            self._create_powershell_module(module_path)
            
            installation_info = {
                'platform': 'powershell',
                'version': '1.0.0',
                'install_path': str(module_path),
                'installed_at': datetime.utcnow().isoformat(),
                'features': [
                    'PowerShell cmdlets',
                    'Pipeline integration',
                    'Object output',
                    'Help system',
                    'Tab completion'
                ]
            }
            self.installations['powershell'] = installation_info
            self._save_installation_registry()
            
            return {
                'success': True,
                'platform': 'powershell',
                'install_path': str(module_path),
                'version': '1.0.0',
                'message': f'ActiveLog PowerShell module installed at {module_path}'
            }
            
        except Exception as e:
            logger.error(f"Failed to install PowerShell CLI: {e}")
            raise

    def _install_python_sdk(self, install_path: Optional[str] = None) -> Dict[str, Any]:
        """Install Python SDK package"""
        try:
            # Create Python SDK structure
            sdk_path = self.sdk_dir / "python" / "activelog_sdk"
            sdk_path.mkdir(parents=True, exist_ok=True)
            
            # Create Python SDK files
            self._create_python_sdk(sdk_path)
            
            # Create setup.py for installation
            setup_py = sdk_path.parent / "setup.py"
            self._create_python_setup(setup_py, sdk_path)
            
            installation_info = {
                'platform': 'python',
                'version': '1.0.0',
                'install_path': str(sdk_path),
                'installed_at': datetime.utcnow().isoformat(),
                'features': [
                    'Python API client',
                    'Async/sync support',
                    'Type hints',
                    'Error handling',
                    'Authentication'
                ]
            }
            self.installations['python'] = installation_info
            self._save_installation_registry()
            
            return {
                'success': True,
                'platform': 'python',
                'install_path': str(sdk_path),
                'version': '1.0.0',
                'message': f'ActiveLog Python SDK created at {sdk_path}'
            }
            
        except Exception as e:
            logger.error(f"Failed to create Python SDK: {e}")
            raise

    def _install_nodejs_package(self, install_path: Optional[str] = None) -> Dict[str, Any]:
        """Install Node.js package"""
        try:
            # Create Node.js package structure
            package_path = self.sdk_dir / "nodejs" / "activelog-client"
            package_path.mkdir(parents=True, exist_ok=True)
            
            # Create Node.js package files
            self._create_nodejs_package(package_path)
            
            installation_info = {
                'platform': 'nodejs',
                'version': '1.0.0',
                'install_path': str(package_path),
                'installed_at': datetime.utcnow().isoformat(),
                'features': [
                    'Node.js client library',
                    'Promise-based API',
                    'TypeScript support',
                    'Streaming support',
                    'CLI wrapper'
                ]
            }
            self.installations['nodejs'] = installation_info
            self._save_installation_registry()
            
            return {
                'success': True,
                'platform': 'nodejs',
                'install_path': str(package_path),
                'version': '1.0.0',
                'message': f'ActiveLog Node.js package created at {package_path}'
            }
            
        except Exception as e:
            logger.error(f"Failed to create Node.js package: {e}")
            raise

    def get_available_commands(self, platform: str = 'bash') -> Dict[str, Any]:
        """Get list of available CLI commands for platform"""
        try:
            commands = {
                'bash': {
                    'auth': {
                        'description': 'Authentication management',
                        'subcommands': ['login', 'logout', 'status', 'refresh'],
                        'usage': 'activelog auth <subcommand>'
                    },
                    'entries': {
                        'description': 'Entry management operations',
                        'subcommands': ['list', 'create', 'update', 'delete', 'search'],
                        'usage': 'activelog entries <subcommand>'
                    },
                    'search': {
                        'description': 'Advanced search operations',
                        'subcommands': ['semantic', 'similarity', 'tags', 'date-range'],
                        'usage': 'activelog search <subcommand>'
                    },
                    'export': {
                        'description': 'Data export operations',
                        'subcommands': ['json', 'csv', 'markdown', 'pdf'],
                        'usage': 'activelog export <format>'
                    },
                    'pipeline': {
                        'description': 'Data pipeline management',
                        'subcommands': ['create', 'run', 'status', 'logs'],
                        'usage': 'activelog pipeline <subcommand>'
                    },
                    'webhook': {
                        'description': 'Webhook management',
                        'subcommands': ['register', 'list', 'delete', 'test'],
                        'usage': 'activelog webhook <subcommand>'
                    },
                    'config': {
                        'description': 'Configuration management',
                        'subcommands': ['get', 'set', 'list', 'reset'],
                        'usage': 'activelog config <subcommand>'
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
                    },
                    'Search-ActiveLog': {
                        'description': 'Search ActiveLog entries',
                        'parameters': ['-Query', '-Type', '-UserId', '-Limit'],
                        'usage': 'Search-ActiveLog -Query "important meeting" -Type semantic'
                    },
                    'Export-ActiveLogData': {
                        'description': 'Export ActiveLog data',
                        'parameters': ['-Format', '-Output', '-UserId', '-DateRange'],
                        'usage': 'Export-ActiveLogData -Format JSON -Output "export.json"'
                    }
                },
                'python': {
                    'client_usage': {
                        'description': 'Python SDK usage examples',
                        'examples': [
                            'from activelog_sdk import ActiveLogClient',
                            'client = ActiveLogClient(api_key="your_key")',
                            'entries = await client.entries.list(limit=10)',
                            'result = client.search.semantic("query text")'
                        ]
                    }
                },
                'nodejs': {
                    'client_usage': {
                        'description': 'Node.js package usage examples',
                        'examples': [
                            'const { ActiveLogClient } = require("activelog-client")',
                            'const client = new ActiveLogClient({ apiKey: "your_key" })',
                            'const entries = await client.entries.list({ limit: 10 })',
                            'const results = await client.search.semantic("query text")'
                        ]
                    }
                }
            }
            
            return {
                'platform': platform,
                'commands': commands.get(platform, {}),
                'total_commands': len(commands.get(platform, {}))
            }
            
        except Exception as e:
            logger.error(f"Failed to get commands for {platform}: {e}")
            raise

    def execute_command(self, command: str, args: List[str], environment: Dict[str, str] = None) -> Dict[str, Any]:
        """Execute CLI command"""
        try:
            # Determine platform from command context
            platform = self._detect_command_platform(command)
            handler = self.platform_handlers.get(platform, self._handle_bash_command)
            
            return handler(command, args, environment or {})
            
        except Exception as e:
            logger.error(f"Failed to execute command {command}: {e}")
            return {
                'success': False,
                'error': str(e),
                'command': command,
                'args': args
            }

    def _handle_bash_command(self, command: str, args: List[str], env: Dict[str, str]) -> Dict[str, Any]:
        """Handle bash/zsh command execution"""
        try:
            # Build command line
            cmd_parts = ['bash', str(self.bin_dir / 'activelog'), command] + args
            
            # Set up environment
            exec_env = os.environ.copy()
            exec_env.update(env)
            
            # Execute command
            result = subprocess.run(
                cmd_parts,
                capture_output=True,
                text=True,
                env=exec_env,
                timeout=30
            )
            
            return {
                'success': result.returncode == 0,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'return_code': result.returncode,
                'command': ' '.join(cmd_parts)
            }
            
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'error': 'Command timed out after 30 seconds',
                'command': command
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'command': command
            }

    def _handle_zsh_command(self, command: str, args: List[str], env: Dict[str, str]) -> Dict[str, Any]:
        """Handle zsh command execution"""
        # Use same handler as bash for now
        return self._handle_bash_command(command, args, env)

    def _handle_powershell_command(self, command: str, args: List[str], env: Dict[str, str]) -> Dict[str, Any]:
        """Handle PowerShell command execution"""
        try:
            # Map command to PowerShell cmdlet
            ps_cmdlets = {
                'entries list': 'Get-ActiveLogEntries',
                'entries create': 'New-ActiveLogEntry',
                'search semantic': 'Search-ActiveLog -Type semantic',
                'export json': 'Export-ActiveLogData -Format JSON'
            }
            
            cmd_key = f"{command} {args[0] if args else ''}".strip()
            ps_command = ps_cmdlets.get(cmd_key, f'Invoke-ActiveLog -Command "{command}" -Args {args}')
            
            # Execute PowerShell command
            result = subprocess.run(
                ['powershell', '-Command', ps_command],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            return {
                'success': result.returncode == 0,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'return_code': result.returncode,
                'command': ps_command
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'command': command
            }

    def _handle_fish_command(self, command: str, args: List[str], env: Dict[str, str]) -> Dict[str, Any]:
        """Handle fish shell command execution"""
        # Use bash handler for now
        return self._handle_bash_command(command, args, env)

    def _handle_cmd_command(self, command: str, args: List[str], env: Dict[str, str]) -> Dict[str, Any]:
        """Handle Windows CMD command execution"""
        try:
            # Use PowerShell for better functionality on Windows
            return self._handle_powershell_command(command, args, env)
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'command': command
            }

    def get_sdk_download_info(self, language: str, version: str = 'latest') -> Dict[str, Any]:
        """Get SDK download information"""
        try:
            sdk_info = {
                'python': {
                    'package_name': 'activelog-sdk',
                    'install_command': 'pip install activelog-sdk',
                    'import_statement': 'from activelog_sdk import ActiveLogClient',
                    'documentation_url': 'https://docs.activelog.com/sdk/python',
                    'repository_url': 'https://github.com/activelog/python-sdk',
                    'latest_version': '1.0.0'
                },
                'nodejs': {
                    'package_name': 'activelog-client',
                    'install_command': 'npm install activelog-client',
                    'import_statement': 'const { ActiveLogClient } = require("activelog-client")',
                    'documentation_url': 'https://docs.activelog.com/sdk/nodejs',
                    'repository_url': 'https://github.com/activelog/nodejs-client',
                    'latest_version': '1.0.0'
                },
                'go': {
                    'package_name': 'github.com/activelog/go-client',
                    'install_command': 'go get github.com/activelog/go-client',
                    'import_statement': 'import "github.com/activelog/go-client"',
                    'documentation_url': 'https://docs.activelog.com/sdk/go',
                    'repository_url': 'https://github.com/activelog/go-client',
                    'latest_version': '1.0.0'
                },
                'rust': {
                    'package_name': 'activelog-client',
                    'install_command': 'cargo add activelog-client',
                    'import_statement': 'use activelog_client::ActiveLogClient;',
                    'documentation_url': 'https://docs.activelog.com/sdk/rust',
                    'repository_url': 'https://github.com/activelog/rust-client',
                    'latest_version': '1.0.0'
                }
            }
            
            if language not in sdk_info:
                raise ValueError(f"Unsupported language: {language}")
            
            info = sdk_info[language].copy()
            info['language'] = language
            info['requested_version'] = version
            
            return info
            
        except Exception as e:
            logger.error(f"Failed to get SDK info for {language}: {e}")
            raise

    def get_usage_metrics(self, time_range: str = '24h') -> Dict[str, Any]:
        """Get CLI usage metrics and analytics"""
        try:
            # Parse time range
            hours = {'1h': 1, '24h': 24, '7d': 168, '30d': 720}.get(time_range, 24)
            since = datetime.utcnow() - timedelta(hours=hours)
            
            # Mock metrics for now - in production, this would query actual usage data
            metrics = {
                'time_range': time_range,
                'period_start': since.isoformat(),
                'period_end': datetime.utcnow().isoformat(),
                'total_commands': 1250,
                'unique_users': 45,
                'most_used_commands': [
                    {'command': 'entries list', 'count': 320},
                    {'command': 'search semantic', 'count': 280},
                    {'command': 'auth status', 'count': 180},
                    {'command': 'export json', 'count': 150},
                    {'command': 'config get', 'count': 120}
                ],
                'platform_usage': {
                    'bash': 60,
                    'powershell': 25,
                    'python_sdk': 10,
                    'nodejs': 5
                },
                'error_rate': 0.02,
                'avg_response_time_ms': 450,
                'installations': {
                    'total': len(self.installations),
                    'by_platform': {k: 1 for k in self.installations.keys()}
                }
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to get usage metrics: {e}")
            raise

    def _detect_command_platform(self, command: str) -> str:
        """Detect which platform a command should use"""
        # Simple heuristics - in practice this might be more sophisticated
        if command.startswith('Get-') or command.startswith('New-') or command.startswith('Set-'):
            return 'powershell'
        else:
            return 'bash'

    def _load_installation_registry(self) -> Dict[str, Any]:
        """Load CLI installation registry"""
        registry_file = self.cli_root / "installations.json"
        try:
            if registry_file.exists():
                with open(registry_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load installation registry: {e}")
        
        return {}

    def _save_installation_registry(self):
        """Save CLI installation registry"""
        registry_file = self.cli_root / "installations.json"
        try:
            with open(registry_file, 'w') as f:
                json.dump(self.installations, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save installation registry: {e}")

    def _create_bash_completion(self, bin_path: Path):
        """Create bash completion file"""
        completion_content = '''
# ActiveLog CLI completion
_activelog_completion() {
    local cur prev commands
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"
    
    commands="auth entries search export pipeline webhook config help version"
    
    case $prev in
        activelog)
            COMPREPLY=($(compgen -W "$commands" -- "$cur"))
            return 0
            ;;
        auth)
            COMPREPLY=($(compgen -W "login logout status refresh" -- "$cur"))
            return 0
            ;;
        entries)
            COMPREPLY=($(compgen -W "list create update delete search" -- "$cur"))
            return 0
            ;;
        search)
            COMPREPLY=($(compgen -W "semantic similarity tags date-range" -- "$cur"))
            return 0
            ;;
        export)
            COMPREPLY=($(compgen -W "json csv markdown pdf" -- "$cur"))
            return 0
            ;;
        pipeline)
            COMPREPLY=($(compgen -W "create run status logs" -- "$cur"))
            return 0
            ;;
        webhook)
            COMPREPLY=($(compgen -W "register list delete test" -- "$cur"))
            return 0
            ;;
        config)
            COMPREPLY=($(compgen -W "get set list reset" -- "$cur"))
            return 0
            ;;
    esac
}

complete -F _activelog_completion activelog
'''
        
        try:
            completion_file = bin_path.parent / "bash_completion.d" / "activelog"
            completion_file.parent.mkdir(exist_ok=True)
            with open(completion_file, 'w') as f:
                f.write(completion_content)
        except Exception as e:
            logger.warning(f"Failed to create bash completion: {e}")

    def _create_powershell_module(self, module_path: Path):
        """Create PowerShell module files"""
        # Module manifest
        manifest_content = '''@{
    ModuleVersion = '1.0.0'
    GUID = 'a1b2c3d4-e5f6-7890-abcd-ef1234567890'
    Author = 'ActiveLog Team'
    CompanyName = 'ActiveLog'
    Copyright = '(c) 2024 ActiveLog. All rights reserved.'
    Description = 'ActiveLog PowerShell Module for CLI operations'
    PowerShellVersion = '5.1'
    FunctionsToExport = @(
        'Get-ActiveLogEntries',
        'New-ActiveLogEntry', 
        'Search-ActiveLog',
        'Export-ActiveLogData',
        'Connect-ActiveLog',
        'Disconnect-ActiveLog'
    )
    CmdletsToExport = @()
    VariablesToExport = '*'
    AliasesToExport = @()
}'''
        
        # Main module file
        module_content = '''# ActiveLog PowerShell Module
$script:ActiveLogConfig = @{
    BaseUrl = 'http://localhost:8342'
    ApiKey = $null
    Headers = @{}
}

function Connect-ActiveLog {
    param(
        [Parameter(Mandatory=$true)]
        [string]$ApiKey,
        
        [string]$BaseUrl = 'http://localhost:8342'
    )
    
    $script:ActiveLogConfig.ApiKey = $ApiKey
    $script:ActiveLogConfig.BaseUrl = $BaseUrl
    $script:ActiveLogConfig.Headers = @{
        'Authorization' = "Bearer $ApiKey"
        'Content-Type' = 'application/json'
    }
    
    Write-Host "Connected to ActiveLog at $BaseUrl" -ForegroundColor Green
}

function Disconnect-ActiveLog {
    $script:ActiveLogConfig.ApiKey = $null
    $script:ActiveLogConfig.Headers = @{}
    Write-Host "Disconnected from ActiveLog" -ForegroundColor Yellow
}

function Get-ActiveLogEntries {
    param(
        [string]$UserId,
        [int]$Limit = 10,
        [string[]]$Tags,
        [datetime]$DateFrom,
        [datetime]$DateTo
    )
    
    $params = @{}
    if ($UserId) { $params.user_id = $UserId }
    if ($Limit) { $params.limit = $Limit }
    if ($Tags) { $params.tags = $Tags -join ',' }
    if ($DateFrom) { $params.date_from = $DateFrom.ToString('yyyy-MM-dd') }
    if ($DateTo) { $params.date_to = $DateTo.ToString('yyyy-MM-dd') }
    
    $response = Invoke-ActiveLogAPI -Endpoint '/api/entries' -Method GET -Params $params
    return $response
}

function New-ActiveLogEntry {
    param(
        [Parameter(Mandatory=$true)]
        [string]$Title,
        
        [Parameter(Mandatory=$true)]
        [string]$Content,
        
        [string[]]$Tags,
        [string]$Category
    )
    
    $body = @{
        title = $Title
        content = $Content
    }
    if ($Tags) { $body.tags = $Tags }
    if ($Category) { $body.category = $Category }
    
    $response = Invoke-ActiveLogAPI -Endpoint '/api/entries' -Method POST -Body $body
    return $response
}

function Search-ActiveLog {
    param(
        [Parameter(Mandatory=$true)]
        [string]$Query,
        
        [ValidateSet('semantic', 'similarity', 'tags', 'date-range')]
        [string]$Type = 'semantic',
        
        [string]$UserId,
        [int]$Limit = 10
    )
    
    $body = @{
        query = $Query
        type = $Type
        limit = $Limit
    }
    if ($UserId) { $body.user_id = $UserId }
    
    $response = Invoke-ActiveLogAPI -Endpoint '/api/search' -Method POST -Body $body
    return $response
}

function Export-ActiveLogData {
    param(
        [Parameter(Mandatory=$true)]
        [ValidateSet('json', 'csv', 'markdown', 'pdf')]
        [string]$Format,
        
        [Parameter(Mandatory=$true)]
        [string]$Output,
        
        [string]$UserId,
        [string]$DateRange
    )
    
    $body = @{
        format = $Format
        output = $Output
    }
    if ($UserId) { $body.user_id = $UserId }
    if ($DateRange) { $body.date_range = $DateRange }
    
    $response = Invoke-ActiveLogAPI -Endpoint '/api/export' -Method POST -Body $body
    return $response
}

function Invoke-ActiveLogAPI {
    param(
        [string]$Endpoint,
        [string]$Method = 'GET',
        [hashtable]$Params = @{},
        [hashtable]$Body = @{}
    )
    
    if (-not $script:ActiveLogConfig.ApiKey) {
        throw "Not connected to ActiveLog. Use Connect-ActiveLog first."
    }
    
    $uri = "$($script:ActiveLogConfig.BaseUrl)$Endpoint"
    
    if ($Params.Count -gt 0) {
        $queryString = ($Params.GetEnumerator() | ForEach-Object { "$($_.Key)=$($_.Value)" }) -join '&'
        $uri += "?$queryString"
    }
    
    $requestParams = @{
        Uri = $uri
        Method = $Method
        Headers = $script:ActiveLogConfig.Headers
    }
    
    if ($Body.Count -gt 0) {
        $requestParams.Body = $Body | ConvertTo-Json -Depth 10
    }
    
    try {
        $response = Invoke-RestMethod @requestParams
        return $response
    }
    catch {
        Write-Error "API request failed: $($_.Exception.Message)"
        throw
    }
}

Export-ModuleMember -Function Get-ActiveLogEntries, New-ActiveLogEntry, Search-ActiveLog, Export-ActiveLogData, Connect-ActiveLog, Disconnect-ActiveLog
'''
        
        try:
            # Write manifest
            with open(module_path / "ActiveLog.psd1", 'w') as f:
                f.write(manifest_content)
            
            # Write module
            with open(module_path / "ActiveLog.psm1", 'w') as f:
                f.write(module_content)
                
        except Exception as e:
            logger.error(f"Failed to create PowerShell module: {e}")
            raise

    def _create_python_sdk(self, sdk_path: Path):
        """Create Python SDK files"""
        # Main client file
        client_content = '''"""
ActiveLog Python SDK
Official Python client for ActiveLog services
"""

import asyncio
import aiohttp
import requests
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import json


class ActiveLogError(Exception):
    """Base exception for ActiveLog SDK errors"""
    pass


class ActiveLogClient:
    """Main ActiveLog client for API interactions"""
    
    def __init__(self, api_key: str, base_url: str = "http://localhost:8342"):
        self.api_key = api_key
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "ActiveLog-Python-SDK/1.0.0"
        }
        
        # Initialize service clients
        self.entries = EntriesClient(self)
        self.search = SearchClient(self)
        self.export = ExportClient(self)
        self.pipelines = PipelineClient(self)
        self.webhooks = WebhookClient(self)

    def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make synchronous HTTP request"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=self.headers,
                **kwargs
            )
            response.raise_for_status()
            return response.json()
            
        except requests.RequestException as e:
            raise ActiveLogError(f"Request failed: {e}")

    async def _async_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make asynchronous HTTP request"""
        url = f"{self.base_url}{endpoint}"
        
        async with aiohttp.ClientSession(headers=self.headers) as session:
            try:
                async with session.request(method, url, **kwargs) as response:
                    response.raise_for_status()
                    return await response.json()
                    
            except aiohttp.ClientError as e:
                raise ActiveLogError(f"Async request failed: {e}")


class EntriesClient:
    """Client for entry operations"""
    
    def __init__(self, client: ActiveLogClient):
        self.client = client

    def list(self, user_id: Optional[str] = None, limit: int = 10, 
             tags: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """List entries"""
        params = {"limit": limit}
        if user_id:
            params["user_id"] = user_id
        if tags:
            params["tags"] = ",".join(tags)
            
        return self.client._request("GET", "/api/entries", params=params)

    async def list_async(self, user_id: Optional[str] = None, limit: int = 10,
                        tags: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """List entries asynchronously"""
        params = {"limit": limit}
        if user_id:
            params["user_id"] = user_id
        if tags:
            params["tags"] = ",".join(tags)
            
        return await self.client._async_request("GET", "/api/entries", params=params)

    def create(self, title: str, content: str, tags: Optional[List[str]] = None,
               category: Optional[str] = None) -> Dict[str, Any]:
        """Create new entry"""
        data = {"title": title, "content": content}
        if tags:
            data["tags"] = tags
        if category:
            data["category"] = category
            
        return self.client._request("POST", "/api/entries", json=data)

    async def create_async(self, title: str, content: str, tags: Optional[List[str]] = None,
                          category: Optional[str] = None) -> Dict[str, Any]:
        """Create new entry asynchronously"""
        data = {"title": title, "content": content}
        if tags:
            data["tags"] = tags
        if category:
            data["category"] = category
            
        return await self.client._async_request("POST", "/api/entries", json=data)


class SearchClient:
    """Client for search operations"""
    
    def __init__(self, client: ActiveLogClient):
        self.client = client

    def semantic(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Perform semantic search"""
        data = {"query": query, "type": "semantic", "limit": limit}
        return self.client._request("POST", "/api/search", json=data)

    def similarity(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Perform similarity search"""
        data = {"query": query, "type": "similarity", "limit": limit}
        return self.client._request("POST", "/api/search", json=data)

    async def semantic_async(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Perform semantic search asynchronously"""
        data = {"query": query, "type": "semantic", "limit": limit}
        return await self.client._async_request("POST", "/api/search", json=data)


class ExportClient:
    """Client for export operations"""
    
    def __init__(self, client: ActiveLogClient):
        self.client = client

    def json(self, output_path: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Export data as JSON"""
        data = {"format": "json", "output": output_path}
        if user_id:
            data["user_id"] = user_id
            
        return self.client._request("POST", "/api/export", json=data)

    def csv(self, output_path: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Export data as CSV"""
        data = {"format": "csv", "output": output_path}
        if user_id:
            data["user_id"] = user_id
            
        return self.client._request("POST", "/api/export", json=data)


class PipelineClient:
    """Client for pipeline operations"""
    
    def __init__(self, client: ActiveLogClient):
        self.client = client

    def create(self, pipeline_config: Dict[str, Any]) -> str:
        """Create new pipeline"""
        response = self.client._request("POST", "/pipelines/create", json=pipeline_config)
        return response.get("pipeline_id")

    def execute(self, pipeline_id: str, data: Optional[Dict[str, Any]] = None) -> str:
        """Execute pipeline"""
        response = self.client._request("POST", f"/pipelines/{pipeline_id}/execute", json=data or {})
        return response.get("execution_id")


class WebhookClient:
    """Client for webhook operations"""
    
    def __init__(self, client: ActiveLogClient):
        self.client = client

    def register(self, webhook_config: Dict[str, Any]) -> Dict[str, Any]:
        """Register new webhook"""
        return self.client._request("POST", "/webhooks/register", json=webhook_config)

    def list(self) -> List[Dict[str, Any]]:
        """List all webhooks"""
        return self.client._request("GET", "/webhooks")


# Convenience functions for quick usage
def create_client(api_key: str, base_url: str = "http://localhost:8342") -> ActiveLogClient:
    """Create ActiveLog client instance"""
    return ActiveLogClient(api_key, base_url)


async def quick_search(api_key: str, query: str, search_type: str = "semantic") -> List[Dict[str, Any]]:
    """Quick async search function"""
    client = ActiveLogClient(api_key)
    if search_type == "semantic":
        return await client.search.semantic_async(query)
    else:
        return await client.search.similarity_async(query)
'''
        
        # __init__.py file
        init_content = '''"""ActiveLog Python SDK"""

from .client import (
    ActiveLogClient,
    ActiveLogError,
    create_client,
    quick_search
)

__version__ = "1.0.0"
__all__ = ["ActiveLogClient", "ActiveLogError", "create_client", "quick_search"]
'''
        
        try:
            # Write main client
            with open(sdk_path / "client.py", 'w') as f:
                f.write(client_content)
            
            # Write __init__.py
            with open(sdk_path / "__init__.py", 'w') as f:
                f.write(init_content)
                
        except Exception as e:
            logger.error(f"Failed to create Python SDK: {e}")
            raise

    def _create_python_setup(self, setup_path: Path, sdk_path: Path):
        """Create setup.py for Python SDK"""
        setup_content = '''from setuptools import setup, find_packages

setup(
    name="activelog-sdk",
    version="1.0.0",
    author="ActiveLog Team",
    author_email="sdk@activelog.com",
    description="Official Python SDK for ActiveLog services",
    long_description=open("README.md").read() if os.path.exists("README.md") else "",
    long_description_content_type="text/markdown",
    url="https://github.com/activelog/python-sdk",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        "requests>=2.28.0",
        "aiohttp>=3.8.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.20.0",
            "black>=22.0.0",
            "isort>=5.10.0",
            "mypy>=1.0.0",
        ]
    },
)
'''
        
        try:
            with open(setup_path, 'w') as f:
                f.write(setup_content)
        except Exception as e:
            logger.error(f"Failed to create Python setup.py: {e}")
            raise

    def _create_nodejs_package(self, package_path: Path):
        """Create Node.js package files"""
        # package.json
        package_json = {
            "name": "activelog-client",
            "version": "1.0.0",
            "description": "Official Node.js client for ActiveLog services",
            "main": "lib/index.js",
            "types": "lib/index.d.ts",
            "scripts": {
                "build": "tsc",
                "test": "jest",
                "lint": "eslint src/**/*.ts",
                "format": "prettier --write src/**/*.ts"
            },
            "keywords": ["activelog", "logging", "api", "client"],
            "author": "ActiveLog Team",
            "license": "MIT",
            "dependencies": {
                "axios": "^1.5.0",
                "ws": "^8.14.0"
            },
            "devDependencies": {
                "@types/node": "^20.0.0",
                "@types/ws": "^8.5.0",
                "typescript": "^5.0.0",
                "jest": "^29.0.0",
                "@types/jest": "^29.0.0",
                "eslint": "^8.0.0",
                "prettier": "^3.0.0"
            }
        }
        
        # Main client file
        client_content = '''import axios, { AxiosInstance, AxiosResponse } from 'axios';
import WebSocket from 'ws';

export interface ActiveLogConfig {
  apiKey: string;
  baseUrl?: string;
  timeout?: number;
}

export interface Entry {
  id: string;
  title: string;
  content: string;
  tags?: string[];
  category?: string;
  created_at: string;
  updated_at: string;
}

export interface SearchResult {
  entries: Entry[];
  total: number;
  query: string;
  type: string;
}

export interface PipelineConfig {
  name: string;
  steps: any[];
  triggers?: any[];
}

export interface WebhookConfig {
  url: string;
  events: string[];
  secret?: string;
}

export class ActiveLogClient {
  private http: AxiosInstance;
  private config: Required<ActiveLogConfig>;

  constructor(config: ActiveLogConfig) {
    this.config = {
      apiKey: config.apiKey,
      baseUrl: config.baseUrl || 'http://localhost:8342',
      timeout: config.timeout || 30000
    };

    this.http = axios.create({
      baseURL: this.config.baseUrl,
      timeout: this.config.timeout,
      headers: {
        'Authorization': `Bearer ${this.config.apiKey}`,
        'Content-Type': 'application/json',
        'User-Agent': 'ActiveLog-Node-Client/1.0.0'
      }
    });

    // Add response interceptor for error handling
    this.http.interceptors.response.use(
      (response) => response,
      (error) => {
        throw new ActiveLogError(
          error.response?.data?.error || error.message,
          error.response?.status
        );
      }
    );
  }

  // Entry operations
  async getEntries(params?: {
    userId?: string;
    limit?: number;
    tags?: string[];
  }): Promise<Entry[]> {
    const response = await this.http.get('/api/entries', { params });
    return response.data;
  }

  async createEntry(entry: {
    title: string;
    content: string;
    tags?: string[];
    category?: string;
  }): Promise<Entry> {
    const response = await this.http.post('/api/entries', entry);
    return response.data;
  }

  async updateEntry(id: string, updates: Partial<Entry>): Promise<Entry> {
    const response = await this.http.put(`/api/entries/${id}`, updates);
    return response.data;
  }

  async deleteEntry(id: string): Promise<void> {
    await this.http.delete(`/api/entries/${id}`);
  }

  // Search operations
  async searchSemantic(query: string, limit: number = 10): Promise<SearchResult> {
    const response = await this.http.post('/api/search', {
      query,
      type: 'semantic',
      limit
    });
    return response.data;
  }

  async searchSimilarity(query: string, limit: number = 10): Promise<SearchResult> {
    const response = await this.http.post('/api/search', {
      query,
      type: 'similarity',
      limit
    });
    return response.data;
  }

  // Export operations
  async exportData(format: 'json' | 'csv' | 'markdown' | 'pdf', output: string, userId?: string): Promise<any> {
    const response = await this.http.post('/api/export', {
      format,
      output,
      user_id: userId
    });
    return response.data;
  }

  // Pipeline operations
  async createPipeline(config: PipelineConfig): Promise<string> {
    const response = await this.http.post('/pipelines/create', config);
    return response.data.pipeline_id;
  }

  async executePipeline(pipelineId: string, data?: any): Promise<string> {
    const response = await this.http.post(`/pipelines/${pipelineId}/execute`, data || {});
    return response.data.execution_id;
  }

  // Webhook operations
  async registerWebhook(config: WebhookConfig): Promise<any> {
    const response = await this.http.post('/webhooks/register', config);
    return response.data;
  }

  async listWebhooks(): Promise<any[]> {
    const response = await this.http.get('/webhooks');
    return response.data;
  }

  // Real-time streaming
  createEventStream(subscriptionConfig: any): WebSocket {
    const wsUrl = this.config.baseUrl.replace('http', 'ws') + '/streaming/events';
    const ws = new WebSocket(wsUrl, {
      headers: {
        'Authorization': `Bearer ${this.config.apiKey}`
      }
    });

    ws.on('open', () => {
      ws.send(JSON.stringify(subscriptionConfig));
    });

    return ws;
  }

  // Batch operations
  async submitBatchJob(jobConfig: any): Promise<string> {
    const response = await this.http.post('/batch/submit', jobConfig);
    return response.data.job_id;
  }

  async getBatchStatus(jobId: string): Promise<any> {
    const response = await this.http.get(`/batch/status/${jobId}`);
    return response.data;
  }

  // Utility methods
  async healthCheck(): Promise<any> {
    const response = await this.http.get('/health');
    return response.data;
  }

  async getUsageMetrics(timeRange: string = '24h'): Promise<any> {
    const response = await this.http.get('/metrics/usage', {
      params: { time_range: timeRange }
    });
    return response.data;
  }
}

export class ActiveLogError extends Error {
  public statusCode?: number;

  constructor(message: string, statusCode?: number) {
    super(message);
    this.name = 'ActiveLogError';
    this.statusCode = statusCode;
  }
}

// Convenience factory function
export function createClient(config: ActiveLogConfig): ActiveLogClient {
  return new ActiveLogClient(config);
}

// Quick utility functions
export async function quickSearch(apiKey: string, query: string, type: 'semantic' | 'similarity' = 'semantic'): Promise<SearchResult> {
  const client = new ActiveLogClient({ apiKey });
  return type === 'semantic' 
    ? await client.searchSemantic(query)
    : await client.searchSimilarity(query);
}

export async function quickCreateEntry(apiKey: string, title: string, content: string): Promise<Entry> {
  const client = new ActiveLogClient({ apiKey });
  return await client.createEntry({ title, content });
}
'''
        
        # TypeScript config
        tsconfig = {
            "compilerOptions": {
                "target": "ES2020",
                "module": "commonjs",
                "lib": ["ES2020"],
                "outDir": "./lib",
                "rootDir": "./src",
                "strict": True,
                "esModuleInterop": True,
                "skipLibCheck": True,
                "forceConsistentCasingInFileNames": True,
                "declaration": True,
                "declarationMap": True,
                "sourceMap": True
            },
            "include": ["src/**/*"],
            "exclude": ["node_modules", "lib", "**/*.test.ts"]
        }
        
        try:
            # Create directories
            src_dir = package_path / "src"
            src_dir.mkdir(exist_ok=True)
            
            # Write package.json
            with open(package_path / "package.json", 'w') as f:
                json.dump(package_json, f, indent=2)
            
            # Write main client file
            with open(src_dir / "index.ts", 'w') as f:
                f.write(client_content)
            
            # Write TypeScript config
            with open(package_path / "tsconfig.json", 'w') as f:
                json.dump(tsconfig, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to create Node.js package: {e}")
            raise