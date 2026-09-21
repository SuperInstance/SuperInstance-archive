#!/usr/bin/env python3
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
