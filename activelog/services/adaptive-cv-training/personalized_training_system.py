"""
Personalized Training System
Advanced personalization for individual boats, users, and fishing environments
"""

import asyncio
import json
import logging
import sqlite3
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, asdict
from collections import defaultdict, Counter
import pickle
import cv2
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler
import hashlib

logger = logging.getLogger(__name__)

@dataclass 
class UserProfile:
    """Complete user profile for personalized training"""
    user_id: str
    boat_id: Optional[str]
    fishing_style: str  # 'commercial', 'sport', 'charter', 'research'
    experience_level: str  # 'novice', 'intermediate', 'expert', 'professional'
    target_species: List[str]
    fishing_regions: List[str]
    equipment_profile: Dict[str, Any]
    preferences: Dict[str, Any]
    created_at: datetime
    last_active: datetime

@dataclass
class EnvironmentalContext:
    """Environmental context for location-specific training"""
    location: Tuple[float, float]  # lat, lon
    depth_range: Tuple[float, float]
    season: str
    water_temperature: Optional[float]
    tide_conditions: Optional[str]
    weather_conditions: Optional[str]
    time_of_day: str
    moon_phase: Optional[str]

@dataclass
class SpeciesContext:
    """Species-specific context and behavior patterns"""
    species: str
    common_locations: List[Tuple[float, float]]
    depth_preferences: Tuple[float, float]
    seasonal_patterns: Dict[str, float]  # season -> likelihood
    time_patterns: Dict[str, float]  # hour -> likelihood
    bait_preferences: List[str]
    size_distribution: Dict[str, float]  # size_range -> frequency
    visual_characteristics: Dict[str, Any]

class PersonalizedModelArchitecture(nn.Module):
    """Personalized model with user-specific adaptations"""
    
    def __init__(self, base_model, user_profile: UserProfile):
        super().__init__()
        
        self.base_model = base_model
        self.user_profile = user_profile
        
        # User-specific feature extractors
        self.user_feature_extractor = self._build_user_features()
        
        # Environmental adaptation layers
        self.environmental_adapter = self._build_environmental_adapter()
        
        # Species-specific heads
        self.species_heads = nn.ModuleDict()
        
        # Attention mechanism for user preferences
        self.preference_attention = self._build_preference_attention()
        
        # Meta-learning components
        self.meta_learner = self._build_meta_learner()
        
    def _build_user_features(self):
        """Build user-specific feature extraction"""
        feature_dim = 128
        
        # Experience level encoding
        experience_levels = ['novice', 'intermediate', 'expert', 'professional']
        experience_embedding = nn.Embedding(len(experience_levels), 16)
        
        # Fishing style encoding
        fishing_styles = ['commercial', 'sport', 'charter', 'research']
        style_embedding = nn.Embedding(len(fishing_styles), 16)
        
        # Equipment profile encoding
        equipment_encoder = nn.Sequential(
            nn.Linear(64, 32),  # Assume 64 equipment features
            nn.ReLU(),
            nn.Linear(32, 16)
        )
        
        # Combine all user features
        return nn.Sequential(
            nn.Linear(48, feature_dim),  # 16+16+16 user features
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(feature_dim, feature_dim)
        )
    
    def _build_environmental_adapter(self):
        """Build environmental adaptation layer"""
        return nn.Sequential(
            nn.Linear(512 + 128, 256),  # Base features + user features
            nn.ReLU(),
            nn.BatchNorm1d(256),
            nn.Dropout(0.4),
            nn.Linear(256, 512)
        )
    
    def _build_preference_attention(self):
        """Build attention mechanism for user preferences"""
        return nn.MultiheadAttention(
            embed_dim=512,
            num_heads=8,
            dropout=0.1,
            batch_first=True
        )
    
    def _build_meta_learner(self):
        """Build meta-learning component for fast adaptation"""
        return nn.Sequential(
            nn.Linear(512, 256),
            nn.ReLU(),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Linear(128, 64)  # Meta parameters
        )
    
    def forward(self, x, environmental_context=None, species_preferences=None):
        # Extract base features
        base_features, _ = self.base_model(x)
        
        # Extract user-specific features
        user_features = self._encode_user_profile()
        
        # Combine features
        combined_features = torch.cat([base_features, user_features.expand(base_features.size(0), -1)], dim=1)
        
        # Environmental adaptation
        adapted_features = self.environmental_adapter(combined_features)
        
        # Apply preference attention
        if species_preferences is not None:
            attended_features, _ = self.preference_attention(
                adapted_features.unsqueeze(1), 
                species_preferences.unsqueeze(1),
                species_preferences.unsqueeze(1)
            )
            adapted_features = attended_features.squeeze(1)
        
        # Meta-learning adaptation
        meta_params = self.meta_learner(adapted_features)
        
        return adapted_features, meta_params
    
    def _encode_user_profile(self):
        """Encode user profile to tensor"""
        # Simplified encoding (in practice, would be more sophisticated)
        device = next(self.parameters()).device
        
        # Experience level (0-3)
        experience_map = {'novice': 0, 'intermediate': 1, 'expert': 2, 'professional': 3}
        experience_idx = experience_map.get(self.user_profile.experience_level, 0)
        
        # Fishing style (0-3)  
        style_map = {'commercial': 0, 'sport': 1, 'charter': 2, 'research': 3}
        style_idx = style_map.get(self.user_profile.fishing_style, 1)
        
        # Create dummy equipment features
        equipment_features = torch.randn(16, device=device)
        
        # Combine all features
        combined = torch.cat([
            torch.tensor([experience_idx, style_idx], device=device, dtype=torch.float32),
            equipment_features
        ])
        
        return self.user_feature_extractor(combined)

class AdaptationStrategy:
    """Strategies for model adaptation based on user characteristics"""
    
    @staticmethod
    def get_strategy(user_profile: UserProfile) -> str:
        """Determine optimal adaptation strategy for user"""
        
        if user_profile.experience_level == 'novice':
            return 'guided_learning'  # More feedback, simpler predictions
        elif user_profile.experience_level == 'professional':
            return 'expert_tuning'  # Fine-grained species distinction
        elif user_profile.fishing_style == 'commercial':
            return 'efficiency_focused'  # Speed and accuracy balance
        elif user_profile.fishing_style == 'research':
            return 'precision_focused'  # Maximum accuracy
        else:
            return 'balanced'  # Standard adaptation

class EnvironmentalLearning:
    """Learn environmental patterns for location-specific adaptation"""
    
    def __init__(self):
        self.location_clusters = {}
        self.species_location_patterns = defaultdict(list)
        self.environmental_features = defaultdict(list)
        
    def add_environmental_data(self, location: Tuple[float, float], 
                             species: str, context: EnvironmentalContext):
        """Add environmental data point"""
        # Cluster locations
        location_key = self._get_location_cluster(location)
        
        if location_key not in self.location_clusters:
            self.location_clusters[location_key] = []
        
        self.location_clusters[location_key].append({
            'species': species,
            'context': context,
            'timestamp': datetime.now()
        })
        
        # Track species-location patterns
        self.species_location_patterns[species].append(location)
        
        # Extract environmental features
        self.environmental_features[location_key].append({
            'depth': (context.depth_range[0] + context.depth_range[1]) / 2,
            'season': context.season,
            'temperature': context.water_temperature or 0,
            'tide': context.tide_conditions,
            'weather': context.weather_conditions,
            'time': context.time_of_day
        })
    
    def _get_location_cluster(self, location: Tuple[float, float], 
                            radius_km: float = 5.0) -> str:
        """Get location cluster identifier"""
        # Simple grid-based clustering
        lat, lon = location
        grid_size = radius_km / 111  # Approximate km to degrees
        
        grid_lat = int(lat / grid_size) * grid_size
        grid_lon = int(lon / grid_size) * grid_size
        
        return f"{grid_lat:.3f},{grid_lon:.3f}"
    
    def get_location_predictions(self, location: Tuple[float, float]) -> Dict[str, float]:
        """Get species probability predictions for location"""
        location_key = self._get_location_cluster(location)
        
        if location_key not in self.location_clusters:
            return {}
        
        # Count species occurrences at this location
        species_counts = Counter()
        total_observations = 0
        
        for observation in self.location_clusters[location_key]:
            species_counts[observation['species']] += 1
            total_observations += 1
        
        # Convert to probabilities
        probabilities = {}
        for species, count in species_counts.items():
            probabilities[species] = count / total_observations
        
        return probabilities

class PersonalizedTrainingSystem:
    """Complete personalized training system"""
    
    def __init__(self, adaptive_system, db_path: str = "personalized_training.db"):
        self.adaptive_system = adaptive_system
        self.db_path = db_path
        
        # User management
        self.user_profiles: Dict[str, UserProfile] = {}
        self.personalized_models: Dict[str, PersonalizedModelArchitecture] = {}
        
        # Environmental learning
        self.environmental_learning = EnvironmentalLearning()
        
        # Species context
        self.species_contexts: Dict[str, SpeciesContext] = {}
        
        # Adaptation strategies
        self.adaptation_strategies: Dict[str, str] = {}
        
        # Performance tracking per user
        self.user_performance: Dict[str, Dict] = defaultdict(dict)
        
        # Initialize database
        self.init_database()
        
        # Load existing profiles
        self.load_user_profiles()
        
    def init_database(self):
        """Initialize personalized training database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_profiles (
                user_id TEXT PRIMARY KEY,
                boat_id TEXT,
                fishing_style TEXT,
                experience_level TEXT,
                target_species TEXT,
                fishing_regions TEXT,
                equipment_profile TEXT,
                preferences TEXT,
                created_at DATETIME,
                last_active DATETIME
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS species_contexts (
                species TEXT PRIMARY KEY,
                common_locations TEXT,
                depth_preferences TEXT,
                seasonal_patterns TEXT,
                time_patterns TEXT,
                bait_preferences TEXT,
                size_distribution TEXT,
                visual_characteristics TEXT,
                updated_at DATETIME
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS environmental_data (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                boat_id TEXT,
                location_lat REAL,
                location_lon REAL,
                species TEXT,
                context_data TEXT,
                timestamp DATETIME
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS personalization_metrics (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                boat_id TEXT,
                adaptation_type TEXT,
                before_accuracy REAL,
                after_accuracy REAL,
                improvement_score REAL,
                timestamp DATETIME
            )
        """)
        
        conn.commit()
        conn.close()
    
    def load_user_profiles(self):
        """Load user profiles from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM user_profiles")
        rows = cursor.fetchall()
        
        for row in rows:
            user_id = row[0]
            profile = UserProfile(
                user_id=user_id,
                boat_id=row[1],
                fishing_style=row[2],
                experience_level=row[3],
                target_species=json.loads(row[4]) if row[4] else [],
                fishing_regions=json.loads(row[5]) if row[5] else [],
                equipment_profile=json.loads(row[6]) if row[6] else {},
                preferences=json.loads(row[7]) if row[7] else {},
                created_at=datetime.fromisoformat(row[8]),
                last_active=datetime.fromisoformat(row[9])
            )
            
            self.user_profiles[user_id] = profile
            
            # Create personalized model
            self.create_personalized_model(profile)
        
        conn.close()
        logger.info(f"Loaded {len(self.user_profiles)} user profiles")
    
    def create_user_profile(self, user_id: str, boat_id: Optional[str] = None,
                          fishing_style: str = 'sport', experience_level: str = 'intermediate',
                          target_species: List[str] = None, 
                          fishing_regions: List[str] = None,
                          equipment_profile: Dict[str, Any] = None,
                          preferences: Dict[str, Any] = None) -> UserProfile:
        """Create new user profile"""
        
        profile = UserProfile(
            user_id=user_id,
            boat_id=boat_id,
            fishing_style=fishing_style,
            experience_level=experience_level,
            target_species=target_species or [],
            fishing_regions=fishing_regions or [],
            equipment_profile=equipment_profile or {},
            preferences=preferences or {},
            created_at=datetime.now(),
            last_active=datetime.now()
        )
        
        self.user_profiles[user_id] = profile
        
        # Save to database
        self.save_user_profile(profile)
        
        # Create personalized model
        self.create_personalized_model(profile)
        
        # Determine adaptation strategy
        self.adaptation_strategies[user_id] = AdaptationStrategy.get_strategy(profile)
        
        logger.info(f"Created user profile for {user_id} with strategy: {self.adaptation_strategies[user_id]}")
        
        return profile
    
    def save_user_profile(self, profile: UserProfile):
        """Save user profile to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO user_profiles (
                user_id, boat_id, fishing_style, experience_level,
                target_species, fishing_regions, equipment_profile,
                preferences, created_at, last_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            profile.user_id,
            profile.boat_id,
            profile.fishing_style,
            profile.experience_level,
            json.dumps(profile.target_species),
            json.dumps(profile.fishing_regions),
            json.dumps(profile.equipment_profile),
            json.dumps(profile.preferences),
            profile.created_at.isoformat(),
            profile.last_active.isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def create_personalized_model(self, profile: UserProfile) -> PersonalizedModelArchitecture:
        """Create personalized model for user"""
        model = PersonalizedModelArchitecture(
            self.adaptive_system.model,
            profile
        )
        
        self.personalized_models[profile.user_id] = model
        
        logger.info(f"Created personalized model for {profile.user_id}")
        return model
    
    def update_user_activity(self, user_id: str, activity_data: Dict[str, Any]):
        """Update user activity and adapt profile"""
        if user_id not in self.user_profiles:
            return
        
        profile = self.user_profiles[user_id]
        profile.last_active = datetime.now()
        
        # Update target species based on recent catches
        if 'recent_species' in activity_data:
            recent_species = activity_data['recent_species']
            
            # Add new species to targets
            for species in recent_species:
                if species not in profile.target_species:
                    profile.target_species.append(species)
            
            # Keep only most recent/frequent species (max 10)
            if len(profile.target_species) > 10:
                # Could implement more sophisticated pruning
                profile.target_species = profile.target_species[-10:]
        
        # Update fishing regions
        if 'location' in activity_data:
            location = activity_data['location']
            location_str = f"{location[0]:.2f},{location[1]:.2f}"
            
            if location_str not in profile.fishing_regions:
                profile.fishing_regions.append(location_str)
            
            # Keep only recent regions (max 20)
            if len(profile.fishing_regions) > 20:
                profile.fishing_regions = profile.fishing_regions[-20:]
        
        # Update equipment profile
        if 'equipment' in activity_data:
            profile.equipment_profile.update(activity_data['equipment'])
        
        # Save updated profile
        self.save_user_profile(profile)
    
    def add_environmental_observation(self, user_id: str, location: Tuple[float, float],
                                   species: str, context: EnvironmentalContext):
        """Add environmental observation for learning"""
        
        # Add to environmental learning system
        self.environmental_learning.add_environmental_data(location, species, context)
        
        # Update user activity
        self.update_user_activity(user_id, {
            'recent_species': [species],
            'location': location
        })
        
        # Save to database
        self.save_environmental_observation(user_id, location, species, context)
    
    def save_environmental_observation(self, user_id: str, location: Tuple[float, float],
                                     species: str, context: EnvironmentalContext):
        """Save environmental observation to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        observation_id = hashlib.md5(
            f"{user_id}_{location}_{species}_{datetime.now().isoformat()}".encode()
        ).hexdigest()
        
        profile = self.user_profiles.get(user_id)
        boat_id = profile.boat_id if profile else None
        
        cursor.execute("""
            INSERT INTO environmental_data (
                id, user_id, boat_id, location_lat, location_lon,
                species, context_data, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            observation_id,
            user_id,
            boat_id,
            location[0],
            location[1],
            species,
            json.dumps(asdict(context), default=str),
            datetime.now()
        ))
        
        conn.commit()
        conn.close()
    
    def get_personalized_predictions(self, user_id: str, image_data: np.ndarray,
                                   location: Optional[Tuple[float, float]] = None,
                                   environmental_context: Optional[EnvironmentalContext] = None) -> Dict[str, Any]:
        """Get personalized predictions for user"""
        
        if user_id not in self.personalized_models:
            # Use base model if no personalized model exists
            return self._get_base_predictions(image_data)
        
        model = self.personalized_models[user_id]
        profile = self.user_profiles[user_id]
        
        # Prepare input
        transform = self._get_transform()
        input_tensor = transform(image_data).unsqueeze(0)
        
        # Get environmental predictions if location provided
        location_priors = {}
        if location:
            location_priors = self.environmental_learning.get_location_predictions(location)
        
        # Get personalized features and predictions
        with torch.no_grad():
            model.eval()
            adapted_features, meta_params = model(input_tensor)
            
            # Apply user-specific classification
            # This would need to be connected to actual classification head
            # For now, returning structure for integration
            
        # Combine with location priors
        base_predictions = self._get_base_predictions(image_data)
        
        # Apply personalization adjustments
        personalized_predictions = self._apply_personalization(
            base_predictions, profile, location_priors, environmental_context
        )
        
        return personalized_predictions
    
    def _apply_personalization(self, base_predictions: Dict[str, Any],
                             profile: UserProfile, 
                             location_priors: Dict[str, float],
                             environmental_context: Optional[EnvironmentalContext]) -> Dict[str, Any]:
        """Apply personalization adjustments to base predictions"""
        
        personalized = base_predictions.copy()
        
        # Boost confidence for target species
        if 'species' in personalized and personalized['species'] in profile.target_species:
            personalized['confidence'] *= 1.2  # 20% boost for target species
        
        # Apply location priors
        if location_priors and 'species' in personalized:
            species = personalized['species']
            if species in location_priors:
                location_boost = location_priors[species]
                personalized['confidence'] *= (1 + location_boost)
        
        # Apply experience-based adjustments
        if profile.experience_level == 'novice':
            # Provide more conservative predictions
            personalized['confidence'] *= 0.9
            personalized['explanation'] = "Conservative prediction for learning"
        elif profile.experience_level == 'expert':
            # Allow more nuanced distinctions
            personalized['confidence'] *= 1.1
            personalized['fine_grained_species'] = self._get_subspecies_prediction(personalized['species'])
        
        # Add personalization metadata
        personalized['personalization'] = {
            'strategy': self.adaptation_strategies.get(profile.user_id, 'balanced'),
            'user_experience': profile.experience_level,
            'target_species_match': personalized.get('species') in profile.target_species,
            'location_familiarity': len(profile.fishing_regions) > 5
        }
        
        return personalized
    
    def _get_base_predictions(self, image_data: np.ndarray) -> Dict[str, Any]:
        """Get base model predictions"""
        # This would call the base adaptive system
        # Simplified for now
        return {
            'species': 'king_salmon',
            'confidence': 0.75,
            'alternatives': [
                {'species': 'coho_salmon', 'confidence': 0.15},
                {'species': 'steelhead', 'confidence': 0.10}
            ]
        }
    
    def _get_subspecies_prediction(self, species: str) -> Optional[str]:
        """Get subspecies or more specific identification"""
        subspecies_map = {
            'king_salmon': ['spring_chinook', 'fall_chinook', 'winter_chinook'],
            'coho_salmon': ['wild_coho', 'hatchery_coho'],
            'steelhead': ['summer_steelhead', 'winter_steelhead']
        }
        
        if species in subspecies_map:
            return subspecies_map[species][0]  # Return first for simplicity
        
        return None
    
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
    
    def get_user_insights(self, user_id: str) -> Dict[str, Any]:
        """Get personalized insights for user"""
        if user_id not in self.user_profiles:
            return {"error": "User profile not found"}
        
        profile = self.user_profiles[user_id]
        
        # Get species success rates
        species_performance = {}
        if user_id in self.user_performance:
            species_performance = self.user_performance[user_id]
        
        # Get location insights
        location_insights = {}
        for region in profile.fishing_regions:
            lat, lon = map(float, region.split(','))
            location_predictions = self.environmental_learning.get_location_predictions((lat, lon))
            location_insights[region] = location_predictions
        
        # Generate recommendations
        recommendations = self._generate_recommendations(profile, species_performance, location_insights)
        
        return {
            "user_profile": asdict(profile),
            "species_performance": species_performance,
            "location_insights": location_insights,
            "recommendations": recommendations,
            "adaptation_strategy": self.adaptation_strategies.get(user_id, 'balanced')
        }
    
    def _generate_recommendations(self, profile: UserProfile, 
                                species_performance: Dict[str, Any],
                                location_insights: Dict[str, Any]) -> List[str]:
        """Generate personalized recommendations"""
        recommendations = []
        
        # Experience-based recommendations
        if profile.experience_level == 'novice':
            recommendations.append("Focus on common species like salmon and trout for better learning")
            recommendations.append("Use voice commands to correct predictions - this helps the AI learn your preferences")
        elif profile.experience_level == 'expert':
            recommendations.append("Enable fine-grained species identification for subspecies recognition")
            recommendations.append("Your expertise can help train the model - consider enabling research mode")
        
        # Performance-based recommendations
        if species_performance:
            low_performing = [s for s, perf in species_performance.items() if perf.get('accuracy', 1) < 0.7]
            if low_performing:
                recommendations.append(f"Practice identifying {', '.join(low_performing[:3])} - these need improvement")
        
        # Location-based recommendations
        if len(profile.fishing_regions) > 5:
            recommendations.append("Your wide fishing experience helps the model understand regional variations")
        elif len(profile.fishing_regions) < 3:
            recommendations.append("Try fishing in different areas to improve model accuracy across locations")
        
        # Equipment-based recommendations
        if 'camera_quality' in profile.equipment_profile:
            quality = profile.equipment_profile['camera_quality']
            if quality == 'low':
                recommendations.append("Consider upgrading your camera for better species recognition")
        
        return recommendations

if __name__ == "__main__":
    # Test personalized training system
    import asyncio
    from main import AdaptiveCVTrainingSystem
    
    async def test_personalized_system():
        # Create adaptive system
        cv_system = AdaptiveCVTrainingSystem()
        
        # Create personalized training system
        personalized_system = PersonalizedTrainingSystem(cv_system)
        
        # Create test user profile
        profile = personalized_system.create_user_profile(
            user_id="test_fisherman",
            boat_id="fishing_vessel_1",
            fishing_style="sport",
            experience_level="intermediate",
            target_species=["king_salmon", "coho_salmon", "steelhead"],
            fishing_regions=["47.6,-122.3", "47.7,-122.4"],
            equipment_profile={"camera_quality": "high", "gps": True},
            preferences={"voice_feedback": True, "detailed_analysis": True}
        )
        
        print("Created user profile:", profile.user_id)
        
        # Add environmental observation
        context = EnvironmentalContext(
            location=(47.6, -122.3),
            depth_range=(20, 40),
            season="summer",
            water_temperature=62.5,
            tide_conditions="incoming",
            weather_conditions="overcast",
            time_of_day="morning",
            moon_phase="new"
        )
        
        personalized_system.add_environmental_observation(
            user_id="test_fisherman",
            location=(47.6, -122.3),
            species="king_salmon",
            context=context
        )
        
        # Get personalized predictions
        dummy_image = np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8)
        predictions = personalized_system.get_personalized_predictions(
            user_id="test_fisherman",
            image_data=dummy_image,
            location=(47.6, -122.3),
            environmental_context=context
        )
        
        print("Personalized predictions:", json.dumps(predictions, indent=2, default=str))
        
        # Get user insights
        insights = personalized_system.get_user_insights("test_fisherman")
        print("User insights:", json.dumps(insights, indent=2, default=str))
    
    # Run test
    asyncio.run(test_personalized_system())