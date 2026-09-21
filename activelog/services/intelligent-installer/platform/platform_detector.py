"""
Advanced Platform Detection and System Analysis
Universal platform detection with detailed system capabilities analysis
"""

import os
import sys
import platform
import subprocess
import asyncio
import json
import logging
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from pathlib import Path

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

try:
    import wmi
    WMI_AVAILABLE = True
except ImportError:
    WMI_AVAILABLE = False

logger = logging.getLogger(__name__)

class PlatformType(Enum):
    WINDOWS = "windows"
    MACOS = "macos"
    LINUX = "linux"
    ANDROID = "android"
    IOS = "ios"
    FREEBSD = "freebsd"
    UNKNOWN = "unknown"

class HardwareArchitecture(Enum):
    X86_64 = "x86_64"
    X86 = "x86"
    ARM64 = "arm64"
    ARM = "arm"
    MIPS = "mips"
    SPARC = "sparc"
    PPC = "ppc"
    UNKNOWN = "unknown"

class ContainerType(Enum):
    NONE = "none"
    DOCKER = "docker"
    PODMAN = "podman"
    LXC = "lxc"
    KUBERNETES = "kubernetes"
    WSL = "wsl"
    UNKNOWN = "unknown"

@dataclass
class SystemCapabilities:
    total_memory: int
    available_memory: int
    cpu_cores: int
    cpu_threads: int
    cpu_frequency: float
    disk_space_total: int
    disk_space_free: int
    network_interfaces: List[str]
    gpu_count: int
    gpu_memory: int
    virtualization_support: bool
    container_support: bool
    admin_privileges: bool
    package_managers: List[str]
    shell_available: List[str]
    python_version: str
    node_version: Optional[str]
    docker_available: bool
    systemd_available: bool

@dataclass
class PlatformInfo:
    platform_type: PlatformType
    platform_version: str
    architecture: HardwareArchitecture
    kernel_version: str
    hostname: str
    domain: Optional[str]
    container_type: ContainerType
    capabilities: SystemCapabilities
    environment_variables: Dict[str, str]
    file_system_type: str
    timezone: str
    locale: str
    user_id: int
    group_id: int
    home_directory: str
    temp_directory: str
    path_separator: str
    line_separator: str
    
class PlatformDetector:
    def __init__(self):
        self.cache_duration = 300  # 5 minutes
        self._cached_info: Optional[PlatformInfo] = None
        self._cache_timestamp = 0
        
    async def detect_platform(self, force_refresh: bool = False) -> PlatformInfo:
        """Comprehensive platform detection with caching"""
        current_time = asyncio.get_event_loop().time()
        
        if (not force_refresh and 
            self._cached_info and 
            current_time - self._cache_timestamp < self.cache_duration):
            return self._cached_info
            
        logger.info("Performing comprehensive platform detection...")
        
        try:
            platform_type = self._detect_platform_type()
            architecture = self._detect_architecture()
            container_type = await self._detect_container_environment()
            capabilities = await self._analyze_system_capabilities()
            
            platform_info = PlatformInfo(
                platform_type=platform_type,
                platform_version=platform.version(),
                architecture=architecture,
                kernel_version=platform.release(),
                hostname=platform.node(),
                domain=self._get_domain(),
                container_type=container_type,
                capabilities=capabilities,
                environment_variables=dict(os.environ),
                file_system_type=self._get_filesystem_type(),
                timezone=self._get_timezone(),
                locale=self._get_locale(),
                user_id=os.getuid() if hasattr(os, 'getuid') else 0,
                group_id=os.getgid() if hasattr(os, 'getgid') else 0,
                home_directory=str(Path.home()),
                temp_directory=self._get_temp_directory(),
                path_separator=os.pathsep,
                line_separator=os.linesep
            )
            
            self._cached_info = platform_info
            self._cache_timestamp = current_time
            
            logger.info(f"Platform detected: {platform_type.value} {architecture.value}")
            return platform_info
            
        except Exception as e:
            logger.error(f"Platform detection failed: {e}")
            # Return minimal fallback info
            return self._create_fallback_info()
    
    def _detect_platform_type(self) -> PlatformType:
        """Detect the operating system platform"""
        system = platform.system().lower()
        
        if system == "windows":
            return PlatformType.WINDOWS
        elif system == "darwin":
            return PlatformType.MACOS
        elif system == "linux":
            # Check for Android
            try:
                with open('/proc/version', 'r') as f:
                    if 'android' in f.read().lower():
                        return PlatformType.ANDROID
            except:
                pass
            return PlatformType.LINUX
        elif system == "freebsd":
            return PlatformType.FREEBSD
        else:
            return PlatformType.UNKNOWN
    
    def _detect_architecture(self) -> HardwareArchitecture:
        """Detect hardware architecture"""
        arch = platform.machine().lower()
        
        if arch in ['amd64', 'x86_64', 'x64']:
            return HardwareArchitecture.X86_64
        elif arch in ['i386', 'i686', 'x86']:
            return HardwareArchitecture.X86
        elif arch in ['arm64', 'aarch64']:
            return HardwareArchitecture.ARM64
        elif arch.startswith('arm'):
            return HardwareArchitecture.ARM
        elif arch.startswith('mips'):
            return HardwareArchitecture.MIPS
        elif arch.startswith('sparc'):
            return HardwareArchitecture.SPARC
        elif arch.startswith('ppc') or arch.startswith('power'):
            return HardwareArchitecture.PPC
        else:
            return HardwareArchitecture.UNKNOWN
    
    async def _detect_container_environment(self) -> ContainerType:
        """Detect if running in a container environment"""
        try:
            # Check for Docker
            if os.path.exists('/.dockerenv'):
                return ContainerType.DOCKER
            
            # Check for WSL
            if 'microsoft' in platform.uname().release.lower():
                return ContainerType.WSL
            
            # Check cgroup for container indicators
            try:
                with open('/proc/1/cgroup', 'r') as f:
                    cgroup_content = f.read().lower()
                    if 'docker' in cgroup_content:
                        return ContainerType.DOCKER
                    elif 'lxc' in cgroup_content:
                        return ContainerType.LXC
                    elif 'kubepods' in cgroup_content:
                        return ContainerType.KUBERNETES
            except:
                pass
            
            # Check environment variables
            if any(var.startswith('KUBERNETES_') for var in os.environ):
                return ContainerType.KUBERNETES
                
            return ContainerType.NONE
            
        except Exception as e:
            logger.warning(f"Container detection failed: {e}")
            return ContainerType.UNKNOWN
    
    async def _analyze_system_capabilities(self) -> SystemCapabilities:
        """Comprehensive system capabilities analysis"""
        try:
            # Memory information
            if PSUTIL_AVAILABLE:
                memory = psutil.virtual_memory()
                total_memory = memory.total
                available_memory = memory.available
                
                # CPU information
                cpu_cores = psutil.cpu_count(logical=False) or 1
                cpu_threads = psutil.cpu_count(logical=True) or 1
                cpu_freq = psutil.cpu_freq()
                cpu_frequency = cpu_freq.current if cpu_freq else 0.0
                
                # Disk information
                disk = psutil.disk_usage('/')
                disk_space_total = disk.total
                disk_space_free = disk.free
                
                # Network interfaces
                network_interfaces = list(psutil.net_if_addrs().keys())
            else:
                # Fallback without psutil
                total_memory = self._get_memory_fallback()
                available_memory = total_memory
                cpu_cores = os.cpu_count() or 1
                cpu_threads = cpu_cores
                cpu_frequency = 0.0
                disk_space_total = 0
                disk_space_free = 0
                network_interfaces = []
            
            # GPU detection
            gpu_count, gpu_memory = await self._detect_gpu()
            
            # Package managers
            package_managers = self._detect_package_managers()
            
            # Shell detection
            shell_available = self._detect_available_shells()
            
            # Version detection
            node_version = await self._get_node_version()
            
            return SystemCapabilities(
                total_memory=total_memory,
                available_memory=available_memory,
                cpu_cores=cpu_cores,
                cpu_threads=cpu_threads,
                cpu_frequency=cpu_frequency,
                disk_space_total=disk_space_total,
                disk_space_free=disk_space_free,
                network_interfaces=network_interfaces,
                gpu_count=gpu_count,
                gpu_memory=gpu_memory,
                virtualization_support=self._check_virtualization_support(),
                container_support=self._check_container_support(),
                admin_privileges=self._check_admin_privileges(),
                package_managers=package_managers,
                shell_available=shell_available,
                python_version=sys.version,
                node_version=node_version,
                docker_available=await self._check_docker_available(),
                systemd_available=self._check_systemd_available()
            )
            
        except Exception as e:
            logger.error(f"System capabilities analysis failed: {e}")
            return self._create_fallback_capabilities()
    
    def _get_memory_fallback(self) -> int:
        """Fallback memory detection without psutil"""
        try:
            if platform.system() == "Linux":
                with open('/proc/meminfo', 'r') as f:
                    for line in f:
                        if line.startswith('MemTotal:'):
                            return int(line.split()[1]) * 1024
            elif platform.system() == "Windows":
                try:
                    import ctypes
                    kernel32 = ctypes.windll.kernel32
                    c_ulong = ctypes.c_ulong
                    class MEMORYSTATUSEX(ctypes.Structure):
                        _fields_ = [
                            ('dwLength', c_ulong),
                            ('dwMemoryLoad', c_ulong),
                            ('ullTotalPhys', ctypes.c_ulonglong),
                            ('ullAvailPhys', ctypes.c_ulonglong),
                        ]
                    memInfo = MEMORYSTATUSEX()
                    memInfo.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
                    kernel32.GlobalMemoryStatusEx(ctypes.byref(memInfo))
                    return memInfo.ullTotalPhys
                except:
                    pass
            return 8 * 1024 * 1024 * 1024  # 8GB fallback
        except:
            return 4 * 1024 * 1024 * 1024  # 4GB fallback
    
    async def _detect_gpu(self) -> Tuple[int, int]:
        """Detect GPU hardware"""
        try:
            gpu_count = 0
            gpu_memory = 0
            
            # NVIDIA detection
            try:
                result = await asyncio.create_subprocess_exec(
                    'nvidia-smi', '--query-gpu=memory.total', '--format=csv,noheader,nounits',
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.DEVNULL
                )
                stdout, _ = await result.communicate()
                if result.returncode == 0:
                    gpu_memories = [int(line.strip()) for line in stdout.decode().strip().split('\n') if line.strip()]
                    gpu_count = len(gpu_memories)
                    gpu_memory = sum(gpu_memories) * 1024 * 1024  # Convert MB to bytes
            except:
                pass
            
            # AMD detection (Linux)
            if gpu_count == 0 and platform.system() == "Linux":
                try:
                    if os.path.exists('/sys/class/drm'):
                        drm_devices = os.listdir('/sys/class/drm')
                        gpu_count = len([d for d in drm_devices if d.startswith('card')])
                except:
                    pass
            
            return gpu_count, gpu_memory
            
        except Exception as e:
            logger.warning(f"GPU detection failed: {e}")
            return 0, 0
    
    def _detect_package_managers(self) -> List[str]:
        """Detect available package managers"""
        managers = []
        
        # Common package managers to check
        pm_commands = {
            'apt': ['apt', 'apt-get'],
            'yum': ['yum'],
            'dnf': ['dnf'],
            'pacman': ['pacman'],
            'zypper': ['zypper'],
            'brew': ['brew'],
            'choco': ['choco'],
            'pip': ['pip', 'pip3'],
            'npm': ['npm'],
            'yarn': ['yarn'],
            'cargo': ['cargo'],
            'gem': ['gem'],
            'go': ['go']
        }
        
        for manager, commands in pm_commands.items():
            for cmd in commands:
                if self._command_exists(cmd):
                    managers.append(manager)
                    break
        
        return managers
    
    def _detect_available_shells(self) -> List[str]:
        """Detect available shell environments"""
        shells = []
        
        shell_paths = [
            '/bin/bash', '/usr/bin/bash',
            '/bin/zsh', '/usr/bin/zsh',
            '/bin/fish', '/usr/bin/fish',
            '/bin/sh', '/usr/bin/sh',
            '/bin/csh', '/usr/bin/csh',
            '/bin/tcsh', '/usr/bin/tcsh'
        ]
        
        for shell_path in shell_paths:
            if os.path.exists(shell_path):
                shells.append(os.path.basename(shell_path))
        
        # Windows shells
        if platform.system() == "Windows":
            shells.extend(['cmd', 'powershell'])
        
        return list(set(shells))
    
    async def _get_node_version(self) -> Optional[str]:
        """Get Node.js version if available"""
        try:
            result = await asyncio.create_subprocess_exec(
                'node', '--version',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL
            )
            stdout, _ = await result.communicate()
            if result.returncode == 0:
                return stdout.decode().strip()
        except:
            pass
        return None
    
    async def _check_docker_available(self) -> bool:
        """Check if Docker is available"""
        try:
            result = await asyncio.create_subprocess_exec(
                'docker', '--version',
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL
            )
            await result.communicate()
            return result.returncode == 0
        except:
            return False
    
    def _check_virtualization_support(self) -> bool:
        """Check if virtualization is supported"""
        try:
            if platform.system() == "Linux":
                # Check for KVM support
                return os.path.exists('/dev/kvm')
            elif platform.system() == "Windows":
                # Check for Hyper-V capability
                try:
                    result = subprocess.run(['systeminfo'], capture_output=True, text=True, timeout=10)
                    return 'Hyper-V' in result.stdout
                except:
                    pass
            return False
        except:
            return False
    
    def _check_container_support(self) -> bool:
        """Check if container technologies are supported"""
        return (self._command_exists('docker') or 
                self._command_exists('podman') or
                self._command_exists('lxc'))
    
    def _check_admin_privileges(self) -> bool:
        """Check if running with administrator/root privileges"""
        try:
            if platform.system() == "Windows":
                import ctypes
                return ctypes.windll.shell32.IsUserAnAdmin()
            else:
                return os.geteuid() == 0
        except:
            return False
    
    def _check_systemd_available(self) -> bool:
        """Check if systemd is available"""
        return os.path.exists('/bin/systemctl') or os.path.exists('/usr/bin/systemctl')
    
    def _command_exists(self, command: str) -> bool:
        """Check if a command exists in PATH"""
        try:
            subprocess.run([command, '--version'], 
                         capture_output=True, 
                         timeout=5)
            return True
        except:
            return False
    
    def _get_domain(self) -> Optional[str]:
        """Get system domain if available"""
        try:
            if platform.system() == "Windows":
                return os.environ.get('USERDOMAIN')
            else:
                # Try to get from hostname
                hostname = platform.node()
                if '.' in hostname:
                    return hostname.split('.', 1)[1]
        except:
            pass
        return None
    
    def _get_filesystem_type(self) -> str:
        """Get primary filesystem type"""
        try:
            if platform.system() == "Linux":
                result = subprocess.run(['df', '-T', '/'], capture_output=True, text=True)
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    if len(lines) > 1:
                        return lines[1].split()[1]
            elif platform.system() == "Windows":
                return "NTFS"
            elif platform.system() == "Darwin":
                return "APFS"
        except:
            pass
        return "unknown"
    
    def _get_timezone(self) -> str:
        """Get system timezone"""
        try:
            import time
            return time.tzname[0]
        except:
            return "UTC"
    
    def _get_locale(self) -> str:
        """Get system locale"""
        try:
            import locale
            return locale.getdefaultlocale()[0] or "en_US"
        except:
            return "en_US"
    
    def _get_temp_directory(self) -> str:
        """Get system temporary directory"""
        import tempfile
        return tempfile.gettempdir()
    
    def _create_fallback_info(self) -> PlatformInfo:
        """Create fallback platform info when detection fails"""
        return PlatformInfo(
            platform_type=PlatformType.UNKNOWN,
            platform_version="unknown",
            architecture=HardwareArchitecture.UNKNOWN,
            kernel_version="unknown",
            hostname="localhost",
            domain=None,
            container_type=ContainerType.UNKNOWN,
            capabilities=self._create_fallback_capabilities(),
            environment_variables={},
            file_system_type="unknown",
            timezone="UTC",
            locale="en_US",
            user_id=0,
            group_id=0,
            home_directory=str(Path.home()),
            temp_directory=self._get_temp_directory(),
            path_separator=os.pathsep,
            line_separator=os.linesep
        )
    
    def _create_fallback_capabilities(self) -> SystemCapabilities:
        """Create fallback system capabilities"""
        return SystemCapabilities(
            total_memory=4 * 1024 * 1024 * 1024,  # 4GB
            available_memory=2 * 1024 * 1024 * 1024,  # 2GB
            cpu_cores=2,
            cpu_threads=2,
            cpu_frequency=2000.0,
            disk_space_total=100 * 1024 * 1024 * 1024,  # 100GB
            disk_space_free=50 * 1024 * 1024 * 1024,   # 50GB
            network_interfaces=[],
            gpu_count=0,
            gpu_memory=0,
            virtualization_support=False,
            container_support=False,
            admin_privileges=False,
            package_managers=[],
            shell_available=[],
            python_version=sys.version,
            node_version=None,
            docker_available=False,
            systemd_available=False
        )

    async def get_platform_info_json(self) -> str:
        """Get platform information as JSON string"""
        info = await self.detect_platform()
        return json.dumps(asdict(info), indent=2, default=str)