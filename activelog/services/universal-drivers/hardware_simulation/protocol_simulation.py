import asyncio
import time
import random
import threading
from typing import Dict, List, Any, Optional, Callable, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import json
from datetime import datetime
import struct
import binascii

class ProtocolType(Enum):
    I2C = "i2c"
    SPI = "spi"
    UART = "uart"
    USB = "usb"
    CAN = "can"
    ETHERNET = "ethernet"
    MODBUS = "modbus"
    MQTT = "mqtt"
    HTTP = "http"
    CUSTOM = "custom"

@dataclass
class ProtocolConfig:
    protocol_type: ProtocolType
    parameters: Dict[str, Any]
    timing_params: Dict[str, float]
    error_injection: Dict[str, float]

@dataclass
class Message:
    protocol: ProtocolType
    source: str
    destination: str
    data: bytes
    timestamp: datetime
    message_id: str
    metadata: Dict[str, Any]

class ProtocolSimulator:
    def __init__(self, config: ProtocolConfig):
        self.config = config
        self.is_running = False
        self.message_queue = asyncio.Queue()
        self.handlers = {}
        self.statistics = {
            'messages_sent': 0,
            'messages_received': 0,
            'bytes_sent': 0,
            'bytes_received': 0,
            'errors': 0,
            'start_time': None
        }
        
    async def start(self):
        if not self.is_running:
            self.is_running = True
            self.statistics['start_time'] = datetime.now()
            await self._protocol_specific_start()
    
    async def stop(self):
        if self.is_running:
            self.is_running = False
            await self._protocol_specific_stop()
    
    async def send_message(self, destination: str, data: bytes, metadata: Dict[str, Any] = None) -> bool:
        if not self.is_running:
            return False
        
        # Simulate transmission delay
        delay = self._calculate_transmission_delay(len(data))
        await asyncio.sleep(delay)
        
        # Inject errors if configured
        if self._should_inject_error('transmission_error'):
            self.statistics['errors'] += 1
            return False
        
        message = Message(
            protocol=self.config.protocol_type,
            source="local",
            destination=destination,
            data=data,
            timestamp=datetime.now(),
            message_id=f"{self.config.protocol_type.value}_{int(time.time() * 1000000)}",
            metadata=metadata or {}
        )
        
        await self.message_queue.put(message)
        self.statistics['messages_sent'] += 1
        self.statistics['bytes_sent'] += len(data)
        
        return True
    
    async def receive_message(self, timeout: float = 1.0) -> Optional[Message]:
        try:
            message = await asyncio.wait_for(self.message_queue.get(), timeout=timeout)
            self.statistics['messages_received'] += 1
            self.statistics['bytes_received'] += len(message.data)
            return message
        except asyncio.TimeoutError:
            return None
    
    def _calculate_transmission_delay(self, data_length: int) -> float:
        protocol = self.config.protocol_type
        
        if protocol == ProtocolType.I2C:
            clock_freq = self.config.parameters.get('clock_frequency', 100000)  # 100kHz default
            bits_per_byte = 9  # 8 data bits + 1 ACK bit
            return (data_length * bits_per_byte) / clock_freq
        
        elif protocol == ProtocolType.SPI:
            clock_freq = self.config.parameters.get('clock_frequency', 1000000)  # 1MHz default
            return (data_length * 8) / clock_freq
        
        elif protocol == ProtocolType.UART:
            baud_rate = self.config.parameters.get('baud_rate', 9600)
            bits_per_byte = self.config.parameters.get('data_bits', 8) + \
                           self.config.parameters.get('stop_bits', 1) + \
                           (1 if self.config.parameters.get('parity') != 'none' else 0) + 1  # start bit
            return (data_length * bits_per_byte) / baud_rate
        
        elif protocol == ProtocolType.USB:
            speed = self.config.parameters.get('speed', 'full')  # low, full, high, super
            speeds = {'low': 1.5e6, 'full': 12e6, 'high': 480e6, 'super': 5e9}
            return (data_length * 8) / speeds.get(speed, 12e6)
        
        elif protocol == ProtocolType.CAN:
            bitrate = self.config.parameters.get('bitrate', 500000)  # 500kbps default
            # CAN frame overhead: start bit, arbitration field, control field, CRC, ACK, EOF
            overhead_bits = 64
            return ((data_length * 8) + overhead_bits) / bitrate
        
        elif protocol == ProtocolType.ETHERNET:
            speed = self.config.parameters.get('speed', 100)  # Mbps
            # Ethernet frame overhead: preamble, header, FCS
            overhead_bytes = 26
            return ((data_length + overhead_bytes) * 8) / (speed * 1e6)
        
        else:
            # Default delay for other protocols
            return self.config.timing_params.get('base_delay', 0.001)
    
    def _should_inject_error(self, error_type: str) -> bool:
        error_rate = self.config.error_injection.get(error_type, 0.0)
        return random.random() < error_rate
    
    async def _protocol_specific_start(self):
        protocol = self.config.protocol_type
        
        if protocol == ProtocolType.I2C:
            await self._start_i2c()
        elif protocol == ProtocolType.SPI:
            await self._start_spi()
        elif protocol == ProtocolType.UART:
            await self._start_uart()
        elif protocol == ProtocolType.USB:
            await self._start_usb()
        elif protocol == ProtocolType.CAN:
            await self._start_can()
        elif protocol == ProtocolType.ETHERNET:
            await self._start_ethernet()
        elif protocol == ProtocolType.MODBUS:
            await self._start_modbus()
        elif protocol == ProtocolType.MQTT:
            await self._start_mqtt()
        elif protocol == ProtocolType.HTTP:
            await self._start_http()
    
    async def _protocol_specific_stop(self):
        # Protocol-specific cleanup
        pass
    
    async def _start_i2c(self):
        # I2C-specific initialization
        self.i2c_address = self.config.parameters.get('address', 0x48)
        self.i2c_registers = {}
        
    async def _start_spi(self):
        # SPI-specific initialization
        self.spi_cs_pin = self.config.parameters.get('cs_pin', 0)
        self.spi_mode = self.config.parameters.get('mode', 0)
    
    async def _start_uart(self):
        # UART-specific initialization
        self.uart_buffer = bytearray()
        
    async def _start_usb(self):
        # USB-specific initialization
        self.usb_endpoints = {}
        self.usb_configuration = 1
    
    async def _start_can(self):
        # CAN-specific initialization
        self.can_filters = []
        self.can_node_id = self.config.parameters.get('node_id', 1)
    
    async def _start_ethernet(self):
        # Ethernet-specific initialization
        self.mac_address = self.config.parameters.get('mac_address', '00:11:22:33:44:55')
        self.ip_address = self.config.parameters.get('ip_address', '192.168.1.100')
    
    async def _start_modbus(self):
        # Modbus-specific initialization
        self.modbus_slave_id = self.config.parameters.get('slave_id', 1)
        self.holding_registers = [0] * 1000
        self.input_registers = [0] * 1000
        self.coils = [False] * 1000
        self.discrete_inputs = [False] * 1000
    
    async def _start_mqtt(self):
        # MQTT-specific initialization
        self.client_id = self.config.parameters.get('client_id', f'simulator_{int(time.time())}')
        self.subscriptions = {}
    
    async def _start_http(self):
        # HTTP-specific initialization
        self.routes = {}
        
    def register_handler(self, event_type: str, handler: Callable):
        if event_type not in self.handlers:
            self.handlers[event_type] = []
        self.handlers[event_type].append(handler)
    
    async def _trigger_handler(self, event_type: str, *args, **kwargs):
        if event_type in self.handlers:
            for handler in self.handlers[event_type]:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(*args, **kwargs)
                    else:
                        handler(*args, **kwargs)
                except Exception as e:
                    print(f"Handler error: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        stats = self.statistics.copy()
        if stats['start_time']:
            uptime = (datetime.now() - stats['start_time']).total_seconds()
            stats['uptime_seconds'] = uptime
            if uptime > 0:
                stats['messages_per_second'] = (stats['messages_sent'] + stats['messages_received']) / uptime
                stats['bytes_per_second'] = (stats['bytes_sent'] + stats['bytes_received']) / uptime
        return stats

class I2CSimulator(ProtocolSimulator):
    def __init__(self, address: int = 0x48, clock_frequency: int = 100000):
        config = ProtocolConfig(
            protocol_type=ProtocolType.I2C,
            parameters={
                'address': address,
                'clock_frequency': clock_frequency
            },
            timing_params={
                'setup_time': 4.7e-6,  # 4.7µs
                'hold_time': 4.0e-6,   # 4.0µs
            },
            error_injection={
                'nak_error': 0.001,
                'bus_contention': 0.0001
            }
        )
        super().__init__(config)
        self.registers = {}
    
    async def read_register(self, register: int) -> int:
        if self._should_inject_error('nak_error'):
            raise Exception("I2C NAK error")
        
        await asyncio.sleep(self.config.timing_params['setup_time'])
        return self.registers.get(register, 0)
    
    async def write_register(self, register: int, value: int):
        if self._should_inject_error('nak_error'):
            raise Exception("I2C NAK error")
        
        await asyncio.sleep(self.config.timing_params['setup_time'])
        self.registers[register] = value

class SPISimulator(ProtocolSimulator):
    def __init__(self, cs_pin: int = 0, clock_frequency: int = 1000000, mode: int = 0):
        config = ProtocolConfig(
            protocol_type=ProtocolType.SPI,
            parameters={
                'cs_pin': cs_pin,
                'clock_frequency': clock_frequency,
                'mode': mode
            },
            timing_params={
                'setup_time': 10e-9,   # 10ns
                'hold_time': 10e-9,    # 10ns
            },
            error_injection={
                'clock_error': 0.0001
            }
        )
        super().__init__(config)
    
    async def transfer(self, tx_data: bytes) -> bytes:
        if self._should_inject_error('clock_error'):
            raise Exception("SPI clock error")
        
        delay = self._calculate_transmission_delay(len(tx_data))
        await asyncio.sleep(delay)
        
        # Echo back data with some modification for simulation
        rx_data = bytes((b + 1) % 256 for b in tx_data)
        return rx_data

class UARTSimulator(ProtocolSimulator):
    def __init__(self, baud_rate: int = 9600, data_bits: int = 8, stop_bits: int = 1, parity: str = 'none'):
        config = ProtocolConfig(
            protocol_type=ProtocolType.UART,
            parameters={
                'baud_rate': baud_rate,
                'data_bits': data_bits,
                'stop_bits': stop_bits,
                'parity': parity
            },
            timing_params={
                'bit_time': 1.0 / baud_rate
            },
            error_injection={
                'framing_error': 0.001,
                'parity_error': 0.0005
            }
        )
        super().__init__(config)
        self.rx_buffer = bytearray()
        self.tx_buffer = bytearray()
    
    async def write(self, data: bytes):
        if self._should_inject_error('framing_error'):
            raise Exception("UART framing error")
        
        self.tx_buffer.extend(data)
        await self.send_message("uart_peer", data)
    
    async def read(self, count: int = 1) -> bytes:
        while len(self.rx_buffer) < count and self.is_running:
            message = await self.receive_message(timeout=0.1)
            if message:
                self.rx_buffer.extend(message.data)
            else:
                break
        
        result = bytes(self.rx_buffer[:count])
        self.rx_buffer = self.rx_buffer[count:]
        return result

class CANSimulator(ProtocolSimulator):
    def __init__(self, node_id: int = 1, bitrate: int = 500000):
        config = ProtocolConfig(
            protocol_type=ProtocolType.CAN,
            parameters={
                'node_id': node_id,
                'bitrate': bitrate
            },
            timing_params={
                'bit_time': 1.0 / bitrate
            },
            error_injection={
                'bit_error': 0.0001,
                'ack_error': 0.0002,
                'crc_error': 0.0001
            }
        )
        super().__init__(config)
        self.filters = []
    
    async def send_frame(self, can_id: int, data: bytes, extended: bool = False):
        if len(data) > 8:
            raise ValueError("CAN data length must be <= 8 bytes")
        
        if self._should_inject_error('bit_error'):
            raise Exception("CAN bit error")
        
        frame_data = struct.pack('<I', can_id) + data
        await self.send_message("can_bus", frame_data, {'extended': extended})
    
    async def receive_frame(self, timeout: float = 1.0) -> Optional[Tuple[int, bytes, bool]]:
        message = await self.receive_message(timeout)
        if message:
            can_id = struct.unpack('<I', message.data[:4])[0]
            data = message.data[4:]
            extended = message.metadata.get('extended', False)
            return can_id, data, extended
        return None

class ProtocolBus:
    def __init__(self):
        self.connected_devices = {}
        self.message_log = []
        self.is_running = False
        self.bus_thread = None
    
    def connect_device(self, device_id: str, simulator: ProtocolSimulator):
        self.connected_devices[device_id] = simulator
        simulator.bus = self
    
    def disconnect_device(self, device_id: str):
        if device_id in self.connected_devices:
            del self.connected_devices[device_id]
    
    async def start(self):
        if not self.is_running:
            self.is_running = True
            # Start all connected devices
            for simulator in self.connected_devices.values():
                await simulator.start()
    
    async def stop(self):
        if self.is_running:
            self.is_running = False
            # Stop all connected devices
            for simulator in self.connected_devices.values():
                await simulator.stop()
    
    async def broadcast_message(self, source_id: str, message: Message):
        self.message_log.append({
            'timestamp': message.timestamp.isoformat(),
            'source': source_id,
            'destination': message.destination,
            'protocol': message.protocol.value,
            'data_hex': binascii.hexlify(message.data).decode(),
            'metadata': message.metadata
        })
        
        # Deliver to target device(s)
        if message.destination == "broadcast":
            for device_id, simulator in self.connected_devices.items():
                if device_id != source_id:
                    await simulator.message_queue.put(message)
        else:
            if message.destination in self.connected_devices:
                await self.connected_devices[message.destination].message_queue.put(message)
    
    def get_message_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        return self.message_log[-limit:]
    
    def export_log(self, filename: str):
        with open(filename, 'w') as f:
            json.dump(self.message_log, f, indent=2)

async def demo_i2c_communication():
    print("Demonstrating I2C communication simulation...")
    
    # Create I2C devices
    master = I2CSimulator(address=0x00, clock_frequency=400000)  # 400kHz
    sensor = I2CSimulator(address=0x48, clock_frequency=400000)  # Temperature sensor
    
    # Create protocol bus
    bus = ProtocolBus()
    bus.connect_device("master", master)
    bus.connect_device("sensor", sensor)
    
    await bus.start()
    
    try:
        # Simulate sensor readings
        await sensor.write_register(0x00, 0x1234)  # Temperature register
        await sensor.write_register(0x01, 0x5678)  # Humidity register
        
        # Master reads from sensor
        temp_value = await sensor.read_register(0x00)
        humidity_value = await sensor.read_register(0x01)
        
        print(f"Temperature: 0x{temp_value:04X}")
        print(f"Humidity: 0x{humidity_value:04X}")
        
        # Show statistics
        print(f"Master stats: {master.get_statistics()}")
        print(f"Sensor stats: {sensor.get_statistics()}")
        
    finally:
        await bus.stop()

async def demo_spi_communication():
    print("Demonstrating SPI communication simulation...")
    
    master = SPISimulator(cs_pin=0, clock_frequency=1000000, mode=0)
    slave = SPISimulator(cs_pin=0, clock_frequency=1000000, mode=0)
    
    bus = ProtocolBus()
    bus.connect_device("spi_master", master)
    bus.connect_device("spi_slave", slave)
    
    await bus.start()
    
    try:
        # SPI transfer
        tx_data = b'\x01\x02\x03\x04'
        rx_data = await master.transfer(tx_data)
        
        print(f"TX: {binascii.hexlify(tx_data).decode()}")
        print(f"RX: {binascii.hexlify(rx_data).decode()}")
        
    finally:
        await bus.stop()

if __name__ == "__main__":
    print("Protocol Simulation Demo")
    print("=" * 50)
    
    asyncio.run(demo_i2c_communication())
    print()
    asyncio.run(demo_spi_communication())