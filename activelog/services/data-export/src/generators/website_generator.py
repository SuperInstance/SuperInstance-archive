"""
Static Website Generator from content with multiple themes and responsive design
"""

import os
import logging
import shutil
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Callable, Optional
from urllib.parse import quote
import base64

from jinja2 import Environment, FileSystemLoader, Template
import markdown
from PIL import Image

from ..core.config import settings
from ..utils.file_utils import get_file_metadata, get_files_by_filters
from ..utils.metadata_extractor import MetadataExtractor

logger = logging.getLogger(__name__)

class WebsiteGenerator:
    """Static website generator with multiple themes and responsive design"""
    
    def __init__(self):
        self.metadata_extractor = MetadataExtractor()
        self.jinja_env = None
        self.themes = {}
        
    async def initialize(self):
        """Initialize website generator"""
        
        # Setup Jinja2 environment
        template_dir = Path(settings.TEMPLATE_DIR) / "website"
        template_dir.mkdir(parents=True, exist_ok=True)
        
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=True
        )
        
        # Load available themes
        self._load_themes()
        
        # Create default templates if they don't exist
        await self._create_default_templates()
        
        logger.info("Website generator initialized")
    
    def _load_themes(self):
        """Load available website themes"""
        
        self.themes = {
            "modern": {
                "name": "Modern Gallery",
                "description": "Clean, modern design with grid layout",
                "template": "modern.html",
                "css": "modern.css",
                "js": "modern.js"
            },
            "classic": {
                "name": "Classic Album",
                "description": "Traditional photo album style",
                "template": "classic.html", 
                "css": "classic.css",
                "js": "classic.js"
            },
            "timeline": {
                "name": "Timeline View",
                "description": "Chronological timeline layout",
                "template": "timeline.html",
                "css": "timeline.css", 
                "js": "timeline.js"
            }
        }
    
    def export(self, job_id: str, config: Dict[str, Any],
              filters: Dict[str, Any], output_dir: str,
              progress_callback: Callable) -> Dict[str, Any]:
        """
        Generate static website from content
        
        Args:
            job_id: Export job identifier
            config: Website generation configuration
            filters: File selection filters
            output_dir: Output directory path
            progress_callback: Progress reporting callback
            
        Returns:
            Export result with website path and metadata
        """
        
        try:
            progress_callback(0, 100, "Initializing website generation")
            
            # Get files to include
            files = get_files_by_filters(filters)
            total_files = len(files)
            
            if total_files == 0:
                return {"success": False, "error": "No files found matching filters"}
            
            # Get website configuration
            website_config = self._get_website_config(config)
            
            # Create website structure
            website_dir = os.path.join(output_dir, "website")
            os.makedirs(website_dir, exist_ok=True)
            
            progress_callback(10, 100, "Creating website structure")
            
            # Generate website
            result = self._generate_website(
                files=files,
                website_dir=website_dir,
                config=website_config,
                progress_callback=progress_callback,
                total_files=total_files
            )
            
            if result["success"]:
                # Create archive of website
                archive_path = os.path.join(output_dir, f"website_{job_id}.zip")
                self._create_website_archive(website_dir, archive_path)
                
                progress_callback(100, 100, "Website generation completed")
                
                return {
                    "success": True,
                    "output_path": archive_path,
                    "filename": f"website_{job_id}.zip",
                    "file_size": os.path.getsize(archive_path),
                    "website_dir": website_dir,
                    "files_included": result.get("files_processed", 0),
                    "pages_created": result.get("pages_created", 0)
                }
            else:
                return result
                
        except Exception as e:
            logger.error(f"Website generation failed for job {job_id}: {e}")
            return {"success": False, "error": str(e)}
    
    def _get_website_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Get website configuration with defaults"""
        
        return {
            "theme": config.get("theme", "modern"),
            "title": config.get("title", "ActiveLog Export"),
            "description": config.get("description", "Generated from ActiveLog data export"),
            "author": config.get("author", "ActiveLog User"),
            "include_metadata": config.get("include_metadata", True),
            "create_thumbnails": config.get("create_thumbnails", True),
            "thumbnail_size": config.get("thumbnail_size", (300, 300)),
            "group_by_date": config.get("group_by_date", True),
            "group_by_type": config.get("group_by_type", False),
            "enable_search": config.get("enable_search", True),
            "enable_slideshow": config.get("enable_slideshow", True),
            "responsive_design": config.get("responsive_design", True),
            "include_download_links": config.get("include_download_links", True),
            "custom_css": config.get("custom_css", ""),
            "custom_js": config.get("custom_js", ""),
            "navigation_style": config.get("navigation_style", "breadcrumb")  # breadcrumb, sidebar, tabs
        }
    
    def _generate_website(self, files: List[str], website_dir: str, 
                         config: Dict[str, Any], progress_callback: Callable,
                         total_files: int) -> Dict[str, Any]:
        """Generate complete website"""
        
        try:
            # Create directory structure
            dirs_to_create = ["assets", "assets/css", "assets/js", "assets/images", 
                             "assets/thumbnails", "pages", "data"]
            
            for dir_name in dirs_to_create:
                os.makedirs(os.path.join(website_dir, dir_name), exist_ok=True)
            
            progress_callback(15, 100, "Processing files")
            
            # Process files and create data structure
            website_data = self._process_files_for_website(
                files, website_dir, config, progress_callback, total_files
            )
            
            progress_callback(60, 100, "Generating HTML pages")
            
            # Generate HTML pages
            pages_created = self._generate_html_pages(
                website_data, website_dir, config
            )
            
            progress_callback(80, 100, "Copying theme assets")
            
            # Copy theme assets
            self._copy_theme_assets(website_dir, config)
            
            progress_callback(90, 100, "Creating search index")
            
            # Create search index if enabled
            if config["enable_search"]:
                self._create_search_index(website_data, website_dir)
            
            return {
                "success": True,
                "files_processed": len(website_data.get("files", [])),
                "pages_created": pages_created
            }
            
        except Exception as e:
            logger.error(f"Website generation failed: {e}")
            return {"success": False, "error": str(e)}
    
    def _process_files_for_website(self, files: List[str], website_dir: str,
                                  config: Dict[str, Any], progress_callback: Callable,
                                  total_files: int) -> Dict[str, Any]:
        """Process files and create website data structure"""
        
        website_data = {
            "config": config,
            "generated_at": datetime.utcnow().isoformat(),
            "total_files": total_files,
            "files": [],
            "groups": {},
            "stats": {
                "images": 0,
                "videos": 0,
                "documents": 0,
                "other": 0
            }
        }
        
        processed_count = 0
        
        for file_path in files:
            try:
                # Get file metadata
                file_metadata = get_file_metadata(file_path)
                
                # Determine file type
                file_extension = Path(file_path).suffix.lower()
                file_type = self._get_file_type(file_extension)
                
                # Copy file to website assets
                relative_path = self._copy_file_to_website(file_path, website_dir, file_type)
                
                # Create thumbnail for images
                thumbnail_path = None
                if file_type == "image" and config["create_thumbnails"]:
                    thumbnail_path = self._create_thumbnail(file_path, website_dir, config)
                
                # Create file data
                file_data = {
                    "original_path": file_path,
                    "filename": os.path.basename(file_path),
                    "relative_path": relative_path,
                    "thumbnail_path": thumbnail_path,
                    "file_type": file_type,
                    "extension": file_extension,
                    "size": file_metadata.get("size", 0),
                    "modified": file_metadata.get("modified_time"),
                    "metadata": file_metadata if config["include_metadata"] else {}
                }
                
                # Add EXIF data for images
                if file_type == "image" and config["include_metadata"]:
                    try:
                        exif_data = self.metadata_extractor.extract_exif_data(file_path)
                        file_data["exif"] = exif_data
                    except Exception as e:
                        logger.warning(f"Failed to extract EXIF from {file_path}: {e}")
                
                website_data["files"].append(file_data)
                
                # Update stats
                website_data["stats"][file_type] += 1
                
                processed_count += 1
                
                # Update progress
                progress = 15 + (processed_count / total_files * 45)
                progress_callback(progress, 100, f"Processed {processed_count}/{total_files} files")
                
            except Exception as e:
                logger.warning(f"Failed to process file {file_path}: {e}")
        
        # Create groups
        if config["group_by_date"]:
            website_data["groups"]["by_date"] = self._group_files_by_date(website_data["files"])
        
        if config["group_by_type"]:
            website_data["groups"]["by_type"] = self._group_files_by_type(website_data["files"])
        
        return website_data
    
    def _get_file_type(self, extension: str) -> str:
        """Determine file type from extension"""
        
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.svg']
        video_extensions = ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm']
        document_extensions = ['.pdf', '.doc', '.docx', '.txt', '.rtf', '.odt', '.md']
        
        if extension in image_extensions:
            return "image"
        elif extension in video_extensions:
            return "video"
        elif extension in document_extensions:
            return "document"
        else:
            return "other"
    
    def _copy_file_to_website(self, file_path: str, website_dir: str, file_type: str) -> str:
        """Copy file to website assets directory"""
        
        try:
            filename = os.path.basename(file_path)
            
            # Create type-specific directory
            type_dir = os.path.join(website_dir, "assets", file_type + "s")
            os.makedirs(type_dir, exist_ok=True)
            
            # Copy file
            dest_path = os.path.join(type_dir, filename)
            
            # Handle duplicate names
            counter = 1
            original_dest = dest_path
            while os.path.exists(dest_path):
                name, ext = os.path.splitext(filename)
                new_filename = f"{name}_{counter}{ext}"
                dest_path = os.path.join(type_dir, new_filename)
                counter += 1
            
            shutil.copy2(file_path, dest_path)
            
            # Return relative path from website root
            return os.path.relpath(dest_path, website_dir).replace(os.sep, '/')
            
        except Exception as e:
            logger.warning(f"Failed to copy file {file_path}: {e}")
            return ""
    
    def _create_thumbnail(self, file_path: str, website_dir: str, config: Dict[str, Any]) -> Optional[str]:
        """Create thumbnail for image file"""
        
        try:
            with Image.open(file_path) as img:
                # Convert to RGB if necessary
                if img.mode in ('RGBA', 'P'):
                    img = img.convert('RGB')
                
                # Create thumbnail
                img.thumbnail(config["thumbnail_size"], Image.Resampling.LANCZOS)
                
                # Save thumbnail
                filename = os.path.basename(file_path)
                name, ext = os.path.splitext(filename)
                thumbnail_filename = f"{name}_thumb.jpg"
                
                thumbnail_dir = os.path.join(website_dir, "assets", "thumbnails")
                thumbnail_path = os.path.join(thumbnail_dir, thumbnail_filename)
                
                img.save(thumbnail_path, "JPEG", quality=85, optimize=True)
                
                # Return relative path
                return os.path.relpath(thumbnail_path, website_dir).replace(os.sep, '/')
                
        except Exception as e:
            logger.warning(f"Failed to create thumbnail for {file_path}: {e}")
            return None
    
    def _group_files_by_date(self, files: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group files by date"""
        
        groups = {}
        
        for file_data in files:
            try:
                modified = file_data.get("modified")
                if modified:
                    if isinstance(modified, str):
                        date_key = modified[:10]  # YYYY-MM-DD
                    else:
                        date_key = modified.strftime("%Y-%m-%d")
                else:
                    date_key = "Unknown Date"
                
                if date_key not in groups:
                    groups[date_key] = []
                
                groups[date_key].append(file_data)
                
            except Exception as e:
                logger.warning(f"Failed to group file by date: {e}")
                # Add to unknown date group
                if "Unknown Date" not in groups:
                    groups["Unknown Date"] = []
                groups["Unknown Date"].append(file_data)
        
        # Sort groups by date
        return dict(sorted(groups.items(), reverse=True))
    
    def _group_files_by_type(self, files: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group files by type"""
        
        groups = {
            "Images": [],
            "Videos": [],
            "Documents": [],
            "Other": []
        }
        
        type_mapping = {
            "image": "Images",
            "video": "Videos", 
            "document": "Documents",
            "other": "Other"
        }
        
        for file_data in files:
            file_type = file_data.get("file_type", "other")
            group_name = type_mapping.get(file_type, "Other")
            groups[group_name].append(file_data)
        
        # Remove empty groups
        return {k: v for k, v in groups.items() if v}
    
    def _generate_html_pages(self, website_data: Dict[str, Any], 
                           website_dir: str, config: Dict[str, Any]) -> int:
        """Generate HTML pages"""
        
        pages_created = 0
        
        try:
            # Get theme template
            theme = config["theme"]
            if theme not in self.themes:
                theme = "modern"
            
            # Load main template
            template = self.jinja_env.get_template(self.themes[theme]["template"])
            
            # Generate index page
            index_html = template.render(
                title=config["title"],
                description=config["description"],
                author=config["author"],
                website_data=website_data,
                config=config,
                page_type="index"
            )
            
            with open(os.path.join(website_dir, "index.html"), 'w', encoding='utf-8') as f:
                f.write(index_html)
            
            pages_created += 1
            
            # Generate gallery pages for groups
            if website_data.get("groups"):
                for group_type, groups in website_data["groups"].items():
                    for group_name, group_files in groups.items():
                        # Create safe filename
                        safe_name = "".join(c for c in group_name if c.isalnum() or c in (' ', '-', '_')).strip()
                        safe_name = safe_name.replace(' ', '_').lower()
                        
                        page_html = template.render(
                            title=f"{config['title']} - {group_name}",
                            description=f"{group_name} from {config['title']}",
                            author=config["author"],
                            website_data=website_data,
                            config=config,
                            page_type="gallery",
                            group_name=group_name,
                            group_files=group_files
                        )
                        
                        page_filename = f"gallery_{group_type}_{safe_name}.html"
                        with open(os.path.join(website_dir, "pages", page_filename), 'w', encoding='utf-8') as f:
                            f.write(page_html)
                        
                        pages_created += 1
            
            # Generate individual file pages if needed
            if config.get("create_individual_pages", False):
                for file_data in website_data["files"][:50]:  # Limit to 50 files
                    safe_name = "".join(c for c in file_data["filename"] if c.isalnum() or c in (' ', '-', '_')).strip()
                    safe_name = safe_name.replace(' ', '_').lower()
                    
                    file_html = template.render(
                        title=f"{config['title']} - {file_data['filename']}",
                        description=f"File: {file_data['filename']}",
                        author=config["author"],
                        website_data=website_data,
                        config=config,
                        page_type="file",
                        file_data=file_data
                    )
                    
                    page_filename = f"file_{safe_name}.html"
                    with open(os.path.join(website_dir, "pages", page_filename), 'w', encoding='utf-8') as f:
                        f.write(file_html)
                    
                    pages_created += 1
            
        except Exception as e:
            logger.error(f"Failed to generate HTML pages: {e}")
            raise
        
        return pages_created
    
    def _copy_theme_assets(self, website_dir: str, config: Dict[str, Any]):
        """Copy theme CSS, JS, and other assets"""
        
        try:
            theme = config["theme"]
            if theme not in self.themes:
                theme = "modern"
            
            # Create default CSS
            css_content = self._get_default_css(theme, config)
            with open(os.path.join(website_dir, "assets", "css", "style.css"), 'w') as f:
                f.write(css_content)
            
            # Create default JS
            js_content = self._get_default_js(theme, config)
            with open(os.path.join(website_dir, "assets", "js", "main.js"), 'w') as f:
                f.write(js_content)
            
            # Add custom CSS/JS if provided
            if config.get("custom_css"):
                with open(os.path.join(website_dir, "assets", "css", "custom.css"), 'w') as f:
                    f.write(config["custom_css"])
            
            if config.get("custom_js"):
                with open(os.path.join(website_dir, "assets", "js", "custom.js"), 'w') as f:
                    f.write(config["custom_js"])
            
        except Exception as e:
            logger.error(f"Failed to copy theme assets: {e}")
            raise
    
    def _create_search_index(self, website_data: Dict[str, Any], website_dir: str):
        """Create search index for JavaScript search functionality"""
        
        try:
            search_index = []
            
            for file_data in website_data["files"]:
                index_item = {
                    "filename": file_data["filename"],
                    "path": file_data["relative_path"],
                    "type": file_data["file_type"],
                    "size": file_data["size"],
                    "keywords": [
                        file_data["filename"],
                        file_data["file_type"],
                        file_data["extension"]
                    ]
                }
                
                # Add metadata keywords
                if file_data.get("metadata"):
                    for key, value in file_data["metadata"].items():
                        if isinstance(value, str) and value:
                            index_item["keywords"].append(value.lower())
                
                search_index.append(index_item)
            
            # Save search index
            with open(os.path.join(website_dir, "data", "search_index.json"), 'w') as f:
                json.dump(search_index, f, indent=2)
            
        except Exception as e:
            logger.warning(f"Failed to create search index: {e}")
    
    def _create_website_archive(self, website_dir: str, archive_path: str):
        """Create ZIP archive of generated website"""
        
        import zipfile
        
        try:
            with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(website_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arc_path = os.path.relpath(file_path, website_dir)
                        zipf.write(file_path, arc_path)
            
        except Exception as e:
            logger.error(f"Failed to create website archive: {e}")
            raise
    
    async def _create_default_templates(self):
        """Create default HTML templates if they don't exist"""
        
        template_dir = Path(settings.TEMPLATE_DIR) / "website"
        
        # Modern theme template
        modern_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <meta name="description" content="{{ description }}">
    <meta name="author" content="{{ author }}">
    <link rel="stylesheet" href="assets/css/style.css">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
</head>
<body>
    <header class="header">
        <div class="container">
            <h1 class="site-title">{{ title }}</h1>
            <p class="site-description">{{ description }}</p>
            {% if config.enable_search %}
            <div class="search-container">
                <input type="text" id="search-input" placeholder="Search files..." class="search-input">
                <i class="fas fa-search search-icon"></i>
            </div>
            {% endif %}
        </div>
    </header>

    <main class="main">
        <div class="container">
            {% if page_type == "index" %}
                <div class="stats">
                    <div class="stat-item">
                        <span class="stat-number">{{ website_data.total_files }}</span>
                        <span class="stat-label">Total Files</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-number">{{ website_data.stats.images }}</span>
                        <span class="stat-label">Images</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-number">{{ website_data.stats.videos }}</span>
                        <span class="stat-label">Videos</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-number">{{ website_data.stats.documents }}</span>
                        <span class="stat-label">Documents</span>
                    </div>
                </div>

                <div class="gallery-grid" id="gallery">
                    {% for file in website_data.files[:50] %}
                    <div class="gallery-item" data-type="{{ file.file_type }}" data-filename="{{ file.filename }}">
                        {% if file.thumbnail_path %}
                            <img src="{{ file.thumbnail_path }}" alt="{{ file.filename }}" class="gallery-image" loading="lazy">
                        {% elif file.file_type == 'video' %}
                            <div class="file-preview video-preview">
                                <i class="fas fa-video"></i>
                                <span>{{ file.filename }}</span>
                            </div>
                        {% elif file.file_type == 'document' %}
                            <div class="file-preview document-preview">
                                <i class="fas fa-file-alt"></i>
                                <span>{{ file.filename }}</span>
                            </div>
                        {% else %}
                            <div class="file-preview other-preview">
                                <i class="fas fa-file"></i>
                                <span>{{ file.filename }}</span>
                            </div>
                        {% endif %}
                        
                        <div class="gallery-overlay">
                            <h3 class="gallery-title">{{ file.filename }}</h3>
                            <p class="gallery-meta">{{ file.size | filesizeformat }} • {{ file.file_type | title }}</p>
                            {% if config.include_download_links %}
                            <a href="{{ file.relative_path }}" download class="download-btn">
                                <i class="fas fa-download"></i> Download
                            </a>
                            {% endif %}
                        </div>
                    </div>
                    {% endfor %}
                </div>
            {% endif %}
        </div>
    </main>

    <footer class="footer">
        <div class="container">
            <p>&copy; {{ website_data.generated_at[:4] }} {{ author }}. Generated with ActiveLog Data Export.</p>
        </div>
    </footer>

    <script src="assets/js/main.js"></script>
</body>
</html>
        """
        
        modern_template_path = template_dir / "modern.html"
        if not modern_template_path.exists():
            with open(modern_template_path, 'w', encoding='utf-8') as f:
                f.write(modern_template)
    
    def _get_default_css(self, theme: str, config: Dict[str, Any]) -> str:
        """Get default CSS for theme"""
        
        if theme == "modern":
            return """
/* Modern Theme CSS */
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    line-height: 1.6;
    color: #333;
    background-color: #f8f9fa;
}

.container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 0 20px;
}

.header {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 2rem 0;
    text-align: center;
}

.site-title {
    font-size: 2.5rem;
    font-weight: 700;
    margin-bottom: 0.5rem;
}

.site-description {
    font-size: 1.1rem;
    opacity: 0.9;
    margin-bottom: 2rem;
}

.search-container {
    position: relative;
    max-width: 400px;
    margin: 0 auto;
}

.search-input {
    width: 100%;
    padding: 12px 50px 12px 20px;
    border: none;
    border-radius: 25px;
    font-size: 1rem;
    background: rgba(255, 255, 255, 0.9);
    color: #333;
}

.search-icon {
    position: absolute;
    right: 20px;
    top: 50%;
    transform: translateY(-50%);
    color: #666;
}

.main {
    padding: 3rem 0;
}

.stats {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 2rem;
    margin-bottom: 3rem;
}

.stat-item {
    background: white;
    padding: 2rem;
    border-radius: 10px;
    text-align: center;
    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
    transition: transform 0.3s ease;
}

.stat-item:hover {
    transform: translateY(-5px);
}

.stat-number {
    display: block;
    font-size: 2.5rem;
    font-weight: 700;
    color: #667eea;
    margin-bottom: 0.5rem;
}

.stat-label {
    font-size: 1rem;
    color: #666;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.gallery-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 2rem;
}

.gallery-item {
    background: white;
    border-radius: 10px;
    overflow: hidden;
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
    transition: all 0.3s ease;
    position: relative;
}

.gallery-item:hover {
    transform: translateY(-10px);
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
}

.gallery-image {
    width: 100%;
    height: 200px;
    object-fit: cover;
}

.file-preview {
    width: 100%;
    height: 200px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    background: #f8f9fa;
    color: #666;
}

.file-preview i {
    font-size: 3rem;
    margin-bottom: 1rem;
}

.file-preview span {
    text-align: center;
    padding: 0 1rem;
    font-weight: 500;
}

.video-preview {
    background: linear-gradient(135deg, #ff6b6b, #ee5a52);
    color: white;
}

.document-preview {
    background: linear-gradient(135deg, #4ecdc4, #44a08d);
    color: white;
}

.other-preview {
    background: linear-gradient(135deg, #feca57, #ff9ff3);
    color: white;
}

.gallery-overlay {
    padding: 1.5rem;
}

.gallery-title {
    font-size: 1.1rem;
    font-weight: 600;
    margin-bottom: 0.5rem;
    word-break: break-word;
}

.gallery-meta {
    font-size: 0.9rem;
    color: #666;
    margin-bottom: 1rem;
}

.download-btn {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem 1rem;
    background: #667eea;
    color: white;
    text-decoration: none;
    border-radius: 5px;
    font-size: 0.9rem;
    transition: background 0.3s ease;
}

.download-btn:hover {
    background: #5a6fd8;
}

.footer {
    background: #333;
    color: white;
    text-align: center;
    padding: 2rem 0;
    margin-top: 3rem;
}

/* Responsive Design */
@media (max-width: 768px) {
    .site-title {
        font-size: 2rem;
    }
    
    .gallery-grid {
        grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
        gap: 1.5rem;
    }
    
    .stats {
        grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
        gap: 1rem;
    }
    
    .stat-number {
        font-size: 2rem;
    }
}

@media (max-width: 480px) {
    .gallery-grid {
        grid-template-columns: 1fr;
    }
    
    .container {
        padding: 0 15px;
    }
}
            """
        else:
            # Default fallback CSS
            return """
/* Default Theme CSS */
body { font-family: Arial, sans-serif; margin: 0; padding: 20px; }
.container { max-width: 1200px; margin: 0 auto; }
.gallery-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 20px; }
.gallery-item { border: 1px solid #ddd; padding: 10px; border-radius: 5px; }
.gallery-image { width: 100%; height: 150px; object-fit: cover; }
            """
    
    def _get_default_js(self, theme: str, config: Dict[str, Any]) -> str:
        """Get default JavaScript for theme"""
        
        js_content = """
// Website functionality
document.addEventListener('DOMContentLoaded', function() {
    // Search functionality
    const searchInput = document.getElementById('search-input');
    const galleryItems = document.querySelectorAll('.gallery-item');
    
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            const searchTerm = this.value.toLowerCase();
            
            galleryItems.forEach(item => {
                const filename = item.dataset.filename.toLowerCase();
                const type = item.dataset.type.toLowerCase();
                
                if (filename.includes(searchTerm) || type.includes(searchTerm)) {
                    item.style.display = 'block';
                } else {
                    item.style.display = 'none';
                }
            });
        });
    }
    
    // Lazy loading for images
    if ('IntersectionObserver' in window) {
        const imageObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    img.src = img.dataset.src || img.src;
                    img.classList.remove('lazy');
                    observer.unobserve(img);
                }
            });
        });
        
        document.querySelectorAll('img[loading="lazy"]').forEach(img => {
            imageObserver.observe(img);
        });
    }
});
        """
        
        if config.get("enable_slideshow"):
            js_content += """
// Simple slideshow functionality
function openSlideshow(imageSrc, title) {
    // Create modal overlay
    const modal = document.createElement('div');
    modal.className = 'slideshow-modal';
    modal.innerHTML = `
        <div class="slideshow-content">
            <span class="slideshow-close">&times;</span>
            <img src="${imageSrc}" alt="${title}" class="slideshow-image">
            <div class="slideshow-title">${title}</div>
        </div>
    `;
    
    document.body.appendChild(modal);
    
    // Close functionality
    modal.querySelector('.slideshow-close').onclick = () => modal.remove();
    modal.onclick = (e) => {
        if (e.target === modal) modal.remove();
    };
    
    // Keyboard navigation
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') modal.remove();
    });
}

// Add click handlers to gallery images
document.querySelectorAll('.gallery-image').forEach(img => {
    img.style.cursor = 'pointer';
    img.onclick = () => openSlideshow(img.src, img.alt);
});
            """
        
        return js_content