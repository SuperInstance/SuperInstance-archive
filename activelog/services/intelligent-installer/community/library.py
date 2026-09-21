"""
Community Configuration Library
Enables sharing, discovering, and collaborating on hardware-optimized configurations
"""

import asyncio
import json
import hashlib
import time
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from collections import defaultdict
import sqlite3
from pathlib import Path

from api.models import (
    HardwareProfile, AdaptiveConfiguration, ConfigurationShare,
    CommunityConfiguration, SystemTier, InterfaceType, ComputeDistribution
)

@dataclass
class ConfigurationRating:
    """User rating for a configuration"""
    configuration_id: str
    user_id: str
    rating: float  # 1-5 scale
    review: Optional[str]
    hardware_match_score: float
    performance_reported: Dict[str, float]
    timestamp: datetime
    verified_user: bool = False

@dataclass
class ConfigurationDownload:
    """Configuration download tracking"""
    configuration_id: str
    user_id: str
    hardware_profile_id: str
    download_timestamp: datetime
    installation_success: Optional[bool] = None
    performance_feedback: Optional[Dict[str, float]] = None
    user_feedback: Optional[str] = None

class ConfigurationDatabase:
    """Database management for community configurations"""
    
    def __init__(self, db_path: str = "community_configs.db"):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize the database schema"""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS configurations (
                    id TEXT PRIMARY KEY,
                    config_data TEXT NOT NULL,
                    hardware_compatibility TEXT NOT NULL,
                    use_case TEXT NOT NULL,
                    author TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL,
                    verified BOOLEAN DEFAULT FALSE,
                    downloads INTEGER DEFAULT 0,
                    average_rating REAL DEFAULT 0.0,
                    total_ratings INTEGER DEFAULT 0
                );
                
                CREATE TABLE IF NOT EXISTS ratings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    configuration_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    rating REAL NOT NULL,
                    review TEXT,
                    hardware_match_score REAL NOT NULL,
                    performance_data TEXT,
                    timestamp TIMESTAMP NOT NULL,
                    verified_user BOOLEAN DEFAULT FALSE,
                    FOREIGN KEY (configuration_id) REFERENCES configurations (id),
                    UNIQUE(configuration_id, user_id)
                );
                
                CREATE TABLE IF NOT EXISTS downloads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    configuration_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    hardware_profile_id TEXT NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    installation_success BOOLEAN,
                    performance_feedback TEXT,
                    user_feedback TEXT,
                    FOREIGN KEY (configuration_id) REFERENCES configurations (id)
                );
                
                CREATE TABLE IF NOT EXISTS compatibility_index (
                    configuration_id TEXT NOT NULL,
                    system_tier TEXT NOT NULL,
                    cpu_cores INTEGER,
                    memory_gb REAL,
                    has_gpu BOOLEAN,
                    interface_type TEXT,
                    compute_distribution TEXT,
                    FOREIGN KEY (configuration_id) REFERENCES configurations (id)
                );
                
                CREATE INDEX IF NOT EXISTS idx_compatibility_tier ON compatibility_index(system_tier);
                CREATE INDEX IF NOT EXISTS idx_compatibility_cpu ON compatibility_index(cpu_cores);
                CREATE INDEX IF NOT EXISTS idx_compatibility_memory ON compatibility_index(memory_gb);
                CREATE INDEX IF NOT EXISTS idx_configurations_rating ON configurations(average_rating);
                CREATE INDEX IF NOT EXISTS idx_configurations_downloads ON configurations(downloads);
            """)
    
    def store_configuration(self, config_share: ConfigurationShare) -> str:
        """Store a shared configuration"""
        
        config_id = self._generate_config_id(config_share)
        
        with sqlite3.connect(self.db_path) as conn:
            # Store main configuration
            conn.execute("""
                INSERT OR REPLACE INTO configurations 
                (id, config_data, hardware_compatibility, use_case, author, 
                 created_at, updated_at, verified, average_rating)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                config_id,
                json.dumps(asdict(config_share.configuration)),
                json.dumps(asdict(config_share.hardware_profile)),
                config_share.use_case,
                config_share.configuration.config_id.split('_')[0],  # Extract author from config_id
                datetime.now(),
                datetime.now(),
                False,  # Not verified initially
                config_share.user_rating or 0.0
            ))
            
            # Store compatibility index
            conn.execute("""
                INSERT OR REPLACE INTO compatibility_index 
                (configuration_id, system_tier, cpu_cores, memory_gb, has_gpu, 
                 interface_type, compute_distribution)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                config_id,
                config_share.hardware_profile.system_tier.value,
                config_share.hardware_profile.cpu.cores,
                config_share.hardware_profile.memory.total_gb,
                config_share.hardware_profile.gpu is not None,
                config_share.configuration.interface_type.value,
                config_share.configuration.compute_distribution.value
            ))
        
        return config_id
    
    def find_compatible_configurations(self, 
                                     hardware_profile: HardwareProfile,
                                     use_case: Optional[str] = None,
                                     limit: int = 20) -> List[CommunityConfiguration]:
        """Find configurations compatible with given hardware"""
        
        with sqlite3.connect(self.db_path) as conn:
            # Build query based on hardware compatibility
            query = """
                SELECT c.*, ci.* FROM configurations c
                JOIN compatibility_index ci ON c.id = ci.configuration_id
                WHERE ci.system_tier = ? 
                AND ci.cpu_cores <= ?
                AND ci.memory_gb <= ?
                AND (ci.has_gpu = 0 OR ? = 1)
            """
            
            params = [
                hardware_profile.system_tier.value,
                hardware_profile.cpu.cores,
                hardware_profile.memory.total_gb,
                1 if hardware_profile.gpu else 0
            ]
            
            if use_case:
                query += " AND c.use_case LIKE ?"
                params.append(f"%{use_case}%")
            
            query += " ORDER BY c.average_rating DESC, c.downloads DESC LIMIT ?"
            params.append(limit)
            
            cursor = conn.execute(query, params)
            results = cursor.fetchall()
            
            configurations = []
            for row in results:
                config_data = json.loads(row[1])
                hardware_data = json.loads(row[2])
                
                community_config = CommunityConfiguration(
                    config_id=row[0],
                    configuration=AdaptiveConfiguration(**config_data),
                    hardware_compatibility=[hardware_profile.system_tier.value],
                    success_rate=0.85,  # Default - could be calculated from download data
                    average_rating=row[9],
                    download_count=row[8],
                    created_at=datetime.fromisoformat(row[4]),
                    updated_at=datetime.fromisoformat(row[5]),
                    author=row[3],
                    verified=bool(row[6])
                )
                configurations.append(community_config)
            
            return configurations
    
    def get_configuration_details(self, config_id: str) -> Optional[CommunityConfiguration]:
        """Get detailed configuration information"""
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT * FROM configurations WHERE id = ?
            """, (config_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            config_data = json.loads(row[1])
            
            return CommunityConfiguration(
                config_id=row[0],
                configuration=AdaptiveConfiguration(**config_data),
                hardware_compatibility=[],  # Would be populated from compatibility_index
                success_rate=0.85,
                average_rating=row[9],
                download_count=row[8],
                created_at=datetime.fromisoformat(row[4]),
                updated_at=datetime.fromisoformat(row[5]),
                author=row[3],
                verified=bool(row[6])
            )
    
    def record_download(self, download: ConfigurationDownload):
        """Record a configuration download"""
        
        with sqlite3.connect(self.db_path) as conn:
            # Record download
            conn.execute("""
                INSERT INTO downloads 
                (configuration_id, user_id, hardware_profile_id, timestamp,
                 installation_success, performance_feedback, user_feedback)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                download.configuration_id,
                download.user_id,
                download.hardware_profile_id,
                download.download_timestamp,
                download.installation_success,
                json.dumps(download.performance_feedback) if download.performance_feedback else None,
                download.user_feedback
            ))
            
            # Update download count
            conn.execute("""
                UPDATE configurations 
                SET downloads = downloads + 1 
                WHERE id = ?
            """, (download.configuration_id,))
    
    def record_rating(self, rating: ConfigurationRating):
        """Record a configuration rating"""
        
        with sqlite3.connect(self.db_path) as conn:
            # Insert or update rating
            conn.execute("""
                INSERT OR REPLACE INTO ratings 
                (configuration_id, user_id, rating, review, hardware_match_score,
                 performance_data, timestamp, verified_user)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                rating.configuration_id,
                rating.user_id,
                rating.rating,
                rating.review,
                rating.hardware_match_score,
                json.dumps(rating.performance_reported),
                rating.timestamp,
                rating.verified_user
            ))
            
            # Update average rating
            cursor = conn.execute("""
                SELECT AVG(rating), COUNT(*) FROM ratings WHERE configuration_id = ?
            """, (rating.configuration_id,))
            
            avg_rating, count = cursor.fetchone()
            
            conn.execute("""
                UPDATE configurations 
                SET average_rating = ?, total_ratings = ?
                WHERE id = ?
            """, (avg_rating, count, rating.configuration_id))
    
    def get_trending_configurations(self, time_window_hours: int = 168,  # 1 week
                                  limit: int = 10) -> List[CommunityConfiguration]:
        """Get trending configurations based on recent downloads and ratings"""
        
        cutoff_time = datetime.now() - timedelta(hours=time_window_hours)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT c.*, 
                       COUNT(d.id) as recent_downloads,
                       AVG(r.rating) as recent_rating
                FROM configurations c
                LEFT JOIN downloads d ON c.id = d.configuration_id 
                    AND d.timestamp > ?
                LEFT JOIN ratings r ON c.id = r.configuration_id 
                    AND r.timestamp > ?
                GROUP BY c.id
                HAVING recent_downloads > 0 OR recent_rating > 0
                ORDER BY (recent_downloads * 0.7 + COALESCE(recent_rating, 0) * 0.3) DESC
                LIMIT ?
            """, (cutoff_time, cutoff_time, limit))
            
            results = cursor.fetchall()
            configurations = []
            
            for row in results:
                config_data = json.loads(row[1])
                
                community_config = CommunityConfiguration(
                    config_id=row[0],
                    configuration=AdaptiveConfiguration(**config_data),
                    hardware_compatibility=[],
                    success_rate=0.85,
                    average_rating=row[9],
                    download_count=row[8],
                    created_at=datetime.fromisoformat(row[4]),
                    updated_at=datetime.fromisoformat(row[5]),
                    author=row[3],
                    verified=bool(row[6])
                )
                configurations.append(community_config)
            
            return configurations
    
    def _generate_config_id(self, config_share: ConfigurationShare) -> str:
        """Generate unique ID for a configuration"""
        
        content = f"{config_share.configuration.config_id}_{config_share.use_case}_{config_share.hardware_profile.profile_id}"
        return hashlib.md5(content.encode()).hexdigest()

class CommunityModerationSystem:
    """System for moderating community contributions"""
    
    def __init__(self):
        self.verification_rules = self._load_verification_rules()
        self.trust_scores = defaultdict(float)
    
    def verify_configuration(self, config_share: ConfigurationShare) -> Dict[str, Any]:
        """Verify a configuration submission"""
        
        verification_result = {
            'passed': True,
            'issues': [],
            'warnings': [],
            'trust_score': 0.5
        }
        
        # Check basic validity
        if not self._validate_configuration_structure(config_share.configuration):
            verification_result['passed'] = False
            verification_result['issues'].append("Invalid configuration structure")
        
        # Check hardware profile validity
        if not self._validate_hardware_profile(config_share.hardware_profile):
            verification_result['passed'] = False
            verification_result['issues'].append("Invalid hardware profile")
        
        # Check for suspicious patterns
        suspicious_patterns = self._check_suspicious_patterns(config_share)
        if suspicious_patterns:
            verification_result['warnings'].extend(suspicious_patterns)
        
        # Calculate trust score
        verification_result['trust_score'] = self._calculate_trust_score(config_share)
        
        return verification_result
    
    def moderate_rating(self, rating: ConfigurationRating) -> bool:
        """Moderate a user rating"""
        
        # Check for spam patterns
        if self._is_spam_rating(rating):
            return False
        
        # Check for inappropriate content
        if rating.review and self._contains_inappropriate_content(rating.review):
            return False
        
        # Check rating validity
        if rating.rating < 1 or rating.rating > 5:
            return False
        
        return True
    
    def _validate_configuration_structure(self, config: AdaptiveConfiguration) -> bool:
        """Validate configuration structure"""
        
        try:
            # Check required fields
            required_fields = ['config_id', 'interface_type', 'compute_distribution']
            for field in required_fields:
                if not hasattr(config, field) or getattr(config, field) is None:
                    return False
            
            # Check value ranges
            if config.cpu_utilization_target < 0 or config.cpu_utilization_target > 100:
                return False
            
            if config.memory_utilization_target < 0 or config.memory_utilization_target > 100:
                return False
            
            return True
            
        except Exception:
            return False
    
    def _validate_hardware_profile(self, profile: HardwareProfile) -> bool:
        """Validate hardware profile"""
        
        try:
            # Check CPU specs
            if profile.cpu.cores < 1 or profile.cpu.cores > 128:
                return False
            
            if profile.cpu.base_frequency_ghz < 0.5 or profile.cpu.base_frequency_ghz > 10:
                return False
            
            # Check memory specs
            if profile.memory.total_gb < 0.5 or profile.memory.total_gb > 1024:
                return False
            
            return True
            
        except Exception:
            return False
    
    def _check_suspicious_patterns(self, config_share: ConfigurationShare) -> List[str]:
        """Check for suspicious patterns in submission"""
        
        warnings = []
        
        # Check for extreme resource allocations
        if config_share.configuration.memory_allocation_mb > 32768:  # 32GB
            warnings.append("Extremely high memory allocation")
        
        if config_share.configuration.processing_threads > 64:
            warnings.append("Unusually high thread count")
        
        # Check for mismatched hardware/config combinations
        if (config_share.hardware_profile.system_tier == SystemTier.BASIC and
            config_share.configuration.ui_complexity == "rich"):
            warnings.append("Rich UI on basic hardware may not perform well")
        
        return warnings
    
    def _calculate_trust_score(self, config_share: ConfigurationShare) -> float:
        """Calculate trust score for a configuration"""
        
        score = 0.5  # Base score
        
        # Bonus for detailed hardware info
        if config_share.hardware_profile.gpu:
            score += 0.1
        
        if config_share.performance_results:
            score += 0.2
        
        if config_share.notes:
            score += 0.1
        
        # Bonus for reasonable configurations
        if self._is_reasonable_config(config_share):
            score += 0.2
        
        return min(1.0, score)
    
    def _is_reasonable_config(self, config_share: ConfigurationShare) -> bool:
        """Check if configuration is reasonable for the hardware"""
        
        config = config_share.configuration
        hardware = config_share.hardware_profile
        
        # Memory allocation should not exceed available memory
        allocated_gb = config.memory_allocation_mb / 1024
        if allocated_gb > hardware.memory.available_gb:
            return False
        
        # Thread count should not greatly exceed CPU threads
        if config.processing_threads > hardware.cpu.threads * 2:
            return False
        
        return True
    
    def _is_spam_rating(self, rating: ConfigurationRating) -> bool:
        """Check if rating appears to be spam"""
        
        # Check for duplicate ratings from same user (already handled by DB constraint)
        # Check for suspicious timing patterns
        # Check for generic review text
        
        if rating.review:
            generic_phrases = ["great", "good", "bad", "ok", "fine", "works"]
            if rating.review.lower().strip() in generic_phrases:
                return True
        
        return False
    
    def _contains_inappropriate_content(self, text: str) -> bool:
        """Check for inappropriate content in text"""
        
        # Simplified inappropriate content detection
        inappropriate_words = ["spam", "scam", "fake", "virus", "malware"]
        text_lower = text.lower()
        
        return any(word in text_lower for word in inappropriate_words)
    
    def _load_verification_rules(self) -> Dict[str, Any]:
        """Load verification rules"""
        
        return {
            'max_memory_allocation_gb': 64,
            'max_processing_threads': 128,
            'max_cpu_utilization': 100,
            'max_cache_size_gb': 8,
            'allowed_interface_types': [t.value for t in InterfaceType],
            'allowed_compute_distributions': [d.value for d in ComputeDistribution]
        }

class CommunityLibrary:
    """Main community library system"""
    
    def __init__(self, db_path: str = "community_configs.db"):
        self.database = ConfigurationDatabase(db_path)
        self.moderation = CommunityModerationSystem()
        self.recommendation_engine = CommunityRecommendationEngine(self.database)
    
    async def submit_configuration(self, config_share: ConfigurationShare,
                                 user_id: str) -> Dict[str, Any]:
        """Submit a configuration to the community library"""
        
        # Verify configuration
        verification_result = self.moderation.verify_configuration(config_share)
        
        if not verification_result['passed']:
            return {
                'success': False,
                'message': 'Configuration failed verification',
                'issues': verification_result['issues']
            }
        
        # Store configuration
        config_id = self.database.store_configuration(config_share)
        
        return {
            'success': True,
            'configuration_id': config_id,
            'message': 'Configuration submitted successfully',
            'warnings': verification_result['warnings'],
            'trust_score': verification_result['trust_score']
        }
    
    async def search_configurations(self, 
                                  hardware_profile: HardwareProfile,
                                  search_criteria: Dict[str, Any]) -> List[CommunityConfiguration]:
        """Search for configurations matching criteria"""
        
        use_case = search_criteria.get('use_case')
        sort_by = search_criteria.get('sort_by', 'rating')  # rating, downloads, recent
        limit = search_criteria.get('limit', 20)
        
        if sort_by == 'trending':
            return self.database.get_trending_configurations(limit=limit)
        else:
            return self.database.find_compatible_configurations(
                hardware_profile, use_case, limit
            )
    
    async def get_recommendations(self, 
                                hardware_profile: HardwareProfile,
                                user_preferences: Dict[str, Any],
                                context: Dict[str, Any]) -> List[CommunityConfiguration]:
        """Get personalized configuration recommendations"""
        
        return await self.recommendation_engine.get_recommendations(
            hardware_profile, user_preferences, context
        )
    
    async def download_configuration(self, config_id: str, user_id: str,
                                   hardware_profile_id: str) -> Dict[str, Any]:
        """Download and track a configuration"""
        
        config = self.database.get_configuration_details(config_id)
        if not config:
            return {
                'success': False,
                'message': 'Configuration not found'
            }
        
        # Record download
        download = ConfigurationDownload(
            configuration_id=config_id,
            user_id=user_id,
            hardware_profile_id=hardware_profile_id,
            download_timestamp=datetime.now()
        )
        self.database.record_download(download)
        
        return {
            'success': True,
            'configuration': config,
            'message': 'Configuration downloaded successfully'
        }
    
    async def rate_configuration(self, config_id: str, user_id: str,
                               rating_data: Dict[str, Any]) -> Dict[str, Any]:
        """Rate a configuration"""
        
        rating = ConfigurationRating(
            configuration_id=config_id,
            user_id=user_id,
            rating=rating_data['rating'],
            review=rating_data.get('review'),
            hardware_match_score=rating_data.get('hardware_match_score', 0.8),
            performance_reported=rating_data.get('performance_data', {}),
            timestamp=datetime.now(),
            verified_user=rating_data.get('verified_user', False)
        )
        
        # Moderate rating
        if not self.moderation.moderate_rating(rating):
            return {
                'success': False,
                'message': 'Rating failed moderation'
            }
        
        # Store rating
        self.database.record_rating(rating)
        
        return {
            'success': True,
            'message': 'Rating recorded successfully'
        }
    
    async def get_configuration_analytics(self, config_id: str) -> Dict[str, Any]:
        """Get analytics for a configuration"""
        
        # Implementation would analyze download patterns, ratings, success rates
        return {
            'download_trend': 'increasing',
            'success_rate': 0.87,
            'average_performance_improvement': 0.23,
            'common_hardware_types': ['standard', 'high_end'],
            'user_satisfaction_trend': 'stable'
        }

class CommunityRecommendationEngine:
    """Engine for recommending community configurations"""
    
    def __init__(self, database: ConfigurationDatabase):
        self.database = database
    
    async def get_recommendations(self, 
                                hardware_profile: HardwareProfile,
                                user_preferences: Dict[str, Any],
                                context: Dict[str, Any]) -> List[CommunityConfiguration]:
        """Get personalized recommendations"""
        
        # Get base compatible configurations
        compatible_configs = self.database.find_compatible_configurations(
            hardware_profile, limit=50
        )
        
        # Score and rank based on user preferences and context
        scored_configs = []
        for config in compatible_configs:
            score = self._calculate_recommendation_score(
                config, hardware_profile, user_preferences, context
            )
            scored_configs.append((config, score))
        
        # Sort by score and return top recommendations
        scored_configs.sort(key=lambda x: x[1], reverse=True)
        
        return [config for config, score in scored_configs[:10]]
    
    def _calculate_recommendation_score(self, 
                                      config: CommunityConfiguration,
                                      hardware_profile: HardwareProfile,
                                      user_preferences: Dict[str, Any],
                                      context: Dict[str, Any]) -> float:
        """Calculate recommendation score for a configuration"""
        
        score = 0.0
        
        # Base score from community ratings
        score += config.average_rating * 0.3
        
        # Popularity bonus
        score += min(1.0, config.download_count / 100) * 0.2
        
        # Hardware compatibility score
        hardware_match = self._calculate_hardware_match(config, hardware_profile)
        score += hardware_match * 0.3
        
        # User preference alignment
        preference_match = self._calculate_preference_match(config, user_preferences)
        score += preference_match * 0.2
        
        return score
    
    def _calculate_hardware_match(self, 
                                config: CommunityConfiguration,
                                hardware_profile: HardwareProfile) -> float:
        """Calculate how well configuration matches hardware"""
        
        # Simplified hardware matching
        match_score = 0.5  # Base score
        
        # System tier match
        if hardware_profile.system_tier.value in config.hardware_compatibility:
            match_score += 0.3
        
        # Interface type appropriateness
        if (hardware_profile.system_tier == SystemTier.HIGH_END and
            config.configuration.interface_type == InterfaceType.FULL_HD):
            match_score += 0.2
        
        return min(1.0, match_score)
    
    def _calculate_preference_match(self, 
                                  config: CommunityConfiguration,
                                  user_preferences: Dict[str, Any]) -> float:
        """Calculate preference alignment score"""
        
        match_score = 0.5  # Base score
        
        # Performance vs efficiency preference
        if user_preferences.get('performance_priority', True):
            if config.configuration.power_profile == 'performance':
                match_score += 0.3
        else:
            if config.configuration.power_profile in ['balanced', 'efficiency']:
                match_score += 0.3
        
        # Privacy preference
        if user_preferences.get('privacy_sensitive', False):
            if not config.configuration.cloud_fallback:
                match_score += 0.2
        
        return min(1.0, match_score)