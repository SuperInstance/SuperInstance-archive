"""
Archive Export (ZIP, tar.gz) with preserved directory structure and metadata
"""

import os
import logging
import zipfile
import tarfile
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Callable, Optional
import shutil

from ..core.config import settings
from ..utils.file_utils import get_file_metadata, get_files_by_filters
from ..utils.metadata_extractor import MetadataExtractor

logger = logging.getLogger(__name__)

class ArchiveExporter:
    """Archive export supporting ZIP and tar.gz formats"""
    
    def __init__(self):
        self.metadata_extractor = MetadataExtractor()
        
    async def initialize(self):
        """Initialize archive exporter"""
        logger.info("Archive exporter initialized")
    
    def export(self, job_id: str, config: Dict[str, Any], 
              filters: Dict[str, Any], output_dir: str,
              progress_callback: Callable) -> Dict[str, Any]:
        """
        Export files to archive format (ZIP or tar.gz)
        
        Args:
            job_id: Export job identifier
            config: Archive export configuration
            filters: File selection filters
            output_dir: Output directory path
            progress_callback: Progress reporting callback
            
        Returns:
            Export result with file path and metadata
        """
        
        try:
            progress_callback(0, 100, "Initializing archive export")
            
            # Get files to export
            files = get_files_by_filters(filters)
            total_files = len(files)
            
            if total_files == 0:
                return {"success": False, "error": "No files found matching filters"}
            
            # Get archive configuration
            archive_config = self._get_archive_config(config)
            archive_format = archive_config["format"]
            
            # Create archive file
            if archive_format == "zip":
                output_filename = f"export_{job_id}.zip"
                result = self._create_zip_archive(
                    files, output_dir, output_filename, 
                    archive_config, progress_callback, total_files
                )
            else:  # tar.gz
                output_filename = f"export_{job_id}.tar.gz"
                result = self._create_tar_archive(
                    files, output_dir, output_filename,
                    archive_config, progress_callback, total_files
                )
            
            if result["success"]:
                output_path = os.path.join(output_dir, output_filename)
                progress_callback(100, 100, "Archive export completed")
                
                return {
                    "success": True,
                    "output_path": output_path,
                    "filename": output_filename,
                    "file_size": os.path.getsize(output_path),
                    "files_included": result.get("files_added", 0),
                    "compression_ratio": result.get("compression_ratio", 0)
                }
            else:
                return result
                
        except Exception as e:
            logger.error(f"Archive export failed for job {job_id}: {e}")
            return {"success": False, "error": str(e)}
    
    def _get_archive_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Get archive configuration with defaults"""
        
        return {
            "format": config.get("format", "zip"),  # zip or tar.gz
            "compression_level": config.get("compression_level", settings.export.compression_level),
            "preserve_structure": config.get("preserve_structure", True),
            "include_metadata": config.get("include_metadata", True),
            "include_hidden": config.get("include_hidden", False),
            "follow_symlinks": config.get("follow_symlinks", False),
            "exclude_patterns": config.get("exclude_patterns", []),
            "max_file_size": config.get("max_file_size", 0),  # 0 = no limit
            "create_manifest": config.get("create_manifest", True),
            "metadata_format": config.get("metadata_format", "json")  # json or txt
        }
    
    def _create_zip_archive(self, files: List[str], output_dir: str, 
                           filename: str, config: Dict[str, Any],
                           progress_callback: Callable, total_files: int) -> Dict[str, Any]:
        """Create ZIP archive"""
        
        try:
            output_path = os.path.join(output_dir, filename)
            
            # Compression method
            compression = zipfile.ZIP_DEFLATED
            compresslevel = config["compression_level"]
            
            original_size = 0
            compressed_size = 0
            files_added = 0
            
            with zipfile.ZipFile(output_path, 'w', compression=compression, 
                               compresslevel=compresslevel) as zipf:
                
                # Create manifest if requested
                manifest_data = []
                
                for i, file_path in enumerate(files):
                    try:
                        # Skip files that match exclude patterns
                        if self._should_exclude_file(file_path, config):
                            continue
                        
                        # Check file size limit
                        file_size = os.path.getsize(file_path)
                        if config["max_file_size"] > 0 and file_size > config["max_file_size"]:
                            logger.warning(f"Skipping large file {file_path}: {file_size} bytes")
                            continue
                        
                        # Determine archive path
                        if config["preserve_structure"]:
                            # Use relative path from common root
                            archive_path = self._get_relative_path(file_path, files)
                        else:
                            # Use just filename
                            archive_path = os.path.basename(file_path)
                        
                        # Add file to archive
                        zipf.write(file_path, archive_path)
                        
                        original_size += file_size
                        files_added += 1
                        
                        # Add to manifest
                        if config["create_manifest"]:
                            file_metadata = get_file_metadata(file_path)
                            manifest_data.append({
                                "original_path": file_path,
                                "archive_path": archive_path,
                                "size": file_size,
                                "modified": file_metadata.get("modified_time"),
                                "checksum": file_metadata.get("checksum")
                            })
                        
                        # Update progress
                        progress = 10 + (i / total_files * 80)
                        progress_callback(progress, 100, f"Added {files_added} files to ZIP")
                        
                    except Exception as e:
                        logger.warning(f"Failed to add file {file_path} to ZIP: {e}")
                
                # Add manifest file
                if config["create_manifest"] and manifest_data:
                    progress_callback(90, 100, "Creating manifest")
                    self._add_manifest_to_zip(zipf, manifest_data, config)
                
                # Add metadata files if requested
                if config["include_metadata"]:
                    progress_callback(95, 100, "Adding metadata files")
                    self._add_metadata_to_zip(zipf, files, config)
            
            # Calculate compression ratio
            compressed_size = os.path.getsize(output_path)
            compression_ratio = original_size / compressed_size if compressed_size > 0 else 1.0
            
            return {
                "success": True,
                "files_added": files_added,
                "original_size": original_size,
                "compressed_size": compressed_size,
                "compression_ratio": compression_ratio
            }
            
        except Exception as e:
            logger.error(f"Failed to create ZIP archive: {e}")
            return {"success": False, "error": str(e)}
    
    def _create_tar_archive(self, files: List[str], output_dir: str,
                           filename: str, config: Dict[str, Any], 
                           progress_callback: Callable, total_files: int) -> Dict[str, Any]:
        """Create tar.gz archive"""
        
        try:
            output_path = os.path.join(output_dir, filename)
            
            original_size = 0
            files_added = 0
            
            with tarfile.open(output_path, 'w:gz', compresslevel=config["compression_level"]) as tarf:
                
                # Create manifest if requested
                manifest_data = []
                
                for i, file_path in enumerate(files):
                    try:
                        # Skip files that match exclude patterns
                        if self._should_exclude_file(file_path, config):
                            continue
                        
                        # Check file size limit
                        file_size = os.path.getsize(file_path)
                        if config["max_file_size"] > 0 and file_size > config["max_file_size"]:
                            logger.warning(f"Skipping large file {file_path}: {file_size} bytes")
                            continue
                        
                        # Determine archive path
                        if config["preserve_structure"]:
                            archive_path = self._get_relative_path(file_path, files)
                        else:
                            archive_path = os.path.basename(file_path)
                        
                        # Add file to archive
                        tarf.add(file_path, arcname=archive_path, recursive=False)
                        
                        original_size += file_size
                        files_added += 1
                        
                        # Add to manifest
                        if config["create_manifest"]:
                            file_metadata = get_file_metadata(file_path)
                            manifest_data.append({
                                "original_path": file_path,
                                "archive_path": archive_path,
                                "size": file_size,
                                "modified": file_metadata.get("modified_time"),
                                "checksum": file_metadata.get("checksum")
                            })
                        
                        # Update progress
                        progress = 10 + (i / total_files * 80)
                        progress_callback(progress, 100, f"Added {files_added} files to tar.gz")
                        
                    except Exception as e:
                        logger.warning(f"Failed to add file {file_path} to tar.gz: {e}")
                
                # Add manifest file
                if config["create_manifest"] and manifest_data:
                    progress_callback(90, 100, "Creating manifest")
                    self._add_manifest_to_tar(tarf, manifest_data, config)
                
                # Add metadata files if requested
                if config["include_metadata"]:
                    progress_callback(95, 100, "Adding metadata files")
                    self._add_metadata_to_tar(tarf, files, config)
            
            # Calculate compression ratio
            compressed_size = os.path.getsize(output_path)
            compression_ratio = original_size / compressed_size if compressed_size > 0 else 1.0
            
            return {
                "success": True,
                "files_added": files_added,
                "original_size": original_size,
                "compressed_size": compressed_size,
                "compression_ratio": compression_ratio
            }
            
        except Exception as e:
            logger.error(f"Failed to create tar.gz archive: {e}")
            return {"success": False, "error": str(e)}
    
    def _should_exclude_file(self, file_path: str, config: Dict[str, Any]) -> bool:
        """Check if file should be excluded"""
        
        # Check hidden files
        if not config["include_hidden"]:
            if os.path.basename(file_path).startswith('.'):
                return True
        
        # Check exclude patterns
        for pattern in config.get("exclude_patterns", []):
            if pattern in file_path:
                return True
        
        return False
    
    def _get_relative_path(self, file_path: str, all_files: List[str]) -> str:
        """Get relative path for archive maintaining directory structure"""
        
        try:
            # Find common root directory
            common_path = os.path.commonpath(all_files)
            
            # Get relative path from common root
            relative_path = os.path.relpath(file_path, common_path)
            
            return relative_path
            
        except Exception:
            # Fallback to basename if can't determine relative path
            return os.path.basename(file_path)
    
    def _add_manifest_to_zip(self, zipf: zipfile.ZipFile, manifest_data: List[Dict], 
                            config: Dict[str, Any]):
        """Add manifest file to ZIP archive"""
        
        try:
            manifest = {
                "created": datetime.utcnow().isoformat(),
                "format": "zip",
                "total_files": len(manifest_data),
                "files": manifest_data
            }
            
            if config["metadata_format"] == "json":
                manifest_content = json.dumps(manifest, indent=2, default=str)
                manifest_filename = "MANIFEST.json"
            else:
                # Text format
                lines = [
                    f"Archive Manifest",
                    f"Created: {manifest['created']}",
                    f"Format: {manifest['format']}",
                    f"Total Files: {manifest['total_files']}",
                    "",
                    "Files:"
                ]
                
                for file_data in manifest_data:
                    lines.append(f"  {file_data['archive_path']}")
                    lines.append(f"    Original: {file_data['original_path']}")
                    lines.append(f"    Size: {file_data['size']} bytes")
                    if file_data.get('modified'):
                        lines.append(f"    Modified: {file_data['modified']}")
                    lines.append("")
                
                manifest_content = "\n".join(lines)
                manifest_filename = "MANIFEST.txt"
            
            # Add manifest to archive
            zipf.writestr(manifest_filename, manifest_content)
            
        except Exception as e:
            logger.warning(f"Failed to create manifest: {e}")
    
    def _add_manifest_to_tar(self, tarf: tarfile.TarFile, manifest_data: List[Dict],
                            config: Dict[str, Any]):
        """Add manifest file to tar.gz archive"""
        
        try:
            manifest = {
                "created": datetime.utcnow().isoformat(),
                "format": "tar.gz",
                "total_files": len(manifest_data),
                "files": manifest_data
            }
            
            if config["metadata_format"] == "json":
                manifest_content = json.dumps(manifest, indent=2, default=str)
                manifest_filename = "MANIFEST.json"
            else:
                # Text format
                lines = [
                    f"Archive Manifest",
                    f"Created: {manifest['created']}",
                    f"Format: {manifest['format']}",
                    f"Total Files: {manifest['total_files']}",
                    "",
                    "Files:"
                ]
                
                for file_data in manifest_data:
                    lines.append(f"  {file_data['archive_path']}")
                    lines.append(f"    Original: {file_data['original_path']}")
                    lines.append(f"    Size: {file_data['size']} bytes")
                    if file_data.get('modified'):
                        lines.append(f"    Modified: {file_data['modified']}")
                    lines.append("")
                
                manifest_content = "\n".join(lines)
                manifest_filename = "MANIFEST.txt"
            
            # Create tarinfo and add to archive
            tarinfo = tarfile.TarInfo(name=manifest_filename)
            tarinfo.size = len(manifest_content.encode('utf-8'))
            tarinfo.mtime = datetime.utcnow().timestamp()
            
            from io import BytesIO
            tarf.addfile(tarinfo, BytesIO(manifest_content.encode('utf-8')))
            
        except Exception as e:
            logger.warning(f"Failed to create manifest: {e}")
    
    def _add_metadata_to_zip(self, zipf: zipfile.ZipFile, files: List[str], 
                            config: Dict[str, Any]):
        """Add metadata files to ZIP archive"""
        
        try:
            # Create comprehensive metadata file
            metadata_collection = {
                "export_info": {
                    "created": datetime.utcnow().isoformat(),
                    "total_files": len(files),
                    "format": "zip"
                },
                "files": []
            }
            
            # Extract metadata for each file
            for file_path in files[:100]:  # Limit to first 100 files for metadata
                try:
                    file_metadata = self.metadata_extractor.extract_all_metadata(file_path)
                    
                    metadata_collection["files"].append({
                        "path": file_path,
                        "metadata": file_metadata
                    })
                    
                except Exception as e:
                    logger.warning(f"Failed to extract metadata for {file_path}: {e}")
            
            # Add metadata file
            if config["metadata_format"] == "json":
                metadata_content = json.dumps(metadata_collection, indent=2, default=str)
                zipf.writestr("metadata.json", metadata_content)
            else:
                # Create text format metadata
                lines = []
                lines.append("File Metadata Export")
                lines.append(f"Created: {metadata_collection['export_info']['created']}")
                lines.append(f"Total Files: {metadata_collection['export_info']['total_files']}")
                lines.append("")
                
                for file_data in metadata_collection["files"]:
                    lines.append(f"File: {file_data['path']}")
                    for key, value in file_data["metadata"].items():
                        lines.append(f"  {key}: {value}")
                    lines.append("")
                
                metadata_content = "\n".join(lines)
                zipf.writestr("metadata.txt", metadata_content)
            
        except Exception as e:
            logger.warning(f"Failed to add metadata files: {e}")
    
    def _add_metadata_to_tar(self, tarf: tarfile.TarFile, files: List[str],
                            config: Dict[str, Any]):
        """Add metadata files to tar.gz archive"""
        
        try:
            # Create comprehensive metadata file
            metadata_collection = {
                "export_info": {
                    "created": datetime.utcnow().isoformat(),
                    "total_files": len(files),
                    "format": "tar.gz"
                },
                "files": []
            }
            
            # Extract metadata for each file
            for file_path in files[:100]:  # Limit to first 100 files for metadata
                try:
                    file_metadata = self.metadata_extractor.extract_all_metadata(file_path)
                    
                    metadata_collection["files"].append({
                        "path": file_path,
                        "metadata": file_metadata
                    })
                    
                except Exception as e:
                    logger.warning(f"Failed to extract metadata for {file_path}: {e}")
            
            # Add metadata file
            if config["metadata_format"] == "json":
                metadata_content = json.dumps(metadata_collection, indent=2, default=str)
                filename = "metadata.json"
            else:
                # Create text format metadata
                lines = []
                lines.append("File Metadata Export")
                lines.append(f"Created: {metadata_collection['export_info']['created']}")
                lines.append(f"Total Files: {metadata_collection['export_info']['total_files']}")
                lines.append("")
                
                for file_data in metadata_collection["files"]:
                    lines.append(f"File: {file_data['path']}")
                    for key, value in file_data["metadata"].items():
                        lines.append(f"  {key}: {value}")
                    lines.append("")
                
                metadata_content = "\n".join(lines)
                filename = "metadata.txt"
            
            # Create tarinfo and add to archive
            tarinfo = tarfile.TarInfo(name=filename)
            tarinfo.size = len(metadata_content.encode('utf-8'))
            tarinfo.mtime = datetime.utcnow().timestamp()
            
            from io import BytesIO
            tarf.addfile(tarinfo, BytesIO(metadata_content.encode('utf-8')))
            
        except Exception as e:
            logger.warning(f"Failed to add metadata files: {e}")
    
    def extract_archive(self, archive_path: str, extract_to: str) -> Dict[str, Any]:
        """Extract archive (utility method)"""
        
        try:
            # Determine archive type
            if archive_path.endswith('.zip'):
                return self._extract_zip(archive_path, extract_to)
            elif archive_path.endswith(('.tar.gz', '.tgz')):
                return self._extract_tar(archive_path, extract_to)
            else:
                return {"success": False, "error": "Unsupported archive format"}
                
        except Exception as e:
            logger.error(f"Failed to extract archive {archive_path}: {e}")
            return {"success": False, "error": str(e)}
    
    def _extract_zip(self, zip_path: str, extract_to: str) -> Dict[str, Any]:
        """Extract ZIP archive"""
        
        try:
            os.makedirs(extract_to, exist_ok=True)
            
            with zipfile.ZipFile(zip_path, 'r') as zipf:
                zipf.extractall(extract_to)
                file_count = len(zipf.namelist())
            
            return {
                "success": True,
                "extracted_files": file_count,
                "extract_path": extract_to
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _extract_tar(self, tar_path: str, extract_to: str) -> Dict[str, Any]:
        """Extract tar.gz archive"""
        
        try:
            os.makedirs(extract_to, exist_ok=True)
            
            with tarfile.open(tar_path, 'r:gz') as tarf:
                tarf.extractall(extract_to)
                file_count = len(tarf.getnames())
            
            return {
                "success": True,
                "extracted_files": file_count,
                "extract_path": extract_to
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}