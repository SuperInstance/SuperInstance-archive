"""
Data Transformation Pipelines for Integration Controller

Provides comprehensive data transformation capabilities including:
- Multi-stage data processing pipelines
- Schema validation and transformation
- Data format conversions (JSON, XML, CSV, Avro, Protobuf)
- Field mapping and enrichment
- Data validation and cleansing
- Real-time and batch processing modes
- Error handling and data quality monitoring
- Custom transformation functions
"""

import asyncio
import json
import csv
import xml.etree.ElementTree as ET
import sqlite3
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Union, Tuple
from concurrent.futures import ThreadPoolExecutor
import logging
import re
from io import StringIO, BytesIO
import base64

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PipelineStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"

class ProcessingMode(Enum):
    REAL_TIME = "real_time"
    BATCH = "batch"
    STREAM = "stream"

class DataFormat(Enum):
    JSON = "json"
    XML = "xml"
    CSV = "csv"
    YAML = "yaml"
    AVRO = "avro"
    PROTOBUF = "protobuf"
    BINARY = "binary"
    TEXT = "text"

class ValidationLevel(Enum):
    NONE = "none"
    BASIC = "basic"
    STRICT = "strict"
    CUSTOM = "custom"

@dataclass
class TransformationStep:
    """Individual transformation step in a pipeline"""
    step_id: str
    name: str
    step_type: str
    config: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    order: int = 0
    error_handling: str = "fail"  # fail, skip, retry
    retry_count: int = 3
    timeout: int = 30
    condition: Optional[str] = None

@dataclass
class DataSchema:
    """Data schema definition for validation"""
    schema_id: str
    name: str
    version: str
    format: DataFormat
    definition: Dict[str, Any] = field(default_factory=dict)
    required_fields: List[str] = field(default_factory=list)
    optional_fields: List[str] = field(default_factory=list)
    validation_rules: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Pipeline:
    """Data transformation pipeline definition"""
    pipeline_id: str
    name: str
    description: str
    steps: List[TransformationStep] = field(default_factory=list)
    input_schema: Optional[DataSchema] = None
    output_schema: Optional[DataSchema] = None
    processing_mode: ProcessingMode = ProcessingMode.REAL_TIME
    batch_size: int = 100
    max_parallel: int = 5
    timeout: int = 300
    error_threshold: float = 0.1  # Fail if error rate > 10%
    status: PipelineStatus = PipelineStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ProcessingResult:
    """Result of data processing"""
    success: bool
    input_data: Any
    output_data: Any = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    processing_time: float = 0.0
    step_results: Dict[str, Any] = field(default_factory=dict)

class DataValidator:
    """Data validation utilities"""
    
    @staticmethod
    def validate_json_schema(data: Dict[str, Any], schema_def: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate data against JSON schema"""
        errors = []
        
        # Basic type checking
        if "type" in schema_def:
            expected_type = schema_def["type"]
            if expected_type == "object" and not isinstance(data, dict):
                errors.append(f"Expected object, got {type(data).__name__}")
            elif expected_type == "array" and not isinstance(data, list):
                errors.append(f"Expected array, got {type(data).__name__}")
            elif expected_type == "string" and not isinstance(data, str):
                errors.append(f"Expected string, got {type(data).__name__}")
            elif expected_type == "number" and not isinstance(data, (int, float)):
                errors.append(f"Expected number, got {type(data).__name__}")
            elif expected_type == "boolean" and not isinstance(data, bool):
                errors.append(f"Expected boolean, got {type(data).__name__}")
        
        # Required fields
        if "required" in schema_def and isinstance(data, dict):
            for field in schema_def["required"]:
                if field not in data:
                    errors.append(f"Required field '{field}' is missing")
        
        # Properties validation
        if "properties" in schema_def and isinstance(data, dict):
            for field, field_schema in schema_def["properties"].items():
                if field in data:
                    field_valid, field_errors = DataValidator.validate_json_schema(data[field], field_schema)
                    if not field_valid:
                        errors.extend([f"Field '{field}': {error}" for error in field_errors])
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_data_format(data: str, format_type: DataFormat) -> Tuple[bool, List[str]]:
        """Validate data format"""
        errors = []
        
        try:
            if format_type == DataFormat.JSON:
                json.loads(data)
            elif format_type == DataFormat.XML:
                ET.fromstring(data)
            elif format_type == DataFormat.CSV:
                csv.reader(StringIO(data))
            # Add more format validations as needed
            
        except Exception as e:
            errors.append(f"Invalid {format_type.value} format: {str(e)}")
        
        return len(errors) == 0, errors

class DataConverter:
    """Data format conversion utilities"""
    
    @staticmethod
    def convert_format(data: Any, from_format: DataFormat, to_format: DataFormat) -> Any:
        """Convert data between formats"""
        if from_format == to_format:
            return data
        
        # Convert to intermediate JSON format first
        if from_format != DataFormat.JSON:
            data = DataConverter._to_json(data, from_format)
        
        # Convert from JSON to target format
        if to_format != DataFormat.JSON:
            data = DataConverter._from_json(data, to_format)
        
        return data
    
    @staticmethod
    def _to_json(data: Any, from_format: DataFormat) -> Dict[str, Any]:
        """Convert various formats to JSON"""
        if from_format == DataFormat.XML:
            return DataConverter._xml_to_json(data)
        elif from_format == DataFormat.CSV:
            return DataConverter._csv_to_json(data)
        elif from_format == DataFormat.TEXT:
            return {"text": data}
        else:
            return data
    
    @staticmethod
    def _from_json(data: Dict[str, Any], to_format: DataFormat) -> Any:
        """Convert JSON to various formats"""
        if to_format == DataFormat.XML:
            return DataConverter._json_to_xml(data)
        elif to_format == DataFormat.CSV:
            return DataConverter._json_to_csv(data)
        elif to_format == DataFormat.TEXT:
            return str(data)
        else:
            return data
    
    @staticmethod
    def _xml_to_json(xml_data: str) -> Dict[str, Any]:
        """Convert XML to JSON"""
        def xml_element_to_dict(element):
            result = {}
            
            # Add attributes
            if element.attrib:
                result["@attributes"] = element.attrib
            
            # Add text content
            if element.text and element.text.strip():
                result["text"] = element.text.strip()
            
            # Add child elements
            for child in element:
                child_data = xml_element_to_dict(child)
                if child.tag in result:
                    # Multiple elements with same tag - create array
                    if not isinstance(result[child.tag], list):
                        result[child.tag] = [result[child.tag]]
                    result[child.tag].append(child_data)
                else:
                    result[child.tag] = child_data
            
            return result
        
        root = ET.fromstring(xml_data)
        return {root.tag: xml_element_to_dict(root)}
    
    @staticmethod
    def _json_to_xml(json_data: Dict[str, Any], root_name: str = "root") -> str:
        """Convert JSON to XML"""
        def dict_to_xml_element(data, tag_name):
            element = ET.Element(tag_name)
            
            if isinstance(data, dict):
                for key, value in data.items():
                    if key == "@attributes":
                        element.attrib.update(value)
                    elif key == "text":
                        element.text = str(value)
                    else:
                        if isinstance(value, list):
                            for item in value:
                                child = dict_to_xml_element(item, key)
                                element.append(child)
                        else:
                            child = dict_to_xml_element(value, key)
                            element.append(child)
            else:
                element.text = str(data)
            
            return element
        
        root = dict_to_xml_element(json_data, root_name)
        return ET.tostring(root, encoding='unicode')
    
    @staticmethod
    def _csv_to_json(csv_data: str) -> List[Dict[str, Any]]:
        """Convert CSV to JSON array"""
        reader = csv.DictReader(StringIO(csv_data))
        return list(reader)
    
    @staticmethod
    def _json_to_csv(json_data: Union[List[Dict], Dict]) -> str:
        """Convert JSON to CSV"""
        if isinstance(json_data, dict):
            json_data = [json_data]
        
        if not json_data:
            return ""
        
        output = StringIO()
        fieldnames = json_data[0].keys()
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        
        writer.writeheader()
        writer.writerows(json_data)
        
        return output.getvalue()

class FieldMapper:
    """Field mapping and transformation utilities"""
    
    @staticmethod
    def apply_field_mapping(data: Dict[str, Any], mapping_config: Dict[str, Any]) -> Dict[str, Any]:
        """Apply field mapping configuration to data"""
        result = {}
        
        for target_field, mapping_rule in mapping_config.items():
            if isinstance(mapping_rule, str):
                # Simple field mapping
                if mapping_rule in data:
                    result[target_field] = data[mapping_rule]
            elif isinstance(mapping_rule, dict):
                # Complex mapping rule
                if "source" in mapping_rule:
                    source_value = FieldMapper._get_nested_value(data, mapping_rule["source"])
                    
                    # Apply transformation if specified
                    if "transform" in mapping_rule:
                        source_value = FieldMapper._apply_transform(source_value, mapping_rule["transform"])
                    
                    # Apply default value if source is None
                    if source_value is None and "default" in mapping_rule:
                        source_value = mapping_rule["default"]
                    
                    result[target_field] = source_value
                elif "constant" in mapping_rule:
                    # Constant value
                    result[target_field] = mapping_rule["constant"]
                elif "expression" in mapping_rule:
                    # Expression evaluation
                    result[target_field] = FieldMapper._evaluate_expression(
                        mapping_rule["expression"], data
                    )
        
        return result
    
    @staticmethod
    def _get_nested_value(data: Dict[str, Any], path: str) -> Any:
        """Get value from nested dictionary using dot notation"""
        keys = path.split('.')
        current = data
        
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            elif isinstance(current, list) and key.isdigit():
                index = int(key)
                if 0 <= index < len(current):
                    current = current[index]
                else:
                    return None
            else:
                return None
        
        return current
    
    @staticmethod
    def _apply_transform(value: Any, transform_config: Dict[str, Any]) -> Any:
        """Apply transformation to value"""
        if value is None:
            return None
        
        transform_type = transform_config.get("type")
        
        if transform_type == "upper":
            return str(value).upper()
        elif transform_type == "lower":
            return str(value).lower()
        elif transform_type == "regex":
            pattern = transform_config.get("pattern", "")
            replacement = transform_config.get("replacement", "")
            return re.sub(pattern, replacement, str(value))
        elif transform_type == "format":
            format_string = transform_config.get("format", "{}")
            return format_string.format(value)
        elif transform_type == "cast":
            cast_type = transform_config.get("target_type", "str")
            if cast_type == "int":
                return int(float(value))
            elif cast_type == "float":
                return float(value)
            elif cast_type == "str":
                return str(value)
            elif cast_type == "bool":
                return bool(value)
        
        return value
    
    @staticmethod
    def _evaluate_expression(expression: str, context: Dict[str, Any]) -> Any:
        """Evaluate simple expression with context"""
        try:
            # Simple expression evaluation (can be extended)
            return eval(expression, {"__builtins__": {}}, context)
        except Exception as e:
            logger.warning(f"Failed to evaluate expression '{expression}': {e}")
            return None

class TransformationEngine:
    """Engine for executing transformation steps"""
    
    def __init__(self):
        self.step_handlers = {
            "validate": self._validate_step,
            "convert": self._convert_step,
            "map_fields": self._map_fields_step,
            "filter": self._filter_step,
            "enrich": self._enrich_step,
            "aggregate": self._aggregate_step,
            "split": self._split_step,
            "merge": self._merge_step,
            "custom": self._custom_step
        }
    
    async def execute_step(self, step: TransformationStep, data: Any, context: Dict[str, Any]) -> ProcessingResult:
        """Execute a single transformation step"""
        start_time = time.time()
        result = ProcessingResult(success=False, input_data=data)
        
        try:
            # Check condition if specified
            if step.condition and not self._evaluate_condition(step.condition, data, context):
                result.success = True
                result.output_data = data
                result.warnings.append(f"Step {step.step_id} skipped due to condition")
                return result
            
            # Execute step
            handler = self.step_handlers.get(step.step_type)
            if not handler:
                raise ValueError(f"Unknown step type: {step.step_type}")
            
            result.output_data = await handler(step, data, context)
            result.success = True
            
        except Exception as e:
            error_msg = f"Step {step.step_id} failed: {str(e)}"
            result.errors.append(error_msg)
            
            if step.error_handling == "skip":
                result.success = True
                result.output_data = data
                result.warnings.append(f"Step {step.step_id} skipped due to error")
            elif step.error_handling == "retry" and step.retry_count > 0:
                # Implement retry logic
                for attempt in range(step.retry_count):
                    try:
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff
                        result.output_data = await handler(step, data, context)
                        result.success = True
                        break
                    except Exception as retry_error:
                        if attempt == step.retry_count - 1:
                            result.errors.append(f"Step {step.step_id} failed after {step.retry_count} retries: {str(retry_error)}")
        
        result.processing_time = time.time() - start_time
        return result
    
    def _evaluate_condition(self, condition: str, data: Any, context: Dict[str, Any]) -> bool:
        """Evaluate step condition"""
        try:
            eval_context = {"data": data, **context}
            return eval(condition, {"__builtins__": {}}, eval_context)
        except Exception as e:
            logger.warning(f"Failed to evaluate condition '{condition}': {e}")
            return True
    
    async def _validate_step(self, step: TransformationStep, data: Any, context: Dict[str, Any]) -> Any:
        """Validation step"""
        config = step.config
        validation_type = config.get("type", "schema")
        
        if validation_type == "schema":
            schema_def = config.get("schema", {})
            if isinstance(data, dict):
                valid, errors = DataValidator.validate_json_schema(data, schema_def)
                if not valid:
                    raise ValueError(f"Schema validation failed: {', '.join(errors)}")
        elif validation_type == "format":
            format_type = DataFormat(config.get("format", "json"))
            if isinstance(data, str):
                valid, errors = DataValidator.validate_data_format(data, format_type)
                if not valid:
                    raise ValueError(f"Format validation failed: {', '.join(errors)}")
        
        return data
    
    async def _convert_step(self, step: TransformationStep, data: Any, context: Dict[str, Any]) -> Any:
        """Format conversion step"""
        config = step.config
        from_format = DataFormat(config.get("from", "json"))
        to_format = DataFormat(config.get("to", "json"))
        
        return DataConverter.convert_format(data, from_format, to_format)
    
    async def _map_fields_step(self, step: TransformationStep, data: Any, context: Dict[str, Any]) -> Any:
        """Field mapping step"""
        config = step.config
        mapping = config.get("mapping", {})
        
        if isinstance(data, dict):
            return FieldMapper.apply_field_mapping(data, mapping)
        elif isinstance(data, list):
            return [FieldMapper.apply_field_mapping(item, mapping) if isinstance(item, dict) else item for item in data]
        else:
            return data
    
    async def _filter_step(self, step: TransformationStep, data: Any, context: Dict[str, Any]) -> Any:
        """Data filtering step"""
        config = step.config
        filter_expr = config.get("expression", "True")
        
        if isinstance(data, list):
            filtered = []
            for item in data:
                try:
                    if eval(filter_expr, {"__builtins__": {}}, {"item": item, **context}):
                        filtered.append(item)
                except Exception as e:
                    logger.warning(f"Filter expression failed for item: {e}")
            return filtered
        else:
            try:
                if eval(filter_expr, {"__builtins__": {}}, {"data": data, **context}):
                    return data
                else:
                    return None
            except Exception as e:
                logger.warning(f"Filter expression failed: {e}")
                return data
    
    async def _enrich_step(self, step: TransformationStep, data: Any, context: Dict[str, Any]) -> Any:
        """Data enrichment step"""
        config = step.config
        enrichments = config.get("enrichments", {})
        
        if isinstance(data, dict):
            enriched = data.copy()
            for field, value_config in enrichments.items():
                if isinstance(value_config, dict):
                    if "constant" in value_config:
                        enriched[field] = value_config["constant"]
                    elif "expression" in value_config:
                        try:
                            enriched[field] = eval(
                                value_config["expression"],
                                {"__builtins__": {}},
                                {"data": data, **context}
                            )
                        except Exception as e:
                            logger.warning(f"Enrichment expression failed for field {field}: {e}")
                else:
                    enriched[field] = value_config
            return enriched
        
        return data
    
    async def _aggregate_step(self, step: TransformationStep, data: Any, context: Dict[str, Any]) -> Any:
        """Data aggregation step"""
        config = step.config
        
        if not isinstance(data, list):
            return data
        
        agg_type = config.get("type", "count")
        group_by = config.get("group_by")
        
        if group_by:
            # Group by field aggregation
            groups = {}
            for item in data:
                if isinstance(item, dict) and group_by in item:
                    key = item[group_by]
                    if key not in groups:
                        groups[key] = []
                    groups[key].append(item)
            
            result = []
            for group_key, group_items in groups.items():
                agg_result = {"group": group_key}
                
                if agg_type == "count":
                    agg_result["count"] = len(group_items)
                elif agg_type == "sum":
                    sum_field = config.get("field")
                    if sum_field:
                        agg_result["sum"] = sum(
                            item.get(sum_field, 0) for item in group_items
                            if isinstance(item.get(sum_field), (int, float))
                        )
                
                result.append(agg_result)
            
            return result
        else:
            # Simple aggregation
            if agg_type == "count":
                return {"count": len(data)}
            elif agg_type == "sum":
                sum_field = config.get("field")
                if sum_field:
                    return {
                        "sum": sum(
                            item.get(sum_field, 0) for item in data
                            if isinstance(item, dict) and isinstance(item.get(sum_field), (int, float))
                        )
                    }
        
        return data
    
    async def _split_step(self, step: TransformationStep, data: Any, context: Dict[str, Any]) -> Any:
        """Data splitting step"""
        config = step.config
        
        if isinstance(data, dict):
            split_field = config.get("field")
            delimiter = config.get("delimiter", ",")
            
            if split_field and split_field in data:
                value = data[split_field]
                if isinstance(value, str):
                    data[split_field] = value.split(delimiter)
        
        return data
    
    async def _merge_step(self, step: TransformationStep, data: Any, context: Dict[str, Any]) -> Any:
        """Data merging step"""
        config = step.config
        merge_source = config.get("source")
        
        if merge_source and merge_source in context:
            merge_data = context[merge_source]
            
            if isinstance(data, dict) and isinstance(merge_data, dict):
                merged = data.copy()
                merged.update(merge_data)
                return merged
        
        return data
    
    async def _custom_step(self, step: TransformationStep, data: Any, context: Dict[str, Any]) -> Any:
        """Custom transformation step"""
        config = step.config
        function_name = config.get("function")
        
        # This would integrate with a custom function registry
        # For now, return data unchanged
        logger.warning(f"Custom step {function_name} not implemented")
        return data

class PipelineEngine:
    """Main pipeline execution engine"""
    
    def __init__(self):
        self.transformation_engine = TransformationEngine()
        self.active_pipelines: Dict[str, Pipeline] = {}
        self.thread_pool = ThreadPoolExecutor(max_workers=10)
    
    async def execute_pipeline(self, pipeline: Pipeline, data: Any, context: Dict[str, Any] = None) -> ProcessingResult:
        """Execute a complete transformation pipeline"""
        if context is None:
            context = {}
        
        pipeline.status = PipelineStatus.RUNNING
        start_time = time.time()
        
        result = ProcessingResult(success=True, input_data=data, output_data=data)
        current_data = data
        
        # Sort steps by order
        sorted_steps = sorted([s for s in pipeline.steps if s.enabled], key=lambda x: x.order)
        
        try:
            for step in sorted_steps:
                step_result = await self.transformation_engine.execute_step(step, current_data, context)
                
                result.step_results[step.step_id] = {
                    "success": step_result.success,
                    "processing_time": step_result.processing_time,
                    "errors": step_result.errors,
                    "warnings": step_result.warnings
                }
                
                if not step_result.success:
                    result.success = False
                    result.errors.extend(step_result.errors)
                    break
                
                result.warnings.extend(step_result.warnings)
                current_data = step_result.output_data
                
                # Update context with step results
                context[f"step_{step.step_id}_result"] = step_result.output_data
            
            result.output_data = current_data
            pipeline.status = PipelineStatus.COMPLETED if result.success else PipelineStatus.FAILED
            
        except Exception as e:
            result.success = False
            result.errors.append(f"Pipeline execution failed: {str(e)}")
            pipeline.status = PipelineStatus.FAILED
        
        result.processing_time = time.time() - start_time
        
        logger.info(f"Pipeline {pipeline.pipeline_id} completed with status {pipeline.status.value}")
        return result
    
    async def execute_batch(self, pipeline: Pipeline, data_batch: List[Any], context: Dict[str, Any] = None) -> List[ProcessingResult]:
        """Execute pipeline on a batch of data"""
        if context is None:
            context = {}
        
        # Process in parallel up to max_parallel
        semaphore = asyncio.Semaphore(pipeline.max_parallel)
        
        async def process_item(item):
            async with semaphore:
                return await self.execute_pipeline(pipeline, item, context.copy())
        
        # Create tasks for all items
        tasks = [process_item(item) for item in data_batch]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Convert exceptions to error results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                error_result = ProcessingResult(
                    success=False,
                    input_data=data_batch[i],
                    errors=[str(result)]
                )
                processed_results.append(error_result)
            else:
                processed_results.append(result)
        
        return processed_results

# Storage for pipelines
class PipelineStorage:
    """Storage for pipeline definitions"""
    
    def __init__(self, db_path: str = "pipeline_storage.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pipelines (
                pipeline_id TEXT PRIMARY KEY,
                name TEXT,
                description TEXT,
                steps TEXT,
                input_schema TEXT,
                output_schema TEXT,
                processing_mode TEXT,
                batch_size INTEGER,
                max_parallel INTEGER,
                timeout INTEGER,
                error_threshold REAL,
                status TEXT,
                created_at TEXT,
                metadata TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def save_pipeline(self, pipeline: Pipeline):
        """Save pipeline to storage"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO pipelines 
            (pipeline_id, name, description, steps, input_schema, output_schema,
             processing_mode, batch_size, max_parallel, timeout, error_threshold,
             status, created_at, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            pipeline.pipeline_id, pipeline.name, pipeline.description,
            json.dumps([asdict(step) for step in pipeline.steps]),
            json.dumps(asdict(pipeline.input_schema)) if pipeline.input_schema else None,
            json.dumps(asdict(pipeline.output_schema)) if pipeline.output_schema else None,
            pipeline.processing_mode.value, pipeline.batch_size, pipeline.max_parallel,
            pipeline.timeout, pipeline.error_threshold, pipeline.status.value,
            pipeline.created_at.isoformat(), json.dumps(pipeline.metadata)
        ))
        
        conn.commit()
        conn.close()

# Factory function
def create_pipeline_engine() -> PipelineEngine:
    """Create and return a pipeline engine instance"""
    return PipelineEngine()

# Helper functions
def create_simple_pipeline(name: str, steps: List[Dict[str, Any]]) -> Pipeline:
    """Create a simple pipeline from step configurations"""
    pipeline_id = str(uuid.uuid4())
    
    transformation_steps = []
    for i, step_config in enumerate(steps):
        step = TransformationStep(
            step_id=f"step_{i+1}",
            name=step_config.get("name", f"Step {i+1}"),
            step_type=step_config["type"],
            config=step_config.get("config", {}),
            order=i
        )
        transformation_steps.append(step)
    
    return Pipeline(
        pipeline_id=pipeline_id,
        name=name,
        description=f"Auto-generated pipeline: {name}",
        steps=transformation_steps
    )