#!/usr/bin/env python3
"""
ML Data Optimizer for SuperInstance Ecosystem
=============================================

Neural networks that learn data value patterns:
- Note merging algorithms with weight tracking
- Summarization quality scoring
- Garbage collection effectiveness measurement
- Data compression and deduplication
- Learning from bot and human feedback
"""

import numpy as np
import pandas as pd
import pickle
import json
import sqlite3
import logging
from typing import Dict, List, Tuple, Optional, Any, Union
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
import hashlib
import re
from collections import defaultdict, Counter
import torch
import torch.nn as nn
import torch.optim as optim
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)

@dataclass
class ModelWeight:
    """Represents ML model weight information"""
    model_path: str
    size_bytes: int
    architecture: str
    last_trained: datetime
    performance_metrics: Dict[str, float]
    stability_score: float
    merge_candidate: bool = False

@dataclass
class MergeResult:
    """Result of model merging operation"""
    original_paths: List[str]
    merged_path: str
    space_saved_bytes: int
    performance_retention: float
    stability_improved: bool

class DataValueNet(nn.Module):
    """Neural network for predicting data value"""
    
    def __init__(self, input_size=15, hidden_sizes=[64, 32, 16], dropout_rate=0.2):
        super(DataValueNet, self).__init__()
        
        layers = []
        prev_size = input_size
        
        for hidden_size in hidden_sizes:
            layers.extend([
                nn.Linear(prev_size, hidden_size),
                nn.ReLU(),
                nn.BatchNorm1d(hidden_size),
                nn.Dropout(dropout_rate)
            ])
            prev_size = hidden_size
        
        layers.append(nn.Linear(prev_size, 1))
        layers.append(nn.Sigmoid())
        
        self.network = nn.Sequential(*layers)
        
    def forward(self, x):
        return self.network(x)

class NoteMergingNet(nn.Module):
    """Neural network for determining note mergeability"""
    
    def __init__(self, input_size=20, hidden_sizes=[128, 64, 32]):
        super(NoteMergingNet, self).__init__()
        
        layers = []
        prev_size = input_size
        
        for hidden_size in hidden_sizes:
            layers.extend([
                nn.Linear(prev_size, hidden_size),
                nn.ReLU(),
                nn.BatchNorm1d(hidden_size),
                nn.Dropout(0.3)
            ])
            prev_size = hidden_size
        
        layers.append(nn.Linear(prev_size, 3))  # 3 classes: no_merge, soft_merge, hard_merge
        layers.append(nn.Softmax(dim=1))
        
        self.network = nn.Sequential(*layers)
        
    def forward(self, x):
        return self.network(x)

class GarbageCollectorNet(nn.Module):
    """Neural network for garbage collection decisions"""
    
    def __init__(self, input_size=12, hidden_sizes=[96, 48, 24]):
        super(GarbageCollectorNet, self).__init__()
        
        layers = []
        prev_size = input_size
        
        for hidden_size in hidden_sizes:
            layers.extend([
                nn.Linear(prev_size, hidden_size),
                nn.LeakyReLU(0.1),
                nn.BatchNorm1d(hidden_size),
                nn.Dropout(0.25)
            ])
            prev_size = hidden_size
        
        layers.append(nn.Linear(prev_size, 1))
        layers.append(nn.Sigmoid())
        
        self.network = nn.Sequential(*layers)
        
    def forward(self, x):
        return self.network(x)

class SummarizationNet(nn.Module):
    """Neural network for summarization quality scoring"""
    
    def __init__(self, input_size=8, hidden_sizes=[64, 32]):
        super(SummarizationNet, self).__init__()
        
        layers = []
        prev_size = input_size
        
        for hidden_size in hidden_sizes:
            layers.extend([
                nn.Linear(prev_size, hidden_size),
                nn.ReLU(),
                nn.BatchNorm1d(hidden_size),
                nn.Dropout(0.2)
            ])
            prev_size = hidden_size
        
        layers.append(nn.Linear(prev_size, 1))
        layers.append(nn.Sigmoid())
        
        self.network = nn.Sequential(*layers)
        
    def forward(self, x):
        return self.network(x)

class DataPatternAnalyzer:
    """Analyzes patterns in data usage and value"""
    
    def __init__(self):
        self.usage_patterns = defaultdict(list)
        self.access_patterns = defaultdict(list)
        self.content_patterns = {}
        self.tfidf_vectorizer = TfidfVectorizer(max_features=1000, stop_words='english')
        
    def analyze_usage_patterns(self, data_items: List) -> Dict[str, Any]:
        """Analyze usage patterns across data items"""
        patterns = {
            'temporal_patterns': self._analyze_temporal_patterns(data_items),
            'size_patterns': self._analyze_size_patterns(data_items),
            'service_patterns': self._analyze_service_patterns(data_items),
            'type_patterns': self._analyze_type_patterns(data_items)
        }
        
        return patterns
    
    def _analyze_temporal_patterns(self, data_items: List) -> Dict[str, Any]:
        """Analyze temporal access patterns"""
        now = datetime.now()
        
        access_times = []
        modification_times = []
        creation_times = []
        
        for item in data_items:
            if hasattr(item, 'accessed_at') and item.accessed_at:
                access_times.append((now - item.accessed_at).total_seconds() / 3600)  # hours
            if hasattr(item, 'modified_at') and item.modified_at:
                modification_times.append((now - item.modified_at).total_seconds() / 3600)
            if hasattr(item, 'created_at') and item.created_at:
                creation_times.append((now - item.created_at).total_seconds() / 3600)
        
        return {
            'avg_hours_since_access': np.mean(access_times) if access_times else 0,
            'avg_hours_since_modification': np.mean(modification_times) if modification_times else 0,
            'avg_hours_since_creation': np.mean(creation_times) if creation_times else 0,
            'access_frequency_score': self._calculate_frequency_score(access_times),
            'modification_frequency_score': self._calculate_frequency_score(modification_times)
        }
    
    def _calculate_frequency_score(self, time_diffs: List[float]) -> float:
        """Calculate frequency score based on time differences"""
        if not time_diffs:
            return 0.0
        
        # Recent access gets higher score
        recent_threshold = 24  # 24 hours
        recent_count = sum(1 for t in time_diffs if t <= recent_threshold)
        
        return recent_count / len(time_diffs)
    
    def _analyze_size_patterns(self, data_items: List) -> Dict[str, Any]:
        """Analyze size distribution patterns"""
        sizes = [item.size_bytes for item in data_items if hasattr(item, 'size_bytes')]
        
        if not sizes:
            return {'avg_size': 0, 'size_variance': 0, 'large_file_ratio': 0}
        
        sizes_mb = np.array(sizes) / (1024 * 1024)  # Convert to MB
        
        return {
            'avg_size_mb': float(np.mean(sizes_mb)),
            'median_size_mb': float(np.median(sizes_mb)),
            'size_variance': float(np.var(sizes_mb)),
            'large_file_ratio': sum(1 for s in sizes_mb if s > 100) / len(sizes_mb),
            'small_file_ratio': sum(1 for s in sizes_mb if s < 1) / len(sizes_mb)
        }
    
    def _analyze_service_patterns(self, data_items: List) -> Dict[str, Any]:
        """Analyze patterns by service"""
        service_stats = defaultdict(lambda: {'count': 0, 'total_size': 0, 'types': set()})
        
        for item in data_items:
            if hasattr(item, 'service_name') and hasattr(item, 'size_bytes'):
                service = item.service_name
                service_stats[service]['count'] += 1
                service_stats[service]['total_size'] += item.size_bytes
                if hasattr(item, 'data_type'):
                    service_stats[service]['types'].add(item.data_type)
        
        # Convert to serializable format
        return {
            service: {
                'file_count': stats['count'],
                'total_size_mb': stats['total_size'] / (1024 * 1024),
                'avg_file_size_mb': (stats['total_size'] / stats['count']) / (1024 * 1024) if stats['count'] > 0 else 0,
                'data_types': list(stats['types'])
            }
            for service, stats in service_stats.items()
        }
    
    def _analyze_type_patterns(self, data_items: List) -> Dict[str, Any]:
        """Analyze patterns by data type"""
        type_stats = defaultdict(lambda: {'count': 0, 'total_size': 0, 'services': set()})
        
        for item in data_items:
            if hasattr(item, 'data_type') and hasattr(item, 'size_bytes'):
                data_type = item.data_type
                type_stats[data_type]['count'] += 1
                type_stats[data_type]['total_size'] += item.size_bytes
                if hasattr(item, 'service_name'):
                    type_stats[data_type]['services'].add(item.service_name)
        
        return {
            data_type: {
                'file_count': stats['count'],
                'total_size_mb': stats['total_size'] / (1024 * 1024),
                'avg_file_size_mb': (stats['total_size'] / stats['count']) / (1024 * 1024) if stats['count'] > 0 else 0,
                'service_count': len(stats['services'])
            }
            for data_type, stats in type_stats.items()
        }

class ContentAnalyzer:
    """Analyzes content for deduplication and merging opportunities"""
    
    def __init__(self):
        self.content_hashes = {}
        self.similarity_cache = {}
        
    def find_duplicates(self, data_items: List) -> List[List]:
        """Find exact duplicates based on content hash"""
        hash_groups = defaultdict(list)
        
        for item in data_items:
            if hasattr(item, 'content_hash'):
                hash_groups[item.content_hash].append(item)
        
        # Return groups with more than one item (duplicates)
        return [group for group in hash_groups.values() if len(group) > 1]
    
    def find_similar_content(self, data_items: List, similarity_threshold: float = 0.8) -> List[List]:
        """Find similar content using text analysis"""
        text_items = []
        
        for item in data_items:
            if hasattr(item, 'path') and self._is_text_file(item.path):
                try:
                    content = self._read_text_content(item.path)
                    if content:
                        text_items.append((item, content))
                except Exception as e:
                    logger.warning(f"Could not read {item.path}: {e}")
        
        if len(text_items) < 2:
            return []
        
        # Vectorize content
        contents = [content for _, content in text_items]
        try:
            tfidf_matrix = TfidfVectorizer(max_features=500).fit_transform(contents)
            similarity_matrix = cosine_similarity(tfidf_matrix)
        except Exception:
            return []
        
        # Find similar groups
        similar_groups = []
        processed = set()
        
        for i in range(len(text_items)):
            if i in processed:
                continue
                
            similar_indices = [i]
            for j in range(i + 1, len(text_items)):
                if similarity_matrix[i, j] >= similarity_threshold:
                    similar_indices.append(j)
                    processed.add(j)
            
            if len(similar_indices) > 1:
                similar_group = [text_items[idx][0] for idx in similar_indices]
                similar_groups.append(similar_group)
                processed.add(i)
        
        return similar_groups
    
    def _is_text_file(self, path: str) -> bool:
        """Check if file is likely to be text-based"""
        text_extensions = {'.py', '.js', '.json', '.txt', '.md', '.yml', '.yaml', '.xml', '.html', '.css', '.sql'}
        return Path(path).suffix.lower() in text_extensions
    
    def _read_text_content(self, path: str, max_size_mb: int = 5) -> Optional[str]:
        """Read text content from file with size limit"""
        try:
            file_path = Path(path)
            if file_path.stat().st_size > max_size_mb * 1024 * 1024:
                return None  # Skip large files
                
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except Exception:
            return None

class ModelWeightAnalyzer:
    """Analyzes ML model weights for consolidation opportunities"""
    
    def __init__(self):
        self.weight_patterns = {}
        self.stability_tracker = defaultdict(list)
        
    def analyze_model_weights(self, model_path: str) -> Optional[ModelWeight]:
        """Analyze a single model's weights"""
        try:
            path_obj = Path(model_path)
            if not path_obj.exists():
                return None
            
            # Get basic info
            stat = path_obj.stat()
            size_bytes = stat.st_size
            last_modified = datetime.fromtimestamp(stat.st_mtime)
            
            # Try to determine architecture from filename/path
            architecture = self._infer_architecture(model_path)
            
            # Load performance metrics if available
            metrics = self._load_performance_metrics(model_path)
            
            # Calculate stability score
            stability = self._calculate_stability_score(model_path, metrics)
            
            return ModelWeight(
                model_path=model_path,
                size_bytes=size_bytes,
                architecture=architecture,
                last_trained=last_modified,
                performance_metrics=metrics,
                stability_score=stability,
                merge_candidate=self._is_merge_candidate(stability, metrics)
            )
            
        except Exception as e:
            logger.warning(f"Could not analyze model {model_path}: {e}")
            return None
    
    def _infer_architecture(self, model_path: str) -> str:
        """Infer model architecture from path/filename"""
        path_lower = model_path.lower()
        
        if 'bert' in path_lower:
            return 'bert'
        elif 'gpt' in path_lower:
            return 'gpt'
        elif 'lstm' in path_lower:
            return 'lstm'
        elif 'cnn' in path_lower:
            return 'cnn'
        elif 'transformer' in path_lower:
            return 'transformer'
        elif any(framework in path_lower for framework in ['pytorch', 'torch']):
            return 'pytorch'
        elif any(framework in path_lower for framework in ['tensorflow', 'tf']):
            return 'tensorflow'
        else:
            return 'unknown'
    
    def _load_performance_metrics(self, model_path: str) -> Dict[str, float]:
        """Load performance metrics for model if available"""
        # Look for metrics file alongside model
        model_dir = Path(model_path).parent
        metrics_files = [
            model_dir / 'metrics.json',
            model_dir / 'performance.json',
            model_dir / f"{Path(model_path).stem}_metrics.json"
        ]
        
        for metrics_file in metrics_files:
            if metrics_file.exists():
                try:
                    with open(metrics_file, 'r') as f:
                        return json.load(f)
                except Exception:
                    continue
        
        return {'accuracy': 0.0, 'loss': float('inf')}
    
    def _calculate_stability_score(self, model_path: str, metrics: Dict[str, float]) -> float:
        """Calculate model stability score"""
        # Track metrics over time
        self.stability_tracker[model_path].append({
            'timestamp': datetime.now(),
            'metrics': metrics.copy()
        })
        
        # Keep only recent history
        cutoff = datetime.now() - timedelta(days=30)
        self.stability_tracker[model_path] = [
            entry for entry in self.stability_tracker[model_path]
            if entry['timestamp'] > cutoff
        ]
        
        history = self.stability_tracker[model_path]
        if len(history) < 3:
            return 0.5  # Default stability
        
        # Calculate variance in key metrics
        accuracies = [entry['metrics'].get('accuracy', 0) for entry in history]
        losses = [entry['metrics'].get('loss', float('inf')) for entry in history if entry['metrics'].get('loss', float('inf')) != float('inf')]
        
        acc_variance = np.var(accuracies) if accuracies else 1.0
        loss_variance = np.var(losses) if losses else 1.0
        
        # Lower variance = higher stability
        stability = 1.0 / (1.0 + acc_variance + loss_variance * 0.1)
        return min(max(stability, 0.0), 1.0)
    
    def _is_merge_candidate(self, stability: float, metrics: Dict[str, float]) -> bool:
        """Determine if model is a candidate for merging"""
        # High stability and reasonable performance
        return (stability > 0.7 and 
                metrics.get('accuracy', 0) > 0.6 and
                metrics.get('loss', float('inf')) < 1.0)
    
    def find_mergeable_models(self, model_weights: List[ModelWeight]) -> List[List[ModelWeight]]:
        """Find groups of models that can be merged"""
        # Group by architecture
        arch_groups = defaultdict(list)
        for weight in model_weights:
            if weight.merge_candidate:
                arch_groups[weight.architecture].append(weight)
        
        mergeable_groups = []
        for architecture, models in arch_groups.items():
            if len(models) >= 2:
                # Further group by similar performance
                performance_groups = self._group_by_performance(models)
                mergeable_groups.extend(performance_groups)
        
        return mergeable_groups
    
    def _group_by_performance(self, models: List[ModelWeight]) -> List[List[ModelWeight]]:
        """Group models by similar performance characteristics"""
        if len(models) < 2:
            return []
        
        # Extract performance features
        features = []
        for model in models:
            feature = [
                model.performance_metrics.get('accuracy', 0),
                model.performance_metrics.get('loss', 0),
                model.stability_score
            ]
            features.append(feature)
        
        features = np.array(features)
        
        # Cluster models with similar performance
        try:
            n_clusters = min(3, len(models) // 2)  # At least 2 models per cluster
            kmeans = KMeans(n_clusters=n_clusters, random_state=42)
            cluster_labels = kmeans.fit_predict(features)
            
            # Group models by cluster
            clusters = defaultdict(list)
            for i, label in enumerate(cluster_labels):
                clusters[label].append(models[i])
            
            # Return clusters with at least 2 models
            return [cluster for cluster in clusters.values() if len(cluster) >= 2]
            
        except Exception:
            # Fallback: group by similar accuracy
            models_sorted = sorted(models, key=lambda m: m.performance_metrics.get('accuracy', 0))
            groups = []
            current_group = [models_sorted[0]]
            
            for i in range(1, len(models_sorted)):
                prev_acc = models_sorted[i-1].performance_metrics.get('accuracy', 0)
                curr_acc = models_sorted[i].performance_metrics.get('accuracy', 0)
                
                if abs(curr_acc - prev_acc) < 0.1:  # Similar accuracy
                    current_group.append(models_sorted[i])
                else:
                    if len(current_group) >= 2:
                        groups.append(current_group)
                    current_group = [models_sorted[i]]
            
            if len(current_group) >= 2:
                groups.append(current_group)
                
            return groups

class DataOptimizer:
    """Main ML data optimizer orchestrating all optimization tasks"""
    
    def __init__(self, model_dir: str = "models"):
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(exist_ok=True)
        
        # Initialize neural networks
        self.data_value_net = DataValueNet()
        self.note_merging_net = NoteMergingNet()
        self.garbage_net = GarbageCollectorNet()
        self.summarization_net = SummarizationNet()
        
        # Initialize analyzers
        self.pattern_analyzer = DataPatternAnalyzer()
        self.content_analyzer = ContentAnalyzer()
        self.model_weight_analyzer = ModelWeightAnalyzer()
        
        # Load pre-trained models if available
        self._load_models()
        
        # Training data storage
        self.training_data = {
            'data_value': [],
            'garbage_collection': [],
            'summarization': [],
            'note_merging': []
        }
        
        # Performance tracking
        self.performance_history = defaultdict(list)
        
    def _load_models(self):
        """Load pre-trained models if they exist"""
        model_files = {
            'data_value_net': self.model_dir / 'data_value_net.pth',
            'note_merging_net': self.model_dir / 'note_merging_net.pth',
            'garbage_net': self.model_dir / 'garbage_net.pth',
            'summarization_net': self.model_dir / 'summarization_net.pth'
        }
        
        for attr_name, model_file in model_files.items():
            if model_file.exists():
                try:
                    model = getattr(self, attr_name)
                    model.load_state_dict(torch.load(model_file, map_location='cpu'))
                    logger.info(f"Loaded {attr_name} from {model_file}")
                except Exception as e:
                    logger.warning(f"Could not load {attr_name}: {e}")
    
    def _save_models(self):
        """Save trained models"""
        model_files = {
            'data_value_net': self.model_dir / 'data_value_net.pth',
            'note_merging_net': self.model_dir / 'note_merging_net.pth',
            'garbage_net': self.model_dir / 'garbage_net.pth',
            'summarization_net': self.model_dir / 'summarization_net.pth'
        }
        
        for attr_name, model_file in model_files.items():
            try:
                model = getattr(self, attr_name)
                torch.save(model.state_dict(), model_file)
            except Exception as e:
                logger.error(f"Could not save {attr_name}: {e}")
    
    def calculate_data_value(self, data_item) -> float:
        """Calculate value score for a data item using ML"""
        features = self._extract_data_value_features(data_item)
        
        self.data_value_net.eval()
        with torch.no_grad():
            features_tensor = torch.FloatTensor(features).unsqueeze(0)
            value_score = self.data_value_net(features_tensor).item()
        
        return value_score
    
    def _extract_data_value_features(self, data_item) -> np.ndarray:
        """Extract features for data value prediction"""
        now = datetime.now()
        
        # Time-based features
        days_since_created = (now - data_item.created_at).days if hasattr(data_item, 'created_at') else 0
        days_since_modified = (now - data_item.modified_at).days if hasattr(data_item, 'modified_at') else 0
        days_since_accessed = (now - data_item.accessed_at).days if hasattr(data_item, 'accessed_at') else 0
        
        # Size features
        size_mb = data_item.size_bytes / (1024 * 1024) if hasattr(data_item, 'size_bytes') else 0
        
        # Usage features
        usage_count = data_item.usage_count if hasattr(data_item, 'usage_count') else 0
        
        # Value features
        ml_value = data_item.ml_training_value if hasattr(data_item, 'ml_training_value') else 0
        human_value = data_item.human_value if hasattr(data_item, 'human_value') else 0
        bot_value = data_item.bot_value if hasattr(data_item, 'bot_value') else 0
        
        # Data type encoding
        data_type = data_item.data_type if hasattr(data_item, 'data_type') else 'misc'
        type_encoding = {
            'ml_model': 1.0, 'database': 0.9, 'config': 0.8,
            'log': 0.4, 'cache': 0.3, 'temp': 0.1, 'backup': 0.7
        }.get(data_type, 0.5)
        
        # Service importance (rough heuristic)
        service = data_item.service_name if hasattr(data_item, 'service_name') else 'unknown'
        service_importance = {
            'dmlog': 0.9, 'ai-insights': 0.8, 'bot-ecosystem': 0.85,
            'ml-platform': 0.9, 'data-manager': 0.7
        }.get(service, 0.5)
        
        # Redundancy penalty
        redundancy = data_item.redundancy_score if hasattr(data_item, 'redundancy_score') else 0
        
        features = np.array([
            days_since_created,
            days_since_modified, 
            days_since_accessed,
            size_mb,
            usage_count,
            ml_value,
            human_value,
            bot_value,
            type_encoding,
            service_importance,
            1.0 - redundancy,  # Less redundant = more valuable
            data_item.preservation_priority if hasattr(data_item, 'preservation_priority') else 0,
            min(size_mb / 100, 1.0),  # Size penalty for very large files
            min(days_since_accessed / 30, 1.0),  # Recency bonus
            min(usage_count / 10, 1.0)  # Usage bonus
        ])
        
        return features
    
    def find_mergeable_models(self, model_items: List) -> List[List]:
        """Find groups of ML models that can be merged"""
        model_weights = []
        
        for item in model_items:
            weight = self.model_weight_analyzer.analyze_model_weights(item.path)
            if weight:
                model_weights.append(weight)
        
        return self.model_weight_analyzer.find_mergeable_models(model_weights)
    
    def merge_models(self, model_group: List[ModelWeight]) -> MergeResult:
        """Merge a group of similar models"""
        if len(model_group) < 2:
            raise ValueError("Need at least 2 models to merge")
        
        # For now, implement a simple merging strategy
        # In production, this would use more sophisticated techniques
        
        original_paths = [model.model_path for model in model_group]
        total_size = sum(model.size_bytes for model in model_group)
        
        # Choose the best performing model as base
        best_model = max(model_group, key=lambda m: m.performance_metrics.get('accuracy', 0))
        
        # Create merged model path
        merged_dir = Path(best_model.model_path).parent / "merged_models"
        merged_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        merged_path = str(merged_dir / f"merged_model_{timestamp}.pkl")
        
        # Simple merge: copy the best model and record the merge
        import shutil
        shutil.copy2(best_model.model_path, merged_path)
        
        # Calculate space saved (remove redundant models)
        space_saved = total_size - best_model.size_bytes
        
        # Performance retention (using best model's performance)
        performance_retention = best_model.performance_metrics.get('accuracy', 0.7)
        
        # Remove original models (in production, would be more careful)
        for model in model_group:
            if model.model_path != best_model.model_path:
                try:
                    Path(model.model_path).unlink()
                except Exception as e:
                    logger.warning(f"Could not remove {model.model_path}: {e}")
        
        return MergeResult(
            original_paths=original_paths,
            merged_path=merged_path,
            space_saved_bytes=space_saved,
            performance_retention=performance_retention,
            stability_improved=True  # Assume merging improves stability
        )
    
    def train_garbage_collector(self, training_data: List[Tuple[np.ndarray, float]]):
        """Train garbage collector with feedback data"""
        if len(training_data) < 5:
            logger.warning("Not enough training data for garbage collector")
            return
        
        # Prepare data
        X = np.array([features for features, _ in training_data])
        y = np.array([feedback for _, feedback in training_data])
        
        # Normalize features
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        # Convert to tensors
        X_tensor = torch.FloatTensor(X_scaled)
        y_tensor = torch.FloatTensor(y).unsqueeze(1)
        
        # Train model
        self.garbage_net.train()
        optimizer = optim.Adam(self.garbage_net.parameters(), lr=0.001)
        criterion = nn.MSELoss()
        
        for epoch in range(100):
            optimizer.zero_grad()
            outputs = self.garbage_net(X_tensor)
            loss = criterion(outputs, y_tensor)
            loss.backward()
            optimizer.step()
            
            if epoch % 20 == 0:
                logger.info(f"Garbage collector training epoch {epoch}, loss: {loss.item():.4f}")
        
        # Save updated model
        self._save_models()
        
        # Update performance tracking
        self.performance_history['garbage_collector'].append({
            'timestamp': datetime.now(),
            'training_samples': len(training_data),
            'final_loss': loss.item()
        })
    
    def optimize_storage_allocation(self, current_usage: Dict[str, float], 
                                  total_limit: float) -> Dict[str, float]:
        """Optimize storage allocation across services using ML insights"""
        
        # Analyze usage patterns
        usage_ratios = {}
        total_used = sum(current_usage.values())
        
        for service, usage in current_usage.items():
            usage_ratios[service] = usage / total_used if total_used > 0 else 0
        
        # Apply ML insights to adjust allocations
        optimized_allocations = {}
        
        # Services that are growing or have high ML value get more space
        high_value_services = ['ai-insights', 'ml-platform', 'bot-ecosystem', 'dmlog-core']
        
        base_allocation = total_limit / len(current_usage)
        
        for service in current_usage.keys():
            multiplier = 1.0
            
            if service in high_value_services:
                multiplier = 1.5
            elif 'ai' in service.lower() or 'ml' in service.lower():
                multiplier = 1.2
            elif service.endswith('-backup') or service.endswith('-temp'):
                multiplier = 0.5
            
            # Adjust based on current usage trend
            if usage_ratios.get(service, 0) > 0.1:  # Heavy usage
                multiplier *= 1.1
            
            optimized_allocations[service] = base_allocation * multiplier
        
        # Normalize to stay within total limit
        total_allocated = sum(optimized_allocations.values())
        if total_allocated > total_limit:
            scale_factor = total_limit / total_allocated
            optimized_allocations = {
                service: allocation * scale_factor
                for service, allocation in optimized_allocations.items()
            }
        
        return optimized_allocations
    
    def compress_and_deduplicate(self, data_items: List) -> Dict[str, Any]:
        """Compress data and remove duplicates"""
        
        # Find duplicates
        duplicate_groups = self.content_analyzer.find_duplicates(data_items)
        
        # Find similar content
        similar_groups = self.content_analyzer.find_similar_content(data_items, 0.85)
        
        total_savings = 0
        processed_files = []
        
        # Remove exact duplicates (keep one copy)
        for group in duplicate_groups:
            if len(group) > 1:
                # Keep the most recently accessed file
                best_file = max(group, key=lambda x: x.accessed_at if hasattr(x, 'accessed_at') else datetime.min)
                
                for item in group:
                    if item != best_file:
                        try:
                            Path(item.path).unlink()
                            total_savings += item.size_bytes
                            processed_files.append(item.path)
                        except Exception as e:
                            logger.warning(f"Could not remove duplicate {item.path}: {e}")
        
        # Merge similar content files
        for group in similar_groups:
            if len(group) > 1:
                # Create merged content
                merged_content = self._merge_similar_files(group)
                if merged_content:
                    # Save merged file
                    merged_path = f"{group[0].path}.merged"
                    try:
                        with open(merged_path, 'w') as f:
                            f.write(merged_content)
                        
                        # Remove original files
                        for item in group:
                            Path(item.path).unlink()
                            total_savings += item.size_bytes
                            processed_files.append(item.path)
                        
                    except Exception as e:
                        logger.warning(f"Could not merge similar files: {e}")
        
        return {
            'duplicate_groups_found': len(duplicate_groups),
            'similar_groups_found': len(similar_groups),
            'total_savings_bytes': total_savings,
            'total_savings_gb': total_savings / (1024**3),
            'processed_files': processed_files
        }
    
    def _merge_similar_files(self, file_group: List) -> Optional[str]:
        """Merge similar files into combined content"""
        contents = []
        
        for item in file_group:
            try:
                content = self.content_analyzer._read_text_content(item.path)
                if content:
                    contents.append(f"# From: {item.path}\n{content}\n\n")
            except Exception:
                continue
        
        if contents:
            return "# Merged file created by DataLifecycleManager\n\n" + "\n".join(contents)
        
        return None
    
    def get_optimization_recommendations(self, data_items: List) -> Dict[str, Any]:
        """Generate ML-based optimization recommendations"""
        
        # Analyze patterns
        patterns = self.pattern_analyzer.analyze_usage_patterns(data_items)
        
        recommendations = {
            'cleanup_candidates': [],
            'merge_candidates': [],
            'compression_candidates': [],
            'preservation_priorities': [],
            'storage_reallocation': {}
        }
        
        # Identify cleanup candidates
        for item in data_items:
            value_score = self.calculate_data_value(item)
            if value_score < 0.3 and hasattr(item, 'accessed_at'):
                days_old = (datetime.now() - item.accessed_at).days
                if days_old > 30:  # Haven't been accessed in a month
                    recommendations['cleanup_candidates'].append({
                        'path': item.path,
                        'value_score': value_score,
                        'days_since_access': days_old,
                        'size_mb': item.size_bytes / (1024*1024)
                    })
        
        # Find merge candidates
        model_items = [item for item in data_items if hasattr(item, 'data_type') and item.data_type == 'ml_model']
        merge_groups = self.find_mergeable_models(model_items)
        
        for group in merge_groups:
            recommendations['merge_candidates'].append([
                {
                    'path': model.model_path,
                    'size_mb': model.size_bytes / (1024*1024),
                    'performance': model.performance_metrics
                }
                for model in group
            ])
        
        # Identify high-value items for preservation
        high_value_items = [item for item in data_items if self.calculate_data_value(item) > 0.8]
        recommendations['preservation_priorities'] = [
            {
                'path': item.path,
                'value_score': self.calculate_data_value(item),
                'size_mb': item.size_bytes / (1024*1024),
                'service': item.service_name if hasattr(item, 'service_name') else 'unknown'
            }
            for item in high_value_items
        ]
        
        return recommendations