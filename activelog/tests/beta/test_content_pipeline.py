"""
Integration tests for content creation pipeline
Tests AI-powered content generation, processing, and delivery across platforms
"""

import pytest
import asyncio
import uuid
import json
import base64
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import httpx
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os

# Test configuration
CONTENT_CREATOR_URL = "http://localhost:8012"
AI_ORCHESTRATOR_URL = "http://localhost:8013"
CREATIVE_SUITE_URL = "http://localhost:8014"
VIDEO_PROCESSOR_URL = "http://localhost:8015"
API_GATEWAY_URL = "http://localhost:8000"


class TestContentCreationPipeline:
    """Test comprehensive content creation and processing pipeline"""
    
    @pytest.fixture
    def content_creator_profile(self):
        """Sample content creator profile"""
        return {
            'creator_id': str(uuid.uuid4()),
            'name': 'Alex ContentMaker',
            'brand': 'Epic Adventures Studio',
            'content_types': ['blog_posts', 'social_media', 'video_scripts', 'd&d_campaigns'],
            'target_audience': 'tabletop_gaming_enthusiasts',
            'tone_preferences': {
                'primary_tone': 'friendly',
                'secondary_tone': 'informative',
                'avoid_tones': ['overly_formal', 'condescending']
            },
            'brand_guidelines': {
                'color_scheme': ['#2D5AA0', '#F4A261', '#E76F51'],
                'fonts': ['Roboto', 'Open Sans'],
                'logo_usage': 'always_include',
                'content_pillars': ['education', 'entertainment', 'community']
            },
            'ai_preferences': {
                'creativity_level': 0.7,
                'fact_checking': True,
                'plagiarism_check': True,
                'brand_consistency': True
            }
        }
    
    @pytest.fixture
    def campaign_content_request(self):
        """Sample D&D campaign content request"""
        return {
            'content_type': 'd&d_campaign',
            'title': 'The Cursed Lighthouse',
            'requirements': {
                'system': 'D&D 5e',
                'level_range': '3-5',
                'session_count': 4,
                'theme': 'maritime_horror',
                'player_count': '4-6',
                'estimated_duration': '16 hours total'
            },
            'deliverables': [
                'campaign_overview',
                'session_outlines',
                'npc_stat_blocks',
                'custom_monsters',
                'battle_maps',
                'handouts',
                'ambient_music_playlist'
            ],
            'deadline': (datetime.utcnow() + timedelta(days=7)).isoformat(),
            'budget': 'premium_tier'
        }
    
    @pytest.fixture
    def video_content_request(self):
        """Sample video content request"""
        return {
            'content_type': 'educational_video',
            'title': 'D&D Character Creation Guide for Beginners',
            'requirements': {
                'duration': '10-12 minutes',
                'format': '1080p MP4',
                'style': 'animated_explainer',
                'narration': 'ai_generated',
                'background_music': True,
                'subtitles': ['english', 'spanish'],
                'thumbnail_variants': 3
            },
            'script_outline': [
                'Introduction to D&D',
                'Choosing a Race',
                'Selecting a Class', 
                'Rolling Stats',
                'Equipment and Backstory',
                'Next Steps'
            ],
            'branding': {
                'include_logo': True,
                'color_scheme': 'brand_colors',
                'end_screen_template': 'subscribe_cta'
            }
        }
    
    @pytest.fixture
    async def authenticated_creator_session(self, content_creator_profile):
        """Authenticated content creator session"""
        return {
            'creator': content_creator_profile,
            'token': 'creator.test.token',
            'headers': {'Authorization': 'Bearer creator.test.token'}
        }

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_ai_campaign_generation_pipeline(self, authenticated_creator_session, campaign_content_request):
        """Test complete AI-powered D&D campaign generation"""
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            creator_session = authenticated_creator_session
            
            # Step 1: Submit campaign generation request
            generation_response = await client.post(
                f"{CONTENT_CREATOR_URL}/api/generate/campaign",
                json=campaign_content_request,
                headers=creator_session['headers']
            )
            assert generation_response.status_code == 202
            
            generation_data = generation_response.json()
            assert 'generation_job_id' in generation_data
            assert generation_data['status'] == 'queued'
            job_id = generation_data['generation_job_id']
            
            # Step 2: Monitor generation progress
            generation_complete = False
            for _ in range(30):  # Wait up to 30 seconds
                status_response = await client.get(
                    f"{CONTENT_CREATOR_URL}/api/jobs/{job_id}/status",
                    headers=creator_session['headers']
                )
                status_data = status_response.json()
                
                if status_data['status'] == 'completed':
                    generation_complete = True
                    assert 'deliverables' in status_data
                    break
                elif status_data['status'] == 'failed':
                    pytest.fail(f"Campaign generation failed: {status_data.get('error')}")
                
                await asyncio.sleep(2)
            
            assert generation_complete, "Campaign generation did not complete in time"
            
            # Step 3: Verify all deliverables were created
            deliverables_response = await client.get(
                f"{CONTENT_CREATOR_URL}/api/jobs/{job_id}/deliverables",
                headers=creator_session['headers']
            )
            deliverables = deliverables_response.json()['deliverables']
            
            expected_deliverables = campaign_content_request['deliverables']
            for deliverable_type in expected_deliverables:
                assert any(d['type'] == deliverable_type for d in deliverables)
            
            # Step 4: Verify content quality and consistency
            campaign_overview = next(d for d in deliverables if d['type'] == 'campaign_overview')
            overview_content = campaign_overview['content']
            
            assert 'The Cursed Lighthouse' in overview_content['title']
            assert overview_content['theme'] == 'maritime_horror'
            assert overview_content['level_range'] == '3-5'
            
            # Step 5: Test content customization
            customization_request = {
                'deliverable_id': campaign_overview['id'],
                'modifications': {
                    'tone_adjustment': 'more_dramatic',
                    'add_section': 'safety_tools_discussion',
                    'expand_section': 'session_zero_guidelines'
                }
            }
            
            customization_response = await client.post(
                f"{CONTENT_CREATOR_URL}/api/deliverables/{campaign_overview['id']}/customize",
                json=customization_request,
                headers=creator_session['headers']
            )
            assert customization_response.status_code == 200
            
            customized_content = customization_response.json()['updated_content']
            assert 'safety_tools' in customized_content.lower()

    @pytest.mark.asyncio
    async def test_video_content_production_pipeline(self, authenticated_creator_session, video_content_request):
        """Test complete video content production from script to final video"""
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            creator_session = authenticated_creator_session
            
            # Step 1: Generate video script
            script_response = await client.post(
                f"{AI_ORCHESTRATOR_URL}/api/generate/video-script",
                json=video_content_request,
                headers=creator_session['headers']
            )
            assert script_response.status_code == 201
            
            script_data = script_response.json()
            assert 'script_sections' in script_data
            assert len(script_data['script_sections']) == len(video_content_request['script_outline'])
            
            # Step 2: Generate visual assets
            visual_request = {
                'script_id': script_data['script_id'],
                'style': video_content_request['requirements']['style'],
                'scenes': script_data['script_sections'],
                'brand_guidelines': creator_session['creator']['brand_guidelines']
            }
            
            visual_response = await client.post(
                f"{CREATIVE_SUITE_URL}/api/generate/visual-assets",
                json=visual_request,
                headers=creator_session['headers']
            )
            assert visual_response.status_code == 202
            
            visual_job_id = visual_response.json()['job_id']
            
            # Wait for visual generation
            await asyncio.sleep(10)
            
            visual_status = await client.get(
                f"{CREATIVE_SUITE_URL}/api/jobs/{visual_job_id}/status",
                headers=creator_session['headers']
            )
            assert visual_status.json()['status'] == 'completed'
            
            # Step 3: Generate AI narration
            narration_request = {
                'script_id': script_data['script_id'],
                'voice_profile': 'friendly_educator',
                'speed': 'normal',
                'language': 'english',
                'emotion_tags': ['enthusiasm', 'clarity', 'warmth']
            }
            
            narration_response = await client.post(
                f"{AI_ORCHESTRATOR_URL}/api/generate/narration",
                json=narration_request,
                headers=creator_session['headers']
            )
            assert narration_response.status_code == 201
            
            narration_data = narration_response.json()
            assert 'audio_segments' in narration_data
            
            # Step 4: Compile final video
            compilation_request = {
                'script_id': script_data['script_id'],
                'visual_job_id': visual_job_id,
                'narration_data': narration_data,
                'background_music': video_content_request['requirements']['background_music'],
                'output_format': {
                    'resolution': '1080p',
                    'framerate': 30,
                    'format': 'MP4',
                    'quality': 'high'
                },
                'branding': video_content_request['branding']
            }
            
            compilation_response = await client.post(
                f"{VIDEO_PROCESSOR_URL}/api/compile/video",
                json=compilation_request,
                headers=creator_session['headers']
            )
            assert compilation_response.status_code == 202
            
            compilation_job_id = compilation_response.json()['job_id']
            
            # Step 5: Monitor video compilation
            compilation_complete = False
            for _ in range(60):  # Video processing can take longer
                compilation_status = await client.get(
                    f"{VIDEO_PROCESSOR_URL}/api/jobs/{compilation_job_id}/status",
                    headers=creator_session['headers']
                )
                status_data = compilation_status.json()
                
                if status_data['status'] == 'completed':
                    compilation_complete = True
                    assert 'video_url' in status_data
                    assert 'thumbnail_urls' in status_data
                    break
                elif status_data['status'] == 'failed':
                    pytest.fail(f"Video compilation failed: {status_data.get('error')}")
                
                await asyncio.sleep(2)
            
            assert compilation_complete, "Video compilation did not complete in time"
            
            # Step 6: Verify video metadata and quality
            final_video = compilation_status.json()
            assert final_video['duration_seconds'] >= 600  # At least 10 minutes
            assert final_video['resolution'] == '1080p'
            assert len(final_video['thumbnail_urls']) == 3  # 3 variants requested

    @pytest.mark.asyncio
    async def test_multi_format_content_adaptation(self, authenticated_creator_session):
        """Test adapting content for multiple platforms and formats"""
        
        async with httpx.AsyncClient() as client:
            creator_session = authenticated_creator_session
            
            # Step 1: Create source content
            source_content = {
                'type': 'blog_post',
                'title': 'Building Your First D&D Character',
                'content': 'A comprehensive guide covering race selection, class features, ability scores, and character backstory development...',
                'target_length': 2000,
                'audience': 'beginners'
            }
            
            source_response = await client.post(
                f"{CONTENT_CREATOR_URL}/api/content/create",
                json=source_content,
                headers=creator_session['headers']
            )
            source_id = source_response.json()['content_id']
            
            # Step 2: Adapt for multiple platforms
            adaptations = [
                {
                    'platform': 'twitter',
                    'format': 'thread',
                    'constraints': {'max_tweets': 10, 'max_chars_per_tweet': 280}
                },
                {
                    'platform': 'instagram',
                    'format': 'carousel_post',
                    'constraints': {'max_slides': 8, 'visual_style': 'infographic'}
                },
                {
                    'platform': 'youtube',
                    'format': 'video_description',
                    'constraints': {'max_chars': 5000, 'include_timestamps': True}
                },
                {
                    'platform': 'tiktok',
                    'format': 'short_video_script',
                    'constraints': {'duration': '60_seconds', 'hook_required': True}
                }
            ]
            
            adaptation_jobs = []
            for adaptation in adaptations:
                adapt_response = await client.post(
                    f"{CONTENT_CREATOR_URL}/api/content/{source_id}/adapt",
                    json=adaptation,
                    headers=creator_session['headers']
                )
                assert adapt_response.status_code == 202
                adaptation_jobs.append((adaptation['platform'], adapt_response.json()['job_id']))
            
            # Step 3: Wait for all adaptations to complete
            completed_adaptations = {}
            for platform, job_id in adaptation_jobs:
                for _ in range(15):
                    status_response = await client.get(
                        f"{CONTENT_CREATOR_URL}/api/jobs/{job_id}/status",
                        headers=creator_session['headers']
                    )
                    status = status_response.json()
                    
                    if status['status'] == 'completed':
                        completed_adaptations[platform] = status['adapted_content']
                        break
                    
                    await asyncio.sleep(1)
            
            # Step 4: Verify adaptations meet platform constraints
            assert len(completed_adaptations) == len(adaptations)
            
            # Twitter thread verification
            twitter_content = completed_adaptations['twitter']
            assert len(twitter_content['tweets']) <= 10
            assert all(len(tweet['text']) <= 280 for tweet in twitter_content['tweets'])
            
            # Instagram carousel verification
            instagram_content = completed_adaptations['instagram']
            assert len(instagram_content['slides']) <= 8
            assert all('visual_description' in slide for slide in instagram_content['slides'])
            
            # TikTok script verification
            tiktok_content = completed_adaptations['tiktok']
            assert 'hook' in tiktok_content
            assert tiktok_content['estimated_duration'] <= 60

    @pytest.mark.asyncio
    async def test_content_collaboration_workflow(self, authenticated_creator_session):
        """Test collaborative content creation and review workflows"""
        
        async with httpx.AsyncClient() as client:
            creator_session = authenticated_creator_session
            
            # Step 1: Create collaborative project
            project_data = {
                'title': 'Epic Fantasy Campaign Series',
                'description': 'Multi-session campaign with custom world building',
                'collaborators': [
                    {'role': 'world_builder', 'user_id': str(uuid.uuid4())},
                    {'role': 'artist', 'user_id': str(uuid.uuid4())},
                    {'role': 'editor', 'user_id': str(uuid.uuid4())}
                ],
                'workflow_stages': [
                    'concept_development',
                    'world_building',
                    'content_creation', 
                    'art_production',
                    'editing_review',
                    'final_approval'
                ]
            }
            
            project_response = await client.post(
                f"{CONTENT_CREATOR_URL}/api/projects/collaborative",
                json=project_data,
                headers=creator_session['headers']
            )
            assert project_response.status_code == 201
            project_id = project_response.json()['project_id']
            
            # Step 2: Submit content for review
            content_submission = {
                'stage': 'content_creation',
                'content_type': 'campaign_module',
                'content': {
                    'title': 'Module 1: The Goblin Uprising',
                    'synopsis': 'Players investigate mysterious goblin raids...',
                    'encounters': ['goblin_ambush', 'goblin_king_throne_room'],
                    'npcs': ['Grax the Goblin King', 'Mira the Village Elder']
                },
                'notes_for_reviewers': 'Looking for feedback on encounter balance and NPC motivations'
            }
            
            submission_response = await client.post(
                f"{CONTENT_CREATOR_URL}/api/projects/{project_id}/submit",
                json=content_submission,
                headers=creator_session['headers']
            )
            assert submission_response.status_code == 201
            submission_id = submission_response.json()['submission_id']
            
            # Step 3: Simulate editor review
            editor_review = {
                'overall_rating': 4,
                'feedback': {
                    'strengths': ['Creative encounter design', 'Rich NPC backgrounds'],
                    'suggestions': ['Add more environmental details', 'Consider goblin tactics'],
                    'required_changes': ['Fix typo in NPC name', 'Clarify treasure distribution']
                },
                'status': 'revision_requested'
            }
            
            review_response = await client.post(
                f"{CONTENT_CREATOR_URL}/api/submissions/{submission_id}/review",
                json=editor_review,
                headers={'Authorization': 'Bearer editor.token'}
            )
            assert review_response.status_code == 200
            
            # Step 4: Submit revision
            revision_data = {
                'changes_made': ['Fixed NPC name typo', 'Added environmental descriptions'],
                'response_to_feedback': 'Addressed all required changes and incorporated suggestions',
                'updated_content': content_submission['content']  # Would include actual changes
            }
            
            revision_response = await client.post(
                f"{CONTENT_CREATOR_URL}/api/submissions/{submission_id}/revise",
                json=revision_data,
                headers=creator_session['headers']
            )
            assert revision_response.status_code == 200
            
            # Step 5: Verify workflow progression
            workflow_status = await client.get(
                f"{CONTENT_CREATOR_URL}/api/projects/{project_id}/workflow-status",
                headers=creator_session['headers']
            )
            workflow_data = workflow_status.json()
            
            assert workflow_data['current_stage'] == 'editing_review'
            assert len(workflow_data['completed_stages']) >= 2

    @pytest.mark.asyncio
    async def test_content_personalization_engine(self, authenticated_creator_session):
        """Test AI-powered content personalization based on audience data"""
        
        async with httpx.AsyncClient() as client:
            creator_session = authenticated_creator_session
            
            # Step 1: Define audience segments
            audience_segments = [
                {
                    'name': 'New Players',
                    'characteristics': {
                        'experience_level': 'beginner',
                        'preferred_content_length': 'short',
                        'learning_style': 'visual',
                        'interests': ['character_creation', 'basic_rules']
                    }
                },
                {
                    'name': 'Veteran Players',
                    'characteristics': {
                        'experience_level': 'expert',
                        'preferred_content_length': 'detailed',
                        'learning_style': 'analytical',
                        'interests': ['advanced_tactics', 'homebrew_rules', 'optimization']
                    }
                },
                {
                    'name': 'Dungeon Masters',
                    'characteristics': {
                        'experience_level': 'intermediate',
                        'preferred_content_length': 'comprehensive',
                        'learning_style': 'practical',
                        'interests': ['world_building', 'npc_creation', 'encounter_design']
                    }
                }
            ]
            
            # Step 2: Create base content
            base_content = {
                'topic': 'Combat Mechanics in D&D 5e',
                'core_information': [
                    'Initiative and turn order',
                    'Attack rolls and armor class',
                    'Damage types and resistance',
                    'Actions, bonus actions, and reactions',
                    'Opportunity attacks and movement'
                ],
                'complexity_level': 'medium'
            }
            
            # Step 3: Generate personalized versions
            personalized_versions = {}
            for segment in audience_segments:
                personalization_request = {
                    'base_content': base_content,
                    'target_audience': segment,
                    'personalization_factors': {
                        'adjust_complexity': True,
                        'add_examples': True,
                        'modify_tone': True,
                        'include_visuals': segment['characteristics']['learning_style'] == 'visual'
                    }
                }
                
                personalize_response = await client.post(
                    f"{AI_ORCHESTRATOR_URL}/api/personalize/content",
                    json=personalization_request,
                    headers=creator_session['headers']
                )
                assert personalize_response.status_code == 201
                
                personalized_versions[segment['name']] = personalize_response.json()['personalized_content']
            
            # Step 4: Verify personalization differences
            new_player_content = personalized_versions['New Players']
            veteran_content = personalized_versions['Veteran Players']
            dm_content = personalized_versions['Dungeon Masters']
            
            # New players should have simpler language and more examples
            assert new_player_content['reading_level'] < veteran_content['reading_level']
            assert len(new_player_content['examples']) > len(veteran_content['examples'])
            
            # Veteran content should have more technical details
            assert 'advanced_mechanics' in veteran_content['sections']
            assert 'optimization_tips' in veteran_content['sections']
            
            # DM content should focus on practical application
            assert 'running_combat_tips' in dm_content['sections']
            assert 'common_mistakes' in dm_content['sections']

    @pytest.mark.asyncio
    async def test_content_analytics_and_optimization(self, authenticated_creator_session):
        """Test content performance analytics and optimization suggestions"""
        
        async with httpx.AsyncClient() as client:
            creator_session = authenticated_creator_session
            
            # Step 1: Create content with tracking
            tracked_content = {
                'title': 'The Ultimate Guide to D&D Spellcasting',
                'content_type': 'blog_post',
                'content': 'Comprehensive guide content...',
                'tracking_enabled': True,
                'analytics_goals': ['engagement', 'shares', 'conversion_to_premium']
            }
            
            content_response = await client.post(
                f"{CONTENT_CREATOR_URL}/api/content/create-tracked",
                json=tracked_content,
                headers=creator_session['headers']
            )
            content_id = content_response.json()['content_id']
            
            # Step 2: Simulate analytics data
            analytics_data = {
                'content_id': content_id,
                'metrics': {
                    'views': 5420,
                    'unique_visitors': 3890,
                    'time_on_page': 340,  # seconds
                    'bounce_rate': 0.32,
                    'social_shares': 156,
                    'comments': 42,
                    'premium_conversions': 23
                },
                'audience_segments': {
                    'new_players': {'views': 2170, 'engagement_rate': 0.65},
                    'experienced_players': {'views': 2380, 'engagement_rate': 0.58},
                    'dungeon_masters': {'views': 870, 'engagement_rate': 0.78}
                },
                'traffic_sources': {
                    'organic_search': 0.45,
                    'social_media': 0.32,
                    'direct': 0.15,
                    'referrals': 0.08
                }
            }
            
            # Submit analytics data
            analytics_response = await client.post(
                f"{CONTENT_CREATOR_URL}/api/analytics/record",
                json=analytics_data,
                headers=creator_session['headers']
            )
            assert analytics_response.status_code == 200
            
            # Step 3: Get optimization suggestions
            optimization_response = await client.get(
                f"{AI_ORCHESTRATOR_URL}/api/analytics/optimize/{content_id}",
                headers=creator_session['headers']
            )
            assert optimization_response.status_code == 200
            
            optimization_data = optimization_response.json()
            
            # Step 4: Verify optimization suggestions are relevant
            suggestions = optimization_data['suggestions']
            assert len(suggestions) > 0
            
            # Should suggest improving engagement with experienced players (lowest rate)
            engagement_suggestion = next(
                (s for s in suggestions if 'experienced_players' in s['target_segment']),
                None
            )
            assert engagement_suggestion is not None
            
            # Should suggest leveraging high DM engagement
            dm_leverage_suggestion = next(
                (s for s in suggestions if 'dungeon_masters' in s['description']),
                None
            )
            assert dm_leverage_suggestion is not None

    @pytest.mark.load
    async def test_content_pipeline_scalability(self, authenticated_creator_session):
        """Test content pipeline under high load"""
        
        async def generate_content_batch(batch_id: int):
            async with httpx.AsyncClient() as client:
                batch_requests = []
                for i in range(5):
                    content_request = {
                        'type': 'social_media_post',
                        'platform': 'twitter',
                        'topic': f'D&D Tip #{batch_id * 5 + i}',
                        'hashtags': ['DnD', 'TTRPG', 'Gaming'],
                        'tone': 'helpful'
                    }
                    batch_requests.append(content_request)
                
                return await client.post(
                    f"{CONTENT_CREATOR_URL}/api/generate/batch",
                    json={'requests': batch_requests},
                    headers=authenticated_creator_session['headers']
                )
        
        # Generate 10 batches concurrently (50 pieces of content)
        tasks = [generate_content_batch(i) for i in range(10)]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify most batches completed successfully
        successful_batches = [
            r for r in responses 
            if not isinstance(r, Exception) and r.status_code in [201, 202]
        ]
        assert len(successful_batches) >= 8
        
        # Verify system health after load test
        health_response = await httpx.AsyncClient().get(
            f"{CONTENT_CREATOR_URL}/api/health"
        )
        assert health_response.status_code == 200
        health_data = health_response.json()
        assert health_data['status'] == 'healthy'
        assert health_data['queue_length'] < 100  # Queue should be manageable