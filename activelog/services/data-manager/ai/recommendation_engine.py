#!/usr/bin/env python3
"""
AI Recommendation Engine for ActiveLog Data Management
Personalized recommendations for data organization, actions, and insights
"""

import asyncio
import json
import logging
import os
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Union, Tuple
from collections import defaultdict, Counter
from pathlib import Path
import numpy as np
from enum import Enum
import statistics

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RecommendationType(Enum):
    """Types of recommendations that can be generated"""
    ORGANIZATION = "organization"
    CLEANUP = "cleanup"
    PRODUCTIVITY = "productivity"
    STORAGE = "storage"
    SECURITY = "security"
    WORKFLOW = "workflow"
    INSIGHT = "insight"
    ACTION = "action"

class RecommendationPriority(Enum):
    """Priority levels for recommendations"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    URGENT = 4

class RecommendationCategory(Enum):
    """Categories for organizing recommendations"""
    DATA_ORGANIZATION = "data_organization"
    PERFORMANCE_OPTIMIZATION = "performance_optimization"
    USER_EXPERIENCE = "user_experience"
    DATA_QUALITY = "data_quality"
    AUTOMATION = "automation"

@dataclass
class UserPreference:
    """User preference for personalization"""
    user_id: str
    preference_type: str
    preference_value: Any
    confidence: float
    learned_from: str  # e.g., "user_action", "pattern_analysis", "explicit_setting"
    created_at: datetime
    updated_at: datetime

@dataclass
class UserBehaviorPattern:
    """Detected user behavior pattern"""
    pattern_id: str
    user_id: str
    pattern_type: str
    description: str
    frequency: float
    confidence: float
    data: Dict[str, Any]
    detected_at: datetime

@dataclass
class Recommendation:
    """A personalized recommendation"""
    recommendation_id: str
    user_id: str
    recommendation_type: RecommendationType
    category: RecommendationCategory
    title: str
    description: str
    priority: RecommendationPriority
    confidence: float
    personalization_factors: List[str]
    action_items: List[Dict[str, Any]]
    expected_benefit: str
    implementation_effort: str  # "low", "medium", "high"
    data: Dict[str, Any]
    created_at: datetime
    expires_at: Optional[datetime] = None
    completed: bool = False
    dismissed: bool = False

class UserProfiler:
    """Analyzes user behavior to build comprehensive profiles"""
    
    def __init__(self):
        self.behavior_patterns = {}
        self.user_preferences = {}
    
    async def analyze_user_behavior(self, user_id: str, data_items: List[Dict[str, Any]], 
                                  activity_history: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Analyze user behavior patterns"""
        profile = {
            "user_id": user_id,
            "content_preferences": await self._analyze_content_preferences(data_items),
            "organization_patterns": await self._analyze_organization_patterns(data_items),
            "activity_patterns": await self._analyze_activity_patterns(data_items, activity_history or []),
            "tool_usage": await self._analyze_tool_usage(activity_history or []),
            "data_quality_habits": await self._analyze_data_quality_habits(data_items),
            "storage_behavior": await self._analyze_storage_behavior(data_items)
        }
        
        return profile
    
    async def _analyze_content_preferences(self, data_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze what types of content the user works with most"""
        content_types = Counter(item.get('data_type', 'unknown') for item in data_items)
        sources = Counter(item.get('source', 'unknown') for item in data_items)
        
        # Analyze file sizes to determine if user prefers large/small files
        sizes = [item.get('size_bytes', 0) for item in data_items if item.get('size_bytes')]
        avg_size = statistics.mean(sizes) if sizes else 0
        
        # Analyze tags and categories
        all_tags = []
        categories = Counter()
        
        for item in data_items:
            tags = item.get('tags', [])
            if tags:
                all_tags.extend(tags)
            
            category = item.get('category')
            if category:
                categories[category] += 1
        
        tag_preferences = Counter(all_tags)
        
        return {
            "primary_content_types": dict(content_types.most_common(5)),
            "preferred_sources": dict(sources.most_common(3)),
            "average_file_size": avg_size,
            "file_size_preference": "large" if avg_size > 10*1024*1024 else "small",
            "preferred_tags": dict(tag_preferences.most_common(10)),
            "preferred_categories": dict(categories.most_common(5))
        }
    
    async def _analyze_organization_patterns(self, data_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze how the user organizes their data"""
        # Analyze folder/directory preferences (mock implementation)
        folder_patterns = defaultdict(int)
        
        for item in data_items:
            # Extract folder patterns from file paths or categories
            category = item.get('category', 'uncategorized')
            folder_patterns[category] += 1
        
        # Analyze naming conventions
        naming_patterns = []
        for item in data_items:
            filename = item.get('metadata', {}).get('filename', '')
            if filename:
                # Simple pattern detection
                if '_' in filename:
                    naming_patterns.append('underscore_separation')
                elif '-' in filename:
                    naming_patterns.append('dash_separation')
                elif filename.islower():
                    naming_patterns.append('lowercase_preferred')
                elif filename.isupper():
                    naming_patterns.append('uppercase_preferred')
        
        naming_preferences = Counter(naming_patterns)
        
        return {
            "folder_organization": dict(folder_patterns),
            "naming_conventions": dict(naming_preferences.most_common(3)),
            "organization_style": "structured" if len(folder_patterns) > 5 else "simple",
            "categorization_rate": len([item for item in data_items if item.get('category')]) / len(data_items) if data_items else 0
        }
    
    async def _analyze_activity_patterns(self, data_items: List[Dict[str, Any]], 
                                       activity_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze user activity patterns"""
        # Time-based activity analysis
        hourly_activity = defaultdict(int)
        daily_activity = defaultdict(int)
        
        for item in data_items:
            created_at = item.get('created_at')
            if created_at:
                if isinstance(created_at, str):
                    dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                else:
                    dt = created_at
                
                hourly_activity[dt.hour] += 1
                daily_activity[dt.strftime('%A')] += 1
        
        # Find peak activity times
        peak_hour = max(hourly_activity.items(), key=lambda x: x[1])[0] if hourly_activity else None
        peak_day = max(daily_activity.items(), key=lambda x: x[1])[0] if daily_activity else None
        
        # Analyze batch vs. individual operations
        batch_operations = 0
        individual_operations = 0
        
        # Group activities by day and count
        daily_counts = defaultdict(int)
        for item in data_items:
            created_at = item.get('created_at')
            if created_at:
                if isinstance(created_at, str):
                    dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                else:
                    dt = created_at
                daily_counts[dt.date()] += 1
        
        for count in daily_counts.values():
            if count > 10:  # More than 10 items in a day suggests batch operation
                batch_operations += 1
            else:
                individual_operations += 1
        
        work_style = "batch_processor" if batch_operations > individual_operations else "incremental_processor"
        
        return {
            "peak_activity_hour": peak_hour,
            "peak_activity_day": peak_day,
            "work_style": work_style,
            "activity_distribution": {
                "hourly": dict(hourly_activity),
                "daily": dict(daily_activity)
            },
            "activity_frequency": len(data_items) / 30 if data_items else 0  # Items per day (assuming 30-day period)
        }
    
    async def _analyze_tool_usage(self, activity_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze which tools and features the user prefers"""
        # Mock tool usage analysis
        tool_usage = Counter()
        feature_usage = Counter()
        
        for activity in activity_history:
            tool = activity.get('tool', 'unknown')
            feature = activity.get('feature', 'unknown')
            
            tool_usage[tool] += 1
            feature_usage[feature] += 1
        
        return {
            "preferred_tools": dict(tool_usage.most_common(5)),
            "preferred_features": dict(feature_usage.most_common(10)),
            "tool_diversity": len(tool_usage),
            "power_user": len(feature_usage) > 20  # Uses many different features
        }
    
    async def _analyze_data_quality_habits(self, data_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze user's data quality maintenance habits"""
        # Analyze classification completeness
        classified_items = len([item for item in data_items if item.get('data_type') != 'unknown'])
        classification_rate = classified_items / len(data_items) if data_items else 0
        
        # Analyze metadata completeness
        items_with_metadata = len([item for item in data_items if item.get('metadata')])
        metadata_rate = items_with_metadata / len(data_items) if data_items else 0
        
        # Analyze tagging habits
        tagged_items = len([item for item in data_items if item.get('tags')])
        tagging_rate = tagged_items / len(data_items) if data_items else 0
        
        # Determine quality consciousness level
        if classification_rate > 0.9 and metadata_rate > 0.8 and tagging_rate > 0.5:
            quality_level = "meticulous"
        elif classification_rate > 0.7 and metadata_rate > 0.5:
            quality_level = "organized"
        elif classification_rate > 0.5:
            quality_level = "basic"
        else:
            quality_level = "minimal"
        
        return {
            "classification_rate": classification_rate,
            "metadata_completeness": metadata_rate,
            "tagging_rate": tagging_rate,
            "quality_consciousness": quality_level,
            "attention_to_detail": "high" if quality_level in ["meticulous", "organized"] else "medium" if quality_level == "basic" else "low"
        }
    
    async def _analyze_storage_behavior(self, data_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze user's storage and archival behavior"""
        # Analyze file size distribution
        sizes = [item.get('size_bytes', 0) for item in data_items if item.get('size_bytes')]
        
        if sizes:
            total_size = sum(sizes)
            avg_size = statistics.mean(sizes)
            largest_files = sorted(sizes, reverse=True)[:10]
        else:
            total_size = avg_size = 0
            largest_files = []
        
        # Analyze data age distribution
        ages = []
        current_time = datetime.now(timezone.utc)
        
        for item in data_items:
            created_at = item.get('created_at')
            if created_at:
                if isinstance(created_at, str):
                    dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                else:
                    dt = created_at
                
                age_days = (current_time - dt).days
                ages.append(age_days)
        
        # Determine storage habits
        old_data_ratio = len([age for age in ages if age > 365]) / len(ages) if ages else 0
        hoarding_tendency = "high" if old_data_ratio > 0.5 else "medium" if old_data_ratio > 0.2 else "low"
        
        return {
            "total_storage_mb": total_size / (1024 * 1024),
            "average_file_size": avg_size,
            "largest_files_sizes": largest_files,
            "data_age_distribution": {
                "avg_age_days": statistics.mean(ages) if ages else 0,
                "old_data_ratio": old_data_ratio
            },
            "hoarding_tendency": hoarding_tendency,
            "storage_efficiency": "good" if total_size < 1024*1024*1024 else "needs_attention"  # < 1GB is good
        }

class RecommendationGenerator:
    """Generates personalized recommendations based on user profiles"""
    
    def __init__(self):
        self.recommendation_templates = self._load_recommendation_templates()
    
    def _load_recommendation_templates(self) -> Dict[str, Any]:
        """Load recommendation templates"""
        return {
            "organization": [
                {
                    "id": "create_folder_structure",
                    "title": "Create Organized Folder Structure",
                    "description": "Based on your content types, create a structured folder system",
                    "category": RecommendationCategory.DATA_ORGANIZATION,
                    "triggers": ["low_organization", "many_content_types"],
                    "implementation_effort": "medium"
                },
                {
                    "id": "tag_untagged_content",
                    "title": "Add Tags to Untagged Content",
                    "description": "Improve searchability by adding relevant tags",
                    "category": RecommendationCategory.DATA_QUALITY,
                    "triggers": ["low_tagging_rate"],
                    "implementation_effort": "low"
                },
                {
                    "id": "standardize_naming",
                    "title": "Standardize File Naming Convention",
                    "description": "Apply consistent naming patterns to your files",
                    "category": RecommendationCategory.DATA_ORGANIZATION,
                    "triggers": ["inconsistent_naming"],
                    "implementation_effort": "medium"
                }
            ],
            "cleanup": [
                {
                    "id": "remove_duplicates",
                    "title": "Remove Duplicate Files",
                    "description": "Free up storage by removing duplicate content",
                    "category": RecommendationCategory.PERFORMANCE_OPTIMIZATION,
                    "triggers": ["high_duplicate_ratio"],
                    "implementation_effort": "low"
                },
                {
                    "id": "archive_old_data",
                    "title": "Archive Old Data",
                    "description": "Move old, rarely accessed data to archive storage",
                    "category": RecommendationCategory.PERFORMANCE_OPTIMIZATION,
                    "triggers": ["high_hoarding_tendency", "large_storage"],
                    "implementation_effort": "medium"
                },
                {
                    "id": "classify_unknown_items",
                    "title": "Classify Unknown Items",
                    "description": "Improve data organization by classifying unidentified items",
                    "category": RecommendationCategory.DATA_QUALITY,
                    "triggers": ["low_classification_rate"],
                    "implementation_effort": "medium"
                }
            ],
            "productivity": [
                {
                    "id": "automate_organization",
                    "title": "Set Up Automated Organization Rules",
                    "description": "Create rules to automatically organize new content",
                    "category": RecommendationCategory.AUTOMATION,
                    "triggers": ["batch_processor", "structured_organization"],
                    "implementation_effort": "high"
                },
                {
                    "id": "workflow_optimization",
                    "title": "Optimize Your Workflow",
                    "description": "Streamline your data management workflow",
                    "category": RecommendationCategory.USER_EXPERIENCE,
                    "triggers": ["power_user", "high_activity"],
                    "implementation_effort": "medium"
                }
            ],
            "storage": [
                {
                    "id": "compress_large_files",
                    "title": "Compress Large Files",
                    "description": "Reduce storage usage by compressing large files",
                    "category": RecommendationCategory.PERFORMANCE_OPTIMIZATION,
                    "triggers": ["large_average_file_size", "storage_needs_attention"],
                    "implementation_effort": "low"
                },
                {
                    "id": "cloud_backup_strategy",
                    "title": "Implement Cloud Backup Strategy",
                    "description": "Protect your data with automated cloud backups",
                    "category": RecommendationCategory.DATA_QUALITY,
                    "triggers": ["large_storage", "important_data"],
                    "implementation_effort": "high"
                }
            ]
        }
    
    async def generate_recommendations(self, user_profile: Dict[str, Any], 
                                     context: Dict[str, Any] = None) -> List[Recommendation]:
        """Generate personalized recommendations based on user profile"""
        recommendations = []
        context = context or {}
        
        # Analyze triggers from user profile
        triggers = await self._identify_triggers(user_profile)
        
        # Generate recommendations for each category
        for category, templates in self.recommendation_templates.items():
            category_recommendations = await self._generate_category_recommendations(
                category, templates, triggers, user_profile, context
            )
            recommendations.extend(category_recommendations)
        
        # Sort by priority and confidence
        recommendations.sort(key=lambda r: (r.priority.value, -r.confidence), reverse=True)
        
        # Limit to top recommendations
        return recommendations[:15]
    
    async def _identify_triggers(self, user_profile: Dict[str, Any]) -> List[str]:
        """Identify triggers based on user profile analysis"""
        triggers = []
        
        # Content preferences triggers
        content_prefs = user_profile.get("content_preferences", {})
        if len(content_prefs.get("primary_content_types", {})) > 5:
            triggers.append("many_content_types")
        
        # Organization triggers
        org_patterns = user_profile.get("organization_patterns", {})
        if org_patterns.get("organization_style") == "simple":
            triggers.append("low_organization")
        if org_patterns.get("categorization_rate", 0) < 0.3:
            triggers.append("low_categorization")
        
        # Activity pattern triggers
        activity_patterns = user_profile.get("activity_patterns", {})
        if activity_patterns.get("work_style") == "batch_processor":
            triggers.append("batch_processor")
        if activity_patterns.get("activity_frequency", 0) > 5:
            triggers.append("high_activity")
        
        # Tool usage triggers
        tool_usage = user_profile.get("tool_usage", {})
        if tool_usage.get("power_user", False):
            triggers.append("power_user")
        
        # Data quality triggers
        quality_habits = user_profile.get("data_quality_habits", {})
        if quality_habits.get("classification_rate", 0) < 0.7:
            triggers.append("low_classification_rate")
        if quality_habits.get("tagging_rate", 0) < 0.3:
            triggers.append("low_tagging_rate")
        if quality_habits.get("quality_consciousness") == "meticulous":
            triggers.append("structured_organization")
        
        # Storage triggers
        storage_behavior = user_profile.get("storage_behavior", {})
        if storage_behavior.get("hoarding_tendency") == "high":
            triggers.append("high_hoarding_tendency")
        if storage_behavior.get("storage_efficiency") == "needs_attention":
            triggers.append("storage_needs_attention")
        if storage_behavior.get("total_storage_mb", 0) > 1000:  # > 1GB
            triggers.append("large_storage")
        if storage_behavior.get("average_file_size", 0) > 50 * 1024 * 1024:  # > 50MB
            triggers.append("large_average_file_size")
        
        return triggers
    
    async def _generate_category_recommendations(self, category: str, templates: List[Dict[str, Any]], 
                                               triggers: List[str], user_profile: Dict[str, Any], 
                                               context: Dict[str, Any]) -> List[Recommendation]:
        """Generate recommendations for a specific category"""
        recommendations = []
        
        for template in templates:
            # Check if template triggers match user triggers
            template_triggers = template.get("triggers", [])
            if any(trigger in triggers for trigger in template_triggers):
                
                # Calculate confidence based on trigger match
                matched_triggers = [t for t in template_triggers if t in triggers]
                confidence = len(matched_triggers) / len(template_triggers)
                
                # Determine priority based on template and user profile
                priority = await self._determine_priority(template, user_profile, triggers)
                
                # Generate personalized action items
                action_items = await self._generate_action_items(template, user_profile)
                
                # Create recommendation
                recommendation = Recommendation(
                    recommendation_id=f"rec_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",
                    user_id=user_profile.get("user_id", "unknown"),
                    recommendation_type=RecommendationType(category),
                    category=template["category"],
                    title=template["title"],
                    description=await self._personalize_description(template["description"], user_profile),
                    priority=priority,
                    confidence=confidence,
                    personalization_factors=matched_triggers,
                    action_items=action_items,
                    expected_benefit=await self._calculate_expected_benefit(template, user_profile),
                    implementation_effort=template["implementation_effort"],
                    data={
                        "template_id": template["id"],
                        "matched_triggers": matched_triggers,
                        "user_profile_factors": await self._extract_relevant_profile_factors(template, user_profile)
                    },
                    created_at=datetime.now(timezone.utc),
                    expires_at=datetime.now(timezone.utc) + timedelta(days=30)
                )
                
                recommendations.append(recommendation)
        
        return recommendations
    
    async def _determine_priority(self, template: Dict[str, Any], user_profile: Dict[str, Any], 
                                triggers: List[str]) -> RecommendationPriority:
        """Determine recommendation priority"""
        # Base priority on template category
        category = template["category"]
        
        if category == RecommendationCategory.DATA_QUALITY:
            return RecommendationPriority.HIGH
        elif category == RecommendationCategory.PERFORMANCE_OPTIMIZATION:
            # Check storage situation
            storage_behavior = user_profile.get("storage_behavior", {})
            if storage_behavior.get("storage_efficiency") == "needs_attention":
                return RecommendationPriority.HIGH
            return RecommendationPriority.MEDIUM
        elif category == RecommendationCategory.AUTOMATION:
            # Higher priority for power users
            tool_usage = user_profile.get("tool_usage", {})
            if tool_usage.get("power_user", False):
                return RecommendationPriority.HIGH
            return RecommendationPriority.MEDIUM
        elif category == RecommendationCategory.USER_EXPERIENCE:
            return RecommendationPriority.MEDIUM
        else:
            return RecommendationPriority.LOW
    
    async def _generate_action_items(self, template: Dict[str, Any], 
                                   user_profile: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate specific action items for the recommendation"""
        template_id = template["id"]
        action_items = []
        
        if template_id == "create_folder_structure":
            content_types = user_profile.get("content_preferences", {}).get("primary_content_types", {})
            for content_type in list(content_types.keys())[:5]:
                action_items.append({
                    "action": "create_folder",
                    "description": f"Create folder for {content_type} files",
                    "parameters": {"folder_name": content_type.title(), "content_type": content_type}
                })
        
        elif template_id == "tag_untagged_content":
            action_items.append({
                "action": "bulk_tag",
                "description": "Review and tag untagged content",
                "parameters": {"filter": "untagged", "suggested_tags": ["important", "work", "personal"]}
            })
        
        elif template_id == "remove_duplicates":
            action_items.append({
                "action": "scan_duplicates",
                "description": "Scan for duplicate files",
                "parameters": {"scan_type": "content_hash"}
            })
            action_items.append({
                "action": "review_duplicates",
                "description": "Review and confirm duplicate removal",
                "parameters": {"auto_remove": False}
            })
        
        elif template_id == "archive_old_data":
            action_items.append({
                "action": "identify_old_data",
                "description": "Identify data older than 1 year",
                "parameters": {"age_threshold_days": 365}
            })
            action_items.append({
                "action": "create_archive",
                "description": "Create archive folder structure",
                "parameters": {"archive_location": "Archive"}
            })
        
        elif template_id == "automate_organization":
            action_items.append({
                "action": "create_auto_rule",
                "description": "Create automatic organization rules",
                "parameters": {"rule_type": "content_type_based"}
            })
        
        # Default action items
        if not action_items:
            action_items.append({
                "action": "review",
                "description": f"Review and implement {template['title'].lower()}",
                "parameters": {}
            })
        
        return action_items
    
    async def _personalize_description(self, base_description: str, user_profile: Dict[str, Any]) -> str:
        """Personalize the recommendation description"""
        # Add user-specific context
        content_prefs = user_profile.get("content_preferences", {})
        primary_type = list(content_prefs.get("primary_content_types", {}).keys())[0] if content_prefs.get("primary_content_types") else "files"
        
        # Simple personalization
        personalized = base_description.replace("your files", f"your {primary_type} files")
        personalized = personalized.replace("your content", f"your {primary_type} content")
        
        return personalized
    
    async def _calculate_expected_benefit(self, template: Dict[str, Any], user_profile: Dict[str, Any]) -> str:
        """Calculate expected benefit from implementing the recommendation"""
        template_id = template["id"]
        
        benefit_mapping = {
            "create_folder_structure": "Improve data findability by 40-60%",
            "tag_untagged_content": "Enhance search accuracy by 30-50%",
            "remove_duplicates": "Free up 10-25% storage space",
            "archive_old_data": "Reduce active data size by 20-40%",
            "automate_organization": "Save 2-5 hours per week on manual organization",
            "classify_unknown_items": "Improve data organization by 25-40%",
            "compress_large_files": "Reduce storage usage by 15-30%",
            "workflow_optimization": "Increase productivity by 15-25%"
        }
        
        return benefit_mapping.get(template_id, "Improve data management efficiency")
    
    async def _extract_relevant_profile_factors(self, template: Dict[str, Any], 
                                               user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Extract relevant profile factors for the recommendation"""
        relevant_factors = {}
        
        # Always include basic profile info
        relevant_factors["organization_style"] = user_profile.get("organization_patterns", {}).get("organization_style")
        relevant_factors["quality_consciousness"] = user_profile.get("data_quality_habits", {}).get("quality_consciousness")
        
        # Include category-specific factors
        category = template["category"]
        
        if category == RecommendationCategory.DATA_ORGANIZATION:
            relevant_factors.update({
                "categorization_rate": user_profile.get("organization_patterns", {}).get("categorization_rate"),
                "primary_content_types": user_profile.get("content_preferences", {}).get("primary_content_types")
            })
        
        elif category == RecommendationCategory.PERFORMANCE_OPTIMIZATION:
            relevant_factors.update({
                "total_storage_mb": user_profile.get("storage_behavior", {}).get("total_storage_mb"),
                "hoarding_tendency": user_profile.get("storage_behavior", {}).get("hoarding_tendency")
            })
        
        elif category == RecommendationCategory.AUTOMATION:
            relevant_factors.update({
                "work_style": user_profile.get("activity_patterns", {}).get("work_style"),
                "power_user": user_profile.get("tool_usage", {}).get("power_user")
            })
        
        return relevant_factors

class RecommendationEngine:
    """Main recommendation engine that orchestrates profiling and recommendation generation"""
    
    def __init__(self, database_url: str = None):
        self.database_url = database_url
        self.profiler = UserProfiler()
        self.generator = RecommendationGenerator()
        self.user_profiles = {}
        self.recommendation_history = {}
    
    async def get_recommendations(self, user_id: str, recommendation_types: List[RecommendationType] = None,
                                refresh_profile: bool = False) -> List[Recommendation]:
        """Get personalized recommendations for a user"""
        # Get or update user profile
        if refresh_profile or user_id not in self.user_profiles:
            await self._update_user_profile(user_id)
        
        user_profile = self.user_profiles.get(user_id, {})
        
        # Generate recommendations
        recommendations = await self.generator.generate_recommendations(user_profile)
        
        # Filter by type if specified
        if recommendation_types:
            recommendations = [r for r in recommendations if r.recommendation_type in recommendation_types]
        
        # Store in history
        if user_id not in self.recommendation_history:
            self.recommendation_history[user_id] = []
        self.recommendation_history[user_id].extend(recommendations)
        
        return recommendations
    
    async def mark_recommendation_completed(self, recommendation_id: str, user_id: str):
        """Mark a recommendation as completed"""
        user_recommendations = self.recommendation_history.get(user_id, [])
        
        for rec in user_recommendations:
            if rec.recommendation_id == recommendation_id:
                rec.completed = True
                rec.expires_at = datetime.now(timezone.utc)  # Expire immediately
                logger.info(f"Recommendation {recommendation_id} marked as completed for user {user_id}")
                break
    
    async def dismiss_recommendation(self, recommendation_id: str, user_id: str):
        """Dismiss a recommendation"""
        user_recommendations = self.recommendation_history.get(user_id, [])
        
        for rec in user_recommendations:
            if rec.recommendation_id == recommendation_id:
                rec.dismissed = True
                rec.expires_at = datetime.now(timezone.utc)  # Expire immediately
                logger.info(f"Recommendation {recommendation_id} dismissed for user {user_id}")
                break
    
    async def get_recommendation_analytics(self, user_id: str) -> Dict[str, Any]:
        """Get analytics on recommendation effectiveness"""
        user_recommendations = self.recommendation_history.get(user_id, [])
        
        if not user_recommendations:
            return {"message": "No recommendation history available"}
        
        total_recommendations = len(user_recommendations)
        completed_recommendations = len([r for r in user_recommendations if r.completed])
        dismissed_recommendations = len([r for r in user_recommendations if r.dismissed])
        
        # Analyze by type
        type_stats = defaultdict(lambda: {"total": 0, "completed": 0, "dismissed": 0})
        
        for rec in user_recommendations:
            rec_type = rec.recommendation_type.value
            type_stats[rec_type]["total"] += 1
            if rec.completed:
                type_stats[rec_type]["completed"] += 1
            if rec.dismissed:
                type_stats[rec_type]["dismissed"] += 1
        
        # Calculate completion rates
        completion_rate = completed_recommendations / total_recommendations if total_recommendations > 0 else 0
        dismissal_rate = dismissed_recommendations / total_recommendations if total_recommendations > 0 else 0
        
        return {
            "total_recommendations": total_recommendations,
            "completed_recommendations": completed_recommendations,
            "dismissed_recommendations": dismissed_recommendations,
            "completion_rate": completion_rate,
            "dismissal_rate": dismissal_rate,
            "type_statistics": dict(type_stats),
            "engagement_score": max(0, completion_rate - dismissal_rate)
        }
    
    async def _update_user_profile(self, user_id: str):
        """Update user profile based on current data"""
        # Get user data
        data_items = await self._get_user_data(user_id)
        activity_history = await self._get_user_activity_history(user_id)
        
        # Analyze behavior
        profile = await self.profiler.analyze_user_behavior(user_id, data_items, activity_history)
        
        # Store profile
        self.user_profiles[user_id] = profile
        
        logger.info(f"Updated profile for user {user_id}")
    
    async def _get_user_data(self, user_id: str) -> List[Dict[str, Any]]:
        """Get user data for profiling (mock implementation)"""
        # In production, this would query the actual database
        return [
            {
                "id": f"item_{i}",
                "user_id": user_id,
                "data_type": ["image", "text", "document", "video", "audio"][i % 5],
                "source": ["google_photos", "dropbox", "email", "manual"][i % 4],
                "created_at": (datetime.now(timezone.utc) - timedelta(days=i % 180)).isoformat(),
                "size_bytes": 1024 * 1024 * (i % 20 + 1),  # 1-20 MB
                "confidence_score": 0.3 + (i % 7) * 0.1,  # 0.3-0.9
                "category": ["work", "personal", "photos", "documents", None][i % 5],
                "tags": [["important"], ["work", "project"], ["personal"], [], ["archive"]][i % 5],
                "metadata": {
                    "filename": f"file_{i}.{['jpg', 'txt', 'pdf', 'mp4', 'mp3'][i % 5]}"
                }
            }
            for i in range(150)  # 150 mock items
        ]
    
    async def _get_user_activity_history(self, user_id: str) -> List[Dict[str, Any]]:
        """Get user activity history for profiling (mock implementation)"""
        return [
            {
                "user_id": user_id,
                "action": ["upload", "organize", "search", "tag", "delete"][i % 5],
                "tool": ["web_ui", "mobile_app", "api"][i % 3],
                "feature": ["file_manager", "search", "auto_organize", "manual_tag", "bulk_operations"][i % 5],
                "timestamp": (datetime.now(timezone.utc) - timedelta(hours=i % 168)).isoformat()  # Last week
            }
            for i in range(50)  # 50 mock activities
        ]

# CLI Interface
async def main():
    """Command-line interface for recommendation engine"""
    import argparse
    
    parser = argparse.ArgumentParser(description='ActiveLog Recommendation Engine')
    parser.add_argument('action', choices=['recommend', 'profile', 'analytics', 'test'])
    parser.add_argument('--user-id', default='test_user', help='User ID for recommendations')
    parser.add_argument('--types', nargs='+', help='Specific recommendation types')
    parser.add_argument('--output', help='Output file for results')
    parser.add_argument('--format', choices=['json', 'summary'], default='summary', help='Output format')
    parser.add_argument('--refresh', action='store_true', help='Refresh user profile')
    
    args = parser.parse_args()
    
    engine = RecommendationEngine()
    
    if args.action == 'recommend':
        # Parse recommendation types
        rec_types = None
        if args.types:
            rec_types = []
            for type_str in args.types:
                try:
                    rec_types.append(RecommendationType(type_str))
                except ValueError:
                    print(f"Warning: Unknown recommendation type '{type_str}'")
        
        # Get recommendations
        recommendations = await engine.get_recommendations(args.user_id, rec_types, args.refresh)
        
        if args.format == 'json':
            output = json.dumps([asdict(rec) for rec in recommendations], indent=2, default=str)
        else:
            output = f"Personalized Recommendations for {args.user_id}\n"
            output += "=" * 50 + "\n\n"
            
            if recommendations:
                for i, rec in enumerate(recommendations, 1):
                    priority_icon = {"low": "○", "medium": "◐", "high": "●", "urgent": "🔴"}
                    icon = priority_icon.get(rec.priority.name.lower(), "•")
                    
                    output += f"{i}. {icon} {rec.title}\n"
                    output += f"   {rec.description}\n"
                    output += f"   Priority: {rec.priority.name}, Confidence: {rec.confidence:.2f}\n"
                    output += f"   Expected Benefit: {rec.expected_benefit}\n"
                    output += f"   Implementation: {rec.implementation_effort} effort\n\n"
            else:
                output += "No recommendations available at this time.\n"
        
        if args.output:
            with open(args.output, 'w') as f:
                f.write(output)
            print(f"Recommendations saved to {args.output}")
        else:
            print(output)
    
    elif args.action == 'profile':
        # Update and show user profile
        await engine._update_user_profile(args.user_id)
        profile = engine.user_profiles.get(args.user_id, {})
        
        if args.format == 'json':
            output = json.dumps(profile, indent=2, default=str)
        else:
            output = f"User Profile for {args.user_id}\n"
            output += "=" * 50 + "\n\n"
            
            for section, data in profile.items():
                if section != "user_id":
                    output += f"{section.replace('_', ' ').title()}:\n"
                    if isinstance(data, dict):
                        for key, value in data.items():
                            output += f"  {key}: {value}\n"
                    else:
                        output += f"  {data}\n"
                    output += "\n"
        
        if args.output:
            with open(args.output, 'w') as f:
                f.write(output)
            print(f"User profile saved to {args.output}")
        else:
            print(output)
    
    elif args.action == 'analytics':
        # Generate some recommendations first to have data
        await engine.get_recommendations(args.user_id)
        
        # Mark some as completed for demo
        user_recs = engine.recommendation_history.get(args.user_id, [])
        if user_recs:
            await engine.mark_recommendation_completed(user_recs[0].recommendation_id, args.user_id)
        
        analytics = await engine.get_recommendation_analytics(args.user_id)
        
        if args.format == 'json':
            output = json.dumps(analytics, indent=2)
        else:
            output = f"Recommendation Analytics for {args.user_id}\n"
            output += "=" * 50 + "\n\n"
            
            if "message" not in analytics:
                output += f"Total Recommendations: {analytics['total_recommendations']}\n"
                output += f"Completed: {analytics['completed_recommendations']} ({analytics['completion_rate']:.1%})\n"
                output += f"Dismissed: {analytics['dismissed_recommendations']} ({analytics['dismissal_rate']:.1%})\n"
                output += f"Engagement Score: {analytics['engagement_score']:.2f}\n\n"
                
                output += "By Type:\n"
                for rec_type, stats in analytics['type_statistics'].items():
                    output += f"  {rec_type}: {stats['completed']}/{stats['total']} completed\n"
            else:
                output += analytics["message"]
        
        if args.output:
            with open(args.output, 'w') as f:
                f.write(output)
            print(f"Analytics saved to {args.output}")
        else:
            print(output)
    
    elif args.action == 'test':
        # Test the recommendation engine
        print("Testing Recommendation Engine...")
        print("=" * 40)
        
        # Test profile generation
        print("\n1. Generating user profile...")
        await engine._update_user_profile(args.user_id)
        profile = engine.user_profiles[args.user_id]
        print(f"   Profile generated with {len(profile)} sections")
        
        # Test recommendation generation
        print("\n2. Generating recommendations...")
        recommendations = await engine.get_recommendations(args.user_id)
        print(f"   Generated {len(recommendations)} recommendations")
        
        # Test by type
        print("\n3. Testing recommendation types:")
        for rec_type in RecommendationType:
            type_recs = await engine.get_recommendations(args.user_id, [rec_type])
            print(f"   {rec_type.value}: {len(type_recs)} recommendations")
        
        # Test analytics
        print("\n4. Testing analytics...")
        if recommendations:
            await engine.mark_recommendation_completed(recommendations[0].recommendation_id, args.user_id)
        
        analytics = await engine.get_recommendation_analytics(args.user_id)
        print(f"   Analytics generated: {analytics.get('engagement_score', 0):.2f} engagement score")
        
        print("\n✓ All tests completed successfully!")

if __name__ == "__main__":
    asyncio.run(main())