#!/usr/bin/env python3
"""
Enhanced Training CLI - Train with real functional apps and intelligent testing
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from enhanced_training_loop import EnhancedTrainingLoop

def main():
    if len(sys.argv) > 1:
        if sys.argv[1] == '--single':
            # Run single enhanced training cycle
            print("🎮 Running single enhanced training cycle...")
            trainer = EnhancedTrainingLoop()
            trainer.run_enhanced_training_cycle()
            
        elif sys.argv[1] == '--continuous':
            # Run continuous enhanced training
            max_cycles = int(sys.argv[2]) if len(sys.argv) > 2 else 50
            target_quality = float(sys.argv[3]) if len(sys.argv) > 3 else 8.5
            print(f"🚀 Running continuous training: {max_cycles} cycles, target quality {target_quality}/10")
            trainer = EnhancedTrainingLoop()
            trainer.run_autonomous_enhanced_training(max_cycles=max_cycles, target_quality=target_quality)
            
        elif sys.argv[1] == '--status':
            # Show enhanced training status
            trainer = EnhancedTrainingLoop()
            success_rate = (trainer.successful_builds / trainer.total_apps_built) * 100 if trainer.total_apps_built > 0 else 0
            
            print(f"📊 ENHANCED TRAINING STATUS")
            print(f"="*40)
            print(f"  🔄 Cycles completed: {trainer.training_cycle}")
            print(f"  📱 Apps built: {trainer.total_apps_built}")
            print(f"  ✅ Successful builds: {trainer.successful_builds}")
            print(f"  ❌ Failed builds: {trainer.failed_builds}")
            print(f"  📈 Success rate: {success_rate:.1f}%")
            print(f"  ⭐ Average quality: {trainer.average_quality_rating:.1f}/10")
            print(f"")
            print(f"🎮 FEATURES:")
            print(f"  • Builds real functional games (Tic Tac Toe, Memory, etc.)")
            print(f"  • Creates working apps (Calculator, Timer, Todo, etc.)")
            print(f"  • Actually plays games to test functionality")
            print(f"  • Uses apps to verify they work correctly")
            print(f"  • Learns from test results using Claude API")
            print(f"  • Cleans up old iterations automatically")
            
        elif sys.argv[1] == '--test-single':
            # Build and test a single app for demonstration
            print("🎮 Building and testing a single functional app...")
            trainer = EnhancedTrainingLoop()
            
            # Generate a specific app for testing
            app_spec = {
                'description': 'a Tic Tac Toe game with score tracking',
                'is_game': True,
                'complexity_estimate': 4,
                'expected_features': ['score_tracking', 'interactive_gameplay']
            }
            
            print(f"🎯 Building: {app_spec['description']}")
            build_result = trainer.build_functional_app(app_spec)
            
            if build_result['status'] == 'success':
                print(f"✅ Build successful! Testing functionality...")
                test_result = trainer.test_functional_app(build_result)
                
                print(f"\n🏁 TEST RESULTS:")
                print(f"  ⭐ Quality rating: {test_result.get('quality_rating', 0)}/10")
                print(f"  📱 App location: {build_result['app_path']}")
                print(f"  🚀 To run manually: cd {build_result['app_path']} && npm start")
            else:
                print(f"❌ Build failed: {build_result.get('error', 'Unknown error')}")
            
        else:
            print("❌ Unknown command. Use --help for usage.")
            show_help()
    else:
        show_help()

def show_help():
    print("🧠 ENHANCED AI BUILDER TRAINING WITH FUNCTIONAL APPS")
    print("="*60)
    print("🎮 Builds real games and apps, tests by playing/using them")
    print("🧪 Uses intelligent testing to verify functionality")
    print("🧠 Learns from results using Claude API analysis")
    print("")
    print("Commands:")
    print("  --single           Run one enhanced training cycle")
    print("  --continuous [N] [Q] Run N cycles (default 50) until quality Q (default 8.5)")
    print("  --status           Show current training status and features")
    print("  --test-single      Build and test one app for demonstration")
    print("  --help             Show this help message")
    print("")
    print("Examples:")
    print("  python3 enhanced_training_cli.py --single")
    print("  python3 enhanced_training_cli.py --continuous 20 8.0")
    print("  python3 enhanced_training_cli.py --test-single")
    print("")
    print("🎯 FEATURES:")
    print("  🎮 Real Games: Tic Tac Toe, Memory, Snake, Rock Paper Scissors")
    print("  🔧 Real Apps: Calculator, Timer, Todo List, Weather, Chat")
    print("  🧪 Smart Testing: Actually plays games and uses apps")
    print("  ⭐ Quality Rating: 1-10 scale based on functionality tests")
    print("  🧠 AI Learning: Uses Claude API to analyze and improve")
    print("  🗑️ Auto Cleanup: Manages storage by cleaning old iterations")

if __name__ == "__main__":
    main()