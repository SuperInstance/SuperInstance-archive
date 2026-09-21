#!/usr/bin/env python3
"""
Protocol Converters
Universal protocol translation and conversion system for hardware drivers
"""

import struct
import json
import zlib
import hashlib
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass
from enum import Enum
from abc import ABC, abstractmethod
import binascii

class ProtocolType(Enum):
    """Supported protocol types"""
    I2C = "i2c"
    SPI = "spi"
    UART = "uart"
    USB = "usb"
    CAN = "can"
    MODBUS = "modbus"
    ETHERNET = "ethernet"
    TCP = "tcp"
    UDP = "udp"
    HTTP = "http"
    MQTT = "mqtt"
    CUSTOM = "custom"

class DataEncoding(Enum):
    """Data encoding types"""
    BINARY = "binary"
    ASCII = "ascii"
    UTF8 = "utf8"
    HEX = "hex"
    BASE64 = "base64"
    JSON = "json"
    PROTOBUF = "protobuf"
    MSGPACK = "msgpack"

class Endianness(Enum):
    """Byte order types"""
    LITTLE = "little"
    BIG = "big"
    NATIVE = "native"

@dataclass
class ProtocolMessage:
    """Universal protocol message container"""
    protocol: ProtocolType
    encoding: DataEncoding
    endianness: Endianness
    data: bytes
    headers: Dict[str, Any]
    metadata: Dict[str, Any]
    checksum: Optional[str] = None
    
    def __post_init__(self):
        if self.checksum is None:
            self.checksum = self._calculate_checksum()
    
    def _calculate_checksum(self) -> str:
        """Calculate CRC32 checksum of data"""
        return f"{zlib.crc32(self.data) & 0xffffffff:08x}"
    
    def verify_checksum(self) -> bool:
        """Verify message integrity"""
        return self.checksum == self._calculate_checksum()

class ProtocolConverter(ABC):
    """Abstract base class for protocol converters"""
    
    @abstractmethod
    def convert_from(self, source_message: ProtocolMessage, 
                    target_protocol: ProtocolType) -> ProtocolMessage:
        """Convert message from source protocol"""
        pass
    
    @abstractmethod
    def convert_to(self, target_message: ProtocolMessage, 
                  source_protocol: ProtocolType) -> ProtocolMessage:
        """Convert message to target protocol"""
        pass
    
    @abstractmethod
    def get_supported_protocols(self) -> List[ProtocolType]:
        """Get list of supported protocols"""
        pass

class UniversalProtocolConverter(ProtocolConverter):
    """Universal protocol converter with support for multiple protocols"""
    
    def __init__(self):
        self.converters = {
            ProtocolType.I2C: I2CConverter(),
            ProtocolType.SPI: SPIConverter(),
            ProtocolType.UART: UARTConverter(),
            ProtocolType.USB: USBConverter(),
            ProtocolType.CAN: CANConverter(),
            ProtocolType.MODBUS: ModbusConverter(),
            ProtocolType.ETHERNET: EthernetConverter(),
            ProtocolType.TCP: TCPConverter(),
            ProtocolType.UDP: UDPConverter(),
            ProtocolType.HTTP: HTTPConverter(),
            ProtocolType.MQTT: MQTTConverter()
        }
    
    def convert_between_protocols(self, message: ProtocolMessage, 
                                target_protocol: ProtocolType) -> ProtocolMessage:
        """Convert message between different protocols"""
        if message.protocol == target_protocol:
            return message
        
        source_converter = self.converters.get(message.protocol)
        target_converter = self.converters.get(target_protocol)
        
        if not source_converter or not target_converter:
            raise ValueError(f"Unsupported protocol conversion: {message.protocol} -> {target_protocol}")
        
        # Convert to universal format first
        universal_data = source_converter.to_universal_format(message)
        
        # Convert to target protocol
        return target_converter.from_universal_format(universal_data, target_protocol)
    
    def get_supported_protocols(self) -> List[ProtocolType]:
        """Get all supported protocols"""
        return list(self.converters.keys())
    
    def convert_from(self, source_message: ProtocolMessage, 
                    target_protocol: ProtocolType) -> ProtocolMessage:
        """Convert message from source protocol"""
        return self.convert_between_protocols(source_message, target_protocol)
    
    def convert_to(self, target_message: ProtocolMessage, 
                  source_protocol: ProtocolType) -> ProtocolMessage:
        """Convert message to target protocol"""
        return self.convert_between_protocols(target_message, source_protocol)

class ProtocolSpecificConverter(ABC):
    """Base class for protocol-specific converters"""
    
    @abstractmethod
    def to_universal_format(self, message: ProtocolMessage) -> Dict[str, Any]:
        """Convert protocol-specific message to universal format"""
        pass
    
    @abstractmethod
    def from_universal_format(self, universal_data: Dict[str, Any], 
                            target_protocol: ProtocolType) -> ProtocolMessage:
        """Convert universal format to protocol-specific message"""
        pass

class I2CConverter(ProtocolSpecificConverter):
    """I2C protocol converter"""
    
    def to_universal_format(self, message: ProtocolMessage) -> Dict[str, Any]:
        """Convert I2C message to universal format"""
        if len(message.data) < 1:
            raise ValueError("I2C message too short")
        
        addr_byte = message.data[0]
        device_address = (addr_byte >> 1) & 0x7F
        read_write = "read" if (addr_byte & 1) else "write"
        
        return {
            "device_address": device_address,
            "operation": read_write,
            "register": message.data[1] if len(message.data) > 1 else None,
            "data": message.data[2:] if len(message.data) > 2 else b'',
            "original_headers": message.headers,
            "original_metadata": message.metadata
        }
    
    def from_universal_format(self, universal_data: Dict[str, Any], 
                            target_protocol: ProtocolType) -> ProtocolMessage:
        """Convert universal format to I2C message"""
        device_addr = universal_data["device_address"]
        is_read = universal_data["operation"] == "read"
        
        # Construct I2C address byte
        addr_byte = (device_addr << 1) | (1 if is_read else 0)
        
        data = bytes([addr_byte])
        if universal_data.get("register") is not None:
            data += bytes([universal_data["register"]])
        if universal_data.get("data"):
            data += universal_data["data"]
        
        return ProtocolMessage(
            protocol=ProtocolType.I2C,
            encoding=DataEncoding.BINARY,
            endianness=Endianness.BIG,
            data=data,
            headers=universal_data.get("original_headers", {}),
            metadata=universal_data.get("original_metadata", {})
        )

class SPIConverter(ProtocolSpecificConverter):
    """SPI protocol converter"""
    
    def to_universal_format(self, message: ProtocolMessage) -> Dict[str, Any]:
        """Convert SPI message to universal format"""
        if len(message.data) < 1:
            raise ValueError("SPI message too short")
        
        return {
            "command": message.data[0],
            "data": message.data[1:] if len(message.data) > 1 else b'',
            "clock_settings": message.headers.get("clock", {}),
            "chip_select": message.headers.get("cs", 0),
            "original_headers": message.headers,
            "original_metadata": message.metadata
        }
    
    def from_universal_format(self, universal_data: Dict[str, Any], 
                            target_protocol: ProtocolType) -> ProtocolMessage:
        """Convert universal format to SPI message"""
        data = bytes([universal_data["command"]])
        if universal_data.get("data"):
            data += universal_data["data"]
        
        headers = universal_data.get("original_headers", {})
        if universal_data.get("clock_settings"):
            headers["clock"] = universal_data["clock_settings"]
        if universal_data.get("chip_select") is not None:
            headers["cs"] = universal_data["chip_select"]
        
        return ProtocolMessage(
            protocol=ProtocolType.SPI,
            encoding=DataEncoding.BINARY,
            endianness=Endianness.BIG,
            data=data,
            headers=headers,
            metadata=universal_data.get("original_metadata", {})
        )

class UARTConverter(ProtocolSpecificConverter):
    """UART protocol converter"""
    
    def to_universal_format(self, message: ProtocolMessage) -> Dict[str, Any]:
        """Convert UART message to universal format"""
        return {
            "data": message.data,
            "baud_rate": message.headers.get("baud_rate", 9600),
            "parity": message.headers.get("parity", "none"),
            "stop_bits": message.headers.get("stop_bits", 1),
            "data_bits": message.headers.get("data_bits", 8),
            "original_headers": message.headers,
            "original_metadata": message.metadata
        }
    
    def from_universal_format(self, universal_data: Dict[str, Any], 
                            target_protocol: ProtocolType) -> ProtocolMessage:
        """Convert universal format to UART message"""
        headers = {
            "baud_rate": universal_data.get("baud_rate", 9600),
            "parity": universal_data.get("parity", "none"),
            "stop_bits": universal_data.get("stop_bits", 1),
            "data_bits": universal_data.get("data_bits", 8)
        }
        headers.update(universal_data.get("original_headers", {}))
        
        return ProtocolMessage(
            protocol=ProtocolType.UART,
            encoding=DataEncoding.BINARY,
            endianness=Endianness.NATIVE,
            data=universal_data["data"],
            headers=headers,
            metadata=universal_data.get("original_metadata", {})
        )

class USBConverter(ProtocolSpecificConverter):
    """USB protocol converter"""
    
    def to_universal_format(self, message: ProtocolMessage) -> Dict[str, Any]:
        """Convert USB message to universal format"""
        return {
            "data": message.data,
            "endpoint": message.headers.get("endpoint", 0),
            "transfer_type": message.headers.get("transfer_type", "bulk"),
            "vendor_id": message.headers.get("vendor_id"),
            "product_id": message.headers.get("product_id"),
            "original_headers": message.headers,
            "original_metadata": message.metadata
        }
    
    def from_universal_format(self, universal_data: Dict[str, Any], 
                            target_protocol: ProtocolType) -> ProtocolMessage:
        """Convert universal format to USB message"""
        headers = {
            "endpoint": universal_data.get("endpoint", 0),
            "transfer_type": universal_data.get("transfer_type", "bulk")
        }
        if universal_data.get("vendor_id"):
            headers["vendor_id"] = universal_data["vendor_id"]
        if universal_data.get("product_id"):
            headers["product_id"] = universal_data["product_id"]
        headers.update(universal_data.get("original_headers", {}))
        
        return ProtocolMessage(
            protocol=ProtocolType.USB,
            encoding=DataEncoding.BINARY,
            endianness=Endianness.LITTLE,
            data=universal_data["data"],
            headers=headers,
            metadata=universal_data.get("original_metadata", {})
        )

class CANConverter(ProtocolSpecificConverter):
    """CAN bus protocol converter"""
    
    def to_universal_format(self, message: ProtocolMessage) -> Dict[str, Any]:
        """Convert CAN message to universal format"""
        return {
            "can_id": message.headers.get("can_id"),
            "extended": message.headers.get("extended", False),
            "remote": message.headers.get("remote", False),
            "data": message.data,
            "original_headers": message.headers,
            "original_metadata": message.metadata
        }
    
    def from_universal_format(self, universal_data: Dict[str, Any], 
                            target_protocol: ProtocolType) -> ProtocolMessage:
        """Convert universal format to CAN message"""
        headers = {
            "can_id": universal_data.get("can_id", 0),
            "extended": universal_data.get("extended", False),
            "remote": universal_data.get("remote", False)
        }
        headers.update(universal_data.get("original_headers", {}))
        
        return ProtocolMessage(
            protocol=ProtocolType.CAN,
            encoding=DataEncoding.BINARY,
            endianness=Endianness.BIG,
            data=universal_data["data"],
            headers=headers,
            metadata=universal_data.get("original_metadata", {})
        )

class ModbusConverter(ProtocolSpecificConverter):
    """Modbus protocol converter"""
    
    def to_universal_format(self, message: ProtocolMessage) -> Dict[str, Any]:
        """Convert Modbus message to universal format"""
        if len(message.data) < 2:
            raise ValueError("Modbus message too short")
        
        slave_address = message.data[0]
        function_code = message.data[1]
        
        return {
            "slave_address": slave_address,
            "function_code": function_code,
            "data": message.data[2:],
            "original_headers": message.headers,
            "original_metadata": message.metadata
        }
    
    def from_universal_format(self, universal_data: Dict[str, Any], 
                            target_protocol: ProtocolType) -> ProtocolMessage:
        """Convert universal format to Modbus message"""
        data = bytes([
            universal_data.get("slave_address", 1),
            universal_data.get("function_code", 3)
        ])
        if universal_data.get("data"):
            data += universal_data["data"]
        
        return ProtocolMessage(
            protocol=ProtocolType.MODBUS,
            encoding=DataEncoding.BINARY,
            endianness=Endianness.BIG,
            data=data,
            headers=universal_data.get("original_headers", {}),
            metadata=universal_data.get("original_metadata", {})
        )

class EthernetConverter(ProtocolSpecificConverter):
    """Ethernet protocol converter"""
    
    def to_universal_format(self, message: ProtocolMessage) -> Dict[str, Any]:
        """Convert Ethernet message to universal format"""
        if len(message.data) < 14:
            raise ValueError("Ethernet frame too short")
        
        dst_mac = message.data[0:6]
        src_mac = message.data[6:12]
        ethertype = struct.unpack('!H', message.data[12:14])[0]
        
        return {
            "dst_mac": dst_mac.hex(':'),
            "src_mac": src_mac.hex(':'),
            "ethertype": ethertype,
            "payload": message.data[14:],
            "original_headers": message.headers,
            "original_metadata": message.metadata
        }
    
    def from_universal_format(self, universal_data: Dict[str, Any], 
                            target_protocol: ProtocolType) -> ProtocolMessage:
        """Convert universal format to Ethernet message"""
        dst_mac = bytes.fromhex(universal_data.get("dst_mac", "ff:ff:ff:ff:ff:ff").replace(':', ''))
        src_mac = bytes.fromhex(universal_data.get("src_mac", "00:00:00:00:00:00").replace(':', ''))
        ethertype = struct.pack('!H', universal_data.get("ethertype", 0x0800))
        
        data = dst_mac + src_mac + ethertype
        if universal_data.get("payload"):
            data += universal_data["payload"]
        
        return ProtocolMessage(
            protocol=ProtocolType.ETHERNET,
            encoding=DataEncoding.BINARY,
            endianness=Endianness.BIG,
            data=data,
            headers=universal_data.get("original_headers", {}),
            metadata=universal_data.get("original_metadata", {})
        )

class TCPConverter(ProtocolSpecificConverter):
    """TCP protocol converter"""
    
    def to_universal_format(self, message: ProtocolMessage) -> Dict[str, Any]:
        """Convert TCP message to universal format"""
        return {
            "src_port": message.headers.get("src_port"),
            "dst_port": message.headers.get("dst_port"),
            "seq_num": message.headers.get("seq_num"),
            "ack_num": message.headers.get("ack_num"),
            "flags": message.headers.get("flags", {}),
            "data": message.data,
            "original_headers": message.headers,
            "original_metadata": message.metadata
        }
    
    def from_universal_format(self, universal_data: Dict[str, Any], 
                            target_protocol: ProtocolType) -> ProtocolMessage:
        """Convert universal format to TCP message"""
        headers = {
            "src_port": universal_data.get("src_port", 0),
            "dst_port": universal_data.get("dst_port", 0),
            "seq_num": universal_data.get("seq_num", 0),
            "ack_num": universal_data.get("ack_num", 0),
            "flags": universal_data.get("flags", {})
        }
        headers.update(universal_data.get("original_headers", {}))
        
        return ProtocolMessage(
            protocol=ProtocolType.TCP,
            encoding=DataEncoding.BINARY,
            endianness=Endianness.BIG,
            data=universal_data["data"],
            headers=headers,
            metadata=universal_data.get("original_metadata", {})
        )

class UDPConverter(ProtocolSpecificConverter):
    """UDP protocol converter"""
    
    def to_universal_format(self, message: ProtocolMessage) -> Dict[str, Any]:
        """Convert UDP message to universal format"""
        return {
            "src_port": message.headers.get("src_port"),
            "dst_port": message.headers.get("dst_port"),
            "data": message.data,
            "original_headers": message.headers,
            "original_metadata": message.metadata
        }
    
    def from_universal_format(self, universal_data: Dict[str, Any], 
                            target_protocol: ProtocolType) -> ProtocolMessage:
        """Convert universal format to UDP message"""
        headers = {
            "src_port": universal_data.get("src_port", 0),
            "dst_port": universal_data.get("dst_port", 0)
        }
        headers.update(universal_data.get("original_headers", {}))
        
        return ProtocolMessage(
            protocol=ProtocolType.UDP,
            encoding=DataEncoding.BINARY,
            endianness=Endianness.BIG,
            data=universal_data["data"],
            headers=headers,
            metadata=universal_data.get("original_metadata", {})
        )

class HTTPConverter(ProtocolSpecificConverter):
    """HTTP protocol converter"""
    
    def to_universal_format(self, message: ProtocolMessage) -> Dict[str, Any]:
        """Convert HTTP message to universal format"""
        return {
            "method": message.headers.get("method", "GET"),
            "url": message.headers.get("url", "/"),
            "version": message.headers.get("version", "HTTP/1.1"),
            "status_code": message.headers.get("status_code"),
            "headers": message.headers.get("http_headers", {}),
            "body": message.data,
            "original_headers": message.headers,
            "original_metadata": message.metadata
        }
    
    def from_universal_format(self, universal_data: Dict[str, Any], 
                            target_protocol: ProtocolType) -> ProtocolMessage:
        """Convert universal format to HTTP message"""
        headers = {
            "method": universal_data.get("method", "GET"),
            "url": universal_data.get("url", "/"),
            "version": universal_data.get("version", "HTTP/1.1"),
            "http_headers": universal_data.get("headers", {})
        }
        if universal_data.get("status_code"):
            headers["status_code"] = universal_data["status_code"]
        headers.update(universal_data.get("original_headers", {}))
        
        return ProtocolMessage(
            protocol=ProtocolType.HTTP,
            encoding=DataEncoding.ASCII,
            endianness=Endianness.NATIVE,
            data=universal_data.get("body", b''),
            headers=headers,
            metadata=universal_data.get("original_metadata", {})
        )

class MQTTConverter(ProtocolSpecificConverter):
    """MQTT protocol converter"""
    
    def to_universal_format(self, message: ProtocolMessage) -> Dict[str, Any]:
        """Convert MQTT message to universal format"""
        return {
            "topic": message.headers.get("topic", ""),
            "qos": message.headers.get("qos", 0),
            "retain": message.headers.get("retain", False),
            "payload": message.data,
            "original_headers": message.headers,
            "original_metadata": message.metadata
        }
    
    def from_universal_format(self, universal_data: Dict[str, Any], 
                            target_protocol: ProtocolType) -> ProtocolMessage:
        """Convert universal format to MQTT message"""
        headers = {
            "topic": universal_data.get("topic", ""),
            "qos": universal_data.get("qos", 0),
            "retain": universal_data.get("retain", False)
        }
        headers.update(universal_data.get("original_headers", {}))
        
        return ProtocolMessage(
            protocol=ProtocolType.MQTT,
            encoding=DataEncoding.UTF8,
            endianness=Endianness.NATIVE,
            data=universal_data.get("payload", b''),
            headers=headers,
            metadata=universal_data.get("original_metadata", {})
        )

class ProtocolTranslationEngine:
    """High-level protocol translation engine"""
    
    def __init__(self):
        self.universal_converter = UniversalProtocolConverter()
        self.translation_rules: Dict[str, Dict[str, Any]] = {}
        self.custom_mappings: Dict[str, callable] = {}
    
    def add_translation_rule(self, rule_name: str, source_protocol: ProtocolType,
                           target_protocol: ProtocolType, 
                           mapping_function: Optional[callable] = None):
        """Add custom translation rule"""
        self.translation_rules[rule_name] = {
            "source": source_protocol,
            "target": target_protocol,
            "mapping": mapping_function
        }
    
    def translate_message(self, message: ProtocolMessage, 
                         target_protocol: ProtocolType,
                         rule_name: Optional[str] = None) -> ProtocolMessage:
        """Translate message using specified rule or default converter"""
        if rule_name and rule_name in self.translation_rules:
            rule = self.translation_rules[rule_name]
            if rule["mapping"]:
                return rule["mapping"](message, target_protocol)
        
        # Use default universal converter
        return self.universal_converter.convert_between_protocols(message, target_protocol)
    
    def batch_translate(self, messages: List[ProtocolMessage], 
                       target_protocol: ProtocolType) -> List[ProtocolMessage]:
        """Batch translate multiple messages"""
        return [self.translate_message(msg, target_protocol) for msg in messages]
    
    def get_supported_translations(self) -> Dict[str, List[ProtocolType]]:
        """Get all supported protocol translations"""
        supported = {}
        for protocol in ProtocolType:
            supported[protocol.value] = [p for p in ProtocolType if p != protocol]
        return supported

# Example usage and testing
if __name__ == "__main__":
    # Create translation engine
    engine = ProtocolTranslationEngine()
    
    # Create sample I2C message
    i2c_message = ProtocolMessage(
        protocol=ProtocolType.I2C,
        encoding=DataEncoding.BINARY,
        endianness=Endianness.BIG,
        data=b'\x90\x00\xFF',  # Address 0x48, register 0x00, data 0xFF
        headers={},
        metadata={"description": "Temperature sensor read"}
    )
    
    print(f"Original I2C message: {i2c_message.data.hex()}")
    
    # Convert I2C to UART
    uart_message = engine.translate_message(i2c_message, ProtocolType.UART)
    print(f"Converted to UART: {uart_message.data.hex()}")
    
    # Convert I2C to Modbus
    modbus_message = engine.translate_message(i2c_message, ProtocolType.MODBUS)
    print(f"Converted to Modbus: {modbus_message.data.hex()}")
    
    # Convert back to I2C to verify round-trip
    back_to_i2c = engine.translate_message(modbus_message, ProtocolType.I2C)
    print(f"Round-trip back to I2C: {back_to_i2c.data.hex()}")
    
    # Test batch translation
    messages = [i2c_message] * 3
    uart_messages = engine.batch_translate(messages, ProtocolType.UART)
    print(f"Batch translated {len(uart_messages)} messages to UART")
    
    # Show supported translations
    supported = engine.get_supported_translations()
    print(f"\nSupported translations: {len(supported)} protocols")
    for protocol, targets in supported.items():
        print(f"  {protocol} -> {len(targets)} target protocols")