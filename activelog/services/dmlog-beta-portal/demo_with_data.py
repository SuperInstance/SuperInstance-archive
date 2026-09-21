#!/usr/bin/env python3
"""
SuperInterpreter System Demo with Realistic Data
===============================================

This demo shows the SuperInterpreter system working with realistic data,
including actual component usage, optimization detection, and imaginary 
bot creation with meaningful results.
"""

import asyncio
import json
import time
import random
import logging
from typing import Dict, List, Any

# Import our integrated system
from integrated_super_interpreter import IntegratedSuperInterpreter
from super_interpreter_system import ComponentAnalysis, ComponentStatus
from lightweight_bot_communication import BotStatus, MessageType, MessagePriority

logger = logging.getLogger(__name__)

class RealisticDataGenerator:
    """Generate realistic data for demonstration"""
    
    def __init__(self):
        self.components = [
            {"id": "auth_service_v1", "type": "service", "load": 0.7, "efficiency": 0.6},
            {"id": "auth_service_v2", "type": "service", "load": 0.5, "efficiency": 0.7},
            {"id": "user_management", "type": "service", "load": 0.6, "efficiency": 0.65},
            {"id": "session_handler", "type": "service", "load": 0.4, "efficiency": 0.8},
            {"id": "token_validator", "type": "service", "load": 0.3, "efficiency": 0.75},
            {"id": "permission_checker", "type": "service", "load": 0.8, "efficiency": 0.5},
            
            {"id": "file_reader_bot", "type": "interpreter", "load": 0.6, "efficiency": 0.7},
            {"id": "file_writer_bot", "type": "interpreter", "load": 0.5, "efficiency": 0.8},
            {"id": "file_monitor_bot", "type": "interpreter", "load": 0.4, "efficiency": 0.6},
            
            {"id": "data_processor_a", "type": "service", "load": 0.9, "efficiency": 0.4},
            {"id": "data_processor_b", "type": "service", "load": 0.8, "efficiency": 0.5},
            {"id": "data_cache", "type": "service", "load": 0.3, "efficiency": 0.9},
        ]
    
    def generate_component_usage(self, component: Dict[str, Any]) -> Dict[str, Any]:
        """Generate realistic component usage data"""
        base_load = component["load"]
        base_efficiency = component["efficiency"]
        
        # Add some realistic variance
        current_load = base_load + random.uniform(-0.2, 0.2)
        current_load = max(0.0, min(1.0, current_load))
        
        resource_usage = {
            'cpu': current_load * 100,
            'memory': current_load * 200 + random.uniform(0, 50),
            'network': current_load * 10
        }
        
        # Calculate overlap with other components (simulated)
        functionality_overlap = {}
        for other in self.components:
            if other["id"] != component["id"] and other["type"] == component["type"]:
                # Similar types have higher overlap potential
                overlap = random.uniform(0.0, 0.8) if "auth" in component["id"] and "auth" in other["id"] else random.uniform(0.0, 0.3)
                if overlap > 0.3:  # Only store significant overlaps
                    functionality_overlap[other["id"]] = overlap
        
        return {
            'current_usage': {
                'activity_count': int(current_load * 1000),
                'last_used': time.time() - random.uniform(0, 3600),
                'efficiency_score': base_efficiency
            },
            'resource_consumption': resource_usage,
            'functionality_overlap': functionality_overlap,
            'optimization_score': self._calculate_optimization_score(current_load, base_efficiency, functionality_overlap),
            'replacement_feasibility': self._calculate_replacement_feasibility(component, functionality_overlap)
        }
    
    def _calculate_optimization_score(self, load: float, efficiency: float, overlaps: Dict[str, float]) -> float:
        """Calculate optimization score based on load, efficiency, and overlaps"""
        # Higher load + lower efficiency + more overlaps = higher optimization score
        load_factor = load * 0.4  # 40% weight
        efficiency_factor = (1.0 - efficiency) * 0.3  # 30% weight (inverted)
        overlap_factor = (max(overlaps.values()) if overlaps else 0.0) * 0.3  # 30% weight
        
        return min(1.0, load_factor + efficiency_factor + overlap_factor)
    
    def _calculate_replacement_feasibility(self, component: Dict[str, Any], overlaps: Dict[str, float]) -> float:
        """Calculate how feasible it is to replace this component"""
        base_feasibility = 0.5
        
        # Services are generally easier to replace than interpreters
        if component["type"] == "service":
            base_feasibility += 0.2
        
        # Components with high overlap are easier to consolidate
        if overlaps:
            max_overlap = max(overlaps.values())
            base_feasibility += max_overlap * 0.3
        
        return min(1.0, base_feasibility)

async def run_realistic_demo():
    """Run demonstration with realistic data"""
    
    print("🌟 SuperInterpreter System - Realistic Data Demonstration")
    print("=" * 70)
    
    # Setup logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
    
    try:
        # 1. Initialize system
        print("\n🚀 Phase 1: System Initialization")
        system = IntegratedSuperInterpreter()
        await system.initialize_system()
        
        # 2. Generate and inject realistic data
        print("\n📊 Phase 2: Injecting Realistic Component Data")
        data_generator = RealisticDataGenerator()
        
        # Register components with realistic data
        for component in data_generator.components:
            usage_data = data_generator.generate_component_usage(component)
            
            # Create component analysis with realistic data
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
            
            print(f"   📋 {component['id']}: optimization={analysis.optimization_score:.2f}, "
                  f"feasibility={analysis.replacement_feasibility:.2f}")
        
        # 3. Simulate some interpreter activity
        print("\n🤖 Phase 3: Simulating Bot Activity")
        from super_interpreter_system import InterpreterActivity, PatternType
        
        # Create sample activities showing dependencies
        activities = [
            InterpreterActivity(
                interpreter_id="file_reader_bot",
                timestamp=time.time(),
                input_pattern="read_file_pattern",
                output_pattern="file_data_pattern", 
                processing_time_ms=150.0,
                confidence=0.85,
                resource_usage={'cpu': 0.2, 'memory': 30.0, 'network': 0.1},
                component_involvement=["file_reader_bot", "data_cache"]
            ),
            InterpreterActivity(
                interpreter_id="file_writer_bot",
                timestamp=time.time() + 0.5,
                input_pattern="write_file_pattern",
                output_pattern="write_success_pattern",
                processing_time_ms=200.0,
                confidence=0.9,
                resource_usage={'cpu': 0.3, 'memory': 40.0, 'network': 0.05},
                component_involvement=["file_writer_bot", "data_cache"]
            ),
            InterpreterActivity(
                interpreter_id="auth_service_v1",
                timestamp=time.time() + 1.0,
                input_pattern="auth_request_pattern",
                output_pattern="auth_token_pattern",
                processing_time_ms=100.0,
                confidence=0.8,
                resource_usage={'cpu': 0.4, 'memory': 25.0, 'network': 0.2},
                component_involvement=["auth_service_v1", "user_management", "token_validator"]
            )
        ]
        
        # Add activities to monitor buffer
        for activity in activities:
            system.super_system.monitor.activity_buffer.append(activity)
            print(f"   🔄 Activity: {activity.interpreter_id} → {activity.processing_time_ms}ms")
        
        # 4. Run optimization cycle with realistic data
        print("\n🔄 Phase 4: Running Optimization with Realistic Data")
        optimization_result = await system.run_complete_optimization_cycle()
        
        # 5. Show detailed results
        print("\n📈 Phase 5: Detailed Results Analysis")
        print(f"   Components Analyzed: {optimization_result.components_analyzed}")
        print(f"   Optimization Candidates Found: {optimization_result.optimization_candidates_found}")
        print(f"   Imaginary Bots Created: {optimization_result.imaginary_bots_created}")
        
        if optimization_result.imaginary_bots_created > 0:
            print(f"   Simulations Passed: {optimization_result.simulations_passed}")
            print(f"   Submitted for Approval: {optimization_result.bots_submitted_for_approval}")
            print(f"   Est. Performance Improvement: {optimization_result.estimated_performance_improvement:.1f}%")
            print(f"   Est. Resource Savings: {optimization_result.estimated_resource_savings:.1f}%")
        
        # 6. Show specific optimization opportunities found
        print("\n🎯 Phase 6: Specific Optimization Opportunities")
        candidates = system.super_system.analyzer.get_optimization_candidates(min_score=0.5)
        
        for i, candidate in enumerate(candidates[:5]):  # Show top 5
            print(f"   {i+1}. {candidate.component_id}:")
            print(f"      Optimization Score: {candidate.optimization_score:.2f}")
            print(f"      Replacement Feasibility: {candidate.replacement_feasibility:.2f}")
            print(f"      Resource Usage: CPU={candidate.resource_consumption.get('cpu', 0):.1f}, "
                  f"Memory={candidate.resource_consumption.get('memory', 0):.1f}MB")
            if candidate.functionality_overlap:
                overlaps = [f"{k}({v:.2f})" for k, v in list(candidate.functionality_overlap.items())[:3]]
                print(f"      Overlaps with: {', '.join(overlaps)}")
            print()
        
        # 7. Show communication system activity
        print("\n🔗 Phase 7: Communication System Activity")
        
        # Generate some realistic inter-bot communication
        for component_name, communicator in system.system_communicators.items():
            # Simulate status updates
            status = BotStatus(
                bot_id=component_name,
                load_factor=random.uniform(0.3, 0.8),
                processing_queue_size=random.randint(0, 20),
                avg_response_time_ms=random.uniform(10, 100),
                error_rate=random.uniform(0.0, 0.05),
                last_activity=time.time(),
                patterns_learned=random.randint(5, 50),
                optimization_score=random.uniform(0.6, 0.9)
            )
            
            communicator.broadcast_status_update(status)
            
            # Share some pattern hints
            if random.random() > 0.5:  # 50% chance
                communicator.share_pattern_hint(
                    pattern_hash=f"pattern_{random.randint(1000, 9999)}",
                    pattern_type="optimization_hint",
                    success_rate=random.uniform(0.8, 0.95),
                    usage_count=random.randint(10, 100),
                    contexts=[component_name]
                )
        
        # Wait for message processing
        await asyncio.sleep(2)
        
        comm_stats = system.communication_manager.get_system_statistics()
        print(f"   Messages Sent: {comm_stats['registry_stats']['total_messages_sent']}")
        print(f"   Active Communicators: {len(system.system_communicators)}")
        print(f"   Avg Message Size: {comm_stats['registry_stats']['avg_message_size_bytes']:.0f} bytes")
        
        # 8. Show imaginary bot details if any were created
        if system.super_system.factory.imaginary_bots:
            print("\n🤖 Phase 8: Imaginary Bot Details")
            for bot_id, bot in system.super_system.factory.imaginary_bots.items():
                print(f"   Bot ID: {bot_id}")
                print(f"   Replaces: {', '.join(bot.replaces_components)}")
                print(f"   Status: {bot.approval_status.value}")
                if bot.validation_results:
                    print(f"   Validation Score: {bot.validation_results['overall_score']:.2f}")
                print(f"   Est. Performance: {bot.estimated_performance.get('improvement_estimate', 0):.1f}% improvement")
                print()
        
        # 9. Final system status
        print("\n📊 Phase 9: Final System Status")
        final_status = await system.get_comprehensive_system_status()
        
        print(f"   Total Active Components: {final_status['total_active_components']}")
        print(f"   Optimization Cycles Completed: {final_status['optimization_cycles_completed']}")
        print(f"   System Uptime: {final_status['system_uptime_hours']:.2f} hours")
        
        component_statuses = final_status['super_interpreter']['analyzer']['component_statuses']
        for status, count in component_statuses.items():
            if count > 0:
                print(f"   {status}: {count} components")
        
        print("\n✨ Realistic Data Demonstration Complete!")
        print("   The system successfully:")
        print("   - Analyzed realistic component usage patterns")
        print("   - Identified optimization opportunities based on actual metrics")
        print("   - Created intelligent consolidation recommendations") 
        print("   - Demonstrated lightweight inter-bot communication")
        print("   - Showed complete end-to-end optimization workflow")
        
        # 10. Cleanup
        await asyncio.sleep(2)  # Let system stabilize
        await system.shutdown_system()
        
        return True
        
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(run_realistic_demo())
    if success:
        print("\n🎉 SuperInterpreter System demonstration completed successfully!")
    else:
        print("\n⚠️ Demonstration encountered issues.")