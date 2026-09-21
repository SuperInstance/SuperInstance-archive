#!/usr/bin/env python3
"""
ActiveLog Unified Search Engine - Multi-modal Search
Advanced multi-modal search supporting text, image, audio, and video content
"""

import asyncio
import json
import logging
import time
import numpy as np
import base64
import hashlib
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass
from collections import defaultdict
import sqlite3
import threading
from io import BytesIO
import wave
import struct

logger = logging.getLogger(__name__)

class ModalityType:
    """Content modality types"""
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"

@dataclass
class MultimodalFeatures:
    """Multi-modal feature representation"""
    document_id: str
    modality: str
    features: Dict[str, np.ndarray]  # Different feature types
    metadata: Dict[str, Any] = None
    created_at: float = 0
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.created_at == 0:
            self.created_at = time.time()

class ImageFeatureExtractor:
    """Extract features from images"""
    
    def __init__(self):
        self.feature_dim = 512
        # In production, use CNN models like ResNet, VGG, or CLIP
    
    def extract_features(self, image_data: bytes) -> Dict[str, np.ndarray]:
        """Extract image features"""
        try:
            # Mock feature extraction - in production use actual CNN
            image_hash = hashlib.md5(image_data).hexdigest()
            np.random.seed(int(image_hash[:8], 16))
            
            features = {
                "visual": np.random.normal(0, 1, self.feature_dim),
                "color_histogram": np.random.random(64),
                "texture": np.random.random(128)
            }
            
            # Normalize features
            for key, feat in features.items():
                features[key] = feat / (np.linalg.norm(feat) + 1e-8)
            
            return features
            
        except Exception as e:
            logger.error(f"Image feature extraction error: {e}")
            return {}
    
    def extract_from_base64(self, base64_data: str) -> Dict[str, np.ndarray]:
        """Extract features from base64 encoded image"""
        try:
            image_data = base64.b64decode(base64_data)
            return self.extract_features(image_data)
        except Exception as e:
            logger.error(f"Base64 image processing error: {e}")
            return {}
    
    def extract_metadata(self, image_data: bytes) -> Dict[str, Any]:
        """Extract image metadata"""
        # Mock metadata extraction
        return {
            "size": len(image_data),
            "format": "unknown",
            "dimensions": {"width": 0, "height": 0},
            "color_space": "RGB"
        }

class AudioFeatureExtractor:
    """Extract features from audio content"""
    
    def __init__(self):
        self.feature_dim = 256
        # In production, use audio ML models like Wav2Vec, OpenAI Whisper
    
    def extract_features(self, audio_data: bytes) -> Dict[str, np.ndarray]:
        """Extract audio features"""
        try:
            # Mock feature extraction
            audio_hash = hashlib.md5(audio_data).hexdigest()
            np.random.seed(int(audio_hash[:8], 16))
            
            features = {
                "mfcc": np.random.normal(0, 1, (13, 100)),  # MFCC features
                "spectral": np.random.random(128),
                "temporal": np.random.random(64)
            }
            
            # Flatten MFCC for similarity computation
            features["mfcc_flat"] = features["mfcc"].flatten()[:self.feature_dim]
            
            # Normalize features
            for key, feat in features.items():
                if feat.ndim == 1:
                    features[key] = feat / (np.linalg.norm(feat) + 1e-8)
            
            return features
            
        except Exception as e:
            logger.error(f"Audio feature extraction error: {e}")
            return {}
    
    def extract_from_wave(self, wave_data: bytes) -> Dict[str, np.ndarray]:
        """Extract features from WAV audio data"""
        try:
            # Parse WAV header (simplified)
            if len(wave_data) < 44:
                raise ValueError("Invalid WAV data")
            
            return self.extract_features(wave_data)
            
        except Exception as e:
            logger.error(f"WAV audio processing error: {e}")
            return {}
    
    def transcribe_audio(self, audio_data: bytes) -> str:
        """Mock audio transcription"""
        # In production, use Whisper or similar ASR model
        audio_hash = hashlib.md5(audio_data).hexdigest()
        mock_transcriptions = [
            "This is a sample audio transcription.",
            "Audio content related to business meeting.",
            "Personal log entry recorded via voice.",
            "Discussion about project requirements.",
            "Meeting notes and action items."
        ]
        return mock_transcriptions[int(audio_hash[:2], 16) % len(mock_transcriptions)]
    
    def extract_metadata(self, audio_data: bytes) -> Dict[str, Any]:
        """Extract audio metadata"""
        return {
            "size": len(audio_data),
            "format": "wav",
            "duration_seconds": len(audio_data) / 44100,  # Mock duration
            "sample_rate": 44100,
            "channels": 2
        }

class VideoFeatureExtractor:
    """Extract features from video content"""
    
    def __init__(self):
        self.feature_dim = 1024
        # In production, use video ML models like Video-BERT, I3D
    
    def extract_features(self, video_data: bytes) -> Dict[str, np.ndarray]:
        """Extract video features"""
        try:
            video_hash = hashlib.md5(video_data).hexdigest()
            np.random.seed(int(video_hash[:8], 16))
            
            features = {
                "visual": np.random.normal(0, 1, self.feature_dim),
                "motion": np.random.random(256),
                "scene": np.random.random(128),
                "temporal": np.random.random(64)
            }
            
            # Normalize features
            for key, feat in features.items():
                features[key] = feat / (np.linalg.norm(feat) + 1e-8)
            
            return features
            
        except Exception as e:
            logger.error(f"Video feature extraction error: {e}")
            return {}
    
    def extract_keyframes(self, video_data: bytes, num_frames: int = 10) -> List[bytes]:
        """Extract keyframes from video"""
        # Mock keyframe extraction
        keyframes = []
        for i in range(num_frames):
            # Generate mock keyframe data
            frame_hash = hashlib.md5(video_data + str(i).encode()).hexdigest()
            frame_data = frame_hash.encode() * 100  # Mock image data
            keyframes.append(frame_data)
        
        return keyframes
    
    def extract_metadata(self, video_data: bytes) -> Dict[str, Any]:
        """Extract video metadata"""
        return {
            "size": len(video_data),
            "format": "mp4",
            "duration_seconds": len(video_data) / 1000000,  # Mock duration
            "resolution": {"width": 1920, "height": 1080},
            "fps": 30,
            "codec": "h264"
        }

class MultimodalIndex:
    """Index for multi-modal content"""
    
    def __init__(self, db_path: str = "multimodal_index.db"):
        self.features: Dict[str, MultimodalFeatures] = {}
        self.modality_features: Dict[str, Dict[str, Dict[str, np.ndarray]]] = defaultdict(lambda: defaultdict(dict))
        
        # Database persistence
        self.db_path = db_path
        self.db_lock = threading.Lock()
        self._init_database()
    
    def _init_database(self):
        """Initialize database for multi-modal features"""
        with self.db_lock:
            conn = sqlite3.connect(self.db_path)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS multimodal_features (
                    document_id TEXT,
                    modality TEXT,
                    feature_type TEXT,
                    features BLOB,
                    metadata TEXT,
                    created_at REAL,
                    PRIMARY KEY(document_id, modality, feature_type),
                    INDEX(modality),
                    INDEX(document_id)
                )
            """)
            conn.commit()
            conn.close()
    
    def add_features(self, features: MultimodalFeatures):
        """Add multi-modal features to index"""
        key = f"{features.document_id}_{features.modality}"
        self.features[key] = features
        
        # Store by modality for efficient search
        for feature_type, feature_vector in features.features.items():
            self.modality_features[features.modality][feature_type][features.document_id] = feature_vector
        
        # Persist to database
        self._persist_features(features)
    
    def _persist_features(self, features: MultimodalFeatures):
        """Persist features to database"""
        def _db_insert():
            with self.db_lock:
                conn = sqlite3.connect(self.db_path)
                
                for feature_type, feature_vector in features.features.items():
                    conn.execute("""
                        INSERT OR REPLACE INTO multimodal_features 
                        (document_id, modality, feature_type, features, metadata, created_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        features.document_id,
                        features.modality,
                        feature_type,
                        feature_vector.tobytes(),
                        json.dumps(features.metadata),
                        features.created_at
                    ))
                
                conn.commit()
                conn.close()
        
        # Run in background
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            executor.submit(_db_insert)
    
    def search_by_modality(self, query_features: Dict[str, np.ndarray], modality: str, 
                          limit: int = 50, threshold: float = 0.1) -> List[Tuple[str, float, str]]:
        """Search by specific modality"""
        results = []
        
        if modality not in self.modality_features:
            return results
        
        # Search each feature type
        for feature_type, feature_dict in self.modality_features[modality].items():
            if feature_type not in query_features:
                continue
            
            query_vector = query_features[feature_type]
            
            # Compute similarities
            for doc_id, doc_vector in feature_dict.items():
                try:
                    # Ensure vectors have same dimension
                    if query_vector.shape != doc_vector.shape:
                        continue
                    
                    # Cosine similarity
                    similarity = np.dot(query_vector, doc_vector) / (
                        np.linalg.norm(query_vector) * np.linalg.norm(doc_vector) + 1e-8
                    )
                    
                    if similarity >= threshold:
                        results.append((doc_id, float(similarity), feature_type))
                        
                except Exception as e:
                    logger.error(f"Similarity computation error: {e}")
                    continue
        
        # Sort by similarity and return top results
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:limit]
    
    def remove_features(self, document_id: str):
        """Remove all features for a document"""
        # Remove from memory
        keys_to_remove = [key for key in self.features.keys() if key.startswith(f"{document_id}_")]
        for key in keys_to_remove:
            del self.features[key]
        
        # Remove from modality indexes
        for modality_dict in self.modality_features.values():
            for feature_dict in modality_dict.values():
                if document_id in feature_dict:
                    del feature_dict[document_id]
        
        # Remove from database
        with self.db_lock:
            conn = sqlite3.connect(self.db_path)
            conn.execute("DELETE FROM multimodal_features WHERE document_id = ?", (document_id,))
            conn.commit()
            conn.close()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get index statistics"""
        modality_counts = defaultdict(int)
        for key in self.features.keys():
            modality = key.split('_', 1)[1]
            modality_counts[modality] += 1
        
        return {
            "total_documents": len(set(key.split('_', 1)[0] for key in self.features.keys())),
            "total_features": len(self.features),
            "modality_distribution": dict(modality_counts)
        }

class MultimodalSearch:
    """Multi-modal search system"""
    
    def __init__(self):
        # Feature extractors
        self.image_extractor = ImageFeatureExtractor()
        self.audio_extractor = AudioFeatureExtractor()
        self.video_extractor = VideoFeatureExtractor()
        
        # Multi-modal index
        self.index = MultimodalIndex()
        
        # Statistics
        self.stats = {
            "documents_indexed": 0,
            "searches_performed": 0,
            "modality_usage": defaultdict(int),
            "avg_search_time_ms": 0
        }
    
    async def index_content(self, document_id: str, content_data: Union[bytes, str], 
                           modality: str, metadata: Dict[str, Any] = None):
        """Index multi-modal content"""
        try:
            if modality == ModalityType.IMAGE:
                features = await self._index_image(document_id, content_data, metadata)
            elif modality == ModalityType.AUDIO:
                features = await self._index_audio(document_id, content_data, metadata)
            elif modality == ModalityType.VIDEO:
                features = await self._index_video(document_id, content_data, metadata)
            elif modality == ModalityType.TEXT:
                features = await self._index_text(document_id, content_data, metadata)
            else:
                raise ValueError(f"Unsupported modality: {modality}")
            
            if features and features.features:
                self.index.add_features(features)
                self.stats["documents_indexed"] += 1
                logger.info(f"Indexed {modality} content for document {document_id}")
            
        except Exception as e:
            logger.error(f"Multi-modal indexing error: {e}")
    
    async def _index_image(self, document_id: str, image_data: Union[bytes, str], 
                          metadata: Dict[str, Any] = None) -> MultimodalFeatures:
        """Index image content"""
        if isinstance(image_data, str):
            # Assume base64 encoded
            features_dict = self.image_extractor.extract_from_base64(image_data)
            actual_metadata = self.image_extractor.extract_metadata(base64.b64decode(image_data))
        else:
            features_dict = self.image_extractor.extract_features(image_data)
            actual_metadata = self.image_extractor.extract_metadata(image_data)
        
        if metadata:
            actual_metadata.update(metadata)
        
        return MultimodalFeatures(
            document_id=document_id,
            modality=ModalityType.IMAGE,
            features=features_dict,
            metadata=actual_metadata
        )
    
    async def _index_audio(self, document_id: str, audio_data: bytes, 
                          metadata: Dict[str, Any] = None) -> MultimodalFeatures:
        """Index audio content"""
        features_dict = self.audio_extractor.extract_features(audio_data)
        actual_metadata = self.audio_extractor.extract_metadata(audio_data)
        
        # Add transcription
        transcription = self.audio_extractor.transcribe_audio(audio_data)
        actual_metadata["transcription"] = transcription
        
        if metadata:
            actual_metadata.update(metadata)
        
        return MultimodalFeatures(
            document_id=document_id,
            modality=ModalityType.AUDIO,
            features=features_dict,
            metadata=actual_metadata
        )
    
    async def _index_video(self, document_id: str, video_data: bytes, 
                          metadata: Dict[str, Any] = None) -> MultimodalFeatures:
        """Index video content"""
        features_dict = self.video_extractor.extract_features(video_data)
        actual_metadata = self.video_extractor.extract_metadata(video_data)
        
        # Extract keyframes and index them as images
        keyframes = self.video_extractor.extract_keyframes(video_data)
        keyframe_features = []
        
        for i, keyframe in enumerate(keyframes[:5]):  # Limit to 5 keyframes
            img_features = self.image_extractor.extract_features(keyframe)
            keyframe_features.append(img_features.get("visual", np.array([])))
        
        if keyframe_features:
            # Average keyframe features
            avg_keyframe_features = np.mean([f for f in keyframe_features if len(f) > 0], axis=0)
            if len(avg_keyframe_features) > 0:
                features_dict["keyframes"] = avg_keyframe_features
        
        if metadata:
            actual_metadata.update(metadata)
        
        return MultimodalFeatures(
            document_id=document_id,
            modality=ModalityType.VIDEO,
            features=features_dict,
            metadata=actual_metadata
        )
    
    async def _index_text(self, document_id: str, text_data: str, 
                         metadata: Dict[str, Any] = None) -> MultimodalFeatures:
        """Index text content for multi-modal search"""
        # Simple text feature extraction (in production, use proper NLP models)
        text_hash = hashlib.md5(text_data.encode()).hexdigest()
        np.random.seed(int(text_hash[:8], 16))
        
        features_dict = {
            "semantic": np.random.normal(0, 1, 512),
            "syntactic": np.random.random(128)
        }
        
        # Normalize features
        for key, feat in features_dict.items():
            features_dict[key] = feat / (np.linalg.norm(feat) + 1e-8)
        
        actual_metadata = {
            "length": len(text_data),
            "word_count": len(text_data.split()),
            "language": "en"  # Mock language detection
        }
        
        if metadata:
            actual_metadata.update(metadata)
        
        return MultimodalFeatures(
            document_id=document_id,
            modality=ModalityType.TEXT,
            features=features_dict,
            metadata=actual_metadata
        )
    
    async def search(self, query, modality: str = None, limit: int = 50) -> List[Tuple[str, float]]:
        """Perform multi-modal search"""
        start_time = time.time()
        
        try:
            # Handle different query types
            if hasattr(query, 'query'):
                query_data = query.query
            else:
                query_data = query
            
            results = []
            
            if modality:
                # Search specific modality
                results = await self._search_modality(query_data, modality, limit)
            else:
                # Search all modalities and combine
                results = await self._search_all_modalities(query_data, limit)
            
            # Update statistics
            search_time = (time.time() - start_time) * 1000
            self.stats["searches_performed"] += 1
            
            # Update average search time
            current_avg = self.stats["avg_search_time_ms"]
            total_searches = self.stats["searches_performed"]
            self.stats["avg_search_time_ms"] = ((current_avg * (total_searches - 1)) + search_time) / total_searches
            
            return results
            
        except Exception as e:
            logger.error(f"Multi-modal search error: {e}")
            return []
    
    async def _search_modality(self, query_data: Union[str, bytes], modality: str, limit: int) -> List[Tuple[str, float]]:
        """Search specific modality"""
        query_features = {}
        
        if modality == ModalityType.IMAGE:
            if isinstance(query_data, str):
                query_features = self.image_extractor.extract_from_base64(query_data)
            else:
                query_features = self.image_extractor.extract_features(query_data)
        elif modality == ModalityType.AUDIO:
            query_features = self.audio_extractor.extract_features(query_data)
        elif modality == ModalityType.VIDEO:
            query_features = self.video_extractor.extract_features(query_data)
        elif modality == ModalityType.TEXT:
            # Generate text features for query
            text_hash = hashlib.md5(str(query_data).encode()).hexdigest()
            np.random.seed(int(text_hash[:8], 16))
            query_features = {
                "semantic": np.random.normal(0, 1, 512) / np.sqrt(512),
                "syntactic": np.random.random(128) / np.sqrt(128)
            }
        
        if not query_features:
            return []
        
        # Search index
        raw_results = self.index.search_by_modality(query_features, modality, limit)
        
        # Convert to expected format (document_id, score)
        results = []
        doc_scores = defaultdict(float)
        
        for doc_id, score, feature_type in raw_results:
            doc_scores[doc_id] = max(doc_scores[doc_id], score)  # Take best score across features
        
        results = [(doc_id, score) for doc_id, score in doc_scores.items()]
        results.sort(key=lambda x: x[1], reverse=True)
        
        self.stats["modality_usage"][modality] += 1
        return results
    
    async def _search_all_modalities(self, query_data: Union[str, bytes], limit: int) -> List[Tuple[str, float]]:
        """Search all modalities and combine results"""
        all_results = defaultdict(float)
        
        # Try each modality (in production, determine modality from query)
        modalities = [ModalityType.TEXT]  # Start with text
        
        if isinstance(query_data, bytes):
            modalities.extend([ModalityType.IMAGE, ModalityType.AUDIO, ModalityType.VIDEO])
        
        for modality in modalities:
            try:
                modality_results = await self._search_modality(query_data, modality, limit)
                
                # Combine results with weighting
                weight = self._get_modality_weight(modality)
                for doc_id, score in modality_results:
                    all_results[doc_id] += score * weight
                    
            except Exception as e:
                logger.warning(f"Search failed for modality {modality}: {e}")
                continue
        
        # Sort combined results
        combined_results = sorted(all_results.items(), key=lambda x: x[1], reverse=True)
        return combined_results[:limit]
    
    def _get_modality_weight(self, modality: str) -> float:
        """Get weighting for modality in combined search"""
        weights = {
            ModalityType.TEXT: 0.4,
            ModalityType.IMAGE: 0.3,
            ModalityType.AUDIO: 0.2,
            ModalityType.VIDEO: 0.1
        }
        return weights.get(modality, 0.1)
    
    async def find_similar_content(self, document_id: str, modality: str, limit: int = 10) -> List[Tuple[str, float]]:
        """Find content similar to a given document"""
        # Get document features
        feature_key = f"{document_id}_{modality}"
        if feature_key not in self.index.features:
            return []
        
        document_features = self.index.features[feature_key]
        
        # Search using document features
        raw_results = self.index.search_by_modality(document_features.features, modality, limit + 1)
        
        # Remove self from results and convert format
        results = []
        for doc_id, score, feature_type in raw_results:
            if doc_id != document_id:
                results.append((doc_id, score))
        
        # Deduplicate and sort
        doc_scores = defaultdict(float)
        for doc_id, score in results:
            doc_scores[doc_id] = max(doc_scores[doc_id], score)
        
        final_results = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)
        return final_results[:limit]
    
    def remove_document(self, document_id: str):
        """Remove document from multi-modal index"""
        self.index.remove_features(document_id)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get multi-modal search statistics"""
        return {
            **self.stats,
            "modality_usage": dict(self.stats["modality_usage"]),
            "index_stats": self.index.get_stats()
        }