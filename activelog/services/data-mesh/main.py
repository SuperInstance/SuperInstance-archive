#!/usr/bin/env python3
"""
Advanced Data Mesh Architecture Service
Decentralized data architecture with domain-driven data ownership
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set, Tuple
import uuid
import hashlib
from dataclasses import dataclass, asdict
from enum import Enum
import threading
from collections import defaultdict, deque
import websockets
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from pydantic import BaseModel
import sqlite3
from contextlib import asynccontextmanager
import aiofiles
import aiohttp
import asyncpg
from confluent_kafka import Producer, Consumer, KafkaException
import redis
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataProductType(Enum):
    ANALYTICAL = "analytical"
    OPERATIONAL = "operational"
    REFERENCE = "reference"
    MASTER = "master"
    TRANSACTIONAL = "transactional"

class DataQuality(Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"

class GovernanceLevel(Enum):
    STRICT = "strict"
    MODERATE = "moderate"
    FLEXIBLE = "flexible"

class AccessPattern(Enum):
    BATCH = "batch"
    STREAMING = "streaming"
    API = "api"
    QUERY = "query"

@dataclass
class DataDomain:
    domain_id: str
    name: str
    description: str
    owner: str
    team: str
    business_capabilities: List[str]
    data_products: List[str]
    governance_level: GovernanceLevel
    created_at: datetime
    last_updated: datetime
    health_score: float

@dataclass
class DataProduct:
    product_id: str
    name: str
    domain_id: str
    type: DataProductType
    description: str
    owner: str
    schema_version: str
    data_contract: Dict[str, Any]
    sla: Dict[str, Any]
    lineage: List[str]
    consumers: Set[str]
    access_patterns: List[AccessPattern]
    quality_score: float
    freshness_sla: int  # minutes
    created_at: datetime
    last_updated: datetime

@dataclass
class DataContract:
    contract_id: str
    product_id: str
    version: str
    schema: Dict[str, Any]
    quality_rules: List[Dict[str, Any]]
    sla_definitions: Dict[str, Any]
    compatibility_rules: Dict[str, Any]
    deprecation_policy: Dict[str, Any]
    created_at: datetime
    is_active: bool

@dataclass
class DataLineage:
    lineage_id: str
    source_product: str
    target_product: str
    transformation_type: str
    transformation_logic: str
    impact_level: float
    created_at: datetime
    validated: bool

@dataclass
class DataMetrics:
    product_id: str
    timestamp: datetime
    volume_gb: float
    throughput_mbps: float
    latency_ms: float
    quality_score: float
    availability_pct: float
    consumer_count: int
    error_rate: float

class DataCatalog:
    """Federated data catalog with semantic search"""
    
    def __init__(self):
        self.products: Dict[str, DataProduct] = {}
        self.domains: Dict[str, DataDomain] = {}
        self.contracts: Dict[str, DataContract] = {}
        self.lineage: List[DataLineage] = []
        self.vectorizer = TfidfVectorizer(stop_words='english', max_features=1000)
        self.product_vectors = {}
        self.search_index_built = False
        
    def register_data_product(self, product: DataProduct) -> bool:
        """Register a new data product"""
        try:
            self.products[product.product_id] = product
            
            # Update domain
            if product.domain_id in self.domains:
                domain = self.domains[product.domain_id]
                if product.product_id not in domain.data_products:
                    domain.data_products.append(product.product_id)
                    domain.last_updated = datetime.now()
            
            # Rebuild search index
            self._rebuild_search_index()
            
            logger.info(f"Registered data product: {product.name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register data product: {e}")
            return False
    
    def register_data_domain(self, domain: DataDomain) -> bool:
        """Register a new data domain"""
        try:
            self.domains[domain.domain_id] = domain
            logger.info(f"Registered data domain: {domain.name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register data domain: {e}")
            return False
    
    def create_data_contract(self, contract: DataContract) -> bool:
        """Create a new data contract"""
        try:
            # Validate contract
            if not self._validate_contract(contract):
                return False
            
            # Deactivate previous versions
            for existing_contract in self.contracts.values():
                if (existing_contract.product_id == contract.product_id and
                    existing_contract.version != contract.version):
                    existing_contract.is_active = False
            
            self.contracts[contract.contract_id] = contract
            
            # Update product schema version
            if contract.product_id in self.products:
                self.products[contract.product_id].schema_version = contract.version
                self.products[contract.product_id].data_contract = contract.schema
            
            logger.info(f"Created data contract: {contract.contract_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create data contract: {e}")
            return False
    
    def _validate_contract(self, contract: DataContract) -> bool:
        """Validate data contract"""
        required_fields = ["schema", "quality_rules", "sla_definitions"]
        
        for field in required_fields:
            if not hasattr(contract, field) or not getattr(contract, field):
                logger.error(f"Contract validation failed: missing {field}")
                return False
        
        # Validate schema structure
        if "fields" not in contract.schema:
            logger.error("Contract validation failed: no fields in schema")
            return False
        
        return True
    
    def add_lineage(self, lineage: DataLineage) -> bool:
        """Add data lineage relationship"""
        try:
            # Validate lineage
            if (lineage.source_product not in self.products or
                lineage.target_product not in self.products):
                logger.error("Lineage validation failed: invalid product references")
                return False
            
            self.lineage.append(lineage)
            
            # Update product lineage
            source_product = self.products[lineage.source_product]
            target_product = self.products[lineage.target_product]
            
            if lineage.target_product not in source_product.lineage:
                source_product.lineage.append(lineage.target_product)
            
            logger.info(f"Added lineage: {lineage.source_product} -> {lineage.target_product}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add lineage: {e}")
            return False
    
    def search_products(self, query: str, domain_filter: Optional[str] = None) -> List[DataProduct]:
        """Semantic search for data products"""
        try:
            if not self.search_index_built:
                self._rebuild_search_index()
            
            if not self.product_vectors:
                return []
            
            # Transform query
            query_vector = self.vectorizer.transform([query])
            
            # Calculate similarities
            similarities = []
            for product_id, product_vector in self.product_vectors.items():
                similarity = cosine_similarity(query_vector, product_vector)[0][0]
                similarities.append((product_id, similarity))
            
            # Sort by similarity
            similarities.sort(key=lambda x: x[1], reverse=True)
            
            # Filter by domain if specified
            results = []
            for product_id, similarity in similarities[:10]:  # Top 10 results
                product = self.products[product_id]
                
                if domain_filter and product.domain_id != domain_filter:
                    continue
                
                if similarity > 0.1:  # Minimum similarity threshold
                    results.append(product)
            
            return results
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    def _rebuild_search_index(self):
        """Rebuild search index for semantic search"""
        try:
            if not self.products:
                return
            
            # Prepare documents for vectorization
            documents = []
            product_ids = []
            
            for product_id, product in self.products.items():
                document = f"{product.name} {product.description} {' '.join(product.business_capabilities if hasattr(product, 'business_capabilities') else [])}"
                documents.append(document)
                product_ids.append(product_id)
            
            # Fit vectorizer and transform documents
            if len(documents) > 0:
                document_vectors = self.vectorizer.fit_transform(documents)
                
                # Store product vectors
                for i, product_id in enumerate(product_ids):
                    self.product_vectors[product_id] = document_vectors[i:i+1]
                
                self.search_index_built = True
                logger.info("Search index rebuilt successfully")
            
        except Exception as e:
            logger.error(f"Failed to rebuild search index: {e}")
    
    def get_lineage_graph(self, product_id: str, depth: int = 3) -> Dict[str, Any]:
        """Get data lineage graph for a product"""
        graph = {
            "nodes": [],
            "edges": []
        }
        
        visited = set()
        queue = [(product_id, 0)]
        
        while queue and depth > 0:
            current_id, current_depth = queue.pop(0)
            
            if current_id in visited or current_depth > depth:
                continue
            
            visited.add(current_id)
            
            # Add node
            if current_id in self.products:
                product = self.products[current_id]
                graph["nodes"].append({
                    "id": current_id,
                    "name": product.name,
                    "type": product.type.value,
                    "domain": product.domain_id,
                    "depth": current_depth
                })
            
            # Add edges and next nodes
            for lineage in self.lineage:
                if lineage.source_product == current_id:
                    graph["edges"].append({
                        "source": lineage.source_product,
                        "target": lineage.target_product,
                        "type": lineage.transformation_type,
                        "impact": lineage.impact_level
                    })
                    queue.append((lineage.target_product, current_depth + 1))
                
                elif lineage.target_product == current_id:
                    graph["edges"].append({
                        "source": lineage.source_product,
                        "target": lineage.target_product,
                        "type": lineage.transformation_type,
                        "impact": lineage.impact_level
                    })
                    queue.append((lineage.source_product, current_depth + 1))
        
        return graph

class DataQualityMonitor:
    """Data quality monitoring and validation"""
    
    def __init__(self):
        self.quality_rules: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.quality_history: Dict[str, List[Tuple[datetime, float]]] = defaultdict(list)
        self.anomaly_threshold = 0.1
        
    def add_quality_rule(self, product_id: str, rule: Dict[str, Any]) -> bool:
        """Add data quality rule for a product"""
        try:
            required_fields = ["rule_type", "condition", "severity"]
            
            if not all(field in rule for field in required_fields):
                logger.error("Quality rule validation failed: missing required fields")
                return False
            
            rule["rule_id"] = str(uuid.uuid4())
            rule["created_at"] = datetime.now()
            
            self.quality_rules[product_id].append(rule)
            logger.info(f"Added quality rule for product {product_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add quality rule: {e}")
            return False
    
    def evaluate_quality(self, product_id: str, data_sample: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate data quality for a product"""
        results = {
            "product_id": product_id,
            "timestamp": datetime.now(),
            "overall_score": 1.0,
            "rule_results": [],
            "anomalies": []
        }
        
        try:
            rules = self.quality_rules.get(product_id, [])
            
            for rule in rules:
                rule_result = self._evaluate_rule(rule, data_sample)
                results["rule_results"].append(rule_result)
                
                # Update overall score
                if not rule_result["passed"]:
                    penalty = 0.2 if rule["severity"] == "high" else 0.1
                    results["overall_score"] = max(0.0, results["overall_score"] - penalty)
            
            # Check for anomalies
            anomalies = self._detect_anomalies(product_id, results["overall_score"])
            results["anomalies"] = anomalies
            
            # Store quality history
            self.quality_history[product_id].append(
                (results["timestamp"], results["overall_score"])
            )
            
            # Keep only recent history
            cutoff_time = datetime.now() - timedelta(days=30)
            self.quality_history[product_id] = [
                (ts, score) for ts, score in self.quality_history[product_id]
                if ts > cutoff_time
            ]
            
            return results
            
        except Exception as e:
            logger.error(f"Quality evaluation failed: {e}")
            results["error"] = str(e)
            return results
    
    def _evaluate_rule(self, rule: Dict[str, Any], data_sample: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate individual quality rule"""
        result = {
            "rule_id": rule["rule_id"],
            "rule_type": rule["rule_type"],
            "passed": True,
            "message": "",
            "value": None
        }
        
        try:
            if rule["rule_type"] == "completeness":
                # Check for null/empty values
                field = rule["condition"]["field"]
                if field in data_sample:
                    value = data_sample[field]
                    result["value"] = value
                    if value is None or value == "":
                        result["passed"] = False
                        result["message"] = f"Field {field} is empty"
                else:
                    result["passed"] = False
                    result["message"] = f"Field {field} is missing"
            
            elif rule["rule_type"] == "range":
                # Check value range
                field = rule["condition"]["field"]
                min_val = rule["condition"].get("min")
                max_val = rule["condition"].get("max")
                
                if field in data_sample:
                    value = data_sample[field]
                    result["value"] = value
                    
                    try:
                        numeric_value = float(value)
                        if min_val is not None and numeric_value < min_val:
                            result["passed"] = False
                            result["message"] = f"Value {numeric_value} below minimum {min_val}"
                        elif max_val is not None and numeric_value > max_val:
                            result["passed"] = False
                            result["message"] = f"Value {numeric_value} above maximum {max_val}"
                    except (ValueError, TypeError):
                        result["passed"] = False
                        result["message"] = f"Value {value} is not numeric"
            
            elif rule["rule_type"] == "format":
                # Check format/pattern
                field = rule["condition"]["field"]
                pattern = rule["condition"]["pattern"]
                
                if field in data_sample:
                    value = str(data_sample[field])
                    result["value"] = value
                    
                    import re
                    if not re.match(pattern, value):
                        result["passed"] = False
                        result["message"] = f"Value {value} doesn't match pattern {pattern}"
            
            elif rule["rule_type"] == "uniqueness":
                # This would require historical data - simplified for now
                result["message"] = "Uniqueness check requires historical data"
            
        except Exception as e:
            result["passed"] = False
            result["message"] = f"Rule evaluation error: {e}"
        
        return result
    
    def _detect_anomalies(self, product_id: str, current_score: float) -> List[Dict[str, Any]]:
        """Detect quality anomalies"""
        anomalies = []
        
        try:
            history = self.quality_history.get(product_id, [])
            
            if len(history) < 5:  # Need sufficient history
                return anomalies
            
            # Calculate recent average
            recent_scores = [score for _, score in history[-10:]]
            avg_score = np.mean(recent_scores)
            std_score = np.std(recent_scores)
            
            # Check for sudden drop
            if current_score < avg_score - (2 * std_score):
                anomalies.append({
                    "type": "quality_drop",
                    "severity": "high",
                    "message": f"Quality score dropped to {current_score:.2f} (avg: {avg_score:.2f})",
                    "detected_at": datetime.now()
                })
            
            # Check for trend
            if len(recent_scores) >= 5:
                trend_slope = np.polyfit(range(len(recent_scores)), recent_scores, 1)[0]
                if trend_slope < -0.05:  # Declining trend
                    anomalies.append({
                        "type": "declining_trend",
                        "severity": "medium",
                        "message": f"Quality trend is declining (slope: {trend_slope:.3f})",
                        "detected_at": datetime.now()
                    })
            
        except Exception as e:
            logger.error(f"Anomaly detection failed: {e}")
        
        return anomalies

class DataMeshOrchestrator:
    """Main data mesh orchestrator"""
    
    def __init__(self):
        self.catalog = DataCatalog()
        self.quality_monitor = DataQualityMonitor()
        self.metrics: Dict[str, DataMetrics] = {}
        self.event_stream = deque(maxlen=1000)
        
        # Initialize storage
        self._init_database()
        
        # Background tasks
        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()
        
        logger.info("Data Mesh Orchestrator initialized")
    
    def _init_database(self):
        """Initialize SQLite database"""
        os.makedirs("data", exist_ok=True)
        self.db_path = "data/data_mesh.db"
        
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS data_domains (
                    domain_id TEXT PRIMARY KEY,
                    name TEXT,
                    description TEXT,
                    owner TEXT,
                    team TEXT,
                    business_capabilities TEXT,
                    data_products TEXT,
                    governance_level TEXT,
                    created_at TIMESTAMP,
                    last_updated TIMESTAMP,
                    health_score REAL
                );
                
                CREATE TABLE IF NOT EXISTS data_products (
                    product_id TEXT PRIMARY KEY,
                    name TEXT,
                    domain_id TEXT,
                    type TEXT,
                    description TEXT,
                    owner TEXT,
                    schema_version TEXT,
                    data_contract TEXT,
                    sla TEXT,
                    lineage TEXT,
                    consumers TEXT,
                    access_patterns TEXT,
                    quality_score REAL,
                    freshness_sla INTEGER,
                    created_at TIMESTAMP,
                    last_updated TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS data_contracts (
                    contract_id TEXT PRIMARY KEY,
                    product_id TEXT,
                    version TEXT,
                    schema TEXT,
                    quality_rules TEXT,
                    sla_definitions TEXT,
                    compatibility_rules TEXT,
                    deprecation_policy TEXT,
                    created_at TIMESTAMP,
                    is_active BOOLEAN
                );
                
                CREATE TABLE IF NOT EXISTS data_lineage (
                    lineage_id TEXT PRIMARY KEY,
                    source_product TEXT,
                    target_product TEXT,
                    transformation_type TEXT,
                    transformation_logic TEXT,
                    impact_level REAL,
                    created_at TIMESTAMP,
                    validated BOOLEAN
                );
                
                CREATE TABLE IF NOT EXISTS data_metrics (
                    product_id TEXT,
                    timestamp TIMESTAMP,
                    volume_gb REAL,
                    throughput_mbps REAL,
                    latency_ms REAL,
                    quality_score REAL,
                    availability_pct REAL,
                    consumer_count INTEGER,
                    error_rate REAL,
                    PRIMARY KEY (product_id, timestamp)
                );
            """)
    
    def create_domain(self, name: str, description: str, owner: str, team: str,
                     business_capabilities: List[str]) -> str:
        """Create a new data domain"""
        domain_id = str(uuid.uuid4())
        
        domain = DataDomain(
            domain_id=domain_id,
            name=name,
            description=description,
            owner=owner,
            team=team,
            business_capabilities=business_capabilities,
            data_products=[],
            governance_level=GovernanceLevel.MODERATE,
            created_at=datetime.now(),
            last_updated=datetime.now(),
            health_score=1.0
        )
        
        success = self.catalog.register_data_domain(domain)
        
        if success:
            # Save to database
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO data_domains VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    domain_id, name, description, owner, team,
                    json.dumps(business_capabilities), json.dumps([]),
                    domain.governance_level.value,
                    domain.created_at.isoformat(),
                    domain.last_updated.isoformat(),
                    domain.health_score
                ))
            
            self._emit_event("domain_created", {"domain_id": domain_id, "name": name})
        
        return domain_id if success else ""
    
    def create_data_product(self, name: str, domain_id: str, product_type: str,
                           description: str, owner: str, sla: Dict[str, Any]) -> str:
        """Create a new data product"""
        if domain_id not in self.catalog.domains:
            raise ValueError("Domain not found")
        
        product_id = str(uuid.uuid4())
        
        try:
            product_type_enum = DataProductType(product_type)
        except ValueError:
            raise ValueError(f"Invalid product type: {product_type}")
        
        product = DataProduct(
            product_id=product_id,
            name=name,
            domain_id=domain_id,
            type=product_type_enum,
            description=description,
            owner=owner,
            schema_version="1.0.0",
            data_contract={},
            sla=sla,
            lineage=[],
            consumers=set(),
            access_patterns=[AccessPattern.API],
            quality_score=1.0,
            freshness_sla=sla.get("freshness_minutes", 60),
            created_at=datetime.now(),
            last_updated=datetime.now()
        )
        
        success = self.catalog.register_data_product(product)
        
        if success:
            # Save to database
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO data_products VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    product_id, name, domain_id, product_type, description, owner,
                    product.schema_version, json.dumps(product.data_contract),
                    json.dumps(sla), json.dumps(product.lineage),
                    json.dumps(list(product.consumers)),
                    json.dumps([ap.value for ap in product.access_patterns]),
                    product.quality_score, product.freshness_sla,
                    product.created_at.isoformat(),
                    product.last_updated.isoformat()
                ))
            
            self._emit_event("data_product_created", {
                "product_id": product_id,
                "name": name,
                "domain_id": domain_id
            })
        
        return product_id if success else ""
    
    def create_data_contract(self, product_id: str, schema: Dict[str, Any],
                            quality_rules: List[Dict[str, Any]],
                            sla_definitions: Dict[str, Any]) -> str:
        """Create data contract for a product"""
        if product_id not in self.catalog.products:
            raise ValueError("Data product not found")
        
        contract_id = str(uuid.uuid4())
        
        # Get next version
        existing_contracts = [
            c for c in self.catalog.contracts.values()
            if c.product_id == product_id
        ]
        
        if existing_contracts:
            versions = [c.version for c in existing_contracts]
            latest_version = max(versions)
            major, minor, patch = latest_version.split('.')
            next_version = f"{major}.{int(minor) + 1}.0"
        else:
            next_version = "1.0.0"
        
        contract = DataContract(
            contract_id=contract_id,
            product_id=product_id,
            version=next_version,
            schema=schema,
            quality_rules=quality_rules,
            sla_definitions=sla_definitions,
            compatibility_rules={"backward_compatible": True},
            deprecation_policy={"notice_period_days": 90},
            created_at=datetime.now(),
            is_active=True
        )
        
        success = self.catalog.create_data_contract(contract)
        
        if success:
            # Add quality rules to monitor
            for rule in quality_rules:
                self.quality_monitor.add_quality_rule(product_id, rule)
            
            # Save to database
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO data_contracts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    contract_id, product_id, next_version,
                    json.dumps(schema), json.dumps(quality_rules),
                    json.dumps(sla_definitions),
                    json.dumps(contract.compatibility_rules),
                    json.dumps(contract.deprecation_policy),
                    contract.created_at.isoformat(),
                    contract.is_active
                ))
            
            self._emit_event("data_contract_created", {
                "contract_id": contract_id,
                "product_id": product_id,
                "version": next_version
            })
        
        return contract_id if success else ""
    
    def add_data_lineage(self, source_product: str, target_product: str,
                        transformation_type: str, transformation_logic: str) -> str:
        """Add data lineage relationship"""
        lineage_id = str(uuid.uuid4())
        
        lineage = DataLineage(
            lineage_id=lineage_id,
            source_product=source_product,
            target_product=target_product,
            transformation_type=transformation_type,
            transformation_logic=transformation_logic,
            impact_level=0.8,  # Default impact level
            created_at=datetime.now(),
            validated=False
        )
        
        success = self.catalog.add_lineage(lineage)
        
        if success:
            # Save to database
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO data_lineage VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    lineage_id, source_product, target_product,
                    transformation_type, transformation_logic,
                    lineage.impact_level, lineage.created_at.isoformat(),
                    lineage.validated
                ))
            
            self._emit_event("lineage_added", {
                "lineage_id": lineage_id,
                "source": source_product,
                "target": target_product
            })
        
        return lineage_id if success else ""
    
    def validate_data_quality(self, product_id: str, data_sample: Dict[str, Any]) -> Dict[str, Any]:
        """Validate data quality for a product"""
        return self.quality_monitor.evaluate_quality(product_id, data_sample)
    
    def record_metrics(self, product_id: str, metrics: Dict[str, Any]):
        """Record data product metrics"""
        timestamp = datetime.now()
        
        data_metrics = DataMetrics(
            product_id=product_id,
            timestamp=timestamp,
            volume_gb=metrics.get("volume_gb", 0.0),
            throughput_mbps=metrics.get("throughput_mbps", 0.0),
            latency_ms=metrics.get("latency_ms", 0.0),
            quality_score=metrics.get("quality_score", 1.0),
            availability_pct=metrics.get("availability_pct", 100.0),
            consumer_count=metrics.get("consumer_count", 0),
            error_rate=metrics.get("error_rate", 0.0)
        )
        
        self.metrics[f"{product_id}_{timestamp.isoformat()}"] = data_metrics
        
        # Save to database
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO data_metrics VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                product_id, timestamp.isoformat(),
                data_metrics.volume_gb, data_metrics.throughput_mbps,
                data_metrics.latency_ms, data_metrics.quality_score,
                data_metrics.availability_pct, data_metrics.consumer_count,
                data_metrics.error_rate
            ))
        
        # Update product quality score
        if product_id in self.catalog.products:
            self.catalog.products[product_id].quality_score = data_metrics.quality_score
    
    def search_data_products(self, query: str, domain_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search for data products"""
        products = self.catalog.search_products(query, domain_filter)
        
        return [
            {
                "product_id": p.product_id,
                "name": p.name,
                "domain_id": p.domain_id,
                "type": p.type.value,
                "description": p.description,
                "owner": p.owner,
                "quality_score": p.quality_score,
                "created_at": p.created_at.isoformat()
            }
            for p in products
        ]
    
    def get_lineage_graph(self, product_id: str, depth: int = 3) -> Dict[str, Any]:
        """Get data lineage graph"""
        return self.catalog.get_lineage_graph(product_id, depth)
    
    def _emit_event(self, event_type: str, data: Dict[str, Any]):
        """Emit event to event stream"""
        event = {
            "event_type": event_type,
            "timestamp": datetime.now().isoformat(),
            "data": data
        }
        self.event_stream.append(event)
    
    def _monitoring_loop(self):
        """Background monitoring loop"""
        while self.monitoring_active:
            try:
                # Monitor data product health
                for product_id, product in self.catalog.products.items():
                    # Check freshness
                    time_since_update = datetime.now() - product.last_updated
                    freshness_violation = time_since_update.total_seconds() > (product.freshness_sla * 60)
                    
                    if freshness_violation:
                        self._emit_event("freshness_violation", {
                            "product_id": product_id,
                            "minutes_late": time_since_update.total_seconds() / 60
                        })
                
                # Monitor domain health
                for domain_id, domain in self.catalog.domains.items():
                    if domain.data_products:
                        avg_quality = np.mean([
                            self.catalog.products[pid].quality_score
                            for pid in domain.data_products
                            if pid in self.catalog.products
                        ])
                        domain.health_score = avg_quality
                
                time.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                time.sleep(10)
    
    def get_mesh_overview(self) -> Dict[str, Any]:
        """Get data mesh overview"""
        return {
            "domains": len(self.catalog.domains),
            "data_products": len(self.catalog.products),
            "contracts": len(self.catalog.contracts),
            "lineage_relationships": len(self.catalog.lineage),
            "total_consumers": sum(
                len(p.consumers) for p in self.catalog.products.values()
            ),
            "avg_quality_score": np.mean([
                p.quality_score for p in self.catalog.products.values()
            ]) if self.catalog.products else 0.0,
            "active_contracts": len([
                c for c in self.catalog.contracts.values() if c.is_active
            ])
        }

# FastAPI application
app = FastAPI(title="Data Mesh Architecture Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global data mesh instance
data_mesh = DataMeshOrchestrator()

# Pydantic models
class DomainRequest(BaseModel):
    name: str
    description: str
    owner: str
    team: str
    business_capabilities: List[str]

class DataProductRequest(BaseModel):
    name: str
    domain_id: str
    type: str
    description: str
    owner: str
    sla: Dict[str, Any]

class ContractRequest(BaseModel):
    schema: Dict[str, Any]
    quality_rules: List[Dict[str, Any]]
    sla_definitions: Dict[str, Any]

class LineageRequest(BaseModel):
    source_product: str
    target_product: str
    transformation_type: str
    transformation_logic: str

class QualityRequest(BaseModel):
    data_sample: Dict[str, Any]

class MetricsRequest(BaseModel):
    metrics: Dict[str, Any]

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Data Mesh Architecture",
        "status": "operational",
        "version": "1.0.0",
        "data_mesh_ready": True
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    overview = data_mesh.get_mesh_overview()
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "mesh_overview": overview
    }

@app.post("/domains")
async def create_domain(request: DomainRequest):
    """Create data domain"""
    try:
        domain_id = data_mesh.create_domain(
            request.name, request.description, request.owner,
            request.team, request.business_capabilities
        )
        
        if not domain_id:
            raise HTTPException(status_code=400, detail="Failed to create domain")
        
        return {
            "success": True,
            "domain_id": domain_id
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/domains")
async def list_domains():
    """List all data domains"""
    domains = []
    for domain in data_mesh.catalog.domains.values():
        domains.append({
            "domain_id": domain.domain_id,
            "name": domain.name,
            "description": domain.description,
            "owner": domain.owner,
            "team": domain.team,
            "data_products_count": len(domain.data_products),
            "health_score": domain.health_score
        })
    
    return {"domains": domains}

@app.post("/domains/{domain_id}/products")
async def create_data_product(domain_id: str, request: DataProductRequest):
    """Create data product"""
    try:
        product_id = data_mesh.create_data_product(
            request.name, domain_id, request.type,
            request.description, request.owner, request.sla
        )
        
        if not product_id:
            raise HTTPException(status_code=400, detail="Failed to create data product")
        
        return {
            "success": True,
            "product_id": product_id
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/products")
async def list_products(domain_id: Optional[str] = None):
    """List data products"""
    products = []
    for product in data_mesh.catalog.products.values():
        if domain_id and product.domain_id != domain_id:
            continue
        
        products.append({
            "product_id": product.product_id,
            "name": product.name,
            "domain_id": product.domain_id,
            "type": product.type.value,
            "description": product.description,
            "owner": product.owner,
            "quality_score": product.quality_score,
            "consumers_count": len(product.consumers)
        })
    
    return {"products": products}

@app.post("/products/{product_id}/contracts")
async def create_contract(product_id: str, request: ContractRequest):
    """Create data contract"""
    try:
        contract_id = data_mesh.create_data_contract(
            product_id, request.schema, request.quality_rules,
            request.sla_definitions
        )
        
        if not contract_id:
            raise HTTPException(status_code=400, detail="Failed to create contract")
        
        return {
            "success": True,
            "contract_id": contract_id
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/lineage")
async def add_lineage(request: LineageRequest):
    """Add data lineage"""
    try:
        lineage_id = data_mesh.add_data_lineage(
            request.source_product, request.target_product,
            request.transformation_type, request.transformation_logic
        )
        
        if not lineage_id:
            raise HTTPException(status_code=400, detail="Failed to add lineage")
        
        return {
            "success": True,
            "lineage_id": lineage_id
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/products/{product_id}/lineage")
async def get_lineage(product_id: str, depth: int = 3):
    """Get data lineage graph"""
    try:
        graph = data_mesh.get_lineage_graph(product_id, depth)
        return graph
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/products/{product_id}/quality")
async def validate_quality(product_id: str, request: QualityRequest):
    """Validate data quality"""
    try:
        result = data_mesh.validate_data_quality(product_id, request.data_sample)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/products/{product_id}/metrics")
async def record_metrics(product_id: str, request: MetricsRequest):
    """Record data product metrics"""
    try:
        data_mesh.record_metrics(product_id, request.metrics)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/search")
async def search_products(q: str, domain: Optional[str] = None):
    """Search data products"""
    try:
        results = data_mesh.search_data_products(q, domain)
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/overview")
async def get_overview():
    """Get data mesh overview"""
    return data_mesh.get_mesh_overview()

@app.websocket("/ws/mesh")
async def mesh_websocket(websocket: WebSocket):
    """WebSocket endpoint for real-time mesh updates"""
    await websocket.accept()
    
    try:
        while True:
            # Send recent events
            recent_events = list(data_mesh.event_stream)[-10:]  # Last 10 events
            
            status = {
                "type": "mesh_status",
                "timestamp": datetime.now().isoformat(),
                "overview": data_mesh.get_mesh_overview(),
                "recent_events": recent_events
            }
            
            await websocket.send_text(json.dumps(status))
            await asyncio.sleep(5)
            
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket error: {e}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8858))
    uvicorn.run(app, host="0.0.0.0", port=port)