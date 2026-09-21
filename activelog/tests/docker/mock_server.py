"""
Mock server for external services during testing
Provides mock OpenAI and S3 APIs
"""

import asyncio
import json
import hashlib
import uvicorn
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
import threading
import os


# Mock OpenAI API
openai_app = FastAPI(title="Mock OpenAI API")

class EmbeddingRequest(BaseModel):
    input: List[str]
    model: str = "text-embedding-ada-002"

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    model: str = "gpt-3.5-turbo"
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = None

@openai_app.get("/health")
async def openai_health():
    return {"status": "healthy", "service": "mock-openai"}

@openai_app.post("/v1/embeddings")
async def create_embeddings(request: EmbeddingRequest):
    """Mock OpenAI embeddings endpoint"""
    
    embeddings = []
    for i, text in enumerate(request.input):
        # Generate deterministic embedding based on text hash
        text_hash = hashlib.md5(text.encode()).hexdigest()
        embedding = [float(int(text_hash[j:j+2], 16) / 255.0 - 0.5) for j in range(0, min(len(text_hash), 32), 2)]
        
        # Pad or truncate to 1536 dimensions
        while len(embedding) < 1536:
            embedding.extend(embedding[:min(1536 - len(embedding), len(embedding))])
        embedding = embedding[:1536]
        
        embeddings.append({
            "object": "embedding",
            "embedding": embedding,
            "index": i
        })
    
    return {
        "object": "list",
        "data": embeddings,
        "model": request.model,
        "usage": {
            "prompt_tokens": sum(len(text.split()) for text in request.input),
            "total_tokens": sum(len(text.split()) for text in request.input)
        }
    }

@openai_app.post("/v1/chat/completions")
async def create_chat_completion(request: ChatRequest):
    """Mock OpenAI chat completions endpoint"""
    
    # Generate response based on the last message
    last_message = request.messages[-1] if request.messages else None
    content = last_message.content.lower() if last_message else ""
    
    # Generate appropriate response
    if "summarize" in content or "summary" in content:
        response_text = "This document discusses key concepts and implementation details with comprehensive coverage of the main topics."
    elif "analyze" in content or "analysis" in content:
        response_text = "The content demonstrates strong technical implementation with well-structured approaches and good practices."
    elif "tag" in content or "extract" in content:
        response_text = "technology, implementation, documentation, analysis, development"
    elif "error" in content or "debug" in content:
        response_text = "Based on the error details, this appears to be a common issue that can be resolved by checking the configuration and ensuring all dependencies are properly installed."
    else:
        response_text = "I understand your request and here's my response based on the provided content and context."
    
    return {
        "id": f"chatcmpl-mock-{abs(hash(str(request.messages))) % 10000}",
        "object": "chat.completion",
        "created": int(datetime.now().timestamp()),
        "model": request.model,
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": response_text
            },
            "finish_reason": "stop"
        }],
        "usage": {
            "prompt_tokens": sum(len(msg.content.split()) for msg in request.messages),
            "completion_tokens": len(response_text.split()),
            "total_tokens": sum(len(msg.content.split()) for msg in request.messages) + len(response_text.split())
        }
    }


# Mock S3 API
s3_app = FastAPI(title="Mock S3 API")

# In-memory storage for S3 objects
s3_storage: Dict[str, Dict[str, Any]] = {}
s3_buckets: Dict[str, Dict[str, Any]] = {
    "activelog-files": {
        "name": "activelog-files",
        "creation_date": datetime.now(timezone.utc).isoformat()
    }
}

@s3_app.get("/health")
async def s3_health():
    return {"status": "healthy", "service": "mock-s3"}

@s3_app.get("/")
async def list_buckets():
    """List S3 buckets"""
    buckets = [
        {
            "Name": bucket_data["name"],
            "CreationDate": bucket_data["creation_date"]
        }
        for bucket_data in s3_buckets.values()
    ]
    
    return {
        "ListAllMyBucketsResult": {
            "Owner": {
                "DisplayName": "mock-user",
                "ID": "mock-user-id"
            },
            "Buckets": {"Bucket": buckets}
        }
    }

@s3_app.put("/{bucket}")
async def create_bucket(bucket: str):
    """Create S3 bucket"""
    if bucket in s3_buckets:
        raise HTTPException(status_code=409, detail="BucketAlreadyExists")
    
    s3_buckets[bucket] = {
        "name": bucket,
        "creation_date": datetime.now(timezone.utc).isoformat()
    }
    
    return Response(status_code=200, headers={"Location": f"/{bucket}"})

@s3_app.get("/{bucket}")
async def list_objects(bucket: str, prefix: str = "", max_keys: int = 1000):
    """List objects in S3 bucket"""
    if bucket not in s3_buckets:
        raise HTTPException(status_code=404, detail="NoSuchBucket")
    
    # Filter objects by prefix
    objects = []
    for key, obj_data in s3_storage.items():
        bucket_name, object_key = key.split("/", 1)
        if bucket_name == bucket and object_key.startswith(prefix):
            objects.append({
                "Key": object_key,
                "Size": obj_data["size"],
                "ETag": f'"{obj_data["etag"]}"',
                "LastModified": obj_data["last_modified"],
                "StorageClass": "STANDARD"
            })
            
            if len(objects) >= max_keys:
                break
    
    return {
        "ListBucketResult": {
            "Name": bucket,
            "Prefix": prefix,
            "MaxKeys": max_keys,
            "IsTruncated": len(objects) >= max_keys,
            "Contents": objects
        }
    }

@s3_app.put("/{bucket}/{key:path}")
async def put_object(bucket: str, key: str, request: Request):
    """Upload object to S3"""
    if bucket not in s3_buckets:
        raise HTTPException(status_code=404, detail="NoSuchBucket")
    
    # Read request body
    body = await request.body()
    
    # Calculate ETag
    etag = hashlib.md5(body).hexdigest()
    
    # Store object
    storage_key = f"{bucket}/{key}"
    s3_storage[storage_key] = {
        "body": body,
        "etag": etag,
        "size": len(body),
        "last_modified": datetime.now(timezone.utc).isoformat(),
        "content_type": request.headers.get("content-type", "binary/octet-stream"),
        "metadata": {}
    }
    
    return Response(
        status_code=200,
        headers={"ETag": f'"{etag}"'},
        content=""
    )

@s3_app.get("/{bucket}/{key:path}")
async def get_object(bucket: str, key: str):
    """Download object from S3"""
    storage_key = f"{bucket}/{key}"
    
    if storage_key not in s3_storage:
        raise HTTPException(status_code=404, detail="NoSuchKey")
    
    obj_data = s3_storage[storage_key]
    
    return Response(
        content=obj_data["body"],
        media_type=obj_data["content_type"],
        headers={
            "ETag": f'"{obj_data["etag"]}"',
            "Content-Length": str(obj_data["size"]),
            "Last-Modified": obj_data["last_modified"]
        }
    )

@s3_app.delete("/{bucket}/{key:path}")
async def delete_object(bucket: str, key: str):
    """Delete object from S3"""
    storage_key = f"{bucket}/{key}"
    
    if storage_key in s3_storage:
        del s3_storage[storage_key]
    
    return Response(status_code=204)

@s3_app.head("/{bucket}/{key:path}")
async def head_object(bucket: str, key: str):
    """Get object metadata"""
    storage_key = f"{bucket}/{key}"
    
    if storage_key not in s3_storage:
        raise HTTPException(status_code=404, detail="NoSuchKey")
    
    obj_data = s3_storage[storage_key]
    
    return Response(
        status_code=200,
        headers={
            "ETag": f'"{obj_data["etag"]}"',
            "Content-Length": str(obj_data["size"]),
            "Last-Modified": obj_data["last_modified"],
            "Content-Type": obj_data["content_type"]
        }
    )


def run_openai_server():
    """Run mock OpenAI server"""
    uvicorn.run(openai_app, host="0.0.0.0", port=9000, log_level="info")

def run_s3_server():
    """Run mock S3 server"""
    uvicorn.run(s3_app, host="0.0.0.0", port=9001, log_level="info")


if __name__ == "__main__":
    # Start both servers in separate threads
    openai_thread = threading.Thread(target=run_openai_server)
    s3_thread = threading.Thread(target=run_s3_server)
    
    openai_thread.daemon = True
    s3_thread.daemon = True
    
    print("Starting mock OpenAI server on port 9000...")
    openai_thread.start()
    
    print("Starting mock S3 server on port 9001...")
    s3_thread.start()
    
    # Keep main thread alive
    try:
        while True:
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down mock servers...")
        exit(0)