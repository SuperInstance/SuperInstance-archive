#!/usr/bin/env python3
"""
GAME TESTING WEB PORTAL
Live web interface to watch AI play games in real-time
Shows game testing attempts, scores, and progression through complexity levels
"""

from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
import threading
import time
import json
import os
from datetime import datetime
import subprocess
import random

from game_progression_tester import GameProgressionTester
from enhanced_training_loop import EnhancedTrainingLoop

app = Flask(__name__)
app.config['SECRET_KEY'] = 'game_testing_portal_secret'
socketio = SocketIO(app, cors_allowed_origins="*")

class GameTestingPortal:
    def __init__(self):
        self.system_name = "GameTestingPortal"
        self.version = "1.0_live_testing"
        
        # Core components
        self.game_tester = None
        self.training_loop = None
        
        # Testing session state
        self.testing_active = False
        self.current_session = None
        self.session_history = []
        
        # Real-time data
        self.live_testing_data = {
            'current_game': None,
            'testing_progress': 0,
            'games_completed': 0,
            'current_level': 'level_1_math',
            'quality_scores': [],
            'live_actions': []
        }
        
        print("🌐 GAME TESTING WEB PORTAL INITIALIZED")
        print("📺 Live game testing visualization ready")
    
    def start_testing_session(self):
        """Start a new game testing session"""
        if self.testing_active:
            return False
        
        print("🚀 Starting new game testing session...")
        
        self.testing_active = True
        self.current_session = {
            'session_id': f"session_{int(time.time())}",
            'start_time': datetime.now().isoformat(),
            'games_tested': [],
            'progression_path': []
        }
        
        # Initialize components
        self.game_tester = GameProgressionTester()
        self.training_loop = EnhancedTrainingLoop()
        
        # Start testing thread
        testing_thread = threading.Thread(target=self.run_continuous_testing)
        testing_thread.daemon = True
        testing_thread.start()
        
        return True
    
    def run_continuous_testing(self):
        """Run continuous game testing with live updates"""
        print("🎮 Starting continuous game testing...")
        
        try:
            while self.testing_active:
                # Get next game to build and test
                game_description = self.game_tester.get_next_game_suggestion()
                
                self.emit_update('game_build_start', {
                    'game_description': game_description,
                    'level': self.game_tester.current_level,
                    'complexity': self.game_tester.game_progression[self.game_tester.current_level]['complexity']
                })
                
                # Build the game
                build_result = self.build_game_for_testing(game_description)
                
                if build_result['status'] == 'success':
                    self.emit_update('game_build_complete', {
                        'success': True,
                        'app_path': build_result['app_path'],
                        'game_url': f"http://localhost:{build_result.get('port', 3000)}"
                    })
                    
                    # Start the game
                    game_process = self.start_game_process(build_result['app_path'])
                    
                    if game_process:
                        time.sleep(3)  # Wait for game to start
                        
                        # Test the game with live updates
                        game_url = f"http://localhost:{build_result.get('port', 3000)}"
                        test_result = self.test_game_with_live_updates(game_url, game_description)
                        
                        # Stop the game
                        self.stop_game_process(game_process)
                        
                        # Record results
                        self.record_test_result(game_description, test_result)
                        
                        # Check progression
                        if self.game_tester.check_progression_readiness():
                            progressed = self.game_tester.progress_to_next_level()
                            if progressed:
                                self.emit_update('level_progression', {
                                    'new_level': self.game_tester.current_level,
                                    'complexity': self.game_tester.game_progression[self.game_tester.current_level]['complexity']
                                })
                    else:
                        self.emit_update('game_start_failed', {'reason': 'Could not start game process'})
                else:
                    self.emit_update('game_build_failed', {'error': build_result.get('error', 'Unknown error')})
                
                # Brief pause between games
                if self.testing_active:
                    time.sleep(5)
                    
        except Exception as e:
            print(f"❌ Testing session error: {e}")
            self.emit_update('session_error', {'error': str(e)})
        finally:
            self.testing_active = False
            if self.game_tester:
                self.game_tester.cleanup()
    
    def build_game_for_testing(self, game_description):
        """Build a game for testing using the enhanced training loop"""
        try:
            app_spec = {
                'description': game_description,
                'is_game': True,
                'complexity_estimate': self.game_tester.game_progression[self.game_tester.current_level]['complexity'],
                'expected_features': ['interactive_gameplay', 'scoring', 'user_feedback']
            }
            
            build_result = self.training_loop.build_functional_app(app_spec)
            
            # Find available port
            port = self.find_available_port()
            build_result['port'] = port
            
            return build_result
            
        except Exception as e:
            return {
                'status': 'failed',
                'error': str(e)
            }
    
    def find_available_port(self, start_port=3000):
        """Find an available port for the game"""
        import socket
        
        for port in range(start_port, start_port + 100):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                result = s.connect_ex(('localhost', port))
                if result != 0:  # Port is available
                    return port
        return start_port  # Fallback
    
    def start_game_process(self, app_path):
        """Start the game server process"""
        try:
            env = os.environ.copy()
            env['PORT'] = str(self.find_available_port())
            
            process = subprocess.Popen(
                ['npm', 'start'],
                cwd=app_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env
            )
            
            return process
            
        except Exception as e:
            print(f"❌ Failed to start game: {e}")
            return None
    
    def stop_game_process(self, process):
        """Stop the game server process"""
        if process:
            try:
                process.terminate()
                process.wait(timeout=5)
            except:
                process.kill()
    
    def test_game_with_live_updates(self, game_url, game_description):
        """Test game with real-time updates to web portal"""
        print(f"🎮 Live testing: {game_description}")
        
        self.emit_update('game_test_start', {
            'game_url': game_url,
            'game_description': game_description,
            'expected_duration': self.game_tester.game_progression[self.game_tester.current_level]['play_duration']
        })
        
        # Perform comprehensive game test
        test_result = self.game_tester.comprehensive_game_test(game_url, game_description)
        
        # Stream gameplay actions in real-time
        gameplay_log = test_result.get('gameplay_log', {})
        actions = gameplay_log.get('actions', [])
        
        for i, action in enumerate(actions):
            self.emit_update('gameplay_action', {
                'action': action,
                'action_number': i + 1,
                'total_actions': len(actions),
                'progress': (i + 1) / len(actions) * 100
            })
            time.sleep(0.1)  # Small delay for live effect
        
        self.emit_update('game_test_complete', {
            'quality_score': test_result['quality_score'],
            'progression_ready': test_result['progression_ready'],
            'gameplay_summary': {
                'total_actions': len(actions),
                'duration': gameplay_log.get('duration', 0),
                'success': gameplay_log.get('success', False)
            }
        })
        
        return test_result
    
    def record_test_result(self, game_description, test_result):
        """Record test result in session history"""
        if self.current_session:
            self.current_session['games_tested'].append({
                'game_description': game_description,
                'test_result': test_result,
                'timestamp': datetime.now().isoformat()
            })
        
        # Update live data
        self.live_testing_data['games_completed'] += 1
        self.live_testing_data['quality_scores'].append(test_result['quality_score'])
        self.live_testing_data['current_level'] = self.game_tester.current_level
    
    def emit_update(self, event_type, data):
        """Emit real-time update to web portal"""
        socketio.emit('testing_update', {
            'event_type': event_type,
            'data': data,
            'timestamp': datetime.now().isoformat()
        })
        
        # Also print to console
        print(f"📡 {event_type}: {data}")
    
    def stop_testing_session(self):
        """Stop the current testing session"""
        self.testing_active = False
        if self.current_session:
            self.current_session['end_time'] = datetime.now().isoformat()
            self.session_history.append(self.current_session)
        
        if self.game_tester:
            self.game_tester.cleanup()
        
        print("⏹️ Game testing session stopped")

# Global portal instance
portal = GameTestingPortal()

@app.route('/')
def index():
    """Main portal page"""
    return render_template('game_testing_portal.html')

@app.route('/api/status')
def get_status():
    """Get current testing status"""
    return jsonify({
        'testing_active': portal.testing_active,
        'current_session': portal.current_session,
        'live_data': portal.live_testing_data,
        'game_tester_info': {
            'current_level': portal.game_tester.current_level if portal.game_tester else 'level_1_math',
            'games_tested': portal.game_tester.games_tested if portal.game_tester else 0,
            'successful_games': portal.game_tester.successful_games if portal.game_tester else 0
        }
    })

@app.route('/api/start_testing', methods=['POST'])
def start_testing():
    """Start a new testing session"""
    success = portal.start_testing_session()
    return jsonify({'success': success})

@app.route('/api/stop_testing', methods=['POST'])
def stop_testing():
    """Stop current testing session"""
    portal.stop_testing_session()
    return jsonify({'success': True})

@app.route('/api/session_history')
def get_session_history():
    """Get testing session history"""
    return jsonify(portal.session_history)

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    print('🔌 Client connected to game testing portal')
    emit('connection_established', {
        'message': 'Connected to Game Testing Portal',
        'status': portal.live_testing_data
    })

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    print('🔌 Client disconnected from game testing portal')

def create_portal_template():
    """Create the HTML template for the web portal"""
    template_dir = os.path.join(os.path.dirname(__file__), 'templates')
    os.makedirs(template_dir, exist_ok=True)
    
    template_content = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🎮 Game Testing Portal - AI Player Live View</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.7.2/socket.io.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Courier New', monospace;
            background: linear-gradient(135deg, #0c0c0c 0%, #1a1a2e 100%);
            color: #00ff41;
            overflow: hidden;
        }
        .container {
            display: grid;
            grid-template-areas: 
                "header header header"
                "status gameplay console"
                "controls gameplay console";
            grid-template-columns: 300px 1fr 350px;
            grid-template-rows: 80px 1fr 120px;
            height: 100vh;
            gap: 10px;
            padding: 10px;
        }
        .header {
            grid-area: header;
            background: rgba(0, 255, 65, 0.1);
            border: 1px solid #00ff41;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 10px;
        }
        .header h1 {
            font-size: 24px;
            text-shadow: 0 0 10px #00ff41;
        }
        .status {
            grid-area: status;
            background: rgba(0, 0, 0, 0.8);
            border: 1px solid #00ff41;
            border-radius: 10px;
            padding: 15px;
            overflow-y: auto;
        }
        .gameplay {
            grid-area: gameplay;
            background: rgba(0, 0, 0, 0.9);
            border: 2px solid #00ff41;
            border-radius: 10px;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            position: relative;
        }
        .console {
            grid-area: console;
            background: rgba(0, 0, 0, 0.9);
            border: 1px solid #00ff41;
            border-radius: 10px;
            padding: 10px;
            overflow-y: auto;
            font-size: 12px;
            line-height: 1.4;
        }
        .controls {
            grid-area: controls;
            background: rgba(0, 255, 65, 0.1);
            border: 1px solid #00ff41;
            border-radius: 10px;
            padding: 15px;
            display: flex;
            gap: 10px;
            align-items: center;
        }
        .btn {
            padding: 10px 20px;
            background: transparent;
            color: #00ff41;
            border: 1px solid #00ff41;
            border-radius: 5px;
            cursor: pointer;
            font-family: inherit;
            font-size: 14px;
            transition: all 0.3s;
        }
        .btn:hover {
            background: rgba(0, 255, 65, 0.2);
            box-shadow: 0 0 10px #00ff41;
        }
        .btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        .status-item {
            margin: 8px 0;
            padding: 5px;
            border-left: 2px solid #00ff41;
            padding-left: 10px;
        }
        .level-indicator {
            font-size: 18px;
            font-weight: bold;
            color: #ffff00;
            text-shadow: 0 0 5px #ffff00;
        }
        .game-frame {
            width: 90%;
            height: 80%;
            border: 1px solid #00ff41;
            border-radius: 5px;
            background: white;
            display: none;
        }
        .game-placeholder {
            text-align: center;
            font-size: 20px;
            opacity: 0.7;
        }
        .progress-bar {
            width: 100%;
            height: 20px;
            background: rgba(0, 0, 0, 0.5);
            border: 1px solid #00ff41;
            border-radius: 10px;
            margin: 10px 0;
            overflow: hidden;
        }
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #00ff41, #ffff00);
            width: 0%;
            transition: width 0.5s;
            border-radius: 10px;
        }
        .console-line {
            margin: 2px 0;
            opacity: 0.9;
        }
        .console-line.highlight {
            color: #ffff00;
            font-weight: bold;
        }
        .score-display {
            position: absolute;
            top: 10px;
            right: 10px;
            background: rgba(0, 0, 0, 0.8);
            padding: 10px;
            border: 1px solid #00ff41;
            border-radius: 5px;
            font-size: 16px;
        }
        .blinking {
            animation: blink 1s infinite;
        }
        @keyframes blink {
            0%, 50% { opacity: 1; }
            51%, 100% { opacity: 0.3; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎮 GAME TESTING PORTAL - AI PLAYER LIVE VIEW</h1>
        </div>
        
        <div class="status">
            <div class="status-item">
                <strong>📊 Current Level:</strong><br>
                <span id="current-level" class="level-indicator">LOADING...</span>
            </div>
            <div class="status-item">
                <strong>🎮 Games Tested:</strong> <span id="games-tested">0</span>
            </div>
            <div class="status-item">
                <strong>✅ Successful:</strong> <span id="games-successful">0</span>
            </div>
            <div class="status-item">
                <strong>⭐ Average Quality:</strong> <span id="average-quality">0.0</span>/10
            </div>
            <div class="status-item">
                <strong>🎯 Current Game:</strong><br>
                <span id="current-game">No game loaded</span>
            </div>
            <div class="progress-bar">
                <div id="progress-fill" class="progress-fill"></div>
            </div>
        </div>
        
        <div class="gameplay">
            <div id="game-placeholder" class="game-placeholder">
                🤖 AI Player Ready<br>
                <small>Start testing to see live gameplay</small>
            </div>
            <iframe id="game-frame" class="game-frame" src="about:blank"></iframe>
            <div class="score-display">
                <div>⚡ Actions: <span id="action-count">0</span></div>
                <div>⏱️ Duration: <span id="test-duration">0s</span></div>
                <div>⭐ Quality: <span id="quality-score">-</span>/10</div>
            </div>
        </div>
        
        <div class="console" id="console">
            <div class="console-line highlight">🎮 GAME TESTING CONSOLE INITIALIZED</div>
            <div class="console-line">📡 WebSocket connection established</div>
            <div class="console-line">🤖 AI player systems ready</div>
            <div class="console-line">📊 Progression tracking: Math → Logic → Arcade → Retro → Classic</div>
        </div>
        
        <div class="controls">
            <button id="start-btn" class="btn">🚀 Start Testing</button>
            <button id="stop-btn" class="btn" disabled>⏹️ Stop Testing</button>
            <button id="clear-btn" class="btn">🗑️ Clear Console</button>
            <div style="margin-left: auto;">
                <span>🔴 LIVE</span>
            </div>
        </div>
    </div>

    <script>
        const socket = io();
        let testingActive = false;
        let actionCount = 0;
        let testStartTime = null;
        let qualityScores = [];

        // DOM elements
        const startBtn = document.getElementById('start-btn');
        const stopBtn = document.getElementById('stop-btn');
        const clearBtn = document.getElementById('clear-btn');
        const console = document.getElementById('console');
        const gameFrame = document.getElementById('game-frame');
        const gamePlaceholder = document.getElementById('game-placeholder');

        // Socket event handlers
        socket.on('connection_established', (data) => {
            addConsoleMessage('🔌 Connected to Game Testing Portal', 'highlight');
            updateStatus(data.status);
        });

        socket.on('testing_update', (update) => {
            handleTestingUpdate(update);
        });

        // Button event handlers
        startBtn.onclick = () => startTesting();
        stopBtn.onclick = () => stopTesting();
        clearBtn.onclick = () => clearConsole();

        async function startTesting() {
            try {
                const response = await fetch('/api/start_testing', { method: 'POST' });
                const result = await response.json();
                
                if (result.success) {
                    testingActive = true;
                    startBtn.disabled = true;
                    stopBtn.disabled = false;
                    addConsoleMessage('🚀 Game testing session started', 'highlight');
                }
            } catch (error) {
                addConsoleMessage(`❌ Failed to start testing: ${error.message}`);
            }
        }

        async function stopTesting() {
            try {
                const response = await fetch('/api/stop_testing', { method: 'POST' });
                const result = await response.json();
                
                if (result.success) {
                    testingActive = false;
                    startBtn.disabled = false;
                    stopBtn.disabled = true;
                    addConsoleMessage('⏹️ Game testing session stopped', 'highlight');
                    hideGameFrame();
                }
            } catch (error) {
                addConsoleMessage(`❌ Failed to stop testing: ${error.message}`);
            }
        }

        function clearConsole() {
            console.innerHTML = '';
            addConsoleMessage('🗑️ Console cleared');
        }

        function handleTestingUpdate(update) {
            const { event_type, data, timestamp } = update;

            switch (event_type) {
                case 'game_build_start':
                    addConsoleMessage(`🏗️ Building game: ${data.game_description}`);
                    addConsoleMessage(`📊 Level: ${data.level} (Complexity: ${data.complexity})`);
                    document.getElementById('current-game').textContent = data.game_description;
                    break;

                case 'game_build_complete':
                    addConsoleMessage(`✅ Game build complete`);
                    addConsoleMessage(`🌐 Game URL: ${data.game_url}`);
                    showGameFrame(data.game_url);
                    break;

                case 'game_build_failed':
                    addConsoleMessage(`❌ Game build failed: ${data.error}`);
                    break;

                case 'game_test_start':
                    addConsoleMessage(`🎮 Starting AI gameplay test...`);
                    addConsoleMessage(`⏱️ Expected duration: ${data.expected_duration}s`);
                    actionCount = 0;
                    testStartTime = Date.now();
                    document.getElementById('action-count').textContent = '0';
                    document.getElementById('test-duration').textContent = '0s';
                    break;

                case 'gameplay_action':
                    actionCount++;
                    document.getElementById('action-count').textContent = actionCount;
                    document.getElementById('progress-fill').style.width = `${data.progress}%`;
                    
                    if (testStartTime) {
                        const duration = Math.floor((Date.now() - testStartTime) / 1000);
                        document.getElementById('test-duration').textContent = `${duration}s`;
                    }
                    
                    addConsoleMessage(`🎮 AI Action ${data.action_number}: ${data.action}`);
                    break;

                case 'game_test_complete':
                    addConsoleMessage(`🏁 Game test complete!`, 'highlight');
                    addConsoleMessage(`⭐ Quality Score: ${data.quality_score}/10`);
                    addConsoleMessage(`📊 Total Actions: ${data.gameplay_summary.total_actions}`);
                    addConsoleMessage(`⏱️ Duration: ${data.gameplay_summary.duration.toFixed(1)}s`);
                    
                    document.getElementById('quality-score').textContent = data.quality_score.toFixed(1);
                    qualityScores.push(data.quality_score);
                    
                    const avgQuality = qualityScores.reduce((a, b) => a + b, 0) / qualityScores.length;
                    document.getElementById('average-quality').textContent = avgQuality.toFixed(1);
                    
                    if (data.progression_ready) {
                        addConsoleMessage(`🆙 Ready for next complexity level!`, 'highlight');
                    } else {
                        addConsoleMessage(`🔄 Needs improvement before progressing`);
                    }
                    
                    setTimeout(() => hideGameFrame(), 3000);
                    break;

                case 'level_progression':
                    addConsoleMessage(`🆙 LEVEL PROGRESSION!`, 'highlight');
                    addConsoleMessage(`📈 Advanced to: ${data.new_level}`);
                    addConsoleMessage(`🎯 New complexity: ${data.complexity}`);
                    document.getElementById('current-level').textContent = data.new_level.replace('_', ' ').toUpperCase();
                    break;

                case 'session_error':
                    addConsoleMessage(`❌ Session error: ${data.error}`);
                    break;
            }
        }

        function addConsoleMessage(message, className = '') {
            const line = document.createElement('div');
            line.className = `console-line ${className}`;
            line.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
            console.appendChild(line);
            console.scrollTop = console.scrollHeight;
        }

        function showGameFrame(gameUrl) {
            gameFrame.src = gameUrl;
            gameFrame.style.display = 'block';
            gamePlaceholder.style.display = 'none';
        }

        function hideGameFrame() {
            gameFrame.style.display = 'none';
            gamePlaceholder.style.display = 'block';
            document.getElementById('current-game').textContent = 'No game loaded';
        }

        function updateStatus(status) {
            // Update status display with live data
            if (status) {
                document.getElementById('games-tested').textContent = status.games_completed || 0;
                document.getElementById('current-level').textContent = 
                    (status.current_level || 'level_1_math').replace('_', ' ').toUpperCase();
            }
        }

        // Update timer every second
        setInterval(() => {
            if (testStartTime) {
                const duration = Math.floor((Date.now() - testStartTime) / 1000);
                document.getElementById('test-duration').textContent = `${duration}s`;
            }
        }, 1000);
    </script>
</body>
</html>'''
    
    with open(os.path.join(template_dir, 'game_testing_portal.html'), 'w') as f:
        f.write(template_content)
    
    print("📄 Web portal template created")

if __name__ == '__main__':
    print("🌐 GAME TESTING WEB PORTAL")
    print("="*50)
    
    # Create template
    create_portal_template()
    
    print("🚀 Starting web portal on http://localhost:5000")
    print("🎮 Features:")
    print("  • Live game testing visualization")
    print("  • Real-time AI player actions")
    print("  • Progressive complexity levels")
    print("  • Quality scoring system")
    print("  • 10+ second gameplay sessions")
    
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)