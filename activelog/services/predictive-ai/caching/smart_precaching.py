#!/usr/bin/env python3
"""
Smart Pre-caching Engine - Intelligently pre-loads likely-needed files based on behavior prediction.
Uses predictive models to cache files before users need them, improving response times.
"""

import asyncio
import json
import hashlib
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict, deque
import math

class CacheStrategy(Enum):
    TEMPORAL_PATTERN = "temporal_pattern"
    BEHAVIORAL_SEQUENCE = "behavioral_sequence"
    CONTENT_SIMILARITY = "content_similarity"
    FREQUENCY_BASED = "frequency_based"
    COLLABORATIVE_FILTERING = "collaborative_filtering"
    CONTEXTUAL_TRIGGERS = "contextual_triggers"

class CacheConfidence(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class FileAccessPattern(Enum):
    SEQUENTIAL = "sequential"  # Files accessed in sequence
    GROUPED = "grouped"        # Files accessed together
    PERIODIC = "periodic"      # Files accessed regularly
    EVENT_DRIVEN = "event_driven"  # Files accessed based on events

@dataclass
class CacheEntry:
    """Cached file entry with metadata."""
    file_id: str
    user_id: str
    file_path: str
    file_size: int
    cache_strategy: CacheStrategy
    confidence: CacheConfidence
    predicted_access_time: datetime
    cached_at: datetime
    last_accessed: Optional[datetime]
    access_count: int
    expires_at: datetime
    metadata: Dict[str, Any]

@dataclass
class PreCachePrediction:
    """Prediction for pre-caching a file."""
    file_id: str
    user_id: str
    file_path: str
    prediction_confidence: float
    predicted_access_window: Tuple[datetime, datetime]
    cache_priority: int  # 1-10, 10 being highest
    reasoning: str
    triggers: List[str]
    related_files: List[str]
    estimated_benefit: float  # Expected time savings

class AccessPatternAnalyzer:
    """Analyzes file access patterns for caching predictions."""
    
    def __init__(self):
        self.access_history = defaultdict(list)
        self.sequence_patterns = defaultdict(list)
        self.temporal_patterns = defaultdict(list)
        self.co_access_patterns = defaultdict(set)
    
    def record_file_access(self, user_id: str, file_path: str, 
                          access_time: datetime, session_id: str,
                          context: Dict[str, Any] = None):
        """Record file access for pattern analysis."""
        access_record = {
            "file_path": file_path,
            "access_time": access_time,
            "session_id": session_id,
            "context": context or {},
            "hour": access_time.hour,
            "day_of_week": access_time.weekday(),
            "day_of_month": access_time.day,
            "month": access_time.month
        }
        
        self.access_history[user_id].append(access_record)
        
        # Keep only recent history (last 1000 accesses)
        if len(self.access_history[user_id]) > 1000:
            self.access_history[user_id] = self.access_history[user_id][-1000:]
        
        # Update patterns
        self._update_patterns(user_id, access_record)
    
    def _update_patterns(self, user_id: str, access_record: Dict[str, Any]):
        """Update access patterns with new record."""
        user_history = self.access_history[user_id]
        
        # Update sequential patterns (files accessed in sequence)
        if len(user_history) >= 2:
            prev_access = user_history[-2]
            current_file = access_record["file_path"]
            prev_file = prev_access["file_path"]
            
            # Only consider sequence if within reasonable time window (1 hour)
            time_diff = (access_record["access_time"] - prev_access["access_time"]).total_seconds()
            if time_diff <= 3600 and current_file != prev_file:
                sequence_key = f"{user_id}_sequence"
                self.sequence_patterns[sequence_key].append((prev_file, current_file, time_diff))
                
                # Keep only recent sequences
                if len(self.sequence_patterns[sequence_key]) > 200:
                    self.sequence_patterns[sequence_key] = self.sequence_patterns[sequence_key][-200:]
        
        # Update co-access patterns (files accessed in same session)
        session_files = [
            record["file_path"] for record in user_history[-10:]  # Last 10 accesses
            if record["session_id"] == access_record["session_id"]
        ]
        
        current_file = access_record["file_path"]
        for other_file in session_files:
            if other_file != current_file:
                co_access_key = tuple(sorted([current_file, other_file]))
                self.co_access_patterns[f"{user_id}_coacccess"].add(co_access_key)
        
        # Update temporal patterns
        temporal_key = f"{user_id}_temporal"
        self.temporal_patterns[temporal_key].append({
            "file_path": access_record["file_path"],
            "hour": access_record["hour"],
            "day_of_week": access_record["day_of_week"],
            "month": access_record["month"],
            "context": access_record["context"]
        })
        
        # Keep only recent temporal patterns
        if len(self.temporal_patterns[temporal_key]) > 500:
            self.temporal_patterns[temporal_key] = self.temporal_patterns[temporal_key][-500:]
    
    def analyze_sequence_patterns(self, user_id: str) -> Dict[str, List[Tuple[str, float]]]:
        """Analyze sequential access patterns."""
        sequence_key = f"{user_id}_sequence"
        sequences = self.sequence_patterns.get(sequence_key, [])
        
        if not sequences:
            return {}
        
        # Build sequence probability map
        sequence_map = defaultdict(list)
        for prev_file, next_file, time_diff in sequences:
            sequence_map[prev_file].append((next_file, time_diff))
        
        # Calculate probabilities for each sequence
        sequence_probs = {}
        for prev_file, next_files in sequence_map.items():
            # Count occurrences of each next file
            next_counts = defaultdict(int)
            total_accesses = len(next_files)
            
            for next_file, _ in next_files:
                next_counts[next_file] += 1
            
            # Convert to probabilities
            probabilities = []
            for next_file, count in next_counts.items():
                probability = count / total_accesses
                if probability >= 0.2:  # At least 20% probability
                    probabilities.append((next_file, probability))
            
            if probabilities:
                sequence_probs[prev_file] = sorted(probabilities, key=lambda x: x[1], reverse=True)
        
        return sequence_probs
    
    def analyze_temporal_patterns(self, user_id: str) -> Dict[str, Dict[str, Any]]:
        """Analyze temporal access patterns."""
        temporal_key = f"{user_id}_temporal"
        temporal_data = self.temporal_patterns.get(temporal_key, [])
        
        if not temporal_data:
            return {}
        
        # Group by file
        file_patterns = defaultdict(lambda: {
            "hours": [], "days": [], "months": [], "contexts": []
        })
        
        for record in temporal_data:
            file_path = record["file_path"]
            file_patterns[file_path]["hours"].append(record["hour"])
            file_patterns[file_path]["days"].append(record["day_of_week"])
            file_patterns[file_path]["months"].append(record["month"])
            file_patterns[file_path]["contexts"].append(record["context"])
        
        # Analyze patterns for each file
        analyzed_patterns = {}
        for file_path, patterns in file_patterns.items():
            if len(patterns["hours"]) < 3:  # Need minimum accesses
                continue
            
            # Find peak hours
            hour_counts = defaultdict(int)
            for hour in patterns["hours"]:
                hour_counts[hour] += 1
            
            peak_hours = sorted(hour_counts.items(), key=lambda x: x[1], reverse=True)[:3]
            
            # Find peak days
            day_counts = defaultdict(int)
            for day in patterns["days"]:
                day_counts[day] += 1
            
            peak_days = sorted(day_counts.items(), key=lambda x: x[1], reverse=True)[:3]
            
            # Calculate regularity (coefficient of variation)
            total_accesses = len(patterns["hours"])
            hour_regularity = max(hour_counts.values()) / total_accesses
            
            analyzed_patterns[file_path] = {
                "peak_hours": [hour for hour, count in peak_hours],
                "peak_days": [day for day, count in peak_days],
                "regularity_score": hour_regularity,
                "total_accesses": total_accesses,
                "last_access_contexts": patterns["contexts"][-3:]  # Last 3 contexts
            }
        
        return analyzed_patterns
    
    def analyze_co_access_patterns(self, user_id: str) -> Dict[str, List[Tuple[str, float]]]:
        """Analyze files that are frequently accessed together."""
        co_access_key = f"{user_id}_coacccess"
        co_accesses = self.co_access_patterns.get(co_access_key, set())
        
        if not co_accesses:
            return {}
        
        # Count co-access frequencies
        co_access_counts = defaultdict(int)
        file_total_accesses = defaultdict(int)
        
        for file1, file2 in co_accesses:
            co_access_counts[(file1, file2)] += 1
            file_total_accesses[file1] += 1
            file_total_accesses[file2] += 1
        
        # Calculate association strength
        associations = defaultdict(list)
        for (file1, file2), co_count in co_access_counts.items():
            if co_count >= 2:  # At least 2 co-accesses
                # Calculate association strength using Jaccard similarity
                total1 = file_total_accesses[file1]
                total2 = file_total_accesses[file2]
                
                jaccard = co_count / (total1 + total2 - co_count)
                
                if jaccard >= 0.3:  # Minimum association threshold
                    associations[file1].append((file2, jaccard))
                    associations[file2].append((file1, jaccard))
        
        # Sort associations by strength
        for file_path in associations:
            associations[file_path] = sorted(
                associations[file_path], 
                key=lambda x: x[1], 
                reverse=True
            )[:5]  # Top 5 associations
        
        return dict(associations)

class PredictiveCacheEngine:
    """Core engine for predictive file caching."""
    
    def __init__(self, cache_size_mb: int = 1024):
        self.pattern_analyzer = AccessPatternAnalyzer()
        self.cache_entries: Dict[str, CacheEntry] = {}
        self.cache_size_mb = cache_size_mb
        self.current_cache_size = 0
        self.prediction_weights = {
            CacheStrategy.TEMPORAL_PATTERN: 0.25,
            CacheStrategy.BEHAVIORAL_SEQUENCE: 0.30,
            CacheStrategy.CONTENT_SIMILARITY: 0.15,
            CacheStrategy.FREQUENCY_BASED: 0.20,
            CacheStrategy.CONTEXTUAL_TRIGGERS: 0.10
        }
    
    async def record_file_access(self, user_id: str, file_path: str, 
                               session_id: str, file_size: int = 0,
                               context: Dict[str, Any] = None):
        """Record file access and update cache predictions."""
        access_time = datetime.now()
        
        # Record in pattern analyzer
        self.pattern_analyzer.record_file_access(
            user_id, file_path, access_time, session_id, context
        )
        
        # Update cache entry if file is cached
        cache_key = f"{user_id}_{hashlib.md5(file_path.encode()).hexdigest()}"
        if cache_key in self.cache_entries:
            entry = self.cache_entries[cache_key]
            entry.last_accessed = access_time
            entry.access_count += 1
        
        # Generate new cache predictions
        await self._update_cache_predictions(user_id, file_path, context or {})
    
    async def _update_cache_predictions(self, user_id: str, current_file: str, 
                                      context: Dict[str, Any]):
        """Update cache predictions based on current access."""
        
        # Get predictions for files to cache
        predictions = await self._generate_cache_predictions(user_id, current_file, context)
        
        # Process predictions
        for prediction in predictions[:10]:  # Top 10 predictions
            await self._process_cache_prediction(prediction)
    
    async def _generate_cache_predictions(self, user_id: str, current_file: str, 
                                        context: Dict[str, Any]) -> List[PreCachePrediction]:
        """Generate predictions for files to pre-cache."""
        predictions = []
        current_time = datetime.now()
        
        # 1. Sequence-based predictions
        sequence_patterns = self.pattern_analyzer.analyze_sequence_patterns(user_id)
        if current_file in sequence_patterns:
            for next_file, probability in sequence_patterns[current_file][:3]:
                prediction = PreCachePrediction(
                    file_id=hashlib.md5(f"{user_id}_{next_file}".encode()).hexdigest(),
                    user_id=user_id,
                    file_path=next_file,
                    prediction_confidence=probability * self.prediction_weights[CacheStrategy.BEHAVIORAL_SEQUENCE],
                    predicted_access_window=(current_time, current_time + timedelta(hours=2)),
                    cache_priority=min(10, int(probability * 10)),
                    reasoning=f"Sequential access pattern: {current_file} → {next_file} ({probability:.1%} probability)",
                    triggers=[CacheStrategy.BEHAVIORAL_SEQUENCE.value],
                    related_files=[current_file],
                    estimated_benefit=probability * 2.0  # Estimated seconds saved
                )
                predictions.append(prediction)
        
        # 2. Co-access predictions
        co_access_patterns = self.pattern_analyzer.analyze_co_access_patterns(user_id)
        if current_file in co_access_patterns:
            for related_file, association in co_access_patterns[current_file][:2]:
                prediction = PreCachePrediction(
                    file_id=hashlib.md5(f"{user_id}_{related_file}".encode()).hexdigest(),
                    user_id=user_id,
                    file_path=related_file,
                    prediction_confidence=association * self.prediction_weights[CacheStrategy.CONTENT_SIMILARITY],
                    predicted_access_window=(current_time, current_time + timedelta(hours=4)),
                    cache_priority=min(10, int(association * 8)),
                    reasoning=f"Frequently accessed together: {association:.1%} association strength",
                    triggers=[CacheStrategy.CONTENT_SIMILARITY.value],
                    related_files=[current_file],
                    estimated_benefit=association * 1.5
                )
                predictions.append(prediction)
        
        # 3. Temporal predictions
        temporal_patterns = self.pattern_analyzer.analyze_temporal_patterns(user_id)
        current_hour = current_time.hour
        current_day = current_time.weekday()
        
        for file_path, pattern_data in temporal_patterns.items():
            if file_path == current_file:
                continue
            
            # Check if we're in a peak access period
            hour_match = current_hour in pattern_data["peak_hours"]
            day_match = current_day in pattern_data["peak_days"]
            regularity = pattern_data["regularity_score"]
            
            if (hour_match or day_match) and regularity >= 0.3:
                confidence = regularity * self.prediction_weights[CacheStrategy.TEMPORAL_PATTERN]
                
                if hour_match and day_match:
                    confidence *= 1.5  # Boost for both hour and day match
                
                prediction = PreCachePrediction(
                    file_id=hashlib.md5(f"{user_id}_{file_path}".encode()).hexdigest(),
                    user_id=user_id,
                    file_path=file_path,
                    prediction_confidence=confidence,
                    predicted_access_window=(current_time, current_time + timedelta(hours=1)),
                    cache_priority=min(10, int(confidence * 12)),
                    reasoning=f"Temporal pattern: typically accessed at this time (regularity: {regularity:.1%})",
                    triggers=[CacheStrategy.TEMPORAL_PATTERN.value],
                    related_files=[],
                    estimated_benefit=confidence * 2.5
                )
                predictions.append(prediction)
        
        # 4. Context-based predictions
        if context:
            context_predictions = await self._generate_context_predictions(
                user_id, context, current_time
            )
            predictions.extend(context_predictions)
        
        # Sort by confidence and estimated benefit
        predictions.sort(key=lambda p: (p.prediction_confidence, p.estimated_benefit), reverse=True)
        
        return predictions
    
    async def _generate_context_predictions(self, user_id: str, context: Dict[str, Any], 
                                          current_time: datetime) -> List[PreCachePrediction]:
        """Generate predictions based on current context."""
        predictions = []
        
        # Context patterns (simplified for demonstration)
        context_file_patterns = {
            "module_fishing": ["fishing_log.json", "catch_photos.jpg", "weather_data.json"],
            "module_business": ["receipts.pdf", "invoices.xlsx", "tax_docs.pdf"],
            "module_study": ["notes.docx", "assignments.pdf", "schedule.json"],
            "time_morning": ["daily_plan.json", "calendar.ics"],
            "time_evening": ["daily_summary.json", "tomorrow_tasks.json"]
        }
        
        # Check context triggers
        for context_key, value in context.items():
            context_pattern = f"{context_key}_{value}"
            
            if context_pattern in context_file_patterns:
                for file_path in context_file_patterns[context_pattern]:
                    prediction = PreCachePrediction(
                        file_id=hashlib.md5(f"{user_id}_{file_path}".encode()).hexdigest(),
                        user_id=user_id,
                        file_path=file_path,
                        prediction_confidence=0.4 * self.prediction_weights[CacheStrategy.CONTEXTUAL_TRIGGERS],
                        predicted_access_window=(current_time, current_time + timedelta(hours=3)),
                        cache_priority=6,
                        reasoning=f"Context trigger: {context_key}={value} typically leads to {file_path} access",
                        triggers=[CacheStrategy.CONTEXTUAL_TRIGGERS.value],
                        related_files=[],
                        estimated_benefit=1.0
                    )
                    predictions.append(prediction)
        
        return predictions
    
    async def _process_cache_prediction(self, prediction: PreCachePrediction):
        """Process a cache prediction and decide whether to cache the file."""
        
        # Skip if confidence is too low
        if prediction.prediction_confidence < 0.1:
            return
        
        cache_key = f"{prediction.user_id}_{hashlib.md5(prediction.file_path.encode()).hexdigest()}"
        
        # Skip if already cached
        if cache_key in self.cache_entries:
            return
        
        # Check if we have space (simplified file size estimation)
        estimated_file_size = self._estimate_file_size(prediction.file_path)
        
        if self.current_cache_size + estimated_file_size > self.cache_size_mb * 1024 * 1024:
            # Try to evict some files to make space
            await self._evict_cache_entries(estimated_file_size)
        
        # Create cache entry
        if self.current_cache_size + estimated_file_size <= self.cache_size_mb * 1024 * 1024:
            confidence_enum = self._convert_confidence(prediction.prediction_confidence)
            strategy = CacheStrategy(prediction.triggers[0]) if prediction.triggers else CacheStrategy.FREQUENCY_BASED
            
            cache_entry = CacheEntry(
                file_id=prediction.file_id,
                user_id=prediction.user_id,
                file_path=prediction.file_path,
                file_size=estimated_file_size,
                cache_strategy=strategy,
                confidence=confidence_enum,
                predicted_access_time=prediction.predicted_access_window[0],
                cached_at=datetime.now(),
                last_accessed=None,
                access_count=0,
                expires_at=prediction.predicted_access_window[1] + timedelta(hours=2),
                metadata={
                    "prediction_confidence": prediction.prediction_confidence,
                    "reasoning": prediction.reasoning,
                    "estimated_benefit": prediction.estimated_benefit
                }
            )
            
            self.cache_entries[cache_key] = cache_entry
            self.current_cache_size += estimated_file_size
            
            # In a real implementation, this would actually cache the file
            print(f"🔄 Pre-cached {prediction.file_path} (confidence: {prediction.prediction_confidence:.2f})")
    
    def _estimate_file_size(self, file_path: str) -> int:
        """Estimate file size based on extension and name."""
        # Simplified size estimation
        extension = file_path.split('.')[-1].lower() if '.' in file_path else ''
        
        size_estimates = {
            'txt': 10 * 1024,        # 10 KB
            'json': 50 * 1024,       # 50 KB
            'pdf': 500 * 1024,       # 500 KB
            'docx': 200 * 1024,      # 200 KB
            'xlsx': 300 * 1024,      # 300 KB
            'jpg': 1 * 1024 * 1024,  # 1 MB
            'png': 2 * 1024 * 1024,  # 2 MB
            'mp4': 10 * 1024 * 1024, # 10 MB
        }
        
        return size_estimates.get(extension, 100 * 1024)  # Default 100 KB
    
    def _convert_confidence(self, confidence: float) -> CacheConfidence:
        """Convert numerical confidence to enum."""
        if confidence >= 0.8:
            return CacheConfidence.CRITICAL
        elif confidence >= 0.6:
            return CacheConfidence.HIGH
        elif confidence >= 0.3:
            return CacheConfidence.MEDIUM
        else:
            return CacheConfidence.LOW
    
    async def _evict_cache_entries(self, space_needed: int):
        """Evict cache entries to make space."""
        current_time = datetime.now()
        
        # Find candidates for eviction
        eviction_candidates = []
        
        for cache_key, entry in self.cache_entries.items():
            # Calculate eviction score (lower = more likely to evict)
            score = 0
            
            # Factor 1: Time since last access (higher = more likely to evict)
            if entry.last_accessed:
                hours_since_access = (current_time - entry.last_accessed).total_seconds() / 3600
                score += hours_since_access * 0.1
            else:
                score += 24  # Never accessed
            
            # Factor 2: Access count (lower = more likely to evict)
            score -= entry.access_count * 0.5
            
            # Factor 3: Confidence (lower = more likely to evict)
            confidence_scores = {
                CacheConfidence.CRITICAL: 4,
                CacheConfidence.HIGH: 3,
                CacheConfidence.MEDIUM: 2,
                CacheConfidence.LOW: 1
            }
            score -= confidence_scores[entry.confidence]
            
            # Factor 4: Expires soon (higher = more likely to evict)
            if entry.expires_at < current_time:
                score += 10  # Already expired
            else:
                hours_to_expiry = (entry.expires_at - current_time).total_seconds() / 3600
                if hours_to_expiry < 2:
                    score += 5
            
            eviction_candidates.append((cache_key, entry, score))
        
        # Sort by eviction score (highest score = first to evict)
        eviction_candidates.sort(key=lambda x: x[2], reverse=True)
        
        # Evict entries until we have enough space
        space_freed = 0
        for cache_key, entry, score in eviction_candidates:
            if space_freed >= space_needed:
                break
            
            del self.cache_entries[cache_key]
            space_freed += entry.file_size
            self.current_cache_size -= entry.file_size
            
            print(f"🗑️ Evicted {entry.file_path} (score: {score:.1f})")
    
    async def get_cache_statistics(self, user_id: str) -> Dict[str, Any]:
        """Get cache statistics for a user."""
        user_entries = [
            entry for entry in self.cache_entries.values()
            if entry.user_id == user_id
        ]
        
        if not user_entries:
            return {"message": "No cache entries for user"}
        
        # Calculate statistics
        total_cached_files = len(user_entries)
        total_cached_size = sum(entry.file_size for entry in user_entries)
        accessed_files = sum(1 for entry in user_entries if entry.access_count > 0)
        cache_hit_rate = accessed_files / total_cached_files if total_cached_files > 0 else 0
        
        # Strategy distribution
        strategy_counts = defaultdict(int)
        for entry in user_entries:
            strategy_counts[entry.cache_strategy.value] += 1
        
        # Confidence distribution
        confidence_counts = defaultdict(int)
        for entry in user_entries:
            confidence_counts[entry.confidence.value] += 1
        
        return {
            "total_cached_files": total_cached_files,
            "total_cached_size_mb": round(total_cached_size / (1024 * 1024), 2),
            "cache_hit_rate": round(cache_hit_rate, 3),
            "accessed_files": accessed_files,
            "strategy_distribution": dict(strategy_counts),
            "confidence_distribution": dict(confidence_counts),
            "cache_utilization": round(self.current_cache_size / (self.cache_size_mb * 1024 * 1024), 2)
        }

class SmartPreCachingEngine:
    """Main smart pre-caching engine orchestrator."""
    
    def __init__(self, cache_size_mb: int = 1024):
        self.predictive_cache = PredictiveCacheEngine(cache_size_mb)
        self.user_contexts = defaultdict(dict)
        self.enabled = True
        
        print(f"🚀 Smart Pre-caching Engine initialized (cache size: {cache_size_mb}MB)")
    
    async def record_file_access(self, user_id: str, file_path: str, 
                               session_id: str, file_size: int = 0,
                               context: Dict[str, Any] = None):
        """Record file access and update cache predictions."""
        if not self.enabled:
            return
        
        # Update user context
        if context:
            self.user_contexts[user_id].update(context)
        
        await self.predictive_cache.record_file_access(
            user_id, file_path, session_id, file_size, self.user_contexts[user_id]
        )
    
    async def get_cache_recommendations(self, user_id: str) -> List[Dict[str, Any]]:
        """Get current cache recommendations for a user."""
        # This would return files that should be pre-cached
        # For demonstration, we'll return some mock recommendations
        recommendations = []
        
        # Get user's cache entries
        user_entries = [
            entry for entry in self.predictive_cache.cache_entries.values()
            if entry.user_id == user_id
        ]
        
        for entry in user_entries[:5]:  # Top 5
            recommendations.append({
                "file_path": entry.file_path,
                "confidence": entry.confidence.value,
                "strategy": entry.cache_strategy.value,
                "predicted_access_time": entry.predicted_access_time.isoformat(),
                "reasoning": entry.metadata.get("reasoning", ""),
                "estimated_benefit": entry.metadata.get("estimated_benefit", 0)
            })
        
        return recommendations
    
    async def get_cache_statistics(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        stats = await self.predictive_cache.get_cache_statistics(user_id)
        
        # Add engine-level statistics
        stats.update({
            "engine_enabled": self.enabled,
            "total_users_tracked": len(self.user_contexts),
            "global_cache_entries": len(self.predictive_cache.cache_entries)
        })
        
        return stats
    
    async def enable_caching(self, user_id: str, enabled: bool = True):
        """Enable or disable caching for a user."""
        # In a real implementation, this would be per-user
        self.enabled = enabled
        status = "enabled" if enabled else "disabled"
        print(f"🔧 Pre-caching {status} for {user_id}")
    
    async def clear_cache(self, user_id: str):
        """Clear cache for a specific user."""
        keys_to_remove = [
            key for key, entry in self.predictive_cache.cache_entries.items()
            if entry.user_id == user_id
        ]
        
        for key in keys_to_remove:
            entry = self.predictive_cache.cache_entries[key]
            self.predictive_cache.current_cache_size -= entry.file_size
            del self.predictive_cache.cache_entries[key]
        
        print(f"🧹 Cleared cache for {user_id} ({len(keys_to_remove)} entries removed)")

# CLI interface for testing
async def main():
    """CLI interface for Smart Pre-caching Engine testing."""
    engine = SmartPreCachingEngine(cache_size_mb=512)  # 512MB cache
    
    print("🚀 Smart Pre-caching Engine Test Suite")
    print("=" * 50)
    
    user_id = "test_user"
    session_id = "session_123"
    
    # Test 1: Record file accesses to build patterns
    print("\n1. Recording file access patterns...")
    
    # Simulate a typical work session
    work_files = [
        ("project_report.docx", {"module": "work", "time": "morning"}),
        ("meeting_notes.txt", {"module": "work", "time": "morning"}),
        ("budget_spreadsheet.xlsx", {"module": "work", "time": "morning"}),
        ("client_presentation.pptx", {"module": "work", "time": "morning"}),
        ("project_timeline.pdf", {"module": "work", "time": "morning"}),
    ]
    
    for file_path, context in work_files:
        await engine.record_file_access(user_id, file_path, session_id, 1024*100, context)
        await asyncio.sleep(0.1)  # Small delay between accesses
    
    print(f"✅ Recorded {len(work_files)} file accesses")
    
    # Test 2: Simulate sequential access pattern
    print("\n2. Building sequential access patterns...")
    
    sequences = [
        ("financial_data.xlsx", "tax_calculations.pdf"),
        ("tax_calculations.pdf", "tax_forms.pdf"),
        ("project_plan.docx", "project_tasks.xlsx"),
        ("project_tasks.xlsx", "project_timeline.pdf"),
    ]
    
    for file1, file2 in sequences:
        # Access first file
        await engine.record_file_access(
            user_id, file1, f"seq_session_{file1}", 1024*50, 
            {"sequence": "first", "module": "finance"}
        )
        await asyncio.sleep(0.5)
        
        # Access second file (establishing sequence)
        await engine.record_file_access(
            user_id, file2, f"seq_session_{file1}", 1024*50, 
            {"sequence": "second", "module": "finance"}
        )
        await asyncio.sleep(0.1)
    
    print(f"✅ Created {len(sequences)} sequential access patterns")
    
    # Test 3: Trigger predictive caching
    print("\n3. Triggering predictive caching...")
    
    # Access a file that should trigger cache predictions
    await engine.record_file_access(
        user_id, "financial_data.xlsx", "trigger_session", 1024*100,
        {"module": "finance", "time": "morning", "activity": "analysis"}
    )
    
    print("✅ Triggered cache prediction analysis")
    
    # Test 4: Get cache recommendations
    print("\n4. Getting cache recommendations...")
    
    recommendations = await engine.get_cache_recommendations(user_id)
    print(f"✅ Generated {len(recommendations)} cache recommendations:")
    
    for i, rec in enumerate(recommendations[:3], 1):
        print(f"   {i}. {rec['file_path']}")
        print(f"      Strategy: {rec['strategy']}")
        print(f"      Confidence: {rec['confidence']}")
        print(f"      Reasoning: {rec['reasoning']}")
    
    # Test 5: Get cache statistics
    print("\n5. Getting cache statistics...")
    
    stats = await engine.get_cache_statistics(user_id)
    if "message" not in stats:
        print(f"✅ Cache statistics:")
        print(f"   Cached files: {stats['total_cached_files']}")
        print(f"   Cache size: {stats['total_cached_size_mb']}MB")
        print(f"   Cache hit rate: {stats['cache_hit_rate']}")
        print(f"   Cache utilization: {stats['cache_utilization']}")
        print(f"   Strategy distribution: {stats['strategy_distribution']}")
    else:
        print(f"ℹ️ {stats['message']}")
    
    # Test 6: Test cache eviction
    print("\n6. Testing cache eviction...")
    
    # Fill cache with large files to trigger eviction
    large_files = [f"large_file_{i}.mp4" for i in range(5)]
    
    for file_path in large_files:
        await engine.record_file_access(
            user_id, file_path, "large_session", 50*1024*1024,  # 50MB files
            {"type": "video", "size": "large"}
        )
    
    final_stats = await engine.get_cache_statistics(user_id)
    if "message" not in final_stats:
        print(f"✅ Cache after large files:")
        print(f"   Cache utilization: {final_stats['cache_utilization']}")
        print(f"   Total files: {final_stats['total_cached_files']}")
    
    print("\n🎉 Smart Pre-caching Engine tests completed!")

if __name__ == "__main__":
    asyncio.run(main())