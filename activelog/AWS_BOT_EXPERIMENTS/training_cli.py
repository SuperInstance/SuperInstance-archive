#!/usr/bin/env python3
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
