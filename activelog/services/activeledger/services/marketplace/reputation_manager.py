"""
Marketplace Reputation and Review System
Manages user reviews, ratings, and reputation scores for marketplace participants
"""

import asyncio
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Optional, List, Tuple
from datetime import datetime, timedelta
from enum import Enum
import logging
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, func, text

from ...models.database import (
    User, MarketplaceReview, MarketplaceTransaction, MarketplaceListing,
    ReputationScore, TransactionType, TransactionStatus, MarketplaceTransactionStatus
)
from ...config.settings import settings
from ..credits.cc_system import ComputeCreditSystem

logger = logging.getLogger(__name__)

class ReviewType(Enum):
    """Types of marketplace reviews"""
    BUYER_TO_SELLER = "buyer_to_seller"
    SELLER_TO_BUYER = "seller_to_buyer"

class ReputationManager:
    """Manages marketplace reviews and reputation scores"""
    
    def __init__(self, db: Session):
        self.db = db
        self.cc_system = ComputeCreditSystem(db)
        
        # Reputation scoring weights
        self.review_weight = Decimal("1.0")
        self.transaction_volume_weight = Decimal("0.3")
        self.completion_rate_weight = Decimal("0.5")
        self.response_time_weight = Decimal("0.2")
        self.dispute_penalty_weight = Decimal("0.8")
        
        # Rating thresholds
        self.excellent_threshold = Decimal("4.5")
        self.good_threshold = Decimal("4.0")
        self.fair_threshold = Decimal("3.0")
        
        # Incentive system
        self.review_reward_cc = Decimal("5")  # Reward for leaving reviews
        self.quality_seller_bonus = Decimal("10")  # Monthly bonus for top sellers
    
    async def create_review(
        self,
        transaction_id: str,
        reviewer_id: str,
        reviewee_id: str,
        rating: int,
        review_text: str,
        review_type: ReviewType,
        aspects: Optional[Dict[str, int]] = None
    ) -> MarketplaceReview:
        """Create a new marketplace review"""
        
        # Validate rating
        if not 1 <= rating <= 5:
            raise ValueError("Rating must be between 1 and 5")
        
        # Verify transaction exists and is completed
        transaction = (
            self.db.query(MarketplaceTransaction)
            .filter(MarketplaceTransaction.id == transaction_id)
            .first()
        )
        
        if not transaction:
            raise ValueError(f"Transaction {transaction_id} not found")
        
        if transaction.status != MarketplaceTransactionStatus.COMPLETED:
            raise ValueError("Can only review completed transactions")
        
        # Verify reviewer is part of the transaction
        if reviewer_id not in [transaction.buyer_id, transaction.seller_id]:
            raise ValueError("Only transaction participants can leave reviews")
        
        # Verify reviewee is the counterparty
        if review_type == ReviewType.BUYER_TO_SELLER:
            if reviewer_id != transaction.buyer_id or reviewee_id != transaction.seller_id:
                raise ValueError("Invalid reviewer/reviewee combination for buyer-to-seller review")
        elif review_type == ReviewType.SELLER_TO_BUYER:
            if reviewer_id != transaction.seller_id or reviewee_id != transaction.buyer_id:
                raise ValueError("Invalid reviewer/reviewee combination for seller-to-buyer review")
        
        # Check if review already exists
        existing_review = (
            self.db.query(MarketplaceReview)
            .filter(
                and_(
                    MarketplaceReview.transaction_id == transaction_id,
                    MarketplaceReview.reviewer_id == reviewer_id,
                    MarketplaceReview.review_type == review_type
                )
            )
            .first()
        )
        
        if existing_review:
            raise ValueError("Review already exists for this transaction")
        
        # Create review
        review = MarketplaceReview(
            transaction_id=transaction_id,
            reviewer_id=reviewer_id,
            reviewee_id=reviewee_id,
            rating=rating,
            review_text=review_text,
            review_type=review_type,
            aspects=aspects or {},
            is_verified=True  # All reviews are verified since they're tied to completed transactions
        )
        
        try:
            self.db.add(review)
            
            # Reward reviewer with CC credits
            await self.cc_system.add_credits(
                reviewer_id,
                self.review_reward_cc,
                TransactionType.REWARD,
                f"Review reward for transaction {transaction_id}",
                metadata={
                    "transaction_id": transaction_id,
                    "review_type": review_type.value,
                    "rating_given": rating,
                    "reviewee_id": reviewee_id
                }
            )
            
            # Update reputation scores
            await self._update_reputation_score(reviewee_id)
            
            self.db.commit()
            
            logger.info(
                f"Created {review_type.value} review: {reviewer_id} rated {reviewee_id} "
                f"{rating}/5 for transaction {transaction_id}"
            )
            
            return review
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create review: {str(e)}")
            raise
    
    async def _update_reputation_score(self, user_id: str):
        """Update comprehensive reputation score for a user"""
        
        # Get or create reputation score record
        reputation = (
            self.db.query(ReputationScore)
            .filter(ReputationScore.user_id == user_id)
            .first()
        )
        
        if not reputation:
            reputation = ReputationScore(user_id=user_id)
            self.db.add(reputation)
        
        # Calculate overall rating
        avg_rating_data = (
            self.db.query(
                func.avg(MarketplaceReview.rating).label("avg_rating"),
                func.count(MarketplaceReview.id).label("review_count")
            )
            .filter(MarketplaceReview.reviewee_id == user_id)
            .first()
        )
        
        avg_rating = avg_rating_data.avg_rating or Decimal("0")
        review_count = avg_rating_data.review_count or 0
        
        # Calculate transaction completion rate
        total_transactions = (
            self.db.query(func.count(MarketplaceTransaction.id))
            .filter(
                (MarketplaceTransaction.buyer_id == user_id) |
                (MarketplaceTransaction.seller_id == user_id)
            )
            .scalar() or 0
        )
        
        completed_transactions = (
            self.db.query(func.count(MarketplaceTransaction.id))
            .filter(
                and_(
                    (MarketplaceTransaction.buyer_id == user_id) |
                    (MarketplaceTransaction.seller_id == user_id),
                    MarketplaceTransaction.status == MarketplaceTransactionStatus.COMPLETED
                )
            )
            .scalar() or 0
        )
        
        completion_rate = (
            Decimal(completed_transactions) / Decimal(total_transactions)
            if total_transactions > 0 else Decimal("1")
        )
        
        # Calculate total transaction volume
        transaction_volume = (
            self.db.query(func.sum(MarketplaceTransaction.total_cost_cc))
            .filter(
                and_(
                    MarketplaceTransaction.seller_id == user_id,
                    MarketplaceTransaction.status == MarketplaceTransactionStatus.COMPLETED
                )
            )
            .scalar() or Decimal("0")
        )
        
        # Calculate dispute rate
        total_disputes = (
            self.db.query(func.count(MarketplaceTransaction.id))
            .filter(
                and_(
                    (MarketplaceTransaction.buyer_id == user_id) |
                    (MarketplaceTransaction.seller_id == user_id),
                    MarketplaceTransaction.dispute_initiated_at.isnot(None)
                )
            )
            .scalar() or 0
        )
        
        dispute_rate = (
            Decimal(total_disputes) / Decimal(total_transactions)
            if total_transactions > 0 else Decimal("0")
        )
        
        # Calculate response time (simplified - could be enhanced with actual message response times)
        avg_response_hours = Decimal("24")  # Default assumption
        
        # Compute comprehensive reputation score
        rating_component = avg_rating * self.review_weight
        
        volume_component = min(
            transaction_volume / Decimal("10000"),  # Normalize by $100 worth
            Decimal("5")
        ) * self.transaction_volume_weight
        
        completion_component = completion_rate * Decimal("5") * self.completion_rate_weight
        
        response_component = max(
            Decimal("5") - (avg_response_hours / Decimal("24")),
            Decimal("1")
        ) * self.response_time_weight
        
        dispute_penalty = dispute_rate * Decimal("5") * self.dispute_penalty_weight
        
        # Calculate final reputation score (0-5 scale)
        reputation_score = max(
            rating_component + volume_component + completion_component + response_component - dispute_penalty,
            Decimal("0")
        )
        
        # Update reputation record
        reputation.overall_rating = avg_rating
        reputation.review_count = review_count
        reputation.transaction_count = total_transactions
        reputation.completion_rate = completion_rate
        reputation.dispute_rate = dispute_rate
        reputation.total_sales_volume_cc = transaction_volume
        reputation.reputation_score = reputation_score
        reputation.last_updated = datetime.utcnow()
        
        # Determine reputation level
        if reputation_score >= self.excellent_threshold:
            reputation.reputation_level = "excellent"
        elif reputation_score >= self.good_threshold:
            reputation.reputation_level = "good"
        elif reputation_score >= self.fair_threshold:
            reputation.reputation_level = "fair"
        else:
            reputation.reputation_level = "poor"
        
        logger.info(f"Updated reputation for user {user_id}: {float(reputation_score):.2f} ({reputation.reputation_level})")
    
    async def get_user_reputation(self, user_id: str) -> Dict:
        """Get comprehensive reputation data for a user"""
        
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        reputation = (
            self.db.query(ReputationScore)
            .filter(ReputationScore.user_id == user_id)
            .first()
        )
        
        if not reputation:
            # Create initial reputation score
            await self._update_reputation_score(user_id)
            reputation = (
                self.db.query(ReputationScore)
                .filter(ReputationScore.user_id == user_id)
                .first()
            )
        
        # Get recent reviews
        recent_reviews = (
            self.db.query(MarketplaceReview)
            .filter(MarketplaceReview.reviewee_id == user_id)
            .order_by(desc(MarketplaceReview.created_at))
            .limit(10)
            .all()
        )
        
        # Get rating distribution
        rating_distribution = (
            self.db.query(
                MarketplaceReview.rating,
                func.count(MarketplaceReview.id).label("count")
            )
            .filter(MarketplaceReview.reviewee_id == user_id)
            .group_by(MarketplaceReview.rating)
            .all()
        )
        
        # Calculate aspect ratings
        aspect_ratings = await self._calculate_aspect_ratings(user_id)
        
        # Get badges/achievements
        badges = await self._get_user_badges(user_id, reputation)
        
        return {
            "user_id": user_id,
            "reputation_summary": {
                "reputation_score": float(reputation.reputation_score),
                "reputation_level": reputation.reputation_level,
                "overall_rating": float(reputation.overall_rating),
                "review_count": reputation.review_count,
                "transaction_count": reputation.transaction_count,
                "completion_rate": float(reputation.completion_rate * 100),
                "dispute_rate": float(reputation.dispute_rate * 100),
                "total_sales_volume_cc": float(reputation.total_sales_volume_cc),
                "last_updated": reputation.last_updated.isoformat()
            },
            "rating_distribution": {
                str(rating.rating): rating.count
                for rating in rating_distribution
            },
            "aspect_ratings": aspect_ratings,
            "recent_reviews": [
                {
                    "review_id": review.id,
                    "reviewer_id": review.reviewer_id,
                    "rating": review.rating,
                    "review_text": review.review_text[:200] + "..." if len(review.review_text) > 200 else review.review_text,
                    "review_type": review.review_type.value,
                    "created_at": review.created_at.isoformat(),
                    "aspects": review.aspects
                }
                for review in recent_reviews
            ],
            "badges": badges
        }
    
    async def _calculate_aspect_ratings(self, user_id: str) -> Dict[str, float]:
        """Calculate average ratings for different aspects"""
        
        # Get all reviews with aspects
        reviews_with_aspects = (
            self.db.query(MarketplaceReview)
            .filter(
                and_(
                    MarketplaceReview.reviewee_id == user_id,
                    MarketplaceReview.aspects.isnot(None)
                )
            )
            .all()
        )
        
        # Aggregate aspect ratings
        aspect_totals = {}
        aspect_counts = {}
        
        for review in reviews_with_aspects:
            for aspect, rating in review.aspects.items():
                if aspect not in aspect_totals:
                    aspect_totals[aspect] = 0
                    aspect_counts[aspect] = 0
                aspect_totals[aspect] += rating
                aspect_counts[aspect] += 1
        
        # Calculate averages
        aspect_averages = {}
        for aspect in aspect_totals:
            aspect_averages[aspect] = aspect_totals[aspect] / aspect_counts[aspect]
        
        return aspect_averages
    
    async def _get_user_badges(self, user_id: str, reputation: ReputationScore) -> List[Dict]:
        """Get user badges and achievements"""
        
        badges = []
        
        # Review count badges
        if reputation.review_count >= 100:
            badges.append({"name": "Review Master", "description": "Received 100+ reviews", "type": "milestone"})
        elif reputation.review_count >= 50:
            badges.append({"name": "Well Reviewed", "description": "Received 50+ reviews", "type": "milestone"})
        elif reputation.review_count >= 10:
            badges.append({"name": "Reviewed", "description": "Received 10+ reviews", "type": "milestone"})
        
        # Rating badges
        if reputation.overall_rating >= 4.8:
            badges.append({"name": "Exceptional", "description": "Maintains 4.8+ star rating", "type": "quality"})
        elif reputation.overall_rating >= 4.5:
            badges.append({"name": "Excellent", "description": "Maintains 4.5+ star rating", "type": "quality"})
        elif reputation.overall_rating >= 4.0:
            badges.append({"name": "Great", "description": "Maintains 4.0+ star rating", "type": "quality"})
        
        # Transaction volume badges
        if reputation.total_sales_volume_cc >= 100000:  # $1000+ in sales
            badges.append({"name": "Power Seller", "description": "$1000+ in total sales", "type": "volume"})
        elif reputation.total_sales_volume_cc >= 50000:  # $500+ in sales
            badges.append({"name": "Top Seller", "description": "$500+ in total sales", "type": "volume"})
        elif reputation.total_sales_volume_cc >= 10000:  # $100+ in sales
            badges.append({"name": "Active Seller", "description": "$100+ in total sales", "type": "volume"})
        
        # Reliability badges
        if reputation.completion_rate >= 0.99:
            badges.append({"name": "Ultra Reliable", "description": "99%+ completion rate", "type": "reliability"})
        elif reputation.completion_rate >= 0.95:
            badges.append({"name": "Reliable", "description": "95%+ completion rate", "type": "reliability"})
        
        # Low dispute rate badge
        if reputation.dispute_rate <= 0.01 and reputation.transaction_count >= 20:
            badges.append({"name": "Dispute-Free", "description": "Very low dispute rate", "type": "trustworthy"})
        
        return badges
    
    async def get_marketplace_leaderboard(
        self,
        category: str = "overall",
        limit: int = 20,
        time_period: Optional[str] = None
    ) -> List[Dict]:
        """Get marketplace leaderboard"""
        
        base_query = self.db.query(ReputationScore, User).join(User, ReputationScore.user_id == User.id)
        
        # Apply time period filter if specified
        if time_period:
            if time_period == "monthly":
                cutoff_date = datetime.utcnow() - timedelta(days=30)
                # Filter by users with recent activity
                base_query = base_query.filter(ReputationScore.last_updated >= cutoff_date)
            elif time_period == "yearly":
                cutoff_date = datetime.utcnow() - timedelta(days=365)
                base_query = base_query.filter(ReputationScore.last_updated >= cutoff_date)
        
        # Order by category
        if category == "overall":
            ordered_query = base_query.order_by(desc(ReputationScore.reputation_score))
        elif category == "rating":
            ordered_query = base_query.order_by(
                desc(ReputationScore.overall_rating),
                desc(ReputationScore.review_count)
            )
        elif category == "volume":
            ordered_query = base_query.order_by(desc(ReputationScore.total_sales_volume_cc))
        elif category == "reviews":
            ordered_query = base_query.order_by(desc(ReputationScore.review_count))
        else:
            ordered_query = base_query.order_by(desc(ReputationScore.reputation_score))
        
        results = ordered_query.limit(limit).all()
        
        return [
            {
                "rank": idx + 1,
                "user_id": result.User.id,
                "username": result.User.username,
                "reputation_score": float(result.ReputationScore.reputation_score),
                "overall_rating": float(result.ReputationScore.overall_rating),
                "review_count": result.ReputationScore.review_count,
                "transaction_count": result.ReputationScore.transaction_count,
                "total_sales_volume_cc": float(result.ReputationScore.total_sales_volume_cc),
                "reputation_level": result.ReputationScore.reputation_level,
                "completion_rate": float(result.ReputationScore.completion_rate * 100)
            }
            for idx, result in enumerate(results)
        ]
    
    async def moderate_review(
        self,
        review_id: str,
        moderator_id: str,
        action: str,
        reason: str
    ) -> MarketplaceReview:
        """Moderate a review (hide, approve, flag)"""
        
        review = self.db.query(MarketplaceReview).filter(MarketplaceReview.id == review_id).first()
        if not review:
            raise ValueError(f"Review {review_id} not found")
        
        if action == "hide":
            review.is_hidden = True
            review.moderation_reason = reason
        elif action == "flag":
            review.is_flagged = True
            review.moderation_reason = reason
        elif action == "approve":
            review.is_hidden = False
            review.is_flagged = False
            review.moderation_reason = None
        else:
            raise ValueError(f"Invalid moderation action: {action}")
        
        review.moderated_by = moderator_id
        review.moderated_at = datetime.utcnow()
        
        self.db.commit()
        
        # Update reputation scores if review visibility changed
        if action in ["hide", "approve"]:
            await self._update_reputation_score(review.reviewee_id)
        
        logger.info(f"Moderated review {review_id}: {action} by {moderator_id}")
        return review
    
    async def get_review_analytics(self, admin_id: str) -> Dict:
        """Get review system analytics for administrators"""
        
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        
        # Total reviews
        total_reviews = self.db.query(func.count(MarketplaceReview.id)).scalar() or 0
        
        # Recent reviews
        recent_reviews = (
            self.db.query(func.count(MarketplaceReview.id))
            .filter(MarketplaceReview.created_at >= thirty_days_ago)
            .scalar() or 0
        )
        
        # Average rating
        avg_rating = (
            self.db.query(func.avg(MarketplaceReview.rating))
            .scalar() or Decimal("0")
        )
        
        # Rating distribution
        rating_distribution = (
            self.db.query(
                MarketplaceReview.rating,
                func.count(MarketplaceReview.id).label("count")
            )
            .group_by(MarketplaceReview.rating)
            .all()
        )
        
        # Moderation stats
        flagged_reviews = (
            self.db.query(func.count(MarketplaceReview.id))
            .filter(MarketplaceReview.is_flagged == True)
            .scalar() or 0
        )
        
        hidden_reviews = (
            self.db.query(func.count(MarketplaceReview.id))
            .filter(MarketplaceReview.is_hidden == True)
            .scalar() or 0
        )
        
        # Top reviewers (by review count)
        top_reviewers = (
            self.db.query(
                MarketplaceReview.reviewer_id,
                func.count(MarketplaceReview.id).label("review_count")
            )
            .group_by(MarketplaceReview.reviewer_id)
            .order_by(desc("review_count"))
            .limit(10)
            .all()
        )
        
        return {
            "overview": {
                "total_reviews": total_reviews,
                "recent_reviews_30d": recent_reviews,
                "average_rating": float(avg_rating),
                "flagged_reviews": flagged_reviews,
                "hidden_reviews": hidden_reviews
            },
            "rating_distribution": {
                str(rating.rating): rating.count
                for rating in rating_distribution
            },
            "top_reviewers": [
                {
                    "reviewer_id": reviewer.reviewer_id,
                    "review_count": reviewer.review_count
                }
                for reviewer in top_reviewers
            ]
        }
    
    async def process_monthly_reputation_rewards(self) -> Dict[str, int]:
        """Process monthly rewards for top-rated sellers"""
        
        # Get top sellers by reputation score
        top_sellers = (
            self.db.query(ReputationScore)
            .filter(
                and_(
                    ReputationScore.reputation_level == "excellent",
                    ReputationScore.transaction_count >= 10  # Minimum activity requirement
                )
            )
            .order_by(desc(ReputationScore.reputation_score))
            .limit(10)
            .all()
        )
        
        results = {"rewarded": 0, "failed": 0}
        
        for seller_reputation in top_sellers:
            try:
                # Award monthly bonus
                await self.cc_system.add_credits(
                    seller_reputation.user_id,
                    self.quality_seller_bonus,
                    TransactionType.REWARD,
                    "Monthly quality seller bonus",
                    metadata={
                        "reputation_score": str(seller_reputation.reputation_score),
                        "reputation_level": seller_reputation.reputation_level,
                        "reward_type": "monthly_excellence_bonus"
                    }
                )
                
                results["rewarded"] += 1
                
            except Exception as e:
                logger.error(f"Failed to reward seller {seller_reputation.user_id}: {str(e)}")
                results["failed"] += 1
        
        logger.info(f"Processed monthly reputation rewards: {results}")
        return results