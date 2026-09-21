"""
File Processor Lambda Function
Handles file processing tasks for ActiveLog
"""

import json
import os
import boto3
import asyncio
import logging
from typing import Dict, Any
from urllib.parse import unquote_plus

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
s3_client = boto3.client('s3')
sqs_client = boto3.client('sqs')

def process_file(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Process file upload events from S3
    """
    try:
        # Parse S3 event
        records = event.get('Records', [])
        
        for record in records:
            # Extract S3 information
            s3_info = record.get('s3', {})
            bucket_name = s3_info.get('bucket', {}).get('name')
            object_key = unquote_plus(s3_info.get('object', {}).get('key', ''))
            
            if not bucket_name or not object_key:
                logger.warning(f"Invalid S3 event: {record}")
                continue
            
            logger.info(f"Processing file: {object_key} from bucket: {bucket_name}")
            
            # Get file metadata
            try:
                response = s3_client.head_object(Bucket=bucket_name, Key=object_key)
                file_size = response.get('ContentLength', 0)
                content_type = response.get('ContentType', 'application/octet-stream')
                last_modified = response.get('LastModified')
                
                logger.info(f"File metadata - Size: {file_size}, Type: {content_type}")
                
            except Exception as e:
                logger.error(f"Error getting file metadata: {e}")
                continue
            
            # Determine file type and processing strategy
            processing_tasks = determine_processing_tasks(object_key, content_type, file_size)
            
            # Queue processing tasks
            for task in processing_tasks:
                queue_processing_task(task, object_key, bucket_name)
            
            # Update file status in database
            update_file_status(object_key, 'processing', {
                'size': file_size,
                'content_type': content_type,
                'last_modified': last_modified.isoformat() if last_modified else None
            })
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': f'Successfully processed {len(records)} file(s)',
                'processed_files': [
                    record.get('s3', {}).get('object', {}).get('key', '')
                    for record in records
                ]
            })
        }
        
    except Exception as e:
        logger.error(f"Error processing files: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'message': 'Failed to process files'
            })
        }


def determine_processing_tasks(object_key: str, content_type: str, file_size: int) -> list:
    """
    Determine what processing tasks are needed for a file
    """
    tasks = []
    
    # Always run virus scan
    tasks.append('virus_scan')
    
    # Text extraction for various file types
    if content_type.startswith('text/'):
        tasks.append('text_extraction')
    elif content_type in [
        'application/pdf',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/vnd.ms-excel',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'application/vnd.ms-powerpoint',
        'application/vnd.openxmlformats-officedocument.presentationml.presentation'
    ]:
        tasks.append('document_processing')
    
    # Image processing
    if content_type.startswith('image/'):
        tasks.append('image_processing')
        if file_size < 10 * 1024 * 1024:  # Less than 10MB
            tasks.append('ocr_processing')
    
    # Audio/Video processing
    if content_type.startswith('audio/') or content_type.startswith('video/'):
        tasks.append('media_processing')
    
    # Archive processing
    if content_type in [
        'application/zip',
        'application/x-rar-compressed',
        'application/x-7z-compressed',
        'application/x-tar',
        'application/gzip'
    ]:
        tasks.append('archive_processing')
    
    # AI analysis for supported files
    if any(task in tasks for task in ['text_extraction', 'document_processing', 'ocr_processing']):
        tasks.append('ai_analysis')
    
    return tasks


def queue_processing_task(task_type: str, object_key: str, bucket_name: str):
    """
    Queue a processing task for async execution
    """
    try:
        queue_url = os.environ.get('PROCESSING_QUEUE_URL')
        if not queue_url:
            logger.warning("PROCESSING_QUEUE_URL not configured")
            return
        
        message = {
            'task_type': task_type,
            'object_key': object_key,
            'bucket_name': bucket_name,
            'timestamp': datetime.now().isoformat()
        }
        
        sqs_client.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(message),
            MessageGroupId=task_type,  # For FIFO queues
            MessageDeduplicationId=f"{task_type}-{object_key}-{int(time.time())}"
        )
        
        logger.info(f"Queued {task_type} task for {object_key}")
        
    except Exception as e:
        logger.error(f"Error queuing task {task_type}: {e}")


def update_file_status(object_key: str, status: str, metadata: Dict[str, Any] = None):
    """
    Update file processing status in database
    """
    try:
        # This would typically connect to the database
        # For now, we'll log the status update
        logger.info(f"File {object_key} status updated to: {status}")
        if metadata:
            logger.info(f"File metadata: {metadata}")
        
        # In a real implementation, you would:
        # 1. Connect to PostgreSQL using the database credentials
        # 2. Update the files table with the new status and metadata
        # 3. Handle any database errors appropriately
        
    except Exception as e:
        logger.error(f"Error updating file status: {e}")


def extract_text_content(bucket_name: str, object_key: str, content_type: str) -> str:
    """
    Extract text content from files based on content type
    """
    try:
        # Download file from S3
        response = s3_client.get_object(Bucket=bucket_name, Key=object_key)
        file_content = response['Body'].read()
        
        # Extract text based on content type
        if content_type.startswith('text/'):
            return file_content.decode('utf-8', errors='ignore')
        
        elif content_type == 'application/pdf':
            # PDF text extraction would require additional libraries
            # like PyPDF2 or pdfplumber
            return extract_pdf_text(file_content)
        
        elif content_type in [
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        ]:
            # Word document processing would require python-docx
            return extract_word_text(file_content)
        
        else:
            logger.warning(f"Unsupported content type for text extraction: {content_type}")
            return ""
    
    except Exception as e:
        logger.error(f"Error extracting text from {object_key}: {e}")
        return ""


def extract_pdf_text(pdf_content: bytes) -> str:
    """
    Extract text from PDF content
    Note: This is a placeholder - would need PyPDF2 or similar library
    """
    # Placeholder implementation
    logger.info("PDF text extraction requested - would use PyPDF2 library")
    return "PDF content extraction placeholder"


def extract_word_text(word_content: bytes) -> str:
    """
    Extract text from Word document content
    Note: This is a placeholder - would need python-docx library
    """
    # Placeholder implementation
    logger.info("Word document text extraction requested - would use python-docx library")
    return "Word document content extraction placeholder"


def generate_thumbnail(bucket_name: str, object_key: str) -> str:
    """
    Generate thumbnail for image files
    """
    try:
        # Download image
        response = s3_client.get_object(Bucket=bucket_name, Key=object_key)
        image_content = response['Body'].read()
        
        # Generate thumbnail (would use PIL/Pillow)
        thumbnail_key = f"thumbnails/{object_key}.thumb.jpg"
        
        # Upload thumbnail back to S3
        s3_client.put_object(
            Bucket=bucket_name,
            Key=thumbnail_key,
            Body=image_content,  # Placeholder - would be actual thumbnail
            ContentType='image/jpeg'
        )
        
        logger.info(f"Generated thumbnail: {thumbnail_key}")
        return thumbnail_key
        
    except Exception as e:
        logger.error(f"Error generating thumbnail for {object_key}: {e}")
        return ""


# Additional imports that would be needed for full implementation
try:
    from datetime import datetime
    import time
except ImportError:
    logger.warning("Some imports not available - using placeholders")
    
    class datetime:
        @staticmethod
        def now():
            return type('obj', (object,), {'isoformat': lambda: '2023-01-01T00:00:00'})()
    
    import time