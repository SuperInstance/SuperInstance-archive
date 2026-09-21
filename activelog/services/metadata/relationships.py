import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Dict, Any, Optional
import uuid
import json
from datetime import datetime

from database import get_db, FileMetadataModel

class RelationshipService:
    @staticmethod
    def create_relationship(
        source_file_id: str,
        target_file_id: str,
        relationship_type: str,
        metadata: Dict[str, Any] = None
    ) -> Optional[str]:
        """Create a new relationship between files"""
        conn = get_db()
        cur = conn.cursor()
        
        try:
            relationship_id = str(uuid.uuid4())
            
            cur.execute("""
                INSERT INTO file_relationships (id, source_file_id, target_file_id, relationship_type, metadata)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (source_file_id, target_file_id, relationship_type) 
                DO UPDATE SET 
                    metadata = EXCLUDED.metadata,
                    created_at = CURRENT_TIMESTAMP
                RETURNING id
            """, (
                relationship_id, 
                source_file_id, 
                target_file_id, 
                relationship_type,
                json.dumps(metadata or {})
            ))
            
            result = cur.fetchone()
            conn.commit()
            return result['id'] if result else relationship_id
            
        except Exception as e:
            conn.rollback()
            print(f"Error creating relationship: {e}")
            return None
        finally:
            cur.close()
            conn.close()
    
    @staticmethod
    def get_by_id(relationship_id: str) -> Optional[Dict[str, Any]]:
        """Get relationship by ID with source and target metadata"""
        conn = get_db()
        cur = conn.cursor()
        
        try:
            cur.execute("""
                SELECT 
                    r.*,
                    s.filename as source_filename,
                    s.file_type as source_file_type,
                    t.filename as target_filename,
                    t.file_type as target_file_type
                FROM file_relationships r
                LEFT JOIN file_metadata s ON r.source_file_id = s.id
                LEFT JOIN file_metadata t ON r.target_file_id = t.id
                WHERE r.id = %s
            """, (relationship_id,))
            
            result = cur.fetchone()
            if result:
                result = dict(result)
                # Parse JSON metadata
                if result.get('metadata'):
                    try:
                        result['metadata'] = json.loads(result['metadata'])
                    except:
                        result['metadata'] = {}
                
                # Add source and target metadata
                source_metadata = FileMetadataModel.get_by_id(result['source_file_id'])
                target_metadata = FileMetadataModel.get_by_id(result['target_file_id'])
                
                result['source_metadata'] = source_metadata
                result['target_metadata'] = target_metadata
            
            return result
            
        finally:
            cur.close()
            conn.close()
    
    @staticmethod
    def get_file_relationships(file_metadata_id: str) -> List[Dict[str, Any]]:
        """Get all relationships for a file (both as source and target)"""
        conn = get_db()
        cur = conn.cursor()
        
        try:
            cur.execute("""
                SELECT 
                    r.*,
                    CASE 
                        WHEN r.source_file_id = %s THEN 'outgoing'
                        ELSE 'incoming'
                    END as direction,
                    CASE 
                        WHEN r.source_file_id = %s THEN t.filename
                        ELSE s.filename
                    END as related_filename,
                    CASE 
                        WHEN r.source_file_id = %s THEN t.file_type
                        ELSE s.file_type
                    END as related_file_type,
                    CASE 
                        WHEN r.source_file_id = %s THEN r.target_file_id
                        ELSE r.source_file_id
                    END as related_file_id
                FROM file_relationships r
                LEFT JOIN file_metadata s ON r.source_file_id = s.id
                LEFT JOIN file_metadata t ON r.target_file_id = t.id
                WHERE r.source_file_id = %s OR r.target_file_id = %s
                ORDER BY r.created_at DESC
            """, (file_metadata_id, file_metadata_id, file_metadata_id, file_metadata_id, file_metadata_id, file_metadata_id))
            
            results = cur.fetchall()
            processed_results = []
            
            for result in results:
                result = dict(result)
                # Parse JSON metadata
                if result.get('metadata'):
                    try:
                        result['metadata'] = json.loads(result['metadata'])
                    except:
                        result['metadata'] = {}
                
                # Add full metadata for source and target
                source_metadata = FileMetadataModel.get_by_id(result['source_file_id'])
                target_metadata = FileMetadataModel.get_by_id(result['target_file_id'])
                
                result['source_metadata'] = source_metadata
                result['target_metadata'] = target_metadata
                
                processed_results.append(result)
            
            return processed_results
            
        finally:
            cur.close()
            conn.close()
    
    @staticmethod
    def delete_relationship(relationship_id: str) -> bool:
        """Delete a relationship"""
        conn = get_db()
        cur = conn.cursor()
        
        try:
            cur.execute("DELETE FROM file_relationships WHERE id = %s", (relationship_id,))
            conn.commit()
            return cur.rowcount > 0
        finally:
            cur.close()
            conn.close()
    
    @staticmethod
    def delete_file_relationships(file_metadata_id: str) -> bool:
        """Delete all relationships for a file"""
        conn = get_db()
        cur = conn.cursor()
        
        try:
            cur.execute("""
                DELETE FROM file_relationships 
                WHERE source_file_id = %s OR target_file_id = %s
            """, (file_metadata_id, file_metadata_id))
            conn.commit()
            return cur.rowcount > 0
        finally:
            cur.close()
            conn.close()
    
    @staticmethod
    def get_relationships_by_type(relationship_type: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get all relationships of a specific type"""
        conn = get_db()
        cur = conn.cursor()
        
        try:
            cur.execute("""
                SELECT 
                    r.*,
                    s.filename as source_filename,
                    s.file_type as source_file_type,
                    t.filename as target_filename,
                    t.file_type as target_file_type
                FROM file_relationships r
                LEFT JOIN file_metadata s ON r.source_file_id = s.id
                LEFT JOIN file_metadata t ON r.target_file_id = t.id
                WHERE r.relationship_type = %s
                ORDER BY r.created_at DESC
                LIMIT %s
            """, (relationship_type, limit))
            
            results = cur.fetchall()
            processed_results = []
            
            for result in results:
                result = dict(result)
                # Parse JSON metadata
                if result.get('metadata'):
                    try:
                        result['metadata'] = json.loads(result['metadata'])
                    except:
                        result['metadata'] = {}
                
                # Add full metadata for source and target
                source_metadata = FileMetadataModel.get_by_id(result['source_file_id'])
                target_metadata = FileMetadataModel.get_by_id(result['target_file_id'])
                
                result['source_metadata'] = source_metadata
                result['target_metadata'] = target_metadata
                
                processed_results.append(result)
            
            return processed_results
            
        finally:
            cur.close()
            conn.close()
    
    @staticmethod
    def find_related_files(
        file_metadata_id: str,
        relationship_types: List[str] = None,
        max_depth: int = 2
    ) -> Dict[str, Any]:
        """Find files related to the given file through relationships (with depth)"""
        conn = get_db()
        cur = conn.cursor()
        
        try:
            # Build the recursive CTE query
            type_filter = ""
            params = [file_metadata_id]
            
            if relationship_types:
                placeholders = ','.join(['%s'] * len(relationship_types))
                type_filter = f"AND relationship_type IN ({placeholders})"
                params.extend(relationship_types)
            
            params.append(max_depth)
            
            query = f"""
                WITH RECURSIVE related_files AS (
                    -- Base case: direct relationships
                    SELECT 
                        CASE 
                            WHEN source_file_id = %s THEN target_file_id
                            ELSE source_file_id
                        END as related_file_id,
                        relationship_type,
                        CASE 
                            WHEN source_file_id = %s THEN 'outgoing'
                            ELSE 'incoming'
                        END as direction,
                        1 as depth,
                        ARRAY[%s] as path
                    FROM file_relationships
                    WHERE (source_file_id = %s OR target_file_id = %s)
                    {type_filter}
                    
                    UNION ALL
                    
                    -- Recursive case: relationships of related files
                    SELECT 
                        CASE 
                            WHEN fr.source_file_id = rf.related_file_id THEN fr.target_file_id
                            ELSE fr.source_file_id
                        END as related_file_id,
                        fr.relationship_type,
                        CASE 
                            WHEN fr.source_file_id = rf.related_file_id THEN 'outgoing'
                            ELSE 'incoming'
                        END as direction,
                        rf.depth + 1,
                        rf.path || rf.related_file_id
                    FROM file_relationships fr
                    JOIN related_files rf ON (fr.source_file_id = rf.related_file_id OR fr.target_file_id = rf.related_file_id)
                    WHERE rf.depth < %s
                        AND NOT (rf.related_file_id = ANY(rf.path))  -- Prevent cycles
                        {type_filter}
                )
                SELECT DISTINCT 
                    rf.related_file_id,
                    rf.relationship_type,
                    rf.direction,
                    rf.depth,
                    fm.filename,
                    fm.file_type,
                    fm.file_path
                FROM related_files rf
                LEFT JOIN file_metadata fm ON rf.related_file_id = fm.id
                WHERE rf.related_file_id != %s  -- Exclude the original file
                ORDER BY rf.depth, fm.filename
            """
            
            # Add the original file_id to params for the final WHERE clause
            params.append(file_metadata_id)
            
            # Duplicate the file_metadata_id and relationship_types for the recursive part
            if relationship_types:
                params.insert(-1, file_metadata_id)  # Before the final file_id
                params[1:1] = [file_metadata_id, file_metadata_id]  # Add two more for the base case
                params[4+len(relationship_types)+1:4+len(relationship_types)+1] = relationship_types  # For recursive part
            else:
                params.insert(-1, file_metadata_id)
                params[1:1] = [file_metadata_id, file_metadata_id]
            
            cur.execute(query, params)
            results = cur.fetchall()
            
            # Group results by depth
            by_depth = {}
            for result in results:
                depth = result['depth']
                if depth not in by_depth:
                    by_depth[depth] = []
                by_depth[depth].append(dict(result))
            
            return {
                "file_metadata_id": file_metadata_id,
                "max_depth": max_depth,
                "total_related": len(results),
                "by_depth": by_depth
            }
            
        except Exception as e:
            print(f"Error finding related files: {e}")
            return {
                "file_metadata_id": file_metadata_id,
                "max_depth": max_depth,
                "total_related": 0,
                "by_depth": {}
            }
        finally:
            cur.close()
            conn.close()
    
    @staticmethod
    def get_relationship_stats() -> Dict[str, Any]:
        """Get statistics about relationships"""
        conn = get_db()
        cur = conn.cursor()
        
        try:
            cur.execute("""
                SELECT 
                    relationship_type,
                    COUNT(*) as count,
                    MIN(created_at) as first_created,
                    MAX(created_at) as last_created
                FROM file_relationships
                GROUP BY relationship_type
                ORDER BY count DESC
            """)
            
            type_stats = cur.fetchall()
            
            cur.execute("SELECT COUNT(*) as total_relationships FROM file_relationships")
            total = cur.fetchone()
            
            cur.execute("""
                SELECT COUNT(DISTINCT source_file_id) + COUNT(DISTINCT target_file_id) as files_with_relationships
                FROM file_relationships
            """)
            files_count = cur.fetchone()
            
            return {
                "total_relationships": total['total_relationships'],
                "files_with_relationships": files_count['files_with_relationships'],
                "by_type": [dict(stat) for stat in type_stats]
            }
            
        finally:
            cur.close()
            conn.close()
    
    @staticmethod
    def suggest_relationships(file_metadata_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Suggest potential relationships for a file based on content similarity, file types, etc."""
        # This is a simple implementation - could be enhanced with ML models
        conn = get_db()
        cur = conn.cursor()
        
        try:
            # Get the current file metadata
            current_file = FileMetadataModel.get_by_id(file_metadata_id)
            if not current_file:
                return []
            
            suggestions = []
            
            # Suggest files with similar names
            if current_file.get('filename'):
                filename_parts = current_file['filename'].lower().split('.')
                if len(filename_parts) > 1:
                    base_name = filename_parts[0]
                    
                    cur.execute("""
                        SELECT id, filename, file_type, 'similar_name' as suggested_relationship
                        FROM file_metadata
                        WHERE id != %s
                            AND LOWER(filename) LIKE %s
                            AND id NOT IN (
                                SELECT target_file_id FROM file_relationships WHERE source_file_id = %s
                                UNION
                                SELECT source_file_id FROM file_relationships WHERE target_file_id = %s
                            )
                        LIMIT 5
                    """, (file_metadata_id, f"%{base_name}%", file_metadata_id, file_metadata_id))
                    
                    suggestions.extend(cur.fetchall())
            
            # Suggest files of the same type
            if current_file.get('file_type'):
                cur.execute("""
                    SELECT id, filename, file_type, 'same_type' as suggested_relationship
                    FROM file_metadata
                    WHERE id != %s
                        AND file_type = %s
                        AND id NOT IN (
                            SELECT target_file_id FROM file_relationships WHERE source_file_id = %s
                            UNION
                            SELECT source_file_id FROM file_relationships WHERE target_file_id = %s
                        )
                    ORDER BY created_at DESC
                    LIMIT 5
                """, (file_metadata_id, current_file['file_type'], file_metadata_id, file_metadata_id))
                
                suggestions.extend(cur.fetchall())
            
            # Remove duplicates and limit results
            seen_ids = set()
            unique_suggestions = []
            
            for suggestion in suggestions:
                if suggestion['id'] not in seen_ids:
                    seen_ids.add(suggestion['id'])
                    unique_suggestions.append(dict(suggestion))
                    
                    if len(unique_suggestions) >= limit:
                        break
            
            return unique_suggestions
            
        except Exception as e:
            print(f"Error suggesting relationships: {e}")
            return []
        finally:
            cur.close()
            conn.close()