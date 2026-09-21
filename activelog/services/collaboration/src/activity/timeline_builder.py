"""
Timeline builder for activity visualization
"""

import logging
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class TimelineBuilder:
    def __init__(self):
        self.activity_groupers = {
            "document": self._group_by_document,
            "user": self._group_by_user,
            "type": self._group_by_type,
            "time": self._group_by_time
        }
        
    async def initialize(self):
        """Initialize timeline builder"""
        logger.info("Initializing timeline builder")
        
    async def cleanup(self):
        """Cleanup resources"""
        logger.info("Cleaning up timeline builder")
        
    async def build_timeline(self, activities: List[Dict[str, Any]], 
                           days_back: int = 7,
                           group_by: str = "time") -> Dict[str, Any]:
        """Build structured timeline from activities"""
        try:
            if not activities:
                return self._empty_timeline(days_back)
            
            # Sort activities by timestamp
            sorted_activities = sorted(activities, key=lambda x: x["created_at"], reverse=True)
            
            # Group activities
            if group_by in self.activity_groupers:
                grouped = self.activity_groupers[group_by](sorted_activities)
            else:
                grouped = self._group_by_time(sorted_activities)
            
            # Build timeline structure
            timeline = {
                "period_days": days_back,
                "start_date": (datetime.now(timezone.utc) - timedelta(days=days_back)).isoformat(),
                "end_date": datetime.now(timezone.utc).isoformat(),
                "total_activities": len(activities),
                "group_by": group_by,
                "groups": grouped,
                "summary": self._build_summary(activities),
                "trends": self._analyze_trends(activities, days_back)
            }
            
            return timeline
            
        except Exception as e:
            logger.error(f"Failed to build timeline: {e}")
            return self._empty_timeline(days_back)
            
    def _group_by_time(self, activities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Group activities by time periods"""
        try:
            grouped = {
                "by_day": defaultdict(list),
                "by_hour": defaultdict(list),
                "recent": []
            }
            
            now = datetime.now(timezone.utc)
            today = now.date()
            current_hour = now.hour
            
            for activity in activities:
                activity_time = activity["created_at"]
                if isinstance(activity_time, str):
                    activity_time = datetime.fromisoformat(activity_time.replace('Z', '+00:00'))
                
                activity_date = activity_time.date()
                activity_hour = activity_time.hour
                
                # Group by day
                if activity_date == today:
                    day_key = "today"
                elif activity_date == today - timedelta(days=1):
                    day_key = "yesterday"
                else:
                    day_key = activity_date.isoformat()
                    
                grouped["by_day"][day_key].append(activity)
                
                # Group by hour (last 24 hours)
                if activity_time > now - timedelta(hours=24):
                    hour_key = f"{activity_date.isoformat()}T{activity_hour:02d}:00:00"
                    grouped["by_hour"][hour_key].append(activity)
                
                # Recent activities (last 2 hours)
                if activity_time > now - timedelta(hours=2):
                    grouped["recent"].append(activity)
            
            # Convert defaultdicts to regular dicts and sort
            grouped["by_day"] = dict(grouped["by_day"])
            grouped["by_hour"] = dict(grouped["by_hour"])
            
            return grouped
            
        except Exception as e:
            logger.error(f"Failed to group by time: {e}")
            return {"by_day": {}, "by_hour": {}, "recent": []}
            
    def _group_by_document(self, activities: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group activities by document"""
        try:
            grouped = defaultdict(list)
            
            for activity in activities:
                document_id = activity.get("document_id")
                if document_id:
                    key = f"{document_id}:{activity.get('document_name', 'Unknown Document')}"
                else:
                    key = "workspace:Workspace Level"
                    
                grouped[key].append(activity)
            
            return dict(grouped)
            
        except Exception as e:
            logger.error(f"Failed to group by document: {e}")
            return {}
            
    def _group_by_user(self, activities: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group activities by user/actor"""
        try:
            grouped = defaultdict(list)
            
            for activity in activities:
                actor_id = activity.get("actor_id", "unknown")
                grouped[actor_id].append(activity)
            
            return dict(grouped)
            
        except Exception as e:
            logger.error(f"Failed to group by user: {e}")
            return {}
            
    def _group_by_type(self, activities: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group activities by activity type"""
        try:
            grouped = defaultdict(list)
            
            for activity in activities:
                activity_type = activity.get("activity_type", "unknown")
                grouped[activity_type].append(activity)
            
            return dict(grouped)
            
        except Exception as e:
            logger.error(f"Failed to group by type: {e}")
            return {}
            
    def _build_summary(self, activities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Build summary statistics for activities"""
        try:
            if not activities:
                return {}
            
            # Count by type
            type_counts = defaultdict(int)
            # Count by user
            user_counts = defaultdict(int)
            # Count by document
            document_counts = defaultdict(int)
            
            unique_users = set()
            unique_documents = set()
            
            for activity in activities:
                activity_type = activity.get("activity_type", "unknown")
                actor_id = activity.get("actor_id")
                document_id = activity.get("document_id")
                
                type_counts[activity_type] += 1
                
                if actor_id:
                    user_counts[actor_id] += 1
                    unique_users.add(actor_id)
                
                if document_id:
                    document_counts[document_id] += 1
                    unique_documents.add(document_id)
            
            # Get top items
            top_types = sorted(type_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            top_users = sorted(user_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            top_documents = sorted(document_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            
            return {
                "total_activities": len(activities),
                "unique_users": len(unique_users),
                "unique_documents": len(unique_documents),
                "activity_types": dict(type_counts),
                "top_activity_types": top_types,
                "top_users": top_users,
                "top_documents": top_documents,
                "first_activity": min(activities, key=lambda x: x["created_at"])["created_at"],
                "latest_activity": max(activities, key=lambda x: x["created_at"])["created_at"]
            }
            
        except Exception as e:
            logger.error(f"Failed to build summary: {e}")
            return {}
            
    def _analyze_trends(self, activities: List[Dict[str, Any]], days_back: int) -> Dict[str, Any]:
        """Analyze activity trends over time"""
        try:
            if not activities or days_back < 2:
                return {}
            
            # Group activities by day
            daily_counts = defaultdict(int)
            hourly_counts = defaultdict(int)
            
            for activity in activities:
                activity_time = activity["created_at"]
                if isinstance(activity_time, str):
                    activity_time = datetime.fromisoformat(activity_time.replace('Z', '+00:00'))
                
                # Daily trend
                day_key = activity_time.date().isoformat()
                daily_counts[day_key] += 1
                
                # Hourly trend (last 24 hours)
                if activity_time > datetime.now(timezone.utc) - timedelta(hours=24):
                    hour_key = activity_time.hour
                    hourly_counts[hour_key] += 1
            
            # Calculate trend direction
            daily_values = list(daily_counts.values())
            if len(daily_values) >= 2:
                recent_avg = sum(daily_values[-3:]) / min(3, len(daily_values[-3:]))
                older_avg = sum(daily_values[:-3]) / max(1, len(daily_values[:-3])) if len(daily_values) > 3 else recent_avg
                
                if recent_avg > older_avg * 1.2:
                    trend_direction = "increasing"
                elif recent_avg < older_avg * 0.8:
                    trend_direction = "decreasing"
                else:
                    trend_direction = "stable"
            else:
                trend_direction = "insufficient_data"
            
            # Find peak activity hours
            if hourly_counts:
                peak_hour = max(hourly_counts.items(), key=lambda x: x[1])
                quiet_hour = min(hourly_counts.items(), key=lambda x: x[1])
            else:
                peak_hour = (0, 0)
                quiet_hour = (0, 0)
            
            return {
                "trend_direction": trend_direction,
                "daily_activity": dict(daily_counts),
                "hourly_activity": dict(hourly_counts),
                "peak_hour": {"hour": peak_hour[0], "count": peak_hour[1]},
                "quiet_hour": {"hour": quiet_hour[0], "count": quiet_hour[1]},
                "total_days_with_activity": len(daily_counts),
                "average_daily_activity": sum(daily_counts.values()) / max(1, len(daily_counts)),
                "most_active_day": max(daily_counts.items(), key=lambda x: x[1]) if daily_counts else None,
                "least_active_day": min(daily_counts.items(), key=lambda x: x[1]) if daily_counts else None
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze trends: {e}")
            return {}
            
    def _empty_timeline(self, days_back: int) -> Dict[str, Any]:
        """Return empty timeline structure"""
        return {
            "period_days": days_back,
            "start_date": (datetime.now(timezone.utc) - timedelta(days=days_back)).isoformat(),
            "end_date": datetime.now(timezone.utc).isoformat(),
            "total_activities": 0,
            "group_by": "time",
            "groups": {"by_day": {}, "by_hour": {}, "recent": []},
            "summary": {},
            "trends": {}
        }
        
    async def build_activity_heatmap(self, activities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Build activity heatmap data for visualization"""
        try:
            heatmap = {
                "days_of_week": defaultdict(int),  # 0 = Monday, 6 = Sunday
                "hours_of_day": defaultdict(int),  # 0-23
                "daily_grid": defaultdict(lambda: defaultdict(int))  # [date][hour] = count
            }
            
            for activity in activities:
                activity_time = activity["created_at"]
                if isinstance(activity_time, str):
                    activity_time = datetime.fromisoformat(activity_time.replace('Z', '+00:00'))
                
                day_of_week = activity_time.weekday()  # 0 = Monday
                hour_of_day = activity_time.hour
                date_key = activity_time.date().isoformat()
                
                heatmap["days_of_week"][day_of_week] += 1
                heatmap["hours_of_day"][hour_of_day] += 1
                heatmap["daily_grid"][date_key][hour_of_day] += 1
            
            # Convert to regular dicts and add metadata
            return {
                "days_of_week": dict(heatmap["days_of_week"]),
                "hours_of_day": dict(heatmap["hours_of_day"]),
                "daily_grid": {date: dict(hours) for date, hours in heatmap["daily_grid"].items()},
                "day_labels": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
                "total_activities": len(activities)
            }
            
        except Exception as e:
            logger.error(f"Failed to build activity heatmap: {e}")
            return {"days_of_week": {}, "hours_of_day": {}, "daily_grid": {}, "day_labels": [], "total_activities": 0}
            
    async def build_collaboration_network(self, activities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Build collaboration network from activities"""
        try:
            # Track user interactions
            user_interactions = defaultdict(lambda: defaultdict(int))
            user_activity_counts = defaultdict(int)
            document_collaborators = defaultdict(set)
            
            for activity in activities:
                actor_id = activity.get("actor_id")
                document_id = activity.get("document_id")
                
                if actor_id:
                    user_activity_counts[actor_id] += 1
                    
                    if document_id:
                        document_collaborators[document_id].add(actor_id)
            
            # Build collaboration edges based on shared document work
            collaboration_edges = []
            for document_id, collaborators in document_collaborators.items():
                collaborator_list = list(collaborators)
                for i, user1 in enumerate(collaborator_list):
                    for user2 in collaborator_list[i+1:]:
                        # Count shared activities
                        shared_activities = sum(1 for activity in activities 
                                              if activity.get("document_id") == document_id and
                                              activity.get("actor_id") in [user1, user2])
                        
                        if shared_activities > 0:
                            collaboration_edges.append({
                                "from": user1,
                                "to": user2,
                                "weight": shared_activities,
                                "shared_document": document_id
                            })
            
            # Build network structure
            network = {
                "nodes": [
                    {
                        "id": user_id,
                        "activity_count": count,
                        "document_count": len([doc for doc, users in document_collaborators.items() if user_id in users])
                    }
                    for user_id, count in user_activity_counts.items()
                ],
                "edges": collaboration_edges,
                "statistics": {
                    "total_users": len(user_activity_counts),
                    "total_collaborations": len(collaboration_edges),
                    "total_documents": len(document_collaborators),
                    "most_active_user": max(user_activity_counts.items(), key=lambda x: x[1]) if user_activity_counts else None,
                    "most_collaborative_document": max(document_collaborators.items(), key=lambda x: len(x[1])) if document_collaborators else None
                }
            }
            
            return network
            
        except Exception as e:
            logger.error(f"Failed to build collaboration network: {e}")
            return {"nodes": [], "edges": [], "statistics": {}}