"""
Usage Tracking System for Beta Pricing Service
Track and analyze user behavior to validate pricing strategies
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from decimal import Decimal
import logging
import sqlite3
import json
import asyncio
from dataclasses import dataclass
from collections import defaultdict
import statistics

logger = logging.getLogger(__name__)

@dataclass
class UsagePattern:
    feature: str
    usage_count: int
    total_duration_ms: int
    avg_duration_ms: float
    success_rate: float
    peak_usage_hours: List[int]

@dataclass
class UserSegment:
    segment_id: str
    criteria: Dict[str, Any]
    user_count: int
    avg_usage: Dict[str, float]
    conversion_rate: float
    revenue_potential: Decimal

class UsageTrackingSystem:
    def __init__(self):
        self.db_path = "/home/activeloguser/activelog/services/beta-pricing/data/beta_pricing.db"
        self.analytics_cache = {}
        self.cache_ttl = timedelta(minutes=15)
        self.processing_queue = asyncio.Queue()
    
    async def record_usage_event(self, event) -> Dict[str, Any]:
        """Record a usage event for analysis"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Store the event
            cursor.execute('''
                INSERT INTO usage_events 
                (id, user_id, event_type, feature_name, duration_ms, api_endpoint,
                 success, session_id, ip_address, user_agent, timestamp, data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                event.id, event.user_id, event.event_type, event.feature_name,
                event.duration_ms, event.api_endpoint, event.success,
                event.session_id, event.ip_address, event.user_agent,
                event.timestamp.isoformat(), event.model_dump_json()
            ))
            
            # Update user usage counters
            if event.event_type == "api_call":
                cursor.execute('''
                    UPDATE beta_users 
                    SET total_api_calls = total_api_calls + 1,
                        monthly_api_calls = monthly_api_calls + 1,
                        updated_at = ?
                    WHERE id = ?
                ''', (datetime.now().isoformat(), event.user_id))
            
            conn.commit()
            conn.close()
            
            # Add to processing queue for real-time analytics
            await self.processing_queue.put(event)
            
            logger.info(f"Recorded usage event {event.id} for user {event.user_id}")
            
            return {
                "event_id": event.id,
                "recorded": True,
                "timestamp": event.timestamp.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error recording usage event: {str(e)}")
            return {
                "event_id": event.id,
                "recorded": False,
                "error": str(e)
            }
    
    async def get_user_analytics(self, user_id: str, period: str = "month") -> Dict[str, Any]:
        """Get comprehensive usage analytics for a user"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Calculate date range
            end_date = datetime.now()
            if period == "week":
                start_date = end_date - timedelta(days=7)
            elif period == "month":
                start_date = end_date - timedelta(days=30)
            elif period == "quarter":
                start_date = end_date - timedelta(days=90)
            else:
                start_date = end_date - timedelta(days=30)
            
            # Get user tier info
            cursor.execute('''
                SELECT tier, experiment_group, created_at
                FROM beta_users WHERE id = ?
            ''', (user_id,))
            
            user_info = cursor.fetchone()
            if not user_info:
                return {"error": f"User {user_id} not found"}
            
            tier, experiment_group, user_created_at = user_info
            
            # Get usage events for period
            cursor.execute('''
                SELECT event_type, feature_name, duration_ms, success, 
                       timestamp, api_endpoint
                FROM usage_events 
                WHERE user_id = ? AND timestamp >= ? AND timestamp <= ?
                ORDER BY timestamp DESC
            ''', (user_id, start_date.isoformat(), end_date.isoformat()))
            
            events = cursor.fetchall()
            conn.close()
            
            # Analyze usage patterns
            patterns = self._analyze_usage_patterns(events)
            
            # Calculate engagement metrics
            engagement_metrics = self._calculate_engagement_metrics(events, period)
            
            # Feature adoption analysis
            feature_adoption = self._analyze_feature_adoption(events)
            
            # Session analytics
            session_analytics = self._analyze_sessions(events)
            
            return {
                "user_id": user_id,
                "period": period,
                "tier": tier,
                "experiment_group": experiment_group,
                "member_since": user_created_at,
                "total_events": len(events),
                "usage_patterns": patterns,
                "engagement_metrics": engagement_metrics,
                "feature_adoption": feature_adoption,
                "session_analytics": session_analytics,
                "generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting user analytics: {str(e)}")
            return {"error": str(e)}
    
    def _analyze_usage_patterns(self, events: List[tuple]) -> Dict[str, UsagePattern]:
        """Analyze usage patterns from events"""
        patterns = {}
        
        # Group events by feature
        feature_events = defaultdict(list)
        
        for event in events:
            event_type, feature_name, duration_ms, success, timestamp, api_endpoint = event
            
            key = feature_name or event_type
            feature_events[key].append({
                'duration_ms': duration_ms or 0,
                'success': success,
                'timestamp': datetime.fromisoformat(timestamp)
            })
        
        # Calculate patterns for each feature
        for feature, feature_event_list in feature_events.items():
            durations = [e['duration_ms'] for e in feature_event_list]
            successes = [e['success'] for e in feature_event_list]
            hours = [e['timestamp'].hour for e in feature_event_list]
            
            # Find peak usage hours
            hour_counts = defaultdict(int)
            for hour in hours:
                hour_counts[hour] += 1
            
            peak_hours = sorted(hour_counts.items(), key=lambda x: x[1], reverse=True)[:3]
            peak_hours = [hour for hour, count in peak_hours]
            
            patterns[feature] = UsagePattern(
                feature=feature,
                usage_count=len(feature_event_list),
                total_duration_ms=sum(durations),
                avg_duration_ms=statistics.mean(durations) if durations else 0,
                success_rate=sum(successes) / len(successes) if successes else 0,
                peak_usage_hours=peak_hours
            )
        
        return {k: {
            'feature': v.feature,
            'usage_count': v.usage_count,
            'total_duration_ms': v.total_duration_ms,
            'avg_duration_ms': v.avg_duration_ms,
            'success_rate': v.success_rate,
            'peak_usage_hours': v.peak_usage_hours
        } for k, v in patterns.items()}
    
    def _calculate_engagement_metrics(self, events: List[tuple], period: str) -> Dict[str, Any]:
        """Calculate user engagement metrics"""
        if not events:
            return {
                "daily_active_sessions": 0,
                "avg_session_duration": 0,
                "feature_diversity": 0,
                "engagement_score": 0
            }
        
        # Calculate daily active sessions
        daily_sessions = set()
        session_durations = []
        features_used = set()
        
        for event in events:
            event_type, feature_name, duration_ms, success, timestamp, api_endpoint = event
            
            date = datetime.fromisoformat(timestamp).date()
            daily_sessions.add(date)
            
            if duration_ms:
                session_durations.append(duration_ms)
            
            if feature_name:
                features_used.add(feature_name)
        
        avg_duration = statistics.mean(session_durations) if session_durations else 0
        
        # Calculate engagement score (0-100)
        days_in_period = 7 if period == "week" else 30 if period == "month" else 90
        engagement_score = min(100, (len(daily_sessions) / days_in_period) * 100)
        
        return {
            "daily_active_sessions": len(daily_sessions),
            "avg_session_duration": avg_duration,
            "feature_diversity": len(features_used),
            "engagement_score": engagement_score
        }
    
    def _analyze_feature_adoption(self, events: List[tuple]) -> Dict[str, Any]:
        """Analyze which features users are adopting"""
        feature_usage = defaultdict(int)
        feature_first_use = {}
        
        for event in events:
            event_type, feature_name, duration_ms, success, timestamp, api_endpoint = event
            
            if feature_name:
                feature_usage[feature_name] += 1
                
                if feature_name not in feature_first_use:
                    feature_first_use[feature_name] = timestamp
        
        # Sort features by usage
        sorted_features = sorted(feature_usage.items(), key=lambda x: x[1], reverse=True)
        
        return {
            "most_used_features": sorted_features[:5],
            "total_features_used": len(feature_usage),
            "feature_adoption_timeline": feature_first_use
        }
    
    def _analyze_sessions(self, events: List[tuple]) -> Dict[str, Any]:
        """Analyze user sessions"""
        if not events:
            return {"total_sessions": 0, "avg_events_per_session": 0}
        
        # Group events by session (assuming events within 30 minutes are same session)
        sessions = []
        current_session = []
        last_timestamp = None
        
        for event in events:
            event_type, feature_name, duration_ms, success, timestamp, api_endpoint = event
            event_time = datetime.fromisoformat(timestamp)
            
            if last_timestamp and (event_time - last_timestamp).total_seconds() > 1800:  # 30 minutes
                if current_session:
                    sessions.append(current_session)
                current_session = [event]
            else:
                current_session.append(event)
            
            last_timestamp = event_time
        
        if current_session:
            sessions.append(current_session)
        
        return {
            "total_sessions": len(sessions),
            "avg_events_per_session": len(events) / len(sessions) if sessions else 0,
            "session_lengths": [len(session) for session in sessions]
        }
    
    async def get_platform_usage(self, period: str = "month") -> Dict[str, Any]:
        """Get platform-wide usage analytics"""
        try:
            cache_key = f"platform_usage_{period}"
            
            # Check cache
            if cache_key in self.analytics_cache:
                cached_data, timestamp = self.analytics_cache[cache_key]
                if datetime.now() - timestamp < self.cache_ttl:
                    return cached_data
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Calculate date range
            end_date = datetime.now()
            if period == "week":
                start_date = end_date - timedelta(days=7)
            elif period == "month":
                start_date = end_date - timedelta(days=30)
            elif period == "quarter":
                start_date = end_date - timedelta(days=90)
            else:
                start_date = end_date - timedelta(days=30)
            
            # Get usage statistics
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_events,
                    COUNT(DISTINCT user_id) as active_users,
                    AVG(duration_ms) as avg_duration,
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as success_rate
                FROM usage_events 
                WHERE timestamp >= ? AND timestamp <= ?
            ''', (start_date.isoformat(), end_date.isoformat()))
            
            overall_stats = cursor.fetchone()
            
            # Get feature usage breakdown
            cursor.execute('''
                SELECT feature_name, COUNT(*) as usage_count
                FROM usage_events 
                WHERE timestamp >= ? AND timestamp <= ? AND feature_name IS NOT NULL
                GROUP BY feature_name
                ORDER BY usage_count DESC
                LIMIT 10
            ''', (start_date.isoformat(), end_date.isoformat()))
            
            feature_usage = cursor.fetchall()
            
            # Get tier usage distribution
            cursor.execute('''
                SELECT b.tier, COUNT(DISTINCT e.user_id) as active_users, COUNT(e.id) as total_events
                FROM usage_events e
                JOIN beta_users b ON e.user_id = b.id
                WHERE e.timestamp >= ? AND e.timestamp <= ?
                GROUP BY b.tier
            ''', (start_date.isoformat(), end_date.isoformat()))
            
            tier_usage = cursor.fetchall()
            
            # Get hourly usage pattern
            cursor.execute('''
                SELECT 
                    CAST(strftime('%H', timestamp) as INTEGER) as hour,
                    COUNT(*) as events
                FROM usage_events 
                WHERE timestamp >= ? AND timestamp <= ?
                GROUP BY hour
                ORDER BY hour
            ''', (start_date.isoformat(), end_date.isoformat()))
            
            hourly_pattern = cursor.fetchall()
            
            conn.close()
            
            result = {
                "period": period,
                "date_range": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat()
                },
                "overall_stats": {
                    "total_events": overall_stats[0] or 0,
                    "active_users": overall_stats[1] or 0,
                    "avg_duration_ms": overall_stats[2] or 0,
                    "success_rate": overall_stats[3] or 0
                },
                "feature_usage": [
                    {"feature": feature, "usage_count": count} 
                    for feature, count in feature_usage
                ],
                "tier_distribution": [
                    {"tier": tier, "active_users": users, "total_events": events}
                    for tier, users, events in tier_usage
                ],
                "hourly_pattern": [
                    {"hour": hour, "events": events}
                    for hour, events in hourly_pattern
                ],
                "generated_at": datetime.now().isoformat()
            }
            
            # Cache the result
            self.analytics_cache[cache_key] = (result, datetime.now())
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting platform usage: {str(e)}")
            return {"error": str(e)}
    
    async def identify_user_segments(self) -> Dict[str, List[UserSegment]]:
        """Identify user segments based on usage patterns"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get user usage statistics
            cursor.execute('''
                SELECT 
                    b.id, b.tier, b.experiment_group, b.has_converted,
                    COUNT(e.id) as total_events,
                    COUNT(DISTINCT e.feature_name) as features_used,
                    AVG(e.duration_ms) as avg_duration,
                    MAX(e.timestamp) as last_activity
                FROM beta_users b
                LEFT JOIN usage_events e ON b.id = e.user_id
                WHERE e.timestamp >= date('now', '-30 days')
                GROUP BY b.id
            ''')
            
            users = cursor.fetchall()
            conn.close()
            
            segments = {
                "usage_based": [],
                "engagement_based": [],
                "conversion_potential": []
            }
            
            # Usage-based segmentation
            usage_segments = self._segment_by_usage(users)
            segments["usage_based"] = usage_segments
            
            # Engagement-based segmentation
            engagement_segments = self._segment_by_engagement(users)
            segments["engagement_based"] = engagement_segments
            
            # Conversion potential segmentation
            conversion_segments = self._segment_by_conversion_potential(users)
            segments["conversion_potential"] = conversion_segments
            
            return segments
            
        except Exception as e:
            logger.error(f"Error identifying user segments: {str(e)}")
            return {"error": str(e)}
    
    def _segment_by_usage(self, users: List[tuple]) -> List[Dict[str, Any]]:
        """Segment users by usage intensity"""
        if not users:
            return []
        
        # Calculate usage quartiles
        event_counts = [user[4] for user in users if user[4]]
        if not event_counts:
            return []
        
        q1 = statistics.quantiles(event_counts, n=4)[0]
        q3 = statistics.quantiles(event_counts, n=4)[2]
        
        segments = {
            "power_users": [],
            "regular_users": [],
            "light_users": [],
            "inactive_users": []
        }
        
        for user in users:
            user_id, tier, experiment_group, has_converted, total_events, features_used, avg_duration, last_activity = user
            
            if total_events >= q3:
                segments["power_users"].append(user)
            elif total_events >= q1:
                segments["regular_users"].append(user)
            elif total_events > 0:
                segments["light_users"].append(user)
            else:
                segments["inactive_users"].append(user)
        
        result = []
        for segment_name, segment_users in segments.items():
            if segment_users:
                avg_events = statistics.mean([u[4] for u in segment_users])
                conversion_rate = sum([u[3] for u in segment_users]) / len(segment_users)
                
                result.append({
                    "segment_id": segment_name,
                    "criteria": {"usage_level": segment_name},
                    "user_count": len(segment_users),
                    "avg_usage": {"events_per_month": avg_events},
                    "conversion_rate": conversion_rate,
                    "revenue_potential": Decimal(str(conversion_rate * len(segment_users) * 50))  # Estimated
                })
        
        return result
    
    def _segment_by_engagement(self, users: List[tuple]) -> List[Dict[str, Any]]:
        """Segment users by engagement level"""
        if not users:
            return []
        
        segments = {
            "highly_engaged": [],
            "moderately_engaged": [],
            "low_engagement": []
        }
        
        for user in users:
            user_id, tier, experiment_group, has_converted, total_events, features_used, avg_duration, last_activity = user
            
            # Calculate engagement score based on multiple factors
            event_score = min(1.0, total_events / 100) if total_events else 0
            feature_score = min(1.0, features_used / 10) if features_used else 0
            duration_score = min(1.0, avg_duration / 60000) if avg_duration else 0  # Normalize to minutes
            
            engagement_score = (event_score + feature_score + duration_score) / 3
            
            if engagement_score >= 0.7:
                segments["highly_engaged"].append(user)
            elif engagement_score >= 0.3:
                segments["moderately_engaged"].append(user)
            else:
                segments["low_engagement"].append(user)
        
        result = []
        for segment_name, segment_users in segments.items():
            if segment_users:
                conversion_rate = sum([u[3] for u in segment_users]) / len(segment_users)
                
                result.append({
                    "segment_id": segment_name,
                    "criteria": {"engagement_level": segment_name},
                    "user_count": len(segment_users),
                    "avg_usage": {"engagement_score": segment_name},
                    "conversion_rate": conversion_rate,
                    "revenue_potential": Decimal(str(conversion_rate * len(segment_users) * 75))
                })
        
        return result
    
    def _segment_by_conversion_potential(self, users: List[tuple]) -> List[Dict[str, Any]]:
        """Segment users by conversion potential"""
        if not users:
            return []
        
        segments = {
            "high_potential": [],
            "medium_potential": [],
            "low_potential": []
        }
        
        for user in users:
            user_id, tier, experiment_group, has_converted, total_events, features_used, avg_duration, last_activity = user
            
            if has_converted:
                continue  # Skip already converted users
            
            # Score based on usage and engagement indicators
            usage_score = min(1.0, total_events / 50) if total_events else 0
            feature_score = min(1.0, features_used / 5) if features_used else 0
            
            # Recent activity bonus
            if last_activity:
                days_since_activity = (datetime.now() - datetime.fromisoformat(last_activity)).days
                recency_score = max(0, 1 - (days_since_activity / 30))
            else:
                recency_score = 0
            
            potential_score = (usage_score + feature_score + recency_score) / 3
            
            if potential_score >= 0.6:
                segments["high_potential"].append(user)
            elif potential_score >= 0.3:
                segments["medium_potential"].append(user)
            else:
                segments["low_potential"].append(user)
        
        result = []
        for segment_name, segment_users in segments.items():
            if segment_users:
                # Estimated conversion rates based on potential
                estimated_conversion = {
                    "high_potential": 0.25,
                    "medium_potential": 0.10,
                    "low_potential": 0.03
                }[segment_name]
                
                result.append({
                    "segment_id": segment_name,
                    "criteria": {"conversion_potential": segment_name},
                    "user_count": len(segment_users),
                    "avg_usage": {"potential_score": segment_name},
                    "conversion_rate": estimated_conversion,
                    "revenue_potential": Decimal(str(estimated_conversion * len(segment_users) * 100))
                })
        
        return result
    
    async def start_analytics_processing(self):
        """Start background analytics processing"""
        logger.info("Starting usage analytics processing...")
        
        while True:
            try:
                # Process events from queue
                if not self.processing_queue.empty():
                    event = await asyncio.wait_for(self.processing_queue.get(), timeout=1.0)
                    await self._process_real_time_event(event)
                
                # Sleep to prevent high CPU usage
                await asyncio.sleep(1)
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error in analytics processing: {str(e)}")
                await asyncio.sleep(5)
    
    async def _process_real_time_event(self, event):
        """Process event for real-time analytics"""
        try:
            # Update real-time metrics
            # This could include updating caches, triggering alerts, etc.
            pass
            
        except Exception as e:
            logger.error(f"Error processing real-time event: {str(e)}")

# Global instance
usage_tracking_system = UsageTrackingSystem()