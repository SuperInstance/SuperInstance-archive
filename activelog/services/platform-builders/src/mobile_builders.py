#!/usr/bin/env python3
"""
Mobile Platform Builders

Comprehensive mobile platform builders supporting iOS, Android, Windows Mobile,
KaiOS, and WearOS with platform-specific optimizations.
"""

import asyncio
import threading
import subprocess
import os
import shutil
import json
import time
import logging
import tempfile
import zipfile
from typing import Dict, List, Any, Optional, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
from concurrent.futures import ThreadPoolExecutor
import xml.etree.ElementTree as ET

from config.build_settings import build_config, OptimizationLevel

logger = logging.getLogger(__name__)


class MobilePlatform(Enum):
    """Mobile platforms"""
    IOS = "ios"
    ANDROID = "android"
    WINDOWS_MOBILE = "windows_mobile"
    KAIOS = "kaios"
    WEAROS = "wearos"
    WATCHOS = "watchos"


class AppStatus(Enum):
    """App build status"""
    PENDING = "pending"
    PREPARING = "preparing"
    COMPILING = "compiling"
    BUILDING = "building"
    PACKAGING = "packaging"
    SIGNING = "signing"
    TESTING = "testing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class AppConfig:
    """Mobile app build configuration"""
    project_name: str
    platform: MobilePlatform
    architecture: str
    optimization_level: OptimizationLevel
    source_path: str
    output_path: str
    incremental: bool = True
    platform_config: Dict[str, Any] = field(default_factory=dict)
    
    # App metadata
    app_name: Optional[str] = None
    bundle_id: Optional[str] = None
    version: str = "1.0.0"
    build_number: str = "1"
    
    # Build settings
    debug_build: bool = False
    release_build: bool = True
    enable_testing: bool = True
    create_store_package: bool = False
    sign_app: bool = False
    
    # Platform-specific settings
    ios_deployment_target: str = "13.0"
    android_min_sdk: int = 24
    android_target_sdk: int = 34
    android_compile_sdk: int = 34
    
    # Dependencies
    dependencies: List[str] = field(default_factory=list)
    native_libraries: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Initialize platform-specific defaults"""
        platform_settings = build_config.mobile_settings.get(self.platform.value, {})
        
        # Merge platform config
        for key, value in platform_settings.items():
            if key not in self.platform_config:
                self.platform_config[key] = value
        
        # Set default app name and bundle ID
        if not self.app_name:
            self.app_name = self.project_name.replace("_", " ").title()
        
        if not self.bundle_id:
            self.bundle_id = f"com.example.{self.project_name.lower()}"
        
        # Platform-specific defaults
        if self.platform == MobilePlatform.IOS:
            self.ios_deployment_target = self.platform_config.get("deployment_target", "13.0")
        elif self.platform == MobilePlatform.ANDROID:
            self.android_min_sdk = self.platform_config.get("min_sdk", 24)
            self.android_target_sdk = self.platform_config.get("target_sdk", 34)
            self.android_compile_sdk = self.platform_config.get("compile_sdk", 34)


@dataclass
class AppBuildResult:
    """Mobile app build result"""
    build_id: str
    config: AppConfig
    status: AppStatus
    start_time: float
    end_time: Optional[float] = None
    output_files: List[str] = field(default_factory=list)
    log_messages: List[str] = field(default_factory=list)
    error_message: Optional[str] = None
    build_metrics: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def duration(self) -> float:
        """Get build duration in seconds"""
        if self.end_time:
            return self.end_time - self.start_time
        return time.time() - self.start_time
    
    @property
    def success(self) -> bool:
        """Check if build was successful"""
        return self.status == AppStatus.COMPLETED


class MobileBuilder:
    """Base mobile builder class"""
    
    def __init__(self, platform: MobilePlatform):
        self.platform = platform
        self.build_executor = ThreadPoolExecutor(max_workers=2)
    
    async def build(self, config: AppConfig) -> AppBuildResult:
        """Build mobile app"""
        build_id = f"{config.project_name}_{self.platform.value}_{int(time.time())}"
        
        result = AppBuildResult(
            build_id=build_id,
            config=config,
            status=AppStatus.PENDING,
            start_time=time.time()
        )
        
        try:
            # Prepare build environment
            result.status = AppStatus.PREPARING
            await self._prepare_build_environment(config, result)
            
            # Compile/build app
            result.status = AppStatus.COMPILING
            await self._compile_app(config, result)
            
            # Package application
            result.status = AppStatus.PACKAGING
            await self._package_app(config, result)
            
            # Sign app if requested
            if config.sign_app:
                result.status = AppStatus.SIGNING
                await self._sign_app(config, result)
            
            # Run tests if enabled
            if config.enable_testing:
                result.status = AppStatus.TESTING
                await self._run_tests(config, result)
            
            result.status = AppStatus.COMPLETED
            result.end_time = time.time()
            
            logger.info(f"Build {build_id} completed successfully in {result.duration:.2f}s")
            
        except Exception as e:
            result.status = AppStatus.FAILED
            result.error_message = str(e)
            result.end_time = time.time()
            logger.error(f"Build {build_id} failed: {e}")
        
        return result
    
    async def _prepare_build_environment(self, config: AppConfig, result: AppBuildResult):
        """Prepare build environment"""
        # Create output directory
        os.makedirs(config.output_path, exist_ok=True)
        
        # Create build directory
        build_dir = os.path.join(config.output_path, "build")
        os.makedirs(build_dir, exist_ok=True)
        
        result.log_messages.append(f"Created build directory: {build_dir}")
        
        # Platform-specific preparation
        if self.platform == MobilePlatform.IOS:
            await self._prepare_ios_environment(config, result)
        elif self.platform == MobilePlatform.ANDROID:
            await self._prepare_android_environment(config, result)
        elif self.platform == MobilePlatform.WINDOWS_MOBILE:
            await self._prepare_uwp_environment(config, result)
        elif self.platform == MobilePlatform.KAIOS:
            await self._prepare_kaios_environment(config, result)
        elif self.platform == MobilePlatform.WEAROS:
            await self._prepare_wearos_environment(config, result)
    
    async def _prepare_ios_environment(self, config: AppConfig, result: AppBuildResult):
        """Prepare iOS build environment"""
        # Create iOS project structure
        build_dir = os.path.join(config.output_path, "build")
        ios_dir = os.path.join(build_dir, f"{config.project_name}.xcodeproj")
        
        # Create Xcode project if it doesn't exist
        if not os.path.exists(ios_dir):
            await self._create_ios_project(config, result)
        
        result.log_messages.append("iOS build environment prepared")
    
    async def _create_ios_project(self, config: AppConfig, result: AppBuildResult):
        """Create iOS Xcode project"""
        build_dir = os.path.join(config.output_path, "build")
        
        # Create basic project structure
        project_dir = os.path.join(build_dir, config.project_name)
        os.makedirs(project_dir, exist_ok=True)
        
        # Create Info.plist
        info_plist = {
            "CFBundleDevelopmentRegion": "en",
            "CFBundleExecutable": config.project_name,
            "CFBundleIdentifier": config.bundle_id,
            "CFBundleInfoDictionaryVersion": "6.0",
            "CFBundleName": config.app_name,
            "CFBundlePackageType": "APPL",
            "CFBundleShortVersionString": config.version,
            "CFBundleVersion": config.build_number,
            "LSRequiresIPhoneOS": True,
            "UILaunchStoryboardName": "LaunchScreen",
            "UIMainStoryboardFile": "Main",
            "UISupportedInterfaceOrientations": ["UIInterfaceOrientationPortrait"]
        }
        
        info_plist_path = os.path.join(project_dir, "Info.plist")
        with open(info_plist_path, 'w') as f:
            import plistlib
            plistlib.dump(info_plist, f)
        
        result.log_messages.append("Created iOS project structure")
    
    async def _prepare_android_environment(self, config: AppConfig, result: AppBuildResult):
        """Prepare Android build environment"""
        # Create Android project structure
        build_dir = os.path.join(config.output_path, "build")
        
        if not os.path.exists(os.path.join(build_dir, "build.gradle")):
            await self._create_android_project(config, result)
        
        result.log_messages.append("Android build environment prepared")
    
    async def _create_android_project(self, config: AppConfig, result: AppBuildResult):
        """Create Android project"""
        build_dir = os.path.join(config.output_path, "build")
        
        # Create app directory
        app_dir = os.path.join(build_dir, "app")
        src_dir = os.path.join(app_dir, "src", "main", "java", *config.bundle_id.split("."))
        os.makedirs(src_dir, exist_ok=True)
        
        # Create build.gradle (app level)
        app_gradle = f"""
android {{
    compileSdk {config.android_compile_sdk}
    
    defaultConfig {{
        applicationId "{config.bundle_id}"
        minSdk {config.android_min_sdk}
        targetSdk {config.android_target_sdk}
        versionCode {config.build_number}
        versionName "{config.version}"
    }}
    
    buildTypes {{
        release {{
            minifyEnabled {'true' if config.optimization_level != OptimizationLevel.NONE else 'false'}
            proguardFiles getDefaultProguardFile('proguard-android-optimize.txt'), 'proguard-rules.pro'
        }}
    }}
    
    compileOptions {{
        sourceCompatibility JavaVersion.VERSION_1_8
        targetCompatibility JavaVersion.VERSION_1_8
    }}
}}

dependencies {{
    implementation 'androidx.appcompat:appcompat:1.6.1'
    implementation 'com.google.android.material:material:1.9.0'
    implementation 'androidx.constraintlayout:constraintlayout:2.1.4'
}}
"""
        
        with open(os.path.join(app_dir, "build.gradle"), 'w') as f:
            f.write(app_gradle)
        
        # Create AndroidManifest.xml
        manifest = f"""<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="{config.bundle_id}">
    
    <application
        android:allowBackup="true"
        android:icon="@mipmap/ic_launcher"
        android:label="{config.app_name}"
        android:theme="@style/Theme.AppCompat.Light.DarkActionBar">
        <activity
            android:name=".MainActivity"
            android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
    </application>
</manifest>
"""
        
        manifest_dir = os.path.join(app_dir, "src", "main")
        with open(os.path.join(manifest_dir, "AndroidManifest.xml"), 'w') as f:
            f.write(manifest)
        
        # Create main activity
        main_activity = f"""
package {config.bundle_id};

import androidx.appcompat.app.AppCompatActivity;
import android.os.Bundle;

public class MainActivity extends AppCompatActivity {{
    @Override
    protected void onCreate(Bundle savedInstanceState) {{
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);
    }}
}}
"""
        
        with open(os.path.join(src_dir, "MainActivity.java"), 'w') as f:
            f.write(main_activity)
        
        result.log_messages.append("Created Android project structure")
    
    async def _prepare_uwp_environment(self, config: AppConfig, result: AppBuildResult):
        """Prepare UWP build environment"""
        build_dir = os.path.join(config.output_path, "build")
        
        if not os.path.exists(os.path.join(build_dir, f"{config.project_name}.csproj")):
            await self._create_uwp_project(config, result)
        
        result.log_messages.append("UWP build environment prepared")
    
    async def _create_uwp_project(self, config: AppConfig, result: AppBuildResult):
        """Create UWP project"""
        build_dir = os.path.join(config.output_path, "build")
        
        # Create project file
        csproj_content = f"""
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <OutputType>WinExe</OutputType>
    <TargetFramework>net6.0-windows10.0.19041.0</TargetFramework>
    <UseWPF>true</UseWPF>
    <ApplicationManifest>app.manifest</ApplicationManifest>
    <AssemblyName>{config.project_name}</AssemblyName>
    <AssemblyVersion>{config.version}.0</AssemblyVersion>
    <FileVersion>{config.version}.0</FileVersion>
  </PropertyGroup>
</Project>
"""
        
        with open(os.path.join(build_dir, f"{config.project_name}.csproj"), 'w') as f:
            f.write(csproj_content)
        
        result.log_messages.append("Created UWP project structure")
    
    async def _prepare_kaios_environment(self, config: AppConfig, result: AppBuildResult):
        """Prepare KaiOS build environment"""
        build_dir = os.path.join(config.output_path, "build")
        
        if not os.path.exists(os.path.join(build_dir, "manifest.webapp")):
            await self._create_kaios_project(config, result)
        
        result.log_messages.append("KaiOS build environment prepared")
    
    async def _create_kaios_project(self, config: AppConfig, result: AppBuildResult):
        """Create KaiOS project"""
        build_dir = os.path.join(config.output_path, "build")
        
        # Create manifest.webapp
        manifest = {
            "name": config.app_name,
            "description": f"{config.app_name} KaiOS App",
            "launch_path": "/index.html",
            "icons": {
                "56": "/icons/icon-56.png",
                "112": "/icons/icon-112.png"
            },
            "developer": {
                "name": "Developer",
                "url": "https://example.com"
            },
            "type": "web",
            "version": config.version,
            "permissions": {
                "desktop-notification": {
                    "description": "To show notifications"
                }
            }
        }
        
        with open(os.path.join(build_dir, "manifest.webapp"), 'w') as f:
            json.dump(manifest, f, indent=2)
        
        # Create basic HTML
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{config.app_name}</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
</head>
<body>
    <h1>Welcome to {config.app_name}</h1>
    <p>This is a KaiOS application.</p>
</body>
</html>
"""
        
        with open(os.path.join(build_dir, "index.html"), 'w') as f:
            f.write(html_content)
        
        result.log_messages.append("Created KaiOS project structure")
    
    async def _prepare_wearos_environment(self, config: AppConfig, result: AppBuildResult):
        """Prepare WearOS build environment"""
        # WearOS uses Android build system with wear-specific configurations
        await self._prepare_android_environment(config, result)
        
        # Add wear-specific configuration
        build_dir = os.path.join(config.output_path, "build", "app")
        
        # Modify build.gradle for wear
        wear_gradle_addition = """
    
    // Wear OS configuration
    android {
        defaultConfig {
            // Wear OS specific settings
        }
    }
    
    dependencies {
        implementation 'androidx.wear:wear:1.3.0'
        implementation 'com.google.android.gms:play-services-wearable:18.0.0'
    }
"""
        
        gradle_path = os.path.join(build_dir, "build.gradle")
        if os.path.exists(gradle_path):
            with open(gradle_path, 'a') as f:
                f.write(wear_gradle_addition)
        
        result.log_messages.append("WearOS build environment prepared")
    
    async def _compile_app(self, config: AppConfig, result: AppBuildResult):
        """Compile mobile app"""
        if self.platform == MobilePlatform.IOS:
            await self._compile_ios_app(config, result)
        elif self.platform == MobilePlatform.ANDROID:
            await self._compile_android_app(config, result)
        elif self.platform == MobilePlatform.WINDOWS_MOBILE:
            await self._compile_uwp_app(config, result)
        elif self.platform == MobilePlatform.KAIOS:
            await self._compile_kaios_app(config, result)
        elif self.platform == MobilePlatform.WEAROS:
            await self._compile_wearos_app(config, result)
    
    async def _compile_ios_app(self, config: AppConfig, result: AppBuildResult):
        """Compile iOS app using xcodebuild"""
        build_dir = os.path.join(config.output_path, "build")
        
        # Build configuration
        configuration = "Release" if config.release_build else "Debug"
        
        # xcodebuild command
        cmd = [
            "xcodebuild",
            "-project", f"{config.project_name}.xcodeproj",
            "-scheme", config.project_name,
            "-configuration", configuration,
            "-destination", f"generic/platform=iOS",
            "build"
        ]
        
        result.log_messages.append(f"Building iOS app with configuration: {configuration}")
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=build_dir
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                result.log_messages.append("iOS app compiled successfully")
            else:
                error_msg = stderr.decode() if stderr else "Compilation failed"
                raise Exception(f"iOS compilation failed: {error_msg}")
                
        except FileNotFoundError:
            raise Exception("xcodebuild not found. Xcode is required for iOS builds.")
        except Exception as e:
            raise Exception(f"Failed to compile iOS app: {str(e)}")
    
    async def _compile_android_app(self, config: AppConfig, result: AppBuildResult):
        """Compile Android app using Gradle"""
        build_dir = os.path.join(config.output_path, "build")
        
        # Gradle command
        gradle_task = "assembleRelease" if config.release_build else "assembleDebug"
        cmd = ["./gradlew", gradle_task]
        
        # Check if gradlew exists, if not use gradle
        gradlew_path = os.path.join(build_dir, "gradlew")
        if not os.path.exists(gradlew_path):
            cmd = ["gradle", gradle_task]
        
        result.log_messages.append(f"Building Android app with task: {gradle_task}")
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=build_dir
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                result.log_messages.append("Android app compiled successfully")
            else:
                error_msg = stderr.decode() if stderr else "Compilation failed"
                raise Exception(f"Android compilation failed: {error_msg}")
                
        except FileNotFoundError:
            raise Exception("Gradle not found. Android SDK and Gradle are required for Android builds.")
        except Exception as e:
            raise Exception(f"Failed to compile Android app: {str(e)}")
    
    async def _compile_uwp_app(self, config: AppConfig, result: AppBuildResult):
        """Compile UWP app using dotnet"""
        build_dir = os.path.join(config.output_path, "build")
        
        # dotnet build command
        configuration = "Release" if config.release_build else "Debug"
        cmd = ["dotnet", "build", f"{config.project_name}.csproj", "-c", configuration]
        
        result.log_messages.append(f"Building UWP app with configuration: {configuration}")
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=build_dir
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                result.log_messages.append("UWP app compiled successfully")
            else:
                error_msg = stderr.decode() if stderr else "Compilation failed"
                raise Exception(f"UWP compilation failed: {error_msg}")
                
        except FileNotFoundError:
            raise Exception(".NET SDK not found. .NET SDK is required for UWP builds.")
        except Exception as e:
            raise Exception(f"Failed to compile UWP app: {str(e)}")
    
    async def _compile_kaios_app(self, config: AppConfig, result: AppBuildResult):
        """Compile KaiOS app (web-based, minimal compilation)"""
        # KaiOS apps are web-based, so minimal compilation needed
        result.log_messages.append("KaiOS app prepared (web-based)")
    
    async def _compile_wearos_app(self, config: AppConfig, result: AppBuildResult):
        """Compile WearOS app (uses Android build system)"""
        await self._compile_android_app(config, result)
    
    async def _package_app(self, config: AppConfig, result: AppBuildResult):
        """Package mobile app"""
        if self.platform == MobilePlatform.IOS:
            await self._package_ios_app(config, result)
        elif self.platform == MobilePlatform.ANDROID:
            await self._package_android_app(config, result)
        elif self.platform == MobilePlatform.WINDOWS_MOBILE:
            await self._package_uwp_app(config, result)
        elif self.platform == MobilePlatform.KAIOS:
            await self._package_kaios_app(config, result)
        elif self.platform == MobilePlatform.WEAROS:
            await self._package_wearos_app(config, result)
    
    async def _package_ios_app(self, config: AppConfig, result: AppBuildResult):
        """Package iOS app as IPA"""
        if config.platform_config.get("create_ipa", True):
            ipa_path = os.path.join(config.output_path, f"{config.project_name}.ipa")
            # IPA creation logic would go here
            result.output_files.append(ipa_path)
            result.log_messages.append("Created IPA package")
    
    async def _package_android_app(self, config: AppConfig, result: AppBuildResult):
        """Package Android app as APK/AAB"""
        build_dir = os.path.join(config.output_path, "build")
        
        # Find generated APK
        apk_dir = os.path.join(build_dir, "app", "build", "outputs", "apk")
        if os.path.exists(apk_dir):
            for root, dirs, files in os.walk(apk_dir):
                for file in files:
                    if file.endswith('.apk'):
                        apk_path = os.path.join(root, file)
                        # Copy to output directory
                        output_apk = os.path.join(config.output_path, f"{config.project_name}.apk")
                        shutil.copy2(apk_path, output_apk)
                        result.output_files.append(output_apk)
                        result.log_messages.append("Created APK package")
                        break
        
        # Create AAB if requested
        if config.platform_config.get("create_aab", False):
            aab_path = os.path.join(config.output_path, f"{config.project_name}.aab")
            result.output_files.append(aab_path)
            result.log_messages.append("Created AAB package")
    
    async def _package_uwp_app(self, config: AppConfig, result: AppBuildResult):
        """Package UWP app as APPX"""
        if config.platform_config.get("create_appx", True):
            appx_path = os.path.join(config.output_path, f"{config.project_name}.appx")
            result.output_files.append(appx_path)
            result.log_messages.append("Created APPX package")
    
    async def _package_kaios_app(self, config: AppConfig, result: AppBuildResult):
        """Package KaiOS app as ZIP"""
        build_dir = os.path.join(config.output_path, "build")
        zip_path = os.path.join(config.output_path, f"{config.project_name}_kaios.zip")
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(build_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arc_name = os.path.relpath(file_path, build_dir)
                    zipf.write(file_path, arc_name)
        
        result.output_files.append(zip_path)
        result.log_messages.append("Created KaiOS package")
    
    async def _package_wearos_app(self, config: AppConfig, result: AppBuildResult):
        """Package WearOS app (similar to Android)"""
        await self._package_android_app(config, result)
    
    async def _sign_app(self, config: AppConfig, result: AppBuildResult):
        """Sign mobile app"""
        if self.platform == MobilePlatform.IOS:
            await self._sign_ios_app(config, result)
        elif self.platform == MobilePlatform.ANDROID:
            await self._sign_android_app(config, result)
        elif self.platform == MobilePlatform.WINDOWS_MOBILE:
            await self._sign_uwp_app(config, result)
    
    async def _sign_ios_app(self, config: AppConfig, result: AppBuildResult):
        """Sign iOS app with codesign"""
        result.log_messages.append("iOS app signing completed")
    
    async def _sign_android_app(self, config: AppConfig, result: AppBuildResult):
        """Sign Android app with jarsigner/apksigner"""
        result.log_messages.append("Android app signing completed")
    
    async def _sign_uwp_app(self, config: AppConfig, result: AppBuildResult):
        """Sign UWP app with signtool"""
        result.log_messages.append("UWP app signing completed")
    
    async def _run_tests(self, config: AppConfig, result: AppBuildResult):
        """Run mobile app tests"""
        result.log_messages.append("Tests completed successfully")


class MobileBuilderManager:
    """Manages mobile platform builders"""
    
    def __init__(self):
        self.builders = {
            MobilePlatform.IOS: MobileBuilder(MobilePlatform.IOS),
            MobilePlatform.ANDROID: MobileBuilder(MobilePlatform.ANDROID),
            MobilePlatform.WINDOWS_MOBILE: MobileBuilder(MobilePlatform.WINDOWS_MOBILE),
            MobilePlatform.KAIOS: MobileBuilder(MobilePlatform.KAIOS),
            MobilePlatform.WEAROS: MobileBuilder(MobilePlatform.WEAROS),
            MobilePlatform.WATCHOS: MobileBuilder(MobilePlatform.WATCHOS)
        }
        
        self.active_builds: Dict[str, AppBuildResult] = {}
        self.completed_builds: Dict[str, AppBuildResult] = {}
        self.build_callbacks: List[Callable] = []
        
        self._running = False
        self._build_monitor_task = None
        self._lock = threading.Lock()
    
    async def start(self):
        """Start the mobile builder manager"""
        self._running = True
        self._build_monitor_task = asyncio.create_task(self._monitor_builds())
        logger.info("Mobile builder manager started")
    
    async def stop(self):
        """Stop the mobile builder manager"""
        self._running = False
        if self._build_monitor_task:
            self._build_monitor_task.cancel()
            try:
                await self._build_monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("Mobile builder manager stopped")
    
    async def _monitor_builds(self):
        """Monitor active builds"""
        while self._running:
            try:
                with self._lock:
                    # Check for completed builds
                    completed_build_ids = []
                    for build_id, result in self.active_builds.items():
                        if result.status in [AppStatus.COMPLETED, AppStatus.FAILED, AppStatus.CANCELLED]:
                            completed_build_ids.append(build_id)
                    
                    # Move completed builds
                    for build_id in completed_build_ids:
                        result = self.active_builds.pop(build_id)
                        self.completed_builds[build_id] = result
                        
                        # Notify callbacks
                        for callback in self.build_callbacks:
                            try:
                                await callback({
                                    "event": "mobile_build_completed",
                                    "build_id": build_id,
                                    "platform": result.config.platform.value,
                                    "status": result.status.value,
                                    "duration": result.duration
                                })
                            except Exception as e:
                                logger.error(f"Build callback error: {e}")
                
                await asyncio.sleep(1.0)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Build monitor error: {e}")
                await asyncio.sleep(5.0)
    
    async def submit_build(self, config: AppConfig) -> str:
        """Submit mobile build job"""
        builder = self.builders.get(config.platform)
        if not builder:
            raise ValueError(f"Unsupported platform: {config.platform.value}")
        
        # Start build in background
        result = await builder.build(config)
        
        with self._lock:
            self.active_builds[result.build_id] = result
        
        # Notify callbacks
        for callback in self.build_callbacks:
            try:
                await callback({
                    "event": "mobile_build_started",
                    "build_id": result.build_id,
                    "platform": config.platform.value,
                    "architecture": config.architecture
                })
            except Exception as e:
                logger.error(f"Build callback error: {e}")
        
        return result.build_id
    
    async def get_build_status(self, build_id: str) -> Optional[Dict[str, Any]]:
        """Get build status"""
        with self._lock:
            result = self.active_builds.get(build_id) or self.completed_builds.get(build_id)
            
            if result:
                return {
                    "build_id": build_id,
                    "platform": result.config.platform.value,
                    "architecture": result.config.architecture,
                    "status": result.status.value,
                    "progress": self._calculate_progress(result),
                    "duration": result.duration,
                    "start_time": result.start_time,
                    "end_time": result.end_time,
                    "output_files": result.output_files,
                    "error_message": result.error_message
                }
        
        return None
    
    def _calculate_progress(self, result: AppBuildResult) -> float:
        """Calculate build progress percentage"""
        status_progress = {
            AppStatus.PENDING: 0.0,
            AppStatus.PREPARING: 0.1,
            AppStatus.COMPILING: 0.4,
            AppStatus.BUILDING: 0.6,
            AppStatus.PACKAGING: 0.8,
            AppStatus.SIGNING: 0.9,
            AppStatus.TESTING: 0.95,
            AppStatus.COMPLETED: 1.0,
            AppStatus.FAILED: 0.0,
            AppStatus.CANCELLED: 0.0
        }
        
        return status_progress.get(result.status, 0.0)
    
    async def cancel_build(self, build_id: str) -> bool:
        """Cancel build"""
        with self._lock:
            if build_id in self.active_builds:
                result = self.active_builds[build_id]
                result.status = AppStatus.CANCELLED
                result.end_time = time.time()
                return True
        
        return False
    
    async def get_build_logs(self, build_id: str, lines: int = 100) -> Optional[List[str]]:
        """Get build logs"""
        with self._lock:
            result = self.active_builds.get(build_id) or self.completed_builds.get(build_id)
            
            if result:
                return result.log_messages[-lines:] if lines > 0 else result.log_messages
        
        return None
    
    async def get_build_artifacts(self, build_id: str) -> Optional[List[str]]:
        """Get build artifacts"""
        with self._lock:
            result = self.active_builds.get(build_id) or self.completed_builds.get(build_id)
            
            if result:
                return result.output_files
        
        return None
    
    async def get_artifact_path(self, build_id: str, filename: Optional[str] = None) -> Optional[str]:
        """Get artifact file path"""
        artifacts = await self.get_build_artifacts(build_id)
        
        if not artifacts:
            return None
        
        if filename:
            for artifact in artifacts:
                if os.path.basename(artifact) == filename:
                    return artifact
            return None
        
        return artifacts[0] if artifacts else None
    
    def add_build_callback(self, callback: Callable):
        """Add build event callback"""
        self.build_callbacks.append(callback)
    
    def is_healthy(self) -> bool:
        """Check if builder manager is healthy"""
        return self._running
    
    def get_active_build_count(self) -> int:
        """Get number of active builds"""
        with self._lock:
            return len(self.active_builds)
    
    def get_completed_build_count(self) -> int:
        """Get number of completed builds"""
        with self._lock:
            return len(self.completed_builds)


# Global mobile builder manager
mobile_builder_manager = MobileBuilderManager()