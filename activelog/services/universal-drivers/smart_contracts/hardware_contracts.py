#!/usr/bin/env python3
"""
Smart Contracts for Hardware
Blockchain-based hardware management, usage billing, and automated service agreements
"""

import hashlib
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
import uuid
from decimal import Decimal

class ContractStatus(Enum):
    """Smart contract status"""
    DRAFT = "draft"
    ACTIVE = "active"
    EXECUTING = "executing"
    COMPLETED = "completed"
    TERMINATED = "terminated"
    DISPUTED = "disputed"
    SUSPENDED = "suspended"

class PaymentStatus(Enum):
    """Payment status for contracts"""
    PENDING = "pending"
    PAID = "paid"
    OVERDUE = "overdue"
    REFUNDED = "refunded"
    DISPUTED = "disputed"

class ContractType(Enum):
    """Types of hardware contracts"""
    DEVICE_REGISTRATION = "device_registration"
    USAGE_BILLING = "usage_billing"
    SLA_ENFORCEMENT = "sla_enforcement"
    MAINTENANCE = "maintenance"
    PERFORMANCE_BOND = "performance_bond"
    RESOURCE_ALLOCATION = "resource_allocation"
    INSURANCE = "insurance"
    DEPRECIATION = "depreciation"
    DISPUTE_RESOLUTION = "dispute_resolution"

@dataclass
class ContractParty:
    """Contract participant"""
    address: str
    name: str
    role: str  # owner, user, provider, maintainer, insurer
    public_key: str
    reputation_score: float = 0.0

@dataclass
class HardwareDevice:
    """Hardware device information"""
    device_id: str
    device_type: str
    manufacturer: str
    model: str
    serial_number: str
    specifications: Dict[str, Any]
    current_value: Decimal
    depreciation_rate: float
    warranty_expires: datetime
    location: Optional[str] = None

@dataclass
class ContractTerms:
    """Contract terms and conditions"""
    duration: timedelta
    payment_amount: Decimal
    payment_frequency: str  # hourly, daily, monthly, one-time
    currency: str = "USD"
    penalty_rate: float = 0.0
    performance_metrics: Dict[str, Any] = None
    sla_requirements: Dict[str, Any] = None

@dataclass
class SmartContract:
    """Base smart contract for hardware"""
    contract_id: str
    contract_type: ContractType
    parties: List[ContractParty]
    device: HardwareDevice
    terms: ContractTerms
    status: ContractStatus
    created_at: datetime
    activated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    conditions: Dict[str, Any] = None
    execution_history: List[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.conditions is None:
            self.conditions = {}
        if self.execution_history is None:
            self.execution_history = []

class BlockchainEngine:
    """Simplified blockchain engine for smart contracts"""
    
    def __init__(self):
        self.contracts: Dict[str, SmartContract] = {}
        self.transaction_history: List[Dict[str, Any]] = []
        self.contract_templates: Dict[ContractType, Dict[str, Any]] = {}
        self.gas_prices: Dict[str, float] = {
            "device_registration": 0.001,
            "payment": 0.002,
            "execution": 0.005,
            "dispute": 0.01
        }
        self._initialize_templates()
    
    def _initialize_templates(self):
        """Initialize contract templates"""
        self.contract_templates = {
            ContractType.DEVICE_REGISTRATION: {
                "required_fields": ["device_id", "owner", "specifications"],
                "default_duration": timedelta(days=365),
                "gas_cost": 0.001
            },
            ContractType.USAGE_BILLING: {
                "required_fields": ["device_id", "user", "billing_rate"],
                "billing_frequencies": ["hourly", "daily", "monthly"],
                "gas_cost": 0.002
            },
            ContractType.SLA_ENFORCEMENT: {
                "required_fields": ["device_id", "provider", "sla_metrics"],
                "default_penalties": {"downtime": 0.1, "performance": 0.05},
                "gas_cost": 0.005
            },
            ContractType.MAINTENANCE: {
                "required_fields": ["device_id", "maintainer", "schedule"],
                "maintenance_types": ["preventive", "corrective", "emergency"],
                "gas_cost": 0.003
            },
            ContractType.PERFORMANCE_BOND: {
                "required_fields": ["device_id", "provider", "bond_amount"],
                "bond_percentage": 0.1,  # 10% of contract value
                "gas_cost": 0.007
            }
        }

class DeviceRegistrationContract(SmartContract):
    """Smart contract for device registration"""
    
    def __init__(self, device: HardwareDevice, owner: ContractParty):
        contract_id = f"reg_{int(time.time())}_{device.device_id[:8]}"
        terms = ContractTerms(
            duration=timedelta(days=365),
            payment_amount=Decimal("10.00"),  # Registration fee
            payment_frequency="one-time",
            currency="USD"
        )
        
        super().__init__(
            contract_id=contract_id,
            contract_type=ContractType.DEVICE_REGISTRATION,
            parties=[owner],
            device=device,
            terms=terms,
            status=ContractStatus.DRAFT,
            created_at=datetime.now(),
            conditions={
                "registration_fee_paid": False,
                "device_verified": False,
                "ownership_confirmed": False
            }
        )
    
    def verify_device(self) -> bool:
        """Verify device authenticity"""
        # Simplified verification - in reality would check hardware signatures
        if self.device.serial_number and self.device.manufacturer:
            self.conditions["device_verified"] = True
            self.execution_history.append({
                "action": "device_verified",
                "timestamp": datetime.now().isoformat(),
                "details": "Device authentication successful"
            })
            return True
        return False
    
    def confirm_ownership(self, signature: str) -> bool:
        """Confirm device ownership with digital signature"""
        # Simplified ownership verification
        if signature and len(signature) >= 64:  # Minimum signature length
            self.conditions["ownership_confirmed"] = True
            self.execution_history.append({
                "action": "ownership_confirmed",
                "timestamp": datetime.now().isoformat(),
                "signature": signature
            })
            return True
        return False
    
    def execute_registration(self) -> bool:
        """Execute device registration"""
        if (self.conditions.get("device_verified") and 
            self.conditions.get("ownership_confirmed") and
            self.conditions.get("registration_fee_paid")):
            
            self.status = ContractStatus.COMPLETED
            self.completed_at = datetime.now()
            
            self.execution_history.append({
                "action": "registration_completed",
                "timestamp": datetime.now().isoformat(),
                "device_id": self.device.device_id
            })
            return True
        return False

class UsageBillingContract(SmartContract):
    """Smart contract for usage-based billing"""
    
    def __init__(self, device: HardwareDevice, user: ContractParty, 
                 provider: ContractParty, hourly_rate: Decimal):
        contract_id = f"billing_{int(time.time())}_{device.device_id[:8]}"
        terms = ContractTerms(
            duration=timedelta(days=30),
            payment_amount=hourly_rate,
            payment_frequency="hourly",
            currency="USD"
        )
        
        super().__init__(
            contract_id=contract_id,
            contract_type=ContractType.USAGE_BILLING,
            parties=[user, provider],
            device=device,
            terms=terms,
            status=ContractStatus.DRAFT,
            created_at=datetime.now(),
            conditions={
                "usage_tracking_enabled": False,
                "billing_authorized": False,
                "total_usage_hours": Decimal("0.0"),
                "total_amount_due": Decimal("0.0"),
                "last_billing_cycle": None
            }
        )
    
    def start_usage_tracking(self) -> bool:
        """Start tracking device usage"""
        self.conditions["usage_tracking_enabled"] = True
        self.status = ContractStatus.ACTIVE
        self.activated_at = datetime.now()
        
        self.execution_history.append({
            "action": "usage_tracking_started",
            "timestamp": datetime.now().isoformat(),
            "hourly_rate": float(self.terms.payment_amount)
        })
        return True
    
    def record_usage(self, usage_hours: Decimal) -> bool:
        """Record device usage"""
        if not self.conditions.get("usage_tracking_enabled"):
            return False
        
        self.conditions["total_usage_hours"] += usage_hours
        amount_due = usage_hours * self.terms.payment_amount
        self.conditions["total_amount_due"] += amount_due
        
        self.execution_history.append({
            "action": "usage_recorded",
            "timestamp": datetime.now().isoformat(),
            "usage_hours": float(usage_hours),
            "amount_due": float(amount_due),
            "total_usage": float(self.conditions["total_usage_hours"])
        })
        return True
    
    def process_billing_cycle(self) -> Dict[str, Any]:
        """Process billing for current cycle"""
        if not self.conditions.get("usage_tracking_enabled"):
            return {"success": False, "reason": "Usage tracking not enabled"}
        
        current_time = datetime.now()
        amount_due = self.conditions["total_amount_due"]
        
        invoice = {
            "contract_id": self.contract_id,
            "billing_period": {
                "start": self.conditions.get("last_billing_cycle", self.activated_at).isoformat(),
                "end": current_time.isoformat()
            },
            "usage_hours": float(self.conditions["total_usage_hours"]),
            "hourly_rate": float(self.terms.payment_amount),
            "amount_due": float(amount_due),
            "due_date": (current_time + timedelta(days=30)).isoformat()
        }
        
        # Reset for next cycle
        self.conditions["total_usage_hours"] = Decimal("0.0")
        self.conditions["total_amount_due"] = Decimal("0.0")
        self.conditions["last_billing_cycle"] = current_time
        
        self.execution_history.append({
            "action": "billing_cycle_processed",
            "timestamp": current_time.isoformat(),
            "invoice": invoice
        })
        
        return {"success": True, "invoice": invoice}

class SLAEnforcementContract(SmartContract):
    """Smart contract for SLA enforcement"""
    
    def __init__(self, device: HardwareDevice, provider: ContractParty,
                 client: ContractParty, sla_metrics: Dict[str, Any]):
        contract_id = f"sla_{int(time.time())}_{device.device_id[:8]}"
        terms = ContractTerms(
            duration=timedelta(days=365),
            payment_amount=Decimal("1000.00"),  # Annual SLA fee
            payment_frequency="monthly",
            currency="USD",
            penalty_rate=0.05,  # 5% penalty for SLA violations
            sla_requirements=sla_metrics
        )
        
        super().__init__(
            contract_id=contract_id,
            contract_type=ContractType.SLA_ENFORCEMENT,
            parties=[provider, client],
            device=device,
            terms=terms,
            status=ContractStatus.DRAFT,
            created_at=datetime.now(),
            conditions={
                "monitoring_active": False,
                "violations": [],
                "uptime_percentage": 100.0,
                "response_times": [],
                "penalties_accrued": Decimal("0.0")
            }
        )
    
    def start_monitoring(self) -> bool:
        """Start SLA monitoring"""
        self.conditions["monitoring_active"] = True
        self.status = ContractStatus.ACTIVE
        self.activated_at = datetime.now()
        
        self.execution_history.append({
            "action": "sla_monitoring_started",
            "timestamp": datetime.now().isoformat(),
            "sla_requirements": self.terms.sla_requirements
        })
        return True
    
    def record_performance_metric(self, metric_name: str, value: float) -> bool:
        """Record performance metric"""
        if not self.conditions.get("monitoring_active"):
            return False
        
        timestamp = datetime.now()
        
        # Check for SLA violations
        violation = self._check_sla_violation(metric_name, value)
        if violation:
            self.conditions["violations"].append({
                "metric": metric_name,
                "expected": self.terms.sla_requirements.get(metric_name),
                "actual": value,
                "timestamp": timestamp.isoformat(),
                "penalty": violation["penalty"]
            })
            self.conditions["penalties_accrued"] += Decimal(str(violation["penalty"]))
        
        self.execution_history.append({
            "action": "performance_metric_recorded",
            "timestamp": timestamp.isoformat(),
            "metric": metric_name,
            "value": value,
            "violation": violation is not None
        })
        
        return True
    
    def _check_sla_violation(self, metric_name: str, value: float) -> Optional[Dict[str, Any]]:
        """Check if metric violates SLA"""
        if metric_name not in self.terms.sla_requirements:
            return None
        
        required = self.terms.sla_requirements[metric_name]
        
        if metric_name == "uptime_percentage" and value < required:
            penalty = float(self.terms.payment_amount) * self.terms.penalty_rate
            return {"penalty": penalty, "reason": f"Uptime {value}% below required {required}%"}
        
        if metric_name == "response_time_ms" and value > required:
            penalty = float(self.terms.payment_amount) * self.terms.penalty_rate * 0.5
            return {"penalty": penalty, "reason": f"Response time {value}ms exceeds {required}ms"}
        
        return None
    
    def calculate_penalties(self) -> Dict[str, Any]:
        """Calculate total SLA penalties"""
        total_penalties = self.conditions["penalties_accrued"]
        violation_count = len(self.conditions["violations"])
        
        return {
            "total_penalties": float(total_penalties),
            "violation_count": violation_count,
            "violations": self.conditions["violations"][-10:],  # Last 10 violations
            "penalty_percentage": float(total_penalties) / float(self.terms.payment_amount) * 100
        }

class MaintenanceContract(SmartContract):
    """Smart contract for device maintenance"""
    
    def __init__(self, device: HardwareDevice, maintainer: ContractParty,
                 owner: ContractParty, maintenance_schedule: Dict[str, Any]):
        contract_id = f"maint_{int(time.time())}_{device.device_id[:8]}"
        terms = ContractTerms(
            duration=timedelta(days=365),
            payment_amount=Decimal("500.00"),  # Annual maintenance fee
            payment_frequency="monthly",
            currency="USD"
        )
        
        super().__init__(
            contract_id=contract_id,
            contract_type=ContractType.MAINTENANCE,
            parties=[maintainer, owner],
            device=device,
            terms=terms,
            status=ContractStatus.DRAFT,
            created_at=datetime.now(),
            conditions={
                "maintenance_schedule": maintenance_schedule,
                "completed_maintenance": [],
                "pending_maintenance": [],
                "emergency_calls": 0,
                "compliance_score": 100.0
            }
        )
    
    def schedule_maintenance(self, maintenance_type: str, 
                           scheduled_date: datetime, description: str) -> str:
        """Schedule maintenance task"""
        task_id = str(uuid.uuid4())
        task = {
            "task_id": task_id,
            "type": maintenance_type,
            "scheduled_date": scheduled_date.isoformat(),
            "description": description,
            "status": "scheduled"
        }
        
        self.conditions["pending_maintenance"].append(task)
        
        self.execution_history.append({
            "action": "maintenance_scheduled",
            "timestamp": datetime.now().isoformat(),
            "task": task
        })
        
        return task_id
    
    def complete_maintenance(self, task_id: str, completion_notes: str,
                           actual_date: datetime) -> bool:
        """Mark maintenance task as completed"""
        # Find pending task
        task = None
        for i, pending_task in enumerate(self.conditions["pending_maintenance"]):
            if pending_task["task_id"] == task_id:
                task = self.conditions["pending_maintenance"].pop(i)
                break
        
        if not task:
            return False
        
        # Mark as completed
        task["status"] = "completed"
        task["completion_date"] = actual_date.isoformat()
        task["completion_notes"] = completion_notes
        
        self.conditions["completed_maintenance"].append(task)
        
        # Update compliance score based on timeliness
        scheduled = datetime.fromisoformat(task["scheduled_date"])
        delay_days = (actual_date - scheduled).days
        if delay_days <= 0:
            compliance_bonus = 2.0
        elif delay_days <= 7:
            compliance_bonus = 0.0
        else:
            compliance_bonus = -5.0 * min(delay_days / 7, 4)  # Max -20 points
        
        self.conditions["compliance_score"] = max(0, 
            self.conditions["compliance_score"] + compliance_bonus)
        
        self.execution_history.append({
            "action": "maintenance_completed",
            "timestamp": datetime.now().isoformat(),
            "task": task,
            "delay_days": delay_days,
            "compliance_adjustment": compliance_bonus
        })
        
        return True
    
    def request_emergency_maintenance(self, description: str, 
                                    urgency: str = "high") -> str:
        """Request emergency maintenance"""
        task_id = self.schedule_maintenance("emergency", datetime.now(), description)
        self.conditions["emergency_calls"] += 1
        
        # Emergency calls may incur additional charges
        if urgency == "critical":
            emergency_fee = self.terms.payment_amount * Decimal("0.5")
        else:
            emergency_fee = self.terms.payment_amount * Decimal("0.25")
        
        self.execution_history.append({
            "action": "emergency_maintenance_requested",
            "timestamp": datetime.now().isoformat(),
            "task_id": task_id,
            "urgency": urgency,
            "emergency_fee": float(emergency_fee)
        })
        
        return task_id

class HardwareContractManager:
    """Manager for all hardware smart contracts"""
    
    def __init__(self):
        self.blockchain_engine = BlockchainEngine()
        self.active_contracts: Dict[str, SmartContract] = {}
        self.contract_factories = {
            ContractType.DEVICE_REGISTRATION: DeviceRegistrationContract,
            ContractType.USAGE_BILLING: UsageBillingContract,
            ContractType.SLA_ENFORCEMENT: SLAEnforcementContract,
            ContractType.MAINTENANCE: MaintenanceContract
        }
    
    def create_contract(self, contract_type: ContractType, 
                       **kwargs) -> SmartContract:
        """Create new smart contract"""
        if contract_type not in self.contract_factories:
            raise ValueError(f"Unsupported contract type: {contract_type}")
        
        factory = self.contract_factories[contract_type]
        contract = factory(**kwargs)
        
        self.active_contracts[contract.contract_id] = contract
        self.blockchain_engine.contracts[contract.contract_id] = contract
        
        return contract
    
    def get_contract(self, contract_id: str) -> Optional[SmartContract]:
        """Get contract by ID"""
        return self.active_contracts.get(contract_id)
    
    def get_contracts_by_device(self, device_id: str) -> List[SmartContract]:
        """Get all contracts for a device"""
        return [contract for contract in self.active_contracts.values()
                if contract.device.device_id == device_id]
    
    def get_contracts_by_party(self, party_address: str) -> List[SmartContract]:
        """Get all contracts for a party"""
        contracts = []
        for contract in self.active_contracts.values():
            for party in contract.parties:
                if party.address == party_address:
                    contracts.append(contract)
                    break
        return contracts
    
    def execute_contract_action(self, contract_id: str, action: str, 
                              **kwargs) -> Dict[str, Any]:
        """Execute action on contract"""
        contract = self.get_contract(contract_id)
        if not contract:
            return {"success": False, "error": "Contract not found"}
        
        try:
            if hasattr(contract, action):
                method = getattr(contract, action)
                result = method(**kwargs)
                
                return {"success": True, "result": result, "contract_status": contract.status.value}
            else:
                return {"success": False, "error": f"Action '{action}' not supported"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_contract_analytics(self) -> Dict[str, Any]:
        """Get analytics across all contracts"""
        total_contracts = len(self.active_contracts)
        contract_by_type = {}
        contract_by_status = {}
        total_value = Decimal("0.0")
        
        for contract in self.active_contracts.values():
            # Count by type
            contract_type = contract.contract_type.value
            contract_by_type[contract_type] = contract_by_type.get(contract_type, 0) + 1
            
            # Count by status
            status = contract.status.value
            contract_by_status[status] = contract_by_status.get(status, 0) + 1
            
            # Sum total value
            total_value += contract.terms.payment_amount
        
        return {
            "total_contracts": total_contracts,
            "contracts_by_type": contract_by_type,
            "contracts_by_status": contract_by_status,
            "total_contract_value": float(total_value),
            "active_contracts": len([c for c in self.active_contracts.values() 
                                   if c.status == ContractStatus.ACTIVE])
        }

# Example usage and testing
if __name__ == "__main__":
    # Create contract manager
    manager = HardwareContractManager()
    
    # Create sample hardware device
    device = HardwareDevice(
        device_id="dev_001",
        device_type="IoT Sensor",
        manufacturer="Acme Corp",
        model="AS-2000",
        serial_number="SN123456789",
        specifications={"temperature_range": "-40 to 85°C", "power": "3.3V"},
        current_value=Decimal("250.00"),
        depreciation_rate=0.15,
        warranty_expires=datetime(2025, 12, 31)
    )
    
    # Create contract parties
    owner = ContractParty(
        address="0x1234567890abcdef",
        name="Device Owner Inc",
        role="owner",
        public_key="pub_key_owner_123"
    )
    
    user = ContractParty(
        address="0xabcdef1234567890",
        name="Service User LLC",
        role="user",
        public_key="pub_key_user_456"
    )
    
    provider = ContractParty(
        address="0x9876543210fedcba",
        name="Hardware Provider Co",
        role="provider",
        public_key="pub_key_provider_789"
    )
    
    # Create device registration contract
    print("Creating device registration contract...")
    reg_contract = manager.create_contract(
        ContractType.DEVICE_REGISTRATION,
        device=device,
        owner=owner
    )
    
    print(f"Registration contract created: {reg_contract.contract_id}")
    
    # Execute registration steps
    reg_contract.verify_device()
    reg_contract.confirm_ownership("digital_signature_123456")
    reg_contract.conditions["registration_fee_paid"] = True
    reg_contract.execute_registration()
    
    print(f"Device registration status: {reg_contract.status.value}")
    
    # Create usage billing contract
    print("\nCreating usage billing contract...")
    billing_contract = manager.create_contract(
        ContractType.USAGE_BILLING,
        device=device,
        user=user,
        provider=provider,
        hourly_rate=Decimal("5.00")
    )
    
    print(f"Billing contract created: {billing_contract.contract_id}")
    
    # Start usage tracking and record some usage
    billing_contract.start_usage_tracking()
    billing_contract.record_usage(Decimal("2.5"))  # 2.5 hours
    billing_contract.record_usage(Decimal("1.75"))  # 1.75 hours
    
    # Process billing cycle
    invoice = billing_contract.process_billing_cycle()
    print(f"Generated invoice: ${invoice['invoice']['amount_due']}")
    
    # Create SLA enforcement contract
    print("\nCreating SLA enforcement contract...")
    sla_contract = manager.create_contract(
        ContractType.SLA_ENFORCEMENT,
        device=device,
        provider=provider,
        client=user,
        sla_metrics={"uptime_percentage": 99.9, "response_time_ms": 100}
    )
    
    print(f"SLA contract created: {sla_contract.contract_id}")
    
    # Start monitoring and record some metrics
    sla_contract.start_monitoring()
    sla_contract.record_performance_metric("uptime_percentage", 99.5)  # Violation
    sla_contract.record_performance_metric("response_time_ms", 150)    # Violation
    
    penalties = sla_contract.calculate_penalties()
    print(f"SLA penalties: ${penalties['total_penalties']}")
    
    # Get analytics
    analytics = manager.get_contract_analytics()
    print(f"\nContract Analytics:")
    print(f"- Total contracts: {analytics['total_contracts']}")
    print(f"- Active contracts: {analytics['active_contracts']}")
    print(f"- Total value: ${analytics['total_contract_value']}")
    print(f"- By type: {analytics['contracts_by_type']}")
    print(f"- By status: {analytics['contracts_by_status']}")