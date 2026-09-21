"""
Affiliate Tracking System
Handles affiliate program management, tracking, and commission calculations
"""

import json
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum
import urllib.parse


class AffiliateStatus(Enum):
    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    TERMINATED = "terminated"


class CommissionType(Enum):
    PERCENTAGE = "percentage"
    FIXED = "fixed"
    TIERED = "tiered"


class ReferralStatus(Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    PAID = "paid"


@dataclass
class AffiliateLink:
    link_id: str
    affiliate_id: str
    product_id: Optional[str]
    campaign_id: Optional[str]
    url: str
    clicks: int
    conversions: int
    created_at: datetime


class AffiliateTrackingSystem:
    """Manages affiliate program and tracking"""
    
    def __init__(self, config, db):
        self.config = config
        self.db = db
        
        # Affiliate program settings
        self.default_commission_rate = config.get('default_commission_rate', 5.0)  # 5%
        self.commission_type = config.get('commission_type', CommissionType.PERCENTAGE.value)
        self.cookie_duration_days = config.get('cookie_duration_days', 30)
        
        # Tracking settings
        self.enable_deep_linking = config.get('enable_deep_linking', True)
        self.enable_coupon_tracking = config.get('enable_coupon_tracking', True)
        self.enable_sub_affiliates = config.get('enable_sub_affiliates', False)
        
        # Payment settings
        self.minimum_payout_amount = config.get('minimum_payout_amount', 50.0)
        self.payment_schedule = config.get('payment_schedule', 'monthly')  # monthly, weekly, bi-weekly
        self.payment_delay_days = config.get('payment_delay_days', 30)
        
        # Fraud protection
        self.enable_fraud_detection = config.get('enable_fraud_detection', True)
        self.max_self_referrals = config.get('max_self_referrals', 0)  # 0 = not allowed
        
        # Base URLs
        self.base_url = config.get('base_url', 'https://example.com')
        self.affiliate_base_url = config.get('affiliate_base_url', f'{self.base_url}/aff')
        
    def register_affiliate(self, registration_data: Dict[str, Any]) -> Dict[str, Any]:
        """Register new affiliate"""
        try:
            # Validate required fields
            required_fields = ['email', 'first_name', 'last_name', 'website', 'promotional_method']
            for field in required_fields:
                if field not in registration_data or not registration_data[field]:
                    raise ValueError(f"Missing required field: {field}")
                    
            # Check if email already exists
            existing_affiliate = self.db.get_affiliate_by_email(registration_data['email'])
            if existing_affiliate:
                raise ValueError("An affiliate account with this email already exists")
                
            # Generate affiliate ID and code
            affiliate_id = f"aff_{datetime.now().timestamp()}"
            affiliate_code = self.generate_affiliate_code(registration_data['email'])
            
            # Create affiliate record
            affiliate = {
                'affiliate_id': affiliate_id,
                'affiliate_code': affiliate_code,
                'email': registration_data['email'].lower(),
                'first_name': registration_data['first_name'],
                'last_name': registration_data['last_name'],
                'company_name': registration_data.get('company_name'),
                'website': registration_data['website'],
                'promotional_method': registration_data['promotional_method'],
                'tax_id': registration_data.get('tax_id'),
                'phone': registration_data.get('phone'),
                'address': registration_data.get('address', {}),
                'status': AffiliateStatus.PENDING.value,
                'commission_rate': self.default_commission_rate,
                'commission_type': self.commission_type,
                'payment_method': registration_data.get('payment_method', 'paypal'),
                'payment_details': registration_data.get('payment_details', {}),
                'notes': registration_data.get('notes', ''),
                'referrer_affiliate_id': registration_data.get('referrer_affiliate_id'),
                'total_clicks': 0,
                'total_conversions': 0,
                'total_commission_earned': 0.0,
                'total_commission_paid': 0.0,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            # Save affiliate
            success = self.db.save_affiliate(affiliate)
            if not success:
                raise Exception("Failed to save affiliate registration")
                
            # Create default tracking links
            self.create_default_tracking_links(affiliate_id)
            
            # Send welcome email
            self.send_affiliate_welcome_email(affiliate_id)
            
            return {
                'success': True,
                'affiliate_id': affiliate_id,
                'affiliate_code': affiliate_code,
                'status': AffiliateStatus.PENDING.value,
                'message': 'Affiliate registration submitted. Awaiting approval.'
            }
            
        except Exception as e:
            raise Exception(f"Error registering affiliate: {e}")
            
    def approve_affiliate(self, approval_data: Dict[str, Any]) -> Dict[str, Any]:
        """Approve affiliate application"""
        try:
            affiliate_id = approval_data['affiliate_id']
            approved_by = approval_data['approved_by']
            custom_commission_rate = approval_data.get('commission_rate')
            
            affiliate = self.db.get_affiliate(affiliate_id)
            if not affiliate:
                raise ValueError("Affiliate not found")
                
            if affiliate['status'] != AffiliateStatus.PENDING.value:
                raise ValueError("Affiliate is not in pending status")
                
            # Update affiliate status
            updates = {
                'status': AffiliateStatus.ACTIVE.value,
                'approved_by': approved_by,
                'approved_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            # Set custom commission rate if provided
            if custom_commission_rate is not None:
                updates['commission_rate'] = custom_commission_rate
                
            success = self.db.update_affiliate(affiliate_id, updates)
            if not success:
                raise Exception("Failed to approve affiliate")
                
            # Send approval notification
            self.send_affiliate_approval_email(affiliate_id)
            
            # Log approval
            self.log_affiliate_event(affiliate_id, 'approved', {
                'approved_by': approved_by,
                'commission_rate': updates.get('commission_rate', affiliate['commission_rate'])
            })
            
            return {
                'success': True,
                'affiliate_id': affiliate_id,
                'status': AffiliateStatus.ACTIVE.value,
                'message': 'Affiliate approved successfully'
            }
            
        except Exception as e:
            raise Exception(f"Error approving affiliate: {e}")
            
    def create_affiliate_link(self, link_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create affiliate tracking link"""
        try:
            affiliate_id = link_data['affiliate_id']
            target_url = link_data.get('target_url', '/')
            product_id = link_data.get('product_id')
            campaign_id = link_data.get('campaign_id')
            custom_parameters = link_data.get('custom_parameters', {})
            
            # Verify affiliate exists and is active
            affiliate = self.db.get_affiliate(affiliate_id)
            if not affiliate:
                raise ValueError("Affiliate not found")
            if affiliate['status'] != AffiliateStatus.ACTIVE.value:
                raise ValueError("Affiliate is not active")
                
            # Generate link ID
            link_id = f"link_{datetime.now().timestamp()}"
            
            # Build affiliate URL
            affiliate_url = self.build_affiliate_url(
                affiliate['affiliate_code'],
                target_url,
                product_id,
                campaign_id,
                custom_parameters
            )
            
            # Create link record
            link = {
                'link_id': link_id,
                'affiliate_id': affiliate_id,
                'affiliate_code': affiliate['affiliate_code'],
                'target_url': target_url,
                'product_id': product_id,
                'campaign_id': campaign_id,
                'custom_parameters': json.dumps(custom_parameters),
                'affiliate_url': affiliate_url,
                'clicks': 0,
                'unique_clicks': 0,
                'conversions': 0,
                'commission_earned': 0.0,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            # Save link
            success = self.db.save_affiliate_link(link)
            if not success:
                raise Exception("Failed to create affiliate link")
                
            return {
                'success': True,
                'link_id': link_id,
                'affiliate_url': affiliate_url,
                'target_url': target_url,
                'message': 'Affiliate link created successfully'
            }
            
        except Exception as e:
            raise Exception(f"Error creating affiliate link: {e}")
            
    def track_click(self, tracking_data: Dict[str, Any]) -> Dict[str, Any]:
        """Track affiliate link click"""
        try:
            affiliate_code = tracking_data['affiliate_code']
            target_url = tracking_data.get('target_url', '/')
            ip_address = tracking_data.get('ip_address')
            user_agent = tracking_data.get('user_agent')
            referrer = tracking_data.get('referrer')
            product_id = tracking_data.get('product_id')
            campaign_id = tracking_data.get('campaign_id')
            
            # Get affiliate
            affiliate = self.db.get_affiliate_by_code(affiliate_code)
            if not affiliate or affiliate['status'] != AffiliateStatus.ACTIVE.value:
                return {
                    'success': False,
                    'redirect_url': self.base_url + target_url,
                    'tracked': False
                }
                
            # Check for fraud indicators
            if self.enable_fraud_detection:
                fraud_check = self.check_click_fraud(affiliate['affiliate_id'], ip_address, user_agent)
                if fraud_check['is_fraud']:
                    return {
                        'success': False,
                        'redirect_url': self.base_url + target_url,
                        'tracked': False,
                        'reason': fraud_check['reason']
                    }
                    
            # Generate click tracking ID
            click_id = f"click_{datetime.now().timestamp()}"
            
            # Check if this is a unique click (same IP within 24 hours)
            is_unique_click = not self.db.has_recent_click(affiliate['affiliate_id'], ip_address, 24)
            
            # Create click record
            click_record = {
                'click_id': click_id,
                'affiliate_id': affiliate['affiliate_id'],
                'affiliate_code': affiliate_code,
                'target_url': target_url,
                'product_id': product_id,
                'campaign_id': campaign_id,
                'ip_address': ip_address,
                'user_agent': user_agent,
                'referrer': referrer,
                'is_unique': is_unique_click,
                'created_at': datetime.now().isoformat()
            }
            
            # Save click
            self.db.save_affiliate_click(click_record)
            
            # Update link statistics
            if product_id:
                self.db.increment_link_clicks(affiliate['affiliate_id'], product_id, is_unique_click)
            else:
                self.db.increment_affiliate_clicks(affiliate['affiliate_id'], is_unique_click)
                
            # Set tracking cookie
            cookie_data = {
                'affiliate_id': affiliate['affiliate_id'],
                'affiliate_code': affiliate_code,
                'click_id': click_id,
                'expires': (datetime.now() + timedelta(days=self.cookie_duration_days)).isoformat()
            }
            
            # Build redirect URL
            redirect_url = self.base_url + target_url
            
            return {
                'success': True,
                'click_id': click_id,
                'redirect_url': redirect_url,
                'tracked': True,
                'cookie_data': cookie_data,
                'cookie_expires': self.cookie_duration_days * 24 * 3600  # seconds
            }
            
        except Exception as e:
            print(f"Error tracking click: {e}")
            return {
                'success': False,
                'redirect_url': self.base_url + tracking_data.get('target_url', '/'),
                'tracked': False
            }
            
    def track_conversion(self, conversion_data: Dict[str, Any]) -> Dict[str, Any]:
        """Track affiliate conversion (sale)"""
        try:
            order_id = conversion_data['order_id']
            affiliate_id = conversion_data.get('affiliate_id')
            affiliate_code = conversion_data.get('affiliate_code')
            click_id = conversion_data.get('click_id')
            
            # Get order details
            order = self.db.get_order(order_id)
            if not order:
                raise ValueError("Order not found")
                
            # Determine affiliate from cookie data if not provided
            if not affiliate_id and affiliate_code:
                affiliate = self.db.get_affiliate_by_code(affiliate_code)
                affiliate_id = affiliate['affiliate_id'] if affiliate else None
                
            if not affiliate_id:
                return {
                    'success': False,
                    'tracked': False,
                    'reason': 'No affiliate tracking found'
                }
                
            # Get affiliate
            affiliate = self.db.get_affiliate(affiliate_id)
            if not affiliate or affiliate['status'] != AffiliateStatus.ACTIVE.value:
                return {
                    'success': False,
                    'tracked': False,
                    'reason': 'Affiliate not active'
                }
                
            # Check if conversion already tracked
            existing_conversion = self.db.get_conversion_by_order(order_id)
            if existing_conversion:
                return {
                    'success': False,
                    'tracked': False,
                    'reason': 'Conversion already tracked'
                }
                
            # Calculate commission
            commission_result = self.calculate_commission(affiliate_id, order)
            
            # Generate conversion ID
            conversion_id = f"conv_{datetime.now().timestamp()}"
            
            # Create conversion record
            conversion = {
                'conversion_id': conversion_id,
                'affiliate_id': affiliate_id,
                'order_id': order_id,
                'click_id': click_id,
                'customer_id': order.get('customer_id'),
                'order_total': order['total'],
                'commission_amount': commission_result['commission'],
                'commission_rate': commission_result['rate'],
                'commission_type': commission_result['type'],
                'product_ids': json.dumps([item['product_id'] for item in order.get('items', [])]),
                'status': ReferralStatus.PENDING.value,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            # Check for fraudulent conversion
            if self.enable_fraud_detection:
                fraud_check = self.check_conversion_fraud(affiliate_id, order)
                if fraud_check['is_fraud']:
                    conversion['status'] = ReferralStatus.CANCELLED.value
                    conversion['fraud_reason'] = fraud_check['reason']
                    
            # Save conversion
            success = self.db.save_affiliate_conversion(conversion)
            if not success:
                raise Exception("Failed to save conversion")
                
            # Update affiliate statistics
            if conversion['status'] == ReferralStatus.PENDING.value:
                self.db.increment_affiliate_conversions(affiliate_id, commission_result['commission'])
                
            # Update link statistics if product-specific
            order_items = order.get('items', [])
            for item in order_items:
                product_id = item.get('product_id')
                if product_id:
                    self.db.increment_link_conversions(affiliate_id, product_id, commission_result['commission'])
                    
            return {
                'success': True,
                'conversion_id': conversion_id,
                'tracked': True,
                'commission_amount': commission_result['commission'],
                'commission_rate': commission_result['rate'],
                'status': conversion['status']
            }
            
        except Exception as e:
            raise Exception(f"Error tracking conversion: {e}")
            
    def calculate_commission(self, affiliate_id: str, order: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate commission for affiliate conversion"""
        try:
            affiliate = self.db.get_affiliate(affiliate_id)
            if not affiliate:
                raise ValueError("Affiliate not found")
                
            order_total = float(order['total'])
            commission_rate = affiliate['commission_rate']
            commission_type = affiliate['commission_type']
            
            if commission_type == CommissionType.PERCENTAGE.value:
                commission = order_total * (commission_rate / 100)
            elif commission_type == CommissionType.FIXED.value:
                commission = commission_rate
            elif commission_type == CommissionType.TIERED.value:
                # Tiered commission based on order value
                commission = self.calculate_tiered_commission(commission_rate, order_total)
            else:
                commission = 0.0
                
            # Apply any commission caps or minimums
            commission = max(0, commission)  # No negative commissions
            max_commission = self.config.get('max_commission_per_order', 1000.0)
            commission = min(commission, max_commission)
            
            return {
                'commission': round(commission, 2),
                'rate': commission_rate,
                'type': commission_type,
                'order_total': order_total
            }
            
        except Exception as e:
            raise Exception(f"Error calculating commission: {e}")
            
    def calculate_tiered_commission(self, tier_config: str, order_total: float) -> float:
        """Calculate tiered commission based on order value"""
        try:
            # tier_config format: "0-100:5,101-500:7,501+:10" (order_range:rate)
            tiers = []
            for tier in tier_config.split(','):
                range_part, rate_part = tier.split(':')
                rate = float(rate_part)
                
                if '+' in range_part:
                    min_amount = float(range_part.replace('+', ''))
                    max_amount = float('inf')
                else:
                    min_amount, max_amount = map(float, range_part.split('-'))
                    
                tiers.append((min_amount, max_amount, rate))
                
            # Find applicable tier
            for min_amount, max_amount, rate in tiers:
                if min_amount <= order_total <= max_amount:
                    return order_total * (rate / 100)
                    
            return 0.0
            
        except Exception:
            return 0.0
            
    def get_affiliate_dashboard(self, affiliate_id: str) -> Dict[str, Any]:
        """Get affiliate dashboard data"""
        try:
            affiliate = self.db.get_affiliate(affiliate_id)
            if not affiliate:
                raise ValueError("Affiliate not found")
                
            # Get performance statistics
            stats = self.db.get_affiliate_statistics(affiliate_id)
            
            # Get recent activity
            recent_clicks = self.db.get_recent_affiliate_clicks(affiliate_id, 10)
            recent_conversions = self.db.get_recent_affiliate_conversions(affiliate_id, 10)
            
            # Get top performing links
            top_links = self.db.get_top_affiliate_links(affiliate_id, 5)
            
            # Calculate conversion rate
            total_clicks = stats.get('total_clicks', 0)
            total_conversions = stats.get('total_conversions', 0)
            conversion_rate = (total_conversions / max(total_clicks, 1)) * 100
            
            # Get payment information
            payment_info = self.get_affiliate_payments(affiliate_id)
            
            return {
                'affiliate_info': {
                    'affiliate_id': affiliate['affiliate_id'],
                    'affiliate_code': affiliate['affiliate_code'],
                    'status': affiliate['status'],
                    'commission_rate': affiliate['commission_rate'],
                    'member_since': affiliate['created_at']
                },
                'performance': {
                    'total_clicks': total_clicks,
                    'unique_clicks': stats.get('unique_clicks', 0),
                    'total_conversions': total_conversions,
                    'conversion_rate': round(conversion_rate, 2),
                    'total_commission_earned': stats.get('total_commission_earned', 0),
                    'pending_commission': stats.get('pending_commission', 0),
                    'paid_commission': stats.get('paid_commission', 0)
                },
                'recent_activity': {
                    'recent_clicks': recent_clicks,
                    'recent_conversions': recent_conversions
                },
                'top_links': top_links,
                'payment_info': payment_info
            }
            
        except Exception as e:
            raise Exception(f"Error getting affiliate dashboard: {e}")
            
    def get_affiliate_payments(self, affiliate_id: str) -> Dict[str, Any]:
        """Get affiliate payment information"""
        try:
            payments = self.db.get_affiliate_payments(affiliate_id)
            pending_amount = self.db.get_affiliate_pending_commission(affiliate_id)
            
            return {
                'pending_amount': pending_amount,
                'minimum_payout': self.minimum_payout_amount,
                'next_payment_date': self.calculate_next_payment_date(),
                'payment_history': payments
            }
            
        except Exception as e:
            raise Exception(f"Error getting affiliate payments: {e}")
            
    def generate_affiliate_payout(self, payout_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate affiliate payout"""
        try:
            affiliate_ids = payout_data.get('affiliate_ids', [])
            if not affiliate_ids:
                # Get all affiliates eligible for payout
                affiliate_ids = self.db.get_affiliates_eligible_for_payout(self.minimum_payout_amount)
                
            payout_id = f"payout_{datetime.now().timestamp()}"
            total_amount = 0.0
            affiliate_payouts = []
            
            for affiliate_id in affiliate_ids:
                # Get pending commission
                pending_amount = self.db.get_affiliate_pending_commission(affiliate_id)
                
                if pending_amount >= self.minimum_payout_amount:
                    affiliate = self.db.get_affiliate(affiliate_id)
                    
                    # Create individual payout record
                    affiliate_payout = {
                        'payout_id': f"{payout_id}_{affiliate_id}",
                        'batch_payout_id': payout_id,
                        'affiliate_id': affiliate_id,
                        'amount': pending_amount,
                        'payment_method': affiliate.get('payment_method', 'paypal'),
                        'payment_details': affiliate.get('payment_details', {}),
                        'status': 'pending',
                        'created_at': datetime.now().isoformat()
                    }
                    
                    affiliate_payouts.append(affiliate_payout)
                    total_amount += pending_amount
                    
                    # Mark conversions as paid
                    self.db.mark_affiliate_conversions_paid(affiliate_id)
                    
            # Create batch payout record
            batch_payout = {
                'batch_payout_id': payout_id,
                'total_amount': total_amount,
                'affiliate_count': len(affiliate_payouts),
                'status': 'pending',
                'created_at': datetime.now().isoformat()
            }
            
            # Save payout records
            self.db.save_batch_payout(batch_payout)
            for payout in affiliate_payouts:
                self.db.save_affiliate_payout(payout)
                
            return {
                'success': True,
                'batch_payout_id': payout_id,
                'total_amount': total_amount,
                'affiliate_count': len(affiliate_payouts),
                'affiliate_payouts': affiliate_payouts
            }
            
        except Exception as e:
            raise Exception(f"Error generating affiliate payout: {e}")
            
    def build_affiliate_url(self, affiliate_code: str, target_url: str, 
                           product_id: Optional[str] = None, 
                           campaign_id: Optional[str] = None,
                           custom_params: Dict[str, Any] = None) -> str:
        """Build affiliate tracking URL"""
        try:
            # Start with base affiliate URL
            url_parts = [self.affiliate_base_url]
            
            # Add affiliate code
            params = {'aff': affiliate_code}
            
            # Add target URL
            if target_url != '/':
                params['url'] = target_url
                
            # Add product ID for deep linking
            if product_id:
                params['pid'] = product_id
                
            # Add campaign ID
            if campaign_id:
                params['cid'] = campaign_id
                
            # Add custom parameters
            if custom_params:
                for key, value in custom_params.items():
                    if key not in params:  # Don't override system params
                        params[key] = value
                        
            # Build query string
            query_string = urllib.parse.urlencode(params)
            
            return f"{self.affiliate_base_url}?{query_string}"
            
        except Exception:
            return f"{self.affiliate_base_url}?aff={affiliate_code}"
            
    def generate_affiliate_code(self, email: str) -> str:
        """Generate unique affiliate code"""
        try:
            # Create hash from email + timestamp
            hash_input = f"{email}{datetime.now().timestamp()}"
            hash_object = hashlib.md5(hash_input.encode())
            hash_hex = hash_object.hexdigest()
            
            # Take first 8 characters and make it more readable
            code = hash_hex[:8].upper()
            
            # Ensure uniqueness
            counter = 0
            original_code = code
            while self.db.affiliate_code_exists(code):
                counter += 1
                code = f"{original_code}{counter}"
                
            return code
            
        except Exception:
            return secrets.token_hex(4).upper()
            
    def create_default_tracking_links(self, affiliate_id: str):
        """Create default tracking links for new affiliate"""
        try:
            default_links = [
                {'target_url': '/', 'description': 'Homepage'},
                {'target_url': '/products', 'description': 'Products Page'},
                {'target_url': '/categories', 'description': 'Categories Page'}
            ]
            
            for link_info in default_links:
                self.create_affiliate_link({
                    'affiliate_id': affiliate_id,
                    'target_url': link_info['target_url'],
                    'custom_parameters': {'desc': link_info['description']}
                })
                
        except Exception as e:
            print(f"Error creating default tracking links: {e}")
            
    def check_click_fraud(self, affiliate_id: str, ip_address: str, user_agent: str) -> Dict[str, Any]:
        """Check for fraudulent clicks"""
        try:
            fraud_reasons = []
            
            # Check for excessive clicks from same IP
            recent_clicks = self.db.get_affiliate_clicks_by_ip(affiliate_id, ip_address, hours=24)
            if len(recent_clicks) > 10:  # More than 10 clicks per day from same IP
                fraud_reasons.append("Excessive clicks from same IP")
                
            # Check for self-referrals if not allowed
            if self.max_self_referrals == 0:
                affiliate = self.db.get_affiliate(affiliate_id)
                if affiliate:
                    # Check if IP belongs to affiliate (simplified check)
                    affiliate_ips = self.db.get_affiliate_known_ips(affiliate_id)
                    if ip_address in affiliate_ips:
                        fraud_reasons.append("Self-referral detected")
                        
            # Check for bot traffic
            if self.is_bot_user_agent(user_agent):
                fraud_reasons.append("Bot traffic detected")
                
            return {
                'is_fraud': len(fraud_reasons) > 0,
                'reason': '; '.join(fraud_reasons) if fraud_reasons else None
            }
            
        except Exception:
            return {'is_fraud': False}
            
    def check_conversion_fraud(self, affiliate_id: str, order: Dict[str, Any]) -> Dict[str, Any]:
        """Check for fraudulent conversions"""
        try:
            fraud_reasons = []
            
            # Check if affiliate is trying to refer themselves
            customer_id = order.get('customer_id')
            if customer_id:
                affiliate = self.db.get_affiliate(affiliate_id)
                if affiliate and affiliate.get('customer_id') == customer_id:
                    fraud_reasons.append("Self-referral conversion")
                    
            # Check for suspicious order patterns
            order_total = float(order.get('total', 0))
            if order_total > 10000:  # Very large orders might be suspicious
                fraud_reasons.append("Unusually large order amount")
                
            # Check conversion timing (too quick might be fraud)
            # This would require checking when the affiliate link was clicked
            
            return {
                'is_fraud': len(fraud_reasons) > 0,
                'reason': '; '.join(fraud_reasons) if fraud_reasons else None
            }
            
        except Exception:
            return {'is_fraud': False}
            
    def is_bot_user_agent(self, user_agent: str) -> bool:
        """Check if user agent appears to be a bot"""
        try:
            if not user_agent:
                return True
                
            bot_indicators = [
                'bot', 'crawler', 'spider', 'scraper', 'wget', 'curl',
                'python', 'java', 'ruby', 'perl', 'php'
            ]
            
            user_agent_lower = user_agent.lower()
            return any(indicator in user_agent_lower for indicator in bot_indicators)
            
        except Exception:
            return False
            
    def calculate_next_payment_date(self) -> str:
        """Calculate next scheduled payment date"""
        try:
            today = datetime.now()
            
            if self.payment_schedule == 'weekly':
                next_payment = today + timedelta(days=7)
            elif self.payment_schedule == 'bi-weekly':
                next_payment = today + timedelta(days=14)
            else:  # monthly
                # Next month, same day
                if today.month == 12:
                    next_payment = today.replace(year=today.year + 1, month=1)
                else:
                    next_payment = today.replace(month=today.month + 1)
                    
            return next_payment.strftime('%Y-%m-%d')
            
        except Exception:
            return (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
            
    def log_affiliate_event(self, affiliate_id: str, event_type: str, event_data: Dict[str, Any]):
        """Log affiliate events for audit trail"""
        try:
            event = {
                'affiliate_id': affiliate_id,
                'event_type': event_type,
                'event_data': json.dumps(event_data),
                'created_at': datetime.now().isoformat()
            }
            
            self.db.save_affiliate_event(event)
            
        except Exception as e:
            print(f"Error logging affiliate event: {e}")
            
    def send_affiliate_welcome_email(self, affiliate_id: str):
        """Send welcome email to new affiliate"""
        try:
            affiliate = self.db.get_affiliate(affiliate_id)
            if affiliate:
                # This would integrate with email service
                print(f"Welcome email sent to affiliate {affiliate['email']}")
        except Exception as e:
            print(f"Error sending welcome email: {e}")
            
    def send_affiliate_approval_email(self, affiliate_id: str):
        """Send approval notification email"""
        try:
            affiliate = self.db.get_affiliate(affiliate_id)
            if affiliate:
                # This would integrate with email service
                print(f"Approval email sent to affiliate {affiliate['email']}")
        except Exception as e:
            print(f"Error sending approval email: {e}")
            
    def get_affiliate_analytics(self, analytics_params: Dict[str, Any]) -> Dict[str, Any]:
        """Get affiliate program analytics"""
        try:
            start_date = analytics_params.get('start_date', (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
            end_date = analytics_params.get('end_date', datetime.now().strftime('%Y-%m-%d'))
            
            analytics = self.db.get_affiliate_program_analytics(start_date, end_date)
            
            return {
                'period': {
                    'start_date': start_date,
                    'end_date': end_date
                },
                'overview': {
                    'total_affiliates': analytics.get('total_affiliates', 0),
                    'active_affiliates': analytics.get('active_affiliates', 0),
                    'total_clicks': analytics.get('total_clicks', 0),
                    'total_conversions': analytics.get('total_conversions', 0),
                    'total_commission_paid': analytics.get('total_commission_paid', 0),
                    'average_commission_per_sale': analytics.get('average_commission_per_sale', 0)
                },
                'performance': {
                    'overall_conversion_rate': analytics.get('overall_conversion_rate', 0),
                    'top_affiliates': analytics.get('top_affiliates', []),
                    'top_products': analytics.get('top_affiliate_products', []),
                    'clicks_by_day': analytics.get('clicks_by_day', []),
                    'conversions_by_day': analytics.get('conversions_by_day', [])
                }
            }
            
        except Exception as e:
            raise Exception(f"Error getting affiliate analytics: {e}")
            
    def suspend_affiliate(self, suspension_data: Dict[str, Any]) -> Dict[str, Any]:
        """Suspend affiliate account"""
        try:
            affiliate_id = suspension_data['affiliate_id']
            reason = suspension_data.get('reason', 'Terms violation')
            suspended_by = suspension_data['suspended_by']
            
            updates = {
                'status': AffiliateStatus.SUSPENDED.value,
                'suspended_by': suspended_by,
                'suspended_at': datetime.now().isoformat(),
                'suspension_reason': reason,
                'updated_at': datetime.now().isoformat()
            }
            
            success = self.db.update_affiliate(affiliate_id, updates)
            if not success:
                raise Exception("Failed to suspend affiliate")
                
            # Log suspension
            self.log_affiliate_event(affiliate_id, 'suspended', {
                'reason': reason,
                'suspended_by': suspended_by
            })
            
            return {
                'success': True,
                'affiliate_id': affiliate_id,
                'status': AffiliateStatus.SUSPENDED.value,
                'message': 'Affiliate suspended successfully'
            }
            
        except Exception as e:
            raise Exception(f"Error suspending affiliate: {e}")