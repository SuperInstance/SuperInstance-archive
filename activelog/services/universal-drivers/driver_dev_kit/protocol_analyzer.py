#!/usr/bin/env python3
"""
Protocol Analyzer
Advanced protocol analysis and reverse engineering tools for hardware drivers
"""

import struct
import binascii
import time
import json
import statistics
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple, Union, BinaryIO
from dataclasses import dataclass, asdict
from enum import Enum
import re

class ProtocolType(Enum):
    """Supported protocol types"""
    I2C = "i2c"
    SPI = "spi"
    UART = "uart"
    USB = "usb"
    CAN = "can"
    ETHERNET = "ethernet"
    BLUETOOTH = "bluetooth"
    MODBUS = "modbus"
    CUSTOM = "custom"

class DataFormat(Enum):
    """Data format types"""
    BINARY = "binary"
    ASCII = "ascii"
    HEX = "hex"
    JSON = "json"
    PROTOBUF = "protobuf"
    MODBUS_RTU = "modbus_rtu"
    MODBUS_TCP = "modbus_tcp"

@dataclass
class ProtocolFrame:
    """Represents a single protocol frame"""
    timestamp: float
    direction: str  # 'tx' or 'rx'
    data: bytes
    protocol: ProtocolType
    metadata: Dict[str, Any] = None
    decoded: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

@dataclass
class ProtocolPattern:
    """Detected protocol pattern"""
    pattern_id: str
    pattern_type: str
    frequency: int
    confidence: float
    description: str
    sample_frames: List[ProtocolFrame]
    register_map: Optional[Dict[str, Any]] = None

class ProtocolAnalyzer:
    """Advanced protocol analyzer for reverse engineering and analysis"""
    
    def __init__(self):
        self.frames: List[ProtocolFrame] = []
        self.patterns: List[ProtocolPattern] = []
        self.statistics: Dict[str, Any] = {}
        self.decoders: Dict[ProtocolType, callable] = {
            ProtocolType.I2C: self._decode_i2c,
            ProtocolType.SPI: self._decode_spi,
            ProtocolType.UART: self._decode_uart,
            ProtocolType.USB: self._decode_usb,
            ProtocolType.CAN: self._decode_can,
            ProtocolType.MODBUS: self._decode_modbus,
        }
    
    def capture_frame(self, data: bytes, protocol: ProtocolType, 
                     direction: str = 'rx', metadata: Dict[str, Any] = None) -> str:
        """Capture a single protocol frame"""
        frame = ProtocolFrame(
            timestamp=time.time(),
            direction=direction,
            data=data,
            protocol=protocol,
            metadata=metadata or {}
        )
        
        # Attempt to decode the frame
        if protocol in self.decoders:
            try:
                frame.decoded = self.decoders[protocol](data, metadata or {})
            except Exception as e:
                frame.metadata['decode_error'] = str(e)
        
        self.frames.append(frame)
        frame_id = f"frame_{len(self.frames)-1}_{int(time.time())}"
        frame.metadata['frame_id'] = frame_id
        
        return frame_id
    
    def load_capture_file(self, filename: str, protocol: ProtocolType, 
                         format_type: DataFormat = DataFormat.HEX) -> int:
        """Load protocol capture from file"""
        frames_loaded = 0
        
        try:
            with open(filename, 'r') as f:
                if format_type == DataFormat.JSON:
                    data = json.load(f)
                    for frame_data in data.get('frames', []):
                        frame = ProtocolFrame(
                            timestamp=frame_data.get('timestamp', time.time()),
                            direction=frame_data.get('direction', 'rx'),
                            data=bytes.fromhex(frame_data['data']),
                            protocol=protocol,
                            metadata=frame_data.get('metadata', {})
                        )
                        self.frames.append(frame)
                        frames_loaded += 1
                        
                elif format_type == DataFormat.HEX:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            # Parse hex data
                            hex_data = re.findall(r'([0-9a-fA-F]{2})', line)
                            if hex_data:
                                data = bytes.fromhex(''.join(hex_data))
                                self.capture_frame(data, protocol)
                                frames_loaded += 1
                                
                elif format_type == DataFormat.BINARY:
                    # Read binary data in chunks
                    chunk_size = 1024
                    while True:
                        chunk = f.read(chunk_size)
                        if not chunk:
                            break
                        self.capture_frame(chunk.encode() if isinstance(chunk, str) else chunk, protocol)
                        frames_loaded += 1
                        
        except Exception as e:
            raise Exception(f"Failed to load capture file: {e}")
        
        return frames_loaded
    
    def analyze_patterns(self) -> List[ProtocolPattern]:
        """Analyze captured frames to detect patterns"""
        self.patterns = []
        
        if len(self.frames) < 2:
            return self.patterns
        
        # Pattern analysis techniques
        self._analyze_command_response_patterns()
        self._analyze_register_access_patterns()
        self._analyze_periodic_patterns()
        self._analyze_data_structure_patterns()
        
        return self.patterns
    
    def _analyze_command_response_patterns(self):
        """Detect command-response patterns"""
        cmd_resp_pairs = []
        
        for i in range(len(self.frames) - 1):
            current = self.frames[i]
            next_frame = self.frames[i + 1]
            
            # Look for TX followed by RX within reasonable time
            if (current.direction == 'tx' and next_frame.direction == 'rx' and 
                next_frame.timestamp - current.timestamp < 0.1):  # 100ms window
                
                cmd_resp_pairs.append((current, next_frame))
        
        if cmd_resp_pairs:
            pattern = ProtocolPattern(
                pattern_id="cmd_resp_001",
                pattern_type="command_response",
                frequency=len(cmd_resp_pairs),
                confidence=0.8 if len(cmd_resp_pairs) > 5 else 0.5,
                description=f"Command-response pattern detected ({len(cmd_resp_pairs)} pairs)",
                sample_frames=[pair[0] for pair in cmd_resp_pairs[:5]]
            )
            self.patterns.append(pattern)
    
    def _analyze_register_access_patterns(self):
        """Detect register read/write patterns"""
        register_accesses = {}
        
        for frame in self.frames:
            if len(frame.data) >= 2:  # Minimum for address + data
                addr = frame.data[0]
                if addr not in register_accesses:
                    register_accesses[addr] = []
                register_accesses[addr].append(frame)
        
        # Find frequently accessed registers
        frequent_regs = {addr: frames for addr, frames in register_accesses.items() 
                        if len(frames) > 3}
        
        if frequent_regs:
            register_map = {}
            for addr, frames in frequent_regs.items():
                values = [frame.data[1:] for frame in frames if len(frame.data) > 1]
                register_map[f"0x{addr:02X}"] = {
                    "access_count": len(frames),
                    "unique_values": len(set(values)),
                    "sample_values": [val.hex() for val in values[:5]]
                }
            
            pattern = ProtocolPattern(
                pattern_id="reg_access_001",
                pattern_type="register_access",
                frequency=sum(len(frames) for frames in frequent_regs.values()),
                confidence=0.9,
                description=f"Register access pattern detected ({len(frequent_regs)} registers)",
                sample_frames=list(frequent_regs.values())[0][:3],
                register_map=register_map
            )
            self.patterns.append(pattern)
    
    def _analyze_periodic_patterns(self):
        """Detect periodic/recurring patterns"""
        if len(self.frames) < 10:
            return
        
        # Group frames by similar data patterns
        pattern_groups = {}
        
        for frame in self.frames:
            # Create pattern key from first few bytes
            pattern_key = frame.data[:min(4, len(frame.data))].hex()
            
            if pattern_key not in pattern_groups:
                pattern_groups[pattern_key] = []
            pattern_groups[pattern_key].append(frame)
        
        # Find patterns that occur regularly
        for pattern_key, frames in pattern_groups.items():
            if len(frames) > 5:  # At least 5 occurrences
                timestamps = [f.timestamp for f in frames]
                intervals = [timestamps[i+1] - timestamps[i] for i in range(len(timestamps)-1)]
                
                if intervals:
                    avg_interval = statistics.mean(intervals)
                    std_dev = statistics.stdev(intervals) if len(intervals) > 1 else 0
                    
                    # Check if intervals are fairly consistent (low std dev)
                    if std_dev < avg_interval * 0.3:  # Within 30% of average
                        pattern = ProtocolPattern(
                            pattern_id=f"periodic_{pattern_key}",
                            pattern_type="periodic",
                            frequency=len(frames),
                            confidence=0.8 if std_dev < avg_interval * 0.1 else 0.6,
                            description=f"Periodic pattern (avg interval: {avg_interval:.3f}s)",
                            sample_frames=frames[:3]
                        )
                        self.patterns.append(pattern)
    
    def _analyze_data_structure_patterns(self):
        """Detect data structure patterns"""
        frame_lengths = [len(f.data) for f in self.frames]
        
        if not frame_lengths:
            return
        
        # Find common frame lengths
        length_counts = {}
        for length in frame_lengths:
            length_counts[length] = length_counts.get(length, 0) + 1
        
        # Check for consistent frame structures
        most_common_length = max(length_counts.items(), key=lambda x: x[1])
        
        if most_common_length[1] > len(self.frames) * 0.3:  # At least 30% of frames
            frames_with_common_length = [f for f in self.frames 
                                       if len(f.data) == most_common_length[0]]
            
            pattern = ProtocolPattern(
                pattern_id="struct_001",
                pattern_type="data_structure",
                frequency=most_common_length[1],
                confidence=0.7,
                description=f"Fixed-length data structure ({most_common_length[0]} bytes)",
                sample_frames=frames_with_common_length[:3]
            )
            self.patterns.append(pattern)
    
    def generate_statistics(self) -> Dict[str, Any]:
        """Generate comprehensive statistics about captured data"""
        if not self.frames:
            return {}
        
        timestamps = [f.timestamp for f in self.frames]
        frame_sizes = [len(f.data) for f in self.frames]
        
        self.statistics = {
            "capture_info": {
                "total_frames": len(self.frames),
                "capture_duration": max(timestamps) - min(timestamps) if len(timestamps) > 1 else 0,
                "first_frame": datetime.fromtimestamp(min(timestamps)).isoformat(),
                "last_frame": datetime.fromtimestamp(max(timestamps)).isoformat()
            },
            "frame_statistics": {
                "avg_frame_size": statistics.mean(frame_sizes),
                "min_frame_size": min(frame_sizes),
                "max_frame_size": max(frame_sizes),
                "total_bytes": sum(frame_sizes)
            },
            "protocol_breakdown": {},
            "direction_breakdown": {"tx": 0, "rx": 0},
            "timing_analysis": {}
        }
        
        # Protocol breakdown
        for frame in self.frames:
            protocol = frame.protocol.value
            if protocol not in self.statistics["protocol_breakdown"]:
                self.statistics["protocol_breakdown"][protocol] = 0
            self.statistics["protocol_breakdown"][protocol] += 1
            
            # Direction breakdown
            self.statistics["direction_breakdown"][frame.direction] += 1
        
        # Timing analysis
        if len(timestamps) > 1:
            intervals = [timestamps[i+1] - timestamps[i] for i in range(len(timestamps)-1)]
            self.statistics["timing_analysis"] = {
                "avg_interval": statistics.mean(intervals),
                "min_interval": min(intervals),
                "max_interval": max(intervals),
                "frame_rate": len(self.frames) / (max(timestamps) - min(timestamps))
            }
        
        return self.statistics
    
    def _decode_i2c(self, data: bytes, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Decode I2C protocol data"""
        decoded = {"protocol": "I2C"}
        
        if len(data) >= 1:
            # First byte typically contains address and R/W bit
            addr_byte = data[0]
            decoded["address"] = (addr_byte >> 1) & 0x7F
            decoded["read_write"] = "read" if (addr_byte & 1) else "write"
            
            if len(data) > 1:
                decoded["data"] = data[1:].hex()
                decoded["data_length"] = len(data) - 1
        
        return decoded
    
    def _decode_spi(self, data: bytes, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Decode SPI protocol data"""
        decoded = {"protocol": "SPI"}
        
        if len(data) >= 1:
            decoded["command"] = f"0x{data[0]:02X}"
            
            if len(data) > 1:
                decoded["data"] = data[1:].hex()
                decoded["data_length"] = len(data) - 1
        
        # SPI-specific metadata
        if "clock_phase" in metadata:
            decoded["clock_phase"] = metadata["clock_phase"]
        if "clock_polarity" in metadata:
            decoded["clock_polarity"] = metadata["clock_polarity"]
        
        return decoded
    
    def _decode_uart(self, data: bytes, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Decode UART protocol data"""
        decoded = {"protocol": "UART"}
        
        decoded["data_hex"] = data.hex()
        decoded["data_length"] = len(data)
        
        # Try to decode as ASCII
        try:
            ascii_data = data.decode('ascii')
            if ascii_data.isprintable():
                decoded["ascii"] = ascii_data
        except:
            pass
        
        # UART-specific metadata
        if "baud_rate" in metadata:
            decoded["baud_rate"] = metadata["baud_rate"]
        if "parity" in metadata:
            decoded["parity"] = metadata["parity"]
        
        return decoded
    
    def _decode_usb(self, data: bytes, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Decode USB protocol data"""
        decoded = {"protocol": "USB"}
        
        if len(data) >= 1:
            # Basic USB packet structure
            decoded["data_hex"] = data.hex()
            decoded["data_length"] = len(data)
        
        # USB-specific metadata
        if "endpoint" in metadata:
            decoded["endpoint"] = metadata["endpoint"]
        if "transfer_type" in metadata:
            decoded["transfer_type"] = metadata["transfer_type"]
        
        return decoded
    
    def _decode_can(self, data: bytes, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Decode CAN protocol data"""
        decoded = {"protocol": "CAN"}
        
        decoded["data_hex"] = data.hex()
        decoded["data_length"] = len(data)
        
        # CAN-specific metadata
        if "can_id" in metadata:
            decoded["can_id"] = f"0x{metadata['can_id']:03X}"
        if "extended" in metadata:
            decoded["extended_frame"] = metadata["extended"]
        
        return decoded
    
    def _decode_modbus(self, data: bytes, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Decode Modbus protocol data"""
        decoded = {"protocol": "Modbus"}
        
        if len(data) >= 2:
            decoded["slave_address"] = data[0]
            decoded["function_code"] = data[1]
            
            # Decode based on function code
            if data[1] == 0x03:  # Read holding registers
                decoded["function"] = "read_holding_registers"
                if len(data) >= 6:
                    start_addr = struct.unpack('>H', data[2:4])[0]
                    reg_count = struct.unpack('>H', data[4:6])[0]
                    decoded["start_address"] = start_addr
                    decoded["register_count"] = reg_count
            elif data[1] == 0x06:  # Write single register
                decoded["function"] = "write_single_register"
                if len(data) >= 6:
                    reg_addr = struct.unpack('>H', data[2:4])[0]
                    reg_value = struct.unpack('>H', data[4:6])[0]
                    decoded["register_address"] = reg_addr
                    decoded["register_value"] = reg_value
        
        return decoded
    
    def export_analysis(self, filename: str, format_type: str = "json") -> bool:
        """Export analysis results"""
        try:
            export_data = {
                "metadata": {
                    "export_timestamp": datetime.now().isoformat(),
                    "analyzer_version": "1.0.0",
                    "total_frames": len(self.frames),
                    "total_patterns": len(self.patterns)
                },
                "statistics": self.statistics,
                "patterns": [asdict(pattern) for pattern in self.patterns],
                "frames": []
            }
            
            # Include sample frames (not all to keep file size manageable)
            sample_size = min(100, len(self.frames))
            for frame in self.frames[:sample_size]:
                frame_data = {
                    "timestamp": frame.timestamp,
                    "direction": frame.direction,
                    "protocol": frame.protocol.value,
                    "data": frame.data.hex(),
                    "metadata": frame.metadata,
                    "decoded": frame.decoded
                }
                export_data["frames"].append(frame_data)
            
            if format_type.lower() == "json":
                with open(filename, 'w') as f:
                    json.dump(export_data, f, indent=2, default=str)
            else:
                raise ValueError(f"Unsupported export format: {format_type}")
            
            return True
        except Exception as e:
            print(f"Export failed: {e}")
            return False
    
    def clear_analysis(self):
        """Clear all captured data and analysis"""
        self.frames.clear()
        self.patterns.clear()
        self.statistics.clear()
    
    def get_frame_by_id(self, frame_id: str) -> Optional[ProtocolFrame]:
        """Get frame by ID"""
        for frame in self.frames:
            if frame.metadata.get('frame_id') == frame_id:
                return frame
        return None
    
    def search_frames(self, pattern: bytes, protocol: Optional[ProtocolType] = None) -> List[ProtocolFrame]:
        """Search for frames containing specific byte pattern"""
        matching_frames = []
        
        for frame in self.frames:
            if protocol and frame.protocol != protocol:
                continue
            
            if pattern in frame.data:
                matching_frames.append(frame)
        
        return matching_frames

# Example usage and testing
if __name__ == "__main__":
    # Create analyzer instance
    analyzer = ProtocolAnalyzer()
    
    # Simulate capturing some I2C frames
    print("Simulating I2C protocol capture...")
    
    # Device address 0x48, reading temperature register
    analyzer.capture_frame(b'\x90\x00', ProtocolType.I2C, 'tx', {'description': 'Read temp register'})
    analyzer.capture_frame(b'\x91\x1A\x2B', ProtocolType.I2C, 'rx', {'description': 'Temperature data'})
    
    # Repeat the pattern
    time.sleep(0.1)
    analyzer.capture_frame(b'\x90\x00', ProtocolType.I2C, 'tx')
    analyzer.capture_frame(b'\x91\x1A\x2C', ProtocolType.I2C, 'rx')
    
    time.sleep(0.1)
    analyzer.capture_frame(b'\x90\x01', ProtocolType.I2C, 'tx', {'description': 'Read config register'})
    analyzer.capture_frame(b'\x91\xFF', ProtocolType.I2C, 'rx')
    
    # Analyze patterns
    patterns = analyzer.analyze_patterns()
    print(f"\nDetected {len(patterns)} patterns:")
    for pattern in patterns:
        print(f"- {pattern.pattern_type}: {pattern.description}")
    
    # Generate statistics
    stats = analyzer.generate_statistics()
    print(f"\nCapture Statistics:")
    print(f"- Total frames: {stats['capture_info']['total_frames']}")
    print(f"- Total bytes: {stats['frame_statistics']['total_bytes']}")
    print(f"- Average frame size: {stats['frame_statistics']['avg_frame_size']:.1f} bytes")
    
    # Export analysis
    if analyzer.export_analysis("sample_analysis.json"):
        print("\nAnalysis exported to sample_analysis.json")