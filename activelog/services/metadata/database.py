import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
import json
from typing import Optional, Dict, Any, List
import uuid

def get_db():
    return psycopg2.connect(
        host="localhost",
        database="activelog",
        user="activelog_admin",
        password="SecurePass123!",
        cursor_factory=RealDictCursor
    )

def init_db():
    """Initialize database tables for metadata service"""
    conn = get_db()
    cur = conn.cursor()
    
    try:
        # Enable pgvector extension
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
        
        # File metadata table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS file_metadata (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                file_id UUID NOT NULL,
                filename VARCHAR(255) NOT NULL,
                file_path TEXT,
                file_size BIGINT,
                file_type VARCHAR(100),
                mime_type VARCHAR(100),
                checksum VARCHAR(64),
                content_text TEXT,
                metadata JSONB DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                indexed_at TIMESTAMP,
                UNIQUE(file_id)
            )
        """)
        
        # Tags table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS tags (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                name VARCHAR(100) UNIQUE NOT NULL,
                description TEXT,
                color VARCHAR(7),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                usage_count INTEGER DEFAULT 0
            )
        """)
        
        # File-tag relationships
        cur.execute("""
            CREATE TABLE IF NOT EXISTS file_tags (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                file_metadata_id UUID REFERENCES file_metadata(id) ON DELETE CASCADE,
                tag_id UUID REFERENCES tags(id) ON DELETE CASCADE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(file_metadata_id, tag_id)
            )
        """)
        
        # Vector embeddings table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS file_embeddings (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                file_metadata_id UUID REFERENCES file_metadata(id) ON DELETE CASCADE,
                embedding_type VARCHAR(50) NOT NULL,
                vector vector(1536),
                model_name VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(file_metadata_id, embedding_type)
            )
        """)
        
        # File relationships table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS file_relationships (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                source_file_id UUID REFERENCES file_metadata(id) ON DELETE CASCADE,
                target_file_id UUID REFERENCES file_metadata(id) ON DELETE CASCADE,
                relationship_type VARCHAR(50) NOT NULL,
                metadata JSONB DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(source_file_id, target_file_id, relationship_type)
            )
        """)
        
        # Create indexes
        cur.execute("CREATE INDEX IF NOT EXISTS idx_file_metadata_file_id ON file_metadata(file_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_file_metadata_filename ON file_metadata(filename)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_file_metadata_file_type ON file_metadata(file_type)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_file_metadata_content_text ON file_metadata USING gin(to_tsvector('english', content_text))")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_file_metadata_metadata ON file_metadata USING gin(metadata)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_tags_name ON tags(name)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_file_tags_file_metadata_id ON file_tags(file_metadata_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_file_tags_tag_id ON file_tags(tag_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_file_embeddings_file_metadata_id ON file_embeddings(file_metadata_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_file_embeddings_type ON file_embeddings(embedding_type)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_file_relationships_source ON file_relationships(source_file_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_file_relationships_target ON file_relationships(target_file_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_file_relationships_type ON file_relationships(relationship_type)")
        
        # Vector similarity search index
        cur.execute("CREATE INDEX IF NOT EXISTS idx_file_embeddings_vector ON file_embeddings USING ivfflat (vector vector_cosine_ops) WITH (lists = 100)")
        
        conn.commit()
        print("Database tables initialized successfully")
        
    except Exception as e:
        conn.rollback()
        print(f"Error initializing database: {e}")
        raise e
    finally:
        cur.close()
        conn.close()

class FileMetadataModel:
    @staticmethod
    def create(file_id: str, filename: str, **kwargs) -> str:
        conn = get_db()
        cur = conn.cursor()
        
        try:
            metadata_id = str(uuid.uuid4())
            cur.execute("""
                INSERT INTO file_metadata (id, file_id, filename, file_path, file_size, 
                                         file_type, mime_type, checksum, content_text, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                metadata_id, file_id, filename,
                kwargs.get('file_path'), kwargs.get('file_size'),
                kwargs.get('file_type'), kwargs.get('mime_type'),
                kwargs.get('checksum'), kwargs.get('content_text'),
                json.dumps(kwargs.get('metadata', {}))
            ))
            
            conn.commit()
            return metadata_id
            
        except psycopg2.IntegrityError:
            conn.rollback()
            return None
        finally:
            cur.close()
            conn.close()
    
    @staticmethod
    def get_by_id(metadata_id: str) -> Optional[Dict[str, Any]]:
        conn = get_db()
        cur = conn.cursor()
        
        try:
            cur.execute("SELECT * FROM file_metadata WHERE id = %s", (metadata_id,))
            return cur.fetchone()
        finally:
            cur.close()
            conn.close()
    
    @staticmethod
    def get_by_file_id(file_id: str) -> Optional[Dict[str, Any]]:
        conn = get_db()
        cur = conn.cursor()
        
        try:
            cur.execute("SELECT * FROM file_metadata WHERE file_id = %s", (file_id,))
            return cur.fetchone()
        finally:
            cur.close()
            conn.close()
    
    @staticmethod
    def update(metadata_id: str, **kwargs) -> bool:
        conn = get_db()
        cur = conn.cursor()
        
        try:
            set_clauses = []
            params = []
            
            for field in ['filename', 'file_path', 'file_size', 'file_type', 'mime_type', 'checksum', 'content_text']:
                if field in kwargs and kwargs[field] is not None:
                    set_clauses.append(f"{field} = %s")
                    params.append(kwargs[field])
            
            if 'metadata' in kwargs:
                set_clauses.append("metadata = %s")
                params.append(json.dumps(kwargs['metadata']))
            
            if not set_clauses:
                return True
            
            set_clauses.append("updated_at = CURRENT_TIMESTAMP")
            params.append(metadata_id)
            
            query = f"UPDATE file_metadata SET {', '.join(set_clauses)} WHERE id = %s"
            cur.execute(query, params)
            conn.commit()
            
            return cur.rowcount > 0
            
        finally:
            cur.close()
            conn.close()
    
    @staticmethod
    def delete(metadata_id: str) -> bool:
        conn = get_db()
        cur = conn.cursor()
        
        try:
            cur.execute("DELETE FROM file_metadata WHERE id = %s", (metadata_id,))
            conn.commit()
            return cur.rowcount > 0
        finally:
            cur.close()
            conn.close()
    
    @staticmethod
    def list_all(limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        conn = get_db()
        cur = conn.cursor()
        
        try:
            cur.execute("""
                SELECT * FROM file_metadata 
                ORDER BY created_at DESC 
                LIMIT %s OFFSET %s
            """, (limit, offset))
            return cur.fetchall()
        finally:
            cur.close()
            conn.close()

class TagModel:
    @staticmethod
    def create(name: str, description: str = None, color: str = None) -> str:
        conn = get_db()
        cur = conn.cursor()
        
        try:
            tag_id = str(uuid.uuid4())
            cur.execute("""
                INSERT INTO tags (id, name, description, color)
                VALUES (%s, %s, %s, %s)
                RETURNING id
            """, (tag_id, name, description, color))
            
            conn.commit()
            return tag_id
            
        except psycopg2.IntegrityError:
            conn.rollback()
            return None
        finally:
            cur.close()
            conn.close()
    
    @staticmethod
    def get_by_id(tag_id: str) -> Optional[Dict[str, Any]]:
        conn = get_db()
        cur = conn.cursor()
        
        try:
            cur.execute("SELECT * FROM tags WHERE id = %s", (tag_id,))
            return cur.fetchone()
        finally:
            cur.close()
            conn.close()
    
    @staticmethod
    def get_by_name(name: str) -> Optional[Dict[str, Any]]:
        conn = get_db()
        cur = conn.cursor()
        
        try:
            cur.execute("SELECT * FROM tags WHERE name = %s", (name,))
            return cur.fetchone()
        finally:
            cur.close()
            conn.close()
    
    @staticmethod
    def list_all() -> List[Dict[str, Any]]:
        conn = get_db()
        cur = conn.cursor()
        
        try:
            cur.execute("SELECT * FROM tags ORDER BY name")
            return cur.fetchall()
        finally:
            cur.close()
            conn.close()
    
    @staticmethod
    def assign_to_file(file_metadata_id: str, tag_id: str) -> bool:
        conn = get_db()
        cur = conn.cursor()
        
        try:
            cur.execute("""
                INSERT INTO file_tags (file_metadata_id, tag_id)
                VALUES (%s, %s)
                ON CONFLICT (file_metadata_id, tag_id) DO NOTHING
            """, (file_metadata_id, tag_id))
            
            # Update usage count
            cur.execute("""
                UPDATE tags SET usage_count = usage_count + 1 
                WHERE id = %s
            """, (tag_id,))
            
            conn.commit()
            return True
            
        except Exception:
            conn.rollback()
            return False
        finally:
            cur.close()
            conn.close()
    
    @staticmethod
    def remove_from_file(file_metadata_id: str, tag_id: str) -> bool:
        conn = get_db()
        cur = conn.cursor()
        
        try:
            cur.execute("""
                DELETE FROM file_tags 
                WHERE file_metadata_id = %s AND tag_id = %s
            """, (file_metadata_id, tag_id))
            
            if cur.rowcount > 0:
                # Update usage count
                cur.execute("""
                    UPDATE tags SET usage_count = GREATEST(0, usage_count - 1) 
                    WHERE id = %s
                """, (tag_id,))
            
            conn.commit()
            return cur.rowcount > 0
            
        finally:
            cur.close()
            conn.close()
    
    @staticmethod
    def get_file_tags(file_metadata_id: str) -> List[Dict[str, Any]]:
        conn = get_db()
        cur = conn.cursor()
        
        try:
            cur.execute("""
                SELECT t.* FROM tags t
                JOIN file_tags ft ON t.id = ft.tag_id
                WHERE ft.file_metadata_id = %s
                ORDER BY t.name
            """, (file_metadata_id,))
            return cur.fetchall()
        finally:
            cur.close()
            conn.close()