#!/usr/bin/env python3
"""
ActiveLog Real-Time Event System - Operational Transform Engine
Handles collaborative editing with conflict resolution
"""

import json
import time
import uuid
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class OperationType(Enum):
    """Types of operations for collaborative editing"""
    INSERT = "insert"
    DELETE = "delete" 
    RETAIN = "retain"
    FORMAT = "format"

@dataclass
class Operation:
    """Single operation in a document"""
    type: OperationType
    position: int
    content: str = ""
    length: int = 0
    attributes: Dict[str, Any] = None
    author: str = ""
    timestamp: float = 0
    
    def __post_init__(self):
        if self.attributes is None:
            self.attributes = {}
        if self.timestamp == 0:
            self.timestamp = time.time()

@dataclass
class DocumentState:
    """State of a collaborative document"""
    id: str
    content: str
    version: int
    operations: List[Operation]
    last_modified: float
    authors: List[str]
    
    def __post_init__(self):
        if not self.operations:
            self.operations = []
        if not self.authors:
            self.authors = []
        if self.last_modified == 0:
            self.last_modified = time.time()

class OperationalTransform:
    """Operational Transform engine for collaborative editing"""
    
    def __init__(self):
        self.documents: Dict[str, DocumentState] = {}
        self.operation_history: Dict[str, List[Operation]] = {}
        
    def create_document(self, doc_id: str, initial_content: str = "", author: str = "") -> DocumentState:
        """Create a new document"""
        document = DocumentState(
            id=doc_id,
            content=initial_content,
            version=0,
            operations=[],
            last_modified=time.time(),
            authors=[author] if author else []
        )
        
        self.documents[doc_id] = document
        self.operation_history[doc_id] = []
        
        logger.info(f"Created document: {doc_id}")
        return document
    
    def apply_operation(self, doc_id: str, operation: Operation) -> Tuple[bool, DocumentState, List[Operation]]:
        """
        Apply operation to document with conflict resolution
        Returns (success, updated_document, transformed_operations)
        """
        if doc_id not in self.documents:
            return False, None, []
        
        document = self.documents[doc_id]
        
        try:
            # Transform operation against concurrent operations
            transformed_ops = self._transform_operation(doc_id, operation)
            
            # Apply the transformed operation
            new_content = self._apply_operation_to_content(document.content, operation)
            
            # Update document state
            document.content = new_content
            document.version += 1
            document.last_modified = time.time()
            
            if operation.author not in document.authors:
                document.authors.append(operation.author)
            
            # Store operation in history
            document.operations.append(operation)
            self.operation_history[doc_id].append(operation)
            
            logger.debug(f"Applied operation to {doc_id}: {operation.type.value}")
            return True, document, transformed_ops
            
        except Exception as e:
            logger.error(f"Failed to apply operation to {doc_id}: {e}")
            return False, document, []
    
    def _transform_operation(self, doc_id: str, operation: Operation) -> List[Operation]:
        """Transform operation against concurrent operations"""
        document = self.documents[doc_id]
        transformed_operations = []
        
        # Get operations that happened after this operation's timestamp
        concurrent_ops = [
            op for op in document.operations
            if op.timestamp > operation.timestamp - 0.1  # Small tolerance
            and op.author != operation.author
        ]
        
        # Transform against each concurrent operation
        current_op = operation
        for concurrent_op in concurrent_ops:
            current_op = self._transform_single_operation(current_op, concurrent_op)
            if current_op:
                transformed_operations.append(current_op)
        
        return transformed_operations
    
    def _transform_single_operation(self, op1: Operation, op2: Operation) -> Optional[Operation]:
        """Transform one operation against another"""
        # INSERT vs INSERT
        if op1.type == OperationType.INSERT and op2.type == OperationType.INSERT:
            if op1.position <= op2.position:
                # op1 comes before op2, adjust op2's position
                op2.position += len(op1.content)
            else:
                # op2 comes before op1, adjust op1's position  
                op1.position += len(op2.content)
        
        # INSERT vs DELETE
        elif op1.type == OperationType.INSERT and op2.type == OperationType.DELETE:
            if op1.position <= op2.position:
                op2.position += len(op1.content)
            elif op1.position < op2.position + op2.length:
                # Insert is within delete range
                op2.length += len(op1.content)
        
        # DELETE vs INSERT
        elif op1.type == OperationType.DELETE and op2.type == OperationType.INSERT:
            if op2.position <= op1.position:
                op1.position += len(op2.content)
            elif op2.position < op1.position + op1.length:
                # Insert is within delete range
                op1.length += len(op2.content)
        
        # DELETE vs DELETE
        elif op1.type == OperationType.DELETE and op2.type == OperationType.DELETE:
            if op1.position + op1.length <= op2.position:
                # op1 is completely before op2
                op2.position -= op1.length
            elif op2.position + op2.length <= op1.position:
                # op2 is completely before op1
                op1.position -= op2.length
            else:
                # Overlapping deletes - complex resolution needed
                return self._resolve_overlapping_deletes(op1, op2)
        
        return op1
    
    def _resolve_overlapping_deletes(self, op1: Operation, op2: Operation) -> Operation:
        """Resolve overlapping delete operations"""
        # Take the union of both delete ranges
        start = min(op1.position, op2.position)
        end = max(op1.position + op1.length, op2.position + op2.length)
        
        return Operation(
            type=OperationType.DELETE,
            position=start,
            length=end - start,
            author=op1.author,
            timestamp=op1.timestamp
        )
    
    def _apply_operation_to_content(self, content: str, operation: Operation) -> str:
        """Apply a single operation to document content"""
        if operation.type == OperationType.INSERT:
            return (content[:operation.position] + 
                   operation.content + 
                   content[operation.position:])
        
        elif operation.type == OperationType.DELETE:
            end_pos = operation.position + operation.length
            return content[:operation.position] + content[end_pos:]
        
        elif operation.type == OperationType.RETAIN:
            # Retain operation doesn't change content
            return content
        
        return content
    
    def get_document(self, doc_id: str) -> Optional[DocumentState]:
        """Get document state"""
        return self.documents.get(doc_id)
    
    def get_document_history(self, doc_id: str, since_version: int = 0) -> List[Operation]:
        """Get operation history for document since version"""
        if doc_id not in self.documents:
            return []
        
        document = self.documents[doc_id]
        return [op for op in document.operations if document.version > since_version]
    
    def replay_operations(self, doc_id: str, from_version: int = 0) -> Optional[DocumentState]:
        """Replay operations to reconstruct document state"""
        if doc_id not in self.operation_history:
            return None
        
        # Start with empty document
        document = DocumentState(
            id=doc_id,
            content="",
            version=0,
            operations=[],
            last_modified=time.time(),
            authors=[]
        )
        
        # Replay operations in order
        operations = self.operation_history[doc_id][from_version:]
        for operation in operations:
            document.content = self._apply_operation_to_content(document.content, operation)
            document.version += 1
            document.operations.append(operation)
            
            if operation.author not in document.authors:
                document.authors.append(operation.author)
        
        return document
    
    def create_operation(self, op_type: str, position: int, content: str = "", 
                        length: int = 0, author: str = "") -> Operation:
        """Create a new operation"""
        return Operation(
            type=OperationType(op_type),
            position=position,
            content=content,
            length=length,
            author=author,
            timestamp=time.time()
        )
    
    def merge_operations(self, operations: List[Operation]) -> List[Operation]:
        """Merge consecutive operations for efficiency"""
        if not operations:
            return []
        
        merged = []
        current_op = operations[0]
        
        for next_op in operations[1:]:
            # Try to merge consecutive operations of same type and author
            if (current_op.type == next_op.type and 
                current_op.author == next_op.author and
                self._can_merge_operations(current_op, next_op)):
                
                current_op = self._merge_two_operations(current_op, next_op)
            else:
                merged.append(current_op)
                current_op = next_op
        
        merged.append(current_op)
        return merged
    
    def _can_merge_operations(self, op1: Operation, op2: Operation) -> bool:
        """Check if two operations can be merged"""
        if op1.type != op2.type or op1.author != op2.author:
            return False
        
        if op1.type == OperationType.INSERT:
            return op1.position + len(op1.content) == op2.position
        elif op1.type == OperationType.DELETE:
            return op1.position == op2.position
        
        return False
    
    def _merge_two_operations(self, op1: Operation, op2: Operation) -> Operation:
        """Merge two compatible operations"""
        if op1.type == OperationType.INSERT:
            return Operation(
                type=OperationType.INSERT,
                position=op1.position,
                content=op1.content + op2.content,
                author=op1.author,
                timestamp=op1.timestamp
            )
        elif op1.type == OperationType.DELETE:
            return Operation(
                type=OperationType.DELETE,
                position=op1.position,
                length=op1.length + op2.length,
                author=op1.author,
                timestamp=op1.timestamp
            )
        
        return op1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get operational transform statistics"""
        total_operations = sum(len(ops) for ops in self.operation_history.values())
        total_documents = len(self.documents)
        
        return {
            "documents": total_documents,
            "total_operations": total_operations,
            "documents_with_operations": {
                doc_id: len(ops) for doc_id, ops in self.operation_history.items()
            }
        }