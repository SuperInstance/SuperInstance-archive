"""
Photo Book/Album Generator with professional layouts and customization
"""

import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Callable, Optional, Tuple
import json

from reportlab.lib.pagesizes import letter, A4, A3, A5
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.lib.colors import black, white, gray, darkgray
from reportlab.lib.units import inch, cm, mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak,
    Table, TableStyle, KeepTogether, Frame, PageTemplate
)
from reportlab.pdfgen import canvas
from PIL import Image as PILImage, ImageEnhance, ImageFilter
import exifread

from ..core.config import settings
from ..utils.file_utils import get_file_metadata, get_files_by_filters
from ..utils.metadata_extractor import MetadataExtractor

logger = logging.getLogger(__name__)

class PhotoBookGenerator:
    """Professional photo book/album generator with multiple layouts"""
    
    def __init__(self):
        self.metadata_extractor = MetadataExtractor()
        self.layouts = self._define_layouts()
        self.styles = None
        
    async def initialize(self):
        """Initialize photo book generator"""
        self.styles = self._create_styles()
        logger.info("Photo book generator initialized")
    
    def _define_layouts(self) -> Dict[str, Dict[str, Any]]:
        """Define available photo book layouts"""
        
        return {
            "classic": {
                "name": "Classic Album",
                "description": "Traditional photo album with captions",
                "photos_per_page": 4,
                "layout_type": "grid",
                "include_captions": True,
                "include_metadata": True,
                "border_style": "simple"
            },
            "magazine": {
                "name": "Magazine Style", 
                "description": "Modern magazine-style layout",
                "photos_per_page": 6,
                "layout_type": "magazine",
                "include_captions": True,
                "include_metadata": False,
                "border_style": "none"
            },
            "portfolio": {
                "name": "Portfolio",
                "description": "Professional portfolio presentation",
                "photos_per_page": 2,
                "layout_type": "portfolio", 
                "include_captions": False,
                "include_metadata": True,
                "border_style": "elegant"
            },
            "collage": {
                "name": "Collage Style",
                "description": "Creative collage layouts",
                "photos_per_page": 8,
                "layout_type": "collage",
                "include_captions": False,
                "include_metadata": False,
                "border_style": "none"
            },
            "timeline": {
                "name": "Timeline",
                "description": "Chronological timeline layout",
                "photos_per_page": 3,
                "layout_type": "timeline",
                "include_captions": True,
                "include_metadata": True,
                "border_style": "timeline"
            }
        }
    
    def _create_styles(self):
        """Create custom PDF styles for photo books"""
        
        styles = getSampleStyleSheet()
        
        # Custom styles for photo books
        styles.add(ParagraphStyle(
            name='BookTitle',
            parent=styles['Title'],
            fontSize=36,
            spaceAfter=30,
            textColor=black,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
        
        styles.add(ParagraphStyle(
            name='SectionTitle',
            parent=styles['Heading1'],
            fontSize=20,
            spaceAfter=15,
            textColor=darkgray,
            alignment=TA_LEFT,
            fontName='Helvetica-Bold'
        ))
        
        styles.add(ParagraphStyle(
            name='PhotoCaption',
            parent=styles['Normal'],
            fontSize=10,
            textColor=darkgray,
            alignment=TA_CENTER,
            fontName='Helvetica-Oblique',
            spaceAfter=6
        ))
        
        styles.add(ParagraphStyle(
            name='PhotoMetadata',
            parent=styles['Normal'],
            fontSize=8,
            textColor=gray,
            alignment=TA_LEFT,
            fontName='Helvetica',
            leftIndent=10
        ))
        
        styles.add(ParagraphStyle(
            name='PageNumber',
            parent=styles['Normal'],
            fontSize=10,
            textColor=gray,
            alignment=TA_CENTER,
            fontName='Helvetica'
        ))
        
        return styles
    
    def export(self, job_id: str, config: Dict[str, Any],
              filters: Dict[str, Any], output_dir: str,
              progress_callback: Callable) -> Dict[str, Any]:
        """
        Generate photo book/album from images
        
        Args:
            job_id: Export job identifier
            config: Photo book configuration
            filters: File selection filters
            output_dir: Output directory path
            progress_callback: Progress reporting callback
            
        Returns:
            Export result with photo book path and metadata
        """
        
        try:
            progress_callback(0, 100, "Initializing photo book generation")
            
            # Get image files
            files = get_files_by_filters(filters)
            
            # Filter for images only
            image_files = [f for f in files if self._is_image_file(f)]
            total_images = len(image_files)
            
            if total_images == 0:
                return {"success": False, "error": "No image files found matching filters"}
            
            # Get photo book configuration
            book_config = self._get_photobook_config(config)
            
            # Sort images by date if requested
            if book_config["sort_by_date"]:
                image_files = self._sort_images_by_date(image_files)
            
            # Create photo book file
            output_filename = f"photobook_{job_id}.pdf"
            output_path = os.path.join(output_dir, output_filename)
            
            # Generate photo book
            result = self._generate_photobook(
                image_files=image_files,
                output_path=output_path,
                config=book_config,
                progress_callback=progress_callback,
                total_images=total_images
            )
            
            if result["success"]:
                progress_callback(100, 100, "Photo book generation completed")
                
                return {
                    "success": True,
                    "output_path": output_path,
                    "filename": output_filename,
                    "file_size": os.path.getsize(output_path),
                    "images_included": total_images,
                    "pages_created": result.get("pages", 0),
                    "layout_used": book_config["layout"]
                }
            else:
                return result
                
        except Exception as e:
            logger.error(f"Photo book generation failed for job {job_id}: {e}")
            return {"success": False, "error": str(e)}
    
    def _get_photobook_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Get photo book configuration with defaults"""
        
        layout = config.get("layout", "classic")
        if layout not in self.layouts:
            layout = "classic"
        
        layout_settings = self.layouts[layout].copy()
        
        return {
            "layout": layout,
            "title": config.get("title", "Photo Album"),
            "subtitle": config.get("subtitle", ""),
            "author": config.get("author", ""),
            "page_size": config.get("page_size", "letter"),  # letter, A4, A3, A5
            "orientation": config.get("orientation", "portrait"),  # portrait, landscape
            "cover_photo": config.get("cover_photo", ""),
            "sort_by_date": config.get("sort_by_date", True),
            "group_by_date": config.get("group_by_date", False),
            "enhance_images": config.get("enhance_images", True),
            "max_image_quality": config.get("max_image_quality", 95),
            "include_cover_page": config.get("include_cover_page", True),
            "include_table_of_contents": config.get("include_table_of_contents", False),
            "margin_size": config.get("margin_size", "normal"),  # small, normal, large
            "color_theme": config.get("color_theme", "neutral"),  # neutral, warm, cool, vintage
            **layout_settings  # Include layout-specific settings
        }
    
    def _is_image_file(self, file_path: str) -> bool:
        """Check if file is a supported image format"""
        
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp']
        extension = Path(file_path).suffix.lower()
        return extension in image_extensions
    
    def _sort_images_by_date(self, image_files: List[str]) -> List[str]:
        """Sort images by date taken (EXIF) or modification date"""
        
        def get_image_date(file_path: str) -> datetime:
            try:
                # Try to get EXIF date first
                exif_data = self.metadata_extractor.extract_exif_data(file_path)
                if exif_data.get("DateTime"):
                    return datetime.strptime(exif_data["DateTime"], "%Y:%m:%d %H:%M:%S")
                elif exif_data.get("DateTimeOriginal"):
                    return datetime.strptime(exif_data["DateTimeOriginal"], "%Y:%m:%d %H:%M:%S")
            except Exception:
                pass
            
            # Fallback to file modification time
            try:
                return datetime.fromtimestamp(os.path.getmtime(file_path))
            except Exception:
                return datetime.min
        
        return sorted(image_files, key=get_image_date)
    
    def _generate_photobook(self, image_files: List[str], output_path: str,
                           config: Dict[str, Any], progress_callback: Callable,
                           total_images: int) -> Dict[str, Any]:
        """Generate the complete photo book"""
        
        try:
            # Determine page size and orientation
            page_size = self._get_page_size(config["page_size"], config["orientation"])
            
            # Create document
            doc = SimpleDocTemplate(
                output_path,
                pagesize=page_size,
                **self._get_margins(config["margin_size"])
            )
            
            # Build content
            story = []
            page_count = 0
            
            # Cover page
            if config["include_cover_page"]:
                progress_callback(5, 100, "Creating cover page")
                cover_content = self._create_cover_page(image_files, config)
                story.extend(cover_content)
                page_count += 1
            
            # Table of contents
            if config["include_table_of_contents"]:
                progress_callback(10, 100, "Creating table of contents")
                toc_content = self._create_table_of_contents(image_files, config)
                story.extend(toc_content)
                page_count += 1
            
            # Group images if requested
            if config["group_by_date"]:
                image_groups = self._group_images_by_date(image_files)
            else:
                image_groups = {"All Photos": image_files}
            
            # Generate photo pages
            processed_images = 0
            
            for group_name, group_images in image_groups.items():
                # Group header
                if len(image_groups) > 1:
                    story.append(PageBreak())
                    story.append(Paragraph(group_name, self.styles['SectionTitle']))
                    story.append(Spacer(1, 20))
                    page_count += 1
                
                # Process images in the group
                pages_in_group = self._create_photo_pages(
                    group_images, config, progress_callback, 
                    processed_images, total_images
                )
                
                story.extend(pages_in_group["content"])
                page_count += pages_in_group["pages"]
                processed_images += len(group_images)
            
            # Build PDF
            progress_callback(90, 100, "Building photo book PDF")
            doc.build(story, onFirstPage=self._create_page_template(config), 
                     onLaterPages=self._create_page_template(config))
            
            progress_callback(100, 100, "Photo book generation completed")
            
            return {
                "success": True,
                "pages": page_count,
                "images_processed": processed_images
            }
            
        except Exception as e:
            logger.error(f"Photo book generation failed: {e}")
            return {"success": False, "error": str(e)}
    
    def _get_page_size(self, size: str, orientation: str) -> Tuple[float, float]:
        """Get page size tuple"""
        
        sizes = {
            "letter": letter,
            "a4": A4,
            "a3": A3,
            "a5": A5
        }
        
        page_size = sizes.get(size.lower(), letter)
        
        if orientation.lower() == "landscape":
            return (page_size[1], page_size[0])
        else:
            return page_size
    
    def _get_margins(self, margin_size: str) -> Dict[str, float]:
        """Get margin settings"""
        
        margin_settings = {
            "small": {
                "rightMargin": 0.5*inch,
                "leftMargin": 0.5*inch, 
                "topMargin": 0.5*inch,
                "bottomMargin": 0.5*inch
            },
            "normal": {
                "rightMargin": 1*inch,
                "leftMargin": 1*inch,
                "topMargin": 1*inch, 
                "bottomMargin": 0.75*inch
            },
            "large": {
                "rightMargin": 1.5*inch,
                "leftMargin": 1.5*inch,
                "topMargin": 1.5*inch,
                "bottomMargin": 1*inch
            }
        }
        
        return margin_settings.get(margin_size, margin_settings["normal"])
    
    def _create_cover_page(self, image_files: List[str], config: Dict[str, Any]) -> List:
        """Create cover page for photo book"""
        
        story = []
        
        # Cover image
        cover_image_path = config.get("cover_photo")
        if not cover_image_path and image_files:
            cover_image_path = image_files[0]  # Use first image as cover
        
        if cover_image_path and os.path.exists(cover_image_path):
            try:
                # Add cover image
                img = Image(cover_image_path)
                
                # Size for cover (larger than regular photos)
                img.drawWidth = 4*inch
                img.drawHeight = 3*inch
                
                story.append(Spacer(1, 1*inch))
                story.append(img)
                story.append(Spacer(1, 0.5*inch))
                
            except Exception as e:
                logger.warning(f"Could not add cover image: {e}")
        
        # Title
        story.append(Paragraph(config["title"], self.styles['BookTitle']))
        
        if config.get("subtitle"):
            story.append(Spacer(1, 20))
            story.append(Paragraph(config["subtitle"], self.styles['SectionTitle']))
        
        # Author
        if config.get("author"):
            story.append(Spacer(1, 1*inch))
            story.append(Paragraph(f"by {config['author']}", self.styles['Normal']))
        
        # Date
        story.append(Spacer(1, 0.5*inch))
        story.append(Paragraph(datetime.now().strftime("%B %Y"), self.styles['Normal']))
        
        story.append(PageBreak())
        
        return story
    
    def _create_table_of_contents(self, image_files: List[str], config: Dict[str, Any]) -> List:
        """Create table of contents"""
        
        story = []
        
        story.append(Paragraph("Table of Contents", self.styles['SectionTitle']))
        story.append(Spacer(1, 20))
        
        # If grouping by date, list date groups
        if config["group_by_date"]:
            image_groups = self._group_images_by_date(image_files)
            page_num = 3  # Start after cover and TOC
            
            for group_name, group_images in image_groups.items():
                story.append(Paragraph(f"{group_name} ... {page_num}", self.styles['Normal']))
                # Estimate pages for this group
                photos_per_page = config["photos_per_page"]
                group_pages = (len(group_images) + photos_per_page - 1) // photos_per_page
                page_num += group_pages
        else:
            # Simple page listing
            photos_per_page = config["photos_per_page"] 
            total_pages = (len(image_files) + photos_per_page - 1) // photos_per_page
            story.append(Paragraph(f"Photo Gallery ... 3", self.styles['Normal']))
            story.append(Paragraph(f"Total Pages: {total_pages + 2}", self.styles['Normal']))
        
        story.append(PageBreak())
        
        return story
    
    def _group_images_by_date(self, image_files: List[str]) -> Dict[str, List[str]]:
        """Group images by date"""
        
        groups = {}
        
        for image_path in image_files:
            try:
                # Get date from EXIF or file modification
                exif_data = self.metadata_extractor.extract_exif_data(image_path)
                date_str = exif_data.get("DateTime") or exif_data.get("DateTimeOriginal")
                
                if date_str:
                    date_obj = datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S")
                    group_key = date_obj.strftime("%B %Y")  # e.g., "March 2024"
                else:
                    # Use file modification date
                    file_date = datetime.fromtimestamp(os.path.getmtime(image_path))
                    group_key = file_date.strftime("%B %Y")
                
                if group_key not in groups:
                    groups[group_key] = []
                
                groups[group_key].append(image_path)
                
            except Exception as e:
                logger.warning(f"Could not get date for {image_path}: {e}")
                # Add to "Unknown Date" group
                if "Unknown Date" not in groups:
                    groups["Unknown Date"] = []
                groups["Unknown Date"].append(image_path)
        
        return groups
    
    def _create_photo_pages(self, images: List[str], config: Dict[str, Any],
                           progress_callback: Callable, processed_so_far: int,
                           total_images: int) -> Dict[str, Any]:
        """Create photo pages using the specified layout"""
        
        layout_type = config["layout_type"]
        photos_per_page = config["photos_per_page"]
        
        story = []
        pages_created = 0
        
        # Process images in chunks
        for i in range(0, len(images), photos_per_page):
            page_images = images[i:i + photos_per_page]
            
            if layout_type == "grid":
                page_content = self._create_grid_layout(page_images, config)
            elif layout_type == "magazine":
                page_content = self._create_magazine_layout(page_images, config)
            elif layout_type == "portfolio":
                page_content = self._create_portfolio_layout(page_images, config)
            elif layout_type == "collage":
                page_content = self._create_collage_layout(page_images, config)
            elif layout_type == "timeline":
                page_content = self._create_timeline_layout(page_images, config)
            else:
                page_content = self._create_grid_layout(page_images, config)  # Fallback
            
            story.extend(page_content)
            pages_created += 1
            
            # Update progress
            current_progress = processed_so_far + i + len(page_images)
            progress = 15 + (current_progress / total_images * 75)
            progress_callback(progress, 100, f"Creating photo pages: {current_progress}/{total_images}")
        
        return {"content": story, "pages": pages_created}
    
    def _create_grid_layout(self, images: List[str], config: Dict[str, Any]) -> List:
        """Create grid-style photo layout"""
        
        story = []
        
        try:
            # Determine grid size based on number of images
            if len(images) <= 2:
                cols = 1
                rows = len(images)
                img_width = 4*inch
                img_height = 3*inch
            elif len(images) <= 4:
                cols = 2
                rows = 2
                img_width = 2.5*inch
                img_height = 2*inch
            else:
                cols = 3
                rows = 2
                img_width = 2*inch
                img_height = 1.5*inch
            
            # Create table data
            table_data = []
            
            for row in range(rows):
                row_data = []
                for col in range(cols):
                    img_index = row * cols + col
                    
                    if img_index < len(images):
                        cell_content = self._create_image_cell(
                            images[img_index], config, img_width, img_height
                        )
                    else:
                        cell_content = ""  # Empty cell
                    
                    row_data.append(cell_content)
                
                table_data.append(row_data)
            
            # Create table
            table = Table(table_data, colWidths=[img_width + 0.5*inch] * cols)
            table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            
            story.append(table)
            story.append(PageBreak())
            
        except Exception as e:
            logger.error(f"Failed to create grid layout: {e}")
            # Fallback: simple image list
            for image_path in images:
                story.extend(self._create_simple_image_section(image_path, config))
        
        return story
    
    def _create_magazine_layout(self, images: List[str], config: Dict[str, Any]) -> List:
        """Create magazine-style layout"""
        
        story = []
        
        # Magazine style uses varied image sizes and positions
        for i, image_path in enumerate(images):
            if i == 0:
                # First image larger
                img_width = 4*inch
                img_height = 3*inch
            elif i % 3 == 1:
                # Smaller images
                img_width = 2*inch  
                img_height = 1.5*inch
            else:
                # Medium images
                img_width = 3*inch
                img_height = 2.25*inch
            
            content = self._create_image_cell(image_path, config, img_width, img_height)
            story.append(content)
            
            if i < len(images) - 1:
                story.append(Spacer(1, 10))
        
        story.append(PageBreak())
        return story
    
    def _create_portfolio_layout(self, images: List[str], config: Dict[str, Any]) -> List:
        """Create portfolio-style layout (fewer, larger images)"""
        
        story = []
        
        for image_path in images:
            # Large images with minimal captions
            content = self._create_image_cell(
                image_path, config, 
                img_width=5*inch, 
                img_height=4*inch
            )
            story.append(content)
            story.append(Spacer(1, 30))
        
        story.append(PageBreak())
        return story
    
    def _create_collage_layout(self, images: List[str], config: Dict[str, Any]) -> List:
        """Create collage-style layout with varied sizes"""
        
        story = []
        
        # Create a more complex table layout for collage effect
        if len(images) >= 4:
            # Create 2x2 grid with varied sizes
            table_data = []
            sizes = [
                (2.5*inch, 2*inch),    # Top left
                (2*inch, 1.5*inch),    # Top right  
                (2*inch, 1.5*inch),    # Bottom left
                (2.5*inch, 2*inch),    # Bottom right
            ]
            
            for row in range(2):
                row_data = []
                for col in range(2):
                    img_index = row * 2 + col
                    if img_index < len(images):
                        width, height = sizes[img_index]
                        cell_content = self._create_image_cell(
                            images[img_index], config, width, height
                        )
                    else:
                        cell_content = ""
                    row_data.append(cell_content)
                table_data.append(row_data)
            
            table = Table(table_data, colWidths=[3*inch, 2.5*inch])
            table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 3),
                ('RIGHTPADDING', (0, 0), (-1, -1), 3),
            ]))
            
            story.append(table)
            
            # Add remaining images if any
            for image_path in images[4:]:
                content = self._create_image_cell(image_path, config, 2*inch, 1.5*inch)
                story.append(content)
        else:
            # Simple layout for fewer images
            for image_path in images:
                content = self._create_image_cell(image_path, config, 3*inch, 2.25*inch)
                story.append(content)
                story.append(Spacer(1, 10))
        
        story.append(PageBreak())
        return story
    
    def _create_timeline_layout(self, images: List[str], config: Dict[str, Any]) -> List:
        """Create timeline-style layout"""
        
        story = []
        
        # Timeline has images with dates prominently displayed
        for i, image_path in enumerate(images):
            # Get image date
            try:
                exif_data = self.metadata_extractor.extract_exif_data(image_path)
                date_str = exif_data.get("DateTime") or exif_data.get("DateTimeOriginal")
                
                if date_str:
                    date_obj = datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S")
                    formatted_date = date_obj.strftime("%B %d, %Y")
                else:
                    file_date = datetime.fromtimestamp(os.path.getmtime(image_path))
                    formatted_date = file_date.strftime("%B %d, %Y")
                
            except Exception:
                formatted_date = "Unknown Date"
            
            # Date header
            story.append(Paragraph(formatted_date, self.styles['SectionTitle']))
            story.append(Spacer(1, 10))
            
            # Image
            content = self._create_image_cell(image_path, config, 4*inch, 3*inch)
            story.append(content)
            
            if i < len(images) - 1:
                story.append(Spacer(1, 30))
        
        story.append(PageBreak())
        return story
    
    def _create_image_cell(self, image_path: str, config: Dict[str, Any],
                          img_width: float, img_height: float) -> KeepTogether:
        """Create a cell containing an image with optional caption and metadata"""
        
        content = []
        
        try:
            # Process image
            processed_path = self._process_image(image_path, config)
            
            # Add image
            img = Image(processed_path or image_path)
            img.drawWidth = img_width
            img.drawHeight = img_height
            content.append(img)
            
            # Add caption if enabled
            if config["include_captions"]:
                filename = os.path.basename(image_path)
                caption_text = Path(filename).stem  # Filename without extension
                content.append(Paragraph(caption_text, self.styles['PhotoCaption']))
            
            # Add metadata if enabled
            if config["include_metadata"]:
                metadata_lines = self._get_image_metadata_summary(image_path)
                for line in metadata_lines[:2]:  # Limit to 2 lines
                    content.append(Paragraph(line, self.styles['PhotoMetadata']))
            
        except Exception as e:
            logger.warning(f"Could not process image {image_path}: {e}")
            # Add placeholder
            error_text = f"[Image could not be displayed: {os.path.basename(image_path)}]"
            content.append(Paragraph(error_text, self.styles['Normal']))
        
        return KeepTogether(content)
    
    def _create_simple_image_section(self, image_path: str, config: Dict[str, Any]) -> List:
        """Create simple image section (fallback)"""
        
        story = []
        
        try:
            img = Image(image_path)
            img.drawWidth = 4*inch
            img.drawHeight = 3*inch
            story.append(img)
            
            if config["include_captions"]:
                filename = os.path.basename(image_path)
                story.append(Paragraph(filename, self.styles['PhotoCaption']))
            
            story.append(Spacer(1, 20))
            
        except Exception as e:
            logger.warning(f"Could not add image {image_path}: {e}")
        
        return story
    
    def _process_image(self, image_path: str, config: Dict[str, Any]) -> Optional[str]:
        """Process image (enhance, resize, etc.) if enabled"""
        
        if not config.get("enhance_images", False):
            return None
        
        try:
            # Create processed image directory
            temp_dir = Path(settings.EXPORT_TEMP_DIR) / "processed_images"
            temp_dir.mkdir(exist_ok=True)
            
            # Process image
            with PILImage.open(image_path) as img:
                # Convert to RGB if necessary
                if img.mode in ('RGBA', 'P'):
                    img = img.convert('RGB')
                
                # Apply enhancements based on color theme
                if config.get("color_theme") == "vintage":
                    # Vintage effect
                    enhancer = ImageEnhance.Color(img)
                    img = enhancer.enhance(0.8)  # Reduce saturation
                    enhancer = ImageEnhance.Contrast(img)
                    img = enhancer.enhance(1.1)  # Increase contrast slightly
                elif config.get("color_theme") == "warm":
                    # Warm tones
                    enhancer = ImageEnhance.Color(img)
                    img = enhancer.enhance(1.1)  # Increase saturation
                elif config.get("color_theme") == "cool":
                    # Cool tones - could implement color temperature adjustment
                    pass
                
                # Save processed image
                processed_filename = f"processed_{os.path.basename(image_path)}"
                processed_path = temp_dir / processed_filename
                
                img.save(
                    processed_path,
                    "JPEG",
                    quality=config.get("max_image_quality", 95),
                    optimize=True
                )
                
                return str(processed_path)
                
        except Exception as e:
            logger.warning(f"Could not process image {image_path}: {e}")
            return None
    
    def _get_image_metadata_summary(self, image_path: str) -> List[str]:
        """Get brief metadata summary for image"""
        
        metadata_lines = []
        
        try:
            # Get file metadata
            file_metadata = get_file_metadata(image_path)
            
            # File size
            if file_metadata.get("size"):
                size_mb = file_metadata["size"] / (1024 * 1024)
                metadata_lines.append(f"Size: {size_mb:.1f} MB")
            
            # Image dimensions
            try:
                with PILImage.open(image_path) as img:
                    width, height = img.size
                    metadata_lines.append(f"Dimensions: {width} × {height}")
            except Exception:
                pass
            
            # Camera info from EXIF
            try:
                exif_data = self.metadata_extractor.extract_exif_data(image_path)
                
                camera = exif_data.get("Model") or exif_data.get("Make")
                if camera:
                    metadata_lines.append(f"Camera: {camera}")
                
                # Camera settings
                settings_parts = []
                if exif_data.get("FNumber"):
                    settings_parts.append(f"f/{exif_data['FNumber']}")
                if exif_data.get("ExposureTime"):
                    settings_parts.append(f"{exif_data['ExposureTime']}s")
                if exif_data.get("ISO"):
                    settings_parts.append(f"ISO {exif_data['ISO']}")
                
                if settings_parts:
                    metadata_lines.append(" • ".join(settings_parts))
                
            except Exception:
                pass
            
        except Exception as e:
            logger.warning(f"Could not extract metadata for {image_path}: {e}")
        
        return metadata_lines[:3]  # Return max 3 lines
    
    def _create_page_template(self, config: Dict[str, Any]):
        """Create page template with headers/footers"""
        
        def page_template(canvas, doc):
            canvas.saveState()
            
            # Add page number
            page_num = canvas.getPageNumber()
            canvas.setFont("Helvetica", 10)
            canvas.setFillColor(gray)
            
            # Bottom center page number
            canvas.drawCentredText(
                doc.width / 2.0 + doc.leftMargin, 
                0.5 * inch, 
                str(page_num)
            )
            
            canvas.restoreState()
        
        return page_template