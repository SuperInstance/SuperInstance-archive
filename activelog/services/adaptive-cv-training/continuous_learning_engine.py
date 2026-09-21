"""
Continuous Learning Engine
Self-improving AI system with feedback loops and personalized adaptation
"""

import asyncio
import json
import logging
import sqlite3
import pickle
import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from collections import defaultdict, deque
import threading
import time
import cv2
from sklearn.metrics import accuracy_score, precision_recall_fscore_support
from sklearn.model_selection import train_test_split
import copy

logger = logging.getLogger(__name__)

@dataclass
class LearningExample:
    """Training example with metadata for continuous learning"""
    image_data: np.ndarray
    true_label: str
    predicted_label: str
    confidence: float
    user_id: str
    boat_id: Optional[str]
    timestamp: datetime
    correction_type: str  # 'voice', 'tote_placement', 'user_feedback'
    context: Dict[str, Any]
    
@dataclass
class ModelPerformanceMetric:
    """Performance tracking for continuous improvement"""
    user_id: str
    boat_id: Optional[str]
    species: str
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    sample_count: int
    last_updated: datetime
    improvement_rate: float

class AdaptiveDataset(Dataset):
    """Dynamic dataset that adapts to user corrections"""
    
    def __init__(self, transform=None):
        self.examples = []
        self.transform = transform
        self.species_to_idx = {}
        self.idx_to_species = {}
        self.next_idx = 0
        
    def add_example(self, example: LearningExample):
        """Add new training example"""
        # Map species to index
        if example.true_label not in self.species_to_idx:
            self.species_to_idx[example.true_label] = self.next_idx
            self.idx_to_species[self.next_idx] = example.true_label
            self.next_idx += 1
        
        self.examples.append(example)
    
    def __len__(self):
        return len(self.examples)
    
    def __getitem__(self, idx):
        example = self.examples[idx]
        
        image = example.image_data
        label = self.species_to_idx[example.true_label]
        
        if self.transform:
            image = self.transform(image)
        
        return image, label, {
            'predicted_label': example.predicted_label,
            'confidence': example.confidence,
            'user_id': example.user_id,
            'boat_id': example.boat_id,
            'correction_type': example.correction_type,
            'timestamp': example.timestamp
        }
    
    def get_user_examples(self, user_id: str, boat_id: Optional[str] = None) -> List[int]:
        """Get indices of examples from specific user/boat"""
        indices = []
        for i, example in enumerate(self.examples):
            if example.user_id == user_id:
                if boat_id is None or example.boat_id == boat_id:
                    indices.append(i)
        return indices
    
    def get_species_distribution(self, user_id: str = None) -> Dict[str, int]:
        """Get species distribution for user or globally"""
        distribution = defaultdict(int)
        for example in self.examples:
            if user_id is None or example.user_id == user_id:
                distribution[example.true_label] += 1
        return dict(distribution)

class PersonalizedModelManager:
    """Manages personalized models for different users/boats"""
    
    def __init__(self, base_model, device):
        self.base_model = base_model
        self.device = device
        self.user_models = {}
        self.user_optimizers = {}
        self.adaptation_layers = {}
        
    def get_user_model(self, user_id: str, boat_id: Optional[str] = None):
        """Get or create personalized model for user/boat"""
        model_key = f"{user_id}_{boat_id}" if boat_id else user_id
        
        if model_key not in self.user_models:
            # Create personalized model by copying base model
            user_model = copy.deepcopy(self.base_model)
            
            # Add adaptation layers
            adaptation_layer = nn.Sequential(
                nn.Linear(512, 256),
                nn.ReLU(),
                nn.Dropout(0.3),
                nn.Linear(256, 128),
                nn.ReLU(),
                nn.Linear(128, len(self.base_model.species_prototypes) if hasattr(self.base_model, 'species_prototypes') else 50)
            ).to(self.device)
            
            self.user_models[model_key] = user_model
            self.adaptation_layers[model_key] = adaptation_layer
            self.user_optimizers[model_key] = optim.Adam(
                list(user_model.parameters()) + list(adaptation_layer.parameters()),
                lr=0.001,
                weight_decay=1e-4
            )
            
            logger.info(f"Created personalized model for {model_key}")
        
        return self.user_models[model_key], self.adaptation_layers[model_key]
    
    def update_user_model(self, user_id: str, examples: List[LearningExample], 
                         boat_id: Optional[str] = None):
        """Update user's personalized model with new examples"""
        model_key = f"{user_id}_{boat_id}" if boat_id else user_id
        
        if model_key not in self.user_models:
            self.get_user_model(user_id, boat_id)
        
        model = self.user_models[model_key]
        adaptation_layer = self.adaptation_layers[model_key]
        optimizer = self.user_optimizers[model_key]
        
        # Create mini-batch from examples
        if len(examples) == 0:
            return
        
        model.train()
        adaptation_layer.train()
        
        # Prepare batch
        images = []
        labels = []
        
        transform = self._get_transform()
        
        for example in examples:
            try:
                image = transform(example.image_data)
                images.append(image)
                # Simple label encoding (would need proper mapping)
                label = hash(example.true_label) % 50  # Temp solution
                labels.append(label)
            except Exception as e:
                logger.error(f"Error processing example: {e}")
                continue
        
        if not images:
            return
        
        batch_images = torch.stack(images).to(self.device)
        batch_labels = torch.tensor(labels, dtype=torch.long).to(self.device)
        
        # Forward pass
        optimizer.zero_grad()
        
        # Extract features
        with torch.no_grad():
            features = model.backbone(batch_images)
        
        # Adaptation layer
        adapted_logits = adaptation_layer(features)
        
        # Loss calculation
        loss = F.cross_entropy(adapted_logits, batch_labels)
        
        # Backward pass
        loss.backward()
        optimizer.step()
        
        logger.info(f"Updated model for {model_key} with {len(examples)} examples, loss: {loss.item:.4f}")
    
    def _get_transform(self):
        """Get image preprocessing transform"""
        from torchvision import transforms
        return transforms.Compose([
            transforms.ToPILImage(),
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], 
                               std=[0.229, 0.224, 0.225])
        ])

class PerformanceTracker:
    """Tracks model performance and improvement over time"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.performance_history = defaultdict(list)
        self.init_database()
        
    def init_database(self):
        """Initialize performance tracking database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS performance_metrics (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                boat_id TEXT,
                species TEXT,
                accuracy REAL,
                precision_score REAL,
                recall_score REAL,
                f1_score REAL,
                sample_count INTEGER,
                timestamp DATETIME,
                improvement_rate REAL
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS learning_events (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                boat_id TEXT,
                event_type TEXT,
                species TEXT,
                confidence_before REAL,
                confidence_after REAL,
                correction_type TEXT,
                timestamp DATETIME,
                context TEXT
            )
        """)
        
        conn.commit()
        conn.close()
    
    def record_learning_event(self, user_id: str, event_type: str, 
                            species: str, confidence_before: float,
                            confidence_after: float, correction_type: str,
                            boat_id: Optional[str] = None, 
                            context: Dict[str, Any] = None):
        """Record a learning event"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO learning_events (
                id, user_id, boat_id, event_type, species, 
                confidence_before, confidence_after, correction_type,
                timestamp, context
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            f"{user_id}_{int(time.time())}",
            user_id,
            boat_id,
            event_type,
            species,
            confidence_before,
            confidence_after,
            correction_type,
            datetime.now(),
            json.dumps(context or {})
        ))
        
        conn.commit()
        conn.close()
    
    def update_performance_metrics(self, metric: ModelPerformanceMetric):
        """Update performance metrics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO performance_metrics (
                id, user_id, boat_id, species, accuracy, precision_score,
                recall_score, f1_score, sample_count, timestamp, improvement_rate
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            f"{metric.user_id}_{metric.boat_id}_{metric.species}",
            metric.user_id,
            metric.boat_id,
            metric.species,
            metric.accuracy,
            metric.precision,
            metric.recall,
            metric.f1_score,
            metric.sample_count,
            metric.last_updated,
            metric.improvement_rate
        ))
        
        conn.commit()
        conn.close()
        
        # Update history
        key = f"{metric.user_id}_{metric.boat_id}_{metric.species}"
        self.performance_history[key].append({
            'timestamp': metric.last_updated,
            'accuracy': metric.accuracy,
            'precision': metric.precision,
            'recall': metric.recall,
            'f1_score': metric.f1_score
        })
    
    def get_improvement_trend(self, user_id: str, species: str, 
                           boat_id: Optional[str] = None) -> Dict[str, Any]:
        """Get improvement trend for user/species"""
        key = f"{user_id}_{boat_id}_{species}"
        history = self.performance_history.get(key, [])
        
        if len(history) < 2:
            return {"trend": "insufficient_data", "improvement_rate": 0.0}
        
        # Calculate trend
        recent_accuracy = np.mean([h['accuracy'] for h in history[-5:]])  # Last 5 measurements
        old_accuracy = np.mean([h['accuracy'] for h in history[:5]])     # First 5 measurements
        
        improvement_rate = (recent_accuracy - old_accuracy) / max(old_accuracy, 0.1)
        
        if improvement_rate > 0.1:
            trend = "improving"
        elif improvement_rate < -0.1:
            trend = "declining"
        else:
            trend = "stable"
        
        return {
            "trend": trend,
            "improvement_rate": improvement_rate,
            "recent_accuracy": recent_accuracy,
            "initial_accuracy": old_accuracy,
            "data_points": len(history)
        }

class ContinuousLearningEngine:
    """Main engine for continuous learning and adaptation"""
    
    def __init__(self, adaptive_system, db_path: str = "continuous_learning.db"):
        self.adaptive_system = adaptive_system
        self.dataset = AdaptiveDataset()
        self.model_manager = PersonalizedModelManager(
            adaptive_system.model,
            torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        )
        self.performance_tracker = PerformanceTracker(db_path)
        
        # Learning parameters
        self.batch_size = 32
        self.learning_rate = 0.001
        self.update_frequency = 10  # Update after N new examples
        self.evaluation_frequency = 50  # Evaluate after N examples
        
        # Learning queues
        self.learning_queue = asyncio.Queue(maxsize=1000)
        self.correction_queue = asyncio.Queue(maxsize=1000)
        
        # Active learning
        self.uncertainty_threshold = 0.7
        self.diversity_sampling = True
        
        # Learning task
        self.learning_task = None
        self.is_learning = False
        
        # Performance cache
        self.performance_cache = {}
        self.cache_ttl = timedelta(minutes=5)
        
    async def start_continuous_learning(self):
        """Start the continuous learning process"""
        self.is_learning = True
        self.learning_task = asyncio.create_task(self._learning_loop())
        logger.info("Continuous learning engine started")
    
    def stop_continuous_learning(self):
        """Stop continuous learning"""
        self.is_learning = False
        if self.learning_task:
            self.learning_task.cancel()
        logger.info("Continuous learning engine stopped")
    
    async def add_correction(self, user_id: str, boat_id: Optional[str],
                           predicted_species: str, correct_species: str,
                           confidence: float, image_data: np.ndarray,
                           correction_type: str, context: Dict[str, Any] = None):
        """Add a correction example for learning"""
        
        example = LearningExample(
            image_data=image_data,
            true_label=correct_species,
            predicted_label=predicted_species,
            confidence=confidence,
            user_id=user_id,
            boat_id=boat_id,
            timestamp=datetime.now(),
            correction_type=correction_type,
            context=context or {}
        )
        
        try:
            await self.correction_queue.put(example)
            
            # Record learning event
            self.performance_tracker.record_learning_event(
                user_id=user_id,
                event_type="correction",
                species=correct_species,
                confidence_before=confidence,
                confidence_after=1.0,  # Corrected examples have perfect confidence
                correction_type=correction_type,
                boat_id=boat_id,
                context=context
            )
            
            logger.info(f"Added correction: {predicted_species} -> {correct_species} (user: {user_id})")
            
        except asyncio.QueueFull:
            logger.warning("Correction queue full, dropping example")
    
    async def add_positive_example(self, user_id: str, boat_id: Optional[str],
                                 species: str, confidence: float, 
                                 image_data: np.ndarray, context: Dict[str, Any] = None):
        """Add a positive training example (correct prediction)"""
        
        example = LearningExample(
            image_data=image_data,
            true_label=species,
            predicted_label=species,
            confidence=confidence,
            user_id=user_id,
            boat_id=boat_id,
            timestamp=datetime.now(),
            correction_type="positive_feedback",
            context=context or {}
        )
        
        try:
            await self.learning_queue.put(example)
            
            # Record positive learning event
            self.performance_tracker.record_learning_event(
                user_id=user_id,
                event_type="positive_example",
                species=species,
                confidence_before=confidence,
                confidence_after=confidence,
                correction_type="positive_feedback",
                boat_id=boat_id,
                context=context
            )
            
        except asyncio.QueueFull:
            logger.warning("Learning queue full, dropping example")
    
    async def _learning_loop(self):
        """Main continuous learning loop"""
        logger.info("Starting continuous learning loop")
        
        correction_batch = []
        learning_batch = []
        
        while self.is_learning:
            try:
                # Process corrections (higher priority)
                try:
                    correction = await asyncio.wait_for(
                        self.correction_queue.get(), timeout=1.0
                    )
                    correction_batch.append(correction)
                    self.dataset.add_example(correction)
                    
                except asyncio.TimeoutError:
                    pass
                
                # Process positive examples
                try:
                    example = await asyncio.wait_for(
                        self.learning_queue.get(), timeout=0.1
                    )
                    learning_batch.append(example)
                    self.dataset.add_example(example)
                    
                except asyncio.TimeoutError:
                    pass
                
                # Update models if we have enough examples
                total_examples = len(correction_batch) + len(learning_batch)
                
                if total_examples >= self.update_frequency:
                    await self._update_personalized_models(
                        correction_batch + learning_batch
                    )
                    
                    correction_batch.clear()
                    learning_batch.clear()
                
                # Evaluate performance periodically
                if len(self.dataset) % self.evaluation_frequency == 0:
                    await self._evaluate_all_models()
                
            except Exception as e:
                logger.error(f"Error in learning loop: {e}")
                await asyncio.sleep(1)
    
    async def _update_personalized_models(self, examples: List[LearningExample]):
        """Update personalized models with new examples"""
        # Group examples by user/boat
        user_examples = defaultdict(list)
        
        for example in examples:
            key = f"{example.user_id}_{example.boat_id}"
            user_examples[key].append(example)
        
        # Update each user's model
        for key, user_batch in user_examples.items():
            user_id, boat_id = key.split('_', 1)
            if boat_id == 'None':
                boat_id = None
            
            try:
                self.model_manager.update_user_model(
                    user_id=user_id,
                    examples=user_batch,
                    boat_id=boat_id
                )
                
                logger.info(f"Updated model for {key} with {len(user_batch)} examples")
                
            except Exception as e:
                logger.error(f"Error updating model for {key}: {e}")
    
    async def _evaluate_all_models(self):
        """Evaluate all personalized models"""
        logger.info("Evaluating all personalized models")
        
        for model_key, model in self.model_manager.user_models.items():
            try:
                user_id, boat_id = model_key.split('_', 1)
                if boat_id == 'None':
                    boat_id = None
                
                # Get user examples for evaluation
                user_indices = self.dataset.get_user_examples(user_id, boat_id)
                
                if len(user_indices) < 10:  # Need minimum examples
                    continue
                
                # Evaluate model performance
                metrics = await self._evaluate_user_model(
                    user_id, boat_id, user_indices
                )
                
                # Update performance tracking
                for species, metric in metrics.items():
                    self.performance_tracker.update_performance_metrics(metric)
                
            except Exception as e:
                logger.error(f"Error evaluating model {model_key}: {e}")
    
    async def _evaluate_user_model(self, user_id: str, boat_id: Optional[str], 
                                 example_indices: List[int]) -> Dict[str, ModelPerformanceMetric]:
        """Evaluate a user's model performance"""
        
        model, adaptation_layer = self.model_manager.get_user_model(user_id, boat_id)
        model.eval()
        adaptation_layer.eval()
        
        # Prepare evaluation data
        all_predictions = []
        all_true_labels = []
        species_predictions = defaultdict(list)
        species_true_labels = defaultdict(list)
        
        transform = self.model_manager._get_transform()
        
        with torch.no_grad():
            for idx in example_indices:
                example = self.dataset.examples[idx]
                
                try:
                    # Process image
                    image = transform(example.image_data).unsqueeze(0)
                    
                    # Get prediction
                    features = model.backbone(image)
                    logits = adaptation_layer(features)
                    predicted_class = torch.argmax(logits, dim=1).item()
                    
                    # Convert back to species name (simplified)
                    predicted_species = example.predicted_label  # Temp solution
                    true_species = example.true_label
                    
                    all_predictions.append(predicted_species)
                    all_true_labels.append(true_species)
                    
                    # Group by species
                    species_predictions[true_species].append(predicted_species)
                    species_true_labels[true_species].append(true_species)
                    
                except Exception as e:
                    logger.error(f"Error processing example {idx}: {e}")
        
        # Calculate metrics per species
        metrics = {}
        
        for species in species_true_labels.keys():
            if len(species_true_labels[species]) < 5:  # Need minimum samples
                continue
            
            y_true = [1 if label == species else 0 for label in species_true_labels[species]]
            y_pred = [1 if pred == species else 0 for pred in species_predictions[species]]
            
            if len(set(y_true)) > 1:  # Need both positive and negative examples
                precision, recall, f1, _ = precision_recall_fscore_support(
                    y_true, y_pred, average='binary', zero_division=0
                )
                accuracy = accuracy_score(y_true, y_pred)
                
                # Calculate improvement rate
                trend_info = self.performance_tracker.get_improvement_trend(
                    user_id, species, boat_id
                )
                
                metric = ModelPerformanceMetric(
                    user_id=user_id,
                    boat_id=boat_id,
                    species=species,
                    accuracy=accuracy,
                    precision=precision[0] if isinstance(precision, np.ndarray) else precision,
                    recall=recall[0] if isinstance(recall, np.ndarray) else recall,
                    f1_score=f1[0] if isinstance(f1, np.ndarray) else f1,
                    sample_count=len(species_true_labels[species]),
                    last_updated=datetime.now(),
                    improvement_rate=trend_info.get("improvement_rate", 0.0)
                )
                
                metrics[species] = metric
        
        logger.info(f"Evaluated {len(metrics)} species for user {user_id}")
        return metrics
    
    async def get_user_performance(self, user_id: str, boat_id: Optional[str] = None) -> Dict[str, Any]:
        """Get performance summary for user"""
        cache_key = f"{user_id}_{boat_id}"
        
        # Check cache
        if cache_key in self.performance_cache:
            cache_entry = self.performance_cache[cache_key]
            if datetime.now() - cache_entry['timestamp'] < self.cache_ttl:
                return cache_entry['data']
        
        # Get user examples
        user_indices = self.dataset.get_user_examples(user_id, boat_id)
        
        if not user_indices:
            return {"error": "No training data found for user"}
        
        # Get species distribution
        species_dist = {}
        correction_count = 0
        positive_count = 0
        
        for idx in user_indices:
            example = self.dataset.examples[idx]
            species = example.true_label
            
            if species not in species_dist:
                species_dist[species] = {"total": 0, "corrections": 0, "positive": 0}
            
            species_dist[species]["total"] += 1
            
            if example.correction_type in ["voice", "tote_placement", "user_feedback"]:
                species_dist[species]["corrections"] += 1
                correction_count += 1
            else:
                species_dist[species]["positive"] += 1
                positive_count += 1
        
        # Get improvement trends
        trends = {}
        for species in species_dist.keys():
            trend_info = self.performance_tracker.get_improvement_trend(
                user_id, species, boat_id
            )
            trends[species] = trend_info
        
        performance_data = {
            "user_id": user_id,
            "boat_id": boat_id,
            "total_examples": len(user_indices),
            "corrections": correction_count,
            "positive_examples": positive_count,
            "species_distribution": species_dist,
            "improvement_trends": trends,
            "last_updated": datetime.now()
        }
        
        # Cache result
        self.performance_cache[cache_key] = {
            'data': performance_data,
            'timestamp': datetime.now()
        }
        
        return performance_data
    
    async def suggest_training_focus(self, user_id: str, boat_id: Optional[str] = None) -> List[str]:
        """Suggest species that need more training focus"""
        performance_data = await self.get_user_performance(user_id, boat_id)
        
        if "error" in performance_data:
            return []
        
        suggestions = []
        species_dist = performance_data["species_distribution"]
        trends = performance_data["improvement_trends"]
        
        for species, dist in species_dist.items():
            # Suggest if:
            # 1. High correction rate
            # 2. Declining trend
            # 3. Low sample count
            
            correction_rate = dist["corrections"] / max(dist["total"], 1)
            trend_info = trends.get(species, {})
            
            if (correction_rate > 0.5 or 
                trend_info.get("trend") == "declining" or
                dist["total"] < 20):
                
                suggestions.append(species)
        
        return suggestions[:5]  # Top 5 suggestions

if __name__ == "__main__":
    # Test continuous learning engine
    import asyncio
    from main import AdaptiveCVTrainingSystem
    
    async def test_continuous_learning():
        # Create adaptive system
        cv_system = AdaptiveCVTrainingSystem()
        
        # Create continuous learning engine
        learning_engine = ContinuousLearningEngine(cv_system)
        
        # Start learning
        await learning_engine.start_continuous_learning()
        
        # Simulate some corrections
        dummy_image = np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8)
        
        await learning_engine.add_correction(
            user_id="test_user",
            boat_id="test_boat",
            predicted_species="coho_salmon",
            correct_species="king_salmon",
            confidence=0.7,
            image_data=dummy_image,
            correction_type="voice"
        )
        
        # Let it learn for a bit
        await asyncio.sleep(5)
        
        # Get performance
        performance = await learning_engine.get_user_performance("test_user", "test_boat")
        print("Performance:", json.dumps(performance, indent=2, default=str))
        
        # Get suggestions
        suggestions = await learning_engine.suggest_training_focus("test_user", "test_boat")
        print("Training suggestions:", suggestions)
        
        # Stop learning
        learning_engine.stop_continuous_learning()
    
    # Run test
    asyncio.run(test_continuous_learning())