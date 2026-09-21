"""
Content rating and review system
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
import uuid
from ..models.base import Review, Product, ProductStatus

class ReviewStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    FLAGGED = "flagged"
    HIDDEN = "hidden"

class FlagReason(Enum):
    INAPPROPRIATE = "inappropriate"
    SPAM = "spam"
    FAKE_REVIEW = "fake_review"
    PERSONAL_ATTACK = "personal_attack"
    OFF_TOPIC = "off_topic"
    SPOILERS = "spoilers"

class ReviewVerification(Enum):
    VERIFIED_PURCHASE = "verified_purchase"
    COMMUNITY_CONTRIBUTOR = "community_contributor"
    EARLY_ACCESS = "early_access"
    PRESS_REVIEW = "press_review"

class ReviewSystem:
    """Manages content ratings and reviews"""
    
    def __init__(self):
        self.reviews: Dict[str, Review] = {}
        self.product_ratings: Dict[str, Dict[str, Any]] = {}  # product_id -> rating_data
        self.user_reviews: Dict[str, List[str]] = {}  # user_id -> review_ids
        self.review_flags: Dict[str, List[Dict[str, Any]]] = {}  # review_id -> flags
        self.helpful_votes: Dict[str, Dict[str, bool]] = {}  # review_id -> {user_id: helpful}
        self.moderation_queue: List[str] = []  # review_ids pending moderation
        
        # Initialize system settings
        self._initialize_system_settings()
    
    def _initialize_system_settings(self):
        """Initialize review system settings"""
        
        self.system_settings = {
            "min_review_length": 10,
            "max_review_length": 5000,
            "require_purchase_for_review": True,
            "auto_approve_verified": True,
            "review_cooldown_hours": 24,
            "max_reviews_per_user_per_product": 1,
            "min_helpful_votes_for_featured": 5,
            "auto_flag_threshold": 3,  # Auto-flag after 3 reports
            "spam_detection_enabled": True
        }
        
        # Rating weights for different aspects
        self.rating_aspects = {
            "overall": {"weight": 1.0, "required": True},
            "quality": {"weight": 0.3, "required": False},
            "value": {"weight": 0.2, "required": False},
            "ease_of_use": {"weight": 0.2, "required": False},
            "creativity": {"weight": 0.2, "required": False},
            "accuracy": {"weight": 0.1, "required": False}
        }
        
        # Content quality indicators
        self.quality_indicators = {
            "detailed_feedback": 2,  # Bonus points for detailed reviews
            "helpful_votes": 1,      # Points per helpful vote
            "verified_purchase": 3,  # Bonus for verified purchases
            "early_reviewer": 1,     # Bonus for early reviewers
            "constructive_criticism": 2  # Bonus for constructive feedback
        }
    
    def submit_review(
        self,
        user_id: str,
        product_id: str,
        rating: int,
        review_text: str,
        aspect_ratings: Dict[str, int] = None,
        is_verified_purchase: bool = False,
        is_early_access: bool = False,
        tags: List[str] = None
    ) -> str:
        """Submit a product review"""
        
        # Validate inputs
        if not 1 <= rating <= 5:
            raise ValueError("Rating must be between 1 and 5")
        
        if len(review_text) < self.system_settings["min_review_length"]:
            raise ValueError(f"Review must be at least {self.system_settings['min_review_length']} characters")
        
        if len(review_text) > self.system_settings["max_review_length"]:
            raise ValueError(f"Review must be less than {self.system_settings['max_review_length']} characters")
        
        # Check if user can review this product
        if not self._can_user_review(user_id, product_id, is_verified_purchase):
            raise ValueError("User cannot review this product")
        
        # Check for duplicate reviews
        if self._user_has_reviewed_product(user_id, product_id):
            raise ValueError("User has already reviewed this product")
        
        # Determine verification status
        verification = None
        if is_verified_purchase:
            verification = ReviewVerification.VERIFIED_PURCHASE
        elif is_early_access:
            verification = ReviewVerification.EARLY_ACCESS
        
        # Create review
        review = Review(
            user_id=user_id,
            product_id=product_id,
            rating=rating,
            review_text=review_text,
            aspect_ratings=aspect_ratings or {},
            verification=verification.value if verification else None,
            tags=tags or [],
            helpful_votes=0,
            total_votes=0,
            status=ReviewStatus.PENDING
        )
        
        self.reviews[review.id] = review
        
        # Track user reviews
        if user_id not in self.user_reviews:
            self.user_reviews[user_id] = []
        self.user_reviews[user_id].append(review.id)
        
        # Auto-approve if eligible
        if self._should_auto_approve(review):
            self.approve_review(review.id)
        else:
            # Add to moderation queue
            self.moderation_queue.append(review.id)
            review.status = ReviewStatus.PENDING
        
        # Check for spam
        if self.system_settings["spam_detection_enabled"]:
            if self._detect_spam(review):
                self.flag_review(review.id, FlagReason.SPAM, "system")
        
        return review.id
    
    def _can_user_review(self, user_id: str, product_id: str, is_verified_purchase: bool) -> bool:
        """Check if user can review this product"""
        
        # If purchase required, check verification
        if self.system_settings["require_purchase_for_review"] and not is_verified_purchase:
            return False
        
        # Check cooldown period
        recent_reviews = [
            r for r in self.user_reviews.get(user_id, [])
            if (self.reviews[r].created_at >= 
                datetime.utcnow() - timedelta(hours=self.system_settings["review_cooldown_hours"]))
        ]
        
        if len(recent_reviews) >= 3:  # Max 3 reviews per cooldown period
            return False
        
        return True
    
    def _user_has_reviewed_product(self, user_id: str, product_id: str) -> bool:
        """Check if user has already reviewed this product"""
        
        user_review_ids = self.user_reviews.get(user_id, [])
        
        for review_id in user_review_ids:
            if review_id in self.reviews:
                review = self.reviews[review_id]
                if review.product_id == product_id:
                    return True
        
        return False
    
    def _should_auto_approve(self, review: Review) -> bool:
        """Determine if review should be auto-approved"""
        
        if not self.system_settings["auto_approve_verified"]:
            return False
        
        # Auto-approve verified purchases with good content
        if (review.verification == ReviewVerification.VERIFIED_PURCHASE.value and
            len(review.review_text) >= 50 and  # Substantial content
            not self._contains_suspicious_content(review.review_text)):
            return True
        
        return False
    
    def _contains_suspicious_content(self, text: str) -> bool:
        """Check for suspicious content patterns"""
        
        suspicious_patterns = [
            "buy now", "click here", "www.", "http", "email me",
            "contact me", "fake", "scam", "terrible", "worst ever"
        ]
        
        text_lower = text.lower()
        return any(pattern in text_lower for pattern in suspicious_patterns)
    
    def _detect_spam(self, review: Review) -> bool:
        """Simple spam detection"""
        
        # Check for repeated characters
        text = review.review_text
        if any(char * 5 in text for char in 'abcdefghijklmnopqrstuvwxyz'):
            return True
        
        # Check for excessive caps
        if sum(1 for c in text if c.isupper()) > len(text) * 0.7:
            return True
        
        # Check for promotional content
        if self._contains_suspicious_content(text):
            return True
        
        return False
    
    def approve_review(self, review_id: str, moderator_id: Optional[str] = None) -> bool:
        """Approve a review"""
        
        if review_id not in self.reviews:
            return False
        
        review = self.reviews[review_id]
        
        if review.status != ReviewStatus.PENDING:
            return False
        
        review.status = ReviewStatus.APPROVED
        review.approved_at = datetime.utcnow()
        
        if moderator_id:
            review.moderated_by = moderator_id
        
        # Update product rating
        self._update_product_rating(review.product_id)
        
        # Remove from moderation queue
        if review_id in self.moderation_queue:
            self.moderation_queue.remove(review_id)
        
        return True
    
    def reject_review(self, review_id: str, moderator_id: str, reason: str) -> bool:
        """Reject a review"""
        
        if review_id not in self.reviews:
            return False
        
        review = self.reviews[review_id]
        review.status = ReviewStatus.REJECTED
        review.rejected_at = datetime.utcnow()
        review.moderated_by = moderator_id
        review.rejection_reason = reason
        
        # Remove from moderation queue
        if review_id in self.moderation_queue:
            self.moderation_queue.remove(review_id)
        
        return True
    
    def flag_review(self, review_id: str, flag_reason: FlagReason, flagger_user_id: str) -> bool:
        """Flag a review for moderation"""
        
        if review_id not in self.reviews:
            return False
        
        if review_id not in self.review_flags:
            self.review_flags[review_id] = []
        
        # Check if user already flagged this review
        existing_flags = [f for f in self.review_flags[review_id] if f["user_id"] == flagger_user_id]
        if existing_flags:
            return False  # User already flagged this review
        
        flag_entry = {
            "user_id": flagger_user_id,
            "reason": flag_reason.value,
            "flagged_at": datetime.utcnow()
        }
        
        self.review_flags[review_id].append(flag_entry)
        
        # Auto-hide if threshold reached
        if len(self.review_flags[review_id]) >= self.system_settings["auto_flag_threshold"]:
            review = self.reviews[review_id]
            review.status = ReviewStatus.FLAGGED
            
            # Add to moderation queue if not already there
            if review_id not in self.moderation_queue:
                self.moderation_queue.append(review_id)
        
        return True
    
    def vote_helpful(self, review_id: str, user_id: str, is_helpful: bool) -> bool:
        """Vote on review helpfulness"""
        
        if review_id not in self.reviews:
            return False
        
        if review_id not in self.helpful_votes:
            self.helpful_votes[review_id] = {}
        
        # Record vote
        old_vote = self.helpful_votes[review_id].get(user_id)
        self.helpful_votes[review_id][user_id] = is_helpful
        
        # Update review counts
        review = self.reviews[review_id]
        
        if old_vote is None:
            # New vote
            review.total_votes += 1
            if is_helpful:
                review.helpful_votes += 1
        elif old_vote != is_helpful:
            # Changed vote
            if is_helpful:
                review.helpful_votes += 1
            else:
                review.helpful_votes -= 1
        
        # Update helpfulness score
        if review.total_votes > 0:
            review.helpfulness_score = review.helpful_votes / review.total_votes
        
        return True
    
    def _update_product_rating(self, product_id: str):
        """Update product's overall rating"""
        
        # Get all approved reviews for product
        product_reviews = [
            r for r in self.reviews.values()
            if (r.product_id == product_id and r.status == ReviewStatus.APPROVED)
        ]
        
        if not product_reviews:
            return
        
        # Calculate weighted average
        total_weight = 0
        weighted_sum = 0
        
        for review in product_reviews:
            weight = 1.0
            
            # Give more weight to verified purchases
            if review.verification == ReviewVerification.VERIFIED_PURCHASE.value:
                weight *= 1.2
            
            # Give more weight to helpful reviews
            if review.helpful_votes > 3:
                weight *= 1.1
            
            # Give less weight to very short reviews
            if len(review.review_text) < 50:
                weight *= 0.8
            
            weighted_sum += review.rating * weight
            total_weight += weight
        
        average_rating = weighted_sum / total_weight if total_weight > 0 else 0
        
        # Calculate rating distribution
        rating_distribution = {}
        for i in range(1, 6):
            rating_distribution[i] = sum(1 for r in product_reviews if r.rating == i)
        
        # Store product rating data
        self.product_ratings[product_id] = {
            "average_rating": Decimal(str(round(average_rating, 2))),
            "review_count": len(product_reviews),
            "rating_distribution": rating_distribution,
            "last_updated": datetime.utcnow()
        }
    
    def get_product_reviews(
        self,
        product_id: str,
        sort_by: str = "helpful",
        filter_rating: Optional[int] = None,
        verified_only: bool = False,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """Get reviews for a product"""
        
        # Get all approved reviews for product
        product_reviews = [
            r for r in self.reviews.values()
            if (r.product_id == product_id and r.status == ReviewStatus.APPROVED)
        ]
        
        # Apply filters
        if filter_rating:
            product_reviews = [r for r in product_reviews if r.rating == filter_rating]
        
        if verified_only:
            product_reviews = [r for r in product_reviews if r.verification == ReviewVerification.VERIFIED_PURCHASE.value]
        
        # Sort reviews
        if sort_by == "helpful":
            product_reviews.sort(key=lambda r: (r.helpful_votes, r.created_at), reverse=True)
        elif sort_by == "recent":
            product_reviews.sort(key=lambda r: r.created_at, reverse=True)
        elif sort_by == "rating_high":
            product_reviews.sort(key=lambda r: (r.rating, r.helpful_votes), reverse=True)
        elif sort_by == "rating_low":
            product_reviews.sort(key=lambda r: (r.rating, r.helpful_votes))
        
        # Paginate
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_reviews = product_reviews[start_idx:end_idx]
        
        # Get product rating summary
        rating_summary = self.product_ratings.get(product_id, {
            "average_rating": Decimal("0"),
            "review_count": 0,
            "rating_distribution": {i: 0 for i in range(1, 6)}
        })
        
        return {
            "product_id": product_id,
            "rating_summary": rating_summary,
            "reviews": [self._format_review_for_display(r) for r in paginated_reviews],
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_reviews": len(product_reviews),
                "total_pages": (len(product_reviews) - 1) // page_size + 1 if product_reviews else 0
            },
            "filters_applied": {
                "rating_filter": filter_rating,
                "verified_only": verified_only,
                "sort_by": sort_by
            }
        }
    
    def _format_review_for_display(self, review: Review) -> Dict[str, Any]:
        """Format review for display to users"""
        
        return {
            "id": review.id,
            "user_id": review.user_id[:8] + "***",  # Partially hide user ID
            "rating": review.rating,
            "review_text": review.review_text,
            "aspect_ratings": review.aspect_ratings,
            "verification": review.verification,
            "tags": review.tags,
            "helpful_votes": review.helpful_votes,
            "total_votes": review.total_votes,
            "helpfulness_score": review.helpfulness_score,
            "created_at": review.created_at,
            "is_featured": self._is_featured_review(review)
        }
    
    def _is_featured_review(self, review: Review) -> bool:
        """Determine if review should be featured"""
        
        return (review.helpful_votes >= self.system_settings["min_helpful_votes_for_featured"] and
                review.verification == ReviewVerification.VERIFIED_PURCHASE.value and
                len(review.review_text) >= 100)
    
    def get_featured_reviews(self, product_id: str, count: int = 3) -> List[Dict[str, Any]]:
        """Get featured reviews for a product"""
        
        product_reviews = [
            r for r in self.reviews.values()
            if (r.product_id == product_id and 
                r.status == ReviewStatus.APPROVED and
                self._is_featured_review(r))
        ]
        
        # Sort by helpfulness and rating
        product_reviews.sort(
            key=lambda r: (r.helpful_votes, r.rating, len(r.review_text)), 
            reverse=True
        )
        
        return [self._format_review_for_display(r) for r in product_reviews[:count]]
    
    def get_review_summary_stats(self, product_id: str) -> Dict[str, Any]:
        """Get detailed review statistics"""
        
        product_reviews = [
            r for r in self.reviews.values()
            if (r.product_id == product_id and r.status == ReviewStatus.APPROVED)
        ]
        
        if not product_reviews:
            return {"no_reviews": True}
        
        # Calculate various metrics
        avg_rating = sum(r.rating for r in product_reviews) / len(product_reviews)
        
        # Aspect rating averages
        aspect_averages = {}
        for aspect in self.rating_aspects:
            ratings = [r.aspect_ratings.get(aspect) for r in product_reviews 
                      if aspect in r.aspect_ratings]
            if ratings:
                aspect_averages[aspect] = sum(ratings) / len(ratings)
        
        # Rating distribution over time
        recent_reviews = [r for r in product_reviews 
                         if r.created_at >= datetime.utcnow() - timedelta(days=30)]
        recent_avg = sum(r.rating for r in recent_reviews) / len(recent_reviews) if recent_reviews else 0
        
        # Most common tags
        all_tags = []
        for review in product_reviews:
            all_tags.extend(review.tags)
        
        tag_counts = {}
        for tag in all_tags:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
        
        popular_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return {
            "total_reviews": len(product_reviews),
            "average_rating": round(avg_rating, 2),
            "recent_average": round(recent_avg, 2),
            "aspect_ratings": aspect_averages,
            "rating_distribution": {
                i: sum(1 for r in product_reviews if r.rating == i)
                for i in range(1, 6)
            },
            "verification_stats": {
                "verified_purchases": sum(1 for r in product_reviews 
                                        if r.verification == ReviewVerification.VERIFIED_PURCHASE.value),
                "unverified": sum(1 for r in product_reviews if not r.verification)
            },
            "popular_tags": popular_tags,
            "review_trends": {
                "last_30_days": len(recent_reviews),
                "average_length": sum(len(r.review_text) for r in product_reviews) / len(product_reviews),
                "helpful_review_ratio": sum(1 for r in product_reviews if r.helpful_votes > 0) / len(product_reviews)
            }
        }
    
    def get_moderation_queue(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get reviews pending moderation"""
        
        queue_reviews = []
        
        for review_id in self.moderation_queue[:limit]:
            if review_id in self.reviews:
                review = self.reviews[review_id]
                flags = self.review_flags.get(review_id, [])
                
                queue_reviews.append({
                    "review": review.dict(),
                    "flags": flags,
                    "flag_count": len(flags),
                    "priority": self._calculate_moderation_priority(review, flags)
                })
        
        # Sort by priority (high priority first)
        queue_reviews.sort(key=lambda x: x["priority"], reverse=True)
        
        return queue_reviews
    
    def _calculate_moderation_priority(self, review: Review, flags: List[Dict[str, Any]]) -> int:
        """Calculate moderation priority score"""
        
        priority = 0
        
        # More flags = higher priority
        priority += len(flags) * 10
        
        # Recent flags are higher priority
        recent_flags = [f for f in flags 
                       if f["flagged_at"] >= datetime.utcnow() - timedelta(hours=24)]
        priority += len(recent_flags) * 5
        
        # Certain flag reasons are higher priority
        serious_reasons = [FlagReason.PERSONAL_ATTACK.value, FlagReason.INAPPROPRIATE.value]
        for flag in flags:
            if flag["reason"] in serious_reasons:
                priority += 20
        
        # New users get higher priority for review
        if review.created_at >= datetime.utcnow() - timedelta(days=7):
            priority += 5
        
        return priority
    
    def generate_review_analytics(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Generate system-wide review analytics"""
        
        # Get reviews in date range
        period_reviews = [
            r for r in self.reviews.values()
            if start_date <= r.created_at <= end_date
        ]
        
        if not period_reviews:
            return {"no_data": True, "period": {"start": start_date, "end": end_date}}
        
        # Overall stats
        total_reviews = len(period_reviews)
        approved_reviews = [r for r in period_reviews if r.status == ReviewStatus.APPROVED]
        rejected_reviews = [r for r in period_reviews if r.status == ReviewStatus.REJECTED]
        
        # Rating analysis
        if approved_reviews:
            avg_rating = sum(r.rating for r in approved_reviews) / len(approved_reviews)
            rating_dist = {i: sum(1 for r in approved_reviews if r.rating == i) for i in range(1, 6)}
        else:
            avg_rating = 0
            rating_dist = {i: 0 for i in range(1, 6)}
        
        # Review quality metrics
        quality_metrics = {
            "average_length": sum(len(r.review_text) for r in approved_reviews) / len(approved_reviews) if approved_reviews else 0,
            "verified_percentage": (sum(1 for r in approved_reviews 
                                      if r.verification == ReviewVerification.VERIFIED_PURCHASE.value) 
                                   / len(approved_reviews) * 100) if approved_reviews else 0,
            "helpful_reviews": sum(1 for r in approved_reviews if r.helpful_votes > 0),
            "average_helpful_votes": sum(r.helpful_votes for r in approved_reviews) / len(approved_reviews) if approved_reviews else 0
        }
        
        # Moderation stats
        moderation_stats = {
            "approval_rate": len(approved_reviews) / total_reviews * 100 if total_reviews > 0 else 0,
            "rejection_rate": len(rejected_reviews) / total_reviews * 100 if total_reviews > 0 else 0,
            "total_flags": sum(len(self.review_flags.get(r.id, [])) for r in period_reviews),
            "auto_approved": sum(1 for r in approved_reviews if not hasattr(r, 'moderated_by'))
        }
        
        # Top products by review volume
        product_review_counts = {}
        for review in approved_reviews:
            product_id = review.product_id
            product_review_counts[product_id] = product_review_counts.get(product_id, 0) + 1
        
        top_reviewed_products = sorted(product_review_counts.items(), 
                                     key=lambda x: x[1], reverse=True)[:10]
        
        return {
            "period": {
                "start_date": start_date,
                "end_date": end_date,
                "days": (end_date - start_date).days
            },
            "overall_stats": {
                "total_reviews": total_reviews,
                "approved_reviews": len(approved_reviews),
                "rejected_reviews": len(rejected_reviews),
                "pending_reviews": len([r for r in period_reviews if r.status == ReviewStatus.PENDING]),
                "average_rating": round(avg_rating, 2),
                "rating_distribution": rating_dist
            },
            "quality_metrics": quality_metrics,
            "moderation_stats": moderation_stats,
            "top_reviewed_products": top_reviewed_products,
            "generated_at": datetime.utcnow()
        }