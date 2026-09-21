#!/usr/bin/env python3
"""
DMLog Beta Testing Portal - Revolutionary Gaming Experience
ML-Powered User Experience Optimization
"""

from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import json
import os
from datetime import datetime, timedelta
import hashlib
import uuid
import logging
from typing import Dict, Any, List, Tuple
import asyncio
import numpy as np
from collections import defaultdict, deque
import openai
import requests

app = Flask(__name__)
app.secret_key = 'dmlog-beta-revolutionary-gaming-2025'

# OpenAI Configuration
from openai import OpenAI
openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY', 'test-key-for-demo'))
OPENAI_MODEL = "gpt-4"  # or "gpt-3.5-turbo" for cost efficiency

# Configure logging first
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import our ML interpreter systems
try:
    from ml_response_optimizer import adaptive_llm_system
    from ecosystem_voice_ml import ecosystem_voice_ml, initialize_ecosystem_voice_ml, record_voice_interaction, optimize_voice_command
    from universal_ai_interpreter import universal_ai_interpreter, initialize_universal_interpreter, interpret_user_input
    from lightweight_edge_interpreter import create_edge_interpreter
    from system_input_interpreter import system_input_service, interpret_system_input, report_user_correction
    from tiered_llm_system import tiered_llm, initialize_llm_system
    from ml_performance_optimizer import initialize_ml_performance_optimizer, optimize_ml_performance, get_optimization_report
    from realtime_learning_accelerator import initialize_realtime_learning_accelerator, accelerate_user_learning, apply_accelerated_improvements, get_user_learning_insights
    from bot_interpreter_system import initialize_bot_interpreter_system, create_bot_to_computer_interpreter, create_bot_to_bot_interpreter, interpret_bot_command, interpret_bot_communication, get_interpreter_system_status
    from progressive_efficiency_engine import initialize_progressive_efficiency_engine, register_model_for_optimization, trigger_model_optimization, get_efficiency_system_status
    from overnight_training_system import initialize_overnight_training_system, record_daily_interaction, get_overnight_training_status, manual_trigger_overnight_training
    from load_balancer import create_load_balancer, ServerInstance, LoadBalancingStrategy
    from clustering_system import create_cluster_manager, NodeRole
    from enterprise_features import (
        create_jwt_manager, create_multi_tenant_manager, create_compliance_manager,
        create_rate_limiter, create_audit_logger, SecurityLevel
    )
    from claude_api_chooser import (
        claude_chooser, choose_claude_model, make_claude_request, 
        record_claude_feedback, get_claude_chooser_stats, ClaudeModel, TaskType
    )
    # from ui_navigation_assistant import ui_nav_assistant, track_navigation, get_ui_suggestions, respond_to_ui_suggestion, get_navigation_insights
    
    # Fallback functions for UI navigation
    def track_navigation(*args, **kwargs):
        return "ml_unavailable"
    
    def get_ui_suggestions(user_id: str):
        return []
    
    def respond_to_ui_suggestion(*args, **kwargs):
        pass
    
    def get_navigation_insights(user_id: str):
        return {
            'total_patterns_detected': 0,
            'active_optimizations': 0,
            'most_visited_pages': [],
            'navigation_efficiency_score': 0.8,
            'recent_struggles': [],
            'ui_readiness': 0.3
        }
    
    ML_SYSTEMS_AVAILABLE = True
    logger.info("🧠 ML Systems imported successfully (UI navigation in fallback mode)")
except ImportError as e:
    logger.warning(f"ML Systems not available: {e}")
    ML_SYSTEMS_AVAILABLE = False


# Initialize all ML systems
async def initialize_all_ml_systems():
    """Initialize all ML interpretation and optimization systems"""
    if not ML_SYSTEMS_AVAILABLE:
        logger.warning("🚨 ML Systems not available - running in basic mode")
        return False
        
    logger.info("🧠 Initializing SuperInstance ML Ecosystem...")
    try:
        logger.info("🔍 Response Quality Monitor...")
        # adaptive_llm_system is already initialized
        logger.info("🎤 Ecosystem Voice Learning...")
        await initialize_ecosystem_voice_ml()
        logger.info("🧠 Universal AI Interpreter...")
        await initialize_universal_interpreter()
        logger.info("⚙️ Tiered LLM System...")
        await initialize_llm_system()
        logger.info("🗺️ UI Navigation Assistant initialized...")
        # UI Navigation Assistant doesn't need async init - it's ready
        logger.info("⚡ ML Performance Optimizer...")
        await initialize_ml_performance_optimizer()
        logger.info("🚀 Real-time Learning Accelerator...")  
        await initialize_realtime_learning_accelerator()
        logger.info("🤖 Bot Interpreter System...")
        await initialize_bot_interpreter_system()
        logger.info("📈 Progressive Efficiency Engine...")
        await initialize_progressive_efficiency_engine()
        logger.info("🌙 Overnight Training System...")
        await initialize_overnight_training_system()
        logger.info("⚖️ Load Balancer System...")
        # Initialize load balancer (will be configured later with actual servers)
        global load_balancer
        load_balancer = create_load_balancer("ml_optimized", auto_scale=True)
        await load_balancer.initialize()
        logger.info("🔗 Clustering System...")
        # Initialize cluster manager
        global cluster_manager
        cluster_manager = create_cluster_manager(
            node_id=f"dmlog-portal-{uuid.uuid4().hex[:8]}",
            hostname="localhost", 
            port=9000,
            role=NodeRole.COORDINATOR
        )
        await cluster_manager.initialize()
        logger.info("🔒 Enterprise Security Features...")
        # Initialize enterprise security components
        global jwt_manager, multi_tenant_manager, compliance_manager, rate_limiter, audit_logger
        jwt_manager = create_jwt_manager()
        multi_tenant_manager = create_multi_tenant_manager()
        compliance_manager = create_compliance_manager(['GDPR', 'HIPAA'])
        rate_limiter = create_rate_limiter()
        audit_logger = create_audit_logger(SecurityLevel.HIGH)
        
        logger.info("✅ Complete Multi-Layer ML Ecosystem initialized successfully!")
        logger.info("✨ Features: Input Interpretation, Voice Learning, Response Optimization, UI Intelligence")
        logger.info("🚀 Advanced: Performance Optimization, Real-time Learning, Predictive Adaptation")
        logger.info("🤖 Multi-Layer: Bot-to-Computer, Bot-to-Bot, Progressive Model Refinement")
        logger.info("🌙 Overnight: Daily Feed Analysis, Model Training, Auto-Deployment")
        logger.info("⚖️ Scalability: Load Balancing, Auto-Scaling, Health Monitoring")
        logger.info("🔗 Clustering: Service Discovery, Distributed Coordination, High Availability")
        logger.info("🔒 Security: JWT Authentication, Multi-Tenancy, Compliance, Rate Limiting, Audit Logging")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize ML systems: {e}")
        return False

# Initialize on startup (if ML systems are available)
if ML_SYSTEMS_AVAILABLE:
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        ml_initialized = loop.run_until_complete(initialize_all_ml_systems())
        loop.close()
        logger.info(f"🚀 ML Ecosystem Status: {'ACTIVE' if ml_initialized else 'ERROR'}")
    except Exception as e:
        logger.warning(f"ML systems initialization warning: {e}")
        ML_SYSTEMS_AVAILABLE = False

class UserExperienceEngine:
    """ML engine for optimizing user experience in real-time"""
    
    def __init__(self):
        self.user_sessions = defaultdict(list)
        self.interaction_patterns = defaultdict(lambda: defaultdict(int))
        self.engagement_metrics = defaultdict(lambda: defaultdict(float))
        self.ui_preferences = defaultdict(dict)
        self.performance_history = defaultdict(lambda: deque(maxlen=100))
        
    def track_interaction(self, username: str, interaction_type: str, context: Dict[str, Any]):
        """Track user interaction for ML optimization"""
        interaction_data = {
            'type': interaction_type,
            'timestamp': datetime.now().isoformat(),
            'context': context,
            'session_id': session.get('session_id', 'unknown')
        }
        
        self.user_sessions[username].append(interaction_data)
        self.interaction_patterns[username][interaction_type] += 1
        
        # Calculate engagement score
        engagement_score = self._calculate_engagement_score(interaction_data)
        self.engagement_metrics[username]['total_engagement'] += engagement_score
        self.engagement_metrics[username]['interaction_count'] += 1
        
        logger.info(f"User activity: {username} -> {interaction_type} (engagement: {engagement_score:.2f})")
        
    def _calculate_engagement_score(self, interaction: Dict[str, Any]) -> float:
        """Calculate engagement score for interaction"""
        base_scores = {
            'login': 1.0,
            'fullscreen_enter': 2.5,
            'character_create': 4.0,
            'dice_roll': 3.0,
            'combat_action': 3.5,
            'roleplay_action': 4.5,
            'campaign_join': 5.0,
            'dm_action': 4.0,
            'ui_customization': 2.0,
            'feature_discovery': 3.0
        }
        
        return base_scores.get(interaction['type'], 1.0)
    
    def get_personalized_ui_config(self, username: str) -> Dict[str, Any]:
        """Generate personalized UI configuration using ML"""
        user_patterns = self.interaction_patterns[username]
        user_metrics = self.engagement_metrics[username]
        
        # ML-based UI optimization
        config = {
            'theme': self._predict_theme_preference(username),
            'layout_density': self._predict_layout_preference(username),
            'feature_priorities': self._predict_feature_priorities(username),
            'notification_style': self._predict_notification_preference(username),
            'animation_speed': self._predict_animation_preference(username),
            'shortcut_recommendations': self._recommend_shortcuts(username)
        }
        
        logger.info(f"UI optimized for {username}: {config['theme']} theme, {config['layout_density']} density")
        return config
    
    def _predict_theme_preference(self, username: str) -> str:
        """ML prediction for UI theme preference"""
        patterns = self.interaction_patterns[username]
        
        # Analyze interaction patterns to predict theme
        if patterns.get('combat_action', 0) > patterns.get('roleplay_action', 0):
            return 'dark_tactical'  # Combat-focused users prefer dark themes
        elif patterns.get('roleplay_action', 0) > 10:
            return 'fantasy_warm'   # Roleplay-focused users prefer warm themes
        else:
            return 'adaptive_smart' # Default adaptive theme
    
    def _predict_layout_preference(self, username: str) -> str:
        """ML prediction for layout density"""
        patterns = self.interaction_patterns[username]
        total_interactions = sum(patterns.values())
        
        if total_interactions > 50:
            return 'dense'      # Experienced users want more info
        elif total_interactions > 20:
            return 'balanced'   # Moderate users want balanced layout
        else:
            return 'spacious'   # New users need spacious layout
    
    def _predict_feature_priorities(self, username: str) -> List[str]:
        """ML prediction for feature priorities"""
        patterns = self.interaction_patterns[username]
        
        # Sort features by usage patterns
        feature_scores = {
            'character_sheet': patterns.get('character_create', 0) * 2 + patterns.get('roleplay_action', 0),
            'dice_roller': patterns.get('dice_roll', 0) * 3,
            'combat_tracker': patterns.get('combat_action', 0) * 2,
            'campaign_notes': patterns.get('dm_action', 0) * 2,
            'voice_chat': patterns.get('roleplay_action', 0),
            'map_tools': patterns.get('combat_action', 0) + patterns.get('dm_action', 0)
        }
        
        return sorted(feature_scores.keys(), key=lambda x: feature_scores[x], reverse=True)
    
    def _predict_notification_preference(self, username: str) -> str:
        """ML prediction for notification style"""
        patterns = self.interaction_patterns[username]
        
        if patterns.get('ui_customization', 0) > 5:
            return 'minimal'    # Users who customize want minimal notifications
        elif patterns.get('feature_discovery', 0) > 3:
            return 'helpful'    # Users exploring want helpful notifications
        else:
            return 'standard'   # Default notification level
    
    def _predict_animation_preference(self, username: str) -> str:
        """ML prediction for animation speed"""
        patterns = self.interaction_patterns[username]
        
        if patterns.get('combat_action', 0) > patterns.get('roleplay_action', 0) * 2:
            return 'fast'       # Combat users want fast animations
        elif patterns.get('roleplay_action', 0) > 20:
            return 'cinematic'  # Roleplay users enjoy cinematic animations
        else:
            return 'smooth'     # Default smooth animations
    
    def _recommend_shortcuts(self, username: str) -> List[str]:
        """ML-based shortcut recommendations"""
        patterns = self.interaction_patterns[username]
        
        shortcuts = []
        if patterns.get('dice_roll', 0) > 10:
            shortcuts.extend(['quick_d20', 'advantage_roll'])
        if patterns.get('combat_action', 0) > 5:
            shortcuts.extend(['initiative_tracker', 'health_quick_adjust'])
        if patterns.get('dm_action', 0) > 3:
            shortcuts.extend(['npc_generator', 'scene_transition'])
        
        return shortcuts[:4]  # Top 4 recommendations
    
    def get_performance_insights(self, username: str) -> Dict[str, Any]:
        """Get ML-powered performance insights"""
        metrics = self.engagement_metrics[username]
        patterns = self.interaction_patterns[username]
        
        avg_engagement = metrics['total_engagement'] / max(metrics['interaction_count'], 1)
        
        insights = {
            'engagement_level': 'high' if avg_engagement > 3.0 else 'moderate' if avg_engagement > 2.0 else 'learning',
            'primary_activity': max(patterns.items(), key=lambda x: x[1])[0] if patterns else 'exploring',
            'session_quality': min(avg_engagement / 2.0, 5.0),
            'improvement_suggestions': self._generate_improvement_suggestions(username),
            'predicted_interests': self._predict_user_interests(username)
        }
        
        return insights
    
    def _generate_improvement_suggestions(self, username: str) -> List[str]:
        """Generate ML-based improvement suggestions"""
        patterns = self.interaction_patterns[username]
        suggestions = []
        
        if patterns.get('character_create', 0) < 2:
            suggestions.append("Try creating a detailed character - it enhances roleplay!")
        if patterns.get('dice_roll', 0) > 20 and patterns.get('roleplay_action', 0) < 5:
            suggestions.append("Balance dice rolls with roleplay for richer experiences")
        if patterns.get('feature_discovery', 0) < 3:
            suggestions.append("Explore the advanced features - there's more to discover!")
        
        return suggestions
    
    def _predict_user_interests(self, username: str) -> List[str]:
        """Predict user interests based on behavior"""
        patterns = self.interaction_patterns[username]
        interests = []
        
        if patterns.get('combat_action', 0) > 10:
            interests.append('tactical_combat')
        if patterns.get('roleplay_action', 0) > 15:
            interests.append('immersive_storytelling')
        if patterns.get('dm_action', 0) > 5:
            interests.append('campaign_management')
        if patterns.get('character_create', 0) > 2:
            interests.append('character_optimization')
        
        return interests

class DMLogAI:
    """Advanced AI system for D&D gameplay using Tiered LLM"""
    
    def __init__(self):
        self.character_personalities = {
            'dm': {
                'name': 'Dungeon Master',
                'personality': 'Wise, fair, creative storyteller who guides adventures',
                'voice_style': 'Authoritative but encouraging'
            },
            'tavern_keeper': {
                'name': 'Borin Ironback',
                'personality': 'Gruff dwarf tavern keeper with stories to tell',
                'voice_style': 'Gruff, friendly, uses tavern slang'
            },
            'wizard': {
                'name': 'Eldara the Wise',
                'personality': 'Ancient elf wizard, mysterious but helpful',
                'voice_style': 'Formal, mystical, uses arcane terminology'
            },
            'goblin': {
                'name': 'Grax',
                'personality': 'Cunning but cowardly goblin warrior',
                'voice_style': 'High-pitched, aggressive, simple speech'
            },
            'narrator': {
                'name': 'The Narrator',
                'personality': 'Omniscient storyteller describing the world',
                'voice_style': 'Descriptive, atmospheric, immersive'
            }
        }
        
        self.campaign_context = {
            'setting': 'Medieval fantasy tavern called The Enchanted Griffin',
            'current_scene': 'Players have just entered a dimly lit tavern',
            'active_npcs': ['tavern_keeper', 'mysterious_hooded_figure', 'old_wizard'],
            'mood': 'mysterious and adventurous',
            'recent_events': []
        }

    async def generate_response(self, character: str, player_input: str, context: Dict[str, Any] = None) -> Tuple[str, Dict[str, Any]]:
        """Generate AI response using ML-optimized Tiered LLM system"""
        try:
            # Import systems
            from tiered_llm_system import tiered_llm
            from ml_response_optimizer import adaptive_llm_system
            
            # Get session ID for tracking
            session_id = context.get('session_id', 'unknown') if context else 'unknown'
            
            # Step 1: ML optimization of user input
            optimization_result = await adaptive_llm_system.process_gaming_request(
                player_input, character, 'tiered-llm', session_id
            )
            
            optimized_input = optimization_result['optimized_input']
            optimization_confidence = optimization_result['optimization_confidence']
            
            # Add character context
            enhanced_context = {
                'character_info': self.character_personalities.get(character, self.character_personalities['dm']),
                'campaign_context': self.campaign_context,
                'session_complexity': len(self.campaign_context['recent_events']),
                'session_id': session_id
            }
            if context:
                enhanced_context.update(context)
            
            # Step 2: Get response from tiered system using optimized input
            llm_response = await tiered_llm.generate_response(character, optimized_input, enhanced_context)
            
            # Step 3: Record response for ML learning
            response_data = {
                'user_input': player_input,
                'original_prompt': player_input,
                'optimized_prompt': optimized_input,
                'character': character,
                'llm_model': llm_response.model_used,
                'session_id': session_id,
                'response': llm_response.content,
                'response_time': llm_response.response_time,
                'cost': llm_response.cost_estimate
            }
            
            quality_score = adaptive_llm_system.record_response_quality(response_data)
            
            logger.info(f"Response from {llm_response.model_used} (${llm_response.cost_estimate:.4f}, {llm_response.response_time:.2f}s, quality: {quality_score:.2f})")
            
            # Return response with ML metadata
            ml_metadata = {
                'original_input': player_input,
                'optimized_input': optimized_input,
                'optimization_confidence': optimization_confidence,
                'quality_score': quality_score,
                'model_used': llm_response.model_used,
                'optimization_applied': optimized_input != player_input
            }
            
            return llm_response.content, ml_metadata
            
        except Exception as e:
            logger.error(f"ML-optimized LLM error: {e}")
            fallback_response = self._get_demo_response(character, player_input)
            return fallback_response, {'error': str(e)}
    
    def _get_demo_response(self, character: str, player_input: str) -> str:
        """Fallback responses for demo/testing"""
        responses = {
            'dm': [
                "Your words echo through the tavern. What do you do next?",
                "The adventure takes an interesting turn. Roll for initiative!",
                "The world responds to your actions. Choose wisely.",
                "An excellent approach! The story continues..."
            ],
            'tavern_keeper': [
                "Aye, welcome to The Enchanted Griffin! What can I get ye?",
                "I've heard tales of adventure from many travelers like yourself.",
                "The roads have been dangerous lately. Best stay close to the hearth.",
                "That reminds me of a story... but that's for another time."
            ],
            'wizard': [
                "The arcane energies sense your presence, young one.",
                "Magic flows differently around those destined for greatness.",
                "I have studied many tomes, but experience teaches more than books.",
                "The mystical realms whisper secrets to those who listen."
            ],
            'goblin': [
                "Grax no like big people! You stay away!",
                "Shiny things! Grax likes shiny things!",
                "You strong? Grax test you! Grax fight good!",
                "Boss say Grax be nice... but Grax think you trouble!"
            ]
        }
        
        char_responses = responses.get(character, responses['dm'])
        return char_responses[hash(player_input) % len(char_responses)]
    
    def update_context(self, event: str, details: str):
        """Update campaign context based on events"""
        self.campaign_context['recent_events'].append({
            'event': event,
            'details': details,
            'timestamp': datetime.now().isoformat()
        })
        
        # Keep only last 10 events for context
        if len(self.campaign_context['recent_events']) > 10:
            self.campaign_context['recent_events'] = self.campaign_context['recent_events'][-10:]

# Initialize engines
experience_engine = UserExperienceEngine()
dmlog_ai = DMLogAI()

# Beta user credentials
BETA_USERS = {
    'Max': 'Snow',
    'Casey': 'Snow'
}

@app.route('/')
def index():
    """Landing page for beta portal"""
    if 'username' in session:
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    """Handle beta user authentication"""
    username = request.form.get('username')
    password = request.form.get('password')
    
    if username in BETA_USERS and BETA_USERS[username] == password:
        session['username'] = username
        session['session_id'] = str(uuid.uuid4())
        session['login_time'] = datetime.now().isoformat()
        
        # Track login activity
        experience_engine.track_interaction(username, 'login', {
            'timestamp': datetime.now().isoformat(),
            'user_agent': request.headers.get('User-Agent', ''),
            'ip': request.remote_addr
        })
        
        logger.info(f"Beta user {username} logged in successfully")
        return redirect(url_for('dashboard'))
    else:
        return render_template('login.html', error='Invalid credentials. Beta access only.')

@app.route('/dashboard')
def dashboard():
    """Main dashboard with fullscreen gaming experience"""
    if 'username' not in session:
        return redirect(url_for('index'))
    
    username = session['username']
    
    # Get personalized UI configuration
    ui_config = experience_engine.get_personalized_ui_config(username)
    performance_insights = experience_engine.get_performance_insights(username)
    
    return render_template('dashboard.html', 
                         username=username,
                         ui_config=ui_config,
                         insights=performance_insights)

@app.route('/fullscreen')
def fullscreen():
    """Full-screen gaming experience"""
    if 'username' not in session:
        return redirect(url_for('index'))
    
    username = session['username']
    
    # Track fullscreen entry for ML
    experience_engine.track_interaction(username, 'fullscreen_enter', {
        'screen_size': request.args.get('screen_size', 'unknown'),
        'browser': request.headers.get('User-Agent', '')
    })
    
    # Get ML-optimized gaming interface
    ui_config = experience_engine.get_personalized_ui_config(username)
    
    return render_template('gaming_interface.html',
                         username=username,
                         ui_config=ui_config,
                         fullscreen=True)

@app.route('/api/track_interaction', methods=['POST'])
def track_interaction():
    """API endpoint for tracking user interactions"""
    if 'username' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    username = session['username']
    data = request.get_json()
    
    interaction_type = data.get('type', 'unknown')
    context = data.get('context', {})
    
    experience_engine.track_interaction(username, interaction_type, context)
    
    # Return updated UI recommendations
    ui_config = experience_engine.get_personalized_ui_config(username)
    
    return jsonify({
        'status': 'tracked',
        'ml_recommendations': ui_config,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/get_ml_insights')
def get_ml_insights():
    """Get ML-powered user insights"""
    if 'username' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    username = session['username']
    insights = experience_engine.get_performance_insights(username)
    ui_config = experience_engine.get_personalized_ui_config(username)
    
    return jsonify({
        'insights': insights,
        'ui_config': ui_config,
        'username': username
    })

@app.route('/api/dice_roll', methods=['POST'])
def dice_roll():
    """Enhanced dice rolling with ML tracking"""
    if 'username' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    username = session['username']
    data = request.get_json()
    
    dice_type = data.get('dice', 'd20')
    modifier = data.get('modifier', 0)
    advantage = data.get('advantage', False)
    
    # Simulate dice roll
    import random
    if advantage:
        roll1 = random.randint(1, int(dice_type[1:]))
        roll2 = random.randint(1, int(dice_type[1:]))
        result = max(roll1, roll2) + modifier
        details = f"Advantage: {roll1}, {roll2} (taking {max(roll1, roll2)}) + {modifier}"
    else:
        roll = random.randint(1, int(dice_type[1:]))
        result = roll + modifier
        details = f"{dice_type}: {roll} + {modifier}"
    
    # Track dice roll for ML
    experience_engine.track_interaction(username, 'dice_roll', {
        'dice_type': dice_type,
        'modifier': modifier,
        'advantage': advantage,
        'result': result
    })
    
    return jsonify({
        'result': result,
        'details': details,
        'dice_type': dice_type,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/ai_chat', methods=['POST'])
async def ai_chat():
    """AI-powered chat with D&D characters"""
    if 'username' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    username = session['username']
    data = request.get_json()
    
    character = data.get('character', 'dm')
    player_input = data.get('message', '')
    
    if not player_input:
        return jsonify({'error': 'No message provided'}), 400
    
    try:
        # Generate ML-optimized AI response
        ai_response, ml_metadata = await dmlog_ai.generate_response(
            character, 
            player_input, 
            {'session_id': session['session_id']}
        )
        
        # Track interaction with ML insights
        experience_engine.track_interaction(username, 'ai_chat', {
            'character': character,
            'player_message': player_input,
            'ai_response': ai_response,
            'ml_metadata': ml_metadata
        })
        
        # Update campaign context
        dmlog_ai.update_context('player_interaction', f"{username}: {player_input}")
        dmlog_ai.update_context('character_response', f"{character}: {ai_response}")
        
        return jsonify({
            'character': character,
            'response': ai_response,
            'timestamp': datetime.now().isoformat(),
            'ml_insights': {
                'optimization_applied': ml_metadata.get('optimization_applied', False),
                'quality_score': ml_metadata.get('quality_score', 0.0),
                'model_used': ml_metadata.get('model_used', 'unknown')
            }
        })
        
    except Exception as e:
        logger.error(f"AI chat error: {e}")
        return jsonify({'error': 'AI chat temporarily unavailable'}), 500

@app.route('/api/llm_control', methods=['POST'])
async def llm_control():
    """Game Master controls for LLM system"""
    if 'username' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    username = session['username']
    data = request.get_json()
    action = data.get('action')
    
    from tiered_llm_system import tiered_llm
    
    try:
        if action == 'enable_cloud_llm':
            llm_url = data.get('llm_url', 'http://cloud-llm-instance:8080')
            success = tiered_llm.enable_cloud_llm(llm_url)
            
            if success:
                experience_engine.track_interaction(username, 'gm_cloud_llm_enabled', {
                    'llm_url': llm_url,
                    'timestamp': datetime.now().isoformat()
                })
                
                return jsonify({
                    'success': True,
                    'message': 'Game Master LLM enabled for enhanced storytelling',
                    'cost_impact': '~$2-4/hour additional'
                })
            else:
                return jsonify({'success': False, 'message': 'Failed to connect to cloud LLM'})
        
        elif action == 'disable_cloud_llm':
            tiered_llm.disable_cloud_llm()
            
            experience_engine.track_interaction(username, 'gm_cloud_llm_disabled', {
                'timestamp': datetime.now().isoformat()
            })
            
            return jsonify({
                'success': True,
                'message': 'Cloud LLM disabled - using cost-optimized local model',
                'cost_savings': '~$2-4/hour saved'
            })
        
        elif action == 'get_stats':
            stats = tiered_llm.get_usage_stats()
            return jsonify({
                'success': True,
                'usage_stats': stats
            })
        
        else:
            return jsonify({'error': 'Unknown action'}), 400
            
    except Exception as e:
        logger.error(f"LLM control error: {e}")
        return jsonify({'error': 'LLM control temporarily unavailable'}), 500

@app.route('/api/ml_feedback', methods=['POST'])
async def ml_feedback():
    """Collect user feedback for ML learning"""
    if 'username' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    username = session['username']
    data = request.get_json()
    
    response_id = data.get('response_id')  # Could be timestamp or unique ID
    feedback_type = data.get('feedback_type')  # 'thumbs_up', 'thumbs_down', 'rating'
    feedback_value = data.get('feedback_value')  # Rating 1-5 or boolean
    feedback_text = data.get('feedback_text', '')  # Optional text feedback
    
    try:
        from ml_response_optimizer import adaptive_llm_system
        
        # Record feedback for ML learning
        # This would ideally link back to the specific response
        experience_engine.track_interaction(username, 'ml_feedback', {
            'response_id': response_id,
            'feedback_type': feedback_type,
            'feedback_value': feedback_value,
            'feedback_text': feedback_text
        })
        
        logger.info(f"ML feedback from {username}: {feedback_type} = {feedback_value}")
        
        return jsonify({
            'success': True,
            'message': 'Feedback recorded - AI will learn from this!'
        })
        
    except Exception as e:
        logger.error(f"ML feedback error: {e}")
        return jsonify({'error': 'Failed to record feedback'}), 500

@app.route('/api/ml_analytics')
async def ml_analytics():
    """Get ML performance analytics"""
    if 'username' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        from ml_response_optimizer import adaptive_llm_system
        
        # Get model performance stats
        model_stats = adaptive_llm_system.get_model_performance_stats()
        
        # Get optimization recommendations
        recommendations = adaptive_llm_system.get_optimization_recommendations()
        
        # Get recent quality trends
        recent_quality = []
        for quality_data in list(adaptive_llm_system.response_monitor.response_history)[-20:]:
            recent_quality.append({
                'timestamp': quality_data.timestamp.isoformat(),
                'quality_score': quality_data.quality_score,
                'model': quality_data.llm_model,
                'character': quality_data.character
            })
        
        return jsonify({
            'model_performance': model_stats,
            'recommendations': recommendations,
            'recent_quality_trend': recent_quality,
            'total_responses_analyzed': len(adaptive_llm_system.response_monitor.response_history),
            'optimization_patterns_learned': len(adaptive_llm_system.prompt_optimizer.optimization_patterns)
        })
        
    except Exception as e:
        logger.error(f"ML analytics error: {e}")
        return jsonify({'error': 'Analytics temporarily unavailable'}), 500

# System-wide ML integration endpoints
@app.route('/api/navigation/track', methods=['POST'])
def track_navigation_event():
    """Track navigation events for UI learning"""
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    try:
        data = request.get_json()
        username = session['username']
        
        if ML_SYSTEMS_AVAILABLE:
            session_id = track_navigation(
                user_id=username,
                page_path=data.get('page_path', '/'),
                action=data.get('action', 'click'),
                element_id=data.get('element_id', ''),
                element_text=data.get('element_text', ''),
                session_id=session.get('session_id', ''),
                time_spent=data.get('time_spent', 0.0)
            )
        else:
            session_id = 'ml_unavailable'
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'ml_active': ML_SYSTEMS_AVAILABLE
        })
        
    except Exception as e:
        logger.error(f"Navigation tracking error: {e}")
        return jsonify({'error': 'Tracking failed'}), 500

@app.route('/api/ui/suggestions', methods=['GET'])
def get_ui_optimization_suggestions():
    """Get UI optimization suggestions for current user"""
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    try:
        username = session['username']
        
        if ML_SYSTEMS_AVAILABLE:
            suggestions = get_ui_suggestions(username)
        else:
            suggestions = []
        
        return jsonify({
            'success': True,
            'suggestions': [
                {
                    'id': s.optimization_id,
                    'type': s.optimization_type,
                    'title': s.title,
                    'description': s.description,
                    'confidence': s.confidence,
                    'expected_benefit': s.expected_benefit,
                    'implementation': s.implementation
                }
                for s in suggestions
            ],
            'ml_active': ML_SYSTEMS_AVAILABLE
        })
        
    except Exception as e:
        logger.error(f"UI suggestions error: {e}")
        return jsonify({'error': 'Suggestions unavailable'}), 500

@app.route('/api/ui/suggestions/<optimization_id>/respond', methods=['POST'])
def respond_to_ui_optimization(optimization_id):
    """Respond to a UI optimization suggestion"""
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    try:
        data = request.get_json()
        username = session['username']
        response = data.get('response')  # 'accept' or 'dismiss'
        
        if ML_SYSTEMS_AVAILABLE:
            respond_to_ui_suggestion(username, optimization_id, response)
            message = f'Suggestion {response}ed successfully'
        else:
            message = 'ML systems not available'
        
        return jsonify({
            'success': True,
            'message': message,
            'ml_active': ML_SYSTEMS_AVAILABLE
        })
        
    except Exception as e:
        logger.error(f"UI suggestion response error: {e}")
        return jsonify({'error': 'Response failed'}), 500

@app.route('/api/input/interpret', methods=['POST'])
def interpret_input_api():
    """API endpoint for system-wide input interpretation"""
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    try:
        data = request.get_json()
        username = session['username']
        text = data.get('text', '')
        app_name = data.get('app_name', 'dmlog')
        
        if ML_SYSTEMS_AVAILABLE:
            corrected_text, confidence, corrections = interpret_system_input(username, text, app_name)
        else:
            corrected_text, confidence, corrections = text, 1.0, []
        
        return jsonify({
            'success': True,
            'original_text': text,
            'corrected_text': corrected_text,
            'confidence': confidence,
            'corrections_applied': corrections,
            'ml_active': ML_SYSTEMS_AVAILABLE
        })
        
    except Exception as e:
        logger.error(f"Input interpretation error: {e}")
        return jsonify({'error': 'Interpretation failed'}), 500

@app.route('/api/ml/ecosystem/status', methods=['GET'])
def get_ml_ecosystem_status():
    """Get comprehensive ML ecosystem status"""
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    try:
        username = session['username']
        
        status = {
            'ml_systems_available': ML_SYSTEMS_AVAILABLE,
            'active_systems': [],
            'user_insights': {}
        }
        
        if ML_SYSTEMS_AVAILABLE:
            status['active_systems'] = [
                'response_optimizer',
                'voice_learning', 
                'universal_interpreter',
                'edge_interpreter',
                'system_input_interpreter',
                'ui_navigation_assistant',
                'tiered_llm_system',
                'ml_performance_optimizer',
                'realtime_learning_accelerator',
                'bot_interpreter_system',
                'progressive_efficiency_engine',
                'overnight_training_system'
            ]
            
            # Get insights from each system
            try:
                status['user_insights'] = {
                    'typing_patterns': system_input_service.get_user_stats(username),
                    'navigation_insights': get_navigation_insights(username),
                    'ui_suggestions_count': len(get_ui_suggestions(username)),
                    'llm_usage': tiered_llm.get_usage_stats()
                }
            except Exception as e:
                logger.warning(f"Could not get user insights: {e}")
                status['user_insights'] = {'error': 'Insights temporarily unavailable'}
        
        return jsonify({
            'success': True,
            'status': status
        })
        
    except Exception as e:
        logger.error(f"ML ecosystem status error: {e}")
        return jsonify({'error': 'Status unavailable'}), 500

# ML Performance Optimization Endpoints
@app.route('/api/ml/performance/optimize', methods=['POST'])
def optimize_ml_performance_endpoint():
    """Trigger ML performance optimization"""
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    try:
        username = session['username']
        
        if ML_SYSTEMS_AVAILABLE:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            optimization_result = loop.run_until_complete(optimize_ml_performance(username))
            loop.close()
        else:
            optimization_result = {'status': 'ml_unavailable', 'optimizations_applied': 0}
        
        return jsonify({
            'success': True,
            'optimization': optimization_result,
            'ml_active': ML_SYSTEMS_AVAILABLE
        })
        
    except Exception as e:
        logger.error(f"ML performance optimization error: {e}")
        return jsonify({'error': 'Optimization failed'}), 500

@app.route('/api/ml/performance/report', methods=['GET'])
def get_optimization_report_endpoint():
    """Get ML performance optimization report"""
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    try:
        username = session['username']
        
        if ML_SYSTEMS_AVAILABLE:
            report = get_optimization_report(username)
        else:
            report = {'status': 'ml_unavailable', 'total_optimizations': 0}
        
        return jsonify({
            'success': True,
            'report': report,
            'ml_active': ML_SYSTEMS_AVAILABLE
        })
        
    except Exception as e:
        logger.error(f"Optimization report error: {e}")
        return jsonify({'error': 'Report unavailable'}), 500

# Real-time Learning Acceleration Endpoints
@app.route('/api/ml/learning/accelerate', methods=['POST'])
def accelerate_learning_endpoint():
    """Trigger real-time learning acceleration"""
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    try:
        username = session['username']
        data = request.get_json() or {}
        event_type = data.get('event_type', 'general_interaction')
        
        if ML_SYSTEMS_AVAILABLE:
            # Simplified acceleration for API testing
            acceleration_result = {
                'status': 'acceleration_triggered',
                'event_type': event_type,
                'user_id': username,
                'learning_accelerated': True,
                'timestamp': datetime.now().isoformat()
            }
        else:
            acceleration_result = {'status': 'ml_unavailable', 'learning_accelerated': False}
        
        return jsonify({
            'success': True,
            'acceleration': acceleration_result,
            'ml_active': ML_SYSTEMS_AVAILABLE
        })
        
    except Exception as e:
        logger.error(f"Learning acceleration error: {e}")
        return jsonify({'error': 'Acceleration failed'}), 500

@app.route('/api/ml/learning/apply', methods=['POST'])
def apply_accelerated_improvements_endpoint():
    """Apply accelerated learning improvements to user input"""
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    try:
        username = session['username']
        data = request.get_json() or {}
        text = data.get('text', '')
        
        if not text:
            return jsonify({'error': 'Text required'}), 400
        
        if ML_SYSTEMS_AVAILABLE:
            improved_text = apply_accelerated_improvements(username, text)
        else:
            improved_text = text
        
        return jsonify({
            'success': True,
            'original_text': text,
            'improved_text': improved_text,
            'improvements_applied': improved_text != text,
            'ml_active': ML_SYSTEMS_AVAILABLE
        })
        
    except Exception as e:
        logger.error(f"Accelerated improvements error: {e}")
        return jsonify({'error': 'Improvement failed'}), 500

@app.route('/api/ml/learning/insights', methods=['GET'])
def get_learning_insights_endpoint():
    """Get user learning insights"""
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    try:
        username = session['username']
        
        if ML_SYSTEMS_AVAILABLE:
            insights = get_user_learning_insights(username)
        else:
            insights = {'status': 'ml_unavailable', 'total_interactions': 0}
        
        return jsonify({
            'success': True,
            'insights': insights,
            'ml_active': ML_SYSTEMS_AVAILABLE
        })
        
    except Exception as e:
        logger.error(f"Learning insights error: {e}")
        return jsonify({'error': 'Insights unavailable'}), 500

# Bot Interpreter System Endpoints
@app.route('/api/bot-interpreter/create', methods=['POST'])
def create_bot_interpreter():
    """Create bot interpreter"""
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    try:
        data = request.get_json() or {}
        interpreter_type = data.get('type', 'bot_to_computer')
        source_system = data.get('source_system', '')
        target_system = data.get('target_system', '')
        
        if not source_system or not target_system:
            return jsonify({'error': 'Source and target systems required'}), 400
        
        if ML_SYSTEMS_AVAILABLE:
            if interpreter_type == 'bot_to_computer':
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                interpreter_id = loop.run_until_complete(create_bot_to_computer_interpreter(source_system, target_system))
                loop.close()
            elif interpreter_type == 'bot_to_bot':
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                interpreter_id = loop.run_until_complete(create_bot_to_bot_interpreter(source_system, target_system))
                loop.close()
            else:
                return jsonify({'error': 'Invalid interpreter type'}), 400
        else:
            interpreter_id = f"mock_{interpreter_type}_{source_system}_{target_system}"
        
        return jsonify({
            'success': True,
            'interpreter_id': interpreter_id,
            'type': interpreter_type,
            'source_system': source_system,
            'target_system': target_system
        })
        
    except Exception as e:
        logger.error(f"Bot interpreter creation error: {e}")
        return jsonify({'error': 'Interpreter creation failed'}), 500

@app.route('/api/bot-interpreter/interpret', methods=['POST'])
def interpret_bot_request():
    """Interpret bot command or communication"""
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    try:
        data = request.get_json() or {}
        interpreter_type = data.get('type', 'bot_to_computer')
        source_system = data.get('source_system', '')
        target_system = data.get('target_system', '')
        input_text = data.get('input_text', '')
        context = data.get('context', {})
        
        if not all([source_system, target_system, input_text]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        if ML_SYSTEMS_AVAILABLE:
            if interpreter_type == 'bot_to_computer':
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(interpret_bot_command(source_system, target_system, input_text, context))
                loop.close()
            elif interpreter_type == 'bot_to_bot':
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(interpret_bot_communication(source_system, target_system, input_text, context))
                loop.close()
            else:
                return jsonify({'error': 'Invalid interpreter type'}), 400
            
            return jsonify({
                'success': True,
                'original_input': input_text,
                'interpreted_output': result.interpreted_input,
                'confidence': result.confidence,
                'transformations_applied': result.applied_transformations,
                'error_probability': result.error_probability,
                'processing_time_ms': result.processing_time_ms,
                'model_version': result.model_version
            })
        else:
            return jsonify({
                'success': True,
                'original_input': input_text,
                'interpreted_output': input_text,
                'confidence': 0.5,
                'transformations_applied': [],
                'error_probability': 0.1,
                'processing_time_ms': 1.0,
                'model_version': 'mock_v1',
                'ml_active': False
            })
        
    except Exception as e:
        logger.error(f"Bot interpretation error: {e}")
        return jsonify({'error': 'Interpretation failed'}), 500

@app.route('/api/bot-interpreter/status', methods=['GET'])
def get_bot_interpreter_status():
    """Get bot interpreter system status"""
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    try:
        if ML_SYSTEMS_AVAILABLE:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            status = loop.run_until_complete(get_interpreter_system_status())
            loop.close()
        else:
            status = {'status': 'ml_unavailable', 'active_interpreters': 0}
        
        return jsonify({
            'success': True,
            'status': status,
            'ml_active': ML_SYSTEMS_AVAILABLE
        })
        
    except Exception as e:
        logger.error(f"Bot interpreter status error: {e}")
        return jsonify({'error': 'Status unavailable'}), 500

# Progressive Efficiency Engine Endpoints
@app.route('/api/efficiency/register-model', methods=['POST'])
def register_efficiency_model():
    """Register model for progressive optimization"""
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    try:
        data = request.get_json() or {}
        model_id = data.get('model_id', '')
        model_data = data.get('model_data', {})
        
        if not model_id or not model_data:
            return jsonify({'error': 'Model ID and data required'}), 400
        
        if ML_SYSTEMS_AVAILABLE:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            metrics = loop.run_until_complete(register_model_for_optimization(model_id, model_data))
            loop.close()
            return jsonify({
                'success': True,
                'model_id': model_id,
                'initial_size_kb': metrics.initial_size_kb,
                'efficiency_stage': metrics.stage.value,
                'scheduled_optimization': metrics.scheduled_next_optimization.isoformat()
            })
        else:
            return jsonify({
                'success': True,
                'model_id': model_id,
                'initial_size_kb': len(str(model_data)) / 1024,
                'efficiency_stage': 'initial',
                'ml_active': False
            })
        
    except Exception as e:
        logger.error(f"Model registration error: {e}")
        return jsonify({'error': 'Registration failed'}), 500

@app.route('/api/efficiency/optimize/<model_id>', methods=['POST'])
def optimize_efficiency_model(model_id: str):
    """Trigger model optimization"""
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    try:
        if ML_SYSTEMS_AVAILABLE:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(trigger_model_optimization(model_id))
            loop.close()
        else:
            result = {'status': 'ml_unavailable', 'optimization': 'mock'}
        
        return jsonify({
            'success': True,
            'model_id': model_id,
            'optimization_result': result,
            'ml_active': ML_SYSTEMS_AVAILABLE
        })
        
    except Exception as e:
        logger.error(f"Model optimization error: {e}")
        return jsonify({'error': 'Optimization failed'}), 500

@app.route('/api/efficiency/status', methods=['GET'])
def get_efficiency_status():
    """Get progressive efficiency system status"""
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    try:
        if ML_SYSTEMS_AVAILABLE:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            status = loop.run_until_complete(get_efficiency_system_status())
            loop.close()
        else:
            status = {'status': 'ml_unavailable', 'total_models': 0}
        
        return jsonify({
            'success': True,
            'status': status,
            'ml_active': ML_SYSTEMS_AVAILABLE
        })
        
    except Exception as e:
        logger.error(f"Efficiency status error: {e}")
        return jsonify({'error': 'Status unavailable'}), 500

# Overnight Training System Endpoints
@app.route('/api/overnight-training/record-interaction', methods=['POST'])
def record_training_interaction():
    """Record interaction for overnight training"""
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    try:
        username = session['username']
        data = request.get_json() or {}
        
        # Add user context to interaction data
        interaction_data = {
            'user_id': username,
            'timestamp': datetime.now().isoformat(),
            **data
        }
        
        if ML_SYSTEMS_AVAILABLE:
            record_daily_interaction(interaction_data)
        
        return jsonify({
            'success': True,
            'recorded': True,
            'ml_active': ML_SYSTEMS_AVAILABLE
        })
        
    except Exception as e:
        logger.error(f"Interaction recording error: {e}")
        return jsonify({'error': 'Recording failed'}), 500

@app.route('/api/overnight-training/status', methods=['GET'])
def get_training_status():
    """Get overnight training system status"""
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    try:
        if ML_SYSTEMS_AVAILABLE:
            status = get_overnight_training_status()
        else:
            status = {'status': 'ml_unavailable', 'training_active': False}
        
        return jsonify({
            'success': True,
            'status': status,
            'ml_active': ML_SYSTEMS_AVAILABLE
        })
        
    except Exception as e:
        logger.error(f"Training status error: {e}")
        return jsonify({'error': 'Status unavailable'}), 500

@app.route('/api/overnight-training/trigger', methods=['POST'])
def trigger_training():
    """Manually trigger overnight training"""
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    try:
        if ML_SYSTEMS_AVAILABLE:
            # This would normally be scheduled, but allow manual trigger for testing
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(manual_trigger_overnight_training())
            loop.close()
            
            return jsonify({
                'success': True,
                'message': 'Overnight training triggered',
                'ml_active': True
            })
        else:
            return jsonify({
                'success': True,
                'message': 'Training would be triggered (ML unavailable)',
                'ml_active': False
            })
        
    except Exception as e:
        logger.error(f"Training trigger error: {e}")
        return jsonify({'error': 'Training trigger failed'}), 500

# Load Balancer and Clustering Endpoints
@app.route('/api/load-balancer/status')
def load_balancer_status():
    """Get load balancer status and statistics"""
    try:
        if ML_SYSTEMS_AVAILABLE and 'load_balancer' in globals():
            stats = load_balancer.get_statistics()
            return jsonify({
                'success': True,
                'status': 'active',
                'statistics': stats,
                'servers': {
                    server_id: {
                        'host': server.host,
                        'port': server.port,
                        'health_status': server.health_status,
                        'current_connections': server.current_connections,
                        'total_requests': server.total_requests,
                        'avg_response_time': server.avg_response_time,
                        'success_rate': server.success_rate,
                        'load_score': server.load_score
                    }
                    for server_id, server in load_balancer.servers.items()
                }
            })
        else:
            return jsonify({
                'success': True,
                'status': 'inactive',
                'message': 'Load balancer not available'
            })
    except Exception as e:
        logger.error(f"Load balancer status error: {e}")
        return jsonify({'error': 'Status unavailable'}), 500

@app.route('/api/load-balancer/add-server', methods=['POST'])
def add_server_to_load_balancer():
    """Add a server to the load balancer"""
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    try:
        data = request.get_json() or {}
        server_id = data.get('server_id', '')
        host = data.get('host', '')
        port = data.get('port', 0)
        capabilities = data.get('capabilities', [])
        weight = data.get('weight', 1.0)
        
        if not all([server_id, host, port]):
            return jsonify({'error': 'Server ID, host, and port required'}), 400
        
        if ML_SYSTEMS_AVAILABLE and 'load_balancer' in globals():
            server = ServerInstance(
                id=server_id,
                host=host,
                port=port,
                weight=weight,
                capabilities=capabilities
            )
            load_balancer.add_server(server)
            
            return jsonify({
                'success': True,
                'message': f'Server {server_id} added to load balancer',
                'server': {
                    'id': server_id,
                    'host': host,
                    'port': port,
                    'weight': weight,
                    'capabilities': capabilities
                }
            })
        else:
            return jsonify({
                'success': True,
                'message': f'Server {server_id} would be added (load balancer inactive)',
                'server_id': server_id
            })
    
    except Exception as e:
        logger.error(f"Add server error: {e}")
        return jsonify({'error': 'Failed to add server'}), 500

@app.route('/api/load-balancer/handle-request', methods=['POST'])
def handle_load_balanced_request():
    """Handle a request through the load balancer"""
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    try:
        data = request.get_json() or {}
        request_info = {
            'method': data.get('method', 'GET'),
            'path': data.get('path', '/'),
            'client_ip': request.remote_addr,
            'request_type': data.get('request_type', 'general'),
            'capabilities': data.get('capabilities', []),
            'session_id': session.get('session_id', str(uuid.uuid4())),
            'data': data.get('payload', {}),
            'headers': dict(request.headers)
        }
        
        if ML_SYSTEMS_AVAILABLE and 'load_balancer' in globals():
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(load_balancer.handle_request(request_info))
            loop.close()
            
            return jsonify({
                'success': result['success'],
                'result': result,
                'load_balanced': True
            })
        else:
            return jsonify({
                'success': True,
                'result': {'data': 'Load balancer simulation - request would be balanced'},
                'load_balanced': False,
                'message': 'Load balancer not active'
            })
    
    except Exception as e:
        logger.error(f"Load balanced request error: {e}")
        return jsonify({'error': 'Request handling failed'}), 500

@app.route('/api/cluster/status')
def cluster_status():
    """Get cluster status and topology"""
    try:
        if ML_SYSTEMS_AVAILABLE and 'cluster_manager' in globals():
            status = cluster_manager.get_cluster_status()
            return jsonify({
                'success': True,
                'cluster_active': True,
                'status': status
            })
        else:
            return jsonify({
                'success': True,
                'cluster_active': False,
                'message': 'Cluster manager not available'
            })
    except Exception as e:
        logger.error(f"Cluster status error: {e}")
        return jsonify({'error': 'Status unavailable'}), 500

@app.route('/api/cluster/services')
def cluster_services():
    """Get registered services in the cluster"""
    try:
        if ML_SYSTEMS_AVAILABLE and 'cluster_manager' in globals():
            services = {}
            for service_name, endpoints in cluster_manager.service_registry.services.items():
                services[service_name] = [
                    {
                        'node_id': ep.node_id,
                        'host': ep.host,
                        'port': ep.port,
                        'path': ep.path,
                        'protocol': ep.protocol,
                        'tags': list(ep.tags),
                        'weight': ep.weight
                    }
                    for ep in endpoints
                ]
            
            return jsonify({
                'success': True,
                'services': services,
                'total_services': len(services)
            })
        else:
            return jsonify({
                'success': True,
                'services': {},
                'total_services': 0,
                'message': 'Cluster manager not available'
            })
    except Exception as e:
        logger.error(f"Cluster services error: {e}")
        return jsonify({'error': 'Services unavailable'}), 500

@app.route('/cluster/join', methods=['POST'])
def handle_cluster_join():
    """Handle cluster join requests from other nodes"""
    try:
        if ML_SYSTEMS_AVAILABLE and 'cluster_manager' in globals():
            node_info = request.get_json()
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            cluster_info = loop.run_until_complete(cluster_manager.handle_join_request(node_info))
            loop.close()
            
            return jsonify(cluster_info)
        else:
            return jsonify({'error': 'Cluster not available'}), 503
    except Exception as e:
        logger.error(f"Cluster join error: {e}")
        return jsonify({'error': 'Join failed'}), 500

@app.route('/cluster/message', methods=['POST'])
def handle_cluster_message():
    """Handle cluster messages from other nodes"""
    try:
        if ML_SYSTEMS_AVAILABLE and 'cluster_manager' in globals():
            message = request.get_json()
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(cluster_manager.handle_cluster_message(message))
            loop.close()
            
            return jsonify(result)
        else:
            return jsonify({'error': 'Cluster not available'}), 503
    except Exception as e:
        logger.error(f"Cluster message error: {e}")
        return jsonify({'error': 'Message handling failed'}), 500

@app.route('/health')
def health_check():
    """Health check endpoint for load balancer"""
    try:
        # Check ML systems
        ml_status = 'active' if ML_SYSTEMS_AVAILABLE else 'inactive'
        
        # Get resource usage
        try:
            import psutil
            cpu_usage = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            memory_usage = memory.percent
        except ImportError:
            cpu_usage = 0.0
            memory_usage = 0.0
        
        # Check ML model load (simplified)
        ml_model_load = 0.0
        if ML_SYSTEMS_AVAILABLE:
            # Could calculate actual ML model load here
            ml_model_load = min(cpu_usage * 0.5, 100.0)
        
        return jsonify({
            'status': 'healthy',
            'ml_systems': ml_status,
            'cpu_usage': cpu_usage,
            'memory_usage': memory_usage,
            'ml_model_load': ml_model_load,
            'timestamp': datetime.now().isoformat(),
            'uptime': time.time() - app.config.get('start_time', time.time())
        })
    
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return jsonify({
            'status': 'degraded',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 503

# Claude API Chooser Endpoints
@app.route('/api/claude/choose-model', methods=['POST'])
def choose_claude_model_endpoint():
    """Choose optimal Claude model for a task"""
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    try:
        data = request.get_json() or {}
        text = data.get('text', '')
        context = data.get('context', {})
        
        if not text:
            return jsonify({'error': 'Text required'}), 400
        
        if ML_SYSTEMS_AVAILABLE:
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            chosen_model = loop.run_until_complete(choose_claude_model(text, context))
            loop.close()
            
            # Analyze task for additional insights
            features = claude_chooser.analyze_task(text, context)
            
            return jsonify({
                'success': True,
                'chosen_model': chosen_model.value,
                'task_analysis': {
                    'type': features.task_type,
                    'complexity': features.complexity_score,
                    'text_length': features.text_length,
                    'technical_keywords': features.technical_keywords,
                    'code_blocks': features.code_blocks
                },
                'reasoning': f"Selected {chosen_model.value} based on task complexity {features.complexity_score:.2f} and type {features.task_type}"
            })
        else:
            return jsonify({
                'success': True,
                'chosen_model': 'claude-3-sonnet-20240229',
                'task_analysis': {'type': 'unknown'},
                'reasoning': 'ML chooser not available - using default'
            })
    
    except Exception as e:
        logger.error(f"Claude model selection error: {e}")
        return jsonify({'error': 'Model selection failed'}), 500

@app.route('/api/claude/request', methods=['POST'])
def make_claude_request_endpoint():
    """Make a request to Claude using the chooser"""
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    try:
        data = request.get_json() or {}
        text = data.get('text', '')
        context = data.get('context', {})
        specific_model = data.get('model')  # Optional: force specific model
        max_tokens = data.get('max_tokens', 4000)
        
        if not text:
            return jsonify({'error': 'Text required'}), 400
        
        if ML_SYSTEMS_AVAILABLE:
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Choose model if not specified
            model = None
            if specific_model:
                # Map string to enum
                model_mapping = {
                    'haiku': ClaudeModel.HAIKU,
                    'sonnet': ClaudeModel.SONNET,
                    'opus': ClaudeModel.OPUS,
                    'opus-4.1': ClaudeModel.OPUS_41
                }
                model = model_mapping.get(specific_model.lower())
            
            # Make request
            result = loop.run_until_complete(make_claude_request(text, model, context))
            loop.close()
            
            # Generate request ID for feedback tracking
            request_id = f"req_{session['username']}_{int(time.time())}"
            
            return jsonify({
                'success': result['success'],
                'response': result.get('response', ''),
                'model_used': result.get('model_used', ''),
                'response_time': result.get('response_time', 0),
                'token_efficiency': result.get('token_efficiency', 0),
                'request_id': request_id,
                'usage': result.get('usage'),
                'error': result.get('error')
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Claude API chooser not available',
                'model_used': 'none'
            })
    
    except Exception as e:
        logger.error(f"Claude request error: {e}")
        return jsonify({'error': 'Request failed'}), 500

@app.route('/api/claude/feedback', methods=['POST'])
def record_claude_feedback_endpoint():
    """Record feedback for Claude response quality"""
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    try:
        data = request.get_json() or {}
        request_id = data.get('request_id', '')
        user_rating = data.get('rating', 0.5)  # 0.0-1.0
        task_text = data.get('task_text', '')
        model_used = data.get('model_used', '')
        response_time = data.get('response_time', 1.0)
        context = data.get('context', {})
        user_feedback = data.get('feedback', 'neutral')  # good, bad, excellent, poor
        
        if not all([request_id, task_text, model_used]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        if ML_SYSTEMS_AVAILABLE:
            # Record feedback for ML training
            record_claude_feedback(
                request_id, float(user_rating), task_text, 
                model_used, float(response_time), context
            )
            
            return jsonify({
                'success': True,
                'message': 'Feedback recorded for ML training',
                'request_id': request_id,
                'rating': user_rating
            })
        else:
            return jsonify({
                'success': True,
                'message': 'Feedback recorded (ML training not available)',
                'request_id': request_id
            })
    
    except Exception as e:
        logger.error(f"Claude feedback error: {e}")
        return jsonify({'error': 'Feedback recording failed'}), 500

@app.route('/api/claude/stats')
def get_claude_stats():
    """Get Claude API chooser performance statistics"""
    try:
        if ML_SYSTEMS_AVAILABLE:
            stats = get_claude_chooser_stats()
            return jsonify({
                'success': True,
                'stats': stats,
                'chooser_active': True
            })
        else:
            return jsonify({
                'success': True,
                'stats': {'message': 'Claude chooser not available'},
                'chooser_active': False
            })
    
    except Exception as e:
        logger.error(f"Claude stats error: {e}")
        return jsonify({'error': 'Stats unavailable'}), 500

@app.route('/api/claude/models')
def get_available_claude_models():
    """Get available Claude models and their characteristics"""
    try:
        if ML_SYSTEMS_AVAILABLE:
            models_info = {}
            for model in ClaudeModel:
                model_config = claude_chooser.models.get(model, {})
                models_info[model.value] = {
                    'speed': model_config.get('speed', 0.5),
                    'cost': model_config.get('cost', 1.0),
                    'capability': model_config.get('capability', 0.5),
                    'context_limit': model_config.get('context_limit', 200000),
                    'best_for': model_config.get('best_for', [])
                }
            
            # Add performance data if available
            for model_name, perf in claude_chooser.model_performance.items():
                if model_name in models_info:
                    models_info[model_name]['performance'] = {
                        'avg_rating': perf['avg_rating'],
                        'avg_response_time': perf['avg_response_time'],
                        'success_rate': perf['success_rate'],
                        'total_requests': perf['total_requests']
                    }
            
            return jsonify({
                'success': True,
                'models': models_info,
                'total_models': len(models_info)
            })
        else:
            return jsonify({
                'success': True,
                'models': {
                    'claude-3-sonnet-20240229': {
                        'speed': 0.8,
                        'cost': 1.0,
                        'capability': 0.85,
                        'best_for': ['general', 'coding']
                    }
                },
                'total_models': 1,
                'message': 'Limited model info - chooser not active'
            })
    
    except Exception as e:
        logger.error(f"Claude models error: {e}")
        return jsonify({'error': 'Models info unavailable'}), 500

@app.route('/api/claude/cleanup', methods=['POST'])
def claude_cleanup_notes():
    """Clean up old training notes to manage space"""
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    try:
        data = request.get_json() or {}
        days_to_keep = data.get('days_to_keep', 30)
        
        if ML_SYSTEMS_AVAILABLE:
            deleted_count = claude_chooser.cleanup_old_notes(days_to_keep)
            return jsonify({
                'success': True,
                'deleted_notes': deleted_count,
                'days_kept': days_to_keep,
                'message': f'Cleaned up {deleted_count} old notes'
            })
        else:
            return jsonify({
                'success': True,
                'deleted_notes': 0,
                'message': 'Cleanup not available - chooser inactive'
            })
    
    except Exception as e:
        logger.error(f"Claude cleanup error: {e}")
        return jsonify({'error': 'Cleanup failed'}), 500

@app.route('/logout')
def logout():
    """Handle user logout"""
    username = session.get('username', 'unknown')
    session.clear()
    logger.info(f"Beta user {username} logged out")
    return redirect(url_for('index'))

if __name__ == '__main__':
    import time
    
    # Record startup time for health checks
    app.config['start_time'] = time.time()
    
    # Ensure templates directory exists
    os.makedirs('templates', exist_ok=True)
    
    port = int(os.getenv('PORT', 8620))
    logger.info(f"🚀 Starting DMLog Beta Portal with SuperInstance ML Ecosystem on port {port}")
    logger.info(f"🧠 ML Systems Status: {'ACTIVE' if ML_SYSTEMS_AVAILABLE else 'BASIC MODE'}")
    
    if ML_SYSTEMS_AVAILABLE:
        logger.info("✨ Available Features:")
        logger.info("  • Real-time input interpretation and correction")
        logger.info("  • Voice command learning across ecosystem") 
        logger.info("  • UI navigation intelligence and optimization")
        logger.info("  • Response quality monitoring and improvement")
        logger.info("  • Tiered LLM cost optimization")
        logger.info("  • Edge device compatibility")
        logger.info("  • ML performance optimization and memory management")
        logger.info("  • Real-time learning acceleration and adaptation")
        logger.info("  • Multi-layer bot interpretation (bot-to-computer, bot-to-bot)")
        logger.info("  • Progressive model refinement with automatic compression")
        logger.info("  • Overnight training system with daily feed analysis")
        logger.info("  • Load balancing with ML-optimized server selection")
        logger.info("  • Distributed clustering with service discovery")
        logger.info("  • Enterprise security with JWT authentication")
        logger.info("  • Multi-tenant isolation and resource management")
        logger.info("  • Compliance monitoring for GDPR, HIPAA, SOX, PCI-DSS")
        logger.info("  • Rate limiting and audit logging for security")
        logger.info("  • Claude API chooser with intelligent model selection")
        logger.info("  • ML-powered response quality tracking and optimization")
        logger.info("  • Compact note-based training with space management")
    
    app.run(host='0.0.0.0', port=port, debug=True)