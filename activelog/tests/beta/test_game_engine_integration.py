"""
Integration tests for game engine integrations
Tests integration with various game engines for D&D, educational games, and simulations
"""

import pytest
import asyncio
import uuid
import json
import websockets
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import httpx
from unittest.mock import Mock, patch, MagicMock
import base64

# Test configuration
DMLOG_GAMEDEV_URL = "http://localhost:8300"
STUDYLOG_GAMES_URL = "http://localhost:8303"
GAMING_PLATFORM_URL = "http://localhost:8016"
UNITY_INTEGRATION_URL = "http://localhost:8017"
WEBSOCKET_GAME_URL = "ws://localhost:8018"


class TestGameEngineIntegration:
    """Test game engine integrations and real-time gaming features"""
    
    @pytest.fixture
    def unity_game_config(self):
        """Sample Unity game configuration for D&D integration"""
        return {
            'game_id': str(uuid.uuid4()),
            'game_name': 'D&D Virtual Tabletop',
            'engine': 'Unity 2022.3 LTS',
            'platform': 'WebGL',
            'features': [
                'real_time_multiplayer',
                'dice_rolling',
                'character_sheets',
                'battle_maps',
                'fog_of_war',
                'voice_chat',
                'initiative_tracker'
            ],
            'max_players': 8,
            'networking': {
                'protocol': 'websocket',
                'tick_rate': 30,
                'interpolation': True,
                'lag_compensation': True
            },
            'assets': {
                'character_models': 'procedural',
                'battle_maps': 'tiled_import',
                'dice_models': '3d_physics',
                'ui_theme': 'fantasy_dark'
            }
        }
    
    @pytest.fixture
    def educational_game_config(self):
        """Sample educational game configuration"""
        return {
            'game_id': str(uuid.uuid4()),
            'game_name': 'Math Quest Adventures',
            'engine': 'Godot 4.0',
            'target_audience': 'grades_6_8',
            'subjects': ['mathematics', 'problem_solving'],
            'features': [
                'adaptive_difficulty',
                'progress_tracking',
                'achievements',
                'multiplayer_cooperation',
                'teacher_dashboard'
            ],
            'learning_objectives': [
                'algebraic_thinking',
                'geometric_reasoning',
                'statistical_analysis'
            ],
            'assessment': {
                'formative': True,
                'summative': True,
                'peer_evaluation': True
            }
        }
    
    @pytest.fixture
    def game_session_data(self):
        """Sample active game session data"""
        return {
            'session_id': str(uuid.uuid4()),
            'campaign_id': str(uuid.uuid4()),
            'players': [
                {
                    'player_id': str(uuid.uuid4()),
                    'character_name': 'Thorin Stonebeard',
                    'character_class': 'Fighter',
                    'level': 5,
                    'position': {'x': 10, 'y': 15, 'z': 0}
                },
                {
                    'player_id': str(uuid.uuid4()),
                    'character_name': 'Luna Starweaver',
                    'character_class': 'Wizard',
                    'level': 5,
                    'position': {'x': 12, 'y': 15, 'z': 0}
                }
            ],
            'dm_id': str(uuid.uuid4()),
            'current_encounter': {
                'name': 'Goblin Ambush',
                'round': 3,
                'turn_order': ['player_1', 'goblin_1', 'player_2', 'goblin_2'],
                'current_turn': 'player_1'
            },
            'battle_map': {
                'name': 'Forest Clearing',
                'size': {'width': 30, 'height': 20},
                'grid_size': 5,  # feet per square
                'terrain_features': [
                    {'type': 'tree', 'position': {'x': 5, 'y': 8}},
                    {'type': 'rock', 'position': {'x': 18, 'y': 12}}
                ]
            }
        }
    
    @pytest.fixture
    async def authenticated_game_sessions(self):
        """Authenticated sessions for DM and players"""
        return {
            'dm': {
                'user_id': str(uuid.uuid4()),
                'token': 'dm.game.token',
                'headers': {'Authorization': 'Bearer dm.game.token'},
                'role': 'dungeon_master'
            },
            'players': [
                {
                    'user_id': str(uuid.uuid4()),
                    'token': f'player_0.game.token',
                    'headers': {'Authorization': f'Bearer player_0.game.token'},
                    'role': 'player'
                },
                {
                    'user_id': str(uuid.uuid4()),
                    'token': f'player_1.game.token',
                    'headers': {'Authorization': f'Bearer player_1.game.token'},
                    'role': 'player'
                }
            ]
        }

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_unity_vtt_real_time_session(self, unity_game_config, game_session_data, authenticated_game_sessions):
        """Test real-time Unity Virtual Tabletop session"""
        
        async with httpx.AsyncClient() as client:
            dm_session = authenticated_game_sessions['dm']
            player_sessions = authenticated_game_sessions['players']
            
            # Step 1: Initialize Unity game instance
            game_init_response = await client.post(
                f"{UNITY_INTEGRATION_URL}/api/games/initialize",
                json=unity_game_config,
                headers=dm_session['headers']
            )
            assert game_init_response.status_code == 201
            
            game_instance = game_init_response.json()
            assert 'game_instance_id' in game_instance
            assert 'websocket_url' in game_instance
            game_instance_id = game_instance['game_instance_id']
            
            # Step 2: DM starts the game session
            session_start_response = await client.post(
                f"{DMLOG_GAMEDEV_URL}/api/sessions/start-unity",
                json={
                    'game_instance_id': game_instance_id,
                    'session_data': game_session_data,
                    'unity_config': unity_game_config
                },
                headers=dm_session['headers']
            )
            assert session_start_response.status_code == 201
            session_id = session_start_response.json()['session_id']
            
            # Step 3: Test WebSocket connection for real-time updates
            websocket_url = f"{WEBSOCKET_GAME_URL}/game/{game_instance_id}"
            
            # Simulate DM connecting
            async with websockets.connect(f"{websocket_url}?token={dm_session['token']}") as dm_ws:
                # Send DM authentication
                auth_message = {
                    'type': 'authenticate',
                    'role': 'dm',
                    'session_id': session_id
                }
                await dm_ws.send(json.dumps(auth_message))
                
                auth_response = await dm_ws.recv()
                auth_data = json.loads(auth_response)
                assert auth_data['status'] == 'authenticated'
                
                # Simulate player connections
                player_websockets = []
                for i, player_session in enumerate(player_sessions):
                    player_ws = await websockets.connect(f"{websocket_url}?token={player_session['token']}")
                    
                    player_auth = {
                        'type': 'authenticate',
                        'role': 'player',
                        'player_id': game_session_data['players'][i]['player_id']
                    }
                    await player_ws.send(json.dumps(player_auth))
                    
                    player_auth_response = await player_ws.recv()
                    assert json.loads(player_auth_response)['status'] == 'authenticated'
                    player_websockets.append(player_ws)
                
                # Step 4: Test real-time dice rolling
                dice_roll = {
                    'type': 'dice_roll',
                    'player_id': game_session_data['players'][0]['player_id'],
                    'dice': '1d20+5',
                    'reason': 'attack_roll',
                    'target': 'goblin_1'
                }
                await dm_ws.send(json.dumps(dice_roll))
                
                # Verify all clients receive dice roll result
                dice_result = await dm_ws.recv()
                dice_data = json.loads(dice_result)
                assert dice_data['type'] == 'dice_result'
                assert 'result' in dice_data
                assert dice_data['total'] >= 6 and dice_data['total'] <= 25
                
                # Step 5: Test character movement
                move_command = {
                    'type': 'character_move',
                    'player_id': game_session_data['players'][0]['player_id'],
                    'from': {'x': 10, 'y': 15},
                    'to': {'x': 12, 'y': 17},
                    'movement_type': 'walk'
                }
                await player_websockets[0].send(json.dumps(move_command))
                
                # DM should receive movement update
                movement_update = await dm_ws.recv()
                movement_data = json.loads(movement_update)
                assert movement_data['type'] == 'character_moved'
                assert movement_data['new_position'] == {'x': 12, 'y': 17}
                
                # Clean up WebSocket connections
                for player_ws in player_websockets:
                    await player_ws.close()

    @pytest.mark.asyncio
    async def test_educational_game_adaptive_learning(self, educational_game_config, authenticated_game_sessions):
        """Test adaptive learning system in educational games"""
        
        async with httpx.AsyncClient() as client:
            student_session = authenticated_game_sessions['players'][0]
            
            # Step 1: Initialize educational game
            game_response = await client.post(
                f"{STUDYLOG_GAMES_URL}/api/games/initialize",
                json=educational_game_config,
                headers=student_session['headers']
            )
            assert game_response.status_code == 201
            game_id = game_response.json()['game_id']
            
            # Step 2: Start learning session
            learning_session = {
                'student_id': student_session['user_id'],
                'subject': 'mathematics',
                'target_skills': ['linear_equations', 'coordinate_geometry'],
                'session_duration': 45,  # minutes
                'adaptive_settings': {
                    'difficulty_adjustment': True,
                    'learning_style_adaptation': True,
                    'pace_adjustment': True
                }
            }
            
            session_response = await client.post(
                f"{STUDYLOG_GAMES_URL}/api/games/{game_id}/start-session",
                json=learning_session,
                headers=student_session['headers']
            )
            assert session_response.status_code == 201
            session_id = session_response.json()['session_id']
            
            # Step 3: Simulate adaptive learning progression
            learning_interactions = [
                {
                    'interaction_type': 'problem_solving',
                    'problem_id': 'linear_eq_001',
                    'student_answer': 'x = 7',
                    'correct_answer': 'x = 7',
                    'time_taken': 45,  # seconds
                    'attempts': 1
                },
                {
                    'interaction_type': 'problem_solving',
                    'problem_id': 'linear_eq_002',
                    'student_answer': 'x = 3',
                    'correct_answer': 'x = 5',
                    'time_taken': 120,
                    'attempts': 2
                },
                {
                    'interaction_type': 'problem_solving',
                    'problem_id': 'coord_geo_001',
                    'student_answer': '(2, 4)',
                    'correct_answer': '(2, 4)',
                    'time_taken': 30,
                    'attempts': 1
                }
            ]
            
            adaptation_data = []
            for interaction in learning_interactions:
                interaction_response = await client.post(
                    f"{STUDYLOG_GAMES_URL}/api/sessions/{session_id}/interaction",
                    json=interaction,
                    headers=student_session['headers']
                )
                assert interaction_response.status_code == 200
                
                adaptation_info = interaction_response.json()
                adaptation_data.append(adaptation_info['adaptation'])
                
                # Verify adaptive adjustments
                if interaction['student_answer'] != interaction['correct_answer']:
                    assert adaptation_info['adaptation']['difficulty_adjusted'] == True
                    assert adaptation_info['adaptation']['new_difficulty'] < adaptation_info['adaptation']['previous_difficulty']
            
            # Step 4: Verify learning analytics
            analytics_response = await client.get(
                f"{STUDYLOG_GAMES_URL}/api/sessions/{session_id}/analytics",
                headers=student_session['headers']
            )
            analytics_data = analytics_response.json()
            
            assert 'skill_progression' in analytics_data
            assert 'difficulty_curve' in analytics_data
            assert 'engagement_metrics' in analytics_data
            
            # Linear equations should show mixed performance
            linear_eq_progress = analytics_data['skill_progression']['linear_equations']
            assert linear_eq_progress['accuracy'] == 0.5  # 1 correct out of 2
            
            # Coordinate geometry should show good performance
            coord_geo_progress = analytics_data['skill_progression']['coordinate_geometry']
            assert coord_geo_progress['accuracy'] == 1.0

    @pytest.mark.asyncio
    async def test_cross_platform_game_sync(self, unity_game_config, authenticated_game_sessions):
        """Test game state synchronization across multiple platforms"""
        
        async with httpx.AsyncClient() as client:
            dm_session = authenticated_game_sessions['dm']
            
            # Step 1: Create campaign in DMLog
            campaign_data = {
                'name': 'Cross-Platform Adventure',
                'system': 'D&D 5e',
                'cross_platform_enabled': True,
                'supported_platforms': ['unity_webgl', 'mobile_app', 'web_interface']
            }
            
            campaign_response = await client.post(
                f"{DMLOG_GAMEDEV_URL}/api/campaigns/create",
                json=campaign_data,
                headers=dm_session['headers']
            )
            campaign_id = campaign_response.json()['campaign_id']
            
            # Step 2: Initialize Unity instance
            unity_instance = await client.post(
                f"{UNITY_INTEGRATION_URL}/api/campaigns/{campaign_id}/initialize",
                json=unity_game_config,
                headers=dm_session['headers']
            )
            unity_instance_id = unity_instance.json()['instance_id']
            
            # Step 3: Make changes in DMLog and verify sync to Unity
            character_update = {
                'character_id': str(uuid.uuid4()),
                'name': 'Sync Test Character',
                'position': {'x': 15, 'y': 10, 'z': 0},
                'hp_current': 45,
                'hp_max': 50,
                'status_effects': ['blessed', 'inspired']
            }
            
            dmlog_update_response = await client.put(
                f"{DMLOG_GAMEDEV_URL}/api/campaigns/{campaign_id}/characters",
                json=character_update,
                headers=dm_session['headers']
            )
            assert dmlog_update_response.status_code == 200
            
            # Wait for synchronization
            await asyncio.sleep(2)
            
            # Verify Unity received the update
            unity_state_response = await client.get(
                f"{UNITY_INTEGRATION_URL}/api/instances/{unity_instance_id}/state",
                headers=dm_session['headers']
            )
            unity_state = unity_state_response.json()
            
            synced_character = next(
                (c for c in unity_state['characters'] if c['name'] == 'Sync Test Character'),
                None
            )
            assert synced_character is not None
            assert synced_character['position'] == character_update['position']
            assert synced_character['hp_current'] == 45
            
            # Step 4: Make changes in Unity and verify sync to DMLog
            unity_character_move = {
                'character_id': character_update['character_id'],
                'new_position': {'x': 20, 'y': 12, 'z': 0},
                'movement_type': 'teleport',
                'timestamp': datetime.utcnow().isoformat()
            }
            
            unity_move_response = await client.post(
                f"{UNITY_INTEGRATION_URL}/api/instances/{unity_instance_id}/character-move",
                json=unity_character_move,
                headers=dm_session['headers']
            )
            assert unity_move_response.status_code == 200
            
            await asyncio.sleep(2)
            
            # Verify DMLog received the update
            dmlog_character_response = await client.get(
                f"{DMLOG_GAMEDEV_URL}/api/campaigns/{campaign_id}/characters/{character_update['character_id']}",
                headers=dm_session['headers']
            )
            dmlog_character = dmlog_character_response.json()
            
            assert dmlog_character['position'] == {'x': 20, 'y': 12, 'z': 0}

    @pytest.mark.asyncio
    async def test_game_engine_physics_integration(self, unity_game_config, authenticated_game_sessions):
        """Test physics engine integration for realistic dice rolling and object interactions"""
        
        async with httpx.AsyncClient() as client:
            dm_session = authenticated_game_sessions['dm']
            
            # Step 1: Initialize physics-enabled game
            physics_config = unity_game_config.copy()
            physics_config['physics'] = {
                'engine': 'Unity Physics',
                'gravity': -9.81,
                'dice_physics': {
                    'material': 'plastic',
                    'bounce': 0.3,
                    'friction': 0.6,
                    'mass': 0.015  # kg
                },
                'collision_detection': 'continuous'
            }
            
            physics_game_response = await client.post(
                f"{UNITY_INTEGRATION_URL}/api/games/initialize-physics",
                json=physics_config,
                headers=dm_session['headers']
            )
            assert physics_game_response.status_code == 201
            physics_instance_id = physics_game_response.json()['instance_id']
            
            # Step 2: Test realistic dice physics
            dice_roll_requests = []
            for i in range(10):
                dice_request = {
                    'dice_type': 'd20',
                    'throw_force': {'x': 2.5, 'y': 8.0, 'z': 1.2},
                    'throw_torque': {'x': 45, 'y': -30, 'z': 15},
                    'surface_material': 'felt',
                    'simulate_physics': True
                }
                
                roll_response = await client.post(
                    f"{UNITY_INTEGRATION_URL}/api/instances/{physics_instance_id}/dice-roll-physics",
                    json=dice_request,
                    headers=dm_session['headers']
                )
                assert roll_response.status_code == 202
                dice_roll_requests.append(roll_response.json()['roll_id'])
            
            # Wait for physics simulations to complete
            await asyncio.sleep(5)
            
            # Step 3: Verify physics simulation results
            physics_results = []
            for roll_id in dice_roll_requests:
                result_response = await client.get(
                    f"{UNITY_INTEGRATION_URL}/api/dice-rolls/{roll_id}/physics-result",
                    headers=dm_session['headers']
                )
                assert result_response.status_code == 200
                
                result_data = result_response.json()
                physics_results.append(result_data)
                
                # Verify realistic physics data
                assert 'final_value' in result_data
                assert 1 <= result_data['final_value'] <= 20
                assert 'simulation_time' in result_data
                assert 'bounce_count' in result_data
                assert 'final_rotation' in result_data
                assert 'trajectory_points' in result_data
            
            # Verify statistical distribution is reasonable
            values = [r['final_value'] for r in physics_results]
            unique_values = len(set(values))
            assert unique_values >= 5  # Should have reasonable variety
            
            # Step 4: Test object collision physics
            collision_test = {
                'object_1': {
                    'type': 'dice',
                    'position': {'x': 0, 'y': 5, 'z': 0},
                    'velocity': {'x': 2, 'y': 0, 'z': 0}
                },
                'object_2': {
                    'type': 'miniature',
                    'position': {'x': 3, 'y': 0, 'z': 0},
                    'mass': 0.05
                },
                'simulate_collision': True
            }
            
            collision_response = await client.post(
                f"{UNITY_INTEGRATION_URL}/api/instances/{physics_instance_id}/collision-test",
                json=collision_test,
                headers=dm_session['headers']
            )
            assert collision_response.status_code == 200
            
            collision_data = collision_response.json()
            assert collision_data['collision_occurred'] == True
            assert 'impact_force' in collision_data
            assert 'post_collision_velocities' in collision_data

    @pytest.mark.asyncio
    async def test_multiplayer_game_session_management(self, unity_game_config, authenticated_game_sessions):
        """Test multiplayer session management, player joining/leaving, and state consistency"""
        
        async with httpx.AsyncClient() as client:
            dm_session = authenticated_game_sessions['dm']
            player_sessions = authenticated_game_sessions['players']
            
            # Step 1: Create multiplayer session
            multiplayer_config = unity_game_config.copy()
            multiplayer_config['multiplayer'] = {
                'max_players': 8,
                'late_join_enabled': True,
                'spectator_mode': True,
                'reconnection_timeout': 300,  # seconds
                'state_synchronization': 'authoritative_server'
            }
            
            session_response = await client.post(
                f"{GAMING_PLATFORM_URL}/api/multiplayer/create-session",
                json=multiplayer_config,
                headers=dm_session['headers']
            )
            assert session_response.status_code == 201
            
            session_data = session_response.json()
            session_id = session_data['session_id']
            join_code = session_data['join_code']
            
            # Step 2: Players join session
            joined_players = []
            for i, player_session in enumerate(player_sessions):
                join_response = await client.post(
                    f"{GAMING_PLATFORM_URL}/api/multiplayer/join-session",
                    json={
                        'join_code': join_code,
                        'player_name': f'Player {i+1}',
                        'character_data': {
                            'name': f'Character {i+1}',
                            'class': 'Fighter' if i == 0 else 'Wizard'
                        }
                    },
                    headers=player_session['headers']
                )
                assert join_response.status_code == 200
                joined_players.append(join_response.json()['player_id'])
            
            # Step 3: Verify session state
            session_state_response = await client.get(
                f"{GAMING_PLATFORM_URL}/api/multiplayer/sessions/{session_id}/state",
                headers=dm_session['headers']
            )
            session_state = session_state_response.json()
            
            assert len(session_state['players']) == 2
            assert session_state['session_status'] == 'active'
            
            # Step 4: Test late joining
            late_joiner = {
                'user_id': str(uuid.uuid4()),
                'token': 'late_joiner.token',
                'headers': {'Authorization': 'Bearer late_joiner.token'}
            }
            
            late_join_response = await client.post(
                f"{GAMING_PLATFORM_URL}/api/multiplayer/join-session",
                json={
                    'join_code': join_code,
                    'player_name': 'Late Joiner',
                    'late_join': True
                },
                headers=late_joiner['headers']
            )
            assert late_join_response.status_code == 200
            
            # Verify late joiner receives current game state
            late_join_data = late_join_response.json()
            assert 'current_game_state' in late_join_data
            assert len(late_join_data['current_game_state']['players']) == 3
            
            # Step 5: Test player disconnection and reconnection
            disconnect_response = await client.post(
                f"{GAMING_PLATFORM_URL}/api/multiplayer/sessions/{session_id}/disconnect",
                json={'player_id': joined_players[0], 'reason': 'network_issue'},
                headers=player_sessions[0]['headers']
            )
            assert disconnect_response.status_code == 200
            
            # Wait briefly, then reconnect
            await asyncio.sleep(2)
            
            reconnect_response = await client.post(
                f"{GAMING_PLATFORM_URL}/api/multiplayer/sessions/{session_id}/reconnect",
                json={'player_id': joined_players[0]},
                headers=player_sessions[0]['headers']
            )
            assert reconnect_response.status_code == 200
            
            # Verify player receives state synchronization
            reconnect_data = reconnect_response.json()
            assert 'state_sync' in reconnect_data
            assert reconnect_data['reconnection_successful'] == True

    @pytest.mark.asyncio
    async def test_game_mod_and_asset_integration(self, unity_game_config, authenticated_game_sessions):
        """Test integration of custom mods, assets, and user-generated content"""
        
        async with httpx.AsyncClient() as client:
            dm_session = authenticated_game_sessions['dm']
            
            # Step 1: Upload custom assets
            custom_assets = {
                'asset_pack_name': 'Pirate Campaign Assets',
                'assets': [
                    {
                        'type': 'character_model',
                        'name': 'Pirate Captain',
                        'file_format': 'fbx',
                        'size_mb': 15.2,
                        'animations': ['idle', 'walk', 'attack', 'death'],
                        'textures': ['diffuse', 'normal', 'specular']
                    },
                    {
                        'type': 'battle_map',
                        'name': 'Pirate Ship Deck',
                        'file_format': 'unity_scene',
                        'size_mb': 42.8,
                        'lighting': 'baked',
                        'collision_meshes': True
                    },
                    {
                        'type': 'audio',
                        'name': 'Sea Shanty Ambient',
                        'file_format': 'ogg',
                        'size_mb': 8.1,
                        'loop': True,
                        'spatial_audio': True
                    }
                ]
            }
            
            asset_upload_response = await client.post(
                f"{UNITY_INTEGRATION_URL}/api/assets/upload",
                json=custom_assets,
                headers=dm_session['headers']
            )
            assert asset_upload_response.status_code == 202
            
            upload_job_id = asset_upload_response.json()['upload_job_id']
            
            # Wait for asset processing
            asset_processed = False
            for _ in range(30):
                processing_status = await client.get(
                    f"{UNITY_INTEGRATION_URL}/api/assets/jobs/{upload_job_id}/status",
                    headers=dm_session['headers']
                )
                status_data = processing_status.json()
                
                if status_data['status'] == 'completed':
                    asset_processed = True
                    break
                elif status_data['status'] == 'failed':
                    pytest.fail(f"Asset processing failed: {status_data.get('error')}")
                
                await asyncio.sleep(2)
            
            assert asset_processed, "Asset processing did not complete in time"
            
            # Step 2: Install mod using custom assets
            mod_config = {
                'mod_name': 'Pirate Adventures Mod',
                'mod_version': '1.0.0',
                'description': 'Adds pirate-themed content to D&D campaigns',
                'asset_pack_id': processing_status.json()['asset_pack_id'],
                'game_rules': {
                    'new_classes': ['Pirate', 'Sea Witch'],
                    'new_spells': ['Control Weather', 'Water Walk'],
                    'new_equipment': ['Cutlass', 'Tricorn Hat', 'Spyglass']
                },
                'compatibility': {
                    'game_version': '1.0+',
                    'required_mods': [],
                    'conflicts_with': []
                }
            }
            
            mod_install_response = await client.post(
                f"{UNITY_INTEGRATION_URL}/api/mods/install",
                json=mod_config,
                headers=dm_session['headers']
            )
            assert mod_install_response.status_code == 201
            
            mod_id = mod_install_response.json()['mod_id']
            
            # Step 3: Test mod functionality in game
            game_with_mod = unity_game_config.copy()
            game_with_mod['enabled_mods'] = [mod_id]
            
            modded_game_response = await client.post(
                f"{UNITY_INTEGRATION_URL}/api/games/initialize",
                json=game_with_mod,
                headers=dm_session['headers']
            )
            assert modded_game_response.status_code == 201
            
            modded_instance_id = modded_game_response.json()['instance_id']
            
            # Verify mod content is available
            available_content_response = await client.get(
                f"{UNITY_INTEGRATION_URL}/api/instances/{modded_instance_id}/available-content",
                headers=dm_session['headers']
            )
            content_data = available_content_response.json()
            
            assert 'Pirate' in content_data['available_classes']
            assert 'Control Weather' in content_data['available_spells']
            assert 'Pirate Ship Deck' in content_data['available_maps']

    @pytest.mark.load
    async def test_game_engine_performance_under_load(self, unity_game_config, authenticated_game_sessions):
        """Test game engine performance under high concurrent load"""
        
        async def create_game_instance(instance_id: int):
            async with httpx.AsyncClient() as client:
                config = unity_game_config.copy()
                config['instance_name'] = f'Load Test Instance {instance_id}'
                
                return await client.post(
                    f"{UNITY_INTEGRATION_URL}/api/games/initialize",
                    json=config,
                    headers=authenticated_game_sessions['dm']['headers']
                )
        
        # Create 20 concurrent game instances
        tasks = [create_game_instance(i) for i in range(20)]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify most instances were created successfully
        successful_instances = [
            r for r in responses 
            if not isinstance(r, Exception) and r.status_code == 201
        ]
        assert len(successful_instances) >= 18
        
        # Test system performance metrics
        performance_response = await httpx.AsyncClient().get(
            f"{UNITY_INTEGRATION_URL}/api/performance/metrics"
        )
        assert performance_response.status_code == 200
        
        performance_data = performance_response.json()
        assert performance_data['cpu_usage'] < 0.9  # Under 90%
        assert performance_data['memory_usage'] < 0.8  # Under 80%
        assert performance_data['active_instances'] >= 18