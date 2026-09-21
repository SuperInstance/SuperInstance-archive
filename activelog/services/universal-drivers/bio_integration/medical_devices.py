import asyncio
import threading
import time
import random
import json
import numpy as np
from typing import Dict, List, Any, Optional, Callable, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime, timedelta
import uuid

class MedicalDeviceType(Enum):
    DNA_SEQUENCER = "dna_sequencer"
    PROTEIN_SYNTHESIZER = "protein_synthesizer"
    PCR_MACHINE = "pcr_machine"
    CENTRIFUGE = "centrifuge"
    MICROSCOPE = "microscope"
    SPECTROPHOTOMETER = "spectrophotometer"
    INCUBATOR = "incubator"
    AUTOCLAVE = "autoclave"
    PIPETTE = "pipette"
    PLATE_READER = "plate_reader"
    FLOW_CYTOMETER = "flow_cytometer"
    CHROMATOGRAPH = "chromatograph"
    MASS_SPECTROMETER = "mass_spectrometer"
    ELECTROPHORESIS = "electrophoresis"
    PROSTHETIC_CONTROLLER = "prosthetic_controller"
    NEURAL_IMPLANT = "neural_implant"
    PACEMAKER = "pacemaker"
    INSULIN_PUMP = "insulin_pump"
    VENTILATOR = "ventilator"
    DIALYSIS_MACHINE = "dialysis_machine"

class DeviceStatus(Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"
    MAINTENANCE = "maintenance"
    CALIBRATING = "calibrating"
    READY = "ready"
    WARMING_UP = "warming_up"

class SafetyLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class MedicalDeviceConfig:
    device_type: MedicalDeviceType
    device_id: str
    manufacturer: str
    model: str
    serial_number: str
    software_version: str
    safety_level: SafetyLevel
    max_temperature: float
    max_pressure: float
    communication_protocol: str
    regulatory_approval: List[str]  # FDA, CE, etc.

@dataclass
class OperationParameters:
    operation_name: str
    parameters: Dict[str, Any]
    estimated_duration: float
    safety_checks_required: bool
    user_supervision_required: bool
    temperature_range: Optional[Tuple[float, float]] = None
    pressure_range: Optional[Tuple[float, float]] = None

@dataclass
class DeviceReading:
    timestamp: datetime
    parameter: str
    value: float
    unit: str
    status: str
    quality: float

class MedicalDevice:
    def __init__(self, config: MedicalDeviceConfig):
        self.config = config
        self.status = DeviceStatus.IDLE
        self.current_operation = None
        self.readings_buffer = []
        self.error_log = []
        self.maintenance_log = []
        self.callbacks = {}
        
        # Device state
        self.temperature = 22.0  # Room temperature
        self.pressure = 1013.25  # Standard atmospheric pressure
        self.humidity = 45.0
        self.last_calibration = datetime.now() - timedelta(days=30)
        self.operation_count = 0
        self.total_runtime = 0.0
        
        # Safety systems
        self.emergency_stop_active = False
        self.safety_interlocks = []
        self.alarm_conditions = {}
        
        # Initialize device-specific parameters
        self._initialize_device_specific()
        
    def _initialize_device_specific(self):
        """Initialize device-specific parameters"""
        device_type = self.config.device_type
        
        if device_type == MedicalDeviceType.DNA_SEQUENCER:
            self.sequencing_chemistry = "sequencing_by_synthesis"
            self.read_length = 150
            self.throughput_gb_per_run = 15
            self.accuracy = 0.999
            
        elif device_type == MedicalDeviceType.PROTEIN_SYNTHESIZER:
            self.synthesis_method = "solid_phase"
            self.max_peptide_length = 50
            self.coupling_efficiency = 0.98
            self.purity_target = 0.95
            
        elif device_type == MedicalDeviceType.PCR_MACHINE:
            self.block_format = "96_well"
            self.max_temperature = 105.0
            self.ramp_rate = 4.5  # °C/s
            self.temperature_accuracy = 0.2
            
        elif device_type == MedicalDeviceType.PROSTHETIC_CONTROLLER:
            self.control_modes = ["position", "velocity", "torque", "myoelectric"]
            self.dof_count = 6  # Degrees of freedom
            self.max_torque = 50.0  # Nm
            self.response_time = 0.1  # seconds
            
        elif device_type == MedicalDeviceType.NEURAL_IMPLANT:
            self.electrode_count = 96
            self.sampling_rate = 30000  # Hz
            self.stimulation_channels = 16
            self.power_consumption = 5.0  # mW
            
    async def initialize(self):
        """Initialize device"""
        print(f"Initializing {self.config.device_type.value}...")
        self.status = DeviceStatus.WARMING_UP
        
        # Simulate initialization time
        await asyncio.sleep(2)
        
        # Perform safety checks
        safety_ok = await self._perform_safety_checks()
        if not safety_ok:
            self.status = DeviceStatus.ERROR
            raise RuntimeError("Safety checks failed")
        
        # Check calibration
        if self._needs_calibration():
            await self.calibrate()
        
        self.status = DeviceStatus.READY
        print("Device initialization complete")
    
    async def _perform_safety_checks(self) -> bool:
        """Perform comprehensive safety checks"""
        print("Performing safety checks...")
        
        safety_checks = [
            ("Temperature sensors", self._check_temperature_sensors()),
            ("Pressure sensors", self._check_pressure_sensors()),
            ("Emergency stop", self._check_emergency_stop()),
            ("Door interlocks", self._check_door_interlocks()),
            ("Software integrity", self._check_software_integrity()),
            ("Power supply", self._check_power_supply())
        ]
        
        all_passed = True
        for check_name, passed in safety_checks:
            if passed:
                print(f"  ✓ {check_name}")
            else:
                print(f"  ✗ {check_name}")
                self._log_error(f"Safety check failed: {check_name}")
                all_passed = False
        
        return all_passed
    
    def _check_temperature_sensors(self) -> bool:
        return random.random() > 0.05  # 95% pass rate
    
    def _check_pressure_sensors(self) -> bool:
        return random.random() > 0.03  # 97% pass rate
    
    def _check_emergency_stop(self) -> bool:
        return not self.emergency_stop_active
    
    def _check_door_interlocks(self) -> bool:
        return random.random() > 0.02  # 98% pass rate
    
    def _check_software_integrity(self) -> bool:
        return random.random() > 0.01  # 99% pass rate
    
    def _check_power_supply(self) -> bool:
        return random.random() > 0.02  # 98% pass rate
    
    def _needs_calibration(self) -> bool:
        """Check if calibration is needed"""
        days_since_calibration = (datetime.now() - self.last_calibration).days
        
        # Different devices have different calibration intervals
        calibration_intervals = {
            MedicalDeviceType.DNA_SEQUENCER: 90,
            MedicalDeviceType.PCR_MACHINE: 30,
            MedicalDeviceType.SPECTROPHOTOMETER: 7,
            MedicalDeviceType.PIPETTE: 365,
            MedicalDeviceType.PROSTHETIC_CONTROLLER: 30,
            MedicalDeviceType.NEURAL_IMPLANT: 180
        }
        
        required_interval = calibration_intervals.get(self.config.device_type, 90)
        return days_since_calibration >= required_interval
    
    async def calibrate(self):
        """Perform device calibration"""
        print(f"Calibrating {self.config.device_type.value}...")
        self.status = DeviceStatus.CALIBRATING
        
        # Simulate calibration process
        calibration_steps = [
            "Baseline measurement",
            "Reference standard check",
            "Multi-point calibration",
            "Linearity verification",
            "Precision check"
        ]
        
        for step in calibration_steps:
            print(f"  {step}...")
            await asyncio.sleep(1)
        
        self.last_calibration = datetime.now()
        self.status = DeviceStatus.READY
        print("Calibration complete")
    
    async def start_operation(self, operation: OperationParameters):
        """Start a device operation"""
        if self.status != DeviceStatus.READY:
            raise RuntimeError(f"Device not ready. Current status: {self.status}")
        
        # Validate operation parameters
        if not self._validate_operation_parameters(operation):
            raise ValueError("Invalid operation parameters")
        
        # Perform pre-operation safety checks if required
        if operation.safety_checks_required:
            safety_ok = await self._perform_safety_checks()
            if not safety_ok:
                raise RuntimeError("Pre-operation safety checks failed")
        
        print(f"Starting operation: {operation.operation_name}")
        self.current_operation = operation
        self.status = DeviceStatus.RUNNING
        self.operation_count += 1
        
        # Start operation monitoring in background
        asyncio.create_task(self._monitor_operation())
        
        # Simulate operation execution
        asyncio.create_task(self._execute_operation())
    
    def _validate_operation_parameters(self, operation: OperationParameters) -> bool:
        """Validate operation parameters"""
        device_type = self.config.device_type
        
        if device_type == MedicalDeviceType.PCR_MACHINE:
            # Validate PCR parameters
            params = operation.parameters
            if 'cycles' not in params or not (1 <= params['cycles'] <= 50):
                return False
            if 'denaturation_temp' not in params or not (85 <= params['denaturation_temp'] <= 98):
                return False
            if 'annealing_temp' not in params or not (50 <= params['annealing_temp'] <= 72):
                return False
        
        elif device_type == MedicalDeviceType.DNA_SEQUENCER:
            params = operation.parameters
            if 'run_type' not in params or params['run_type'] not in ['rapid', 'standard', 'high_output']:
                return False
        
        elif device_type == MedicalDeviceType.PROSTHETIC_CONTROLLER:
            params = operation.parameters
            if 'control_mode' not in params or params['control_mode'] not in self.control_modes:
                return False
            if 'target_position' in params and not (-180 <= params['target_position'] <= 180):
                return False
        
        return True
    
    async def _monitor_operation(self):
        """Monitor operation progress and safety"""
        start_time = time.time()
        
        while self.status == DeviceStatus.RUNNING:
            # Update device readings
            await self._update_readings()
            
            # Check for alarm conditions
            self._check_alarm_conditions()
            
            # Update progress
            elapsed_time = time.time() - start_time
            if self.current_operation:
                progress = min(elapsed_time / self.current_operation.estimated_duration, 1.0)
                
                # Trigger progress callbacks
                if 'progress_update' in self.callbacks:
                    for callback in self.callbacks['progress_update']:
                        try:
                            callback(progress, elapsed_time)
                        except Exception as e:
                            print(f"Progress callback error: {e}")
            
            await asyncio.sleep(1)
    
    async def _execute_operation(self):
        """Execute the current operation"""
        if not self.current_operation:
            return
        
        operation = self.current_operation
        device_type = self.config.device_type
        
        try:
            if device_type == MedicalDeviceType.PCR_MACHINE:
                await self._execute_pcr(operation)
            elif device_type == MedicalDeviceType.DNA_SEQUENCER:
                await self._execute_sequencing(operation)
            elif device_type == MedicalDeviceType.PROTEIN_SYNTHESIZER:
                await self._execute_protein_synthesis(operation)
            elif device_type == MedicalDeviceType.PROSTHETIC_CONTROLLER:
                await self._execute_prosthetic_control(operation)
            elif device_type == MedicalDeviceType.NEURAL_IMPLANT:
                await self._execute_neural_stimulation(operation)
            else:
                # Generic operation execution
                await asyncio.sleep(operation.estimated_duration)
            
            self.status = DeviceStatus.READY
            self.current_operation = None
            self.total_runtime += operation.estimated_duration
            
            print(f"Operation '{operation.operation_name}' completed successfully")
            
            # Trigger completion callback
            if 'operation_complete' in self.callbacks:
                for callback in self.callbacks['operation_complete']:
                    try:
                        callback(operation, True)
                    except Exception as e:
                        print(f"Completion callback error: {e}")
        
        except Exception as e:
            self.status = DeviceStatus.ERROR
            self._log_error(f"Operation failed: {str(e)}")
            
            if 'operation_complete' in self.callbacks:
                for callback in self.callbacks['operation_complete']:
                    try:
                        callback(operation, False)
                    except Exception as e:
                        print(f"Error callback error: {e}")
    
    async def _execute_pcr(self, operation: OperationParameters):
        """Execute PCR operation"""
        params = operation.parameters
        cycles = params['cycles']
        
        print(f"Running PCR: {cycles} cycles")
        
        for cycle in range(cycles):
            # Denaturation
            self.temperature = params['denaturation_temp']
            await asyncio.sleep(0.1)  # Accelerated for demo
            
            # Annealing
            self.temperature = params['annealing_temp']
            await asyncio.sleep(0.1)
            
            # Extension
            self.temperature = params.get('extension_temp', 72)
            await asyncio.sleep(0.1)
            
            print(f"Cycle {cycle + 1}/{cycles} complete")
        
        self.temperature = 22.0  # Cool down
    
    async def _execute_sequencing(self, operation: OperationParameters):
        """Execute DNA sequencing operation"""
        params = operation.parameters
        run_type = params['run_type']
        
        run_times = {'rapid': 300, 'standard': 1800, 'high_output': 7200}  # seconds
        actual_duration = run_times.get(run_type, 1800)
        
        print(f"Running {run_type} sequencing run")
        
        # Simulate sequencing steps
        steps = ["Template preparation", "Sequencing", "Base calling", "Quality scoring"]
        step_duration = actual_duration / len(steps)
        
        for step in steps:
            print(f"  {step}...")
            await asyncio.sleep(step_duration / 10)  # Accelerated for demo
    
    async def _execute_protein_synthesis(self, operation: OperationParameters):
        """Execute protein synthesis operation"""
        params = operation.parameters
        sequence_length = params.get('sequence_length', 20)
        
        print(f"Synthesizing protein of {sequence_length} amino acids")
        
        for position in range(sequence_length):
            # Simulate coupling reaction
            await asyncio.sleep(0.1)  # Accelerated for demo
            
            # Random coupling efficiency
            efficiency = random.uniform(0.95, 0.99)
            if position % 5 == 0:
                print(f"Position {position + 1}: coupling efficiency {efficiency:.1%}")
    
    async def _execute_prosthetic_control(self, operation: OperationParameters):
        """Execute prosthetic control operation"""
        params = operation.parameters
        control_mode = params['control_mode']
        
        print(f"Prosthetic control: {control_mode} mode")
        
        if control_mode == "position":
            target_position = params['target_position']
            current_position = 0
            
            while abs(current_position - target_position) > 1:
                step = 5 if target_position > current_position else -5
                current_position += step
                print(f"Position: {current_position}°")
                await asyncio.sleep(0.1)
    
    async def _execute_neural_stimulation(self, operation: OperationParameters):
        """Execute neural stimulation operation"""
        params = operation.parameters
        stimulation_pattern = params.get('pattern', 'continuous')
        duration = params.get('duration', 10)
        
        print(f"Neural stimulation: {stimulation_pattern} for {duration}s")
        
        start_time = time.time()
        while time.time() - start_time < duration:
            # Simulate stimulation pulse
            print(f"Stimulation pulse at {time.time() - start_time:.1f}s")
            await asyncio.sleep(1)
    
    async def _update_readings(self):
        """Update device sensor readings"""
        timestamp = datetime.now()
        
        # Common readings for all devices
        readings = [
            DeviceReading(timestamp, "temperature", self.temperature + random.gauss(0, 0.1), "°C", "normal", 0.95),
            DeviceReading(timestamp, "pressure", self.pressure + random.gauss(0, 1), "hPa", "normal", 0.92),
            DeviceReading(timestamp, "humidity", self.humidity + random.gauss(0, 2), "%", "normal", 0.90)
        ]
        
        # Device-specific readings
        device_type = self.config.device_type
        
        if device_type == MedicalDeviceType.PCR_MACHINE and self.current_operation:
            readings.append(DeviceReading(timestamp, "block_temperature", self.temperature, "°C", "normal", 0.98))
            readings.append(DeviceReading(timestamp, "lid_temperature", self.temperature + 10, "°C", "normal", 0.95))
        
        elif device_type == MedicalDeviceType.DNA_SEQUENCER and self.current_operation:
            readings.append(DeviceReading(timestamp, "flow_rate", 1.5 + random.gauss(0, 0.1), "mL/min", "normal", 0.93))
            readings.append(DeviceReading(timestamp, "laser_power", 50 + random.gauss(0, 2), "mW", "normal", 0.97))
        
        elif device_type == MedicalDeviceType.PROSTHETIC_CONTROLLER:
            readings.append(DeviceReading(timestamp, "joint_angle", random.uniform(-90, 90), "degrees", "normal", 0.99))
            readings.append(DeviceReading(timestamp, "motor_current", random.uniform(0.1, 2.0), "A", "normal", 0.96))
        
        elif device_type == MedicalDeviceType.NEURAL_IMPLANT:
            readings.append(DeviceReading(timestamp, "stimulation_amplitude", 100 + random.gauss(0, 5), "μA", "normal", 0.98))
            readings.append(DeviceReading(timestamp, "impedance", 15 + random.gauss(0, 2), "kΩ", "normal", 0.94))
        
        # Store readings
        self.readings_buffer.extend(readings)
        if len(self.readings_buffer) > 1000:  # Keep last 1000 readings
            self.readings_buffer = self.readings_buffer[-1000:]
    
    def _check_alarm_conditions(self):
        """Check for alarm conditions"""
        alarms_triggered = []
        
        # Temperature alarm
        if self.temperature > self.config.max_temperature:
            alarms_triggered.append("high_temperature")
        
        # Pressure alarm  
        if self.pressure > self.config.max_pressure:
            alarms_triggered.append("high_pressure")
        
        # Process alarms
        for alarm in alarms_triggered:
            if alarm not in self.alarm_conditions:
                self.alarm_conditions[alarm] = datetime.now()
                self._trigger_alarm(alarm)
    
    def _trigger_alarm(self, alarm_type: str):
        """Trigger alarm"""
        print(f"⚠️  ALARM: {alarm_type}")
        
        if 'alarm' in self.callbacks:
            for callback in self.callbacks['alarm']:
                try:
                    callback(alarm_type, datetime.now())
                except Exception as e:
                    print(f"Alarm callback error: {e}")
    
    def _log_error(self, error_message: str):
        """Log error"""
        error_entry = {
            'timestamp': datetime.now().isoformat(),
            'message': error_message,
            'status': self.status.value,
            'operation': self.current_operation.operation_name if self.current_operation else None
        }
        self.error_log.append(error_entry)
        print(f"ERROR: {error_message}")
    
    def emergency_stop(self):
        """Activate emergency stop"""
        print("🚨 EMERGENCY STOP ACTIVATED")
        self.emergency_stop_active = True
        self.status = DeviceStatus.ERROR
        self.current_operation = None
        
        if 'emergency_stop' in self.callbacks:
            for callback in self.callbacks['emergency_stop']:
                try:
                    callback(datetime.now())
                except Exception as e:
                    print(f"Emergency stop callback error: {e}")
    
    def reset_emergency_stop(self):
        """Reset emergency stop"""
        self.emergency_stop_active = False
        self.status = DeviceStatus.IDLE
        print("Emergency stop reset")
    
    def register_callback(self, event_type: str, callback: Callable):
        """Register event callback"""
        if event_type not in self.callbacks:
            self.callbacks[event_type] = []
        self.callbacks[event_type].append(callback)
    
    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive device status"""
        return {
            'device_id': self.config.device_id,
            'device_type': self.config.device_type.value,
            'status': self.status.value,
            'current_operation': self.current_operation.operation_name if self.current_operation else None,
            'temperature': self.temperature,
            'pressure': self.pressure,
            'humidity': self.humidity,
            'operation_count': self.operation_count,
            'total_runtime': self.total_runtime,
            'last_calibration': self.last_calibration.isoformat(),
            'emergency_stop_active': self.emergency_stop_active,
            'active_alarms': list(self.alarm_conditions.keys()),
            'error_count': len(self.error_log)
        }
    
    def get_recent_readings(self, count: int = 10) -> List[Dict[str, Any]]:
        """Get recent sensor readings"""
        recent = self.readings_buffer[-count:] if self.readings_buffer else []
        return [
            {
                'timestamp': r.timestamp.isoformat(),
                'parameter': r.parameter,
                'value': r.value,
                'unit': r.unit,
                'status': r.status,
                'quality': r.quality
            }
            for r in recent
        ]

if __name__ == "__main__":
    print("Medical Device Simulation")
    print("=" * 50)
    
    async def demo():
        # Create PCR machine
        pcr_config = MedicalDeviceConfig(
            device_type=MedicalDeviceType.PCR_MACHINE,
            device_id="PCR_001",
            manufacturer="BioRad",
            model="CFX96",
            serial_number="BR123456",
            software_version="3.1.1",
            safety_level=SafetyLevel.HIGH,
            max_temperature=105.0,
            max_pressure=2000.0,
            communication_protocol="ethernet",
            regulatory_approval=["FDA", "CE"]
        )
        
        pcr = MedicalDevice(pcr_config)
        
        # Register callbacks
        def on_progress(progress, elapsed_time):
            print(f"Progress: {progress:.1%} ({elapsed_time:.1f}s)")
        
        def on_alarm(alarm_type, timestamp):
            print(f"ALARM TRIGGERED: {alarm_type} at {timestamp}")
        
        pcr.register_callback('progress_update', on_progress)
        pcr.register_callback('alarm', on_alarm)
        
        try:
            # Initialize device
            await pcr.initialize()
            
            # Prepare PCR operation
            pcr_operation = OperationParameters(
                operation_name="COVID-19 Detection",
                parameters={
                    'cycles': 35,
                    'denaturation_temp': 95.0,
                    'annealing_temp': 60.0,
                    'extension_temp': 72.0
                },
                estimated_duration=90.0,  # seconds
                safety_checks_required=True,
                user_supervision_required=True
            )
            
            # Start operation
            await pcr.start_operation(pcr_operation)
            
            # Monitor operation
            while pcr.status == DeviceStatus.RUNNING:
                await asyncio.sleep(1)
                status = pcr.get_status()
                print(f"Temperature: {status['temperature']:.1f}°C")
            
            print("Final status:", pcr.get_status())
            
        except Exception as e:
            print(f"Operation failed: {e}")
    
    asyncio.run(demo())