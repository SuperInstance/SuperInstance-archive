# Metadata Service API

The Metadata Service manages file metadata, tags, search indexing, and vector embeddings for semantic search.

## Base URL
```
http://localhost:8002
```

## Endpoints

### File Metadata

#### POST /metadata
Create or update file metadata.

**Headers:**
```
Authorization: Bearer <jwt_token>
```

**Request Body:**
```json
{
  "file_id": "file_unique_id",
  "filename": "document.pdf",
  "file_path": "/uploads/documents/document.pdf",
  "file_size": 1024000,
  "mime_type": "application/pdf",
  "checksum": "sha256_hash",
  "metadata": {
    "title": "Important Document",
    "author": "John Doe",
    "created_date": "2024-01-01T00:00:00Z",
    "modified_date": "2024-01-01T12:00:00Z",
    "description": "This is an important document",
    "keywords": ["important", "document", "pdf"]
  }
}
```

**Response:**
```json
{
  "id": "metadata_id",
  "file_id": "file_unique_id",
  "filename": "document.pdf",
  "status": "indexed",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T12:00:00Z"
}
```

#### GET /metadata/{file_id}
Get metadata for a specific file.

**Headers:**
```
Authorization: Bearer <jwt_token>
```

**Response:**
```json
{
  "id": "metadata_id",
  "file_id": "file_unique_id",
  "filename": "document.pdf",
  "file_path": "/uploads/documents/document.pdf",
  "file_size": 1024000,
  "mime_type": "application/pdf",
  "checksum": "sha256_hash",
  "metadata": {
    "title": "Important Document",
    "author": "John Doe",
    "created_date": "2024-01-01T00:00:00Z",
    "description": "This is an important document"
  },
  "tags": ["work", "important"],
  "embeddings_status": "completed",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T12:00:00Z"
}
```

#### PUT /metadata/{file_id}
Update file metadata.

**Headers:**
```
Authorization: Bearer <jwt_token>
```

**Request Body:**
```json
{
  "metadata": {
    "title": "Updated Document Title",
    "description": "Updated description",
    "keywords": ["updated", "document"]
  }
}
```

**Response:**
```json
{
  "message": "Metadata updated successfully",
  "updated_at": "2024-01-01T12:00:00Z"
}
```

#### DELETE /metadata/{file_id}
Delete file metadata.

**Headers:**
```
Authorization: Bearer <jwt_token>
```

**Response:**
```json
{
  "message": "Metadata deleted successfully"
}
```

### Tags Management

#### GET /tags
Get all available tags.

**Headers:**
```
Authorization: Bearer <jwt_token>
```

**Query Parameters:**
- `search`: Search tag names
- `limit`: Maximum number of tags to return (default: 100)
- `popular`: Return only popular tags (default: false)

**Response:**
```json
{
  "tags": [
    {
      "name": "work",
      "count": 150,
      "color": "#FF5722"
    },
    {
      "name": "important",
      "count": 89,
      "color": "#F44336"
    }
  ],
  "total": 2
}
```

#### POST /tags/{file_id}
Add tags to a file.

**Headers:**
```
Authorization: Bearer <jwt_token>
```

**Request Body:**
```json
{
  "tags": ["work", "important", "project-alpha"]
}
```

**Response:**
```json
{
  "message": "Tags added successfully",
  "tags": ["work", "important", "project-alpha"]
}
```

#### DELETE /tags/{file_id}
Remove tags from a file.

**Headers:**
```
Authorization: Bearer <jwt_token>
```

**Request Body:**
```json
{
  "tags": ["old-tag"]
}
```

**Response:**
```json
{
  "message": "Tags removed successfully"
}
```

### Search

#### GET /search
Search files by text query.

**Headers:**
```
Authorization: Bearer <jwt_token>
```

**Query Parameters:**
- `q`: Search query (required)
- `page`: Page number (default: 1)
- `per_page`: Items per page (default: 20, max: 100)
- `file_types`: Filter by file types (e.g., "pdf,docx")
- `tags`: Filter by tags (e.g., "work,important")
- `date_from`: Filter files from date (ISO format)
- `date_to`: Filter files to date (ISO format)
- `size_min`: Minimum file size in bytes
- `size_max`: Maximum file size in bytes
- `sort`: Sort order (relevance, date_asc, date_desc, size_asc, size_desc)

**Response:**
```json
{
  "results": [
    {
      "file_id": "file_unique_id",
      "filename": "document.pdf",
      "file_path": "/uploads/documents/document.pdf",
      "title": "Important Document",
      "description": "This is an important document",
      "tags": ["work", "important"],
      "score": 0.95,
      "highlights": [
        "This is an <em>important</em> document about work"
      ],
      "created_at": "2024-01-01T00:00:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 1,
    "total_pages": 1
  },
  "facets": {
    "file_types": {
      "pdf": 50,
      "docx": 30,
      "txt": 20
    },
    "tags": {
      "work": 45,
      "important": 25,
      "personal": 30
    }
  }
}
```

#### POST /search/advanced
Advanced search with complex filters.

**Headers:**
```
Authorization: Bearer <jwt_token>
```

**Request Body:**
```json
{
  "query": {
    "bool": {
      "must": [
        {
          "match": {
            "content": "important document"
          }
        }
      ],
      "filter": [
        {
          "terms": {
            "tags": ["work", "project"]
          }
        },
        {
          "range": {
            "file_size": {
              "gte": 1000,
              "lte": 10000000
            }
          }
        }
      ]
    }
  },
  "sort": [
    {
      "_score": {
        "order": "desc"
      }
    },
    {
      "created_at": {
        "order": "desc"
      }
    }
  ],
  "page": 1,
  "per_page": 20
}
```

### Vector Embeddings

#### POST /embeddings/generate
Generate vector embeddings for a file.

**Headers:**
```
Authorization: Bearer <jwt_token>
```

**Request Body:**
```json
{
  "file_id": "file_unique_id",
  "content": "Text content to generate embeddings for",
  "model": "sentence-transformers/all-MiniLM-L6-v2"
}
```

**Response:**
```json
{
  "message": "Embeddings generated successfully",
  "embedding_id": "embedding_unique_id",
  "dimensions": 384,
  "model": "sentence-transformers/all-MiniLM-L6-v2"
}
```

#### POST /embeddings/search
Semantic search using vector similarity.

**Headers:**
```
Authorization: Bearer <jwt_token>
```

**Request Body:**
```json
{
  "query": "Find documents about machine learning projects",
  "limit": 20,
  "threshold": 0.7,
  "include_metadata": true
}
```

**Response:**
```json
{
  "results": [
    {
      "file_id": "file_unique_id",
      "filename": "ml-project.pdf",
      "similarity_score": 0.89,
      "metadata": {
        "title": "Machine Learning Project Report",
        "author": "Data Scientist"
      },
      "tags": ["ml", "project", "research"]
    }
  ],
  "query_embedding_time_ms": 45,
  "search_time_ms": 123
}
```

### Relationships

#### POST /relationships
Create relationships between files.

**Headers:**
```
Authorization: Bearer <jwt_token>
```

**Request Body:**
```json
{
  "source_file_id": "file1_id",
  "target_file_id": "file2_id",
  "relationship_type": "references",
  "metadata": {
    "description": "File 1 references concepts from File 2",
    "strength": 0.85
  }
}
```

**Response:**
```json
{
  "relationship_id": "rel_unique_id",
  "message": "Relationship created successfully"
}
```

#### GET /relationships/{file_id}
Get all relationships for a file.

**Headers:**
```
Authorization: Bearer <jwt_token>
```

**Response:**
```json
{
  "incoming": [
    {
      "relationship_id": "rel1_id",
      "source_file_id": "other_file_id",
      "relationship_type": "references",
      "strength": 0.85
    }
  ],
  "outgoing": [
    {
      "relationship_id": "rel2_id",
      "target_file_id": "another_file_id",
      "relationship_type": "similar_to",
      "strength": 0.92
    }
  ]
}
```

### Batch Operations

#### POST /batch/metadata
Bulk create or update metadata for multiple files.

**Headers:**
```
Authorization: Bearer <jwt_token>
```

**Request Body:**
```json
{
  "operations": [
    {
      "operation": "create",
      "file_id": "file1_id",
      "data": {
        "filename": "doc1.pdf",
        "metadata": {
          "title": "Document 1"
        }
      }
    },
    {
      "operation": "update",
      "file_id": "file2_id",
      "data": {
        "metadata": {
          "title": "Updated Document 2"
        }
      }
    }
  ]
}
```

**Response:**
```json
{
  "batch_id": "batch_unique_id",
  "total_operations": 2,
  "successful": 2,
  "failed": 0,
  "results": [
    {
      "file_id": "file1_id",
      "status": "success"
    },
    {
      "file_id": "file2_id",
      "status": "success"
    }
  ]
}
```

#### GET /batch/{batch_id}/status
Get batch operation status.

**Headers:**
```
Authorization: Bearer <jwt_token>
```

**Response:**
```json
{
  "batch_id": "batch_unique_id",
  "status": "completed",
  "total_operations": 2,
  "successful": 2,
  "failed": 0,
  "progress_percentage": 100,
  "created_at": "2024-01-01T00:00:00Z",
  "completed_at": "2024-01-01T00:05:00Z"
}
```

## Error Codes

| Code | Status | Description |
|------|--------|-------------|
| META001 | 404 | File metadata not found |
| META002 | 400 | Invalid file ID format |
| META003 | 400 | Invalid metadata format |
| META004 | 409 | Metadata already exists |
| META005 | 400 | Invalid search query |
| META006 | 500 | Search index unavailable |
| META007 | 400 | Invalid embedding model |
| META008 | 500 | Embedding generation failed |
| META009 | 400 | Invalid relationship type |
| META010 | 429 | Search rate limit exceeded |

## Search Query Syntax

### Simple Queries
- `word` - Search for exact word
- `"exact phrase"` - Search for exact phrase
- `word1 AND word2` - Both words must be present
- `word1 OR word2` - Either word can be present
- `word1 NOT word2` - First word present, second word absent

### Field-Specific Queries
- `title:word` - Search in title field
- `author:"John Doe"` - Search in author field
- `content:machine learning` - Search in content

### Wildcard and Fuzzy
- `wor*` - Wildcard matching
- `word~` - Fuzzy matching
- `word~2` - Fuzzy matching with edit distance of 2

## Vector Search Models

Available embedding models:
- `sentence-transformers/all-MiniLM-L6-v2` (default, 384 dimensions)
- `sentence-transformers/all-mpnet-base-v2` (768 dimensions)
- `text-embedding-ada-002` (OpenAI, 1536 dimensions)

## Examples

### Search Files
```bash
curl -X GET "http://localhost:8002/search?q=machine%20learning&file_types=pdf&page=1" \
  -H "Authorization: Bearer jwt_token"
```

### Add Metadata
```bash
curl -X POST "http://localhost:8002/metadata" \
  -H "Authorization: Bearer jwt_token" \
  -H "Content-Type: application/json" \
  -d '{
    "file_id": "unique_file_id",
    "filename": "report.pdf",
    "metadata": {
      "title": "Annual Report",
      "author": "Finance Team"
    }
  }'
```

### Semantic Search
```bash
curl -X POST "http://localhost:8002/embeddings/search" \
  -H "Authorization: Bearer jwt_token" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "artificial intelligence research papers",
    "limit": 10,
    "threshold": 0.8
  }'
```