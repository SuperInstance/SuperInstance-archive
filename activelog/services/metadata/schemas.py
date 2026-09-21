from pydantic import BaseModel, validator
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
import uuid

class FileMetadataCreate(BaseModel):
    file_id: str
    filename: str
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    file_type: Optional[str] = None
    mime_type: Optional[str] = None
    checksum: Optional[str] = None
    content_text: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = {}
    
    @validator('file_id')
    def validate_file_id(cls, v):
        try:
            uuid.UUID(v)
            return v
        except ValueError:
            raise ValueError('file_id must be a valid UUID')

class FileMetadataUpdate(BaseModel):
    filename: Optional[str] = None
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    file_type: Optional[str] = None
    mime_type: Optional[str] = None
    checksum: Optional[str] = None
    content_text: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class FileMetadataResponse(BaseModel):
    id: str
    file_id: str
    filename: str
    file_path: Optional[str]
    file_size: Optional[int]
    file_type: Optional[str]
    mime_type: Optional[str]
    checksum: Optional[str]
    content_text: Optional[str]
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    indexed_at: Optional[datetime]
    tags: Optional[List[Dict[str, Any]]] = []

class TagCreate(BaseModel):
    name: str
    description: Optional[str] = None
    color: Optional[str] = None
    
    @validator('name')
    def validate_name(cls, v):
        if len(v.strip()) == 0:
            raise ValueError('Tag name cannot be empty')
        if len(v) > 100:
            raise ValueError('Tag name cannot exceed 100 characters')
        return v.strip().lower()
    
    @validator('color')
    def validate_color(cls, v):
        if v and not v.startswith('#'):
            raise ValueError('Color must be a hex color code starting with #')
        return v

class TagResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    color: Optional[str]
    created_at: datetime
    usage_count: int

class TagAssignment(BaseModel):
    tag_ids: List[str]

class EmbeddingCreate(BaseModel):
    model_config = {"protected_namespaces": ()}
    
    file_metadata_id: str
    embedding_type: str
    vector: List[float]
    model_name: Optional[str] = None
    
    @validator('vector')
    def validate_vector(cls, v):
        if len(v) != 1536:
            raise ValueError('Vector must have exactly 1536 dimensions')
        return v
    
    @validator('embedding_type')
    def validate_embedding_type(cls, v):
        allowed_types = ['text', 'image', 'audio', 'code']
        if v not in allowed_types:
            raise ValueError(f'Embedding type must be one of: {allowed_types}')
        return v

class EmbeddingResponse(BaseModel):
    model_config = {"protected_namespaces": ()}
    
    id: str
    file_metadata_id: str
    embedding_type: str
    model_name: Optional[str]
    created_at: datetime

class VectorSearchRequest(BaseModel):
    vector: List[float]
    embedding_type: str = "text"
    limit: int = 10
    similarity_threshold: float = 0.7
    
    @validator('vector')
    def validate_vector(cls, v):
        if len(v) != 1536:
            raise ValueError('Vector must have exactly 1536 dimensions')
        return v
    
    @validator('limit')
    def validate_limit(cls, v):
        if v < 1 or v > 100:
            raise ValueError('Limit must be between 1 and 100')
        return v

class VectorSearchResult(BaseModel):
    file_metadata_id: str
    similarity: float
    metadata: FileMetadataResponse

class RelationshipCreate(BaseModel):
    source_file_id: str
    target_file_id: str
    relationship_type: str
    metadata: Optional[Dict[str, Any]] = {}
    
    @validator('relationship_type')
    def validate_relationship_type(cls, v):
        allowed_types = ['derived_from', 'contains', 'references', 'similar_to', 'depends_on', 'version_of', 'duplicate_of']
        if v not in allowed_types:
            raise ValueError(f'Relationship type must be one of: {allowed_types}')
        return v

class RelationshipResponse(BaseModel):
    id: str
    source_file_id: str
    target_file_id: str
    relationship_type: str
    metadata: Dict[str, Any]
    created_at: datetime
    source_metadata: Optional[FileMetadataResponse]
    target_metadata: Optional[FileMetadataResponse]

class SearchRequest(BaseModel):
    query: Optional[str] = None
    file_type: Optional[str] = None
    tags: Optional[List[str]] = None
    size: int = 20
    from_: int = 0
    
    @validator('size')
    def validate_size(cls, v):
        if v < 1 or v > 100:
            raise ValueError('Size must be between 1 and 100')
        return v

class SearchResponse(BaseModel):
    total: int
    results: List[Dict[str, Any]]

class BatchMetadataCreate(BaseModel):
    files: List[FileMetadataCreate]
    
    @validator('files')
    def validate_files(cls, v):
        if len(v) == 0:
            raise ValueError('At least one file must be provided')
        if len(v) > 100:
            raise ValueError('Cannot process more than 100 files at once')
        return v

class BatchMetadataResponse(BaseModel):
    total_processed: int
    successful: int
    failed: int
    results: List[Dict[str, Any]]

class BatchTagAssignment(BaseModel):
    file_metadata_ids: List[str]
    tag_ids: List[str]
    
    @validator('file_metadata_ids')
    def validate_file_ids(cls, v):
        if len(v) == 0:
            raise ValueError('At least one file ID must be provided')
        if len(v) > 100:
            raise ValueError('Cannot process more than 100 files at once')
        return v

class FileSyncWebhook(BaseModel):
    event_type: str
    file_id: str
    file_path: str
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    checksum: Optional[str] = None
    
    @validator('event_type')
    def validate_event_type(cls, v):
        allowed_events = ['file_created', 'file_updated', 'file_deleted']
        if v not in allowed_events:
            raise ValueError(f'Event type must be one of: {allowed_events}')
        return v

class AggregationResponse(BaseModel):
    file_types: Dict[str, int]
    popular_tags: List[Dict[str, Any]]