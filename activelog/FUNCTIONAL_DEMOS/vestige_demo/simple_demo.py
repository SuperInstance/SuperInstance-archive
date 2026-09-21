#!/usr/bin/env python3
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
