import sqlite3
import json
import time
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import pandas as pd
import numpy as np
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed


class FeatureType(Enum):
    NUMERIC = "numeric"
    CATEGORICAL = "categorical"
    TEXT = "text"
    BOOLEAN = "boolean"
    TIMESTAMP = "timestamp"
    EMBEDDING = "embedding"


class DataFreshness(Enum):
    FRESH = "fresh"
    STALE = "stale"
    EXPIRED = "expired"


@dataclass
class FeatureSchema:
    feature_name: str
    feature_type: FeatureType
    description: str
    default_value: Any = None
    validation_rules: Dict[str, Any] = None
    tags: List[str] = None
    created_at: datetime = None
    updated_at: datetime = None


@dataclass
class FeatureGroup:
    group_id: str
    group_name: str
    description: str
    features: List[FeatureSchema]
    primary_keys: List[str]
    event_timestamp_column: str
    ttl_hours: Optional[int] = None
    tags: List[str] = None
    created_at: datetime = None
    updated_at: datetime = None


@dataclass
class FeatureValue:
    feature_name: str
    entity_id: str
    value: Any
    timestamp: datetime
    feature_group_id: str
    metadata: Dict[str, Any] = None


class FeatureTransform:
    def __init__(self, transform_id: str, name: str, 
                 function: Callable[[Any], Any], 
                 input_features: List[str],
                 output_feature: str,
                 description: str = ""):
        self.transform_id = transform_id
        self.name = name
        self.function = function
        self.input_features = input_features
        self.output_feature = output_feature
        self.description = description
        self.created_at = datetime.now()


class FeatureStore:
    def __init__(self, db_path: str = "ml_platform.db"):
        self.db_path = db_path
        self.feature_groups = {}
        self.transforms = {}
        self.cache = {}
        self.cache_lock = threading.RLock()
        self._init_database()
        self._load_feature_groups()
    
    def _init_database(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Feature groups table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS feature_groups (
                group_id TEXT PRIMARY KEY,
                group_name TEXT NOT NULL,
                description TEXT,
                schema_json TEXT NOT NULL,
                primary_keys TEXT NOT NULL,
                event_timestamp_column TEXT NOT NULL,
                ttl_hours INTEGER,
                tags TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        ''')
        
        # Feature values table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS feature_values (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                feature_group_id TEXT NOT NULL,
                entity_id TEXT NOT NULL,
                feature_name TEXT NOT NULL,
                feature_value TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                metadata TEXT,
                INDEX (feature_group_id, entity_id, feature_name),
                INDEX (timestamp)
            )
        ''')
        
        # Feature transforms table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS feature_transforms (
                transform_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                input_features TEXT NOT NULL,
                output_feature TEXT NOT NULL,
                description TEXT,
                created_at TEXT NOT NULL
            )
        ''')
        
        # Feature lineage table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS feature_lineage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_feature TEXT NOT NULL,
                derived_feature TEXT NOT NULL,
                transform_id TEXT,
                created_at TEXT NOT NULL
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _load_feature_groups(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM feature_groups")
        rows = cursor.fetchall()
        
        for row in rows:
            group_id, group_name, description, schema_json, primary_keys, event_timestamp_column, ttl_hours, tags, created_at, updated_at = row
            
            features = []
            schema_data = json.loads(schema_json)
            for feature_data in schema_data:
                features.append(FeatureSchema(
                    feature_name=feature_data["feature_name"],
                    feature_type=FeatureType(feature_data["feature_type"]),
                    description=feature_data["description"],
                    default_value=feature_data.get("default_value"),
                    validation_rules=feature_data.get("validation_rules"),
                    tags=feature_data.get("tags", []),
                    created_at=datetime.fromisoformat(feature_data["created_at"]) if feature_data.get("created_at") else None,
                    updated_at=datetime.fromisoformat(feature_data["updated_at"]) if feature_data.get("updated_at") else None
                ))
            
            feature_group = FeatureGroup(
                group_id=group_id,
                group_name=group_name,
                description=description,
                features=features,
                primary_keys=json.loads(primary_keys),
                event_timestamp_column=event_timestamp_column,
                ttl_hours=ttl_hours,
                tags=json.loads(tags) if tags else [],
                created_at=datetime.fromisoformat(created_at),
                updated_at=datetime.fromisoformat(updated_at)
            )
            
            self.feature_groups[group_id] = feature_group
        
        conn.close()
    
    def create_feature_group(self, feature_group: FeatureGroup) -> bool:
        try:
            feature_group.created_at = datetime.now()
            feature_group.updated_at = datetime.now()
            
            # Validate feature group
            self._validate_feature_group(feature_group)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Serialize features
            features_data = []
            for feature in feature_group.features:
                feature_dict = asdict(feature)
                if feature_dict["created_at"]:
                    feature_dict["created_at"] = feature_dict["created_at"].isoformat()
                if feature_dict["updated_at"]:
                    feature_dict["updated_at"] = feature_dict["updated_at"].isoformat()
                features_data.append(feature_dict)
            
            cursor.execute('''
                INSERT INTO feature_groups 
                (group_id, group_name, description, schema_json, primary_keys, 
                 event_timestamp_column, ttl_hours, tags, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                feature_group.group_id,
                feature_group.group_name,
                feature_group.description,
                json.dumps(features_data),
                json.dumps(feature_group.primary_keys),
                feature_group.event_timestamp_column,
                feature_group.ttl_hours,
                json.dumps(feature_group.tags),
                feature_group.created_at.isoformat(),
                feature_group.updated_at.isoformat()
            ))
            
            conn.commit()
            conn.close()
            
            self.feature_groups[feature_group.group_id] = feature_group
            return True
            
        except Exception as e:
            print(f"Error creating feature group: {e}")
            return False
    
    def _validate_feature_group(self, feature_group: FeatureGroup):
        if not feature_group.group_id:
            raise ValueError("Feature group must have an ID")
        
        if not feature_group.features:
            raise ValueError("Feature group must have at least one feature")
        
        if not feature_group.primary_keys:
            raise ValueError("Feature group must have primary keys")
        
        # Check if event timestamp column exists in features
        feature_names = [f.feature_name for f in feature_group.features]
        if feature_group.event_timestamp_column not in feature_names:
            raise ValueError(f"Event timestamp column '{feature_group.event_timestamp_column}' not found in features")
    
    def ingest_features(self, feature_group_id: str, data: Union[Dict[str, Any], List[Dict[str, Any]]], 
                       entity_id: Optional[str] = None, timestamp: Optional[datetime] = None) -> bool:
        if feature_group_id not in self.feature_groups:
            raise ValueError(f"Feature group {feature_group_id} not found")
        
        feature_group = self.feature_groups[feature_group_id]
        
        # Convert single dict to list
        if isinstance(data, dict):
            data = [data]
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for record in data:
                record_timestamp = timestamp or datetime.now()
                if feature_group.event_timestamp_column in record:
                    record_timestamp = record[feature_group.event_timestamp_column]
                    if isinstance(record_timestamp, str):
                        record_timestamp = datetime.fromisoformat(record_timestamp)
                
                # Determine entity ID
                if entity_id is None:
                    # Use primary keys to create entity ID
                    entity_parts = []
                    for key in feature_group.primary_keys:
                        if key in record:
                            entity_parts.append(str(record[key]))
                    record_entity_id = "|".join(entity_parts)
                else:
                    record_entity_id = entity_id
                
                # Insert each feature value
                for feature in feature_group.features:
                    feature_name = feature.feature_name
                    if feature_name in record:
                        value = record[feature_name]
                        
                        # Validate and convert value
                        validated_value = self._validate_and_convert_feature_value(feature, value)
                        
                        cursor.execute('''
                            INSERT INTO feature_values 
                            (feature_group_id, entity_id, feature_name, feature_value, timestamp, metadata)
                            VALUES (?, ?, ?, ?, ?, ?)
                        ''', (
                            feature_group_id,
                            record_entity_id,
                            feature_name,
                            json.dumps(validated_value),
                            record_timestamp.isoformat(),
                            json.dumps({})
                        ))
            
            conn.commit()
            conn.close()
            
            # Clear cache for affected entities
            with self.cache_lock:
                cache_keys_to_remove = [k for k in self.cache.keys() if k.startswith(f"{feature_group_id}:")]
                for key in cache_keys_to_remove:
                    del self.cache[key]
            
            return True
            
        except Exception as e:
            print(f"Error ingesting features: {e}")
            return False
    
    def _validate_and_convert_feature_value(self, feature: FeatureSchema, value: Any) -> Any:
        if value is None:
            return feature.default_value
        
        # Type validation and conversion
        if feature.feature_type == FeatureType.NUMERIC:
            if not isinstance(value, (int, float, np.number)):
                try:
                    value = float(value)
                except ValueError:
                    raise ValueError(f"Cannot convert {value} to numeric for feature {feature.feature_name}")
        
        elif feature.feature_type == FeatureType.BOOLEAN:
            if not isinstance(value, bool):
                if isinstance(value, str):
                    value = value.lower() in ('true', '1', 'yes', 'on')
                else:
                    value = bool(value)
        
        elif feature.feature_type == FeatureType.CATEGORICAL:
            value = str(value)
        
        elif feature.feature_type == FeatureType.TIMESTAMP:
            if isinstance(value, str):
                value = datetime.fromisoformat(value)
            elif not isinstance(value, datetime):
                raise ValueError(f"Invalid timestamp format for feature {feature.feature_name}")
        
        # Validation rules
        if feature.validation_rules:
            self._apply_validation_rules(feature, value)
        
        return value
    
    def _apply_validation_rules(self, feature: FeatureSchema, value: Any):
        rules = feature.validation_rules
        
        if "min_value" in rules and value < rules["min_value"]:
            raise ValueError(f"Value {value} is below minimum {rules['min_value']} for feature {feature.feature_name}")
        
        if "max_value" in rules and value > rules["max_value"]:
            raise ValueError(f"Value {value} is above maximum {rules['max_value']} for feature {feature.feature_name}")
        
        if "allowed_values" in rules and value not in rules["allowed_values"]:
            raise ValueError(f"Value {value} not in allowed values for feature {feature.feature_name}")
        
        if "regex" in rules:
            import re
            if not re.match(rules["regex"], str(value)):
                raise ValueError(f"Value {value} doesn't match regex pattern for feature {feature.feature_name}")
    
    def get_features(self, feature_group_id: str, entity_ids: Union[str, List[str]], 
                    feature_names: Optional[List[str]] = None,
                    as_of_timestamp: Optional[datetime] = None) -> Dict[str, Dict[str, Any]]:
        if feature_group_id not in self.feature_groups:
            raise ValueError(f"Feature group {feature_group_id} not found")
        
        if isinstance(entity_ids, str):
            entity_ids = [entity_ids]
        
        feature_group = self.feature_groups[feature_group_id]
        
        # Use all features if not specified
        if feature_names is None:
            feature_names = [f.feature_name for f in feature_group.features]
        
        as_of_timestamp = as_of_timestamp or datetime.now()
        
        results = {}
        
        for entity_id in entity_ids:
            # Check cache first
            cache_key = f"{feature_group_id}:{entity_id}:{as_of_timestamp.isoformat()}"
            with self.cache_lock:
                if cache_key in self.cache:
                    cached_result = self.cache[cache_key]
                    # Filter by requested feature names
                    filtered_result = {k: v for k, v in cached_result.items() if k in feature_names}
                    results[entity_id] = filtered_result
                    continue
            
            # Fetch from database
            entity_features = self._fetch_entity_features(
                feature_group_id, entity_id, feature_names, as_of_timestamp
            )
            
            # Apply TTL check
            if feature_group.ttl_hours:
                entity_features = self._apply_ttl_filter(entity_features, feature_group.ttl_hours, as_of_timestamp)
            
            # Fill default values
            entity_features = self._fill_default_values(feature_group, entity_features, feature_names)
            
            results[entity_id] = entity_features
            
            # Cache result
            with self.cache_lock:
                self.cache[cache_key] = entity_features.copy()
        
        return results
    
    def _fetch_entity_features(self, feature_group_id: str, entity_id: str, 
                              feature_names: List[str], as_of_timestamp: datetime) -> Dict[str, Any]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get latest value for each feature before as_of_timestamp
        features = {}
        
        for feature_name in feature_names:
            cursor.execute('''
                SELECT feature_value, timestamp, metadata
                FROM feature_values 
                WHERE feature_group_id = ? AND entity_id = ? AND feature_name = ? 
                    AND timestamp <= ?
                ORDER BY timestamp DESC 
                LIMIT 1
            ''', (feature_group_id, entity_id, feature_name, as_of_timestamp.isoformat()))
            
            row = cursor.fetchone()
            if row:
                features[feature_name] = {
                    "value": json.loads(row[0]),
                    "timestamp": datetime.fromisoformat(row[1]),
                    "metadata": json.loads(row[2]) if row[2] else {}
                }
        
        conn.close()
        return features
    
    def _apply_ttl_filter(self, features: Dict[str, Any], ttl_hours: int, as_of_timestamp: datetime) -> Dict[str, Any]:
        cutoff_time = as_of_timestamp - timedelta(hours=ttl_hours)
        
        filtered_features = {}
        for feature_name, feature_data in features.items():
            if feature_data["timestamp"] >= cutoff_time:
                filtered_features[feature_name] = feature_data
        
        return filtered_features
    
    def _fill_default_values(self, feature_group: FeatureGroup, features: Dict[str, Any], 
                           requested_features: List[str]) -> Dict[str, Any]:
        feature_schema_map = {f.feature_name: f for f in feature_group.features}
        
        for feature_name in requested_features:
            if feature_name not in features:
                schema = feature_schema_map.get(feature_name)
                if schema and schema.default_value is not None:
                    features[feature_name] = {
                        "value": schema.default_value,
                        "timestamp": datetime.now(),
                        "metadata": {"source": "default_value"}
                    }
        
        return features
    
    def get_online_features(self, feature_service_name: str, entity_ids: Union[str, List[str]], 
                          request_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        # Simplified online feature serving
        # In production, this would integrate with a real-time feature serving system
        
        if isinstance(entity_ids, str):
            entity_ids = [entity_ids]
        
        results = {}
        
        # Apply transforms if any
        for entity_id in entity_ids:
            entity_features = {}
            
            # Get base features from all feature groups
            for feature_group_id in self.feature_groups.keys():
                group_features = self.get_features(feature_group_id, entity_id)
                if entity_id in group_features:
                    for feature_name, feature_data in group_features[entity_id].items():
                        entity_features[feature_name] = feature_data["value"]
            
            # Apply transforms
            entity_features = self._apply_transforms(entity_features, request_data)
            
            results[entity_id] = entity_features
        
        return results
    
    def add_transform(self, transform: FeatureTransform):
        self.transforms[transform.transform_id] = transform
        
        # Store in database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO feature_transforms 
            (transform_id, name, input_features, output_feature, description, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            transform.transform_id,
            transform.name,
            json.dumps(transform.input_features),
            transform.output_feature,
            transform.description,
            transform.created_at.isoformat()
        ))
        
        # Record lineage
        for input_feature in transform.input_features:
            cursor.execute('''
                INSERT INTO feature_lineage 
                (source_feature, derived_feature, transform_id, created_at)
                VALUES (?, ?, ?, ?)
            ''', (
                input_feature,
                transform.output_feature,
                transform.transform_id,
                datetime.now().isoformat()
            ))
        
        conn.commit()
        conn.close()
    
    def _apply_transforms(self, features: Dict[str, Any], request_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        # Apply feature transforms
        transformed_features = features.copy()
        
        for transform in self.transforms.values():
            # Check if all input features are available
            if all(input_feat in transformed_features for input_feat in transform.input_features):
                try:
                    input_values = [transformed_features[feat] for feat in transform.input_features]
                    output_value = transform.function(*input_values)
                    transformed_features[transform.output_feature] = output_value
                except Exception as e:
                    print(f"Error applying transform {transform.name}: {e}")
        
        return transformed_features
    
    def get_feature_statistics(self, feature_group_id: str, feature_name: str, 
                             days: int = 7) -> Dict[str, Any]:
        if feature_group_id not in self.feature_groups:
            raise ValueError(f"Feature group {feature_group_id} not found")
        
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT feature_value, timestamp 
            FROM feature_values 
            WHERE feature_group_id = ? AND feature_name = ? 
                AND timestamp >= ? AND timestamp <= ?
            ORDER BY timestamp
        ''', (feature_group_id, feature_name, start_time.isoformat(), end_time.isoformat()))
        
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            return {"error": "No data found"}
        
        values = []
        timestamps = []
        
        for row in rows:
            value = json.loads(row[0])
            if isinstance(value, (int, float)):
                values.append(value)
                timestamps.append(datetime.fromisoformat(row[1]))
        
        if not values:
            return {"error": "No numeric data found"}
        
        stats = {
            "feature_group_id": feature_group_id,
            "feature_name": feature_name,
            "time_period": f"{days} days",
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "mean": sum(values) / len(values),
            "median": sorted(values)[len(values) // 2],
            "first_seen": min(timestamps).isoformat(),
            "last_seen": max(timestamps).isoformat()
        }
        
        return stats
    
    def get_feature_lineage(self, feature_name: str) -> Dict[str, Any]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Find upstream dependencies
        cursor.execute('''
            SELECT source_feature, transform_id, created_at
            FROM feature_lineage 
            WHERE derived_feature = ?
        ''', (feature_name,))
        
        upstream = []
        for row in cursor.fetchall():
            upstream.append({
                "source_feature": row[0],
                "transform_id": row[1],
                "created_at": row[2]
            })
        
        # Find downstream dependencies
        cursor.execute('''
            SELECT derived_feature, transform_id, created_at
            FROM feature_lineage 
            WHERE source_feature = ?
        ''', (feature_name,))
        
        downstream = []
        for row in cursor.fetchall():
            downstream.append({
                "derived_feature": row[0],
                "transform_id": row[1],
                "created_at": row[2]
            })
        
        conn.close()
        
        return {
            "feature_name": feature_name,
            "upstream_dependencies": upstream,
            "downstream_dependencies": downstream
        }
    
    def clear_cache(self):
        with self.cache_lock:
            self.cache.clear()


# Usage example
if __name__ == "__main__":
    fs = FeatureStore()
    
    # Create feature group
    user_features = FeatureGroup(
        group_id="user_features",
        group_name="User Features",
        description="Basic user demographic and behavioral features",
        features=[
            FeatureSchema("user_id", FeatureType.CATEGORICAL, "Unique user identifier"),
            FeatureSchema("age", FeatureType.NUMERIC, "User age", validation_rules={"min_value": 0, "max_value": 120}),
            FeatureSchema("country", FeatureType.CATEGORICAL, "User country"),
            FeatureSchema("is_premium", FeatureType.BOOLEAN, "Premium subscription status", default_value=False),
            FeatureSchema("last_login", FeatureType.TIMESTAMP, "Last login timestamp"),
            FeatureSchema("total_purchases", FeatureType.NUMERIC, "Total number of purchases", default_value=0)
        ],
        primary_keys=["user_id"],
        event_timestamp_column="last_login",
        ttl_hours=168  # 7 days
    )
    
    fs.create_feature_group(user_features)
    
    # Ingest some data
    user_data = {
        "user_id": "user123",
        "age": 28,
        "country": "US",
        "is_premium": True,
        "last_login": datetime.now(),
        "total_purchases": 5
    }
    
    fs.ingest_features("user_features", user_data)
    
    # Get features
    features = fs.get_features("user_features", "user123")
    print("Retrieved features:", features)
    
    # Add a transform
    def calculate_age_group(age):
        if age < 18:
            return "minor"
        elif age < 65:
            return "adult"
        else:
            return "senior"
    
    age_group_transform = FeatureTransform(
        transform_id="age_group",
        name="Age Group Calculator",
        function=calculate_age_group,
        input_features=["age"],
        output_feature="age_group",
        description="Categorizes users into age groups"
    )
    
    fs.add_transform(age_group_transform)
    
    # Get online features with transforms
    online_features = fs.get_online_features("user_service", "user123")
    print("Online features with transforms:", online_features)