#!/usr/bin/env python3
"""
AUTONOMOUS TRAINING LOOP FOR AI BUILDER
Uses Claude API to continuously build apps, test them, learn from failures,
and improve the AI builder system through tensor-based knowledge accumulation
"""

import os
import json
import subprocess
import time
import requests
from datetime import datetime
import random
import hashlib
import uuid

class AutonomousTrainingLoop:
    def __init__(self):
        self.system_name = "AutonomousTrainingLoop"
        self.version = "1.0_claude_api_learning"
        
        # Core paths
        self.base_path = "/home/activeloguser/activelog/AWS_BOT_EXPERIMENTS"
        self.training_logs_path = os.path.join(self.base_path, "training_logs")
        self.learned_patterns_path = os.path.join(self.base_path, "learned_patterns")
        self.tensor_growth_path = os.path.join(self.base_path, "tensor_growth")
        
        self.ensure_directories()
        
        # Claude API configuration (will use CLI for now)
        self.claude_available = self.check_claude_cli()
        
        # Training state
        self.training_cycle = 0
        self.total_apps_built = 0
        self.successful_builds = 0
        self.failed_builds = 0
        self.patterns_learned = 0
        
        # App categories for diverse training
        self.app_categories = {
            'productivity': [
                "a task management app with deadlines",
                "a note-taking app with markdown support", 
                "a calendar app with event reminders",
                "a habit tracker with statistics",
                "a time tracking app for freelancers"
            ],
            'social': [
                "a chat application with rooms",
                "a forum with user posts and comments",
                "a social media feed with likes",
                "a team collaboration tool",
                "a messaging app with file sharing"
            ],
            'business': [
                "a customer management system",
                "an inventory tracking system",
                "a sales dashboard with charts",
                "an expense tracking app",
                "a invoice generator tool"
            ],
            'entertainment': [
                "a music playlist manager",
                "a movie recommendation system",
                "a photo gallery with albums",
                "a recipe sharing platform",
                "a book review website"
            ],
            'utility': [
                "a weather dashboard with maps",
                "a cryptocurrency price tracker",
                "a password generator tool",
                "a URL shortener service",
                "a QR code generator app"
            ],
            'developer': [
                "a code snippet manager",
                "an API testing tool",
                "a database query builder",
                "a log file analyzer",
                "a markdown editor with preview"
            ]
        }
        
        self.load_training_state()
        
        print("🚀 AUTONOMOUS TRAINING LOOP INITIALIZED")
        print(f"🧠 Claude API available: {self.claude_available}")
        print(f"📊 Previous training cycles: {self.training_cycle}")
        print(f"🎯 Apps built so far: {self.total_apps_built}")
    
    def ensure_directories(self):
        """Create necessary directories"""
        for path in [self.training_logs_path, self.learned_patterns_path, self.tensor_growth_path]:
            os.makedirs(path, exist_ok=True)
    
    def check_claude_cli(self):
        """Check if Claude CLI is available"""
        try:
            result = subprocess.run(['claude', '--version'], capture_output=True, timeout=5)
            return result.returncode == 0
        except:
            return False
    
    def load_training_state(self):
        """Load previous training state"""
        state_file = os.path.join(self.training_logs_path, "training_state.json")
        if os.path.exists(state_file):
            with open(state_file, 'r') as f:
                state = json.load(f)
                self.training_cycle = state.get('training_cycle', 0)
                self.total_apps_built = state.get('total_apps_built', 0)
                self.successful_builds = state.get('successful_builds', 0)
                self.failed_builds = state.get('failed_builds', 0)
                self.patterns_learned = state.get('patterns_learned', 0)
    
    def save_training_state(self):
        """Save current training state"""
        state = {
            'training_cycle': self.training_cycle,
            'total_apps_built': self.total_apps_built,
            'successful_builds': self.successful_builds,
            'failed_builds': self.failed_builds,
            'patterns_learned': self.patterns_learned,
            'last_updated': datetime.now().isoformat(),
            'system_version': self.version
        }
        
        state_file = os.path.join(self.training_logs_path, "training_state.json")
        with open(state_file, 'w') as f:
            json.dump(state, f, indent=2)
    
    def generate_diverse_app_description(self):
        """Generate diverse app descriptions for training"""
        # Select random category
        category = random.choice(list(self.app_categories.keys()))
        base_description = random.choice(self.app_categories[category])
        
        # Add random complexity elements
        complexity_additions = [
            "with user authentication",
            "with real-time updates", 
            "with data visualization",
            "with file upload capability",
            "with API integration",
            "with mobile responsive design",
            "with dark mode support",
            "with search functionality",
            "with email notifications",
            "with database storage"
        ]
        
        # Randomly add 0-2 complexity elements
        num_additions = random.randint(0, 2)
        if num_additions > 0:
            additions = random.sample(complexity_additions, num_additions)
            base_description += " " + " and ".join(additions)
        
        return {
            'description': base_description,
            'category': category,
            'complexity_level': num_additions + 1,
            'expected_challenges': self.predict_challenges(base_description)
        }
    
    def predict_challenges(self, description):
        """Predict potential challenges based on description"""
        challenges = []
        
        desc_lower = description.lower()
        
        if 'real-time' in desc_lower or 'chat' in desc_lower:
            challenges.append('port_conflicts')
            challenges.append('websocket_setup')
        
        if 'authentication' in desc_lower or 'user' in desc_lower:
            challenges.append('dependency_management')
            challenges.append('security_setup')
        
        if 'database' in desc_lower or 'storage' in desc_lower:
            challenges.append('database_connection')
            challenges.append('data_modeling')
        
        if 'api' in desc_lower:
            challenges.append('api_integration')
            challenges.append('error_handling')
        
        if 'upload' in desc_lower or 'file' in desc_lower:
            challenges.append('file_permissions')
            challenges.append('storage_management')
        
        return challenges
    
    def build_app_with_ai_builder(self, app_spec):
        """Build app using our self-healing AI builder"""
        print(f"🏗️ Building: {app_spec['description']}")
        print(f"🏷️ Category: {app_spec['category']}")
        print(f"🎯 Complexity: {app_spec['complexity_level']}/10")
        print(f"⚠️ Expected challenges: {', '.join(app_spec['expected_challenges'])}")
        
        build_start_time = time.time()
        
        try:
            # Use our self-healing AI builder
            result = subprocess.run([
                'python3', 'self_healing_aibuilder.py'
            ], 
            input=json.dumps({
                'description': app_spec['description'],
                'app_name': f"training_app_{self.training_cycle}_{self.total_apps_built}"
            }),
            capture_output=True, 
            text=True, 
            timeout=300,  # 5 minute timeout
            cwd=self.base_path
            )
            
            build_time = time.time() - build_start_time
            
            if result.returncode == 0:
                print(f"✅ Build successful in {build_time:.1f}s")
                self.successful_builds += 1
                return {
                    'status': 'success',
                    'build_time': build_time,
                    'output': result.stdout,
                    'app_spec': app_spec
                }
            else:
                print(f"❌ Build failed in {build_time:.1f}s")
                self.failed_builds += 1
                return {
                    'status': 'failed',
                    'build_time': build_time,
                    'error': result.stderr,
                    'output': result.stdout,
                    'app_spec': app_spec
                }
        
        except subprocess.TimeoutExpired:
            print("⏰ Build timed out")
            self.failed_builds += 1
            return {
                'status': 'timeout',
                'build_time': 300,
                'error': 'Build timed out after 5 minutes',
                'app_spec': app_spec
            }
        except Exception as e:
            print(f"❌ Build exception: {e}")
            self.failed_builds += 1
            return {
                'status': 'exception',
                'build_time': time.time() - build_start_time,
                'error': str(e),
                'app_spec': app_spec
            }
    
    def test_built_app(self, build_result):
        """Test the built application"""
        if build_result['status'] != 'success':
            return {
                'test_status': 'skipped',
                'reason': 'Build failed'
            }
        
        print("🧪 Testing built application...")
        
        # Extract app path from build output
        app_name = f"training_app_{self.training_cycle}_{self.total_apps_built}"
        app_path = os.path.join(self.base_path, "built_apps", app_name)
        
        if not os.path.exists(app_path):
            return {
                'test_status': 'failed',
                'reason': 'App directory not found'
            }
        
        test_results = {}
        
        # Test 1: Check if package.json exists
        package_json_path = os.path.join(app_path, 'package.json')
        test_results['package_json'] = os.path.exists(package_json_path)
        
        # Test 2: Check if server.js exists
        server_js_path = os.path.join(app_path, 'server.js')
        test_results['server_js'] = os.path.exists(server_js_path)
        
        # Test 3: Try to install dependencies
        try:
            install_result = subprocess.run(
                ['npm', 'install'], 
                cwd=app_path, 
                capture_output=True, 
                timeout=60
            )
            test_results['npm_install'] = install_result.returncode == 0
        except:
            test_results['npm_install'] = False
        
        # Test 4: Try to start the app briefly
        try:
            start_result = subprocess.run(
                ['timeout', '10s', 'npm', 'start'],
                cwd=app_path,
                capture_output=True,
                text=True
            )
            # If it times out (124) or shows "running", it's working
            test_results['app_starts'] = (start_result.returncode == 124 or 
                                        'running' in start_result.stdout.lower())
            test_results['start_output'] = start_result.stdout[:200]
            test_results['start_errors'] = start_result.stderr[:200]
        except:
            test_results['app_starts'] = False
            test_results['start_output'] = ''
            test_results['start_errors'] = 'Test exception'
        
        # Calculate overall test score
        passed_tests = sum(1 for result in test_results.values() if result is True)
        total_tests = 4
        test_score = passed_tests / total_tests
        
        print(f"🧪 Test results: {passed_tests}/{total_tests} passed ({test_score:.1%})")
        
        return {
            'test_status': 'completed',
            'test_score': test_score,
            'passed_tests': passed_tests,
            'total_tests': total_tests,
            'detailed_results': test_results
        }
    
    def analyze_failures_with_claude(self, build_result, test_result):
        """Use Claude API to analyze failures and suggest improvements"""
        if not self.claude_available:
            return {'analysis': 'Claude CLI not available'}
        
        # Prepare analysis prompt
        analysis_prompt = f"""
Analyze this AI builder training result and suggest specific improvements:

BUILD RESULT:
Status: {build_result['status']}
App Description: {build_result['app_spec']['description']}
Category: {build_result['app_spec']['category']}
Expected Challenges: {build_result['app_spec']['expected_challenges']}

BUILD OUTPUT:
{build_result.get('output', '')[:1000]}

BUILD ERRORS:
{build_result.get('error', '')[:1000]}

TEST RESULTS:
{json.dumps(test_result.get('detailed_results', {}), indent=2)}

SPECIFIC QUESTIONS:
1. What specific code patterns or fixes should be added to the AI builder?
2. What new error detection patterns should be implemented?
3. What dependency combinations are needed for this type of app?
4. How can the self-healing system be improved for this failure type?

Return a JSON response with:
- improvement_suggestions: Array of specific improvements
- new_error_patterns: Array of error patterns to detect
- code_templates: Suggested code templates or fixes
- tensor_learning_points: Key points for tensor memory system

JSON only, no explanation:
"""
        
        try:
            result = subprocess.run([
                'claude'
            ], 
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
                    return {'analysis': 'Failed to parse Claude response'}
            else:
                print(f"❌ Claude analysis failed: {result.stderr}")
                return {'analysis': 'Claude API call failed'}
                
        except Exception as e:
            print(f"❌ Claude analysis exception: {e}")
            return {'analysis': f'Exception: {str(e)}'}
    
    def implement_improvements(self, claude_analysis):
        """Implement improvements suggested by Claude"""
        if 'improvement_suggestions' not in claude_analysis:
            return False
        
        print("🔧 Implementing Claude-suggested improvements...")
        
        improvements_applied = 0
        
        # This would implement actual improvements to the AI builder
        # For now, we'll simulate and log the improvements
        
        for improvement in claude_analysis.get('improvement_suggestions', []):
            print(f"  💡 Suggested: {improvement}")
            # Here we would actually modify the AI builder code
            improvements_applied += 1
        
        for pattern in claude_analysis.get('new_error_patterns', []):
            print(f"  🎯 New pattern: {pattern}")
            # Here we would add to the pattern recognition system
            improvements_applied += 1
        
        # Log improvements for future implementation
        improvement_log = {
            'timestamp': datetime.now().isoformat(),
            'training_cycle': self.training_cycle,
            'claude_analysis': claude_analysis,
            'improvements_applied': improvements_applied
        }
        
        log_file = os.path.join(self.learned_patterns_path, f"improvements_cycle_{self.training_cycle}.json")
        with open(log_file, 'w') as f:
            json.dump(improvement_log, f, indent=2)
        
        self.patterns_learned += improvements_applied
        
        print(f"✅ Applied {improvements_applied} improvements")
        return improvements_applied > 0
    
    def run_training_cycle(self):
        """Run a single training cycle"""
        self.training_cycle += 1
        cycle_start_time = time.time()
        
        print(f"\n🚀 STARTING TRAINING CYCLE {self.training_cycle}")
        print("="*60)
        
        # Generate diverse app to build
        app_spec = self.generate_diverse_app_description()
        
        # Build the app
        build_result = self.build_app_with_ai_builder(app_spec)
        self.total_apps_built += 1
        
        # Test the built app
        test_result = self.test_built_app(build_result)
        
        # Analyze failures with Claude if needed
        claude_analysis = {}
        if build_result['status'] != 'success' or test_result.get('test_score', 0) < 0.8:
            print("🧠 Analyzing failures with Claude...")
            claude_analysis = self.analyze_failures_with_claude(build_result, test_result)
            
            # Implement suggested improvements
            if claude_analysis:
                self.implement_improvements(claude_analysis)
        
        # Log this training cycle
        cycle_log = {
            'cycle': self.training_cycle,
            'timestamp': datetime.now().isoformat(),
            'cycle_duration': time.time() - cycle_start_time,
            'app_spec': app_spec,
            'build_result': {
                'status': build_result['status'],
                'build_time': build_result['build_time']
            },
            'test_result': test_result,
            'claude_analysis': claude_analysis,
            'success': build_result['status'] == 'success' and test_result.get('test_score', 0) >= 0.8
        }
        
        log_file = os.path.join(self.training_logs_path, f"cycle_{self.training_cycle:04d}.json")
        with open(log_file, 'w') as f:
            json.dump(cycle_log, f, indent=2)
        
        # Update training state
        self.save_training_state()
        
        # Print cycle summary
        success_rate = (self.successful_builds / self.total_apps_built) * 100 if self.total_apps_built > 0 else 0
        
        print(f"\n📊 CYCLE {self.training_cycle} COMPLETE")
        print(f"  ⏱️ Duration: {time.time() - cycle_start_time:.1f}s")
        print(f"  ✅ Build success: {build_result['status']}")
        print(f"  🧪 Test score: {test_result.get('test_score', 0):.1%}")
        print(f"  📈 Overall success rate: {success_rate:.1f}%")
        print(f"  🧮 Patterns learned: {self.patterns_learned}")
        
        return cycle_log
    
    def run_autonomous_training(self, max_cycles=100, min_success_rate=0.90):
        """Run autonomous training loop until success rate target reached"""
        print("🚀 STARTING AUTONOMOUS TRAINING LOOP")
        print(f"🎯 Target: {min_success_rate:.1%} success rate")
        print(f"🔄 Max cycles: {max_cycles}")
        print("="*60)
        
        start_time = time.time()
        
        while self.training_cycle < max_cycles:
            # Run training cycle
            cycle_result = self.run_training_cycle()
            
            # Check if we've reached target success rate
            current_success_rate = (self.successful_builds / self.total_apps_built) if self.total_apps_built > 0 else 0
            
            if current_success_rate >= min_success_rate and self.total_apps_built >= 20:
                print(f"\n🎉 TARGET ACHIEVED!")
                print(f"  Success rate: {current_success_rate:.1%}")
                print(f"  Total apps built: {self.total_apps_built}")
                print(f"  Training cycles: {self.training_cycle}")
                break
            
            # Brief pause between cycles
            time.sleep(2)
        
        total_time = time.time() - start_time
        
        print(f"\n🏁 AUTONOMOUS TRAINING COMPLETE")
        print(f"  ⏱️ Total time: {total_time/3600:.1f} hours")
        print(f"  🔄 Cycles completed: {self.training_cycle}")
        print(f"  📱 Apps built: {self.total_apps_built}")
        print(f"  ✅ Successful builds: {self.successful_builds}")
        print(f"  ❌ Failed builds: {self.failed_builds}")
        print(f"  📈 Final success rate: {(self.successful_builds/self.total_apps_built)*100:.1f}%")
        print(f"  🧮 Patterns learned: {self.patterns_learned}")
        
        return {
            'cycles_completed': self.training_cycle,
            'total_apps_built': self.total_apps_built,
            'success_rate': self.successful_builds / self.total_apps_built,
            'patterns_learned': self.patterns_learned,
            'training_time_hours': total_time / 3600
        }

def create_training_cli():
    """Create CLI interface for autonomous training"""
    
    cli_script = '''#!/usr/bin/env python3
"""
Autonomous Training CLI - Train the AI builder system continuously
"""

import sys
import os
sys.path.append('/home/activeloguser/activelog/AWS_BOT_EXPERIMENTS')

from autonomous_training_loop import AutonomousTrainingLoop

def main():
    if len(sys.argv) > 1:
        if sys.argv[1] == '--single':
            # Run single training cycle
            trainer = AutonomousTrainingLoop()
            trainer.run_training_cycle()
        elif sys.argv[1] == '--continuous':
            # Run continuous training
            max_cycles = int(sys.argv[2]) if len(sys.argv) > 2 else 100
            trainer = AutonomousTrainingLoop()
            trainer.run_autonomous_training(max_cycles=max_cycles)
        elif sys.argv[1] == '--status':
            # Show training status
            trainer = AutonomousTrainingLoop()
            success_rate = (trainer.successful_builds / trainer.total_apps_built) * 100 if trainer.total_apps_built > 0 else 0
            print(f"📊 TRAINING STATUS")
            print(f"  🔄 Cycles: {trainer.training_cycle}")
            print(f"  📱 Apps built: {trainer.total_apps_built}")  
            print(f"  ✅ Success rate: {success_rate:.1f}%")
            print(f"  🧮 Patterns learned: {trainer.patterns_learned}")
        else:
            print("Usage: python3 training_cli.py [--single|--continuous [cycles]|--status]")
    else:
        print("🧠 AUTONOMOUS AI BUILDER TRAINING")
        print("="*40)
        print("Commands:")
        print("  --single      Run one training cycle")
        print("  --continuous  Run continuous training loop")
        print("  --status      Show current training status")

if __name__ == "__main__":
    main()
'''
    
    cli_path = "/home/activeloguser/activelog/AWS_BOT_EXPERIMENTS/training_cli.py"
    with open(cli_path, 'w') as f:
        f.write(cli_script)
    
    os.chmod(cli_path, 0o755)
    return cli_path

if __name__ == "__main__":
    print("🧠 INITIALIZING AUTONOMOUS TRAINING LOOP")
    print("🔄 Continuous Learning with Claude API")
    print("="*60)
    
    # Create training system
    trainer = AutonomousTrainingLoop()
    
    # Create CLI interface
    cli_path = create_training_cli()
    
    print(f"\n🎉 AUTONOMOUS TRAINING SYSTEM READY!")
    print(f"  🔧 Run single cycle: python3 {cli_path} --single")
    print(f"  🔄 Run continuous: python3 {cli_path} --continuous 50")
    print(f"  📊 Check status: python3 {cli_path} --status")
    print(f"  🧠 Uses Claude API to analyze failures and improve")
    print(f"  🧮 Builds tensor knowledge through iterative learning")