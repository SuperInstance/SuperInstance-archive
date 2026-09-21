#!/usr/bin/env python3
"""
GAME PROGRESSION TESTER
Tests games from simple math games to complex Atari/Apple 2 style games
Progressively builds complexity: Math -> Puzzle -> Arcade -> Complex
Uses real player behavior simulation with 10+ seconds of gameplay
"""

import os
import json
import time
import random
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
import threading
import subprocess

class GameProgressionTester:
    def __init__(self):
        self.system_name = "GameProgressionTester"
        self.version = "1.0_game_focused"
        
        # Game progression levels
        self.game_progression = {
            'level_1_math': {
                'complexity': 1,
                'examples': [
                    'simple addition math game',
                    'multiplication tables quiz',
                    'number guessing with hints',
                    'basic calculator with history'
                ],
                'play_duration': 15,  # seconds
                'success_criteria': ['correct_calculations', 'user_feedback', 'score_tracking']
            },
            'level_2_logic': {
                'complexity': 2,
                'examples': [
                    'tic tac toe with AI opponent',
                    'memory matching card game',
                    'rock paper scissors tournament',
                    'simple word puzzle game'
                ],
                'play_duration': 20,
                'success_criteria': ['game_logic', 'win_conditions', 'player_interaction']
            },
            'level_3_arcade': {
                'complexity': 3,
                'examples': [
                    'snake game with scoring',
                    'breakout brick breaker',
                    'simple platformer jump game',
                    'space invaders clone'
                ],
                'play_duration': 30,
                'success_criteria': ['collision_detection', 'game_physics', 'level_progression']
            },
            'level_4_retro': {
                'complexity': 4,
                'examples': [
                    'pac man maze game',
                    'asteroids space shooter',
                    'frogger crossing game',
                    'centipede arcade clone'
                ],
                'play_duration': 45,
                'success_criteria': ['complex_ai', 'multiple_mechanics', 'high_score_system']
            },
            'level_5_classic': {
                'complexity': 5,
                'examples': [
                    'apple 2 style adventure game',
                    'atari combat tank battle',
                    'text adventure with graphics',
                    'strategy game with units'
                ],
                'play_duration': 60,
                'success_criteria': ['multiple_systems', 'save_state', 'complex_interactions']
            }
        }
        
        self.current_level = 'level_1_math'
        self.games_tested = 0
        self.successful_games = 0
        self.testing_session_active = False
        
        # Browser setup
        self.setup_browser()
        
        print("🎮 GAME PROGRESSION TESTER INITIALIZED")
        print(f"📊 Starting at: {self.current_level}")
        print(f"🎯 Target: Progress from math games to Atari/Apple 2 complexity")
    
    def setup_browser(self):
        """Setup browser with game testing optimizations"""
        try:
            chrome_options = Options()
            # Remove headless for visual testing
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1200,800")
            chrome_options.add_argument("--start-maximized")
            
            self.driver = webdriver.Chrome(options=chrome_options)
            print("✅ Game testing browser initialized")
        except Exception as e:
            print(f"❌ Browser setup failed: {e}")
            self.driver = None
    
    def play_math_game(self, game_url, duration=15):
        """Play math-based games with realistic player behavior"""
        print(f"🧮 Playing math game for {duration} seconds...")
        
        gameplay_log = {
            'game_type': 'math',
            'start_time': time.time(),
            'actions': [],
            'scores': [],
            'completed_operations': 0
        }
        
        try:
            self.driver.get(game_url)
            time.sleep(2)
            
            end_time = time.time() + duration
            
            while time.time() < end_time:
                # Look for math input fields
                inputs = self.driver.find_elements(By.TAG_NAME, "input")
                buttons = self.driver.find_elements(By.TAG_NAME, "button")
                
                if inputs:
                    # Type numbers in math inputs
                    for inp in inputs[:2]:  # First 2 inputs
                        if inp.is_displayed() and inp.is_enabled():
                            number = str(random.randint(1, 50))
                            inp.clear()
                            inp.send_keys(number)
                            gameplay_log['actions'].append(f'entered_{number}')
                            time.sleep(0.5)
                
                # Click calculation buttons
                calc_buttons = ['=', 'Calculate', 'Check', 'Submit', 'Go']
                for button in buttons:
                    if any(text in button.text for text in calc_buttons):
                        try:
                            button.click()
                            gameplay_log['actions'].append(f'clicked_{button.text}')
                            gameplay_log['completed_operations'] += 1
                            time.sleep(1)
                            
                            # Check for score updates
                            score_elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'Score') or contains(text(), 'Points')]")
                            for score_elem in score_elements:
                                if score_elem.text:
                                    gameplay_log['scores'].append(score_elem.text)
                            break
                        except Exception as e:
                            continue
                
                # Random delay like human player
                time.sleep(random.uniform(0.5, 2.0))
            
            gameplay_log['duration'] = time.time() - gameplay_log['start_time']
            gameplay_log['success'] = gameplay_log['completed_operations'] > 0
            
            print(f"🧮 Math game session complete: {gameplay_log['completed_operations']} operations")
            return gameplay_log
            
        except Exception as e:
            gameplay_log['error'] = str(e)
            gameplay_log['success'] = False
            return gameplay_log
    
    def play_logic_game(self, game_url, duration=20):
        """Play logic/puzzle games with strategic thinking"""
        print(f"🧩 Playing logic game for {duration} seconds...")
        
        gameplay_log = {
            'game_type': 'logic',
            'start_time': time.time(),
            'actions': [],
            'moves_made': 0,
            'game_state_changes': 0
        }
        
        try:
            self.driver.get(game_url)
            time.sleep(2)
            
            end_time = time.time() + duration
            
            while time.time() < end_time:
                # Tic Tac Toe gameplay
                cells = self.driver.find_elements(By.CLASS_NAME, "cell")
                if len(cells) == 9:  # Tic tac toe board
                    empty_cells = [cell for cell in cells if not cell.text.strip()]
                    if empty_cells:
                        # Choose random empty cell
                        cell = random.choice(empty_cells)
                        cell.click()
                        gameplay_log['actions'].append(f'clicked_cell')
                        gameplay_log['moves_made'] += 1
                        time.sleep(1)
                        
                        # Check game status
                        status_elements = self.driver.find_elements(By.ID, "status")
                        if status_elements and status_elements[0].text:
                            gameplay_log['actions'].append(f'status_{status_elements[0].text}')
                            if 'win' in status_elements[0].text.lower() or 'tie' in status_elements[0].text.lower():
                                # Start new game
                                new_game_buttons = self.driver.find_elements(By.XPATH, "//button[contains(text(), 'New') or contains(text(), 'Reset')]")
                                if new_game_buttons:
                                    new_game_buttons[0].click()
                                    gameplay_log['game_state_changes'] += 1
                
                # Memory game gameplay
                cards = self.driver.find_elements(By.CLASS_NAME, "card")
                if len(cards) >= 8:  # Memory card game
                    unmatched_cards = [card for card in cards if 'matched' not in card.get_attribute('class')]
                    if len(unmatched_cards) >= 2:
                        # Flip two cards
                        for i in range(2):
                            card = random.choice(unmatched_cards)
                            if card not in [c for c in cards if 'flipped' in c.get_attribute('class')]:
                                card.click()
                                gameplay_log['actions'].append(f'flipped_card')
                                gameplay_log['moves_made'] += 1
                                time.sleep(0.8)
                
                # General button clicking for other games
                interactive_buttons = self.driver.find_elements(By.XPATH, "//button[not(contains(@class, 'reset')) and not(contains(@class, 'new'))]")
                if interactive_buttons and random.random() > 0.7:  # 30% chance
                    button = random.choice(interactive_buttons)
                    if button.is_displayed() and button.is_enabled():
                        button.click()
                        gameplay_log['actions'].append(f'clicked_button')
                        time.sleep(0.5)
                
                time.sleep(random.uniform(1.0, 2.5))
            
            gameplay_log['duration'] = time.time() - gameplay_log['start_time']
            gameplay_log['success'] = gameplay_log['moves_made'] > 3
            
            print(f"🧩 Logic game session complete: {gameplay_log['moves_made']} moves made")
            return gameplay_log
            
        except Exception as e:
            gameplay_log['error'] = str(e)
            gameplay_log['success'] = False
            return gameplay_log
    
    def play_arcade_game(self, game_url, duration=30):
        """Play arcade-style games with rapid interactions"""
        print(f"🕹️ Playing arcade game for {duration} seconds...")
        
        gameplay_log = {
            'game_type': 'arcade',
            'start_time': time.time(),
            'actions': [],
            'key_presses': 0,
            'score_changes': []
        }
        
        try:
            self.driver.get(game_url)
            time.sleep(2)
            
            # Focus on game area
            game_area = self.driver.find_element(By.TAG_NAME, "body")
            game_area.click()
            
            end_time = time.time() + duration
            actions = ActionChains(self.driver)
            
            while time.time() < end_time:
                # Simulate arcade game controls
                key_choices = [Keys.ARROW_UP, Keys.ARROW_DOWN, Keys.ARROW_LEFT, Keys.ARROW_RIGHT, Keys.SPACE]
                
                # Rapid key presses like arcade gameplay
                for _ in range(random.randint(1, 3)):
                    key = random.choice(key_choices)
                    actions.send_keys(key).perform()
                    gameplay_log['actions'].append(f'key_{key}')
                    gameplay_log['key_presses'] += 1
                    time.sleep(0.1)
                
                # Check for score updates
                score_elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'Score') or contains(text(), 'Points') or contains(text(), 'Level')]")
                for score_elem in score_elements:
                    if score_elem.text and score_elem.text not in gameplay_log['score_changes']:
                        gameplay_log['score_changes'].append(score_elem.text)
                
                # Occasional mouse clicks for shooting/actions
                if random.random() > 0.8:  # 20% chance
                    actions.click().perform()
                    gameplay_log['actions'].append('mouse_click')
                
                time.sleep(random.uniform(0.2, 0.8))
            
            gameplay_log['duration'] = time.time() - gameplay_log['start_time']
            gameplay_log['success'] = gameplay_log['key_presses'] > 10
            
            print(f"🕹️ Arcade game session complete: {gameplay_log['key_presses']} inputs made")
            return gameplay_log
            
        except Exception as e:
            gameplay_log['error'] = str(e)
            gameplay_log['success'] = False
            return gameplay_log
    
    def comprehensive_game_test(self, game_url, game_description):
        """Comprehensively test a game with appropriate play style"""
        print(f"🎮 Testing game: {game_description}")
        
        # Determine game type and appropriate testing approach
        desc_lower = game_description.lower()
        
        if any(word in desc_lower for word in ['math', 'calculator', 'number', 'add', 'multiply']):
            gameplay_log = self.play_math_game(game_url, self.game_progression[self.current_level]['play_duration'])
        elif any(word in desc_lower for word in ['tic tac toe', 'memory', 'puzzle', 'logic']):
            gameplay_log = self.play_logic_game(game_url, self.game_progression[self.current_level]['play_duration'])
        elif any(word in desc_lower for word in ['snake', 'breakout', 'arcade', 'shooter', 'space']):
            gameplay_log = self.play_arcade_game(game_url, self.game_progression[self.current_level]['play_duration'])
        else:
            # Default to logic game testing
            gameplay_log = self.play_logic_game(game_url, self.game_progression[self.current_level]['play_duration'])
        
        # Evaluate gameplay quality
        quality_score = self.evaluate_gameplay_quality(gameplay_log, game_description)
        
        test_result = {
            'game_description': game_description,
            'game_url': game_url,
            'current_level': self.current_level,
            'gameplay_log': gameplay_log,
            'quality_score': quality_score,
            'test_timestamp': datetime.now().isoformat(),
            'progression_ready': quality_score >= 7.0  # Ready for next level if 7+/10
        }
        
        self.games_tested += 1
        if test_result['progression_ready']:
            self.successful_games += 1
            print(f"✅ Game passed! Quality: {quality_score}/10")
        else:
            print(f"❌ Game needs improvement. Quality: {quality_score}/10")
        
        return test_result
    
    def evaluate_gameplay_quality(self, gameplay_log, description):
        """Evaluate the quality of gameplay experience"""
        score = 0
        
        # Basic functionality (30 points)
        if gameplay_log.get('success', False):
            score += 30
        
        # Interaction quality (25 points)
        actions = len(gameplay_log.get('actions', []))
        if actions > 5:
            score += 25
        elif actions > 2:
            score += 15
        elif actions > 0:
            score += 10
        
        # Game-specific scoring (25 points)
        game_type = gameplay_log.get('game_type', 'unknown')
        if game_type == 'math':
            operations = gameplay_log.get('completed_operations', 0)
            if operations >= 3:
                score += 25
            elif operations >= 1:
                score += 15
        elif game_type == 'logic':
            moves = gameplay_log.get('moves_made', 0)
            if moves >= 5:
                score += 25
            elif moves >= 2:
                score += 15
        elif game_type == 'arcade':
            inputs = gameplay_log.get('key_presses', 0)
            if inputs >= 20:
                score += 25
            elif inputs >= 10:
                score += 15
        
        # Duration compliance (20 points)
        duration = gameplay_log.get('duration', 0)
        expected_duration = self.game_progression[self.current_level]['play_duration']
        if duration >= expected_duration * 0.8:  # At least 80% of expected duration
            score += 20
        elif duration >= expected_duration * 0.5:
            score += 10
        
        return min(10, score / 10)  # Convert to 1-10 scale
    
    def check_progression_readiness(self):
        """Check if ready to progress to next level"""
        if self.games_tested >= 3 and self.successful_games >= 2:  # At least 2/3 games successful
            return True
        return False
    
    def progress_to_next_level(self):
        """Progress to the next complexity level"""
        levels = list(self.game_progression.keys())
        current_index = levels.index(self.current_level)
        
        if current_index < len(levels) - 1:
            self.current_level = levels[current_index + 1]
            self.games_tested = 0
            self.successful_games = 0
            print(f"🆙 PROGRESSED TO {self.current_level}")
            print(f"📊 New complexity level: {self.game_progression[self.current_level]['complexity']}")
            return True
        else:
            print(f"🏆 MAXIMUM LEVEL REACHED: {self.current_level}")
            return False
    
    def get_next_game_suggestion(self):
        """Get suggestion for next game to build and test"""
        level_info = self.game_progression[self.current_level]
        return random.choice(level_info['examples'])
    
    def cleanup(self):
        """Cleanup resources"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass

if __name__ == "__main__":
    tester = GameProgressionTester()
    print("🎮 GAME PROGRESSION TESTER READY")
    print("📈 Progressive complexity: Math → Logic → Arcade → Retro → Classic")
    print("⏱️ Minimum 10+ seconds gameplay per test")
    print("🎯 Human-like player behavior simulation")