"""
Advanced pagination optimizations for ActiveLog.
Implements cursor-based pagination for better performance on large datasets.
"""
import base64
import json
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass
from abc import ABC, abstractmethod
from datetime import datetime
import asyncio
import logging

logger = logging.getLogger(__name__)


@dataclass
class CursorInfo:
    """Information about cursor position and pagination metadata."""
    cursor: Optional[str]
    has_previous: bool
    has_next: bool
    total_count: Optional[int] = None
    page_info: Optional[Dict[str, Any]] = None


@dataclass
class PaginatedResult:
    """Result container for paginated data."""
    items: List[Any]
    cursor_info: CursorInfo
    metadata: Optional[Dict[str, Any]] = None


class CursorEncoder:
    """Handles encoding/decoding of cursor tokens."""
    
    @staticmethod
    def encode_cursor(data: Dict[str, Any]) -> str:
        """Encode cursor data to base64 string."""
        try:
            json_str = json.dumps(data, default=str)
            encoded = base64.urlsafe_b64encode(json_str.encode()).decode()
            return encoded
        except Exception as e:
            logger.error(f"Failed to encode cursor: {e}")
            raise ValueError("Invalid cursor data")
    
    @staticmethod
    def decode_cursor(cursor: str) -> Dict[str, Any]:
        """Decode base64 cursor string to data."""
        try:
            decoded = base64.urlsafe_b64decode(cursor.encode()).decode()
            return json.loads(decoded)
        except Exception as e:
            logger.error(f"Failed to decode cursor: {e}")
            raise ValueError("Invalid cursor format")


class BasePaginator(ABC):
    """Base class for pagination implementations."""
    
    def __init__(self, page_size: int = 50, max_page_size: int = 1000):
        self.page_size = min(page_size, max_page_size)
        self.max_page_size = max_page_size
    
    @abstractmethod
    async def paginate(
        self,
        cursor: Optional[str] = None,
        limit: Optional[int] = None,
        **kwargs
    ) -> PaginatedResult:
        """Execute pagination query."""
        pass
    
    def validate_limit(self, limit: Optional[int]) -> int:
        """Validate and normalize limit parameter."""
        if limit is None:
            return self.page_size
        return min(max(1, limit), self.max_page_size)


class TimestampCursorPaginator(BasePaginator):
    """Cursor pagination based on timestamp fields."""
    
    def __init__(
        self,
        db_connection,
        table_name: str,
        timestamp_field: str = 'created_at',
        id_field: str = 'id',
        page_size: int = 50,
        max_page_size: int = 1000
    ):
        super().__init__(page_size, max_page_size)
        self.db_connection = db_connection
        self.table_name = table_name
        self.timestamp_field = timestamp_field
        self.id_field = id_field
    
    async def paginate(
        self,
        cursor: Optional[str] = None,
        limit: Optional[int] = None,
        where_clause: str = "",
        where_params: List[Any] = None,
        select_fields: str = "*",
        order_desc: bool = True
    ) -> PaginatedResult:
        """Paginate using timestamp cursor."""
        limit = self.validate_limit(limit)
        where_params = where_params or []
        
        # Build base query
        base_where = where_clause
        cursor_where = ""
        cursor_params = []
        
        # Handle cursor positioning
        if cursor:
            try:
                cursor_data = CursorEncoder.decode_cursor(cursor)
                timestamp = cursor_data['timestamp']
                record_id = cursor_data['id']
                
                if order_desc:
                    cursor_where = f"""
                        AND (
                            {self.timestamp_field} < ${{}} 
                            OR (
                                {self.timestamp_field} = ${{}} 
                                AND {self.id_field} < ${{}}
                            )
                        )
                    """
                else:
                    cursor_where = f"""
                        AND (
                            {self.timestamp_field} > ${{}} 
                            OR (
                                {self.timestamp_field} = ${{}} 
                                AND {self.id_field} > ${{}}
                            )
                        )
                    """
                
                cursor_params = [timestamp, timestamp, record_id]
                
            except Exception as e:
                logger.error(f"Invalid cursor: {e}")
                raise ValueError("Invalid cursor")
        
        # Combine where clauses
        full_where = base_where
        if cursor_where:
            if base_where:
                full_where = f"{base_where} {cursor_where}"
            else:
                full_where = f"WHERE {cursor_where[4:]}"  # Remove "AND "
        
        # Build final query
        order_direction = "DESC" if order_desc else "ASC"
        query = f"""
            SELECT {select_fields}
            FROM {self.table_name}
            {full_where}
            ORDER BY {self.timestamp_field} {order_direction}, {self.id_field} {order_direction}
            LIMIT ${{}}
        """
        
        # Format placeholders
        param_count = len(where_params) + len(cursor_params)
        for i in range(param_count + 1):
            query = query.replace('${}', f'${i + 1}', 1)
        
        # Execute query with one extra item to check for next page
        all_params = where_params + cursor_params + [limit + 1]
        rows = await self.db_connection.fetch(query, *all_params)
        
        # Process results
        has_next = len(rows) > limit
        items = [dict(row) for row in rows[:limit]]
        
        # Create cursor info
        next_cursor = None
        if has_next and items:
            last_item = items[-1]
            next_cursor = CursorEncoder.encode_cursor({
                'timestamp': last_item[self.timestamp_field],
                'id': last_item[self.id_field]
            })
        
        cursor_info = CursorInfo(
            cursor=next_cursor,
            has_previous=cursor is not None,
            has_next=has_next
        )
        
        return PaginatedResult(items=items, cursor_info=cursor_info)


class OffsetPaginator(BasePaginator):
    """Traditional offset-based pagination with optimizations."""
    
    def __init__(
        self,
        db_connection,
        table_name: str,
        page_size: int = 50,
        max_page_size: int = 1000,
        max_offset: int = 10000  # Limit offset to prevent slow queries
    ):
        super().__init__(page_size, max_page_size)
        self.db_connection = db_connection
        self.table_name = table_name
        self.max_offset = max_offset
    
    async def paginate(
        self,
        page: int = 1,
        limit: Optional[int] = None,
        where_clause: str = "",
        where_params: List[Any] = None,
        select_fields: str = "*",
        order_by: str = "created_at DESC",
        count_total: bool = False
    ) -> PaginatedResult:
        """Paginate using offset method."""
        limit = self.validate_limit(limit)
        where_params = where_params or []
        
        # Validate page and calculate offset
        page = max(1, page)
        offset = (page - 1) * limit
        
        if offset > self.max_offset:
            raise ValueError(f"Offset {offset} exceeds maximum allowed {self.max_offset}")
        
        # Build query
        base_query = f"""
            SELECT {select_fields}
            FROM {self.table_name}
            {where_clause}
            ORDER BY {order_by}
            LIMIT ${len(where_params) + 1} OFFSET ${len(where_params) + 2}
        """
        
        # Get total count if requested
        total_count = None
        if count_total:
            count_query = f"""
                SELECT COUNT(*) as total
                FROM {self.table_name}
                {where_clause}
            """
            count_row = await self.db_connection.fetchrow(count_query, *where_params)
            total_count = count_row['total'] if count_row else 0
        
        # Execute main query
        rows = await self.db_connection.fetch(
            base_query, *where_params, limit + 1, offset
        )
        
        # Process results
        has_next = len(rows) > limit
        items = [dict(row) for row in rows[:limit]]
        
        cursor_info = CursorInfo(
            cursor=str(page + 1) if has_next else None,
            has_previous=page > 1,
            has_next=has_next,
            total_count=total_count,
            page_info={
                'current_page': page,
                'per_page': limit,
                'offset': offset
            }
        )
        
        return PaginatedResult(items=items, cursor_info=cursor_info)


class KeysetPaginator(BasePaginator):
    """Keyset pagination for efficient traversal of ordered data."""
    
    def __init__(
        self,
        db_connection,
        table_name: str,
        key_fields: List[str],
        page_size: int = 50,
        max_page_size: int = 1000
    ):
        super().__init__(page_size, max_page_size)
        self.db_connection = db_connection
        self.table_name = table_name
        self.key_fields = key_fields
    
    async def paginate(
        self,
        cursor: Optional[str] = None,
        limit: Optional[int] = None,
        where_clause: str = "",
        where_params: List[Any] = None,
        select_fields: str = "*",
        order_desc: bool = True
    ) -> PaginatedResult:
        """Paginate using keyset method."""
        limit = self.validate_limit(limit)
        where_params = where_params or []
        
        # Build cursor conditions
        cursor_conditions = []
        cursor_params = []
        
        if cursor:
            try:
                cursor_data = CursorEncoder.decode_cursor(cursor)
                
                # Build progressive conditions for multiple key fields
                for i, field in enumerate(self.key_fields):
                    condition_parts = []
                    
                    # Equal conditions for previous fields
                    for j in range(i):
                        prev_field = self.key_fields[j]
                        condition_parts.append(f"{prev_field} = ${{}}")
                        cursor_params.append(cursor_data[prev_field])
                    
                    # Comparison for current field
                    operator = "<" if order_desc else ">"
                    condition_parts.append(f"{field} {operator} ${{}}")
                    cursor_params.append(cursor_data[field])
                    
                    cursor_conditions.append("(" + " AND ".join(condition_parts) + ")")
                
                cursor_where = " OR ".join(cursor_conditions)
                
            except Exception as e:
                logger.error(f"Invalid keyset cursor: {e}")
                raise ValueError("Invalid cursor")
        
        # Combine where clauses
        full_where = where_clause
        if cursor_where:
            if where_clause:
                full_where = f"{where_clause} AND ({cursor_where})"
            else:
                full_where = f"WHERE ({cursor_where})"
        
        # Build order clause
        order_direction = "DESC" if order_desc else "ASC"
        order_fields = [f"{field} {order_direction}" for field in self.key_fields]
        order_clause = "ORDER BY " + ", ".join(order_fields)
        
        # Build final query
        query = f"""
            SELECT {select_fields}
            FROM {self.table_name}
            {full_where}
            {order_clause}
            LIMIT ${{}}
        """
        
        # Format placeholders
        param_count = len(where_params) + len(cursor_params)
        for i in range(param_count + 1):
            query = query.replace('${}', f'${i + 1}', 1)
        
        # Execute query
        all_params = where_params + cursor_params + [limit + 1]
        rows = await self.db_connection.fetch(query, *all_params)
        
        # Process results
        has_next = len(rows) > limit
        items = [dict(row) for row in rows[:limit]]
        
        # Create next cursor
        next_cursor = None
        if has_next and items:
            last_item = items[-1]
            cursor_data = {field: last_item[field] for field in self.key_fields}
            next_cursor = CursorEncoder.encode_cursor(cursor_data)
        
        cursor_info = CursorInfo(
            cursor=next_cursor,
            has_previous=cursor is not None,
            has_next=has_next
        )
        
        return PaginatedResult(items=items, cursor_info=cursor_info)


class FilesPaginator(TimestampCursorPaginator):
    """Specialized paginator for files with additional filtering."""
    
    def __init__(self, db_connection):
        super().__init__(
            db_connection=db_connection,
            table_name='files',
            timestamp_field='updated_at',
            id_field='id'
        )
    
    async def get_user_files(
        self,
        user_id: str,
        cursor: Optional[str] = None,
        limit: Optional[int] = None,
        content_type_filter: Optional[str] = None,
        size_filter: Optional[Tuple[int, int]] = None
    ) -> PaginatedResult:
        """Get paginated user files with filters."""
        where_conditions = ["user_id = $1", "deleted_at IS NULL"]
        where_params = [user_id]
        param_index = 2
        
        # Add content type filter
        if content_type_filter:
            where_conditions.append(f"content_type LIKE ${param_index}")
            where_params.append(f"{content_type_filter}%")
            param_index += 1
        
        # Add size filter
        if size_filter:
            min_size, max_size = size_filter
            where_conditions.append(f"size BETWEEN ${param_index} AND ${param_index + 1}")
            where_params.extend([min_size, max_size])
            param_index += 2
        
        where_clause = "WHERE " + " AND ".join(where_conditions)
        
        select_fields = """
            id, name, size, content_type, created_at, updated_at,
            CASE 
                WHEN size > 104857600 THEN 'large'  -- > 100MB
                WHEN size > 10485760 THEN 'medium'  -- > 10MB
                ELSE 'small'
            END as size_category
        """
        
        return await self.paginate(
            cursor=cursor,
            limit=limit,
            where_clause=where_clause,
            where_params=where_params,
            select_fields=select_fields
        )


class SearchPaginator(BasePaginator):
    """Paginator for search results with relevance scoring."""
    
    def __init__(self, db_connection):
        super().__init__()
        self.db_connection = db_connection
    
    async def search_files(
        self,
        user_id: str,
        search_query: str,
        cursor: Optional[str] = None,
        limit: Optional[int] = None
    ) -> PaginatedResult:
        """Search files with cursor pagination."""
        limit = self.validate_limit(limit)
        
        # Parse cursor for search pagination
        search_after_score = None
        search_after_id = None
        
        if cursor:
            try:
                cursor_data = CursorEncoder.decode_cursor(cursor)
                search_after_score = cursor_data['score']
                search_after_id = cursor_data['id']
            except Exception:
                raise ValueError("Invalid search cursor")
        
        # Build search query
        base_query = """
            WITH search_results AS (
                SELECT 
                    id, name, size, content_type, updated_at,
                    ts_rank(
                        to_tsvector('english', name || ' ' || COALESCE(description, '')), 
                        plainto_tsquery('english', $2)
                    ) as relevance_score
                FROM files
                WHERE user_id = $1 
                  AND deleted_at IS NULL
                  AND to_tsvector('english', name || ' ' || COALESCE(description, '')) 
                      @@ plainto_tsquery('english', $2)
        """
        
        cursor_condition = ""
        params = [user_id, search_query]
        
        if search_after_score is not None:
            cursor_condition = """
                AND (
                    relevance_score < $3 
                    OR (relevance_score = $3 AND id < $4)
                )
            """
            params.extend([search_after_score, search_after_id])
        
        final_query = f"""
            {base_query}
            {cursor_condition}
            )
            SELECT * FROM search_results
            ORDER BY relevance_score DESC, id DESC
            LIMIT ${len(params) + 1}
        """
        
        # Execute with extra item to check for more results
        rows = await self.db_connection.fetch(final_query, *params, limit + 1)
        
        # Process results
        has_next = len(rows) > limit
        items = [dict(row) for row in rows[:limit]]
        
        # Create next cursor
        next_cursor = None
        if has_next and items:
            last_item = items[-1]
            next_cursor = CursorEncoder.encode_cursor({
                'score': last_item['relevance_score'],
                'id': last_item['id']
            })
        
        cursor_info = CursorInfo(
            cursor=next_cursor,
            has_previous=cursor is not None,
            has_next=has_next
        )
        
        return PaginatedResult(items=items, cursor_info=cursor_info)


class PaginationService:
    """Service for managing different pagination strategies."""
    
    def __init__(self, db_connection_manager):
        self.db_manager = db_connection_manager
        self._paginators = {}
    
    def get_files_paginator(self) -> FilesPaginator:
        """Get files paginator instance."""
        if 'files' not in self._paginators:
            self._paginators['files'] = FilesPaginator(None)  # Will set connection per request
        return self._paginators['files']
    
    def get_search_paginator(self) -> SearchPaginator:
        """Get search paginator instance."""
        if 'search' not in self._paginators:
            self._paginators['search'] = SearchPaginator(None)
        return self._paginators['search']
    
    async def paginate_user_files(
        self,
        user_id: str,
        cursor: Optional[str] = None,
        limit: Optional[int] = None,
        **filters
    ) -> PaginatedResult:
        """Paginate user files with connection management."""
        async with self.db_manager.get_postgres_connection() as conn:
            paginator = self.get_files_paginator()
            paginator.db_connection = conn
            return await paginator.get_user_files(
                user_id=user_id,
                cursor=cursor,
                limit=limit,
                **filters
            )
    
    async def search_user_files(
        self,
        user_id: str,
        search_query: str,
        cursor: Optional[str] = None,
        limit: Optional[int] = None
    ) -> PaginatedResult:
        """Search user files with pagination."""
        async with self.db_manager.get_postgres_connection() as conn:
            paginator = self.get_search_paginator()
            paginator.db_connection = conn
            return await paginator.search_files(
                user_id=user_id,
                search_query=search_query,
                cursor=cursor,
                limit=limit
            )


# Global service instance
pagination_service = None


async def initialize_pagination_service(db_connection_manager):
    """Initialize the global pagination service."""
    global pagination_service
    pagination_service = PaginationService(db_connection_manager)
    return pagination_service


def get_pagination_service() -> PaginationService:
    """Get the global pagination service."""
    if pagination_service is None:
        raise RuntimeError("Pagination service not initialized")
    return pagination_service