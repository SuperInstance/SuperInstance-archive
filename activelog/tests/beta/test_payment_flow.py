"""
Integration tests for payment flows with credits system
Tests the complete payment ecosystem across ActiveLog platforms
"""

import pytest
import asyncio
import uuid
import json
import time
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Any, List, Optional
import httpx
from unittest.mock import Mock, patch, MagicMock
import random

# Test configuration
PAYMENT_SERVICE_URL = "http://localhost:8004"
ACTIVELEDGER_URL = "http://localhost:8005"
API_GATEWAY_URL = "http://localhost:8000"
STRIPE_MOCK_URL = "http://localhost:8888"  # Mock Stripe webhook endpoint


class TestPaymentFlow:
    """Test comprehensive payment flows with credits system"""
    
    @pytest.fixture
    def test_user_with_credits(self):
        """User with initial credits for testing"""
        return {
            'id': str(uuid.uuid4()),
            'email': 'paymenttest@example.com',
            'name': 'Payment Test User',
            'credits_balance': Decimal('100.00'),
            'payment_methods': ['credits', 'stripe'],
            'stripe_customer_id': 'cus_test_customer',
            'subscription_tier': 'basic'
        }
    
    @pytest.fixture
    def mock_stripe_payment(self):
        """Mock Stripe payment method"""
        return {
            'id': 'pm_test_card',
            'type': 'card',
            'card': {
                'brand': 'visa',
                'last4': '4242',
                'exp_month': 12,
                'exp_year': 2025
            }
        }
    
    @pytest.fixture
    async def authenticated_user_session(self, test_user_with_credits):
        """Authenticated user session with payment capabilities"""
        return {
            'user': test_user_with_credits,
            'token': 'test.payment.token',
            'headers': {'Authorization': 'Bearer test.payment.token'}
        }

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_credit_purchase_flow(self, authenticated_user_session, mock_stripe_payment):
        """Test purchasing credits with Stripe integration"""
        
        async with httpx.AsyncClient() as client:
            # Step 1: Get current credit balance
            balance_response = await client.get(
                f"{ACTIVELEDGER_URL}/api/credits/balance",
                headers=authenticated_user_session['headers']
            )
            assert balance_response.status_code == 200
            initial_balance = Decimal(balance_response.json()['balance'])
            
            # Step 2: Create credit purchase order
            purchase_request = {
                'credit_amount': 50.00,
                'payment_method_id': mock_stripe_payment['id'],
                'currency': 'USD'
            }
            
            purchase_response = await client.post(
                f"{ACTIVELEDGER_URL}/api/credits/purchase",
                json=purchase_request,
                headers=authenticated_user_session['headers']
            )
            assert purchase_response.status_code == 201
            
            purchase_data = purchase_response.json()
            assert 'transaction_id' in purchase_data
            assert 'stripe_payment_intent_id' in purchase_data
            assert purchase_data['amount'] == 50.00
            assert purchase_data['status'] == 'pending'
            
            # Step 3: Simulate Stripe webhook confirmation
            webhook_payload = {
                'id': 'evt_test_webhook',
                'object': 'event',
                'type': 'payment_intent.succeeded',
                'data': {
                    'object': {
                        'id': purchase_data['stripe_payment_intent_id'],
                        'amount': 5000,  # $50.00 in cents
                        'currency': 'usd',
                        'status': 'succeeded',
                        'metadata': {
                            'user_id': authenticated_user_session['user']['id'],
                            'transaction_id': purchase_data['transaction_id']
                        }
                    }
                }
            }
            
            webhook_response = await client.post(
                f"{PAYMENT_SERVICE_URL}/webhooks/stripe",
                json=webhook_payload,
                headers={'stripe-signature': 'test_signature'}
            )
            assert webhook_response.status_code == 200
            
            # Step 4: Verify credits were added
            await asyncio.sleep(1)  # Allow for processing
            
            updated_balance_response = await client.get(
                f"{ACTIVELEDGER_URL}/api/credits/balance",
                headers=authenticated_user_session['headers']
            )
            updated_balance = Decimal(updated_balance_response.json()['balance'])
            
            assert updated_balance == initial_balance + Decimal('50.00')
            
            # Step 5: Verify transaction history
            history_response = await client.get(
                f"{ACTIVELEDGER_URL}/api/transactions/history",
                headers=authenticated_user_session['headers']
            )
            transactions = history_response.json()['transactions']
            
            credit_purchase = next(
                t for t in transactions 
                if t['type'] == 'credit_purchase' and t['amount'] == 50.00
            )
            assert credit_purchase['status'] == 'completed'

    @pytest.mark.asyncio
    async def test_credit_payment_for_service(self, authenticated_user_session):
        """Test paying for services using credits"""
        
        async with httpx.AsyncClient() as client:
            # Step 1: Create a service order (custom MakerLog item)
            service_order = {
                'service_type': 'custom_item',
                'item_details': {
                    'name': 'Custom Dice Set',
                    'description': 'Personalized metal dice set with engraving',
                    'specifications': {
                        'material': 'aluminum',
                        'finish': 'anodized blue',
                        'engraving': 'Player Name'
                    }
                },
                'quoted_price': 45.00,
                'maker_id': str(uuid.uuid4())
            }
            
            order_response = await client.post(
                f"{API_GATEWAY_URL}/api/orders/create",
                json=service_order,
                headers=authenticated_user_session['headers']
            )
            assert order_response.status_code == 201
            order_id = order_response.json()['order_id']
            
            # Step 2: Process payment with credits
            payment_request = {
                'order_id': order_id,
                'payment_method': 'credits',
                'amount': 45.00
            }
            
            payment_response = await client.post(
                f"{PAYMENT_SERVICE_URL}/api/payments/process",
                json=payment_request,
                headers=authenticated_user_session['headers']
            )
            assert payment_response.status_code == 200
            
            payment_data = payment_response.json()
            assert payment_data['status'] == 'completed'
            assert payment_data['payment_method'] == 'credits'
            assert payment_data['amount_charged'] == 45.00
            
            # Step 3: Verify credits were deducted
            balance_response = await client.get(
                f"{ACTIVELEDGER_URL}/api/credits/balance",
                headers=authenticated_user_session['headers']
            )
            current_balance = Decimal(balance_response.json()['balance'])
            assert current_balance == Decimal('55.00')  # 100 - 45
            
            # Step 4: Verify maker receives payment
            maker_earnings_response = await client.get(
                f"{ACTIVELEDGER_URL}/api/earnings/{service_order['maker_id']}",
                headers=authenticated_user_session['headers']
            )
            assert maker_earnings_response.status_code == 200
            
            earnings_data = maker_earnings_response.json()
            assert earnings_data['pending_earnings'] >= 40.50  # After platform fees

    @pytest.mark.asyncio
    async def test_insufficient_credits_fallback(self, authenticated_user_session, mock_stripe_payment):
        """Test fallback to Stripe when insufficient credits"""
        
        async with httpx.AsyncClient() as client:
            # Create order that exceeds credit balance
            large_order = {
                'service_type': 'custom_item',
                'quoted_price': 150.00,  # More than $100 credit balance
                'maker_id': str(uuid.uuid4())
            }
            
            order_response = await client.post(
                f"{API_GATEWAY_URL}/api/orders/create",
                json=large_order,
                headers=authenticated_user_session['headers']
            )
            order_id = order_response.json()['order_id']
            
            # Attempt payment with credits (should indicate insufficient funds)
            payment_request = {
                'order_id': order_id,
                'payment_method': 'credits',
                'amount': 150.00
            }
            
            payment_response = await client.post(
                f"{PAYMENT_SERVICE_URL}/api/payments/process",
                json=payment_request,
                headers=authenticated_user_session['headers']
            )
            assert payment_response.status_code == 402  # Payment required
            
            error_data = payment_response.json()
            assert error_data['error'] == 'insufficient_credits'
            assert 'suggested_actions' in error_data
            
            # Use hybrid payment (credits + Stripe)
            hybrid_payment = {
                'order_id': order_id,
                'payment_method': 'hybrid',
                'credit_amount': 100.00,
                'stripe_payment_method_id': mock_stripe_payment['id'],
                'stripe_amount': 50.00,
                'total_amount': 150.00
            }
            
            hybrid_response = await client.post(
                f"{PAYMENT_SERVICE_URL}/api/payments/process",
                json=hybrid_payment,
                headers=authenticated_user_session['headers']
            )
            assert hybrid_response.status_code == 200
            
            payment_data = hybrid_response.json()
            assert payment_data['status'] == 'completed'
            assert payment_data['credits_used'] == 100.00
            assert payment_data['stripe_charged'] == 50.00

    @pytest.mark.asyncio
    async def test_subscription_payment_flow(self, authenticated_user_session, mock_stripe_payment):
        """Test subscription upgrade and recurring payments"""
        
        async with httpx.AsyncClient() as client:
            # Step 1: Get available subscription plans
            plans_response = await client.get(
                f"{ACTIVELEDGER_URL}/api/subscriptions/plans"
            )
            assert plans_response.status_code == 200
            plans = plans_response.json()['plans']
            
            premium_plan = next(p for p in plans if p['tier'] == 'premium')
            assert premium_plan['monthly_price'] == 19.99
            
            # Step 2: Upgrade to premium subscription
            upgrade_request = {
                'plan_id': premium_plan['id'],
                'payment_method_id': mock_stripe_payment['id'],
                'billing_cycle': 'monthly'
            }
            
            upgrade_response = await client.post(
                f"{ACTIVELEDGER_URL}/api/subscriptions/upgrade",
                json=upgrade_request,
                headers=authenticated_user_session['headers']
            )
            assert upgrade_response.status_code == 201
            
            subscription_data = upgrade_response.json()
            assert subscription_data['tier'] == 'premium'
            assert subscription_data['status'] == 'active'
            
            # Step 3: Verify premium features are enabled
            features_response = await client.get(
                f"{API_GATEWAY_URL}/api/user/features",
                headers=authenticated_user_session['headers']
            )
            features = features_response.json()['features']
            
            assert features['advanced_ai_assistance'] == True
            assert features['priority_support'] == True
            assert features['custom_branding'] == True
            
            # Step 4: Test pro-rated billing calculation
            billing_response = await client.get(
                f"{ACTIVELEDGER_URL}/api/subscriptions/billing/next",
                headers=authenticated_user_session['headers']
            )
            billing_data = billing_response.json()
            
            assert billing_data['amount'] == 19.99
            assert billing_data['next_billing_date'] is not None

    @pytest.mark.asyncio
    async def test_refund_processing(self, authenticated_user_session):
        """Test refund processing back to credits and payment methods"""
        
        async with httpx.AsyncClient() as client:
            # Create and pay for an order
            order_request = {
                'service_type': 'custom_item',
                'quoted_price': 35.00,
                'maker_id': str(uuid.uuid4())
            }
            
            order_response = await client.post(
                f"{API_GATEWAY_URL}/api/orders/create",
                json=order_request,
                headers=authenticated_user_session['headers']
            )
            order_id = order_response.json()['order_id']
            
            # Pay with credits
            payment_response = await client.post(
                f"{PAYMENT_SERVICE_URL}/api/payments/process",
                json={
                    'order_id': order_id,
                    'payment_method': 'credits',
                    'amount': 35.00
                },
                headers=authenticated_user_session['headers']
            )
            payment_id = payment_response.json()['payment_id']
            
            # Request refund
            refund_request = {
                'payment_id': payment_id,
                'reason': 'customer_request',
                'amount': 35.00,
                'refund_method': 'original'  # Back to credits
            }
            
            refund_response = await client.post(
                f"{PAYMENT_SERVICE_URL}/api/refunds/process",
                json=refund_request,
                headers=authenticated_user_session['headers']
            )
            assert refund_response.status_code == 200
            
            refund_data = refund_response.json()
            assert refund_data['status'] == 'completed'
            assert refund_data['amount'] == 35.00
            
            # Verify credits restored
            balance_response = await client.get(
                f"{ACTIVELEDGER_URL}/api/credits/balance",
                headers=authenticated_user_session['headers']
            )
            current_balance = Decimal(balance_response.json()['balance'])
            assert current_balance == Decimal('100.00')  # Back to original

    @pytest.mark.asyncio
    async def test_marketplace_commission_system(self, authenticated_user_session):
        """Test commission calculations and maker payouts"""
        
        async with httpx.AsyncClient() as client:
            # Create a maker profile
            maker_profile = {
                'business_name': 'Test Maker Shop',
                'commission_rate': 0.15,  # 15% to platform
                'payout_method': 'credits',
                'minimum_payout': 25.00
            }
            
            maker_response = await client.post(
                f"{API_GATEWAY_URL}/api/makers/profile",
                json=maker_profile,
                headers=authenticated_user_session['headers']
            )
            maker_id = maker_response.json()['maker_id']
            
            # Complete several orders for commission testing
            order_values = [45.00, 67.00, 23.00, 89.00]
            
            for value in order_values:
                # Create order
                order_response = await client.post(
                    f"{API_GATEWAY_URL}/api/orders/create",
                    json={
                        'service_type': 'custom_item',
                        'quoted_price': value,
                        'maker_id': maker_id
                    },
                    headers=authenticated_user_session['headers']
                )
                order_id = order_response.json()['order_id']
                
                # Process payment
                await client.post(
                    f"{PAYMENT_SERVICE_URL}/api/payments/process",
                    json={
                        'order_id': order_id,
                        'payment_method': 'credits',
                        'amount': value
                    },
                    headers=authenticated_user_session['headers']
                )
                
                # Mark order as completed
                await client.post(
                    f"{API_GATEWAY_URL}/api/orders/{order_id}/complete",
                    headers=authenticated_user_session['headers']
                )
            
            # Check commission calculations
            commission_response = await client.get(
                f"{ACTIVELEDGER_URL}/api/commissions/maker/{maker_id}",
                headers=authenticated_user_session['headers']
            )
            commission_data = commission_response.json()
            
            total_sales = sum(order_values)  # $224.00
            expected_commission = total_sales * 0.15  # $33.60
            expected_maker_earnings = total_sales - expected_commission  # $190.40
            
            assert commission_data['total_sales'] == total_sales
            assert commission_data['platform_commission'] == expected_commission
            assert commission_data['maker_earnings'] == expected_maker_earnings
            
            # Test payout processing
            payout_response = await client.post(
                f"{ACTIVELEDGER_URL}/api/payouts/process/{maker_id}",
                headers=authenticated_user_session['headers']
            )
            assert payout_response.status_code == 200
            
            payout_data = payout_response.json()
            assert payout_data['amount'] == expected_maker_earnings
            assert payout_data['method'] == 'credits'

    @pytest.mark.asyncio 
    async def test_payment_dispute_handling(self, authenticated_user_session):
        """Test handling of payment disputes and chargebacks"""
        
        async with httpx.AsyncClient() as client:
            # Create and pay for order with Stripe
            order_response = await client.post(
                f"{API_GATEWAY_URL}/api/orders/create",
                json={
                    'service_type': 'custom_item',
                    'quoted_price': 75.00,
                    'maker_id': str(uuid.uuid4())
                },
                headers=authenticated_user_session['headers']
            )
            order_id = order_response.json()['order_id']
            
            payment_response = await client.post(
                f"{PAYMENT_SERVICE_URL}/api/payments/process",
                json={
                    'order_id': order_id,
                    'payment_method': 'stripe',
                    'stripe_payment_method_id': 'pm_test_card',
                    'amount': 75.00
                },
                headers=authenticated_user_session['headers']
            )
            payment_id = payment_response.json()['payment_id']
            
            # Simulate chargeback notification from Stripe
            chargeback_webhook = {
                'id': 'evt_chargeback',
                'type': 'charge.dispute.created',
                'data': {
                    'object': {
                        'id': 'dp_test_dispute',
                        'amount': 7500,  # $75.00 in cents
                        'charge': payment_id,
                        'reason': 'fraudulent',
                        'status': 'warning_needs_response'
                    }
                }
            }
            
            dispute_response = await client.post(
                f"{PAYMENT_SERVICE_URL}/webhooks/stripe",
                json=chargeback_webhook,
                headers={'stripe-signature': 'test_signature'}
            )
            assert dispute_response.status_code == 200
            
            # Check dispute was recorded
            disputes_response = await client.get(
                f"{PAYMENT_SERVICE_URL}/api/disputes",
                headers=authenticated_user_session['headers']
            )
            disputes = disputes_response.json()['disputes']
            
            relevant_dispute = next(d for d in disputes if d['payment_id'] == payment_id)
            assert relevant_dispute['status'] == 'needs_response'
            assert relevant_dispute['amount'] == 75.00

    @pytest.mark.asyncio
    async def test_tax_calculation_integration(self, authenticated_user_session):
        """Test tax calculation for different regions and services"""
        
        async with httpx.AsyncClient() as client:
            # Update user location for tax calculation
            location_update = await client.put(
                f"{API_GATEWAY_URL}/api/user/location",
                json={
                    'country': 'US',
                    'state': 'CA',
                    'city': 'San Francisco',
                    'postal_code': '94105'
                },
                headers=authenticated_user_session['headers']
            )
            assert location_update.status_code == 200
            
            # Create order that requires tax calculation
            order_response = await client.post(
                f"{API_GATEWAY_URL}/api/orders/create",
                json={
                    'service_type': 'physical_item',
                    'quoted_price': 100.00,
                    'maker_id': str(uuid.uuid4()),
                    'shipping_required': True
                },
                headers=authenticated_user_session['headers']
            )
            order_data = order_response.json()
            
            # Verify tax calculation
            assert 'tax_amount' in order_data
            assert 'tax_rate' in order_data
            assert order_data['tax_rate'] > 0  # CA should have sales tax
            
            expected_tax = 100.00 * order_data['tax_rate']
            assert abs(order_data['tax_amount'] - expected_tax) < 0.01
            
            total_with_tax = 100.00 + order_data['tax_amount']
            assert abs(order_data['total_amount'] - total_with_tax) < 0.01

    @pytest.mark.load
    async def test_concurrent_payment_processing(self, authenticated_user_session):
        """Test system under concurrent payment load"""
        
        async def process_payment(payment_amount: float):
            async with httpx.AsyncClient() as client:
                order_response = await client.post(
                    f"{API_GATEWAY_URL}/api/orders/create",
                    json={
                        'service_type': 'digital_item',
                        'quoted_price': payment_amount,
                        'maker_id': str(uuid.uuid4())
                    },
                    headers=authenticated_user_session['headers']
                )
                order_id = order_response.json()['order_id']
                
                return await client.post(
                    f"{PAYMENT_SERVICE_URL}/api/payments/process",
                    json={
                        'order_id': order_id,
                        'payment_method': 'credits',
                        'amount': payment_amount
                    },
                    headers=authenticated_user_session['headers']
                )
        
        # Process 10 concurrent payments
        payment_amounts = [random.uniform(5.0, 25.0) for _ in range(10)]
        tasks = [process_payment(amount) for amount in payment_amounts]
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify most payments succeeded
        successful_payments = [
            r for r in responses 
            if not isinstance(r, Exception) and r.status_code == 200
        ]
        assert len(successful_payments) >= 8  # Allow for some failures under load

    @pytest.mark.asyncio
    async def test_payment_analytics_and_reporting(self, authenticated_user_session):
        """Test payment analytics and financial reporting"""
        
        async with httpx.AsyncClient() as client:
            # Generate several transactions for analytics
            transactions = [
                {'type': 'credit_purchase', 'amount': 50.00},
                {'type': 'service_payment', 'amount': 25.00},
                {'type': 'subscription', 'amount': 19.99},
                {'type': 'service_payment', 'amount': 35.00},
                {'type': 'refund', 'amount': -10.00}
            ]
            
            for transaction in transactions:
                await client.post(
                    f"{ACTIVELEDGER_URL}/api/transactions/create",
                    json=transaction,
                    headers=authenticated_user_session['headers']
                )
            
            # Get payment analytics
            analytics_response = await client.get(
                f"{ACTIVELEDGER_URL}/api/analytics/payments",
                params={'timeframe': '30_days'},
                headers=authenticated_user_session['headers']
            )
            assert analytics_response.status_code == 200
            
            analytics = analytics_response.json()
            assert 'total_volume' in analytics
            assert 'transaction_count' in analytics
            assert 'payment_methods_breakdown' in analytics
            assert 'revenue_trends' in analytics
            
            # Verify calculations
            expected_volume = sum(t['amount'] for t in transactions if t['amount'] > 0)
            assert abs(analytics['total_volume'] - expected_volume) < 0.01