#!/usr/bin/env python3
"""
Comprehensive Intelligent Data Management System for SuperInstance Ecosystem
===============================================================

This system provides:
- Intelligent log and note cleanup
- ML weight consolidation and merging
- 30GB total storage cap management
- Garbage collection bot with learning capabilities
- Summarization bot with quality scoring
- Data value scoring system
- Automatic deletion of low-value data
- Preservation of valuable data for future builders
- Self-training system for optimization bots
"""

import os
import json
import sqlite3
import logging
import hashlib
import threading
import time
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor
import numpy as np
import pickle
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import psutil
import shutil

# Import our ML optimizer
from ml_data_optimizer import (
    DataValueNet, NoteMergingNet, GarbageCollectorNet, 
    SummarizationNet, DataOptimizer
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data_lifecycle_manager.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class DataItem:
    """Represents a data item in the ecosystem"""
    path: str
    size_bytes: int
    created_at: datetime
    modified_at: datetime
    accessed_at: datetime
    content_hash: str
    data_type: str  # log, note, model, cache, temp, etc.
    service_name: str
    value_score: float = 0.0
    usage_count: int = 0
    ml_training_value: float = 0.0
    human_value: float = 0.0
    bot_value: float = 0.0
    redundancy_score: float = 0.0
    preservation_priority: int = 0

@dataclass
class StorageConfig:
    """Storage configuration and limits"""
    total_limit_gb: float = 30.0
    service_allocations: Dict[str, float] = None
    emergency_cleanup_threshold: float = 0.95
    warning_threshold: float = 0.85
    
    def __post_init__(self):
        if self.service_allocations is None:
            self.service_allocations = {
                "dmlog": 5.0,
                "ml-models": 8.0,
                "logs": 3.0,
                "cache": 2.0,
                "temp": 1.0,
                "backups": 4.0,
                "ai-training": 6.0,
                "misc": 1.0
            }

class ServiceIntegrator:
    """Integrates with all services in the ecosystem"""
    
    def __init__(self, base_path: str = "/home/activeloguser/activelog/services"):
        self.base_path = Path(base_path)
        self.services = self._discover_services()
        self.monitored_paths = self._get_monitored_paths()
        
    def _discover_services(self) -> List[str]:
        """Discover all services in the ecosystem"""
        services = []
        if self.base_path.exists():
            for item in self.base_path.iterdir():
                if item.is_dir() and not item.name.startswith('.'):
                    services.append(item.name)
        logger.info(f"Discovered {len(services)} services")
        return services
    
    def _get_monitored_paths(self) -> Dict[str, List[Path]]:
        """Get paths to monitor for each service"""
        monitored = {}
        for service in self.services:
            service_path = self.base_path / service
            paths = []
            
            # Common file patterns to monitor
            patterns = [
                "*.log", "*.db", "*.json", "*.pkl", "*.model",
                "*.cache", "*.tmp", "*.backup", "requirements.txt",
                "node_modules/", "__pycache__/", ".git/"
            ]
            
            for pattern in patterns:
                paths.extend(service_path.rglob(pattern))
            
            monitored[service] = paths
            
        return monitored
    
    def get_service_data_items(self, service: str) -> List[DataItem]:
        """Get all data items for a specific service"""
        items = []
        if service not in self.monitored_paths:
            return items
            
        for path in self.monitored_paths[service]:
            if path.exists() and path.is_file():
                try:
                    stat = path.stat()
                    content_hash = self._calculate_hash(path)
                    data_type = self._classify_data_type(path)
                    
                    item = DataItem(
                        path=str(path),
                        size_bytes=stat.st_size,
                        created_at=datetime.fromtimestamp(stat.st_ctime),
                        modified_at=datetime.fromtimestamp(stat.st_mtime),
                        accessed_at=datetime.fromtimestamp(stat.st_atime),
                        content_hash=content_hash,
                        data_type=data_type,
                        service_name=service
                    )
                    items.append(item)
                except (OSError, PermissionError) as e:
                    logger.warning(f"Could not process {path}: {e}")
                    
        return items
    
    def _calculate_hash(self, path: Path) -> str:
        """Calculate content hash for file"""
        try:
            if path.stat().st_size > 100 * 1024 * 1024:  # Skip files > 100MB
                return f"large_file_{path.stat().st_size}"
                
            with open(path, 'rb') as f:
                content = f.read()
                return hashlib.sha256(content).hexdigest()
        except Exception:
            return f"error_{path.stat().st_size}"
    
    def _classify_data_type(self, path: Path) -> str:
        """Classify the type of data file"""
        suffix = path.suffix.lower()
        name = path.name.lower()
        
        if suffix in ['.log']:
            return 'log'
        elif suffix in ['.db', '.sqlite', '.sqlite3']:
            return 'database'
        elif suffix in ['.json', '.yaml', '.yml', '.xml']:
            return 'config'
        elif suffix in ['.pkl', '.pickle', '.model', '.h5', '.pt', '.pth']:
            return 'ml_model'
        elif suffix in ['.cache', '.tmp']:
            return 'cache'
        elif 'backup' in name:
            return 'backup'
        elif path.parent.name in ['node_modules', '__pycache__']:
            return 'temp'
        else:
            return 'misc'

class GarbageCollectionBot:
    """Intelligent garbage collection bot with learning capabilities"""
    
    def __init__(self, ml_optimizer):
        self.ml_optimizer = ml_optimizer
        self.deletion_history = []
        self.feedback_scores = {}  # Track deletion effectiveness
        
    def evaluate_deletion_candidates(self, items: List[DataItem]) -> List[Tuple[DataItem, float]]:
        """Evaluate items for deletion with confidence scores"""
        candidates = []
        
        for item in items:
            # Calculate deletion confidence using ML
            features = self._extract_features(item)
            confidence = self.ml_optimizer.garbage_net.predict(features)
            
            # Apply rules for safety
            if self._is_safe_to_delete(item):
                candidates.append((item, confidence))
                
        # Sort by confidence (highest first)
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates
    
    def _extract_features(self, item: DataItem) -> np.ndarray:
        """Extract features for ML prediction"""
        # Time-based features
        now = datetime.now()
        days_since_modified = (now - item.modified_at).days
        days_since_accessed = (now - item.accessed_at).days
        
        # Size and usage features
        size_mb = item.size_bytes / (1024 * 1024)
        
        # Data type encoding
        type_encoding = {
            'temp': 1.0, 'cache': 0.8, 'log': 0.6,
            'backup': 0.3, 'config': 0.1, 'ml_model': 0.0,
            'database': 0.2, 'misc': 0.5
        }.get(item.data_type, 0.5)
        
        features = np.array([
            days_since_modified,
            days_since_accessed,
            size_mb,
            item.usage_count,
            item.value_score,
            item.redundancy_score,
            type_encoding,
            item.ml_training_value,
            item.human_value,
            item.bot_value
        ])
        
        return features
    
    def _is_safe_to_delete(self, item: DataItem) -> bool:
        """Check if item is safe to delete"""
        # Never delete critical files
        critical_patterns = [
            'main.py', 'requirements.txt', 'config.json',
            'package.json', '.env'
        ]
        
        filename = Path(item.path).name.lower()
        if any(pattern in filename for pattern in critical_patterns):
            return False
            
        # Don't delete recently accessed files
        if (datetime.now() - item.accessed_at).days < 1:
            return False
            
        # Don't delete high-value items
        if item.value_score > 0.8:
            return False
            
        return True
    
    def execute_cleanup(self, candidates: List[Tuple[DataItem, float]], 
                       target_reduction_gb: float) -> Dict[str, Any]:
        """Execute cleanup with specified target reduction"""
        deleted_items = []
        total_freed_bytes = 0
        target_bytes = target_reduction_gb * 1024 * 1024 * 1024
        
        for item, confidence in candidates:
            if total_freed_bytes >= target_bytes:
                break
                
            try:
                path = Path(item.path)
                if path.exists():
                    file_size = path.stat().st_size
                    
                    # Create backup record before deletion
                    self._record_deletion(item, confidence)
                    
                    # Delete file
                    path.unlink()
                    deleted_items.append(item)
                    total_freed_bytes += file_size
                    
                    logger.info(f"Deleted {item.path} (freed {file_size} bytes)")
                    
            except Exception as e:
                logger.error(f"Failed to delete {item.path}: {e}")
        
        return {
            'deleted_count': len(deleted_items),
            'freed_gb': total_freed_bytes / (1024 * 1024 * 1024),
            'deleted_items': [asdict(item) for item in deleted_items]
        }
    
    def _record_deletion(self, item: DataItem, confidence: float):
        """Record deletion for learning purposes"""
        self.deletion_history.append({
            'timestamp': datetime.now(),
            'item': asdict(item),
            'confidence': confidence,
            'feedback_received': False
        })
    
    def receive_feedback(self, deletion_id: int, feedback_score: float, 
                        feedback_type: str):
        """Receive feedback on deletion quality"""
        if deletion_id < len(self.deletion_history):
            self.deletion_history[deletion_id]['feedback_received'] = True
            self.feedback_scores[deletion_id] = {
                'score': feedback_score,
                'type': feedback_type,
                'timestamp': datetime.now()
            }
            
            # Update ML model with feedback
            self._update_model_with_feedback()
    
    def _update_model_with_feedback(self):
        """Update garbage collection model with feedback"""
        # Prepare training data from feedback
        training_data = []
        for i, record in enumerate(self.deletion_history):
            if record['feedback_received'] and i in self.feedback_scores:
                item_data = DataItem(**record['item'])
                features = self._extract_features(item_data)
                feedback = self.feedback_scores[i]['score']
                training_data.append((features, feedback))
        
        if len(training_data) > 10:  # Need minimum samples
            self.ml_optimizer.train_garbage_collector(training_data)

class SummarizationBot:
    """Intelligent summarization bot with quality assessment"""
    
    def __init__(self, ml_optimizer):
        self.ml_optimizer = ml_optimizer
        self.summaries = {}
        self.quality_scores = {}
        
    def create_summary(self, items: List[DataItem], 
                      summary_type: str = "general") -> Dict[str, Any]:
        """Create intelligent summary of data items"""
        if not items:
            return {'summary': '', 'quality_score': 0.0}
        
        # Group items by type and service
        grouped = self._group_items(items)
        
        # Generate summary using ML
        summary_features = self._extract_summary_features(grouped)
        summary_text = self._generate_summary_text(grouped, summary_type)
        
        # Score summary quality
        quality_score = self.ml_optimizer.summarization_net.predict(summary_features)
        
        summary_id = hashlib.sha256(summary_text.encode()).hexdigest()[:16]
        
        summary_data = {
            'id': summary_id,
            'text': summary_text,
            'quality_score': float(quality_score),
            'item_count': len(items),
            'type': summary_type,
            'created_at': datetime.now().isoformat(),
            'compressed_ratio': len(summary_text) / sum(item.size_bytes for item in items),
            'coverage_analysis': self._analyze_coverage(items, summary_text)
        }
        
        self.summaries[summary_id] = summary_data
        return summary_data
    
    def _group_items(self, items: List[DataItem]) -> Dict[str, Dict[str, List[DataItem]]]:
        """Group items by service and data type"""
        grouped = {}
        for item in items:
            service = item.service_name
            data_type = item.data_type
            
            if service not in grouped:
                grouped[service] = {}
            if data_type not in grouped[service]:
                grouped[service][data_type] = []
                
            grouped[service][data_type].append(item)
            
        return grouped
    
    def _extract_summary_features(self, grouped_items: Dict) -> np.ndarray:
        """Extract features for summary quality prediction"""
        total_items = sum(len(items) for service in grouped_items.values() 
                         for items in service.values())
        service_count = len(grouped_items)
        avg_item_size = np.mean([item.size_bytes for service in grouped_items.values() 
                                for items in service.values() for item in items])
        
        features = np.array([
            total_items,
            service_count,
            avg_item_size,
            len(str(grouped_items)),  # Complexity proxy
        ])
        
        return features
    
    def _generate_summary_text(self, grouped_items: Dict, 
                              summary_type: str) -> str:
        """Generate human-readable summary text"""
        summary_parts = []
        
        summary_parts.append(f"Data Summary ({summary_type.title()})")
        summary_parts.append("=" * 40)
        
        total_size = 0
        total_files = 0
        
        for service, types in grouped_items.items():
            service_size = 0
            service_files = 0
            type_details = []
            
            for data_type, items in types.items():
                type_size = sum(item.size_bytes for item in items)
                service_size += type_size
                service_files += len(items)
                
                type_details.append(f"  - {data_type}: {len(items)} files, "
                                  f"{type_size / (1024*1024):.2f} MB")
            
            summary_parts.append(f"\n{service}: {service_files} files, "
                                f"{service_size / (1024*1024):.2f} MB")
            summary_parts.extend(type_details)
            
            total_size += service_size
            total_files += service_files
        
        summary_parts.append(f"\nTotal: {total_files} files, "
                           f"{total_size / (1024*1024):.2f} MB")
        
        return "\n".join(summary_parts)
    
    def _analyze_coverage(self, items: List[DataItem], summary: str) -> Dict[str, float]:
        """Analyze how well summary covers the data"""
        # Simple coverage analysis
        service_coverage = {}
        type_coverage = {}
        
        services = set(item.service_name for item in items)
        types = set(item.data_type for item in items)
        
        for service in services:
            service_coverage[service] = 1.0 if service in summary else 0.0
            
        for data_type in types:
            type_coverage[data_type] = 1.0 if data_type in summary else 0.0
        
        return {
            'service_coverage': np.mean(list(service_coverage.values())),
            'type_coverage': np.mean(list(type_coverage.values())),
            'overall_coverage': (np.mean(list(service_coverage.values())) + 
                               np.mean(list(type_coverage.values()))) / 2
        }

class DataLifecycleManager:
    """Main data lifecycle management system"""
    
    def __init__(self, config_path: str = None):
        self.config = StorageConfig()
        self.db_path = "data_lifecycle.db"
        self.service_integrator = ServiceIntegrator()
        self.ml_optimizer = DataOptimizer()
        self.garbage_bot = GarbageCollectionBot(self.ml_optimizer)
        self.summarization_bot = SummarizationBot(self.ml_optimizer)
        self.monitoring_active = False
        
        # Initialize database
        self._init_database()
        
        # Load configuration if provided
        if config_path and Path(config_path).exists():
            self._load_config(config_path)
    
    def _init_database(self):
        """Initialize SQLite database for tracking"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Data items table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS data_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT UNIQUE NOT NULL,
                size_bytes INTEGER NOT NULL,
                created_at TIMESTAMP NOT NULL,
                modified_at TIMESTAMP NOT NULL,
                accessed_at TIMESTAMP NOT NULL,
                content_hash TEXT NOT NULL,
                data_type TEXT NOT NULL,
                service_name TEXT NOT NULL,
                value_score REAL DEFAULT 0.0,
                usage_count INTEGER DEFAULT 0,
                ml_training_value REAL DEFAULT 0.0,
                human_value REAL DEFAULT 0.0,
                bot_value REAL DEFAULT 0.0,
                redundancy_score REAL DEFAULT 0.0,
                preservation_priority INTEGER DEFAULT 0,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Storage analytics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS storage_analytics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                service_name TEXT NOT NULL,
                total_size_bytes INTEGER NOT NULL,
                file_count INTEGER NOT NULL,
                avg_file_size REAL NOT NULL,
                data_types TEXT NOT NULL  -- JSON
            )
        ''')
        
        # Cleanup history table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cleanup_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                cleanup_type TEXT NOT NULL,
                files_deleted INTEGER NOT NULL,
                bytes_freed INTEGER NOT NULL,
                efficiency_score REAL DEFAULT 0.0,
                details TEXT  -- JSON
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _load_config(self, config_path: str):
        """Load configuration from file"""
        with open(config_path, 'r') as f:
            config_data = json.load(f)
            self.config = StorageConfig(**config_data)
    
    def get_storage_status(self) -> Dict[str, Any]:
        """Get current storage status across all services"""
        total_size = 0
        service_usage = {}
        
        for service in self.service_integrator.services:
            items = self.service_integrator.get_service_data_items(service)
            service_size = sum(item.size_bytes for item in items)
            service_usage[service] = {
                'size_bytes': service_size,
                'size_gb': service_size / (1024 * 1024 * 1024),
                'file_count': len(items),
                'allocation_gb': self.config.service_allocations.get(service, 1.0),
                'usage_percent': (service_size / (1024 * 1024 * 1024)) / 
                               self.config.service_allocations.get(service, 1.0)
            }
            total_size += service_size
        
        total_gb = total_size / (1024 * 1024 * 1024)
        usage_percent = total_gb / self.config.total_limit_gb
        
        return {
            'total_size_gb': total_gb,
            'total_limit_gb': self.config.total_limit_gb,
            'usage_percent': usage_percent,
            'available_gb': self.config.total_limit_gb - total_gb,
            'service_usage': service_usage,
            'status': self._get_status_level(usage_percent),
            'recommendations': self._get_recommendations(usage_percent, service_usage)
        }
    
    def _get_status_level(self, usage_percent: float) -> str:
        """Get status level based on usage"""
        if usage_percent >= self.config.emergency_cleanup_threshold:
            return 'CRITICAL'
        elif usage_percent >= self.config.warning_threshold:
            return 'WARNING'
        else:
            return 'OK'
    
    def _get_recommendations(self, usage_percent: float, 
                           service_usage: Dict) -> List[str]:
        """Generate recommendations based on usage"""
        recommendations = []
        
        if usage_percent >= self.config.emergency_cleanup_threshold:
            recommendations.append("Immediate cleanup required - storage critical")
            recommendations.append("Run garbage collection on all services")
            
        elif usage_percent >= self.config.warning_threshold:
            recommendations.append("Consider running cleanup soon")
            
            # Find services over allocation
            for service, usage in service_usage.items():
                if usage['usage_percent'] > 1.0:
                    recommendations.append(f"Service '{service}' is over allocation")
        
        # Suggest specific optimizations
        if usage_percent > 0.5:
            recommendations.append("Consider enabling automatic summarization")
            recommendations.append("Review ML model consolidation opportunities")
        
        return recommendations
    
    def run_intelligent_cleanup(self, target_reduction_gb: float = None, 
                              services: List[str] = None) -> Dict[str, Any]:
        """Run intelligent cleanup across services"""
        if target_reduction_gb is None:
            status = self.get_storage_status()
            if status['usage_percent'] > self.config.warning_threshold:
                # Calculate how much to clean up
                current_gb = status['total_size_gb']
                target_gb = self.config.total_limit_gb * 0.7  # Clean to 70%
                target_reduction_gb = max(0, current_gb - target_gb)
            else:
                target_reduction_gb = 0
        
        if target_reduction_gb == 0:
            return {'message': 'No cleanup needed', 'freed_gb': 0}
        
        # Get all items to consider
        all_items = []
        target_services = services or self.service_integrator.services
        
        for service in target_services:
            items = self.service_integrator.get_service_data_items(service)
            # Update value scores using ML
            for item in items:
                item.value_score = self.ml_optimizer.calculate_data_value(item)
            all_items.extend(items)
        
        # Get deletion candidates
        candidates = self.garbage_bot.evaluate_deletion_candidates(all_items)
        
        # Execute cleanup
        cleanup_result = self.garbage_bot.execute_cleanup(candidates, target_reduction_gb)
        
        # Record cleanup
        self._record_cleanup('intelligent', cleanup_result)
        
        return cleanup_result
    
    def consolidate_ml_weights(self) -> Dict[str, Any]:
        """Consolidate ML weights when they reach stable states"""
        # Find ML model files
        model_items = []
        for service in self.service_integrator.services:
            items = self.service_integrator.get_service_data_items(service)
            model_items.extend([item for item in items if item.data_type == 'ml_model'])
        
        # Group similar models for potential merging
        merge_groups = self.ml_optimizer.find_mergeable_models(model_items)
        
        consolidated = []
        for group in merge_groups:
            if len(group) > 1:
                merged_result = self.ml_optimizer.merge_models(group)
                consolidated.append(merged_result)
        
        return {
            'groups_found': len(merge_groups),
            'models_consolidated': len(consolidated),
            'space_saved_gb': sum(result.get('space_saved_bytes', 0) 
                                for result in consolidated) / (1024**3)
        }
    
    def create_intelligent_summary(self, services: List[str] = None) -> Dict[str, Any]:
        """Create intelligent summary of ecosystem data"""
        target_services = services or self.service_integrator.services
        all_items = []
        
        for service in target_services:
            items = self.service_integrator.get_service_data_items(service)
            all_items.extend(items)
        
        return self.summarization_bot.create_summary(all_items, "ecosystem")
    
    def _record_cleanup(self, cleanup_type: str, result: Dict[str, Any]):
        """Record cleanup operation in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO cleanup_history 
            (cleanup_type, files_deleted, bytes_freed, details)
            VALUES (?, ?, ?, ?)
        ''', (
            cleanup_type,
            result.get('deleted_count', 0),
            int(result.get('freed_gb', 0) * 1024**3),
            json.dumps(result)
        ))
        
        conn.commit()
        conn.close()
    
    def start_monitoring(self):
        """Start continuous monitoring"""
        self.monitoring_active = True
        
        def monitor_loop():
            while self.monitoring_active:
                try:
                    # Update storage analytics
                    self._update_storage_analytics()
                    
                    # Check if automatic cleanup needed
                    status = self.get_storage_status()
                    if status['usage_percent'] > self.config.emergency_cleanup_threshold:
                        logger.warning("Emergency cleanup triggered")
                        self.run_intelligent_cleanup()
                    
                    # Sleep for 5 minutes
                    time.sleep(300)
                    
                except Exception as e:
                    logger.error(f"Error in monitoring loop: {e}")
                    time.sleep(60)  # Wait a minute on error
        
        threading.Thread(target=monitor_loop, daemon=True).start()
        logger.info("Storage monitoring started")
    
    def _update_storage_analytics(self):
        """Update storage analytics in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for service in self.service_integrator.services:
            items = self.service_integrator.get_service_data_items(service)
            
            if items:
                total_size = sum(item.size_bytes for item in items)
                avg_size = total_size / len(items)
                
                # Count by data type
                type_counts = {}
                for item in items:
                    type_counts[item.data_type] = type_counts.get(item.data_type, 0) + 1
                
                cursor.execute('''
                    INSERT INTO storage_analytics 
                    (service_name, total_size_bytes, file_count, avg_file_size, data_types)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    service,
                    total_size,
                    len(items),
                    avg_size,
                    json.dumps(type_counts)
                ))
        
        conn.commit()
        conn.close()

# Flask web interface
app = Flask(__name__)
CORS(app)

# Global manager instance
lifecycle_manager = None

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'monitoring_active': lifecycle_manager.monitoring_active if lifecycle_manager else False
    })

@app.route('/status', methods=['GET'])
def get_status():
    """Get storage status"""
    if not lifecycle_manager:
        return jsonify({'error': 'Manager not initialized'}), 500
    
    return jsonify(lifecycle_manager.get_storage_status())

@app.route('/cleanup', methods=['POST'])
def run_cleanup():
    """Run intelligent cleanup"""
    if not lifecycle_manager:
        return jsonify({'error': 'Manager not initialized'}), 500
    
    data = request.get_json() or {}
    target_gb = data.get('target_reduction_gb')
    services = data.get('services')
    
    result = lifecycle_manager.run_intelligent_cleanup(target_gb, services)
    return jsonify(result)

@app.route('/consolidate', methods=['POST'])
def consolidate_models():
    """Consolidate ML models"""
    if not lifecycle_manager:
        return jsonify({'error': 'Manager not initialized'}), 500
    
    result = lifecycle_manager.consolidate_ml_weights()
    return jsonify(result)

@app.route('/summarize', methods=['POST'])
def create_summary():
    """Create data summary"""
    if not lifecycle_manager:
        return jsonify({'error': 'Manager not initialized'}), 500
    
    data = request.get_json() or {}
    services = data.get('services')
    
    result = lifecycle_manager.create_intelligent_summary(services)
    return jsonify(result)

@app.route('/dashboard', methods=['GET'])
def dashboard():
    """Simple web dashboard"""
    if not lifecycle_manager:
        return "Manager not initialized", 500
    
    status = lifecycle_manager.get_storage_status()
    
    html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Data Lifecycle Manager Dashboard</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .status-ok { color: green; }
            .status-warning { color: orange; }
            .status-critical { color: red; }
            .metric { background: #f5f5f5; padding: 10px; margin: 10px 0; border-radius: 5px; }
        </style>
    </head>
    <body>
        <h1>Data Lifecycle Manager Dashboard</h1>
        
        <div class="metric">
            <h3>Storage Status: <span class="status-{{ status['status'].lower() }}">{{ status['status'] }}</span></h3>
            <p>Usage: {{ "%.2f"|format(status['usage_percent'] * 100) }}% ({{ "%.2f"|format(status['total_size_gb']) }} GB / {{ status['total_limit_gb'] }} GB)</p>
            <p>Available: {{ "%.2f"|format(status['available_gb']) }} GB</p>
        </div>
        
        <div class="metric">
            <h3>Recommendations</h3>
            <ul>
            {% for rec in status['recommendations'] %}
                <li>{{ rec }}</li>
            {% endfor %}
            </ul>
        </div>
        
        <div class="metric">
            <h3>Service Usage</h3>
            {% for service, usage in status['service_usage'].items() %}
                <p><strong>{{ service }}:</strong> {{ "%.2f"|format(usage['size_gb']) }} GB 
                   ({{ "%.1f"|format(usage['usage_percent'] * 100) }}% of allocation)</p>
            {% endfor %}
        </div>
        
        <div style="margin-top: 30px;">
            <button onclick="runCleanup()">Run Cleanup</button>
            <button onclick="consolidateModels()">Consolidate Models</button>
            <button onclick="createSummary()">Create Summary</button>
        </div>
        
        <script>
            function runCleanup() {
                fetch('/cleanup', { method: 'POST' })
                    .then(r => r.json())
                    .then(data => {
                        alert('Cleanup completed: ' + data.freed_gb + ' GB freed');
                        location.reload();
                    });
            }
            
            function consolidateModels() {
                fetch('/consolidate', { method: 'POST' })
                    .then(r => r.json())
                    .then(data => {
                        alert('Consolidation completed: ' + data.space_saved_gb + ' GB saved');
                        location.reload();
                    });
            }
            
            function createSummary() {
                fetch('/summarize', { method: 'POST' })
                    .then(r => r.json())
                    .then(data => {
                        alert('Summary created with quality score: ' + data.quality_score);
                    });
            }
        </script>
    </body>
    </html>
    '''
    
    from jinja2 import Template
    template = Template(html)
    return template.render(status=status)

def main():
    """Main entry point"""
    global lifecycle_manager
    
    # Initialize the manager
    lifecycle_manager = DataLifecycleManager()
    
    # Start monitoring
    lifecycle_manager.start_monitoring()
    
    logger.info("Data Lifecycle Manager initialized successfully")
    logger.info(f"Monitoring {len(lifecycle_manager.service_integrator.services)} services")
    
    # Start web interface
    port = int(os.getenv('PORT', 8490))
    app.run(host='0.0.0.0', port=port, debug=False)

if __name__ == '__main__':
    main()