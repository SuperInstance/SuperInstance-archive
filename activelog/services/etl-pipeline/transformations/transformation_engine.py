"""
Data Transformation Engine
Comprehensive library for data transformations in ETL pipeline
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Callable, Union, Iterator
from datetime import datetime, timedelta
import json
import re
from dataclasses import dataclass, field
from enum import Enum
import pandas as pd
import numpy as np
from sqlalchemy import create_engine
import hashlib
import uuid
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import multiprocessing as mp

logger = logging.getLogger(__name__)

class TransformationType(str, Enum):
    CLEAN = "clean"
    VALIDATE = "validate"
    NORMALIZE = "normalize"
    AGGREGATE = "aggregate"
    ENRICH = "enrich"
    FILTER = "filter"
    MAP = "map"
    REDUCE = "reduce"
    JOIN = "join"
    SPLIT = "split"
    MERGE = "merge"
    PIVOT = "pivot"
    UNPIVOT = "unpivot"
    CUSTOM = "custom"

class DataType(str, Enum):
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATE = "date"
    DATETIME = "datetime"
    JSON = "json"
    ARRAY = "array"
    OBJECT = "object"

@dataclass
class TransformationRule:
    rule_id: str
    transformation_type: TransformationType
    source_fields: List[str]
    target_field: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    conditions: List[Dict[str, Any]] = field(default_factory=list)
    priority: int = 1  # 1=highest, 10=lowest
    enabled: bool = True
    description: str = ""

@dataclass
class TransformationResult:
    success: bool
    transformed_data: Any
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    execution_time: float = 0.0

class BaseTransformation(ABC):
    """Abstract base class for transformations"""
    
    def __init__(self, rule: TransformationRule):
        self.rule = rule
        self.stats = {
            'processed_records': 0,
            'failed_records': 0,
            'execution_times': []
        }
    
    @abstractmethod
    async def transform(self, data: Any) -> TransformationResult:
        """Apply transformation to data"""
        pass
    
    def validate_conditions(self, record: Dict[str, Any]) -> bool:
        """Check if record meets transformation conditions"""
        if not self.rule.conditions:
            return True
        
        for condition in self.rule.conditions:
            field = condition.get('field')
            operator = condition.get('operator')
            value = condition.get('value')
            
            if field not in record:
                return False
            
            record_value = record[field]
            
            if operator == 'equals' and record_value != value:
                return False
            elif operator == 'not_equals' and record_value == value:
                return False
            elif operator == 'greater_than' and record_value <= value:
                return False
            elif operator == 'less_than' and record_value >= value:
                return False
            elif operator == 'contains' and value not in str(record_value):
                return False
            elif operator == 'regex' and not re.match(value, str(record_value)):
                return False
        
        return True

class CleanTransformation(BaseTransformation):
    """Data cleaning transformations"""
    
    async def transform(self, data: Any) -> TransformationResult:
        start_time = datetime.utcnow()
        errors = []
        warnings = []
        
        try:
            if isinstance(data, dict):
                cleaned_data = await self._clean_record(data)
            elif isinstance(data, list):
                cleaned_data = []
                for record in data:
                    if isinstance(record, dict):
                        cleaned_record = await self._clean_record(record)
                        cleaned_data.append(cleaned_record)
                    else:
                        cleaned_data.append(record)
            else:
                cleaned_data = data
            
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            return TransformationResult(
                success=True,
                transformed_data=cleaned_data,
                errors=errors,
                warnings=warnings,
                execution_time=execution_time,
                metadata={'cleaning_rules_applied': len(self.rule.parameters)}
            )
            
        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            errors.append(str(e))
            
            return TransformationResult(
                success=False,
                transformed_data=data,
                errors=errors,
                execution_time=execution_time
            )
    
    async def _clean_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Clean individual record"""
        cleaned = record.copy()
        
        for field in self.rule.source_fields:
            if field not in cleaned:
                continue
            
            value = cleaned[field]
            
            # Apply cleaning operations
            if self.rule.parameters.get('trim_whitespace', True):
                if isinstance(value, str):
                    value = value.strip()
            
            if self.rule.parameters.get('remove_nulls', True):
                if value is None or value == '':
                    if self.rule.parameters.get('null_replacement'):
                        value = self.rule.parameters['null_replacement']
                    else:
                        del cleaned[field]
                        continue
            
            if self.rule.parameters.get('lowercase', False):
                if isinstance(value, str):
                    value = value.lower()
            
            if self.rule.parameters.get('uppercase', False):
                if isinstance(value, str):
                    value = value.upper()
            
            if self.rule.parameters.get('remove_duplicates', False):
                if isinstance(value, list):
                    value = list(dict.fromkeys(value))  # Preserve order
            
            if self.rule.parameters.get('regex_replace'):
                regex_config = self.rule.parameters['regex_replace']
                if isinstance(value, str):
                    value = re.sub(regex_config['pattern'], regex_config['replacement'], value)
            
            cleaned[field] = value
        
        return cleaned

class ValidateTransformation(BaseTransformation):
    """Data validation transformations"""
    
    async def transform(self, data: Any) -> TransformationResult:
        start_time = datetime.utcnow()
        errors = []
        warnings = []
        validation_results = []
        
        try:
            if isinstance(data, dict):
                validation_result = await self._validate_record(data)
                validation_results.append(validation_result)
            elif isinstance(data, list):
                for record in data:
                    if isinstance(record, dict):
                        validation_result = await self._validate_record(record)
                        validation_results.append(validation_result)
            
            # Aggregate validation results
            total_records = len(validation_results)
            valid_records = sum(1 for result in validation_results if result['is_valid'])
            invalid_records = total_records - valid_records
            
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            return TransformationResult(
                success=True,
                transformed_data=data,  # Validation doesn't modify data
                errors=errors,
                warnings=warnings,
                execution_time=execution_time,
                metadata={
                    'total_records': total_records,
                    'valid_records': valid_records,
                    'invalid_records': invalid_records,
                    'validation_results': validation_results
                }
            )
            
        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            errors.append(str(e))
            
            return TransformationResult(
                success=False,
                transformed_data=data,
                errors=errors,
                execution_time=execution_time
            )
    
    async def _validate_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Validate individual record"""
        validation_result = {
            'is_valid': True,
            'field_validations': {},
            'errors': []
        }
        
        for field in self.rule.source_fields:
            field_validation = await self._validate_field(field, record.get(field))
            validation_result['field_validations'][field] = field_validation
            
            if not field_validation['is_valid']:
                validation_result['is_valid'] = False
                validation_result['errors'].extend(field_validation['errors'])
        
        return validation_result
    
    async def _validate_field(self, field_name: str, value: Any) -> Dict[str, Any]:
        """Validate individual field"""
        validation_result = {
            'is_valid': True,
            'errors': []
        }
        
        field_rules = self.rule.parameters.get('field_rules', {}).get(field_name, {})
        
        # Required field validation
        if field_rules.get('required', False):
            if value is None or (isinstance(value, str) and value.strip() == ''):
                validation_result['is_valid'] = False
                validation_result['errors'].append(f"Field '{field_name}' is required")
                return validation_result
        
        if value is None:
            return validation_result  # Skip further validation for null values
        
        # Data type validation
        expected_type = field_rules.get('type')
        if expected_type:
            if not await self._validate_type(value, expected_type):
                validation_result['is_valid'] = False
                validation_result['errors'].append(f"Field '{field_name}' has invalid type. Expected: {expected_type}")
        
        # Length validation
        if 'min_length' in field_rules:
            if isinstance(value, str) and len(value) < field_rules['min_length']:
                validation_result['is_valid'] = False
                validation_result['errors'].append(f"Field '{field_name}' is too short")
        
        if 'max_length' in field_rules:
            if isinstance(value, str) and len(value) > field_rules['max_length']:
                validation_result['is_valid'] = False
                validation_result['errors'].append(f"Field '{field_name}' is too long")
        
        # Pattern validation
        if 'pattern' in field_rules:
            if isinstance(value, str) and not re.match(field_rules['pattern'], value):
                validation_result['is_valid'] = False
                validation_result['errors'].append(f"Field '{field_name}' doesn't match required pattern")
        
        # Range validation
        if 'min_value' in field_rules:
            if isinstance(value, (int, float)) and value < field_rules['min_value']:
                validation_result['is_valid'] = False
                validation_result['errors'].append(f"Field '{field_name}' is below minimum value")
        
        if 'max_value' in field_rules:
            if isinstance(value, (int, float)) and value > field_rules['max_value']:
                validation_result['is_valid'] = False
                validation_result['errors'].append(f"Field '{field_name}' is above maximum value")
        
        return validation_result
    
    async def _validate_type(self, value: Any, expected_type: str) -> bool:
        """Validate data type"""
        type_mapping = {
            'string': str,
            'integer': int,
            'float': (int, float),
            'boolean': bool,
            'list': list,
            'dict': dict
        }
        
        expected_python_type = type_mapping.get(expected_type.lower())
        if expected_python_type:
            return isinstance(value, expected_python_type)
        
        return True

class NormalizeTransformation(BaseTransformation):
    """Data normalization transformations"""
    
    async def transform(self, data: Any) -> TransformationResult:
        start_time = datetime.utcnow()
        errors = []
        warnings = []
        
        try:
            if isinstance(data, dict):
                normalized_data = await self._normalize_record(data)
            elif isinstance(data, list):
                normalized_data = []
                for record in data:
                    if isinstance(record, dict):
                        normalized_record = await self._normalize_record(record)
                        normalized_data.append(normalized_record)
                    else:
                        normalized_data.append(record)
            else:
                normalized_data = data
            
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            return TransformationResult(
                success=True,
                transformed_data=normalized_data,
                errors=errors,
                warnings=warnings,
                execution_time=execution_time,
                metadata={'normalization_rules_applied': len(self.rule.parameters)}
            )
            
        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            errors.append(str(e))
            
            return TransformationResult(
                success=False,
                transformed_data=data,
                errors=errors,
                execution_time=execution_time
            )
    
    async def _normalize_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize individual record"""
        normalized = record.copy()
        
        for field in self.rule.source_fields:
            if field not in normalized:
                continue
            
            value = normalized[field]
            normalization_type = self.rule.parameters.get('normalization_type', 'standard')
            
            if normalization_type == 'standard' and isinstance(value, (int, float)):
                # Standard normalization (z-score)
                mean = self.rule.parameters.get('mean', 0)
                std = self.rule.parameters.get('std', 1)
                normalized[field] = (value - mean) / std
            
            elif normalization_type == 'min_max' and isinstance(value, (int, float)):
                # Min-max normalization
                min_val = self.rule.parameters.get('min', 0)
                max_val = self.rule.parameters.get('max', 1)
                normalized[field] = (value - min_val) / (max_val - min_val)
            
            elif normalization_type == 'decimal_scaling' and isinstance(value, (int, float)):
                # Decimal scaling normalization
                max_abs = self.rule.parameters.get('max_abs', 1)
                j = len(str(int(max_abs)))
                normalized[field] = value / (10 ** j)
            
            elif normalization_type == 'text_case' and isinstance(value, str):
                case_type = self.rule.parameters.get('case', 'lower')
                if case_type == 'lower':
                    normalized[field] = value.lower()
                elif case_type == 'upper':
                    normalized[field] = value.upper()
                elif case_type == 'title':
                    normalized[field] = value.title()
        
        return normalized

class AggregateTransformation(BaseTransformation):
    """Data aggregation transformations"""
    
    async def transform(self, data: Any) -> TransformationResult:
        start_time = datetime.utcnow()
        errors = []
        warnings = []
        
        try:
            if not isinstance(data, list):
                errors.append("Aggregation requires list of records")
                return TransformationResult(
                    success=False,
                    transformed_data=data,
                    errors=errors,
                    execution_time=(datetime.utcnow() - start_time).total_seconds()
                )
            
            # Convert to DataFrame for easier aggregation
            df = pd.DataFrame(data)
            
            group_by_fields = self.rule.parameters.get('group_by', [])
            aggregation_functions = self.rule.parameters.get('functions', {})
            
            if group_by_fields:
                # Group by aggregation
                grouped = df.groupby(group_by_fields)
                aggregated_df = grouped.agg(aggregation_functions).reset_index()
            else:
                # Global aggregation
                aggregated_values = {}
                for field, functions in aggregation_functions.items():
                    if isinstance(functions, str):
                        functions = [functions]
                    
                    for func in functions:
                        if func == 'count':
                            aggregated_values[f"{field}_{func}"] = len(df[field])
                        elif func == 'sum':
                            aggregated_values[f"{field}_{func}"] = df[field].sum()
                        elif func == 'mean':
                            aggregated_values[f"{field}_{func}"] = df[field].mean()
                        elif func == 'median':
                            aggregated_values[f"{field}_{func}"] = df[field].median()
                        elif func == 'min':
                            aggregated_values[f"{field}_{func}"] = df[field].min()
                        elif func == 'max':
                            aggregated_values[f"{field}_{func}"] = df[field].max()
                        elif func == 'std':
                            aggregated_values[f"{field}_{func}"] = df[field].std()
                
                aggregated_df = pd.DataFrame([aggregated_values])
            
            # Convert back to list of dictionaries
            aggregated_data = aggregated_df.to_dict('records')
            
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            return TransformationResult(
                success=True,
                transformed_data=aggregated_data,
                errors=errors,
                warnings=warnings,
                execution_time=execution_time,
                metadata={
                    'input_records': len(data),
                    'output_records': len(aggregated_data),
                    'group_by_fields': group_by_fields
                }
            )
            
        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            errors.append(str(e))
            
            return TransformationResult(
                success=False,
                transformed_data=data,
                errors=errors,
                execution_time=execution_time
            )

class EnrichTransformation(BaseTransformation):
    """Data enrichment transformations"""
    
    async def transform(self, data: Any) -> TransformationResult:
        start_time = datetime.utcnow()
        errors = []
        warnings = []
        
        try:
            if isinstance(data, dict):
                enriched_data = await self._enrich_record(data)
            elif isinstance(data, list):
                enriched_data = []
                for record in data:
                    if isinstance(record, dict):
                        enriched_record = await self._enrich_record(record)
                        enriched_data.append(enriched_record)
                    else:
                        enriched_data.append(record)
            else:
                enriched_data = data
            
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            return TransformationResult(
                success=True,
                transformed_data=enriched_data,
                errors=errors,
                warnings=warnings,
                execution_time=execution_time,
                metadata={'enrichment_fields_added': len(self.rule.parameters.get('enrichment_rules', {}))}
            )
            
        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            errors.append(str(e))
            
            return TransformationResult(
                success=False,
                transformed_data=data,
                errors=errors,
                execution_time=execution_time
            )
    
    async def _enrich_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich individual record"""
        enriched = record.copy()
        
        enrichment_rules = self.rule.parameters.get('enrichment_rules', {})
        
        for new_field, rule_config in enrichment_rules.items():
            rule_type = rule_config.get('type', 'static')
            
            if rule_type == 'static':
                # Add static value
                enriched[new_field] = rule_config.get('value')
            
            elif rule_type == 'computed':
                # Compute value from existing fields
                expression = rule_config.get('expression', '')
                try:
                    # Simple expression evaluation (be careful with security!)
                    enriched[new_field] = eval(expression, {"__builtins__": {}}, enriched)
                except Exception as e:
                    logger.warning(f"Failed to compute field {new_field}: {e}")
            
            elif rule_type == 'lookup':
                # Lookup value from external source
                lookup_table = rule_config.get('lookup_table', {})
                lookup_key = rule_config.get('lookup_key', '')
                if lookup_key in enriched:
                    key_value = enriched[lookup_key]
                    enriched[new_field] = lookup_table.get(key_value, rule_config.get('default'))
            
            elif rule_type == 'timestamp':
                # Add timestamp
                enriched[new_field] = datetime.utcnow().isoformat()
            
            elif rule_type == 'uuid':
                # Add UUID
                enriched[new_field] = str(uuid.uuid4())
            
            elif rule_type == 'hash':
                # Add hash of specified fields
                hash_fields = rule_config.get('hash_fields', [])
                hash_input = ''.join(str(enriched.get(field, '')) for field in hash_fields)
                enriched[new_field] = hashlib.md5(hash_input.encode()).hexdigest()
        
        return enriched

class CustomTransformation(BaseTransformation):
    """Custom transformation with user-defined function"""
    
    def __init__(self, rule: TransformationRule, custom_function: Callable = None):
        super().__init__(rule)
        self.custom_function = custom_function
    
    async def transform(self, data: Any) -> TransformationResult:
        start_time = datetime.utcnow()
        errors = []
        warnings = []
        
        try:
            if not self.custom_function:
                errors.append("No custom function provided")
                return TransformationResult(
                    success=False,
                    transformed_data=data,
                    errors=errors,
                    execution_time=(datetime.utcnow() - start_time).total_seconds()
                )
            
            # Execute custom function
            if asyncio.iscoroutinefunction(self.custom_function):
                transformed_data = await self.custom_function(data, self.rule.parameters)
            else:
                transformed_data = self.custom_function(data, self.rule.parameters)
            
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            return TransformationResult(
                success=True,
                transformed_data=transformed_data,
                errors=errors,
                warnings=warnings,
                execution_time=execution_time,
                metadata={'custom_function': self.custom_function.__name__ if hasattr(self.custom_function, '__name__') else 'anonymous'}
            )
            
        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            errors.append(str(e))
            
            return TransformationResult(
                success=False,
                transformed_data=data,
                errors=errors,
                execution_time=execution_time
            )

class TransformationEngine:
    """Main transformation engine orchestrating all transformations"""
    
    def __init__(self, max_workers: int = None):
        self.transformations = {}
        self.execution_stats = {}
        self.max_workers = max_workers or mp.cpu_count()
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
        
        # Register built-in transformations
        self._register_builtin_transformations()
    
    def _register_builtin_transformations(self):
        """Register built-in transformation types"""
        self.transformation_classes = {
            TransformationType.CLEAN: CleanTransformation,
            TransformationType.VALIDATE: ValidateTransformation,
            TransformationType.NORMALIZE: NormalizeTransformation,
            TransformationType.AGGREGATE: AggregateTransformation,
            TransformationType.ENRICH: EnrichTransformation,
            TransformationType.CUSTOM: CustomTransformation
        }
    
    def register_transformation(self, transformation_rule: TransformationRule, custom_function: Callable = None):
        """Register a transformation rule"""
        transformation_class = self.transformation_classes.get(transformation_rule.transformation_type)
        
        if not transformation_class:
            raise ValueError(f"Unsupported transformation type: {transformation_rule.transformation_type}")
        
        if transformation_rule.transformation_type == TransformationType.CUSTOM:
            transformation = transformation_class(transformation_rule, custom_function)
        else:
            transformation = transformation_class(transformation_rule)
        
        self.transformations[transformation_rule.rule_id] = transformation
        logger.info(f"Registered transformation: {transformation_rule.rule_id}")
    
    async def apply_transformation(self, rule_id: str, data: Any) -> TransformationResult:
        """Apply specific transformation to data"""
        if rule_id not in self.transformations:
            return TransformationResult(
                success=False,
                transformed_data=data,
                errors=[f"Transformation rule '{rule_id}' not found"]
            )
        
        transformation = self.transformations[rule_id]
        
        if not transformation.rule.enabled:
            return TransformationResult(
                success=True,
                transformed_data=data,
                warnings=[f"Transformation rule '{rule_id}' is disabled"]
            )
        
        result = await transformation.transform(data)
        
        # Update stats
        self._update_stats(rule_id, result)
        
        return result
    
    async def apply_transformation_pipeline(self, rule_ids: List[str], data: Any) -> TransformationResult:
        """Apply multiple transformations in sequence"""
        current_data = data
        all_errors = []
        all_warnings = []
        total_execution_time = 0.0
        pipeline_metadata = []
        
        # Sort by priority
        sorted_rules = sorted(
            [(rule_id, self.transformations[rule_id].rule.priority) for rule_id in rule_ids if rule_id in self.transformations],
            key=lambda x: x[1]
        )
        
        for rule_id, _ in sorted_rules:
            result = await self.apply_transformation(rule_id, current_data)
            
            if result.success:
                current_data = result.transformed_data
            else:
                # Decide whether to continue or stop on error
                continue_on_error = self.transformations[rule_id].rule.parameters.get('continue_on_error', True)
                if not continue_on_error:
                    return TransformationResult(
                        success=False,
                        transformed_data=current_data,
                        errors=all_errors + result.errors,
                        warnings=all_warnings + result.warnings,
                        execution_time=total_execution_time + result.execution_time,
                        metadata={'pipeline_stopped_at': rule_id, 'completed_stages': pipeline_metadata}
                    )
            
            all_errors.extend(result.errors)
            all_warnings.extend(result.warnings)
            total_execution_time += result.execution_time
            
            pipeline_metadata.append({
                'rule_id': rule_id,
                'success': result.success,
                'execution_time': result.execution_time,
                'metadata': result.metadata
            })
        
        return TransformationResult(
            success=len(all_errors) == 0,
            transformed_data=current_data,
            errors=all_errors,
            warnings=all_warnings,
            execution_time=total_execution_time,
            metadata={'pipeline_stages': pipeline_metadata}
        )
    
    async def apply_parallel_transformations(self, transformations_config: Dict[str, Any], data: Any) -> Dict[str, TransformationResult]:
        """Apply multiple transformations in parallel"""
        tasks = {}
        
        for rule_id, config in transformations_config.items():
            if rule_id in self.transformations:
                # Create copy of data for each transformation
                data_copy = json.loads(json.dumps(data)) if isinstance(data, (dict, list)) else data
                task = asyncio.create_task(self.apply_transformation(rule_id, data_copy))
                tasks[rule_id] = task
        
        results = {}
        for rule_id, task in tasks.items():
            try:
                result = await task
                results[rule_id] = result
            except Exception as e:
                results[rule_id] = TransformationResult(
                    success=False,
                    transformed_data=data,
                    errors=[str(e)]
                )
        
        return results
    
    def _update_stats(self, rule_id: str, result: TransformationResult):
        """Update execution statistics"""
        if rule_id not in self.execution_stats:
            self.execution_stats[rule_id] = {
                'total_executions': 0,
                'successful_executions': 0,
                'failed_executions': 0,
                'total_execution_time': 0.0,
                'average_execution_time': 0.0
            }
        
        stats = self.execution_stats[rule_id]
        stats['total_executions'] += 1
        stats['total_execution_time'] += result.execution_time
        
        if result.success:
            stats['successful_executions'] += 1
        else:
            stats['failed_executions'] += 1
        
        stats['average_execution_time'] = stats['total_execution_time'] / stats['total_executions']
    
    def get_transformation_stats(self) -> Dict[str, Any]:
        """Get execution statistics for all transformations"""
        return self.execution_stats.copy()
    
    def get_registered_transformations(self) -> List[str]:
        """Get list of registered transformation rule IDs"""
        return list(self.transformations.keys())
    
    def remove_transformation(self, rule_id: str) -> bool:
        """Remove a transformation rule"""
        if rule_id in self.transformations:
            del self.transformations[rule_id]
            if rule_id in self.execution_stats:
                del self.execution_stats[rule_id]
            return True
        return False
    
    def clear_transformations(self):
        """Clear all registered transformations"""
        self.transformations.clear()
        self.execution_stats.clear()
    
    async def shutdown(self):
        """Shutdown the transformation engine"""
        self.executor.shutdown(wait=True)
        logger.info("Transformation engine shutdown completed")

# Example transformation rules
SAMPLE_TRANSFORMATION_RULES = [
    TransformationRule(
        rule_id="clean_user_data",
        transformation_type=TransformationType.CLEAN,
        source_fields=["name", "email", "phone"],
        target_field="cleaned_user_data",
        parameters={
            "trim_whitespace": True,
            "remove_nulls": True,
            "lowercase": True
        },
        description="Clean user data by trimming whitespace and converting to lowercase"
    ),
    
    TransformationRule(
        rule_id="validate_email",
        transformation_type=TransformationType.VALIDATE,
        source_fields=["email"],
        target_field="email_validation",
        parameters={
            "field_rules": {
                "email": {
                    "required": True,
                    "type": "string",
                    "pattern": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
                }
            }
        },
        description="Validate email format"
    ),
    
    TransformationRule(
        rule_id="normalize_scores",
        transformation_type=TransformationType.NORMALIZE,
        source_fields=["score"],
        target_field="normalized_score",
        parameters={
            "normalization_type": "min_max",
            "min": 0,
            "max": 100
        },
        description="Normalize scores to 0-1 range"
    ),
    
    TransformationRule(
        rule_id="aggregate_sales",
        transformation_type=TransformationType.AGGREGATE,
        source_fields=["region", "sales_amount"],
        target_field="aggregated_sales",
        parameters={
            "group_by": ["region"],
            "functions": {
                "sales_amount": ["sum", "mean", "count"]
            }
        },
        description="Aggregate sales data by region"
    ),
    
    TransformationRule(
        rule_id="enrich_with_metadata",
        transformation_type=TransformationType.ENRICH,
        source_fields=["user_id"],
        target_field="enriched_data",
        parameters={
            "enrichment_rules": {
                "processed_at": {"type": "timestamp"},
                "record_id": {"type": "uuid"},
                "user_hash": {
                    "type": "hash",
                    "hash_fields": ["user_id", "email"]
                }
            }
        },
        description="Enrich data with timestamps and generated IDs"
    )
]

def get_sample_transformation_rules() -> List[TransformationRule]:
    """Get sample transformation rules for testing"""
    return SAMPLE_TRANSFORMATION_RULES