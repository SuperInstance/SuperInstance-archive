#!/usr/bin/env python3
"""
Build Configuration Settings

Configuration settings for the platform builders service.
"""

import os
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum


class LogLevel(Enum):
    """Logging levels"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class OptimizationLevel(Enum):
    """Build optimization levels"""
    NONE = "none"
    BASIC = "basic"
    BALANCED = "balanced"
    AGGRESSIVE = "aggressive"
    SIZE = "size"
    SPEED = "speed"


@dataclass
class BuildSettings:
    """Build configuration settings"""
    
    # Service settings
    host: str = "0.0.0.0"
    port: int = 8432
    debug: bool = False
    log_level: LogLevel = LogLevel.INFO
    start_time: float = time.time()
    
    # Build settings
    max_concurrent_builds: int = 4
    build_timeout_minutes: int = 60
    cleanup_old_builds_days: int = 7
    incremental_builds_enabled: bool = True
    
    # Paths
    projects_dir: str = "projects"
    builds_dir: str = "builds"
    dist_dir: str = "dist"
    cache_dir: str = "cache"
    temp_dir: str = "/tmp/platform-builders"
    
    # Optimization settings
    default_optimization_level: OptimizationLevel = OptimizationLevel.BALANCED
    enable_lto: bool = True  # Link-time optimization
    enable_pgo: bool = False  # Profile-guided optimization
    strip_debug_symbols: bool = True
    compress_binaries: bool = True
    
    # Platform-specific settings
    desktop_settings: Dict[str, Any] = None
    mobile_settings: Dict[str, Any] = None
    embedded_settings: Dict[str, Any] = None
    edge_settings: Dict[str, Any] = None
    
    # Distribution settings
    enable_signing: bool = True
    enable_delta_updates: bool = True
    rollback_enabled: bool = True
    staged_rollout_percentage: int = 10
    
    # Security settings
    signature_verification: bool = True
    encryption_enabled: bool = True
    secure_boot_support: bool = True
    
    def __post_init__(self):
        # Initialize platform-specific settings
        if self.desktop_settings is None:
            self.desktop_settings = {
                "windows": {
                    "msvc_version": "2022",
                    "windows_sdk_version": "10.0.22000.0",
                    "target_frameworks": ["net6.0", "net48"],
                    "sign_binaries": True,
                    "create_installer": True,
                    "installer_type": "msi"
                },
                "macos": {
                    "xcode_version": "15.0",
                    "deployment_target": "11.0",
                    "code_signing": True,
                    "notarization": True,
                    "create_dmg": True,
                    "app_store_ready": False
                },
                "linux": {
                    "gcc_version": "11",
                    "create_appimage": True,
                    "create_flatpak": True,
                    "create_snap": True,
                    "create_deb": True,
                    "create_rpm": True
                },
                "chromeos": {
                    "create_crx": True,
                    "manifest_version": 3,
                    "web_store_ready": True
                },
                "freebsd": {
                    "clang_version": "15",
                    "create_pkg": True
                }
            }
        
        if self.mobile_settings is None:
            self.mobile_settings = {
                "ios": {
                    "xcode_version": "15.0",
                    "deployment_target": "13.0",
                    "code_signing": True,
                    "app_store_ready": True,
                    "create_ipa": True,
                    "bitcode_enabled": False
                },
                "android": {
                    "gradle_version": "8.0",
                    "compile_sdk": 34,
                    "min_sdk": 24,
                    "target_sdk": 34,
                    "create_aab": True,
                    "create_apk": True,
                    "sign_release": True,
                    "proguard_enabled": True
                },
                "windows_mobile": {
                    "uwp_version": "10.0.22000.0",
                    "create_appx": True,
                    "store_ready": True
                },
                "kaios": {
                    "web_manifest": True,
                    "privileged_app": False
                },
                "wearos": {
                    "wear_os_version": "4.0",
                    "create_wear_apk": True
                }
            }
        
        if self.embedded_settings is None:
            self.embedded_settings = {
                "raspberry_pi": {
                    "cross_compile": True,
                    "target_arch": "armv7l",
                    "optimize_for_size": True,
                    "create_image": True
                },
                "arduino": {
                    "arduino_cli": True,
                    "board_manager": "arduino:avr",
                    "optimize_for_size": True,
                    "create_hex": True
                },
                "esp32": {
                    "idf_version": "5.1",
                    "target_chip": "esp32",
                    "flash_size": "4MB",
                    "optimize_for_size": True,
                    "create_bin": True
                },
                "jetson": {
                    "jetpack_version": "5.1",
                    "cuda_version": "11.8",
                    "tensorrt_enabled": True,
                    "create_deb": True
                },
                "beaglebone": {
                    "cross_compile": True,
                    "target_arch": "armv7l",
                    "device_tree": True,
                    "create_image": True
                },
                "plc": {
                    "codesys_compatible": True,
                    "iec_61131": True,
                    "real_time": True
                },
                "automotive": {
                    "autosar_classic": True,
                    "automotive_grade": True,
                    "functional_safety": True
                },
                "marine": {
                    "nmea_2000": True,
                    "maritime_grade": True,
                    "corrosion_resistant": True
                },
                "smart_home": {
                    "zigbee_support": True,
                    "wifi_support": True,
                    "low_power": True
                },
                "medical": {
                    "fda_compliant": True,
                    "hipaa_compliant": True,
                    "medical_grade": True
                }
            }
        
        if self.edge_settings is None:
            self.edge_settings = {
                "aws_greengrass": {
                    "greengrass_version": "2.0",
                    "lambda_support": True,
                    "create_component": True
                },
                "azure_iot_edge": {
                    "iot_edge_version": "1.4",
                    "create_module": True,
                    "container_support": True
                },
                "google_edge_tpu": {
                    "coral_support": True,
                    "tflite_support": True,
                    "create_model": True
                },
                "nvidia_edge": {
                    "jetpack_version": "5.1",
                    "deepstream_support": True,
                    "create_container": True
                },
                "intel_nuc": {
                    "openvino_support": True,
                    "create_package": True,
                    "hardware_acceleration": True
                }
            }
        
        # Ensure directories exist
        for directory in [self.projects_dir, self.builds_dir, self.dist_dir, 
                         self.cache_dir, self.temp_dir]:
            os.makedirs(directory, exist_ok=True)


# Global configuration instance
build_config = BuildSettings()

# Platform-specific compiler configurations
COMPILER_CONFIGS = {
    "windows": {
        "x86": {
            "compiler": "cl.exe",
            "flags": ["/O2", "/GL", "/DWIN32", "/D_WINDOWS"],
            "linker_flags": ["/LTCG", "/OPT:REF", "/OPT:ICF"]
        },
        "x64": {
            "compiler": "cl.exe",
            "flags": ["/O2", "/GL", "/D_WIN64", "/D_WINDOWS"],
            "linker_flags": ["/LTCG", "/OPT:REF", "/OPT:ICF"]
        },
        "arm64": {
            "compiler": "cl.exe",
            "flags": ["/O2", "/GL", "/D_WIN64", "/D_ARM64"],
            "linker_flags": ["/LTCG", "/OPT:REF", "/OPT:ICF", "/MACHINE:ARM64"]
        }
    },
    "macos": {
        "x64": {
            "compiler": "clang",
            "flags": ["-O3", "-flto", "-mmacosx-version-min=11.0", "-arch", "x86_64"],
            "linker_flags": ["-flto", "-Wl,-dead_strip"]
        },
        "arm64": {
            "compiler": "clang",
            "flags": ["-O3", "-flto", "-mmacosx-version-min=11.0", "-arch", "arm64"],
            "linker_flags": ["-flto", "-Wl,-dead_strip"]
        }
    },
    "linux": {
        "x86": {
            "compiler": "gcc",
            "flags": ["-O3", "-flto", "-march=i686", "-m32"],
            "linker_flags": ["-flto", "-Wl,--gc-sections", "-s"]
        },
        "x64": {
            "compiler": "gcc",
            "flags": ["-O3", "-flto", "-march=x86-64", "-m64"],
            "linker_flags": ["-flto", "-Wl,--gc-sections", "-s"]
        },
        "arm": {
            "compiler": "arm-linux-gnueabihf-gcc",
            "flags": ["-O3", "-flto", "-march=armv7-a", "-mfpu=neon"],
            "linker_flags": ["-flto", "-Wl,--gc-sections", "-s"]
        },
        "arm64": {
            "compiler": "aarch64-linux-gnu-gcc",
            "flags": ["-O3", "-flto", "-march=armv8-a"],
            "linker_flags": ["-flto", "-Wl,--gc-sections", "-s"]
        }
    },
    "embedded": {
        "avr": {
            "compiler": "avr-gcc",
            "flags": ["-Os", "-flto", "-mmcu=atmega328p"],
            "linker_flags": ["-flto", "-Wl,--gc-sections"]
        },
        "esp32": {
            "compiler": "xtensa-esp32-elf-gcc",
            "flags": ["-Os", "-flto", "-ffunction-sections", "-fdata-sections"],
            "linker_flags": ["-flto", "-Wl,--gc-sections"]
        },
        "arm_cortex_m": {
            "compiler": "arm-none-eabi-gcc",
            "flags": ["-Os", "-flto", "-mcpu=cortex-m4", "-mthumb"],
            "linker_flags": ["-flto", "-Wl,--gc-sections", "-nostartfiles"]
        }
    }
}

# Build templates for different project types
BUILD_TEMPLATES = {
    "desktop_app": {
        "languages": ["c++", "c#", "python", "rust", "go"],
        "frameworks": ["qt", "gtk", "wpf", "electron", "tauri"],
        "build_systems": ["cmake", "msbuild", "cargo", "go_build"]
    },
    "mobile_app": {
        "languages": ["swift", "kotlin", "dart", "c++"],
        "frameworks": ["ios_native", "android_native", "flutter", "react_native"],
        "build_systems": ["xcode", "gradle", "flutter_build"]
    },
    "web_app": {
        "languages": ["javascript", "typescript", "rust", "go"],
        "frameworks": ["react", "vue", "angular", "svelte", "wasm"],
        "build_systems": ["webpack", "vite", "parcel", "cargo_web"]
    },
    "embedded_firmware": {
        "languages": ["c", "c++", "rust"],
        "frameworks": ["arduino", "esp_idf", "zephyr", "freertos"],
        "build_systems": ["make", "cmake", "platformio", "cargo_embed"]
    },
    "edge_service": {
        "languages": ["python", "go", "rust", "c++"],
        "frameworks": ["docker", "kubernetes", "lambda", "azure_functions"],
        "build_systems": ["docker", "cargo", "go_build", "pip"]
    }
}

# Optimization profiles for different use cases
OPTIMIZATION_PROFILES = {
    OptimizationLevel.NONE: {
        "compiler_flags": [],
        "linker_flags": [],
        "strip_symbols": False,
        "compress": False,
        "lto": False,
        "pgo": False
    },
    OptimizationLevel.BASIC: {
        "compiler_flags": ["-O1"],
        "linker_flags": [],
        "strip_symbols": True,
        "compress": False,
        "lto": False,
        "pgo": False
    },
    OptimizationLevel.BALANCED: {
        "compiler_flags": ["-O2"],
        "linker_flags": ["-Wl,--gc-sections"],
        "strip_symbols": True,
        "compress": True,
        "lto": True,
        "pgo": False
    },
    OptimizationLevel.AGGRESSIVE: {
        "compiler_flags": ["-O3", "-ffast-math", "-funroll-loops"],
        "linker_flags": ["-Wl,--gc-sections", "-Wl,--strip-all"],
        "strip_symbols": True,
        "compress": True,
        "lto": True,
        "pgo": True
    },
    OptimizationLevel.SIZE: {
        "compiler_flags": ["-Os", "-ffunction-sections", "-fdata-sections"],
        "linker_flags": ["-Wl,--gc-sections", "-Wl,--strip-all"],
        "strip_symbols": True,
        "compress": True,
        "lto": True,
        "pgo": False
    },
    OptimizationLevel.SPEED: {
        "compiler_flags": ["-Ofast", "-march=native", "-funroll-loops", "-fomit-frame-pointer"],
        "linker_flags": ["-Wl,--gc-sections"],
        "strip_symbols": True,
        "compress": False,
        "lto": True,
        "pgo": True
    }
}

# Security configurations
SECURITY_CONFIGS = {
    "basic": {
        "stack_protection": True,
        "fortify_source": True,
        "relro": True,
        "nx_bit": True,
        "pie": True
    },
    "enhanced": {
        "stack_protection": True,
        "fortify_source": True,
        "relro": "full",
        "nx_bit": True,
        "pie": True,
        "stack_canary": True,
        "cfi": True  # Control Flow Integrity
    },
    "maximum": {
        "stack_protection": True,
        "fortify_source": True,
        "relro": "full",
        "nx_bit": True,
        "pie": True,
        "stack_canary": True,
        "cfi": True,
        "shadow_stack": True,
        "cet": True,  # Control-flow Enforcement Technology
        "mbec": True  # Mode-based Execute Control
    }
}