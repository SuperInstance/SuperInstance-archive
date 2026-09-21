"""
File Upload Security for ActiveLog
Implements comprehensive file upload validation, virus scanning, and security controls.
"""

import os
import mimetypes
import hashlib
import magic
import tempfile
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, BinaryIO
import re
from dataclasses import dataclass
from enum import Enum
import time
import logging
from PIL import Image, ImageFile
import zipfile
import tarfile
import json


class FileValidationResult(Enum):
    """File validation result status."""
    SAFE = "safe"
    SUSPICIOUS = "suspicious"
    MALICIOUS = "malicious"
    BLOCKED = "blocked"
    ERROR = "error"


@dataclass
class FileValidationReport:
    """File validation report."""
    filename: str
    original_size: int
    mime_type: str
    file_extension: str
    detected_type: str
    validation_result: FileValidationResult
    security_score: int  # 0-100
    issues: List[str]
    warnings: List[str]
    metadata: Dict[str, Any]
    hash_sha256: str
    scan_duration_ms: int


class FileUploadSecurityManager:
    """Manages secure file upload validation and processing."""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or self._get_default_config()
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Initialize file type detector
        self.magic_detector = magic.Magic(mime=True)
        
        # Quarantine directory for suspicious files
        self.quarantine_dir = Path(self.config['quarantine_dir'])
        self.quarantine_dir.mkdir(parents=True, exist_ok=True)
        
        # Load malware signatures if available
        self.malware_signatures = self._load_malware_signatures()
        
        # Image processing safety
        ImageFile.LOAD_TRUNCATED_IMAGES = True
        Image.MAX_IMAGE_PIXELS = self.config['max_image_pixels']
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default security configuration."""
        return {
            # File size limits (in bytes)
            'max_file_size': 100 * 1024 * 1024,  # 100MB
            'max_image_size': 50 * 1024 * 1024,   # 50MB
            'max_document_size': 200 * 1024 * 1024,  # 200MB
            'max_archive_size': 500 * 1024 * 1024,   # 500MB
            
            # Image security
            'max_image_pixels': 100000000,  # 100MP
            'max_image_dimension': 50000,   # 50k pixels per dimension
            
            # Archive security
            'max_archive_files': 10000,
            'max_archive_depth': 10,
            'max_extracted_size': 1024 * 1024 * 1024,  # 1GB
            
            # Allowed file types
            'allowed_image_types': [
                'image/jpeg', 'image/png', 'image/gif', 'image/webp',
                'image/bmp', 'image/tiff', 'image/svg+xml'
            ],
            'allowed_document_types': [
                'application/pdf', 'text/plain', 'text/csv',
                'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                'application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                'application/vnd.ms-powerpoint', 'application/vnd.openxmlformats-officedocument.presentationml.presentation'
            ],
            'allowed_archive_types': [
                'application/zip', 'application/x-tar', 'application/gzip'
            ],
            'allowed_video_types': [
                'video/mp4', 'video/mpeg', 'video/quicktime', 'video/x-msvideo'
            ],
            'allowed_audio_types': [
                'audio/mpeg', 'audio/wav', 'audio/x-wav', 'audio/ogg'
            ],
            
            # Blocked file types
            'blocked_extensions': [
                '.exe', '.bat', '.cmd', '.com', '.pif', '.scr', '.vbs',
                '.js', '.jse', '.ws', '.wsf', '.wsc', '.wsh', '.ps1',
                '.msi', '.msp', '.mst', '.dll', '.sys', '.reg'
            ],
            
            # Security settings
            'enable_virus_scanning': True,
            'enable_archive_scanning': True,
            'enable_metadata_extraction': True,
            'quarantine_suspicious': True,
            'quarantine_dir': '/tmp/activelog_quarantine',
            
            # Content analysis
            'scan_embedded_files': True,
            'check_file_signatures': True,
            'validate_file_headers': True,
            'analyze_macros': True
        }
    
    def _load_malware_signatures(self) -> Dict[str, List[str]]:
        """Load known malware signatures."""
        # In production, this would load from a malware signature database
        return {
            'eicar_test': ['X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*'],
            'suspicious_patterns': [
                b'eval\\s*\\(',
                b'document\\.write',
                b'<script[^>]*>.*?</script>',
                b'javascript:',
                b'vbscript:'
            ]
        }
    
    def validate_file(self, file_path: str, original_filename: str = None) -> FileValidationReport:
        """
        Perform comprehensive file validation.
        
        Args:
            file_path: Path to the file to validate
            original_filename: Original filename from upload
            
        Returns:
            FileValidationReport with validation results
        """
        start_time = time.time()
        file_path = Path(file_path)
        
        if not file_path.exists():
            return FileValidationReport(
                filename=original_filename or str(file_path),
                original_size=0,
                mime_type="",
                file_extension="",
                detected_type="",
                validation_result=FileValidationResult.ERROR,
                security_score=0,
                issues=["File not found"],
                warnings=[],
                metadata={},
                hash_sha256="",
                scan_duration_ms=0
            )
        
        # Initialize report
        file_size = file_path.stat().st_size
        file_extension = file_path.suffix.lower()
        filename = original_filename or file_path.name
        
        report = FileValidationReport(
            filename=filename,
            original_size=file_size,
            mime_type="",
            file_extension=file_extension,
            detected_type="",
            validation_result=FileValidationResult.SAFE,
            security_score=100,
            issues=[],
            warnings=[],
            metadata={},
            hash_sha256="",
            scan_duration_ms=0
        )
        
        try:
            # Calculate file hash
            report.hash_sha256 = self._calculate_file_hash(file_path)
            
            # Detect MIME type
            report.mime_type = self.magic_detector.from_file(str(file_path))
            report.detected_type = report.mime_type
            
            # Basic security checks
            self._check_file_size(report)
            self._check_file_extension(report)
            self._check_filename_security(report)
            
            # MIME type validation
            self._validate_mime_type(report)
            
            # File signature validation
            self._validate_file_signature(file_path, report)
            
            # Content-based security checks
            self._scan_file_content(file_path, report)
            
            # Type-specific validation
            if report.mime_type.startswith('image/'):
                self._validate_image_file(file_path, report)
            elif report.mime_type.startswith('application/'):
                self._validate_document_file(file_path, report)
            elif report.mime_type in self.config['allowed_archive_types']:
                self._validate_archive_file(file_path, report)
            
            # Virus scanning
            if self.config['enable_virus_scanning']:
                self._scan_for_malware(file_path, report)
            
            # Final security assessment
            self._assess_final_security_score(report)
            
        except Exception as e:
            self.logger.error(f"Error validating file {filename}: {e}")
            report.validation_result = FileValidationResult.ERROR
            report.issues.append(f"Validation error: {str(e)}")
            report.security_score = 0
        
        # Calculate scan duration
        scan_duration = (time.time() - start_time) * 1000
        report.scan_duration_ms = int(scan_duration)
        
        # Handle quarantine
        if report.validation_result in [FileValidationResult.SUSPICIOUS, FileValidationResult.MALICIOUS]:
            if self.config['quarantine_suspicious']:
                self._quarantine_file(file_path, report)
        
        return report
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of file."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def _check_file_size(self, report: FileValidationReport):
        """Check file size limits."""
        max_size = self.config['max_file_size']
        
        # Type-specific size limits
        if report.mime_type.startswith('image/'):
            max_size = self.config['max_image_size']
        elif report.mime_type.startswith('application/'):
            max_size = self.config['max_document_size']
        elif report.mime_type in self.config['allowed_archive_types']:
            max_size = self.config['max_archive_size']
        
        if report.original_size > max_size:
            report.issues.append(f"File size ({report.original_size} bytes) exceeds limit ({max_size} bytes)")
            report.validation_result = FileValidationResult.BLOCKED
            report.security_score -= 50
        elif report.original_size > max_size * 0.8:
            report.warnings.append(f"File size is close to limit ({report.original_size}/{max_size} bytes)")
            report.security_score -= 10
    
    def _check_file_extension(self, report: FileValidationReport):
        """Check file extension against blocklist."""
        if report.file_extension in self.config['blocked_extensions']:
            report.issues.append(f"File extension '{report.file_extension}' is blocked")
            report.validation_result = FileValidationResult.BLOCKED
            report.security_score = 0
    
    def _check_filename_security(self, report: FileValidationReport):
        """Check filename for security issues."""
        filename = report.filename
        
        # Check for path traversal
        if '..' in filename or '/' in filename or '\\\\' in filename:
            report.issues.append("Filename contains path traversal sequences")
            report.security_score -= 30
        
        # Check for suspicious patterns
        suspicious_patterns = [
            r'\\.(bat|cmd|exe|scr|pif)\\.',  # Double extension
            r'[<>:"|?*]',  # Invalid filename characters
            r'^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])$',  # Reserved names
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, filename, re.IGNORECASE):
                report.warnings.append(f"Suspicious filename pattern: {pattern}")
                report.security_score -= 10
        
        # Check filename length
        if len(filename) > 255:
            report.issues.append("Filename too long")
            report.security_score -= 20
    
    def _validate_mime_type(self, report: FileValidationReport):
        """Validate MIME type against allowed types."""
        mime_type = report.mime_type
        
        allowed_types = (
            self.config['allowed_image_types'] +
            self.config['allowed_document_types'] +
            self.config['allowed_archive_types'] +
            self.config['allowed_video_types'] +
            self.config['allowed_audio_types']
        )
        
        if mime_type not in allowed_types:
            report.issues.append(f"MIME type '{mime_type}' is not allowed")
            report.validation_result = FileValidationResult.BLOCKED
            report.security_score = 0
    
    def _validate_file_signature(self, file_path: Path, report: FileValidationReport):
        """Validate file signature matches extension and MIME type."""
        if not self.config['validate_file_headers']:
            return
        
        # Read file header
        with open(file_path, 'rb') as f:
            header = f.read(16)
        
        # Common file signatures
        signatures = {
            b'\\x89PNG\\r\\n\\x1a\\n': 'image/png',
            b'\\xff\\xd8\\xff': 'image/jpeg',
            b'GIF87a': 'image/gif',
            b'GIF89a': 'image/gif',
            b'%PDF': 'application/pdf',
            b'PK\\x03\\x04': 'application/zip',
            b'\\x50\\x4b\\x05\\x06': 'application/zip',
            b'\\x50\\x4b\\x07\\x08': 'application/zip',
        }
        
        # Check if file signature matches claimed type
        signature_match = False
        for sig, expected_mime in signatures.items():
            if header.startswith(sig):
                if expected_mime != report.mime_type:
                    report.warnings.append(f"File signature mismatch: expected {expected_mime}, got {report.mime_type}")
                    report.security_score -= 15
                signature_match = True
                break
        
        if not signature_match and report.mime_type in ['image/jpeg', 'image/png', 'image/gif', 'application/pdf']:
            report.warnings.append("Could not verify file signature")
            report.security_score -= 10
    
    def _scan_file_content(self, file_path: Path, report: FileValidationReport):
        """Scan file content for malicious patterns."""
        try:
            # Read file content (limit to first 1MB for performance)
            with open(file_path, 'rb') as f:
                content = f.read(1024 * 1024)
            
            # Check for malware signatures
            for sig_name, signatures in self.malware_signatures.items():
                for signature in signatures:
                    if isinstance(signature, str):
                        if signature.encode() in content:
                            report.issues.append(f"Malware signature detected: {sig_name}")
                            report.validation_result = FileValidationResult.MALICIOUS
                            report.security_score = 0
                    elif isinstance(signature, bytes):
                        if re.search(signature, content, re.IGNORECASE):
                            report.warnings.append(f"Suspicious pattern detected: {sig_name}")
                            report.security_score -= 25
            
            # Check for embedded scripts
            script_patterns = [
                b'<script[^>]*>',
                b'javascript:',
                b'vbscript:',
                b'eval\\s*\\(',
                b'document\\.write'
            ]
            
            for pattern in script_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    report.warnings.append("Embedded script content detected")
                    report.security_score -= 20
                    break
            
        except Exception as e:
            report.warnings.append(f"Could not scan file content: {e}")
    
    def _validate_image_file(self, file_path: Path, report: FileValidationReport):
        """Validate image file security."""
        try:
            with Image.open(file_path) as img:
                width, height = img.size
                
                # Check image dimensions
                max_dimension = self.config['max_image_dimension']
                if width > max_dimension or height > max_dimension:
                    report.issues.append(f"Image dimensions ({width}x{height}) exceed limit ({max_dimension})")
                    report.security_score -= 30
                
                # Check pixel count
                pixel_count = width * height
                if pixel_count > self.config['max_image_pixels']:
                    report.issues.append(f"Image pixel count ({pixel_count}) exceeds limit")
                    report.security_score -= 25
                
                # Store image metadata
                report.metadata['image'] = {
                    'width': width,
                    'height': height,
                    'format': img.format,
                    'mode': img.mode,
                    'has_transparency': img.mode in ('RGBA', 'LA') or 'transparency' in img.info
                }
                
                # Check for suspicious EXIF data
                if hasattr(img, '_getexif') and img._getexif():
                    exif = img._getexif()
                    if exif:
                        # Check for GPS data (privacy concern)
                        gps_tags = [34853]  # GPS Info tag
                        if any(tag in exif for tag in gps_tags):
                            report.warnings.append("Image contains GPS location data")
                            report.security_score -= 5
                
        except Exception as e:
            report.warnings.append(f"Could not validate image: {e}")
            report.security_score -= 10
    
    def _validate_document_file(self, file_path: Path, report: FileValidationReport):
        """Validate document file security."""
        # PDF-specific validation
        if report.mime_type == 'application/pdf':
            self._validate_pdf_file(file_path, report)
        
        # Office document validation
        elif 'officedocument' in report.mime_type or 'msword' in report.mime_type:
            self._validate_office_file(file_path, report)
    
    def _validate_pdf_file(self, file_path: Path, report: FileValidationReport):
        """Validate PDF file security."""
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
            
            # Check for suspicious PDF features
            suspicious_features = [
                b'/JavaScript',
                b'/JS',
                b'/AcroForm',
                b'/XFA',
                b'/EmbeddedFile',
                b'/Launch',
                b'/GoToR'
            ]
            
            for feature in suspicious_features:
                if feature in content:
                    report.warnings.append(f"PDF contains potentially dangerous feature: {feature.decode()}")
                    report.security_score -= 15
            
            # Check PDF version
            version_match = re.search(b'%PDF-([0-9]\\.[0-9])', content[:100])
            if version_match:
                version = version_match.group(1).decode()
                report.metadata['pdf_version'] = version
                
                # Warn about very old PDF versions
                if version < '1.4':
                    report.warnings.append(f"Old PDF version ({version}) may have security issues")
                    report.security_score -= 5
            
        except Exception as e:
            report.warnings.append(f"Could not validate PDF: {e}")
    
    def _validate_office_file(self, file_path: Path, report: FileValidationReport):
        """Validate Microsoft Office file security."""
        try:
            # Office files are ZIP archives
            if zipfile.is_zipfile(file_path):
                with zipfile.ZipFile(file_path, 'r') as zf:
                    # Check for macro files
                    macro_files = [name for name in zf.namelist() if 'vbaProject' in name or name.endswith('.bin')]
                    if macro_files:
                        report.warnings.append("Document contains macros")
                        report.security_score -= 25
                    
                    # Check for external links
                    for name in zf.namelist():
                        if name.endswith('.rels'):
                            try:
                                content = zf.read(name)
                                if b'http://' in content or b'https://' in content:
                                    report.warnings.append("Document contains external links")
                                    report.security_score -= 10
                            except:
                                pass
            
        except Exception as e:
            report.warnings.append(f"Could not validate Office document: {e}")
    
    def _validate_archive_file(self, file_path: Path, report: FileValidationReport):
        """Validate archive file security."""
        if not self.config['enable_archive_scanning']:
            return
        
        try:
            if zipfile.is_zipfile(file_path):
                self._validate_zip_file(file_path, report)
            elif tarfile.is_tarfile(file_path):
                self._validate_tar_file(file_path, report)
            
        except Exception as e:
            report.warnings.append(f"Could not validate archive: {e}")
    
    def _validate_zip_file(self, file_path: Path, report: FileValidationReport):
        """Validate ZIP file security."""
        with zipfile.ZipFile(file_path, 'r') as zf:
            file_count = len(zf.namelist())
            total_size = 0
            
            # Check file count
            if file_count > self.config['max_archive_files']:
                report.issues.append(f"Archive contains too many files ({file_count})")
                report.security_score -= 30
            
            # Check compression ratio and file names
            for info in zf.infolist():
                total_size += info.file_size
                
                # Check for zip bombs (high compression ratio)
                if info.compress_size > 0:
                    ratio = info.file_size / info.compress_size
                    if ratio > 100:  # More than 100:1 compression
                        report.warnings.append(f"Suspicious compression ratio: {ratio:.1f}:1")
                        report.security_score -= 20
                
                # Check for path traversal in archive
                if '..' in info.filename or info.filename.startswith('/'):
                    report.issues.append("Archive contains path traversal")
                    report.validation_result = FileValidationResult.MALICIOUS
                    report.security_score = 0
                
                # Check for suspicious file types in archive
                file_ext = Path(info.filename).suffix.lower()
                if file_ext in self.config['blocked_extensions']:
                    report.warnings.append(f"Archive contains blocked file type: {file_ext}")
                    report.security_score -= 25
            
            # Check total extracted size
            if total_size > self.config['max_extracted_size']:
                report.issues.append(f"Archive extracted size too large ({total_size} bytes)")
                report.security_score -= 40
            
            report.metadata['archive'] = {
                'file_count': file_count,
                'total_size': total_size,
                'compression_ratio': total_size / file_path.stat().st_size if file_path.stat().st_size > 0 else 0
            }
    
    def _validate_tar_file(self, file_path: Path, report: FileValidationReport):
        """Validate TAR file security."""
        with tarfile.open(file_path, 'r') as tf:
            members = tf.getmembers()
            file_count = len(members)
            total_size = sum(m.size for m in members if m.isfile())
            
            # Check file count
            if file_count > self.config['max_archive_files']:
                report.issues.append(f"Archive contains too many files ({file_count})")
                report.security_score -= 30
            
            # Check for suspicious members
            for member in members:
                # Check for path traversal
                if '..' in member.name or member.name.startswith('/'):
                    report.issues.append("Archive contains path traversal")
                    report.validation_result = FileValidationResult.MALICIOUS
                    report.security_score = 0
                
                # Check for device files or special files
                if member.isdev() or member.isfifo():
                    report.warnings.append("Archive contains device/special files")
                    report.security_score -= 20
            
            # Check total extracted size
            if total_size > self.config['max_extracted_size']:
                report.issues.append(f"Archive extracted size too large ({total_size} bytes)")
                report.security_score -= 40
    
    def _scan_for_malware(self, file_path: Path, report: FileValidationReport):
        """Scan file for malware using available scanners."""
        # Try ClamAV if available
        if shutil.which('clamscan'):
            try:
                result = subprocess.run(
                    ['clamscan', '--no-summary', str(file_path)],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode == 1:  # Virus found
                    report.issues.append("Malware detected by ClamAV")
                    report.validation_result = FileValidationResult.MALICIOUS
                    report.security_score = 0
                elif result.returncode != 0:  # Error
                    report.warnings.append("ClamAV scan failed")
                
            except subprocess.TimeoutExpired:
                report.warnings.append("Virus scan timed out")
            except Exception as e:
                report.warnings.append(f"Virus scan error: {e}")
        else:
            report.warnings.append("No virus scanner available")
    
    def _assess_final_security_score(self, report: FileValidationReport):
        """Assess final security score and validation result."""
        if report.validation_result == FileValidationResult.BLOCKED:
            return
        
        if report.security_score <= 0:
            report.validation_result = FileValidationResult.MALICIOUS
        elif report.security_score <= 50:
            report.validation_result = FileValidationResult.SUSPICIOUS
        elif report.security_score <= 80:
            report.validation_result = FileValidationResult.SUSPICIOUS
        else:
            report.validation_result = FileValidationResult.SAFE
        
        # Ensure score is within bounds
        report.security_score = max(0, min(100, report.security_score))
    
    def _quarantine_file(self, file_path: Path, report: FileValidationReport):
        """Move suspicious file to quarantine."""
        try:
            quarantine_path = self.quarantine_dir / f"{report.hash_sha256}_{file_path.name}"
            shutil.move(str(file_path), str(quarantine_path))
            
            # Save quarantine metadata
            metadata_path = quarantine_path.with_suffix('.json')
            with open(metadata_path, 'w') as f:
                json.dump({
                    'original_filename': report.filename,
                    'quarantine_time': time.time(),
                    'validation_result': report.validation_result.value,
                    'security_score': report.security_score,
                    'issues': report.issues,
                    'warnings': report.warnings
                }, f, indent=2)
            
            self.logger.warning(f"File quarantined: {report.filename} -> {quarantine_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to quarantine file: {e}")
    
    def validate_upload_stream(self, file_stream: BinaryIO, filename: str, 
                              max_size: int = None) -> FileValidationReport:
        """
        Validate file from upload stream.
        
        Args:
            file_stream: File upload stream
            filename: Original filename
            max_size: Maximum file size (overrides config)
            
        Returns:
            FileValidationReport
        """
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            
            # Copy stream to temp file with size limit
            max_size = max_size or self.config['max_file_size']
            bytes_written = 0
            
            while True:
                chunk = file_stream.read(8192)
                if not chunk:
                    break
                
                bytes_written += len(chunk)
                if bytes_written > max_size:
                    temp_path.unlink(missing_ok=True)
                    return FileValidationReport(
                        filename=filename,
                        original_size=bytes_written,
                        mime_type="",
                        file_extension="",
                        detected_type="",
                        validation_result=FileValidationResult.BLOCKED,
                        security_score=0,
                        issues=[f"File too large (>{max_size} bytes)"],
                        warnings=[],
                        metadata={},
                        hash_sha256="",
                        scan_duration_ms=0
                    )
                
                temp_file.write(chunk)
        
        try:
            # Validate the temporary file
            report = self.validate_file(str(temp_path), filename)
            return report
        finally:
            # Cleanup temp file if not quarantined
            if temp_path.exists():
                temp_path.unlink(missing_ok=True)
    
    def generate_security_report(self, reports: List[FileValidationReport]) -> str:
        """Generate security report for multiple file validations."""
        total_files = len(reports)
        safe_files = sum(1 for r in reports if r.validation_result == FileValidationResult.SAFE)
        suspicious_files = sum(1 for r in reports if r.validation_result == FileValidationResult.SUSPICIOUS)
        malicious_files = sum(1 for r in reports if r.validation_result == FileValidationResult.MALICIOUS)
        blocked_files = sum(1 for r in reports if r.validation_result == FileValidationResult.BLOCKED)
        
        avg_score = sum(r.security_score for r in reports) / total_files if total_files > 0 else 0
        
        report_lines = [
            "=" * 80,
            "FILE UPLOAD SECURITY REPORT",
            "=" * 80,
            f"Total Files Processed: {total_files}",
            f"Average Security Score: {avg_score:.1f}/100",
            "",
            "VALIDATION RESULTS:",
            f"  ✅ Safe: {safe_files} files",
            f"  ⚠️ Suspicious: {suspicious_files} files",
            f"  🚨 Malicious: {malicious_files} files",
            f"  🚫 Blocked: {blocked_files} files",
            "",
            "SECURITY ISSUES:",
        ]
        
        # Collect all issues
        all_issues = []
        for report in reports:
            all_issues.extend(report.issues)
        
        from collections import Counter
        issue_counter = Counter(all_issues)
        
        for issue, count in issue_counter.most_common(10):
            report_lines.append(f"  • {issue} ({count} files)")
        
        report_lines.extend([
            "",
            "RECOMMENDATIONS:",
            "- Implement strict file type validation",
            "- Use virus scanning for all uploads",
            "- Validate file signatures and headers",
            "- Limit file sizes appropriately",
            "- Scan archive contents for threats",
            "- Monitor quarantined files regularly",
            "",
            "=" * 80
        ])
        
        return "\\n".join(report_lines)


def main():
    """Demo of file upload security system."""
    print("🛡️ File Upload Security System for ActiveLog")
    print("==============================================")
    
    # Initialize security manager
    security_manager = FileUploadSecurityManager()
    
    # Create test files
    test_dir = Path("/tmp/activelog_file_tests")
    test_dir.mkdir(exist_ok=True)
    
    # Test 1: Safe text file
    safe_file = test_dir / "safe_document.txt"
    with open(safe_file, 'w') as f:
        f.write("This is a safe text document for testing.")
    
    print(f"\\n📄 Testing safe text file...")
    report1 = security_manager.validate_file(str(safe_file))
    print(f"Result: {report1.validation_result.value} (Score: {report1.security_score}/100)")
    
    # Test 2: EICAR test file (malware test)
    eicar_file = test_dir / "eicar_test.txt"
    with open(eicar_file, 'w') as f:
        f.write("X5O!P%@AP[4\\\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*")
    
    print(f"\\n🦠 Testing EICAR malware test file...")
    report2 = security_manager.validate_file(str(eicar_file))
    print(f"Result: {report2.validation_result.value} (Score: {report2.security_score}/100)")
    
    # Test 3: Suspicious filename
    suspicious_file = test_dir / "document.pdf.exe"
    with open(suspicious_file, 'w') as f:
        f.write("This file has a suspicious double extension.")
    
    print(f"\\n🔍 Testing suspicious filename...")
    report3 = security_manager.validate_file(str(suspicious_file))
    print(f"Result: {report3.validation_result.value} (Score: {report3.security_score}/100)")
    
    # Generate summary report
    reports = [report1, report2, report3]
    summary_report = security_manager.generate_security_report(reports)
    
    # Save report
    report_path = Path(__file__).parent.parent / "reports" / "file_upload_security_report.txt"
    report_path.parent.mkdir(exist_ok=True)
    
    with open(report_path, 'w') as f:
        f.write(summary_report)
    
    print(f"\\n📊 Security report saved to: {report_path}")
    print(summary_report)
    
    # Cleanup
    shutil.rmtree(test_dir, ignore_errors=True)
    
    print("\\n✅ File Upload Security System demo completed!")


if __name__ == "__main__":
    main()