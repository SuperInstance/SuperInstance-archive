"""
Community Hub - Central platform for collaborative learning and configuration sharing
"""

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict, field
from typing import Dict, List, Optional, Any, Set, Tuple
from enum import Enum
from pathlib import Path
import hashlib
import statistics

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False

try:
    from cryptography.fernet import Fernet
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False

logger = logging.getLogger(__name__)

class ShareType(Enum):
    CONFIGURATION = "configuration"
    BENCHMARK = "benchmark"
    TROUBLESHOOTING = "troubleshooting"
    TUTORIAL = "tutorial"
    OPTIMIZATION = "optimization"
    REVIEW = "review"

class ContributionStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    FEATURED = "featured"
    ARCHIVED = "archived"

class UserRole(Enum):
    MEMBER = "member"
    CONTRIBUTOR = "contributor"
    EXPERT = "expert"
    MODERATOR = "moderator"
    ADMIN = "admin"

class ReputationLevel(Enum):
    NEWCOMER = "newcomer"        # 0-99
    CONTRIBUTOR = "contributor"  # 100-499
    EXPERT = "expert"           # 500-1999
    MASTER = "master"           # 2000-4999
    LEGEND = "legend"           # 5000+

@dataclass
class UserProfile:
    user_id: str
    username: str
    email: str
    role: UserRole
    reputation_score: int
    reputation_level: ReputationLevel
    contributions_count: int
    downloads_count: int
    ratings_given: int
    expertise_areas: List[str]
    badges: List[str]
    join_date: datetime
    last_active: datetime
    bio: Optional[str] = None
    location: Optional[str] = None
    website: Optional[str] = None

@dataclass
class ConfigurationShare:
    share_id: str
    title: str
    description: str
    author_id: str
    share_type: ShareType
    status: ContributionStatus
    configuration_data: Dict[str, Any]
    hardware_profile: Dict[str, Any]
    performance_metrics: Dict[str, float]
    tags: List[str]
    category: str
    difficulty_level: str  # beginner, intermediate, advanced, expert
    estimated_time: int  # minutes
    prerequisites: List[str]
    compatibility_info: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    downloads: int = 0
    rating_average: float = 0.0
    rating_count: int = 0
    views: int = 0
    comments_count: int = 0

@dataclass
class UserContribution:
    contribution_id: str
    user_id: str
    share_id: str
    contribution_type: str  # upload, review, comment, rating, report
    content: Dict[str, Any]
    timestamp: datetime
    reputation_earned: int = 0
    status: str = "active"

@dataclass
class ReputationTransaction:
    transaction_id: str
    user_id: str
    action: str  # upload, download, rating_received, helpful_comment, etc.
    points: int
    reference_id: Optional[str]  # ID of related content
    timestamp: datetime
    description: str

class ReputationSystem:
    """Advanced reputation and scoring system"""
    
    def __init__(self):
        self.reputation_rules = {
            'configuration_upload': 10,
            'configuration_approved': 25,
            'configuration_featured': 100,
            'helpful_rating_received': 5,
            'download_milestone_100': 20,
            'download_milestone_500': 50,
            'download_milestone_1000': 100,
            'expert_verification': 200,
            'troubleshooting_solved': 15,
            'tutorial_created': 30,
            'bug_report_valid': 10,
            'moderation_action': 5,
            'beta_testing': 25,
            'competition_win': 500,
            'community_event': 50
        }
        
        self.reputation_levels = {
            ReputationLevel.NEWCOMER: (0, 99),
            ReputationLevel.CONTRIBUTOR: (100, 499),
            ReputationLevel.EXPERT: (500, 1999),
            ReputationLevel.MASTER: (2000, 4999),
            ReputationLevel.LEGEND: (5000, float('inf'))
        }
        
        self.badges = {
            'first_contribution': {'name': 'First Steps', 'description': 'Made first contribution'},
            'helpful_contributor': {'name': 'Helper', 'description': '10+ helpful contributions'},
            'expert_reviewer': {'name': 'Expert Eye', 'description': 'Expert-level reviews'},
            'popular_creator': {'name': 'Crowd Favorite', 'description': '1000+ downloads'},
            'troubleshooter': {'name': 'Problem Solver', 'description': 'Solved 25+ issues'},
            'beta_tester': {'name': 'Early Adopter', 'description': 'Active beta tester'},
            'competition_winner': {'name': 'Champion', 'description': 'Won optimization competition'},
            'community_leader': {'name': 'Leader', 'description': 'Community leadership'},
            'mentor': {'name': 'Mentor', 'description': 'Helped 100+ newcomers'}
        }
        
        self.logger = logging.getLogger(__name__)
    
    async def calculate_reputation_score(self, user_id: str, transactions: List[ReputationTransaction]) -> int:
        """Calculate total reputation score for user"""
        try:
            user_transactions = [t for t in transactions if t.user_id == user_id]
            total_score = sum(t.points for t in user_transactions)
            
            # Apply time decay for very old contributions (older than 2 years)
            now = datetime.utcnow()
            decayed_score = 0
            
            for transaction in user_transactions:
                age_days = (now - transaction.timestamp).days
                if age_days > 730:  # 2 years
                    decay_factor = max(0.5, 1.0 - (age_days - 730) / 1095)  # 3 year full decay
                    decayed_score += transaction.points * decay_factor
                else:
                    decayed_score += transaction.points
            
            return max(0, int(decayed_score))
            
        except Exception as e:
            self.logger.error(f"Reputation calculation failed: {e}")
            return 0
    
    def get_reputation_level(self, score: int) -> ReputationLevel:
        """Get reputation level based on score"""
        for level, (min_score, max_score) in self.reputation_levels.items():
            if min_score <= score <= max_score:
                return level
        return ReputationLevel.NEWCOMER
    
    async def award_reputation(self, user_id: str, action: str, reference_id: Optional[str] = None) -> int:
        """Award reputation points for an action"""
        try:
            points = self.reputation_rules.get(action, 0)
            
            if points > 0:
                transaction = ReputationTransaction(
                    transaction_id=str(uuid.uuid4()),
                    user_id=user_id,
                    action=action,
                    points=points,
                    reference_id=reference_id,
                    timestamp=datetime.utcnow(),
                    description=f"Earned {points} points for {action}"
                )
                
                # Store transaction (would integrate with database)
                self.logger.info(f"Awarded {points} reputation to {user_id} for {action}")
                
                return points
            
            return 0
            
        except Exception as e:
            self.logger.error(f"Reputation award failed: {e}")
            return 0
    
    def check_badge_eligibility(self, user_profile: UserProfile, user_stats: Dict[str, Any]) -> List[str]:
        """Check which badges user is eligible for"""
        eligible_badges = []
        
        try:
            stats = user_stats
            
            # First contribution badge
            if stats.get('contributions', 0) >= 1 and 'first_contribution' not in user_profile.badges:
                eligible_badges.append('first_contribution')
            
            # Helpful contributor badge
            if stats.get('helpful_contributions', 0) >= 10 and 'helpful_contributor' not in user_profile.badges:
                eligible_badges.append('helpful_contributor')
            
            # Popular creator badge
            if stats.get('total_downloads', 0) >= 1000 and 'popular_creator' not in user_profile.badges:
                eligible_badges.append('popular_creator')
            
            # Troubleshooter badge
            if stats.get('issues_solved', 0) >= 25 and 'troubleshooter' not in user_profile.badges:
                eligible_badges.append('troubleshooter')
            
            # Expert reviewer badge
            if (user_profile.reputation_level in [ReputationLevel.EXPERT, ReputationLevel.MASTER, ReputationLevel.LEGEND] 
                and stats.get('expert_reviews', 0) >= 10 
                and 'expert_reviewer' not in user_profile.badges):
                eligible_badges.append('expert_reviewer')
            
        except Exception as e:
            self.logger.error(f"Badge eligibility check failed: {e}")
        
        return eligible_badges

class CommunityModeration:
    """Community moderation and content quality system"""
    
    def __init__(self):
        self.moderation_rules = {
            'min_description_length': 50,
            'required_tags': 1,
            'max_tags': 10,
            'required_hardware_info': ['cpu', 'memory', 'storage'],
            'banned_words': ['spam', 'fake', 'virus', 'malware'],
            'max_file_size_mb': 50
        }
        
        self.quality_thresholds = {
            'min_rating_for_featured': 4.5,
            'min_downloads_for_featured': 100,
            'min_reviews_for_featured': 10,
            'auto_approve_expert_threshold': ReputationLevel.EXPERT
        }
        
        self.logger = logging.getLogger(__name__)
    
    async def moderate_submission(self, submission: ConfigurationShare, author: UserProfile) -> Tuple[bool, List[str]]:
        """Moderate a community submission"""
        try:
            issues = []
            approved = True
            
            # Check basic requirements
            if len(submission.description) < self.moderation_rules['min_description_length']:
                issues.append(f"Description too short (minimum {self.moderation_rules['min_description_length']} characters)")
                approved = False
            
            if len(submission.tags) < self.moderation_rules['required_tags']:
                issues.append("At least one tag is required")
                approved = False
            
            if len(submission.tags) > self.moderation_rules['max_tags']:
                issues.append(f"Too many tags (maximum {self.moderation_rules['max_tags']})")
                approved = False
            
            # Check for banned content
            content_text = f"{submission.title} {submission.description}".lower()
            banned_found = [word for word in self.moderation_rules['banned_words'] if word in content_text]
            if banned_found:
                issues.append(f"Contains banned words: {', '.join(banned_found)}")
                approved = False
            
            # Check hardware information completeness
            hardware_info = submission.hardware_profile
            missing_hw_info = [info for info in self.moderation_rules['required_hardware_info'] 
                             if info not in hardware_info]
            if missing_hw_info:
                issues.append(f"Missing hardware information: {', '.join(missing_hw_info)}")
                approved = False
            
            # Auto-approve for trusted users
            if (author.reputation_level.value >= self.quality_thresholds['auto_approve_expert_threshold'].value 
                and len(issues) == 0):
                approved = True
                issues.append("Auto-approved (trusted contributor)")
            
            self.logger.info(f"Moderation result for {submission.share_id}: {'Approved' if approved else 'Rejected'}")
            
            return approved, issues
            
        except Exception as e:
            self.logger.error(f"Moderation failed: {e}")
            return False, [f"Moderation error: {str(e)}"]
    
    async def check_for_featured_content(self, submission: ConfigurationShare) -> bool:
        """Check if content qualifies for featured status"""
        try:
            if submission.status != ContributionStatus.APPROVED:
                return False
            
            # Check quality thresholds
            quality_checks = [
                submission.rating_average >= self.quality_thresholds['min_rating_for_featured'],
                submission.downloads >= self.quality_thresholds['min_downloads_for_featured'],
                submission.rating_count >= self.quality_thresholds['min_reviews_for_featured']
            ]
            
            if all(quality_checks):
                self.logger.info(f"Content {submission.share_id} qualifies for featured status")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Featured content check failed: {e}")
            return False

class CommunityHub:
    """Main community hub orchestrator"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        self.users: Dict[str, UserProfile] = {}
        self.contributions: Dict[str, ConfigurationShare] = {}
        self.user_contributions: Dict[str, List[UserContribution]] = {}
        self.reputation_transactions: List[ReputationTransaction] = []
        
        # Initialize subsystems
        self.reputation_system = ReputationSystem()
        self.moderation_system = CommunityModeration()
        
        self.storage_path = Path(config.get('storage_path', './community_data'))
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.logger = logging.getLogger(__name__)
    
    async def initialize(self) -> bool:
        """Initialize community hub"""
        try:
            self.logger.info("Initializing community learning network...")
            
            # Load existing data
            await self._load_community_data()
            
            # Start background tasks
            asyncio.create_task(self._periodic_maintenance())
            asyncio.create_task(self._update_featured_content())
            
            self.logger.info("Community hub initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Community hub initialization failed: {e}")
            return False
    
    async def register_user(self, user_data: Dict[str, Any]) -> UserProfile:
        """Register new community user"""
        try:
            user_id = user_data.get('user_id') or str(uuid.uuid4())
            
            user_profile = UserProfile(
                user_id=user_id,
                username=user_data['username'],
                email=user_data['email'],
                role=UserRole.MEMBER,
                reputation_score=0,
                reputation_level=ReputationLevel.NEWCOMER,
                contributions_count=0,
                downloads_count=0,
                ratings_given=0,
                expertise_areas=user_data.get('expertise_areas', []),
                badges=[],
                join_date=datetime.utcnow(),
                last_active=datetime.utcnow(),
                bio=user_data.get('bio'),
                location=user_data.get('location'),
                website=user_data.get('website')
            )
            
            self.users[user_id] = user_profile
            
            # Award first-time registration points
            await self.reputation_system.award_reputation(user_id, 'registration', user_id)
            
            self.logger.info(f"User registered: {user_profile.username} ({user_id})")
            return user_profile
            
        except Exception as e:
            self.logger.error(f"User registration failed: {e}")
            raise
    
    async def submit_configuration(self, 
                                 user_id: str, 
                                 config_data: Dict[str, Any]) -> ConfigurationShare:
        """Submit configuration to community"""
        try:
            if user_id not in self.users:
                raise ValueError("User not found")
            
            user_profile = self.users[user_id]
            share_id = str(uuid.uuid4())
            
            submission = ConfigurationShare(
                share_id=share_id,
                title=config_data['title'],
                description=config_data['description'],
                author_id=user_id,
                share_type=ShareType(config_data.get('type', 'configuration')),
                status=ContributionStatus.PENDING,
                configuration_data=config_data['configuration'],
                hardware_profile=config_data['hardware_profile'],
                performance_metrics=config_data.get('performance_metrics', {}),
                tags=config_data.get('tags', []),
                category=config_data.get('category', 'general'),
                difficulty_level=config_data.get('difficulty_level', 'intermediate'),
                estimated_time=config_data.get('estimated_time', 30),
                prerequisites=config_data.get('prerequisites', []),
                compatibility_info=config_data.get('compatibility_info', {}),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            # Moderate submission
            approved, issues = await self.moderation_system.moderate_submission(submission, user_profile)
            
            if approved:
                submission.status = ContributionStatus.APPROVED
                # Award reputation for approved submission
                points = await self.reputation_system.award_reputation(
                    user_id, 'configuration_approved', share_id
                )
                
                # Update user profile
                user_profile.contributions_count += 1
                await self._update_user_reputation(user_id)
                
            else:
                submission.status = ContributionStatus.REJECTED
                self.logger.warning(f"Submission rejected: {', '.join(issues)}")
            
            # Store submission
            self.contributions[share_id] = submission
            
            # Record contribution
            contribution = UserContribution(
                contribution_id=str(uuid.uuid4()),
                user_id=user_id,
                share_id=share_id,
                contribution_type='upload',
                content={'issues': issues, 'approved': approved},
                timestamp=datetime.utcnow(),
                reputation_earned=points if approved else 0
            )
            
            if user_id not in self.user_contributions:
                self.user_contributions[user_id] = []
            self.user_contributions[user_id].append(contribution)
            
            self.logger.info(f"Configuration submitted: {submission.title} by {user_profile.username}")
            return submission
            
        except Exception as e:
            self.logger.error(f"Configuration submission failed: {e}")
            raise
    
    async def search_configurations(self, 
                                  search_params: Dict[str, Any]) -> List[ConfigurationShare]:
        """Search community configurations"""
        try:
            results = []
            
            # Get approved configurations
            approved_configs = [c for c in self.contributions.values() 
                              if c.status == ContributionStatus.APPROVED]
            
            # Apply filters
            if 'query' in search_params:
                query = search_params['query'].lower()
                approved_configs = [c for c in approved_configs 
                                  if query in c.title.lower() or query in c.description.lower()]
            
            if 'category' in search_params:
                category = search_params['category']
                approved_configs = [c for c in approved_configs if c.category == category]
            
            if 'tags' in search_params:
                required_tags = set(search_params['tags'])
                approved_configs = [c for c in approved_configs 
                                  if required_tags.intersection(set(c.tags))]
            
            if 'difficulty' in search_params:
                difficulty = search_params['difficulty']
                approved_configs = [c for c in approved_configs if c.difficulty_level == difficulty]
            
            if 'hardware_match' in search_params:
                # Hardware compatibility matching
                user_hardware = search_params['hardware_match']
                compatible_configs = []
                
                for config in approved_configs:
                    compatibility_score = await self._calculate_hardware_compatibility(
                        user_hardware, config.hardware_profile
                    )
                    if compatibility_score > 0.7:  # 70% compatibility threshold
                        compatible_configs.append(config)
                
                approved_configs = compatible_configs
            
            # Sort results
            sort_by = search_params.get('sort_by', 'rating')
            if sort_by == 'rating':
                results = sorted(approved_configs, key=lambda c: c.rating_average, reverse=True)
            elif sort_by == 'downloads':
                results = sorted(approved_configs, key=lambda c: c.downloads, reverse=True)
            elif sort_by == 'date':
                results = sorted(approved_configs, key=lambda c: c.created_at, reverse=True)
            else:
                results = approved_configs
            
            # Limit results
            limit = search_params.get('limit', 20)
            results = results[:limit]
            
            self.logger.info(f"Configuration search returned {len(results)} results")
            return results
            
        except Exception as e:
            self.logger.error(f"Configuration search failed: {e}")
            return []
    
    async def download_configuration(self, user_id: str, share_id: str) -> Optional[Dict[str, Any]]:
        """Download configuration from community"""
        try:
            if share_id not in self.contributions:
                return None
            
            config = self.contributions[share_id]
            
            if config.status != ContributionStatus.APPROVED:
                return None
            
            # Update download count
            config.downloads += 1
            config.views += 1
            
            # Update user download count
            if user_id in self.users:
                self.users[user_id].downloads_count += 1
            
            # Award reputation to author for download milestones
            if config.downloads in [100, 500, 1000]:
                milestone_action = f'download_milestone_{config.downloads}'
                await self.reputation_system.award_reputation(
                    config.author_id, milestone_action, share_id
                )
            
            # Return configuration data
            download_data = {
                'share_id': share_id,
                'title': config.title,
                'description': config.description,
                'configuration': config.configuration_data,
                'hardware_profile': config.hardware_profile,
                'performance_metrics': config.performance_metrics,
                'tags': config.tags,
                'author_id': config.author_id,
                'download_count': config.downloads,
                'rating': config.rating_average,
                'downloaded_at': datetime.utcnow().isoformat()
            }
            
            self.logger.info(f"Configuration downloaded: {config.title} by user {user_id}")
            return download_data
            
        except Exception as e:
            self.logger.error(f"Configuration download failed: {e}")
            return None
    
    async def rate_configuration(self, user_id: str, share_id: str, rating: int, review: Optional[str] = None) -> bool:
        """Rate and review a configuration"""
        try:
            if share_id not in self.contributions or user_id not in self.users:
                return False
            
            config = self.contributions[share_id]
            
            if config.author_id == user_id:
                self.logger.warning("Users cannot rate their own configurations")
                return False
            
            # Update configuration rating
            # In a real system, this would check for existing ratings
            config.rating_count += 1
            
            # Simple average calculation (would use more sophisticated system)
            current_total = config.rating_average * (config.rating_count - 1)
            new_total = current_total + rating
            config.rating_average = new_total / config.rating_count
            
            # Update user stats
            self.users[user_id].ratings_given += 1
            
            # Award reputation to configuration author for positive ratings
            if rating >= 4:
                await self.reputation_system.award_reputation(
                    config.author_id, 'helpful_rating_received', share_id
                )
            
            # Record contribution
            contribution = UserContribution(
                contribution_id=str(uuid.uuid4()),
                user_id=user_id,
                share_id=share_id,
                contribution_type='rating',
                content={'rating': rating, 'review': review},
                timestamp=datetime.utcnow()
            )
            
            if user_id not in self.user_contributions:
                self.user_contributions[user_id] = []
            self.user_contributions[user_id].append(contribution)
            
            self.logger.info(f"Configuration rated: {rating}/5 for {config.title}")
            return True
            
        except Exception as e:
            self.logger.error(f"Configuration rating failed: {e}")
            return False
    
    async def get_user_profile(self, user_id: str) -> Optional[UserProfile]:
        """Get user profile with updated stats"""
        try:
            if user_id not in self.users:
                return None
            
            await self._update_user_reputation(user_id)
            return self.users[user_id]
            
        except Exception as e:
            self.logger.error(f"User profile retrieval failed: {e}")
            return None
    
    async def get_trending_configurations(self, limit: int = 10) -> List[ConfigurationShare]:
        """Get trending configurations based on recent activity"""
        try:
            approved_configs = [c for c in self.contributions.values() 
                              if c.status == ContributionStatus.APPROVED]
            
            # Calculate trending score (combination of recent downloads, ratings, views)
            now = datetime.utcnow()
            
            def trending_score(config: ConfigurationShare) -> float:
                age_days = (now - config.created_at).days + 1
                recent_activity = config.downloads + config.rating_count + config.views
                
                # Weight recent activity higher, decay older content
                score = recent_activity / (age_days ** 0.5)
                
                # Bonus for high ratings
                if config.rating_average > 0:
                    score *= (config.rating_average / 5.0)
                
                return score
            
            trending = sorted(approved_configs, key=trending_score, reverse=True)
            
            return trending[:limit]
            
        except Exception as e:
            self.logger.error(f"Trending configurations retrieval failed: {e}")
            return []
    
    async def _update_user_reputation(self, user_id: str):
        """Update user reputation and badges"""
        try:
            if user_id not in self.users:
                return
            
            user_profile = self.users[user_id]
            
            # Calculate current reputation score
            new_score = await self.reputation_system.calculate_reputation_score(
                user_id, self.reputation_transactions
            )
            
            # Update reputation level
            old_level = user_profile.reputation_level
            new_level = self.reputation_system.get_reputation_level(new_score)
            
            user_profile.reputation_score = new_score
            user_profile.reputation_level = new_level
            
            # Check for new badges
            user_stats = await self._get_user_statistics(user_id)
            new_badges = self.reputation_system.check_badge_eligibility(user_profile, user_stats)
            
            for badge in new_badges:
                if badge not in user_profile.badges:
                    user_profile.badges.append(badge)
                    self.logger.info(f"Badge awarded to {user_profile.username}: {badge}")
            
            # Level up notification
            if new_level != old_level:
                self.logger.info(f"User {user_profile.username} leveled up: {old_level.value} -> {new_level.value}")
            
        except Exception as e:
            self.logger.error(f"User reputation update failed: {e}")
    
    async def _get_user_statistics(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive user statistics"""
        try:
            user_contribs = self.user_contributions.get(user_id, [])
            user_configs = [c for c in self.contributions.values() if c.author_id == user_id]
            
            stats = {
                'contributions': len(user_contribs),
                'helpful_contributions': len([c for c in user_contribs if c.contribution_type == 'rating' and c.content.get('rating', 0) >= 4]),
                'total_downloads': sum(c.downloads for c in user_configs),
                'issues_solved': len([c for c in user_contribs if c.contribution_type == 'troubleshooting']),
                'expert_reviews': len([c for c in user_contribs if c.contribution_type == 'review']),
                'configurations_uploaded': len(user_configs),
                'average_rating': statistics.mean([c.rating_average for c in user_configs if c.rating_average > 0]) if user_configs else 0
            }
            
            return stats
            
        except Exception as e:
            self.logger.error(f"User statistics calculation failed: {e}")
            return {}
    
    async def _calculate_hardware_compatibility(self, 
                                              user_hardware: Dict[str, Any], 
                                              config_hardware: Dict[str, Any]) -> float:
        """Calculate hardware compatibility score"""
        try:
            compatibility_score = 0.0
            total_weight = 0.0
            
            # Define component weights
            component_weights = {
                'cpu': 0.4,
                'memory': 0.3,
                'storage': 0.2,
                'gpu': 0.1
            }
            
            for component, weight in component_weights.items():
                if component in user_hardware and component in config_hardware:
                    total_weight += weight
                    
                    # Simple compatibility check (would be more sophisticated in practice)
                    user_spec = user_hardware[component]
                    config_spec = config_hardware[component]
                    
                    if isinstance(user_spec, dict) and isinstance(config_spec, dict):
                        # Compare specifications
                        component_score = self._compare_component_specs(user_spec, config_spec)
                        compatibility_score += component_score * weight
            
            if total_weight > 0:
                return compatibility_score / total_weight
            
            return 0.0
            
        except Exception as e:
            self.logger.error(f"Hardware compatibility calculation failed: {e}")
            return 0.0
    
    def _compare_component_specs(self, user_spec: Dict[str, Any], config_spec: Dict[str, Any]) -> float:
        """Compare individual component specifications"""
        # Simplified component comparison logic
        # In practice, this would be much more sophisticated
        
        score = 0.0
        comparisons = 0
        
        # Compare numeric values (assuming higher is better)
        for key in ['cores', 'frequency', 'memory_size', 'speed']:
            if key in user_spec and key in config_spec:
                try:
                    user_val = float(user_spec[key])
                    config_val = float(config_spec[key])
                    
                    if user_val >= config_val:
                        score += 1.0
                    else:
                        score += user_val / config_val
                    
                    comparisons += 1
                except (ValueError, TypeError):
                    pass
        
        # Compare string values (exact match)
        for key in ['brand', 'model', 'type']:
            if key in user_spec and key in config_spec:
                if user_spec[key].lower() == config_spec[key].lower():
                    score += 1.0
                else:
                    score += 0.5  # Partial compatibility
                comparisons += 1
        
        if comparisons > 0:
            return min(1.0, score / comparisons)
        
        return 0.5  # Default neutral compatibility
    
    async def _periodic_maintenance(self):
        """Periodic maintenance tasks"""
        while True:
            try:
                await asyncio.sleep(3600)  # Run every hour
                
                # Update user activity
                await self._update_user_activity()
                
                # Clean up old data
                await self._cleanup_old_data()
                
                # Save community data
                await self._save_community_data()
                
            except Exception as e:
                self.logger.error(f"Periodic maintenance failed: {e}")
    
    async def _update_featured_content(self):
        """Update featured content based on quality metrics"""
        while True:
            try:
                await asyncio.sleep(86400)  # Run daily
                
                for config in self.contributions.values():
                    if config.status == ContributionStatus.APPROVED:
                        if await self.moderation_system.check_for_featured_content(config):
                            config.status = ContributionStatus.FEATURED
                            
                            # Award reputation for featured content
                            await self.reputation_system.award_reputation(
                                config.author_id, 'configuration_featured', config.share_id
                            )
                
            except Exception as e:
                self.logger.error(f"Featured content update failed: {e}")
    
    async def _load_community_data(self):
        """Load community data from storage"""
        try:
            # Load users
            users_file = self.storage_path / 'users.json'
            if users_file.exists():
                with open(users_file, 'r') as f:
                    users_data = json.load(f)
                    for user_data in users_data:
                        user_data['join_date'] = datetime.fromisoformat(user_data['join_date'])
                        user_data['last_active'] = datetime.fromisoformat(user_data['last_active'])
                        user_data['role'] = UserRole(user_data['role'])
                        user_data['reputation_level'] = ReputationLevel(user_data['reputation_level'])
                        
                        user_profile = UserProfile(**user_data)
                        self.users[user_profile.user_id] = user_profile
            
            self.logger.info(f"Loaded {len(self.users)} community users")
            
        except Exception as e:
            self.logger.error(f"Community data loading failed: {e}")
    
    async def _save_community_data(self):
        """Save community data to storage"""
        try:
            # Save users
            users_data = []
            for user in self.users.values():
                user_dict = asdict(user)
                user_dict['join_date'] = user.join_date.isoformat()
                user_dict['last_active'] = user.last_active.isoformat()
                user_dict['role'] = user.role.value
                user_dict['reputation_level'] = user.reputation_level.value
                users_data.append(user_dict)
            
            users_file = self.storage_path / 'users.json'
            with open(users_file, 'w') as f:
                json.dump(users_data, f, indent=2)
            
            self.logger.debug("Community data saved successfully")
            
        except Exception as e:
            self.logger.error(f"Community data saving failed: {e}")