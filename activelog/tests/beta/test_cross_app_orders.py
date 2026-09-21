"""
Integration tests for cross-app order flows (DMLog → MakerLog)
Tests the complete order flow from D&D campaigns to MakerLog projects
"""

import pytest
import asyncio
import uuid
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List
import httpx
from unittest.mock import Mock, patch, MagicMock

# Test configuration
DMLOG_BASE_URL = "http://localhost:8300"
MAKERLOG_BASE_URL = "http://localhost:8301" 
CROSS_APP_ORDERS_URL = "http://localhost:8302"
API_GATEWAY_URL = "http://localhost:8000"


class TestCrossAppOrderFlow:
    """Test cross-application order flows between DMLog and MakerLog"""
    
    @pytest.fixture
    async def dmlog_campaign(self):
        """Create a sample DMLog campaign for testing"""
        return {
            'id': str(uuid.uuid4()),
            'name': 'Test D&D Campaign',
            'dm_id': str(uuid.uuid4()),
            'players': [
                {'id': str(uuid.uuid4()), 'name': 'Alice', 'character': 'Elf Wizard'},
                {'id': str(uuid.uuid4()), 'name': 'Bob', 'character': 'Human Fighter'}
            ],
            'setting': 'fantasy',
            'level_range': '1-5',
            'custom_items': [
                {
                    'name': 'Custom Dice Tower',
                    'type': 'accessory',
                    'description': 'A wooden dice tower with campaign logo',
                    'specifications': {
                        'material': 'oak wood',
                        'height': '6 inches',
                        'engraving': 'campaign name and date'
                    }
                },
                {
                    'name': 'Character Miniatures Set',
                    'type': 'miniatures', 
                    'description': 'Custom 3D printed miniatures for all PCs',
                    'specifications': {
                        'scale': '28mm',
                        'material': 'resin',
                        'finish': 'primer ready',
                        'count': 2
                    }
                }
            ],
            'budget': 150.00,
            'delivery_date': (datetime.utcnow() + timedelta(days=30)).isoformat()
        }
    
    @pytest.fixture
    async def authenticated_user(self):
        """Create an authenticated user session"""
        user_data = {
            'id': str(uuid.uuid4()),
            'email': 'testuser@example.com',
            'name': 'Test User',
            'dmlog_account': True,
            'makerlog_account': True,
            'credits': 200.0
        }
        
        # Mock JWT token
        token = "test.jwt.token.here"
        
        return {
            'user': user_data,
            'token': token,
            'headers': {'Authorization': f'Bearer {token}'}
        }

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_complete_cross_app_order_flow(self, dmlog_campaign, authenticated_user):
        """Test complete flow from DMLog campaign to MakerLog project creation"""
        
        async with httpx.AsyncClient() as client:
            # Step 1: Create DMLog campaign
            campaign_response = await client.post(
                f"{DMLOG_BASE_URL}/api/campaigns",
                json=dmlog_campaign,
                headers=authenticated_user['headers']
            )
            assert campaign_response.status_code == 201
            campaign_id = campaign_response.json()['campaign_id']
            
            # Step 2: Generate custom items order from DMLog
            order_request = {
                'campaign_id': campaign_id,
                'items': dmlog_campaign['custom_items'],
                'target_platform': 'makerlog',
                'auto_create_project': True
            }
            
            order_response = await client.post(
                f"{CROSS_APP_ORDERS_URL}/api/orders/create",
                json=order_request,
                headers=authenticated_user['headers']
            )
            assert order_response.status_code == 201
            order_data = order_response.json()
            
            assert 'order_id' in order_data
            assert 'makerlog_project_id' in order_data
            assert order_data['status'] == 'pending_maker_acceptance'
            
            # Step 3: Verify MakerLog project was created
            project_response = await client.get(
                f"{MAKERLOG_BASE_URL}/api/projects/{order_data['makerlog_project_id']}",
                headers=authenticated_user['headers']
            )
            assert project_response.status_code == 200
            project_data = project_response.json()
            
            assert project_data['source'] == 'dmlog_order'
            assert project_data['original_order_id'] == order_data['order_id']
            assert len(project_data['items']) == 2
            
            # Step 4: Simulate maker accepting the project
            accept_response = await client.post(
                f"{MAKERLOG_BASE_URL}/api/projects/{order_data['makerlog_project_id']}/accept",
                json={'estimated_completion': '2024-09-15', 'quote': 145.00},
                headers=authenticated_user['headers']
            )
            assert accept_response.status_code == 200
            
            # Step 5: Check order status updated
            status_response = await client.get(
                f"{CROSS_APP_ORDERS_URL}/api/orders/{order_data['order_id']}/status",
                headers=authenticated_user['headers']
            )
            assert status_response.status_code == 200
            status_data = status_response.json()
            
            assert status_data['status'] == 'accepted'
            assert status_data['quote'] == 145.00
            
            # Step 6: Test order tracking
            tracking_response = await client.get(
                f"{CROSS_APP_ORDERS_URL}/api/orders/{order_data['order_id']}/tracking",
                headers=authenticated_user['headers']
            )
            assert tracking_response.status_code == 200
            tracking_data = tracking_response.json()
            
            assert len(tracking_data['timeline']) > 0
            assert tracking_data['current_status'] == 'accepted'

    @pytest.mark.asyncio
    async def test_order_with_custom_specifications(self, authenticated_user):
        """Test order flow with detailed custom specifications"""
        
        complex_item = {
            'name': 'Custom Battle Map',
            'type': 'accessory',
            'description': 'Large format battle map with specific encounter layout',
            'specifications': {
                'dimensions': '36x24 inches',
                'material': 'vinyl with dry-erase surface',
                'grid_type': '1-inch squares',
                'artwork': 'custom dungeon layout',
                'lamination': 'heavy-duty',
                'mounting': 'hanging grommets'
            },
            'reference_images': [
                'https://example.com/sketch1.jpg',
                'https://example.com/sketch2.jpg'
            ],
            'special_requirements': [
                'Waterproof coating',
                'Portable storage tube included'
            ]
        }
        
        async with httpx.AsyncClient() as client:
            order_response = await client.post(
                f"{CROSS_APP_ORDERS_URL}/api/orders/create",
                json={
                    'items': [complex_item],
                    'target_platform': 'makerlog',
                    'priority': 'high',
                    'delivery_requirements': {
                        'max_delivery_time': 21,
                        'shipping_preference': 'expedited'
                    }
                },
                headers=authenticated_user['headers']
            )
            
            assert order_response.status_code == 201
            order_data = order_response.json()
            
            # Verify specifications were preserved
            assert 'specifications_preserved' in order_data
            assert order_data['specifications_preserved'] == True

    @pytest.mark.asyncio
    async def test_order_rejection_flow(self, dmlog_campaign, authenticated_user):
        """Test handling of rejected orders"""
        
        async with httpx.AsyncClient() as client:
            # Create order
            order_response = await client.post(
                f"{CROSS_APP_ORDERS_URL}/api/orders/create", 
                json={
                    'items': dmlog_campaign['custom_items'],
                    'target_platform': 'makerlog'
                },
                headers=authenticated_user['headers']
            )
            order_id = order_response.json()['order_id']
            makerlog_project_id = order_response.json()['makerlog_project_id']
            
            # Simulate maker rejection
            reject_response = await client.post(
                f"{MAKERLOG_BASE_URL}/api/projects/{makerlog_project_id}/reject",
                json={
                    'reason': 'Insufficient detail in specifications',
                    'suggestions': 'Please provide material preferences and color scheme'
                },
                headers=authenticated_user['headers']
            )
            assert reject_response.status_code == 200
            
            # Check order status
            status_response = await client.get(
                f"{CROSS_APP_ORDERS_URL}/api/orders/{order_id}/status",
                headers=authenticated_user['headers']
            )
            status_data = status_response.json()
            
            assert status_data['status'] == 'rejected'
            assert 'rejection_reason' in status_data
            assert 'suggestions' in status_data

    @pytest.mark.asyncio
    async def test_bulk_order_processing(self, authenticated_user):
        """Test processing multiple orders simultaneously"""
        
        orders = []
        for i in range(5):
            orders.append({
                'campaign_name': f'Campaign {i+1}',
                'items': [
                    {
                        'name': f'Custom Item {i+1}',
                        'type': 'accessory',
                        'description': f'Test item for campaign {i+1}'
                    }
                ],
                'target_platform': 'makerlog'
            })
        
        async with httpx.AsyncClient() as client:
            # Submit bulk order
            bulk_response = await client.post(
                f"{CROSS_APP_ORDERS_URL}/api/orders/bulk-create",
                json={'orders': orders},
                headers=authenticated_user['headers']
            )
            
            assert bulk_response.status_code == 201
            bulk_data = bulk_response.json()
            
            assert len(bulk_data['created_orders']) == 5
            assert bulk_data['total_projects_created'] == 5
            
            # Verify all orders were processed
            for order_id in bulk_data['created_orders']:
                status_response = await client.get(
                    f"{CROSS_APP_ORDERS_URL}/api/orders/{order_id}/status",
                    headers=authenticated_user['headers']
                )
                assert status_response.status_code == 200

    @pytest.mark.asyncio
    async def test_payment_integration(self, authenticated_user):
        """Test payment processing in cross-app orders"""
        
        order_item = {
            'name': 'Premium Dice Set',
            'type': 'accessory',
            'estimated_cost': 75.00
        }
        
        async with httpx.AsyncClient() as client:
            # Create order
            order_response = await client.post(
                f"{CROSS_APP_ORDERS_URL}/api/orders/create",
                json={
                    'items': [order_item],
                    'target_platform': 'makerlog',
                    'payment_method': 'credits'
                },
                headers=authenticated_user['headers']
            )
            order_id = order_response.json()['order_id']
            
            # Accept order with final quote
            makerlog_project_id = order_response.json()['makerlog_project_id']
            accept_response = await client.post(
                f"{MAKERLOG_BASE_URL}/api/projects/{makerlog_project_id}/accept",
                json={'quote': 80.00},
                headers=authenticated_user['headers']
            )
            
            # Process payment
            payment_response = await client.post(
                f"{CROSS_APP_ORDERS_URL}/api/orders/{order_id}/payment/process",
                json={'confirm_payment': True},
                headers=authenticated_user['headers']
            )
            
            assert payment_response.status_code == 200
            payment_data = payment_response.json()
            
            assert payment_data['payment_status'] == 'completed'
            assert payment_data['amount_charged'] == 80.00
            assert payment_data['remaining_credits'] == 120.00

    @pytest.mark.asyncio
    async def test_order_modification_flow(self, authenticated_user):
        """Test modifying orders after creation but before acceptance"""
        
        original_item = {
            'name': 'Basic Dice Tower',
            'type': 'accessory',
            'specifications': {'material': 'plastic'}
        }
        
        async with httpx.AsyncClient() as client:
            # Create order
            order_response = await client.post(
                f"{CROSS_APP_ORDERS_URL}/api/orders/create",
                json={'items': [original_item], 'target_platform': 'makerlog'},
                headers=authenticated_user['headers']
            )
            order_id = order_response.json()['order_id']
            
            # Modify order
            modification = {
                'items': [{
                    'name': 'Premium Wooden Dice Tower',
                    'type': 'accessory',
                    'specifications': {
                        'material': 'oak wood',
                        'finish': 'stained and sealed'
                    }
                }],
                'modification_reason': 'Upgraded material preference'
            }
            
            modify_response = await client.put(
                f"{CROSS_APP_ORDERS_URL}/api/orders/{order_id}/modify",
                json=modification,
                headers=authenticated_user['headers']
            )
            
            assert modify_response.status_code == 200
            
            # Verify modification reflected in MakerLog project
            makerlog_project_id = order_response.json()['makerlog_project_id']
            project_response = await client.get(
                f"{MAKERLOG_BASE_URL}/api/projects/{makerlog_project_id}",
                headers=authenticated_user['headers']
            )
            project_data = project_response.json()
            
            assert project_data['items'][0]['specifications']['material'] == 'oak wood'

    @pytest.mark.asyncio
    async def test_cross_app_notifications(self, authenticated_user):
        """Test notification system across DMLog and MakerLog"""
        
        async with httpx.AsyncClient() as client:
            # Create order
            order_response = await client.post(
                f"{CROSS_APP_ORDERS_URL}/api/orders/create",
                json={
                    'items': [{'name': 'Test Item', 'type': 'accessory'}],
                    'target_platform': 'makerlog',
                    'enable_notifications': True
                },
                headers=authenticated_user['headers']
            )
            order_id = order_response.json()['order_id']
            
            # Check notifications were created
            notifications_response = await client.get(
                f"{API_GATEWAY_URL}/api/notifications",
                headers=authenticated_user['headers']
            )
            
            notifications = notifications_response.json()['notifications']
            order_notifications = [n for n in notifications if order_id in n.get('metadata', {}).get('order_id', '')]
            
            assert len(order_notifications) > 0
            assert any(n['type'] == 'cross_app_order_created' for n in order_notifications)

    @pytest.mark.asyncio
    async def test_error_recovery_mechanisms(self, authenticated_user):
        """Test system recovery from various error conditions"""
        
        async with httpx.AsyncClient() as client:
            # Test recovery from MakerLog service downtime
            with patch('httpx.AsyncClient.post') as mock_post:
                # Simulate MakerLog service error
                mock_post.side_effect = httpx.ConnectError("Service unavailable")
                
                order_response = await client.post(
                    f"{CROSS_APP_ORDERS_URL}/api/orders/create",
                    json={
                        'items': [{'name': 'Test Item', 'type': 'accessory'}],
                        'target_platform': 'makerlog'
                    },
                    headers=authenticated_user['headers']
                )
                
                # Should still create order but with retry status
                assert order_response.status_code == 202  # Accepted for processing
                order_data = order_response.json()
                assert order_data['status'] == 'pending_retry'

    @pytest.mark.load
    async def test_concurrent_order_processing(self, authenticated_user):
        """Test system under concurrent order load"""
        
        async def create_order(session_id: int):
            async with httpx.AsyncClient() as client:
                return await client.post(
                    f"{CROSS_APP_ORDERS_URL}/api/orders/create",
                    json={
                        'items': [{'name': f'Concurrent Item {session_id}', 'type': 'accessory'}],
                        'target_platform': 'makerlog'
                    },
                    headers=authenticated_user['headers']
                )
        
        # Create 20 concurrent orders
        tasks = [create_order(i) for i in range(20)]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify most orders succeeded
        successful_orders = [r for r in responses if not isinstance(r, Exception) and r.status_code in [201, 202]]
        assert len(successful_orders) >= 18  # Allow for some failures under load

    @pytest.mark.asyncio
    async def test_data_consistency_validation(self, dmlog_campaign, authenticated_user):
        """Test data consistency between DMLog and MakerLog systems"""
        
        async with httpx.AsyncClient() as client:
            # Create order
            order_response = await client.post(
                f"{CROSS_APP_ORDERS_URL}/api/orders/create",
                json={
                    'campaign_id': dmlog_campaign['id'],
                    'items': dmlog_campaign['custom_items'],
                    'target_platform': 'makerlog'
                },
                headers=authenticated_user['headers']
            )
            
            order_id = order_response.json()['order_id']
            makerlog_project_id = order_response.json()['makerlog_project_id']
            
            # Verify data consistency
            order_details = await client.get(
                f"{CROSS_APP_ORDERS_URL}/api/orders/{order_id}",
                headers=authenticated_user['headers']
            )
            
            project_details = await client.get(
                f"{MAKERLOG_BASE_URL}/api/projects/{makerlog_project_id}",
                headers=authenticated_user['headers']
            )
            
            order_data = order_details.json()
            project_data = project_details.json()
            
            # Validate consistency
            assert len(order_data['items']) == len(project_data['items'])
            
            for i, order_item in enumerate(order_data['items']):
                project_item = project_data['items'][i]
                assert order_item['name'] == project_item['name']
                assert order_item['type'] == project_item['type']
                if 'specifications' in order_item:
                    assert order_item['specifications'] == project_item['specifications']