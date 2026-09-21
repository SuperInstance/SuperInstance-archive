#!/usr/bin/env python3
"""
SLA Scheduler for ActiveLog Compute Tiers
Intelligent instance selection based on Service Level Agreement requirements
"""

import boto3
import json
import logging
import math
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)

class SLALevel(Enum):
    """SLA service levels"""
    PLATINUM = "platinum"  # 99.99% uptime, <1ms latency
    GOLD = "gold"          # 99.9% uptime, <5ms latency
    SILVER = "silver"      # 99.5% uptime, <10ms latency
    BRONZE = "bronze"      # 99.0% uptime, <50ms latency
    BASIC = "basic"        # 95.0% uptime, best effort

class AvailabilityZoneClass(Enum):
    """Availability zone reliability classes"""
    PREMIUM = "premium"    # Highest reliability
    STANDARD = "standard"  # Normal reliability
    ECONOMY = "economy"    # Lower cost, potentially less reliable

class InstanceReliabilityTier(Enum):
    """Instance reliability tiers"""
    MISSION_CRITICAL = "mission_critical"
    HIGH_AVAILABILITY = "high_availability"
    STANDARD = "standard"
    BEST_EFFORT = "best_effort"

@dataclass
class SLARequirement:
    """SLA requirement specification"""
    sla_level: SLALevel
    uptime_requirement_percent: float
    max_latency_ms: float
    max_downtime_minutes_per_month: float
    availability_zones_required: int
    backup_instance_required: bool
    auto_failover_required: bool
    data_durability_requirement: str  # "11-nines", "9-nines", "standard"
    compliance_requirements: List[str]
    monitoring_interval_seconds: int
    notification_channels: List[str]

@dataclass
class WorkloadCharacteristics:
    """Workload characteristics affecting SLA"""
    workload_id: str
    workload_name: str
    criticality_level: str  # "critical", "important", "standard", "low"
    expected_load_pattern: str  # "steady", "bursty", "seasonal", "unpredictable"
    fault_tolerance: str  # "none", "low", "medium", "high"
    recovery_time_objective_minutes: int  # RTO
    recovery_point_objective_minutes: int  # RPO
    data_locality_constraints: List[str]
    regulatory_requirements: List[str]
    peak_concurrent_users: int
    average_request_rate: float
    data_volume_gb: float

@dataclass
class InstanceSLACapability:
    """SLA capabilities of an instance configuration"""
    instance_type: str
    estimated_uptime_percent: float
    avg_latency_ms: float
    failover_time_seconds: float
    backup_availability: bool
    multi_az_support: bool
    compliance_certifications: List[str]
    monitoring_capabilities: List[str]
    auto_recovery_features: List[str]
    cost_per_hour: float
    reliability_score: float

@dataclass
class SLASelection:
    """SLA-based instance selection result"""
    workload_id: str
    selected_instances: List[Dict[str, Any]]
    availability_zones: List[str]
    sla_compliance_score: float
    estimated_uptime_percent: float
    estimated_cost_monthly: float
    backup_configuration: Dict[str, Any]
    monitoring_configuration: Dict[str, Any]
    failover_configuration: Dict[str, Any]
    compliance_status: Dict[str, bool]
    risk_assessment: Dict[str, Any]
    recommendations: List[str]

class SLAScheduler:
    """Schedules instances based on SLA requirements"""
    
    def __init__(self, ec2_client, cloudwatch_client):
        self.ec2 = ec2_client
        self.cloudwatch = cloudwatch_client
        
        # Instance SLA capabilities database
        self.instance_sla_capabilities = self._build_sla_capabilities_database()
        
        # Availability zone reliability data
        self.az_reliability = self._initialize_az_reliability()
        
        # SLA templates
        self.sla_templates = self._define_sla_templates()
        
        # Compliance certifications by instance family
        self.compliance_certifications = {
            'c5': ['SOC2', 'PCI-DSS', 'HIPAA', 'ISO27001'],
            'c5n': ['SOC2', 'PCI-DSS', 'HIPAA', 'ISO27001', 'FedRAMP'],
            'm5': ['SOC2', 'PCI-DSS', 'HIPAA', 'ISO27001'],
            'r5': ['SOC2', 'PCI-DSS', 'HIPAA', 'ISO27001'],
            'i3': ['SOC2', 'PCI-DSS', 'ISO27001'],
            'p3': ['SOC2', 'ISO27001'],
            'g4dn': ['SOC2', 'ISO27001'],
            'x1e': ['SOC2', 'PCI-DSS', 'HIPAA', 'ISO27001', 'FedRAMP']
        }

    def _build_sla_capabilities_database(self) -> Dict[str, InstanceSLACapability]:
        """Build database of instance SLA capabilities"""
        capabilities = {}
        
        # Define instance SLA characteristics
        instance_data = [
            # Instance type, uptime%, avg latency ms, failover time, backup, multi-az, cost/hour, reliability
            ('c5.large', 99.95, 2.5, 60, True, True, 0.085, 0.95),
            ('c5.xlarge', 99.95, 2.5, 60, True, True, 0.17, 0.95),
            ('c5.2xlarge', 99.96, 2.0, 45, True, True, 0.34, 0.96),
            ('c5.4xlarge', 99.97, 1.8, 45, True, True, 0.68, 0.97),
            ('c5.9xlarge', 99.98, 1.5, 30, True, True, 1.53, 0.98),
            ('c5.18xlarge', 99.99, 1.2, 30, True, True, 3.06, 0.99),
            
            ('c5n.large', 99.96, 2.0, 45, True, True, 0.108, 0.96),
            ('c5n.xlarge', 99.97, 1.8, 45, True, True, 0.216, 0.97),
            ('c5n.2xlarge', 99.98, 1.5, 30, True, True, 0.432, 0.98),
            ('c5n.4xlarge', 99.98, 1.3, 30, True, True, 0.864, 0.98),
            ('c5n.9xlarge', 99.99, 1.0, 20, True, True, 1.944, 0.99),
            ('c5n.18xlarge', 99.995, 0.8, 15, True, True, 3.888, 0.995),
            
            ('m5.large', 99.9, 3.0, 90, True, True, 0.096, 0.92),
            ('m5.xlarge', 99.92, 2.8, 75, True, True, 0.192, 0.93),
            ('m5.2xlarge', 99.94, 2.5, 60, True, True, 0.384, 0.94),
            ('m5.4xlarge', 99.95, 2.2, 60, True, True, 0.768, 0.95),
            ('m5.8xlarge', 99.96, 2.0, 45, True, True, 1.536, 0.96),
            ('m5.16xlarge', 99.98, 1.8, 30, True, True, 3.072, 0.98),
            
            ('r5.large', 99.92, 2.8, 75, True, True, 0.126, 0.93),
            ('r5.xlarge', 99.94, 2.5, 60, True, True, 0.252, 0.94),
            ('r5.2xlarge', 99.95, 2.2, 60, True, True, 0.504, 0.95),
            ('r5.4xlarge', 99.96, 2.0, 45, True, True, 1.008, 0.96),
            ('r5.8xlarge', 99.97, 1.8, 45, True, True, 2.016, 0.97),
            ('r5.16xlarge', 99.98, 1.5, 30, True, True, 4.032, 0.98),
            
            ('i3.large', 99.8, 4.0, 120, False, False, 0.156, 0.88),
            ('i3.xlarge', 99.85, 3.5, 100, False, True, 0.312, 0.90),
            ('i3.2xlarge', 99.9, 3.0, 90, True, True, 0.624, 0.92),
            ('i3.4xlarge', 99.92, 2.8, 75, True, True, 1.248, 0.93),
            
            ('p3.2xlarge', 99.7, 5.0, 180, False, False, 3.06, 0.85),
            ('p3.8xlarge', 99.8, 4.0, 150, True, True, 12.24, 0.88),
            ('p3.16xlarge', 99.85, 3.5, 120, True, True, 24.48, 0.90),
            
            ('g4dn.xlarge', 99.75, 4.5, 150, False, False, 0.526, 0.87),
            ('g4dn.2xlarge', 99.8, 4.0, 120, False, True, 0.752, 0.88),
            ('g4dn.4xlarge', 99.85, 3.5, 100, True, True, 1.204, 0.90),
            
            ('x1e.xlarge', 99.98, 1.5, 30, True, True, 0.834, 0.98),
            ('x1e.2xlarge', 99.985, 1.2, 25, True, True, 1.668, 0.985),
            ('x1e.4xlarge', 99.99, 1.0, 20, True, True, 3.336, 0.99),
        ]
        
        for data in instance_data:
            instance_type, uptime, latency, failover, backup, multi_az, cost, reliability = data
            instance_family = instance_type.split('.')[0]
            
            capabilities[instance_type] = InstanceSLACapability(
                instance_type=instance_type,
                estimated_uptime_percent=uptime,
                avg_latency_ms=latency,
                failover_time_seconds=failover,
                backup_availability=backup,
                multi_az_support=multi_az,
                compliance_certifications=self.compliance_certifications.get(instance_family, []),
                monitoring_capabilities=self._get_monitoring_capabilities(instance_type),
                auto_recovery_features=self._get_auto_recovery_features(instance_type),
                cost_per_hour=cost,
                reliability_score=reliability
            )
        
        return capabilities

    def _get_monitoring_capabilities(self, instance_type: str) -> List[str]:
        """Get monitoring capabilities for instance type"""
        base_monitoring = ['CloudWatch', 'System Manager', 'Instance Status Checks']
        
        instance_family = instance_type.split('.')[0]
        size = instance_type.split('.')[1]
        
        # Enhanced monitoring for larger instances
        if size in ['8xlarge', '16xlarge', '18xlarge', '24xlarge']:
            base_monitoring.extend(['Enhanced Networking Metrics', 'Detailed CPU Metrics'])
        
        # GPU monitoring
        if instance_family in ['p3', 'p4', 'g4dn']:
            base_monitoring.extend(['GPU Utilization', 'GPU Memory'])
        
        # Network-optimized monitoring
        if instance_family in ['c5n', 'r5n', 'm5n']:
            base_monitoring.append('Enhanced Network Monitoring')
        
        return base_monitoring

    def _get_auto_recovery_features(self, instance_type: str) -> List[str]:
        """Get auto-recovery features for instance type"""
        features = ['Auto Recovery', 'Termination Protection']
        
        instance_family = instance_type.split('.')[0]
        size = instance_type.split('.')[1]
        
        # Enhanced features for premium instances
        if size in ['8xlarge', '16xlarge', '18xlarge', '24xlarge']:
            features.extend(['Auto Scaling Integration', 'Load Balancer Health Checks'])
        
        # Specialized features
        if instance_family in ['c5n', 'x1e']:
            features.append('Enhanced Placement Groups')
        
        return features

    def _initialize_az_reliability(self) -> Dict[str, Dict[str, Any]]:
        """Initialize availability zone reliability data"""
        return {
            'us-east-1a': {
                'reliability_class': AvailabilityZoneClass.PREMIUM,
                'historical_uptime_percent': 99.99,
                'avg_latency_to_region_ms': 0.5,
                'disaster_recovery_tier': 'primary'
            },
            'us-east-1b': {
                'reliability_class': AvailabilityZoneClass.PREMIUM,
                'historical_uptime_percent': 99.98,
                'avg_latency_to_region_ms': 0.6,
                'disaster_recovery_tier': 'primary'
            },
            'us-east-1c': {
                'reliability_class': AvailabilityZoneClass.STANDARD,
                'historical_uptime_percent': 99.95,
                'avg_latency_to_region_ms': 0.8,
                'disaster_recovery_tier': 'secondary'
            },
            'us-west-2a': {
                'reliability_class': AvailabilityZoneClass.PREMIUM,
                'historical_uptime_percent': 99.99,
                'avg_latency_to_region_ms': 0.4,
                'disaster_recovery_tier': 'primary'
            },
            'us-west-2b': {
                'reliability_class': AvailabilityZoneClass.PREMIUM,
                'historical_uptime_percent': 99.98,
                'avg_latency_to_region_ms': 0.5,
                'disaster_recovery_tier': 'primary'
            },
            'us-west-2c': {
                'reliability_class': AvailabilityZoneClass.STANDARD,
                'historical_uptime_percent': 99.96,
                'avg_latency_to_region_ms': 0.7,
                'disaster_recovery_tier': 'secondary'
            }
        }

    def _define_sla_templates(self) -> Dict[SLALevel, SLARequirement]:
        """Define standard SLA requirement templates"""
        return {
            SLALevel.PLATINUM: SLARequirement(
                sla_level=SLALevel.PLATINUM,
                uptime_requirement_percent=99.99,
                max_latency_ms=1.0,
                max_downtime_minutes_per_month=4.32,  # 99.99% uptime
                availability_zones_required=3,
                backup_instance_required=True,
                auto_failover_required=True,
                data_durability_requirement="11-nines",
                compliance_requirements=["SOC2", "PCI-DSS", "HIPAA", "ISO27001"],
                monitoring_interval_seconds=30,
                notification_channels=["email", "sms", "slack", "pagerduty"]
            ),
            SLALevel.GOLD: SLARequirement(
                sla_level=SLALevel.GOLD,
                uptime_requirement_percent=99.9,
                max_latency_ms=5.0,
                max_downtime_minutes_per_month=43.2,  # 99.9% uptime
                availability_zones_required=2,
                backup_instance_required=True,
                auto_failover_required=True,
                data_durability_requirement="9-nines",
                compliance_requirements=["SOC2", "ISO27001"],
                monitoring_interval_seconds=60,
                notification_channels=["email", "slack"]
            ),
            SLALevel.SILVER: SLARequirement(
                sla_level=SLALevel.SILVER,
                uptime_requirement_percent=99.5,
                max_latency_ms=10.0,
                max_downtime_minutes_per_month=216,  # 99.5% uptime
                availability_zones_required=2,
                backup_instance_required=False,
                auto_failover_required=False,
                data_durability_requirement="9-nines",
                compliance_requirements=["SOC2"],
                monitoring_interval_seconds=300,
                notification_channels=["email"]
            ),
            SLALevel.BRONZE: SLARequirement(
                sla_level=SLALevel.BRONZE,
                uptime_requirement_percent=99.0,
                max_latency_ms=50.0,
                max_downtime_minutes_per_month=432,  # 99.0% uptime
                availability_zones_required=1,
                backup_instance_required=False,
                auto_failover_required=False,
                data_durability_requirement="standard",
                compliance_requirements=[],
                monitoring_interval_seconds=900,
                notification_channels=["email"]
            ),
            SLALevel.BASIC: SLARequirement(
                sla_level=SLALevel.BASIC,
                uptime_requirement_percent=95.0,
                max_latency_ms=100.0,
                max_downtime_minutes_per_month=2160,  # 95.0% uptime
                availability_zones_required=1,
                backup_instance_required=False,
                auto_failover_required=False,
                data_durability_requirement="standard",
                compliance_requirements=[],
                monitoring_interval_seconds=1800,
                notification_channels=[]
            )
        }

    def select_instances(self, sla_requirements: Dict[str, Any], 
                        workload_characteristics: Dict[str, Any] = None) -> SLASelection:
        """Select instances based on SLA requirements"""
        try:
            # Parse SLA requirements
            sla_req = self._parse_sla_requirements(sla_requirements)
            workload = self._parse_workload_characteristics(workload_characteristics or {})
            
            # Find instances that meet SLA requirements
            suitable_instances = self._find_sla_suitable_instances(sla_req, workload)
            
            if not suitable_instances:
                return self._create_error_selection(
                    workload.workload_id,
                    "No instances found that meet SLA requirements"
                )
            
            # Select optimal instances
            selected_instances = self._select_optimal_instances(suitable_instances, sla_req, workload)
            
            # Select availability zones
            selected_azs = self._select_availability_zones(sla_req, workload)
            
            # Calculate SLA compliance score
            compliance_score = self._calculate_sla_compliance_score(selected_instances, sla_req)
            
            # Estimate overall uptime
            estimated_uptime = self._estimate_overall_uptime(selected_instances, selected_azs, sla_req)
            
            # Calculate costs
            estimated_cost = self._calculate_monthly_cost(selected_instances, sla_req)
            
            # Generate configurations
            backup_config = self._generate_backup_configuration(sla_req, workload)
            monitoring_config = self._generate_monitoring_configuration(sla_req, selected_instances)
            failover_config = self._generate_failover_configuration(sla_req, selected_instances, selected_azs)
            
            # Check compliance status
            compliance_status = self._check_compliance_status(selected_instances, sla_req)
            
            # Assess risks
            risk_assessment = self._assess_sla_risks(selected_instances, selected_azs, sla_req, workload)
            
            # Generate recommendations
            recommendations = self._generate_sla_recommendations(selected_instances, sla_req, workload, risk_assessment)
            
            return SLASelection(
                workload_id=workload.workload_id,
                selected_instances=[self._instance_to_dict(inst) for inst in selected_instances],
                availability_zones=selected_azs,
                sla_compliance_score=compliance_score,
                estimated_uptime_percent=estimated_uptime,
                estimated_cost_monthly=estimated_cost,
                backup_configuration=backup_config,
                monitoring_configuration=monitoring_config,
                failover_configuration=failover_config,
                compliance_status=compliance_status,
                risk_assessment=risk_assessment,
                recommendations=recommendations
            )
            
        except Exception as e:
            logger.error(f"Failed to select SLA instances: {e}")
            return self._create_error_selection("unknown", f"Selection error: {str(e)}")

    def _parse_sla_requirements(self, sla_data: Dict[str, Any]) -> SLARequirement:
        """Parse SLA requirements from input data"""
        sla_level = SLALevel(sla_data.get('sla_level', 'silver'))
        
        # Use template as base and override with specific requirements
        template = self.sla_templates[sla_level]
        
        return SLARequirement(
            sla_level=sla_level,
            uptime_requirement_percent=sla_data.get('uptime_requirement_percent', template.uptime_requirement_percent),
            max_latency_ms=sla_data.get('max_latency_ms', template.max_latency_ms),
            max_downtime_minutes_per_month=sla_data.get('max_downtime_minutes_per_month', template.max_downtime_minutes_per_month),
            availability_zones_required=sla_data.get('availability_zones_required', template.availability_zones_required),
            backup_instance_required=sla_data.get('backup_instance_required', template.backup_instance_required),
            auto_failover_required=sla_data.get('auto_failover_required', template.auto_failover_required),
            data_durability_requirement=sla_data.get('data_durability_requirement', template.data_durability_requirement),
            compliance_requirements=sla_data.get('compliance_requirements', template.compliance_requirements),
            monitoring_interval_seconds=sla_data.get('monitoring_interval_seconds', template.monitoring_interval_seconds),
            notification_channels=sla_data.get('notification_channels', template.notification_channels)
        )

    def _parse_workload_characteristics(self, workload_data: Dict[str, Any]) -> WorkloadCharacteristics:
        """Parse workload characteristics from input data"""
        return WorkloadCharacteristics(
            workload_id=workload_data.get('workload_id', f'workload_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}'),
            workload_name=workload_data.get('workload_name', 'Unnamed Workload'),
            criticality_level=workload_data.get('criticality_level', 'standard'),
            expected_load_pattern=workload_data.get('expected_load_pattern', 'steady'),
            fault_tolerance=workload_data.get('fault_tolerance', 'medium'),
            recovery_time_objective_minutes=workload_data.get('recovery_time_objective_minutes', 60),
            recovery_point_objective_minutes=workload_data.get('recovery_point_objective_minutes', 15),
            data_locality_constraints=workload_data.get('data_locality_constraints', []),
            regulatory_requirements=workload_data.get('regulatory_requirements', []),
            peak_concurrent_users=workload_data.get('peak_concurrent_users', 1000),
            average_request_rate=workload_data.get('average_request_rate', 100.0),
            data_volume_gb=workload_data.get('data_volume_gb', 100.0)
        )

    def _find_sla_suitable_instances(self, sla_req: SLARequirement, 
                                   workload: WorkloadCharacteristics) -> List[InstanceSLACapability]:
        """Find instances that meet SLA requirements"""
        suitable_instances = []
        
        for instance_type, capability in self.instance_sla_capabilities.items():
            # Check uptime requirement
            if capability.estimated_uptime_percent < sla_req.uptime_requirement_percent:
                continue
            
            # Check latency requirement
            if capability.avg_latency_ms > sla_req.max_latency_ms:
                continue
            
            # Check backup requirement
            if sla_req.backup_instance_required and not capability.backup_availability:
                continue
            
            # Check multi-AZ requirement
            if sla_req.availability_zones_required > 1 and not capability.multi_az_support:
                continue
            
            # Check compliance requirements
            if not all(req in capability.compliance_certifications for req in sla_req.compliance_requirements):
                continue
            
            # Check failover time against RTO
            if capability.failover_time_seconds > workload.recovery_time_objective_minutes * 60:
                continue
            
            suitable_instances.append(capability)
        
        return suitable_instances

    def _select_optimal_instances(self, suitable_instances: List[InstanceSLACapability], 
                                sla_req: SLARequirement, workload: WorkloadCharacteristics) -> List[InstanceSLACapability]:
        """Select optimal instances from suitable candidates"""
        # Score instances based on SLA requirements and cost
        scored_instances = []
        
        for instance in suitable_instances:
            score = self._calculate_instance_sla_score(instance, sla_req, workload)
            scored_instances.append((score, instance))
        
        # Sort by score (higher is better)
        scored_instances.sort(key=lambda x: x[0], reverse=True)
        
        # Select instances based on requirements
        selected = []
        
        if sla_req.backup_instance_required:
            # Select primary and backup instances
            if len(scored_instances) >= 2:
                selected.append(scored_instances[0][1])  # Primary
                selected.append(scored_instances[1][1])  # Backup
            elif len(scored_instances) == 1:
                selected.append(scored_instances[0][1])  # Only primary
        else:
            # Select single instance
            if scored_instances:
                selected.append(scored_instances[0][1])
        
        return selected

    def _calculate_instance_sla_score(self, instance: InstanceSLACapability, 
                                    sla_req: SLARequirement, workload: WorkloadCharacteristics) -> float:
        """Calculate SLA score for instance"""
        score = 0.0
        
        # Uptime score (40% weight)
        uptime_score = min(100, (instance.estimated_uptime_percent / sla_req.uptime_requirement_percent) * 100)
        score += uptime_score * 0.4
        
        # Latency score (30% weight)
        if instance.avg_latency_ms <= sla_req.max_latency_ms:
            latency_score = 100 - (instance.avg_latency_ms / sla_req.max_latency_ms * 50)
        else:
            latency_score = 0
        score += latency_score * 0.3
        
        # Reliability score (20% weight)
        reliability_score = instance.reliability_score * 100
        score += reliability_score * 0.2
        
        # Cost efficiency score (10% weight)
        # Lower cost is better, but not at expense of reliability
        cost_efficiency = max(0, 100 - (instance.cost_per_hour * 10))  # Normalize cost
        score += cost_efficiency * 0.1
        
        # Bonus for over-meeting requirements
        if instance.estimated_uptime_percent > sla_req.uptime_requirement_percent:
            score += (instance.estimated_uptime_percent - sla_req.uptime_requirement_percent) * 10
        
        # Bonus for additional features
        if len(instance.auto_recovery_features) > 3:
            score += 10
        
        if len(instance.monitoring_capabilities) > 5:
            score += 5
        
        return score

    def _select_availability_zones(self, sla_req: SLARequirement, 
                                 workload: WorkloadCharacteristics) -> List[str]:
        """Select optimal availability zones for SLA requirements"""
        # Get available AZs sorted by reliability
        available_azs = list(self.az_reliability.keys())
        
        # Sort by reliability class and uptime
        available_azs.sort(key=lambda az: (
            self.az_reliability[az]['reliability_class'] == AvailabilityZoneClass.PREMIUM,
            self.az_reliability[az]['historical_uptime_percent']
        ), reverse=True)
        
        # Select required number of AZs
        selected_azs = available_azs[:sla_req.availability_zones_required]
        
        # Apply data locality constraints
        if workload.data_locality_constraints:
            constrained_azs = [az for az in selected_azs if az in workload.data_locality_constraints]
            if constrained_azs:
                selected_azs = constrained_azs
        
        return selected_azs

    def _calculate_sla_compliance_score(self, instances: List[InstanceSLACapability], 
                                      sla_req: SLARequirement) -> float:
        """Calculate overall SLA compliance score"""
        if not instances:
            return 0.0
        
        # Average instance scores
        instance_scores = []
        for instance in instances:
            uptime_compliance = min(1.0, instance.estimated_uptime_percent / sla_req.uptime_requirement_percent)
            latency_compliance = 1.0 if instance.avg_latency_ms <= sla_req.max_latency_ms else 0.8
            reliability_compliance = instance.reliability_score
            
            instance_score = (uptime_compliance + latency_compliance + reliability_compliance) / 3
            instance_scores.append(instance_score)
        
        average_score = sum(instance_scores) / len(instance_scores)
        
        # Bonus for redundancy
        if len(instances) > 1 and sla_req.backup_instance_required:
            average_score *= 1.1  # 10% bonus for redundancy
        
        return min(1.0, average_score) * 100  # Convert to percentage

    def _estimate_overall_uptime(self, instances: List[InstanceSLACapability], 
                               availability_zones: List[str], sla_req: SLARequirement) -> float:
        """Estimate overall system uptime"""
        if not instances:
            return 0.0
        
        # Single instance uptime
        if len(instances) == 1:
            instance_uptime = instances[0].estimated_uptime_percent / 100
            az_uptime = self.az_reliability[availability_zones[0]]['historical_uptime_percent'] / 100
            return (instance_uptime * az_uptime) * 100
        
        # Multi-instance with failover
        primary_uptime = instances[0].estimated_uptime_percent / 100
        backup_uptime = instances[1].estimated_uptime_percent / 100 if len(instances) > 1 else 0.99
        
        # Calculate combined uptime (assuming proper failover)
        combined_downtime = (1 - primary_uptime) * (1 - backup_uptime)
        combined_uptime = 1 - combined_downtime
        
        # Factor in AZ reliability
        if len(availability_zones) > 1:
            az_reliability_factor = 1.0  # Multiple AZs provide additional reliability
        else:
            az_uptime = self.az_reliability[availability_zones[0]]['historical_uptime_percent'] / 100
            combined_uptime *= az_uptime
        
        return combined_uptime * 100

    def _calculate_monthly_cost(self, instances: List[InstanceSLACapability], 
                              sla_req: SLARequirement) -> float:
        """Calculate estimated monthly cost"""
        total_cost = 0.0
        
        for instance in instances:
            # Base instance cost
            monthly_cost = instance.cost_per_hour * 24 * 30
            
            # Additional costs for SLA requirements
            if sla_req.backup_instance_required:
                monthly_cost *= 1.5  # Backup instance and additional storage
            
            if sla_req.monitoring_interval_seconds <= 60:
                monthly_cost *= 1.1  # Enhanced monitoring costs
            
            if sla_req.auto_failover_required:
                monthly_cost *= 1.05  # Auto-failover infrastructure
            
            total_cost += monthly_cost
        
        return total_cost

    def _generate_backup_configuration(self, sla_req: SLARequirement, 
                                     workload: WorkloadCharacteristics) -> Dict[str, Any]:
        """Generate backup configuration for SLA requirements"""
        config = {
            'backup_enabled': sla_req.backup_instance_required,
            'backup_frequency_hours': 24,  # Default daily backups
            'retention_days': 30
        }
        
        if sla_req.data_durability_requirement == "11-nines":
            config.update({
                'backup_frequency_hours': 6,  # Every 6 hours
                'retention_days': 90,
                'cross_region_replication': True,
                'point_in_time_recovery': True
            })
        elif sla_req.data_durability_requirement == "9-nines":
            config.update({
                'backup_frequency_hours': 12,  # Every 12 hours
                'retention_days': 60,
                'cross_region_replication': False,
                'point_in_time_recovery': True
            })
        
        # Adjust based on RPO
        if workload.recovery_point_objective_minutes <= 15:
            config['backup_frequency_hours'] = 1  # Hourly backups
        elif workload.recovery_point_objective_minutes <= 60:
            config['backup_frequency_hours'] = 4  # Every 4 hours
        
        return config

    def _generate_monitoring_configuration(self, sla_req: SLARequirement, 
                                         instances: List[InstanceSLACapability]) -> Dict[str, Any]:
        """Generate monitoring configuration"""
        config = {
            'monitoring_interval_seconds': sla_req.monitoring_interval_seconds,
            'notification_channels': sla_req.notification_channels,
            'metrics_to_monitor': [
                'CPUUtilization',
                'StatusCheckFailed',
                'NetworkIn',
                'NetworkOut'
            ],
            'alarms': []
        }
        
        # Add detailed monitoring for high SLA levels
        if sla_req.sla_level in [SLALevel.PLATINUM, SLALevel.GOLD]:
            config['metrics_to_monitor'].extend([
                'StatusCheckFailed_Instance',
                'StatusCheckFailed_System',
                'DiskReadOps',
                'DiskWriteOps',
                'NetworkLatency'
            ])
        
        # Add instance-specific monitoring
        for instance in instances:
            if 'GPU' in ' '.join(instance.monitoring_capabilities):
                config['metrics_to_monitor'].extend(['GPUUtilization', 'GPUMemoryUtilization'])
        
        # Define alarms based on SLA requirements
        config['alarms'] = [
            {
                'name': 'HighCPUUtilization',
                'metric': 'CPUUtilization',
                'threshold': 80,
                'comparison': 'GreaterThanThreshold'
            },
            {
                'name': 'InstanceStatusCheckFailed',
                'metric': 'StatusCheckFailed_Instance',
                'threshold': 0,
                'comparison': 'GreaterThanThreshold'
            }
        ]
        
        return config

    def _generate_failover_configuration(self, sla_req: SLARequirement, 
                                       instances: List[InstanceSLACapability], 
                                       availability_zones: List[str]) -> Dict[str, Any]:
        """Generate failover configuration"""
        config = {
            'auto_failover_enabled': sla_req.auto_failover_required,
            'failover_timeout_seconds': 300,  # 5 minutes default
            'health_check_interval_seconds': 30
        }
        
        if sla_req.auto_failover_required:
            # Configure based on RTO requirements
            primary_instance = instances[0] if instances else None
            if primary_instance:
                config['failover_timeout_seconds'] = min(300, primary_instance.failover_time_seconds)
            
            # Multi-AZ failover
            if len(availability_zones) > 1:
                config.update({
                    'cross_az_failover': True,
                    'primary_az': availability_zones[0],
                    'secondary_az': availability_zones[1] if len(availability_zones) > 1 else None
                })
            
            # Load balancer configuration
            config.update({
                'load_balancer_health_check': True,
                'health_check_grace_period_seconds': 60,
                'unhealthy_threshold': 2,
                'healthy_threshold': 2
            })
        
        return config

    def _check_compliance_status(self, instances: List[InstanceSLACapability], 
                               sla_req: SLARequirement) -> Dict[str, bool]:
        """Check compliance status for requirements"""
        status = {}
        
        for requirement in sla_req.compliance_requirements:
            compliant = all(requirement in instance.compliance_certifications for instance in instances)
            status[requirement] = compliant
        
        # Additional compliance checks
        status['uptime_requirement_met'] = all(
            instance.estimated_uptime_percent >= sla_req.uptime_requirement_percent
            for instance in instances
        )
        
        status['latency_requirement_met'] = all(
            instance.avg_latency_ms <= sla_req.max_latency_ms
            for instance in instances
        )
        
        status['backup_requirement_met'] = not sla_req.backup_instance_required or all(
            instance.backup_availability for instance in instances
        )
        
        return status

    def _assess_sla_risks(self, instances: List[InstanceSLACapability], 
                         availability_zones: List[str], sla_req: SLARequirement, 
                         workload: WorkloadCharacteristics) -> Dict[str, Any]:
        """Assess SLA-related risks"""
        risks = {
            'overall_risk_level': 'low',
            'risk_factors': [],
            'mitigation_strategies': []
        }
        
        risk_score = 0
        
        # Single point of failure risks
        if len(instances) == 1 and sla_req.sla_level in [SLALevel.PLATINUM, SLALevel.GOLD]:
            risks['risk_factors'].append('Single instance without backup for high SLA level')
            risks['mitigation_strategies'].append('Consider adding backup instance')
            risk_score += 30
        
        # AZ concentration risk
        if len(availability_zones) == 1 and sla_req.availability_zones_required > 1:
            risks['risk_factors'].append('Single availability zone deployment')
            risks['mitigation_strategies'].append('Deploy across multiple availability zones')
            risk_score += 20
        
        # Latency buffer risk
        min_latency = min(instance.avg_latency_ms for instance in instances) if instances else 100
        latency_buffer = (sla_req.max_latency_ms - min_latency) / sla_req.max_latency_ms
        if latency_buffer < 0.2:  # Less than 20% buffer
            risks['risk_factors'].append('Minimal latency buffer')
            risks['mitigation_strategies'].append('Consider higher performance instances')
            risk_score += 15
        
        # Compliance gaps
        for requirement in sla_req.compliance_requirements:
            compliant = all(requirement in instance.compliance_certifications for instance in instances)
            if not compliant:
                risks['risk_factors'].append(f'Compliance gap: {requirement}')
                risks['mitigation_strategies'].append(f'Select instances with {requirement} certification')
                risk_score += 25
        
        # Determine overall risk level
        if risk_score >= 50:
            risks['overall_risk_level'] = 'high'
        elif risk_score >= 25:
            risks['overall_risk_level'] = 'medium'
        
        risks['risk_score'] = risk_score
        
        return risks

    def _generate_sla_recommendations(self, instances: List[InstanceSLACapability], 
                                    sla_req: SLARequirement, workload: WorkloadCharacteristics, 
                                    risk_assessment: Dict[str, Any]) -> List[str]:
        """Generate SLA optimization recommendations"""
        recommendations = []
        
        # High-risk recommendations
        if risk_assessment['overall_risk_level'] == 'high':
            recommendations.append('Consider upgrading to higher reliability instance types')
            recommendations.append('Implement comprehensive monitoring and alerting')
        
        # Backup recommendations
        if not sla_req.backup_instance_required and sla_req.sla_level in [SLALevel.PLATINUM, SLALevel.GOLD]:
            recommendations.append('Add backup instances for higher availability')
        
        # Performance recommendations
        min_latency = min(instance.avg_latency_ms for instance in instances) if instances else 100
        if min_latency > sla_req.max_latency_ms * 0.8:
            recommendations.append('Consider instances with better network performance')
        
        # Cost optimization recommendations
        if instances:
            avg_cost = sum(instance.cost_per_hour for instance in instances) / len(instances)
            if avg_cost > 2.0 and sla_req.sla_level in [SLALevel.BRONZE, SLALevel.BASIC]:
                recommendations.append('Consider cost-optimized instance types for lower SLA requirements')
        
        # Monitoring recommendations
        if sla_req.monitoring_interval_seconds > 300:
            recommendations.append('Implement more frequent monitoring for better SLA compliance')
        
        # Auto-scaling recommendations
        if workload.expected_load_pattern == 'bursty':
            recommendations.append('Configure auto-scaling for variable load patterns')
        
        return recommendations

    def _instance_to_dict(self, instance: InstanceSLACapability) -> Dict[str, Any]:
        """Convert instance capability to dictionary"""
        return {
            'instance_type': instance.instance_type,
            'estimated_uptime_percent': instance.estimated_uptime_percent,
            'avg_latency_ms': instance.avg_latency_ms,
            'failover_time_seconds': instance.failover_time_seconds,
            'backup_availability': instance.backup_availability,
            'multi_az_support': instance.multi_az_support,
            'compliance_certifications': instance.compliance_certifications,
            'monitoring_capabilities': instance.monitoring_capabilities,
            'auto_recovery_features': instance.auto_recovery_features,
            'cost_per_hour': instance.cost_per_hour,
            'reliability_score': instance.reliability_score
        }

    def _create_error_selection(self, workload_id: str, error_message: str) -> SLASelection:
        """Create error SLA selection result"""
        return SLASelection(
            workload_id=workload_id,
            selected_instances=[],
            availability_zones=[],
            sla_compliance_score=0.0,
            estimated_uptime_percent=0.0,
            estimated_cost_monthly=0.0,
            backup_configuration={'error': error_message},
            monitoring_configuration={'error': error_message},
            failover_configuration={'error': error_message},
            compliance_status={'error': True},
            risk_assessment={'overall_risk_level': 'high', 'error': error_message},
            recommendations=[f'Error: {error_message}']
        )

    def get_sla_templates(self) -> Dict[str, Dict[str, Any]]:
        """Get available SLA templates"""
        try:
            templates = {}
            
            for level, template in self.sla_templates.items():
                templates[level.value] = {
                    'sla_level': template.sla_level.value,
                    'uptime_requirement_percent': template.uptime_requirement_percent,
                    'max_latency_ms': template.max_latency_ms,
                    'max_downtime_minutes_per_month': template.max_downtime_minutes_per_month,
                    'availability_zones_required': template.availability_zones_required,
                    'backup_instance_required': template.backup_instance_required,
                    'auto_failover_required': template.auto_failover_required,
                    'data_durability_requirement': template.data_durability_requirement,
                    'compliance_requirements': template.compliance_requirements,
                    'monitoring_interval_seconds': template.monitoring_interval_seconds,
                    'notification_channels': template.notification_channels
                }
            
            return {
                'timestamp': datetime.utcnow().isoformat(),
                'templates': templates
            }
            
        except Exception as e:
            logger.error(f"Failed to get SLA templates: {e}")
            return {'error': str(e)}

    def get_instance_sla_capabilities(self) -> Dict[str, Any]:
        """Get SLA capabilities of all instances"""
        try:
            capabilities = {}
            
            for instance_type, capability in self.instance_sla_capabilities.items():
                capabilities[instance_type] = self._instance_to_dict(capability)
            
            return {
                'timestamp': datetime.utcnow().isoformat(),
                'instance_capabilities': capabilities,
                'total_instances': len(capabilities)
            }
            
        except Exception as e:
            logger.error(f"Failed to get instance SLA capabilities: {e}")
            return {'error': str(e)}