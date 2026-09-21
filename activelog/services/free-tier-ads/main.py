#!/usr/bin/env python3
"""
Free Tier with Ads System
Manages compute balance and ad-based free tier for all ActiveLog domains
"""

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from datetime import datetime, timedelta
import sqlite3
import os
import uvicorn
import logging
from typing import List, Optional, Dict, Any
import json
import numpy as np
import asyncio
from collections import defaultdict, deque
import threading
import time
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
import pickle

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="ActiveLog ML-Powered Ad Revenue System",
    description="ML-powered ad targeting and revenue optimization across all domains",
    version="2.0.0"
)

# Database setup
DB_PATH = "data/free_tier.db"
ML_MODEL_PATH = "models/"

# ML-powered ad targeting models
class AdTargetingEngine:
    """Advanced ML-powered ad targeting and revenue optimization"""
    
    def __init__(self):
        self.user_profiles = defaultdict(lambda: {
            'demographics': {},
            'interests': set(),
            'behavior_patterns': deque(maxlen=1000),
            'engagement_history': deque(maxlen=500),
            'conversion_rates': defaultdict(float),
            'value_score': 0.0
        })
        self.ad_performance = defaultdict(lambda: {
            'impressions': 0,
            'clicks': 0,
            'conversions': 0,
            'revenue': 0.0,
            'targeting_accuracy': 0.0
        })
        self.ml_models = {}
        self.scalers = {}
        self.revenue_optimizer = None
        
        self.init_ml_models()
        self.start_background_optimization()
    
    def init_ml_models(self):
        """Initialize ML models for ad targeting"""
        os.makedirs(ML_MODEL_PATH, exist_ok=True)
        
        model_types = ['engagement_predictor', 'conversion_predictor', 'value_estimator']
        
        for model_type in model_types:
            model_file = f"{ML_MODEL_PATH}{model_type}_model.pkl"
            scaler_file = f"{ML_MODEL_PATH}{model_type}_scaler.pkl"
            
            try:
                with open(model_file, 'rb') as f:
                    self.ml_models[model_type] = pickle.load(f)
                with open(scaler_file, 'rb') as f:
                    self.scalers[model_type] = pickle.load(f)
                logger.info(f"Loaded {model_type} model")
            except FileNotFoundError:
                # Create new models
                self.ml_models[model_type] = RandomForestClassifier(n_estimators=100, random_state=42)
                self.scalers[model_type] = StandardScaler()
                logger.info(f"Created new {model_type} model")
    
    def update_user_profile(self, user_id: str, domain: str, activity_data: Dict[str, Any]):
        """Update user profile with new activity data"""
        profile = self.user_profiles[user_id]
        
        # Update demographics
        if 'age' in activity_data:
            profile['demographics']['age'] = activity_data['age']
        if 'location' in activity_data:
            profile['demographics']['location'] = activity_data['location']
        if 'device_type' in activity_data:
            profile['demographics']['device_type'] = activity_data['device_type']
        
        # Update interests based on activity
        if 'page_views' in activity_data:
            for page in activity_data['page_views']:
                interest = self.extract_interest_from_page(page)
                if interest:
                    profile['interests'].add(interest)
        
        # Update behavior patterns
        behavior = {
            'domain': domain,
            'timestamp': datetime.now(),
            'session_duration': activity_data.get('session_duration', 0),
            'pages_visited': activity_data.get('pages_visited', 0),
            'actions_taken': activity_data.get('actions_taken', 0),
            'time_of_day': datetime.now().hour,
            'day_of_week': datetime.now().weekday()
        }
        profile['behavior_patterns'].append(behavior)
        
        # Calculate user value score
        profile['value_score'] = self.calculate_user_value(profile)
        
        logger.debug(f"Updated profile for user {user_id}")
    
    def extract_interest_from_page(self, page_url: str) -> Optional[str]:
        """Extract interest category from page URL"""
        interest_mapping = {
            'business': ['dashboard', 'analytics', 'reports', 'finance'],
            'personal': ['journal', 'diary', 'personal', 'thoughts'],
            'gaming': ['game', 'player', 'score', 'achievement'],
            'education': ['study', 'learn', 'course', 'tutorial'],
            'creative': ['maker', 'project', 'build', 'create'],
            'outdoor': ['fishing', 'marine', 'boat', 'captain'],
            'entertainment': ['dm', 'campaign', 'story', 'character']
        }
        
        page_lower = page_url.lower()
        for interest, keywords in interest_mapping.items():
            if any(keyword in page_lower for keyword in keywords):
                return interest
        
        return None
    
    def calculate_user_value(self, profile: Dict[str, Any]) -> float:
        """Calculate user value score based on behavior and engagement"""
        value_score = 0.0
        
        # Engagement frequency
        if profile['behavior_patterns']:
            recent_sessions = [b for b in profile['behavior_patterns'] 
                             if b['timestamp'] > datetime.now() - timedelta(days=7)]
            value_score += min(len(recent_sessions) * 0.1, 1.0)
        
        # Session quality
        if profile['behavior_patterns']:
            avg_session_duration = np.mean([b['session_duration'] for b in profile['behavior_patterns']])
            avg_pages = np.mean([b['pages_visited'] for b in profile['behavior_patterns']])
            value_score += min(avg_session_duration / 1800 * 0.3, 0.3)  # 30 min = max score
            value_score += min(avg_pages / 10 * 0.2, 0.2)  # 10 pages = max score
        
        # Conversion history
        total_conversions = sum(profile['conversion_rates'].values())
        value_score += min(total_conversions * 0.4, 0.4)
        
        return min(value_score, 1.0)
    
    def predict_ad_engagement(self, user_id: str, ad_type: str, context: Dict[str, Any]) -> Dict[str, float]:
        """Predict user engagement probability for different ad types"""
        profile = self.user_profiles[user_id]
        
        # Create feature vector
        features = self.create_feature_vector(profile, ad_type, context)
        
        predictions = {}
        
        # Predict engagement probability
        if 'engagement_predictor' in self.ml_models:
            try:
                features_scaled = self.scalers['engagement_predictor'].transform([features])
                eng_prob = self.ml_models['engagement_predictor'].predict_proba(features_scaled)[0]
                predictions['engagement_probability'] = eng_prob[1] if len(eng_prob) > 1 else 0.5
            except:
                predictions['engagement_probability'] = 0.5
        
        # Predict conversion probability
        if 'conversion_predictor' in self.ml_models:
            try:
                features_scaled = self.scalers['conversion_predictor'].transform([features])
                conv_prob = self.ml_models['conversion_predictor'].predict_proba(features_scaled)[0]
                predictions['conversion_probability'] = conv_prob[1] if len(conv_prob) > 1 else 0.1
            except:
                predictions['conversion_probability'] = 0.1
        
        # Estimate value
        if 'value_estimator' in self.ml_models:
            try:
                features_scaled = self.scalers['value_estimator'].transform([features])
                value_est = self.ml_models['value_estimator'].predict(features_scaled)[0]
                predictions['estimated_value'] = max(value_est, 0.01)
            except:
                predictions['estimated_value'] = 0.05
        
        return predictions
    
    def create_feature_vector(self, profile: Dict[str, Any], ad_type: str, context: Dict[str, Any]) -> List[float]:
        """Create feature vector for ML predictions"""
        features = []
        
        # User demographics
        features.append(profile['demographics'].get('age', 30) / 100.0)
        features.append(1.0 if profile['demographics'].get('device_type') == 'mobile' else 0.0)
        
        # User value score
        features.append(profile['value_score'])
        
        # Behavioral features
        if profile['behavior_patterns']:
            recent_sessions = [b for b in profile['behavior_patterns'] 
                             if b['timestamp'] > datetime.now() - timedelta(days=7)]
            features.append(len(recent_sessions) / 7.0)  # Sessions per day
            
            if recent_sessions:
                features.append(np.mean([s['session_duration'] for s in recent_sessions]) / 3600.0)
                features.append(np.mean([s['pages_visited'] for s in recent_sessions]) / 20.0)
            else:
                features.extend([0.0, 0.0])
        else:
            features.extend([0.0, 0.0, 0.0])
        
        # Interest matching
        relevant_interests = self.get_relevant_interests_for_ad(ad_type)
        interest_match = len(profile['interests'].intersection(relevant_interests)) / max(len(relevant_interests), 1)
        features.append(interest_match)
        
        # Time context
        features.append(context.get('hour_of_day', 12) / 24.0)
        features.append(context.get('day_of_week', 1) / 7.0)
        
        # Ad type encoding (one-hot)
        ad_types = ['banner', 'video', 'native', 'interstitial', 'sponsored']
        for atype in ad_types:
            features.append(1.0 if ad_type == atype else 0.0)
        
        return features
    
    def get_relevant_interests_for_ad(self, ad_type: str) -> set:
        """Get relevant interests for ad type"""
        ad_interest_mapping = {
            'business_tools': {'business', 'professional'},
            'gaming': {'gaming', 'entertainment'},
            'education': {'education', 'learning'},
            'outdoor_gear': {'outdoor', 'sports'},
            'creative_software': {'creative', 'design'},
            'productivity': {'business', 'professional', 'education'}
        }
        
        return ad_interest_mapping.get(ad_type, set())
    
    def optimize_ad_placement(self, user_id: str, available_ads: List[Dict[str, Any]], 
                             context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Optimize ad placement using ML predictions"""
        ad_scores = []
        
        for ad in available_ads:
            predictions = self.predict_ad_engagement(user_id, ad['type'], context)
            
            # Calculate overall score
            score = (
                predictions['engagement_probability'] * 0.4 +
                predictions['conversion_probability'] * 0.4 +
                predictions['estimated_value'] * 0.2
            )
            
            ad_with_score = ad.copy()
            ad_with_score['ml_score'] = score
            ad_with_score['predictions'] = predictions
            ad_scores.append(ad_with_score)
        
        # Sort by score (highest first)
        return sorted(ad_scores, key=lambda x: x['ml_score'], reverse=True)
    
    def record_ad_interaction(self, user_id: str, ad_id: str, interaction_type: str, 
                            value: float = 0.0):
        """Record ad interaction for ML training"""
        profile = self.user_profiles[user_id]
        ad_perf = self.ad_performance[ad_id]
        
        # Update engagement history
        engagement = {
            'ad_id': ad_id,
            'interaction_type': interaction_type,
            'value': value,
            'timestamp': datetime.now()
        }
        profile['engagement_history'].append(engagement)
        
        # Update ad performance
        if interaction_type == 'impression':
            ad_perf['impressions'] += 1
        elif interaction_type == 'click':
            ad_perf['clicks'] += 1
        elif interaction_type == 'conversion':
            ad_perf['conversions'] += 1
            ad_perf['revenue'] += value
            
            # Update user conversion rates
            ad_type = ad_id.split('_')[0] if '_' in ad_id else 'unknown'
            profile['conversion_rates'][ad_type] += 0.1
    
    def retrain_models(self):
        """Retrain ML models with recent data"""
        logger.info("Retraining ML models with recent engagement data")
        
        # Collect training data
        X_engagement = []
        y_engagement = []
        X_conversion = []
        y_conversion = []
        X_value = []
        y_value = []
        
        for user_id, profile in self.user_profiles.items():
            for engagement in profile['engagement_history']:
                if engagement['timestamp'] > datetime.now() - timedelta(days=30):
                    # Create features for this engagement
                    ad_type = engagement['ad_id'].split('_')[0] if '_' in engagement['ad_id'] else 'unknown'
                    context = {'hour_of_day': engagement['timestamp'].hour, 'day_of_week': engagement['timestamp'].weekday()}
                    features = self.create_feature_vector(profile, ad_type, context)
                    
                    # Engagement labels
                    X_engagement.append(features)
                    y_engagement.append(1 if engagement['interaction_type'] in ['click', 'conversion'] else 0)
                    
                    # Conversion labels
                    X_conversion.append(features)
                    y_conversion.append(1 if engagement['interaction_type'] == 'conversion' else 0)
                    
                    # Value labels
                    X_value.append(features)
                    y_value.append(engagement['value'])
        
        # Train models if we have enough data
        if len(X_engagement) > 100:
            try:
                # Train engagement predictor
                X_eng_scaled = self.scalers['engagement_predictor'].fit_transform(X_engagement)
                self.ml_models['engagement_predictor'].fit(X_eng_scaled, y_engagement)
                
                # Train conversion predictor  
                X_conv_scaled = self.scalers['conversion_predictor'].fit_transform(X_conversion)
                self.ml_models['conversion_predictor'].fit(X_conv_scaled, y_conversion)
                
                # Train value estimator (regression)
                from sklearn.ensemble import RandomForestRegressor
                if not isinstance(self.ml_models['value_estimator'], RandomForestRegressor):
                    self.ml_models['value_estimator'] = RandomForestRegressor(n_estimators=100, random_state=42)
                
                X_val_scaled = self.scalers['value_estimator'].fit_transform(X_value)
                self.ml_models['value_estimator'].fit(X_val_scaled, y_value)
                
                # Save models
                self.save_models()
                
                logger.info(f"Models retrained with {len(X_engagement)} engagement samples")
                
            except Exception as e:
                logger.error(f"Model retraining failed: {e}")
    
    def save_models(self):
        """Save trained models to disk"""
        for model_type in self.ml_models:
            model_file = f"{ML_MODEL_PATH}{model_type}_model.pkl"
            scaler_file = f"{ML_MODEL_PATH}{model_type}_scaler.pkl"
            
            with open(model_file, 'wb') as f:
                pickle.dump(self.ml_models[model_type], f)
            with open(scaler_file, 'wb') as f:
                pickle.dump(self.scalers[model_type], f)
    
    def get_revenue_analytics(self) -> Dict[str, Any]:
        """Get comprehensive revenue analytics"""
        total_impressions = sum(perf['impressions'] for perf in self.ad_performance.values())
        total_clicks = sum(perf['clicks'] for perf in self.ad_performance.values())
        total_conversions = sum(perf['conversions'] for perf in self.ad_performance.values())
        total_revenue = sum(perf['revenue'] for perf in self.ad_performance.values())
        
        analytics = {
            'total_impressions': total_impressions,
            'total_clicks': total_clicks,
            'total_conversions': total_conversions,
            'total_revenue': round(total_revenue, 2),
            'ctr': round((total_clicks / max(total_impressions, 1)) * 100, 2),
            'conversion_rate': round((total_conversions / max(total_clicks, 1)) * 100, 2),
            'revenue_per_impression': round(total_revenue / max(total_impressions, 1), 4),
            'revenue_per_click': round(total_revenue / max(total_clicks, 1), 2),
            'active_users': len(self.user_profiles),
            'high_value_users': len([p for p in self.user_profiles.values() if p['value_score'] > 0.7])
        }
        
        return analytics
    
    def start_background_optimization(self):
        """Start background ML optimization tasks"""
        def optimization_worker():
            while True:
                try:
                    # Retrain models every 4 hours
                    self.retrain_models()
                    
                    # Cleanup old data
                    cutoff_time = datetime.now() - timedelta(days=90)
                    for profile in self.user_profiles.values():
                        profile['behavior_patterns'] = deque([
                            b for b in profile['behavior_patterns'] 
                            if b['timestamp'] > cutoff_time
                        ], maxlen=1000)
                        profile['engagement_history'] = deque([
                            e for e in profile['engagement_history'] 
                            if e['timestamp'] > cutoff_time
                        ], maxlen=500)
                    
                    time.sleep(14400)  # 4 hours
                    
                except Exception as e:
                    logger.error(f"Background optimization error: {e}")
                    time.sleep(3600)  # Retry in 1 hour
        
        threading.Thread(target=optimization_worker, daemon=True).start()
        logger.info("ML optimization background tasks started")

# Global ad targeting engine
ad_targeting_engine = AdTargetingEngine()

def init_db():
    """Initialize the database"""
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # User compute balance table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_balance (
            user_id TEXT PRIMARY KEY,
            compute_minutes INTEGER DEFAULT 0,
            total_ads_watched INTEGER DEFAULT 0,
            last_ad_timestamp DATETIME,
            domain TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Ad watch history
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ad_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            domain TEXT,
            ad_type TEXT,
            ad_duration INTEGER,
            compute_earned INTEGER,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Usage tracking
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usage_tracking (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            domain TEXT,
            service_type TEXT,
            compute_used INTEGER,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()

init_db()

# Pydantic models
class AdWatchRequest(BaseModel):
    user_id: str
    domain: str
    ad_type: str = "standard"
    ad_duration: int = 30  # seconds

class ComputeUsageRequest(BaseModel):
    user_id: str
    domain: str
    service_type: str
    compute_minutes: int

class UserBalance(BaseModel):
    user_id: str
    compute_minutes: int
    total_ads_watched: int
    last_ad_timestamp: Optional[datetime]
    domain: str

class FreeTimerConfig:
    """Configuration for free tier compute allocation"""
    
    # Ad duration to compute minutes mapping
    AD_COMPUTE_RATES = {
        "short": {"duration": 15, "compute": 5},      # 15-second ad = 5 minutes
        "standard": {"duration": 30, "compute": 10},   # 30-second ad = 10 minutes  
        "long": {"duration": 60, "compute": 25},       # 60-second ad = 25 minutes
        "premium": {"duration": 120, "compute": 60}    # 120-second ad = 60 minutes
    }
    
    # Daily limits
    MAX_ADS_PER_DAY = 20
    MAX_COMPUTE_PER_DAY = 480  # 8 hours
    
    # Minimum intervals between ads
    MIN_AD_INTERVAL_MINUTES = 3

class PersonalLogFreeTimer:
    """Free tier timer implementation"""
    
    def calculate_free_minutes(self, ad_type: str, ad_duration: int) -> int:
        """Calculate compute minutes earned from watching an ad"""
        if ad_type in FreeTimerConfig.AD_COMPUTE_RATES:
            return FreeTimerConfig.AD_COMPUTE_RATES[ad_type]["compute"]
        
        # Fallback calculation: 30-second ad = 10 minutes free compute
        return max(1, ad_duration // 3)
    
    def balance_check(self, user_id: str, domain: str) -> dict:
        """Check user's compute balance"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT compute_minutes, total_ads_watched FROM user_balance WHERE user_id = ? AND domain = ?",
            (user_id, domain)
        )
        result = cursor.fetchone()
        conn.close()
        
        if result:
            compute_minutes, total_ads = result
            if compute_minutes <= 0:
                return {
                    "status": "more_ads_required",
                    "compute_minutes": compute_minutes,
                    "total_ads_watched": total_ads,
                    "message": "Watch ads to earn more compute time"
                }
            return {
                "status": "features_available",
                "compute_minutes": compute_minutes,
                "total_ads_watched": total_ads,
                "message": f"{compute_minutes} minutes of compute available"
            }
        
        return {
            "status": "new_user",
            "compute_minutes": 0,
            "total_ads_watched": 0,
            "message": "Watch your first ad to start earning compute time"
        }

timer = PersonalLogFreeTimer()

def get_db():
    """Database dependency"""
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
    finally:
        conn.close()

@app.get("/")
async def root():
    return {
        "service": "ActiveLog Free Tier with Ads",
        "status": "operational",
        "supported_domains": [
            "PersonalLog", "MakerLog", "LucidDreamer", "BusinessLog",
            "Capitaine", "DeckBoss", "DMLog", "FishingLog", 
            "RealLog", "PlayerLog", "StudyLog"
        ]
    }

@app.post("/watch-ad")
async def watch_ad(request: AdWatchRequest, conn: sqlite3.Connection = Depends(get_db)):
    """Record ad watch and credit compute time"""
    try:
        cursor = conn.cursor()
        
        # Check if user exists
        cursor.execute(
            "SELECT compute_minutes, total_ads_watched, last_ad_timestamp FROM user_balance WHERE user_id = ? AND domain = ?",
            (request.user_id, request.domain)
        )
        result = cursor.fetchone()
        
        # Check ad interval limit
        if result and result[2]:
            last_ad = datetime.fromisoformat(result[2])
            if datetime.now() - last_ad < timedelta(minutes=FreeTimerConfig.MIN_AD_INTERVAL_MINUTES):
                raise HTTPException(
                    status_code=429, 
                    detail=f"Must wait {FreeTimerConfig.MIN_AD_INTERVAL_MINUTES} minutes between ads"
                )
        
        # Calculate compute minutes earned
        compute_earned = timer.calculate_free_minutes(request.ad_type, request.ad_duration)
        
        if result:
            # Update existing user
            new_compute = result[0] + compute_earned
            new_total_ads = result[1] + 1
            
            cursor.execute("""
                UPDATE user_balance 
                SET compute_minutes = ?, total_ads_watched = ?, last_ad_timestamp = ?
                WHERE user_id = ? AND domain = ?
            """, (new_compute, new_total_ads, datetime.now().isoformat(), request.user_id, request.domain))
        else:
            # Create new user
            cursor.execute("""
                INSERT INTO user_balance (user_id, compute_minutes, total_ads_watched, last_ad_timestamp, domain)
                VALUES (?, ?, 1, ?, ?)
            """, (request.user_id, compute_earned, datetime.now().isoformat(), request.domain))
        
        # Record ad watch history
        cursor.execute("""
            INSERT INTO ad_history (user_id, domain, ad_type, ad_duration, compute_earned)
            VALUES (?, ?, ?, ?, ?)
        """, (request.user_id, request.domain, request.ad_type, request.ad_duration, compute_earned))
        
        conn.commit()
        
        # Get updated balance
        balance_info = timer.balance_check(request.user_id, request.domain)
        
        logger.info(f"User {request.user_id} watched {request.ad_type} ad, earned {compute_earned} minutes")
        
        return {
            "success": True,
            "compute_earned": compute_earned,
            "ad_type": request.ad_type,
            "ad_duration": request.ad_duration,
            "balance": balance_info,
            "message": f"Earned {compute_earned} minutes of compute time!"
        }
        
    except Exception as e:
        logger.error(f"Error processing ad watch: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/use-compute")
async def use_compute(request: ComputeUsageRequest, conn: sqlite3.Connection = Depends(get_db)):
    """Deduct compute time from user balance"""
    try:
        cursor = conn.cursor()
        
        # Get current balance
        cursor.execute(
            "SELECT compute_minutes FROM user_balance WHERE user_id = ? AND domain = ?",
            (request.user_id, request.domain)
        )
        result = cursor.fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="User not found")
        
        current_balance = result[0]
        
        if current_balance < request.compute_minutes:
            return {
                "success": False,
                "error": "insufficient_compute",
                "current_balance": current_balance,
                "requested": request.compute_minutes,
                "message": "Not enough compute time. Watch ads to earn more!"
            }
        
        # Deduct compute time
        new_balance = current_balance - request.compute_minutes
        
        cursor.execute(
            "UPDATE user_balance SET compute_minutes = ? WHERE user_id = ? AND domain = ?",
            (new_balance, request.user_id, request.domain)
        )
        
        # Record usage
        cursor.execute("""
            INSERT INTO usage_tracking (user_id, domain, service_type, compute_used)
            VALUES (?, ?, ?, ?)
        """, (request.user_id, request.domain, request.service_type, request.compute_minutes))
        
        conn.commit()
        
        logger.info(f"User {request.user_id} used {request.compute_minutes} minutes, remaining: {new_balance}")
        
        return {
            "success": True,
            "compute_used": request.compute_minutes,
            "remaining_balance": new_balance,
            "service_type": request.service_type
        }
        
    except Exception as e:
        logger.error(f"Error processing compute usage: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/balance/{user_id}/{domain}")
async def get_balance(user_id: str, domain: str):
    """Get user's current compute balance"""
    return timer.balance_check(user_id, domain)

@app.get("/ad-rates")
async def get_ad_rates():
    """Get current ad rates and compute allocation"""
    return {
        "rates": FreeTimerConfig.AD_COMPUTE_RATES,
        "limits": {
            "max_ads_per_day": FreeTimerConfig.MAX_ADS_PER_DAY,
            "max_compute_per_day": FreeTimerConfig.MAX_COMPUTE_PER_DAY,
            "min_ad_interval_minutes": FreeTimerConfig.MIN_AD_INTERVAL_MINUTES
        }
    }

@app.get("/stats/{domain}")
async def get_domain_stats(domain: str, conn: sqlite3.Connection = Depends(get_db)):
    """Get statistics for a domain"""
    cursor = conn.cursor()
    
    # Total users
    cursor.execute("SELECT COUNT(*) FROM user_balance WHERE domain = ?", (domain,))
    total_users = cursor.fetchone()[0]
    
    # Total ads watched
    cursor.execute("SELECT SUM(total_ads_watched) FROM user_balance WHERE domain = ?", (domain,))
    total_ads = cursor.fetchone()[0] or 0
    
    # Total compute allocated
    cursor.execute("SELECT SUM(compute_earned) FROM ad_history WHERE domain = ?", (domain,))
    total_compute_allocated = cursor.fetchone()[0] or 0
    
    # Total compute used
    cursor.execute("SELECT SUM(compute_used) FROM usage_tracking WHERE domain = ?", (domain,))
    total_compute_used = cursor.fetchone()[0] or 0
    
    return {
        "domain": domain,
        "total_users": total_users,
        "total_ads_watched": total_ads,
        "total_compute_allocated": total_compute_allocated,
        "total_compute_used": total_compute_used,
        "compute_utilization": round((total_compute_used / max(total_compute_allocated, 1)) * 100, 2)
    }

# ML-Powered Ad Targeting Endpoints

@app.post("/ml/user-profile/update")
async def update_user_profile(user_id: str, domain: str, activity_data: Dict[str, Any]):
    """Update user profile with activity data for ML targeting"""
    try:
        ad_targeting_engine.update_user_profile(user_id, domain, activity_data)
        
        return {
            "success": True,
            "user_id": user_id,
            "domain": domain,
            "updated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Profile update error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/ml/ads/optimize")
async def optimize_ad_placement(
    user_id: str,
    context: Optional[Dict[str, Any]] = None,
    max_ads: int = 5
):
    """Get optimized ad placement using ML predictions"""
    try:
        if context is None:
            context = {
                "hour_of_day": datetime.now().hour,
                "day_of_week": datetime.now().weekday()
            }
        
        # Mock available ads (in production, this would come from ad server)
        available_ads = [
            {"id": "business_tools_001", "type": "business_tools", "title": "Pro Analytics Dashboard", "cpm": 2.50},
            {"id": "gaming_002", "type": "gaming", "title": "Epic Adventure Game", "cpm": 1.80},
            {"id": "education_003", "type": "education", "title": "Online Course Platform", "cpm": 3.20},
            {"id": "creative_software_004", "type": "creative_software", "title": "Design Software Suite", "cpm": 4.10},
            {"id": "outdoor_gear_005", "type": "outdoor_gear", "title": "Fishing Equipment", "cpm": 2.90},
            {"id": "productivity_006", "type": "productivity", "title": "Project Management Tool", "cpm": 3.50}
        ]
        
        # Get ML-optimized ad placement
        optimized_ads = ad_targeting_engine.optimize_ad_placement(user_id, available_ads, context)
        
        # Limit to requested number
        result_ads = optimized_ads[:max_ads]
        
        return {
            "user_id": user_id,
            "optimized_ads": result_ads,
            "total_available": len(available_ads),
            "returned": len(result_ads),
            "optimization_timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Ad optimization error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ml/ads/interaction")
async def record_ad_interaction(
    user_id: str,
    ad_id: str,
    interaction_type: str,
    value: float = 0.0
):
    """Record ad interaction for ML training"""
    try:
        ad_targeting_engine.record_ad_interaction(user_id, ad_id, interaction_type, value)
        
        return {
            "success": True,
            "user_id": user_id,
            "ad_id": ad_id,
            "interaction_type": interaction_type,
            "value": value,
            "recorded_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Interaction recording error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/ml/user/{user_id}/predictions")
async def get_user_ad_predictions(
    user_id: str,
    ad_type: str,
    context: Optional[Dict[str, Any]] = None
):
    """Get ML predictions for user ad engagement"""
    try:
        if context is None:
            context = {
                "hour_of_day": datetime.now().hour,
                "day_of_week": datetime.now().weekday()
            }
        
        predictions = ad_targeting_engine.predict_ad_engagement(user_id, ad_type, context)
        
        # Get user profile summary
        profile = ad_targeting_engine.user_profiles[user_id]
        profile_summary = {
            "value_score": profile['value_score'],
            "interests": list(profile['interests']),
            "recent_sessions": len([b for b in profile['behavior_patterns'] 
                                  if b['timestamp'] > datetime.now() - timedelta(days=7)]),
            "total_engagements": len(profile['engagement_history'])
        }
        
        return {
            "user_id": user_id,
            "ad_type": ad_type,
            "predictions": predictions,
            "profile_summary": profile_summary,
            "generated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/ml/revenue/analytics")
async def get_ml_revenue_analytics():
    """Get comprehensive ML-powered revenue analytics"""
    try:
        analytics = ad_targeting_engine.get_revenue_analytics()
        
        # Add ML-specific metrics
        ml_metrics = {
            "ml_models_loaded": len(ad_targeting_engine.ml_models),
            "user_profiles_active": len(ad_targeting_engine.user_profiles),
            "high_value_users_percentage": round(
                (analytics['high_value_users'] / max(analytics['active_users'], 1)) * 100, 2
            ),
            "avg_user_value_score": round(
                np.mean([p['value_score'] for p in ad_targeting_engine.user_profiles.values()]) 
                if ad_targeting_engine.user_profiles else 0, 3
            )
        }
        
        # Combine analytics
        complete_analytics = {**analytics, **ml_metrics}
        complete_analytics["generated_at"] = datetime.now().isoformat()
        
        return complete_analytics
        
    except Exception as e:
        logger.error(f"Analytics error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ml/models/retrain")
async def trigger_model_retraining(background_tasks: BackgroundTasks):
    """Manually trigger ML model retraining"""
    try:
        def retrain_task():
            ad_targeting_engine.retrain_models()
        
        background_tasks.add_task(retrain_task)
        
        return {
            "success": True,
            "message": "Model retraining initiated",
            "initiated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Retraining trigger error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/ml/models/status")
async def get_ml_models_status():
    """Get status of ML models"""
    try:
        model_status = {}
        
        for model_type, model in ad_targeting_engine.ml_models.items():
            # Get model info
            status = {
                "loaded": True,
                "type": type(model).__name__,
                "trained": hasattr(model, 'feature_importances_') or hasattr(model, 'coef_')
            }
            
            # Add feature importance if available
            if hasattr(model, 'feature_importances_'):
                status["feature_importances"] = model.feature_importances_.tolist()[:10]  # Top 10
            
            model_status[model_type] = status
        
        return {
            "models": model_status,
            "total_models": len(ad_targeting_engine.ml_models),
            "last_training_check": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Model status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/ml/performance/dashboard")
async def get_ml_performance_dashboard():
    """Get comprehensive ML performance dashboard"""
    try:
        # Get revenue analytics
        revenue_analytics = ad_targeting_engine.get_revenue_analytics()
        
        # Calculate performance metrics
        total_profiles = len(ad_targeting_engine.user_profiles)
        active_profiles = len([p for p in ad_targeting_engine.user_profiles.values() 
                              if p['behavior_patterns'] and 
                              p['behavior_patterns'][-1]['timestamp'] > datetime.now() - timedelta(days=7)])
        
        # Get ad performance summary
        ad_performance_summary = {}
        for ad_id, perf in ad_targeting_engine.ad_performance.items():
            ad_type = ad_id.split('_')[0] if '_' in ad_id else 'unknown'
            if ad_type not in ad_performance_summary:
                ad_performance_summary[ad_type] = {
                    "impressions": 0, "clicks": 0, "conversions": 0, "revenue": 0.0
                }
            
            ad_performance_summary[ad_type]["impressions"] += perf["impressions"]
            ad_performance_summary[ad_type]["clicks"] += perf["clicks"] 
            ad_performance_summary[ad_type]["conversions"] += perf["conversions"]
            ad_performance_summary[ad_type]["revenue"] += perf["revenue"]
        
        # Calculate CTR and conversion rates by ad type
        for ad_type, stats in ad_performance_summary.items():
            stats["ctr"] = round((stats["clicks"] / max(stats["impressions"], 1)) * 100, 2)
            stats["conversion_rate"] = round((stats["conversions"] / max(stats["clicks"], 1)) * 100, 2)
            stats["revenue_per_impression"] = round(stats["revenue"] / max(stats["impressions"], 1), 4)
        
        dashboard = {
            "overview": revenue_analytics,
            "user_engagement": {
                "total_profiles": total_profiles,
                "active_profiles": active_profiles,
                "engagement_rate": round((active_profiles / max(total_profiles, 1)) * 100, 2)
            },
            "ad_performance_by_type": ad_performance_summary,
            "ml_system_health": {
                "models_loaded": len(ad_targeting_engine.ml_models),
                "background_optimization": "running",
                "last_update": datetime.now().isoformat()
            },
            "generated_at": datetime.now().isoformat()
        }
        
        return dashboard
        
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)