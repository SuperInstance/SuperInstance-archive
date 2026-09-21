"""
Execution context for workflow variables and data passing
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, Union, List
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

@dataclass
class VariableMetadata:
    """Metadata for context variables"""
    created_at: datetime
    updated_at: datetime
    source: str  # Where the variable came from (trigger, step, etc.)
    data_type: str
    is_sensitive: bool = False

class ExecutionContext:
    """Manages variables and data flow within a workflow execution"""
    
    def __init__(self, execution_id: str):
        self.execution_id = execution_id
        self.variables: Dict[str, Any] = {}
        self.metadata: Dict[str, VariableMetadata] = {}
        self.created_at = datetime.utcnow()
        
    def set_variable(self, name: str, value: Any, source: str = "system", is_sensitive: bool = False):
        """Set a variable in the execution context"""
        
        # Store the value
        self.variables[name] = value
        
        # Store metadata
        current_time = datetime.utcnow()
        self.metadata[name] = VariableMetadata(
            created_at=current_time if name not in self.metadata else self.metadata[name].created_at,
            updated_at=current_time,
            source=source,
            data_type=type(value).__name__,
            is_sensitive=is_sensitive
        )
        
        logger.debug(f"Set variable '{name}' = {value if not is_sensitive else '[REDACTED]'}")
    
    def get_variable(self, name: str, default: Any = None) -> Any:
        """Get a variable from the execution context"""
        return self.variables.get(name, default)
    
    def has_variable(self, name: str) -> bool:
        """Check if a variable exists in the context"""
        return name in self.variables
    
    def remove_variable(self, name: str) -> bool:
        """Remove a variable from the context"""
        if name in self.variables:
            del self.variables[name]
            del self.metadata[name]
            return True
        return False
    
    def get_all_variables(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """Get all variables from the context"""
        if include_sensitive:
            return self.variables.copy()
        
        # Filter out sensitive variables
        filtered_vars = {}
        for name, value in self.variables.items():
            if name in self.metadata and not self.metadata[name].is_sensitive:
                filtered_vars[name] = value
            elif name not in self.metadata:
                filtered_vars[name] = value
        
        return filtered_vars
    
    def get_variable_info(self, name: str) -> Optional[Dict[str, Any]]:
        """Get information about a variable"""
        if name not in self.variables:
            return None
        
        info = {
            "name": name,
            "value": self.variables[name],
            "exists": True
        }
        
        if name in self.metadata:
            meta = self.metadata[name]
            info.update({
                "created_at": meta.created_at.isoformat(),
                "updated_at": meta.updated_at.isoformat(),
                "source": meta.source,
                "data_type": meta.data_type,
                "is_sensitive": meta.is_sensitive
            })
            
            # Redact sensitive values
            if meta.is_sensitive:
                info["value"] = "[REDACTED]"
        
        return info
    
    def list_variables(self, include_sensitive: bool = False) -> List[Dict[str, Any]]:
        """List all variables with their metadata"""
        variable_list = []
        
        for name in self.variables.keys():
            var_info = self.get_variable_info(name)
            if var_info and (include_sensitive or not var_info.get("is_sensitive", False)):
                variable_list.append(var_info)
        
        return variable_list
    
    def merge_variables(self, other_variables: Dict[str, Any], source: str = "merge"):
        """Merge variables from another source"""
        for name, value in other_variables.items():
            self.set_variable(name, value, source)
    
    def resolve_path(self, path: str) -> Any:
        """Resolve a variable path (e.g., 'user.name', 'response.data.items[0]')"""
        try:
            parts = path.split('.')
            current = self.variables
            
            for part in parts:
                # Handle array indexing
                if '[' in part and ']' in part:
                    key = part[:part.index('[')]
                    index_str = part[part.index('[')+1:part.index(']')]
                    
                    if key:
                        current = current[key]
                    
                    try:
                        index = int(index_str)
                        current = current[index]
                    except (ValueError, TypeError):
                        # String key for dictionary
                        current = current[index_str]
                else:
                    current = current[part]
            
            return current
            
        except (KeyError, IndexError, TypeError):
            return None
    
    def evaluate_expression(self, expression: str) -> Any:
        """Evaluate a simple expression with context variables"""
        try:
            # Simple variable substitution
            if expression.startswith('{{') and expression.endswith('}}'):
                var_path = expression[2:-2].strip()
                return self.resolve_path(var_path)
            
            # Direct variable reference
            if expression in self.variables:
                return self.variables[expression]
            
            # Path reference
            return self.resolve_path(expression)
            
        except Exception as e:
            logger.error(f"Error evaluating expression '{expression}': {e}")
            return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary for serialization"""
        return {
            "execution_id": self.execution_id,
            "created_at": self.created_at.isoformat(),
            "variables": self.get_all_variables(include_sensitive=False),
            "variable_count": len(self.variables),
            "metadata": {
                name: {
                    "created_at": meta.created_at.isoformat(),
                    "updated_at": meta.updated_at.isoformat(),
                    "source": meta.source,
                    "data_type": meta.data_type,
                    "is_sensitive": meta.is_sensitive
                }
                for name, meta in self.metadata.items()
            }
        }
    
    def from_dict(self, data: Dict[str, Any]):
        """Restore context from dictionary"""
        self.execution_id = data.get("execution_id", self.execution_id)
        
        if "created_at" in data:
            self.created_at = datetime.fromisoformat(data["created_at"])
        
        # Restore variables
        variables = data.get("variables", {})
        for name, value in variables.items():
            self.variables[name] = value
        
        # Restore metadata
        metadata = data.get("metadata", {})
        for name, meta_dict in metadata.items():
            self.metadata[name] = VariableMetadata(
                created_at=datetime.fromisoformat(meta_dict["created_at"]),
                updated_at=datetime.fromisoformat(meta_dict["updated_at"]),
                source=meta_dict["source"],
                data_type=meta_dict["data_type"],
                is_sensitive=meta_dict.get("is_sensitive", False)
            )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get context statistics"""
        sensitive_count = sum(1 for meta in self.metadata.values() if meta.is_sensitive)
        
        return {
            "execution_id": self.execution_id,
            "total_variables": len(self.variables),
            "sensitive_variables": sensitive_count,
            "public_variables": len(self.variables) - sensitive_count,
            "created_at": self.created_at.isoformat(),
            "age_seconds": (datetime.utcnow() - self.created_at).total_seconds()
        }