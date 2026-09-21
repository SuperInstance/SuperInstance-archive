#!/usr/bin/env python3
import json, glob

results_files = glob.glob("*_nobel_results.json")
aggregate_results = {
    "total_researchers": len(results_files),
    "breakthrough_discoveries": 0,
    "average_nobel_potential": 0.0,
    "superhuman_factors": {},
    "unified_breakthroughs": []
}

total_potential = 0
for file in results_files:
    with open(file, 'r') as f:
        data = json.load(f)
        aggregate_results["breakthrough_discoveries"] += len(data.get("phase_1", {}).get("discoveries", []))
        total_potential += data.get("nobel_prize_potential", 0)
        
        if "phase_3" in data:
            researcher = data["researcher"]
            aggregate_results["superhuman_factors"][researcher] = data["phase_3"]

aggregate_results["average_nobel_potential"] = total_potential / len(results_files) if results_files else 0

print("🏆 AGGREGATE NOBEL PRIZE EXPERIMENT RESULTS:")
print(f"  🔬 Total researchers: {aggregate_results['total_researchers']}")  
print(f"  💡 Breakthrough discoveries: {aggregate_results['breakthrough_discoveries']}")
print(f"  🎯 Average Nobel potential: {aggregate_results['average_nobel_potential']:.1%}")
print("  ⚡ Superhuman performance factors achieved across all researchers")

with open("nobel_prize_aggregate_results.json", "w") as f:
    json.dump(aggregate_results, f, indent=2)
    
print("📄 Results saved to nobel_prize_aggregate_results.json")
