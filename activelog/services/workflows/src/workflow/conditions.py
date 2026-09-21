"""
Condition evaluation system for workflow branching and logic
"""

import logging
import operator
import re
from datetime import datetime, timedelta
from typing import Dict, Any, List, Union, Callable
from enum import Enum

from .context import ExecutionContext

logger = logging.getLogger(__name__)

class ConditionOperator(Enum):
    """Supported condition operators"""
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    GREATER_THAN = "greater_than"
    GREATER_THAN_OR_EQUAL = "greater_than_or_equal"
    LESS_THAN = "less_than"
    LESS_THAN_OR_EQUAL = "less_than_or_equal"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    MATCHES_REGEX = "matches_regex"
    IN_LIST = "in_list"
    NOT_IN_LIST = "not_in_list"
    IS_EMPTY = "is_empty"
    IS_NOT_EMPTY = "is_not_empty"
    IS_NULL = "is_null"
    IS_NOT_NULL = "is_not_null"
    AND = "and"
    OR = "or"
    NOT = "not"

class ConditionEvaluator:
    """Evaluates conditional expressions in workflows"""
    
    def __init__(self, context: ExecutionContext = None):
        self.context = context
        
        # Operator mapping
        self.operators: Dict[str, Callable] = {
            ConditionOperator.EQUALS.value: self._op_equals,
            ConditionOperator.NOT_EQUALS.value: self._op_not_equals,
            ConditionOperator.GREATER_THAN.value: self._op_greater_than,
            ConditionOperator.GREATER_THAN_OR_EQUAL.value: self._op_greater_than_or_equal,
            ConditionOperator.LESS_THAN.value: self._op_less_than,
            ConditionOperator.LESS_THAN_OR_EQUAL.value: self._op_less_than_or_equal,
            ConditionOperator.CONTAINS.value: self._op_contains,
            ConditionOperator.NOT_CONTAINS.value: self._op_not_contains,
            ConditionOperator.STARTS_WITH.value: self._op_starts_with,
            ConditionOperator.ENDS_WITH.value: self._op_ends_with,
            ConditionOperator.MATCHES_REGEX.value: self._op_matches_regex,
            ConditionOperator.IN_LIST.value: self._op_in_list,
            ConditionOperator.NOT_IN_LIST.value: self._op_not_in_list,
            ConditionOperator.IS_EMPTY.value: self._op_is_empty,
            ConditionOperator.IS_NOT_EMPTY.value: self._op_is_not_empty,
            ConditionOperator.IS_NULL.value: self._op_is_null,
            ConditionOperator.IS_NOT_NULL.value: self._op_is_not_null,
            ConditionOperator.AND.value: self._op_and,
            ConditionOperator.OR.value: self._op_or,
            ConditionOperator.NOT.value: self._op_not,
        }
    
    async def evaluate(self, condition: Dict[str, Any]) -> bool:
        """Evaluate a condition expression"""
        try:
            return await self._evaluate_condition(condition)
        except Exception as e:
            logger.error(f"Error evaluating condition {condition}: {e}")
            return False
    
    async def _evaluate_condition(self, condition: Dict[str, Any]) -> bool:
        """Internal condition evaluation"""
        
        if not isinstance(condition, dict):
            return bool(condition)
        
        # Get operator
        op = condition.get("operator", condition.get("op"))
        if not op:
            return False
        
        # Check if operator exists
        if op not in self.operators:
            logger.error(f"Unknown operator: {op}")
            return False
        
        # Get operator function
        op_func = self.operators[op]
        
        # Execute operator
        return await op_func(condition)
    
    def _resolve_value(self, value: Any) -> Any:
        """Resolve a value (could be variable reference or literal)"""
        if not self.context:
            return value
        
        # Handle variable references
        if isinstance(value, str):
            # Template variable (e.g., "{{ variable_name }}")
            if value.startswith("{{") and value.endswith("}}"):
                var_name = value[2:-2].strip()
                return self.context.resolve_path(var_name)
            
            # Direct variable reference (e.g., "variable_name")
            if value in self.context.variables:
                return self.context.get_variable(value)
            
            # Path reference (e.g., "user.name")
            if "." in value:
                resolved = self.context.resolve_path(value)
                if resolved is not None:
                    return resolved
        
        return value
    
    # Comparison operators
    async def _op_equals(self, condition: Dict[str, Any]) -> bool:
        left = self._resolve_value(condition.get("left"))
        right = self._resolve_value(condition.get("right"))
        return left == right
    
    async def _op_not_equals(self, condition: Dict[str, Any]) -> bool:
        left = self._resolve_value(condition.get("left"))
        right = self._resolve_value(condition.get("right"))
        return left != right
    
    async def _op_greater_than(self, condition: Dict[str, Any]) -> bool:
        left = self._resolve_value(condition.get("left"))
        right = self._resolve_value(condition.get("right"))
        try:
            return float(left) > float(right)
        except (TypeError, ValueError):
            return False
    
    async def _op_greater_than_or_equal(self, condition: Dict[str, Any]) -> bool:
        left = self._resolve_value(condition.get("left"))
        right = self._resolve_value(condition.get("right"))
        try:
            return float(left) >= float(right)
        except (TypeError, ValueError):
            return False
    
    async def _op_less_than(self, condition: Dict[str, Any]) -> bool:
        left = self._resolve_value(condition.get("left"))
        right = self._resolve_value(condition.get("right"))
        try:
            return float(left) < float(right)
        except (TypeError, ValueError):
            return False
    
    async def _op_less_than_or_equal(self, condition: Dict[str, Any]) -> bool:
        left = self._resolve_value(condition.get("left"))
        right = self._resolve_value(condition.get("right"))
        try:
            return float(left) <= float(right)
        except (TypeError, ValueError):
            return False
    
    # String operators
    async def _op_contains(self, condition: Dict[str, Any]) -> bool:
        left = str(self._resolve_value(condition.get("left", "")))
        right = str(self._resolve_value(condition.get("right", "")))
        return right in left
    
    async def _op_not_contains(self, condition: Dict[str, Any]) -> bool:
        return not await self._op_contains(condition)
    
    async def _op_starts_with(self, condition: Dict[str, Any]) -> bool:
        left = str(self._resolve_value(condition.get("left", "")))
        right = str(self._resolve_value(condition.get("right", "")))
        return left.startswith(right)
    
    async def _op_ends_with(self, condition: Dict[str, Any]) -> bool:
        left = str(self._resolve_value(condition.get("left", "")))
        right = str(self._resolve_value(condition.get("right", "")))
        return left.endswith(right)
    
    async def _op_matches_regex(self, condition: Dict[str, Any]) -> bool:
        left = str(self._resolve_value(condition.get("left", "")))
        pattern = str(self._resolve_value(condition.get("right", "")))
        flags = condition.get("flags", 0)
        
        try:
            return bool(re.search(pattern, left, flags))
        except re.error:
            return False
    
    # List operators
    async def _op_in_list(self, condition: Dict[str, Any]) -> bool:
        left = self._resolve_value(condition.get("left"))
        right = self._resolve_value(condition.get("right"))
        
        if not isinstance(right, (list, tuple, set)):
            return False
        
        return left in right
    
    async def _op_not_in_list(self, condition: Dict[str, Any]) -> bool:
        return not await self._op_in_list(condition)
    
    # Null/empty operators
    async def _op_is_empty(self, condition: Dict[str, Any]) -> bool:
        value = self._resolve_value(condition.get("value"))
        
        if value is None:
            return True
        
        if isinstance(value, (str, list, dict, tuple)):
            return len(value) == 0
        
        return False
    
    async def _op_is_not_empty(self, condition: Dict[str, Any]) -> bool:
        return not await self._op_is_empty(condition)
    
    async def _op_is_null(self, condition: Dict[str, Any]) -> bool:
        value = self._resolve_value(condition.get("value"))
        return value is None
    
    async def _op_is_not_null(self, condition: Dict[str, Any]) -> bool:
        return not await self._op_is_null(condition)
    
    # Logical operators
    async def _op_and(self, condition: Dict[str, Any]) -> bool:
        conditions = condition.get("conditions", [])
        
        for sub_condition in conditions:
            if not await self._evaluate_condition(sub_condition):
                return False
        
        return True
    
    async def _op_or(self, condition: Dict[str, Any]) -> bool:
        conditions = condition.get("conditions", [])
        
        for sub_condition in conditions:
            if await self._evaluate_condition(sub_condition):
                return True
        
        return False
    
    async def _op_not(self, condition: Dict[str, Any]) -> bool:
        sub_condition = condition.get("condition")
        if sub_condition is None:
            return False
        
        return not await self._evaluate_condition(sub_condition)
    
    def get_supported_operators(self) -> List[str]:
        """Get list of supported operators"""
        return list(self.operators.keys())
    
    async def validate_condition(self, condition: Dict[str, Any]) -> Dict[str, Any]:
        """Validate condition syntax"""
        errors = []
        warnings = []
        
        try:
            # Check if condition is a dictionary
            if not isinstance(condition, dict):
                errors.append("Condition must be a dictionary")
                return {"valid": False, "errors": errors, "warnings": warnings}
            
            # Check for operator
            op = condition.get("operator", condition.get("op"))
            if not op:
                errors.append("Operator is required")
            elif op not in self.operators:
                errors.append(f"Unknown operator: {op}")
            
            # Validate based on operator type
            if op in ["equals", "not_equals", "greater_than", "greater_than_or_equal", 
                     "less_than", "less_than_or_equal", "contains", "not_contains",
                     "starts_with", "ends_with", "matches_regex"]:
                if "left" not in condition:
                    errors.append("'left' value is required for comparison operators")
                if "right" not in condition:
                    errors.append("'right' value is required for comparison operators")
            
            elif op in ["in_list", "not_in_list"]:
                if "left" not in condition:
                    errors.append("'left' value is required for list operators")
                if "right" not in condition:
                    errors.append("'right' value (list) is required for list operators")
            
            elif op in ["is_empty", "is_not_empty", "is_null", "is_not_null"]:
                if "value" not in condition:
                    errors.append("'value' is required for null/empty operators")
            
            elif op in ["and", "or"]:
                if "conditions" not in condition:
                    errors.append("'conditions' array is required for logical operators")
                elif not isinstance(condition["conditions"], list):
                    errors.append("'conditions' must be an array")
                elif len(condition["conditions"]) == 0:
                    warnings.append("Empty conditions array")
            
            elif op == "not":
                if "condition" not in condition:
                    errors.append("'condition' is required for NOT operator")
            
            # Check for variable references
            self._check_variable_references(condition, warnings)
            
        except Exception as e:
            errors.append(f"Validation error: {str(e)}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    def _check_variable_references(self, condition: Dict[str, Any], warnings: List[str]):
        """Check if variable references exist in context"""
        if not self.context:
            return
        
        def check_value(value):
            if isinstance(value, str):
                # Template variable
                if value.startswith("{{") and value.endswith("}}"):
                    var_name = value[2:-2].strip()
                    if not self.context.has_variable(var_name) and "." not in var_name:
                        warnings.append(f"Variable '{var_name}' not found in context")
                
                # Direct variable reference
                elif value in self.context.variables or "." in value:
                    # Path or direct reference - skip warning as it might be valid
                    pass
        
        # Check all values in condition
        for key, value in condition.items():
            if key in ["left", "right", "value"]:
                check_value(value)
            elif key == "conditions" and isinstance(value, list):
                for sub_condition in value:
                    if isinstance(sub_condition, dict):
                        self._check_variable_references(sub_condition, warnings)
            elif key == "condition" and isinstance(value, dict):
                self._check_variable_references(value, warnings)