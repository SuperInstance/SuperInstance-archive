#!/usr/bin/env python3
"""
Packet Sniffer and Decoder
Real-time packet capture and decoding for hardware protocol analysis
"""

import socket
import struct
import time
import threading
import queue
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from enum import Enum
import json

class CaptureMode(Enum):
    """Packet capture modes"""
    RAW_ETHERNET = "raw_ethernet"
    RAW_IP = "raw_ip"
    UDP = "udp"
    TCP = "tcp"
    SERIAL = "serial"
    GPIO = "gpio"
    I2C = "i2c"
    SPI = "spi"

@dataclass
class PacketInfo:
    """Information about a captured packet"""
    timestamp: float
    capture_mode: CaptureMode
    source: str
    destination: str
    protocol: str
    length: int
    data: bytes
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

class PacketDecoder:
    """Decode various packet types and protocols"""
    
    @staticmethod
    def decode_ethernet(data: bytes) -> Dict[str, Any]:
        """Decode Ethernet frame"""
        if len(data) < 14:
            return {"error": "Ethernet frame too short"}
        
        # Ethernet header: dst(6) + src(6) + type(2)
        dst_mac = ':'.join(f'{b:02x}' for b in data[0:6])
        src_mac = ':'.join(f'{b:02x}' for b in data[6:12])
        eth_type = struct.unpack('!H', data[12:14])[0]
        
        decoded = {
            "dst_mac": dst_mac,
            "src_mac": src_mac,
            "ethertype": f"0x{eth_type:04x}",
            "payload_length": len(data) - 14
        }
        
        # Decode based on EtherType
        if eth_type == 0x0800:  # IPv4
            decoded["protocol"] = "IPv4"
            if len(data) > 14:
                decoded["ip_data"] = PacketDecoder.decode_ipv4(data[14:])
        elif eth_type == 0x86DD:  # IPv6
            decoded["protocol"] = "IPv6"
        elif eth_type == 0x0806:  # ARP
            decoded["protocol"] = "ARP"
            if len(data) > 14:
                decoded["arp_data"] = PacketDecoder.decode_arp(data[14:])
        
        return decoded
    
    @staticmethod
    def decode_ipv4(data: bytes) -> Dict[str, Any]:
        """Decode IPv4 packet"""
        if len(data) < 20:
            return {"error": "IPv4 packet too short"}
        
        # IPv4 header
        version_ihl = data[0]
        version = (version_ihl >> 4) & 0xF
        ihl = (version_ihl & 0xF) * 4  # Header length in bytes
        
        tos = data[1]
        total_length = struct.unpack('!H', data[2:4])[0]
        identification = struct.unpack('!H', data[4:6])[0]
        flags_fragment = struct.unpack('!H', data[6:8])[0]
        ttl = data[8]
        protocol = data[9]
        checksum = struct.unpack('!H', data[10:12])[0]
        
        src_ip = '.'.join(str(b) for b in data[12:16])
        dst_ip = '.'.join(str(b) for b in data[16:20])
        
        decoded = {
            "version": version,
            "header_length": ihl,
            "tos": tos,
            "total_length": total_length,
            "identification": identification,
            "flags": (flags_fragment >> 13) & 0x7,
            "fragment_offset": flags_fragment & 0x1FFF,
            "ttl": ttl,
            "protocol": protocol,
            "checksum": f"0x{checksum:04x}",
            "src_ip": src_ip,
            "dst_ip": dst_ip
        }
        
        # Decode transport layer
        if protocol == 6:  # TCP
            decoded["transport"] = "TCP"
            if len(data) > ihl:
                decoded["tcp_data"] = PacketDecoder.decode_tcp(data[ihl:])
        elif protocol == 17:  # UDP
            decoded["transport"] = "UDP"
            if len(data) > ihl:
                decoded["udp_data"] = PacketDecoder.decode_udp(data[ihl:])
        elif protocol == 1:  # ICMP
            decoded["transport"] = "ICMP"
        
        return decoded
    
    @staticmethod
    def decode_tcp(data: bytes) -> Dict[str, Any]:
        """Decode TCP segment"""
        if len(data) < 20:
            return {"error": "TCP segment too short"}
        
        src_port = struct.unpack('!H', data[0:2])[0]
        dst_port = struct.unpack('!H', data[2:4])[0]
        seq_num = struct.unpack('!I', data[4:8])[0]
        ack_num = struct.unpack('!I', data[8:12])[0]
        
        header_flags = struct.unpack('!H', data[12:14])[0]
        header_length = ((header_flags >> 12) & 0xF) * 4
        flags = header_flags & 0x1FF
        
        window_size = struct.unpack('!H', data[14:16])[0]
        checksum = struct.unpack('!H', data[16:18])[0]
        urgent_ptr = struct.unpack('!H', data[18:20])[0]
        
        return {
            "src_port": src_port,
            "dst_port": dst_port,
            "seq_num": seq_num,
            "ack_num": ack_num,
            "header_length": header_length,
            "flags": {
                "fin": bool(flags & 0x01),
                "syn": bool(flags & 0x02),
                "rst": bool(flags & 0x04),
                "psh": bool(flags & 0x08),
                "ack": bool(flags & 0x10),
                "urg": bool(flags & 0x20)
            },
            "window_size": window_size,
            "checksum": f"0x{checksum:04x}",
            "urgent_ptr": urgent_ptr,
            "payload_length": len(data) - header_length
        }
    
    @staticmethod
    def decode_udp(data: bytes) -> Dict[str, Any]:
        """Decode UDP datagram"""
        if len(data) < 8:
            return {"error": "UDP datagram too short"}
        
        src_port = struct.unpack('!H', data[0:2])[0]
        dst_port = struct.unpack('!H', data[2:4])[0]
        length = struct.unpack('!H', data[4:6])[0]
        checksum = struct.unpack('!H', data[6:8])[0]
        
        return {
            "src_port": src_port,
            "dst_port": dst_port,
            "length": length,
            "checksum": f"0x{checksum:04x}",
            "payload_length": length - 8
        }
    
    @staticmethod
    def decode_arp(data: bytes) -> Dict[str, Any]:
        """Decode ARP packet"""
        if len(data) < 28:
            return {"error": "ARP packet too short"}
        
        hardware_type = struct.unpack('!H', data[0:2])[0]
        protocol_type = struct.unpack('!H', data[2:4])[0]
        hardware_len = data[4]
        protocol_len = data[5]
        operation = struct.unpack('!H', data[6:8])[0]
        
        sender_mac = ':'.join(f'{b:02x}' for b in data[8:14])
        sender_ip = '.'.join(str(b) for b in data[14:18])
        target_mac = ':'.join(f'{b:02x}' for b in data[18:24])
        target_ip = '.'.join(str(b) for b in data[24:28])
        
        return {
            "hardware_type": hardware_type,
            "protocol_type": f"0x{protocol_type:04x}",
            "hardware_len": hardware_len,
            "protocol_len": protocol_len,
            "operation": "request" if operation == 1 else "reply" if operation == 2 else f"unknown({operation})",
            "sender_mac": sender_mac,
            "sender_ip": sender_ip,
            "target_mac": target_mac,
            "target_ip": target_ip
        }

class PacketSniffer:
    """Multi-protocol packet sniffer and analyzer"""
    
    def __init__(self):
        self.capture_active = False
        self.capture_thread = None
        self.packet_queue = queue.Queue()
        self.packet_callbacks: List[Callable[[PacketInfo], None]] = []
        self.statistics = {
            "total_packets": 0,
            "bytes_captured": 0,
            "protocols": {},
            "capture_start": None,
            "capture_duration": 0
        }
        
    def add_packet_callback(self, callback: Callable[[PacketInfo], None]):
        """Add callback for packet processing"""
        self.packet_callbacks.append(callback)
    
    def remove_packet_callback(self, callback: Callable[[PacketInfo], None]):
        """Remove packet callback"""
        if callback in self.packet_callbacks:
            self.packet_callbacks.remove(callback)
    
    def start_capture(self, mode: CaptureMode, interface: str = None, 
                     filter_params: Dict[str, Any] = None) -> bool:
        """Start packet capture"""
        if self.capture_active:
            return False
        
        self.capture_active = True
        self.statistics["capture_start"] = time.time()
        self.statistics["total_packets"] = 0
        self.statistics["bytes_captured"] = 0
        self.statistics["protocols"] = {}
        
        if mode == CaptureMode.RAW_ETHERNET:
            self.capture_thread = threading.Thread(
                target=self._capture_raw_ethernet,
                args=(interface, filter_params or {})
            )
        elif mode == CaptureMode.RAW_IP:
            self.capture_thread = threading.Thread(
                target=self._capture_raw_ip,
                args=(filter_params or {},)
            )
        elif mode == CaptureMode.UDP:
            self.capture_thread = threading.Thread(
                target=self._capture_udp,
                args=(filter_params or {},)
            )
        elif mode == CaptureMode.TCP:
            self.capture_thread = threading.Thread(
                target=self._capture_tcp,
                args=(filter_params or {},)
            )
        elif mode == CaptureMode.SERIAL:
            self.capture_thread = threading.Thread(
                target=self._capture_serial,
                args=(interface, filter_params or {})
            )
        else:
            self.capture_active = False
            return False
        
        self.capture_thread.daemon = True
        self.capture_thread.start()
        return True
    
    def stop_capture(self) -> Dict[str, Any]:
        """Stop packet capture and return statistics"""
        if not self.capture_active:
            return self.statistics
        
        self.capture_active = False
        
        if self.capture_thread and self.capture_thread.is_alive():
            self.capture_thread.join(timeout=2.0)
        
        if self.statistics["capture_start"]:
            self.statistics["capture_duration"] = time.time() - self.statistics["capture_start"]
        
        return self.statistics
    
    def _process_packet(self, packet_info: PacketInfo):
        """Process captured packet"""
        # Update statistics
        self.statistics["total_packets"] += 1
        self.statistics["bytes_captured"] += packet_info.length
        
        protocol = packet_info.protocol
        if protocol not in self.statistics["protocols"]:
            self.statistics["protocols"][protocol] = 0
        self.statistics["protocols"][protocol] += 1
        
        # Add to queue
        try:
            self.packet_queue.put_nowait(packet_info)
        except queue.Full:
            # Queue is full, remove oldest packet
            try:
                self.packet_queue.get_nowait()
                self.packet_queue.put_nowait(packet_info)
            except queue.Empty:
                pass
        
        # Call registered callbacks
        for callback in self.packet_callbacks:
            try:
                callback(packet_info)
            except Exception as e:
                print(f"Callback error: {e}")
    
    def _capture_raw_ethernet(self, interface: str, filter_params: Dict[str, Any]):
        """Capture raw Ethernet frames"""
        try:
            # Create raw socket (requires root privileges)
            sock = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.ntohs(0x0003))
            if interface:
                sock.bind((interface, 0))
            
            while self.capture_active:
                try:
                    data, addr = sock.recvfrom(65536)
                    
                    packet_info = PacketInfo(
                        timestamp=time.time(),
                        capture_mode=CaptureMode.RAW_ETHERNET,
                        source=addr[0] if addr else "unknown",
                        destination="",  # Will be filled from packet data
                        protocol="ethernet",
                        length=len(data),
                        data=data,
                        metadata={"interface": interface}
                    )
                    
                    # Decode Ethernet frame
                    try:
                        decoded = PacketDecoder.decode_ethernet(data)
                        packet_info.metadata["decoded"] = decoded
                        if "dst_mac" in decoded:
                            packet_info.destination = decoded["dst_mac"]
                        if "src_mac" in decoded:
                            packet_info.source = decoded["src_mac"]
                    except Exception as e:
                        packet_info.metadata["decode_error"] = str(e)
                    
                    self._process_packet(packet_info)
                    
                except socket.timeout:
                    continue
                except Exception as e:
                    if self.capture_active:
                        print(f"Ethernet capture error: {e}")
                    break
                    
        except Exception as e:
            print(f"Failed to create raw Ethernet socket: {e}")
        finally:
            try:
                sock.close()
            except:
                pass
    
    def _capture_raw_ip(self, filter_params: Dict[str, Any]):
        """Capture raw IP packets"""
        try:
            # Create raw IP socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_IP)
            sock.bind(('', 0))
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
            
            while self.capture_active:
                try:
                    data, addr = sock.recvfrom(65536)
                    
                    packet_info = PacketInfo(
                        timestamp=time.time(),
                        capture_mode=CaptureMode.RAW_IP,
                        source=addr[0],
                        destination="",  # Will be filled from IP header
                        protocol="ip",
                        length=len(data),
                        data=data
                    )
                    
                    # Decode IP packet
                    try:
                        decoded = PacketDecoder.decode_ipv4(data)
                        packet_info.metadata = {"decoded": decoded}
                        if "dst_ip" in decoded:
                            packet_info.destination = decoded["dst_ip"]
                    except Exception as e:
                        packet_info.metadata = {"decode_error": str(e)}
                    
                    self._process_packet(packet_info)
                    
                except socket.timeout:
                    continue
                except Exception as e:
                    if self.capture_active:
                        print(f"IP capture error: {e}")
                    break
                    
        except Exception as e:
            print(f"Failed to create raw IP socket: {e}")
        finally:
            try:
                sock.close()
            except:
                pass
    
    def _capture_udp(self, filter_params: Dict[str, Any]):
        """Capture UDP packets"""
        port = filter_params.get("port", 0)
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.bind(('', port))
            sock.settimeout(1.0)
            
            while self.capture_active:
                try:
                    data, addr = sock.recvfrom(65536)
                    
                    packet_info = PacketInfo(
                        timestamp=time.time(),
                        capture_mode=CaptureMode.UDP,
                        source=f"{addr[0]}:{addr[1]}",
                        destination=f"local:{port}",
                        protocol="udp",
                        length=len(data),
                        data=data,
                        metadata={"src_addr": addr[0], "src_port": addr[1], "dst_port": port}
                    )
                    
                    self._process_packet(packet_info)
                    
                except socket.timeout:
                    continue
                except Exception as e:
                    if self.capture_active:
                        print(f"UDP capture error: {e}")
                    break
                    
        except Exception as e:
            print(f"Failed to create UDP socket: {e}")
        finally:
            try:
                sock.close()
            except:
                pass
    
    def _capture_tcp(self, filter_params: Dict[str, Any]):
        """Capture TCP connections"""
        port = filter_params.get("port", 8080)
        
        try:
            server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_sock.bind(('', port))
            server_sock.listen(5)
            server_sock.settimeout(1.0)
            
            while self.capture_active:
                try:
                    client_sock, addr = server_sock.accept()
                    client_sock.settimeout(1.0)
                    
                    # Handle connection in separate thread
                    threading.Thread(
                        target=self._handle_tcp_connection,
                        args=(client_sock, addr),
                        daemon=True
                    ).start()
                    
                except socket.timeout:
                    continue
                except Exception as e:
                    if self.capture_active:
                        print(f"TCP capture error: {e}")
                    break
                    
        except Exception as e:
            print(f"Failed to create TCP server socket: {e}")
        finally:
            try:
                server_sock.close()
            except:
                pass
    
    def _handle_tcp_connection(self, sock: socket.socket, addr):
        """Handle TCP connection"""
        try:
            while self.capture_active:
                data = sock.recv(4096)
                if not data:
                    break
                
                packet_info = PacketInfo(
                    timestamp=time.time(),
                    capture_mode=CaptureMode.TCP,
                    source=f"{addr[0]}:{addr[1]}",
                    destination="local",
                    protocol="tcp",
                    length=len(data),
                    data=data,
                    metadata={"src_addr": addr[0], "src_port": addr[1]}
                )
                
                self._process_packet(packet_info)
                
        except socket.timeout:
            pass
        except Exception as e:
            print(f"TCP connection error: {e}")
        finally:
            try:
                sock.close()
            except:
                pass
    
    def _capture_serial(self, device: str, filter_params: Dict[str, Any]):
        """Capture serial data"""
        try:
            import serial
            
            baud_rate = filter_params.get("baud_rate", 9600)
            timeout = filter_params.get("timeout", 1.0)
            
            ser = serial.Serial(device, baud_rate, timeout=timeout)
            
            while self.capture_active:
                try:
                    data = ser.read(1024)  # Read up to 1KB
                    if data:
                        packet_info = PacketInfo(
                            timestamp=time.time(),
                            capture_mode=CaptureMode.SERIAL,
                            source=device,
                            destination="local",
                            protocol="serial",
                            length=len(data),
                            data=data,
                            metadata={"device": device, "baud_rate": baud_rate}
                        )
                        
                        self._process_packet(packet_info)
                        
                except Exception as e:
                    if self.capture_active:
                        print(f"Serial capture error: {e}")
                    break
                    
        except ImportError:
            print("pyserial not available for serial capture")
        except Exception as e:
            print(f"Failed to open serial device {device}: {e}")
        finally:
            try:
                ser.close()
            except:
                pass
    
    def get_packets(self, count: int = None) -> List[PacketInfo]:
        """Get captured packets from queue"""
        packets = []
        retrieved = 0
        
        while (count is None or retrieved < count):
            try:
                packet = self.packet_queue.get_nowait()
                packets.append(packet)
                retrieved += 1
            except queue.Empty:
                break
        
        return packets
    
    def save_capture(self, filename: str, format_type: str = "json") -> bool:
        """Save captured packets to file"""
        try:
            packets = self.get_packets()  # Get all packets
            
            if format_type.lower() == "json":
                export_data = {
                    "metadata": {
                        "export_timestamp": datetime.now().isoformat(),
                        "total_packets": len(packets),
                        "statistics": self.statistics
                    },
                    "packets": []
                }
                
                for packet in packets:
                    packet_data = {
                        "timestamp": packet.timestamp,
                        "capture_mode": packet.capture_mode.value,
                        "source": packet.source,
                        "destination": packet.destination,
                        "protocol": packet.protocol,
                        "length": packet.length,
                        "data": packet.data.hex(),
                        "metadata": packet.metadata
                    }
                    export_data["packets"].append(packet_data)
                
                with open(filename, 'w') as f:
                    json.dump(export_data, f, indent=2, default=str)
                    
            elif format_type.lower() == "pcap":
                # Basic PCAP format (simplified)
                with open(filename, 'wb') as f:
                    # PCAP header
                    pcap_header = struct.pack('<LHHLLLL', 
                                            0xa1b2c3d4,  # magic number
                                            2, 4,        # version major, minor
                                            0,           # thiszone
                                            0,           # sigfigs
                                            65535,       # snaplen
                                            1)           # network (Ethernet)
                    f.write(pcap_header)
                    
                    # Write packets
                    for packet in packets:
                        ts_sec = int(packet.timestamp)
                        ts_usec = int((packet.timestamp - ts_sec) * 1000000)
                        
                        packet_header = struct.pack('<LLLL',
                                                  ts_sec, ts_usec,
                                                  len(packet.data),
                                                  len(packet.data))
                        f.write(packet_header)
                        f.write(packet.data)
            else:
                return False
            
            # Re-queue packets
            for packet in packets:
                try:
                    self.packet_queue.put_nowait(packet)
                except queue.Full:
                    break
            
            return True
            
        except Exception as e:
            print(f"Save capture failed: {e}")
            return False

# Example usage and testing
if __name__ == "__main__":
    def packet_handler(packet: PacketInfo):
        """Example packet handler"""
        print(f"Packet: {packet.protocol} from {packet.source} to {packet.destination} ({packet.length} bytes)")
        if "decoded" in packet.metadata:
            decoded = packet.metadata["decoded"]
            if "src_ip" in decoded:
                print(f"  IP: {decoded['src_ip']} -> {decoded['dst_ip']}")
    
    # Create sniffer
    sniffer = PacketSniffer()
    sniffer.add_packet_callback(packet_handler)
    
    print("Starting UDP packet capture on port 12345...")
    print("Send UDP packets to localhost:12345 to test")
    
    # Start UDP capture
    if sniffer.start_capture(CaptureMode.UDP, filter_params={"port": 12345}):
        print("Capture started. Press Ctrl+C to stop...")
        
        try:
            # Let it run for a while
            time.sleep(30)
        except KeyboardInterrupt:
            print("\nStopping capture...")
        
        # Stop capture
        stats = sniffer.stop_capture()
        print(f"\nCapture Statistics:")
        print(f"- Total packets: {stats['total_packets']}")
        print(f"- Bytes captured: {stats['bytes_captured']}")
        print(f"- Duration: {stats['capture_duration']:.2f} seconds")
        print(f"- Protocols: {stats['protocols']}")
        
        # Save capture
        if stats['total_packets'] > 0:
            if sniffer.save_capture("captured_packets.json"):
                print("Capture saved to captured_packets.json")
    else:
        print("Failed to start capture")