"""
Virus Scanner Lambda Function
Handles virus scanning for uploaded files in ActiveLog
"""

import json
import os
import boto3
import logging
import hashlib
import subprocess
from typing import Dict, Any
from urllib.parse import unquote_plus

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
s3_client = boto3.client('s3')
sns_client = boto3.client('sns')

def scan_file(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Scan uploaded files for viruses and malware
    """
    try:
        # Parse S3 event
        records = event.get('Records', [])
        scan_results = []
        
        for record in records:
            # Extract S3 information
            s3_info = record.get('s3', {})
            bucket_name = s3_info.get('bucket', {}).get('name')
            object_key = unquote_plus(s3_info.get('object', {}).get('key', ''))
            
            if not bucket_name or not object_key:
                logger.warning(f"Invalid S3 event: {record}")
                continue
            
            logger.info(f"Scanning file: {object_key} from bucket: {bucket_name}")
            
            # Perform virus scan
            scan_result = await perform_virus_scan(bucket_name, object_key)
            scan_results.append(scan_result)
            
            # Handle scan results
            await handle_scan_result(bucket_name, object_key, scan_result)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': f'Scanned {len(records)} file(s)',
                'scan_results': scan_results
            })
        }
        
    except Exception as e:
        logger.error(f"Error in virus scanner: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'message': 'Failed to scan files'
            })
        }


async def perform_virus_scan(bucket_name: str, object_key: str) -> Dict[str, Any]:
    """
    Perform virus scan on the file
    """
    try:
        # Download file for scanning
        local_file_path = f"/tmp/{os.path.basename(object_key)}"
        
        # Get file metadata first
        head_response = s3_client.head_object(Bucket=bucket_name, Key=object_key)
        file_size = head_response.get('ContentLength', 0)
        content_type = head_response.get('ContentType', 'application/octet-stream')
        
        # Skip scanning for very large files (>100MB) or certain file types
        max_scan_size = 100 * 1024 * 1024  # 100MB
        if file_size > max_scan_size:
            return {
                'object_key': object_key,
                'status': 'skipped',
                'reason': f'File too large for scanning: {file_size} bytes',
                'file_size': file_size,
                'scanned_at': datetime.now().isoformat()
            }
        
        # Skip certain file types that are generally safe
        safe_content_types = [
            'text/plain',
            'application/json',
            'image/jpeg',
            'image/png',
            'image/gif'
        ]
        
        if content_type in safe_content_types and file_size < 1024 * 1024:  # <1MB
            return await quick_hash_check(bucket_name, object_key, file_size)
        
        # Download file
        s3_client.download_file(bucket_name, object_key, local_file_path)
        
        # Perform multiple scan types
        scan_results = {
            'object_key': object_key,
            'file_size': file_size,
            'content_type': content_type,
            'scanned_at': datetime.now().isoformat(),
            'scans': {}
        }
        
        # Hash-based scan (check against known malware hashes)
        hash_result = await hash_based_scan(local_file_path)
        scan_results['scans']['hash_check'] = hash_result
        
        # Signature-based scan (simplified ClamAV-like scanning)
        signature_result = await signature_based_scan(local_file_path)
        scan_results['scans']['signature_check'] = signature_result
        
        # Heuristic analysis
        heuristic_result = await heuristic_analysis(local_file_path, content_type)
        scan_results['scans']['heuristic_analysis'] = heuristic_result
        
        # File structure analysis
        structure_result = await file_structure_analysis(local_file_path, content_type)
        scan_results['scans']['structure_analysis'] = structure_result
        
        # Determine overall result
        is_infected = any(
            scan.get('threat_detected', False) 
            for scan in scan_results['scans'].values()
        )
        
        scan_results['status'] = 'infected' if is_infected else 'clean'
        
        if is_infected:
            threats = []
            for scan_name, scan_data in scan_results['scans'].items():
                if scan_data.get('threat_detected'):
                    threats.extend(scan_data.get('threats', []))
            scan_results['threats'] = list(set(threats))
        
        # Clean up local file
        if os.path.exists(local_file_path):
            os.remove(local_file_path)
        
        logger.info(f"Scan completed for {object_key}: {scan_results['status']}")
        
        return scan_results
        
    except Exception as e:
        logger.error(f"Error scanning file {object_key}: {e}")
        return {
            'object_key': object_key,
            'status': 'error',
            'error': str(e),
            'scanned_at': datetime.now().isoformat()
        }


async def quick_hash_check(bucket_name: str, object_key: str, file_size: int) -> Dict[str, Any]:
    """
    Quick hash-based check for small, safe files
    """
    try:
        # Download file
        response = s3_client.get_object(Bucket=bucket_name, Key=object_key)
        file_content = response['Body'].read()
        
        # Calculate file hash
        file_hash = hashlib.sha256(file_content).hexdigest()
        
        # Check against known malware hashes (simplified)
        known_malware_hashes = await get_known_malware_hashes()
        
        is_malware = file_hash in known_malware_hashes
        
        return {
            'object_key': object_key,
            'status': 'infected' if is_malware else 'clean',
            'file_size': file_size,
            'file_hash': file_hash,
            'scan_type': 'quick_hash',
            'threats': ['Known malware hash'] if is_malware else [],
            'scanned_at': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in quick hash check for {object_key}: {e}")
        return {
            'object_key': object_key,
            'status': 'error',
            'error': str(e)
        }


async def hash_based_scan(file_path: str) -> Dict[str, Any]:
    """
    Hash-based malware detection
    """
    try:
        # Calculate file hashes
        with open(file_path, 'rb') as f:
            file_content = f.read()
        
        md5_hash = hashlib.md5(file_content).hexdigest()
        sha1_hash = hashlib.sha1(file_content).hexdigest()
        sha256_hash = hashlib.sha256(file_content).hexdigest()
        
        # Check against known malware hashes
        known_hashes = await get_known_malware_hashes()
        
        threat_detected = any(hash_val in known_hashes for hash_val in [md5_hash, sha1_hash, sha256_hash])
        
        return {
            'threat_detected': threat_detected,
            'threats': ['Known malware hash'] if threat_detected else [],
            'hashes': {
                'md5': md5_hash,
                'sha1': sha1_hash,
                'sha256': sha256_hash
            },
            'scan_time': 0.1  # Placeholder
        }
        
    except Exception as e:
        logger.error(f"Error in hash-based scan: {e}")
        return {
            'threat_detected': False,
            'error': str(e)
        }


async def signature_based_scan(file_path: str) -> Dict[str, Any]:
    """
    Signature-based malware detection (simplified)
    """
    try:
        # Read file content
        with open(file_path, 'rb') as f:
            file_content = f.read()
        
        # Define some simple malware signatures (hex patterns)
        malware_signatures = {
            'EICAR': b'X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*',
            'suspicious_pattern_1': b'\\x4d\\x5a\\x90\\x00',  # PE header
            'suspicious_pattern_2': b'\\x50\\x4b\\x03\\x04',  # ZIP header with suspicious content
        }
        
        detected_threats = []
        
        for threat_name, signature in malware_signatures.items():
            if signature in file_content:
                detected_threats.append(threat_name)
        
        # Check for suspicious strings
        suspicious_strings = [
            b'cmd.exe',
            b'powershell.exe',
            b'eval(',
            b'system(',
            b'exec(',
            b'<script>',
            b'javascript:',
            b'data:text/html'
        ]
        
        for suspicious_string in suspicious_strings:
            if suspicious_string in file_content:
                detected_threats.append(f'Suspicious string: {suspicious_string.decode("utf-8", errors="ignore")}')
        
        return {
            'threat_detected': len(detected_threats) > 0,
            'threats': detected_threats,
            'signatures_checked': len(malware_signatures),
            'scan_time': 0.2  # Placeholder
        }
        
    except Exception as e:
        logger.error(f"Error in signature-based scan: {e}")
        return {
            'threat_detected': False,
            'error': str(e)
        }


async def heuristic_analysis(file_path: str, content_type: str) -> Dict[str, Any]:
    """
    Heuristic analysis for suspicious behavior patterns
    """
    try:
        suspicious_indicators = []
        risk_score = 0
        
        # Get file stats
        file_stat = os.stat(file_path)
        file_size = file_stat.st_size
        
        # Check for suspicious file characteristics
        if file_size == 0:
            suspicious_indicators.append('Zero-byte file')
            risk_score += 20
        
        if file_size > 100 * 1024 * 1024:  # >100MB
            suspicious_indicators.append('Unusually large file')
            risk_score += 10
        
        # Content type vs actual file analysis
        with open(file_path, 'rb') as f:
            file_header = f.read(512)  # Read first 512 bytes
        
        # Check for content type spoofing
        if content_type.startswith('image/') and not is_valid_image_header(file_header):
            suspicious_indicators.append('Content type mismatch - claimed image but invalid header')
            risk_score += 30
        
        if content_type.startswith('text/') and has_binary_content(file_header):
            suspicious_indicators.append('Content type mismatch - claimed text but contains binary')
            risk_score += 25
        
        # Check for executable content in non-executable files
        if not content_type.startswith('application/') and has_executable_patterns(file_header):
            suspicious_indicators.append('Executable patterns in non-executable file')
            risk_score += 40
        
        # Entropy analysis (high entropy may indicate encryption/packing)
        entropy = calculate_entropy(file_header)
        if entropy > 7.5:  # High entropy threshold
            suspicious_indicators.append(f'High entropy content (entropy: {entropy:.2f})')
            risk_score += 15
        
        threat_detected = risk_score >= 50  # Threshold for threat detection
        
        return {
            'threat_detected': threat_detected,
            'threats': suspicious_indicators if threat_detected else [],
            'risk_score': risk_score,
            'entropy': entropy,
            'scan_time': 0.3  # Placeholder
        }
        
    except Exception as e:
        logger.error(f"Error in heuristic analysis: {e}")
        return {
            'threat_detected': False,
            'error': str(e)
        }


async def file_structure_analysis(file_path: str, content_type: str) -> Dict[str, Any]:
    """
    Analyze file structure for anomalies
    """
    try:
        issues = []
        
        with open(file_path, 'rb') as f:
            file_content = f.read(1024)  # Read first 1KB
        
        # Check for null bytes in text files
        if content_type.startswith('text/') and b'\\x00' in file_content:
            issues.append('Null bytes in text file')
        
        # Check for suspicious file headers
        suspicious_headers = {
            b'MZ': 'PE executable header',
            b'\\x7fELF': 'ELF executable header',
            b'\\xca\\xfe\\xba\\xbe': 'Java class file header',
            b'\\xfe\\xed\\xfa': 'Mach-O executable header'
        }
        
        for header, description in suspicious_headers.items():
            if file_content.startswith(header) and not content_type.startswith('application/'):
                issues.append(f'Suspicious header: {description}')
        
        # Check for polyglot files (files that are valid in multiple formats)
        if (file_content.startswith(b'\\x89PNG') and b'<script>' in file_content):
            issues.append('Possible PNG polyglot with script content')
        
        if (file_content.startswith(b'GIF') and (b'<script>' in file_content or b'javascript:' in file_content)):
            issues.append('Possible GIF polyglot with script content')
        
        threat_detected = len(issues) > 0
        
        return {
            'threat_detected': threat_detected,
            'threats': issues,
            'scan_time': 0.1  # Placeholder
        }
        
    except Exception as e:
        logger.error(f"Error in file structure analysis: {e}")
        return {
            'threat_detected': False,
            'error': str(e)
        }


async def handle_scan_result(bucket_name: str, object_key: str, scan_result: Dict[str, Any]):
    """
    Handle the results of virus scanning
    """
    try:
        status = scan_result.get('status')
        
        if status == 'infected':
            # Quarantine infected file
            await quarantine_file(bucket_name, object_key, scan_result)
            
            # Send alert notification
            await send_security_alert(bucket_name, object_key, scan_result)
            
            # Update file status in database
            await update_file_security_status(object_key, 'quarantined', scan_result)
            
        elif status == 'clean':
            # Mark file as clean
            await update_file_security_status(object_key, 'clean', scan_result)
            
        elif status == 'error':
            # Log error and mark for manual review
            logger.error(f"Scan error for {object_key}: {scan_result.get('error')}")
            await update_file_security_status(object_key, 'scan_error', scan_result)
        
        # Store scan results
        await store_scan_results(object_key, scan_result)
        
    except Exception as e:
        logger.error(f"Error handling scan result for {object_key}: {e}")


async def quarantine_file(bucket_name: str, object_key: str, scan_result: Dict[str, Any]):
    """
    Quarantine infected file
    """
    try:
        # Move file to quarantine location
        quarantine_key = f"quarantine/{object_key}"
        
        # Copy to quarantine location
        copy_source = {'Bucket': bucket_name, 'Key': object_key}
        s3_client.copy_object(
            CopySource=copy_source,
            Bucket=bucket_name,
            Key=quarantine_key,
            MetadataDirective='REPLACE',
            Metadata={
                'quarantine_reason': 'virus_detected',
                'threats': ','.join(scan_result.get('threats', [])),
                'quarantined_at': datetime.now().isoformat(),
                'original_key': object_key
            }
        )
        
        # Delete original file
        s3_client.delete_object(Bucket=bucket_name, Key=object_key)
        
        logger.info(f"File quarantined: {object_key} -> {quarantine_key}")
        
    except Exception as e:
        logger.error(f"Error quarantining file {object_key}: {e}")


async def send_security_alert(bucket_name: str, object_key: str, scan_result: Dict[str, Any]):
    """
    Send security alert for infected file
    """
    try:
        alert_topic_arn = os.environ.get('SECURITY_ALERT_TOPIC_ARN')
        if not alert_topic_arn:
            logger.warning("Security alert topic ARN not configured")
            return
        
        message = {
            'alert_type': 'virus_detected',
            'severity': 'high',
            'timestamp': datetime.now().isoformat(),
            'details': {
                'bucket': bucket_name,
                'object_key': object_key,
                'threats': scan_result.get('threats', []),
                'file_size': scan_result.get('file_size'),
                'content_type': scan_result.get('content_type')
            }
        }
        
        sns_client.publish(
            TopicArn=alert_topic_arn,
            Message=json.dumps(message),
            Subject=f'Security Alert: Virus Detected in {object_key}'
        )
        
        logger.info(f"Security alert sent for {object_key}")
        
    except Exception as e:
        logger.error(f"Error sending security alert: {e}")


# Utility functions
def is_valid_image_header(file_header: bytes) -> bool:
    """Check if file has valid image header"""
    image_headers = [
        b'\\x89PNG\\r\\n\\x1a\\n',  # PNG
        b'\\xff\\xd8\\xff',         # JPEG
        b'GIF87a',                  # GIF87a
        b'GIF89a',                  # GIF89a
        b'BM',                      # BMP
        b'RIFF'                     # WebP (starts with RIFF)
    ]
    return any(file_header.startswith(header) for header in image_headers)


def has_binary_content(file_header: bytes) -> bool:
    """Check if content appears to be binary"""
    # Count null bytes and non-printable characters
    null_count = file_header.count(b'\\x00')
    non_printable = sum(1 for byte in file_header if byte < 32 and byte not in [9, 10, 13])
    
    return null_count > 0 or non_printable > len(file_header) * 0.1


def has_executable_patterns(file_header: bytes) -> bool:
    """Check for executable file patterns"""
    executable_patterns = [
        b'MZ',                      # PE executable
        b'\\x7fELF',                # ELF executable
        b'\\xca\\xfe\\xba\\xbe',    # Java class
        b'\\xfe\\xed\\xfa'          # Mach-O
    ]
    return any(file_header.startswith(pattern) for pattern in executable_patterns)


def calculate_entropy(data: bytes) -> float:
    """Calculate Shannon entropy of data"""
    if not data:
        return 0
    
    # Count frequency of each byte
    frequency = {}
    for byte in data:
        frequency[byte] = frequency.get(byte, 0) + 1
    
    # Calculate entropy
    entropy = 0
    length = len(data)
    for count in frequency.values():
        p = count / length
        if p > 0:
            entropy -= p * (p.bit_length() - 1)
    
    return entropy


async def get_known_malware_hashes() -> set:
    """Get set of known malware hashes"""
    # In a real implementation, this would fetch from a threat intelligence feed
    # For now, return a small set of test hashes
    return {
        '44d88612fea8a8f36de82e1278abb02f',  # Example MD5
        'X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*'  # EICAR test
    }


async def update_file_security_status(object_key: str, status: str, scan_result: Dict[str, Any]):
    """Update file security status in database"""
    try:
        # This would update the database with scan results
        logger.info(f"File {object_key} security status: {status}")
        # Database update would be implemented here
    except Exception as e:
        logger.error(f"Error updating file security status: {e}")


async def store_scan_results(object_key: str, scan_result: Dict[str, Any]):
    """Store detailed scan results"""
    try:
        # This would store scan results in database or S3 for auditing
        logger.info(f"Storing scan results for {object_key}")
        # Storage implementation would be here
    except Exception as e:
        logger.error(f"Error storing scan results: {e}")


# Import datetime for timestamps
try:
    from datetime import datetime
except ImportError:
    logger.warning("datetime import not available")
    
    class datetime:
        @staticmethod
        def now():
            return type('obj', (object,), {'isoformat': lambda: '2023-01-01T00:00:00'})()