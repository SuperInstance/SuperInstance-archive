"""
Backup Processor Lambda Function
Handles automated backup tasks for ActiveLog
"""

import json
import os
import boto3
import logging
import subprocess
from typing import Dict, Any
from datetime import datetime, timedelta
import gzip
import shutil

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
s3_client = boto3.client('s3')
rds_client = boto3.client('rds')
secrets_client = boto3.client('secretsmanager')

def create_backup(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Create comprehensive backup of ActiveLog data
    """
    try:
        backup_type = event.get('backup_type', 'full')
        backup_id = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        logger.info(f"Starting {backup_type} backup with ID: {backup_id}")
        
        results = {
            'backup_id': backup_id,
            'backup_type': backup_type,
            'started_at': datetime.now().isoformat(),
            'components': {}
        }
        
        # Database backup
        if backup_type in ['full', 'database']:
            db_result = await create_database_backup(backup_id)
            results['components']['database'] = db_result
        
        # File storage backup
        if backup_type in ['full', 'files']:
            files_result = await create_files_backup(backup_id)
            results['components']['files'] = files_result
        
        # Configuration backup
        if backup_type in ['full', 'config']:
            config_result = await create_config_backup(backup_id)
            results['components']['config'] = config_result
        
        # Logs backup
        if backup_type in ['full', 'logs']:
            logs_result = await create_logs_backup(backup_id)
            results['components']['logs'] = logs_result
        
        results['completed_at'] = datetime.now().isoformat()
        results['status'] = 'completed'
        
        # Store backup manifest
        await store_backup_manifest(backup_id, results)
        
        # Clean up old backups
        await cleanup_old_backups()
        
        logger.info(f"Backup {backup_id} completed successfully")
        
        return {
            'statusCode': 200,
            'body': json.dumps(results)
        }
        
    except Exception as e:
        logger.error(f"Error creating backup: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'message': 'Failed to create backup'
            })
        }


async def create_database_backup(backup_id: str) -> Dict[str, Any]:
    """
    Create database backup using pg_dump
    """
    try:
        logger.info("Starting database backup")
        
        # Get database credentials from secrets
        db_secret_arn = os.environ.get('SECRET_ARN')
        secret_response = secrets_client.get_secret_value(SecretId=db_secret_arn)
        db_password = secret_response['SecretString']
        
        db_host = os.environ.get('DATABASE_HOST')
        db_name = os.environ.get('DB_NAME', 'activelog')
        db_user = os.environ.get('DB_USER', 'activelog')
        
        # Create pg_dump command
        dump_file = f"/tmp/{backup_id}_database.sql"
        
        # Set environment variable for password
        env = os.environ.copy()
        env['PGPASSWORD'] = db_password
        
        # Run pg_dump
        cmd = [
            'pg_dump',
            '-h', db_host,
            '-U', db_user,
            '-d', db_name,
            '--verbose',
            '--no-password',
            '--format=custom',
            '--compress=9',
            '--file', dump_file
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, env=env)
        
        if result.returncode != 0:
            raise Exception(f"pg_dump failed: {result.stderr}")
        
        # Compress and upload to S3
        compressed_file = f"{dump_file}.gz"
        with open(dump_file, 'rb') as f_in:
            with gzip.open(compressed_file, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        backup_bucket = os.environ.get('BACKUP_BUCKET')
        s3_key = f"database/{backup_id}_database.sql.gz"
        
        with open(compressed_file, 'rb') as f:
            s3_client.upload_fileobj(
                f, backup_bucket, s3_key,
                ExtraArgs={
                    'ServerSideEncryption': 'AES256',
                    'Metadata': {
                        'backup_id': backup_id,
                        'backup_type': 'database',
                        'created_at': datetime.now().isoformat()
                    }
                }
            )
        
        # Clean up local files
        os.remove(dump_file)
        os.remove(compressed_file)
        
        file_size = os.path.getsize(compressed_file) if os.path.exists(compressed_file) else 0
        
        logger.info(f"Database backup completed: {s3_key}")
        
        return {
            'status': 'completed',
            's3_key': s3_key,
            'file_size': file_size,
            'compression': 'gzip',
            'completed_at': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error creating database backup: {e}")
        return {
            'status': 'failed',
            'error': str(e)
        }


async def create_files_backup(backup_id: str) -> Dict[str, Any]:
    """
    Create backup of user files from S3
    """
    try:
        logger.info("Starting files backup")
        
        source_bucket = os.environ.get('S3_BUCKET')
        backup_bucket = os.environ.get('BACKUP_BUCKET')
        
        # List all objects in source bucket
        paginator = s3_client.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=source_bucket)
        
        copied_files = []
        total_size = 0
        
        for page in pages:
            if 'Contents' not in page:
                continue
                
            for obj in page['Contents']:
                source_key = obj['Key']
                backup_key = f"files/{backup_id}/{source_key}"
                
                # Copy object to backup bucket
                copy_source = {'Bucket': source_bucket, 'Key': source_key}
                
                s3_client.copy_object(
                    CopySource=copy_source,
                    Bucket=backup_bucket,
                    Key=backup_key,
                    ServerSideEncryption='AES256',
                    MetadataDirective='COPY'
                )
                
                copied_files.append({
                    'source_key': source_key,
                    'backup_key': backup_key,
                    'size': obj['Size']
                })
                
                total_size += obj['Size']
        
        logger.info(f"Files backup completed: {len(copied_files)} files, {total_size} bytes")
        
        return {
            'status': 'completed',
            'files_count': len(copied_files),
            'total_size': total_size,
            'completed_at': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error creating files backup: {e}")
        return {
            'status': 'failed',
            'error': str(e)
        }


async def create_config_backup(backup_id: str) -> Dict[str, Any]:
    """
    Create backup of configuration data
    """
    try:
        logger.info("Starting configuration backup")
        
        # Backup environment variables and configuration
        config_data = {
            'environment_variables': {
                key: value for key, value in os.environ.items()
                if not key.endswith('_PASSWORD') and not key.endswith('_SECRET')
            },
            'lambda_configuration': {
                'function_name': os.environ.get('AWS_LAMBDA_FUNCTION_NAME'),
                'runtime': 'python3.11',
                'memory_size': os.environ.get('AWS_LAMBDA_FUNCTION_MEMORY_SIZE'),
                'timeout': os.environ.get('AWS_LAMBDA_FUNCTION_TIMEOUT')
            },
            'backup_metadata': {
                'backup_id': backup_id,
                'created_at': datetime.now().isoformat(),
                'version': '1.0'
            }
        }
        
        # Upload configuration to S3
        backup_bucket = os.environ.get('BACKUP_BUCKET')
        s3_key = f"config/{backup_id}_config.json"
        
        s3_client.put_object(
            Bucket=backup_bucket,
            Key=s3_key,
            Body=json.dumps(config_data, indent=2),
            ContentType='application/json',
            ServerSideEncryption='AES256'
        )
        
        logger.info(f"Configuration backup completed: {s3_key}")
        
        return {
            'status': 'completed',
            's3_key': s3_key,
            'config_items': len(config_data),
            'completed_at': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error creating configuration backup: {e}")
        return {
            'status': 'failed',
            'error': str(e)
        }


async def create_logs_backup(backup_id: str) -> Dict[str, Any]:
    """
    Create backup of CloudWatch logs
    """
    try:
        logger.info("Starting logs backup")
        
        # This is a simplified implementation
        # In a real scenario, you would use CloudWatch Logs API to export logs
        
        logs_data = {
            'backup_id': backup_id,
            'log_groups': [
                '/aws/lambda/activelog-file-processor',
                '/aws/lambda/activelog-ai-processor',
                '/aws/lambda/activelog-notification-processor',
                '/ecs/activelog'
            ],
            'export_note': 'Log export would be implemented using CloudWatch Logs API',
            'created_at': datetime.now().isoformat()
        }
        
        # Upload logs metadata to S3
        backup_bucket = os.environ.get('BACKUP_BUCKET')
        s3_key = f"logs/{backup_id}_logs_metadata.json"
        
        s3_client.put_object(
            Bucket=backup_bucket,
            Key=s3_key,
            Body=json.dumps(logs_data, indent=2),
            ContentType='application/json',
            ServerSideEncryption='AES256'
        )
        
        logger.info(f"Logs backup metadata completed: {s3_key}")
        
        return {
            'status': 'completed',
            's3_key': s3_key,
            'log_groups_count': len(logs_data['log_groups']),
            'completed_at': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error creating logs backup: {e}")
        return {
            'status': 'failed',
            'error': str(e)
        }


async def store_backup_manifest(backup_id: str, backup_results: Dict[str, Any]):
    """
    Store backup manifest for tracking and recovery
    """
    try:
        backup_bucket = os.environ.get('BACKUP_BUCKET')
        manifest_key = f"manifests/{backup_id}_manifest.json"
        
        s3_client.put_object(
            Bucket=backup_bucket,
            Key=manifest_key,
            Body=json.dumps(backup_results, indent=2),
            ContentType='application/json',
            ServerSideEncryption='AES256'
        )
        
        logger.info(f"Backup manifest stored: {manifest_key}")
        
    except Exception as e:
        logger.error(f"Error storing backup manifest: {e}")


async def cleanup_old_backups():
    """
    Clean up old backups based on retention policy
    """
    try:
        backup_bucket = os.environ.get('BACKUP_BUCKET')
        retention_days = int(os.environ.get('BACKUP_RETENTION_DAYS', '30'))
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        
        # List all backup manifests
        response = s3_client.list_objects_v2(
            Bucket=backup_bucket,
            Prefix='manifests/'
        )
        
        deleted_backups = []
        
        if 'Contents' in response:
            for obj in response['Contents']:
                if obj['LastModified'].replace(tzinfo=None) < cutoff_date:
                    # Extract backup_id from manifest filename
                    manifest_key = obj['Key']
                    backup_id = manifest_key.split('/')[-1].replace('_manifest.json', '')
                    
                    # Delete all backup files for this backup_id
                    await delete_backup_files(backup_id)
                    deleted_backups.append(backup_id)
        
        if deleted_backups:
            logger.info(f"Cleaned up {len(deleted_backups)} old backups: {deleted_backups}")
        else:
            logger.info("No old backups to clean up")
            
    except Exception as e:
        logger.error(f"Error cleaning up old backups: {e}")


async def delete_backup_files(backup_id: str):
    """
    Delete all files associated with a backup
    """
    try:
        backup_bucket = os.environ.get('BACKUP_BUCKET')
        
        # List all objects with backup_id prefix
        paginator = s3_client.get_paginator('list_objects_v2')
        pages = paginator.paginate(
            Bucket=backup_bucket,
            Prefix=f"database/{backup_id}"
        )
        
        objects_to_delete = []
        
        for page in pages:
            if 'Contents' in page:
                for obj in page['Contents']:
                    objects_to_delete.append({'Key': obj['Key']})
        
        # Add other backup components
        additional_prefixes = [
            f"files/{backup_id}",
            f"config/{backup_id}",
            f"logs/{backup_id}",
            f"manifests/{backup_id}"
        ]
        
        for prefix in additional_prefixes:
            response = s3_client.list_objects_v2(Bucket=backup_bucket, Prefix=prefix)
            if 'Contents' in response:
                for obj in response['Contents']:
                    objects_to_delete.append({'Key': obj['Key']})
        
        # Delete objects in batches
        if objects_to_delete:
            # S3 delete_objects can handle up to 1000 objects at once
            for i in range(0, len(objects_to_delete), 1000):
                batch = objects_to_delete[i:i+1000]
                s3_client.delete_objects(
                    Bucket=backup_bucket,
                    Delete={'Objects': batch}
                )
        
        logger.info(f"Deleted {len(objects_to_delete)} backup files for {backup_id}")
        
    except Exception as e:
        logger.error(f"Error deleting backup files for {backup_id}: {e}")


def restore_from_backup(backup_id: str, restore_type: str = 'full') -> Dict[str, Any]:
    """
    Restore data from a specific backup
    Note: This is a placeholder for restore functionality
    """
    try:
        logger.info(f"Restore request for backup {backup_id}, type: {restore_type}")
        
        # In a real implementation, this would:
        # 1. Validate the backup exists and is complete
        # 2. Download backup files from S3
        # 3. Restore database using pg_restore
        # 4. Restore files to S3
        # 5. Validate restore integrity
        
        return {
            'status': 'restore_initiated',
            'backup_id': backup_id,
            'restore_type': restore_type,
            'message': 'Restore functionality would be implemented here'
        }
        
    except Exception as e:
        logger.error(f"Error restoring from backup {backup_id}: {e}")
        return {
            'status': 'failed',
            'error': str(e)
        }