from elasticsearch import AsyncElasticsearch
from typing import Dict, Any, List, Optional
import json
import logging

# Initialize Elasticsearch client
es_client = AsyncElasticsearch(
    hosts=["http://localhost:9200"],
    verify_certs=False,
    ssl_show_warn=False
)

logger = logging.getLogger(__name__)

async def init_elasticsearch():
    """Initialize Elasticsearch indices"""
    try:
        # Create file metadata index
        file_metadata_mapping = {
            "mappings": {
                "properties": {
                    "file_id": {"type": "keyword"},
                    "filename": {
                        "type": "text",
                        "analyzer": "standard",
                        "fields": {
                            "keyword": {"type": "keyword"}
                        }
                    },
                    "file_path": {
                        "type": "text",
                        "analyzer": "standard",
                        "fields": {
                            "keyword": {"type": "keyword"}
                        }
                    },
                    "file_type": {"type": "keyword"},
                    "mime_type": {"type": "keyword"},
                    "file_size": {"type": "long"},
                    "content_text": {
                        "type": "text",
                        "analyzer": "standard"
                    },
                    "tags": {
                        "type": "nested",
                        "properties": {
                            "id": {"type": "keyword"},
                            "name": {"type": "keyword"},
                            "description": {"type": "text"}
                        }
                    },
                    "metadata": {"type": "object"},
                    "created_at": {"type": "date"},
                    "updated_at": {"type": "date"},
                    "indexed_at": {"type": "date"}
                }
            },
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 0,
                "analysis": {
                    "analyzer": {
                        "filename_analyzer": {
                            "type": "custom",
                            "tokenizer": "standard",
                            "filter": ["lowercase", "stop"]
                        }
                    }
                }
            }
        }
        
        # Check if index exists
        if not await es_client.indices.exists(index="file_metadata"):
            await es_client.indices.create(
                index="file_metadata",
                body=file_metadata_mapping
            )
            logger.info("Created file_metadata index")
        
        print("Elasticsearch indices initialized successfully")
        
    except Exception as e:
        logger.error(f"Error initializing Elasticsearch: {e}")
        print(f"Error initializing Elasticsearch: {e}")

class ElasticsearchService:
    @staticmethod
    async def index_file_metadata(metadata_id: str, data: Dict[str, Any]):
        """Index file metadata in Elasticsearch"""
        try:
            await es_client.index(
                index="file_metadata",
                id=metadata_id,
                body=data
            )
            return True
        except Exception as e:
            logger.error(f"Error indexing file metadata {metadata_id}: {e}")
            return False
    
    @staticmethod
    async def update_file_metadata(metadata_id: str, data: Dict[str, Any]):
        """Update file metadata in Elasticsearch"""
        try:
            await es_client.update(
                index="file_metadata",
                id=metadata_id,
                body={"doc": data}
            )
            return True
        except Exception as e:
            logger.error(f"Error updating file metadata {metadata_id}: {e}")
            return False
    
    @staticmethod
    async def delete_file_metadata(metadata_id: str):
        """Delete file metadata from Elasticsearch"""
        try:
            await es_client.delete(
                index="file_metadata",
                id=metadata_id
            )
            return True
        except Exception as e:
            logger.error(f"Error deleting file metadata {metadata_id}: {e}")
            return False
    
    @staticmethod
    async def search_files(
        query: str = None,
        file_type: str = None,
        tags: List[str] = None,
        size: int = 20,
        from_: int = 0
    ) -> Dict[str, Any]:
        """Search files using Elasticsearch"""
        try:
            search_body = {
                "query": {
                    "bool": {
                        "must": [],
                        "filter": []
                    }
                },
                "highlight": {
                    "fields": {
                        "content_text": {},
                        "filename": {}
                    }
                },
                "size": size,
                "from": from_
            }
            
            # Add text query
            if query:
                search_body["query"]["bool"]["must"].append({
                    "multi_match": {
                        "query": query,
                        "fields": ["filename^3", "content_text^2", "file_path"],
                        "type": "best_fields",
                        "fuzziness": "AUTO"
                    }
                })
            else:
                search_body["query"]["bool"]["must"].append({"match_all": {}})
            
            # Add file type filter
            if file_type:
                search_body["query"]["bool"]["filter"].append({
                    "term": {"file_type": file_type}
                })
            
            # Add tags filter
            if tags:
                search_body["query"]["bool"]["filter"].append({
                    "nested": {
                        "path": "tags",
                        "query": {
                            "terms": {"tags.name": tags}
                        }
                    }
                })
            
            response = await es_client.search(
                index="file_metadata",
                body=search_body
            )
            
            return {
                "total": response["hits"]["total"]["value"],
                "results": [
                    {
                        "id": hit["_id"],
                        "score": hit["_score"],
                        "source": hit["_source"],
                        "highlight": hit.get("highlight", {})
                    }
                    for hit in response["hits"]["hits"]
                ]
            }
            
        except Exception as e:
            logger.error(f"Error searching files: {e}")
            return {"total": 0, "results": []}
    
    @staticmethod
    async def suggest_tags(prefix: str, size: int = 10) -> List[str]:
        """Get tag suggestions based on prefix"""
        try:
            search_body = {
                "suggest": {
                    "tag_suggest": {
                        "prefix": prefix,
                        "completion": {
                            "field": "tags.name",
                            "size": size
                        }
                    }
                }
            }
            
            response = await es_client.search(
                index="file_metadata",
                body=search_body
            )
            
            suggestions = []
            for suggestion in response.get("suggest", {}).get("tag_suggest", []):
                for option in suggestion.get("options", []):
                    suggestions.append(option["text"])
            
            return list(set(suggestions))
            
        except Exception as e:
            logger.error(f"Error getting tag suggestions: {e}")
            return []
    
    @staticmethod
    async def aggregate_by_file_type() -> Dict[str, int]:
        """Get file count aggregation by file type"""
        try:
            search_body = {
                "size": 0,
                "aggs": {
                    "file_types": {
                        "terms": {
                            "field": "file_type",
                            "size": 50
                        }
                    }
                }
            }
            
            response = await es_client.search(
                index="file_metadata",
                body=search_body
            )
            
            aggregations = {}
            for bucket in response["aggregations"]["file_types"]["buckets"]:
                aggregations[bucket["key"]] = bucket["doc_count"]
            
            return aggregations
            
        except Exception as e:
            logger.error(f"Error getting file type aggregations: {e}")
            return {}
    
    @staticmethod
    async def get_popular_tags(size: int = 20) -> List[Dict[str, Any]]:
        """Get most popular tags"""
        try:
            search_body = {
                "size": 0,
                "aggs": {
                    "popular_tags": {
                        "nested": {
                            "path": "tags"
                        },
                        "aggs": {
                            "tag_names": {
                                "terms": {
                                    "field": "tags.name",
                                    "size": size
                                }
                            }
                        }
                    }
                }
            }
            
            response = await es_client.search(
                index="file_metadata",
                body=search_body
            )
            
            tags = []
            for bucket in response["aggregations"]["popular_tags"]["tag_names"]["buckets"]:
                tags.append({
                    "name": bucket["key"],
                    "count": bucket["doc_count"]
                })
            
            return tags
            
        except Exception as e:
            logger.error(f"Error getting popular tags: {e}")
            return []