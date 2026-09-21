"""
Reviews and Ratings System
Handles customer reviews, ratings, and product feedback management
"""

import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum
import re


class ReviewStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    FLAGGED = "flagged"
    SPAM = "spam"


class ReviewType(Enum):
    PRODUCT = "product"
    SERVICE = "service"
    PURCHASE = "purchase"


class RatingAspect(Enum):
    QUALITY = "quality"
    VALUE = "value"
    SHIPPING = "shipping"
    SERVICE = "service"
    DESIGN = "design"


@dataclass
class Review:
    review_id: str
    product_id: str
    customer_id: str
    order_id: Optional[str]
    rating: int  # 1-5 stars
    title: str
    content: str
    status: ReviewStatus
    helpful_votes: int
    not_helpful_votes: int
    verified_purchase: bool
    created_at: datetime
    updated_at: datetime


class ReviewsRatingsSystem:
    """Manages product reviews and ratings"""
    
    def __init__(self, config, db):
        self.config = config
        self.db = db
        
        # Review settings
        self.require_purchase_verification = config.get('require_purchase_verification', True)
        self.auto_approve_reviews = config.get('auto_approve_reviews', False)
        self.min_review_length = config.get('min_review_length', 10)
        self.max_review_length = config.get('max_review_length', 2000)
        
        # Rating settings
        self.enable_aspect_ratings = config.get('enable_aspect_ratings', True)
        self.require_rating_with_review = config.get('require_rating_with_review', True)
        self.allow_anonymous_reviews = config.get('allow_anonymous_reviews', False)
        
        # Moderation settings
        self.enable_spam_detection = config.get('enable_spam_detection', True)
        self.enable_profanity_filter = config.get('enable_profanity_filter', True)
        self.review_cooldown_hours = config.get('review_cooldown_hours', 24)
        
        # Incentive settings
        self.enable_review_rewards = config.get('enable_review_rewards', True)
        self.review_reward_points = config.get('review_reward_points', 10)
        
    def submit_review(self, review_data: Dict[str, Any]) -> Dict[str, Any]:
        """Submit new product review"""
        try:
            # Validate required fields
            required_fields = ['product_id', 'customer_id', 'rating', 'title', 'content']
            for field in required_fields:
                if field not in review_data or not review_data[field]:
                    raise ValueError(f"Missing required field: {field}")
                    
            product_id = review_data['product_id']
            customer_id = review_data['customer_id']
            rating = int(review_data['rating'])
            title = review_data['title'].strip()
            content = review_data['content'].strip()
            order_id = review_data.get('order_id')
            
            # Validate rating range
            if rating < 1 or rating > 5:
                raise ValueError("Rating must be between 1 and 5 stars")
                
            # Validate content length
            if len(content) < self.min_review_length:
                raise ValueError(f"Review must be at least {self.min_review_length} characters long")
            if len(content) > self.max_review_length:
                raise ValueError(f"Review cannot exceed {self.max_review_length} characters")
                
            # Check if product exists
            product = self.db.get_product(product_id)
            if not product:
                raise ValueError("Product not found")
                
            # Check if customer has already reviewed this product
            existing_review = self.db.get_customer_product_review(customer_id, product_id)
            if existing_review:
                raise ValueError("You have already reviewed this product")
                
            # Check review cooldown
            if self.review_cooldown_hours > 0:
                last_review = self.db.get_customer_last_review(customer_id)
                if last_review:
                    last_review_time = datetime.fromisoformat(last_review['created_at'])
                    cooldown_end = last_review_time + timedelta(hours=self.review_cooldown_hours)
                    if datetime.now() < cooldown_end:
                        raise ValueError(f"Please wait {self.review_cooldown_hours} hours before submitting another review")
                        
            # Verify purchase if required
            verified_purchase = False
            if self.require_purchase_verification:
                if order_id:
                    purchase_verification = self.verify_purchase(customer_id, product_id, order_id)
                    verified_purchase = purchase_verification['verified']
                    if not verified_purchase:
                        raise ValueError("You must purchase this product before reviewing it")
                else:
                    # Check if customer has any order with this product
                    purchase_verification = self.verify_any_purchase(customer_id, product_id)
                    verified_purchase = purchase_verification['verified']
                    if not verified_purchase:
                        raise ValueError("You must purchase this product before reviewing it")
                    order_id = purchase_verification.get('order_id')
                    
            # Content moderation
            moderation_result = self.moderate_review_content(title, content)
            if not moderation_result['approved']:
                raise ValueError(f"Review content not approved: {moderation_result['reason']}")
                
            # Generate review ID
            review_id = f"review_{datetime.now().timestamp()}"
            
            # Determine initial status
            initial_status = ReviewStatus.APPROVED if self.auto_approve_reviews else ReviewStatus.PENDING
            if moderation_result['flagged']:
                initial_status = ReviewStatus.FLAGGED
                
            # Create review record
            review = {
                'review_id': review_id,
                'product_id': product_id,
                'customer_id': customer_id,
                'order_id': order_id,
                'rating': rating,
                'title': title,
                'content': content,
                'status': initial_status.value,
                'verified_purchase': verified_purchase,
                'helpful_votes': 0,
                'not_helpful_votes': 0,
                'reported_count': 0,
                'aspect_ratings': review_data.get('aspect_ratings', {}),
                'images': review_data.get('images', []),
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            # Save review
            success = self.db.save_review(review)
            if not success:
                raise Exception("Failed to save review")
                
            # Update product rating statistics
            self.update_product_rating_stats(product_id)
            
            # Award points if enabled
            if self.enable_review_rewards and initial_status == ReviewStatus.APPROVED:
                self.award_review_points(customer_id, review_id)
                
            # Send notifications
            self.send_review_notifications(review_id)
            
            return {
                'success': True,
                'review_id': review_id,
                'status': initial_status.value,
                'verified_purchase': verified_purchase,
                'awaiting_approval': initial_status == ReviewStatus.PENDING,
                'message': 'Review submitted successfully' if initial_status == ReviewStatus.APPROVED else 'Review submitted and awaiting approval'
            }
            
        except Exception as e:
            raise Exception(f"Error submitting review: {e}")
            
    def get_product_reviews(self, product_id: str, filters: Dict[str, Any] = None, page: int = 1, limit: int = 20) -> Dict[str, Any]:
        """Get reviews for a product"""
        try:
            if filters is None:
                filters = {}
                
            # Only show approved reviews by default
            filters.setdefault('status', ReviewStatus.APPROVED.value)
            
            reviews = self.db.get_product_reviews(product_id, filters, page, limit)
            
            # Enrich review data
            enriched_reviews = []
            for review in reviews:
                enriched_review = self.enrich_review_data(review)
                enriched_reviews.append(enriched_review)
                
            # Get review statistics
            review_stats = self.get_product_review_stats(product_id)
            
            # Get total count for pagination
            total_count = self.db.get_product_review_count(product_id, filters)
            total_pages = (total_count + limit - 1) // limit
            
            return {
                'product_id': product_id,
                'reviews': enriched_reviews,
                'statistics': review_stats,
                'pagination': {
                    'page': page,
                    'limit': limit,
                    'total_count': total_count,
                    'total_pages': total_pages,
                    'has_next': page < total_pages,
                    'has_prev': page > 1
                },
                'filters_applied': filters
            }
            
        except Exception as e:
            raise Exception(f"Error getting product reviews: {e}")
            
    def get_customer_reviews(self, customer_id: str, page: int = 1, limit: int = 20) -> Dict[str, Any]:
        """Get reviews by customer"""
        try:
            reviews = self.db.get_customer_reviews(customer_id, page, limit)
            
            # Enrich review data
            enriched_reviews = []
            for review in reviews:
                enriched_review = self.enrich_review_data(review)
                enriched_reviews.append(enriched_review)
                
            # Get total count
            total_count = self.db.get_customer_review_count(customer_id)
            total_pages = (total_count + limit - 1) // limit
            
            return {
                'customer_id': customer_id,
                'reviews': enriched_reviews,
                'pagination': {
                    'page': page,
                    'limit': limit,
                    'total_count': total_count,
                    'total_pages': total_pages,
                    'has_next': page < total_pages,
                    'has_prev': page > 1
                }
            }
            
        except Exception as e:
            raise Exception(f"Error getting customer reviews: {e}")
            
    def update_review(self, review_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update existing review"""
        try:
            # Get existing review
            review = self.db.get_review(review_id)
            if not review:
                raise ValueError("Review not found")
                
            # Check if review can be updated (only pending or approved reviews)
            if review['status'] not in [ReviewStatus.PENDING.value, ReviewStatus.APPROVED.value]:
                raise ValueError("Review cannot be updated in its current status")
                
            # Validate updates
            updates = {}
            
            if 'rating' in update_data:
                rating = int(update_data['rating'])
                if rating < 1 or rating > 5:
                    raise ValueError("Rating must be between 1 and 5 stars")
                updates['rating'] = rating
                
            if 'title' in update_data:
                title = update_data['title'].strip()
                if not title:
                    raise ValueError("Title is required")
                updates['title'] = title
                
            if 'content' in update_data:
                content = update_data['content'].strip()
                if len(content) < self.min_review_length:
                    raise ValueError(f"Review must be at least {self.min_review_length} characters long")
                if len(content) > self.max_review_length:
                    raise ValueError(f"Review cannot exceed {self.max_review_length} characters")
                updates['content'] = content
                
            if 'aspect_ratings' in update_data:
                updates['aspect_ratings'] = update_data['aspect_ratings']
                
            # Content moderation for updated content
            if 'title' in updates or 'content' in updates:
                moderation_result = self.moderate_review_content(
                    updates.get('title', review['title']),
                    updates.get('content', review['content'])
                )
                
                if not moderation_result['approved']:
                    raise ValueError(f"Updated content not approved: {moderation_result['reason']}")
                    
                if moderation_result['flagged']:
                    updates['status'] = ReviewStatus.FLAGGED.value
                    
            # Update timestamps
            updates['updated_at'] = datetime.now().isoformat()
            
            # Save updates
            success = self.db.update_review(review_id, updates)
            if not success:
                raise Exception("Failed to update review")
                
            # Update product rating statistics if rating changed
            if 'rating' in updates:
                self.update_product_rating_stats(review['product_id'])
                
            return {
                'success': True,
                'review_id': review_id,
                'message': 'Review updated successfully'
            }
            
        except Exception as e:
            raise Exception(f"Error updating review: {e}")
            
    def delete_review(self, review_id: str, deletion_reason: Optional[str] = None) -> Dict[str, Any]:
        """Delete review (soft delete)"""
        try:
            review = self.db.get_review(review_id)
            if not review:
                raise ValueError("Review not found")
                
            # Soft delete - update status and add deletion info
            updates = {
                'status': ReviewStatus.REJECTED.value,
                'deleted_at': datetime.now().isoformat(),
                'deletion_reason': deletion_reason or 'Deleted by user',
                'updated_at': datetime.now().isoformat()
            }
            
            success = self.db.update_review(review_id, updates)
            if not success:
                raise Exception("Failed to delete review")
                
            # Update product rating statistics
            self.update_product_rating_stats(review['product_id'])
            
            return {
                'success': True,
                'review_id': review_id,
                'message': 'Review deleted successfully'
            }
            
        except Exception as e:
            raise Exception(f"Error deleting review: {e}")
            
    def vote_helpful(self, vote_data: Dict[str, Any]) -> Dict[str, Any]:
        """Vote on review helpfulness"""
        try:
            review_id = vote_data['review_id']
            customer_id = vote_data['customer_id']
            helpful = vote_data['helpful']  # True for helpful, False for not helpful
            
            # Check if customer already voted on this review
            existing_vote = self.db.get_review_vote(review_id, customer_id)
            if existing_vote:
                # Update existing vote if different
                if existing_vote['helpful'] != helpful:
                    self.db.update_review_vote(existing_vote['vote_id'], {
                        'helpful': helpful,
                        'updated_at': datetime.now().isoformat()
                    })
                    
                    # Update vote counts
                    self.update_review_vote_counts(review_id)
                    
                    return {
                        'success': True,
                        'review_id': review_id,
                        'vote_changed': True,
                        'message': 'Vote updated successfully'
                    }
                else:
                    return {
                        'success': True,
                        'review_id': review_id,
                        'vote_changed': False,
                        'message': 'Vote already recorded'
                    }
                    
            # Create new vote
            vote = {
                'vote_id': f"vote_{datetime.now().timestamp()}",
                'review_id': review_id,
                'customer_id': customer_id,
                'helpful': helpful,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            success = self.db.save_review_vote(vote)
            if not success:
                raise Exception("Failed to save vote")
                
            # Update vote counts
            self.update_review_vote_counts(review_id)
            
            return {
                'success': True,
                'review_id': review_id,
                'vote_id': vote['vote_id'],
                'helpful': helpful,
                'message': 'Vote recorded successfully'
            }
            
        except Exception as e:
            raise Exception(f"Error voting on review: {e}")
            
    def report_review(self, report_data: Dict[str, Any]) -> Dict[str, Any]:
        """Report review for moderation"""
        try:
            review_id = report_data['review_id']
            reporter_id = report_data['customer_id']
            reason = report_data['reason']
            details = report_data.get('details', '')
            
            # Check if customer already reported this review
            existing_report = self.db.get_review_report(review_id, reporter_id)
            if existing_report:
                return {
                    'success': True,
                    'review_id': review_id,
                    'already_reported': True,
                    'message': 'Review already reported by you'
                }
                
            # Create report
            report = {
                'report_id': f"report_{datetime.now().timestamp()}",
                'review_id': review_id,
                'reporter_id': reporter_id,
                'reason': reason,
                'details': details,
                'status': 'pending',
                'created_at': datetime.now().isoformat()
            }
            
            success = self.db.save_review_report(report)
            if not success:
                raise Exception("Failed to save report")
                
            # Update review reported count
            self.db.increment_review_report_count(review_id)
            
            # Auto-flag review if it has too many reports
            report_threshold = self.config.get('auto_flag_report_threshold', 3)
            current_reports = self.db.get_review_report_count(review_id)
            
            if current_reports >= report_threshold:
                self.db.update_review(review_id, {
                    'status': ReviewStatus.FLAGGED.value,
                    'updated_at': datetime.now().isoformat()
                })
                
            return {
                'success': True,
                'review_id': review_id,
                'report_id': report['report_id'],
                'message': 'Review reported for moderation'
            }
            
        except Exception as e:
            raise Exception(f"Error reporting review: {e}")
            
    def moderate_review(self, moderation_data: Dict[str, Any]) -> Dict[str, Any]:
        """Moderate review (admin function)"""
        try:
            review_id = moderation_data['review_id']
            action = moderation_data['action']  # 'approve', 'reject', 'flag'
            moderator_id = moderation_data['moderator_id']
            notes = moderation_data.get('notes', '')
            
            review = self.db.get_review(review_id)
            if not review:
                raise ValueError("Review not found")
                
            # Map action to status
            status_map = {
                'approve': ReviewStatus.APPROVED,
                'reject': ReviewStatus.REJECTED,
                'flag': ReviewStatus.FLAGGED
            }
            
            if action not in status_map:
                raise ValueError("Invalid moderation action")
                
            new_status = status_map[action]
            
            # Update review
            updates = {
                'status': new_status.value,
                'moderated_by': moderator_id,
                'moderated_at': datetime.now().isoformat(),
                'moderation_notes': notes,
                'updated_at': datetime.now().isoformat()
            }
            
            success = self.db.update_review(review_id, updates)
            if not success:
                raise Exception("Failed to moderate review")
                
            # Update product rating statistics
            self.update_product_rating_stats(review['product_id'])
            
            # Award or revoke points based on moderation
            if self.enable_review_rewards:
                if new_status == ReviewStatus.APPROVED and review['status'] != ReviewStatus.APPROVED.value:
                    self.award_review_points(review['customer_id'], review_id)
                elif new_status != ReviewStatus.APPROVED and review['status'] == ReviewStatus.APPROVED.value:
                    self.revoke_review_points(review['customer_id'], review_id)
                    
            # Close related reports if approved
            if new_status == ReviewStatus.APPROVED:
                self.db.close_review_reports(review_id)
                
            return {
                'success': True,
                'review_id': review_id,
                'action': action,
                'new_status': new_status.value,
                'message': f'Review {action}ed successfully'
            }
            
        except Exception as e:
            raise Exception(f"Error moderating review: {e}")
            
    def get_product_review_stats(self, product_id: str) -> Dict[str, Any]:
        """Get comprehensive review statistics for product"""
        try:
            stats = self.db.get_product_review_statistics(product_id)
            
            # Calculate additional metrics
            total_reviews = stats.get('total_reviews', 0)
            if total_reviews > 0:
                rating_distribution = stats.get('rating_distribution', {})
                
                # Calculate percentages
                rating_percentages = {}
                for rating in range(1, 6):
                    count = rating_distribution.get(str(rating), 0)
                    percentage = round((count / total_reviews) * 100, 1)
                    rating_percentages[str(rating)] = percentage
                    
                stats['rating_percentages'] = rating_percentages
                
            # Add aspect ratings if enabled
            if self.enable_aspect_ratings:
                aspect_stats = self.db.get_product_aspect_ratings(product_id)
                stats['aspect_ratings'] = aspect_stats
                
            return {
                'product_id': product_id,
                'average_rating': stats.get('average_rating', 0),
                'total_reviews': total_reviews,
                'rating_distribution': stats.get('rating_distribution', {}),
                'rating_percentages': stats.get('rating_percentages', {}),
                'verified_purchase_percentage': stats.get('verified_purchase_percentage', 0),
                'aspect_ratings': stats.get('aspect_ratings', {}),
                'recent_reviews_trend': stats.get('recent_reviews_trend', 0),
                'recommendation_percentage': self.calculate_recommendation_percentage(product_id)
            }
            
        except Exception as e:
            raise Exception(f"Error getting review statistics: {e}")
            
    def get_review_analytics(self, analytics_params: Dict[str, Any]) -> Dict[str, Any]:
        """Get review analytics and insights"""
        try:
            start_date = analytics_params.get('start_date', (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
            end_date = analytics_params.get('end_date', datetime.now().strftime('%Y-%m-%d'))
            
            analytics = self.db.get_review_analytics(start_date, end_date)
            
            return {
                'period': {
                    'start_date': start_date,
                    'end_date': end_date
                },
                'total_reviews': analytics.get('total_reviews', 0),
                'average_rating': analytics.get('average_rating', 0),
                'reviews_by_rating': analytics.get('reviews_by_rating', {}),
                'reviews_by_status': analytics.get('reviews_by_status', {}),
                'verified_purchase_rate': analytics.get('verified_purchase_rate', 0),
                'top_reviewed_products': analytics.get('top_reviewed_products', []),
                'most_helpful_reviewers': analytics.get('most_helpful_reviewers', []),
                'moderation_stats': {
                    'pending_reviews': analytics.get('pending_reviews', 0),
                    'flagged_reviews': analytics.get('flagged_reviews', 0),
                    'spam_detected': analytics.get('spam_detected', 0)
                }
            }
            
        except Exception as e:
            raise Exception(f"Error getting review analytics: {e}")
            
    def enrich_review_data(self, review: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich review data with additional information"""
        try:
            # Add customer information (public data only)
            if review.get('customer_id'):
                customer = self.db.get_customer(review['customer_id'])
                if customer:
                    review['customer_name'] = f"{customer.get('first_name', '')} {customer.get('last_name', '')}".strip()
                    review['customer_initial'] = customer.get('first_name', 'A')[0].upper()
                    
            # Add product information
            if review.get('product_id'):
                product = self.db.get_product(review['product_id'])
                if product:
                    review['product_name'] = product.get('name', '')
                    review['product_image'] = product.get('images', [None])[0]
                    
            # Add helpful vote ratio
            total_votes = review.get('helpful_votes', 0) + review.get('not_helpful_votes', 0)
            if total_votes > 0:
                review['helpfulness_ratio'] = round((review.get('helpful_votes', 0) / total_votes) * 100, 1)
            else:
                review['helpfulness_ratio'] = 0
                
            # Add time ago
            created_at = datetime.fromisoformat(review['created_at'])
            time_diff = datetime.now() - created_at
            review['time_ago'] = self.format_time_ago(time_diff)
            
            return review
            
        except Exception:
            return review
            
    def verify_purchase(self, customer_id: str, product_id: str, order_id: str) -> Dict[str, Any]:
        """Verify customer purchased the product"""
        try:
            # Check if order exists and belongs to customer
            order = self.db.get_order(order_id)
            if not order or order.get('customer_id') != customer_id:
                return {'verified': False, 'reason': 'Order not found or does not belong to customer'}
                
            # Check if order contains the product
            order_items = order.get('items', [])
            for item in order_items:
                if item.get('product_id') == product_id:
                    return {'verified': True, 'order_id': order_id}
                    
            return {'verified': False, 'reason': 'Product not found in order'}
            
        except Exception:
            return {'verified': False, 'reason': 'Verification failed'}
            
    def verify_any_purchase(self, customer_id: str, product_id: str) -> Dict[str, Any]:
        """Verify customer has purchased the product in any order"""
        try:
            purchase = self.db.get_customer_product_purchase(customer_id, product_id)
            if purchase:
                return {'verified': True, 'order_id': purchase.get('order_id')}
            else:
                return {'verified': False, 'reason': 'No purchase found for this product'}
        except Exception:
            return {'verified': False, 'reason': 'Verification failed'}
            
    def moderate_review_content(self, title: str, content: str) -> Dict[str, Any]:
        """Moderate review content for spam and inappropriate content"""
        try:
            flagged_reasons = []
            
            # Profanity filter
            if self.enable_profanity_filter:
                if self.contains_profanity(title) or self.contains_profanity(content):
                    flagged_reasons.append('Contains inappropriate language')
                    
            # Spam detection
            if self.enable_spam_detection:
                spam_indicators = self.detect_spam_indicators(title, content)
                if spam_indicators:
                    flagged_reasons.extend(spam_indicators)
                    
            # Check for promotional content
            if self.contains_promotional_content(content):
                flagged_reasons.append('Contains promotional content')
                
            return {
                'approved': len(flagged_reasons) == 0,
                'flagged': len(flagged_reasons) > 0,
                'reason': '; '.join(flagged_reasons) if flagged_reasons else None
            }
            
        except Exception:
            return {'approved': True, 'flagged': False}
            
    def contains_profanity(self, text: str) -> bool:
        """Check if text contains profanity"""
        try:
            # Simple profanity filter - in production, use a proper library
            profanity_words = ['spam', 'fake', 'scam']  # Simplified list
            text_lower = text.lower()
            return any(word in text_lower for word in profanity_words)
        except Exception:
            return False
            
    def detect_spam_indicators(self, title: str, content: str) -> List[str]:
        """Detect spam indicators in review content"""
        try:
            indicators = []
            combined_text = f"{title} {content}".lower()
            
            # Check for excessive capitalization
            if sum(1 for c in combined_text if c.isupper()) > len(combined_text) * 0.3:
                indicators.append('Excessive capitalization')
                
            # Check for repeated characters
            if re.search(r'(.)\1{4,}', combined_text):
                indicators.append('Repeated characters')
                
            # Check for promotional keywords
            promo_keywords = ['buy now', 'click here', 'visit our website', 'contact us']
            if any(keyword in combined_text for keyword in promo_keywords):
                indicators.append('Promotional language')
                
            # Check for excessive punctuation
            if combined_text.count('!') > 5 or combined_text.count('?') > 5:
                indicators.append('Excessive punctuation')
                
            return indicators
            
        except Exception:
            return []
            
    def contains_promotional_content(self, content: str) -> bool:
        """Check if content contains promotional material"""
        try:
            content_lower = content.lower()
            promo_patterns = [
                r'https?://[^\s]+',  # URLs
                r'www\.[^\s]+',      # www links
                r'\b\d{10,}\b',      # Phone numbers
                r'email.*@',         # Email references
            ]
            
            return any(re.search(pattern, content_lower) for pattern in promo_patterns)
        except Exception:
            return False
            
    def update_product_rating_stats(self, product_id: str):
        """Update product rating statistics"""
        try:
            # This would recalculate and cache product rating stats
            # For performance, this might be done asynchronously
            self.db.update_product_rating_cache(product_id)
        except Exception as e:
            print(f"Error updating product rating stats: {e}")
            
    def update_review_vote_counts(self, review_id: str):
        """Update review helpful/not helpful vote counts"""
        try:
            vote_counts = self.db.get_review_vote_counts(review_id)
            
            self.db.update_review(review_id, {
                'helpful_votes': vote_counts.get('helpful', 0),
                'not_helpful_votes': vote_counts.get('not_helpful', 0),
                'updated_at': datetime.now().isoformat()
            })
            
        except Exception as e:
            print(f"Error updating review vote counts: {e}")
            
    def award_review_points(self, customer_id: str, review_id: str):
        """Award points to customer for review"""
        try:
            if self.enable_review_rewards:
                # This would integrate with loyalty/points system
                print(f"Awarded {self.review_reward_points} points to customer {customer_id} for review {review_id}")
        except Exception as e:
            print(f"Error awarding review points: {e}")
            
    def revoke_review_points(self, customer_id: str, review_id: str):
        """Revoke points from customer for rejected review"""
        try:
            if self.enable_review_rewards:
                # This would integrate with loyalty/points system
                print(f"Revoked {self.review_reward_points} points from customer {customer_id} for review {review_id}")
        except Exception as e:
            print(f"Error revoking review points: {e}")
            
    def calculate_recommendation_percentage(self, product_id: str) -> float:
        """Calculate percentage of customers who would recommend product"""
        try:
            # Consider 4-5 star reviews as recommendations
            stats = self.db.get_product_review_statistics(product_id)
            rating_dist = stats.get('rating_distribution', {})
            
            total_reviews = sum(int(count) for count in rating_dist.values())
            if total_reviews == 0:
                return 0.0
                
            recommendations = int(rating_dist.get('4', 0)) + int(rating_dist.get('5', 0))
            return round((recommendations / total_reviews) * 100, 1)
            
        except Exception:
            return 0.0
            
    def format_time_ago(self, time_diff: timedelta) -> str:
        """Format time difference as human-readable string"""
        try:
            days = time_diff.days
            hours = time_diff.seconds // 3600
            minutes = (time_diff.seconds % 3600) // 60
            
            if days > 0:
                return f"{days} day{'s' if days != 1 else ''} ago"
            elif hours > 0:
                return f"{hours} hour{'s' if hours != 1 else ''} ago"
            elif minutes > 0:
                return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
            else:
                return "Just now"
                
        except Exception:
            return "Recently"
            
    def send_review_notifications(self, review_id: str):
        """Send notifications for new review"""
        try:
            # This would send notifications to store owners, etc.
            print(f"Review notifications sent for review {review_id}")
        except Exception as e:
            print(f"Error sending review notifications: {e}")
            
    def get_pending_reviews(self, page: int = 1, limit: int = 50) -> Dict[str, Any]:
        """Get reviews pending moderation"""
        try:
            reviews = self.db.get_reviews_by_status(ReviewStatus.PENDING.value, page, limit)
            
            enriched_reviews = []
            for review in reviews:
                enriched_review = self.enrich_review_data(review)
                enriched_reviews.append(enriched_review)
                
            total_count = self.db.get_review_count_by_status(ReviewStatus.PENDING.value)
            total_pages = (total_count + limit - 1) // limit
            
            return {
                'reviews': enriched_reviews,
                'pagination': {
                    'page': page,
                    'limit': limit,
                    'total_count': total_count,
                    'total_pages': total_pages,
                    'has_next': page < total_pages,
                    'has_prev': page > 1
                }
            }
            
        except Exception as e:
            raise Exception(f"Error getting pending reviews: {e}")
            
    def cleanup_old_reviews(self, days_old: int = 2555) -> int:
        """Clean up old reviews (for data retention compliance)"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_old)
            cleanup_count = self.db.delete_old_reviews(cutoff_date.isoformat())
            return cleanup_count
        except Exception as e:
            print(f"Error cleaning up old reviews: {e}")
            return 0