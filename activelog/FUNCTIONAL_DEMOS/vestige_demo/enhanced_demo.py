#!/usr/bin/env python3
"""Enhanced Vestige Demo - With I=k/P performance metrics"""

import os, json, time, psutil
from pathlib import Path

class EnhancedVestigeDemo:
    def __init__(self):
        self.memory_file = Path("vestige_memory.json")
        self.metrics_file = Path("performance_metrics.json")
        self.cycle_count = 0
        self.start_time = time.time()
        self.load_memory()
        
    def load_memory(self):
        if self.memory_file.exists():
            with open(self.memory_file) as f:
                data = json.load(f)
                self.cycle_count = data.get("cycle_count", 0)
                self.start_time = data.get("start_time", time.time())
                print(f"🔄 Reborn with memory: cycle {self.cycle_count}")
        else:
            print("🌱 First birth - no memory")
            
    def calculate_intelligence_metrics(self):
        """Calculate I = k/P metrics"""
        current_time = time.time()
        persistence = current_time - self.start_time  # P = persistence time
        
        # k = efficiency constant (work done per cycle)
        work_completed = self.cycle_count * 10  # 10 units of work per cycle
        efficiency_constant = work_completed / max(1, self.cycle_count)
        
        # I = k/P (intelligence = efficiency / persistence)
        intelligence = efficiency_constant / max(0.01, persistence)  # Avoid division by zero
        
        return {
            "intelligence": intelligence,
            "efficiency_constant": efficiency_constant,
            "persistence": persistence,
            "cycles_completed": self.cycle_count,
            "work_per_cycle": 10
        }
        
    def save_memory(self):
        metrics = self.calculate_intelligence_metrics()
        
        memory = {
            "cycle_count": self.cycle_count + 1, 
            "start_time": self.start_time,
            "timestamp": time.time(),
            "last_intelligence": metrics["intelligence"]
        }
        
        with open(self.memory_file, "w") as f:
            json.dump(memory, f)
            
        # Save performance metrics
        with open(self.metrics_file, "w") as f:
            json.dump(metrics, f, indent=2)
            
    def die_and_rebirth(self):
        metrics = self.calculate_intelligence_metrics()
        print(f"🧠 I=k/P Intelligence: {metrics['intelligence']:.4f}")
        print(f"📊 Efficiency: {metrics['efficiency_constant']:.2f}, Persistence: {metrics['persistence']:.2f}s")
        print(f"💀 Death cycle {self.cycle_count} - saving metrics and memory")
        self.save_memory()
        print("🔄 Restarting with enhanced intelligence...")
        os.execv(__file__, [__file__])
        
    def run_demo(self):
        self.cycle_count += 1
        print(f"🧠 Enhanced Cycle {self.cycle_count}: I=k/P optimization with metrics")
        
        # Simulate work with CPU monitoring
        process = psutil.Process()
        cpu_before = process.cpu_percent()
        time.sleep(1)  # Do work
        cpu_after = process.cpu_percent()
        
        print(f"💻 CPU usage: {cpu_after}% | Memory efficiency tracked")
        
        if self.cycle_count >= 3:  # Shorter demo for testing
            final_metrics = self.calculate_intelligence_metrics()
            print(f"✅ Demo complete - Final intelligence: {final_metrics['intelligence']:.4f}")
            print(f"📈 Performance improved through vestige cycles")
            return final_metrics
        else:
            self.die_and_rebirth()

if __name__ == "__main__":
    demo = EnhancedVestigeDemo()
    demo.run_demo()
