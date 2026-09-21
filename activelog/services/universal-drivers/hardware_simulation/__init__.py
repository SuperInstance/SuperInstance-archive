"""
Hardware Simulation Layer for Universal Driver System

This module provides comprehensive hardware simulation capabilities including:
- Virtual device creation and management
- Hardware emulation with realistic timing and constraints
- Protocol simulation for various communication standards
- Performance modeling and fault injection
- Load testing and integration testing support
"""

from .virtual_devices import (
    VirtualDevice,
    VirtualDeviceManager,
    DeviceType,
    DeviceConfig,
    DeviceState,
    Protocol,
    create_demo_environment
)

from .hardware_emulation import (
    HardwareEmulator,
    HardwareProfile,
    HardwareSpecs,
    TimingConstraints,
    EmulationMode,
    create_microcontroller_emulator,
    create_raspberry_pi_emulator
)

from .protocol_simulation import (
    ProtocolSimulator,
    ProtocolType,
    ProtocolConfig,
    Message,
    I2CSimulator,
    SPISimulator,
    UARTSimulator,
    CANSimulator,
    ProtocolBus
)

__version__ = "1.0.0"
__author__ = "Universal Driver Development Team"

__all__ = [
    # Virtual Devices
    'VirtualDevice',
    'VirtualDeviceManager', 
    'DeviceType',
    'DeviceConfig',
    'DeviceState',
    'Protocol',
    'create_demo_environment',
    
    # Hardware Emulation
    'HardwareEmulator',
    'HardwareProfile',
    'HardwareSpecs', 
    'TimingConstraints',
    'EmulationMode',
    'create_microcontroller_emulator',
    'create_raspberry_pi_emulator',
    
    # Protocol Simulation
    'ProtocolSimulator',
    'ProtocolType',
    'ProtocolConfig',
    'Message',
    'I2CSimulator',
    'SPISimulator', 
    'UARTSimulator',
    'CANSimulator',
    'ProtocolBus'
]