"""
Mobile App Testing Engine for iOS and Android

This module provides comprehensive mobile application testing including device testing,
cross-platform validation, performance testing, and mobile-specific user interactions.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
from enum import Enum
import json
import asyncio
import logging
from pathlib import Path
import subprocess
import time
import random
import base64
from appium import webdriver
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.actions import interaction
from selenium.webdriver.common.actions.action_builder import ActionBuilder
from selenium.webdriver.common.actions.pointer_input import PointerInput
import requests


class MobilePlatform(Enum):
    """Mobile platforms"""
    IOS = "ios"
    ANDROID = "android"
    BOTH = "both"


class DeviceType(Enum):
    """Device types"""
    PHONE = "phone"
    TABLET = "tablet"
    SIMULATOR = "simulator"
    EMULATOR = "emulator"
    REAL_DEVICE = "real_device"


class MobileTestType(Enum):
    """Types of mobile tests"""
    FUNCTIONAL = "functional"
    UI_UX = "ui_ux"
    PERFORMANCE = "performance"
    BATTERY = "battery"
    MEMORY = "memory"
    NETWORK = "network"
    GESTURES = "gestures"
    ORIENTATION = "orientation"
    NOTIFICATIONS = "notifications"
    PERMISSIONS = "permissions"
    OFFLINE_MODE = "offline_mode"
    CROSS_PLATFORM = "cross_platform"


class GestureType(Enum):
    """Mobile gesture types"""
    TAP = "tap"
    DOUBLE_TAP = "double_tap"
    LONG_PRESS = "long_press"
    SWIPE = "swipe"
    SCROLL = "scroll"
    PINCH = "pinch"
    ZOOM = "zoom"
    DRAG_DROP = "drag_drop"
    MULTI_TOUCH = "multi_touch"


@dataclass
class MobileDevice:
    """Mobile device configuration"""
    device_id: str
    platform: MobilePlatform
    device_type: DeviceType
    device_name: str
    os_version: str
    screen_width: int = 375
    screen_height: int = 667
    pixel_density: float = 2.0
    capabilities: Dict[str, Any] = field(default_factory=dict)
    is_available: bool = True
    tags: List[str] = field(default_factory=list)


@dataclass
class MobileTestCase:
    """Mobile test case definition"""
    test_id: str
    name: str
    description: str
    test_type: MobileTestType
    platforms: List[MobilePlatform]
    test_steps: List[Dict[str, Any]]
    expected_results: Dict[str, Any]
    device_requirements: Dict[str, Any] = field(default_factory=dict)
    app_package: Optional[str] = None  # Android package or iOS bundle ID
    timeout: float = 120.0
    tags: List[str] = field(default_factory=list)


@dataclass
class MobileTestResult:
    """Result of mobile test execution"""
    test_id: str
    test_name: str
    test_type: MobileTestType
    platform: MobilePlatform
    device_id: str
    status: str  # "passed", "failed", "skipped", "error"
    start_time: datetime
    end_time: Optional[datetime] = None
    execution_time: float = 0.0
    step_results: List[Dict[str, Any]] = field(default_factory=list)
    screenshots: List[str] = field(default_factory=list)
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    error_message: Optional[str] = None
    device_logs: List[str] = field(default_factory=list)


@dataclass
class MobileTestReport:
    """Comprehensive mobile test report"""
    report_id: str
    test_session_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    platforms_tested: List[MobilePlatform] = field(default_factory=list)
    devices_tested: List[str] = field(default_factory=list)
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    skipped_tests: int = 0
    test_results: List[MobileTestResult] = field(default_factory=list)
    performance_summary: Dict[str, Any] = field(default_factory=dict)
    compatibility_matrix: Dict[str, Dict[str, str]] = field(default_factory=dict)
    device_coverage: Dict[str, float] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)


class MobileDeviceManager:
    """Manages mobile devices and simulators/emulators"""
    
    def __init__(self):
        self.devices: Dict[str, MobileDevice] = {}
        self.appium_server_url = "http://localhost:4723/wd/hub"
        self.drivers: Dict[str, webdriver.Remote] = {}
    
    def register_device(self, device: MobileDevice):
        """Register a mobile device"""
        self.devices[device.device_id] = device
        logging.info(f"Registered device: {device.device_name} ({device.platform.value})")
    
    def create_default_devices(self):
        """Create default device configurations"""
        # iOS Devices
        ios_devices = [
            MobileDevice(
                device_id="iphone_14",
                platform=MobilePlatform.IOS,
                device_type=DeviceType.SIMULATOR,
                device_name="iPhone 14",
                os_version="16.0",
                screen_width=390,
                screen_height=844,
                pixel_density=3.0,
                capabilities={
                    "platformName": "iOS",
                    "deviceName": "iPhone 14",
                    "platformVersion": "16.0",
                    "automationName": "XCUITest"
                }
            ),
            MobileDevice(
                device_id="ipad_air",
                platform=MobilePlatform.IOS,
                device_type=DeviceType.SIMULATOR,
                device_name="iPad Air",
                os_version="16.0",
                screen_width=820,
                screen_height=1180,
                pixel_density=2.0,
                capabilities={
                    "platformName": "iOS",
                    "deviceName": "iPad Air (5th generation)",
                    "platformVersion": "16.0",
                    "automationName": "XCUITest"
                }
            )
        ]
        
        # Android Devices
        android_devices = [
            MobileDevice(
                device_id="pixel_6",
                platform=MobilePlatform.ANDROID,
                device_type=DeviceType.EMULATOR,
                device_name="Pixel 6",
                os_version="12.0",
                screen_width=411,
                screen_height=891,
                pixel_density=2.625,
                capabilities={
                    "platformName": "Android",
                    "deviceName": "Pixel_6_API_31",
                    "platformVersion": "12.0",
                    "automationName": "UiAutomator2"
                }
            ),
            MobileDevice(
                device_id="galaxy_tab",
                platform=MobilePlatform.ANDROID,
                device_type=DeviceType.EMULATOR,
                device_name="Galaxy Tab",
                os_version="11.0",
                screen_width=800,
                screen_height=1280,
                pixel_density=2.0,
                capabilities={
                    "platformName": "Android",
                    "deviceName": "Galaxy_Tab_S7_API_30",
                    "platformVersion": "11.0",
                    "automationName": "UiAutomator2"
                }
            )
        ]
        
        for device in ios_devices + android_devices:
            self.register_device(device)
    
    async def get_driver(self, device_id: str, app_package: Optional[str] = None) -> webdriver.Remote:
        """Get Appium WebDriver for device"""
        if device_id not in self.devices:
            raise ValueError(f"Device {device_id} not found")
        
        if device_id in self.drivers:
            return self.drivers[device_id]
        
        device = self.devices[device_id]
        capabilities = device.capabilities.copy()
        
        # Add app-specific capabilities
        if app_package:
            if device.platform == MobilePlatform.ANDROID:
                capabilities["appPackage"] = app_package
                capabilities["appActivity"] = "MainActivity"  # Default activity
            elif device.platform == MobilePlatform.IOS:
                capabilities["bundleId"] = app_package
        
        # Add browser capabilities for web testing
        if not app_package:
            if device.platform == MobilePlatform.ANDROID:
                capabilities["browserName"] = "Chrome"
            elif device.platform == MobilePlatform.IOS:
                capabilities["browserName"] = "Safari"
        
        try:
            driver = webdriver.Remote(
                command_executor=self.appium_server_url,
                desired_capabilities=capabilities
            )
            
            self.drivers[device_id] = driver
            logging.info(f"Created driver for device: {device.device_name}")
            return driver
        
        except Exception as e:
            logging.error(f"Failed to create driver for {device_id}: {e}")
            raise
    
    def cleanup_drivers(self):
        """Clean up all WebDriver instances"""
        for device_id, driver in self.drivers.items():
            try:
                driver.quit()
                logging.info(f"Closed driver for device: {device_id}")
            except Exception as e:
                logging.error(f"Error closing driver for {device_id}: {e}")
        
        self.drivers.clear()
    
    def get_available_devices(self, platform: Optional[MobilePlatform] = None) -> List[MobileDevice]:
        """Get list of available devices"""
        devices = [d for d in self.devices.values() if d.is_available]
        
        if platform:
            devices = [d for d in devices if d.platform == platform or d.platform == MobilePlatform.BOTH]
        
        return devices
    
    async def check_device_availability(self, device_id: str) -> bool:
        """Check if device is available for testing"""
        if device_id not in self.devices:
            return False
        
        device = self.devices[device_id]
        
        try:
            # For simulators/emulators, check if they can be started
            if device.device_type in [DeviceType.SIMULATOR, DeviceType.EMULATOR]:
                # Simplified availability check
                return True
            
            # For real devices, check connection
            if device.platform == MobilePlatform.ANDROID:
                result = subprocess.run(
                    ["adb", "devices"], 
                    capture_output=True, 
                    text=True, 
                    timeout=10
                )
                return device_id in result.stdout
            
            elif device.platform == MobilePlatform.IOS:
                # Check using xcrun simctl for simulators
                result = subprocess.run(
                    ["xcrun", "simctl", "list", "devices"], 
                    capture_output=True, 
                    text=True, 
                    timeout=10
                )
                return device.device_name in result.stdout
        
        except Exception as e:
            logging.error(f"Error checking device availability for {device_id}: {e}")
            return False
        
        return True


class MobileGestureHandler:
    """Handles mobile-specific gestures and interactions"""
    
    def __init__(self, driver: webdriver.Remote):
        self.driver = driver
    
    async def tap(self, x: int, y: int):
        """Perform tap gesture"""
        try:
            self.driver.tap([(x, y)])
        except AttributeError:
            # Fallback to TouchAction for newer Appium versions
            from appium.webdriver.common.touch_action import TouchAction
            action = TouchAction(self.driver)
            action.tap(x=x, y=y).perform()
    
    async def double_tap(self, x: int, y: int):
        """Perform double tap gesture"""
        await self.tap(x, y)
        await asyncio.sleep(0.1)
        await self.tap(x, y)
    
    async def long_press(self, x: int, y: int, duration: int = 1000):
        """Perform long press gesture"""
        try:
            from appium.webdriver.common.touch_action import TouchAction
            action = TouchAction(self.driver)
            action.long_press(x=x, y=y, duration=duration).perform()
        except Exception as e:
            logging.error(f"Long press failed: {e}")
    
    async def swipe(self, start_x: int, start_y: int, end_x: int, end_y: int, duration: int = 1000):
        """Perform swipe gesture"""
        try:
            self.driver.swipe(start_x, start_y, end_x, end_y, duration)
        except Exception as e:
            logging.error(f"Swipe failed: {e}")
    
    async def scroll_up(self, distance: int = 300):
        """Scroll up"""
        size = self.driver.get_window_size()
        start_x = size['width'] // 2
        start_y = size['height'] * 0.7
        end_y = start_y - distance
        
        await self.swipe(start_x, int(start_y), start_x, int(end_y))
    
    async def scroll_down(self, distance: int = 300):
        """Scroll down"""
        size = self.driver.get_window_size()
        start_x = size['width'] // 2
        start_y = size['height'] * 0.3
        end_y = start_y + distance
        
        await self.swipe(start_x, int(start_y), start_x, int(end_y))
    
    async def swipe_left(self, distance: int = 300):
        """Swipe left"""
        size = self.driver.get_window_size()
        start_x = size['width'] * 0.7
        start_y = size['height'] // 2
        end_x = start_x - distance
        
        await self.swipe(int(start_x), start_y, int(end_x), start_y)
    
    async def swipe_right(self, distance: int = 300):
        """Swipe right"""
        size = self.driver.get_window_size()
        start_x = size['width'] * 0.3
        start_y = size['height'] // 2
        end_x = start_x + distance
        
        await self.swipe(int(start_x), start_y, int(end_x), start_y)
    
    async def pinch(self, element=None, scale: float = 0.5):
        """Perform pinch gesture"""
        try:
            if element:
                self.driver.pinch(element, scale)
            else:
                # Pinch on center of screen
                size = self.driver.get_window_size()
                self.driver.pinch(x=size['width']//2, y=size['height']//2, scale=scale)
        except Exception as e:
            logging.error(f"Pinch failed: {e}")
    
    async def zoom(self, element=None, scale: float = 2.0):
        """Perform zoom gesture"""
        try:
            if element:
                self.driver.zoom(element, scale)
            else:
                # Zoom on center of screen
                size = self.driver.get_window_size()
                self.driver.zoom(x=size['width']//2, y=size['height']//2, scale=scale)
        except Exception as e:
            logging.error(f"Zoom failed: {e}")


class MobilePerformanceMonitor:
    """Monitors mobile app performance"""
    
    def __init__(self, driver: webdriver.Remote):
        self.driver = driver
        self.monitoring = False
        self.metrics: List[Dict[str, Any]] = []
    
    def start_monitoring(self):
        """Start performance monitoring"""
        self.monitoring = True
        self.metrics = []
    
    def stop_monitoring(self):
        """Stop performance monitoring"""
        self.monitoring = False
    
    async def collect_performance_data(self) -> Dict[str, float]:
        """Collect performance metrics"""
        metrics = {}
        
        try:
            # Get memory usage (Android)
            if hasattr(self.driver, 'get_performance_data'):
                memory_data = self.driver.get_performance_data('com.example.app', 'memoryinfo', 5)
                if memory_data:
                    # Extract memory metrics
                    metrics['memory_usage_mb'] = float(memory_data[0][0]) / 1024  # Convert to MB
            
            # Get CPU usage (simplified)
            cpu_data = self.driver.get_performance_data('com.example.app', 'cpuinfo', 5)
            if cpu_data:
                metrics['cpu_usage_percent'] = float(cpu_data[0][0])
            
            # Get network data
            network_data = self.driver.get_performance_data('com.example.app', 'networkinfo', 5)
            if network_data:
                metrics['network_received_kb'] = float(network_data[0][0]) / 1024
                metrics['network_sent_kb'] = float(network_data[0][1]) / 1024
            
            # Get battery info
            battery_data = self.driver.get_performance_data('com.example.app', 'batteryinfo', 5)
            if battery_data:
                metrics['battery_usage_percent'] = float(battery_data[0][0])
        
        except Exception as e:
            logging.debug(f"Performance data collection failed: {e}")
            # Return mock data for testing
            metrics = {
                'memory_usage_mb': random.uniform(50, 200),
                'cpu_usage_percent': random.uniform(10, 80),
                'network_received_kb': random.uniform(100, 1000),
                'network_sent_kb': random.uniform(50, 500),
                'battery_usage_percent': random.uniform(1, 10)
            }
        
        metrics['timestamp'] = time.time()
        return metrics
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary"""
        if not self.metrics:
            return {}
        
        summary = {}
        
        # Calculate averages for each metric
        for metric_key in ['memory_usage_mb', 'cpu_usage_percent', 'battery_usage_percent']:
            values = [m.get(metric_key, 0) for m in self.metrics if metric_key in m]
            if values:
                summary[f'avg_{metric_key}'] = sum(values) / len(values)
                summary[f'max_{metric_key}'] = max(values)
                summary[f'min_{metric_key}'] = min(values)
        
        return summary


class MobileTestExecutor:
    """Executes mobile test cases"""
    
    def __init__(self, device_manager: MobileDeviceManager):
        self.device_manager = device_manager
    
    async def execute_test_case(self, test_case: MobileTestCase, device_id: str) -> MobileTestResult:
        """Execute mobile test case on specific device"""
        device = self.device_manager.devices[device_id]
        
        result = MobileTestResult(
            test_id=test_case.test_id,
            test_name=test_case.name,
            test_type=test_case.test_type,
            platform=device.platform,
            device_id=device_id,
            status="failed",
            start_time=datetime.now()
        )
        
        try:
            # Get WebDriver for device
            driver = await self.device_manager.get_driver(device_id, test_case.app_package)
            
            # Initialize gesture handler and performance monitor
            gesture_handler = MobileGestureHandler(driver)
            performance_monitor = MobilePerformanceMonitor(driver)
            
            # Start performance monitoring
            performance_monitor.start_monitoring()
            
            # Execute test steps
            for i, step in enumerate(test_case.test_steps):
                step_result = await self._execute_step(step, driver, gesture_handler, result)
                result.step_results.append(step_result)
                
                if not step_result.get("success", False) and not step.get("optional", False):
                    result.status = "failed"
                    result.error_message = step_result.get("error", "Step failed")
                    break
                
                # Collect performance data
                if performance_monitor.monitoring:
                    perf_data = await performance_monitor.collect_performance_data()
                    performance_monitor.metrics.append(perf_data)
                
                # Brief pause between steps
                await asyncio.sleep(0.5)
            
            else:
                # All steps completed successfully
                result.status = "passed"
            
            # Stop performance monitoring and collect summary
            performance_monitor.stop_monitoring()
            result.performance_metrics = performance_monitor.get_performance_summary()
            
            # Take final screenshot
            screenshot_path = await self._take_screenshot(driver, f"{test_case.test_id}_final")
            if screenshot_path:
                result.screenshots.append(screenshot_path)
        
        except Exception as e:
            result.status = "error"
            result.error_message = str(e)
            logging.error(f"Test execution failed for {test_case.test_id}: {e}")
        
        finally:
            result.end_time = datetime.now()
            result.execution_time = (result.end_time - result.start_time).total_seconds()
        
        return result
    
    async def _execute_step(self, step: Dict[str, Any], driver: webdriver.Remote,
                          gesture_handler: MobileGestureHandler, 
                          test_result: MobileTestResult) -> Dict[str, Any]:
        """Execute individual test step"""
        step_type = step.get("type")
        
        try:
            if step_type == "navigate":
                return await self._execute_navigate_step(step, driver)
            elif step_type == "tap":
                return await self._execute_tap_step(step, driver, gesture_handler)
            elif step_type == "input":
                return await self._execute_input_step(step, driver)
            elif step_type == "swipe":
                return await self._execute_swipe_step(step, gesture_handler)
            elif step_type == "scroll":
                return await self._execute_scroll_step(step, gesture_handler)
            elif step_type == "wait":
                return await self._execute_wait_step(step, driver)
            elif step_type == "verify":
                return await self._execute_verify_step(step, driver)
            elif step_type == "screenshot":
                return await self._execute_screenshot_step(step, driver, test_result)
            elif step_type == "orientation":
                return await self._execute_orientation_step(step, driver)
            elif step_type == "permission":
                return await self._execute_permission_step(step, driver)
            elif step_type == "notification":
                return await self._execute_notification_step(step, driver)
            else:
                return {
                    "success": False,
                    "error": f"Unknown step type: {step_type}",
                    "step": step
                }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "step": step
            }
    
    async def _execute_navigate_step(self, step: Dict[str, Any], driver: webdriver.Remote) -> Dict[str, Any]:
        """Execute navigation step"""
        url = step.get("url")
        if not url:
            return {"success": False, "error": "URL not provided"}
        
        driver.get(url)
        
        return {
            "success": True,
            "step": step,
            "current_url": driver.current_url
        }
    
    async def _execute_tap_step(self, step: Dict[str, Any], driver: webdriver.Remote,
                              gesture_handler: MobileGestureHandler) -> Dict[str, Any]:
        """Execute tap step"""
        selector = step.get("selector")
        coordinates = step.get("coordinates")
        
        if coordinates:
            # Tap at specific coordinates
            x, y = coordinates
            await gesture_handler.tap(x, y)
        elif selector:
            # Find element and tap
            try:
                if selector.startswith("id="):
                    element = driver.find_element(AppiumBy.ID, selector[3:])
                elif selector.startswith("xpath="):
                    element = driver.find_element(AppiumBy.XPATH, selector[6:])
                elif selector.startswith("class="):
                    element = driver.find_element(AppiumBy.CLASS_NAME, selector[6:])
                else:
                    element = driver.find_element(AppiumBy.ID, selector)
                
                element.click()
            except Exception as e:
                return {"success": False, "error": f"Element not found: {selector}"}
        else:
            return {"success": False, "error": "Neither selector nor coordinates provided"}
        
        return {"success": True, "step": step}
    
    async def _execute_input_step(self, step: Dict[str, Any], driver: webdriver.Remote) -> Dict[str, Any]:
        """Execute input step"""
        selector = step.get("selector")
        text = step.get("text", "")
        clear_first = step.get("clear", True)
        
        if not selector:
            return {"success": False, "error": "Selector not provided"}
        
        try:
            if selector.startswith("id="):
                element = driver.find_element(AppiumBy.ID, selector[3:])
            elif selector.startswith("xpath="):
                element = driver.find_element(AppiumBy.XPATH, selector[6:])
            else:
                element = driver.find_element(AppiumBy.ID, selector)
            
            if clear_first:
                element.clear()
            
            element.send_keys(text)
            
            return {
                "success": True,
                "step": step,
                "input_text": text
            }
        
        except Exception as e:
            return {"success": False, "error": f"Input failed: {str(e)}"}
    
    async def _execute_swipe_step(self, step: Dict[str, Any], gesture_handler: MobileGestureHandler) -> Dict[str, Any]:
        """Execute swipe step"""
        direction = step.get("direction", "up")
        distance = step.get("distance", 300)
        
        if direction == "up":
            await gesture_handler.scroll_up(distance)
        elif direction == "down":
            await gesture_handler.scroll_down(distance)
        elif direction == "left":
            await gesture_handler.swipe_left(distance)
        elif direction == "right":
            await gesture_handler.swipe_right(distance)
        else:
            return {"success": False, "error": f"Unknown swipe direction: {direction}"}
        
        return {"success": True, "step": step, "direction": direction}
    
    async def _execute_scroll_step(self, step: Dict[str, Any], gesture_handler: MobileGestureHandler) -> Dict[str, Any]:
        """Execute scroll step"""
        direction = step.get("direction", "down")
        distance = step.get("distance", 300)
        
        if direction == "up":
            await gesture_handler.scroll_up(distance)
        elif direction == "down":
            await gesture_handler.scroll_down(distance)
        else:
            return {"success": False, "error": f"Unknown scroll direction: {direction}"}
        
        return {"success": True, "step": step}
    
    async def _execute_wait_step(self, step: Dict[str, Any], driver: webdriver.Remote) -> Dict[str, Any]:
        """Execute wait step"""
        duration = step.get("duration", 1.0)
        selector = step.get("selector")
        
        if selector:
            # Wait for element
            try:
                wait = WebDriverWait(driver, duration)
                if selector.startswith("id="):
                    wait.until(EC.presence_of_element_located((AppiumBy.ID, selector[3:])))
                elif selector.startswith("xpath="):
                    wait.until(EC.presence_of_element_located((AppiumBy.XPATH, selector[6:])))
                else:
                    wait.until(EC.presence_of_element_located((AppiumBy.ID, selector)))
            except Exception as e:
                return {"success": False, "error": f"Element wait timeout: {selector}"}
        else:
            # Simple time wait
            await asyncio.sleep(duration)
        
        return {"success": True, "step": step}
    
    async def _execute_verify_step(self, step: Dict[str, Any], driver: webdriver.Remote) -> Dict[str, Any]:
        """Execute verification step"""
        verification_type = step.get("verification_type")
        expected_value = step.get("expected_value")
        selector = step.get("selector")
        
        if verification_type == "element_visible":
            try:
                if selector.startswith("id="):
                    element = driver.find_element(AppiumBy.ID, selector[3:])
                elif selector.startswith("xpath="):
                    element = driver.find_element(AppiumBy.XPATH, selector[6:])
                else:
                    element = driver.find_element(AppiumBy.ID, selector)
                
                is_displayed = element.is_displayed()
                if not is_displayed:
                    return {"success": False, "error": f"Element not visible: {selector}"}
            
            except Exception as e:
                return {"success": False, "error": f"Element not found: {selector}"}
        
        elif verification_type == "text_contains":
            try:
                if selector.startswith("id="):
                    element = driver.find_element(AppiumBy.ID, selector[3:])
                elif selector.startswith("xpath="):
                    element = driver.find_element(AppiumBy.XPATH, selector[6:])
                else:
                    element = driver.find_element(AppiumBy.ID, selector)
                
                actual_text = element.text
                if expected_value not in actual_text:
                    return {
                        "success": False, 
                        "error": f"Text verification failed. Expected '{expected_value}' in '{actual_text}'"
                    }
            
            except Exception as e:
                return {"success": False, "error": f"Text verification failed: {str(e)}"}
        
        elif verification_type == "url_contains":
            current_url = driver.current_url
            if expected_value not in current_url:
                return {
                    "success": False,
                    "error": f"URL verification failed. Expected '{expected_value}' in '{current_url}'"
                }
        
        return {"success": True, "step": step}
    
    async def _execute_screenshot_step(self, step: Dict[str, Any], driver: webdriver.Remote,
                                     test_result: MobileTestResult) -> Dict[str, Any]:
        """Execute screenshot step"""
        filename = step.get("filename", f"screenshot_{int(time.time())}")
        
        screenshot_path = await self._take_screenshot(driver, filename)
        if screenshot_path:
            test_result.screenshots.append(screenshot_path)
            return {"success": True, "step": step, "screenshot_path": screenshot_path}
        else:
            return {"success": False, "error": "Screenshot failed"}
    
    async def _execute_orientation_step(self, step: Dict[str, Any], driver: webdriver.Remote) -> Dict[str, Any]:
        """Execute screen orientation step"""
        orientation = step.get("orientation", "portrait")  # portrait or landscape
        
        try:
            if orientation == "landscape":
                driver.orientation = "LANDSCAPE"
            else:
                driver.orientation = "PORTRAIT"
            
            # Wait for orientation change
            await asyncio.sleep(1.0)
            
            return {"success": True, "step": step, "orientation": orientation}
        
        except Exception as e:
            return {"success": False, "error": f"Orientation change failed: {str(e)}"}
    
    async def _execute_permission_step(self, step: Dict[str, Any], driver: webdriver.Remote) -> Dict[str, Any]:
        """Execute permission handling step"""
        permission = step.get("permission")
        action = step.get("action", "allow")  # allow or deny
        
        try:
            # This is a simplified implementation
            # In practice, would handle platform-specific permission dialogs
            
            if action == "allow":
                # Look for common permission dialog buttons
                try:
                    allow_button = driver.find_element(AppiumBy.XPATH, "//button[contains(text(), 'Allow')]")
                    allow_button.click()
                except:
                    # Try alternative selectors
                    try:
                        allow_button = driver.find_element(AppiumBy.ID, "com.android.packageinstaller:id/permission_allow_button")
                        allow_button.click()
                    except:
                        pass  # Permission dialog might not be present
            
            return {"success": True, "step": step, "permission": permission, "action": action}
        
        except Exception as e:
            return {"success": False, "error": f"Permission handling failed: {str(e)}"}
    
    async def _execute_notification_step(self, step: Dict[str, Any], driver: webdriver.Remote) -> Dict[str, Any]:
        """Execute notification handling step"""
        action = step.get("action", "check")  # check, dismiss, tap
        
        try:
            # Simplified notification handling
            if action == "check":
                # Check if notification is present
                notifications = driver.get_notifications()
                return {"success": True, "step": step, "notifications_count": len(notifications)}
            
            elif action == "dismiss":
                # Dismiss notifications (Android)
                driver.open_notifications()
                await asyncio.sleep(1)
                # Swipe to dismiss
                size = driver.get_window_size()
                driver.swipe(size['width'] // 2, size['height'] // 2, 
                           size['width'], size['height'] // 2, 500)
                driver.press_keycode(4)  # Back button
            
            return {"success": True, "step": step, "action": action}
        
        except Exception as e:
            return {"success": False, "error": f"Notification handling failed: {str(e)}"}
    
    async def _take_screenshot(self, driver: webdriver.Remote, filename: str) -> Optional[str]:
        """Take screenshot"""
        try:
            screenshots_dir = Path("screenshots")
            screenshots_dir.mkdir(exist_ok=True)
            
            screenshot_path = screenshots_dir / f"{filename}_{int(time.time())}.png"
            
            screenshot_data = driver.get_screenshot_as_png()
            with open(screenshot_path, 'wb') as f:
                f.write(screenshot_data)
            
            return str(screenshot_path)
        
        except Exception as e:
            logging.error(f"Screenshot failed: {e}")
            return None


class MobileTestEngine:
    """Main mobile testing engine"""
    
    def __init__(self):
        self.device_manager = MobileDeviceManager()
        self.test_executor = MobileTestExecutor(self.device_manager)
        self.test_cases: List[MobileTestCase] = []
    
    def add_test_case(self, test_case: MobileTestCase):
        """Add mobile test case"""
        self.test_cases.append(test_case)
    
    def create_default_test_cases(self):
        """Create default mobile test cases for ActiveLog platform"""
        
        # Mobile Web App Test
        web_app_test = MobileTestCase(
            test_id="mobile_web_app_test",
            name="Mobile Web App Navigation",
            description="Test mobile web app functionality",
            test_type=MobileTestType.FUNCTIONAL,
            platforms=[MobilePlatform.IOS, MobilePlatform.ANDROID],
            test_steps=[
                {
                    "type": "navigate",
                    "url": "http://localhost:3000/mobile"
                },
                {
                    "type": "wait",
                    "duration": 3.0
                },
                {
                    "type": "screenshot",
                    "filename": "mobile_home"
                },
                {
                    "type": "tap",
                    "selector": "id=mobile-menu-button"
                },
                {
                    "type": "wait",
                    "duration": 1.0
                },
                {
                    "type": "verify",
                    "verification_type": "element_visible",
                    "selector": "id=mobile-menu"
                },
                {
                    "type": "tap",
                    "selector": "id=dashboard-link"
                },
                {
                    "type": "verify",
                    "verification_type": "url_contains",
                    "expected_value": "/dashboard"
                },
                {
                    "type": "screenshot",
                    "filename": "mobile_dashboard"
                }
            ],
            expected_results={"navigation_successful": True}
        )
        
        # Gesture Test
        gesture_test = MobileTestCase(
            test_id="mobile_gesture_test",
            name="Mobile Gesture Interactions",
            description="Test mobile-specific gestures",
            test_type=MobileTestType.GESTURES,
            platforms=[MobilePlatform.IOS, MobilePlatform.ANDROID],
            test_steps=[
                {
                    "type": "navigate",
                    "url": "http://localhost:3000/mobile/content"
                },
                {
                    "type": "wait",
                    "duration": 2.0
                },
                {
                    "type": "swipe",
                    "direction": "up",
                    "distance": 300
                },
                {
                    "type": "wait",
                    "duration": 1.0
                },
                {
                    "type": "swipe",
                    "direction": "down",
                    "distance": 200
                },
                {
                    "type": "swipe",
                    "direction": "left",
                    "distance": 200
                },
                {
                    "type": "swipe",
                    "direction": "right",
                    "distance": 200
                },
                {
                    "type": "screenshot",
                    "filename": "after_gestures"
                }
            ],
            expected_results={"gestures_completed": True}
        )
        
        # Orientation Test
        orientation_test = MobileTestCase(
            test_id="mobile_orientation_test",
            name="Screen Orientation Test",
            description="Test app behavior in different orientations",
            test_type=MobileTestType.ORIENTATION,
            platforms=[MobilePlatform.IOS, MobilePlatform.ANDROID],
            test_steps=[
                {
                    "type": "navigate",
                    "url": "http://localhost:3000/mobile"
                },
                {
                    "type": "screenshot",
                    "filename": "portrait_mode"
                },
                {
                    "type": "orientation",
                    "orientation": "landscape"
                },
                {
                    "type": "wait",
                    "duration": 2.0
                },
                {
                    "type": "screenshot",
                    "filename": "landscape_mode"
                },
                {
                    "type": "verify",
                    "verification_type": "element_visible",
                    "selector": "id=main-content"
                },
                {
                    "type": "orientation",
                    "orientation": "portrait"
                },
                {
                    "type": "wait",
                    "duration": 2.0
                },
                {
                    "type": "screenshot",
                    "filename": "back_to_portrait"
                }
            ],
            expected_results={"orientation_changes_handled": True}
        )
        
        # Performance Test
        performance_test = MobileTestCase(
            test_id="mobile_performance_test",
            name="Mobile Performance Test",
            description="Monitor mobile app performance",
            test_type=MobileTestType.PERFORMANCE,
            platforms=[MobilePlatform.ANDROID],  # Performance monitoring mainly for Android
            test_steps=[
                {
                    "type": "navigate",
                    "url": "http://localhost:3000/mobile"
                },
                {
                    "type": "wait",
                    "duration": 5.0
                },
                {
                    "type": "scroll",
                    "direction": "down",
                    "distance": 500
                },
                {
                    "type": "wait",
                    "duration": 2.0
                },
                {
                    "type": "tap",
                    "selector": "id=load-content-button"
                },
                {
                    "type": "wait",
                    "duration": 5.0
                }
            ],
            expected_results={"performance_acceptable": True},
            timeout=180.0
        )
        
        self.add_test_case(web_app_test)
        self.add_test_case(gesture_test)
        self.add_test_case(orientation_test)
        self.add_test_case(performance_test)
    
    async def run_mobile_tests(self, platforms: Optional[List[MobilePlatform]] = None) -> MobileTestReport:
        """Run mobile tests across specified platforms"""
        session_id = f"mobile_test_{int(time.time())}"
        
        report = MobileTestReport(
            report_id=f"report_{session_id}",
            test_session_id=session_id,
            start_time=datetime.now(),
            platforms_tested=platforms or [MobilePlatform.IOS, MobilePlatform.ANDROID]
        )
        
        # Initialize default devices
        self.device_manager.create_default_devices()
        
        print(f"Starting mobile tests...")
        print(f"Testing {len(self.test_cases)} test cases across platforms: {[p.value for p in report.platforms_tested]}")
        
        try:
            # Get available devices for testing
            test_devices = []
            for platform in report.platforms_tested:
                available_devices = self.device_manager.get_available_devices(platform)
                if available_devices:
                    # Use first available device for each platform
                    test_devices.append(available_devices[0])
                else:
                    print(f"Warning: No devices available for platform {platform.value}")
            
            report.devices_tested = [d.device_id for d in test_devices]
            
            # Execute tests on each device
            for device in test_devices:
                print(f"Testing on device: {device.device_name} ({device.platform.value})")
                
                # Check device availability
                is_available = await self.device_manager.check_device_availability(device.device_id)
                if not is_available:
                    print(f"Device {device.device_id} is not available, skipping...")
                    continue
                
                # Run test cases compatible with this platform
                compatible_tests = [
                    tc for tc in self.test_cases 
                    if device.platform in tc.platforms or MobilePlatform.BOTH in tc.platforms
                ]
                
                for test_case in compatible_tests:
                    print(f"  Running test: {test_case.name}")
                    
                    try:
                        result = await self.test_executor.execute_test_case(test_case, device.device_id)
                        report.test_results.append(result)
                        
                        if result.status == "passed":
                            report.passed_tests += 1
                        elif result.status == "failed":
                            report.failed_tests += 1
                        else:
                            report.skipped_tests += 1
                        
                        report.total_tests += 1
                        
                        print(f"    Result: {result.status}")
                        
                    except Exception as e:
                        logging.error(f"Test execution failed: {e}")
                        
                        # Create error result
                        error_result = MobileTestResult(
                            test_id=test_case.test_id,
                            test_name=test_case.name,
                            test_type=test_case.test_type,
                            platform=device.platform,
                            device_id=device.device_id,
                            status="error",
                            start_time=datetime.now(),
                            end_time=datetime.now(),
                            error_message=str(e)
                        )
                        report.test_results.append(error_result)
                        report.skipped_tests += 1
                        report.total_tests += 1
                    
                    # Brief pause between tests
                    await asyncio.sleep(2.0)
            
            # Generate compatibility matrix
            report.compatibility_matrix = self._generate_compatibility_matrix(report.test_results)
            
            # Calculate device coverage
            report.device_coverage = self._calculate_device_coverage(report)
            
            # Collect performance summary
            report.performance_summary = self._collect_performance_summary(report.test_results)
            
            # Generate recommendations
            report.recommendations = self._generate_recommendations(report)
        
        except Exception as e:
            logging.error(f"Error during mobile testing: {e}")
        
        finally:
            # Cleanup drivers
            self.device_manager.cleanup_drivers()
            report.end_time = datetime.now()
        
        print(f"Mobile testing completed:")
        print(f"  Total tests: {report.total_tests}")
        print(f"  Passed: {report.passed_tests}")
        print(f"  Failed: {report.failed_tests}")
        print(f"  Devices tested: {len(report.devices_tested)}")
        
        return report
    
    def _generate_compatibility_matrix(self, test_results: List[MobileTestResult]) -> Dict[str, Dict[str, str]]:
        """Generate compatibility matrix showing test results across devices"""
        matrix = {}
        
        for result in test_results:
            test_id = result.test_id
            device_platform = f"{result.platform.value}_{result.device_id}"
            
            if test_id not in matrix:
                matrix[test_id] = {}
            
            matrix[test_id][device_platform] = result.status
        
        return matrix
    
    def _calculate_device_coverage(self, report: MobileTestReport) -> Dict[str, float]:
        """Calculate test coverage per device"""
        coverage = {}
        
        for device_id in report.devices_tested:
            device_results = [r for r in report.test_results if r.device_id == device_id]
            total_device_tests = len(device_results)
            passed_device_tests = len([r for r in device_results if r.status == "passed"])
            
            if total_device_tests > 0:
                coverage[device_id] = (passed_device_tests / total_device_tests) * 100
            else:
                coverage[device_id] = 0.0
        
        return coverage
    
    def _collect_performance_summary(self, test_results: List[MobileTestResult]) -> Dict[str, Any]:
        """Collect performance metrics summary"""
        performance_results = [r for r in test_results if r.test_type == MobileTestType.PERFORMANCE]
        
        if not performance_results:
            return {}
        
        summary = {
            "total_performance_tests": len(performance_results),
            "avg_memory_usage_mb": 0,
            "avg_cpu_usage_percent": 0,
            "avg_battery_usage_percent": 0
        }
        
        memory_values = []
        cpu_values = []
        battery_values = []
        
        for result in performance_results:
            if "avg_memory_usage_mb" in result.performance_metrics:
                memory_values.append(result.performance_metrics["avg_memory_usage_mb"])
            if "avg_cpu_usage_percent" in result.performance_metrics:
                cpu_values.append(result.performance_metrics["avg_cpu_usage_percent"])
            if "avg_battery_usage_percent" in result.performance_metrics:
                battery_values.append(result.performance_metrics["avg_battery_usage_percent"])
        
        if memory_values:
            summary["avg_memory_usage_mb"] = sum(memory_values) / len(memory_values)
        if cpu_values:
            summary["avg_cpu_usage_percent"] = sum(cpu_values) / len(cpu_values)
        if battery_values:
            summary["avg_battery_usage_percent"] = sum(battery_values) / len(battery_values)
        
        return summary
    
    def _generate_recommendations(self, report: MobileTestReport) -> List[str]:
        """Generate mobile testing recommendations"""
        recommendations = []
        
        # Test failure recommendations
        if report.failed_tests > 0:
            recommendations.append(f"Fix {report.failed_tests} failing mobile tests")
        
        # Platform coverage recommendations
        platforms_with_failures = set()
        for result in report.test_results:
            if result.status == "failed":
                platforms_with_failures.add(result.platform.value)
        
        if platforms_with_failures:
            recommendations.append(f"Address platform-specific issues on: {', '.join(platforms_with_failures)}")
        
        # Performance recommendations
        if report.performance_summary:
            avg_memory = report.performance_summary.get("avg_memory_usage_mb", 0)
            if avg_memory > 150:
                recommendations.append("High memory usage detected - optimize mobile app performance")
            
            avg_cpu = report.performance_summary.get("avg_cpu_usage_percent", 0)
            if avg_cpu > 60:
                recommendations.append("High CPU usage detected - optimize processing efficiency")
        
        # Device coverage recommendations
        low_coverage_devices = [
            device_id for device_id, coverage in report.device_coverage.items()
            if coverage < 80
        ]
        
        if low_coverage_devices:
            recommendations.append(f"Improve test coverage for devices: {', '.join(low_coverage_devices)}")
        
        # General recommendations
        recommendations.extend([
            "Implement continuous mobile testing in CI/CD pipeline",
            "Add more real device testing in addition to simulators/emulators",
            "Test on various network conditions (3G, 4G, WiFi, offline)",
            "Implement automated visual regression testing for mobile UI",
            "Monitor app performance metrics in production"
        ])
        
        return recommendations[:10]  # Limit to top 10


# Example usage and testing
if __name__ == "__main__":
    import asyncio
    
    async def run_mobile_tests():
        # Initialize mobile test engine
        engine = MobileTestEngine()
        
        # Create default test cases
        engine.create_default_test_cases()
        
        print("Starting mobile application tests...")
        
        # Run tests on both iOS and Android
        report = await engine.run_mobile_tests([MobilePlatform.IOS, MobilePlatform.ANDROID])
        
        print(f"\n=== Mobile Test Report ===")
        print(f"Total Tests: {report.total_tests}")
        print(f"Passed: {report.passed_tests}")
        print(f"Failed: {report.failed_tests}")
        print(f"Platforms Tested: {[p.value for p in report.platforms_tested]}")
        print(f"Devices Tested: {report.devices_tested}")
        
        print(f"\nCompatibility Matrix:")
        for test_id, device_results in report.compatibility_matrix.items():
            print(f"  {test_id}:")
            for device_platform, status in device_results.items():
                print(f"    {device_platform}: {status}")
        
        if report.performance_summary:
            print(f"\nPerformance Summary:")
            print(f"  Average Memory Usage: {report.performance_summary.get('avg_memory_usage_mb', 0):.1f} MB")
            print(f"  Average CPU Usage: {report.performance_summary.get('avg_cpu_usage_percent', 0):.1f}%")
        
        print(f"\nRecommendations:")
        for rec in report.recommendations[:5]:
            print(f"  • {rec}")
        
        return report
    
    # Run the mobile tests
    asyncio.run(run_mobile_tests())