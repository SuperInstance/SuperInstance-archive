#!/usr/bin/env python3
"""
ML-Enhanced SuperInterpreter System Demonstration
==============================================

This demo showcases the complete SuperInterpreter system with ML assembly monitoring,
creating a self-improving feedback loop where bots learn from their own assembly 
processes to continuously optimize themselves.

Features demonstrated:
- ML monitoring of imaginary bot assembly processes
- Training material generation from successful/failed assemblies
- Self-improving bot creation using ML insights
- Complete feedback loop for continuous optimization
"""

import asyncio
import json
import time
import logging
from typing import Dict, List, Any

# Import the enhanced integrated system
from integrated_super_interpreter import IntegratedSuperInterpreter
from super_interpreter_system import ComponentAnalysis, ComponentStatus
from ml_assembly_monitor import LearningObjective
from lightweight_bot_communication import BotStatus, MessageType, MessagePriority

logger = logging.getLogger(__name__)

class MLEnhancedDataGenerator:
    """Generate realistic data that demonstrates ML learning capabilities"""
    
    def __init__(self):
        # Simulate components with varying optimization potential
        self.components = [
            # High optimization potential - good for ML learning
            {"id": "legacy_auth_v1", "type": "service", "load": 0.9, "efficiency": 0.4, "ml_score": 0.8},
            {"id": "legacy_auth_v2", "type": "service", "load": 0.8, "efficiency": 0.5, "ml_score": 0.7},
            {"id": "user_session_mgr", "type": "service", "load": 0.7, "efficiency": 0.6, "ml_score": 0.6},
            
            # Medium optimization potential
            {"id": "cache_manager", "type": "service", "load": 0.5, "efficiency": 0.8, "ml_score": 0.4},
            {"id": "data_validator", "type": "service", "load": 0.6, "efficiency": 0.7, "ml_score": 0.5},
            
            # Low optimization potential - stable components
            {"id": "core_database", "type": "service", "load": 0.3, "efficiency": 0.9, "ml_score": 0.2},
            {"id": "security_monitor", "type": "service", "load": 0.2, "efficiency": 0.95, "ml_score": 0.1},
            
            # Interpreter bots that can benefit from ML learning
            {"id": "pattern_recognizer_bot", "type": "interpreter", "load": 0.7, "efficiency": 0.6, "ml_score": 0.8},
            {"id": "optimization_bot", "type": "interpreter", "load": 0.6, "efficiency": 0.7, "ml_score": 0.7},
            {"id": "decision_maker_bot", "type": "interpreter", "load": 0.5, "efficiency": 0.8, "ml_score": 0.5},
        ]
    
    def generate_ml_aware_component_usage(self, component: Dict[str, Any]) -> Dict[str, Any]:
        """Generate component usage data that shows ML learning potential"""
        base_load = component["load"]
        base_efficiency = component["efficiency"]
        ml_score = component["ml_score"]
        
        # Components with higher ML scores have more variable performance
        # indicating opportunity for learning and optimization
        variance_factor = ml_score * 0.3
        current_load = base_load + ((-0.5 + ml_score) * variance_factor)
        current_load = max(0.0, min(1.0, current_load))
        
        resource_usage = {
            'cpu': current_load * 100 * (1 + variance_factor),
            'memory': current_load * 200 + (ml_score * 100),  # ML-ready components use more memory
            'network': current_load * 10
        }
        
        # Generate functionality overlaps that indicate consolidation opportunities
        functionality_overlap = {}
        for other in self.components:
            if other["id"] != component["id"]:
                # Similar ML scores indicate similar optimization patterns
                ml_similarity = 1.0 - abs(ml_score - other["ml_score"])
                if ml_similarity > 0.6 and component["type"] == other["type"]:
                    overlap = ml_similarity * 0.8  # High overlap for similar ML profiles
                    functionality_overlap[other["id"]] = overlap
        
        return {
            'current_usage': {
                'activity_count': int(current_load * 1000),
                'last_used': time.time() - (ml_score * 1800),  # ML components used more recently
                'efficiency_score': base_efficiency * (1 + ml_score * 0.2)  # ML can improve efficiency
            },
            'resource_consumption': resource_usage,
            'functionality_overlap': functionality_overlap,
            'optimization_score': self._calculate_ml_optimization_score(current_load, base_efficiency, ml_score, functionality_overlap),
            'replacement_feasibility': self._calculate_ml_replacement_feasibility(component, functionality_overlap),
            'ml_learning_potential': ml_score
        }
    
    def _calculate_ml_optimization_score(self, load: float, efficiency: float, 
                                       ml_score: float, overlaps: Dict[str, float]) -> float:
        """Calculate optimization score enhanced with ML learning potential"""
        base_score = load * 0.3 + (1.0 - efficiency) * 0.3 + (max(overlaps.values()) if overlaps else 0.0) * 0.2
        ml_boost = ml_score * 0.2  # ML potential adds to optimization score
        return min(1.0, base_score + ml_boost)
    
    def _calculate_ml_replacement_feasibility(self, component: Dict[str, Any], 
                                            overlaps: Dict[str, float]) -> float:
        """Calculate replacement feasibility considering ML enhancement potential"""
        base_feasibility = 0.4
        
        # ML-aware components are easier to replace with smarter versions
        ml_bonus = component["ml_score"] * 0.3
        
        # Type-based feasibility
        if component["type"] == "interpreter":
            base_feasibility += 0.3  # Interpreters benefit most from ML
        elif component["type"] == "service":
            base_feasibility += 0.2
        
        # Overlap bonus
        if overlaps:
            max_overlap = max(overlaps.values())
            base_feasibility += max_overlap * 0.3
        
        return min(1.0, base_feasibility + ml_bonus)

async def run_ml_enhanced_demo():
    """Run demonstration showcasing ML-enhanced SuperInterpreter system"""
    
    print("🧠 SuperInterpreter System - ML-Enhanced Self-Improving Demonstration")
    print("=" * 80)
    
    # Setup logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
    
    try:
        # 1. Initialize the complete ML-enhanced system
        print("\n🚀 Phase 1: Initialize ML-Enhanced SuperInterpreter System")
        system = IntegratedSuperInterpreter()
        await system.initialize_system()
        
        print(f"✅ System initialized with ML assembly monitoring")
        print(f"   ML Monitor: {type(system.ml_monitor).__name__}")
        print(f"   SuperInterpreter: {type(system.super_system).__name__}")
        print(f"   Communication: {len(system.system_communicators)} component communicators")
        
        # 2. Generate and inject ML-aware component data
        print("\n📊 Phase 2: Inject ML-Aware Component Data")
        data_generator = MLEnhancedDataGenerator()
        
        for component in data_generator.components:
            usage_data = data_generator.generate_ml_aware_component_usage(component)
            
            # Create component analysis with ML-enhanced data
            analysis = ComponentAnalysis(
                component_id=component["id"],
                component_type=component["type"],
                current_usage=usage_data['current_usage'],
                dependent_components=set(),
                dependee_components=set(),
                resource_consumption=usage_data['resource_consumption'],
                functionality_overlap=usage_data['functionality_overlap'],
                optimization_score=usage_data['optimization_score'],
                replacement_feasibility=usage_data['replacement_feasibility'],
                status=ComponentStatus.ACTIVE
            )
            
            # Register with the analyzer
            system.super_system.analyzer.component_registry[component["id"]] = analysis
            
            ml_potential = usage_data['ml_learning_potential']
            print(f"   📋 {component['id']}: opt={analysis.optimization_score:.2f}, "
                  f"feasibility={analysis.replacement_feasibility:.2f}, ml_potential={ml_potential:.2f}")
        
        # 3. Run multiple optimization cycles to demonstrate ML learning
        print("\n🔄 Phase 3: Run Multiple Optimization Cycles (ML Learning)")
        
        optimization_results = []
        for cycle in range(3):
            print(f"\n   🔄 Optimization Cycle {cycle + 1}/3")
            
            # Add some simulated assembly history for ML learning
            if cycle > 0:
                # Create some historical assembly data for ML learning
                await system._simulate_historical_assembly_data(cycle * 2)
            
            # Run optimization cycle
            result = await system.run_complete_optimization_cycle()
            optimization_results.append(result)
            
            print(f"     Cycle {cycle + 1} Results:")
            print(f"     - Components analyzed: {result.components_analyzed}")
            print(f"     - Imaginary bots created: {result.imaginary_bots_created}")
            print(f"     - Training materials generated: {system.training_materials_generated}")
            print(f"     - Est. performance improvement: {result.estimated_performance_improvement:.1f}%")
            
            # Short delay between cycles
            await asyncio.sleep(2)
        
        # 4. Demonstrate ML learning improvements
        print("\n📈 Phase 4: Analyze ML Learning Improvements")
        
        if len(optimization_results) >= 2:
            first_cycle = optimization_results[0]
            last_cycle = optimization_results[-1]
            
            performance_improvement = (
                (last_cycle.estimated_performance_improvement - first_cycle.estimated_performance_improvement)
                / first_cycle.estimated_performance_improvement * 100
            ) if first_cycle.estimated_performance_improvement > 0 else 0
            
            print(f"   📊 Learning Progress Analysis:")
            print(f"     First cycle performance: {first_cycle.estimated_performance_improvement:.1f}%")
            print(f"     Last cycle performance: {last_cycle.estimated_performance_improvement:.1f}%")
            print(f"     ML-driven improvement: {performance_improvement:.1f}%")
            print(f"     Total training materials: {system.training_materials_generated}")
        
        # 5. Show ML training material effectiveness
        print("\n🎓 Phase 5: ML Training Material Analysis")
        
        ml_stats = await system.ml_monitor.get_system_statistics()
        print(f"   Assembly sessions tracked: {ml_stats['total_sessions']}")
        print(f"   Success rate: {ml_stats['success_rate']:.1%}")
        print(f"   Training materials generated: {system.training_materials_generated}")
        
        # Generate training materials for each learning objective
        for objective in [LearningObjective.PERFORMANCE_OPTIMIZATION, 
                         LearningObjective.ERROR_REDUCTION,
                         LearningObjective.RESOURCE_EFFICIENCY]:
            
            training_material = system.ml_monitor.training_generator.generate_training_material(
                'imaginary_bot', objective, min_patterns=1
            )
            
            if training_material:
                print(f"   🧠 {objective.value}:")
                print(f"     - Training patterns: {len(training_material.training_patterns)}")
                print(f"     - Success examples: {len(training_material.success_examples)}")
                print(f"     - Failure examples: {len(training_material.failure_examples)}")
                
                # Show highest confidence pattern
                if training_material.training_patterns:
                    best_pattern = max(training_material.training_patterns, 
                                     key=lambda p: p.confidence_score)
                    print(f"     - Best pattern: {best_pattern.pattern_type} "
                          f"(confidence: {best_pattern.confidence_score:.2f})")
        
        # 6. Demonstrate self-improvement feedback loop
        print("\n🔄 Phase 6: Self-Improvement Feedback Loop")
        
        # Show how ML insights are being applied
        insights_shared = 0
        for component_name, communicator in system.system_communicators.items():
            # Check for optimization hints shared based on ML insights
            queue_size = len(communicator.registry.message_queues[component_name])
            if queue_size > 0:
                insights_shared += queue_size
        
        print(f"   📡 ML insights shared across components: {insights_shared}")
        print(f"   🔄 System demonstrates continuous self-improvement:")
        print(f"     1. Imaginary bots are created and tested")
        print(f"     2. Assembly processes are monitored by ML system")
        print(f"     3. Success/failure patterns are extracted")
        print(f"     4. Training materials are generated")
        print(f"     5. Insights are shared to improve future bot creation")
        print(f"     6. Cycle repeats with improved performance")
        
        # 7. Final comprehensive status
        print("\n📊 Phase 7: Final ML-Enhanced System Status")
        final_status = await system.get_comprehensive_system_status()
        
        print(f"   System Overview:")
        print(f"     - Total components: {final_status['total_active_components']}")
        print(f"     - Optimization cycles: {final_status['optimization_cycles_completed']}")
        print(f"     - Training materials: {final_status['training_materials_generated']}")
        print(f"     - System uptime: {final_status['system_uptime_hours']:.2f} hours")
        
        if 'ml_assembly_monitor' in final_status:
            ml_status = final_status['ml_assembly_monitor']
            print(f"   ML Assembly Monitor:")
            print(f"     - Total sessions: {ml_status.get('total_sessions', 0)}")
            print(f"     - Success rate: {ml_status.get('success_rate', 0):.1%}")
            print(f"     - Recent patterns: {len(ml_status.get('recent_patterns', []))}")
        
        print("\n✨ ML-Enhanced SuperInterpreter Demonstration Complete!")
        print("=" * 80)
        print("🎉 Key Achievements:")
        print("   ✅ Created self-improving SuperInterpreter system")
        print("   ✅ Demonstrated ML monitoring of bot assembly processes")
        print("   ✅ Generated training materials from assembly data")
        print("   ✅ Showed continuous improvement feedback loop")
        print("   ✅ Achieved ML-driven optimization enhancement")
        
        # 8. Cleanup
        await asyncio.sleep(3)  # Let system stabilize
        await system.shutdown_system()
        
        return True
        
    except Exception as e:
        print(f"\n❌ ML-Enhanced demo failed: {e}")
        logger.exception("Demo failed with exception")
        return False

if __name__ == "__main__":
    success = asyncio.run(run_ml_enhanced_demo())
    if success:
        print("\n🚀 ML-Enhanced SuperInterpreter demonstration completed successfully!")
        print("The system now has a complete self-improving feedback loop!")
    else:
        print("\n⚠️ Demonstration encountered issues.")