#!/usr/bin/env python3
"""
Bulk Data Transformation Scripts for ActiveLog Migration
Handles large-scale data transformations, format conversions, and schema updates
"""

import asyncio
import json
import csv
import logging
import os
import re
import shutil
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable, Union, Generator
from xml.etree import ElementTree as ET
import aiofiles
import aiohttp
from PIL import Image, ExifTags
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class TransformationConfig:
    """Configuration for bulk transformations"""
    source_format: str
    target_format: str
    batch_size: int = 1000
    max_workers: int = 4
    validate_output: bool = True
    preserve_metadata: bool = True
    compression_level: int = 6
    error_threshold: float = 0.05  # 5% error rate threshold

@dataclass
class TransformationResult:
    """Result of bulk transformation operation"""
    total_records: int
    successful: int
    failed: int
    errors: List[str]
    output_files: List[str]
    processing_time: float
    transformation_id: str

class DataTransformer:
    """Base class for data transformations"""
    
    def __init__(self, config: TransformationConfig):
        self.config = config
        self.errors = []
        self.start_time = None
        self.transformation_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    async def transform(self, source_path: str, target_path: str) -> TransformationResult:
        """Execute transformation with error handling and progress tracking"""
        self.start_time = datetime.now()
        self.errors = []
        
        try:
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            
            if self.config.source_format == "json" and self.config.target_format == "csv":
                result = await self._json_to_csv(source_path, target_path)
            elif self.config.source_format == "csv" and self.config.target_format == "json":
                result = await self._csv_to_json(source_path, target_path)
            elif self.config.source_format == "xml" and self.config.target_format == "json":
                result = await self._xml_to_json(source_path, target_path)
            elif self.config.source_format == "json" and self.config.target_format == "parquet":
                result = await self._json_to_parquet(source_path, target_path)
            else:
                raise ValueError(f"Unsupported transformation: {self.config.source_format} -> {self.config.target_format}")
            
            processing_time = (datetime.now() - self.start_time).total_seconds()
            
            return TransformationResult(
                total_records=result['total'],
                successful=result['successful'],
                failed=result['failed'],
                errors=self.errors,
                output_files=[target_path],
                processing_time=processing_time,
                transformation_id=self.transformation_id
            )
            
        except Exception as e:
            logger.error(f"Transformation failed: {str(e)}")
            self.errors.append(str(e))
            return TransformationResult(0, 0, 1, self.errors, [], 0, self.transformation_id)
    
    async def _json_to_csv(self, source_path: str, target_path: str) -> Dict[str, int]:
        """Convert JSON file to CSV format"""
        total, successful, failed = 0, 0, 0
        
        async with aiofiles.open(source_path, 'r') as source_file:
            data = json.loads(await source_file.read())
            
            if not isinstance(data, list):
                data = [data]
            
            if not data:
                return {'total': 0, 'successful': 0, 'failed': 0}
            
            # Extract headers from first record
            headers = self._extract_nested_keys(data[0])
            
            async with aiofiles.open(target_path, 'w', newline='') as target_file:
                # Write CSV header
                await target_file.write(','.join(headers) + '\n')
                
                for record in data:
                    total += 1
                    try:
                        flattened = self._flatten_dict(record)
                        row = [str(flattened.get(header, '')) for header in headers]
                        escaped_row = [self._escape_csv_value(value) for value in row]
                        await target_file.write(','.join(escaped_row) + '\n')
                        successful += 1
                    except Exception as e:
                        failed += 1
                        self.errors.append(f"Record {total}: {str(e)}")
        
        return {'total': total, 'successful': successful, 'failed': failed}
    
    async def _csv_to_json(self, source_path: str, target_path: str) -> Dict[str, int]:
        """Convert CSV file to JSON format"""
        total, successful, failed = 0, 0, 0
        records = []
        
        async with aiofiles.open(source_path, 'r') as source_file:
            content = await source_file.read()
            csv_reader = csv.DictReader(content.splitlines())
            
            for row in csv_reader:
                total += 1
                try:
                    # Convert empty strings to None
                    cleaned_row = {k: (v if v != '' else None) for k, v in row.items()}
                    records.append(cleaned_row)
                    successful += 1
                except Exception as e:
                    failed += 1
                    self.errors.append(f"Row {total}: {str(e)}")
        
        async with aiofiles.open(target_path, 'w') as target_file:
            await target_file.write(json.dumps(records, indent=2, default=str))
        
        return {'total': total, 'successful': successful, 'failed': failed}
    
    async def _xml_to_json(self, source_path: str, target_path: str) -> Dict[str, int]:
        """Convert XML file to JSON format"""
        try:
            tree = ET.parse(source_path)
            root = tree.getroot()
            
            data = self._xml_to_dict(root)
            
            async with aiofiles.open(target_path, 'w') as target_file:
                await target_file.write(json.dumps(data, indent=2, default=str))
            
            return {'total': 1, 'successful': 1, 'failed': 0}
        except Exception as e:
            self.errors.append(f"XML parsing error: {str(e)}")
            return {'total': 1, 'successful': 0, 'failed': 1}
    
    async def _json_to_parquet(self, source_path: str, target_path: str) -> Dict[str, int]:
        """Convert JSON file to Parquet format (requires pandas/pyarrow)"""
        try:
            import pandas as pd
            
            async with aiofiles.open(source_path, 'r') as source_file:
                data = json.loads(await source_file.read())
            
            if isinstance(data, list):
                df = pd.DataFrame(data)
            else:
                df = pd.DataFrame([data])
            
            df.to_parquet(target_path, compression='snappy')
            
            return {'total': len(df), 'successful': len(df), 'failed': 0}
        except ImportError:
            error_msg = "pandas and pyarrow required for Parquet export"
            self.errors.append(error_msg)
            return {'total': 0, 'successful': 0, 'failed': 1}
        except Exception as e:
            self.errors.append(f"Parquet conversion error: {str(e)}")
            return {'total': 0, 'successful': 0, 'failed': 1}
    
    def _flatten_dict(self, d: Dict[str, Any], parent_key: str = '', sep: str = '.') -> Dict[str, Any]:
        """Flatten nested dictionary"""
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep=sep).items())
            elif isinstance(v, list):
                items.append((new_key, json.dumps(v)))
            else:
                items.append((new_key, v))
        return dict(items)
    
    def _extract_nested_keys(self, obj: Any, prefix: str = '') -> List[str]:
        """Extract all keys from nested structure"""
        keys = []
        if isinstance(obj, dict):
            for k, v in obj.items():
                key = f"{prefix}.{k}" if prefix else k
                if isinstance(v, dict):
                    keys.extend(self._extract_nested_keys(v, key))
                else:
                    keys.append(key)
        return keys
    
    def _xml_to_dict(self, element: ET.Element) -> Dict[str, Any]:
        """Convert XML element to dictionary"""
        result = {}
        
        # Add attributes
        if element.attrib:
            result.update({f"@{k}": v for k, v in element.attrib.items()})
        
        # Add text content
        if element.text and element.text.strip():
            result['#text'] = element.text.strip()
        
        # Add child elements
        for child in element:
            child_data = self._xml_to_dict(child)
            if child.tag in result:
                if not isinstance(result[child.tag], list):
                    result[child.tag] = [result[child.tag]]
                result[child.tag].append(child_data)
            else:
                result[child.tag] = child_data
        
        return result
    
    def _escape_csv_value(self, value: str) -> str:
        """Escape CSV value with quotes if needed"""
        if ',' in value or '"' in value or '\n' in value:
            return f'"{value.replace('"', '""')}"'
        return value

class BulkMediaTransformer:
    """Transform media files (images, videos) with metadata preservation"""
    
    def __init__(self, config: TransformationConfig):
        self.config = config
        self.supported_formats = {
            'image': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'],
            'video': ['.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm'],
            'audio': ['.mp3', '.wav', '.flac', '.aac', '.ogg']
        }
    
    async def transform_media_batch(self, source_dir: str, target_dir: str, 
                                  target_format: str) -> TransformationResult:
        """Transform batch of media files to target format"""
        start_time = datetime.now()
        os.makedirs(target_dir, exist_ok=True)
        
        total_files = 0
        successful = 0
        failed = 0
        errors = []
        output_files = []
        
        with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            futures = []
            
            for root, dirs, files in os.walk(source_dir):
                for file in files:
                    if any(file.lower().endswith(ext) for ext in self.supported_formats['image']):
                        source_path = os.path.join(root, file)
                        relative_path = os.path.relpath(source_path, source_dir)
                        target_path = os.path.join(target_dir, 
                                                 os.path.splitext(relative_path)[0] + f'.{target_format}')
                        
                        os.makedirs(os.path.dirname(target_path), exist_ok=True)
                        
                        future = executor.submit(self._transform_image, source_path, target_path, target_format)
                        futures.append((future, source_path, target_path))
                        total_files += 1
            
            for future, source_path, target_path in futures:
                try:
                    result = future.result()
                    if result:
                        successful += 1
                        output_files.append(target_path)
                    else:
                        failed += 1
                        errors.append(f"Failed to transform {source_path}")
                except Exception as e:
                    failed += 1
                    errors.append(f"Error transforming {source_path}: {str(e)}")
        
        processing_time = (datetime.now() - start_time).total_seconds()
        transformation_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        return TransformationResult(
            total_records=total_files,
            successful=successful,
            failed=failed,
            errors=errors,
            output_files=output_files,
            processing_time=processing_time,
            transformation_id=transformation_id
        )
    
    def _transform_image(self, source_path: str, target_path: str, target_format: str) -> bool:
        """Transform single image file"""
        try:
            with Image.open(source_path) as img:
                # Preserve EXIF data if requested
                exif_dict = None
                if self.config.preserve_metadata and hasattr(img, '_getexif'):
                    exif_dict = img._getexif()
                
                # Convert and save
                if target_format.lower() == 'jpg' and img.mode in ('RGBA', 'LA', 'P'):
                    # Convert to RGB for JPEG
                    img = img.convert('RGB')
                
                save_kwargs = {}
                if target_format.lower() in ['jpg', 'jpeg']:
                    save_kwargs['quality'] = 85
                    save_kwargs['optimize'] = True
                    if exif_dict:
                        save_kwargs['exif'] = img.info.get('exif', b'')
                
                img.save(target_path, format=target_format.upper(), **save_kwargs)
                return True
        except Exception as e:
            logger.error(f"Image transformation failed for {source_path}: {str(e)}")
            return False

class DatabaseSchemaTransformer:
    """Transform database schemas and migrate data between different database formats"""
    
    def __init__(self, config: TransformationConfig):
        self.config = config
    
    async def transform_schema(self, source_db_url: str, target_db_url: str, 
                             table_mappings: Dict[str, str]) -> TransformationResult:
        """Transform data between different database schemas"""
        start_time = datetime.now()
        
        source_engine = create_async_engine(source_db_url)
        target_engine = create_async_engine(target_db_url)
        
        total_records = 0
        successful = 0
        failed = 0
        errors = []
        
        try:
            async with source_engine.begin() as source_conn:
                async with target_engine.begin() as target_conn:
                    for source_table, target_table in table_mappings.items():
                        try:
                            # Get source data
                            result = await source_conn.execute(
                                sa.text(f"SELECT * FROM {source_table}")
                            )
                            rows = result.fetchall()
                            columns = result.keys()
                            
                            if not rows:
                                continue
                            
                            # Prepare batch insert
                            batch_data = []
                            for row in rows:
                                total_records += 1
                                try:
                                    row_dict = dict(zip(columns, row))
                                    transformed_row = self._transform_row_schema(row_dict, source_table, target_table)
                                    batch_data.append(transformed_row)
                                    
                                    if len(batch_data) >= self.config.batch_size:
                                        inserted = await self._batch_insert(target_conn, target_table, batch_data)
                                        successful += inserted
                                        failed += len(batch_data) - inserted
                                        batch_data = []
                                        
                                except Exception as e:
                                    failed += 1
                                    errors.append(f"Row transformation error in {source_table}: {str(e)}")
                            
                            # Insert remaining batch
                            if batch_data:
                                inserted = await self._batch_insert(target_conn, target_table, batch_data)
                                successful += inserted
                                failed += len(batch_data) - inserted
                                
                        except Exception as e:
                            errors.append(f"Table transformation error {source_table}: {str(e)}")
            
        except Exception as e:
            errors.append(f"Database connection error: {str(e)}")
        finally:
            await source_engine.dispose()
            await target_engine.dispose()
        
        processing_time = (datetime.now() - start_time).total_seconds()
        transformation_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        return TransformationResult(
            total_records=total_records,
            successful=successful,
            failed=failed,
            errors=errors,
            output_files=[],
            processing_time=processing_time,
            transformation_id=transformation_id
        )
    
    def _transform_row_schema(self, row: Dict[str, Any], source_table: str, target_table: str) -> Dict[str, Any]:
        """Transform row data according to schema mapping"""
        # Example transformations - customize based on actual schema differences
        transformations = {
            'user_profiles': {
                'full_name': lambda row: f"{row.get('first_name', '')} {row.get('last_name', '')}".strip(),
                'created_at': lambda row: datetime.fromisoformat(row['created_at']) if isinstance(row.get('created_at'), str) else row.get('created_at'),
                'is_active': lambda row: bool(row.get('status') == 'active')
            }
        }
        
        if source_table in transformations:
            for new_field, transform_func in transformations[source_table].items():
                try:
                    row[new_field] = transform_func(row)
                except Exception as e:
                    logger.warning(f"Field transformation failed for {new_field}: {str(e)}")
        
        return row
    
    async def _batch_insert(self, conn, table_name: str, batch_data: List[Dict[str, Any]]) -> int:
        """Insert batch of data into target table"""
        try:
            if not batch_data:
                return 0
            
            # Build parameterized insert query
            columns = list(batch_data[0].keys())
            placeholders = ', '.join([f':{col}' for col in columns])
            query = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"
            
            result = await conn.execute(sa.text(query), batch_data)
            return len(batch_data)
        except Exception as e:
            logger.error(f"Batch insert failed: {str(e)}")
            return 0

class BulkTransformationManager:
    """Orchestrate multiple bulk transformations"""
    
    def __init__(self):
        self.active_transformations = {}
        self.transformation_history = []
    
    async def schedule_transformation(self, transformation_type: str, config: TransformationConfig,
                                    source_path: str, target_path: str, **kwargs) -> str:
        """Schedule a bulk transformation task"""
        transformation_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        
        if transformation_type == "data":
            transformer = DataTransformer(config)
            task = asyncio.create_task(transformer.transform(source_path, target_path))
        elif transformation_type == "media":
            transformer = BulkMediaTransformer(config)
            task = asyncio.create_task(transformer.transform_media_batch(
                source_path, target_path, kwargs.get('target_format', 'jpg')))
        elif transformation_type == "database":
            transformer = DatabaseSchemaTransformer(config)
            task = asyncio.create_task(transformer.transform_schema(
                source_path, target_path, kwargs.get('table_mappings', {})))
        else:
            raise ValueError(f"Unknown transformation type: {transformation_type}")
        
        self.active_transformations[transformation_id] = {
            'task': task,
            'type': transformation_type,
            'config': config,
            'source': source_path,
            'target': target_path,
            'started_at': datetime.now()
        }
        
        return transformation_id
    
    async def get_transformation_status(self, transformation_id: str) -> Dict[str, Any]:
        """Get status of transformation task"""
        if transformation_id not in self.active_transformations:
            return {'status': 'not_found'}
        
        transformation = self.active_transformations[transformation_id]
        task = transformation['task']
        
        if task.done():
            try:
                result = task.result()
                status = {
                    'status': 'completed',
                    'result': asdict(result),
                    'started_at': transformation['started_at'].isoformat(),
                    'completed_at': datetime.now().isoformat()
                }
                # Move to history
                self.transformation_history.append(status)
                del self.active_transformations[transformation_id]
                return status
            except Exception as e:
                status = {
                    'status': 'failed',
                    'error': str(e),
                    'started_at': transformation['started_at'].isoformat(),
                    'failed_at': datetime.now().isoformat()
                }
                self.transformation_history.append(status)
                del self.active_transformations[transformation_id]
                return status
        else:
            return {
                'status': 'running',
                'type': transformation['type'],
                'started_at': transformation['started_at'].isoformat(),
                'elapsed_time': (datetime.now() - transformation['started_at']).total_seconds()
            }
    
    async def cancel_transformation(self, transformation_id: str) -> bool:
        """Cancel running transformation"""
        if transformation_id in self.active_transformations:
            task = self.active_transformations[transformation_id]['task']
            task.cancel()
            del self.active_transformations[transformation_id]
            return True
        return False
    
    def list_transformations(self) -> Dict[str, Any]:
        """List all active and completed transformations"""
        active = {tid: {
            'type': info['type'],
            'started_at': info['started_at'].isoformat(),
            'elapsed_time': (datetime.now() - info['started_at']).total_seconds()
        } for tid, info in self.active_transformations.items()}
        
        return {
            'active': active,
            'history': self.transformation_history[-50:]  # Last 50 transformations
        }

# CLI Interface
async def main():
    """Command-line interface for bulk transformations"""
    import argparse
    
    parser = argparse.ArgumentParser(description='ActiveLog Bulk Data Transformation Tool')
    parser.add_argument('action', choices=['transform', 'status', 'list', 'cancel'])
    parser.add_argument('--type', choices=['data', 'media', 'database'], default='data')
    parser.add_argument('--source-format', default='json')
    parser.add_argument('--target-format', default='csv')
    parser.add_argument('--source', help='Source file/directory path')
    parser.add_argument('--target', help='Target file/directory path')
    parser.add_argument('--batch-size', type=int, default=1000)
    parser.add_argument('--workers', type=int, default=4)
    parser.add_argument('--transformation-id', help='Transformation ID for status/cancel operations')
    
    args = parser.parse_args()
    
    manager = BulkTransformationManager()
    
    if args.action == 'transform':
        if not args.source or not args.target:
            print("Error: --source and --target required for transform action")
            return
        
        config = TransformationConfig(
            source_format=args.source_format,
            target_format=args.target_format,
            batch_size=args.batch_size,
            max_workers=args.workers
        )
        
        transformation_id = await manager.schedule_transformation(
            args.type, config, args.source, args.target
        )
        
        print(f"Transformation scheduled with ID: {transformation_id}")
        
        # Wait for completion and show result
        while True:
            status = await manager.get_transformation_status(transformation_id)
            if status['status'] in ['completed', 'failed', 'not_found']:
                print(json.dumps(status, indent=2))
                break
            await asyncio.sleep(1)
    
    elif args.action == 'status':
        if not args.transformation_id:
            print("Error: --transformation-id required for status action")
            return
        
        status = await manager.get_transformation_status(args.transformation_id)
        print(json.dumps(status, indent=2))
    
    elif args.action == 'list':
        transformations = manager.list_transformations()
        print(json.dumps(transformations, indent=2))
    
    elif args.action == 'cancel':
        if not args.transformation_id:
            print("Error: --transformation-id required for cancel action")
            return
        
        cancelled = await manager.cancel_transformation(args.transformation_id)
        print(f"Transformation {'cancelled' if cancelled else 'not found'}")

if __name__ == "__main__":
    asyncio.run(main())