import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Dict, Any, Optional
import uuid
from datetime import datetime

from database import get_db

class EmbeddingService:
    @staticmethod
    def create_embedding(
        file_metadata_id: str,
        embedding_type: str,
        vector: List[float],
        model_name: str = None
    ) -> Optional[str]:
        """Create a new embedding for a file"""
        conn = get_db()
        cur = conn.cursor()
        
        try:
            embedding_id = str(uuid.uuid4())
            
            # Convert list to vector format for PostgreSQL
            vector_str = '[' + ','.join(map(str, vector)) + ']'
            
            cur.execute("""
                INSERT INTO file_embeddings (id, file_metadata_id, embedding_type, vector, model_name)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (file_metadata_id, embedding_type) 
                DO UPDATE SET 
                    vector = EXCLUDED.vector,
                    model_name = EXCLUDED.model_name,
                    created_at = CURRENT_TIMESTAMP
                RETURNING id
            """, (embedding_id, file_metadata_id, embedding_type, vector_str, model_name))
            
            result = cur.fetchone()
            conn.commit()
            return result['id'] if result else embedding_id
            
        except Exception as e:
            conn.rollback()
            print(f"Error creating embedding: {e}")
            return None
        finally:
            cur.close()
            conn.close()
    
    @staticmethod
    def get_by_id(embedding_id: str) -> Optional[Dict[str, Any]]:
        """Get embedding by ID"""
        conn = get_db()
        cur = conn.cursor()
        
        try:
            cur.execute("""
                SELECT id, file_metadata_id, embedding_type, model_name, created_at
                FROM file_embeddings 
                WHERE id = %s
            """, (embedding_id,))
            
            return cur.fetchone()
            
        finally:
            cur.close()
            conn.close()
    
    @staticmethod
    def get_by_file_and_type(file_metadata_id: str, embedding_type: str) -> Optional[Dict[str, Any]]:
        """Get embedding by file metadata ID and type"""
        conn = get_db()
        cur = conn.cursor()
        
        try:
            cur.execute("""
                SELECT id, file_metadata_id, embedding_type, vector, model_name, created_at
                FROM file_embeddings 
                WHERE file_metadata_id = %s AND embedding_type = %s
            """, (file_metadata_id, embedding_type))
            
            result = cur.fetchone()
            if result and result['vector']:
                # Convert vector back to list
                vector_str = str(result['vector'])
                if vector_str.startswith('[') and vector_str.endswith(']'):
                    vector_list = [float(x.strip()) for x in vector_str[1:-1].split(',')]
                    result = dict(result)
                    result['vector'] = vector_list
            
            return result
            
        finally:
            cur.close()
            conn.close()
    
    @staticmethod
    def vector_search(
        vector: List[float],
        embedding_type: str = "text",
        limit: int = 10,
        similarity_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """Perform vector similarity search"""
        conn = get_db()
        cur = conn.cursor()
        
        try:
            # Convert vector to string format
            vector_str = '[' + ','.join(map(str, vector)) + ']'
            
            cur.execute("""
                SELECT 
                    fe.file_metadata_id,
                    1 - (fe.vector <=> %s::vector) as similarity
                FROM file_embeddings fe
                WHERE fe.embedding_type = %s
                    AND 1 - (fe.vector <=> %s::vector) >= %s
                ORDER BY fe.vector <=> %s::vector
                LIMIT %s
            """, (vector_str, embedding_type, vector_str, similarity_threshold, vector_str, limit))
            
            results = cur.fetchall()
            return [dict(result) for result in results]
            
        except Exception as e:
            print(f"Error in vector search: {e}")
            return []
        finally:
            cur.close()
            conn.close()
    
    @staticmethod
    def delete_embedding(embedding_id: str) -> bool:
        """Delete an embedding"""
        conn = get_db()
        cur = conn.cursor()
        
        try:
            cur.execute("DELETE FROM file_embeddings WHERE id = %s", (embedding_id,))
            conn.commit()
            return cur.rowcount > 0
        finally:
            cur.close()
            conn.close()
    
    @staticmethod
    def delete_file_embeddings(file_metadata_id: str) -> bool:
        """Delete all embeddings for a file"""
        conn = get_db()
        cur = conn.cursor()
        
        try:
            cur.execute("DELETE FROM file_embeddings WHERE file_metadata_id = %s", (file_metadata_id,))
            conn.commit()
            return cur.rowcount > 0
        finally:
            cur.close()
            conn.close()
    
    @staticmethod
    def get_file_embeddings(file_metadata_id: str) -> List[Dict[str, Any]]:
        """Get all embeddings for a file"""
        conn = get_db()
        cur = conn.cursor()
        
        try:
            cur.execute("""
                SELECT id, file_metadata_id, embedding_type, model_name, created_at
                FROM file_embeddings 
                WHERE file_metadata_id = %s
                ORDER BY created_at DESC
            """, (file_metadata_id,))
            
            return cur.fetchall()
            
        finally:
            cur.close()
            conn.close()
    
    @staticmethod
    def find_similar_files(
        file_metadata_id: str,
        embedding_type: str = "text",
        limit: int = 10,
        similarity_threshold: float = 0.8
    ) -> List[Dict[str, Any]]:
        """Find files similar to the given file"""
        # First get the embedding for the given file
        embedding = EmbeddingService.get_by_file_and_type(file_metadata_id, embedding_type)
        if not embedding or not embedding.get('vector'):
            return []
        
        # Search for similar vectors, excluding the original file
        conn = get_db()
        cur = conn.cursor()
        
        try:
            vector_str = '[' + ','.join(map(str, embedding['vector'])) + ']'
            
            cur.execute("""
                SELECT 
                    fe.file_metadata_id,
                    1 - (fe.vector <=> %s::vector) as similarity
                FROM file_embeddings fe
                WHERE fe.embedding_type = %s
                    AND fe.file_metadata_id != %s
                    AND 1 - (fe.vector <=> %s::vector) >= %s
                ORDER BY fe.vector <=> %s::vector
                LIMIT %s
            """, (vector_str, embedding_type, file_metadata_id, vector_str, similarity_threshold, vector_str, limit))
            
            results = cur.fetchall()
            return [dict(result) for result in results]
            
        except Exception as e:
            print(f"Error finding similar files: {e}")
            return []
        finally:
            cur.close()
            conn.close()
    
    @staticmethod
    def get_embedding_stats() -> Dict[str, Any]:
        """Get statistics about embeddings"""
        conn = get_db()
        cur = conn.cursor()
        
        try:
            cur.execute("""
                SELECT 
                    embedding_type,
                    COUNT(*) as count,
                    COUNT(DISTINCT file_metadata_id) as unique_files,
                    MIN(created_at) as first_created,
                    MAX(created_at) as last_created
                FROM file_embeddings
                GROUP BY embedding_type
                ORDER BY count DESC
            """)
            
            type_stats = cur.fetchall()
            
            cur.execute("SELECT COUNT(*) as total_embeddings FROM file_embeddings")
            total = cur.fetchone()
            
            return {
                "total_embeddings": total['total_embeddings'],
                "by_type": [dict(stat) for stat in type_stats]
            }
            
        finally:
            cur.close()
            conn.close()