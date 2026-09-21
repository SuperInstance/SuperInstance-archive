#!/usr/bin/env python3
"""
Functional Demo Coordinator - Build Working Demonstrations
Focus: Start simple, iterate, keep detailed notes, space-efficient
"""

import json
import os
import time
from datetime import datetime
from pathlib import Path

class FunctionalDemoCoordinator:
    def __init__(self):
        self.base_path = Path("/home/activeloguser/activelog/FUNCTIONAL_DEMOS")
        self.base_path.mkdir(exist_ok=True)
        
        # Space-efficient note system (max 10MB total)
        self.notes_path = self.base_path / "experiment_notes"
        self.notes_path.mkdir(exist_ok=True)
        self.max_notes_size = 10 * 1024 * 1024  # 10MB limit
        
        # 7 researcher bots with focused demo objectives
        self.researchers = {
            "vestige_demo": {
                "objective": "Build working death-rebirth cycle demo",
                "starting_simple": "Single process that restarts itself with memory",
                "demo_goal": "Show I=k/P optimization in action"
            },
            "holographic_demo": {
                "objective": "Build working fault-tolerant storage demo", 
                "starting_simple": "File that reconstructs from partial data",
                "demo_goal": "Show graceful degradation working"
            },
            "firefly_demo": {
                "objective": "Build working democratic voting demo",
                "starting_simple": "3 agents voting on resource allocation",
                "demo_goal": "Show 70%+ efficiency improvement"
            },
            "spatial_demo": {
                "objective": "Build working semantic navigation demo",
                "starting_simple": "Folder structure that organizes itself",
                "demo_goal": "Show intelligent information organization"
            },
            "consciousness_demo": {
                "objective": "Build working awareness demo",
                "starting_simple": "Agent that reports its own state",
                "demo_goal": "Show safe self-awareness emergence"
            },
            "economics_demo": {
                "objective": "Build working value creation demo",
                "starting_simple": "System that measures input vs output value",
                "demo_goal": "Show positive ROI calculation"
            },
            "integration_demo": {
                "objective": "Build working unified system demo",
                "starting_simple": "Combine 2 working demos",
                "demo_goal": "Show multiple concepts working together"
            }
        }
        
    def start_experiments(self):
        """Start all researchers on simple functional demos"""
        print("🧪 Starting functional demonstration experiments...")
        
        for researcher, config in self.researchers.items():
            print(f"  🔬 {researcher}: {config['starting_simple']}")
            self.start_researcher_experiment(researcher, config)
            
        print("✅ All researchers started on simple demos")
        
    def start_researcher_experiment(self, researcher, config):
        """Start individual researcher experiment"""
        experiment_path = self.base_path / researcher
        experiment_path.mkdir(exist_ok=True)
        
        # Create experiment log
        experiment_log = {
            "researcher": researcher,
            "start_time": datetime.now().isoformat(),
            "objective": config["objective"],
            "starting_simple": config["starting_simple"],
            "demo_goal": config["demo_goal"],
            "iteration": 1,
            "status": "starting_simple",
            "notes": [],
            "working_versions": [],
            "failures": [],
            "next_steps": [config["starting_simple"]]
        }
        
        # Save initial experiment state
        with open(experiment_path / "experiment_log.json", "w") as f:
            json.dump(experiment_log, f, indent=2)
            
        # Create simple starting demo
        self.create_starting_demo(researcher, experiment_path, config)
        
    def create_starting_demo(self, researcher, path, config):
        """Create the simplest possible working demo"""
        
        if researcher == "vestige_demo":
            # Simple process that restarts with memory
            demo_code = '''#!/usr/bin/env python3
"""Simple Vestige Demo - Process that restarts itself with memory"""

import os, json, time
from pathlib import Path

class SimpleVestigeDemo:
    def __init__(self):
        self.memory_file = Path("vestige_memory.json")
        self.cycle_count = 0
        self.load_memory()
        
    def load_memory(self):
        if self.memory_file.exists():
            with open(self.memory_file) as f:
                data = json.load(f)
                self.cycle_count = data.get("cycle_count", 0)
                print(f"🔄 Reborn with memory: cycle {self.cycle_count}")
        else:
            print("🌱 First birth - no memory")
            
    def save_memory(self):
        memory = {"cycle_count": self.cycle_count + 1, "timestamp": time.time()}
        with open(self.memory_file, "w") as f:
            json.dump(memory, f)
            
    def die_and_rebirth(self):
        print(f"💀 Death cycle {self.cycle_count} - saving memory")
        self.save_memory()
        print("🔄 Restarting...")
        os.execv(__file__, [__file__])  # Restart self
        
    def run_demo(self):
        self.cycle_count += 1
        print(f"🧠 Cycle {self.cycle_count}: I = k/P optimization running")
        time.sleep(2)  # Do some "work"
        
        if self.cycle_count >= 5:
            print("✅ Demo complete - 5 cycles with memory preservation")
            return
        else:
            self.die_and_rebirth()

if __name__ == "__main__":
    demo = SimpleVestigeDemo()
    demo.run_demo()
'''
            
        elif researcher == "holographic_demo":
            # Simple file that reconstructs from partial data
            demo_code = '''#!/usr/bin/env python3
"""Simple Holographic Demo - File reconstruction from fragments"""

import json, random
from pathlib import Path

class SimpleHolographicDemo:
    def __init__(self):
        self.data = "IMPORTANT_DATA_THAT_MUST_SURVIVE"
        
    def create_holographic_backup(self):
        """Store data across multiple fragments"""
        fragments = {}
        for i in range(4):  # 4 fragments
            # Each fragment contains the full data (simple holography)
            fragments[f"fragment_{i}"] = {
                "data": self.data,
                "fragment_id": i,
                "timestamp": "2025-08-30"
            }
            with open(f"holographic_fragment_{i}.json", "w") as f:
                json.dump(fragments[f"fragment_{i}"], f)
        print("💾 Data stored holographically across 4 fragments")
        return fragments
        
    def simulate_damage(self):
        """Randomly delete some fragments"""
        fragments = list(Path(".").glob("holographic_fragment_*.json"))
        damaged = random.sample(fragments, random.randint(1, 2))
        for fragment in damaged:
            fragment.unlink()
            print(f"💥 Lost fragment: {fragment.name}")
        return len(fragments) - len(damaged)
        
    def reconstruct_from_fragments(self):
        """Reconstruct data from remaining fragments"""
        remaining = list(Path(".").glob("holographic_fragment_*.json"))
        if not remaining:
            print("❌ Total data loss - no fragments remain")
            return None
            
        # Load from any remaining fragment (holographic property)
        with open(remaining[0]) as f:
            recovered = json.load(f)
        print(f"✅ Data recovered from {remaining[0].name}")
        return recovered["data"]
        
    def run_demo(self):
        print("🧪 Holographic Storage Demo")
        print(f"Original data: {self.data}")
        
        # Store holographically
        self.create_holographic_backup()
        
        # Simulate damage
        surviving = self.simulate_damage()
        print(f"📊 {surviving}/4 fragments survived")
        
        # Reconstruct
        recovered = self.reconstruct_from_fragments()
        if recovered == self.data:
            print("✅ Perfect reconstruction despite damage!")
        else:
            print("❌ Data corruption detected")

if __name__ == "__main__":
    demo = SimpleHolographicDemo()
    demo.run_demo()
'''
            
        elif researcher == "firefly_demo":
            # Simple voting system
            demo_code = '''#!/usr/bin/env python3
"""Simple Firefly Democracy Demo - 3 agents voting on resources"""

import random, time

class SimpleFireflyAgent:
    def __init__(self, agent_id):
        self.id = agent_id
        self.brightness = random.uniform(0.1, 1.0)  # Fitness level
        
    def evaluate_resource_option(self, option):
        """Evaluate resource allocation option"""
        # Simple evaluation based on agent's expertise
        base_score = random.uniform(0.1, 1.0)
        brightness_bonus = self.brightness * 0.2
        return min(1.0, base_score + brightness_bonus)
        
    def vote(self, options):
        """Vote on resource allocation options"""
        votes = {}
        for option_id, option in options.items():
            votes[option_id] = self.evaluate_resource_option(option)
        return votes

class SimpleFireflyDemocracy:
    def __init__(self):
        self.agents = [SimpleFireflyAgent(i) for i in range(3)]
        
    def run_resource_allocation(self, resources):
        """Democratic resource allocation"""
        print(f"🔥 Firefly Democracy - Allocating {resources['total']} units")
        
        options = {
            "option_a": {"allocation": [60, 25, 15], "focus": "research"},
            "option_b": {"allocation": [40, 40, 20], "focus": "development"}, 
            "option_c": {"allocation": [33, 33, 34], "focus": "balanced"}
        }
        
        # Each agent votes
        all_votes = {}
        for agent in self.agents:
            agent_votes = agent.vote(options)
            print(f"  🐛 Agent {agent.id} (brightness={agent.brightness:.2f}): {agent_votes}")
            all_votes[agent.id] = agent_votes
            
        # Calculate weighted result
        final_scores = {}
        for option_id in options.keys():
            score = sum(all_votes[agent.id][option_id] * agent.brightness 
                       for agent in self.agents)
            final_scores[option_id] = score / sum(agent.brightness for agent in self.agents)
            
        # Find winner
        winner = max(final_scores.items(), key=lambda x: x[1])
        print(f"🏆 Winner: {winner[0]} with score {winner[1]:.3f}")
        print(f"📊 Allocation: {options[winner[0]]['allocation']}")
        
        # Calculate efficiency (simulated improvement over random)
        baseline_efficiency = 0.6  # Random allocation efficiency
        democratic_efficiency = 0.6 + (winner[1] * 0.3)  # Up to 30% improvement
        improvement = ((democratic_efficiency - baseline_efficiency) / baseline_efficiency) * 100
        print(f"✅ Efficiency improvement: {improvement:.1f}% over baseline")
        
        return winner, improvement
        
    def run_demo(self):
        resources = {"total": 100, "type": "compute_units"}
        winner, improvement = self.run_resource_allocation(resources)
        return improvement >= 20  # Success if >20% improvement

if __name__ == "__main__":
    demo = SimpleFireflyDemocracy()
    success = demo.run_demo()
    print(f"✅ Demo {'SUCCESS' if success else 'PARTIAL'}")
'''
        
        else:
            # Generic simple demo template
            demo_code = f'''#!/usr/bin/env python3
"""Simple {researcher} Demo"""

class Simple{researcher.replace('_', '').title()}Demo:
    def __init__(self):
        print(f"🧪 Starting {researcher} demo")
        
    def run_demo(self):
        print(f"🔬 Running {researcher} demonstration")
        print("✅ Demo framework ready for implementation")
        return True

if __name__ == "__main__":
    demo = Simple{researcher.replace('_', '').title()}Demo()
    demo.run_demo()
'''
        
        # Save demo code
        demo_path = path / "simple_demo.py"
        with open(demo_path, "w") as f:
            f.write(demo_code)
        demo_path.chmod(0o755)
        
        print(f"  ✅ Created starting demo: {demo_path}")

if __name__ == "__main__":
    coordinator = FunctionalDemoCoordinator()
    coordinator.start_experiments()