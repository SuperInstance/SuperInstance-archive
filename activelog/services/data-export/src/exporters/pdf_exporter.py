"""
PDF Export with preserved metadata and rich formatting
"""

import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Callable, Optional
import json

from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.lib.colors import black, blue, gray, white
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak,
    Table, TableStyle, KeepTogether
)
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from PIL import Image as PILImage
import exifread
import piexif

from ..core.config import settings
from ..utils.file_utils import get_file_metadata, get_files_by_filters
from ..utils.metadata_extractor import MetadataExtractor

logger = logging.getLogger(__name__)

class PDFExporter:
    """PDF export with rich formatting and metadata preservation"""
    
    def __init__(self):
        self.styles = None
        self.metadata_extractor = MetadataExtractor()
        
    async def initialize(self):
        """Initialize PDF exporter"""
        self.styles = self._create_styles()
        logger.info("PDF exporter initialized")
    
    def _create_styles(self):
        """Create custom PDF styles"""
        styles = getSampleStyleSheet()
        
        # Custom styles
        styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            textColor=colors.darkblue,
            alignment=TA_CENTER
        ))
        
        styles.add(ParagraphStyle(
            name='CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            spaceAfter=12,
            textColor=colors.darkblue,
            leftIndent=0
        ))
        
        styles.add(ParagraphStyle(
            name='MetadataLabel',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.darkgray,
            fontName='Helvetica-Bold'
        ))
        
        styles.add(ParagraphStyle(
            name='MetadataValue',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.black,
            leftIndent=20
        ))
        
        styles.add(ParagraphStyle(
            name='ImageCaption',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.darkgray,
            alignment=TA_CENTER,
            spaceAfter=12
        ))
        
        styles.add(ParagraphStyle(
            name='FileInfo',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.gray,
            fontName='Courier'
        ))
        
        return styles
    
    def export(self, job_id: str, config: Dict[str, Any], 
              filters: Dict[str, Any], output_dir: str,
              progress_callback: Callable) -> Dict[str, Any]:
        """
        Export files to PDF format
        
        Args:
            job_id: Export job identifier
            config: PDF export configuration
            filters: File selection filters
            output_dir: Output directory path
            progress_callback: Progress reporting callback
            
        Returns:
            Export result with file path and metadata
        """
        
        try:
            progress_callback(0, 100, "Initializing PDF export")
            
            # Get files to export
            files = get_files_by_filters(filters)
            total_files = len(files)
            
            if total_files == 0:
                return {"success": False, "error": "No files found matching filters"}
            
            # Configure PDF
            pdf_config = self._get_pdf_config(config)
            
            # Create PDF file
            output_filename = f"export_{job_id}.pdf"
            output_path = os.path.join(output_dir, output_filename)
            
            # Generate PDF
            result = self._generate_pdf(
                files=files,
                output_path=output_path,
                config=pdf_config,
                progress_callback=progress_callback,
                total_files=total_files
            )
            
            if result["success"]:
                progress_callback(100, 100, "PDF export completed")
                return {
                    "success": True,
                    "output_path": output_path,
                    "filename": output_filename,
                    "file_size": os.path.getsize(output_path),
                    "pages_created": result.get("pages", 0),
                    "files_included": total_files
                }
            else:
                return result
                
        except Exception as e:
            logger.error(f"PDF export failed for job {job_id}: {e}")
            return {"success": False, "error": str(e)}
    
    def _get_pdf_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Get PDF configuration with defaults"""
        
        return {
            "page_size": config.get("page_size", "letter"),
            "include_metadata": config.get("include_metadata", True),
            "include_images": config.get("include_images", True),
            "include_thumbnails": config.get("include_thumbnails", True),
            "image_quality": config.get("image_quality", settings.export.pdf_quality),
            "compress_images": config.get("compress_images", settings.export.pdf_compress_images),
            "max_image_width": config.get("max_image_width", 400),
            "max_image_height": config.get("max_image_height", 300),
            "show_file_paths": config.get("show_file_paths", True),
            "group_by_type": config.get("group_by_type", False),
            "include_exif": config.get("include_exif", True),
            "table_of_contents": config.get("table_of_contents", True)
        }
    
    def _generate_pdf(self, files: List[str], output_path: str, 
                     config: Dict[str, Any], progress_callback: Callable,
                     total_files: int) -> Dict[str, Any]:
        """Generate PDF document"""
        
        try:
            # Determine page size
            page_size = letter if config["page_size"] == "letter" else A4
            
            # Create document
            doc = SimpleDocTemplate(
                output_path,
                pagesize=page_size,
                rightMargin=72,
                leftMargin=72,
                topMargin=72,
                bottomMargin=18
            )
            
            # Build content
            story = []
            
            # Title page
            progress_callback(5, 100, "Creating title page")
            story.extend(self._create_title_page(files, config))
            
            # Table of contents (if enabled)
            if config["table_of_contents"]:
                progress_callback(10, 100, "Generating table of contents")
                story.extend(self._create_table_of_contents(files, config))
            
            # Group files if requested
            if config["group_by_type"]:
                file_groups = self._group_files_by_type(files)
            else:
                file_groups = {"All Files": files}
            
            # Process each group
            processed_files = 0
            total_pages = 0
            
            for group_name, group_files in file_groups.items():
                progress_callback(
                    10 + (processed_files / total_files * 80), 
                    100, 
                    f"Processing {group_name}"
                )
                
                # Group header
                if len(file_groups) > 1:
                    story.append(PageBreak())
                    story.append(Paragraph(group_name, self.styles['CustomHeading']))
                    story.append(Spacer(1, 12))
                
                # Process files in group
                for file_path in group_files:
                    try:
                        file_content = self._create_file_section(file_path, config)
                        story.extend(file_content)
                        processed_files += 1
                        
                        # Update progress
                        progress = 10 + (processed_files / total_files * 80)
                        progress_callback(progress, 100, f"Processed {processed_files}/{total_files} files")
                        
                    except Exception as e:
                        logger.warning(f"Failed to process file {file_path}: {e}")
                        # Add error note
                        story.append(Paragraph(f"<b>File:</b> {file_path}", self.styles['Normal']))
                        story.append(Paragraph(f"<i>Error: Could not process file - {str(e)}</i>", 
                                             self.styles['MetadataValue']))
                        story.append(Spacer(1, 12))
            
            # Build PDF
            progress_callback(90, 100, "Building PDF document")
            doc.build(story)
            
            # Get page count
            try:
                # Simple page count estimation
                total_pages = len(story) // 10  # Rough estimate
            except:
                total_pages = 1
            
            progress_callback(100, 100, "PDF generation completed")
            
            return {
                "success": True,
                "pages": total_pages,
                "files_processed": processed_files
            }
            
        except Exception as e:
            logger.error(f"PDF generation failed: {e}")
            return {"success": False, "error": str(e)}
    
    def _create_title_page(self, files: List[str], config: Dict[str, Any]) -> List:
        """Create PDF title page"""
        
        story = []
        
        # Title
        title = "ActiveLog Data Export"
        story.append(Paragraph(title, self.styles['CustomTitle']))
        story.append(Spacer(1, 30))
        
        # Export info
        export_info = [
            f"Export Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Total Files: {len(files)}",
            f"Export Format: PDF"
        ]
        
        for info in export_info:
            story.append(Paragraph(info, self.styles['Normal']))
        
        story.append(Spacer(1, 20))
        
        # Configuration summary
        story.append(Paragraph("Export Configuration:", self.styles['CustomHeading']))
        
        config_items = [
            f"Include Metadata: {'Yes' if config['include_metadata'] else 'No'}",
            f"Include Images: {'Yes' if config['include_images'] else 'No'}",
            f"Include EXIF Data: {'Yes' if config['include_exif'] else 'No'}",
            f"Page Size: {config['page_size'].upper()}"
        ]
        
        for item in config_items:
            story.append(Paragraph(f"• {item}", self.styles['Normal']))
        
        story.append(PageBreak())
        
        return story
    
    def _create_table_of_contents(self, files: List[str], config: Dict[str, Any]) -> List:
        """Create table of contents"""
        
        story = []
        
        story.append(Paragraph("Table of Contents", self.styles['CustomHeading']))
        story.append(Spacer(1, 12))
        
        # Group files for TOC
        if config["group_by_type"]:
            file_groups = self._group_files_by_type(files)
            
            for group_name, group_files in file_groups.items():
                story.append(Paragraph(f"<b>{group_name}</b> ({len(group_files)} files)", 
                                     self.styles['Normal']))
                
                # List first few files in each group
                for file_path in group_files[:5]:
                    filename = os.path.basename(file_path)
                    story.append(Paragraph(f"  • {filename}", self.styles['MetadataValue']))
                
                if len(group_files) > 5:
                    story.append(Paragraph(f"  ... and {len(group_files) - 5} more files", 
                                         self.styles['MetadataValue']))
                
                story.append(Spacer(1, 6))
        else:
            # Simple file list
            for i, file_path in enumerate(files[:20]):  # Show first 20
                filename = os.path.basename(file_path)
                story.append(Paragraph(f"{i+1}. {filename}", self.styles['Normal']))
            
            if len(files) > 20:
                story.append(Paragraph(f"... and {len(files) - 20} more files", 
                                     self.styles['MetadataValue']))
        
        story.append(PageBreak())
        
        return story
    
    def _create_file_section(self, file_path: str, config: Dict[str, Any]) -> List:
        """Create PDF section for a single file"""
        
        story = []
        
        try:
            # File header
            filename = os.path.basename(file_path)
            story.append(Paragraph(f"<b>{filename}</b>", self.styles['CustomHeading']))
            
            if config["show_file_paths"]:
                story.append(Paragraph(f"<i>{file_path}</i>", self.styles['FileInfo']))
            
            story.append(Spacer(1, 6))
            
            # File metadata
            if config["include_metadata"]:
                metadata = get_file_metadata(file_path)
                story.extend(self._create_metadata_section(metadata))
            
            # Handle different file types
            file_extension = Path(file_path).suffix.lower()
            
            if self._is_image_file(file_extension) and config["include_images"]:
                image_section = self._create_image_section(file_path, config)
                story.extend(image_section)
            elif self._is_text_file(file_extension):
                text_section = self._create_text_section(file_path, config)
                story.extend(text_section)
            else:
                # Generic file info
                story.append(Paragraph(f"File Type: {file_extension.upper()} file", 
                                     self.styles['Normal']))
            
            # EXIF data for images
            if (self._is_image_file(file_extension) and 
                config["include_exif"] and config["include_metadata"]):
                exif_section = self._create_exif_section(file_path)
                story.extend(exif_section)
            
            story.append(Spacer(1, 20))
            
        except Exception as e:
            logger.warning(f"Error creating section for {file_path}: {e}")
            story.append(Paragraph(f"Error processing file: {str(e)}", 
                                 self.styles['MetadataValue']))
        
        return story
    
    def _create_metadata_section(self, metadata: Dict[str, Any]) -> List:
        """Create metadata section"""
        
        story = []
        
        if not metadata:
            return story
        
        # Create metadata table
        table_data = []
        
        for key, value in metadata.items():
            if value is not None and value != "":
                # Format value
                if isinstance(value, datetime):
                    formatted_value = value.strftime("%Y-%m-%d %H:%M:%S")
                elif isinstance(value, (int, float)):
                    if key.lower().endswith('size'):
                        formatted_value = self._format_file_size(value)
                    else:
                        formatted_value = str(value)
                else:
                    formatted_value = str(value)
                
                table_data.append([
                    Paragraph(f"<b>{key}:</b>", self.styles['MetadataLabel']),
                    Paragraph(formatted_value, self.styles['MetadataValue'])
                ])
        
        if table_data:
            table = Table(table_data, colWidths=[2*inch, 4*inch])
            table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                ('TOPPADDING', (0, 0), (-1, -1), 2),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ]))
            
            story.append(table)
            story.append(Spacer(1, 12))
        
        return story
    
    def _create_image_section(self, file_path: str, config: Dict[str, Any]) -> List:
        """Create image section with thumbnail"""
        
        story = []
        
        try:
            # Add image
            img = Image(file_path)
            
            # Calculate size to fit in page
            max_width = config["max_image_width"]
            max_height = config["max_image_height"]
            
            # Get actual image dimensions
            pil_img = PILImage.open(file_path)
            img_width, img_height = pil_img.size
            
            # Calculate scaling
            width_scale = max_width / img_width
            height_scale = max_height / img_height
            scale = min(width_scale, height_scale, 1.0)  # Don't upscale
            
            final_width = img_width * scale
            final_height = img_height * scale
            
            img.drawWidth = final_width
            img.drawHeight = final_height
            
            story.append(img)
            
            # Image caption
            caption = f"Image: {os.path.basename(file_path)} ({img_width}x{img_height})"
            story.append(Paragraph(caption, self.styles['ImageCaption']))
            
        except Exception as e:
            logger.warning(f"Could not include image {file_path}: {e}")
            story.append(Paragraph(f"[Image could not be displayed: {str(e)}]", 
                                 self.styles['MetadataValue']))
        
        return story
    
    def _create_text_section(self, file_path: str, config: Dict[str, Any]) -> List:
        """Create text file content section"""
        
        story = []
        
        try:
            # Read file content (limit size)
            max_size = 10000  # 10KB limit for text preview
            
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read(max_size)
            
            if len(content) == max_size:
                content += "\n... (content truncated)"
            
            # Add content
            story.append(Paragraph("<b>Content Preview:</b>", self.styles['MetadataLabel']))
            story.append(Spacer(1, 6))
            
            # Format content (escape HTML and preserve some formatting)
            content = content.replace('<', '&lt;').replace('>', '&gt;')
            content = content.replace('\n', '<br/>')
            
            story.append(Paragraph(content, self.styles['FileInfo']))
            
        except Exception as e:
            logger.warning(f"Could not read text file {file_path}: {e}")
            story.append(Paragraph(f"[Text content could not be displayed: {str(e)}]", 
                                 self.styles['MetadataValue']))
        
        return story
    
    def _create_exif_section(self, file_path: str) -> List:
        """Create EXIF data section for images"""
        
        story = []
        
        try:
            exif_data = self.metadata_extractor.extract_exif_data(file_path)
            
            if exif_data:
                story.append(Paragraph("<b>EXIF Data:</b>", self.styles['MetadataLabel']))
                story.append(Spacer(1, 6))
                
                # Create EXIF table
                table_data = []
                
                for key, value in exif_data.items():
                    if value and str(value).strip():
                        table_data.append([
                            Paragraph(f"{key}:", self.styles['MetadataLabel']),
                            Paragraph(str(value), self.styles['MetadataValue'])
                        ])
                
                if table_data:
                    table = Table(table_data, colWidths=[2*inch, 4*inch])
                    table.setStyle(TableStyle([
                        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                        ('FONTSIZE', (0, 0), (-1, -1), 8),
                        ('LEFTPADDING', (0, 0), (-1, -1), 0),
                        ('TOPPADDING', (0, 0), (-1, -1), 1),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
                    ]))
                    
                    story.append(table)
                    story.append(Spacer(1, 12))
                
        except Exception as e:
            logger.warning(f"Could not extract EXIF data from {file_path}: {e}")
        
        return story
    
    def _group_files_by_type(self, files: List[str]) -> Dict[str, List[str]]:
        """Group files by type"""
        
        groups = {
            "Images": [],
            "Documents": [],
            "Videos": [],
            "Audio": [],
            "Archives": [],
            "Other": []
        }
        
        for file_path in files:
            extension = Path(file_path).suffix.lower()
            
            if extension in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp']:
                groups["Images"].append(file_path)
            elif extension in ['.pdf', '.doc', '.docx', '.txt', '.rtf', '.odt']:
                groups["Documents"].append(file_path)
            elif extension in ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv']:
                groups["Videos"].append(file_path)
            elif extension in ['.mp3', '.wav', '.flac', '.aac', '.ogg']:
                groups["Audio"].append(file_path)
            elif extension in ['.zip', '.rar', '.7z', '.tar', '.gz']:
                groups["Archives"].append(file_path)
            else:
                groups["Other"].append(file_path)
        
        # Remove empty groups
        return {k: v for k, v in groups.items() if v}
    
    def _is_image_file(self, extension: str) -> bool:
        """Check if file is an image"""
        return extension in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp']
    
    def _is_text_file(self, extension: str) -> bool:
        """Check if file is text-based"""
        return extension in ['.txt', '.md', '.py', '.js', '.html', '.css', '.json', '.xml', '.csv']
    
    def _format_file_size(self, size_bytes: int) -> str:
        """Format file size in human readable format"""
        
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"