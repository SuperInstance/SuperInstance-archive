import asyncio
import json
import time
import random
import threading
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import uuid
from datetime import datetime, timedelta
import numpy as np

class EmulationMode(Enum):
    REAL_TIME = "real_time"
    ACCELERATED = "accelerated"
    STEP_BY_STEP = "step_by_step"
    REPLAY = "replay"

class HardwareProfile(Enum):
    MICROCONTROLLER = "microcontroller"
    SINGLE_BOARD_COMPUTER = "single_board_computer"
    EMBEDDED_SYSTEM = "embedded_system"
    INDUSTRIAL_CONTROLLER = "industrial_controller"
    IOT_DEVICE = "iot_device"
    FPGA = "fpga"
    DSP = "dsp"
    CUSTOM = "custom"

@dataclass
class HardwareSpecs:
    profile: HardwareProfile
    cpu_mhz: int
    ram_kb: int
    flash_kb: int
    gpio_pins: int
    analog_pins: int
    pwm_channels: int
    spi_channels: int
    i2c_channels: int
    uart_channels: int
    power_consumption_mw: float
    operating_voltage: float
    temperature_range: tuple

@dataclass
class TimingConstraints:
    instruction_cycle_ns: float
    interrupt_latency_us: float
    context_switch_us: float
    memory_access_ns: float
    peripheral_access_us: float
    dma_setup_us: float

class HardwareEmulator:
    def __init__(self, specs: HardwareSpecs, constraints: TimingConstraints):
        self.specs = specs
        self.constraints = constraints
        self.mode = EmulationMode.REAL_TIME
        self.time_scale = 1.0
        
        self.cpu_load = 0.0
        self.memory_usage = 0
        self.power_consumption = specs.power_consumption_mw
        self.temperature = 25.0
        
        self.gpio_states = {i: False for i in range(specs.gpio_pins)}
        self.analog_values = {i: 0.0 for i in range(specs.analog_pins)}
        self.pwm_values = {i: 0.0 for i in range(specs.pwm_channels)}
        
        self.peripherals = {}
        self.interrupt_handlers = {}
        self.memory_map = {}
        
        self.execution_log = []
        self.performance_metrics = {}
        
        self.is_running = False
        self.emulation_thread = None
        
    def start_emulation(self):
        if not self.is_running:
            self.is_running = True
            self.emulation_thread = threading.Thread(target=self._emulation_loop)
            self.emulation_thread.daemon = True
            self.emulation_thread.start()
    
    def stop_emulation(self):
        self.is_running = False
        if self.emulation_thread:
            self.emulation_thread.join()
    
    def _emulation_loop(self):
        last_update = time.time()
        
        while self.is_running:
            current_time = time.time()
            dt = (current_time - last_update) * self.time_scale
            
            if self.mode == EmulationMode.REAL_TIME:
                self._update_real_time(dt)
                time.sleep(0.001)  # 1ms sleep
            elif self.mode == EmulationMode.ACCELERATED:
                self._update_accelerated(dt)
                time.sleep(0.0001)  # 0.1ms sleep
            elif self.mode == EmulationMode.STEP_BY_STEP:
                self._wait_for_step()
            
            last_update = current_time
    
    def _update_real_time(self, dt):
        self._update_cpu_load()
        self._update_temperature(dt)
        self._update_power_consumption()
        self._process_interrupts()
        self._update_peripherals(dt)
        self._log_execution_state()
    
    def _update_accelerated(self, dt):
        self._update_real_time(dt * self.time_scale)
    
    def _wait_for_step(self):
        # Wait for external step command
        time.sleep(0.1)
    
    def _update_cpu_load(self):
        # Simulate variable CPU load based on active tasks
        base_load = 10 + len(self.peripherals) * 5
        variation = random.uniform(-5, 15)
        self.cpu_load = max(0, min(100, base_load + variation))
    
    def _update_temperature(self, dt):
        # Simple thermal model
        ambient_temp = 25.0
        thermal_resistance = 2.0  # °C/W
        thermal_capacity = 0.1  # J/°C
        
        power_dissipation = self.power_consumption / 1000.0  # Convert mW to W
        target_temp = ambient_temp + (power_dissipation * thermal_resistance)
        
        temp_change = (target_temp - self.temperature) * dt / thermal_capacity
        self.temperature += temp_change
        
        # Add noise
        self.temperature += random.uniform(-0.1, 0.1)
    
    def _update_power_consumption(self):
        # Calculate dynamic power based on CPU load and peripheral usage
        base_power = self.specs.power_consumption_mw * 0.3  # Static power
        dynamic_power = self.specs.power_consumption_mw * 0.7 * (self.cpu_load / 100.0)
        peripheral_power = sum(p.get('power_mw', 0) for p in self.peripherals.values())
        
        self.power_consumption = base_power + dynamic_power + peripheral_power
    
    def _process_interrupts(self):
        # Simulate interrupt processing
        for handler_name, handler in self.interrupt_handlers.items():
            if handler.get('pending', False):
                self._execute_interrupt(handler_name, handler)
    
    def _execute_interrupt(self, name: str, handler: Dict):
        start_time = time.time()
        
        # Simulate interrupt latency
        time.sleep(self.constraints.interrupt_latency_us / 1_000_000)
        
        # Execute handler function if provided
        if 'function' in handler:
            try:
                handler['function']()
            except Exception as e:
                self.execution_log.append({
                    'type': 'interrupt_error',
                    'name': name,
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                })
        
        handler['pending'] = False
        handler['last_executed'] = datetime.now().isoformat()
        
        execution_time = (time.time() - start_time) * 1_000_000  # Convert to microseconds
        self.execution_log.append({
            'type': 'interrupt_executed',
            'name': name,
            'execution_time_us': execution_time,
            'timestamp': datetime.now().isoformat()
        })
    
    def _update_peripherals(self, dt):
        for name, peripheral in self.peripherals.items():
            if 'update_function' in peripheral:
                try:
                    peripheral['update_function'](dt)
                except Exception as e:
                    self.execution_log.append({
                        'type': 'peripheral_error',
                        'name': name,
                        'error': str(e),
                        'timestamp': datetime.now().isoformat()
                    })
    
    def _log_execution_state(self):
        # Log system state periodically (every 100ms)
        if len(self.execution_log) == 0 or time.time() - getattr(self, '_last_log_time', 0) > 0.1:
            self.execution_log.append({
                'type': 'system_state',
                'cpu_load': self.cpu_load,
                'memory_usage': self.memory_usage,
                'power_consumption': self.power_consumption,
                'temperature': self.temperature,
                'timestamp': datetime.now().isoformat()
            })
            self._last_log_time = time.time()
    
    def set_gpio_pin(self, pin: int, value: bool):
        if 0 <= pin < self.specs.gpio_pins:
            self.gpio_states[pin] = value
            self._trigger_gpio_interrupt(pin, value)
        else:
            raise ValueError(f"Invalid GPIO pin: {pin}")
    
    def get_gpio_pin(self, pin: int) -> bool:
        if 0 <= pin < self.specs.gpio_pins:
            return self.gpio_states[pin]
        else:
            raise ValueError(f"Invalid GPIO pin: {pin}")
    
    def set_analog_value(self, pin: int, value: float):
        if 0 <= pin < self.specs.analog_pins:
            self.analog_values[pin] = max(0.0, min(3.3, value))  # Assume 3.3V ADC
        else:
            raise ValueError(f"Invalid analog pin: {pin}")
    
    def get_analog_value(self, pin: int) -> float:
        if 0 <= pin < self.specs.analog_pins:
            return self.analog_values[pin]
        else:
            raise ValueError(f"Invalid analog pin: {pin}")
    
    def set_pwm_duty(self, channel: int, duty: float):
        if 0 <= channel < self.specs.pwm_channels:
            self.pwm_values[channel] = max(0.0, min(1.0, duty))
        else:
            raise ValueError(f"Invalid PWM channel: {channel}")
    
    def get_pwm_duty(self, channel: int) -> float:
        if 0 <= channel < self.specs.pwm_channels:
            return self.pwm_values[channel]
        else:
            raise ValueError(f"Invalid PWM channel: {channel}")
    
    def _trigger_gpio_interrupt(self, pin: int, value: bool):
        interrupt_name = f"gpio_{pin}_interrupt"
        if interrupt_name in self.interrupt_handlers:
            self.interrupt_handlers[interrupt_name]['pending'] = True
    
    def register_interrupt_handler(self, name: str, function: Callable = None):
        self.interrupt_handlers[name] = {
            'function': function,
            'pending': False,
            'registered': datetime.now().isoformat()
        }
    
    def trigger_interrupt(self, name: str):
        if name in self.interrupt_handlers:
            self.interrupt_handlers[name]['pending'] = True
        else:
            raise ValueError(f"Unknown interrupt: {name}")
    
    def add_peripheral(self, name: str, config: Dict[str, Any]):
        self.peripherals[name] = config.copy()
        self.peripherals[name]['added'] = datetime.now().isoformat()
    
    def remove_peripheral(self, name: str):
        if name in self.peripherals:
            del self.peripherals[name]
    
    def allocate_memory(self, size_bytes: int, name: str = None) -> int:
        if not name:
            name = f"mem_{uuid.uuid4().hex[:8]}"
        
        if self.memory_usage + size_bytes > self.specs.ram_kb * 1024:
            raise RuntimeError("Out of memory")
        
        address = len(self.memory_map) * 4  # Simulate 32-bit addressing
        self.memory_map[address] = {
            'name': name,
            'size': size_bytes,
            'allocated': datetime.now().isoformat()
        }
        self.memory_usage += size_bytes
        
        return address
    
    def free_memory(self, address: int):
        if address in self.memory_map:
            self.memory_usage -= self.memory_map[address]['size']
            del self.memory_map[address]
    
    def read_memory(self, address: int, size: int) -> bytes:
        # Simulate memory read timing
        time.sleep(self.constraints.memory_access_ns / 1_000_000_000)
        
        if address in self.memory_map:
            # Return simulated data
            return bytes(random.randint(0, 255) for _ in range(size))
        else:
            raise RuntimeError(f"Invalid memory address: 0x{address:08X}")
    
    def write_memory(self, address: int, data: bytes):
        # Simulate memory write timing
        time.sleep(self.constraints.memory_access_ns / 1_000_000_000)
        
        if address in self.memory_map:
            # Simulate write operation
            pass
        else:
            raise RuntimeError(f"Invalid memory address: 0x{address:08X}")
    
    def set_emulation_mode(self, mode: EmulationMode, time_scale: float = 1.0):
        self.mode = mode
        self.time_scale = time_scale
    
    def step_execution(self):
        if self.mode == EmulationMode.STEP_BY_STEP:
            self._update_real_time(0.001)  # Step by 1ms
    
    def get_system_state(self) -> Dict[str, Any]:
        return {
            'specs': asdict(self.specs),
            'cpu_load': self.cpu_load,
            'memory_usage': self.memory_usage,
            'memory_total': self.specs.ram_kb * 1024,
            'power_consumption': self.power_consumption,
            'temperature': self.temperature,
            'gpio_states': self.gpio_states.copy(),
            'analog_values': self.analog_values.copy(),
            'pwm_values': self.pwm_values.copy(),
            'peripherals': list(self.peripherals.keys()),
            'interrupts': list(self.interrupt_handlers.keys()),
            'mode': self.mode.value,
            'time_scale': self.time_scale,
            'is_running': self.is_running
        }
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        recent_logs = [log for log in self.execution_log if log['type'] == 'system_state'][-100:]
        
        if not recent_logs:
            return {}
        
        cpu_loads = [log['cpu_load'] for log in recent_logs]
        temperatures = [log['temperature'] for log in recent_logs]
        power_consumptions = [log['power_consumption'] for log in recent_logs]
        
        return {
            'avg_cpu_load': np.mean(cpu_loads),
            'max_cpu_load': np.max(cpu_loads),
            'min_cpu_load': np.min(cpu_loads),
            'avg_temperature': np.mean(temperatures),
            'max_temperature': np.max(temperatures),
            'avg_power_consumption': np.mean(power_consumptions),
            'max_power_consumption': np.max(power_consumptions),
            'total_interrupts': len([log for log in self.execution_log if log['type'] == 'interrupt_executed']),
            'total_errors': len([log for log in self.execution_log if 'error' in log['type']]),
            'uptime_seconds': time.time() - getattr(self, '_start_time', time.time())
        }
    
    def export_execution_log(self, filename: str, limit: int = None):
        logs_to_export = self.execution_log
        if limit:
            logs_to_export = logs_to_export[-limit:]
        
        with open(filename, 'w') as f:
            json.dump(logs_to_export, f, indent=2)
    
    def inject_fault(self, fault_type: str, duration: float = 1.0, **kwargs):
        def restore_normal():
            time.sleep(duration)
            # Restore normal operation based on fault type
            
        if fault_type == "high_temperature":
            self.temperature += kwargs.get('temp_increase', 20)
        elif fault_type == "memory_corruption":
            # Simulate memory corruption
            corrupt_addresses = random.sample(list(self.memory_map.keys()), 
                                           min(len(self.memory_map), kwargs.get('corrupt_count', 1)))
            for addr in corrupt_addresses:
                self.memory_map[addr]['corrupted'] = True
        elif fault_type == "power_spike":
            self.power_consumption *= kwargs.get('spike_multiplier', 2.0)
        elif fault_type == "clock_drift":
            self.time_scale *= kwargs.get('drift_factor', 1.1)
        
        # Schedule restoration
        restore_thread = threading.Thread(target=restore_normal)
        restore_thread.daemon = True
        restore_thread.start()

def create_microcontroller_emulator():
    specs = HardwareSpecs(
        profile=HardwareProfile.MICROCONTROLLER,
        cpu_mhz=48,
        ram_kb=32,
        flash_kb=256,
        gpio_pins=20,
        analog_pins=8,
        pwm_channels=6,
        spi_channels=2,
        i2c_channels=2,
        uart_channels=2,
        power_consumption_mw=50.0,
        operating_voltage=3.3,
        temperature_range=(-40, 85)
    )
    
    constraints = TimingConstraints(
        instruction_cycle_ns=20.8,  # 48 MHz = 20.8ns per cycle
        interrupt_latency_us=2.0,
        context_switch_us=10.0,
        memory_access_ns=50.0,
        peripheral_access_us=1.0,
        dma_setup_us=5.0
    )
    
    return HardwareEmulator(specs, constraints)

def create_raspberry_pi_emulator():
    specs = HardwareSpecs(
        profile=HardwareProfile.SINGLE_BOARD_COMPUTER,
        cpu_mhz=1500,
        ram_kb=1024 * 1024,  # 1GB
        flash_kb=16 * 1024 * 1024,  # 16GB SD card
        gpio_pins=40,
        analog_pins=0,  # No built-in ADC
        pwm_channels=4,
        spi_channels=2,
        i2c_channels=2,
        uart_channels=2,
        power_consumption_mw=2500.0,
        operating_voltage=5.0,
        temperature_range=(0, 70)
    )
    
    constraints = TimingConstraints(
        instruction_cycle_ns=0.67,  # 1.5 GHz
        interrupt_latency_us=0.1,
        context_switch_us=1.0,
        memory_access_ns=10.0,
        peripheral_access_us=0.1,
        dma_setup_us=1.0
    )
    
    return HardwareEmulator(specs, constraints)

if __name__ == "__main__":
    print("Creating microcontroller emulator...")
    emulator = create_microcontroller_emulator()
    
    # Add some peripherals
    emulator.add_peripheral("led", {"type": "output", "pin": 13, "power_mw": 20})
    emulator.add_peripheral("button", {"type": "input", "pin": 2, "pullup": True})
    emulator.add_peripheral("temp_sensor", {"type": "i2c", "address": 0x48, "power_mw": 5})
    
    # Register interrupt handlers
    def button_handler():
        print("Button pressed!")
    
    emulator.register_interrupt_handler("gpio_2_interrupt", button_handler)
    
    emulator.start_emulation()
    
    try:
        print("Running emulation for 10 seconds...")
        
        # Simulate some activity
        for i in range(10):
            time.sleep(1)
            emulator.set_gpio_pin(13, i % 2 == 0)  # Blink LED
            
            if i == 3:
                emulator.set_gpio_pin(2, True)  # Trigger button
                time.sleep(0.1)
                emulator.set_gpio_pin(2, False)
            
            if i == 7:
                print("Injecting temperature fault...")
                emulator.inject_fault("high_temperature", duration=2.0, temp_increase=15)
        
        print("\nFinal system state:")
        state = emulator.get_system_state()
        for key, value in state.items():
            if key not in ['gpio_states', 'analog_values', 'pwm_values']:
                print(f"  {key}: {value}")
        
        print("\nPerformance metrics:")
        metrics = emulator.get_performance_metrics()
        for key, value in metrics.items():
            print(f"  {key}: {value:.2f}")
    
    finally:
        emulator.stop_emulation()
        print("Emulation stopped.")