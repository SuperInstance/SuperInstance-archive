"""
Integration tests for complete user journey from signup to first creation
Tests the end-to-end user experience across the ActiveLog ecosystem
"""

import pytest
import asyncio
import uuid
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import httpx
from unittest.mock import Mock, patch, MagicMock
import random
import string

# Test configuration
AUTH_SERVICE_URL = "http://localhost:8001"
API_GATEWAY_URL = "http://localhost:8000"
DMLOG_URL = "http://localhost:8300"
MAKERLOG_URL = "http://localhost:8301"
STUDYLOG_URL = "http://localhost:8303"
FRONTEND_SHELL_URL = "http://localhost:3000"


class TestUserJourney:
    """Test complete user journey from signup to first meaningful creation"""
    
    @pytest.fixture
    def user_persona_beginner(self):
        """Beginner user persona for testing"""
        return {
            'type': 'beginner',
            'email': f'beginner_{uuid.uuid4().hex[:8]}@example.com',
            'name': 'Alex Newcomer',
            'interests': ['d&d', 'creative projects'],
            'experience_level': 'novice',
            'goals': ['learn d&d', 'create custom items', 'connect with others'],
            'preferred_platform': 'dmlog'
        }
    
    @pytest.fixture
    def user_persona_creator(self):
        """Creator/maker user persona for testing"""
        return {
            'type': 'creator',
            'email': f'creator_{uuid.uuid4().hex[:8]}@example.com',
            'name': 'Jordan Craftsperson',
            'interests': ['3d printing', 'woodworking', 'custom designs'],
            'experience_level': 'intermediate',
            'goals': ['sell custom items', 'build portfolio', 'grow business'],
            'preferred_platform': 'makerlog'
        }
    
    @pytest.fixture
    def user_persona_student(self):
        """Student user persona for testing"""
        return {
            'type': 'student',
            'email': f'student_{uuid.uuid4().hex[:8]}@example.com',
            'name': 'Casey Learner',
            'interests': ['mathematics', 'science', 'gamification'],
            'experience_level': 'novice',
            'goals': ['improve grades', 'learn efficiently', 'track progress'],
            'preferred_platform': 'studylog'
        }

    async def complete_signup_flow(self, client: httpx.AsyncClient, user_persona: Dict) -> Dict:
        """Complete the signup process for a user persona"""
        
        # Step 1: Check email availability
        email_check_response = await client.get(
            f"{AUTH_SERVICE_URL}/api/auth/check-email",
            params={'email': user_persona['email']}
        )
        assert email_check_response.status_code == 200
        assert email_check_response.json()['available'] == True
        
        # Step 2: Register user
        registration_data = {
            'email': user_persona['email'],
            'name': user_persona['name'],
            'password': 'SecurePassword123!',
            'interests': user_persona['interests'],
            'experience_level': user_persona['experience_level'],
            'goals': user_persona['goals'],
            'preferred_platform': user_persona['preferred_platform'],
            'marketing_consent': True
        }
        
        register_response = await client.post(
            f"{AUTH_SERVICE_URL}/api/auth/register",
            json=registration_data
        )
        assert register_response.status_code == 201
        
        registration_result = register_response.json()
        assert 'user_id' in registration_result
        assert 'verification_token' in registration_result
        
        # Step 3: Verify email (simulate email verification)
        verify_response = await client.post(
            f"{AUTH_SERVICE_URL}/api/auth/verify-email",
            json={'token': registration_result['verification_token']}
        )
        assert verify_response.status_code == 200
        
        # Step 4: Complete login
        login_response = await client.post(
            f"{AUTH_SERVICE_URL}/api/auth/login",
            json={
                'email': user_persona['email'],
                'password': 'SecurePassword123!'
            }
        )
        assert login_response.status_code == 200
        
        login_result = login_response.json()
        return {
            'user_id': registration_result['user_id'],
            'access_token': login_result['access_token'],
            'refresh_token': login_result['refresh_token'],
            'headers': {'Authorization': f"Bearer {login_result['access_token']}"},
            'profile': login_result['user']
        }

    async def complete_onboarding_flow(self, client: httpx.AsyncClient, user_session: Dict, persona: Dict) -> Dict:
        """Complete the onboarding tutorial and setup"""
        
        # Step 1: Get onboarding tasks
        onboarding_response = await client.get(
            f"{API_GATEWAY_URL}/api/onboarding/tasks",
            headers=user_session['headers']
        )
        assert onboarding_response.status_code == 200
        
        tasks = onboarding_response.json()['tasks']
        assert len(tasks) > 0
        
        onboarding_progress = {}
        
        # Step 2: Complete profile setup
        profile_setup = await client.put(
            f"{API_GATEWAY_URL}/api/user/profile",
            json={
                'bio': f"New to {persona['preferred_platform']}, excited to learn!",
                'avatar_url': 'https://example.com/default-avatar.png',
                'skills': persona['interests'],
                'goals': persona['goals']
            },
            headers=user_session['headers']
        )
        assert profile_setup.status_code == 200
        onboarding_progress['profile_setup'] = True
        
        # Step 3: Take platform-specific tutorial
        tutorial_start = await client.post(
            f"{API_GATEWAY_URL}/api/tutorials/start",
            json={'tutorial_type': f"{persona['preferred_platform']}_basics"},
            headers=user_session['headers']
        )
        assert tutorial_start.status_code == 201
        
        tutorial_id = tutorial_start.json()['tutorial_id']
        
        # Simulate completing tutorial steps
        for step in range(3):
            step_response = await client.post(
                f"{API_GATEWAY_URL}/api/tutorials/{tutorial_id}/complete-step",
                json={'step': step, 'time_spent': 120},
                headers=user_session['headers']
            )
            assert step_response.status_code == 200
        
        onboarding_progress['tutorial_completed'] = True
        
        # Step 4: Connect to preferred platform
        platform_connection = await client.post(
            f"{API_GATEWAY_URL}/api/platforms/{persona['preferred_platform']}/connect",
            headers=user_session['headers']
        )
        assert platform_connection.status_code == 200
        onboarding_progress['platform_connected'] = True
        
        # Step 5: Complete onboarding
        onboarding_complete = await client.post(
            f"{API_GATEWAY_URL}/api/onboarding/complete",
            headers=user_session['headers']
        )
        assert onboarding_complete.status_code == 200
        
        return onboarding_progress

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_beginner_dmlog_journey(self, user_persona_beginner):
        """Test complete journey for a beginner user creating their first D&D campaign"""
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Complete signup and onboarding
            user_session = await self.complete_signup_flow(client, user_persona_beginner)
            onboarding_progress = await self.complete_onboarding_flow(client, user_session, user_persona_beginner)
            
            assert all(onboarding_progress.values())
            
            # Step 1: Create first D&D campaign
            campaign_data = {
                'name': 'My First D&D Adventure',
                'description': 'A beginner-friendly campaign for new players',
                'setting': 'fantasy',
                'max_players': 4,
                'experience_level': 'beginner',
                'session_frequency': 'weekly',
                'platform_preferences': ['online', 'voice_chat']
            }
            
            campaign_response = await client.post(
                f"{DMLOG_URL}/api/campaigns",
                json=campaign_data,
                headers=user_session['headers']
            )
            assert campaign_response.status_code == 201
            campaign_id = campaign_response.json()['campaign_id']
            
            # Step 2: Use AI assistant to help design first encounter
            ai_help_response = await client.post(
                f"{DMLOG_URL}/api/ai/encounter-generator",
                json={
                    'campaign_id': campaign_id,
                    'encounter_type': 'social',
                    'difficulty': 'easy',
                    'theme': 'tavern meeting'
                },
                headers=user_session['headers']
            )
            assert ai_help_response.status_code == 200
            encounter_data = ai_help_response.json()
            
            assert 'npcs' in encounter_data
            assert 'dialogue_options' in encounter_data
            assert 'suggested_outcomes' in encounter_data
            
            # Step 3: Save the encounter to campaign
            save_encounter_response = await client.post(
                f"{DMLOG_URL}/api/campaigns/{campaign_id}/encounters",
                json={
                    'name': 'First Tavern Meeting',
                    'data': encounter_data,
                    'encounter_type': 'social'
                },
                headers=user_session['headers']
            )
            assert save_encounter_response.status_code == 201
            
            # Step 4: Invite players (simulate finding players through platform)
            player_invites = [
                {'email': 'player1@example.com', 'role': 'player'},
                {'email': 'player2@example.com', 'role': 'player'}
            ]
            
            for invite in player_invites:
                invite_response = await client.post(
                    f"{DMLOG_URL}/api/campaigns/{campaign_id}/invites",
                    json=invite,
                    headers=user_session['headers']
                )
                assert invite_response.status_code == 201
            
            # Step 5: Schedule first session
            session_schedule = await client.post(
                f"{DMLOG_URL}/api/campaigns/{campaign_id}/sessions/schedule",
                json={
                    'date': (datetime.utcnow() + timedelta(days=7)).isoformat(),
                    'duration_hours': 3,
                    'platform': 'discord',
                    'notes': 'First session - character creation and introductions'
                },
                headers=user_session['headers']
            )
            assert session_schedule.status_code == 201
            
            # Step 6: Verify achievement unlocked
            achievements_response = await client.get(
                f"{API_GATEWAY_URL}/api/user/achievements",
                headers=user_session['headers']
            )
            achievements = achievements_response.json()['achievements']
            
            first_campaign_achievement = next(
                (a for a in achievements if a['type'] == 'first_campaign_created'), 
                None
            )
            assert first_campaign_achievement is not None
            assert first_campaign_achievement['unlocked'] == True

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_creator_makerlog_journey(self, user_persona_creator):
        """Test complete journey for a creator setting up their MakerLog profile and first project"""
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Complete signup and onboarding
            user_session = await self.complete_signup_flow(client, user_persona_creator)
            onboarding_progress = await self.complete_onboarding_flow(client, user_session, user_persona_creator)
            
            # Step 1: Set up maker profile with portfolio
            maker_profile = {
                'business_name': 'Jordan\'s Custom Creations',
                'specialties': ['3d_printing', 'woodworking', 'laser_cutting'],
                'experience_years': 3,
                'location': 'Austin, TX',
                'shipping_options': ['local_pickup', 'us_shipping'],
                'payment_methods': ['stripe', 'paypal'],
                'portfolio_description': 'Creating unique, custom items for tabletop gaming and home decor'
            }
            
            profile_response = await client.post(
                f"{MAKERLOG_URL}/api/makers/profile",
                json=maker_profile,
                headers=user_session['headers']
            )
            assert profile_response.status_code == 201
            
            # Step 2: Upload portfolio images
            portfolio_items = [
                {
                    'title': 'Custom Dice Tower',
                    'description': 'Hand-crafted oak dice tower with custom engraving',
                    'images': ['https://example.com/dice-tower-1.jpg'],
                    'materials': ['oak_wood', 'brass_hardware'],
                    'time_to_complete': 8,
                    'price_range': [45, 75]
                },
                {
                    'title': '3D Printed Miniatures',
                    'description': 'High-detail resin miniatures for tabletop gaming',
                    'images': ['https://example.com/miniatures-1.jpg'],
                    'materials': ['resin'],
                    'time_to_complete': 2,
                    'price_range': [15, 25]
                }
            ]
            
            for item in portfolio_items:
                portfolio_response = await client.post(
                    f"{MAKERLOG_URL}/api/makers/portfolio",
                    json=item,
                    headers=user_session['headers']
                )
                assert portfolio_response.status_code == 201
            
            # Step 3: Set availability and preferences
            availability_response = await client.put(
                f"{MAKERLOG_URL}/api/makers/availability",
                json={
                    'accepting_projects': True,
                    'capacity': 'medium',
                    'lead_time_days': 14,
                    'min_project_value': 25.00,
                    'max_project_value': 500.00,
                    'preferred_project_types': ['gaming_accessories', 'home_decor']
                },
                headers=user_session['headers']
            )
            assert availability_response.status_code == 200
            
            # Step 4: Create first project (responding to order request)
            # Simulate receiving an order request
            project_data = {
                'title': 'Custom Battle Map Set',
                'client_requirements': {
                    'item_type': 'battle_maps',
                    'quantity': 3,
                    'size': 'large_format',
                    'theme': 'dungeon',
                    'deadline': (datetime.utcnow() + timedelta(days=21)).isoformat()
                },
                'estimated_hours': 12,
                'material_costs': 35.00,
                'quoted_price': 120.00,
                'project_notes': 'Three interconnected dungeon maps with modular design'
            }
            
            project_response = await client.post(
                f"{MAKERLOG_URL}/api/projects",
                json=project_data,
                headers=user_session['headers']
            )
            assert project_response.status_code == 201
            project_id = project_response.json()['project_id']
            
            # Step 5: Document project progress
            progress_updates = [
                {'status': 'design_phase', 'notes': 'Completed initial sketches and layout plans'},
                {'status': 'material_prep', 'notes': 'Materials ordered and received'},
                {'status': 'production', 'notes': 'Started cutting and assembly'}
            ]
            
            for update in progress_updates:
                progress_response = await client.post(
                    f"{MAKERLOG_URL}/api/projects/{project_id}/progress",
                    json=update,
                    headers=user_session['headers']
                )
                assert progress_response.status_code == 201
                
                # Simulate time passing
                await asyncio.sleep(0.1)
            
            # Step 6: Complete project and request payment
            completion_response = await client.post(
                f"{MAKERLOG_URL}/api/projects/{project_id}/complete",
                json={
                    'completion_photos': ['https://example.com/completed-maps.jpg'],
                    'final_notes': 'Project completed successfully, ready for delivery',
                    'shipping_tracking': 'TRACK123456'
                },
                headers=user_session['headers']
            )
            assert completion_response.status_code == 200
            
            # Step 7: Verify maker achievement and rating system
            profile_check = await client.get(
                f"{MAKERLOG_URL}/api/makers/profile",
                headers=user_session['headers']
            )
            profile_data = profile_check.json()
            
            assert profile_data['projects_completed'] == 1
            assert profile_data['total_earnings'] == 120.00
            assert 'first_project_completion' in profile_data['achievements']

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_student_studylog_journey(self, user_persona_student):
        """Test complete journey for a student setting up learning goals and tracking progress"""
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Complete signup and onboarding
            user_session = await self.complete_signup_flow(client, user_persona_student)
            onboarding_progress = await self.complete_onboarding_flow(client, user_session, user_persona_student)
            
            # Step 1: Set up learning profile and goals
            learning_profile = {
                'grade_level': '9th',
                'subjects_of_interest': ['mathematics', 'physics', 'computer_science'],
                'learning_style': 'visual',
                'study_goals': [
                    {'subject': 'mathematics', 'target_grade': 'A', 'current_grade': 'B+'},
                    {'subject': 'physics', 'target_grade': 'B+', 'current_grade': 'B'},
                ],
                'study_schedule': {
                    'preferred_times': ['after_school', 'weekend_mornings'],
                    'max_session_length': 60,
                    'break_frequency': 25  # Pomodoro-style
                }
            }
            
            profile_response = await client.post(
                f"{STUDYLOG_URL}/api/students/profile",
                json=learning_profile,
                headers=user_session['headers']
            )
            assert profile_response.status_code == 201
            
            # Step 2: Create first study session
            study_session = {
                'subject': 'mathematics',
                'topic': 'Quadratic Equations',
                'planned_duration': 45,
                'resources': [
                    {'type': 'textbook', 'name': 'Algebra 2 - Chapter 4'},
                    {'type': 'online_video', 'url': 'https://example.com/quadratic-equations'}
                ],
                'goals': ['Complete practice problems 1-15', 'Understand vertex form']
            }
            
            session_response = await client.post(
                f"{STUDYLOG_URL}/api/study-sessions",
                json=study_session,
                headers=user_session['headers']
            )
            assert session_response.status_code == 201
            session_id = session_response.json()['session_id']
            
            # Step 3: Use AI tutor for help
            ai_tutor_request = {
                'subject': 'mathematics',
                'topic': 'quadratic_equations',
                'question': 'I\'m having trouble understanding how to convert from standard form to vertex form',
                'learning_style': 'visual'
            }
            
            tutor_response = await client.post(
                f"{STUDYLOG_URL}/api/ai-tutor/help",
                json=ai_tutor_request,
                headers=user_session['headers']
            )
            assert tutor_response.status_code == 200
            
            tutor_help = tutor_response.json()
            assert 'explanation' in tutor_help
            assert 'visual_examples' in tutor_help
            assert 'practice_problems' in tutor_help
            
            # Step 4: Complete study session with progress tracking
            session_completion = {
                'actual_duration': 48,
                'completed_goals': ['Complete practice problems 1-15', 'Understand vertex form'],
                'difficulty_rating': 3,  # 1-5 scale
                'confidence_level': 4,   # 1-5 scale
                'notes': 'AI tutor explanation really helped with vertex form conversion',
                'next_session_plan': 'Practice more complex quadratic problems'
            }
            
            completion_response = await client.post(
                f"{STUDYLOG_URL}/api/study-sessions/{session_id}/complete",
                json=session_completion,
                headers=user_session['headers']
            )
            assert completion_response.status_code == 200
            
            # Step 5: Take a practice quiz
            quiz_request = await client.post(
                f"{STUDYLOG_URL}/api/quizzes/generate",
                json={
                    'subject': 'mathematics',
                    'topics': ['quadratic_equations'],
                    'difficulty': 'intermediate',
                    'question_count': 5
                },
                headers=user_session['headers']
            )
            assert quiz_request.status_code == 201
            quiz_id = quiz_request.json()['quiz_id']
            
            # Simulate taking the quiz
            quiz_answers = {
                'answers': [
                    {'question_id': 1, 'answer': 'B', 'time_spent': 120},
                    {'question_id': 2, 'answer': 'A', 'time_spent': 90},
                    {'question_id': 3, 'answer': 'C', 'time_spent': 150},
                    {'question_id': 4, 'answer': 'B', 'time_spent': 110},
                    {'question_id': 5, 'answer': 'D', 'time_spent': 95}
                ]
            }
            
            quiz_submission = await client.post(
                f"{STUDYLOG_URL}/api/quizzes/{quiz_id}/submit",
                json=quiz_answers,
                headers=user_session['headers']
            )
            assert quiz_submission.status_code == 200
            
            quiz_results = quiz_submission.json()
            assert 'score' in quiz_results
            assert quiz_results['score'] >= 60  # Reasonable passing score
            
            # Step 6: View progress analytics
            progress_response = await client.get(
                f"{STUDYLOG_URL}/api/students/progress",
                headers=user_session['headers'],
                params={'timeframe': '7_days'}
            )
            assert progress_response.status_code == 200
            
            progress_data = progress_response.json()
            assert 'study_time_total' in progress_data
            assert 'topics_covered' in progress_data
            assert 'quiz_scores' in progress_data
            assert progress_data['study_time_total'] >= 48

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_cross_platform_user_journey(self, user_persona_beginner):
        """Test user journey across multiple platforms (DMLog → MakerLog integration)"""
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Start with DMLog user
            user_session = await self.complete_signup_flow(client, user_persona_beginner)
            onboarding_progress = await self.complete_onboarding_flow(client, user_session, user_persona_beginner)
            
            # Step 1: Create D&D campaign with custom item needs
            campaign_response = await client.post(
                f"{DMLOG_URL}/api/campaigns",
                json={
                    'name': 'Pirates of the Forgotten Coast',
                    'setting': 'nautical',
                    'custom_item_requests': [
                        {
                            'name': 'Ship Battle Map',
                            'type': 'battle_map',
                            'urgency': 'medium',
                            'budget': 75.00
                        }
                    ]
                },
                headers=user_session['headers']
            )
            campaign_id = campaign_response.json()['campaign_id']
            
            # Step 2: Request custom items through integrated marketplace
            item_request = await client.post(
                f"{API_GATEWAY_URL}/api/marketplace/request-item",
                json={
                    'source_platform': 'dmlog',
                    'source_id': campaign_id,
                    'item_details': {
                        'name': 'Ship Battle Map',
                        'specifications': 'Large format nautical battle map with ship interior/exterior',
                        'budget': 75.00,
                        'deadline': (datetime.utcnow() + timedelta(days=14)).isoformat()
                    },
                    'target_platform': 'makerlog'
                },
                headers=user_session['headers']
            )
            assert item_request.status_code == 201
            request_id = item_request.json()['request_id']
            
            # Step 3: Enable cross-platform notifications
            notification_setup = await client.put(
                f"{API_GATEWAY_URL}/api/user/notification-preferences",
                json={
                    'cross_platform_updates': True,
                    'item_request_updates': True,
                    'maker_responses': True
                },
                headers=user_session['headers']
            )
            assert notification_setup.status_code == 200
            
            # Step 4: Simulate maker accepting the request
            # This would normally be done by a different user, but we'll simulate it
            maker_response = await client.post(
                f"{API_GATEWAY_URL}/api/marketplace/requests/{request_id}/respond",
                json={
                    'response_type': 'accept',
                    'quoted_price': 72.00,
                    'estimated_completion': (datetime.utcnow() + timedelta(days=12)).isoformat(),
                    'maker_notes': 'I can create this as a modular battle map set'
                },
                headers=user_session['headers']
            )
            assert maker_response.status_code == 200
            
            # Step 5: Verify cross-platform data synchronization
            dmlog_item_status = await client.get(
                f"{DMLOG_URL}/api/campaigns/{campaign_id}/custom-items",
                headers=user_session['headers']
            )
            assert dmlog_item_status.status_code == 200
            
            items = dmlog_item_status.json()['custom_items']
            ship_map_item = next(item for item in items if item['name'] == 'Ship Battle Map')
            assert ship_map_item['status'] == 'accepted'
            assert ship_map_item['quoted_price'] == 72.00

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_user_journey_performance_metrics(self, user_persona_beginner):
        """Test and measure performance of critical user journey steps"""
        
        performance_metrics = {}
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Measure signup time
            start_time = time.time()
            user_session = await self.complete_signup_flow(client, user_persona_beginner)
            performance_metrics['signup_duration'] = time.time() - start_time
            
            # Measure onboarding time
            start_time = time.time()
            onboarding_progress = await self.complete_onboarding_flow(client, user_session, user_persona_beginner)
            performance_metrics['onboarding_duration'] = time.time() - start_time
            
            # Measure first content creation time
            start_time = time.time()
            campaign_response = await client.post(
                f"{DMLOG_URL}/api/campaigns",
                json={
                    'name': 'Performance Test Campaign',
                    'description': 'Testing content creation performance'
                },
                headers=user_session['headers']
            )
            performance_metrics['first_creation_duration'] = time.time() - start_time
            
            # Assert reasonable performance benchmarks
            assert performance_metrics['signup_duration'] < 5.0  # Under 5 seconds
            assert performance_metrics['onboarding_duration'] < 10.0  # Under 10 seconds
            assert performance_metrics['first_creation_duration'] < 3.0  # Under 3 seconds
            
            # Log metrics for monitoring
            print(f"Performance Metrics: {json.dumps(performance_metrics, indent=2)}")

    @pytest.mark.asyncio
    @pytest.mark.accessibility
    async def test_user_journey_accessibility(self, user_persona_beginner):
        """Test user journey with accessibility considerations"""
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Test with accessibility preferences
            user_persona_beginner['accessibility_needs'] = {
                'screen_reader': True,
                'high_contrast': True,
                'keyboard_navigation': True,
                'reduced_motion': True
            }
            
            user_session = await self.complete_signup_flow(client, user_persona_beginner)
            
            # Verify accessibility preferences are preserved
            preferences_response = await client.get(
                f"{API_GATEWAY_URL}/api/user/preferences",
                headers=user_session['headers']
            )
            
            preferences = preferences_response.json()
            assert preferences['accessibility']['screen_reader'] == True
            assert preferences['accessibility']['high_contrast'] == True

    @pytest.mark.asyncio
    @pytest.mark.security
    async def test_user_journey_security(self, user_persona_beginner):
        """Test security aspects of user journey"""
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Test that sensitive data is properly handled
            user_session = await self.complete_signup_flow(client, user_persona_beginner)
            
            # Attempt to access another user's data (should fail)
            other_user_id = str(uuid.uuid4())
            unauthorized_response = await client.get(
                f"{API_GATEWAY_URL}/api/users/{other_user_id}/profile",
                headers=user_session['headers']
            )
            assert unauthorized_response.status_code == 403
            
            # Test session token validation
            invalid_headers = {'Authorization': 'Bearer invalid.token.here'}
            invalid_response = await client.get(
                f"{API_GATEWAY_URL}/api/user/profile",
                headers=invalid_headers
            )
            assert invalid_response.status_code == 401