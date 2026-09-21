"""
Capability Negotiation System
Handles automatic capability detection, negotiation, and resource allocation
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
import json
import math

from core.udp_core import DeviceManifest, DeviceCapability

logger = logging.getLogger(__name__)

@dataclass
class CapabilityRequest:
    """Represents a capability request from an application"""
    request_id: str
    application_id: str
    capabilities: List[str]
    requirements: Dict[str, Any]
    priority: int
    deadline: Optional[datetime]
    qos_requirements: Dict[str, Any]
    
@dataclass
class CapabilityAllocation:
    """Represents an allocated capability"""
    allocation_id: str
    device_id: str
    capability_name: str
    allocated_resources: Dict[str, Any]
    qos_profile: Dict[str, Any]
    start_time: datetime
    estimated_duration: Optional[int]
    actual_performance: Dict[str, float]

@dataclass
class NegotiationResult:
    """Result of capability negotiation"""
    success: bool
    allocations: List[CapabilityAllocation]
    rejected_capabilities: List[str]
    alternative_suggestions: List[Dict[str, Any]]
    estimated_performance: Dict[str, float]
    total_cost: float

class CapabilityNegotiator:
    """Main capability negotiation and allocation system"""
    
    def __init__(self, config, comm_manager):
        self.config = config
        self.comm_manager = comm_manager
        self.capability_matcher = CapabilityMatcher()
        self.resource_allocator = ResourceAllocator()
        self.performance_predictor = PerformancePredictor()
        self.qos_manager = CapabilityQoSManager()
        
        # Active state
        self.pending_requests: Dict[str, CapabilityRequest] = {}
        self.active_allocations: Dict[str, CapabilityAllocation] = {}
        self.device_capabilities: Dict[str, List[DeviceCapability]] = {}
        self.negotiation_history: List[Dict[str, Any]] = []
        
    async def initialize(self):
        """Initialize capability negotiator"""
        logger.info("Initializing Capability Negotiator...")
        
        await self.capability_matcher.initialize()
        await self.resource_allocator.initialize()
        await self.performance_predictor.initialize()
        await self.qos_manager.initialize()
        
        # Start background tasks
        asyncio.create_task(self.optimization_task())
        asyncio.create_task(self.monitoring_task())
        asyncio.create_task(self.rebalancing_task())
        
        logger.info("Capability Negotiator initialized")
    
    async def negotiate_capabilities(self, manifest: DeviceManifest):
        """Handle new device capability negotiation"""
        try:
            device_id = manifest.device_id
            capabilities = manifest.capabilities
            
            # Store device capabilities
            self.device_capabilities[device_id] = capabilities
            
            # Check for pending requests that this device can fulfill
            await self.match_pending_requests(device_id, capabilities)
            
            # Update resource availability
            await self.resource_allocator.update_device_resources(device_id, capabilities)
            
            logger.info(f"Capabilities updated for device: {device_id}")
            
        except Exception as e:
            logger.error(f"Error in capability negotiation: {e}")
    
    async def request_capabilities(self, request: CapabilityRequest) -> NegotiationResult:
        """Process a capability request and negotiate allocation"""
        try:
            request_id = request.request_id
            self.pending_requests[request_id] = request
            
            logger.info(f"Processing capability request: {request_id}")
            
            # Step 1: Find matching devices
            matches = await self.capability_matcher.find_matches(
                request.capabilities, 
                request.requirements
            )
            
            if not matches:
                return NegotiationResult(
                    success=False,
                    allocations=[],
                    rejected_capabilities=request.capabilities,
                    alternative_suggestions=await self.suggest_alternatives(request),
                    estimated_performance={},
                    total_cost=0.0
                )
            
            # Step 2: Check resource availability
            available_resources = await self.resource_allocator.check_availability(
                matches, request.requirements
            )
            
            # Step 3: Predict performance
            performance_estimates = await self.performance_predictor.estimate_performance(
                matches, request.requirements
            )
            
            # Step 4: Negotiate QoS
            qos_profiles = await self.qos_manager.negotiate_qos(
                matches, request.qos_requirements
            )
            
            # Step 5: Make allocation decisions
            allocations = await self.make_allocation_decisions(
                request, matches, available_resources, performance_estimates, qos_profiles
            )
            
            # Step 6: Allocate resources
            successful_allocations = []
            rejected_capabilities = []
            
            for capability_name, allocation_info in allocations.items():
                if await self.allocate_capability(request, capability_name, allocation_info):
                    allocation = CapabilityAllocation(
                        allocation_id=f"{request_id}_{capability_name}",
                        device_id=allocation_info['device_id'],
                        capability_name=capability_name,
                        allocated_resources=allocation_info['resources'],
                        qos_profile=allocation_info['qos_profile'],
                        start_time=datetime.utcnow(),
                        estimated_duration=request.requirements.get('duration'),
                        actual_performance={}
                    )
                    successful_allocations.append(allocation)
                    self.active_allocations[allocation.allocation_id] = allocation
                else:
                    rejected_capabilities.append(capability_name)
            
            # Remove from pending requests if successful
            if successful_allocations:
                del self.pending_requests[request_id]
            
            # Record negotiation
            self.record_negotiation(request, successful_allocations, rejected_capabilities)
            
            result = NegotiationResult(
                success=len(successful_allocations) > 0,
                allocations=successful_allocations,
                rejected_capabilities=rejected_capabilities,
                alternative_suggestions=await self.suggest_alternatives(request) if rejected_capabilities else [],
                estimated_performance=performance_estimates,
                total_cost=self.calculate_allocation_cost(successful_allocations)
            )
            
            logger.info(f"Negotiation complete for {request_id}: {len(successful_allocations)} allocated, {len(rejected_capabilities)} rejected")
            
            return result
            
        except Exception as e:
            logger.error(f"Error in capability negotiation: {e}")
            return NegotiationResult(
                success=False,
                allocations=[],
                rejected_capabilities=request.capabilities,
                alternative_suggestions=[],
                estimated_performance={},
                total_cost=0.0
            )
    
    async def release_capabilities(self, allocation_ids: List[str]) -> bool:
        """Release capability allocations"""
        try:
            success = True
            
            for allocation_id in allocation_ids:
                if allocation_id in self.active_allocations:
                    allocation = self.active_allocations[allocation_id]
                    
                    # Release resources
                    await self.resource_allocator.release_resources(
                        allocation.device_id,
                        allocation.capability_name,
                        allocation.allocated_resources
                    )
                    
                    # Remove QoS profile
                    await self.qos_manager.remove_qos_profile(allocation_id)
                    
                    # Remove allocation
                    del self.active_allocations[allocation_id]
                    
                    logger.info(f"Released allocation: {allocation_id}")
                else:
                    success = False
                    logger.warning(f"Allocation not found: {allocation_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error releasing capabilities: {e}")
            return False
    
    async def get_device_capabilities(self, device_id: str) -> List[DeviceCapability]:
        """Get capabilities for a specific device"""
        return self.device_capabilities.get(device_id, [])
    
    async def match_pending_requests(self, device_id: str, capabilities: List[DeviceCapability]):
        """Check if new device can fulfill pending requests"""
        capability_names = [cap.name for cap in capabilities]
        
        for request_id, request in list(self.pending_requests.items()):
            # Check if any requested capabilities match
            matching_caps = set(request.capabilities).intersection(set(capability_names))
            
            if matching_caps:
                logger.info(f"New device {device_id} can fulfill request {request_id}: {matching_caps}")
                # Trigger re-negotiation for this request
                await self.request_capabilities(request)
    
    async def make_allocation_decisions(self, request: CapabilityRequest, 
                                     matches: Dict[str, List[str]],
                                     resources: Dict[str, Dict[str, Any]],
                                     performance: Dict[str, Dict[str, float]],
                                     qos_profiles: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Make intelligent allocation decisions"""
        
        allocations = {}
        
        for capability_name in request.capabilities:
            if capability_name not in matches:
                continue
            
            device_candidates = matches[capability_name]
            
            # Score each device candidate
            best_device = None
            best_score = -1
            best_allocation = None
            
            for device_id in device_candidates:
                if device_id not in resources or device_id not in performance:
                    continue
                
                score = await self.score_device_for_capability(
                    device_id, capability_name, request, 
                    resources[device_id], performance[device_id], qos_profiles.get(device_id, {})
                )
                
                if score > best_score:
                    best_score = score
                    best_device = device_id
                    best_allocation = {
                        'device_id': device_id,
                        'resources': resources[device_id],
                        'qos_profile': qos_profiles.get(device_id, {}),
                        'performance': performance[device_id],
                        'score': score
                    }
            
            if best_allocation:
                allocations[capability_name] = best_allocation
        
        return allocations
    
    async def score_device_for_capability(self, device_id: str, capability_name: str,
                                        request: CapabilityRequest,
                                        resources: Dict[str, Any],
                                        performance: Dict[str, float],
                                        qos_profile: Dict[str, Any]) -> float:
        """Score a device for a specific capability"""
        
        score = 0.0
        
        # Performance score (40%)
        performance_score = performance.get('overall', 0.5)
        score += performance_score * 0.4
        
        # Resource availability score (30%)
        resource_score = min(1.0, resources.get('availability', 0.5))
        score += resource_score * 0.3
        
        # QoS match score (20%)
        qos_score = await self.calculate_qos_match_score(request.qos_requirements, qos_profile)
        score += qos_score * 0.2
        
        # Priority and load balancing (10%)
        current_load = len([a for a in self.active_allocations.values() if a.device_id == device_id])
        max_load = resources.get('max_concurrent', 10)
        load_score = max(0, (max_load - current_load) / max_load)
        score += load_score * 0.1
        
        return score
    
    async def calculate_qos_match_score(self, requirements: Dict[str, Any], 
                                      profile: Dict[str, Any]) -> float:
        """Calculate how well QoS profile matches requirements"""
        if not requirements or not profile:
            return 0.5
        
        total_score = 0.0
        count = 0
        
        for req_key, req_value in requirements.items():
            if req_key in profile:
                profile_value = profile[req_key]
                
                # Different scoring based on requirement type
                if req_key in ['latency', 'response_time']:
                    # Lower is better for latency
                    if profile_value <= req_value:
                        total_score += 1.0
                    else:
                        total_score += max(0, 1 - (profile_value - req_value) / req_value)
                
                elif req_key in ['bandwidth', 'throughput', 'accuracy']:
                    # Higher is better
                    if profile_value >= req_value:
                        total_score += 1.0
                    else:
                        total_score += profile_value / req_value
                
                else:
                    # Generic scoring
                    total_score += 0.5
                
                count += 1
        
        return total_score / count if count > 0 else 0.5
    
    async def allocate_capability(self, request: CapabilityRequest, 
                                capability_name: str, 
                                allocation_info: Dict[str, Any]) -> bool:
        """Actually allocate a capability"""
        try:
            device_id = allocation_info['device_id']
            resources = allocation_info['resources']
            
            # Reserve resources
            success = await self.resource_allocator.reserve_resources(
                device_id, capability_name, resources
            )
            
            if success:
                # Setup QoS profile
                await self.qos_manager.setup_qos_profile(
                    f"{request.request_id}_{capability_name}",
                    allocation_info['qos_profile']
                )
            
            return success
            
        except Exception as e:
            logger.error(f"Error allocating capability {capability_name}: {e}")
            return False
    
    async def suggest_alternatives(self, request: CapabilityRequest) -> List[Dict[str, Any]]:
        """Suggest alternative solutions when request cannot be fulfilled"""
        suggestions = []
        
        # Suggest relaxing requirements
        relaxed_reqs = request.requirements.copy()
        for key in ['accuracy', 'resolution', 'quality']:
            if key in relaxed_reqs and isinstance(relaxed_reqs[key], (int, float)):
                relaxed_reqs[key] *= 0.8  # Reduce by 20%
        
        suggestions.append({
            'type': 'relaxed_requirements',
            'description': 'Consider relaxing quality requirements',
            'modified_requirements': relaxed_reqs
        })
        
        # Suggest alternative capabilities
        for capability in request.capabilities:
            alternatives = await self.capability_matcher.find_alternative_capabilities(capability)
            if alternatives:
                suggestions.append({
                    'type': 'alternative_capability',
                    'original': capability,
                    'alternatives': alternatives,
                    'description': f'Alternative capabilities for {capability}'
                })
        
        # Suggest scheduling for later
        suggestions.append({
            'type': 'delayed_execution',
            'description': 'Schedule request for later when resources become available',
            'estimated_wait_time': '5-10 minutes'
        })
        
        return suggestions
    
    def calculate_allocation_cost(self, allocations: List[CapabilityAllocation]) -> float:
        """Calculate total cost of allocations"""
        total_cost = 0.0
        
        for allocation in allocations:
            # Base cost calculation
            base_cost = 1.0  # Base cost per allocation
            
            # Resource usage multiplier
            resources = allocation.allocated_resources
            resource_multiplier = resources.get('cost_multiplier', 1.0)
            
            # Duration multiplier
            duration = allocation.estimated_duration or 60  # Default 1 minute
            duration_multiplier = duration / 60  # Cost per minute
            
            allocation_cost = base_cost * resource_multiplier * duration_multiplier
            total_cost += allocation_cost
        
        return total_cost
    
    def record_negotiation(self, request: CapabilityRequest, 
                          allocations: List[CapabilityAllocation],
                          rejected: List[str]):
        """Record negotiation history for learning"""
        record = {
            'timestamp': datetime.utcnow().isoformat(),
            'request_id': request.request_id,
            'application_id': request.application_id,
            'requested_capabilities': request.capabilities,
            'requirements': request.requirements,
            'allocated_capabilities': [a.capability_name for a in allocations],
            'rejected_capabilities': rejected,
            'success_rate': len(allocations) / len(request.capabilities) if request.capabilities else 0,
            'total_cost': self.calculate_allocation_cost(allocations)
        }
        
        self.negotiation_history.append(record)
        
        # Keep only last 1000 records
        if len(self.negotiation_history) > 1000:
            self.negotiation_history = self.negotiation_history[-1000:]
    
    async def optimization_task(self):
        """Background task for optimization"""
        while True:
            try:
                await asyncio.sleep(300)  # Every 5 minutes
                await self.optimize_allocations()
            except Exception as e:
                logger.error(f"Optimization task error: {e}")
                await asyncio.sleep(60)
    
    async def monitoring_task(self):
        """Background task for monitoring"""
        while True:
            try:
                await asyncio.sleep(60)  # Every minute
                await self.monitor_allocations()
            except Exception as e:
                logger.error(f"Monitoring task error: {e}")
                await asyncio.sleep(60)
    
    async def rebalancing_task(self):
        """Background task for rebalancing"""
        while True:
            try:
                await asyncio.sleep(600)  # Every 10 minutes
                await self.rebalance_allocations()
            except Exception as e:
                logger.error(f"Rebalancing task error: {e}")
                await asyncio.sleep(300)
    
    async def optimize_allocations(self):
        """Optimize current allocations"""
        logger.debug("Optimizing capability allocations...")
        
        # Could implement allocation optimization algorithms here
        # For now, just log current state
        active_count = len(self.active_allocations)
        pending_count = len(self.pending_requests)
        
        logger.debug(f"Allocation status: {active_count} active, {pending_count} pending")
    
    async def monitor_allocations(self):
        """Monitor allocation performance"""
        for allocation_id, allocation in self.active_allocations.items():
            try:
                # Check if allocation is still active
                device_status = await self.comm_manager.get_connection_status(allocation.device_id)
                
                if not device_status.get('connected', False):
                    logger.warning(f"Device disconnected for allocation: {allocation_id}")
                    # Could trigger reallocation here
                
            except Exception as e:
                logger.debug(f"Error monitoring allocation {allocation_id}: {e}")
    
    async def rebalance_allocations(self):
        """Rebalance allocations for optimal performance"""
        logger.debug("Rebalancing capability allocations...")
        
        # Could implement smart rebalancing algorithms here
        # For now, just cleanup expired allocations
        
        current_time = datetime.utcnow()
        expired_allocations = []
        
        for allocation_id, allocation in self.active_allocations.items():
            if allocation.estimated_duration:
                expected_end = allocation.start_time + timedelta(seconds=allocation.estimated_duration)
                if current_time > expected_end:
                    expired_allocations.append(allocation_id)
        
        if expired_allocations:
            await self.release_capabilities(expired_allocations)
            logger.info(f"Released {len(expired_allocations)} expired allocations")

class CapabilityMatcher:
    """Matches capability requests to available devices"""
    
    def __init__(self):
        self.capability_taxonomy = {}
        self.device_capabilities = {}
    
    async def initialize(self):
        """Initialize capability matcher"""
        await self.build_capability_taxonomy()
    
    async def build_capability_taxonomy(self):
        """Build taxonomy of capabilities and their relationships"""
        self.capability_taxonomy = {
            # Input capabilities
            'image_capture': ['camera', 'webcam', 'phone_camera'],
            'video_capture': ['camera', 'webcam', 'video_camera'],
            'audio_capture': ['microphone', 'audio_interface'],
            'motion_detection': ['accelerometer', 'gyroscope', 'motion_sensor'],
            'temperature_sensing': ['temperature_sensor', 'thermocouple'],
            
            # Output capabilities
            'display_output': ['monitor', 'screen', 'projector'],
            'audio_output': ['speaker', 'headphones', 'audio_interface'],
            'print_output': ['printer', '3d_printer', 'plotter'],
            
            # Compute capabilities
            'parallel_processing': ['gpu', 'fpga', 'cluster'],
            'machine_learning': ['gpu', 'tpu', 'neural_processor'],
            'signal_processing': ['dsp', 'fpga', 'asic'],
            
            # Storage capabilities
            'data_storage': ['hdd', 'ssd', 'cloud_storage'],
            'backup_storage': ['tape', 'cloud_backup', 'nas']
        }
    
    async def find_matches(self, requested_capabilities: List[str], 
                          requirements: Dict[str, Any]) -> Dict[str, List[str]]:
        """Find devices that match requested capabilities"""
        matches = {}
        
        for capability in requested_capabilities:
            matches[capability] = await self.find_devices_for_capability(capability, requirements)
        
        return matches
    
    async def find_devices_for_capability(self, capability: str, 
                                        requirements: Dict[str, Any]) -> List[str]:
        """Find devices that provide a specific capability"""
        matching_devices = []
        
        # Direct capability match
        for device_id, device_caps in self.device_capabilities.items():
            for cap in device_caps:
                if cap.name == capability:
                    # Check if device meets requirements
                    if await self.check_requirements_match(cap, requirements):
                        matching_devices.append(device_id)
        
        # Taxonomy-based matching
        if capability in self.capability_taxonomy:
            related_capabilities = self.capability_taxonomy[capability]
            
            for device_id, device_caps in self.device_capabilities.items():
                for cap in device_caps:
                    if cap.category in related_capabilities:
                        if await self.check_requirements_match(cap, requirements):
                            if device_id not in matching_devices:
                                matching_devices.append(device_id)
        
        return matching_devices
    
    async def check_requirements_match(self, capability: DeviceCapability, 
                                     requirements: Dict[str, Any]) -> bool:
        """Check if capability meets requirements"""
        
        for req_key, req_value in requirements.items():
            
            # Check parameters
            if req_key in capability.parameters:
                param_value = capability.parameters[req_key]
                
                # Type-specific comparisons
                if isinstance(req_value, (int, float)) and isinstance(param_value, (int, float)):
                    if param_value < req_value:
                        return False
                elif isinstance(req_value, str) and isinstance(param_value, str):
                    if param_value.lower() != req_value.lower():
                        return False
                elif isinstance(req_value, list) and isinstance(param_value, list):
                    if not any(item in param_value for item in req_value):
                        return False
            
            # Check quality metrics
            elif req_key in capability.quality_metrics:
                metric_value = capability.quality_metrics[req_key]
                
                if isinstance(req_value, (int, float)) and isinstance(metric_value, (int, float)):
                    if metric_value < req_value:
                        return False
        
        return True
    
    async def find_alternative_capabilities(self, capability: str) -> List[str]:
        """Find alternative capabilities"""
        alternatives = []
        
        # Look for capabilities in the same taxonomy group
        for tax_capability, related in self.capability_taxonomy.items():
            if capability in related:
                alternatives.extend([c for c in related if c != capability])
        
        return alternatives
    
    def update_device_capabilities(self, device_id: str, capabilities: List[DeviceCapability]):
        """Update capabilities for a device"""
        self.device_capabilities[device_id] = capabilities

class ResourceAllocator:
    """Manages resource allocation for capabilities"""
    
    def __init__(self):
        self.device_resources = {}
        self.allocated_resources = {}
    
    async def initialize(self):
        """Initialize resource allocator"""
        pass
    
    async def update_device_resources(self, device_id: str, capabilities: List[DeviceCapability]):
        """Update resource information for a device"""
        resources = {
            'capabilities': capabilities,
            'max_concurrent': 5,  # Default max concurrent allocations
            'available': True,
            'performance_rating': 1.0,
            'cost_multiplier': 1.0
        }
        
        # Estimate resources based on capabilities
        for cap in capabilities:
            if cap.bandwidth_requirements:
                resources['bandwidth_requirement'] = cap.bandwidth_requirements
            if cap.power_requirements:
                resources['power_requirement'] = cap.power_requirements
        
        self.device_resources[device_id] = resources
    
    async def check_availability(self, matches: Dict[str, List[str]], 
                               requirements: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Check resource availability for matched devices"""
        availability = {}
        
        for capability, device_ids in matches.items():
            for device_id in device_ids:
                if device_id not in availability:
                    availability[device_id] = await self.get_device_availability(device_id)
        
        return availability
    
    async def get_device_availability(self, device_id: str) -> Dict[str, Any]:
        """Get availability information for a device"""
        if device_id not in self.device_resources:
            return {'availability': 0.0}
        
        resources = self.device_resources[device_id]
        allocated_count = len([a for a in self.allocated_resources.values() if a['device_id'] == device_id])
        max_concurrent = resources.get('max_concurrent', 5)
        
        availability = max(0, (max_concurrent - allocated_count) / max_concurrent)
        
        return {
            'availability': availability,
            'max_concurrent': max_concurrent,
            'current_allocations': allocated_count,
            'performance_rating': resources.get('performance_rating', 1.0),
            'cost_multiplier': resources.get('cost_multiplier', 1.0)
        }
    
    async def reserve_resources(self, device_id: str, capability_name: str, 
                              resources: Dict[str, Any]) -> bool:
        """Reserve resources for a capability"""
        try:
            allocation_key = f"{device_id}_{capability_name}_{datetime.utcnow().timestamp()}"
            
            self.allocated_resources[allocation_key] = {
                'device_id': device_id,
                'capability_name': capability_name,
                'resources': resources,
                'timestamp': datetime.utcnow()
            }
            
            return True
            
        except Exception as e:
            logger.error(f"Error reserving resources: {e}")
            return False
    
    async def release_resources(self, device_id: str, capability_name: str, 
                              resources: Dict[str, Any]) -> bool:
        """Release reserved resources"""
        try:
            # Find and remove matching allocation
            to_remove = []
            for key, allocation in self.allocated_resources.items():
                if (allocation['device_id'] == device_id and 
                    allocation['capability_name'] == capability_name):
                    to_remove.append(key)
            
            for key in to_remove:
                del self.allocated_resources[key]
            
            return True
            
        except Exception as e:
            logger.error(f"Error releasing resources: {e}")
            return False

class PerformancePredictor:
    """Predicts performance for capability allocations"""
    
    def __init__(self):
        self.performance_history = {}
        self.prediction_models = {}
    
    async def initialize(self):
        """Initialize performance predictor"""
        pass
    
    async def estimate_performance(self, matches: Dict[str, List[str]], 
                                 requirements: Dict[str, Any]) -> Dict[str, Dict[str, float]]:
        """Estimate performance for matched devices"""
        estimates = {}
        
        for capability, device_ids in matches.items():
            for device_id in device_ids:
                estimates[device_id] = await self.predict_device_performance(
                    device_id, capability, requirements
                )
        
        return estimates
    
    async def predict_device_performance(self, device_id: str, capability: str, 
                                       requirements: Dict[str, Any]) -> Dict[str, float]:
        """Predict performance for a specific device and capability"""
        
        # Base performance prediction
        base_performance = 0.7  # Default performance score
        
        # Adjust based on historical data if available
        history_key = f"{device_id}_{capability}"
        if history_key in self.performance_history:
            history = self.performance_history[history_key]
            base_performance = sum(history) / len(history)
        
        # Predict specific metrics
        prediction = {
            'overall': base_performance,
            'latency': self.predict_latency(device_id, capability),
            'throughput': self.predict_throughput(device_id, capability),
            'accuracy': self.predict_accuracy(device_id, capability),
            'reliability': self.predict_reliability(device_id, capability)
        }
        
        return prediction
    
    def predict_latency(self, device_id: str, capability: str) -> float:
        """Predict latency in milliseconds"""
        # Simple prediction based on capability type
        base_latency = {
            'camera': 50,
            'sensor': 10,
            'compute': 100,
            'storage': 20
        }
        
        return base_latency.get(capability.split('_')[0], 50)
    
    def predict_throughput(self, device_id: str, capability: str) -> float:
        """Predict throughput (operations per second)"""
        # Simple prediction
        base_throughput = {
            'camera': 30,  # FPS
            'sensor': 1000,  # Samples per second
            'compute': 100,  # Operations per second
            'storage': 1000  # MB/s
        }
        
        return base_throughput.get(capability.split('_')[0], 100)
    
    def predict_accuracy(self, device_id: str, capability: str) -> float:
        """Predict accuracy (0-1)"""
        return 0.95  # Default high accuracy
    
    def predict_reliability(self, device_id: str, capability: str) -> float:
        """Predict reliability (0-1)"""
        return 0.99  # Default high reliability
    
    def update_performance_history(self, device_id: str, capability: str, 
                                 actual_performance: float):
        """Update performance history with actual results"""
        history_key = f"{device_id}_{capability}"
        
        if history_key not in self.performance_history:
            self.performance_history[history_key] = []
        
        self.performance_history[history_key].append(actual_performance)
        
        # Keep only last 100 measurements
        if len(self.performance_history[history_key]) > 100:
            self.performance_history[history_key] = self.performance_history[history_key][-100:]

class CapabilityQoSManager:
    """Manages Quality of Service for capabilities"""
    
    def __init__(self):
        self.qos_profiles = {}
        self.active_profiles = {}
    
    async def initialize(self):
        """Initialize QoS manager"""
        # Define standard QoS profiles
        self.qos_profiles = {
            'real_time': {
                'max_latency': 10,  # ms
                'min_throughput': 1000,  # ops/sec
                'priority': 1,
                'jitter_tolerance': 1  # ms
            },
            'interactive': {
                'max_latency': 100,
                'min_throughput': 100,
                'priority': 2,
                'jitter_tolerance': 10
            },
            'batch': {
                'max_latency': 5000,
                'min_throughput': 10,
                'priority': 3,
                'jitter_tolerance': 1000
            },
            'best_effort': {
                'max_latency': float('inf'),
                'min_throughput': 1,
                'priority': 4,
                'jitter_tolerance': float('inf')
            }
        }
    
    async def negotiate_qos(self, matches: Dict[str, List[str]], 
                          requirements: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Negotiate QoS profiles for matched devices"""
        qos_assignments = {}
        
        # Determine appropriate QoS profile
        profile_name = await self.determine_qos_profile(requirements)
        base_profile = self.qos_profiles.get(profile_name, self.qos_profiles['best_effort'])
        
        for capability, device_ids in matches.items():
            for device_id in device_ids:
                qos_assignments[device_id] = await self.customize_qos_profile(
                    device_id, capability, base_profile, requirements
                )
        
        return qos_assignments
    
    async def determine_qos_profile(self, requirements: Dict[str, Any]) -> str:
        """Determine appropriate QoS profile based on requirements"""
        
        # Check for real-time requirements
        if requirements.get('latency', float('inf')) <= 20:
            return 'real_time'
        
        # Check for interactive requirements
        elif requirements.get('latency', float('inf')) <= 200:
            return 'interactive'
        
        # Check for batch processing
        elif requirements.get('priority', 5) >= 3:
            return 'batch'
        
        else:
            return 'best_effort'
    
    async def customize_qos_profile(self, device_id: str, capability: str,
                                  base_profile: Dict[str, Any],
                                  requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Customize QoS profile for specific device and requirements"""
        
        profile = base_profile.copy()
        
        # Apply requirement-specific customizations
        if 'latency' in requirements:
            profile['max_latency'] = min(profile['max_latency'], requirements['latency'])
        
        if 'throughput' in requirements:
            profile['min_throughput'] = max(profile['min_throughput'], requirements['throughput'])
        
        if 'priority' in requirements:
            profile['priority'] = requirements['priority']
        
        return profile
    
    async def setup_qos_profile(self, allocation_id: str, profile: Dict[str, Any]):
        """Setup QoS profile for an allocation"""
        self.active_profiles[allocation_id] = {
            'profile': profile,
            'created_at': datetime.utcnow(),
            'metrics': {
                'actual_latency': [],
                'actual_throughput': [],
                'violations': 0
            }
        }
    
    async def remove_qos_profile(self, allocation_id: str):
        """Remove QoS profile"""
        if allocation_id in self.active_profiles:
            del self.active_profiles[allocation_id]
    
    async def monitor_qos_compliance(self, allocation_id: str, 
                                   actual_metrics: Dict[str, float]):
        """Monitor QoS compliance"""
        if allocation_id not in self.active_profiles:
            return
        
        profile_info = self.active_profiles[allocation_id]
        profile = profile_info['profile']
        metrics = profile_info['metrics']
        
        # Check latency
        if 'latency' in actual_metrics:
            metrics['actual_latency'].append(actual_metrics['latency'])
            if actual_metrics['latency'] > profile['max_latency']:
                metrics['violations'] += 1
                logger.warning(f"Latency violation for {allocation_id}: {actual_metrics['latency']}ms > {profile['max_latency']}ms")
        
        # Check throughput
        if 'throughput' in actual_metrics:
            metrics['actual_throughput'].append(actual_metrics['throughput'])
            if actual_metrics['throughput'] < profile['min_throughput']:
                metrics['violations'] += 1
                logger.warning(f"Throughput violation for {allocation_id}: {actual_metrics['throughput']} < {profile['min_throughput']}")
        
        # Keep only recent measurements
        if len(metrics['actual_latency']) > 100:
            metrics['actual_latency'] = metrics['actual_latency'][-100:]
        if len(metrics['actual_throughput']) > 100:
            metrics['actual_throughput'] = metrics['actual_throughput'][-100:]