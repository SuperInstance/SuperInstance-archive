#!/usr/bin/env python3
"""
Experiment Runner - Iterative testing with note comparison
"""

import json
import subprocess
import time
from datetime import datetime
from pathlib import Path

class ExperimentRunner:
    def __init__(self):
        self.base_path = Path("/home/activeloguser/activelog/FUNCTIONAL_DEMOS")
        self.shared_notes = self.base_path / "shared_notes.json"
        
    def run_all_demos_and_take_notes(self):
        """Run all demos, take notes, compare with others"""
        print("🔬 Running all functional demos and taking notes...")
        
        demo_results = {}
        
        # Test each demo and record results
        for demo_dir in self.base_path.glob("*_demo"):
            demo_name = demo_dir.name
            print(f"\n🧪 Testing {demo_name}...")
            
            # Run demo and capture output
            result = self.run_demo_safely(demo_dir / "simple_demo.py")
            
            # Take notes on what worked/failed
            notes = self.analyze_demo_results(demo_name, result)
            demo_results[demo_name] = notes
            
        # Save notes to shared location
        self.save_shared_notes(demo_results)
        
        # Cross-compare notes between researchers
        self.compare_researcher_notes(demo_results)
        
        return demo_results
        
    def run_demo_safely(self, demo_script):
        """Run demo and capture results safely"""
        try:
            result = subprocess.run(
                ["python", str(demo_script)], 
                capture_output=True, 
                text=True, 
                timeout=30,
                cwd=demo_script.parent
            )
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr,
                "runtime": "< 30s"
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Timeout after 30s", "output": ""}
        except Exception as e:
            return {"success": False, "error": str(e), "output": ""}
            
    def analyze_demo_results(self, demo_name, result):
        """Analyze what worked and what needs improvement"""
        notes = {
            "demo_name": demo_name,
            "timestamp": datetime.now().isoformat(),
            "success": result["success"],
            "observations": [],
            "improvements_needed": [],
            "working_concepts": [],
            "next_iteration_ideas": []
        }
        
        if result["success"]:
            # Analyze successful output for key concepts
            output = result["output"]
            
            if "vestige" in demo_name:
                if "Reborn with memory" in output:
                    notes["working_concepts"].append("Memory preservation across death-rebirth cycles")
                if "cycle" in output.lower():
                    notes["working_concepts"].append("I=k/P optimization cycling")
                notes["next_iteration_ideas"].append("Add performance metrics to measure I=k/P improvement")
                
            elif "holographic" in demo_name:
                if "Perfect reconstruction" in output:
                    notes["working_concepts"].append("Fault-tolerant data reconstruction")
                if "fragments survived" in output:
                    notes["working_concepts"].append("Graceful degradation")
                notes["next_iteration_ideas"].append("Test with more severe damage scenarios")
                
            elif "firefly" in demo_name:
                if "SUCCESS" in output:
                    notes["working_concepts"].append("Democratic resource allocation")
                if "improvement" in output:
                    efficiency_line = [line for line in output.split("\n") if "improvement" in line]
                    if efficiency_line:
                        notes["working_concepts"].append(f"Efficiency gains: {efficiency_line[0]}")
                notes["next_iteration_ideas"].append("Scale to more agents and test efficiency")
                
            notes["observations"].append(f"Demo completed successfully in under 30s")
            
        else:
            notes["observations"].append(f"Demo failed: {result['error']}")
            notes["improvements_needed"].append("Fix execution errors before iteration")
            
        return notes
        
    def save_shared_notes(self, demo_results):
        """Save all notes to shared location for cross-comparison"""
        shared_data = {
            "timestamp": datetime.now().isoformat(),
            "experiment_cycle": self.get_current_cycle(),
            "demo_results": demo_results,
            "cross_analysis": self.generate_cross_analysis(demo_results)
        }
        
        with open(self.shared_notes, "w") as f:
            json.dump(shared_data, f, indent=2)
        
        print(f"💾 Shared notes saved: {len(demo_results)} demos analyzed")
        
    def get_current_cycle(self):
        """Get current experiment cycle number"""
        if self.shared_notes.exists():
            with open(self.shared_notes) as f:
                data = json.load(f)
                return data.get("experiment_cycle", 0) + 1
        return 1
        
    def generate_cross_analysis(self, demo_results):
        """Generate cross-analysis comparing all researcher notes"""
        analysis = {
            "successful_demos": [],
            "failed_demos": [],
            "common_patterns": [],
            "integration_opportunities": [],
            "space_efficiency_notes": []
        }
        
        for demo_name, notes in demo_results.items():
            if notes["success"]:
                analysis["successful_demos"].append({
                    "demo": demo_name,
                    "key_concepts": notes["working_concepts"]
                })
            else:
                analysis["failed_demos"].append({
                    "demo": demo_name, 
                    "issues": notes["improvements_needed"]
                })
                
        # Look for integration opportunities
        successful_concepts = []
        for demo in analysis["successful_demos"]:
            successful_concepts.extend(demo["key_concepts"])
            
        if len(analysis["successful_demos"]) >= 2:
            analysis["integration_opportunities"].append(
                f"Can combine {len(analysis['successful_demos'])} working demos"
            )
            
        # Space efficiency analysis
        analysis["space_efficiency_notes"].append(
            f"Total demos: {len(demo_results)}, using minimal disk space"
        )
        
        return analysis
        
    def compare_researcher_notes(self, demo_results):
        """Compare notes between researchers and suggest improvements"""
        print("\n🔍 Cross-comparing researcher notes...")
        
        working_demos = [name for name, notes in demo_results.items() if notes["success"]]
        failed_demos = [name for name, notes in demo_results.items() if not notes["success"]]
        
        print(f"✅ Working demos: {len(working_demos)}")
        print(f"❌ Failed demos: {len(failed_demos)}")
        
        if working_demos:
            print("\n🎯 Integration opportunities:")
            for i, demo1 in enumerate(working_demos):
                for demo2 in working_demos[i+1:]:
                    print(f"  • Combine {demo1} + {demo2}")
                    
        if failed_demos:
            print("\n🔧 Improvements needed:")
            for demo in failed_demos:
                issues = demo_results[demo]["improvements_needed"]
                for issue in issues:
                    print(f"  • {demo}: {issue}")
                    
        # Suggest next iteration improvements
        print("\n🚀 Next iteration suggestions:")
        for demo_name, notes in demo_results.items():
            for idea in notes["next_iteration_ideas"]:
                print(f"  • {demo_name}: {idea}")

if __name__ == "__main__":
    runner = ExperimentRunner()
    results = runner.run_all_demos_and_take_notes()
    
    print(f"\n📊 Experiment complete: {len(results)} demos tested")
    print("📝 Notes saved for researcher comparison")
    print("🔄 Ready for next iteration")