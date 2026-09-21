#!/usr/bin/env python3
"""
Platform Detection System

Intelligent platform detection for automatic build configuration
and optimization recommendations.
"""

import platform
import os
import subprocess
import json
import logging
from typing import Dict, List, Any, Optional
import asyncio

logger = logging.getLogger(__name__)


class PlatformDetector:
    """Intelligent platform detection system"""
    
    def __init__(self):
        self.system_info = self._gather_system_info()
    
    def _gather_system_info(self) -> Dict[str, Any]:
        """Gather comprehensive system information"""
        info = {
            "os": platform.system(),
            "os_version": platform.release(),
            "architecture": platform.machine(),
            "processor": platform.processor(),
            "python_version": platform.python_version(),
            "hostname": platform.node()
        }
        
        # Additional platform-specific information
        if info["os"] == "Windows":
            info.update(self._get_windows_info())
        elif info["os"] == "Darwin":
            info.update(self._get_macos_info())
        elif info["os"] == "Linux":
            info.update(self._get_linux_info())
        
        return info
    
    def _get_windows_info(self) -> Dict[str, Any]:
        """Get Windows-specific information"""
        info = {}
        try:
            import winreg
            
            # Get Windows version details
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 
                               r"SOFTWARE\Microsoft\Windows NT\CurrentVersion")
            info["build_number"] = winreg.QueryValueEx(key, "CurrentBuild")[0]
            info["product_name"] = winreg.QueryValueEx(key, "ProductName")[0]
            winreg.CloseKey(key)
            
        except ImportError:
            info["build_number"] = "unknown"
            info["product_name"] = "Windows"
        except Exception as e:
            logger.warning(f"Failed to get Windows info: {e}")
        
        return info
    
    def _get_macos_info(self) -> Dict[str, Any]:
        """Get macOS-specific information"""
        info = {}
        try:
            # Get macOS version
            result = subprocess.run(["sw_vers"], capture_output=True, text=True)
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if line.startswith('ProductVersion:'):
                        info["macos_version"] = line.split(':')[1].strip()
                    elif line.startswith('BuildVersion:'):
                        info["build_version"] = line.split(':')[1].strip()
            
            # Check for Apple Silicon
            if platform.machine() == "arm64":
                info["apple_silicon"] = True
            else:
                info["apple_silicon"] = False
                
        except Exception as e:
            logger.warning(f"Failed to get macOS info: {e}")
        
        return info
    
    def _get_linux_info(self) -> Dict[str, Any]:
        """Get Linux-specific information"""
        info = {}
        try:
            # Get distribution info
            if os.path.exists("/etc/os-release"):
                with open("/etc/os-release", 'r') as f:
                    for line in f:
                        if line.startswith('ID='):
                            info["distribution"] = line.split('=')[1].strip().strip('"')
                        elif line.startswith('VERSION_ID='):
                            info["version_id"] = line.split('=')[1].strip().strip('"')
            
            # Check for desktop environment
            desktop_env = os.environ.get("XDG_CURRENT_DESKTOP")
            if desktop_env:
                info["desktop_environment"] = desktop_env.lower()
            
            # Check for package managers
            package_managers = []
            for pm in ["apt", "dnf", "yum", "pacman", "zypper"]:
                if subprocess.run(["which", pm], capture_output=True).returncode == 0:
                    package_managers.append(pm)
            info["package_managers"] = package_managers
            
        except Exception as e:
            logger.warning(f"Failed to get Linux info: {e}")
        
        return info
    
    def detect_platform(self) -> Dict[str, Any]:
        """Detect current platform with detailed information"""
        platform_info = {
            "detected_platform": self._classify_platform(),
            "architecture": self._normalize_architecture(),
            "system_info": self.system_info,
            "build_recommendations": self._get_build_recommendations(),
            "supported_formats": self._get_supported_package_formats(),
            "development_tools": self._detect_development_tools()
        }
        
        return platform_info
    
    def _classify_platform(self) -> str:
        """Classify the platform type"""
        os_name = self.system_info["os"]
        
        if os_name == "Windows":
            return "windows"
        elif os_name == "Darwin":
            return "macos"
        elif os_name == "Linux":
            # Check for embedded/mobile Linux
            if self._is_android():
                return "android"
            elif self._is_embedded_linux():
                return "embedded_linux"
            else:
                return "linux"
        else:
            return "unknown"
    
    def _normalize_architecture(self) -> str:
        """Normalize architecture names"""
        arch = self.system_info["architecture"].lower()
        
        arch_mapping = {
            "x86_64": "x64",
            "amd64": "x64",
            "i386": "x86",
            "i686": "x86",
            "arm64": "arm64",
            "aarch64": "arm64",
            "armv7l": "arm",
            "armv6l": "arm"
        }
        
        return arch_mapping.get(arch, arch)
    
    def _is_android(self) -> bool:
        """Check if running on Android"""
        try:
            with open("/proc/version", 'r') as f:
                version = f.read().lower()
                return "android" in version
        except:
            return False
    
    def _is_embedded_linux(self) -> bool:
        """Check if running on embedded Linux"""
        # Check for common embedded indicators
        embedded_indicators = [
            "/sys/firmware/devicetree/base/model",  # Device tree
            "/proc/device-tree/model",              # Alternative device tree path
            "/boot/config.txt",                     # Raspberry Pi
            "/sys/class/thermal/thermal_zone0"      # ARM thermal management
        ]
        
        for indicator in embedded_indicators:
            if os.path.exists(indicator):
                return True
        
        return False
    
    def _get_build_recommendations(self) -> List[Dict[str, Any]]:
        """Get build recommendations for the platform"""
        recommendations = []
        
        platform_type = self._classify_platform()
        arch = self._normalize_architecture()
        
        if platform_type == "windows":
            recommendations.extend([
                {
                    "type": "compiler",
                    "recommendation": "Use MSVC 2022 for best Windows compatibility",
                    "flags": ["/O2", "/GL", "/LTCG"]
                },
                {
                    "type": "package_format",
                    "recommendation": "Create MSI installer for enterprise distribution",
                    "formats": ["msi", "exe"]
                }
            ])
        
        elif platform_type == "macos":
            recommendations.extend([
                {
                    "type": "compiler",
                    "recommendation": "Use Clang with Xcode for optimal performance",
                    "flags": ["-O3", "-flto", "-march=native"]
                },
                {
                    "type": "package_format",
                    "recommendation": "Create DMG for standard distribution",
                    "formats": ["dmg", "pkg"]
                }
            ])
            
            if arch == "arm64":
                recommendations.append({
                    "type": "optimization",
                    "recommendation": "Enable Apple Silicon optimizations",
                    "flags": ["-mcpu=apple-a14"]
                })
        
        elif platform_type == "linux":
            recommendations.extend([
                {
                    "type": "compiler",
                    "recommendation": "Use GCC with LTO for size optimization",
                    "flags": ["-O2", "-flto", "-ffunction-sections"]
                },
                {
                    "type": "package_format",
                    "recommendation": "Create multiple package formats",
                    "formats": ["deb", "rpm", "appimage"]
                }
            ])
        
        return recommendations
    
    def _get_supported_package_formats(self) -> List[str]:
        """Get supported package formats for the platform"""
        platform_type = self._classify_platform()
        
        format_mapping = {
            "windows": ["msi", "exe", "appx", "zip"],
            "macos": ["dmg", "pkg", "zip"],
            "linux": ["deb", "rpm", "appimage", "flatpak", "snap", "tar.gz"],
            "android": ["apk", "aab"],
            "embedded_linux": ["tar.gz", "bin", "hex"]
        }
        
        return format_mapping.get(platform_type, ["zip"])
    
    def _detect_development_tools(self) -> Dict[str, bool]:
        """Detect available development tools"""
        tools = {}
        
        # Compilers
        for compiler in ["gcc", "clang", "cl", "arm-linux-gnueabihf-gcc"]:
            tools[f"compiler_{compiler}"] = self._check_tool_available(compiler)
        
        # Build systems
        for build_tool in ["make", "cmake", "ninja", "msbuild", "xcodebuild"]:
            tools[f"build_{build_tool}"] = self._check_tool_available(build_tool)
        
        # Package managers
        for pm in ["apt", "dnf", "brew", "vcpkg", "conan"]:
            tools[f"package_manager_{pm}"] = self._check_tool_available(pm)
        
        # Mobile development
        tools["android_sdk"] = os.path.exists(os.path.expanduser("~/Android/Sdk"))
        tools["xcode"] = self._check_tool_available("xcodebuild")
        
        # Container tools
        tools["docker"] = self._check_tool_available("docker")
        tools["podman"] = self._check_tool_available("podman")
        
        return tools
    
    def _check_tool_available(self, tool: str) -> bool:
        """Check if a tool is available in PATH"""
        try:
            result = subprocess.run(["which", tool], capture_output=True)
            return result.returncode == 0
        except:
            return False
    
    async def detect_build_requirements(self, source_path: str) -> Dict[str, Any]:
        """Detect build requirements from source code"""
        requirements = {
            "languages": [],
            "frameworks": [],
            "build_systems": [],
            "dependencies": [],
            "recommended_tools": [],
            "estimated_build_time": "unknown"
        }
        
        if not os.path.exists(source_path):
            return requirements
        
        # Analyze files in source directory
        for root, dirs, files in os.walk(source_path):
            for file in files:
                file_path = os.path.join(root, file)
                file_ext = os.path.splitext(file)[1].lower()
                file_name = os.path.basename(file).lower()
                
                # Detect languages
                language_map = {
                    ".c": "c",
                    ".cpp": "cpp",
                    ".cxx": "cpp",
                    ".cc": "cpp",
                    ".h": "c",
                    ".hpp": "cpp",
                    ".py": "python",
                    ".js": "javascript",
                    ".ts": "typescript",
                    ".java": "java",
                    ".kt": "kotlin",
                    ".swift": "swift",
                    ".rs": "rust",
                    ".go": "go",
                    ".cs": "csharp"
                }
                
                if file_ext in language_map:
                    lang = language_map[file_ext]
                    if lang not in requirements["languages"]:
                        requirements["languages"].append(lang)
                
                # Detect build systems
                if file_name in ["makefile", "cmake"]:
                    if "make" not in requirements["build_systems"]:
                        requirements["build_systems"].append("make")
                elif file_name == "cmakelists.txt":
                    if "cmake" not in requirements["build_systems"]:
                        requirements["build_systems"].append("cmake")
                elif file_name in ["package.json"]:
                    if "npm" not in requirements["build_systems"]:
                        requirements["build_systems"].append("npm")
                elif file_name == "cargo.toml":
                    if "cargo" not in requirements["build_systems"]:
                        requirements["build_systems"].append("cargo")
                elif file_ext == ".sln" or file_ext == ".csproj":
                    if "msbuild" not in requirements["build_systems"]:
                        requirements["build_systems"].append("msbuild")
                
                # Detect frameworks
                if file_name == "requirements.txt":
                    requirements["frameworks"].extend(await self._parse_python_requirements(file_path))
                elif file_name == "package.json":
                    requirements["frameworks"].extend(await self._parse_node_dependencies(file_path))
        
        # Generate recommendations
        requirements["recommended_tools"] = self._generate_tool_recommendations(requirements)
        requirements["estimated_build_time"] = self._estimate_build_time(requirements)
        
        return requirements
    
    async def _parse_python_requirements(self, file_path: str) -> List[str]:
        """Parse Python requirements.txt file"""
        frameworks = []
        try:
            with open(file_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        package = line.split('==')[0].split('>=')[0].split('<=')[0]
                        frameworks.append(f"python_{package}")
        except Exception as e:
            logger.warning(f"Failed to parse requirements.txt: {e}")
        
        return frameworks
    
    async def _parse_node_dependencies(self, file_path: str) -> List[str]:
        """Parse Node.js package.json file"""
        frameworks = []
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                
                for dep_type in ["dependencies", "devDependencies"]:
                    deps = data.get(dep_type, {})
                    for package in deps.keys():
                        frameworks.append(f"node_{package}")
                        
        except Exception as e:
            logger.warning(f"Failed to parse package.json: {e}")
        
        return frameworks
    
    def _generate_tool_recommendations(self, requirements: Dict[str, Any]) -> List[str]:
        """Generate tool recommendations based on requirements"""
        recommendations = []
        
        languages = requirements["languages"]
        build_systems = requirements["build_systems"]
        
        # Compiler recommendations
        if "c" in languages or "cpp" in languages:
            platform_type = self._classify_platform()
            if platform_type == "windows":
                recommendations.append("Install Visual Studio 2022")
            elif platform_type == "macos":
                recommendations.append("Install Xcode Command Line Tools")
            else:
                recommendations.append("Install GCC/Clang compiler")
        
        if "python" in languages:
            recommendations.append("Install Python 3.9+")
        
        if "rust" in languages:
            recommendations.append("Install Rust toolchain")
        
        if "go" in languages:
            recommendations.append("Install Go compiler")
        
        # Build system recommendations
        if "cmake" in build_systems:
            recommendations.append("Install CMake 3.15+")
        
        if "npm" in build_systems:
            recommendations.append("Install Node.js and npm")
        
        return recommendations
    
    def _estimate_build_time(self, requirements: Dict[str, Any]) -> str:
        """Estimate build time based on project complexity"""
        complexity_score = 0
        
        # Language complexity
        complexity_score += len(requirements["languages"]) * 10
        
        # Framework complexity
        complexity_score += len(requirements["frameworks"]) * 5
        
        # Build system complexity
        complexity_score += len(requirements["build_systems"]) * 15
        
        if complexity_score < 30:
            return "1-3 minutes"
        elif complexity_score < 60:
            return "3-10 minutes"
        elif complexity_score < 100:
            return "10-30 minutes"
        else:
            return "30+ minutes"