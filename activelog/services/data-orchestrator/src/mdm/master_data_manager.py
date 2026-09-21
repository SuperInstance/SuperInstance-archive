"""
Master Data Management Engine
Handles data deduplication, golden record creation, and cross-service data synchronization
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set, Tuple
import hashlib
import json
from dataclasses import dataclass, field
from collections import defaultdict
import difflib
import structlog
import aiohttp
from sqlalchemy import create_engine, Column, String, DateTime, Integer, JSON, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import redis.asyncio as redis
from fuzzywuzzy import fuzz

logger = structlog.get_logger(__name__)

Base = declarative_base()

class MasterRecord(Base):
    __tablename__ = 'master_records'
    
    id = Column(String, primary_key=True)
    entity_type = Column(String, nullable=False)
    golden_data = Column(JSON, nullable=False)
    confidence_score = Column(Integer, default=100)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    source_systems = Column(JSON, default=list)
    is_active = Column(Boolean, default=True)
    version = Column(Integer, default=1)

class DuplicateRecord(Base):
    __tablename__ = 'duplicate_records'
    
    id = Column(String, primary_key=True)
    master_id = Column(String, nullable=False)
    entity_type = Column(String, nullable=False)
    source_system = Column(String, nullable=False)
    source_data = Column(JSON, nullable=False)
    similarity_score = Column(Integer, nullable=False)
    status = Column(String, default='linked')  # linked, unlinked, pending_review
    created_at = Column(DateTime, default=datetime.utcnow)

class DataLineage(Base):
    __tablename__ = 'data_lineage'
    
    id = Column(String, primary_key=True)
    source_system = Column(String, nullable=False)
    target_system = Column(String, nullable=False)
    entity_type = Column(String, nullable=False)
    entity_id = Column(String, nullable=False)
    transformation_rules = Column(JSON, default=dict)
    sync_status = Column(String, default='pending')  # pending, synced, failed
    last_sync = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

@dataclass
class MatchRule:
    entity_type: str
    fields: List[str]
    weights: Dict[str, float] = field(default_factory=dict)
    threshold: float = 0.8
    exact_match_fields: List[str] = field(default_factory=list)
    fuzzy_match_fields: List[str] = field(default_factory=list)

@dataclass
class SyncRule:
    source_system: str
    target_system: str
    entity_type: str
    field_mappings: Dict[str, str]
    transformation_rules: Dict[str, str] = field(default_factory=dict)
    sync_frequency: str = "hourly"  # hourly, daily, weekly, real-time
    enabled: bool = True

class MasterDataManager:
    """
    Master Data Management Engine
    
    Provides:
    - Data deduplication using fuzzy matching
    - Golden record creation and maintenance
    - Cross-service data synchronization
    - Data lineage tracking
    - Conflict resolution
    - Data quality enforcement
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.db_engine = create_engine(config.get('database_url', 'sqlite:///mdm.db'))
        Base.metadata.create_all(self.db_engine)
        self.Session = sessionmaker(bind=self.db_engine)
        
        self.redis_client = None
        self.match_rules: Dict[str, MatchRule] = {}
        self.sync_rules: Dict[str, List[SyncRule]] = defaultdict(list)
        self.service_endpoints = config.get('service_endpoints', {})
        
        self._setup_default_rules()
        
    async def initialize(self):
        """Initialize async components"""
        redis_url = self.config.get('redis_url', 'redis://localhost:6379')
        self.redis_client = redis.from_url(redis_url)
        
        logger.info("Master Data Manager initialized")
        
    def _setup_default_rules(self):
        """Setup default matching and sync rules for DMLog entities"""
        
        # User matching rules
        self.match_rules['user'] = MatchRule(
            entity_type='user',
            fields=['email', 'username', 'full_name'],
            weights={'email': 0.6, 'username': 0.3, 'full_name': 0.1},
            threshold=0.85,
            exact_match_fields=['email'],
            fuzzy_match_fields=['username', 'full_name']
        )
        
        # Character matching rules
        self.match_rules['character'] = MatchRule(
            entity_type='character',
            fields=['name', 'class', 'race', 'owner_id'],
            weights={'name': 0.4, 'owner_id': 0.4, 'class': 0.1, 'race': 0.1},
            threshold=0.8,
            exact_match_fields=['owner_id'],
            fuzzy_match_fields=['name']
        )
        
        # Campaign matching rules
        self.match_rules['campaign'] = MatchRule(
            entity_type='campaign',
            fields=['name', 'dm_id', 'system'],
            weights={'name': 0.5, 'dm_id': 0.4, 'system': 0.1},
            threshold=0.85,
            exact_match_fields=['dm_id'],
            fuzzy_match_fields=['name']
        )
        
        # Session matching rules
        self.match_rules['session'] = MatchRule(
            entity_type='session',
            fields=['campaign_id', 'session_number', 'date'],
            weights={'campaign_id': 0.6, 'session_number': 0.3, 'date': 0.1},
            threshold=0.9,
            exact_match_fields=['campaign_id', 'session_number']
        )
        
        # Default sync rules between services
        services = ['dmlog-core', 'character-ai', 'world-builder', 'battle-simulator', 
                   'session-manager', 'marketplace', 'voice-synthesis']
        
        for source in services:
            for target in services:
                if source != target:
                    self.sync_rules[source].append(SyncRule(
                        source_system=source,
                        target_system=target,
                        entity_type='user',
                        field_mappings={
                            'id': 'user_id',
                            'email': 'email',
                            'username': 'username',
                            'profile': 'user_profile'
                        },
                        sync_frequency='real-time'
                    ))
        
    async def process_entity(self, entity_type: str, entity_data: Dict[str, Any], 
                           source_system: str) -> Dict[str, Any]:
        """
        Process an entity for deduplication and master record management
        
        Returns:
        - master_id: ID of the master record
        - is_duplicate: Whether this was identified as a duplicate
        - confidence: Matching confidence score
        """
        try:
            entity_id = entity_data.get('id') or self._generate_id(entity_data)
            
            # Find potential duplicates
            duplicates = await self._find_duplicates(entity_type, entity_data, source_system)
            
            if duplicates:
                # Handle duplicate found
                best_match = max(duplicates, key=lambda x: x['similarity_score'])
                
                if best_match['similarity_score'] >= self.match_rules[entity_type].threshold * 100:
                    # High confidence match - link to existing master
                    master_id = best_match['master_id']
                    await self._link_duplicate(entity_id, master_id, entity_type, 
                                             source_system, entity_data, best_match['similarity_score'])
                    
                    # Update master record with new data
                    await self._update_master_record(master_id, entity_data, source_system)
                    
                    logger.info(f"Linked duplicate {entity_type}", 
                              entity_id=entity_id, master_id=master_id, 
                              confidence=best_match['similarity_score'])
                    
                    return {
                        'master_id': master_id,
                        'is_duplicate': True,
                        'confidence': best_match['similarity_score'],
                        'action': 'linked'
                    }
                else:
                    # Low confidence - create new master but flag for review
                    master_id = await self._create_master_record(entity_type, entity_data, source_system)
                    
                    await self._flag_for_review(entity_id, best_match['master_id'], 
                                              entity_type, best_match['similarity_score'])
                    
                    return {
                        'master_id': master_id,
                        'is_duplicate': False,
                        'confidence': 100,
                        'action': 'flagged_for_review',
                        'potential_duplicate': best_match['master_id']
                    }
            else:
                # No duplicates found - create new master record
                master_id = await self._create_master_record(entity_type, entity_data, source_system)
                
                logger.info(f"Created new master {entity_type}", 
                          entity_id=entity_id, master_id=master_id)
                
                return {
                    'master_id': master_id,
                    'is_duplicate': False,
                    'confidence': 100,
                    'action': 'created'
                }
                
        except Exception as e:
            logger.error(f"Error processing {entity_type} entity", 
                        entity_id=entity_data.get('id'), error=str(e))
            raise
            
    async def _find_duplicates(self, entity_type: str, entity_data: Dict[str, Any], 
                             source_system: str) -> List[Dict[str, Any]]:
        """Find potential duplicate entities using fuzzy matching"""
        
        if entity_type not in self.match_rules:
            return []
            
        rule = self.match_rules[entity_type]
        
        with self.Session() as session:
            # Get existing master records of the same type
            existing_records = session.query(MasterRecord).filter(
                MasterRecord.entity_type == entity_type,
                MasterRecord.is_active == True
            ).all()
            
            duplicates = []
            
            for record in existing_records:
                similarity_score = self._calculate_similarity(
                    entity_data, record.golden_data, rule
                )
                
                if similarity_score > 0.5:  # Minimum similarity threshold
                    duplicates.append({
                        'master_id': record.id,
                        'similarity_score': int(similarity_score * 100),
                        'golden_data': record.golden_data
                    })
                    
            return sorted(duplicates, key=lambda x: x['similarity_score'], reverse=True)
            
    def _calculate_similarity(self, data1: Dict[str, Any], data2: Dict[str, Any], 
                            rule: MatchRule) -> float:
        """Calculate similarity score between two entities"""
        
        total_score = 0.0
        total_weight = 0.0
        
        for field in rule.fields:
            weight = rule.weights.get(field, 1.0 / len(rule.fields))
            total_weight += weight
            
            val1 = str(data1.get(field, ''))
            val2 = str(data2.get(field, ''))
            
            if not val1 or not val2:
                continue
                
            if field in rule.exact_match_fields:
                # Exact match required
                field_score = 1.0 if val1.lower() == val2.lower() else 0.0
            elif field in rule.fuzzy_match_fields:
                # Fuzzy string matching
                field_score = fuzz.ratio(val1.lower(), val2.lower()) / 100.0
            else:
                # Default fuzzy matching
                field_score = fuzz.token_sort_ratio(val1.lower(), val2.lower()) / 100.0
                
            total_score += field_score * weight
            
        return total_score / total_weight if total_weight > 0 else 0.0
        
    async def _create_master_record(self, entity_type: str, entity_data: Dict[str, Any], 
                                  source_system: str) -> str:
        """Create a new master record"""
        
        master_id = self._generate_id(entity_data, prefix='master')
        
        with self.Session() as session:
            master_record = MasterRecord(
                id=master_id,
                entity_type=entity_type,
                golden_data=entity_data,
                confidence_score=100,
                source_systems=[source_system]
            )
            
            session.add(master_record)
            session.commit()
            
        # Cache in Redis for fast access
        await self.redis_client.hset(
            f"master:{entity_type}:{master_id}",
            mapping={
                'data': json.dumps(entity_data),
                'source_systems': json.dumps([source_system]),
                'updated_at': datetime.utcnow().isoformat()
            }
        )
        
        return master_id
        
    async def _update_master_record(self, master_id: str, new_data: Dict[str, Any], 
                                  source_system: str):
        """Update master record with new data from source system"""
        
        with self.Session() as session:
            record = session.query(MasterRecord).filter(MasterRecord.id == master_id).first()
            
            if record:
                # Merge data (simple merge strategy - can be enhanced)
                merged_data = {**record.golden_data, **new_data}
                
                # Update source systems
                source_systems = set(record.source_systems or [])
                source_systems.add(source_system)
                
                record.golden_data = merged_data
                record.source_systems = list(source_systems)
                record.updated_at = datetime.utcnow()
                record.version += 1
                
                session.commit()
                
                # Update Redis cache
                await self.redis_client.hset(
                    f"master:{record.entity_type}:{master_id}",
                    mapping={
                        'data': json.dumps(merged_data),
                        'source_systems': json.dumps(list(source_systems)),
                        'updated_at': datetime.utcnow().isoformat()
                    }
                )
                
    async def _link_duplicate(self, entity_id: str, master_id: str, entity_type: str, 
                            source_system: str, source_data: Dict[str, Any], 
                            similarity_score: int):
        """Link a duplicate entity to its master record"""
        
        duplicate_id = f"{source_system}:{entity_id}"
        
        with self.Session() as session:
            duplicate_record = DuplicateRecord(
                id=duplicate_id,
                master_id=master_id,
                entity_type=entity_type,
                source_system=source_system,
                source_data=source_data,
                similarity_score=similarity_score,
                status='linked'
            )
            
            session.add(duplicate_record)
            session.commit()
            
    async def _flag_for_review(self, entity_id: str, potential_master_id: str, 
                             entity_type: str, similarity_score: int):
        """Flag potential duplicate for manual review"""
        
        review_key = f"review:{entity_type}:{entity_id}"
        review_data = {
            'entity_id': entity_id,
            'potential_master_id': potential_master_id,
            'similarity_score': similarity_score,
            'created_at': datetime.utcnow().isoformat(),
            'status': 'pending_review'
        }
        
        await self.redis_client.hset(review_key, mapping=review_data)
        await self.redis_client.sadd('pending_reviews', review_key)
        
    async def synchronize_entities(self, entity_type: str, source_system: str, 
                                 target_systems: List[str] = None) -> Dict[str, Any]:
        """
        Synchronize entities across systems based on sync rules
        """
        try:
            if target_systems is None:
                target_systems = [rule.target_system for rule in self.sync_rules[source_system]]
                
            sync_results = {
                'synced': 0,
                'failed': 0,
                'skipped': 0,
                'details': []
            }
            
            # Get entities to sync from source system
            entities = await self._fetch_entities_from_source(source_system, entity_type)
            
            for entity in entities:
                master_result = await self.process_entity(entity_type, entity, source_system)
                master_id = master_result['master_id']
                
                # Sync to target systems
                for target_system in target_systems:
                    sync_rule = self._get_sync_rule(source_system, target_system, entity_type)
                    
                    if sync_rule and sync_rule.enabled:
                        try:
                            success = await self._sync_to_target(
                                master_id, entity, sync_rule, target_system
                            )
                            
                            if success:
                                sync_results['synced'] += 1
                                await self._record_sync_lineage(
                                    source_system, target_system, entity_type, 
                                    entity.get('id'), 'synced'
                                )
                            else:
                                sync_results['failed'] += 1
                                await self._record_sync_lineage(
                                    source_system, target_system, entity_type, 
                                    entity.get('id'), 'failed'
                                )
                                
                        except Exception as e:
                            sync_results['failed'] += 1
                            logger.error(f"Sync failed for {entity_type}", 
                                       source=source_system, target=target_system, 
                                       entity_id=entity.get('id'), error=str(e))
                    else:
                        sync_results['skipped'] += 1
                        
            logger.info(f"Synchronization completed for {entity_type}", 
                      source=source_system, results=sync_results)
                      
            return sync_results
            
        except Exception as e:
            logger.error(f"Synchronization failed for {entity_type}", 
                        source=source_system, error=str(e))
            raise
            
    def _get_sync_rule(self, source_system: str, target_system: str, 
                      entity_type: str) -> Optional[SyncRule]:
        """Get sync rule for specific source -> target -> entity combination"""
        
        for rule in self.sync_rules.get(source_system, []):
            if rule.target_system == target_system and rule.entity_type == entity_type:
                return rule
        return None
        
    async def _fetch_entities_from_source(self, source_system: str, 
                                        entity_type: str) -> List[Dict[str, Any]]:
        """Fetch entities from source system API"""
        
        endpoint = self.service_endpoints.get(source_system)
        if not endpoint:
            logger.warning(f"No endpoint configured for {source_system}")
            return []
            
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{endpoint}/api/{entity_type}"
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get('data', [])
                    else:
                        logger.error(f"Failed to fetch {entity_type} from {source_system}", 
                                   status=response.status)
                        return []
                        
        except Exception as e:
            logger.error(f"Error fetching entities from {source_system}", error=str(e))
            return []
            
    async def _sync_to_target(self, master_id: str, entity_data: Dict[str, Any], 
                            sync_rule: SyncRule, target_system: str) -> bool:
        """Sync entity to target system"""
        
        endpoint = self.service_endpoints.get(target_system)
        if not endpoint:
            return False
            
        try:
            # Transform data according to sync rule
            transformed_data = self._transform_data(entity_data, sync_rule)
            
            async with aiohttp.ClientSession() as session:
                url = f"{endpoint}/api/{sync_rule.entity_type}/sync"
                async with session.post(url, json={
                    'master_id': master_id,
                    'data': transformed_data,
                    'source_system': sync_rule.source_system
                }) as response:
                    return response.status in [200, 201]
                    
        except Exception as e:
            logger.error(f"Error syncing to {target_system}", error=str(e))
            return False
            
    def _transform_data(self, data: Dict[str, Any], sync_rule: SyncRule) -> Dict[str, Any]:
        """Transform data according to sync rule mappings"""
        
        transformed = {}
        
        for source_field, target_field in sync_rule.field_mappings.items():
            if source_field in data:
                value = data[source_field]
                
                # Apply transformation rules if any
                if target_field in sync_rule.transformation_rules:
                    transform_rule = sync_rule.transformation_rules[target_field]
                    # Simple transformation rules (can be enhanced)
                    if transform_rule == 'uppercase':
                        value = str(value).upper()
                    elif transform_rule == 'lowercase':
                        value = str(value).lower()
                        
                transformed[target_field] = value
                
        return transformed
        
    async def _record_sync_lineage(self, source_system: str, target_system: str, 
                                 entity_type: str, entity_id: str, status: str):
        """Record data lineage for sync operation"""
        
        lineage_id = f"{source_system}:{target_system}:{entity_type}:{entity_id}"
        
        with self.Session() as session:
            lineage = session.query(DataLineage).filter(
                DataLineage.id == lineage_id
            ).first()
            
            if lineage:
                lineage.sync_status = status
                lineage.last_sync = datetime.utcnow()
            else:
                lineage = DataLineage(
                    id=lineage_id,
                    source_system=source_system,
                    target_system=target_system,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    sync_status=status,
                    last_sync=datetime.utcnow()
                )
                session.add(lineage)
                
            session.commit()
            
    async def get_master_record(self, master_id: str) -> Optional[Dict[str, Any]]:
        """Get master record by ID"""
        
        # Try Redis cache first
        cached = await self.redis_client.hgetall(f"master:*:{master_id}")
        if cached:
            return {
                'master_id': master_id,
                'data': json.loads(cached.get('data', '{}')),
                'source_systems': json.loads(cached.get('source_systems', '[]')),
                'updated_at': cached.get('updated_at')
            }
            
        # Fallback to database
        with self.Session() as session:
            record = session.query(MasterRecord).filter(
                MasterRecord.id == master_id
            ).first()
            
            if record:
                return {
                    'master_id': record.id,
                    'entity_type': record.entity_type,
                    'data': record.golden_data,
                    'confidence_score': record.confidence_score,
                    'source_systems': record.source_systems,
                    'version': record.version,
                    'created_at': record.created_at.isoformat(),
                    'updated_at': record.updated_at.isoformat()
                }
                
        return None
        
    async def get_duplicates(self, master_id: str) -> List[Dict[str, Any]]:
        """Get all duplicates linked to a master record"""
        
        with self.Session() as session:
            duplicates = session.query(DuplicateRecord).filter(
                DuplicateRecord.master_id == master_id
            ).all()
            
            return [
                {
                    'id': dup.id,
                    'source_system': dup.source_system,
                    'source_data': dup.source_data,
                    'similarity_score': dup.similarity_score,
                    'status': dup.status,
                    'created_at': dup.created_at.isoformat()
                }
                for dup in duplicates
            ]
            
    async def resolve_conflict(self, master_id: str, resolution_data: Dict[str, Any]) -> bool:
        """Manually resolve data conflicts for a master record"""
        
        try:
            with self.Session() as session:
                record = session.query(MasterRecord).filter(
                    MasterRecord.id == master_id
                ).first()
                
                if record:
                    record.golden_data = resolution_data
                    record.updated_at = datetime.utcnow()
                    record.version += 1
                    record.confidence_score = 100  # Manual resolution = high confidence
                    
                    session.commit()
                    
                    # Update cache
                    await self.redis_client.hset(
                        f"master:{record.entity_type}:{master_id}",
                        mapping={
                            'data': json.dumps(resolution_data),
                            'updated_at': datetime.utcnow().isoformat()
                        }
                    )
                    
                    logger.info(f"Conflict resolved for master record {master_id}")
                    return True
                    
            return False
            
        except Exception as e:
            logger.error(f"Error resolving conflict for {master_id}", error=str(e))
            return False
            
    async def get_pending_reviews(self) -> List[Dict[str, Any]]:
        """Get entities pending manual review"""
        
        review_keys = await self.redis_client.smembers('pending_reviews')
        reviews = []
        
        for key in review_keys:
            review_data = await self.redis_client.hgetall(key)
            if review_data:
                reviews.append({
                    'key': key,
                    **review_data
                })
                
        return reviews
        
    async def approve_review(self, review_key: str, action: str) -> bool:
        """Approve or reject a pending review"""
        
        try:
            review_data = await self.redis_client.hgetall(review_key)
            
            if action == 'approve':
                # Link the entities
                await self._link_duplicate(
                    review_data['entity_id'],
                    review_data['potential_master_id'],
                    review_key.split(':')[1],  # entity_type
                    'manual_review',
                    {},  # source_data would need to be stored
                    int(review_data['similarity_score'])
                )
            
            # Remove from pending reviews
            await self.redis_client.srem('pending_reviews', review_key)
            await self.redis_client.delete(review_key)
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing review {review_key}", error=str(e))
            return False
            
    def _generate_id(self, data: Dict[str, Any], prefix: str = '') -> str:
        """Generate a unique ID for an entity"""
        
        # Create hash from key fields
        key_data = json.dumps(data, sort_keys=True)
        hash_value = hashlib.md5(key_data.encode()).hexdigest()[:12]
        
        if prefix:
            return f"{prefix}_{hash_value}_{int(datetime.utcnow().timestamp())}"
        else:
            return f"{hash_value}_{int(datetime.utcnow().timestamp())}"
            
    async def get_statistics(self) -> Dict[str, Any]:
        """Get MDM statistics and metrics"""
        
        with self.Session() as session:
            # Master records stats
            total_masters = session.query(MasterRecord).filter(
                MasterRecord.is_active == True
            ).count()
            
            masters_by_type = session.query(
                MasterRecord.entity_type,
                session.query(MasterRecord).filter(
                    MasterRecord.entity_type == MasterRecord.entity_type,
                    MasterRecord.is_active == True
                ).count().label('count')
            ).group_by(MasterRecord.entity_type).all()
            
            # Duplicate records stats
            total_duplicates = session.query(DuplicateRecord).count()
            
            duplicates_by_status = session.query(
                DuplicateRecord.status,
                session.query(DuplicateRecord).filter(
                    DuplicateRecord.status == DuplicateRecord.status
                ).count().label('count')
            ).group_by(DuplicateRecord.status).all()
            
            # Data lineage stats
            recent_syncs = session.query(DataLineage).filter(
                DataLineage.last_sync > datetime.utcnow() - timedelta(hours=24)
            ).count()
            
            failed_syncs = session.query(DataLineage).filter(
                DataLineage.sync_status == 'failed'
            ).count()
            
        # Pending reviews
        pending_reviews = len(await self.redis_client.smembers('pending_reviews'))
        
        return {
            'master_records': {
                'total': total_masters,
                'by_type': {row.entity_type: row.count for row in masters_by_type}
            },
            'duplicate_records': {
                'total': total_duplicates,
                'by_status': {row.status: row.count for row in duplicates_by_status}
            },
            'synchronization': {
                'recent_syncs_24h': recent_syncs,
                'failed_syncs': failed_syncs
            },
            'pending_reviews': pending_reviews,
            'data_quality': {
                'deduplication_rate': (total_duplicates / (total_masters + total_duplicates) * 100) if (total_masters + total_duplicates) > 0 else 0,
                'sync_success_rate': ((recent_syncs - failed_syncs) / recent_syncs * 100) if recent_syncs > 0 else 0
            }
        }
        
    async def cleanup_old_data(self, retention_days: int = 90):
        """Clean up old duplicate and lineage records"""
        
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
        
        with self.Session() as session:
            # Clean old duplicate records
            deleted_duplicates = session.query(DuplicateRecord).filter(
                DuplicateRecord.created_at < cutoff_date,
                DuplicateRecord.status == 'linked'
            ).delete()
            
            # Clean old lineage records
            deleted_lineage = session.query(DataLineage).filter(
                DataLineage.created_at < cutoff_date,
                DataLineage.sync_status == 'synced'
            ).delete()
            
            session.commit()
            
        logger.info(f"Cleaned up old data", 
                  duplicates_deleted=deleted_duplicates,
                  lineage_deleted=deleted_lineage)
                  
    async def start_background_tasks(self):
        """Start background tasks for MDM maintenance"""
        
        async def periodic_cleanup():
            while True:
                try:
                    await self.cleanup_old_data()
                    await asyncio.sleep(86400)  # Daily cleanup
                except Exception as e:
                    logger.error("Error in periodic cleanup", error=str(e))
                    await asyncio.sleep(3600)  # Retry in 1 hour
                    
        async def sync_scheduler():
            while True:
                try:
                    # Schedule automatic syncs based on sync rules
                    for source_system, rules in self.sync_rules.items():
                        for rule in rules:
                            if rule.sync_frequency == 'hourly':
                                await self.synchronize_entities(
                                    rule.entity_type, source_system, [rule.target_system]
                                )
                    
                    await asyncio.sleep(3600)  # Hourly check
                except Exception as e:
                    logger.error("Error in sync scheduler", error=str(e))
                    await asyncio.sleep(1800)  # Retry in 30 minutes
                    
        # Start background tasks
        asyncio.create_task(periodic_cleanup())
        asyncio.create_task(sync_scheduler())
        
        logger.info("MDM background tasks started")