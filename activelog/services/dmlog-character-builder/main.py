"""
Advanced D&D Character Builder - Surpassing D&D Beyond
Revolutionary character creation with AI, voice guidance, and advanced optimization
"""

from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
import sqlite3
import json
import uuid
from datetime import datetime
import logging
import random
import re
from typing import Dict, List, Any, Optional, Tuple
import speech_recognition as sr
from pathlib import Path

# Import our advanced modules
from character_optimizer import CharacterOptimizer, PartyAnalyzer
from voice_handler import VoiceCharacterGuide
from ai_generators import CharacterVisualizer, CharacterAIGenerator
from dnd_data import DnDDatabase
from advanced_ai import AdvancedCharacterAI
from webgl_visualizer import WebGLCharacterVisualizer
from combat_simulator import CombatSimulator
from multiclass_optimizer import MulticlassOptimizer
from neural_optimizer import WorldClassNeuralOptimizer
from raytracing_renderer import PhotorealisticRaytracer
from multiplayer_system import MultiplayerCharacterBuilder
from mocap_animation import ProfessionalMocapSystem

app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize database
DB_PATH = 'character_builder.db'

def init_db():
    """Initialize the character builder database"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Characters table with advanced features
    c.execute('''CREATE TABLE IF NOT EXISTS characters (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        player_id TEXT,
        campaign_id TEXT,
        level INTEGER DEFAULT 1,
        experience INTEGER DEFAULT 0,
        race TEXT,
        class TEXT,
        subclass TEXT,
        background TEXT,
        alignment TEXT,
        ability_scores TEXT,  -- JSON: {str, dex, con, int, wis, cha}
        skills TEXT,          -- JSON array of skill proficiencies
        languages TEXT,       -- JSON array of languages
        proficiencies TEXT,   -- JSON array of tool/weapon proficiencies
        features TEXT,        -- JSON array of racial/class features
        spells TEXT,          -- JSON array of known spells
        equipment TEXT,       -- JSON array of equipment with quantities
        backstory TEXT,
        personality_traits TEXT,
        ideals TEXT,
        bonds TEXT,
        flaws TEXT,
        appearance TEXT,
        voice_profile TEXT,   -- JSON: voice characteristics for AI
        optimization_score REAL DEFAULT 0,
        build_type TEXT,      -- tank, damage, support, utility, etc.
        multiclass_path TEXT, -- JSON: suggested multiclass progression
        party_role TEXT,      -- primary role in party composition
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Parties table for group optimization
    c.execute('''CREATE TABLE IF NOT EXISTS parties (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        campaign_id TEXT,
        dm_id TEXT,
        members TEXT,         -- JSON array of character IDs
        composition_analysis TEXT,  -- JSON: party strengths/weaknesses
        recommended_builds TEXT,    -- JSON: suggested character builds
        balance_score REAL DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Templates table for quick-start builds
    c.execute('''CREATE TABLE IF NOT EXISTS build_templates (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        category TEXT,        -- iconic, optimized, beginner, etc.
        build_data TEXT,      -- JSON: complete character build
        tags TEXT,            -- JSON array of searchable tags
        power_level INTEGER,  -- 1-10 optimization rating
        complexity INTEGER,   -- 1-5 complexity for new players
        description TEXT,
        author TEXT,
        votes INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Homebrew content table
    c.execute('''CREATE TABLE IF NOT EXISTS homebrew_content (
        id TEXT PRIMARY KEY,
        type TEXT,            -- race, class, feat, spell, etc.
        name TEXT NOT NULL,
        content_data TEXT,    -- JSON: homebrew rules/stats
        balance_rating REAL,  -- AI-assessed balance score
        creator_id TEXT,
        approved BOOLEAN DEFAULT FALSE,
        warnings TEXT,        -- JSON array of balance concerns
        usage_count INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Voice session data for guided creation
    c.execute('''CREATE TABLE IF NOT EXISTS voice_sessions (
        id TEXT PRIMARY KEY,
        character_id TEXT,
        session_data TEXT,    -- JSON: conversation context and preferences
        voice_commands TEXT,  -- JSON array of processed commands
        suggestions TEXT,     -- JSON: AI suggestions based on voice input
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    conn.commit()
    conn.close()

# Initialize components
optimizer = CharacterOptimizer()
party_analyzer = PartyAnalyzer()
voice_guide = VoiceCharacterGuide()
visualizer = CharacterVisualizer()
dnd_db = DnDDatabase()
ai_generator = CharacterAIGenerator()

# Initialize next-generation systems
advanced_ai = AdvancedCharacterAI()
webgl_visualizer = WebGLCharacterVisualizer()
combat_simulator = CombatSimulator()

# Initialize world-class systems
neural_optimizer = WorldClassNeuralOptimizer()
raytracing_renderer = PhotorealisticRaytracer()
multiplayer_system = MultiplayerCharacterBuilder()
mocap_system = ProfessionalMocapSystem(port=8410)
multiclass_optimizer = MulticlassOptimizer()

@app.route('/')
def home():
    """Serve the advanced character builder interface"""
    return render_template('character_builder.html')

@app.route('/api/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'dmlog-character-builder',
        'version': '3.0.0',
        'features': [
            'advanced_optimization',
            'voice_guidance', 
            'ai_generation',
            'party_analysis',
            '3d_visualization',
            'combat_simulation',
            'multiclass_optimization',
            'advanced_backstory_ai',
            'real_time_visualization'
        ]
    })

# Character Creation Endpoints

@app.route('/api/character/create', methods=['POST'])
def create_character():
    """Create a new character with advanced optimization"""
    data = request.json
    
    character_id = str(uuid.uuid4())
    character_data = {
        'id': character_id,
        'name': data.get('name', 'Unnamed Character'),
        'player_id': data.get('player_id'),
        'campaign_id': data.get('campaign_id'),
        'level': data.get('level', 1),
        'race': data.get('race'),
        'class': data.get('class'),
        'subclass': data.get('subclass'),
        'background': data.get('background'),
        'alignment': data.get('alignment'),
        'ability_scores': json.dumps(data.get('ability_scores', {})),
        'skills': json.dumps(data.get('skills', [])),
        'languages': json.dumps(data.get('languages', [])),
        'proficiencies': json.dumps(data.get('proficiencies', [])),
        'features': json.dumps(data.get('features', [])),
        'spells': json.dumps(data.get('spells', [])),
        'equipment': json.dumps(data.get('equipment', [])),
        'backstory': data.get('backstory', ''),
        'personality_traits': data.get('personality_traits', ''),
        'ideals': data.get('ideals', ''),
        'bonds': data.get('bonds', ''),
        'flaws': data.get('flaws', ''),
        'appearance': data.get('appearance', '')
    }
    
    # Run optimization analysis
    optimization_result = optimizer.analyze_build(character_data)
    character_data['optimization_score'] = optimization_result['score']
    character_data['build_type'] = optimization_result['build_type']
    character_data['multiclass_path'] = json.dumps(optimization_result.get('multiclass_suggestions', []))
    
    # Save to database
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    placeholders = ', '.join(['?' for _ in character_data])
    columns = ', '.join(character_data.keys())
    
    c.execute(f'INSERT INTO characters ({columns}) VALUES ({placeholders})', 
              list(character_data.values()))
    
    conn.commit()
    conn.close()
    
    return jsonify({
        'character_id': character_id,
        'message': 'Character created successfully',
        'optimization': optimization_result
    })

@app.route('/api/character/step/<step>', methods=['POST'])
def character_step(step):
    """Handle step-by-step character creation with real-time feedback"""
    data = request.json
    
    response = {
        'step': step,
        'valid': True,
        'suggestions': [],
        'warnings': [],
        'preview': {},
        'next_step': None
    }
    
    if step == 'race':
        race = data.get('race')
        race_data = dnd_db.get_race(race)
        
        if race_data:
            response['preview'] = {
                'ability_bonuses': race_data.ability_score_increases,
                'traits': race_data.traits,
                'languages': race_data.languages,
                'proficiencies': race_data.proficiencies
            }
            response['suggestions'] = optimizer.suggest_classes_for_race(race)
            response['next_step'] = 'class'
    
    elif step == 'class':
        character_class = data.get('class')
        race = data.get('race')
        
        class_data = dnd_db.get_class(character_class)
        synergy_score = optimizer.calculate_race_class_synergy(race, character_class)
        
        if class_data:
            response['preview'] = {
                'hit_die': class_data['hit_die'],
                'primary_ability': class_data['primary_ability'],
                'saving_throws': class_data['saving_throw_proficiencies'],
                'skills': class_data['skill_choices'],
                'equipment': class_data['starting_equipment']
            }
            
            if synergy_score > 0.8:
                response['suggestions'].append("Excellent race/class combination!")
            elif synergy_score < 0.4:
                response['warnings'].append("This combination may not be optimal")
            
            response['next_step'] = 'abilities'
    
    elif step == 'abilities':
        method = data.get('method')  # point_buy, standard_array, roll
        scores = data.get('scores', {})
        race = data.get('race')
        character_class = data.get('class')
        
        if method == 'point_buy':
            point_cost = optimizer.calculate_point_buy_cost(scores)
            if point_cost > 27:
                response['valid'] = False
                response['warnings'].append(f"Point buy cost ({point_cost}) exceeds limit (27)")
        
        # Apply racial bonuses
        final_scores = optimizer.apply_racial_bonuses(scores, race)
        optimization = optimizer.optimize_ability_scores(final_scores, character_class)
        
        response['preview'] = {
            'final_scores': final_scores,
            'modifiers': {ability: (score - 10) // 2 for ability, score in final_scores.items()},
            'optimization_rating': optimization['rating'],
            'suggestions': optimization['improvements']
        }
        
        response['next_step'] = 'skills'
    
    elif step == 'skills':
        selected_skills = data.get('skills', [])
        character_class = data.get('class')
        background = data.get('background')
        
        available_skills = dnd_db.get_available_skills(character_class, background)
        skill_recommendations = optimizer.recommend_skills(character_class, selected_skills)
        
        response['preview'] = {
            'available_skills': available_skills,
            'recommendations': skill_recommendations,
            'synergies': optimizer.analyze_skill_synergies(selected_skills, character_class)
        }
        
        response['next_step'] = 'equipment'
    
    elif step == 'equipment':
        equipment = data.get('equipment', [])
        character_class = data.get('class')
        background = data.get('background')
        
        encumbrance = optimizer.calculate_encumbrance(equipment)
        optimization = optimizer.optimize_starting_equipment(character_class, background)
        
        response['preview'] = {
            'encumbrance': encumbrance,
            'ac_calculation': optimizer.calculate_ac(equipment),
            'damage_potential': optimizer.calculate_damage_potential(equipment, character_class),
            'optimized_loadout': optimization
        }
        
        response['next_step'] = 'background'
    
    return jsonify(response)

@app.route('/api/character/optimize', methods=['POST'])
def optimize_character():
    """Provide optimization suggestions for character build"""
    data = request.json
    
    optimization = optimizer.full_character_analysis(data)
    
    return jsonify({
        'overall_score': optimization['score'],
        'strengths': optimization['strengths'],
        'weaknesses': optimization['weaknesses'],
        'improvements': optimization['suggested_improvements'],
        'multiclass_options': optimization['multiclass_paths'],
        'feat_recommendations': optimization['recommended_feats'],
        'spell_optimization': optimization.get('spell_suggestions', []),
        'equipment_upgrades': optimization.get('equipment_suggestions', [])
    })

# Voice-Guided Creation Endpoints

@app.route('/api/voice/start-session', methods=['POST'])
def start_voice_session():
    """Start a voice-guided character creation session"""
    data = request.json
    session_id = str(uuid.uuid4())
    
    session = voice_guide.start_session(
        session_id=session_id,
        player_preferences=data.get('preferences', {}),
        campaign_info=data.get('campaign_info', {})
    )
    
    return jsonify({
        'session_id': session_id,
        'welcome_message': session['welcome'],
        'listening': True,
        'suggested_concepts': session['initial_suggestions']
    })

@app.route('/api/voice/process', methods=['POST'])
def process_voice_input():
    """Process voice input and provide intelligent responses"""
    data = request.json
    session_id = data.get('session_id')
    audio_data = data.get('audio_data')  # Base64 encoded audio
    text_input = data.get('text_input')  # Alternative text input
    
    if audio_data:
        # Process audio with speech recognition
        text_input = voice_guide.speech_to_text(audio_data)
    
    if not text_input:
        return jsonify({'error': 'No input received'}), 400
    
    # Process natural language input
    response = voice_guide.process_command(session_id, text_input)
    
    return jsonify({
        'recognized_text': text_input,
        'ai_response': response['message'],
        'suggested_actions': response['actions'],
        'character_updates': response.get('updates', {}),
        'next_question': response.get('next_question'),
        'confidence': response.get('confidence', 0.0)
    })

@app.route('/api/voice/generate-character', methods=['POST'])
def voice_generate_character():
    """Generate character from voice description"""
    data = request.json
    description = data.get('description')
    session_id = data.get('session_id')
    
    # Use AI to interpret the description and generate character
    character_concept = ai_generator.interpret_character_concept(description)
    generated_character = ai_generator.generate_character_from_concept(character_concept)
    
    # Apply voice preferences from session
    if session_id:
        session_data = voice_guide.get_session_data(session_id)
        generated_character = voice_guide.apply_session_preferences(
            generated_character, session_data
        )
    
    return jsonify({
        'concept_interpretation': character_concept,
        'generated_character': generated_character,
        'confidence': character_concept.get('confidence', 0.0),
        'alternatives': ai_generator.generate_alternatives(character_concept)
    })

# Party Builder Endpoints

@app.route('/api/party/create', methods=['POST'])
def create_party():
    """Create a new party and analyze composition"""
    data = request.json
    party_id = str(uuid.uuid4())
    
    party_data = {
        'id': party_id,
        'name': data.get('name', 'Unnamed Party'),
        'campaign_id': data.get('campaign_id'),
        'dm_id': data.get('dm_id'),
        'members': json.dumps(data.get('members', []))
    }
    
    # Analyze party composition
    if data.get('members'):
        analysis = party_analyzer.analyze_composition(data['members'])
        party_data['composition_analysis'] = json.dumps(analysis)
        party_data['balance_score'] = analysis['balance_score']
        party_data['recommended_builds'] = json.dumps(analysis['recommendations'])
    
    # Save to database
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    placeholders = ', '.join(['?' for _ in party_data])
    columns = ', '.join(party_data.keys())
    
    c.execute(f'INSERT INTO parties ({columns}) VALUES ({placeholders})', 
              list(party_data.values()))
    
    conn.commit()
    conn.close()
    
    return jsonify({
        'party_id': party_id,
        'message': 'Party created successfully',
        'analysis': analysis if data.get('members') else None
    })

@app.route('/api/party/<party_id>/analyze')
def analyze_party(party_id):
    """Analyze party composition and provide recommendations"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('SELECT * FROM parties WHERE id = ?', (party_id,))
    party = c.fetchone()
    
    if not party:
        return jsonify({'error': 'Party not found'}), 404
    
    member_ids = json.loads(party[4])  # members column
    
    # Get character data for all members
    characters = []
    for member_id in member_ids:
        c.execute('SELECT * FROM characters WHERE id = ?', (member_id,))
        char_data = c.fetchone()
        if char_data:
            characters.append(char_data)
    
    conn.close()
    
    # Perform comprehensive party analysis
    analysis = party_analyzer.comprehensive_analysis(characters)
    
    return jsonify({
        'party_id': party_id,
        'member_count': len(characters),
        'analysis': analysis,
        'recommendations': {
            'missing_roles': analysis['missing_roles'],
            'suggested_builds': analysis['build_suggestions'],
            'power_balance': analysis['power_analysis'],
            'synergy_opportunities': analysis['synergies']
        }
    })

# Quick-Start Templates

@app.route('/api/templates')
def get_templates():
    """Get all available character templates"""
    category = request.args.get('category', 'all')
    complexity = request.args.get('complexity', 'all')
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    query = 'SELECT * FROM build_templates WHERE 1=1'
    params = []
    
    if category != 'all':
        query += ' AND category = ?'
        params.append(category)
    
    if complexity != 'all':
        query += ' AND complexity <= ?'
        params.append(int(complexity))
    
    query += ' ORDER BY votes DESC, name ASC'
    
    c.execute(query, params)
    templates = c.fetchall()
    conn.close()
    
    # Convert to list of dictionaries
    template_list = []
    for template in templates:
        template_dict = {
            'id': template[0],
            'name': template[1],
            'category': template[2],
            'build_data': json.loads(template[3]),
            'tags': json.loads(template[4]),
            'power_level': template[5],
            'complexity': template[6],
            'description': template[7],
            'author': template[8],
            'votes': template[9]
        }
        template_list.append(template_dict)
    
    return jsonify({
        'templates': template_list,
        'categories': ['iconic', 'optimized', 'beginner', 'roleplay', 'multiclass'],
        'total': len(template_list)
    })

@app.route('/api/templates/random')
def random_character():
    """Generate a completely random character"""
    constraints = {
        'level': request.args.get('level', random.randint(1, 5)),
        'class': request.args.get('class'),
        'race': request.args.get('race'),
        'power_level': request.args.get('power_level', 'balanced')
    }
    
    character = ai_generator.generate_random_character(constraints)
    
    return jsonify({
        'character': character,
        'generation_method': 'random',
        'constraints_applied': constraints,
        'reroll_available': True
    })

# Import/Export Endpoints

@app.route('/api/import/dndbeyond', methods=['POST'])
def import_from_dndbeyond():
    """Import character from D&D Beyond (web scraping)"""
    data = request.json
    url = data.get('url')
    
    if not url:
        return jsonify({'error': 'D&D Beyond URL required'}), 400
    
    try:
        # Import character data (implementation would use web scraping)
        imported_character = ai_generator.import_from_dndbeyond(url)
        
        return jsonify({
            'imported_character': imported_character,
            'conversion_notes': imported_character.get('notes', []),
            'success': True
        })
    
    except Exception as e:
        return jsonify({
            'error': f'Import failed: {str(e)}',
            'success': False
        }), 500

@app.route('/api/export/<character_id>/<format>')
def export_character(character_id, format):
    """Export character to various formats"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('SELECT * FROM characters WHERE id = ?', (character_id,))
    character = c.fetchone()
    conn.close()
    
    if not character:
        return jsonify({'error': 'Character not found'}), 404
    
    # Convert character data
    character_data = {
        'id': character[0],
        'name': character[1],
        'level': character[4],
        'race': character[6],
        'class': character[7],
        'background': character[9],
        'ability_scores': json.loads(character[11]),
        'skills': json.loads(character[12]),
        # ... other fields
    }
    
    if format == 'pdf':
        # Generate PDF character sheet
        pdf_data = ai_generator.generate_pdf_character_sheet(character_data)
        return pdf_data, 200, {
            'Content-Type': 'application/pdf',
            'Content-Disposition': f'attachment; filename="{character_data["name"]}.pdf"'
        }
    
    elif format == 'roll20':
        # Convert to Roll20 format
        roll20_data = ai_generator.convert_to_roll20(character_data)
        return jsonify(roll20_data)
    
    elif format == 'foundry':
        # Convert to Foundry VTT format
        foundry_data = ai_generator.convert_to_foundry(character_data)
        return jsonify(foundry_data)
    
    else:
        return jsonify({'error': 'Unsupported export format'}), 400

# Real-time Visualization

@app.route('/api/character/visualize', methods=['POST'])
def visualize_character():
    """Generate real-time character visualization"""
    data = request.json
    
    visualization_data = visualizer.generate_character_image(
        race=data.get('race'),
        class_name=data.get('class'),
        appearance=data.get('appearance', {}),
        equipment=data.get('equipment', []),
        style=data.get('style', 'realistic')
    )
    
    return jsonify({
        'image_url': visualization_data['image_url'],
        'image_data': visualization_data.get('base64_data'),
        'generation_time': visualization_data['generation_time'],
        'style_applied': visualization_data['style'],
        'alternatives': visualization_data.get('alternatives', [])
    })

@app.route('/api/character/generate-art', methods=['POST'])
def generate_character_art():
    """Generate AI character art from description"""
    data = request.json
    description = data.get('description')
    character_data = data.get('character_data', {})
    
    art_prompt = ai_generator.create_art_prompt(description, character_data)
    generated_art = ai_generator.generate_character_art(art_prompt)
    
    return jsonify({
        'art_url': generated_art['url'],
        'prompt_used': art_prompt,
        'style': generated_art.get('style'),
        'variations': generated_art.get('variations', []),
        'generation_id': generated_art['id']
    })

# Professional Motion Capture Animation System

@app.route('/api/mocap/status', methods=['GET'])
def get_mocap_status():
    """Get motion capture system status"""
    return jsonify({
        'system_status': 'running',
        'websocket_port': 8410,
        'connected_clients': len(mocap_system.connected_clients),
        'recording_active': mocap_system.is_recording,
        'animation_library_size': len(mocap_system.animation_library),
        'capabilities': {
            'realtime_mocap': True,
            'facial_capture': True,
            'hand_tracking': True,
            'animation_blending': True,
            'professional_calibration': True
        }
    })

@app.route('/api/mocap/animations', methods=['GET'])
def get_animation_library():
    """Get available animations from the mocap library"""
    animations = {}
    for name, clip in mocap_system.animation_library.items():
        animations[name] = {
            'name': clip.name,
            'type': clip.animation_type.value,
            'duration': clip.duration,
            'frame_count': len(clip.frames),
            'loop': clip.loop,
            'priority': clip.priority
        }
    
    return jsonify({
        'animations': animations,
        'total_count': len(animations)
    })

@app.route('/api/mocap/skeleton', methods=['GET'])
def get_character_skeleton():
    """Get character skeleton structure for animation"""
    skeleton_data = {
        'bones': mocap_system.skeleton.bones,
        'hierarchy': mocap_system.skeleton.bone_hierarchy,
        'bind_pose': {
            bone_name: {
                'position': transform.position.tolist(),
                'rotation': transform.rotation.tolist(),
                'scale': transform.scale.tolist()
            }
            for bone_name, transform in mocap_system.skeleton.bind_pose.items()
        }
    }
    
    return jsonify(skeleton_data)

@app.route('/api/mocap/character/animate', methods=['POST'])
def animate_character():
    """Apply mocap animation to character"""
    data = request.json
    character_id = data.get('character_id')
    animation_name = data.get('animation_name')
    blend_weight = data.get('blend_weight', 1.0)
    
    if not character_id or not animation_name:
        return jsonify({'error': 'Character ID and animation name required'}), 400
    
    if animation_name not in mocap_system.animation_library:
        return jsonify({'error': f'Animation "{animation_name}" not found'}), 404
    
    # Get character data
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT data FROM characters WHERE id = ?', (character_id,))
    result = c.fetchone()
    conn.close()
    
    if not result:
        return jsonify({'error': 'Character not found'}), 404
    
    character_data = json.loads(result[0])
    
    # Apply animation with raytracing renderer
    animated_render = raytracing_renderer.render_animated_character(
        character_model=character_data,
        animation_name=animation_name,
        blend_weight=blend_weight
    )
    
    return jsonify({
        'character_id': character_id,
        'animation_applied': animation_name,
        'blend_weight': blend_weight,
        'render_data': {
            'image_url': animated_render.get('image_url'),
            'animation_frames': animated_render.get('frame_count'),
            'render_quality': animated_render.get('quality_score')
        }
    })

@app.route('/api/neural/optimize', methods=['POST'])
def neural_optimize_character():
    """Use neural network to optimize character build"""
    data = request.json
    character_data = data.get('character_data', {})
    optimization_goals = data.get('goals', ['combat', 'roleplay'])
    
    # Use neural optimizer
    optimized_build = neural_optimizer.optimize_character_build(
        character_data=character_data,
        optimization_goals=optimization_goals,
        use_quantum_enhancement=data.get('quantum_enhancement', True)
    )
    
    return jsonify({
        'original_build': character_data,
        'optimized_build': optimized_build.get('character_build'),
        'optimization_score': optimized_build.get('score'),
        'improvements': optimized_build.get('improvements'),
        'neural_analysis': optimized_build.get('analysis'),
        'quantum_enhanced': optimized_build.get('quantum_enhanced', False)
    })

@app.route('/api/raytracing/render', methods=['POST'])
def raytracing_render():
    """Generate photorealistic character render using ray tracing"""
    data = request.json
    character_data = data.get('character_data', {})
    lighting_setup = data.get('lighting', 'studio')
    quality_preset = data.get('quality', 'high')
    
    # Render with photorealistic ray tracer
    render_result = raytracing_renderer.render_character(
        character_model=character_data,
        lighting_environment=lighting_setup,
        quality_preset=quality_preset
    )
    
    return jsonify({
        'render_url': render_result.get('image_url'),
        'render_data': render_result.get('base64_data'),
        'lighting_used': lighting_setup,
        'quality_preset': quality_preset,
        'render_time': render_result.get('render_time'),
        'ray_samples': render_result.get('sample_count'),
        'global_illumination': render_result.get('gi_enabled', True)
    })

# Static files
@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)

if __name__ == '__main__':
    init_db()
    
    logger.info("Starting World-Class Character Builder")
    logger.info("Features: Neural Optimization, Ray Tracing, Mocap Animation, Multiplayer Collaboration")
    logger.info("Professional Motion Capture System running on port 8410")
    
    # Start mocap system in background
    import threading
    import asyncio
    
    def start_mocap_server():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(mocap_system.start_server())
    
    mocap_thread = threading.Thread(target=start_mocap_server, daemon=True)
    mocap_thread.start()
    
    app.run(host='0.0.0.0', port=8405, debug=True)