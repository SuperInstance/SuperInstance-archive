#!/usr/bin/env python3
"""
ENHANCED TRAINING LOOP WITH REAL FUNCTIONAL APPS
Builds real functional apps/games, tests them thoroughly, and learns from results
Includes file cleanup system to manage storage
"""

import os
import json
import subprocess
import time
import shutil
from datetime import datetime, timedelta
import random
import hashlib

from functional_app_generator import FunctionalAppGenerator
from intelligent_app_tester import IntelligentAppTester
from self_healing_aibuilder import SelfHealingAIBuilder

class EnhancedTrainingLoop:
    def __init__(self):
        self.system_name = "EnhancedTrainingLoop"
        self.version = "2.0_functional_apps_testing"
        
        # Core paths
        self.base_path = "/home/activeloguser/activelog/AWS_BOT_EXPERIMENTS"
        self.training_logs_path = os.path.join(self.base_path, "training_logs")
        self.built_apps_path = os.path.join(self.base_path, "built_apps")
        self.backup_path = os.path.join(self.base_path, "backup_iterations")
        
        self.ensure_directories()
        
        # Initialize components
        self.app_generator = FunctionalAppGenerator()
        self.app_tester = IntelligentAppTester()
        self.ai_builder = SelfHealingAIBuilder()
        
        # Training state
        self.training_cycle = 0
        self.total_apps_built = 0
        self.successful_builds = 0
        self.failed_builds = 0
        self.average_quality_rating = 0.0
        
        # Load previous training state
        self.load_training_state()
        
        print("🚀 ENHANCED TRAINING LOOP INITIALIZED")
        print(f"🎮 Builds real functional games and apps")
        print(f"🧪 Tests apps by actually playing/using them")
        print(f"🗑️ Automatic cleanup of old iterations")
        print(f"📊 Current cycle: {self.training_cycle}")
        print(f"📱 Apps built: {self.total_apps_built}")
        print(f"⭐ Average quality: {self.average_quality_rating}/10")
    
    def ensure_directories(self):
        """Create necessary directories"""
        for path in [self.training_logs_path, self.built_apps_path, self.backup_path]:
            os.makedirs(path, exist_ok=True)
    
    def load_training_state(self):
        """Load previous training state"""
        state_file = os.path.join(self.training_logs_path, "enhanced_training_state.json")
        if os.path.exists(state_file):
            with open(state_file, 'r') as f:
                state = json.load(f)
                self.training_cycle = state.get('training_cycle', 0)
                self.total_apps_built = state.get('total_apps_built', 0)
                self.successful_builds = state.get('successful_builds', 0)
                self.failed_builds = state.get('failed_builds', 0)
                self.average_quality_rating = state.get('average_quality_rating', 0.0)
    
    def save_training_state(self):
        """Save current training state"""
        state = {
            'training_cycle': self.training_cycle,
            'total_apps_built': self.total_apps_built,
            'successful_builds': self.successful_builds,
            'failed_builds': self.failed_builds,
            'average_quality_rating': self.average_quality_rating,
            'last_updated': datetime.now().isoformat(),
            'system_version': self.version
        }
        
        state_file = os.path.join(self.training_logs_path, "enhanced_training_state.json")
        with open(state_file, 'w') as f:
            json.dump(state, f, indent=2)
    
    def generate_creative_app_description(self):
        """Generate creative and specific app descriptions"""
        # Game categories with specific implementations
        game_types = [
            "a Tic Tac Toe game with score tracking",
            "a memory matching card game with emoji cards",
            "a number guessing game with hints and scoring",
            "a rock paper scissors game with win statistics",
            "a word scramble game with different difficulty levels",
            "a simple Snake game with high scores",
            "a color matching puzzle game",
            "a Simon Says memory game with sounds",
            "a connect four game for two players",
            "a breakout brick breaker game"
        ]
        
        # Functional app categories
        app_types = [
            "a scientific calculator with history",
            "a timer app with multiple alarms",
            "a stopwatch with lap timing",
            "a todo list with priority levels",
            "a weather app with 5-day forecast",
            "a currency converter with live rates",
            "a password generator with options",
            "a QR code generator and reader",
            "a markdown editor with live preview",
            "a color picker tool with palette saving"
        ]
        
        # Combine all types
        all_types = game_types + app_types
        
        # Select random type and add creative elements
        base_description = random.choice(all_types)
        
        # Add random enhancements
        enhancements = [
            "with beautiful animations",
            "with sound effects",
            "with dark mode support", 
            "with mobile responsive design",
            "with keyboard shortcuts",
            "with save/load functionality",
            "with social sharing features",
            "with customizable themes"
        ]
        
        # 50% chance to add enhancement
        if random.random() > 0.5:
            enhancement = random.choice(enhancements)
            base_description += " " + enhancement
        
        return {
            'description': base_description,
            'is_game': any(word in base_description.lower() for word in ['game', 'play', 'puzzle']),
            'complexity_estimate': self.estimate_complexity(base_description),
            'expected_features': self.extract_expected_features(base_description)
        }
    
    def estimate_complexity(self, description):
        """Estimate app complexity (1-10)"""
        complexity = 1
        
        # Base complexity by type
        if any(word in description.lower() for word in ['game', 'play']):
            complexity += 2
        
        # Add complexity for features
        features = ['animation', 'sound', 'save', 'load', 'responsive', 'theme', 'sharing', 'api']
        for feature in features:
            if feature in description.lower():
                complexity += 1
        
        return min(10, complexity)
    
    def extract_expected_features(self, description):
        """Extract expected features from description"""
        features = []
        desc_lower = description.lower()
        
        if 'score' in desc_lower or 'scoring' in desc_lower:
            features.append('score_tracking')
        if 'timer' in desc_lower or 'time' in desc_lower:
            features.append('timing_functionality')
        if 'save' in desc_lower or 'load' in desc_lower:
            features.append('persistence')
        if 'animation' in desc_lower:
            features.append('animations')
        if 'sound' in desc_lower:
            features.append('audio')
        if 'responsive' in desc_lower:
            features.append('mobile_friendly')
        if 'dark mode' in desc_lower:
            features.append('theme_switching')
        
        return features
    
    def build_functional_app(self, app_spec):
        """Build a real functional app using our enhanced system"""
        print(f"🏗️ Building functional app: {app_spec['description']}")
        
        app_name = f"training_app_{self.training_cycle:04d}_{self.total_apps_built:04d}"
        app_path = os.path.join(self.built_apps_path, app_name)
        
        build_start_time = time.time()
        
        try:
            # Use functional app generator to create real working app
            build_result = self.app_generator.identify_app_type_and_generate(
                app_spec['description'], 
                app_path
            )
            
            # Install dependencies
            install_result = subprocess.run(
                ['npm', 'install'],
                cwd=app_path,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            build_time = time.time() - build_start_time
            
            if install_result.returncode == 0:
                print(f"✅ Functional app built successfully in {build_time:.1f}s")
                self.successful_builds += 1
                
                return {
                    'status': 'success',
                    'app_name': app_name,
                    'app_path': app_path,
                    'build_time': build_time,
                    'build_result': build_result,
                    'app_spec': app_spec
                }
            else:
                print(f"❌ Dependency installation failed")
                self.failed_builds += 1
                
                return {
                    'status': 'failed',
                    'app_name': app_name,
                    'app_path': app_path,
                    'build_time': build_time,
                    'error': install_result.stderr,
                    'app_spec': app_spec
                }
            
        except Exception as e:
            build_time = time.time() - build_start_time
            print(f"❌ App build failed: {e}")
            self.failed_builds += 1
            
            return {
                'status': 'exception',
                'app_name': app_name,
                'app_path': app_path,
                'build_time': build_time,
                'error': str(e),
                'app_spec': app_spec
            }
    
    def test_functional_app(self, build_result):
        """Test the functional app by actually using it"""
        if build_result['status'] != 'success':
            return {
                'test_status': 'skipped',
                'reason': 'Build failed',
                'quality_rating': 0
            }
        
        print(f"🧪 Testing functional app: {build_result['app_name']}")
        
        try:
            # Use intelligent app tester to comprehensively test the app
            test_result = self.app_tester.test_app_comprehensively(
                build_result['app_path'],
                build_result['app_spec']['description'],
                port=None
            )
            
            quality_rating = test_result.get('quality_rating', 0)
            
            print(f"🏁 App testing complete")
            print(f"⭐ Quality rating: {quality_rating}/10")
            print(f"✅ Tests passed: {test_result.get('passed_tests', 0)}/{test_result.get('total_tests', 0)}")
            
            return {
                'test_status': 'completed',
                'quality_rating': quality_rating,
                'detailed_results': test_result,
                'recommendation': self.generate_improvement_recommendation(test_result)
            }
            
        except Exception as e:
            print(f"❌ App testing failed: {e}")
            
            return {
                'test_status': 'failed',
                'error': str(e),
                'quality_rating': 0
            }
    
    def generate_improvement_recommendation(self, test_result):
        """Generate recommendations for improvement based on test results"""
        recommendations = []
        
        # Analyze failed tests
        for test in test_result.get('tests_performed', []):
            if not test.get('passed', False):
                test_name = test.get('test_name')
                
                if test_name == 'connectivity':
                    recommendations.append("Fix server startup and port binding issues")
                elif test_name == 'functionality':
                    recommendations.append("Add missing functional elements and interactive features")
                elif test_name == 'interactive':
                    recommendations.append("Improve user interface responsiveness and interactivity")
                elif test_name == 'performance':
                    recommendations.append("Optimize loading times and reduce response sizes")
        
        # Check quality rating
        quality_rating = test_result.get('quality_rating', 0)
        if quality_rating < 7:
            recommendations.append("Overall quality needs improvement - focus on core functionality")
        elif quality_rating < 9:
            recommendations.append("Good functionality, polish user experience and add features")
        
        return recommendations if recommendations else ["App quality is excellent, no major improvements needed"]
    
    def analyze_and_learn_from_results(self, build_result, test_result):
        """Analyze results using Claude API and learn patterns"""
        print("🧠 Analyzing results for learning...")
        
        # Use Claude CLI to analyze the results
        analysis_prompt = f"""
Analyze this training iteration result and provide specific improvements:

APP SPEC:
Description: {build_result['app_spec']['description']}
Expected Features: {build_result['app_spec']['expected_features']}
Complexity: {build_result['app_spec']['complexity_estimate']}/10

BUILD RESULT:
Status: {build_result['status']}
Build Time: {build_result.get('build_time', 0):.2f}s

TEST RESULT:
Quality Rating: {test_result.get('quality_rating', 0)}/10
Tests Passed: {test_result.get('detailed_results', {}).get('passed_tests', 0)}/{test_result.get('detailed_results', {}).get('total_tests', 0)}
Recommendations: {test_result.get('recommendation', [])}

SPECIFIC QUESTIONS:
1. What code improvements would increase the quality rating?
2. What missing features should be added to this app type?
3. How can the AI builder be enhanced for this category of apps?
4. What testing improvements would better evaluate this app type?

Return JSON with:
- code_improvements: Specific code changes needed
- missing_features: Features that should be added  
- builder_enhancements: AI builder system improvements
- testing_enhancements: Better testing methods
- success_probability: Estimated success rate for this app type (0-1)

JSON only:
"""
        
        try:
            result = subprocess.run(
                ['claude'],
                input=analysis_prompt,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                try:
                    analysis = json.loads(result.stdout.strip())
                    print("🧠 Claude analysis completed")
                    return analysis
                except json.JSONDecodeError:
                    print("⚠️ Claude returned non-JSON response")
                    return self.fallback_analysis(build_result, test_result)
            else:
                print("❌ Claude analysis failed")
                return self.fallback_analysis(build_result, test_result)
                
        except Exception as e:
            print(f"❌ Claude analysis exception: {e}")
            return self.fallback_analysis(build_result, test_result)
    
    def fallback_analysis(self, build_result, test_result):
        """Fallback analysis when Claude is not available"""
        quality_rating = test_result.get('quality_rating', 0)
        
        analysis = {
            'code_improvements': [],
            'missing_features': [],
            'builder_enhancements': [],
            'testing_enhancements': [],
            'success_probability': quality_rating / 10
        }
        
        if quality_rating < 5:
            analysis['code_improvements'] = [
                "Fix basic functionality issues",
                "Ensure all interactive elements work",
                "Add proper error handling"
            ]
            analysis['builder_enhancements'] = [
                "Improve basic code generation templates",
                "Add more thorough testing during build"
            ]
        elif quality_rating < 8:
            analysis['code_improvements'] = [
                "Polish user interface",
                "Add visual feedback for user actions",
                "Improve responsive design"
            ]
            analysis['missing_features'] = [
                "Enhanced styling and animations",
                "Better user experience features"
            ]
        
        return analysis
    
    def cleanup_old_iterations(self, keep_last_n=5):
        """Clean up old training iterations, keeping only the last N"""
        print(f"🗑️ Cleaning up old iterations (keeping last {keep_last_n})")
        
        try:
            # Get all training app directories
            app_dirs = []
            if os.path.exists(self.built_apps_path):
                for item in os.listdir(self.built_apps_path):
                    if item.startswith('training_app_') and os.path.isdir(os.path.join(self.built_apps_path, item)):
                        app_dirs.append(item)
            
            # Sort by name (which includes cycle and app numbers)
            app_dirs.sort()
            
            # Keep only the last N, backup and delete the rest
            if len(app_dirs) > keep_last_n:
                to_remove = app_dirs[:-keep_last_n]
                
                for app_dir in to_remove:
                    app_path = os.path.join(self.built_apps_path, app_dir)
                    backup_path = os.path.join(self.backup_path, f"{app_dir}_{int(time.time())}")
                    
                    try:
                        # Create backup
                        shutil.move(app_path, backup_path)
                        print(f"📦 Backed up and moved: {app_dir}")
                    except Exception as e:
                        print(f"⚠️ Failed to backup {app_dir}: {e}")
                        try:
                            # If backup fails, just delete
                            shutil.rmtree(app_path)
                            print(f"🗑️ Deleted: {app_dir}")
                        except Exception as e2:
                            print(f"❌ Failed to delete {app_dir}: {e2}")
            
            # Clean up old training logs (keep last 10 cycles)
            log_files = []
            if os.path.exists(self.training_logs_path):
                for item in os.listdir(self.training_logs_path):
                    if item.startswith('enhanced_cycle_') and item.endswith('.json'):
                        log_files.append(item)
            
            log_files.sort()
            if len(log_files) > 10:
                for log_file in log_files[:-10]:
                    try:
                        os.remove(os.path.join(self.training_logs_path, log_file))
                        print(f"🗑️ Cleaned log: {log_file}")
                    except Exception as e:
                        print(f"⚠️ Failed to clean log {log_file}: {e}")
            
            print(f"✅ Cleanup complete")
            
        except Exception as e:
            print(f"❌ Cleanup failed: {e}")
    
    def run_enhanced_training_cycle(self):
        """Run a single enhanced training cycle"""
        self.training_cycle += 1
        cycle_start_time = time.time()
        
        print(f"\n🚀 ENHANCED TRAINING CYCLE {self.training_cycle}")
        print("="*60)
        
        # Generate creative app specification
        app_spec = self.generate_creative_app_description()
        print(f"🎯 App type: {'🎮 Game' if app_spec['is_game'] else '🔧 App'}")
        print(f"📊 Complexity: {app_spec['complexity_estimate']}/10")
        print(f"🎪 Features: {', '.join(app_spec['expected_features']) if app_spec['expected_features'] else 'Basic'}")
        
        # Build functional app
        build_result = self.build_functional_app(app_spec)
        self.total_apps_built += 1
        
        # Test the functional app
        test_result = self.test_functional_app(build_result)
        
        # Update average quality rating
        quality_rating = test_result.get('quality_rating', 0)
        if self.total_apps_built == 1:
            self.average_quality_rating = quality_rating
        else:
            self.average_quality_rating = (self.average_quality_rating * (self.total_apps_built - 1) + quality_rating) / self.total_apps_built
        
        # Analyze and learn from results
        learning_analysis = self.analyze_and_learn_from_results(build_result, test_result)
        
        # Log this training cycle
        cycle_log = {
            'cycle': self.training_cycle,
            'timestamp': datetime.now().isoformat(),
            'cycle_duration': time.time() - cycle_start_time,
            'app_spec': app_spec,
            'build_result': {
                'status': build_result['status'],
                'build_time': build_result.get('build_time', 0),
                'app_name': build_result.get('app_name'),
                'app_path': build_result.get('app_path')
            },
            'test_result': {
                'test_status': test_result.get('test_status'),
                'quality_rating': quality_rating,
                'tests_passed': test_result.get('detailed_results', {}).get('passed_tests', 0),
                'total_tests': test_result.get('detailed_results', {}).get('total_tests', 0),
                'recommendations': test_result.get('recommendation', [])
            },
            'learning_analysis': learning_analysis,
            'success': build_result['status'] == 'success' and quality_rating >= 7.0
        }
        
        # Save cycle log
        log_file = os.path.join(self.training_logs_path, f"enhanced_cycle_{self.training_cycle:04d}.json")
        with open(log_file, 'w') as f:
            json.dump(cycle_log, f, indent=2)
        
        # Update training state
        self.save_training_state()
        
        # Clean up old iterations every 5 cycles
        if self.training_cycle % 5 == 0:
            self.cleanup_old_iterations(keep_last_n=5)
        
        # Print cycle summary
        success_rate = (self.successful_builds / self.total_apps_built) * 100 if self.total_apps_built > 0 else 0
        
        print(f"\n📊 ENHANCED CYCLE {self.training_cycle} COMPLETE")
        print(f"  ⏱️ Duration: {time.time() - cycle_start_time:.1f}s")
        print(f"  🏗️ Build: {build_result['status']}")
        print(f"  ⭐ Quality: {quality_rating}/10")
        print(f"  📈 Success rate: {success_rate:.1f}%")
        print(f"  🧮 Avg quality: {self.average_quality_rating:.1f}/10")
        print(f"  🎯 Learning insights: {len(learning_analysis.get('code_improvements', []))} improvements identified")
        
        return cycle_log
    
    def run_autonomous_enhanced_training(self, max_cycles=50, target_quality=8.5):
        """Run autonomous enhanced training loop"""
        print("🚀 STARTING AUTONOMOUS ENHANCED TRAINING")
        print(f"🎯 Target: {target_quality}/10 average quality")
        print(f"🔄 Max cycles: {max_cycles}")
        print(f"🎮 Building real functional apps and games")
        print("="*60)
        
        start_time = time.time()
        
        while self.training_cycle < max_cycles:
            # Run training cycle
            cycle_result = self.run_enhanced_training_cycle()
            
            # Check if we've reached target quality
            if self.average_quality_rating >= target_quality and self.total_apps_built >= 10:
                print(f"\n🎉 TARGET QUALITY ACHIEVED!")
                print(f"  Average quality: {self.average_quality_rating:.1f}/10")
                print(f"  Total apps built: {self.total_apps_built}")
                print(f"  Training cycles: {self.training_cycle}")
                break
            
            # Brief pause between cycles
            time.sleep(1)
        
        total_time = time.time() - start_time
        
        print(f"\n🏁 ENHANCED TRAINING COMPLETE")
        print(f"  ⏱️ Total time: {total_time/3600:.1f} hours")
        print(f"  🔄 Cycles: {self.training_cycle}")
        print(f"  📱 Apps built: {self.total_apps_built}")
        print(f"  ✅ Successful: {self.successful_builds}")
        print(f"  ❌ Failed: {self.failed_builds}")
        print(f"  📈 Success rate: {(self.successful_builds/self.total_apps_built)*100:.1f}%")
        print(f"  ⭐ Average quality: {self.average_quality_rating:.1f}/10")
        
        # Final cleanup
        self.app_tester.cleanup()
        
        return {
            'cycles_completed': self.training_cycle,
            'total_apps_built': self.total_apps_built,
            'success_rate': self.successful_builds / self.total_apps_built,
            'average_quality': self.average_quality_rating,
            'training_time_hours': total_time / 3600
        }

if __name__ == "__main__":
    print("🚀 ENHANCED TRAINING LOOP WITH FUNCTIONAL APPS")
    print("🎮 Builds real games and apps, tests by playing them")
    print("🧠 Learns from results using Claude API analysis")
    print("="*60)
    
    trainer = EnhancedTrainingLoop()
    
    print(f"\n🎉 ENHANCED TRAINING SYSTEM READY!")
    print(f"  🎮 Builds functional games: Tic Tac Toe, Memory, Calculator, etc.")
    print(f"  🧪 Tests by actually playing/using the apps")
    print(f"  🧠 Uses Claude API to analyze and learn from results")
    print(f"  🗑️ Automatically cleans up old iterations")
    print(f"  📈 Tracks quality improvements over time")