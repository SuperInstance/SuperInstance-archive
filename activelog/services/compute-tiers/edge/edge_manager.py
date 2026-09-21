#!/usr/bin/env python3
"""
Edge Compute Manager for ActiveLog Compute Tiers
Intelligent edge computing deployment and management
"""

import logging
import json
import math
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import requests

logger = logging.getLogger(__name__)

class EdgeTier(Enum):
    """Edge compute tiers"""
    ULTRA_EDGE = "ultra_edge"      # <5ms latency, IoT/sensors
    REGIONAL_EDGE = "regional_edge" # <20ms latency, city-level
    METRO_EDGE = "metro_edge"      # <50ms latency, metro area
    MICRO_EDGE = "micro_edge"      # <100ms latency, local processing

class DeviceType(Enum):
    """Edge device types"""
    RASPBERRY_PI = "raspberry_pi"
    JETSON_NANO = "jetson_nano"
    AWS_WAVELENGTH = "aws_wavelength"
    AZURE_EDGE = "azure_edge"
    CUSTOM_HARDWARE = "custom_hardware"
    MOBILE_DEVICE = "mobile_device"

class EdgeWorkloadType(Enum):
    """Types of edge workloads"""
    IOT_PROCESSING = "iot_processing"
    COMPUTER_VISION = "computer_vision"
    AR_VR = "ar_vr"
    REAL_TIME_ANALYTICS = "real_time_analytics"
    CONTENT_DELIVERY = "content_delivery"
    GAMING = "gaming"
    INDUSTRIAL_AUTOMATION = "industrial_automation"

@dataclass
class EdgeLocation:
    """Edge compute location"""
    location_id: str
    location_name: str
    city: str
    state: str
    country: str
    coordinates: Tuple[float, float]  # lat, lng
    tier: EdgeTier
    devices: List[str]
    network_latency_ms: float
    bandwidth_mbps: float
    power_available_watts: float
    cooling_capacity: str
    security_level: str

@dataclass
class EdgeDevice:
    """Edge computing device"""
    device_id: str
    device_name: str
    device_type: DeviceType
    location_id: str
    cpu_cores: int
    memory_gb: float
    storage_gb: float
    gpu_available: bool
    gpu_memory_gb: float
    power_consumption_watts: float
    operating_temp_range: Tuple[float, float]
    network_interfaces: List[str]
    current_utilization: Dict[str, float]
    health_status: str
    last_heartbeat: datetime
    cost_per_hour: float

@dataclass
class EdgeWorkload:
    """Edge workload specification"""
    workload_id: str
    workload_name: str
    workload_type: EdgeWorkloadType
    resource_requirements: Dict[str, float]
    latency_requirements: Dict[str, float]
    data_sources: List[str]
    data_sinks: List[str]
    processing_frequency: str  # "continuous", "batch", "event_driven"
    priority: int
    mobility_pattern: str  # "static", "mobile", "nomadic"
    failover_requirements: Dict[str, Any]

@dataclass
class EdgeDeployment:
    """Edge deployment result"""
    workload_id: str
    deployment_id: str
    selected_devices: List[str]
    device_details: List[Dict[str, Any]]
    deployment_strategy: str
    estimated_latency_ms: float
    estimated_cost_hourly: float
    data_flow_plan: Dict[str, Any]
    redundancy_plan: Dict[str, Any]
    monitoring_plan: Dict[str, Any]
    edge_optimization_applied: List[str]
    reasoning: str
    confidence_score: float

class EdgeManager:
    """Manages edge compute deployments and optimization"""
    
    def __init__(self, config):
        self.config = config
        
        # Edge infrastructure registry
        self.edge_locations: Dict[str, EdgeLocation] = {}
        self.edge_devices: Dict[str, EdgeDevice] = {}
        
        # Active deployments
        self.active_deployments: Dict[str, Dict[str, Any]] = {}
        
        # Edge networking information
        self.network_topology = {}
        
        # Initialize edge infrastructure
        self._initialize_edge_infrastructure()
        
        # Edge optimization strategies
        self.optimization_strategies = {
            'latency_first': {
                'latency_weight': 0.6,
                'cost_weight': 0.2,
                'reliability_weight': 0.2
            },
            'cost_optimized': {
                'latency_weight': 0.2,
                'cost_weight': 0.6,
                'reliability_weight': 0.2
            },
            'balanced': {
                'latency_weight': 0.4,
                'cost_weight': 0.3,
                'reliability_weight': 0.3
            },
            'reliability_first': {
                'latency_weight': 0.3,
                'cost_weight': 0.2,
                'reliability_weight': 0.5
            }
        }

    def _initialize_edge_infrastructure(self):
        """Initialize edge infrastructure catalog"""
        # Define edge locations
        edge_locations_data = [
            {
                'location_id': 'edge_nyc_manhattan',
                'location_name': 'NYC Manhattan Edge',
                'city': 'New York',
                'state': 'NY',
                'country': 'USA',
                'coordinates': (40.7831, -73.9712),
                'tier': EdgeTier.ULTRA_EDGE,
                'network_latency_ms': 2.0,
                'bandwidth_mbps': 10000,
                'power_available_watts': 50000,
                'cooling_capacity': 'active',
                'security_level': 'high'
            },
            {
                'location_id': 'edge_sf_downtown',
                'location_name': 'San Francisco Downtown Edge',
                'city': 'San Francisco',
                'state': 'CA',
                'country': 'USA',
                'coordinates': (37.7749, -122.4194),
                'tier': EdgeTier.ULTRA_EDGE,
                'network_latency_ms': 1.8,
                'bandwidth_mbps': 15000,
                'power_available_watts': 60000,
                'cooling_capacity': 'active',
                'security_level': 'high'
            },
            {
                'location_id': 'edge_chicago_loop',
                'location_name': 'Chicago Loop Edge',
                'city': 'Chicago',
                'state': 'IL',
                'country': 'USA',
                'coordinates': (41.8781, -87.6298),
                'tier': EdgeTier.REGIONAL_EDGE,
                'network_latency_ms': 8.0,
                'bandwidth_mbps': 5000,
                'power_available_watts': 30000,
                'cooling_capacity': 'passive',
                'security_level': 'medium'
            },
            {
                'location_id': 'edge_austin_central',
                'location_name': 'Austin Central Edge',
                'city': 'Austin',
                'state': 'TX',
                'country': 'USA',
                'coordinates': (30.2672, -97.7431),
                'tier': EdgeTier.METRO_EDGE,
                'network_latency_ms': 15.0,
                'bandwidth_mbps': 2000,
                'power_available_watts': 20000,
                'cooling_capacity': 'passive',
                'security_level': 'medium'
            },
            {
                'location_id': 'edge_seattle_downtown',
                'location_name': 'Seattle Downtown Edge',
                'city': 'Seattle',
                'state': 'WA',
                'country': 'USA',
                'coordinates': (47.6062, -122.3321),
                'tier': EdgeTier.MICRO_EDGE,
                'network_latency_ms': 25.0,
                'bandwidth_mbps': 1000,
                'power_available_watts': 10000,
                'cooling_capacity': 'passive',
                'security_level': 'standard'
            }
        ]
        
        # Initialize locations
        for location_data in edge_locations_data:
            location = EdgeLocation(
                location_id=location_data['location_id'],
                location_name=location_data['location_name'],
                city=location_data['city'],
                state=location_data['state'],
                country=location_data['country'],
                coordinates=location_data['coordinates'],
                tier=location_data['tier'],
                devices=[],  # Will be populated with devices
                network_latency_ms=location_data['network_latency_ms'],
                bandwidth_mbps=location_data['bandwidth_mbps'],
                power_available_watts=location_data['power_available_watts'],
                cooling_capacity=location_data['cooling_capacity'],
                security_level=location_data['security_level']
            )
            self.edge_locations[location.location_id] = location
        
        # Define edge devices
        self._initialize_edge_devices()

    def _initialize_edge_devices(self):
        """Initialize edge devices catalog"""
        device_configs = [
            # Ultra Edge - NYC
            {
                'device_id': 'jetson_nyc_001',
                'device_name': 'Jetson Xavier NYC-001',
                'device_type': DeviceType.JETSON_NANO,
                'location_id': 'edge_nyc_manhattan',
                'cpu_cores': 8,
                'memory_gb': 32,
                'storage_gb': 512,
                'gpu_available': True,
                'gpu_memory_gb': 32,
                'power_consumption_watts': 30,
                'cost_per_hour': 2.5
            },
            {
                'device_id': 'wavelength_nyc_001',
                'device_name': 'AWS Wavelength NYC-001',
                'device_type': DeviceType.AWS_WAVELENGTH,
                'location_id': 'edge_nyc_manhattan',
                'cpu_cores': 16,
                'memory_gb': 64,
                'storage_gb': 1000,
                'gpu_available': True,
                'gpu_memory_gb': 16,
                'power_consumption_watts': 200,
                'cost_per_hour': 5.2
            },
            
            # Ultra Edge - San Francisco
            {
                'device_id': 'azure_edge_sf_001',
                'device_name': 'Azure Edge SF-001',
                'device_type': DeviceType.AZURE_EDGE,
                'location_id': 'edge_sf_downtown',
                'cpu_cores': 12,
                'memory_gb': 48,
                'storage_gb': 800,
                'gpu_available': True,
                'gpu_memory_gb': 24,
                'power_consumption_watts': 150,
                'cost_per_hour': 4.8
            },
            {
                'device_id': 'custom_sf_001',
                'device_name': 'Custom Hardware SF-001',
                'device_type': DeviceType.CUSTOM_HARDWARE,
                'location_id': 'edge_sf_downtown',
                'cpu_cores': 20,
                'memory_gb': 128,
                'storage_gb': 2000,
                'gpu_available': True,
                'gpu_memory_gb': 48,
                'power_consumption_watts': 400,
                'cost_per_hour': 8.5
            },
            
            # Regional Edge - Chicago
            {
                'device_id': 'jetson_chi_001',
                'device_name': 'Jetson Xavier CHI-001',
                'device_type': DeviceType.JETSON_NANO,
                'location_id': 'edge_chicago_loop',
                'cpu_cores': 8,
                'memory_gb': 32,
                'storage_gb': 512,
                'gpu_available': True,
                'gpu_memory_gb': 32,
                'power_consumption_watts': 30,
                'cost_per_hour': 2.2
            },
            {
                'device_id': 'rpi_cluster_chi_001',
                'device_name': 'RPi Cluster CHI-001',
                'device_type': DeviceType.RASPBERRY_PI,
                'location_id': 'edge_chicago_loop',
                'cpu_cores': 16,  # 4 RPi 4B units
                'memory_gb': 32,  # 8GB each
                'storage_gb': 512,  # 128GB each
                'gpu_available': False,
                'gpu_memory_gb': 0,
                'power_consumption_watts': 60,
                'cost_per_hour': 1.2
            },
            
            # Metro Edge - Austin
            {
                'device_id': 'jetson_aus_001',
                'device_name': 'Jetson Nano AUS-001',
                'device_type': DeviceType.JETSON_NANO,
                'location_id': 'edge_austin_central',
                'cpu_cores': 4,
                'memory_gb': 8,
                'storage_gb': 256,
                'gpu_available': True,
                'gpu_memory_gb': 8,
                'power_consumption_watts': 15,
                'cost_per_hour': 1.8
            },
            
            # Micro Edge - Seattle
            {
                'device_id': 'rpi_sea_001',
                'device_name': 'Raspberry Pi SEA-001',
                'device_type': DeviceType.RASPBERRY_PI,
                'location_id': 'edge_seattle_downtown',
                'cpu_cores': 4,
                'memory_gb': 8,
                'storage_gb': 128,
                'gpu_available': False,
                'gpu_memory_gb': 0,
                'power_consumption_watts': 15,
                'cost_per_hour': 0.8
            }
        ]
        
        # Initialize devices
        for device_config in device_configs:
            # Generate realistic utilization
            current_utilization = {
                'cpu_percent': 20 + (hash(device_config['device_id']) % 40),  # 20-60%
                'memory_percent': 15 + (hash(device_config['device_id']) % 35),  # 15-50%
                'storage_percent': 10 + (hash(device_config['device_id']) % 30),  # 10-40%
                'gpu_percent': 5 + (hash(device_config['device_id']) % 25) if device_config['gpu_available'] else 0  # 5-30%
            }
            
            device = EdgeDevice(
                device_id=device_config['device_id'],
                device_name=device_config['device_name'],
                device_type=device_config['device_type'],
                location_id=device_config['location_id'],
                cpu_cores=device_config['cpu_cores'],
                memory_gb=device_config['memory_gb'],
                storage_gb=device_config['storage_gb'],
                gpu_available=device_config['gpu_available'],
                gpu_memory_gb=device_config['gpu_memory_gb'],
                power_consumption_watts=device_config['power_consumption_watts'],
                operating_temp_range=(0, 70),  # Default range
                network_interfaces=['ethernet', 'wifi', '5G'],
                current_utilization=current_utilization,
                health_status='healthy',
                last_heartbeat=datetime.utcnow(),
                cost_per_hour=device_config['cost_per_hour']
            )
            
            self.edge_devices[device.device_id] = device
            
            # Add device to location
            if device.location_id in self.edge_locations:
                self.edge_locations[device.location_id].devices.append(device.device_id)

    def deploy_workload(self, workload_spec: Dict[str, Any], 
                       edge_preferences: Dict[str, Any] = None) -> EdgeDeployment:
        """Deploy workload to edge infrastructure"""
        try:
            # Parse workload specification
            workload = self._parse_edge_workload_spec(workload_spec)
            preferences = edge_preferences or {}
            
            # Find suitable edge devices
            suitable_devices = self._find_suitable_edge_devices(workload, preferences)
            
            if not suitable_devices:
                return self._create_error_deployment(
                    workload.workload_id,
                    "No suitable edge devices found for workload requirements"
                )
            
            # Select optimal devices
            selected_devices = self._select_optimal_edge_devices(workload, suitable_devices, preferences)
            
            # Determine deployment strategy
            deployment_strategy = self._determine_deployment_strategy(workload, selected_devices)
            
            # Calculate estimates
            estimated_latency = self._calculate_edge_latency(workload, selected_devices)
            estimated_cost = self._calculate_edge_cost(workload, selected_devices)
            
            # Generate plans
            data_flow_plan = self._generate_edge_data_flow_plan(workload, selected_devices)
            redundancy_plan = self._generate_edge_redundancy_plan(workload, selected_devices, suitable_devices)
            monitoring_plan = self._generate_edge_monitoring_plan(workload, selected_devices)
            
            # Apply edge optimizations
            edge_optimizations = self._apply_edge_optimizations(workload, selected_devices)
            
            # Generate reasoning
            reasoning = self._generate_edge_reasoning(workload, selected_devices, deployment_strategy, preferences)
            
            # Calculate confidence score
            confidence_score = self._calculate_edge_confidence(workload, selected_devices)
            
            # Create deployment ID
            deployment_id = f"edge_deploy_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{workload.workload_id[:8]}"
            
            # Register active deployment
            self.active_deployments[deployment_id] = {
                'workload': workload,
                'devices': [device.device_id for device in selected_devices],
                'start_time': datetime.utcnow(),
                'strategy': deployment_strategy,
                'estimated_cost': estimated_cost
            }
            
            return EdgeDeployment(
                workload_id=workload.workload_id,
                deployment_id=deployment_id,
                selected_devices=[device.device_id for device in selected_devices],
                device_details=[self._device_to_dict(device) for device in selected_devices],
                deployment_strategy=deployment_strategy,
                estimated_latency_ms=estimated_latency,
                estimated_cost_hourly=estimated_cost,
                data_flow_plan=data_flow_plan,
                redundancy_plan=redundancy_plan,
                monitoring_plan=monitoring_plan,
                edge_optimization_applied=edge_optimizations,
                reasoning=reasoning,
                confidence_score=confidence_score
            )
            
        except Exception as e:
            logger.error(f"Failed to deploy edge workload: {e}")
            return self._create_error_deployment(
                workload_spec.get('workload_id', 'unknown'),
                f"Deployment error: {str(e)}"
            )

    def _parse_edge_workload_spec(self, spec: Dict[str, Any]) -> EdgeWorkload:
        """Parse edge workload specification"""
        return EdgeWorkload(
            workload_id=spec.get('workload_id', f'edge_workload_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}'),
            workload_name=spec.get('workload_name', 'Unnamed Edge Workload'),
            workload_type=EdgeWorkloadType(spec.get('workload_type', 'iot_processing')),
            resource_requirements=spec.get('resource_requirements', {
                'cpu_cores': 2.0,
                'memory_gb': 4.0,
                'storage_gb': 50.0,
                'gpu_required': False
            }),
            latency_requirements=spec.get('latency_requirements', {'max_latency_ms': 50.0}),
            data_sources=spec.get('data_sources', ['local_sensors']),
            data_sinks=spec.get('data_sinks', ['cloud_storage']),
            processing_frequency=spec.get('processing_frequency', 'continuous'),
            priority=spec.get('priority', 5),
            mobility_pattern=spec.get('mobility_pattern', 'static'),
            failover_requirements=spec.get('failover_requirements', {})
        )

    def _find_suitable_edge_devices(self, workload: EdgeWorkload, 
                                   preferences: Dict[str, Any]) -> List[EdgeDevice]:
        """Find edge devices suitable for workload"""
        suitable_devices = []
        
        for device in self.edge_devices.values():
            # Check device health and availability
            if device.health_status != 'healthy':
                continue
            
            # Check heartbeat (device must be responsive)
            if (datetime.utcnow() - device.last_heartbeat).total_seconds() > 300:
                continue
            
            # Check resource requirements
            if not self._device_meets_requirements(device, workload.resource_requirements):
                continue
            
            # Check latency requirements
            location = self.edge_locations.get(device.location_id)
            if location and location.network_latency_ms > workload.latency_requirements.get('max_latency_ms', 100):
                continue
            
            # Check workload type compatibility
            if not self._device_supports_workload_type(device, workload.workload_type):
                continue
            
            # Check location preferences
            preferred_locations = preferences.get('preferred_locations', [])
            if preferred_locations and device.location_id not in preferred_locations:
                continue
            
            # Check edge tier preferences
            preferred_tiers = preferences.get('preferred_tiers', [])
            if preferred_tiers and location and location.tier.value not in preferred_tiers:
                continue
            
            suitable_devices.append(device)
        
        return suitable_devices

    def _device_meets_requirements(self, device: EdgeDevice, requirements: Dict[str, Any]) -> bool:
        """Check if device meets resource requirements"""
        # CPU check
        required_cpu = requirements.get('cpu_cores', 1.0)
        available_cpu = device.cpu_cores * (1 - device.current_utilization['cpu_percent'] / 100)
        if available_cpu < required_cpu:
            return False
        
        # Memory check
        required_memory = requirements.get('memory_gb', 1.0)
        available_memory = device.memory_gb * (1 - device.current_utilization['memory_percent'] / 100)
        if available_memory < required_memory:
            return False
        
        # Storage check
        required_storage = requirements.get('storage_gb', 10.0)
        available_storage = device.storage_gb * (1 - device.current_utilization['storage_percent'] / 100)
        if available_storage < required_storage:
            return False
        
        # GPU check
        gpu_required = requirements.get('gpu_required', False)
        if gpu_required and not device.gpu_available:
            return False
        
        return True

    def _device_supports_workload_type(self, device: EdgeDevice, workload_type: EdgeWorkloadType) -> bool:
        """Check if device supports workload type"""
        device_capabilities = {
            DeviceType.RASPBERRY_PI: [
                EdgeWorkloadType.IOT_PROCESSING,
                EdgeWorkloadType.REAL_TIME_ANALYTICS
            ],
            DeviceType.JETSON_NANO: [
                EdgeWorkloadType.IOT_PROCESSING,
                EdgeWorkloadType.COMPUTER_VISION,
                EdgeWorkloadType.REAL_TIME_ANALYTICS,
                EdgeWorkloadType.INDUSTRIAL_AUTOMATION
            ],
            DeviceType.AWS_WAVELENGTH: [
                EdgeWorkloadType.AR_VR,
                EdgeWorkloadType.GAMING,
                EdgeWorkloadType.CONTENT_DELIVERY,
                EdgeWorkloadType.REAL_TIME_ANALYTICS
            ],
            DeviceType.AZURE_EDGE: [
                EdgeWorkloadType.AR_VR,
                EdgeWorkloadType.COMPUTER_VISION,
                EdgeWorkloadType.REAL_TIME_ANALYTICS,
                EdgeWorkloadType.INDUSTRIAL_AUTOMATION
            ],
            DeviceType.CUSTOM_HARDWARE: [
                # Assume custom hardware can handle any workload
                workload_type
            ],
            DeviceType.MOBILE_DEVICE: [
                EdgeWorkloadType.AR_VR,
                EdgeWorkloadType.GAMING,
                EdgeWorkloadType.IOT_PROCESSING
            ]
        }
        
        supported_types = device_capabilities.get(device.device_type, [])
        return workload_type in supported_types

    def _select_optimal_edge_devices(self, workload: EdgeWorkload, suitable_devices: List[EdgeDevice],
                                   preferences: Dict[str, Any]) -> List[EdgeDevice]:
        """Select optimal edge devices based on strategy"""
        if not suitable_devices:
            return []
        
        # Determine optimization strategy
        strategy = preferences.get('optimization_strategy', 'balanced')
        strategy_config = self.optimization_strategies.get(strategy, self.optimization_strategies['balanced'])
        
        # Score devices
        scored_devices = []
        for device in suitable_devices:
            score = self._calculate_edge_device_score(device, workload, strategy_config)
            scored_devices.append((score, device))
        
        # Sort by score (higher is better)
        scored_devices.sort(key=lambda x: x[0], reverse=True)
        
        # Select devices based on requirements
        selected_devices = []
        
        # For high-priority workloads or specific failover requirements, select multiple devices
        if workload.priority <= 3 or workload.failover_requirements.get('redundancy_required', False):
            # Select primary device
            selected_devices.append(scored_devices[0][1])
            
            # Select backup device from different location if available
            primary_location = selected_devices[0].location_id
            for score, device in scored_devices[1:]:
                if device.location_id != primary_location:
                    selected_devices.append(device)
                    break
        else:
            # Select single best device
            selected_devices.append(scored_devices[0][1])
        
        return selected_devices

    def _calculate_edge_device_score(self, device: EdgeDevice, workload: EdgeWorkload,
                                   strategy_config: Dict[str, float]) -> float:
        """Calculate device score based on optimization strategy"""
        score = 0.0
        
        # Latency score (lower latency is better)
        location = self.edge_locations.get(device.location_id)
        if location:
            max_latency = workload.latency_requirements.get('max_latency_ms', 100.0)
            latency_score = max(0, 100 - (location.network_latency_ms / max_latency * 100))
            score += latency_score * strategy_config['latency_weight']
        
        # Cost score (lower cost is better)
        cost_score = max(0, 100 - (device.cost_per_hour * 10))  # Normalize cost
        score += cost_score * strategy_config['cost_weight']
        
        # Reliability score
        reliability_factors = []
        
        # Device type reliability
        device_reliability = {
            DeviceType.RASPBERRY_PI: 0.85,
            DeviceType.JETSON_NANO: 0.90,
            DeviceType.AWS_WAVELENGTH: 0.99,
            DeviceType.AZURE_EDGE: 0.98,
            DeviceType.CUSTOM_HARDWARE: 0.95,
            DeviceType.MOBILE_DEVICE: 0.80
        }
        reliability_factors.append(device_reliability.get(device.device_type, 0.9))
        
        # Current utilization (prefer moderately utilized devices)
        avg_utilization = (
            device.current_utilization['cpu_percent'] + 
            device.current_utilization['memory_percent']
        ) / 2
        utilization_reliability = 1.0 - abs(avg_utilization - 60) / 100  # Target 60% utilization
        reliability_factors.append(max(0, utilization_reliability))
        
        # Edge tier reliability
        if location:
            tier_reliability = {
                EdgeTier.ULTRA_EDGE: 0.99,
                EdgeTier.REGIONAL_EDGE: 0.95,
                EdgeTier.METRO_EDGE: 0.90,
                EdgeTier.MICRO_EDGE: 0.85
            }
            reliability_factors.append(tier_reliability.get(location.tier, 0.9))
        
        avg_reliability = sum(reliability_factors) / len(reliability_factors)
        reliability_score = avg_reliability * 100
        score += reliability_score * strategy_config['reliability_weight']
        
        # Resource efficiency bonus
        required_cpu = workload.resource_requirements.get('cpu_cores', 1.0)
        available_cpu = device.cpu_cores * (1 - device.current_utilization['cpu_percent'] / 100)
        cpu_efficiency = min(1.0, required_cpu / available_cpu)  # Prefer exact fit
        
        required_memory = workload.resource_requirements.get('memory_gb', 1.0)
        available_memory = device.memory_gb * (1 - device.current_utilization['memory_percent'] / 100)
        memory_efficiency = min(1.0, required_memory / available_memory)
        
        efficiency_score = (cpu_efficiency + memory_efficiency) / 2 * 20
        score += efficiency_score
        
        # Workload type compatibility bonus
        if self._device_supports_workload_type(device, workload.workload_type):
            score += 15
        
        # GPU availability bonus
        if workload.resource_requirements.get('gpu_required') and device.gpu_available:
            score += 10
        
        return score

    def _determine_deployment_strategy(self, workload: EdgeWorkload, devices: List[EdgeDevice]) -> str:
        """Determine deployment strategy"""
        if len(devices) > 1:
            # Check if devices are in different locations
            locations = set(device.location_id for device in devices)
            if len(locations) > 1:
                return "multi_location_redundant"
            else:
                return "single_location_redundant"
        else:
            # Single device deployment
            device = devices[0]
            location = self.edge_locations.get(device.location_id)
            
            if location and location.tier == EdgeTier.ULTRA_EDGE:
                return "ultra_low_latency"
            elif workload.workload_type in [EdgeWorkloadType.IOT_PROCESSING, EdgeWorkloadType.INDUSTRIAL_AUTOMATION]:
                return "iot_optimized"
            elif workload.workload_type in [EdgeWorkloadType.AR_VR, EdgeWorkloadType.GAMING]:
                return "real_time_interactive"
            elif workload.workload_type == EdgeWorkloadType.COMPUTER_VISION:
                return "vision_processing"
            else:
                return "standard_edge"

    def _calculate_edge_latency(self, workload: EdgeWorkload, devices: List[EdgeDevice]) -> float:
        """Calculate estimated edge latency"""
        if not devices:
            return 1000.0
        
        # Use minimum latency among selected devices
        min_latency = float('inf')
        
        for device in devices:
            location = self.edge_locations.get(device.location_id)
            if location:
                device_latency = location.network_latency_ms
                
                # Add processing latency based on workload type
                processing_latency = {
                    EdgeWorkloadType.IOT_PROCESSING: 1.0,
                    EdgeWorkloadType.COMPUTER_VISION: 5.0,
                    EdgeWorkloadType.AR_VR: 2.0,
                    EdgeWorkloadType.REAL_TIME_ANALYTICS: 3.0,
                    EdgeWorkloadType.CONTENT_DELIVERY: 1.0,
                    EdgeWorkloadType.GAMING: 1.5,
                    EdgeWorkloadType.INDUSTRIAL_AUTOMATION: 2.0
                }.get(workload.workload_type, 2.0)
                
                total_latency = device_latency + processing_latency
                min_latency = min(min_latency, total_latency)
        
        return min_latency if min_latency != float('inf') else 50.0

    def _calculate_edge_cost(self, workload: EdgeWorkload, devices: List[EdgeDevice]) -> float:
        """Calculate estimated hourly cost"""
        total_cost = 0.0
        
        for device in devices:
            # Base device cost
            device_cost = device.cost_per_hour
            
            # Add power consumption cost (approximate)
            power_cost_per_hour = (device.power_consumption_watts / 1000) * 0.12  # $0.12/kWh
            device_cost += power_cost_per_hour
            
            # Add data transfer costs for cloud connectivity
            if 'cloud_storage' in workload.data_sinks:
                data_transfer_cost = 0.05  # $0.05/hour for data transfer
                device_cost += data_transfer_cost
            
            total_cost += device_cost
        
        return round(total_cost, 3)

    def _generate_edge_data_flow_plan(self, workload: EdgeWorkload, devices: List[EdgeDevice]) -> Dict[str, Any]:
        """Generate data flow plan for edge deployment"""
        plan = {
            'data_sources': workload.data_sources,
            'data_sinks': workload.data_sinks,
            'processing_locations': [device.device_id for device in devices],
            'data_flow_pattern': workload.processing_frequency,
            'data_retention_policy': 'local_cache_1h',
            'bandwidth_requirements': {}
        }
        
        # Estimate bandwidth requirements
        if workload.workload_type == EdgeWorkloadType.COMPUTER_VISION:
            plan['bandwidth_requirements']['video_input'] = '10-50 Mbps'
            plan['bandwidth_requirements']['processed_output'] = '1-5 Mbps'
        elif workload.workload_type == EdgeWorkloadType.IOT_PROCESSING:
            plan['bandwidth_requirements']['sensor_input'] = '1-10 Mbps'
            plan['bandwidth_requirements']['aggregated_output'] = '0.1-1 Mbps'
        elif workload.workload_type == EdgeWorkloadType.AR_VR:
            plan['bandwidth_requirements']['ar_vr_data'] = '25-100 Mbps'
            plan['bandwidth_requirements']['response_data'] = '5-20 Mbps'
        
        # Data routing optimization
        if len(devices) > 1:
            plan['load_balancing'] = 'round_robin'
            plan['data_synchronization'] = 'eventual_consistency'
        
        # Edge-to-cloud synchronization
        if 'cloud_storage' in workload.data_sinks:
            plan['cloud_sync'] = {
                'sync_frequency': 'every_5_minutes',
                'compression_enabled': True,
                'encryption_enabled': True
            }
        
        return plan

    def _generate_edge_redundancy_plan(self, workload: EdgeWorkload, selected_devices: List[EdgeDevice],
                                     suitable_devices: List[EdgeDevice]) -> Dict[str, Any]:
        """Generate redundancy plan"""
        plan = {
            'redundancy_enabled': len(selected_devices) > 1,
            'primary_device': selected_devices[0].device_id if selected_devices else None,
            'backup_devices': [device.device_id for device in selected_devices[1:]] if len(selected_devices) > 1 else [],
            'failover_strategy': 'automatic',
            'failover_time_seconds': 30
        }
        
        # Add standby devices from different locations
        standby_devices = []
        selected_locations = set(device.location_id for device in selected_devices)
        
        for device in suitable_devices:
            if device not in selected_devices and device.location_id not in selected_locations:
                standby_devices.append(device.device_id)
                if len(standby_devices) >= 2:  # Limit standby devices
                    break
        
        plan['standby_devices'] = standby_devices
        
        # Adjust based on workload criticality
        if workload.priority <= 2:
            plan['failover_time_seconds'] = 10
            plan['health_check_interval_seconds'] = 15
        elif workload.priority >= 8:
            plan['failover_time_seconds'] = 60
            plan['health_check_interval_seconds'] = 60
        else:
            plan['health_check_interval_seconds'] = 30
        
        return plan

    def _generate_edge_monitoring_plan(self, workload: EdgeWorkload, devices: List[EdgeDevice]) -> Dict[str, Any]:
        """Generate monitoring plan for edge deployment"""
        plan = {
            'monitoring_enabled': True,
            'monitoring_interval_seconds': 30,
            'metrics_to_monitor': [
                'cpu_utilization',
                'memory_utilization',
                'network_latency',
                'device_temperature',
                'power_consumption',
                'storage_utilization'
            ],
            'alert_thresholds': {
                'cpu_utilization': 85,
                'memory_utilization': 90,
                'network_latency': workload.latency_requirements.get('max_latency_ms', 100) * 1.5,
                'device_temperature': 65,  # Celsius
                'storage_utilization': 95
            },
            'notification_channels': ['email']
        }
        
        # Add workload-specific monitoring
        if workload.workload_type == EdgeWorkloadType.COMPUTER_VISION:
            plan['metrics_to_monitor'].extend(['gpu_utilization', 'inference_rate', 'accuracy_score'])
            plan['alert_thresholds']['gpu_utilization'] = 90
        
        if workload.workload_type == EdgeWorkloadType.IOT_PROCESSING:
            plan['metrics_to_monitor'].extend(['message_queue_depth', 'processing_rate'])
        
        if workload.workload_type in [EdgeWorkloadType.AR_VR, EdgeWorkloadType.GAMING]:
            plan['metrics_to_monitor'].extend(['frame_rate', 'response_time'])
            plan['alert_thresholds']['response_time'] = 16  # 60 FPS target
        
        # Adjust monitoring frequency based on priority
        if workload.priority <= 2:
            plan['monitoring_interval_seconds'] = 15
        elif workload.priority >= 8:
            plan['monitoring_interval_seconds'] = 60
        
        return plan

    def _apply_edge_optimizations(self, workload: EdgeWorkload, devices: List[EdgeDevice]) -> List[str]:
        """Apply edge-specific optimizations"""
        optimizations = []
        
        # Model compression for ML workloads
        if workload.workload_type in [EdgeWorkloadType.COMPUTER_VISION, EdgeWorkloadType.AR_VR]:
            optimizations.append('model_quantization')
            optimizations.append('neural_network_pruning')
        
        # Data preprocessing optimization
        if workload.workload_type == EdgeWorkloadType.IOT_PROCESSING:
            optimizations.append('sensor_data_aggregation')
            optimizations.append('local_filtering')
        
        # Caching optimization
        if workload.processing_frequency == 'continuous':
            optimizations.append('result_caching')
            optimizations.append('input_data_preprocessing')
        
        # Network optimization
        optimizations.append('data_compression')
        optimizations.append('edge_cdn_caching')
        
        # Power optimization for low-power devices
        low_power_devices = [DeviceType.RASPBERRY_PI, DeviceType.JETSON_NANO]
        if any(device.device_type in low_power_devices for device in devices):
            optimizations.append('cpu_frequency_scaling')
            optimizations.append('sleep_mode_scheduling')
        
        # GPU optimization
        if any(device.gpu_available for device in devices):
            optimizations.append('gpu_memory_management')
            optimizations.append('cuda_kernel_optimization')
        
        return optimizations

    def _generate_edge_reasoning(self, workload: EdgeWorkload, devices: List[EdgeDevice],
                               deployment_strategy: str, preferences: Dict[str, Any]) -> str:
        """Generate reasoning for edge deployment decision"""
        reasons = []
        
        # Strategy reasoning
        reasons.append(f"Selected {deployment_strategy} deployment strategy for {workload.workload_type.value} workload")
        
        # Device selection reasoning
        if devices:
            primary_device = devices[0]
            location = self.edge_locations.get(primary_device.location_id)
            if location:
                reasons.append(f"Deployed to {location.tier.value} edge tier in {location.city} for latency optimization")
        
        # Latency reasoning
        max_latency = workload.latency_requirements.get('max_latency_ms', 100)
        if max_latency < 10:
            reasons.append("Ultra-low latency requirements demand edge processing")
        elif max_latency < 50:
            reasons.append("Low latency requirements favor edge deployment")
        
        # Workload type reasoning
        if workload.workload_type == EdgeWorkloadType.IOT_PROCESSING:
            reasons.append("IoT workload benefits from local data processing and aggregation")
        elif workload.workload_type == EdgeWorkloadType.COMPUTER_VISION:
            reasons.append("Computer vision workload requires GPU acceleration and low latency")
        elif workload.workload_type == EdgeWorkloadType.AR_VR:
            reasons.append("AR/VR workload demands ultra-low latency and real-time processing")
        
        # Redundancy reasoning
        if len(devices) > 1:
            reasons.append(f"Multi-device deployment provides redundancy for priority {workload.priority} workload")
        
        # Cost reasoning
        total_cost = sum(device.cost_per_hour for device in devices)
        if total_cost < 2.0:
            reasons.append("Cost-effective edge deployment using efficient hardware")
        
        return "; ".join(reasons)

    def _calculate_edge_confidence(self, workload: EdgeWorkload, devices: List[EdgeDevice]) -> float:
        """Calculate confidence score for edge deployment"""
        if not devices:
            return 0.0
        
        confidence = 0.8  # Base confidence
        
        # Device availability confidence
        avg_utilization = sum(
            (device.current_utilization['cpu_percent'] + device.current_utilization['memory_percent']) / 2
            for device in devices
        ) / len(devices)
        
        if avg_utilization < 50:
            confidence += 0.1  # Good availability
        elif avg_utilization > 80:
            confidence -= 0.2  # High utilization risk
        
        # Latency confidence
        estimated_latency = self._calculate_edge_latency(workload, devices)
        max_latency = workload.latency_requirements.get('max_latency_ms', 100)
        latency_margin = (max_latency - estimated_latency) / max_latency
        
        if latency_margin > 0.5:
            confidence += 0.1  # Good latency margin
        elif latency_margin < 0.1:
            confidence -= 0.2  # Tight latency margin
        
        # Redundancy confidence
        if len(devices) > 1:
            confidence += 0.1  # Redundancy bonus
        
        # Device type confidence
        reliable_types = [DeviceType.AWS_WAVELENGTH, DeviceType.AZURE_EDGE]
        if any(device.device_type in reliable_types for device in devices):
            confidence += 0.05
        
        return min(1.0, max(0.0, confidence))

    def _device_to_dict(self, device: EdgeDevice) -> Dict[str, Any]:
        """Convert edge device to dictionary"""
        return {
            'device_id': device.device_id,
            'device_name': device.device_name,
            'device_type': device.device_type.value,
            'location_id': device.location_id,
            'cpu_cores': device.cpu_cores,
            'memory_gb': device.memory_gb,
            'storage_gb': device.storage_gb,
            'gpu_available': device.gpu_available,
            'gpu_memory_gb': device.gpu_memory_gb,
            'power_consumption_watts': device.power_consumption_watts,
            'current_utilization': device.current_utilization,
            'health_status': device.health_status,
            'cost_per_hour': device.cost_per_hour
        }

    def _create_error_deployment(self, workload_id: str, error_message: str) -> EdgeDeployment:
        """Create error edge deployment"""
        return EdgeDeployment(
            workload_id=workload_id,
            deployment_id="error",
            selected_devices=[],
            device_details=[],
            deployment_strategy="error",
            estimated_latency_ms=1000.0,
            estimated_cost_hourly=0.0,
            data_flow_plan={'error': error_message},
            redundancy_plan={'error': error_message},
            monitoring_plan={'error': error_message},
            edge_optimization_applied=[],
            reasoning=f"Error: {error_message}",
            confidence_score=0.0
        )

    def get_edge_infrastructure_status(self) -> Dict[str, Any]:
        """Get current edge infrastructure status"""
        try:
            status = {
                'timestamp': datetime.utcnow().isoformat(),
                'edge_locations': len(self.edge_locations),
                'edge_devices': len(self.edge_devices),
                'active_deployments': len(self.active_deployments),
                'locations': {},
                'devices_by_type': {},
                'devices_by_tier': {},
                'total_capacity': {'cpu_cores': 0, 'memory_gb': 0, 'storage_gb': 0, 'gpu_count': 0},
                'total_utilization': {'cpu_cores': 0, 'memory_gb': 0, 'storage_gb': 0, 'gpu_count': 0}
            }
            
            # Process locations
            for location_id, location in self.edge_locations.items():
                status['locations'][location_id] = {
                    'location_name': location.location_name,
                    'city': location.city,
                    'tier': location.tier.value,
                    'device_count': len(location.devices),
                    'network_latency_ms': location.network_latency_ms,
                    'bandwidth_mbps': location.bandwidth_mbps
                }
                
                # Count by tier
                tier = location.tier.value
                status['devices_by_tier'][tier] = status['devices_by_tier'].get(tier, 0) + len(location.devices)
            
            # Process devices
            for device in self.edge_devices.values():
                # Count by type
                device_type = device.device_type.value
                status['devices_by_type'][device_type] = status['devices_by_type'].get(device_type, 0) + 1
                
                # Aggregate capacity
                status['total_capacity']['cpu_cores'] += device.cpu_cores
                status['total_capacity']['memory_gb'] += device.memory_gb
                status['total_capacity']['storage_gb'] += device.storage_gb
                if device.gpu_available:
                    status['total_capacity']['gpu_count'] += 1
                
                # Aggregate utilization
                status['total_utilization']['cpu_cores'] += device.cpu_cores * (device.current_utilization['cpu_percent'] / 100)
                status['total_utilization']['memory_gb'] += device.memory_gb * (device.current_utilization['memory_percent'] / 100)
                status['total_utilization']['storage_gb'] += device.storage_gb * (device.current_utilization['storage_percent'] / 100)
                if device.gpu_available:
                    status['total_utilization']['gpu_count'] += device.current_utilization['gpu_percent'] / 100
            
            # Calculate utilization percentages
            status['utilization_percentages'] = {}
            for resource in status['total_capacity']:
                if status['total_capacity'][resource] > 0:
                    utilization_pct = (status['total_utilization'][resource] / status['total_capacity'][resource]) * 100
                    status['utilization_percentages'][resource] = round(utilization_pct, 1)
                else:
                    status['utilization_percentages'][resource] = 0.0
            
            return status
            
        except Exception as e:
            logger.error(f"Failed to get edge infrastructure status: {e}")
            return {'error': str(e)}

    def get_deployment_status(self, deployment_id: Optional[str] = None) -> Dict[str, Any]:
        """Get edge deployment status"""
        try:
            if deployment_id:
                if deployment_id in self.active_deployments:
                    deployment_info = self.active_deployments[deployment_id]
                    runtime = datetime.utcnow() - deployment_info['start_time']
                    
                    return {
                        'deployment_id': deployment_id,
                        'status': 'running',
                        'runtime_minutes': runtime.total_seconds() / 60,
                        'workload_id': deployment_info['workload'].workload_id,
                        'devices': deployment_info['devices'],
                        'strategy': deployment_info['strategy'],
                        'estimated_cost': deployment_info['estimated_cost']
                    }
                else:
                    return {'error': f'Deployment {deployment_id} not found'}
            
            # Return all active deployments
            deployments_status = []
            for dep_id, deployment_info in self.active_deployments.items():
                runtime = datetime.utcnow() - deployment_info['start_time']
                deployments_status.append({
                    'deployment_id': dep_id,
                    'workload_id': deployment_info['workload'].workload_id,
                    'workload_name': deployment_info['workload'].workload_name,
                    'status': 'running',
                    'runtime_minutes': runtime.total_seconds() / 60,
                    'devices': deployment_info['devices'],
                    'strategy': deployment_info['strategy'],
                    'estimated_cost': deployment_info['estimated_cost']
                })
            
            return {
                'timestamp': datetime.utcnow().isoformat(),
                'active_deployments_count': len(deployments_status),
                'deployments': deployments_status
            }
            
        except Exception as e:
            logger.error(f"Failed to get deployment status: {e}")
            return {'error': str(e)}