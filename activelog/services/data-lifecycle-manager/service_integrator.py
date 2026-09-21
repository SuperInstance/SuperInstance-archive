#!/usr/bin/env python3
"""
Service Integration Layer for SuperInstance Ecosystem
===================================================

Integration with all 40+ services:
- Connect to all services in /home/activeloguser/activelog/services/
- Monitor log files, databases, ML models, cache files
- Intelligent cleanup of temporary files and outdated data
- Service-specific data value assessment
- Cross-service data deduplication
- Building bots network mission integration
"""

import os
import json
import sqlite3
import logging
import asyncio
import aiohttp
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any, Set
from dataclasses import dataclass, asdict
from pathlib import Path
import hashlib
import psutil
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import yaml
import configparser

logger = logging.getLogger(__name__)

@dataclass
class ServiceInfo:
    """Information about a discovered service"""
    name: str
    path: str
    service_type: str  # python, node, java, etc.
    main_file: Optional[str]
    config_files: List[str]
    log_files: List[str]
    data_files: List[str]
    temp_files: List[str]
    cache_files: List[str]
    ml_models: List[str]
    databases: List[str]
    port: Optional[int]
    status: str  # running, stopped, unknown
    pid: Optional[int]
    memory_usage_mb: float = 0.0
    cpu_percent: float = 0.0
    last_accessed: Optional[datetime] = None
    data_value_score: float = 0.0

@dataclass
class ServiceDataPattern:
    """Data pattern for a specific service"""
    service_name: str
    typical_log_size_mb: float
    log_rotation_frequency: str
    cache_retention_hours: int
    temp_file_patterns: List[str]
    backup_frequency: str
    ml_model_update_frequency: str
    database_growth_rate_mb_per_day: float
    importance_score: float  # 0.0 to 1.0

class ServiceDiscovery:
    """Discovers and analyzes services in the ecosystem"""
    
    def __init__(self, base_path: str = "/home/activeloguser/activelog/services"):
        self.base_path = Path(base_path)
        self.services: Dict[str, ServiceInfo] = {}
        self.service_patterns: Dict[str, ServiceDataPattern] = {}
        self.discovery_cache_file = "service_discovery_cache.json"
        
    def discover_all_services(self) -> Dict[str, ServiceInfo]:
        """Discover all services in the ecosystem"""
        logger.info(f"Discovering services in {self.base_path}")
        
        if not self.base_path.exists():
            logger.error(f"Base path {self.base_path} does not exist")
            return {}
        
        # Load cache if exists
        self._load_discovery_cache()
        
        discovered_services = {}
        
        # Parallel discovery for performance
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            
            for item in self.base_path.iterdir():
                if item.is_dir() and not item.name.startswith('.'):
                    future = executor.submit(self._analyze_service_directory, item)
                    futures.append((item.name, future))
            
            for service_name, future in futures:
                try:
                    service_info = future.result(timeout=30)
                    if service_info:
                        discovered_services[service_name] = service_info
                except Exception as e:
                    logger.warning(f"Failed to analyze service {service_name}: {e}")
        
        self.services = discovered_services
        self._save_discovery_cache()
        
        logger.info(f"Discovered {len(discovered_services)} services")
        return discovered_services
    
    def _analyze_service_directory(self, service_path: Path) -> Optional[ServiceInfo]:
        """Analyze a single service directory"""
        try:
            service_name = service_path.name
            
            # Determine service type and main file
            service_type, main_file = self._determine_service_type(service_path)
            
            # Find various file types
            config_files = self._find_files_by_patterns(service_path, ['*.json', '*.yaml', '*.yml', '*.ini', '*.conf', '*.env'])
            log_files = self._find_files_by_patterns(service_path, ['*.log', '*.out', '*.err'])
            temp_files = self._find_files_by_patterns(service_path, ['*.tmp', '*.temp', '*.bak', '*.swp'])
            cache_files = self._find_files_by_patterns(service_path, ['*.cache', '*cache*'])
            ml_models = self._find_files_by_patterns(service_path, ['*.model', '*.pkl', '*.h5', '*.pt', '*.pth', '*.onnx'])
            databases = self._find_files_by_patterns(service_path, ['*.db', '*.sqlite', '*.sqlite3'])
            
            # Find data files (non-executable files)
            data_patterns = ['*.csv', '*.json', '*.xml', '*.txt', '*.md']
            data_files = self._find_files_by_patterns(service_path, data_patterns)
            
            # Get running status
            port, pid, status = self._get_service_status(service_name, main_file)
            
            # Get resource usage if running
            memory_usage, cpu_percent = self._get_resource_usage(pid) if pid else (0.0, 0.0)
            
            # Calculate last accessed time
            last_accessed = self._get_last_accessed_time(service_path)
            
            service_info = ServiceInfo(
                name=service_name,
                path=str(service_path),
                service_type=service_type,
                main_file=main_file,
                config_files=config_files,
                log_files=log_files,
                data_files=data_files,
                temp_files=temp_files,
                cache_files=cache_files,
                ml_models=ml_models,
                databases=databases,
                port=port,
                status=status,
                pid=pid,
                memory_usage_mb=memory_usage,
                cpu_percent=cpu_percent,
                last_accessed=last_accessed
            )
            
            return service_info
            
        except Exception as e:
            logger.warning(f"Error analyzing service {service_path.name}: {e}")
            return None
    
    def _determine_service_type(self, service_path: Path) -> Tuple[str, Optional[str]]:
        """Determine service type and main file"""
        main_files = {
            'python': ['main.py', 'app.py', 'server.py', 'run.py'],
            'node': ['server.js', 'index.js', 'app.js', 'main.js'],
            'java': ['Main.java', 'Application.java'],
            'shell': ['start.sh', 'run.sh', 'main.sh']
        }
        
        # Check for package.json (Node.js)
        if (service_path / 'package.json').exists():
            for main_file in main_files['node']:
                if (service_path / main_file).exists():
                    return 'node', main_file
            return 'node', 'index.js'  # Default
        
        # Check for Python files
        for main_file in main_files['python']:
            if (service_path / main_file).exists():
                return 'python', main_file
        
        # Check for Java files
        java_files = list(service_path.rglob('*.java'))
        if java_files:
            for main_file in main_files['java']:
                if (service_path / main_file).exists():
                    return 'java', main_file
            return 'java', java_files[0].name
        
        # Check for shell scripts
        for main_file in main_files['shell']:
            if (service_path / main_file).exists():
                return 'shell', main_file
        
        # Check for Dockerfile
        if (service_path / 'Dockerfile').exists():
            return 'docker', 'Dockerfile'
        
        return 'unknown', None
    
    def _find_files_by_patterns(self, service_path: Path, patterns: List[str]) -> List[str]:
        """Find files matching patterns"""
        found_files = []
        for pattern in patterns:
            found_files.extend([str(f) for f in service_path.rglob(pattern) if f.is_file()])
        return found_files
    
    def _get_service_status(self, service_name: str, main_file: Optional[str]) -> Tuple[Optional[int], Optional[int], str]:
        """Get service running status"""
        port = None
        pid = None
        status = 'unknown'
        
        try:
            # Look for running processes
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    proc_info = proc.info
                    cmdline = ' '.join(proc_info['cmdline']) if proc_info['cmdline'] else ''
                    
                    # Check if this process is running our service
                    if (service_name in cmdline or 
                        (main_file and main_file in cmdline)):
                        pid = proc_info['pid']
                        status = 'running'
                        
                        # Try to extract port from command line
                        port = self._extract_port_from_cmdline(cmdline)
                        break
                        
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            if status == 'unknown':
                status = 'stopped'
                
        except Exception as e:
            logger.debug(f"Error checking status for {service_name}: {e}")
            status = 'unknown'
        
        return port, pid, status
    
    def _extract_port_from_cmdline(self, cmdline: str) -> Optional[int]:
        """Extract port number from command line"""
        import re
        
        # Common port patterns
        patterns = [
            r'--port[=\s]+(\d+)',
            r'-p[=\s]+(\d+)',
            r'PORT[=\s]+(\d+)',
            r':(\d{4,5})',  # Port in URL format
        ]
        
        for pattern in patterns:
            match = re.search(pattern, cmdline, re.IGNORECASE)
            if match:
                try:
                    return int(match.group(1))
                except ValueError:
                    continue
        
        return None
    
    def _get_resource_usage(self, pid: int) -> Tuple[float, float]:
        """Get resource usage for a process"""
        try:
            process = psutil.Process(pid)
            memory_mb = process.memory_info().rss / (1024 * 1024)
            cpu_percent = process.cpu_percent()
            return memory_mb, cpu_percent
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return 0.0, 0.0
    
    def _get_last_accessed_time(self, service_path: Path) -> Optional[datetime]:
        """Get last accessed time for service files"""
        try:
            latest_access = None
            for file_path in service_path.rglob('*'):
                if file_path.is_file():
                    try:
                        access_time = datetime.fromtimestamp(file_path.stat().st_atime)
                        if latest_access is None or access_time > latest_access:
                            latest_access = access_time
                    except (OSError, PermissionError):
                        continue
            return latest_access
        except Exception:
            return None
    
    def _load_discovery_cache(self):
        """Load service discovery cache"""
        cache_file = Path(self.discovery_cache_file)
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    cache_data = json.load(f)
                    # Convert to ServiceInfo objects
                    for name, data in cache_data.get('services', {}).items():
                        # Convert datetime strings back to datetime objects
                        if data.get('last_accessed'):
                            data['last_accessed'] = datetime.fromisoformat(data['last_accessed'])
                        self.services[name] = ServiceInfo(**data)
                    logger.info(f"Loaded {len(self.services)} services from cache")
            except Exception as e:
                logger.warning(f"Error loading discovery cache: {e}")
    
    def _save_discovery_cache(self):
        """Save service discovery cache"""
        try:
            cache_data = {
                'timestamp': datetime.now().isoformat(),
                'services': {}
            }
            
            for name, service in self.services.items():
                service_dict = asdict(service)
                # Convert datetime to string for JSON serialization
                if service_dict['last_accessed']:
                    service_dict['last_accessed'] = service_dict['last_accessed'].isoformat()
                cache_data['services'][name] = service_dict
            
            with open(self.discovery_cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
                
        except Exception as e:
            logger.warning(f"Error saving discovery cache: {e}")

class ServiceDataManager:
    """Manages data across all services"""
    
    def __init__(self, service_discovery: ServiceDiscovery):
        self.discovery = service_discovery
        self.cleanup_strategies = self._initialize_cleanup_strategies()
        self.deduplication_cache = {}
        
    def _initialize_cleanup_strategies(self) -> Dict[str, Dict[str, Any]]:
        """Initialize service-specific cleanup strategies"""
        return {
            # Core system services - high value, conservative cleanup
            'dmlog-core': {
                'log_retention_days': 30,
                'temp_retention_hours': 24,
                'cache_retention_hours': 72,
                'importance': 0.9
            },
            'ai-insights': {
                'log_retention_days': 21,
                'temp_retention_hours': 12,
                'cache_retention_hours': 48,
                'importance': 0.85
            },
            'bot-ecosystem': {
                'log_retention_days': 14,
                'temp_retention_hours': 6,
                'cache_retention_hours': 24,
                'importance': 0.8
            },
            
            # ML and training services
            'ml-platform': {
                'log_retention_days': 14,
                'temp_retention_hours': 2,
                'cache_retention_hours': 12,
                'model_retention_days': 60,
                'importance': 0.85
            },
            'adaptive-cv-training': {
                'log_retention_days': 7,
                'temp_retention_hours': 1,
                'cache_retention_hours': 6,
                'model_retention_days': 30,
                'importance': 0.7
            },
            
            # Development and testing services
            'dev-sandbox': {
                'log_retention_days': 3,
                'temp_retention_hours': 0.5,
                'cache_retention_hours': 2,
                'importance': 0.3
            },
            'game-dev-mode': {
                'log_retention_days': 7,
                'temp_retention_hours': 2,
                'cache_retention_hours': 8,
                'importance': 0.4
            },
            
            # Backup and sync services
            'backup-dr': {
                'log_retention_days': 60,
                'temp_retention_hours': 1,
                'cache_retention_hours': 4,
                'importance': 0.9
            },
            'file-sync': {
                'log_retention_days': 14,
                'temp_retention_hours': 0.25,
                'cache_retention_hours': 1,
                'importance': 0.6
            },
            
            # Default strategy for unknown services
            'default': {
                'log_retention_days': 7,
                'temp_retention_hours': 2,
                'cache_retention_hours': 8,
                'importance': 0.5
            }
        }
    
    def analyze_service_data_patterns(self, service_name: str) -> ServiceDataPattern:
        """Analyze data patterns for a specific service"""
        if service_name not in self.discovery.services:
            logger.warning(f"Service {service_name} not found")
            return self._get_default_pattern(service_name)
        
        service = self.discovery.services[service_name]
        strategy = self.cleanup_strategies.get(service_name, self.cleanup_strategies['default'])
        
        # Calculate typical log size
        log_sizes = []
        for log_file in service.log_files:
            try:
                size_mb = Path(log_file).stat().st_size / (1024 * 1024)
                log_sizes.append(size_mb)
            except (OSError, FileNotFoundError):
                continue
        
        typical_log_size = sum(log_sizes) / len(log_sizes) if log_sizes else 0.0
        
        # Analyze database growth (simplified)
        db_growth_rate = 0.0
        if service.databases:
            # This would ideally track database size over time
            # For now, estimate based on current size and service type
            total_db_size = sum(
                Path(db).stat().st_size / (1024 * 1024)
                for db in service.databases
                if Path(db).exists()
            )
            
            # Estimate growth rate based on service type
            if 'ml' in service_name.lower() or 'training' in service_name.lower():
                db_growth_rate = total_db_size * 0.1  # 10% per day for ML services
            elif 'log' in service_name.lower():
                db_growth_rate = total_db_size * 0.05  # 5% per day for logging services
            else:
                db_growth_rate = total_db_size * 0.02  # 2% per day for other services
        
        # Determine temp file patterns
        temp_patterns = []
        for temp_file in service.temp_files:
            pattern = Path(temp_file).suffix or '*'
            if pattern not in temp_patterns:
                temp_patterns.append(pattern)
        
        return ServiceDataPattern(
            service_name=service_name,
            typical_log_size_mb=typical_log_size,
            log_rotation_frequency='daily' if typical_log_size > 10 else 'weekly',
            cache_retention_hours=strategy['cache_retention_hours'],
            temp_file_patterns=temp_patterns,
            backup_frequency='daily' if strategy['importance'] > 0.7 else 'weekly',
            ml_model_update_frequency='weekly' if 'ml' in service_name.lower() else 'monthly',
            database_growth_rate_mb_per_day=db_growth_rate,
            importance_score=strategy['importance']
        )
    
    def _get_default_pattern(self, service_name: str) -> ServiceDataPattern:
        """Get default pattern for unknown services"""
        return ServiceDataPattern(
            service_name=service_name,
            typical_log_size_mb=1.0,
            log_rotation_frequency='weekly',
            cache_retention_hours=8,
            temp_file_patterns=['*.tmp'],
            backup_frequency='weekly',
            ml_model_update_frequency='monthly',
            database_growth_rate_mb_per_day=0.1,
            importance_score=0.5
        )
    
    def cleanup_service_data(self, service_name: str, aggressive: bool = False) -> Dict[str, Any]:
        """Clean up data for a specific service"""
        if service_name not in self.discovery.services:
            return {'error': f'Service {service_name} not found'}
        
        service = self.discovery.services[service_name]
        strategy = self.cleanup_strategies.get(service_name, self.cleanup_strategies['default'])
        pattern = self.analyze_service_data_patterns(service_name)
        
        cleanup_results = {
            'service_name': service_name,
            'files_deleted': 0,
            'bytes_freed': 0,
            'actions_taken': []
        }
        
        # Adjust retention based on aggressiveness
        multiplier = 0.5 if aggressive else 1.0
        log_retention_days = int(strategy['log_retention_days'] * multiplier)
        temp_retention_hours = strategy['temp_retention_hours'] * multiplier
        cache_retention_hours = strategy['cache_retention_hours'] * multiplier
        
        now = datetime.now()
        
        # Clean up log files
        for log_file_path in service.log_files:
            try:
                log_path = Path(log_file_path)
                if not log_path.exists():
                    continue
                
                # Check age
                modified_time = datetime.fromtimestamp(log_path.stat().st_mtime)
                age_days = (now - modified_time).days
                
                if age_days > log_retention_days:
                    size_bytes = log_path.stat().st_size
                    log_path.unlink()
                    cleanup_results['files_deleted'] += 1
                    cleanup_results['bytes_freed'] += size_bytes
                    cleanup_results['actions_taken'].append(f"Deleted old log: {log_path.name}")
                    
            except Exception as e:
                logger.warning(f"Error cleaning log file {log_file_path}: {e}")
        
        # Clean up temp files
        for temp_file_path in service.temp_files:
            try:
                temp_path = Path(temp_file_path)
                if not temp_path.exists():
                    continue
                
                modified_time = datetime.fromtimestamp(temp_path.stat().st_mtime)
                age_hours = (now - modified_time).total_seconds() / 3600
                
                if age_hours > temp_retention_hours:
                    size_bytes = temp_path.stat().st_size
                    temp_path.unlink()
                    cleanup_results['files_deleted'] += 1
                    cleanup_results['bytes_freed'] += size_bytes
                    cleanup_results['actions_taken'].append(f"Deleted temp file: {temp_path.name}")
                    
            except Exception as e:
                logger.warning(f"Error cleaning temp file {temp_file_path}: {e}")
        
        # Clean up cache files
        for cache_file_path in service.cache_files:
            try:
                cache_path = Path(cache_file_path)
                if not cache_path.exists():
                    continue
                
                modified_time = datetime.fromtimestamp(cache_path.stat().st_mtime)
                age_hours = (now - modified_time).total_seconds() / 3600
                
                if age_hours > cache_retention_hours:
                    size_bytes = cache_path.stat().st_size
                    cache_path.unlink()
                    cleanup_results['files_deleted'] += 1
                    cleanup_results['bytes_freed'] += size_bytes
                    cleanup_results['actions_taken'].append(f"Deleted cache file: {cache_path.name}")
                    
            except Exception as e:
                logger.warning(f"Error cleaning cache file {cache_file_path}: {e}")
        
        return cleanup_results
    
    def cross_service_deduplication(self, services: List[str] = None) -> Dict[str, Any]:
        """Perform cross-service data deduplication"""
        target_services = services or list(self.discovery.services.keys())
        
        # Collect all files with their hashes
        file_hashes = defaultdict(list)  # hash -> [(service, file_path, size), ...]
        total_scanned = 0
        
        for service_name in target_services:
            if service_name not in self.discovery.services:
                continue
                
            service = self.discovery.services[service_name]
            
            # Check data files and config files for duplicates
            files_to_check = service.data_files + service.config_files
            
            for file_path in files_to_check:
                try:
                    path = Path(file_path)
                    if not path.exists() or path.stat().st_size > 100 * 1024 * 1024:  # Skip files > 100MB
                        continue
                    
                    file_hash = self._calculate_file_hash(path)
                    file_size = path.stat().st_size
                    
                    file_hashes[file_hash].append((service_name, str(path), file_size))
                    total_scanned += 1
                    
                except Exception as e:
                    logger.debug(f"Error processing file {file_path}: {e}")
        
        # Find duplicates and remove them
        duplicates_found = []
        total_freed_bytes = 0
        files_removed = 0
        
        for file_hash, file_list in file_hashes.items():
            if len(file_list) > 1:  # Duplicates found
                # Sort by importance (keep file from most important service)
                file_list.sort(key=lambda x: self.cleanup_strategies.get(x[0], self.cleanup_strategies['default'])['importance'], reverse=True)
                
                # Keep the first file, remove others
                keep_service, keep_path, keep_size = file_list[0]
                duplicates_to_remove = file_list[1:]
                
                duplicate_info = {
                    'hash': file_hash,
                    'kept_file': {'service': keep_service, 'path': keep_path, 'size': keep_size},
                    'removed_files': []
                }
                
                for service, path, size in duplicates_to_remove:
                    try:
                        Path(path).unlink()
                        duplicate_info['removed_files'].append({'service': service, 'path': path, 'size': size})
                        total_freed_bytes += size
                        files_removed += 1
                    except Exception as e:
                        logger.warning(f"Error removing duplicate file {path}: {e}")
                
                if duplicate_info['removed_files']:  # Only add if we actually removed files
                    duplicates_found.append(duplicate_info)
        
        return {
            'total_files_scanned': total_scanned,
            'duplicate_groups_found': len(duplicates_found),
            'files_removed': files_removed,
            'bytes_freed': total_freed_bytes,
            'bytes_freed_mb': total_freed_bytes / (1024 * 1024),
            'duplicate_details': duplicates_found[:10]  # Limit details for performance
        }
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of file contents"""
        hash_sha256 = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception:
            # Fallback to path-based hash if file can't be read
            return hashlib.sha256(str(file_path).encode()).hexdigest()

class BuildingBotsNetworkIntegration:
    """Integration with building bots network mission"""
    
    def __init__(self, service_discovery: ServiceDiscovery):
        self.discovery = service_discovery
        self.bot_services = self._identify_bot_services()
        self.mission_priorities = self._initialize_mission_priorities()
        
    def _identify_bot_services(self) -> List[str]:
        """Identify services that are part of the building bots network"""
        bot_keywords = [
            'bot', 'ai', 'ml', 'agent', 'assistant', 'orchestrator',
            'optimizer', 'analyzer', 'trainer', 'predictor', 'enhancer'
        ]
        
        bot_services = []
        for service_name in self.discovery.services.keys():
            if any(keyword in service_name.lower() for keyword in bot_keywords):
                bot_services.append(service_name)
        
        return bot_services
    
    def _initialize_mission_priorities(self) -> Dict[str, float]:
        """Initialize mission priorities for different bot services"""
        return {
            # Core AI infrastructure - highest priority
            'ai-orchestrator': 1.0,
            'bot-ecosystem': 1.0,
            'bot-orchestrator': 1.0,
            
            # Learning and training systems
            'adaptive-cv-training': 0.9,
            'ml-platform': 0.9,
            'bot-training-hub': 0.9,
            'education-ai': 0.85,
            
            # Specialized bots
            'ai-insights': 0.8,
            'ai-optimizer': 0.8,
            'predictive-ai': 0.8,
            'intelligent-cache': 0.7,
            
            # Support systems
            'analytics-platform': 0.7,
            'monitoring-observability': 0.75,
            'performance-monitor': 0.7,
            
            # Development and testing
            'ai-tools': 0.6,
            'dev-productivity': 0.6,
            
            # Experimental/Research
            'dream-simulator': 0.5,
            'quantum-integration': 0.5
        }
    
    def optimize_for_mission(self) -> Dict[str, Any]:
        """Optimize data management for building bots network mission"""
        optimization_results = {
            'mission_aligned_services': len(self.bot_services),
            'priority_allocations': {},
            'data_flow_optimizations': [],
            'cross_bot_learning_opportunities': [],
            'resource_reallocations': []
        }
        
        # Analyze current resource allocation vs mission priorities
        total_priority_weight = sum(self.mission_priorities.values())
        
        for service_name in self.bot_services:
            if service_name in self.discovery.services:
                service = self.discovery.services[service_name]
                priority = self.mission_priorities.get(service_name, 0.5)
                
                # Calculate optimal allocation
                optimal_allocation_ratio = priority / total_priority_weight
                current_size_mb = sum(
                    Path(f).stat().st_size / (1024 * 1024)
                    for f in (service.data_files + service.ml_models + service.databases)
                    if Path(f).exists()
                )
                
                optimization_results['priority_allocations'][service_name] = {
                    'current_size_mb': current_size_mb,
                    'priority_score': priority,
                    'optimal_allocation_ratio': optimal_allocation_ratio,
                    'mission_critical': priority >= 0.9
                }
        
        # Identify data flow optimization opportunities
        optimization_results['data_flow_optimizations'] = self._identify_data_flow_optimizations()
        
        # Find cross-bot learning opportunities
        optimization_results['cross_bot_learning_opportunities'] = self._find_cross_bot_learning_opportunities()
        
        return optimization_results
    
    def _identify_data_flow_optimizations(self) -> List[Dict[str, Any]]:
        """Identify opportunities to optimize data flow between bots"""
        optimizations = []
        
        # Look for services that produce data consumed by other services
        producer_consumer_pairs = [
            ('ai-insights', 'bot-training-hub', 'insight_data'),
            ('analytics-platform', 'predictive-ai', 'analytics_data'),
            ('performance-monitor', 'ai-optimizer', 'performance_metrics'),
            ('adaptive-cv-training', 'ml-platform', 'trained_models'),
        ]
        
        for producer, consumer, data_type in producer_consumer_pairs:
            if producer in self.discovery.services and consumer in self.discovery.services:
                optimizations.append({
                    'type': 'data_pipeline',
                    'producer': producer,
                    'consumer': consumer,
                    'data_type': data_type,
                    'optimization': 'direct_data_sharing',
                    'estimated_benefit': 'reduced_duplication_and_latency'
                })
        
        return optimizations
    
    def _find_cross_bot_learning_opportunities(self) -> List[Dict[str, Any]]:
        """Find opportunities for bots to learn from each other's data"""
        opportunities = []
        
        # ML models that could benefit from shared training data
        ml_services = [s for s in self.bot_services if 'ml' in s.lower() or 'ai' in s.lower() or 'training' in s.lower()]
        
        for service in ml_services:
            if service in self.discovery.services:
                service_info = self.discovery.services[service]
                if service_info.ml_models:
                    opportunities.append({
                        'type': 'model_sharing',
                        'service': service,
                        'models_count': len(service_info.ml_models),
                        'sharing_potential': 'high' if len(service_info.ml_models) > 3 else 'medium',
                        'benefit': 'accelerated_learning_across_bots'
                    })
        
        return opportunities

class ServiceIntegrationOrchestrator:
    """Main orchestrator for service integration"""
    
    def __init__(self, base_path: str = "/home/activeloguser/activelog/services"):
        self.discovery = ServiceDiscovery(base_path)
        self.data_manager = ServiceDataManager(self.discovery)
        self.bot_integration = BuildingBotsNetworkIntegration(self.discovery)
        self.integration_status = {}
        
    async def initialize_integration(self) -> Dict[str, Any]:
        """Initialize integration with all services"""
        logger.info("Initializing service integration...")
        
        # Discover all services
        services = self.discovery.discover_all_services()
        
        # Analyze data patterns
        patterns = {}
        for service_name in services.keys():
            patterns[service_name] = self.data_manager.analyze_service_data_patterns(service_name)
        
        # Optimize for building bots mission
        mission_optimization = self.bot_integration.optimize_for_mission()
        
        integration_results = {
            'total_services_discovered': len(services),
            'bot_services_identified': len(self.bot_integration.bot_services),
            'services_by_type': self._categorize_services(services),
            'data_patterns_analyzed': len(patterns),
            'mission_optimization': mission_optimization,
            'integration_health': self._assess_integration_health(services)
        }
        
        logger.info(f"Integration initialized: {len(services)} services discovered")
        return integration_results
    
    def _categorize_services(self, services: Dict[str, ServiceInfo]) -> Dict[str, int]:
        """Categorize services by type"""
        categories = defaultdict(int)
        for service in services.values():
            categories[service.service_type] += 1
        return dict(categories)
    
    def _assess_integration_health(self, services: Dict[str, ServiceInfo]) -> Dict[str, Any]:
        """Assess overall integration health"""
        running_services = sum(1 for s in services.values() if s.status == 'running')
        total_memory_mb = sum(s.memory_usage_mb for s in services.values())
        high_importance_services = sum(
            1 for name in services.keys()
            if self.data_manager.cleanup_strategies.get(name, {}).get('importance', 0.5) > 0.8
        )
        
        return {
            'running_services': running_services,
            'total_services': len(services),
            'running_percentage': (running_services / len(services)) * 100 if services else 0,
            'total_memory_usage_mb': total_memory_mb,
            'high_importance_services': high_importance_services,
            'health_score': self._calculate_health_score(services)
        }
    
    def _calculate_health_score(self, services: Dict[str, ServiceInfo]) -> float:
        """Calculate overall integration health score (0-1)"""
        if not services:
            return 0.0
        
        # Factors contributing to health score
        running_ratio = sum(1 for s in services.values() if s.status == 'running') / len(services)
        
        # Memory efficiency (lower is better, but we need some services running)
        avg_memory_per_service = sum(s.memory_usage_mb for s in services.values()) / len(services)
        memory_efficiency = max(0, 1 - (avg_memory_per_service / 1000))  # Normalize to 1GB per service
        
        # Critical services running
        critical_services = [name for name, strategy in self.data_manager.cleanup_strategies.items() 
                           if strategy.get('importance', 0.5) > 0.8]
        critical_running = sum(
            1 for name in critical_services 
            if name in services and services[name].status == 'running'
        )
        critical_ratio = critical_running / len(critical_services) if critical_services else 1.0
        
        # Weighted health score
        health_score = (
            running_ratio * 0.3 +           # 30% weight on services running
            memory_efficiency * 0.2 +       # 20% weight on memory efficiency
            critical_ratio * 0.5            # 50% weight on critical services
        )
        
        return min(max(health_score, 0.0), 1.0)
    
    async def perform_ecosystem_cleanup(self, aggressive: bool = False) -> Dict[str, Any]:
        """Perform cleanup across the entire ecosystem"""
        logger.info(f"Starting ecosystem cleanup (aggressive={aggressive})")
        
        cleanup_results = {
            'total_files_deleted': 0,
            'total_bytes_freed': 0,
            'services_cleaned': 0,
            'service_results': {},
            'cross_service_deduplication': {},
            'cleanup_duration_seconds': 0
        }
        
        start_time = time.time()
        
        try:
            # Clean up each service
            services_to_clean = list(self.discovery.services.keys())
            
            # Prioritize cleanup based on importance (clean less important services more aggressively)
            services_to_clean.sort(
                key=lambda s: self.data_manager.cleanup_strategies.get(s, {}).get('importance', 0.5)
            )
            
            with ThreadPoolExecutor(max_workers=5) as executor:
                cleanup_futures = {
                    executor.submit(self.data_manager.cleanup_service_data, service, aggressive): service
                    for service in services_to_clean
                }
                
                for future in as_completed(cleanup_futures):
                    service_name = cleanup_futures[future]
                    try:
                        result = future.result(timeout=300)  # 5 minute timeout per service
                        cleanup_results['service_results'][service_name] = result
                        
                        if 'error' not in result:
                            cleanup_results['total_files_deleted'] += result.get('files_deleted', 0)
                            cleanup_results['total_bytes_freed'] += result.get('bytes_freed', 0)
                            cleanup_results['services_cleaned'] += 1
                            
                    except Exception as e:
                        logger.error(f"Error cleaning service {service_name}: {e}")
                        cleanup_results['service_results'][service_name] = {'error': str(e)}
            
            # Perform cross-service deduplication
            dedup_result = self.data_manager.cross_service_deduplication()
            cleanup_results['cross_service_deduplication'] = dedup_result
            cleanup_results['total_files_deleted'] += dedup_result.get('files_removed', 0)
            cleanup_results['total_bytes_freed'] += dedup_result.get('bytes_freed', 0)
            
        except Exception as e:
            logger.error(f"Error during ecosystem cleanup: {e}")
            cleanup_results['error'] = str(e)
        
        cleanup_results['cleanup_duration_seconds'] = time.time() - start_time
        cleanup_results['total_mb_freed'] = cleanup_results['total_bytes_freed'] / (1024 * 1024)
        cleanup_results['total_gb_freed'] = cleanup_results['total_bytes_freed'] / (1024 * 1024 * 1024)
        
        logger.info(f"Ecosystem cleanup completed: {cleanup_results['total_gb_freed']:.2f} GB freed")
        return cleanup_results
    
    def get_integration_status(self) -> Dict[str, Any]:
        """Get current integration status"""
        services = self.discovery.services
        
        return {
            'timestamp': datetime.now().isoformat(),
            'total_services': len(services),
            'services_by_status': {
                'running': sum(1 for s in services.values() if s.status == 'running'),
                'stopped': sum(1 for s in services.values() if s.status == 'stopped'),
                'unknown': sum(1 for s in services.values() if s.status == 'unknown')
            },
            'resource_usage': {
                'total_memory_mb': sum(s.memory_usage_mb for s in services.values()),
                'avg_cpu_percent': sum(s.cpu_percent for s in services.values()) / len(services) if services else 0
            },
            'bot_services_count': len(self.bot_integration.bot_services),
            'integration_health': self._assess_integration_health(services),
            'last_discovery': self.discovery.discovery_cache_file
        }