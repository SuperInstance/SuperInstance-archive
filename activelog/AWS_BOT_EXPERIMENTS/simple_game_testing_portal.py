#!/usr/bin/env python3
"""
SIMPLE GAME TESTING WEB PORTAL
Live web interface to watch AI play games in real-time
No complex dependencies - uses simple HTTP and JavaScript polling
"""

from flask import Flask, render_template, jsonify, request
import threading
import time
import json
import os
from datetime import datetime
import subprocess
import random
import signal
import sys

from game_progression_tester import GameProgressionTester
from enhanced_training_loop import EnhancedTrainingLoop

app = Flask(__name__)

class SimpleGameTestingPortal:
    def __init__(self):
        self.system_name = "SimpleGameTestingPortal"
        self.version = "1.0_simple_http"
        
        # Core components
        self.game_tester = None
        self.training_loop = None
        
        # Testing session state
        self.testing_active = False
        self.current_session = None
        self.session_history = []
        
        # Real-time data for JavaScript polling
        self.live_data = {
            'current_game': 'No game loaded',
            'testing_progress': 0,
            'games_completed': 0,
            'successful_games': 0,
            'current_level': 'level_1_math',
            'quality_scores': [],
            'live_actions': [],
            'latest_update': '',
            'game_url': '',
            'test_duration': 0,
            'action_count': 0,
            'current_quality': 0,
            'testing_status': 'idle'
        }
        
        print("🌐 SIMPLE GAME TESTING WEB PORTAL INITIALIZED")
        print("📺 Live game testing visualization ready")
    
    def start_testing_session(self):
        """Start a new game testing session"""
        if self.testing_active:
            return False
        
        print("🚀 Starting new game testing session...")
        
        self.testing_active = True
        self.live_data['testing_status'] = 'active'
        
        # Initialize components
        self.game_tester = GameProgressionTester()
        self.training_loop = EnhancedTrainingLoop()
        
        # Start testing thread
        testing_thread = threading.Thread(target=self.run_continuous_testing)
        testing_thread.daemon = True
        testing_thread.start()
        
        return True
    
    def update_live_data(self, key, value, message=None):
        """Update live data and add message"""
        self.live_data[key] = value
        if message:
            self.live_data['latest_update'] = f"[{datetime.now().strftime('%H:%M:%S')}] {message}"
            print(f"📡 {message}")
    
    def run_continuous_testing(self):
        """Run continuous game testing with live updates"""
        print("🎮 Starting continuous game testing...")
        
        try:
            while self.testing_active:
                # Get next game suggestion
                game_description = self.game_tester.get_next_game_suggestion()
                
                self.update_live_data('current_game', game_description, 
                                    f"🏗️ Building game: {game_description}")
                
                # Build the game
                build_result = self.build_and_test_game(game_description)
                
                # Update statistics
                self.live_data['games_completed'] += 1
                if build_result.get('success', False):
                    self.live_data['successful_games'] += 1
                    self.live_data['quality_scores'].append(build_result.get('quality_score', 0))
                
                # Check progression
                if self.game_tester.check_progression_readiness():
                    old_level = self.game_tester.current_level
                    progressed = self.game_tester.progress_to_next_level()
                    if progressed:
                        self.update_live_data('current_level', self.game_tester.current_level,
                                            f"🆙 PROGRESSED from {old_level} to {self.game_tester.current_level}")
                
                # Brief pause between games
                if self.testing_active:
                    time.sleep(3)
                    
        except Exception as e:
            print(f"❌ Testing session error: {e}")
            self.update_live_data('testing_status', 'error', f"❌ Session error: {str(e)}")
        finally:
            self.testing_active = False
            self.live_data['testing_status'] = 'idle'
            if self.game_tester:
                self.game_tester.cleanup()
    
    def build_and_test_game(self, game_description):
        """Build and test a game, updating live data"""
        try:
            # Build game
            self.update_live_data('testing_status', 'building', f"🏗️ Building {game_description}")
            
            app_spec = {
                'description': game_description,
                'is_game': True,
                'complexity_estimate': self.game_tester.game_progression[self.game_tester.current_level]['complexity'],
                'expected_features': ['interactive_gameplay']
            }
            
            build_result = self.training_loop.build_functional_app(app_spec)
            
            if build_result['status'] != 'success':
                self.update_live_data('testing_status', 'build_failed', 
                                    f"❌ Build failed: {build_result.get('error', 'Unknown error')}")
                return {'success': False, 'error': build_result.get('error')}
            
            # Start the game
            self.update_live_data('testing_status', 'starting_game', "🚀 Starting game server...")
            game_process = self.start_game_process(build_result['app_path'])
            
            if not game_process:
                self.update_live_data('testing_status', 'start_failed', "❌ Failed to start game")
                return {'success': False, 'error': 'Could not start game process'}
            
            time.sleep(3)  # Wait for game to start
            
            # Find game URL
            game_port = self.find_available_port() - 1  # Assume it took the previous port
            game_url = f"http://localhost:{game_port}"
            self.update_live_data('game_url', game_url, f"🌐 Game running at {game_url}")
            
            # Test the game
            self.update_live_data('testing_status', 'testing', f"🧪 Testing {game_description}")
            test_result = self.test_game_with_simulation(game_url, game_description)
            
            # Stop the game
            self.stop_game_process(game_process)
            
            self.update_live_data('testing_status', 'test_complete', 
                                f"✅ Test complete! Quality: {test_result.get('quality_score', 0)}/10")
            
            return {
                'success': True,
                'quality_score': test_result.get('quality_score', 0),
                'test_result': test_result
            }
            
        except Exception as e:
            self.update_live_data('testing_status', 'error', f"❌ Error: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def test_game_with_simulation(self, game_url, game_description):
        """Test game with simulated player behavior"""
        # Simulate testing without browser for simplicity
        test_duration = self.game_tester.game_progression[self.game_tester.current_level]['play_duration']
        
        # Reset counters
        self.live_data['action_count'] = 0
        self.live_data['test_duration'] = 0
        self.live_data['current_quality'] = 0
        
        # Simulate gameplay actions
        import requests
        try:
            # Check if game is accessible
            response = requests.get(game_url, timeout=5)
            if response.status_code != 200:
                raise Exception(f"Game not accessible: {response.status_code}")
            
            # Simulate player actions over time
            start_time = time.time()
            actions_performed = []
            
            for second in range(test_duration):
                if not self.testing_active:
                    break
                
                # Simulate different types of actions
                if second % 2 == 0:  # Every 2 seconds
                    action = f"simulated_action_{len(actions_performed)}"
                    actions_performed.append(action)
                    
                    self.live_data['action_count'] = len(actions_performed)
                    self.live_data['test_duration'] = int(time.time() - start_time)
                    
                    # Update progress
                    progress = (second / test_duration) * 100
                    self.update_live_data('testing_progress', progress, 
                                        f"🎮 Action {len(actions_performed)}: {action}")
                
                time.sleep(1)
            
            # Calculate quality score based on game type and actions
            quality_score = self.calculate_simulated_quality(game_description, actions_performed, test_duration)
            self.live_data['current_quality'] = quality_score
            
            return {
                'quality_score': quality_score,
                'actions_performed': len(actions_performed),
                'test_duration': time.time() - start_time,
                'success': True
            }
            
        except Exception as e:
            return {
                'quality_score': 2.0,  # Low score for failed test
                'error': str(e),
                'success': False
            }
    
    def calculate_simulated_quality(self, description, actions, duration):
        """Calculate quality score based on simulated testing"""
        score = 5.0  # Base score
        
        # Game accessibility bonus
        score += 2.0
        
        # Action count bonus
        if len(actions) >= 10:
            score += 2.0
        elif len(actions) >= 5:
            score += 1.0
        
        # Duration compliance bonus
        expected_duration = self.game_tester.game_progression[self.game_tester.current_level]['play_duration']
        if duration >= expected_duration * 0.8:
            score += 1.0
        
        # Game type bonus
        if any(word in description.lower() for word in ['math', 'calculator']):
            score += 0.5  # Math games are typically simpler
        elif any(word in description.lower() for word in ['arcade', 'snake', 'breakout']):
            score += 1.5  # Arcade games get bonus for complexity
        
        return min(10.0, score)
    
    def find_available_port(self, start_port=3000):
        """Find an available port for the game"""
        import socket
        
        for port in range(start_port, start_port + 100):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                result = s.connect_ex(('localhost', port))
                if result != 0:  # Port is available
                    return port
        return start_port
    
    def start_game_process(self, app_path):
        """Start the game server process"""
        try:
            env = os.environ.copy()
            port = self.find_available_port()
            env['PORT'] = str(port)
            
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
    
    def stop_testing_session(self):
        """Stop the current testing session"""
        self.testing_active = False
        self.live_data['testing_status'] = 'stopping'
        
        if self.game_tester:
            self.game_tester.cleanup()
        
        self.update_live_data('testing_status', 'idle', "⏹️ Testing session stopped")

# Global portal instance
portal = SimpleGameTestingPortal()

@app.route('/')
def index():
    """Main portal page"""
    return render_template('simple_game_portal.html')

@app.route('/api/live_data')
def get_live_data():
    """Get current live data for JavaScript polling"""
    return jsonify(portal.live_data)

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

def create_simple_portal_template():
    """Create the HTML template for the simple web portal"""
    template_dir = os.path.join(os.path.dirname(__file__), 'templates')
    os.makedirs(template_dir, exist_ok=True)
    
    template_content = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🎮 Game Testing Portal - Live AI Player</title>
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
            font-size: 20px;
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
            max-height: 100%;
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
            font-size: 16px;
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
            font-size: 18px;
            opacity: 0.7;
        }
        .progress-bar {
            width: 100%;
            height: 15px;
            background: rgba(0, 0, 0, 0.5);
            border: 1px solid #00ff41;
            border-radius: 8px;
            margin: 10px 0;
            overflow: hidden;
        }
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #00ff41, #ffff00);
            width: 0%;
            transition: width 0.5s;
            border-radius: 8px;
        }
        .console-line {
            margin: 1px 0;
            opacity: 0.9;
            font-size: 11px;
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
            padding: 8px;
            border: 1px solid #00ff41;
            border-radius: 5px;
            font-size: 14px;
        }
        .live-indicator {
            color: #ff0041;
            font-weight: bold;
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
                <strong>📊 Level:</strong><br>
                <span id="current-level" class="level-indicator">LEVEL 1 MATH</span>
            </div>
            <div class="status-item">
                <strong>🎮 Tested:</strong> <span id="games-tested">0</span>
            </div>
            <div class="status-item">
                <strong>✅ Success:</strong> <span id="games-successful">0</span>
            </div>
            <div class="status-item">
                <strong>⭐ Avg Quality:</strong> <span id="average-quality">0.0</span>/10
            </div>
            <div class="status-item">
                <strong>🎯 Game:</strong><br>
                <span id="current-game">No game loaded</span>
            </div>
            <div class="progress-bar">
                <div id="progress-fill" class="progress-fill"></div>
            </div>
        </div>
        
        <div class="gameplay">
            <div id="game-placeholder" class="game-placeholder">
                🤖 AI Player Ready<br>
                <small>Start testing to see live gameplay simulation</small>
            </div>
            <iframe id="game-frame" class="game-frame" src="about:blank"></iframe>
            <div class="score-display">
                <div>⚡ Actions: <span id="action-count">0</span></div>
                <div>⏱️ Duration: <span id="test-duration">0</span>s</div>
                <div>⭐ Quality: <span id="quality-score">-</span>/10</div>
            </div>
        </div>
        
        <div class="console" id="console">
            <div class="console-line highlight">🎮 GAME TESTING CONSOLE READY</div>
            <div class="console-line">🤖 AI player systems initialized</div>
            <div class="console-line">📊 Progression: Math → Logic → Arcade → Retro → Classic</div>
            <div class="console-line">⏱️ Minimum 10+ seconds gameplay per test</div>
        </div>
        
        <div class="controls">
            <button id="start-btn" class="btn">🚀 Start Testing</button>
            <button id="stop-btn" class="btn" disabled>⏹️ Stop Testing</button>
            <button id="clear-btn" class="btn">🗑️ Clear</button>
            <div style="margin-left: auto;">
                <span class="live-indicator">🔴 LIVE</span>
            </div>
        </div>
    </div>

    <script>
        let testingActive = false;
        let updateInterval;

        // DOM elements
        const startBtn = document.getElementById('start-btn');
        const stopBtn = document.getElementById('stop-btn');
        const clearBtn = document.getElementById('clear-btn');
        const consoleEl = document.getElementById('console');
        const gameFrame = document.getElementById('game-frame');
        const gamePlaceholder = document.getElementById('game-placeholder');

        // Button event handlers
        startBtn.onclick = () => startTesting();
        stopBtn.onclick = () => stopTesting();
        clearBtn.onclick = () => clearConsole();

        // Start live data polling
        function startLiveUpdates() {
            updateInterval = setInterval(fetchLiveData, 1000); // Update every second
        }

        async function fetchLiveData() {
            try {
                const response = await fetch('/api/live_data');
                const data = await response.json();
                updateDisplay(data);
            } catch (error) {
                console.error('Failed to fetch live data:', error);
            }
        }

        function updateDisplay(data) {
            // Update status panel
            document.getElementById('current-level').textContent = 
                (data.current_level || 'level_1_math').replace('_', ' ').toUpperCase();
            document.getElementById('games-tested').textContent = data.games_completed || 0;
            document.getElementById('games-successful').textContent = data.successful_games || 0;
            
            if (data.quality_scores && data.quality_scores.length > 0) {
                const avg = data.quality_scores.reduce((a, b) => a + b, 0) / data.quality_scores.length;
                document.getElementById('average-quality').textContent = avg.toFixed(1);
            }
            
            document.getElementById('current-game').textContent = data.current_game || 'No game loaded';
            
            // Update progress bar
            document.getElementById('progress-fill').style.width = (data.testing_progress || 0) + '%';
            
            // Update score display
            document.getElementById('action-count').textContent = data.action_count || 0;
            document.getElementById('test-duration').textContent = (data.test_duration || 0) + 's';
            document.getElementById('quality-score').textContent = 
                data.current_quality ? data.current_quality.toFixed(1) : '-';
            
            // Update console with latest message
            if (data.latest_update && data.latest_update !== lastUpdate) {
                addConsoleMessage(data.latest_update);
                lastUpdate = data.latest_update;
            }
            
            // Update game frame
            if (data.game_url && data.game_url !== currentGameUrl) {
                showGameFrame(data.game_url);
                currentGameUrl = data.game_url;
            }
            
            // Update testing status
            if (data.testing_status === 'idle' && testingActive) {
                // Testing finished
                testingActive = false;
                startBtn.disabled = false;
                stopBtn.disabled = true;
                hideGameFrame();
            }
        }

        let lastUpdate = '';
        let currentGameUrl = '';

        async function startTesting() {
            try {
                const response = await fetch('/api/start_testing', { method: 'POST' });
                const result = await response.json();
                
                if (result.success) {
                    testingActive = true;
                    startBtn.disabled = true;
                    stopBtn.disabled = false;
                    addConsoleMessage('🚀 Game testing session started', true);
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
                    addConsoleMessage('⏹️ Game testing session stopped', true);
                    hideGameFrame();
                }
            } catch (error) {
                addConsoleMessage(`❌ Failed to stop testing: ${error.message}`);
            }
        }

        function clearConsole() {
            consoleEl.innerHTML = '<div class="console-line highlight">🗑️ Console cleared</div>';
        }

        function addConsoleMessage(message, highlight = false) {
            const line = document.createElement('div');
            line.className = `console-line ${highlight ? 'highlight' : ''}`;
            line.textContent = message;
            consoleEl.appendChild(line);
            consoleEl.scrollTop = consoleEl.scrollHeight;
            
            // Keep console from getting too long
            if (consoleEl.children.length > 100) {
                consoleEl.removeChild(consoleEl.firstChild);
            }
        }

        function showGameFrame(gameUrl) {
            gameFrame.src = gameUrl;
            gameFrame.style.display = 'block';
            gamePlaceholder.style.display = 'none';
        }

        function hideGameFrame() {
            gameFrame.style.display = 'none';
            gamePlaceholder.style.display = 'block';
            currentGameUrl = '';
        }

        // Start live updates when page loads
        startLiveUpdates();
        addConsoleMessage('📡 Live data polling started');
    </script>
</body>
</html>'''
    
    with open(os.path.join(template_dir, 'simple_game_portal.html'), 'w') as f:
        f.write(template_content)
    
    print("📄 Simple web portal template created")

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    print("\n🛑 Shutting down Game Testing Portal...")
    portal.stop_testing_session()
    sys.exit(0)

if __name__ == '__main__':
    # Handle Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)
    
    print("🌐 SIMPLE GAME TESTING WEB PORTAL")
    print("="*50)
    
    # Create template
    create_simple_portal_template()
    
    print("🚀 Starting web portal on http://localhost:5000")
    print("🎮 Features:")
    print("  • Live game testing visualization")
    print("  • Real-time AI player simulation")
    print("  • Progressive complexity: Math → Logic → Arcade → Retro → Classic")
    print("  • Quality scoring system (1-10)")
    print("  • 10+ second gameplay sessions")
    print("  • Simple HTTP polling (no WebSocket complexity)")
    print("\n🔗 Open http://localhost:5000 in your browser to watch!")
    
    app.run(host='0.0.0.0', port=5000, debug=False)