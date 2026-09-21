#!/usr/bin/env python3
"""
High-Performance Database Connection Pool Manager
Provides async connection pooling for SQLite and PostgreSQL across all services
"""

import asyncio
import aiosqlite
import asyncpg
import redis.asyncio as redis
from typing import Dict, Optional, Any, AsyncContextManager
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
import logging
import os
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

@dataclass
class PoolConfig:
    """Database pool configuration"""
    min_size: int = 5
    max_size: int = 20
    timeout: float = 30.0
    retry_attempts: int = 3
    retry_delay: float = 1.0

class DatabaseConnectionManager:
    """Centralized database connection pool manager for ActiveLog services"""
    
    def __init__(self):
        self.pools: Dict[str, Any] = {}
        self.redis_pools: Dict[str, redis.Redis] = {}
        self.sqlite_pools: Dict[str, aiosqlite.Connection] = {}
        self.config = PoolConfig()
        self._initialized = False
    
    async def initialize(self):
        """Initialize connection pools for all databases"""
        if self._initialized:
            return
        
        try:
            # Initialize PostgreSQL pools
            await self._init_postgres_pools()
            
            # Initialize Redis pools
            await self._init_redis_pools()
            
            # Initialize SQLite connections (managed differently due to file-based nature)
            await self._init_sqlite_pools()
            
            self._initialized = True
            logger.info("Database connection manager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize database connections: {e}")
            raise
    
    async def _init_postgres_pools(self):
        """Initialize PostgreSQL connection pools"""
        postgres_configs = {
            'main': {
                'host': os.getenv('POSTGRES_HOST', 'localhost'),
                'port': int(os.getenv('POSTGRES_PORT', 5432)),
                'database': os.getenv('POSTGRES_DB', 'activelog'),
                'user': os.getenv('POSTGRES_USER', 'activelog_admin'),
                'password': os.getenv('POSTGRES_PASSWORD', 'your_password_here')
            },
            'metadata': {
                'host': os.getenv('METADATA_POSTGRES_HOST', 'localhost'),
                'port': int(os.getenv('METADATA_POSTGRES_PORT', 5432)),
                'database': os.getenv('METADATA_POSTGRES_DB', 'activelog_metadata'),
                'user': os.getenv('METADATA_POSTGRES_USER', 'activelog_admin'),
                'password': os.getenv('METADATA_POSTGRES_PASSWORD', 'your_password_here')
            }
        }
        
        for name, config in postgres_configs.items():
            try:
                pool = await asyncpg.create_pool(
                    host=config['host'],
                    port=config['port'],
                    database=config['database'],
                    user=config['user'],
                    password=config['password'],
                    min_size=self.config.min_size,
                    max_size=self.config.max_size,
                    command_timeout=self.config.timeout
                )
                self.pools[f'postgres_{name}'] = pool
                logger.info(f"PostgreSQL pool '{name}' initialized")
                
            except Exception as e:
                logger.warning(f"Failed to initialize PostgreSQL pool '{name}': {e}")
    
    async def _init_redis_pools(self):
        """Initialize Redis connection pools"""
        redis_configs = {
            'main': {
                'host': os.getenv('REDIS_HOST', 'localhost'),
                'port': int(os.getenv('REDIS_PORT', 6379)),
                'db': 0
            },
            'cache': {
                'host': os.getenv('REDIS_HOST', 'localhost'),
                'port': int(os.getenv('REDIS_PORT', 6379)),
                'db': 1
            },
            'sessions': {
                'host': os.getenv('REDIS_HOST', 'localhost'),
                'port': int(os.getenv('REDIS_PORT', 6379)),
                'db': 2
            }
        }
        
        for name, config in redis_configs.items():
            try:
                pool = redis.Redis(
                    host=config['host'],
                    port=config['port'],
                    db=config['db'],
                    decode_responses=True,
                    socket_keepalive=True,
                    socket_keepalive_options={},
                    health_check_interval=30,
                    retry_on_timeout=True,
                    max_connections=self.config.max_size
                )
                
                # Test connection
                await pool.ping()
                self.redis_pools[name] = pool
                logger.info(f"Redis pool '{name}' initialized")
                
            except Exception as e:
                logger.warning(f"Failed to initialize Redis pool '{name}': {e}")
    
    async def _init_sqlite_pools(self):
        """Initialize SQLite connections (one per common database)"""
        # Common SQLite databases across services
        sqlite_dbs = [
            'auth/auth_data.db',
            'beta-pricing/data/beta_pricing.db',
            'invoice-engine/data/invoice_engine.db',
            'permissions/data/permissions/permissions.json',  # Will handle JSON separately
        ]
        
        base_path = Path('/home/activeloguser/activelog/services')
        
        for db_path in sqlite_dbs:
            if db_path.endswith('.json'):
                continue  # Skip JSON files
            
            full_path = base_path / db_path
            if full_path.exists():
                try:
                    # Create connection pool-like behavior for SQLite
                    conn = await aiosqlite.connect(str(full_path))
                    await conn.execute("PRAGMA journal_mode=WAL")  # Performance optimization
                    await conn.execute("PRAGMA synchronous=NORMAL")  # Balance safety/speed
                    await conn.execute("PRAGMA cache_size=10000")  # 10MB cache
                    await conn.execute("PRAGMA temp_store=memory")  # Use memory for temp
                    await conn.commit()
                    
                    db_name = db_path.replace('/', '_').replace('.db', '')
                    self.sqlite_pools[db_name] = conn
                    logger.info(f"SQLite connection '{db_name}' initialized with optimizations")
                    
                except Exception as e:
                    logger.warning(f"Failed to initialize SQLite connection for {db_path}: {e}")
    
    @asynccontextmanager
    async def get_postgres_connection(self, pool_name: str = 'main') -> AsyncContextManager[asyncpg.Connection]:
        """Get PostgreSQL connection from pool with automatic cleanup"""
        pool_key = f'postgres_{pool_name}'
        if pool_key not in self.pools:
            raise ValueError(f"PostgreSQL pool '{pool_name}' not initialized")
        
        pool = self.pools[pool_key]
        async with pool.acquire() as connection:
            try:
                yield connection
            except Exception as e:
                # Log error but don't reraise to allow connection cleanup
                logger.error(f"PostgreSQL operation error in pool '{pool_name}': {e}")
                raise
    
    async def get_redis_connection(self, pool_name: str = 'main') -> redis.Redis:
        """Get Redis connection"""
        if pool_name not in self.redis_pools:
            raise ValueError(f"Redis pool '{pool_name}' not initialized")
        
        return self.redis_pools[pool_name]
    
    @asynccontextmanager
    async def get_sqlite_connection(self, db_name: str) -> AsyncContextManager[aiosqlite.Connection]:
        """Get SQLite connection with automatic cleanup"""
        if db_name not in self.sqlite_pools:
            # Dynamic connection creation for unknown databases
            base_path = Path('/home/activeloguser/activelog/services')
            potential_paths = [
                base_path / f"{db_name}.db",
                base_path / db_name / "data" / f"{db_name}.db",
                base_path / db_name / f"{db_name}.db"
            ]
            
            for path in potential_paths:
                if path.exists():
                    conn = await aiosqlite.connect(str(path))
                    await conn.execute("PRAGMA journal_mode=WAL")
                    await conn.execute("PRAGMA synchronous=NORMAL")
                    await conn.commit()
                    
                    try:
                        yield conn
                    finally:
                        await conn.close()
                    return
            
            raise ValueError(f"SQLite database '{db_name}' not found")
        
        connection = self.sqlite_pools[db_name]
        yield connection
    
    async def execute_with_retry(self, operation, max_retries: int = 3):
        """Execute database operation with retry logic"""
        last_error = None
        
        for attempt in range(max_retries):
            try:
                return await operation()
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt) * self.config.retry_delay
                    logger.warning(f"Database operation failed (attempt {attempt + 1}/{max_retries}), retrying in {wait_time}s: {e}")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Database operation failed after {max_retries} attempts: {e}")
        
        raise last_error
    
    async def health_check(self) -> Dict[str, bool]:
        """Check health of all connection pools"""
        health_status = {}
        
        # Check PostgreSQL pools
        for name, pool in self.pools.items():
            try:
                async with pool.acquire() as conn:
                    await conn.fetchval("SELECT 1")
                health_status[name] = True
            except Exception as e:
                logger.error(f"Health check failed for {name}: {e}")
                health_status[name] = False
        
        # Check Redis pools
        for name, redis_conn in self.redis_pools.items():
            try:
                await redis_conn.ping()
                health_status[f"redis_{name}"] = True
            except Exception as e:
                logger.error(f"Health check failed for redis_{name}: {e}")
                health_status[f"redis_{name}"] = False
        
        # Check SQLite connections
        for name, conn in self.sqlite_pools.items():
            try:
                await conn.execute("SELECT 1")
                health_status[f"sqlite_{name}"] = True
            except Exception as e:
                logger.error(f"Health check failed for sqlite_{name}: {e}")
                health_status[f"sqlite_{name}"] = False
        
        return health_status
    
    async def get_pool_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics"""
        stats = {}
        
        for name, pool in self.pools.items():
            if hasattr(pool, '_queue'):
                stats[name] = {
                    'size': pool.get_size(),
                    'min_size': pool.get_min_size(),
                    'max_size': pool.get_max_size(),
                    'idle_size': pool.get_idle_size(),
                    'queue_size': pool._queue.qsize()
                }
        
        return stats
    
    async def close_all(self):
        """Close all connection pools"""
        logger.info("Closing all database connection pools...")
        
        # Close PostgreSQL pools
        for name, pool in self.pools.items():
            try:
                await pool.close()
                logger.info(f"Closed PostgreSQL pool: {name}")
            except Exception as e:
                logger.error(f"Error closing PostgreSQL pool {name}: {e}")
        
        # Close Redis connections
        for name, redis_conn in self.redis_pools.items():
            try:
                await redis_conn.close()
                logger.info(f"Closed Redis pool: {name}")
            except Exception as e:
                logger.error(f"Error closing Redis pool {name}: {e}")
        
        # Close SQLite connections
        for name, conn in self.sqlite_pools.items():
            try:
                await conn.close()
                logger.info(f"Closed SQLite connection: {name}")
            except Exception as e:
                logger.error(f"Error closing SQLite connection {name}: {e}")
        
        self._initialized = False
        self.pools.clear()
        self.redis_pools.clear()
        self.sqlite_pools.clear()

# Global connection manager instance
db_manager = DatabaseConnectionManager()

# Convenience functions for services
async def init_db_connections():
    """Initialize database connections - call this in service startup"""
    await db_manager.initialize()

async def close_db_connections():
    """Close database connections - call this in service shutdown"""
    await db_manager.close_all()

def get_postgres_pool(pool_name: str = 'main'):
    """Get PostgreSQL connection context manager"""
    return db_manager.get_postgres_connection(pool_name)

async def get_redis_pool(pool_name: str = 'main'):
    """Get Redis connection"""
    return await db_manager.get_redis_connection(pool_name)

def get_sqlite_pool(db_name: str):
    """Get SQLite connection context manager"""
    return db_manager.get_sqlite_connection(db_name)

async def db_health_check():
    """Check health of all database connections"""
    return await db_manager.health_check()

async def db_stats():
    """Get database connection statistics"""
    return await db_manager.get_pool_stats()