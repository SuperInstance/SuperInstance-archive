#!/usr/bin/env python3
"""
Custom Branding Tools System
Advanced branding and theme customization system with asset management,
multi-brand support, theme engine, and brand guideline enforcement.
"""

import asyncio
import json
import logging
import sqlite3
import uuid
import os
import shutil
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import aiofiles
import hashlib
from PIL import Image, ImageDraw, ImageFont
import colorsys
import re
from io import BytesIO
import base64

logger = logging.getLogger(__name__)

class BrandAssetType:
    LOGO = "logo"
    ICON = "icon"
    FAVICON = "favicon"
    BANNER = "banner"
    BACKGROUND = "background"
    PATTERN = "pattern"
    FONT = "font"
    VIDEO = "video"
    AUDIO = "audio"

class ThemeMode:
    LIGHT = "light"
    DARK = "dark"
    AUTO = "auto"
    CUSTOM = "custom"

class CustomBrandingSystem:
    def __init__(self):
        self.db_path = "/home/activeloguser/activelog/services/enterprise-custom/data/enterprise_custom.db"
        self.assets_path = "/home/activeloguser/activelog/services/enterprise-custom/data/brand_assets"
        self.brand_configurations = {}
        self.asset_storage = {}
        self.theme_templates = {}
        self.brand_guidelines = {}
        self.supported_formats = {
            "image": [".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"],
            "font": [".ttf", ".otf", ".woff", ".woff2"],
            "video": [".mp4", ".webm", ".mov"],
            "audio": [".mp3", ".wav", ".ogg"]
        }
        
    async def initialize(self):
        """Initialize the custom branding system"""
        try:
            await self._setup_database_tables()
            await self._create_asset_directories()
            await self._load_theme_templates()
            await self._load_existing_brands()
            await self._initialize_color_tools()
            logger.info("Custom branding system initialized")
        except Exception as e:
            logger.error(f"Failed to initialize branding system: {e}")
            raise

    async def _setup_database_tables(self):
        """Setup database tables for branding"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Brand configurations table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS brand_configurations (
                id TEXT PRIMARY KEY,
                organization_id TEXT NOT NULL,
                brand_name TEXT NOT NULL,
                is_primary BOOLEAN DEFAULT FALSE,
                status TEXT DEFAULT 'draft',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data TEXT NOT NULL,
                FOREIGN KEY (organization_id) REFERENCES enterprise_organizations (id)
            )
        ''')
        
        # Brand assets table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS brand_assets (
                id TEXT PRIMARY KEY,
                brand_id TEXT NOT NULL,
                asset_type TEXT NOT NULL,
                asset_name TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_size INTEGER,
                mime_type TEXT,
                dimensions TEXT,
                alt_text TEXT,
                tags TEXT,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT,
                FOREIGN KEY (brand_id) REFERENCES brand_configurations (id)
            )
        ''')
        
        # Theme configurations table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS theme_configurations (
                id TEXT PRIMARY KEY,
                brand_id TEXT NOT NULL,
                theme_name TEXT NOT NULL,
                theme_mode TEXT DEFAULT 'light',
                color_palette TEXT NOT NULL,
                typography TEXT,
                spacing_scale TEXT,
                component_styles TEXT,
                custom_css TEXT,
                is_active BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data TEXT NOT NULL,
                FOREIGN KEY (brand_id) REFERENCES brand_configurations (id)
            )
        ''')
        
        # Brand guidelines table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS brand_guidelines (
                id TEXT PRIMARY KEY,
                brand_id TEXT NOT NULL,
                guideline_type TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                rules TEXT NOT NULL,
                examples TEXT,
                enforcement_level TEXT DEFAULT 'warning',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (brand_id) REFERENCES brand_configurations (id)
            )
        ''')
        
        conn.commit()
        conn.close()

    async def _create_asset_directories(self):
        """Create directories for storing brand assets"""
        directories = [
            self.assets_path,
            f"{self.assets_path}/logos",
            f"{self.assets_path}/icons",
            f"{self.assets_path}/backgrounds",
            f"{self.assets_path}/fonts",
            f"{self.assets_path}/generated",
            f"{self.assets_path}/temp"
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)

    async def _load_theme_templates(self):
        """Load pre-defined theme templates"""
        self.theme_templates = {
            "modern_corporate": {
                "name": "Modern Corporate",
                "description": "Clean, professional design suitable for corporate environments",
                "color_palette": {
                    "primary": "#0066CC",
                    "secondary": "#FF6B35",
                    "accent": "#28A745",
                    "neutral": "#6C757D",
                    "background": "#FFFFFF",
                    "surface": "#F8F9FA",
                    "text_primary": "#212529",
                    "text_secondary": "#6C757D"
                },
                "typography": {
                    "font_family_primary": "Inter, system-ui, sans-serif",
                    "font_family_secondary": "Roboto, sans-serif",
                    "font_family_monospace": "Fira Code, monospace",
                    "font_sizes": {
                        "xs": "0.75rem",
                        "sm": "0.875rem",
                        "base": "1rem",
                        "lg": "1.125rem",
                        "xl": "1.25rem",
                        "2xl": "1.5rem",
                        "3xl": "1.875rem",
                        "4xl": "2.25rem"
                    },
                    "font_weights": {
                        "light": 300,
                        "normal": 400,
                        "medium": 500,
                        "semibold": 600,
                        "bold": 700
                    }
                },
                "spacing": {
                    "xs": "0.25rem",
                    "sm": "0.5rem",
                    "md": "1rem",
                    "lg": "1.5rem",
                    "xl": "2rem",
                    "2xl": "3rem"
                },
                "border_radius": {
                    "sm": "0.25rem",
                    "md": "0.5rem",
                    "lg": "0.75rem",
                    "xl": "1rem"
                },
                "shadows": {
                    "sm": "0 1px 2px 0 rgba(0, 0, 0, 0.05)",
                    "md": "0 4px 6px -1px rgba(0, 0, 0, 0.1)",
                    "lg": "0 10px 15px -3px rgba(0, 0, 0, 0.1)"
                }
            },
            "creative_vibrant": {
                "name": "Creative Vibrant",
                "description": "Bold, colorful design for creative industries",
                "color_palette": {
                    "primary": "#FF6B6B",
                    "secondary": "#4ECDC4",
                    "accent": "#FFE66D",
                    "neutral": "#95A5A6",
                    "background": "#FFFFFF",
                    "surface": "#F7F9FC",
                    "text_primary": "#2C3E50",
                    "text_secondary": "#7F8C8D"
                },
                "typography": {
                    "font_family_primary": "Poppins, sans-serif",
                    "font_family_secondary": "Open Sans, sans-serif",
                    "font_family_monospace": "Source Code Pro, monospace"
                }
            },
            "minimalist_clean": {
                "name": "Minimalist Clean",
                "description": "Simple, clean design with focus on content",
                "color_palette": {
                    "primary": "#000000",
                    "secondary": "#FFFFFF",
                    "accent": "#E0E0E0",
                    "neutral": "#757575",
                    "background": "#FAFAFA",
                    "surface": "#FFFFFF",
                    "text_primary": "#212121",
                    "text_secondary": "#757575"
                }
            },
            "dark_theme": {
                "name": "Dark Professional",
                "description": "Professional dark theme for reduced eye strain",
                "color_palette": {
                    "primary": "#BB86FC",
                    "secondary": "#03DAC6",
                    "accent": "#CF6679",
                    "neutral": "#FFFFFF",
                    "background": "#121212",
                    "surface": "#1E1E1E",
                    "text_primary": "#FFFFFF",
                    "text_secondary": "#AAAAAA"
                }
            }
        }

    async def _load_existing_brands(self):
        """Load existing brand configurations"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, organization_id, data FROM brand_configurations
            ''')
            
            brands = cursor.fetchall()
            for brand_id, org_id, data_json in brands:
                brand_data = json.loads(data_json)
                self.brand_configurations[brand_id] = brand_data
                
            conn.close()
            logger.info(f"Loaded {len(brands)} existing brand configurations")
        except Exception as e:
            logger.error(f"Failed to load existing brands: {e}")

    async def _initialize_color_tools(self):
        """Initialize color manipulation tools"""
        self.color_tools = {
            "palette_generators": ["complementary", "triadic", "analogous", "split_complementary"],
            "accessibility_checkers": ["wcag_aa", "wcag_aaa"],
            "color_spaces": ["rgb", "hsl", "hsv", "lab", "hex"]
        }

    async def upload_assets(self, files: List, metadata: dict = None) -> Dict[str, Any]:
        """Upload and process brand assets"""
        try:
            uploaded_assets = []
            processing_errors = []
            
            for file in files:
                try:
                    # Validate file
                    validation_result = await self._validate_asset_file(file)
                    if not validation_result["valid"]:
                        processing_errors.append({
                            "filename": file.filename,
                            "error": validation_result["error"]
                        })
                        continue
                    
                    # Generate asset ID
                    asset_id = f"ASSET_{uuid.uuid4().hex[:12].upper()}"
                    
                    # Determine asset type
                    asset_type = await self._determine_asset_type(file)
                    
                    # Create file path
                    file_extension = Path(file.filename).suffix.lower()
                    filename = f"{asset_id}{file_extension}"
                    asset_directory = f"{self.assets_path}/{asset_type}s"
                    file_path = f"{asset_directory}/{filename}"
                    
                    # Save file
                    async with aiofiles.open(file_path, 'wb') as f:
                        content = await file.read()
                        await f.write(content)
                    
                    # Process asset
                    processed_asset = await self._process_asset(asset_id, file_path, asset_type, file)
                    
                    # Generate variations if needed
                    variations = await self._generate_asset_variations(processed_asset)
                    
                    # Store asset metadata
                    asset_metadata = {
                        "id": asset_id,
                        "original_filename": file.filename,
                        "asset_type": asset_type,
                        "file_path": file_path,
                        "file_size": len(content),
                        "mime_type": file.content_type,
                        "dimensions": processed_asset.get("dimensions"),
                        "color_palette": processed_asset.get("dominant_colors"),
                        "variations": variations,
                        "upload_metadata": metadata or {},
                        "uploaded_at": datetime.now().isoformat()
                    }
                    
                    self.asset_storage[asset_id] = asset_metadata
                    uploaded_assets.append(asset_metadata)
                    
                except Exception as e:
                    processing_errors.append({
                        "filename": file.filename,
                        "error": str(e)
                    })
            
            return {
                "status": "success" if uploaded_assets else "partial_error",
                "uploaded_assets": uploaded_assets,
                "total_uploaded": len(uploaded_assets),
                "processing_errors": processing_errors,
                "asset_ids": [asset["id"] for asset in uploaded_assets]
            }
            
        except Exception as e:
            logger.error(f"Failed to upload assets: {e}")
            return {
                "status": "error",
                "message": str(e)
            }

    async def _validate_asset_file(self, file) -> Dict[str, Any]:
        """Validate uploaded asset file"""
        # Check file size (max 50MB)
        if hasattr(file, 'size') and file.size > 50 * 1024 * 1024:
            return {
                "valid": False,
                "error": "File size exceeds 50MB limit"
            }
        
        # Check file extension
        file_extension = Path(file.filename).suffix.lower()
        valid_extensions = []
        for format_type, extensions in self.supported_formats.items():
            valid_extensions.extend(extensions)
        
        if file_extension not in valid_extensions:
            return {
                "valid": False,
                "error": f"Unsupported file format: {file_extension}"
            }
        
        # Check filename for security
        if re.search(r'[<>:"/\\|?*]', file.filename):
            return {
                "valid": False,
                "error": "Filename contains invalid characters"
            }
        
        return {"valid": True}

    async def _determine_asset_type(self, file) -> str:
        """Determine asset type based on filename and content"""
        filename = file.filename.lower()
        file_extension = Path(filename).suffix.lower()
        
        # Determine by filename patterns
        if "logo" in filename:
            return BrandAssetType.LOGO
        elif "icon" in filename:
            return BrandAssetType.ICON
        elif "favicon" in filename:
            return BrandAssetType.FAVICON
        elif "banner" in filename:
            return BrandAssetType.BANNER
        elif "background" in filename:
            return BrandAssetType.BACKGROUND
        elif "pattern" in filename:
            return BrandAssetType.PATTERN
        
        # Determine by file type
        if file_extension in self.supported_formats["font"]:
            return BrandAssetType.FONT
        elif file_extension in self.supported_formats["video"]:
            return BrandAssetType.VIDEO
        elif file_extension in self.supported_formats["audio"]:
            return BrandAssetType.AUDIO
        else:
            return BrandAssetType.LOGO  # Default for images

    async def _process_asset(self, asset_id: str, file_path: str, asset_type: str, file) -> Dict[str, Any]:
        """Process uploaded asset"""
        processed_data = {
            "asset_id": asset_id,
            "asset_type": asset_type
        }
        
        if asset_type in [BrandAssetType.LOGO, BrandAssetType.ICON, BrandAssetType.BANNER, BrandAssetType.BACKGROUND]:
            # Process image assets
            processed_data.update(await self._process_image_asset(file_path))
        elif asset_type == BrandAssetType.FONT:
            # Process font assets
            processed_data.update(await self._process_font_asset(file_path))
        
        return processed_data

    async def _process_image_asset(self, file_path: str) -> Dict[str, Any]:
        """Process image asset"""
        try:
            with Image.open(file_path) as img:
                # Get image dimensions
                width, height = img.size
                
                # Extract dominant colors
                dominant_colors = await self._extract_dominant_colors(img)
                
                # Generate color palette
                color_palette = await self._generate_color_palette(dominant_colors)
                
                # Check image quality
                quality_score = await self._assess_image_quality(img)
                
                return {
                    "dimensions": {"width": width, "height": height},
                    "format": img.format,
                    "mode": img.mode,
                    "dominant_colors": dominant_colors,
                    "suggested_palette": color_palette,
                    "quality_score": quality_score,
                    "has_transparency": img.mode in ('RGBA', 'LA', 'P')
                }
        except Exception as e:
            logger.error(f"Failed to process image asset: {e}")
            return {}

    async def _extract_dominant_colors(self, img: Image.Image, num_colors: int = 5) -> List[str]:
        """Extract dominant colors from image"""
        try:
            # Resize image for faster processing
            img_small = img.resize((150, 150))
            
            # Convert to RGB if necessary
            if img_small.mode != 'RGB':
                img_small = img_small.convert('RGB')
            
            # Get color histogram
            colors = img_small.getcolors(maxcolors=256*256*256)
            if not colors:
                return ["#000000"]
            
            # Sort by frequency and get top colors
            colors.sort(key=lambda x: x[0], reverse=True)
            
            dominant_colors = []
            for count, color in colors[:num_colors]:
                hex_color = "#{:02x}{:02x}{:02x}".format(color[0], color[1], color[2])
                dominant_colors.append(hex_color)
            
            return dominant_colors
            
        except Exception as e:
            logger.error(f"Failed to extract dominant colors: {e}")
            return ["#000000"]

    async def _generate_color_palette(self, base_colors: List[str]) -> Dict[str, str]:
        """Generate complementary color palette"""
        try:
            if not base_colors:
                return {}
            
            primary_color = base_colors[0]
            
            # Convert hex to HSV
            primary_rgb = tuple(int(primary_color[i:i+2], 16) for i in (1, 3, 5))
            primary_hsv = colorsys.rgb_to_hsv(primary_rgb[0]/255, primary_rgb[1]/255, primary_rgb[2]/255)
            
            # Generate complementary colors
            complementary_h = (primary_hsv[0] + 0.5) % 1
            analogous_h1 = (primary_hsv[0] + 0.083) % 1  # +30 degrees
            analogous_h2 = (primary_hsv[0] - 0.083) % 1  # -30 degrees
            
            def hsv_to_hex(h, s, v):
                rgb = colorsys.hsv_to_rgb(h, s, v)
                return "#{:02x}{:02x}{:02x}".format(
                    int(rgb[0] * 255),
                    int(rgb[1] * 255),
                    int(rgb[2] * 255)
                )
            
            palette = {
                "primary": primary_color,
                "complementary": hsv_to_hex(complementary_h, primary_hsv[1], primary_hsv[2]),
                "analogous_1": hsv_to_hex(analogous_h1, primary_hsv[1], primary_hsv[2]),
                "analogous_2": hsv_to_hex(analogous_h2, primary_hsv[1], primary_hsv[2]),
                "light_variant": hsv_to_hex(primary_hsv[0], primary_hsv[1] * 0.5, min(primary_hsv[2] * 1.2, 1)),
                "dark_variant": hsv_to_hex(primary_hsv[0], min(primary_hsv[1] * 1.2, 1), primary_hsv[2] * 0.8)
            }
            
            return palette
            
        except Exception as e:
            logger.error(f"Failed to generate color palette: {e}")
            return {}

    async def _assess_image_quality(self, img: Image.Image) -> float:
        """Assess image quality score"""
        try:
            width, height = img.size
            
            # Basic quality metrics
            resolution_score = min((width * height) / (1920 * 1080), 1.0)  # Normalize to 1080p
            aspect_ratio = width / height
            aspect_score = 1.0 if 0.5 <= aspect_ratio <= 2.0 else 0.7  # Penalize extreme ratios
            
            # Check if image has sufficient contrast
            if img.mode == 'RGB':
                grayscale = img.convert('L')
                histogram = grayscale.histogram()
                contrast_score = (max(histogram) - min(histogram)) / sum(histogram)
            else:
                contrast_score = 0.8  # Default for non-RGB images
            
            overall_score = (resolution_score * 0.4 + aspect_score * 0.3 + contrast_score * 0.3)
            return min(round(overall_score, 2), 1.0)
            
        except Exception as e:
            logger.error(f"Failed to assess image quality: {e}")
            return 0.5

    async def _process_font_asset(self, file_path: str) -> Dict[str, Any]:
        """Process font asset"""
        try:
            file_size = os.path.getsize(file_path)
            font_name = Path(file_path).stem
            
            return {
                "font_name": font_name,
                "file_size": file_size,
                "format": Path(file_path).suffix.lower(),
                "web_compatible": Path(file_path).suffix.lower() in ['.woff', '.woff2']
            }
        except Exception as e:
            logger.error(f"Failed to process font asset: {e}")
            return {}

    async def _generate_asset_variations(self, asset_data: dict) -> Dict[str, str]:
        """Generate variations of the asset"""
        variations = {}
        asset_type = asset_data.get("asset_type")
        
        if asset_type in [BrandAssetType.LOGO, BrandAssetType.ICON]:
            # Generate different sizes for logos/icons
            sizes = ["small", "medium", "large", "xlarge"]
            for size in sizes:
                variation_path = await self._generate_sized_variation(asset_data, size)
                if variation_path:
                    variations[f"{size}_version"] = variation_path
        
        return variations

    async def _generate_sized_variation(self, asset_data: dict, size: str) -> str:
        """Generate sized variation of asset"""
        # This would contain actual image resizing logic
        # For now, returning a placeholder path
        asset_id = asset_data.get("asset_id")
        return f"{self.assets_path}/generated/{asset_id}_{size}.png"

    async def configure_branding(self, org_id: str, branding_data: dict) -> Dict[str, Any]:
        """Configure custom branding for organization"""
        try:
            brand_id = branding_data.get("brand_id")
            if not brand_id:
                brand_id = f"BRAND_{uuid.uuid4().hex[:12].upper()}"
            
            # Build brand configuration
            brand_config = {
                "id": brand_id,
                "organization_id": org_id,
                "brand_name": branding_data.get("brand_name", "Default Brand"),
                "is_primary": branding_data.get("is_primary", True),
                "logo_assets": branding_data.get("logo_assets", {}),
                "color_palette": branding_data.get("color_palette", {}),
                "typography": branding_data.get("typography", {}),
                "spacing": branding_data.get("spacing", {}),
                "brand_voice": branding_data.get("brand_voice", {}),
                "usage_guidelines": branding_data.get("usage_guidelines", {}),
                "component_styles": branding_data.get("component_styles", {}),
                "custom_css": branding_data.get("custom_css", ""),
                "status": "active",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            # Validate brand configuration
            validation_result = await self._validate_brand_configuration(brand_config)
            if not validation_result["valid"]:
                return {
                    "status": "error",
                    "message": "Brand configuration validation failed",
                    "errors": validation_result["errors"]
                }
            
            # Generate theme configurations
            themes = await self._generate_brand_themes(brand_config)
            brand_config["themes"] = themes
            
            # Create brand guidelines
            guidelines = await self._generate_brand_guidelines(brand_config)
            brand_config["guidelines"] = guidelines
            
            # Store brand configuration
            await self._store_brand_configuration(brand_config)
            
            # Generate CSS files
            css_files = await self._generate_brand_css(brand_config)
            
            self.brand_configurations[brand_id] = brand_config
            
            return {
                "status": "success",
                "brand_id": brand_id,
                "brand_name": brand_config["brand_name"],
                "configuration": brand_config,
                "generated_themes": len(themes),
                "css_files": css_files,
                "preview_url": f"/preview/brand/{brand_id}",
                "next_steps": [
                    "Review generated themes",
                    "Test brand consistency",
                    "Apply to applications",
                    "Set up brand guidelines enforcement"
                ]
            }
            
        except Exception as e:
            logger.error(f"Failed to configure branding: {e}")
            return {
                "status": "error",
                "message": str(e)
            }

    async def _validate_brand_configuration(self, brand_config: dict) -> Dict[str, Any]:
        """Validate brand configuration"""
        errors = []
        
        # Required fields
        required_fields = ["brand_name", "organization_id"]
        for field in required_fields:
            if not brand_config.get(field):
                errors.append(f"Missing required field: {field}")
        
        # Color palette validation
        color_palette = brand_config.get("color_palette", {})
        for color_name, color_value in color_palette.items():
            if not self._is_valid_color(color_value):
                errors.append(f"Invalid color format for {color_name}: {color_value}")
        
        # Typography validation
        typography = brand_config.get("typography", {})
        if typography:
            font_families = typography.get("font_families", [])
            for font_family in font_families:
                if not isinstance(font_family, str) or len(font_family.strip()) == 0:
                    errors.append(f"Invalid font family: {font_family}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }

    def _is_valid_color(self, color: str) -> bool:
        """Validate color format"""
        if not isinstance(color, str):
            return False
        
        # Hex color
        if color.startswith('#') and len(color) in [4, 7]:
            try:
                int(color[1:], 16)
                return True
            except ValueError:
                return False
        
        # RGB/RGBA
        rgb_pattern = r'^rgba?\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*(?:,\s*[\d.]+)?\s*\)$'
        if re.match(rgb_pattern, color):
            return True
        
        # HSL/HSLA
        hsl_pattern = r'^hsla?\(\s*\d+\s*,\s*\d+%\s*,\s*\d+%\s*(?:,\s*[\d.]+)?\s*\)$'
        if re.match(hsl_pattern, color):
            return True
        
        # Named colors (basic validation)
        named_colors = ['red', 'blue', 'green', 'yellow', 'black', 'white', 'gray', 'orange', 'purple', 'pink']
        if color.lower() in named_colors:
            return True
        
        return False

    async def _generate_brand_themes(self, brand_config: dict) -> Dict[str, Any]:
        """Generate theme configurations based on brand"""
        themes = {}
        color_palette = brand_config.get("color_palette", {})
        typography = brand_config.get("typography", {})
        
        # Light theme
        light_theme = {
            "name": "Light Theme",
            "mode": ThemeMode.LIGHT,
            "colors": {
                "primary": color_palette.get("primary", "#0066CC"),
                "secondary": color_palette.get("secondary", "#FF6B35"),
                "background": "#FFFFFF",
                "surface": "#F8F9FA",
                "text_primary": "#212529",
                "text_secondary": "#6C757D",
                **color_palette
            },
            "typography": typography,
            "components": await self._generate_component_styles(color_palette, ThemeMode.LIGHT)
        }
        
        # Dark theme
        dark_theme = {
            "name": "Dark Theme",
            "mode": ThemeMode.DARK,
            "colors": {
                "primary": color_palette.get("primary", "#BB86FC"),
                "secondary": color_palette.get("secondary", "#03DAC6"),
                "background": "#121212",
                "surface": "#1E1E1E",
                "text_primary": "#FFFFFF",
                "text_secondary": "#AAAAAA",
                **self._adjust_colors_for_dark_mode(color_palette)
            },
            "typography": typography,
            "components": await self._generate_component_styles(color_palette, ThemeMode.DARK)
        }
        
        themes["light"] = light_theme
        themes["dark"] = dark_theme
        
        return themes

    def _adjust_colors_for_dark_mode(self, color_palette: dict) -> Dict[str, str]:
        """Adjust colors for dark mode"""
        adjusted_colors = {}
        
        for color_name, color_value in color_palette.items():
            try:
                # Convert hex to RGB
                if color_value.startswith('#'):
                    rgb = tuple(int(color_value[i:i+2], 16) for i in (1, 3, 5))
                    hsv = colorsys.rgb_to_hsv(rgb[0]/255, rgb[1]/255, rgb[2]/255)
                    
                    # Adjust brightness for dark mode
                    adjusted_hsv = (hsv[0], hsv[1] * 0.8, min(hsv[2] * 1.2, 1.0))
                    adjusted_rgb = colorsys.hsv_to_rgb(*adjusted_hsv)
                    
                    adjusted_color = "#{:02x}{:02x}{:02x}".format(
                        int(adjusted_rgb[0] * 255),
                        int(adjusted_rgb[1] * 255),
                        int(adjusted_rgb[2] * 255)
                    )
                    adjusted_colors[color_name] = adjusted_color
                else:
                    adjusted_colors[color_name] = color_value
            except:
                adjusted_colors[color_name] = color_value
        
        return adjusted_colors

    async def _generate_component_styles(self, color_palette: dict, theme_mode: str) -> Dict[str, Any]:
        """Generate component-specific styles"""
        primary_color = color_palette.get("primary", "#0066CC")
        secondary_color = color_palette.get("secondary", "#FF6B35")
        
        return {
            "button": {
                "primary": {
                    "background_color": primary_color,
                    "text_color": "#FFFFFF",
                    "hover_background": self._darken_color(primary_color, 0.1),
                    "border_radius": "0.5rem",
                    "padding": "0.75rem 1.5rem"
                },
                "secondary": {
                    "background_color": "transparent",
                    "text_color": primary_color,
                    "border": f"2px solid {primary_color}",
                    "hover_background": primary_color,
                    "hover_text_color": "#FFFFFF"
                }
            },
            "card": {
                "background": "#FFFFFF" if theme_mode == ThemeMode.LIGHT else "#1E1E1E",
                "border": "1px solid #E0E0E0" if theme_mode == ThemeMode.LIGHT else "1px solid #333333",
                "border_radius": "0.75rem",
                "box_shadow": "0 4px 6px rgba(0, 0, 0, 0.1)" if theme_mode == ThemeMode.LIGHT else "0 4px 6px rgba(0, 0, 0, 0.3)"
            },
            "navigation": {
                "background": primary_color,
                "text_color": "#FFFFFF",
                "active_background": self._darken_color(primary_color, 0.2),
                "hover_background": self._darken_color(primary_color, 0.1)
            },
            "form": {
                "input_background": "#FFFFFF" if theme_mode == ThemeMode.LIGHT else "#2A2A2A",
                "input_border": "#D0D0D0" if theme_mode == ThemeMode.LIGHT else "#404040",
                "focus_border": primary_color,
                "label_color": "#333333" if theme_mode == ThemeMode.LIGHT else "#CCCCCC"
            }
        }

    def _darken_color(self, hex_color: str, amount: float) -> str:
        """Darken a hex color by a specified amount"""
        try:
            # Convert hex to RGB
            rgb = tuple(int(hex_color[i:i+2], 16) for i in (1, 3, 5))
            
            # Darken each component
            darkened_rgb = tuple(max(0, int(c * (1 - amount))) for c in rgb)
            
            # Convert back to hex
            return "#{:02x}{:02x}{:02x}".format(*darkened_rgb)
        except:
            return hex_color

    async def _generate_brand_guidelines(self, brand_config: dict) -> List[Dict[str, Any]]:
        """Generate brand usage guidelines"""
        guidelines = []
        
        # Logo usage guidelines
        if brand_config.get("logo_assets"):
            guidelines.append({
                "type": "logo_usage",
                "title": "Logo Usage Guidelines",
                "rules": [
                    "Always maintain minimum clear space around logo",
                    "Do not modify logo colors without approval",
                    "Use appropriate logo variant for background contrast",
                    "Maintain aspect ratio when resizing"
                ],
                "enforcement_level": "strict"
            })
        
        # Color guidelines
        if brand_config.get("color_palette"):
            guidelines.append({
                "type": "color_usage",
                "title": "Color Palette Guidelines",
                "rules": [
                    "Use primary color for main actions and emphasis",
                    "Use secondary color sparingly for accents",
                    "Maintain accessibility contrast ratios",
                    "Avoid using custom colors outside the defined palette"
                ],
                "enforcement_level": "warning"
            })
        
        # Typography guidelines
        if brand_config.get("typography"):
            guidelines.append({
                "type": "typography",
                "title": "Typography Guidelines",
                "rules": [
                    "Use primary font family for headings",
                    "Use secondary font family for body text",
                    "Maintain consistent font sizing hierarchy",
                    "Ensure proper line height and spacing"
                ],
                "enforcement_level": "warning"
            })
        
        return guidelines

    async def _store_brand_configuration(self, brand_config: dict):
        """Store brand configuration in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO brand_configurations 
                (id, organization_id, brand_name, is_primary, status, data)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                brand_config["id"],
                brand_config["organization_id"],
                brand_config["brand_name"],
                brand_config["is_primary"],
                brand_config["status"],
                json.dumps(brand_config)
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to store brand configuration: {e}")
            raise

    async def _generate_brand_css(self, brand_config: dict) -> Dict[str, str]:
        """Generate CSS files for brand themes"""
        css_files = {}
        
        themes = brand_config.get("themes", {})
        
        for theme_name, theme_data in themes.items():
            css_content = await self._generate_theme_css(theme_data)
            css_filename = f"brand-{brand_config['id'].lower()}-{theme_name}.css"
            css_path = f"{self.assets_path}/generated/{css_filename}"
            
            # Write CSS file
            async with aiofiles.open(css_path, 'w') as f:
                await f.write(css_content)
            
            css_files[theme_name] = css_path
        
        return css_files

    async def _generate_theme_css(self, theme_data: dict) -> str:
        """Generate CSS content for theme"""
        colors = theme_data.get("colors", {})
        typography = theme_data.get("typography", {})
        components = theme_data.get("components", {})
        
        css_content = f"""
/* Generated Theme CSS */
:root {{
    /* Colors */
    --color-primary: {colors.get('primary', '#0066CC')};
    --color-secondary: {colors.get('secondary', '#FF6B35')};
    --color-background: {colors.get('background', '#FFFFFF')};
    --color-surface: {colors.get('surface', '#F8F9FA')};
    --color-text-primary: {colors.get('text_primary', '#212529')};
    --color-text-secondary: {colors.get('text_secondary', '#6C757D')};
    
    /* Typography */
    --font-family-primary: {typography.get('font_family_primary', 'Inter, sans-serif')};
    --font-family-secondary: {typography.get('font_family_secondary', 'Roboto, sans-serif')};
    
    /* Spacing */
    --spacing-xs: 0.25rem;
    --spacing-sm: 0.5rem;
    --spacing-md: 1rem;
    --spacing-lg: 1.5rem;
    --spacing-xl: 2rem;
    
    /* Border Radius */
    --border-radius-sm: 0.25rem;
    --border-radius-md: 0.5rem;
    --border-radius-lg: 0.75rem;
}}

/* Component Styles */
.btn-primary {{
    background-color: var(--color-primary);
    color: {components.get('button', {}).get('primary', {}).get('text_color', '#FFFFFF')};
    border: none;
    border-radius: var(--border-radius-md);
    padding: var(--spacing-sm) var(--spacing-lg);
    font-family: var(--font-family-primary);
    font-weight: 500;
    cursor: pointer;
    transition: background-color 0.2s ease;
}}

.btn-primary:hover {{
    background-color: {components.get('button', {}).get('primary', {}).get('hover_background', 'var(--color-primary)')};
}}

.btn-secondary {{
    background-color: transparent;
    color: var(--color-primary);
    border: 2px solid var(--color-primary);
    border-radius: var(--border-radius-md);
    padding: var(--spacing-sm) var(--spacing-lg);
    font-family: var(--font-family-primary);
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s ease;
}}

.btn-secondary:hover {{
    background-color: var(--color-primary);
    color: white;
}}

.card {{
    background-color: {components.get('card', {}).get('background', 'var(--color-surface)')};
    border: {components.get('card', {}).get('border', '1px solid #E0E0E0')};
    border-radius: {components.get('card', {}).get('border_radius', 'var(--border-radius-lg)')};
    box-shadow: {components.get('card', {}).get('box_shadow', '0 4px 6px rgba(0, 0, 0, 0.1)')};
    padding: var(--spacing-lg);
}}

.navigation {{
    background-color: {components.get('navigation', {}).get('background', 'var(--color-primary)')};
    color: {components.get('navigation', {}).get('text_color', '#FFFFFF')};
}}

.form-input {{
    background-color: {components.get('form', {}).get('input_background', '#FFFFFF')};
    border: 1px solid {components.get('form', {}).get('input_border', '#D0D0D0')};
    border-radius: var(--border-radius-sm);
    padding: var(--spacing-sm);
    font-family: var(--font-family-secondary);
}}

.form-input:focus {{
    border-color: {components.get('form', {}).get('focus_border', 'var(--color-primary)')};
    outline: none;
    box-shadow: 0 0 0 3px rgba(0, 102, 204, 0.1);
}}

/* Typography Classes */
.text-primary {{ color: var(--color-text-primary); }}
.text-secondary {{ color: var(--color-text-secondary); }}
.font-primary {{ font-family: var(--font-family-primary); }}
.font-secondary {{ font-family: var(--font-family-secondary); }}

/* Utility Classes */
.bg-primary {{ background-color: var(--color-primary); }}
.bg-secondary {{ background-color: var(--color-secondary); }}
.bg-surface {{ background-color: var(--color-surface); }}
"""
        
        return css_content

    async def get_theme_config(self, org_id: str) -> Dict[str, Any]:
        """Get theme configuration for organization"""
        try:
            # Find primary brand for organization
            primary_brand = None
            for brand_id, brand_data in self.brand_configurations.items():
                if (brand_data.get("organization_id") == org_id and 
                    brand_data.get("is_primary", False)):
                    primary_brand = brand_data
                    break
            
            if not primary_brand:
                # Return default theme if no primary brand found
                return {
                    "status": "default",
                    "message": "No primary brand found, using default theme",
                    "theme": self.theme_templates["modern_corporate"]
                }
            
            # Get active theme
            themes = primary_brand.get("themes", {})
            active_theme = themes.get("light", {})  # Default to light theme
            
            # Add asset URLs
            logo_assets = primary_brand.get("logo_assets", {})
            
            theme_config = {
                "brand_id": primary_brand["id"],
                "brand_name": primary_brand["brand_name"],
                "theme": active_theme,
                "assets": {
                    "logo": logo_assets.get("primary", ""),
                    "logo_dark": logo_assets.get("dark_variant", ""),
                    "icon": logo_assets.get("icon", ""),
                    "favicon": logo_assets.get("favicon", "")
                },
                "custom_css": primary_brand.get("custom_css", ""),
                "guidelines": primary_brand.get("guidelines", [])
            }
            
            return {
                "status": "success",
                "theme_config": theme_config
            }
            
        except Exception as e:
            logger.error(f"Failed to get theme config: {e}")
            return {
                "status": "error",
                "message": str(e)
            }

# Global instance
custom_branding_system = CustomBrandingSystem()