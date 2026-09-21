from fastapi import APIRouter, HTTPException, status, Depends, BackgroundTasks
from typing import List, Optional
import httpx
from datetime import datetime

from schemas import (
    FileMetadataCreate, FileMetadataUpdate, FileMetadataResponse,
    TagCreate, TagResponse, TagAssignment, SearchRequest, SearchResponse,
    EmbeddingCreate, EmbeddingResponse, VectorSearchRequest, VectorSearchResult,
    RelationshipCreate, RelationshipResponse, BatchMetadataCreate, BatchMetadataResponse,
    BatchTagAssignment, FileSyncWebhook, AggregationResponse
)
from database import FileMetadataModel, TagModel, get_db
from elasticsearch_client import ElasticsearchService
from embeddings import EmbeddingService
from relationships import RelationshipService

# Metadata CRUD Router
metadata_router = APIRouter()

@metadata_router.post("/", response_model=FileMetadataResponse, status_code=status.HTTP_201_CREATED)
async def create_file_metadata(
    metadata: FileMetadataCreate,
    background_tasks: BackgroundTasks
):
    # Check if metadata already exists for this file
    existing = FileMetadataModel.get_by_file_id(metadata.file_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Metadata already exists for this file"
        )
    
    # Create metadata record
    metadata_id = FileMetadataModel.create(
        file_id=metadata.file_id,
        filename=metadata.filename,
        file_path=metadata.file_path,
        file_size=metadata.file_size,
        file_type=metadata.file_type,
        mime_type=metadata.mime_type,
        checksum=metadata.checksum,
        content_text=metadata.content_text,
        metadata=metadata.metadata
    )
    
    if not metadata_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create metadata"
        )
    
    # Index in Elasticsearch asynchronously
    metadata_dict = metadata.dict()
    metadata_dict['id'] = metadata_id
    metadata_dict['created_at'] = datetime.utcnow().isoformat()
    metadata_dict['updated_at'] = datetime.utcnow().isoformat()
    metadata_dict['tags'] = []
    
    background_tasks.add_task(
        ElasticsearchService.index_file_metadata,
        metadata_id,
        metadata_dict
    )
    
    # Return the created metadata
    created_metadata = FileMetadataModel.get_by_id(metadata_id)
    created_metadata['tags'] = []
    return FileMetadataResponse(**created_metadata)

@metadata_router.get("/{metadata_id}", response_model=FileMetadataResponse)
async def get_file_metadata(metadata_id: str):
    metadata = FileMetadataModel.get_by_id(metadata_id)
    if not metadata:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Metadata not found"
        )
    
    # Get associated tags
    tags = TagModel.get_file_tags(metadata_id)
    metadata['tags'] = tags or []
    
    return FileMetadataResponse(**metadata)

@metadata_router.put("/{metadata_id}", response_model=FileMetadataResponse)
async def update_file_metadata(
    metadata_id: str,
    update_data: FileMetadataUpdate,
    background_tasks: BackgroundTasks
):
    # Check if metadata exists
    existing = FileMetadataModel.get_by_id(metadata_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Metadata not found"
        )
    
    # Update metadata
    update_dict = {k: v for k, v in update_data.dict().items() if v is not None}
    if not update_dict:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid fields to update"
        )
    
    success = FileMetadataModel.update(metadata_id, **update_dict)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update metadata"
        )
    
    # Update in Elasticsearch asynchronously
    es_update_data = update_dict.copy()
    es_update_data['updated_at'] = datetime.utcnow().isoformat()
    
    background_tasks.add_task(
        ElasticsearchService.update_file_metadata,
        metadata_id,
        es_update_data
    )
    
    # Return updated metadata
    updated_metadata = FileMetadataModel.get_by_id(metadata_id)
    tags = TagModel.get_file_tags(metadata_id)
    updated_metadata['tags'] = tags or []
    
    return FileMetadataResponse(**updated_metadata)

@metadata_router.delete("/{metadata_id}")
async def delete_file_metadata(metadata_id: str, background_tasks: BackgroundTasks):
    # Check if metadata exists
    existing = FileMetadataModel.get_by_id(metadata_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Metadata not found"
        )
    
    # Delete from database
    success = FileMetadataModel.delete(metadata_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to delete metadata"
        )
    
    # Delete from Elasticsearch asynchronously
    background_tasks.add_task(
        ElasticsearchService.delete_file_metadata,
        metadata_id
    )
    
    return {"message": "Metadata deleted successfully"}

@metadata_router.get("/", response_model=List[FileMetadataResponse])
async def list_file_metadata(limit: int = 100, offset: int = 0):
    if limit > 1000:
        limit = 1000
    
    metadata_list = FileMetadataModel.list_all(limit=limit, offset=offset)
    
    # Add tags to each metadata record
    for metadata in metadata_list:
        tags = TagModel.get_file_tags(metadata['id'])
        metadata['tags'] = tags or []
    
    return [FileMetadataResponse(**metadata) for metadata in metadata_list]

# Tags Router
tags_router = APIRouter()

@tags_router.post("/", response_model=TagResponse, status_code=status.HTTP_201_CREATED)
async def create_tag(tag: TagCreate):
    # Check if tag already exists
    existing = TagModel.get_by_name(tag.name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tag with this name already exists"
        )
    
    tag_id = TagModel.create(
        name=tag.name,
        description=tag.description,
        color=tag.color
    )
    
    if not tag_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create tag"
        )
    
    created_tag = TagModel.get_by_id(tag_id)
    return TagResponse(**created_tag)

@tags_router.get("/", response_model=List[TagResponse])
async def list_tags():
    tags = TagModel.list_all()
    return [TagResponse(**tag) for tag in tags]

@tags_router.get("/{tag_id}", response_model=TagResponse)
async def get_tag(tag_id: str):
    tag = TagModel.get_by_id(tag_id)
    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found"
        )
    return TagResponse(**tag)

@tags_router.post("/{metadata_id}/assign")
async def assign_tags_to_file(
    metadata_id: str,
    tag_assignment: TagAssignment,
    background_tasks: BackgroundTasks
):
    # Check if metadata exists
    metadata = FileMetadataModel.get_by_id(metadata_id)
    if not metadata:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Metadata not found"
        )
    
    # Assign tags
    successful_assignments = []
    failed_assignments = []
    
    for tag_id in tag_assignment.tag_ids:
        tag = TagModel.get_by_id(tag_id)
        if not tag:
            failed_assignments.append({"tag_id": tag_id, "reason": "Tag not found"})
            continue
        
        success = TagModel.assign_to_file(metadata_id, tag_id)
        if success:
            successful_assignments.append(tag_id)
        else:
            failed_assignments.append({"tag_id": tag_id, "reason": "Assignment failed"})
    
    # Update Elasticsearch with new tags
    if successful_assignments:
        tags = TagModel.get_file_tags(metadata_id)
        es_tags = [{"id": tag["id"], "name": tag["name"], "description": tag["description"]} for tag in tags]
        
        background_tasks.add_task(
            ElasticsearchService.update_file_metadata,
            metadata_id,
            {"tags": es_tags}
        )
    
    return {
        "successful_assignments": successful_assignments,
        "failed_assignments": failed_assignments
    }

@tags_router.delete("/{metadata_id}/tags/{tag_id}")
async def remove_tag_from_file(
    metadata_id: str,
    tag_id: str,
    background_tasks: BackgroundTasks
):
    # Check if metadata exists
    metadata = FileMetadataModel.get_by_id(metadata_id)
    if not metadata:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Metadata not found"
        )
    
    # Remove tag
    success = TagModel.remove_from_file(metadata_id, tag_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag assignment not found"
        )
    
    # Update Elasticsearch
    tags = TagModel.get_file_tags(metadata_id)
    es_tags = [{"id": tag["id"], "name": tag["name"], "description": tag["description"]} for tag in tags]
    
    background_tasks.add_task(
        ElasticsearchService.update_file_metadata,
        metadata_id,
        {"tags": es_tags}
    )
    
    return {"message": "Tag removed successfully"}

# Search Router
search_router = APIRouter()

@search_router.post("/", response_model=SearchResponse)
async def search_files(search_request: SearchRequest):
    results = await ElasticsearchService.search_files(
        query=search_request.query,
        file_type=search_request.file_type,
        tags=search_request.tags,
        size=search_request.size,
        from_=search_request.from_
    )
    
    return SearchResponse(**results)

@search_router.get("/aggregations", response_model=AggregationResponse)
async def get_search_aggregations():
    file_types = await ElasticsearchService.aggregate_by_file_type()
    popular_tags = await ElasticsearchService.get_popular_tags()
    
    return AggregationResponse(
        file_types=file_types,
        popular_tags=popular_tags
    )

# Embeddings Router
embeddings_router = APIRouter()

@embeddings_router.post("/", response_model=EmbeddingResponse, status_code=status.HTTP_201_CREATED)
async def create_embedding(embedding: EmbeddingCreate):
    # Check if metadata exists
    metadata = FileMetadataModel.get_by_id(embedding.file_metadata_id)
    if not metadata:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File metadata not found"
        )
    
    embedding_id = EmbeddingService.create_embedding(
        file_metadata_id=embedding.file_metadata_id,
        embedding_type=embedding.embedding_type,
        vector=embedding.vector,
        model_name=embedding.model_name
    )
    
    if not embedding_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create embedding"
        )
    
    created_embedding = EmbeddingService.get_by_id(embedding_id)
    return EmbeddingResponse(**created_embedding)

@embeddings_router.post("/search", response_model=List[VectorSearchResult])
async def vector_search(search_request: VectorSearchRequest):
    results = EmbeddingService.vector_search(
        vector=search_request.vector,
        embedding_type=search_request.embedding_type,
        limit=search_request.limit,
        similarity_threshold=search_request.similarity_threshold
    )
    
    # Enrich results with metadata
    enriched_results = []
    for result in results:
        metadata = FileMetadataModel.get_by_id(result['file_metadata_id'])
        if metadata:
            tags = TagModel.get_file_tags(result['file_metadata_id'])
            metadata['tags'] = tags or []
            
            enriched_results.append(VectorSearchResult(
                file_metadata_id=result['file_metadata_id'],
                similarity=result['similarity'],
                metadata=FileMetadataResponse(**metadata)
            ))
    
    return enriched_results

# Relationships Router
relationships_router = APIRouter()

@relationships_router.post("/", response_model=RelationshipResponse, status_code=status.HTTP_201_CREATED)
async def create_relationship(relationship: RelationshipCreate):
    # Validate that both files exist
    source_metadata = FileMetadataModel.get_by_id(relationship.source_file_id)
    target_metadata = FileMetadataModel.get_by_id(relationship.target_file_id)
    
    if not source_metadata:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source file metadata not found"
        )
    
    if not target_metadata:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target file metadata not found"
        )
    
    relationship_id = RelationshipService.create_relationship(
        source_file_id=relationship.source_file_id,
        target_file_id=relationship.target_file_id,
        relationship_type=relationship.relationship_type,
        metadata=relationship.metadata
    )
    
    if not relationship_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create relationship"
        )
    
    created_relationship = RelationshipService.get_by_id(relationship_id)
    return RelationshipResponse(**created_relationship)

@relationships_router.get("/{file_metadata_id}", response_model=List[RelationshipResponse])
async def get_file_relationships(file_metadata_id: str):
    # Check if metadata exists
    metadata = FileMetadataModel.get_by_id(file_metadata_id)
    if not metadata:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File metadata not found"
        )
    
    relationships = RelationshipService.get_file_relationships(file_metadata_id)
    return [RelationshipResponse(**rel) for rel in relationships]

# Batch Operations Router
batch_router = APIRouter()

@batch_router.post("/metadata", response_model=BatchMetadataResponse)
async def batch_create_metadata(
    batch_request: BatchMetadataCreate,
    background_tasks: BackgroundTasks
):
    results = []
    successful = 0
    failed = 0
    
    for file_metadata in batch_request.files:
        try:
            # Check if metadata already exists
            existing = FileMetadataModel.get_by_file_id(file_metadata.file_id)
            if existing:
                results.append({
                    "file_id": file_metadata.file_id,
                    "status": "failed",
                    "error": "Metadata already exists"
                })
                failed += 1
                continue
            
            # Create metadata
            metadata_id = FileMetadataModel.create(
                file_id=file_metadata.file_id,
                filename=file_metadata.filename,
                file_path=file_metadata.file_path,
                file_size=file_metadata.file_size,
                file_type=file_metadata.file_type,
                mime_type=file_metadata.mime_type,
                checksum=file_metadata.checksum,
                content_text=file_metadata.content_text,
                metadata=file_metadata.metadata
            )
            
            if metadata_id:
                results.append({
                    "file_id": file_metadata.file_id,
                    "metadata_id": metadata_id,
                    "status": "success"
                })
                successful += 1
                
                # Queue for Elasticsearch indexing
                metadata_dict = file_metadata.dict()
                metadata_dict['id'] = metadata_id
                metadata_dict['created_at'] = datetime.utcnow().isoformat()
                metadata_dict['updated_at'] = datetime.utcnow().isoformat()
                metadata_dict['tags'] = []
                
                background_tasks.add_task(
                    ElasticsearchService.index_file_metadata,
                    metadata_id,
                    metadata_dict
                )
            else:
                results.append({
                    "file_id": file_metadata.file_id,
                    "status": "failed",
                    "error": "Failed to create metadata"
                })
                failed += 1
                
        except Exception as e:
            results.append({
                "file_id": file_metadata.file_id,
                "status": "failed",
                "error": str(e)
            })
            failed += 1
    
    return BatchMetadataResponse(
        total_processed=len(batch_request.files),
        successful=successful,
        failed=failed,
        results=results
    )

@batch_router.post("/tags/assign", response_model=BatchMetadataResponse)
async def batch_assign_tags(
    batch_assignment: BatchTagAssignment,
    background_tasks: BackgroundTasks
):
    results = []
    successful = 0
    failed = 0
    
    # Validate all tag IDs first
    valid_tag_ids = []
    for tag_id in batch_assignment.tag_ids:
        tag = TagModel.get_by_id(tag_id)
        if tag:
            valid_tag_ids.append(tag_id)
    
    if not valid_tag_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid tag IDs provided"
        )
    
    for file_metadata_id in batch_assignment.file_metadata_ids:
        try:
            # Check if metadata exists
            metadata = FileMetadataModel.get_by_id(file_metadata_id)
            if not metadata:
                results.append({
                    "file_metadata_id": file_metadata_id,
                    "status": "failed",
                    "error": "Metadata not found"
                })
                failed += 1
                continue
            
            # Assign all valid tags
            assigned_tags = []
            for tag_id in valid_tag_ids:
                if TagModel.assign_to_file(file_metadata_id, tag_id):
                    assigned_tags.append(tag_id)
            
            if assigned_tags:
                results.append({
                    "file_metadata_id": file_metadata_id,
                    "status": "success",
                    "assigned_tags": assigned_tags
                })
                successful += 1
                
                # Update Elasticsearch
                tags = TagModel.get_file_tags(file_metadata_id)
                es_tags = [{"id": tag["id"], "name": tag["name"], "description": tag["description"]} for tag in tags]
                
                background_tasks.add_task(
                    ElasticsearchService.update_file_metadata,
                    file_metadata_id,
                    {"tags": es_tags}
                )
            else:
                results.append({
                    "file_metadata_id": file_metadata_id,
                    "status": "failed",
                    "error": "No tags could be assigned"
                })
                failed += 1
                
        except Exception as e:
            results.append({
                "file_metadata_id": file_metadata_id,
                "status": "failed",
                "error": str(e)
            })
            failed += 1
    
    return BatchMetadataResponse(
        total_processed=len(batch_assignment.file_metadata_ids),
        successful=successful,
        failed=failed,
        results=results
    )

# File-sync integration webhook
@batch_router.post("/webhook/file-sync")
async def file_sync_webhook(
    webhook_data: FileSyncWebhook,
    background_tasks: BackgroundTasks
):
    """Handle webhook events from file-sync service"""
    
    if webhook_data.event_type == "file_created":
        # Create metadata if it doesn't exist
        existing = FileMetadataModel.get_by_file_id(webhook_data.file_id)
        if not existing:
            # Extract file info
            import os
            filename = os.path.basename(webhook_data.file_path)
            file_type = filename.split('.')[-1].lower() if '.' in filename else 'unknown'
            
            metadata_id = FileMetadataModel.create(
                file_id=webhook_data.file_id,
                filename=filename,
                file_path=webhook_data.file_path,
                file_size=webhook_data.file_size,
                file_type=file_type,
                mime_type=webhook_data.mime_type,
                checksum=webhook_data.checksum
            )
            
            if metadata_id:
                # Index in Elasticsearch
                metadata_dict = {
                    'id': metadata_id,
                    'file_id': webhook_data.file_id,
                    'filename': filename,
                    'file_path': webhook_data.file_path,
                    'file_size': webhook_data.file_size,
                    'file_type': file_type,
                    'mime_type': webhook_data.mime_type,
                    'checksum': webhook_data.checksum,
                    'created_at': datetime.utcnow().isoformat(),
                    'updated_at': datetime.utcnow().isoformat(),
                    'tags': [],
                    'metadata': {}
                }
                
                background_tasks.add_task(
                    ElasticsearchService.index_file_metadata,
                    metadata_id,
                    metadata_dict
                )
    
    elif webhook_data.event_type == "file_updated":
        # Update existing metadata
        existing = FileMetadataModel.get_by_file_id(webhook_data.file_id)
        if existing:
            update_data = {
                'file_size': webhook_data.file_size,
                'checksum': webhook_data.checksum
            }
            
            FileMetadataModel.update(existing['id'], **update_data)
            
            # Update Elasticsearch
            update_data['updated_at'] = datetime.utcnow().isoformat()
            background_tasks.add_task(
                ElasticsearchService.update_file_metadata,
                existing['id'],
                update_data
            )
    
    elif webhook_data.event_type == "file_deleted":
        # Delete metadata
        existing = FileMetadataModel.get_by_file_id(webhook_data.file_id)
        if existing:
            FileMetadataModel.delete(existing['id'])
            
            # Delete from Elasticsearch
            background_tasks.add_task(
                ElasticsearchService.delete_file_metadata,
                existing['id']
            )
    
    return {"message": f"Processed {webhook_data.event_type} event for file {webhook_data.file_id}"}