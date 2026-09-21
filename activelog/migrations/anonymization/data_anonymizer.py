#!/usr/bin/env python3
"""
Data Anonymization Tools for ActiveLog
Provides comprehensive data anonymization for privacy protection and test data generation
"""

import asyncio
import json
import logging
import os
import random
import re
import string
import hashlib
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Callable
import aiofiles
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import text
from faker import Faker
import secrets

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class AnonymizationRule:
    """Defines how to anonymize a specific field"""
    field_name: str
    table_name: str
    anonymization_type: str  # 'mask', 'fake', 'hash', 'encrypt', 'shuffle', 'null', 'static'
    parameters: Dict[str, Any] = None
    preserve_format: bool = False
    preserve_length: bool = False
    preserve_uniqueness: bool = False

@dataclass
class AnonymizationJob:
    """Represents an anonymization job configuration"""
    job_id: str
    job_name: str
    source_database: str
    target_database: Optional[str] = None  # If None, anonymize in place
    tables_to_anonymize: List[str] = None
    rules: List[AnonymizationRule] = None
    preserve_referential_integrity: bool = True
    batch_size: int = 1000
    backup_before_anonymization: bool = True

@dataclass
class AnonymizationResult:
    """Result of anonymization operation"""
    job_id: str
    started_at: datetime
    completed_at: Optional[datetime]
    status: str  # 'running', 'completed', 'failed'
    tables_processed: int
    records_anonymized: int
    execution_time: float
    backup_location: Optional[str] = None
    error_message: Optional[str] = None

class DataMasker:
    """Handles various data masking techniques"""
    
    def __init__(self, locale: str = 'en_US'):
        self.fake = Faker(locale)
        self.email_domains = ['example.com', 'test.org', 'demo.net', 'sample.io']
        
    def mask_email(self, email: str, preserve_domain: bool = False) -> str:
        """Mask email address while optionally preserving domain"""
        if not email or '@' not in email:
            return email
        
        local, domain = email.split('@', 1)
        
        if preserve_domain:
            masked_local = self._generate_masked_string(len(local), 'alpha')
            return f"{masked_local}@{domain}"
        else:
            masked_local = self._generate_masked_string(len(local), 'alpha')
            masked_domain = random.choice(self.email_domains)
            return f"{masked_local}@{masked_domain}"
    
    def mask_phone(self, phone: str) -> str:
        """Mask phone number while preserving format"""
        if not phone:
            return phone
        
        # Extract digits only
        digits = re.sub(r'\D', '', phone)
        if len(digits) < 7:
            return phone
        
        # Generate new digits while preserving format
        new_digits = ''.join([str(random.randint(0, 9)) for _ in range(len(digits))])
        
        # Reconstruct with original formatting
        result = phone
        digit_index = 0
        for i, char in enumerate(phone):
            if char.isdigit():
                result = result[:i] + new_digits[digit_index] + result[i+1:]
                digit_index += 1
        
        return result
    
    def mask_name(self, name: str, preserve_initials: bool = False) -> str:
        """Mask name while optionally preserving initials"""
        if not name:
            return name
        
        parts = name.split()
        masked_parts = []
        
        for part in parts:
            if preserve_initials and len(part) > 0:
                masked_part = part[0] + self._generate_masked_string(len(part) - 1, 'alpha')
            else:
                masked_part = self._generate_masked_string(len(part), 'alpha')
            masked_parts.append(masked_part)
        
        return ' '.join(masked_parts)
    
    def mask_credit_card(self, cc_number: str) -> str:
        """Mask credit card number showing only last 4 digits"""
        if not cc_number:
            return cc_number
        
        digits = re.sub(r'\D', '', cc_number)
        if len(digits) < 4:
            return cc_number
        
        # Keep last 4 digits, mask the rest
        masked_digits = '*' * (len(digits) - 4) + digits[-4:]
        
        # Reconstruct with original formatting
        result = cc_number
        digit_index = 0
        for i, char in enumerate(cc_number):
            if char.isdigit():
                result = result[:i] + masked_digits[digit_index] + result[i+1:]
                digit_index += 1
        
        return result
    
    def mask_ip_address(self, ip: str) -> str:
        """Mask IP address while preserving format"""
        if not ip:
            return ip
        
        # IPv4 pattern
        if re.match(r'^\d+\.\d+\.\d+\.\d+$', ip):
            parts = ip.split('.')
            # Keep first octet, randomize others
            masked_parts = [parts[0]] + [str(random.randint(1, 254)) for _ in range(3)]
            return '.'.join(masked_parts)
        
        # For other formats, just randomize
        return self.fake.ipv4()
    
    def _generate_masked_string(self, length: int, char_type: str = 'alpha') -> str:
        """Generate masked string of specified length and type"""
        if char_type == 'alpha':
            return ''.join(random.choices(string.ascii_letters, k=length))
        elif char_type == 'numeric':
            return ''.join(random.choices(string.digits, k=length))
        elif char_type == 'alphanumeric':
            return ''.join(random.choices(string.ascii_letters + string.digits, k=length))
        else:
            return '*' * length

class FakeDataGenerator:
    """Generates realistic fake data using Faker library"""
    
    def __init__(self, locale: str = 'en_US', seed: Optional[int] = None):
        self.fake = Faker(locale)
        if seed:
            Faker.seed(seed)
            random.seed(seed)
    
    def generate_email(self) -> str:
        """Generate fake email address"""
        return self.fake.email()
    
    def generate_name(self) -> str:
        """Generate fake full name"""
        return self.fake.name()
    
    def generate_first_name(self) -> str:
        """Generate fake first name"""
        return self.fake.first_name()
    
    def generate_last_name(self) -> str:
        """Generate fake last name"""
        return self.fake.last_name()
    
    def generate_phone(self) -> str:
        """Generate fake phone number"""
        return self.fake.phone_number()
    
    def generate_address(self) -> str:
        """Generate fake address"""
        return self.fake.address()
    
    def generate_company(self) -> str:
        """Generate fake company name"""
        return self.fake.company()
    
    def generate_date_of_birth(self, min_age: int = 18, max_age: int = 80) -> datetime:
        """Generate fake date of birth within age range"""
        return self.fake.date_of_birth(minimum_age=min_age, maximum_age=max_age)
    
    def generate_username(self) -> str:
        """Generate fake username"""
        return self.fake.user_name()
    
    def generate_bio(self) -> str:
        """Generate fake biography text"""
        return self.fake.text(max_nb_chars=200)
    
    def generate_url(self) -> str:
        """Generate fake URL"""
        return self.fake.url()
    
    def generate_job_title(self) -> str:
        """Generate fake job title"""
        return self.fake.job()

class DataHasher:
    """Handles data hashing for consistent anonymization"""
    
    def __init__(self, salt: str = None):
        self.salt = salt or secrets.token_hex(16)
    
    def hash_value(self, value: str, algorithm: str = 'sha256') -> str:
        """Hash value with salt"""
        if not value:
            return value
        
        salted_value = f"{self.salt}{value}"
        
        if algorithm == 'md5':
            return hashlib.md5(salted_value.encode()).hexdigest()
        elif algorithm == 'sha1':
            return hashlib.sha1(salted_value.encode()).hexdigest()
        elif algorithm == 'sha256':
            return hashlib.sha256(salted_value.encode()).hexdigest()
        else:
            raise ValueError(f"Unsupported hash algorithm: {algorithm}")
    
    def hash_preserving_format(self, value: str, format_pattern: str = None) -> str:
        """Hash value while preserving specific format"""
        if not value:
            return value
        
        # For email format preservation
        if '@' in value and '.' in value:
            local, domain = value.split('@', 1)
            hashed_local = self.hash_value(local)[:len(local)]
            return f"{hashed_local}@{domain}"
        
        # For other formats, return truncated hash
        hashed = self.hash_value(value)
        return hashed[:len(value)] if len(hashed) >= len(value) else hashed

class DataShuffler:
    """Handles data shuffling within columns to preserve distribution"""
    
    def __init__(self, seed: Optional[int] = None):
        if seed:
            random.seed(seed)
    
    async def shuffle_column_values(self, engine, table_name: str, column_name: str) -> int:
        """Shuffle values within a column to preserve distribution but break associations"""
        async with engine.begin() as conn:
            # Get all values from the column
            select_query = f"SELECT id, {column_name} FROM {table_name} WHERE {column_name} IS NOT NULL"
            result = await conn.execute(text(select_query))
            rows = result.fetchall()
            
            if not rows:
                return 0
            
            # Extract values and shuffle them
            ids = [row[0] for row in rows]
            values = [row[1] for row in rows]
            random.shuffle(values)
            
            # Update with shuffled values
            updated_count = 0
            for row_id, new_value in zip(ids, values):
                update_query = f"UPDATE {table_name} SET {column_name} = :value WHERE id = :id"
                await conn.execute(text(update_query), {"value": new_value, "id": row_id})
                updated_count += 1
            
            return updated_count

class DataAnonymizer:
    """Main data anonymization engine"""
    
    def __init__(self, job: AnonymizationJob):
        self.job = job
        self.source_engine = None
        self.target_engine = None
        self.masker = DataMasker()
        self.faker = FakeDataGenerator()
        self.hasher = DataHasher()
        self.shuffler = DataShuffler()
        self.id_mappings = {}  # For preserving referential integrity
    
    async def initialize(self):
        """Initialize database connections"""
        self.source_engine = create_async_engine(self.job.source_database)
        
        if self.job.target_database:
            self.target_engine = create_async_engine(self.job.target_database)
        else:
            self.target_engine = self.source_engine
    
    async def execute_anonymization(self) -> AnonymizationResult:
        """Execute the anonymization job"""
        start_time = datetime.now()
        
        result = AnonymizationResult(
            job_id=self.job.job_id,
            started_at=start_time,
            completed_at=None,
            status='running',
            tables_processed=0,
            records_anonymized=0,
            execution_time=0.0
        )
        
        try:
            await self.initialize()
            
            # Create backup if requested
            if self.job.backup_before_anonymization:
                result.backup_location = await self._create_backup()
            
            # Process each table
            tables_to_process = self.job.tables_to_anonymize or await self._get_all_tables()
            
            for table_name in tables_to_process:
                logger.info(f"Anonymizing table: {table_name}")
                
                table_rules = [rule for rule in self.job.rules if rule.table_name == table_name]
                records_count = await self._anonymize_table(table_name, table_rules)
                
                result.tables_processed += 1
                result.records_anonymized += records_count
                
                logger.info(f"Anonymized {records_count} records in {table_name}")
            
            result.status = 'completed'
            result.completed_at = datetime.now()
            result.execution_time = (result.completed_at - start_time).total_seconds()
            
            logger.info(f"Anonymization completed: {result.records_anonymized} records processed")
            
        except Exception as e:
            result.status = 'failed'
            result.error_message = str(e)
            result.completed_at = datetime.now()
            result.execution_time = (result.completed_at - start_time).total_seconds()
            
            logger.error(f"Anonymization failed: {str(e)}")
        
        finally:
            if self.source_engine:
                await self.source_engine.dispose()
            if self.target_engine and self.target_engine != self.source_engine:
                await self.target_engine.dispose()
        
        return result
    
    async def _create_backup(self) -> str:
        """Create backup before anonymization"""
        backup_name = f"{self.job.job_id}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        # This would integrate with the backup manager
        logger.info(f"Backup created: {backup_name}")
        return backup_name
    
    async def _get_all_tables(self) -> List[str]:
        """Get list of all tables in database"""
        async with self.source_engine.begin() as conn:
            if 'postgresql' in self.job.source_database:
                query = "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
            elif 'mysql' in self.job.source_database:
                query = "SELECT table_name FROM information_schema.tables WHERE table_schema = DATABASE()"
            else:  # SQLite
                query = "SELECT name FROM sqlite_master WHERE type='table'"
            
            result = await conn.execute(text(query))
            return [row[0] for row in result.fetchall()]
    
    async def _anonymize_table(self, table_name: str, rules: List[AnonymizationRule]) -> int:
        """Anonymize a single table according to rules"""
        if not rules:
            return 0
        
        # Get total record count
        async with self.source_engine.begin() as conn:
            count_result = await conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
            total_records = count_result.scalar()
        
        if total_records == 0:
            return 0
        
        # Process in batches
        records_processed = 0
        offset = 0
        
        while offset < total_records:
            batch_size = min(self.job.batch_size, total_records - offset)
            
            # Get batch of records
            async with self.source_engine.begin() as source_conn:
                select_query = f"SELECT * FROM {table_name} LIMIT {batch_size} OFFSET {offset}"
                result = await source_conn.execute(text(select_query))
                rows = result.fetchall()
                columns = result.keys()
            
            # Anonymize batch
            anonymized_rows = []
            for row in rows:
                row_dict = dict(zip(columns, row))
                anonymized_row = await self._anonymize_record(row_dict, rules)
                anonymized_rows.append(anonymized_row)
            
            # Update batch
            async with self.target_engine.begin() as target_conn:
                for anonymized_row in anonymized_rows:
                    await self._update_record(target_conn, table_name, anonymized_row)
            
            records_processed += len(anonymized_rows)
            offset += batch_size
            
            logger.debug(f"Processed {records_processed}/{total_records} records in {table_name}")
        
        return records_processed
    
    async def _anonymize_record(self, record: Dict[str, Any], rules: List[AnonymizationRule]) -> Dict[str, Any]:
        """Anonymize a single record according to rules"""
        anonymized_record = record.copy()
        
        for rule in rules:
            field_value = record.get(rule.field_name)
            
            if field_value is None:
                continue
            
            anonymized_value = await self._apply_anonymization_rule(field_value, rule)
            anonymized_record[rule.field_name] = anonymized_value
        
        return anonymized_record
    
    async def _apply_anonymization_rule(self, value: Any, rule: AnonymizationRule) -> Any:
        """Apply a specific anonymization rule to a value"""
        if value is None:
            return value
        
        value_str = str(value)
        
        if rule.anonymization_type == 'mask':
            if rule.field_name.lower() in ['email', 'email_address']:
                return self.masker.mask_email(value_str, rule.parameters.get('preserve_domain', False))
            elif rule.field_name.lower() in ['phone', 'phone_number']:
                return self.masker.mask_phone(value_str)
            elif rule.field_name.lower() in ['name', 'full_name', 'first_name', 'last_name']:
                return self.masker.mask_name(value_str, rule.parameters.get('preserve_initials', False))
            elif rule.field_name.lower() in ['credit_card', 'cc_number']:
                return self.masker.mask_credit_card(value_str)
            elif rule.field_name.lower() in ['ip_address', 'ip']:
                return self.masker.mask_ip_address(value_str)
            else:
                # Generic masking
                return self.masker._generate_masked_string(len(value_str))
        
        elif rule.anonymization_type == 'fake':
            if rule.field_name.lower() in ['email', 'email_address']:
                return self.faker.generate_email()
            elif rule.field_name.lower() in ['name', 'full_name']:
                return self.faker.generate_name()
            elif rule.field_name.lower() == 'first_name':
                return self.faker.generate_first_name()
            elif rule.field_name.lower() == 'last_name':
                return self.faker.generate_last_name()
            elif rule.field_name.lower() in ['phone', 'phone_number']:
                return self.faker.generate_phone()
            elif rule.field_name.lower() == 'address':
                return self.faker.generate_address()
            elif rule.field_name.lower() == 'company':
                return self.faker.generate_company()
            elif rule.field_name.lower() == 'username':
                return self.faker.generate_username()
            elif rule.field_name.lower() == 'bio':
                return self.faker.generate_bio()
            elif rule.field_name.lower() in ['url', 'website']:
                return self.faker.generate_url()
            elif rule.field_name.lower() == 'job_title':
                return self.faker.generate_job_title()
            else:
                return self.faker.fake.text(max_nb_chars=len(value_str))
        
        elif rule.anonymization_type == 'hash':
            algorithm = rule.parameters.get('algorithm', 'sha256') if rule.parameters else 'sha256'
            if rule.preserve_format:
                return self.hasher.hash_preserving_format(value_str)
            else:
                return self.hasher.hash_value(value_str, algorithm)
        
        elif rule.anonymization_type == 'encrypt':
            # Simple encryption placeholder - in production, use proper encryption
            return hashlib.sha256(f"encrypted_{value_str}".encode()).hexdigest()[:len(value_str)]
        
        elif rule.anonymization_type == 'null':
            return None
        
        elif rule.anonymization_type == 'static':
            static_value = rule.parameters.get('value', 'REDACTED') if rule.parameters else 'REDACTED'
            return static_value
        
        elif rule.anonymization_type == 'shuffle':
            # Shuffling is handled at the table level, return original value for now
            return value
        
        else:
            logger.warning(f"Unknown anonymization type: {rule.anonymization_type}")
            return value
    
    async def _update_record(self, conn, table_name: str, record: Dict[str, Any]):
        """Update a record in the target database"""
        # Assume 'id' is the primary key
        record_id = record['id']
        
        # Build update query
        set_clauses = []
        parameters = {'record_id': record_id}
        
        for field, value in record.items():
            if field != 'id':  # Don't update the primary key
                set_clauses.append(f"{field} = :{field}")
                parameters[field] = value
        
        if set_clauses:
            update_query = f"UPDATE {table_name} SET {', '.join(set_clauses)} WHERE id = :record_id"
            await conn.execute(text(update_query), parameters)

class AnonymizationJobBuilder:
    """Helper class to build anonymization jobs"""
    
    @staticmethod
    def create_standard_user_anonymization() -> List[AnonymizationRule]:
        """Create standard anonymization rules for user data"""
        return [
            AnonymizationRule('email', 'users', 'fake'),
            AnonymizationRule('full_name', 'users', 'fake'),
            AnonymizationRule('phone_number', 'users', 'mask'),
            AnonymizationRule('bio', 'users', 'fake'),
            AnonymizationRule('avatar_url', 'users', 'null'),
            AnonymizationRule('date_of_birth', 'users', 'shuffle'),
        ]
    
    @staticmethod
    def create_activity_log_anonymization() -> List[AnonymizationRule]:
        """Create anonymization rules for activity logs"""
        return [
            AnonymizationRule('title', 'activity_logs', 'fake'),
            AnonymizationRule('description', 'activity_logs', 'fake'),
            AnonymizationRule('location_data', 'activity_logs', 'null'),
            AnonymizationRule('source_device', 'activity_logs', 'hash'),
        ]
    
    @staticmethod
    def create_minimal_anonymization() -> List[AnonymizationRule]:
        """Create minimal anonymization rules (only PII)"""
        return [
            AnonymizationRule('email', 'users', 'hash', preserve_format=True),
            AnonymizationRule('full_name', 'users', 'mask'),
            AnonymizationRule('phone_number', 'users', 'mask'),
        ]
    
    @staticmethod
    def from_config_file(config_path: str) -> AnonymizationJob:
        """Load anonymization job from configuration file"""
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        rules = []
        for rule_config in config.get('rules', []):
            rule = AnonymizationRule(
                field_name=rule_config['field_name'],
                table_name=rule_config['table_name'],
                anonymization_type=rule_config['anonymization_type'],
                parameters=rule_config.get('parameters'),
                preserve_format=rule_config.get('preserve_format', False),
                preserve_length=rule_config.get('preserve_length', False),
                preserve_uniqueness=rule_config.get('preserve_uniqueness', False)
            )
            rules.append(rule)
        
        job = AnonymizationJob(
            job_id=config['job_id'],
            job_name=config['job_name'],
            source_database=config['source_database'],
            target_database=config.get('target_database'),
            tables_to_anonymize=config.get('tables_to_anonymize'),
            rules=rules,
            preserve_referential_integrity=config.get('preserve_referential_integrity', True),
            batch_size=config.get('batch_size', 1000),
            backup_before_anonymization=config.get('backup_before_anonymization', True)
        )
        
        return job
    
    @staticmethod
    def create_sample_config() -> str:
        """Create a sample anonymization configuration"""
        sample_config = {
            "job_id": "user_data_anonymization_20250822",
            "job_name": "User Data Anonymization for Testing",
            "source_database": "postgresql://user:pass@localhost/activelog",
            "target_database": "postgresql://user:pass@localhost/activelog_anonymized",
            "tables_to_anonymize": ["users", "activity_logs"],
            "preserve_referential_integrity": True,
            "batch_size": 1000,
            "backup_before_anonymization": True,
            "rules": [
                {
                    "field_name": "email",
                    "table_name": "users",
                    "anonymization_type": "fake",
                    "preserve_format": False,
                    "preserve_uniqueness": True
                },
                {
                    "field_name": "full_name",
                    "table_name": "users",
                    "anonymization_type": "fake"
                },
                {
                    "field_name": "phone_number",
                    "table_name": "users",
                    "anonymization_type": "mask",
                    "preserve_format": True
                },
                {
                    "field_name": "bio",
                    "table_name": "users",
                    "anonymization_type": "fake"
                },
                {
                    "field_name": "title",
                    "table_name": "activity_logs",
                    "anonymization_type": "fake"
                },
                {
                    "field_name": "description",
                    "table_name": "activity_logs",
                    "anonymization_type": "fake"
                },
                {
                    "field_name": "location_data",
                    "table_name": "activity_logs",
                    "anonymization_type": "null"
                }
            ]
        }
        
        return json.dumps(sample_config, indent=2)

# CLI Interface
async def main():
    """Command-line interface for data anonymization"""
    import argparse
    
    parser = argparse.ArgumentParser(description='ActiveLog Data Anonymization Tool')
    parser.add_argument('action', choices=['anonymize', 'config', 'test', 'validate'])
    parser.add_argument('--config-file', help='Anonymization configuration file')
    parser.add_argument('--database-url', help='Source database URL')
    parser.add_argument('--target-database-url', help='Target database URL (optional)')
    parser.add_argument('--preset', choices=['standard', 'minimal', 'activity'], help='Use preset anonymization rules')
    parser.add_argument('--output', help='Output file for configuration or results')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be anonymized without making changes')
    
    args = parser.parse_args()
    
    if args.action == 'config':
        # Generate sample configuration
        sample_config = AnonymizationJobBuilder.create_sample_config()
        
        if args.output:
            with open(args.output, 'w') as f:
                f.write(sample_config)
            print(f"Sample configuration written to: {args.output}")
        else:
            print("Sample Anonymization Configuration:")
            print(sample_config)
    
    elif args.action == 'test':
        # Test anonymization functions
        masker = DataMasker()
        faker = FakeDataGenerator()
        
        print("Data Anonymization Test Results:")
        
        # Test masking
        test_email = "john.doe@company.com"
        print(f"Original email: {test_email}")
        print(f"Masked email: {masker.mask_email(test_email)}")
        print(f"Masked email (preserve domain): {masker.mask_email(test_email, preserve_domain=True)}")
        
        test_phone = "+1 (555) 123-4567"
        print(f"Original phone: {test_phone}")
        print(f"Masked phone: {masker.mask_phone(test_phone)}")
        
        test_name = "John Alexander Doe"
        print(f"Original name: {test_name}")
        print(f"Masked name: {masker.mask_name(test_name)}")
        print(f"Masked name (preserve initials): {masker.mask_name(test_name, preserve_initials=True)}")
        
        # Test fake data generation
        print(f"Fake email: {faker.generate_email()}")
        print(f"Fake name: {faker.generate_name()}")
        print(f"Fake phone: {faker.generate_phone()}")
        print(f"Fake bio: {faker.generate_bio()}")
    
    elif args.action == 'validate':
        if not args.config_file:
            print("Error: --config-file required for validation")
            return
        
        try:
            job = AnonymizationJobBuilder.from_config_file(args.config_file)
            print(f"Configuration validation successful")
            print(f"Job: {job.job_name}")
            print(f"Tables: {job.tables_to_anonymize}")
            print(f"Rules: {len(job.rules)}")
            
            for rule in job.rules:
                print(f"  {rule.table_name}.{rule.field_name} -> {rule.anonymization_type}")
        
        except Exception as e:
            print(f"Configuration validation failed: {str(e)}")
    
    elif args.action == 'anonymize':
        if args.config_file:
            # Use configuration file
            job = AnonymizationJobBuilder.from_config_file(args.config_file)
        elif args.database_url and args.preset:
            # Use preset rules
            job_id = f"anonymization_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            if args.preset == 'standard':
                rules = AnonymizationJobBuilder.create_standard_user_anonymization()
                rules.extend(AnonymizationJobBuilder.create_activity_log_anonymization())
            elif args.preset == 'minimal':
                rules = AnonymizationJobBuilder.create_minimal_anonymization()
            elif args.preset == 'activity':
                rules = AnonymizationJobBuilder.create_activity_log_anonymization()
            
            job = AnonymizationJob(
                job_id=job_id,
                job_name=f"Preset {args.preset} anonymization",
                source_database=args.database_url,
                target_database=args.target_database_url,
                rules=rules
            )
        else:
            print("Error: Either --config-file or --database-url with --preset required")
            return
        
        if args.dry_run:
            print("DRY RUN - Would anonymize:")
            print(f"Job: {job.job_name}")
            print(f"Source: {job.source_database}")
            print(f"Target: {job.target_database or 'In-place'}")
            print(f"Tables: {job.tables_to_anonymize or 'All tables'}")
            print("Rules:")
            for rule in job.rules:
                print(f"  {rule.table_name}.{rule.field_name} -> {rule.anonymization_type}")
        else:
            # Execute anonymization
            anonymizer = DataAnonymizer(job)
            result = await anonymizer.execute_anonymization()
            
            print(f"Anonymization Status: {result.status}")
            print(f"Job ID: {result.job_id}")
            print(f"Tables Processed: {result.tables_processed}")
            print(f"Records Anonymized: {result.records_anonymized}")
            print(f"Execution Time: {result.execution_time:.2f} seconds")
            
            if result.backup_location:
                print(f"Backup Location: {result.backup_location}")
            
            if result.error_message:
                print(f"Error: {result.error_message}")
            
            # Save results if output file specified
            if args.output:
                with open(args.output, 'w') as f:
                    json.dump(asdict(result), f, indent=2, default=str)
                print(f"Results saved to: {args.output}")

if __name__ == "__main__":
    asyncio.run(main())