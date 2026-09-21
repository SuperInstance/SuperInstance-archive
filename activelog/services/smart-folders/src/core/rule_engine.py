"""
Rule Engine for Dynamic Folder Content Filtering

Supports complex rule-based filtering with multiple operators and conditions:
- File attribute matching (name, size, date, type, etc.)
- Content-based rules (text content, metadata)
- Logical operators (AND, OR, NOT)
- Regular expressions and pattern matching
- Performance optimized evaluation
"""

import asyncio
import logging
import re
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Set
from pathlib import Path
import mimetypes
import json

import magic
from PIL import Image

from .config import settings
from .database import RuleOperator

logger = logging.getLogger(__name__)

class RuleEvaluationError(Exception):
    """Exception raised during rule evaluation"""
    pass

class FileInfo:
    """File information container for rule evaluation"""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.path = Path(file_path)
        self._stat = None
        self._content = None
        self._metadata = None
        
    @property
    def stat(self):
        """Get file stat information"""
        if self._stat is None:
            try:
                self._stat = self.path.stat()
            except (OSError, IOError):
                self._stat = None
        return self._stat
    
    @property
    def name(self) -> str:
        """Get file name"""
        return self.path.name
    
    @property
    def stem(self) -> str:
        """Get file name without extension"""
        return self.path.stem
    
    @property
    def suffix(self) -> str:
        """Get file extension"""
        return self.path.suffix.lower()
    
    @property
    def size(self) -> int:
        """Get file size in bytes"""
        return self.stat.st_size if self.stat else 0
    
    @property
    def created_time(self) -> datetime:
        """Get file creation time"""
        if self.stat:
            return datetime.fromtimestamp(self.stat.st_ctime)
        return datetime.min
    
    @property
    def modified_time(self) -> datetime:
        """Get file modification time"""
        if self.stat:
            return datetime.fromtimestamp(self.stat.st_mtime)
        return datetime.min
    
    @property
    def accessed_time(self) -> datetime:
        """Get file access time"""
        if self.stat:
            return datetime.fromtimestamp(self.stat.st_atime)
        return datetime.min
    
    @property
    def mime_type(self) -> str:
        """Get MIME type"""
        mime_type, _ = mimetypes.guess_type(self.file_path)
        return mime_type or "application/octet-stream"
    
    @property
    def file_type(self) -> str:
        """Get general file type category"""
        mime = self.mime_type
        
        if mime.startswith("image/"):
            return "image"
        elif mime.startswith("video/"):
            return "video"
        elif mime.startswith("audio/"):
            return "audio"
        elif mime.startswith("text/"):
            return "text"
        elif mime in ["application/pdf", "application/msword", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]:
            return "document"
        elif mime.startswith("application/"):
            return "application"
        else:
            return "other"
    
    def get_content(self, max_size: int = 10000) -> str:
        """Get file content for text files"""
        if self._content is not None:
            return self._content
        
        try:
            if self.file_type == "text" and self.size <= max_size:
                with open(self.file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    self._content = f.read()
            else:
                self._content = ""
        except Exception as e:
            logger.debug(f"Could not read content from {self.file_path}: {e}")
            self._content = ""
        
        return self._content
    
    def get_metadata(self) -> Dict[str, Any]:
        """Get file metadata"""
        if self._metadata is not None:
            return self._metadata
        
        self._metadata = {}
        
        try:
            # Image metadata
            if self.file_type == "image":
                try:
                    with Image.open(self.file_path) as img:
                        self._metadata.update({
                            "width": img.width,
                            "height": img.height,
                            "format": img.format,
                            "mode": img.mode
                        })
                        
                        # EXIF data
                        if hasattr(img, '_getexif') and img._getexif():
                            self._metadata["exif"] = dict(img._getexif())
                            
                except Exception as e:
                    logger.debug(f"Could not extract image metadata from {self.file_path}: {e}")
            
            # Add more metadata extraction as needed
            
        except Exception as e:
            logger.debug(f"Error extracting metadata from {self.file_path}: {e}")
        
        return self._metadata

class RuleEngine:
    """Rule engine for evaluating folder rules against files"""
    
    def __init__(self):
        self.operators = {
            RuleOperator.EQUALS: self._op_equals,
            RuleOperator.NOT_EQUALS: self._op_not_equals,
            RuleOperator.CONTAINS: self._op_contains,
            RuleOperator.NOT_CONTAINS: self._op_not_contains,
            RuleOperator.STARTS_WITH: self._op_starts_with,
            RuleOperator.ENDS_WITH: self._op_ends_with,
            RuleOperator.REGEX: self._op_regex,
            RuleOperator.GREATER_THAN: self._op_greater_than,
            RuleOperator.LESS_THAN: self._op_less_than,
            RuleOperator.BETWEEN: self._op_between,
            RuleOperator.IN: self._op_in,
            RuleOperator.NOT_IN: self._op_not_in,
            RuleOperator.EXISTS: self._op_exists,
            RuleOperator.NOT_EXISTS: self._op_not_exists
        }
        
        self.field_extractors = {
            "file_name": lambda f: f.name,
            "file_stem": lambda f: f.stem,
            "file_extension": lambda f: f.suffix,
            "file_size": lambda f: f.size,
            "created_date": lambda f: f.created_time,
            "modified_date": lambda f: f.modified_time,
            "accessed_date": lambda f: f.accessed_time,
            "file_type": lambda f: f.file_type,
            "mime_type": lambda f: f.mime_type,
            "content": lambda f: f.get_content(),
            "path": lambda f: f.file_path,
            "metadata": lambda f: f.get_metadata()
        }
        
        self.evaluation_stats = {
            "total_evaluations": 0,
            "total_files_processed": 0,
            "total_execution_time": 0.0,
            "rule_performance": {}
        }
    
    async def initialize(self):
        """Initialize rule engine"""
        logger.info("Rule engine initialized")
    
    async def evaluate_rules(self, rules: List[Dict[str, Any]], logic: str = "AND", 
                           user_id: str = None) -> List[Dict[str, Any]]:
        """
        Evaluate rules against file system and return matching files
        
        Args:
            rules: List of rule definitions
            logic: Logic for combining rules ("AND" or "OR")
            user_id: User ID for file access permissions
            
        Returns:
            List of matching file information
        """
        
        if not rules:
            return []
        
        start_time = time.time()
        matching_files = []
        
        try:
            # Get files to evaluate (this would typically come from a file index)
            files_to_evaluate = await self._get_files_to_evaluate(user_id)
            
            for file_path in files_to_evaluate:
                try:
                    file_info = FileInfo(file_path)
                    
                    # Skip if file doesn't exist
                    if not file_info.path.exists():
                        continue
                    
                    # Evaluate rules against file
                    if await self._evaluate_rules_for_file(file_info, rules, logic):
                        # File matches rules, add to results
                        matching_files.append(self._create_file_result(file_info, rules))
                
                except Exception as e:
                    logger.debug(f"Error evaluating file {file_path}: {e}")
                    continue
            
            # Update statistics
            execution_time = time.time() - start_time
            self.evaluation_stats["total_evaluations"] += 1
            self.evaluation_stats["total_files_processed"] += len(files_to_evaluate)
            self.evaluation_stats["total_execution_time"] += execution_time
            
            logger.info(f"Rule evaluation completed: {len(matching_files)} matches from {len(files_to_evaluate)} files in {execution_time:.2f}s")
            
            return matching_files
            
        except Exception as e:
            logger.error(f"Rule evaluation failed: {e}")
            raise RuleEvaluationError(f"Failed to evaluate rules: {str(e)}")
    
    async def _get_files_to_evaluate(self, user_id: str) -> List[str]:
        """Get list of files to evaluate against rules"""
        
        # This is a simplified implementation
        # In a real system, this would query a file index or database
        # with proper permission checking
        
        files = []
        
        try:
            # For demo purposes, scan a limited directory structure
            # In production, use a proper file index
            base_paths = [
                "/tmp/activelog_demo/files",  # Demo files
                os.path.expanduser("~/Documents"),
                os.path.expanduser("~/Downloads")
            ]
            
            for base_path in base_paths:
                if os.path.exists(base_path):
                    for root, dirs, file_names in os.walk(base_path):
                        # Limit depth to avoid performance issues
                        level = root.replace(base_path, '').count(os.sep)
                        if level < 3:
                            for file_name in file_names[:100]:  # Limit files per directory
                                file_path = os.path.join(root, file_name)
                                if os.path.isfile(file_path):
                                    files.append(file_path)
            
            # Limit total files to avoid memory issues
            return files[:1000]
            
        except Exception as e:
            logger.error(f"Error getting files to evaluate: {e}")
            return []
    
    async def _evaluate_rules_for_file(self, file_info: FileInfo, 
                                     rules: List[Dict[str, Any]], logic: str) -> bool:
        """Evaluate all rules for a single file"""
        
        if not rules:
            return True
        
        results = []
        
        for rule in rules:
            try:
                result = await self._evaluate_single_rule(file_info, rule)
                results.append(result)
            except Exception as e:
                logger.debug(f"Error evaluating rule {rule}: {e}")
                results.append(False)
        
        # Apply logic
        if logic.upper() == "OR":
            return any(results)
        else:  # Default to AND
            return all(results)
    
    async def _evaluate_single_rule(self, file_info: FileInfo, rule: Dict[str, Any]) -> bool:
        """Evaluate a single rule against a file"""
        
        try:
            field = rule["condition_field"]
            operator = RuleOperator(rule["operator"])
            value = rule["value"]
            
            # Extract field value from file
            if field not in self.field_extractors:
                logger.warning(f"Unknown field: {field}")
                return False
            
            field_value = self.field_extractors[field](file_info)
            
            # Apply operator
            if operator not in self.operators:
                logger.warning(f"Unknown operator: {operator}")
                return False
            
            return self.operators[operator](field_value, value)
            
        except Exception as e:
            logger.debug(f"Error evaluating rule: {e}")
            return False
    
    def _create_file_result(self, file_info: FileInfo, matched_rules: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create file result dictionary"""
        
        return {
            "file_id": f"file_{hash(file_info.file_path)}",  # Simple file ID
            "file_path": file_info.file_path,
            "file_name": file_info.name,
            "file_size": file_info.size,
            "file_type": file_info.file_type,
            "mime_type": file_info.mime_type,
            "created_at": file_info.created_time.isoformat(),
            "modified_at": file_info.modified_time.isoformat(),
            "matched_rules": [rule.get("name", "unnamed") for rule in matched_rules],
            "match_score": 1.0  # Could implement more sophisticated scoring
        }
    
    # Operator implementations
    def _op_equals(self, field_value: Any, rule_value: Any) -> bool:
        """Equals operator"""
        return str(field_value).lower() == str(rule_value).lower()
    
    def _op_not_equals(self, field_value: Any, rule_value: Any) -> bool:
        """Not equals operator"""
        return not self._op_equals(field_value, rule_value)
    
    def _op_contains(self, field_value: Any, rule_value: Any) -> bool:
        """Contains operator"""
        return str(rule_value).lower() in str(field_value).lower()
    
    def _op_not_contains(self, field_value: Any, rule_value: Any) -> bool:
        """Not contains operator"""
        return not self._op_contains(field_value, rule_value)
    
    def _op_starts_with(self, field_value: Any, rule_value: Any) -> bool:
        """Starts with operator"""
        return str(field_value).lower().startswith(str(rule_value).lower())
    
    def _op_ends_with(self, field_value: Any, rule_value: Any) -> bool:
        """Ends with operator"""
        return str(field_value).lower().endswith(str(rule_value).lower())
    
    def _op_regex(self, field_value: Any, rule_value: Any) -> bool:
        """Regular expression operator"""
        try:
            pattern = re.compile(str(rule_value), re.IGNORECASE)
            return bool(pattern.search(str(field_value)))
        except re.error:
            logger.warning(f"Invalid regex pattern: {rule_value}")
            return False
    
    def _op_greater_than(self, field_value: Any, rule_value: Any) -> bool:
        """Greater than operator"""
        try:
            # Handle different data types
            if isinstance(field_value, datetime):
                if isinstance(rule_value, str):
                    rule_value = datetime.fromisoformat(rule_value.replace('Z', '+00:00'))
                return field_value > rule_value
            else:
                return float(field_value) > float(rule_value)
        except (ValueError, TypeError):
            return False
    
    def _op_less_than(self, field_value: Any, rule_value: Any) -> bool:
        """Less than operator"""
        try:
            if isinstance(field_value, datetime):
                if isinstance(rule_value, str):
                    rule_value = datetime.fromisoformat(rule_value.replace('Z', '+00:00'))
                return field_value < rule_value
            else:
                return float(field_value) < float(rule_value)
        except (ValueError, TypeError):
            return False
    
    def _op_between(self, field_value: Any, rule_value: Any) -> bool:
        """Between operator (expects rule_value to be [min, max])"""
        try:
            if not isinstance(rule_value, (list, tuple)) or len(rule_value) != 2:
                return False
            
            min_val, max_val = rule_value
            
            if isinstance(field_value, datetime):
                if isinstance(min_val, str):
                    min_val = datetime.fromisoformat(min_val.replace('Z', '+00:00'))
                if isinstance(max_val, str):
                    max_val = datetime.fromisoformat(max_val.replace('Z', '+00:00'))
                return min_val <= field_value <= max_val
            else:
                return float(min_val) <= float(field_value) <= float(max_val)
        except (ValueError, TypeError):
            return False
    
    def _op_in(self, field_value: Any, rule_value: Any) -> bool:
        """In operator (checks if field_value is in rule_value list)"""
        if not isinstance(rule_value, (list, tuple)):
            return False
        return str(field_value).lower() in [str(v).lower() for v in rule_value]
    
    def _op_not_in(self, field_value: Any, rule_value: Any) -> bool:
        """Not in operator"""
        return not self._op_in(field_value, rule_value)
    
    def _op_exists(self, field_value: Any, rule_value: Any) -> bool:
        """Exists operator (checks if field has a value)"""
        return field_value is not None and field_value != ""
    
    def _op_not_exists(self, field_value: Any, rule_value: Any) -> bool:
        """Not exists operator"""
        return not self._op_exists(field_value, rule_value)
    
    async def validate_rule(self, rule: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a rule definition"""
        
        errors = []
        warnings = []
        
        # Check required fields
        required_fields = ["condition_field", "operator", "value"]
        for field in required_fields:
            if field not in rule:
                errors.append(f"Missing required field: {field}")
        
        # Validate condition field
        if rule.get("condition_field") not in self.field_extractors:
            errors.append(f"Invalid condition field: {rule.get('condition_field')}")
        
        # Validate operator
        try:
            operator = RuleOperator(rule.get("operator"))
            if operator not in self.operators:
                errors.append(f"Unsupported operator: {rule.get('operator')}")
        except ValueError:
            errors.append(f"Invalid operator: {rule.get('operator')}")
        
        # Validate value format for specific operators
        operator = rule.get("operator")
        value = rule.get("value")
        
        if operator == "between" and not isinstance(value, (list, tuple)):
            errors.append("Between operator requires array value with [min, max]")
        
        if operator == "regex":
            try:
                re.compile(str(value))
            except re.error as e:
                errors.append(f"Invalid regex pattern: {str(e)}")
        
        if operator in ["in", "not_in"] and not isinstance(value, (list, tuple)):
            warnings.append("In/not_in operators work best with array values")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get rule engine performance statistics"""
        
        stats = self.evaluation_stats.copy()
        
        if stats["total_evaluations"] > 0:
            stats["average_execution_time"] = stats["total_execution_time"] / stats["total_evaluations"]
            stats["average_files_per_evaluation"] = stats["total_files_processed"] / stats["total_evaluations"]
        
        return stats
    
    async def cleanup(self):
        """Clean up rule engine resources"""
        logger.info("Rule engine cleaned up")