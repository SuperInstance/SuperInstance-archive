"""
Hardware Upgrade Guidance System for Adaptive UX

This module provides intelligent hardware upgrade recommendations including
bottleneck identification, performance improvement estimates, cost-benefit analysis,
compatibility checking, and future-proofing advice.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict, field
from enum import Enum
import numpy as np
from collections import defaultdict
import requests
from concurrent.futures import ThreadPoolExecutor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ComponentType(Enum):
    CPU = "cpu"
    GPU = "gpu"
    RAM = "ram"
    STORAGE = "storage"
    MOTHERBOARD = "motherboard"
    POWER_SUPPLY = "power_supply"
    COOLING = "cooling"
    DISPLAY = "display"
    NETWORK = "network"
    AUDIO = "audio"

class BottleneckSeverity(Enum):
    NONE = "none"
    MINOR = "minor" 
    MODERATE = "moderate"
    MAJOR = "major"
    CRITICAL = "critical"

class UpgradeUrgency(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class UpgradeType(Enum):
    REPLACEMENT = "replacement"
    ADDITION = "addition"
    CONFIGURATION = "configuration"
    SOFTWARE = "software"

@dataclass
class HardwareComponent:
    component_type: ComponentType
    model: str
    manufacturer: str
    specifications: Dict[str, Any]
    performance_score: float  # 0-100
    age_years: float
    current_price: Optional[float] = None
    availability: str = "available"
    power_consumption: Optional[int] = None
    thermal_design_power: Optional[int] = None

@dataclass
class SystemConfiguration:
    cpu: HardwareComponent
    gpu: Optional[HardwareComponent]
    ram: HardwareComponent
    storage: List[HardwareComponent]
    motherboard: HardwareComponent
    power_supply: HardwareComponent
    display: Optional[HardwareComponent]
    total_system_score: float = 0.0
    bottleneck_score: float = 0.0

@dataclass
class PerformanceBottleneck:
    component_type: ComponentType
    severity: BottleneckSeverity
    impact_percentage: float  # How much it's limiting overall performance
    description: str
    evidence: List[str]
    affected_use_cases: List[str]

@dataclass
class UpgradeRecommendation:
    component_type: ComponentType
    current_component: HardwareComponent
    recommended_components: List[HardwareComponent]
    upgrade_type: UpgradeType
    urgency: UpgradeUrgency
    estimated_cost: float
    performance_improvement: float  # Percentage
    compatibility_score: float  # 0-1
    future_proof_years: int
    cost_benefit_ratio: float
    installation_difficulty: str
    power_requirements: Dict[str, Any]
    thermal_considerations: Dict[str, Any]
    justification: str
    alternatives: List[str] = field(default_factory=list)

@dataclass
class CostBenefitAnalysis:
    upgrade_cost: float
    performance_gain: float
    productivity_improvement: float
    longevity_extension_years: int
    total_value_score: float
    payback_period_months: Optional[int]
    comparison_alternatives: List[Dict[str, Any]] = field(default_factory=list)

class HardwareDatabase:
    """Hardware component database with pricing and specifications"""
    
    def __init__(self):
        self.components: Dict[ComponentType, List[HardwareComponent]] = defaultdict(list)
        self.price_history: Dict[str, List[Tuple[datetime, float]]] = defaultdict(list)
        self.compatibility_matrix: Dict[str, Dict[str, float]] = defaultdict(dict)
        
        # Initialize with sample data
        self._initialize_sample_data()
    
    def _initialize_sample_data(self):
        """Initialize with sample hardware data"""
        
        # Sample CPUs
        cpus = [
            HardwareComponent(
                component_type=ComponentType.CPU,
                model="AMD Ryzen 7 7800X3D",
                manufacturer="AMD",
                specifications={
                    "cores": 8,
                    "threads": 16,
                    "base_clock": 4.2,
                    "boost_clock": 5.0,
                    "cache_mb": 96,
                    "tdp": 120,
                    "socket": "AM5",
                    "architecture": "Zen 4"
                },
                performance_score=95.0,
                age_years=0.5,
                current_price=449.99,
                power_consumption=120,
                thermal_design_power=120
            ),
            HardwareComponent(
                component_type=ComponentType.CPU,
                model="Intel Core i7-13700K",
                manufacturer="Intel",
                specifications={
                    "cores": 16,
                    "threads": 24,
                    "base_clock": 3.4,
                    "boost_clock": 5.4,
                    "cache_mb": 30,
                    "tdp": 125,
                    "socket": "LGA1700",
                    "architecture": "Raptor Lake"
                },
                performance_score=92.0,
                age_years=0.8,
                current_price=419.99,
                power_consumption=125,
                thermal_design_power=125
            ),
            HardwareComponent(
                component_type=ComponentType.CPU,
                model="AMD Ryzen 5 5600X",
                manufacturer="AMD",
                specifications={
                    "cores": 6,
                    "threads": 12,
                    "base_clock": 3.7,
                    "boost_clock": 4.6,
                    "cache_mb": 32,
                    "tdp": 65,
                    "socket": "AM4",
                    "architecture": "Zen 3"
                },
                performance_score=78.0,
                age_years=3.0,
                current_price=199.99,
                power_consumption=65,
                thermal_design_power=65
            )
        ]
        
        # Sample GPUs
        gpus = [
            HardwareComponent(
                component_type=ComponentType.GPU,
                model="NVIDIA RTX 4080",
                manufacturer="NVIDIA",
                specifications={
                    "memory_gb": 16,
                    "memory_type": "GDDR6X",
                    "cuda_cores": 9728,
                    "base_clock": 2205,
                    "boost_clock": 2505,
                    "memory_bandwidth": 716.8,
                    "pcie_version": "4.0",
                    "power_connectors": "3x8pin"
                },
                performance_score=88.0,
                age_years=1.0,
                current_price=1199.99,
                power_consumption=320,
                thermal_design_power=320
            ),
            HardwareComponent(
                component_type=ComponentType.GPU,
                model="AMD Radeon RX 7800 XT",
                manufacturer="AMD",
                specifications={
                    "memory_gb": 16,
                    "memory_type": "GDDR6",
                    "compute_units": 60,
                    "base_clock": 1295,
                    "boost_clock": 2430,
                    "memory_bandwidth": 624,
                    "pcie_version": "4.0",
                    "power_connectors": "2x8pin"
                },
                performance_score=82.0,
                age_years=0.3,
                current_price=799.99,
                power_consumption=263,
                thermal_design_power=263
            )
        ]
        
        # Sample RAM
        ram_modules = [
            HardwareComponent(
                component_type=ComponentType.RAM,
                model="G.Skill Trident Z5 32GB DDR5-6000",
                manufacturer="G.Skill",
                specifications={
                    "capacity_gb": 32,
                    "speed": 6000,
                    "type": "DDR5",
                    "timings": "CL36-36-36-96",
                    "voltage": 1.35,
                    "modules": 2
                },
                performance_score=85.0,
                age_years=1.0,
                current_price=219.99,
                power_consumption=10
            ),
            HardwareComponent(
                component_type=ComponentType.RAM,
                model="Corsair Vengeance LPX 16GB DDR4-3200",
                manufacturer="Corsair",
                specifications={
                    "capacity_gb": 16,
                    "speed": 3200,
                    "type": "DDR4",
                    "timings": "CL16-18-18-36",
                    "voltage": 1.35,
                    "modules": 2
                },
                performance_score=70.0,
                age_years=4.0,
                current_price=79.99,
                power_consumption=8
            )
        ]
        
        # Sample Storage
        storage_devices = [
            HardwareComponent(
                component_type=ComponentType.STORAGE,
                model="Samsung 980 PRO 2TB NVMe",
                manufacturer="Samsung",
                specifications={
                    "capacity_gb": 2000,
                    "interface": "NVMe PCIe 4.0",
                    "read_speed": 7000,
                    "write_speed": 5100,
                    "form_factor": "M.2 2280",
                    "endurance_tbw": 1200
                },
                performance_score=92.0,
                age_years=2.0,
                current_price=199.99,
                power_consumption=6
            ),
            HardwareComponent(
                component_type=ComponentType.STORAGE,
                model="WD Blue 1TB SATA SSD",
                manufacturer="Western Digital",
                specifications={
                    "capacity_gb": 1000,
                    "interface": "SATA 3.0",
                    "read_speed": 560,
                    "write_speed": 530,
                    "form_factor": "2.5-inch"
                },
                performance_score=68.0,
                age_years=5.0,
                current_price=89.99,
                power_consumption=3
            )
        ]
        
        self.components[ComponentType.CPU] = cpus
        self.components[ComponentType.GPU] = gpus
        self.components[ComponentType.RAM] = ram_modules
        self.components[ComponentType.STORAGE] = storage_devices
        
        logger.info("Hardware database initialized with sample data")
    
    def search_components(self, component_type: ComponentType, 
                         filters: Dict[str, Any] = None) -> List[HardwareComponent]:
        """Search for components by type and filters"""
        components = self.components.get(component_type, [])
        
        if not filters:
            return components
        
        filtered = []
        for component in components:
            matches = True
            
            for filter_key, filter_value in filters.items():
                if filter_key == "max_price" and component.current_price:
                    if component.current_price > filter_value:
                        matches = False
                        break
                elif filter_key == "min_performance":
                    if component.performance_score < filter_value:
                        matches = False
                        break
                elif filter_key == "max_age":
                    if component.age_years > filter_value:
                        matches = False
                        break
                elif filter_key in component.specifications:
                    spec_value = component.specifications[filter_key]
                    if isinstance(filter_value, dict):
                        if "min" in filter_value and spec_value < filter_value["min"]:
                            matches = False
                            break
                        if "max" in filter_value and spec_value > filter_value["max"]:
                            matches = False
                            break
                    else:
                        if spec_value != filter_value:
                            matches = False
                            break
            
            if matches:
                filtered.append(component)
        
        return sorted(filtered, key=lambda x: x.performance_score, reverse=True)

class BottleneckAnalyzer:
    """Analyze system bottlenecks and performance limitations"""
    
    def __init__(self):
        self.analysis_cache = {}
        
    async def analyze_system_bottlenecks(self, config: SystemConfiguration,
                                       usage_patterns: Dict[str, float]) -> List[PerformanceBottleneck]:
        """Analyze system for performance bottlenecks"""
        bottlenecks = []
        
        try:
            # CPU bottleneck analysis
            cpu_bottleneck = await self._analyze_cpu_bottleneck(config, usage_patterns)
            if cpu_bottleneck:
                bottlenecks.append(cpu_bottleneck)
            
            # GPU bottleneck analysis
            if config.gpu:
                gpu_bottleneck = await self._analyze_gpu_bottleneck(config, usage_patterns)
                if gpu_bottleneck:
                    bottlenecks.append(gpu_bottleneck)
            
            # RAM bottleneck analysis
            ram_bottleneck = await self._analyze_ram_bottleneck(config, usage_patterns)
            if ram_bottleneck:
                bottlenecks.append(ram_bottleneck)
            
            # Storage bottleneck analysis
            storage_bottleneck = await self._analyze_storage_bottleneck(config, usage_patterns)
            if storage_bottleneck:
                bottlenecks.append(storage_bottleneck)
            
            # Cross-component bottleneck analysis
            cross_bottlenecks = await self._analyze_cross_component_bottlenecks(config, usage_patterns)
            bottlenecks.extend(cross_bottlenecks)
            
            # Sort by severity and impact
            bottlenecks.sort(key=lambda x: (x.severity.value, -x.impact_percentage))
            
            return bottlenecks
            
        except Exception as e:
            logger.error(f"Error analyzing system bottlenecks: {e}")
            return []
    
    async def _analyze_cpu_bottleneck(self, config: SystemConfiguration, 
                                    usage_patterns: Dict[str, float]) -> Optional[PerformanceBottleneck]:
        """Analyze CPU performance bottlenecks"""
        cpu = config.cpu
        cpu_score = cpu.performance_score
        
        # Check if CPU is limiting performance
        evidence = []
        affected_use_cases = []
        
        # Age-based analysis
        if cpu.age_years > 4:
            evidence.append(f"CPU is {cpu.age_years:.1f} years old")
            
        # Performance score analysis
        if cpu_score < 70:
            evidence.append(f"CPU performance score is low ({cpu_score:.1f}/100)")
            affected_use_cases.extend(["gaming", "content_creation", "development"])
        
        # Usage pattern analysis
        cpu_intensive_usage = usage_patterns.get("cpu_intensive_tasks", 0.0)
        if cpu_intensive_usage > 0.6 and cpu_score < 80:
            evidence.append("High CPU-intensive workload with moderate CPU performance")
            affected_use_cases.extend(["video_editing", "3d_rendering", "compilation"])
        
        # Core count analysis
        cores = cpu.specifications.get("cores", 4)
        if cores < 6 and usage_patterns.get("multitasking", 0.0) > 0.7:
            evidence.append(f"Limited core count ({cores}) for multitasking workloads")
            affected_use_cases.append("multitasking")
        
        if evidence:
            # Determine severity
            if cpu_score < 50 or cpu.age_years > 6:
                severity = BottleneckSeverity.CRITICAL
                impact = 40.0
            elif cpu_score < 65 or cpu.age_years > 4:
                severity = BottleneckSeverity.MAJOR
                impact = 25.0
            elif cpu_score < 75:
                severity = BottleneckSeverity.MODERATE
                impact = 15.0
            else:
                severity = BottleneckSeverity.MINOR
                impact = 8.0
            
            return PerformanceBottleneck(
                component_type=ComponentType.CPU,
                severity=severity,
                impact_percentage=impact,
                description=f"CPU ({cpu.model}) is limiting system performance",
                evidence=evidence,
                affected_use_cases=affected_use_cases
            )
        
        return None
    
    async def _analyze_gpu_bottleneck(self, config: SystemConfiguration, 
                                    usage_patterns: Dict[str, float]) -> Optional[PerformanceBottleneck]:
        """Analyze GPU performance bottlenecks"""
        if not config.gpu:
            # No discrete GPU - check if one is needed
            gpu_intensive_usage = usage_patterns.get("gpu_intensive_tasks", 0.0)
            if gpu_intensive_usage > 0.3:
                return PerformanceBottleneck(
                    component_type=ComponentType.GPU,
                    severity=BottleneckSeverity.MAJOR,
                    impact_percentage=35.0,
                    description="No discrete GPU for GPU-intensive tasks",
                    evidence=["Using integrated graphics", "High GPU workload detected"],
                    affected_use_cases=["gaming", "machine_learning", "video_editing"]
                )
            return None
        
        gpu = config.gpu
        gpu_score = gpu.performance_score
        evidence = []
        affected_use_cases = []
        
        # Age and performance analysis
        if gpu.age_years > 3:
            evidence.append(f"GPU is {gpu.age_years:.1f} years old")
        
        if gpu_score < 70:
            evidence.append(f"GPU performance score is low ({gpu_score:.1f}/100)")
            affected_use_cases.extend(["gaming", "ai_workloads", "content_creation"])
        
        # VRAM analysis
        vram_gb = gpu.specifications.get("memory_gb", 4)
        if vram_gb < 8 and usage_patterns.get("high_resolution_gaming", 0.0) > 0.5:
            evidence.append(f"Limited VRAM ({vram_gb}GB) for high-resolution gaming")
            affected_use_cases.append("4k_gaming")
        
        if evidence:
            if gpu_score < 60 or vram_gb < 6:
                severity = BottleneckSeverity.MAJOR
                impact = 30.0
            elif gpu_score < 75:
                severity = BottleneckSeverity.MODERATE
                impact = 20.0
            else:
                severity = BottleneckSeverity.MINOR
                impact = 10.0
            
            return PerformanceBottleneck(
                component_type=ComponentType.GPU,
                severity=severity,
                impact_percentage=impact,
                description=f"GPU ({gpu.model}) is limiting graphics performance",
                evidence=evidence,
                affected_use_cases=affected_use_cases
            )
        
        return None
    
    async def _analyze_ram_bottleneck(self, config: SystemConfiguration, 
                                    usage_patterns: Dict[str, float]) -> Optional[PerformanceBottleneck]:
        """Analyze RAM performance bottlenecks"""
        ram = config.ram
        capacity_gb = ram.specifications.get("capacity_gb", 8)
        ram_speed = ram.specifications.get("speed", 2400)
        ram_type = ram.specifications.get("type", "DDR4")
        
        evidence = []
        affected_use_cases = []
        
        # Capacity analysis
        if capacity_gb < 16 and usage_patterns.get("memory_intensive_tasks", 0.0) > 0.5:
            evidence.append(f"Limited RAM capacity ({capacity_gb}GB) for memory-intensive tasks")
            affected_use_cases.extend(["content_creation", "development", "multitasking"])
        
        if capacity_gb < 8:
            evidence.append("RAM capacity below modern minimum requirements")
            affected_use_cases.extend(["gaming", "productivity"])
        
        # Speed analysis
        if ram_type == "DDR4" and ram_speed < 3200:
            evidence.append(f"RAM speed ({ram_speed} MHz) below optimal for modern systems")
        elif ram_type == "DDR5" and ram_speed < 5600:
            evidence.append(f"DDR5 RAM speed ({ram_speed} MHz) below optimal")
        
        # Age analysis
        if ram.age_years > 5:
            evidence.append(f"RAM is {ram.age_years:.1f} years old")
        
        if evidence:
            if capacity_gb < 8:
                severity = BottleneckSeverity.CRITICAL
                impact = 25.0
            elif capacity_gb < 16 and usage_patterns.get("memory_intensive_tasks", 0.0) > 0.5:
                severity = BottleneckSeverity.MAJOR
                impact = 20.0
            else:
                severity = BottleneckSeverity.MODERATE
                impact = 10.0
            
            return PerformanceBottleneck(
                component_type=ComponentType.RAM,
                severity=severity,
                impact_percentage=impact,
                description=f"RAM ({ram.model}) is limiting system performance",
                evidence=evidence,
                affected_use_cases=affected_use_cases
            )
        
        return None
    
    async def _analyze_storage_bottleneck(self, config: SystemConfiguration, 
                                        usage_patterns: Dict[str, float]) -> Optional[PerformanceBottleneck]:
        """Analyze storage performance bottlenecks"""
        storage_devices = config.storage
        if not storage_devices:
            return None
        
        # Analyze primary storage (assume first in list)
        primary_storage = storage_devices[0]
        interface = primary_storage.specifications.get("interface", "SATA")
        read_speed = primary_storage.specifications.get("read_speed", 100)
        
        evidence = []
        affected_use_cases = []
        
        # Interface analysis
        if "SATA" in interface and usage_patterns.get("storage_intensive_tasks", 0.0) > 0.5:
            evidence.append("Using SATA interface instead of NVMe for storage-intensive tasks")
            affected_use_cases.extend(["content_creation", "development", "gaming"])
        
        # Speed analysis
        if read_speed < 3000:  # Below NVMe speeds
            evidence.append(f"Storage read speed ({read_speed} MB/s) below optimal for modern workloads")
            
        # Capacity analysis
        total_capacity = sum(device.specifications.get("capacity_gb", 0) for device in storage_devices)
        if total_capacity < 500:
            evidence.append(f"Limited storage capacity ({total_capacity}GB)")
            affected_use_cases.extend(["content_storage", "gaming"])
        
        if evidence:
            if "SATA" in interface and read_speed < 600:
                severity = BottleneckSeverity.MAJOR
                impact = 15.0
            else:
                severity = BottleneckSeverity.MODERATE
                impact = 8.0
            
            return PerformanceBottleneck(
                component_type=ComponentType.STORAGE,
                severity=severity,
                impact_percentage=impact,
                description=f"Storage ({primary_storage.model}) is limiting system responsiveness",
                evidence=evidence,
                affected_use_cases=affected_use_cases
            )
        
        return None
    
    async def _analyze_cross_component_bottlenecks(self, config: SystemConfiguration, 
                                                 usage_patterns: Dict[str, float]) -> List[PerformanceBottleneck]:
        """Analyze bottlenecks caused by component mismatches"""
        bottlenecks = []
        
        # CPU-GPU balance
        cpu_score = config.cpu.performance_score
        gpu_score = config.gpu.performance_score if config.gpu else 0
        
        if abs(cpu_score - gpu_score) > 20 and min(cpu_score, gpu_score) > 0:
            if cpu_score > gpu_score + 20:
                bottleneck_component = ComponentType.GPU
                description = "GPU is significantly weaker than CPU, creating imbalance"
            else:
                bottleneck_component = ComponentType.CPU
                description = "CPU is significantly weaker than GPU, creating imbalance"
            
            bottlenecks.append(PerformanceBottleneck(
                component_type=bottleneck_component,
                severity=BottleneckSeverity.MODERATE,
                impact_percentage=12.0,
                description=description,
                evidence=[f"CPU score: {cpu_score:.1f}, GPU score: {gpu_score:.1f}"],
                affected_use_cases=["gaming", "content_creation"]
            ))
        
        # RAM-CPU compatibility
        ram_type = config.ram.specifications.get("type", "DDR4")
        ram_speed = config.ram.specifications.get("speed", 2400)
        cpu_architecture = config.cpu.specifications.get("architecture", "")
        
        if ("Zen 4" in cpu_architecture or "Raptor Lake" in cpu_architecture) and ram_type == "DDR4":
            bottlenecks.append(PerformanceBottleneck(
                component_type=ComponentType.RAM,
                severity=BottleneckSeverity.MINOR,
                impact_percentage=5.0,
                description="Modern CPU with older DDR4 RAM instead of DDR5",
                evidence=["Latest CPU architecture with DDR4 memory"],
                affected_use_cases=["memory_bandwidth_dependent_tasks"]
            ))
        
        return bottlenecks

class UpgradeRecommendationEngine:
    """Generate intelligent hardware upgrade recommendations"""
    
    def __init__(self, hardware_db: HardwareDatabase):
        self.hardware_db = hardware_db
        self.bottleneck_analyzer = BottleneckAnalyzer()
        
    async def generate_recommendations(self, config: SystemConfiguration,
                                     usage_patterns: Dict[str, float],
                                     budget: Optional[float] = None,
                                     priorities: List[str] = None) -> List[UpgradeRecommendation]:
        """Generate comprehensive upgrade recommendations"""
        
        recommendations = []
        
        try:
            # Analyze current bottlenecks
            bottlenecks = await self.bottleneck_analyzer.analyze_system_bottlenecks(config, usage_patterns)
            
            # Generate recommendations for each bottleneck
            for bottleneck in bottlenecks:
                if bottleneck.severity in [BottleneckSeverity.MAJOR, BottleneckSeverity.CRITICAL]:
                    rec = await self._generate_component_recommendation(
                        config, bottleneck, usage_patterns, budget
                    )
                    if rec:
                        recommendations.append(rec)
            
            # Generate proactive recommendations
            proactive_recs = await self._generate_proactive_recommendations(
                config, usage_patterns, budget
            )
            recommendations.extend(proactive_recs)
            
            # Sort by priority
            recommendations.sort(key=lambda x: (x.urgency.value, -x.performance_improvement))
            
            return recommendations[:10]  # Return top 10 recommendations
            
        except Exception as e:
            logger.error(f"Error generating upgrade recommendations: {e}")
            return []
    
    async def _generate_component_recommendation(self, config: SystemConfiguration,
                                               bottleneck: PerformanceBottleneck,
                                               usage_patterns: Dict[str, float],
                                               budget: Optional[float]) -> Optional[UpgradeRecommendation]:
        """Generate recommendation for specific component bottleneck"""
        
        component_type = bottleneck.component_type
        current_component = self._get_current_component(config, component_type)
        
        if not current_component:
            return None
        
        # Search for better components
        search_filters = self._build_search_filters(current_component, budget, usage_patterns)
        candidates = self.hardware_db.search_components(component_type, search_filters)
        
        # Filter out components that aren't significantly better
        better_candidates = [
            comp for comp in candidates 
            if comp.performance_score > current_component.performance_score + 10
        ]
        
        if not better_candidates:
            return None
        
        # Select top recommendations
        recommended_components = better_candidates[:3]
        best_component = recommended_components[0]
        
        # Calculate metrics
        performance_improvement = self._calculate_performance_improvement(
            current_component, best_component, bottleneck
        )
        
        compatibility_score = await self._check_compatibility(config, best_component)
        estimated_cost = best_component.current_price or 0
        
        # Determine urgency
        urgency = self._determine_urgency(bottleneck, current_component, usage_patterns)
        
        # Cost-benefit analysis
        cost_benefit_ratio = performance_improvement / max(estimated_cost, 1) * 100
        
        # Future-proofing estimate
        future_proof_years = self._estimate_future_proofing(best_component, usage_patterns)
        
        # Installation difficulty
        installation_difficulty = self._assess_installation_difficulty(component_type, config)
        
        # Power and thermal requirements
        power_requirements = self._analyze_power_requirements(config, best_component)
        thermal_considerations = self._analyze_thermal_requirements(config, best_component)
        
        # Generate justification
        justification = self._generate_justification(
            bottleneck, current_component, best_component, performance_improvement
        )
        
        # Generate alternatives
        alternatives = self._generate_alternatives(component_type, current_component, budget)
        
        return UpgradeRecommendation(
            component_type=component_type,
            current_component=current_component,
            recommended_components=recommended_components,
            upgrade_type=UpgradeType.REPLACEMENT,
            urgency=urgency,
            estimated_cost=estimated_cost,
            performance_improvement=performance_improvement,
            compatibility_score=compatibility_score,
            future_proof_years=future_proof_years,
            cost_benefit_ratio=cost_benefit_ratio,
            installation_difficulty=installation_difficulty,
            power_requirements=power_requirements,
            thermal_considerations=thermal_considerations,
            justification=justification,
            alternatives=alternatives
        )
    
    def _get_current_component(self, config: SystemConfiguration, 
                              component_type: ComponentType) -> Optional[HardwareComponent]:
        """Get current component of specified type"""
        if component_type == ComponentType.CPU:
            return config.cpu
        elif component_type == ComponentType.GPU:
            return config.gpu
        elif component_type == ComponentType.RAM:
            return config.ram
        elif component_type == ComponentType.STORAGE:
            return config.storage[0] if config.storage else None
        elif component_type == ComponentType.MOTHERBOARD:
            return config.motherboard
        elif component_type == ComponentType.POWER_SUPPLY:
            return config.power_supply
        return None
    
    def _build_search_filters(self, current_component: HardwareComponent,
                             budget: Optional[float],
                             usage_patterns: Dict[str, float]) -> Dict[str, Any]:
        """Build search filters for component upgrades"""
        filters = {}
        
        # Budget filter
        if budget:
            filters["max_price"] = budget
        
        # Performance filter - must be significantly better
        filters["min_performance"] = current_component.performance_score + 10
        
        # Age filter - prefer newer components
        filters["max_age"] = 2.0
        
        # Component-specific filters
        if current_component.component_type == ComponentType.CPU:
            # Prefer same or newer socket if possible
            current_socket = current_component.specifications.get("socket")
            if current_socket:
                filters["socket"] = current_socket
        
        elif current_component.component_type == ComponentType.RAM:
            # RAM type compatibility
            current_type = current_component.specifications.get("type", "DDR4")
            filters["type"] = current_type
            
            # Capacity requirements based on usage
            if usage_patterns.get("memory_intensive_tasks", 0.0) > 0.5:
                filters["capacity_gb"] = {"min": 32}
            else:
                filters["capacity_gb"] = {"min": 16}
        
        elif current_component.component_type == ComponentType.GPU:
            # VRAM requirements
            if usage_patterns.get("high_resolution_gaming", 0.0) > 0.5:
                filters["memory_gb"] = {"min": 12}
            elif usage_patterns.get("gaming", 0.0) > 0.3:
                filters["memory_gb"] = {"min": 8}
        
        return filters
    
    def _calculate_performance_improvement(self, current: HardwareComponent,
                                         recommended: HardwareComponent,
                                         bottleneck: PerformanceBottleneck) -> float:
        """Calculate expected performance improvement"""
        # Base improvement from performance scores
        score_improvement = recommended.performance_score - current.performance_score
        base_improvement = score_improvement / current.performance_score * 100
        
        # Adjust based on bottleneck severity and impact
        severity_multiplier = {
            BottleneckSeverity.CRITICAL: 1.5,
            BottleneckSeverity.MAJOR: 1.2,
            BottleneckSeverity.MODERATE: 1.0,
            BottleneckSeverity.MINOR: 0.7
        }
        
        adjusted_improvement = base_improvement * severity_multiplier[bottleneck.severity]
        
        # Cap realistic improvement based on bottleneck impact
        max_improvement = bottleneck.impact_percentage * 2
        
        return min(adjusted_improvement, max_improvement)
    
    async def _check_compatibility(self, config: SystemConfiguration, 
                                 component: HardwareComponent) -> float:
        """Check compatibility score for component with current system"""
        compatibility_score = 1.0
        issues = []
        
        if component.component_type == ComponentType.CPU:
            # Check socket compatibility
            current_socket = config.motherboard.specifications.get("socket")
            new_socket = component.specifications.get("socket")
            
            if current_socket != new_socket:
                compatibility_score -= 0.5
                issues.append("Requires motherboard upgrade")
            
            # Check RAM compatibility
            if "DDR5" in component.specifications.get("memory_support", ""):
                if config.ram.specifications.get("type") == "DDR4":
                    compatibility_score -= 0.2
                    issues.append("May require RAM upgrade for optimal performance")
        
        elif component.component_type == ComponentType.GPU:
            # Check power supply compatibility
            gpu_power = component.power_consumption or 0
            psu_capacity = config.power_supply.specifications.get("wattage", 500)
            
            # Estimate total system power
            estimated_total = gpu_power + 200  # Rough estimate for rest of system
            
            if estimated_total > psu_capacity * 0.8:  # 80% PSU load limit
                compatibility_score -= 0.3
                issues.append("May require power supply upgrade")
            
            # Check physical clearance (simplified)
            gpu_length = component.specifications.get("length_mm", 250)
            if gpu_length > 300:  # Assume case limit
                compatibility_score -= 0.1
                issues.append("Verify GPU clearance in case")
        
        elif component.component_type == ComponentType.RAM:
            # Check motherboard support
            mb_max_ram = config.motherboard.specifications.get("max_ram_gb", 64)
            new_ram_capacity = component.specifications.get("capacity_gb", 16)
            
            if new_ram_capacity > mb_max_ram:
                compatibility_score -= 0.4
                issues.append("Exceeds motherboard maximum RAM capacity")
        
        return max(0.0, compatibility_score)
    
    def _determine_urgency(self, bottleneck: PerformanceBottleneck,
                          current_component: HardwareComponent,
                          usage_patterns: Dict[str, float]) -> UpgradeUrgency:
        """Determine upgrade urgency"""
        
        if bottleneck.severity == BottleneckSeverity.CRITICAL:
            return UpgradeUrgency.CRITICAL
        
        if bottleneck.severity == BottleneckSeverity.MAJOR:
            if current_component.age_years > 4:
                return UpgradeUrgency.HIGH
            return UpgradeUrgency.MEDIUM
        
        if bottleneck.severity == BottleneckSeverity.MODERATE:
            if any(usage_patterns.get(use_case, 0) > 0.7 for use_case in bottleneck.affected_use_cases):
                return UpgradeUrgency.MEDIUM
            return UpgradeUrgency.LOW
        
        return UpgradeUrgency.LOW
    
    def _estimate_future_proofing(self, component: HardwareComponent,
                                 usage_patterns: Dict[str, float]) -> int:
        """Estimate how many years component will remain relevant"""
        
        # Base future-proofing from performance score
        if component.performance_score > 90:
            base_years = 5
        elif component.performance_score > 80:
            base_years = 4
        elif component.performance_score > 70:
            base_years = 3
        else:
            base_years = 2
        
        # Adjust for component type and specifications
        if component.component_type == ComponentType.GPU:
            vram_gb = component.specifications.get("memory_gb", 8)
            if vram_gb >= 16:
                base_years += 1
            elif vram_gb < 8:
                base_years -= 1
        
        elif component.component_type == ComponentType.CPU:
            cores = component.specifications.get("cores", 4)
            if cores >= 12:
                base_years += 1
            elif cores < 6:
                base_years -= 1
        
        elif component.component_type == ComponentType.RAM:
            ram_type = component.specifications.get("type", "DDR4")
            if ram_type == "DDR5":
                base_years += 1
        
        return max(1, base_years)
    
    def _assess_installation_difficulty(self, component_type: ComponentType,
                                       config: SystemConfiguration) -> str:
        """Assess installation difficulty"""
        
        if component_type == ComponentType.CPU:
            return "Moderate - Requires thermal paste application and careful handling"
        elif component_type == ComponentType.GPU:
            return "Easy - Simple PCIe slot installation"
        elif component_type == ComponentType.RAM:
            return "Easy - Simple slot installation"
        elif component_type == ComponentType.STORAGE:
            return "Easy to Moderate - Depends on drive type and available slots"
        elif component_type == ComponentType.MOTHERBOARD:
            return "Difficult - Requires complete system disassembly"
        elif component_type == ComponentType.POWER_SUPPLY:
            return "Moderate - Requires cable management"
        
        return "Moderate"
    
    def _analyze_power_requirements(self, config: SystemConfiguration,
                                  component: HardwareComponent) -> Dict[str, Any]:
        """Analyze power requirements for new component"""
        
        current_psu_wattage = config.power_supply.specifications.get("wattage", 500)
        component_power = component.power_consumption or 0
        
        # Estimate current system power consumption
        current_total_power = (
            config.cpu.power_consumption +
            (config.gpu.power_consumption if config.gpu else 0) +
            config.ram.specifications.get("power_consumption", 10) +
            sum(storage.specifications.get("power_consumption", 5) for storage in config.storage) +
            50  # Motherboard, fans, etc.
        )
        
        # Calculate new power consumption
        if component.component_type == ComponentType.CPU:
            new_total_power = current_total_power - config.cpu.power_consumption + component_power
        elif component.component_type == ComponentType.GPU:
            current_gpu_power = config.gpu.power_consumption if config.gpu else 0
            new_total_power = current_total_power - current_gpu_power + component_power
        else:
            new_total_power = current_total_power + component_power
        
        power_headroom = current_psu_wattage - new_total_power
        utilization = new_total_power / current_psu_wattage
        
        return {
            "current_psu_wattage": current_psu_wattage,
            "estimated_new_consumption": new_total_power,
            "power_headroom": power_headroom,
            "psu_utilization": utilization,
            "psu_upgrade_needed": utilization > 0.8,
            "recommended_psu_wattage": int(new_total_power * 1.3) if utilization > 0.8 else None
        }
    
    def _analyze_thermal_requirements(self, config: SystemConfiguration,
                                    component: HardwareComponent) -> Dict[str, Any]:
        """Analyze thermal requirements for new component"""
        
        component_tdp = component.thermal_design_power or component.power_consumption or 0
        
        thermal_considerations = {
            "component_tdp": component_tdp,
            "cooling_requirement": "adequate",
            "case_airflow_important": False,
            "cpu_cooler_upgrade": False
        }
        
        if component.component_type == ComponentType.CPU:
            if component_tdp > 125:
                thermal_considerations["cooling_requirement"] = "high_performance"
                thermal_considerations["cpu_cooler_upgrade"] = True
                thermal_considerations["case_airflow_important"] = True
            elif component_tdp > 95:
                thermal_considerations["cooling_requirement"] = "performance"
                thermal_considerations["case_airflow_important"] = True
        
        elif component.component_type == ComponentType.GPU:
            if component_tdp > 250:
                thermal_considerations["cooling_requirement"] = "high_performance"
                thermal_considerations["case_airflow_important"] = True
        
        return thermal_considerations
    
    def _generate_justification(self, bottleneck: PerformanceBottleneck,
                               current: HardwareComponent,
                               recommended: HardwareComponent,
                               improvement: float) -> str:
        """Generate justification text for upgrade recommendation"""
        
        justification_parts = []
        
        # Bottleneck justification
        justification_parts.append(f"Current {bottleneck.component_type.value} is creating a {bottleneck.severity.value} bottleneck, limiting performance by {bottleneck.impact_percentage:.1f}%.")
        
        # Age justification
        if current.age_years > 3:
            justification_parts.append(f"The current {current.model} is {current.age_years:.1f} years old and showing its age.")
        
        # Performance justification
        justification_parts.append(f"Upgrading to {recommended.model} would provide an estimated {improvement:.1f}% performance improvement.")
        
        # Use case justification
        if bottleneck.affected_use_cases:
            use_cases_str = ", ".join(bottleneck.affected_use_cases)
            justification_parts.append(f"This upgrade would particularly benefit: {use_cases_str}.")
        
        return " ".join(justification_parts)
    
    def _generate_alternatives(self, component_type: ComponentType,
                              current: HardwareComponent,
                              budget: Optional[float]) -> List[str]:
        """Generate alternative solutions"""
        
        alternatives = []
        
        if component_type == ComponentType.CPU:
            alternatives.extend([
                "Overclock current CPU if thermally feasible",
                "Optimize software and background processes",
                "Consider used/refurbished CPU options"
            ])
        
        elif component_type == ComponentType.GPU:
            alternatives.extend([
                "Lower game settings to reduce GPU load",
                "Consider previous generation GPU for better value",
                "Wait for next generation releases for price drops"
            ])
        
        elif component_type == ComponentType.RAM:
            alternatives.extend([
                "Add more RAM modules if slots available",
                "Optimize memory usage and close unnecessary programs",
                "Consider faster RAM speed instead of more capacity"
            ])
        
        elif component_type == ComponentType.STORAGE:
            alternatives.extend([
                "Add SSD as secondary drive instead of replacing",
                "Clean up existing storage to free space",
                "Use external storage for less frequently accessed files"
            ])
        
        if budget:
            alternatives.append(f"Wait and save for higher-end option within ${budget:.0f} budget")
        
        return alternatives
    
    async def _generate_proactive_recommendations(self, config: SystemConfiguration,
                                                usage_patterns: Dict[str, float],
                                                budget: Optional[float]) -> List[UpgradeRecommendation]:
        """Generate proactive upgrade recommendations for future-proofing"""
        
        proactive_recs = []
        
        # Check for components nearing end of life
        components_to_check = [
            (ComponentType.CPU, config.cpu),
            (ComponentType.GPU, config.gpu),
            (ComponentType.RAM, config.ram)
        ]
        
        for comp_type, component in components_to_check:
            if component and component.age_years > 3 and component.performance_score < 80:
                # This component will likely need replacement soon
                candidates = self.hardware_db.search_components(
                    comp_type, 
                    {"min_performance": component.performance_score + 15, "max_age": 1.0}
                )
                
                if candidates and (not budget or candidates[0].current_price <= budget):
                    proactive_recs.append(UpgradeRecommendation(
                        component_type=comp_type,
                        current_component=component,
                        recommended_components=candidates[:3],
                        upgrade_type=UpgradeType.REPLACEMENT,
                        urgency=UpgradeUrgency.LOW,
                        estimated_cost=candidates[0].current_price or 0,
                        performance_improvement=15.0,
                        compatibility_score=0.9,
                        future_proof_years=4,
                        cost_benefit_ratio=20.0,
                        installation_difficulty="Moderate",
                        power_requirements={},
                        thermal_considerations={},
                        justification=f"Proactive upgrade to prevent future bottleneck as {component.model} ages"
                    ))
        
        return proactive_recs

class CostBenefitCalculator:
    """Calculate cost-benefit analysis for upgrade recommendations"""
    
    async def analyze_upgrade_value(self, recommendation: UpgradeRecommendation,
                                   user_profile: Dict[str, Any]) -> CostBenefitAnalysis:
        """Perform comprehensive cost-benefit analysis"""
        
        try:
            upgrade_cost = recommendation.estimated_cost
            performance_gain = recommendation.performance_improvement
            
            # Calculate productivity improvement
            productivity_improvement = self._calculate_productivity_improvement(
                recommendation, user_profile
            )
            
            # Calculate longevity extension
            longevity_extension = self._calculate_longevity_extension(recommendation)
            
            # Calculate total value score
            total_value_score = self._calculate_total_value_score(
                performance_gain, productivity_improvement, longevity_extension, upgrade_cost
            )
            
            # Calculate payback period
            payback_period = self._calculate_payback_period(
                upgrade_cost, productivity_improvement, user_profile
            )
            
            # Generate comparison alternatives
            alternatives = await self._generate_cost_alternatives(recommendation)
            
            return CostBenefitAnalysis(
                upgrade_cost=upgrade_cost,
                performance_gain=performance_gain,
                productivity_improvement=productivity_improvement,
                longevity_extension_years=longevity_extension,
                total_value_score=total_value_score,
                payback_period_months=payback_period,
                comparison_alternatives=alternatives
            )
            
        except Exception as e:
            logger.error(f"Error in cost-benefit analysis: {e}")
            return CostBenefitAnalysis(
                upgrade_cost=recommendation.estimated_cost,
                performance_gain=recommendation.performance_improvement,
                productivity_improvement=0.0,
                longevity_extension_years=recommendation.future_proof_years,
                total_value_score=0.0,
                payback_period_months=None
            )
    
    def _calculate_productivity_improvement(self, recommendation: UpgradeRecommendation,
                                          user_profile: Dict[str, Any]) -> float:
        """Calculate productivity improvement from upgrade"""
        
        base_productivity_gain = recommendation.performance_improvement * 0.3
        
        # Adjust based on user's work type
        work_type = user_profile.get("work_type", "general")
        
        multipliers = {
            "content_creator": 1.5,
            "developer": 1.3,
            "gamer": 0.8,
            "office_worker": 0.6,
            "student": 0.7,
            "designer": 1.4
        }
        
        multiplier = multipliers.get(work_type, 1.0)
        
        # Adjust based on component type
        component_productivity_impact = {
            ComponentType.CPU: 1.2,
            ComponentType.GPU: 0.8,
            ComponentType.RAM: 1.0,
            ComponentType.STORAGE: 1.1
        }
        
        component_multiplier = component_productivity_impact.get(
            recommendation.component_type, 1.0
        )
        
        return base_productivity_gain * multiplier * component_multiplier
    
    def _calculate_longevity_extension(self, recommendation: UpgradeRecommendation) -> int:
        """Calculate how much longer the system will remain viable"""
        
        base_extension = recommendation.future_proof_years
        
        # Adjust based on performance improvement
        if recommendation.performance_improvement > 30:
            base_extension += 1
        elif recommendation.performance_improvement > 50:
            base_extension += 2
        
        # Adjust based on component type
        if recommendation.component_type in [ComponentType.CPU, ComponentType.GPU]:
            base_extension += 1  # Core components have bigger impact on longevity
        
        return min(base_extension, 6)  # Cap at 6 years
    
    def _calculate_total_value_score(self, performance_gain: float,
                                   productivity_improvement: float,
                                   longevity_extension: int,
                                   cost: float) -> float:
        """Calculate overall value score"""
        
        # Normalize components
        performance_value = performance_gain / 10  # 10% performance = 1 point
        productivity_value = productivity_improvement / 5  # 5% productivity = 1 point
        longevity_value = longevity_extension * 2  # 1 year = 2 points
        cost_penalty = cost / 100  # $100 = 1 penalty point
        
        total_value = performance_value + productivity_value + longevity_value - cost_penalty
        
        return max(0, total_value)
    
    def _calculate_payback_period(self, cost: float, productivity_improvement: float,
                                 user_profile: Dict[str, Any]) -> Optional[int]:
        """Calculate payback period in months"""
        
        if productivity_improvement <= 0:
            return None
        
        # Estimate monthly value from productivity improvement
        hourly_rate = user_profile.get("hourly_rate", 25)  # Default $25/hour
        hours_per_month = user_profile.get("work_hours_per_month", 160)  # ~40 hours/week
        
        monthly_productivity_value = (
            hourly_rate * hours_per_month * (productivity_improvement / 100)
        )
        
        if monthly_productivity_value <= 0:
            return None
        
        payback_months = cost / monthly_productivity_value
        
        return int(payback_months) if payback_months <= 60 else None  # Cap at 5 years
    
    async def _generate_cost_alternatives(self, recommendation: UpgradeRecommendation) -> List[Dict[str, Any]]:
        """Generate cost alternative analysis"""
        
        alternatives = []
        
        # Used/refurbished option
        used_price = recommendation.estimated_cost * 0.7
        alternatives.append({
            "option": "Used/Refurbished",
            "cost": used_price,
            "performance_gain": recommendation.performance_improvement * 0.9,
            "risk_factor": "Medium - No warranty, unknown history",
            "value_score": recommendation.performance_improvement * 0.9 / (used_price / 100)
        })
        
        # Previous generation option
        prev_gen_price = recommendation.estimated_cost * 0.8
        alternatives.append({
            "option": "Previous Generation",
            "cost": prev_gen_price,
            "performance_gain": recommendation.performance_improvement * 0.8,
            "risk_factor": "Low - New with warranty",
            "value_score": recommendation.performance_improvement * 0.8 / (prev_gen_price / 100)
        })
        
        # Wait for sales option
        sale_price = recommendation.estimated_cost * 0.85
        alternatives.append({
            "option": "Wait for Sales/Price Drop",
            "cost": sale_price,
            "performance_gain": recommendation.performance_improvement,
            "risk_factor": "Low - Timing uncertainty",
            "value_score": recommendation.performance_improvement / (sale_price / 100)
        })
        
        return alternatives

class HardwareUpgradeGuidance:
    """Main hardware upgrade guidance system"""
    
    def __init__(self):
        self.hardware_db = HardwareDatabase()
        self.recommendation_engine = UpgradeRecommendationEngine(self.hardware_db)
        self.cost_benefit_calculator = CostBenefitCalculator()
        
        # User system tracking
        self.user_systems: Dict[str, SystemConfiguration] = {}
        self.user_profiles: Dict[str, Dict[str, Any]] = {}
        
        logger.info("Hardware Upgrade Guidance system initialized")
    
    async def analyze_system(self, user_id: str, system_config: SystemConfiguration,
                           usage_patterns: Dict[str, float],
                           user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Perform comprehensive system analysis"""
        
        try:
            # Store user data
            self.user_systems[user_id] = system_config
            self.user_profiles[user_id] = user_profile
            
            # Get budget from user profile
            budget = user_profile.get("upgrade_budget")
            priorities = user_profile.get("upgrade_priorities", [])
            
            # Generate recommendations
            recommendations = await self.recommendation_engine.generate_recommendations(
                system_config, usage_patterns, budget, priorities
            )
            
            # Perform cost-benefit analysis for top recommendations
            detailed_recommendations = []
            for rec in recommendations[:5]:  # Top 5 recommendations
                cost_benefit = await self.cost_benefit_calculator.analyze_upgrade_value(
                    rec, user_profile
                )
                
                detailed_rec = {
                    "component_type": rec.component_type.value,
                    "current_component": {
                        "model": rec.current_component.model,
                        "performance_score": rec.current_component.performance_score,
                        "age_years": rec.current_component.age_years
                    },
                    "recommended_component": {
                        "model": rec.recommended_components[0].model,
                        "performance_score": rec.recommended_components[0].performance_score,
                        "price": rec.recommended_components[0].current_price
                    },
                    "upgrade_analysis": {
                        "urgency": rec.urgency.value,
                        "estimated_cost": rec.estimated_cost,
                        "performance_improvement": rec.performance_improvement,
                        "compatibility_score": rec.compatibility_score,
                        "future_proof_years": rec.future_proof_years,
                        "installation_difficulty": rec.installation_difficulty,
                        "justification": rec.justification
                    },
                    "cost_benefit": asdict(cost_benefit),
                    "power_requirements": rec.power_requirements,
                    "thermal_considerations": rec.thermal_considerations,
                    "alternatives": rec.alternatives
                }
                
                detailed_recommendations.append(detailed_rec)
            
            # Generate system overview
            system_overview = await self._generate_system_overview(system_config, usage_patterns)
            
            # Generate timeline recommendations
            upgrade_timeline = await self._generate_upgrade_timeline(recommendations, user_profile)
            
            return {
                "user_id": user_id,
                "analysis_date": datetime.now().isoformat(),
                "system_overview": system_overview,
                "upgrade_recommendations": detailed_recommendations,
                "upgrade_timeline": upgrade_timeline,
                "total_estimated_cost": sum(rec.estimated_cost for rec in recommendations[:3]),
                "priority_upgrades": [rec for rec in detailed_recommendations if rec["upgrade_analysis"]["urgency"] in ["high", "critical"]],
                "budget_analysis": await self._analyze_budget_options(recommendations, budget) if budget else None
            }
            
        except Exception as e:
            logger.error(f"Error analyzing system: {e}")
            return {"error": str(e)}
    
    async def _generate_system_overview(self, config: SystemConfiguration,
                                      usage_patterns: Dict[str, float]) -> Dict[str, Any]:
        """Generate system overview and health assessment"""
        
        # Calculate overall system score
        component_scores = [
            config.cpu.performance_score * 0.3,
            (config.gpu.performance_score if config.gpu else 0) * 0.25,
            config.ram.performance_score * 0.15,
            (config.storage[0].performance_score if config.storage else 0) * 0.15,
            config.motherboard.performance_score * 0.1,
            config.power_supply.performance_score * 0.05
        ]
        
        overall_score = sum(score for score in component_scores if score > 0)
        
        # Calculate system age
        components_with_age = [comp for comp in [config.cpu, config.gpu, config.ram] + config.storage if comp]
        avg_age = np.mean([comp.age_years for comp in components_with_age]) if components_with_age else 0
        
        # Determine system category
        if overall_score >= 85:
            system_category = "High-End Gaming/Workstation"
        elif overall_score >= 70:
            system_category = "Mid-Range Performance"
        elif overall_score >= 55:
            system_category = "Budget/Entry-Level"
        else:
            system_category = "Legacy System"
        
        return {
            "overall_score": overall_score,
            "system_category": system_category,
            "average_age_years": avg_age,
            "components_summary": {
                "cpu": {"model": config.cpu.model, "score": config.cpu.performance_score},
                "gpu": {"model": config.gpu.model, "score": config.gpu.performance_score} if config.gpu else None,
                "ram": {"model": config.ram.model, "capacity_gb": config.ram.specifications.get("capacity_gb")},
                "storage": [{"model": storage.model, "capacity_gb": storage.specifications.get("capacity_gb")} for storage in config.storage]
            },
            "system_strengths": await self._identify_system_strengths(config),
            "system_weaknesses": await self._identify_system_weaknesses(config, usage_patterns)
        }
    
    async def _identify_system_strengths(self, config: SystemConfiguration) -> List[str]:
        """Identify system strengths"""
        strengths = []
        
        if config.cpu.performance_score >= 85:
            strengths.append(f"Excellent CPU performance ({config.cpu.model})")
        
        if config.gpu and config.gpu.performance_score >= 85:
            strengths.append(f"High-end graphics capability ({config.gpu.model})")
        
        if config.ram.specifications.get("capacity_gb", 0) >= 32:
            strengths.append("Ample RAM capacity for demanding tasks")
        
        if any(storage.specifications.get("interface", "").startswith("NVMe") for storage in config.storage):
            strengths.append("Fast NVMe storage for quick load times")
        
        return strengths
    
    async def _identify_system_weaknesses(self, config: SystemConfiguration,
                                        usage_patterns: Dict[str, float]) -> List[str]:
        """Identify system weaknesses"""
        weaknesses = []
        
        if config.cpu.performance_score < 60:
            weaknesses.append(f"CPU performance is below modern standards ({config.cpu.model})")
        
        if not config.gpu and usage_patterns.get("gaming", 0.0) > 0.3:
            weaknesses.append("No discrete GPU for gaming workloads")
        elif config.gpu and config.gpu.performance_score < 60:
            weaknesses.append("GPU performance is limiting graphics capabilities")
        
        if config.ram.specifications.get("capacity_gb", 0) < 16:
            weaknesses.append("RAM capacity may be insufficient for modern applications")
        
        if all(storage.specifications.get("interface", "").startswith("SATA") for storage in config.storage):
            weaknesses.append("Storage bottleneck - consider NVMe upgrade")
        
        return weaknesses
    
    async def _generate_upgrade_timeline(self, recommendations: List[UpgradeRecommendation],
                                       user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Generate recommended upgrade timeline"""
        
        budget = user_profile.get("upgrade_budget", 1000)
        timeline = {
            "immediate": [],
            "short_term": [],  # 3-6 months
            "medium_term": [],  # 6-12 months
            "long_term": []     # 1-2 years
        }
        
        total_cost = 0
        
        for rec in recommendations:
            if rec.urgency == UpgradeUrgency.CRITICAL:
                timeline["immediate"].append({
                    "component": rec.component_type.value,
                    "cost": rec.estimated_cost,
                    "reason": "Critical performance bottleneck"
                })
                total_cost += rec.estimated_cost
            
            elif rec.urgency == UpgradeUrgency.HIGH and total_cost + rec.estimated_cost <= budget:
                timeline["short_term"].append({
                    "component": rec.component_type.value,
                    "cost": rec.estimated_cost,
                    "reason": "High impact upgrade within budget"
                })
                total_cost += rec.estimated_cost
            
            elif rec.urgency == UpgradeUrgency.MEDIUM:
                timeline["medium_term"].append({
                    "component": rec.component_type.value,
                    "cost": rec.estimated_cost,
                    "reason": "Performance improvement opportunity"
                })
            
            else:
                timeline["long_term"].append({
                    "component": rec.component_type.value,
                    "cost": rec.estimated_cost,
                    "reason": "Future-proofing consideration"
                })
        
        return timeline
    
    async def _analyze_budget_options(self, recommendations: List[UpgradeRecommendation],
                                    budget: float) -> Dict[str, Any]:
        """Analyze upgrade options within budget"""
        
        # Sort by cost-benefit ratio
        sorted_recs = sorted(recommendations, key=lambda x: x.cost_benefit_ratio, reverse=True)
        
        budget_options = []
        remaining_budget = budget
        
        for rec in sorted_recs:
            if rec.estimated_cost <= remaining_budget:
                budget_options.append({
                    "component": rec.component_type.value,
                    "cost": rec.estimated_cost,
                    "performance_gain": rec.performance_improvement,
                    "cost_benefit_ratio": rec.cost_benefit_ratio
                })
                remaining_budget -= rec.estimated_cost
        
        return {
            "budget": budget,
            "recommended_upgrades": budget_options,
            "total_cost": budget - remaining_budget,
            "remaining_budget": remaining_budget,
            "max_performance_gain": sum(opt["performance_gain"] for opt in budget_options)
        }

# Usage example
async def main():
    """Example usage of Hardware Upgrade Guidance"""
    
    guidance = HardwareUpgradeGuidance()
    
    # Create sample system configuration
    cpu = HardwareComponent(
        component_type=ComponentType.CPU,
        model="Intel Core i5-8400",
        manufacturer="Intel",
        specifications={"cores": 6, "threads": 6, "base_clock": 2.8},
        performance_score=65.0,
        age_years=4.5,
        current_price=200.0
    )
    
    gpu = HardwareComponent(
        component_type=ComponentType.GPU,
        model="NVIDIA GTX 1060 6GB",
        manufacturer="NVIDIA",
        specifications={"memory_gb": 6, "cuda_cores": 1280},
        performance_score=58.0,
        age_years=5.0,
        current_price=250.0
    )
    
    ram = HardwareComponent(
        component_type=ComponentType.RAM,
        model="Generic DDR4-2400 16GB",
        manufacturer="Generic",
        specifications={"capacity_gb": 16, "speed": 2400, "type": "DDR4"},
        performance_score=60.0,
        age_years=4.0,
        current_price=80.0
    )
    
    storage = HardwareComponent(
        component_type=ComponentType.STORAGE,
        model="WD Blue 1TB HDD",
        manufacturer="Western Digital",
        specifications={"capacity_gb": 1000, "interface": "SATA", "read_speed": 150},
        performance_score=45.0,
        age_years=5.0,
        current_price=50.0
    )
    
    motherboard = HardwareComponent(
        component_type=ComponentType.MOTHERBOARD,
        model="Generic B360",
        manufacturer="Generic",
        specifications={"socket": "LGA1151", "max_ram_gb": 64},
        performance_score=70.0,
        age_years=4.5,
        current_price=100.0
    )
    
    psu = HardwareComponent(
        component_type=ComponentType.POWER_SUPPLY,
        model="Generic 600W 80+ Bronze",
        manufacturer="Generic",
        specifications={"wattage": 600, "efficiency": "80+ Bronze"},
        performance_score=65.0,
        age_years=4.5,
        current_price=70.0
    )
    
    system_config = SystemConfiguration(
        cpu=cpu,
        gpu=gpu,
        ram=ram,
        storage=[storage],
        motherboard=motherboard,
        power_supply=psu
    )
    
    # Sample usage patterns
    usage_patterns = {
        "gaming": 0.7,
        "productivity": 0.4,
        "content_creation": 0.3,
        "cpu_intensive_tasks": 0.5,
        "gpu_intensive_tasks": 0.6,
        "memory_intensive_tasks": 0.3,
        "storage_intensive_tasks": 0.4
    }
    
    # Sample user profile
    user_profile = {
        "work_type": "gamer",
        "upgrade_budget": 800.0,
        "hourly_rate": 25,
        "upgrade_priorities": ["gaming_performance", "future_proofing"]
    }
    
    print("Analyzing system for upgrade recommendations...")
    analysis = await guidance.analyze_system("user123", system_config, usage_patterns, user_profile)
    
    print(f"System Overview: {analysis['system_overview']['system_category']}")
    print(f"Overall Score: {analysis['system_overview']['overall_score']:.1f}/100")
    print(f"Number of Recommendations: {len(analysis['upgrade_recommendations'])}")
    
    for i, rec in enumerate(analysis['upgrade_recommendations'][:3], 1):
        print(f"\n{i}. {rec['component_type'].upper()} Upgrade:")
        print(f"   Current: {rec['current_component']['model']}")
        print(f"   Recommended: {rec['recommended_component']['model']}")
        print(f"   Cost: ${rec['upgrade_analysis']['estimated_cost']:.0f}")
        print(f"   Performance Gain: {rec['upgrade_analysis']['performance_improvement']:.1f}%")
        print(f"   Urgency: {rec['upgrade_analysis']['urgency']}")

if __name__ == "__main__":
    asyncio.run(main())