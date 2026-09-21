#!/usr/bin/env python3
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
