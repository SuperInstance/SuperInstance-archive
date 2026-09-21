#!/usr/bin/env python3
"""
Automated Screenshot Generation System
Generates app store screenshots for all ActiveLog applications
"""

import os
import json
import yaml
import asyncio
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import subprocess
from datetime import datetime
import logging

# Screenshot generation using Playwright for web-based UI
try:
    from playwright.async_api import async_playwright, Page, Browser
except ImportError:
    print("Please install playwright: pip install playwright")
    exit(1)

# Image manipulation
try:
    from PIL import Image, ImageDraw, ImageFont
    import cv2
    import numpy as np
except ImportError:
    print("Please install Pillow and OpenCV: pip install Pillow opencv-python")
    exit(1)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Platform(Enum):
    IOS = "ios"
    ANDROID = "android"

class DeviceType(Enum):
    PHONE_PORTRAIT = "phone_portrait"
    PHONE_LANDSCAPE = "phone_landscape"
    TABLET_7_INCH = "7_inch_tablet"
    TABLET_10_INCH = "10_inch_tablet"
    IPHONE_6_7_INCH = "6.7_inch_display"
    IPHONE_6_1_INCH = "6.1_inch_display"
    IPHONE_5_5_INCH = "5.5_inch_display"
    IPAD_12_9_INCH = "12.9_inch_display"
    IPAD_11_INCH = "11_inch_display"

@dataclass
class ScreenshotConfig:
    width: int
    height: int
    device_name: str
    platform: Platform
    device_type: DeviceType

@dataclass
class SceneConfig:
    name: str
    title: str
    description: str
    url_path: str
    wait_selector: Optional[str] = None
    custom_actions: Optional[List[str]] = None

class ScreenshotGenerator:
    """Generates app store screenshots for ActiveLog applications"""
    
    def __init__(self):
        self.base_url = "http://localhost:3000"  # Development server
        self.output_dir = "/home/activeloguser/activelog/deployment/stores/screenshots"
        self.device_configs = self._load_device_configs()
        self.apps = ["activelog", "activelog-ai", "activeledger"]
        
    def _load_device_configs(self) -> Dict[DeviceType, ScreenshotConfig]:
        """Load device configuration for screenshots"""
        return {
            # iOS Devices
            DeviceType.IPHONE_6_7_INCH: ScreenshotConfig(
                width=1290, height=2796, device_name="iPhone 14 Pro Max",
                platform=Platform.IOS, device_type=DeviceType.IPHONE_6_7_INCH
            ),
            DeviceType.IPHONE_6_1_INCH: ScreenshotConfig(
                width=1179, height=2556, device_name="iPhone 14 Pro",
                platform=Platform.IOS, device_type=DeviceType.IPHONE_6_1_INCH
            ),
            DeviceType.IPHONE_5_5_INCH: ScreenshotConfig(
                width=1242, height=2208, device_name="iPhone 8 Plus",
                platform=Platform.IOS, device_type=DeviceType.IPHONE_5_5_INCH
            ),
            DeviceType.IPAD_12_9_INCH: ScreenshotConfig(
                width=2048, height=2732, device_name="iPad Pro 12.9\"",
                platform=Platform.IOS, device_type=DeviceType.IPAD_12_9_INCH
            ),
            DeviceType.IPAD_11_INCH: ScreenshotConfig(
                width=1668, height=2388, device_name="iPad Pro 11\"",
                platform=Platform.IOS, device_type=DeviceType.IPAD_11_INCH
            ),
            
            # Android Devices
            DeviceType.PHONE_PORTRAIT: ScreenshotConfig(
                width=1080, height=1920, device_name="Android Phone",
                platform=Platform.ANDROID, device_type=DeviceType.PHONE_PORTRAIT
            ),
            DeviceType.PHONE_LANDSCAPE: ScreenshotConfig(
                width=1920, height=1080, device_name="Android Phone Landscape",
                platform=Platform.ANDROID, device_type=DeviceType.PHONE_LANDSCAPE
            ),
            DeviceType.TABLET_7_INCH: ScreenshotConfig(
                width=1200, height=1920, device_name="Android 7\" Tablet",
                platform=Platform.ANDROID, device_type=DeviceType.TABLET_7_INCH
            ),
            DeviceType.TABLET_10_INCH: ScreenshotConfig(
                width=1600, height=2560, device_name="Android 10\" Tablet",
                platform=Platform.ANDROID, device_type=DeviceType.TABLET_10_INCH
            )
        }
    
    async def generate_all_screenshots(self):
        """Generate screenshots for all apps and devices"""
        logger.info("Starting screenshot generation for all ActiveLog apps")
        
        # Create output directories
        for app in self.apps:
            for platform in Platform:
                os.makedirs(
                    os.path.join(self.output_dir, app, platform.value),
                    exist_ok=True
                )
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            
            for app in self.apps:
                await self._generate_app_screenshots(browser, app)
            
            await browser.close()
        
        logger.info("Screenshot generation completed")
    
    async def _generate_app_screenshots(self, browser: Browser, app: str):
        """Generate screenshots for a specific app"""
        logger.info(f"Generating screenshots for {app}")
        
        # Load app metadata
        metadata = self._load_app_metadata(app)
        scenes = metadata.get("screenshots", {}).get("scenes", [])
        required_sizes = metadata.get("screenshots", {}).get("required_sizes", {})
        
        for scene_config in scenes:
            scene = SceneConfig(
                name=scene_config["name"],
                title=scene_config["title"],
                description=scene_config["description"],
                url_path=f"/{app}/{scene_config['name']}",
                wait_selector=scene_config.get("wait_selector"),
                custom_actions=scene_config.get("custom_actions")
            )
            
            # Generate for iOS devices
            if "ios" in required_sizes:
                for device_type_str in required_sizes["ios"]:
                    device_type = DeviceType(device_type_str)
                    await self._capture_scene_screenshot(
                        browser, app, scene, device_type
                    )
            
            # Generate for Android devices
            if "android" in required_sizes:
                for device_type_str in required_sizes["android"]:
                    device_type = DeviceType(device_type_str)
                    await self._capture_scene_screenshot(
                        browser, app, scene, device_type
                    )
    
    async def _capture_scene_screenshot(
        self, 
        browser: Browser, 
        app: str, 
        scene: SceneConfig, 
        device_type: DeviceType
    ):
        """Capture a screenshot for a specific scene and device"""
        config = self.device_configs[device_type]
        page = await browser.new_page()
        
        try:
            # Set viewport
            await page.set_viewport_size(
                {"width": config.width, "height": config.height}
            )
            
            # Navigate to scene
            url = f"{self.base_url}{scene.url_path}"
            await page.goto(url)
            
            # Wait for content to load
            if scene.wait_selector:
                await page.wait_for_selector(scene.wait_selector)
            else:
                await page.wait_for_load_state("networkidle")
            
            # Perform custom actions if specified
            if scene.custom_actions:
                await self._perform_custom_actions(page, scene.custom_actions)
            
            # Additional wait for animations
            await page.wait_for_timeout(2000)
            
            # Capture screenshot
            screenshot_path = os.path.join(
                self.output_dir,
                app,
                config.platform.value,
                f"{scene.name}_{config.device_type.value}.png"
            )
            
            await page.screenshot(path=screenshot_path, full_page=False)
            
            # Add device frame and annotations
            await self._add_device_frame_and_annotations(
                screenshot_path, config, scene
            )
            
            logger.info(f"Generated: {screenshot_path}")
            
        except Exception as e:
            logger.error(f"Failed to capture {app}/{scene.name}/{device_type.value}: {e}")
        
        finally:
            await page.close()
    
    async def _perform_custom_actions(self, page: Page, actions: List[str]):
        """Perform custom actions on the page before screenshot"""
        for action in actions:
            if action.startswith("click:"):
                selector = action.split(":", 1)[1]
                await page.click(selector)
                await page.wait_for_timeout(1000)
            elif action.startswith("hover:"):
                selector = action.split(":", 1)[1]
                await page.hover(selector)
                await page.wait_for_timeout(500)
            elif action.startswith("fill:"):
                parts = action.split(":", 2)
                selector, text = parts[1], parts[2]
                await page.fill(selector, text)
            elif action.startswith("wait:"):
                ms = int(action.split(":", 1)[1])
                await page.wait_for_timeout(ms)
    
    async def _add_device_frame_and_annotations(
        self, 
        screenshot_path: str, 
        config: ScreenshotConfig, 
        scene: SceneConfig
    ):
        """Add device frame and marketing annotations to screenshot"""
        try:
            # Load the screenshot
            img = Image.open(screenshot_path)
            
            # Add device frame if available
            if config.platform == Platform.IOS:
                img = self._add_ios_device_frame(img, config)
            else:
                img = self._add_android_device_frame(img, config)
            
            # Add title and description overlay
            img = self._add_marketing_overlay(img, scene, config)
            
            # Save the enhanced screenshot
            img.save(screenshot_path, quality=95, optimize=True)
            
        except Exception as e:
            logger.error(f"Failed to enhance screenshot {screenshot_path}: {e}")
    
    def _add_ios_device_frame(self, img: Image.Image, config: ScreenshotConfig) -> Image.Image:
        """Add iOS device frame around screenshot"""
        # This would load and composite device frame images
        # For now, just add a simple border
        border_size = 20
        border_color = "#000000"
        
        # Create new image with border
        new_width = img.width + (border_size * 2)
        new_height = img.height + (border_size * 2)
        bordered_img = Image.new("RGB", (new_width, new_height), border_color)
        
        # Paste original image in center
        bordered_img.paste(img, (border_size, border_size))
        
        return bordered_img
    
    def _add_android_device_frame(self, img: Image.Image, config: ScreenshotConfig) -> Image.Image:
        """Add Android device frame around screenshot"""
        # Similar to iOS but with Material Design styling
        border_size = 15
        border_color = "#121212"  # Material Dark
        
        new_width = img.width + (border_size * 2)
        new_height = img.height + (border_size * 2)
        bordered_img = Image.new("RGB", (new_width, new_height), border_color)
        bordered_img.paste(img, (border_size, border_size))
        
        return bordered_img
    
    def _add_marketing_overlay(
        self, 
        img: Image.Image, 
        scene: SceneConfig, 
        config: ScreenshotConfig
    ) -> Image.Image:
        """Add marketing text overlay to screenshot"""
        try:
            draw = ImageDraw.Draw(img)
            
            # Try to load a nice font
            try:
                title_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 48)
                desc_font = ImageFont.truetype("DejaVuSans.ttf", 32)
            except:
                title_font = ImageFont.load_default()
                desc_font = ImageFont.load_default()
            
            # Add title at the top
            title_y = 50
            draw.text(
                (50, title_y), 
                scene.title, 
                fill="#FFFFFF", 
                font=title_font,
                stroke_width=2,
                stroke_fill="#000000"
            )
            
            # Add description
            desc_y = title_y + 80
            # Wrap text for description
            desc_lines = self._wrap_text(scene.description, desc_font, img.width - 100)
            for i, line in enumerate(desc_lines):
                draw.text(
                    (50, desc_y + (i * 40)), 
                    line, 
                    fill="#CCCCCC", 
                    font=desc_font,
                    stroke_width=1,
                    stroke_fill="#000000"
                )
            
            return img
            
        except Exception as e:
            logger.error(f"Failed to add marketing overlay: {e}")
            return img
    
    def _wrap_text(self, text: str, font: ImageFont.ImageFont, max_width: int) -> List[str]:
        """Wrap text to fit within specified width"""
        words = text.split()
        lines = []
        current_line = []
        
        for word in words:
            test_line = " ".join(current_line + [word])
            bbox = font.getbbox(test_line)
            width = bbox[2] - bbox[0]
            
            if width <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(" ".join(current_line))
                    current_line = [word]
                else:
                    lines.append(word)
        
        if current_line:
            lines.append(" ".join(current_line))
        
        return lines[:3]  # Limit to 3 lines
    
    def _load_app_metadata(self, app: str) -> Dict:
        """Load app metadata from YAML file"""
        metadata_file = os.path.join(
            "/home/activeloguser/activelog/deployment/stores/metadata",
            f"{app}-store.yaml"
        )
        
        try:
            with open(metadata_file, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Failed to load metadata for {app}: {e}")
            return {}
    
    async def generate_app_icons(self):
        """Generate app icons in various sizes"""
        logger.info("Generating app icons")
        
        icon_sizes = {
            "ios": [20, 29, 40, 58, 60, 76, 80, 87, 120, 152, 167, 180, 1024],
            "android": [36, 48, 72, 96, 144, 192, 512]
        }
        
        for app in self.apps:
            for platform, sizes in icon_sizes.items():
                for size in sizes:
                    await self._generate_app_icon(app, platform, size)
    
    async def _generate_app_icon(self, app: str, platform: str, size: int):
        """Generate a single app icon"""
        # This would create app icons based on brand guidelines
        # For now, create a simple colored square with app initial
        
        colors = {
            "activelog": "#2196F3",      # Blue
            "activelog-ai": "#9C27B0",   # Purple
            "activeledger": "#4CAF50"    # Green
        }
        
        color = colors.get(app, "#607D8B")
        initial = app[0].upper()
        
        # Create icon
        img = Image.new("RGB", (size, size), color)
        draw = ImageDraw.Draw(img)
        
        # Add text
        try:
            font_size = max(size // 3, 12)
            font = ImageFont.truetype("DejaVuSans-Bold.ttf", font_size)
        except:
            font = ImageFont.load_default()
        
        # Center the text
        bbox = draw.textbbox((0, 0), initial, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        x = (size - text_width) // 2
        y = (size - text_height) // 2
        
        draw.text((x, y), initial, fill="#FFFFFF", font=font)
        
        # Save icon
        icon_dir = os.path.join(self.output_dir, app, platform, "icons")
        os.makedirs(icon_dir, exist_ok=True)
        
        icon_path = os.path.join(icon_dir, f"icon_{size}x{size}.png")
        img.save(icon_path, quality=95)
        
        logger.info(f"Generated icon: {icon_path}")

async def main():
    """Main function to run screenshot generation"""
    generator = ScreenshotGenerator()
    
    # Generate app icons
    await generator.generate_app_icons()
    
    # Generate screenshots
    await generator.generate_all_screenshots()
    
    print("Screenshot generation completed!")
    print(f"Output directory: {generator.output_dir}")

if __name__ == "__main__":
    asyncio.run(main())