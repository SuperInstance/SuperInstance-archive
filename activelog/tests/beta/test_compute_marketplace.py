"""
Integration tests for compute marketplace transactions
Tests the compute resource sharing and marketplace functionality
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
COMPUTE_EXCHANGE_URL = "http://localhost:8009"
COMPUTE_MARKET_URL = "http://localhost:8010"
API_GATEWAY_URL = "http://localhost:8000"
MONITORING_URL = "http://localhost:8011"


class TestComputeMarketplace:
    """Test compute marketplace transactions and resource sharing"""
    
    @pytest.fixture
    def compute_provider_profile(self):
        """Sample compute provider profile"""
        return {
            'provider_id': str(uuid.uuid4()),
            'name': 'High-Performance Computing Co.',
            'description': 'GPU cluster for AI/ML workloads',
            'location': 'US-West-2',
            'verified': True,
            'resources': {
                'gpu_clusters': [
                    {
                        'name': 'RTX-4090-Cluster-01',
                        'gpu_count': 8,
                        'gpu_type': 'RTX 4090',
                        'memory_per_gpu': '24GB',
                        'compute_capability': '8.9'
                    },
                    {
                        'name': 'A100-Cluster-01', 
                        'gpu_count': 4,
                        'gpu_type': 'A100',
                        'memory_per_gpu': '80GB',
                        'compute_capability': '8.0'
                    }
                ],
                'cpu_nodes': [
                    {
                        'name': 'CPU-Node-01',
                        'cores': 64,
                        'memory': '512GB',
                        'architecture': 'x86_64'
                    }
                ]
            },
            'pricing': {
                'gpu_rtx4090_per_hour': 2.50,
                'gpu_a100_per_hour': 8.00,
                'cpu_core_per_hour': 0.10,
                'storage_gb_per_hour': 0.01
            },
            'availability': {
                'uptime_sla': 99.9,
                'maintenance_windows': ['Sunday 02:00-04:00 UTC']
            }
        }
    
    @pytest.fixture
    def compute_consumer_profile(self):
        """Sample compute consumer profile"""
        return {
            'consumer_id': str(uuid.uuid4()),
            'name': 'AI Research Lab',
            'organization': 'University Research',
            'budget_limit': 1000.00,
            'preferred_regions': ['US-West-2', 'US-East-1'],
            'workload_types': ['machine_learning', 'data_processing', 'simulation'],
            'credits_balance': 500.00
        }
    
    @pytest.fixture
    def ml_training_job(self):
        """Sample ML training job request"""
        return {
            'job_id': str(uuid.uuid4()),
            'name': 'BERT Model Fine-tuning',
            'description': 'Fine-tune BERT model on custom dataset',
            'requirements': {
                'gpu_count': 2,
                'gpu_memory': '16GB',
                'cpu_cores': 8,
                'memory': '64GB',
                'storage': '100GB',
                'estimated_runtime': '4 hours',
                'max_runtime': '6 hours'
            },
            'docker_image': 'tensorflow/tensorflow:2.12.0-gpu',
            'environment_vars': {
                'DATASET_PATH': '/data/bert_dataset',
                'MODEL_OUTPUT_PATH': '/output/bert_model',
                'BATCH_SIZE': '32'
            },
            'budget_limit': 50.00,
            'priority': 'normal'
        }
    
    @pytest.fixture
    async def authenticated_sessions(self, compute_provider_profile, compute_consumer_profile):
        """Authenticated sessions for provider and consumer"""
        return {
            'provider': {
                'user_id': compute_provider_profile['provider_id'],
                'token': 'provider.test.token',
                'headers': {'Authorization': 'Bearer provider.test.token'},
                'profile': compute_provider_profile
            },
            'consumer': {
                'user_id': compute_consumer_profile['consumer_id'],
                'token': 'consumer.test.token',
                'headers': {'Authorization': 'Bearer consumer.test.token'},
                'profile': compute_consumer_profile
            }
        }

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_compute_resource_listing_and_discovery(self, authenticated_sessions):
        """Test listing and discovering available compute resources"""
        
        async with httpx.AsyncClient() as client:
            # Step 1: Provider registers their compute resources
            provider_session = authenticated_sessions['provider']
            
            registration_response = await client.post(
                f"{COMPUTE_EXCHANGE_URL}/api/providers/register",
                json=provider_session['profile'],
                headers=provider_session['headers']
            )
            assert registration_response.status_code == 201
            
            provider_data = registration_response.json()
            assert provider_data['status'] == 'registered'
            assert 'verification_pending' in provider_data
            
            # Step 2: Simulate verification completion
            verify_response = await client.post(
                f"{COMPUTE_EXCHANGE_URL}/api/providers/{provider_session['user_id']}/verify",
                json={'verification_status': 'approved', 'admin_notes': 'Test verification'},
                headers={'Authorization': 'Bearer admin.token'}  # Admin token
            )
            assert verify_response.status_code == 200
            
            # Step 3: Consumer searches for available resources
            consumer_session = authenticated_sessions['consumer']
            
            search_response = await client.get(
                f"{COMPUTE_MARKET_URL}/api/resources/search",
                params={
                    'gpu_type': 'RTX 4090',
                    'min_gpu_count': 2,
                    'max_price_per_hour': 5.00,
                    'region': 'US-West-2'
                },
                headers=consumer_session['headers']
            )
            assert search_response.status_code == 200
            
            search_results = search_response.json()
            assert len(search_results['resources']) > 0
            
            # Verify our provider's resources appear in results
            provider_resource = next(
                (r for r in search_results['resources'] 
                 if r['provider_id'] == provider_session['user_id']),
                None
            )
            assert provider_resource is not None
            assert provider_resource['gpu_type'] == 'RTX 4090'
            assert provider_resource['available'] == True

    @pytest.mark.asyncio
    async def test_compute_job_submission_and_matching(self, authenticated_sessions, ml_training_job):
        """Test submitting compute jobs and automatic resource matching"""
        
        async with httpx.AsyncClient() as client:
            consumer_session = authenticated_sessions['consumer']
            provider_session = authenticated_sessions['provider']
            
            # Setup provider first
            await client.post(
                f"{COMPUTE_EXCHANGE_URL}/api/providers/register",
                json=provider_session['profile'],
                headers=provider_session['headers']
            )
            
            # Step 1: Consumer submits job request
            job_response = await client.post(
                f"{COMPUTE_MARKET_URL}/api/jobs/submit",
                json=ml_training_job,
                headers=consumer_session['headers']
            )
            assert job_response.status_code == 201
            
            job_data = job_response.json()
            assert job_data['status'] == 'pending_match'
            assert 'estimated_cost' in job_data
            job_id = job_data['job_id']
            
            # Step 2: Wait for automatic resource matching
            matched = False
            for _ in range(10):
                match_status = await client.get(
                    f"{COMPUTE_MARKET_URL}/api/jobs/{job_id}/status",
                    headers=consumer_session['headers']
                )
                status_data = match_status.json()
                
                if status_data['status'] == 'matched':
                    matched = True
                    assert 'matched_provider' in status_data
                    assert 'resource_allocation' in status_data
                    break
                elif status_data['status'] == 'failed':
                    pytest.fail(f"Job matching failed: {status_data.get('error')}")
                
                await asyncio.sleep(1)
            
            assert matched, "Job was not matched within timeout period"
            
            # Step 3: Verify resource reservation
            reservation_response = await client.get(
                f"{COMPUTE_EXCHANGE_URL}/api/providers/{provider_session['user_id']}/reservations",
                headers=provider_session['headers']
            )
            reservations = reservation_response.json()['reservations']
            
            job_reservation = next(
                (r for r in reservations if r['job_id'] == job_id),
                None
            )
            assert job_reservation is not None
            assert job_reservation['status'] == 'reserved'

    @pytest.mark.asyncio
    async def test_compute_job_execution_lifecycle(self, authenticated_sessions, ml_training_job):
        """Test complete compute job execution lifecycle"""
        
        async with httpx.AsyncClient() as client:
            consumer_session = authenticated_sessions['consumer']
            provider_session = authenticated_sessions['provider']
            
            # Setup and submit job
            await client.post(
                f"{COMPUTE_EXCHANGE_URL}/api/providers/register",
                json=provider_session['profile'],
                headers=provider_session['headers']
            )
            
            job_response = await client.post(
                f"{COMPUTE_MARKET_URL}/api/jobs/submit",
                json=ml_training_job,
                headers=consumer_session['headers']
            )
            job_id = job_response.json()['job_id']
            
            # Wait for matching
            await asyncio.sleep(2)
            
            # Step 1: Provider accepts the job
            accept_response = await client.post(
                f"{COMPUTE_EXCHANGE_URL}/api/jobs/{job_id}/accept",
                json={
                    'estimated_start_time': (datetime.utcnow() + timedelta(minutes=5)).isoformat(),
                    'resource_allocation': {
                        'gpu_cluster': 'RTX-4090-Cluster-01',
                        'gpu_count': 2,
                        'cpu_cores': 8,
                        'memory': '64GB'
                    }
                },
                headers=provider_session['headers']
            )
            assert accept_response.status_code == 200
            
            # Step 2: Job execution starts
            start_response = await client.post(
                f"{COMPUTE_EXCHANGE_URL}/api/jobs/{job_id}/start",
                json={
                    'container_id': 'container_abc123',
                    'actual_resources': {
                        'gpu_ids': ['gpu_0', 'gpu_1'],
                        'node_id': 'node_001'
                    }
                },
                headers=provider_session['headers']
            )
            assert start_response.status_code == 200
            
            # Step 3: Monitor job progress
            progress_updates = [
                {'progress': 0.25, 'status': 'training', 'epoch': 1},
                {'progress': 0.50, 'status': 'training', 'epoch': 2},
                {'progress': 0.75, 'status': 'training', 'epoch': 3},
                {'progress': 1.0, 'status': 'completed', 'epoch': 4}
            ]
            
            for update in progress_updates:
                progress_response = await client.post(
                    f"{COMPUTE_EXCHANGE_URL}/api/jobs/{job_id}/progress",
                    json=update,
                    headers=provider_session['headers']
                )
                assert progress_response.status_code == 200
                await asyncio.sleep(0.5)
            
            # Step 4: Job completion
            completion_response = await client.post(
                f"{COMPUTE_EXCHANGE_URL}/api/jobs/{job_id}/complete",
                json={
                    'exit_code': 0,
                    'runtime_hours': 3.5,
                    'output_files': [
                        {'name': 'model.h5', 'size': '500MB'},
                        {'name': 'training_log.txt', 'size': '2MB'}
                    ],
                    'resource_usage': {
                        'peak_gpu_memory': '14GB',
                        'avg_cpu_usage': 0.85,
                        'total_compute_hours': 7.0  # 2 GPUs * 3.5 hours
                    }
                },
                headers=provider_session['headers']
            )
            assert completion_response.status_code == 200
            
            # Step 5: Verify final status and billing
            final_status = await client.get(
                f"{COMPUTE_MARKET_URL}/api/jobs/{job_id}/status",
                headers=consumer_session['headers']
            )
            status_data = final_status.json()
            
            assert status_data['status'] == 'completed'
            assert status_data['runtime_hours'] == 3.5
            assert 'final_cost' in status_data
            
            # Verify cost calculation (2 GPUs * 3.5 hours * $2.50/hour)
            expected_cost = 2 * 3.5 * 2.50  # $17.50
            assert abs(status_data['final_cost'] - expected_cost) < 0.01

    @pytest.mark.asyncio
    async def test_compute_resource_scaling(self, authenticated_sessions):
        """Test dynamic resource scaling during job execution"""
        
        async with httpx.AsyncClient() as client:
            consumer_session = authenticated_sessions['consumer']
            provider_session = authenticated_sessions['provider']
            
            # Setup provider with scalable resources
            scalable_profile = provider_session['profile'].copy()
            scalable_profile['scaling_options'] = {
                'auto_scale': True,
                'min_resources': {'gpu_count': 1, 'cpu_cores': 4},
                'max_resources': {'gpu_count': 8, 'cpu_cores': 32},
                'scale_up_threshold': 0.8,  # 80% utilization
                'scale_down_threshold': 0.3  # 30% utilization
            }
            
            await client.post(
                f"{COMPUTE_EXCHANGE_URL}/api/providers/register",
                json=scalable_profile,
                headers=provider_session['headers']
            )
            
            # Submit job with scaling requirements
            scaling_job = {
                'name': 'Variable Load Training',
                'requirements': {
                    'gpu_count': 2,  # Initial requirement
                    'max_gpu_count': 6,  # Can scale up to 6
                    'auto_scale': True
                },
                'budget_limit': 100.00
            }
            
            job_response = await client.post(
                f"{COMPUTE_MARKET_URL}/api/jobs/submit",
                json=scaling_job,
                headers=consumer_session['headers']
            )
            job_id = job_response.json()['job_id']
            
            await asyncio.sleep(2)  # Wait for matching
            
            # Start job
            await client.post(
                f"{COMPUTE_EXCHANGE_URL}/api/jobs/{job_id}/start",
                json={'initial_resources': {'gpu_count': 2}},
                headers=provider_session['headers']
            )
            
            # Simulate high resource utilization triggering scale-up
            scale_trigger = await client.post(
                f"{COMPUTE_EXCHANGE_URL}/api/jobs/{job_id}/metrics",
                json={
                    'timestamp': datetime.utcnow().isoformat(),
                    'gpu_utilization': 0.95,  # High utilization
                    'memory_usage': 0.88,
                    'queue_length': 100
                },
                headers=provider_session['headers']
            )
            assert scale_trigger.status_code == 200
            
            # Check if scaling was triggered
            scaling_status = await client.get(
                f"{COMPUTE_EXCHANGE_URL}/api/jobs/{job_id}/scaling-events",
                headers=provider_session['headers']
            )
            events = scaling_status.json()['scaling_events']
            
            scale_up_event = next(
                (e for e in events if e['action'] == 'scale_up'),
                None
            )
            assert scale_up_event is not None
            assert scale_up_event['from_gpu_count'] == 2
            assert scale_up_event['to_gpu_count'] > 2

    @pytest.mark.asyncio
    async def test_compute_marketplace_bidding(self, authenticated_sessions, ml_training_job):
        """Test bidding system for compute resources"""
        
        async with httpx.AsyncClient() as client:
            consumer_session = authenticated_sessions['consumer']
            
            # Create multiple provider profiles with different pricing
            providers = []
            for i in range(3):
                provider_profile = {
                    'provider_id': str(uuid.uuid4()),
                    'name': f'Compute Provider {i+1}',
                    'resources': {
                        'gpu_clusters': [{
                            'name': f'GPU-Cluster-{i+1}',
                            'gpu_count': 4,
                            'gpu_type': 'RTX 4090'
                        }]
                    },
                    'pricing': {
                        'gpu_rtx4090_per_hour': 2.0 + (i * 0.5)  # $2.0, $2.5, $3.0
                    }
                }
                
                await client.post(
                    f"{COMPUTE_EXCHANGE_URL}/api/providers/register",
                    json=provider_profile,
                    headers={'Authorization': f'Bearer provider_{i}.token'}
                )
                providers.append(provider_profile)
            
            # Submit job with bidding enabled
            bidding_job = ml_training_job.copy()
            bidding_job['bidding_enabled'] = True
            bidding_job['max_price_per_gpu_hour'] = 2.75
            bidding_job['auction_duration_minutes'] = 5
            
            auction_response = await client.post(
                f"{COMPUTE_MARKET_URL}/api/jobs/submit-auction",
                json=bidding_job,
                headers=consumer_session['headers']
            )
            assert auction_response.status_code == 201
            
            auction_data = auction_response.json()
            assert auction_data['status'] == 'auction_active'
            auction_id = auction_data['auction_id']
            
            # Simulate provider bids
            bids = [
                {'provider_id': providers[0]['provider_id'], 'price_per_gpu_hour': 2.25, 'estimated_start': 10},
                {'provider_id': providers[1]['provider_id'], 'price_per_gpu_hour': 2.40, 'estimated_start': 5},
                {'provider_id': providers[2]['provider_id'], 'price_per_gpu_hour': 2.70, 'estimated_start': 2}
            ]
            
            for i, bid in enumerate(bids):
                bid_response = await client.post(
                    f"{COMPUTE_MARKET_URL}/api/auctions/{auction_id}/bid",
                    json=bid,
                    headers={'Authorization': f'Bearer provider_{i}.token'}
                )
                assert bid_response.status_code == 200
            
            # Wait for auction to complete (shortened for testing)
            await asyncio.sleep(2)
            
            # Force auction completion
            complete_response = await client.post(
                f"{COMPUTE_MARKET_URL}/api/auctions/{auction_id}/complete",
                headers={'Authorization': 'Bearer admin.token'}
            )
            assert complete_response.status_code == 200
            
            # Verify winning bid
            result_response = await client.get(
                f"{COMPUTE_MARKET_URL}/api/auctions/{auction_id}/result",
                headers=consumer_session['headers']
            )
            result = result_response.json()
            
            assert result['status'] == 'completed'
            assert result['winning_bid']['price_per_gpu_hour'] == 2.25  # Lowest bid
            assert result['winning_bid']['provider_id'] == providers[0]['provider_id']

    @pytest.mark.asyncio
    async def test_compute_resource_monitoring_and_sla(self, authenticated_sessions, ml_training_job):
        """Test resource monitoring and SLA compliance"""
        
        async with httpx.AsyncClient() as client:
            consumer_session = authenticated_sessions['consumer']
            provider_session = authenticated_sessions['provider']
            
            # Setup provider with SLA commitments
            sla_profile = provider_session['profile'].copy()
            sla_profile['sla'] = {
                'uptime_guarantee': 99.9,
                'response_time_ms': 100,
                'throughput_guarantee': 0.95,
                'penalties': {
                    'uptime_breach': 0.1,  # 10% credit
                    'performance_breach': 0.05  # 5% credit
                }
            }
            
            await client.post(
                f"{COMPUTE_EXCHANGE_URL}/api/providers/register",
                json=sla_profile,
                headers=provider_session['headers']
            )
            
            # Submit and start job
            job_response = await client.post(
                f"{COMPUTE_MARKET_URL}/api/jobs/submit",
                json=ml_training_job,
                headers=consumer_session['headers']
            )
            job_id = job_response.json()['job_id']
            
            await asyncio.sleep(1)
            await client.post(
                f"{COMPUTE_EXCHANGE_URL}/api/jobs/{job_id}/start",
                headers=provider_session['headers']
            )
            
            # Send monitoring data
            monitoring_data = [
                {
                    'timestamp': datetime.utcnow().isoformat(),
                    'cpu_usage': 0.85,
                    'gpu_usage': 0.92,
                    'memory_usage': 0.78,
                    'network_io': 1500000,  # bytes/sec
                    'disk_io': 500000,
                    'response_time_ms': 95
                },
                {
                    'timestamp': (datetime.utcnow() + timedelta(minutes=1)).isoformat(),
                    'cpu_usage': 0.88,
                    'gpu_usage': 0.94,
                    'memory_usage': 0.82,
                    'network_io': 1600000,
                    'disk_io': 450000,
                    'response_time_ms': 110  # SLA breach
                }
            ]
            
            for data in monitoring_data:
                monitor_response = await client.post(
                    f"{MONITORING_URL}/api/jobs/{job_id}/metrics",
                    json=data,
                    headers=provider_session['headers']
                )
                assert monitor_response.status_code == 200
            
            # Check SLA compliance
            sla_response = await client.get(
                f"{MONITORING_URL}/api/jobs/{job_id}/sla-status",
                headers=consumer_session['headers']
            )
            sla_status = sla_response.json()
            
            assert 'sla_breaches' in sla_status
            assert len(sla_status['sla_breaches']) == 1  # Response time breach
            assert sla_status['sla_breaches'][0]['type'] == 'response_time'
            assert sla_status['overall_compliance'] < 100.0

    @pytest.mark.asyncio
    async def test_compute_cost_optimization(self, authenticated_sessions):
        """Test cost optimization features for compute jobs"""
        
        async with httpx.AsyncClient() as client:
            consumer_session = authenticated_sessions['consumer']
            
            # Create job with cost optimization preferences
            cost_optimized_job = {
                'name': 'Cost-Optimized Training',
                'requirements': {
                    'gpu_count': 4,
                    'flexible_gpu_type': True,  # Allow different GPU types
                    'preemptible': True,  # Allow interruption for lower cost
                    'deadline': (datetime.utcnow() + timedelta(hours=12)).isoformat()
                },
                'optimization_preferences': {
                    'priority': 'cost',  # vs 'speed' or 'reliability'
                    'max_interruptions': 3,
                    'auto_checkpoint_interval': 30,  # minutes
                    'spot_instance_ok': True
                },
                'budget_limit': 25.00
            }
            
            optimization_response = await client.post(
                f"{COMPUTE_MARKET_URL}/api/jobs/submit-optimized",
                json=cost_optimized_job,
                headers=consumer_session['headers']
            )
            assert optimization_response.status_code == 201
            
            optimization_data = optimization_response.json()
            assert 'cost_projections' in optimization_data
            assert 'alternative_configurations' in optimization_data
            
            # Verify cost projections include multiple options
            projections = optimization_data['cost_projections']
            assert len(projections) > 1
            
            # Should include spot pricing option
            spot_option = next(
                (p for p in projections if p['instance_type'] == 'spot'),
                None
            )
            assert spot_option is not None
            assert spot_option['estimated_cost'] < projections[0]['estimated_cost']
            
            # Choose the spot option
            job_id = optimization_data['job_id']
            choice_response = await client.post(
                f"{COMPUTE_MARKET_URL}/api/jobs/{job_id}/choose-configuration",
                json={'selected_configuration': 'spot_optimized'},
                headers=consumer_session['headers']
            )
            assert choice_response.status_code == 200

    @pytest.mark.asyncio
    async def test_multi_region_compute_deployment(self, authenticated_sessions):
        """Test deploying compute jobs across multiple regions"""
        
        async with httpx.AsyncClient() as client:
            consumer_session = authenticated_sessions['consumer']
            
            # Register providers in different regions
            regions = ['us-west-2', 'us-east-1', 'eu-west-1']
            provider_ids = []
            
            for i, region in enumerate(regions):
                provider_profile = {
                    'provider_id': str(uuid.uuid4()),
                    'name': f'Provider {region}',
                    'location': region,
                    'resources': {
                        'gpu_clusters': [{
                            'gpu_count': 4,
                            'gpu_type': 'RTX 4090'
                        }]
                    },
                    'pricing': {'gpu_rtx4090_per_hour': 2.0 + (i * 0.2)}
                }
                
                await client.post(
                    f"{COMPUTE_EXCHANGE_URL}/api/providers/register",
                    json=provider_profile,
                    headers={'Authorization': f'Bearer provider_{region}.token'}
                )
                provider_ids.append(provider_profile['provider_id'])
            
            # Submit distributed training job
            distributed_job = {
                'name': 'Multi-Region Distributed Training',
                'requirements': {
                    'total_gpu_count': 8,
                    'distribution_strategy': 'multi_region',
                    'preferred_regions': regions,
                    'communication_latency_tolerance': 100  # ms
                },
                'job_type': 'distributed_training',
                'budget_limit': 80.00
            }
            
            distributed_response = await client.post(
                f"{COMPUTE_MARKET_URL}/api/jobs/submit-distributed",
                json=distributed_job,
                headers=consumer_session['headers']
            )
            assert distributed_response.status_code == 201
            
            job_data = distributed_response.json()
            assert job_data['distribution_plan']['regions'] == len(regions)
            assert job_data['total_nodes'] >= 2  # At least 2 nodes for distribution

    @pytest.mark.load
    async def test_concurrent_compute_marketplace_operations(self, authenticated_sessions):
        """Test marketplace under concurrent load"""
        
        async def submit_random_job(session_id: int):
            async with httpx.AsyncClient() as client:
                job_data = {
                    'name': f'Concurrent Job {session_id}',
                    'requirements': {
                        'gpu_count': random.randint(1, 4),
                        'estimated_runtime': f'{random.randint(1, 6)} hours'
                    },
                    'budget_limit': random.uniform(20.0, 100.0)
                }
                
                return await client.post(
                    f"{COMPUTE_MARKET_URL}/api/jobs/submit",
                    json=job_data,
                    headers=authenticated_sessions['consumer']['headers']
                )
        
        # Submit 20 concurrent jobs
        tasks = [submit_random_job(i) for i in range(20)]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify most jobs were submitted successfully
        successful_jobs = [
            r for r in responses 
            if not isinstance(r, Exception) and r.status_code == 201
        ]
        assert len(successful_jobs) >= 18  # Allow for some failures under load
        
        # Verify the marketplace can handle the load
        marketplace_status = await httpx.AsyncClient().get(
            f"{COMPUTE_MARKET_URL}/api/status"
        )
        assert marketplace_status.status_code == 200
        status_data = marketplace_status.json()
        assert status_data['queue_length'] >= 18

    @pytest.mark.asyncio
    async def test_compute_fraud_detection_and_security(self, authenticated_sessions):
        """Test fraud detection and security measures in compute marketplace"""
        
        async with httpx.AsyncClient() as client:
            consumer_session = authenticated_sessions['consumer']
            
            # Test 1: Detect suspicious job patterns
            suspicious_jobs = []
            for i in range(10):
                job_data = {
                    'name': f'Suspicious Job {i}',
                    'requirements': {'gpu_count': 8},  # High resource request
                    'budget_limit': 1000.00,  # High budget
                    'priority': 'urgent'
                }
                
                response = await client.post(
                    f"{COMPUTE_MARKET_URL}/api/jobs/submit",
                    json=job_data,
                    headers=consumer_session['headers']
                )
                suspicious_jobs.append(response)
            
            # Check if fraud detection was triggered
            fraud_check = await client.get(
                f"{COMPUTE_MARKET_URL}/api/fraud/user-activity",
                headers=consumer_session['headers']
            )
            fraud_data = fraud_check.json()
            
            assert 'risk_score' in fraud_data
            assert fraud_data['risk_score'] > 0.7  # High risk due to suspicious pattern
            
            # Test 2: Resource verification
            verification_response = await client.post(
                f"{COMPUTE_EXCHANGE_URL}/api/verification/resource-audit",
                json={'provider_id': authenticated_sessions['provider']['user_id']},
                headers={'Authorization': 'Bearer admin.token'}
            )
            assert verification_response.status_code == 200
            
            verification_result = verification_response.json()
            assert 'resource_verification' in verification_result
            assert verification_result['resource_verification']['status'] == 'verified'