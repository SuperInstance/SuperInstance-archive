#!/usr/bin/env python3
"""
LoRaWAN Gateway Integration Template
Provides integration with LoRaWAN networks and gateways
"""

import json
import struct
import logging
import asyncio
import socket
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from enum import Enum
import base64
import hashlib
import hmac

class LoRaWANMessageType(Enum):
    JOIN_REQUEST = 0x00
    JOIN_ACCEPT = 0x01
    UNCONFIRMED_DATA_UP = 0x02
    UNCONFIRMED_DATA_DOWN = 0x03
    CONFIRMED_DATA_UP = 0x04
    CONFIRMED_DATA_DOWN = 0x05
    REJOIN_REQUEST = 0x06
    PROPRIETARY = 0x07

class LoRaWANGateway:
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize LoRaWAN Gateway
        
        Required config:
        - gateway_id: Gateway EUI (8 bytes hex string)
        - server_address: Network server address
        - server_port: Network server port (usually 1700)
        - frequency_plan: Frequency plan (EU868, US915, etc.)
        - network_session_key: Network session key (16 bytes hex)
        - app_session_key: Application session key (16 bytes hex)
        - device_addresses: List of device addresses to handle
        """
        self.config = config
        self.socket = None
        self.running = False
        self.logger = logging.getLogger(__name__)
        self.message_handlers = {}
        self.device_counters = {}  # Track frame counters per device
        
        # Protocol constants
        self.PROTOCOL_VERSION = 2
        self.PUSH_DATA = 0x00
        self.PUSH_ACK = 0x01
        self.PULL_DATA = 0x02
        self.PULL_RESP = 0x03
        self.PULL_ACK = 0x04
        self.TX_ACK = 0x05
        
    async def start(self) -> bool:
        """Start the LoRaWAN gateway"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.setblocking(False)
            
            self.running = True
            self.logger.info("LoRaWAN Gateway started")
            
            # Start background tasks
            asyncio.create_task(self._send_pull_data())
            asyncio.create_task(self._handle_incoming_packets())
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start LoRaWAN gateway: {e}")
            return False
            
    async def stop(self):
        """Stop the LoRaWAN gateway"""
        self.running = False
        if self.socket:
            self.socket.close()
        self.logger.info("LoRaWAN Gateway stopped")
        
    async def _send_pull_data(self):
        """Send periodic PULL_DATA packets to maintain connection"""
        while self.running:
            try:
                packet = self._create_pull_data_packet()
                await self._send_packet(packet)
                await asyncio.sleep(30)  # Send every 30 seconds
                
            except Exception as e:
                self.logger.error(f"PULL_DATA send error: {e}")
                await asyncio.sleep(5)
                
    def _create_pull_data_packet(self) -> bytes:
        """Create PULL_DATA packet"""
        gateway_eui = bytes.fromhex(self.config['gateway_id'])
        token = struct.pack('>H', int(datetime.now().timestamp()) & 0xFFFF)
        
        packet = struct.pack('BBB', 
                           self.PROTOCOL_VERSION,
                           token[0], token[1])
        packet += struct.pack('B', self.PULL_DATA)
        packet += gateway_eui
        
        return packet
        
    async def _send_packet(self, packet: bytes):
        """Send packet to network server"""
        loop = asyncio.get_event_loop()
        await loop.sock_sendto(
            self.socket, 
            packet, 
            (self.config['server_address'], self.config['server_port'])
        )
        
    async def _handle_incoming_packets(self):
        """Handle incoming packets from network server"""
        while self.running:
            try:
                loop = asyncio.get_event_loop()
                data, addr = await loop.sock_recvfrom(self.socket, 1024)
                
                await self._process_packet(data, addr)
                
            except Exception as e:
                if self.running:  # Only log if we're still running
                    self.logger.error(f"Packet handling error: {e}")
                await asyncio.sleep(0.1)
                
    async def _process_packet(self, data: bytes, addr: Tuple[str, int]):
        """Process incoming packet from network server"""
        if len(data) < 4:
            return
            
        version = data[0]
        token = struct.unpack('>H', data[1:3])[0]
        packet_type = data[3]
        
        if packet_type == self.PULL_RESP:
            await self._handle_pull_response(data[4:], token)
        elif packet_type == self.PUSH_ACK:
            self.logger.debug(f"PUSH_ACK received with token {token}")
        elif packet_type == self.TX_ACK:
            await self._handle_tx_ack(data[4:], token)
            
    async def _handle_pull_response(self, payload: bytes, token: int):
        """Handle PULL_RESP (downlink) from network server"""
        try:
            if not payload:
                return
                
            json_data = json.loads(payload.decode('utf-8'))
            
            if 'txpk' in json_data:
                txpk = json_data['txpk']
                await self._process_downlink(txpk)
                
        except Exception as e:
            self.logger.error(f"PULL_RESP handling error: {e}")
            
    async def _process_downlink(self, txpk: Dict[str, Any]):
        """Process downlink transmission request"""
        try:
            # Decode the payload
            rf_data = base64.b64decode(txpk['data'])
            
            # Extract LoRaWAN frame
            mhdr = rf_data[0]
            message_type = (mhdr >> 5) & 0x07
            
            if len(rf_data) < 4:
                return
                
            # Extract device address (4 bytes, little endian)
            dev_addr = struct.unpack('<I', rf_data[1:5])[0]
            
            self.logger.info(f"Downlink for device {dev_addr:08x}: {txpk}")
            
            # Here you would typically forward to the actual LoRa radio
            # For this template, we'll just log the transmission
            await self._simulate_radio_transmission(txpk, rf_data)
            
        except Exception as e:
            self.logger.error(f"Downlink processing error: {e}")
            
    async def _simulate_radio_transmission(self, txpk: Dict[str, Any], rf_data: bytes):
        """Simulate radio transmission (replace with actual radio interface)"""
        self.logger.info(f"Transmitting on freq {txpk.get('freq', 0)} MHz, "
                        f"SF{txpk.get('datr', 'unknown')}, "
                        f"power {txpk.get('powe', 14)} dBm")
        
        # In a real implementation, you would:
        # 1. Configure radio parameters (frequency, spreading factor, power)
        # 2. Transmit the RF data
        # 3. Handle transmission timing requirements
        
    async def receive_uplink(self, rf_data: bytes, metadata: Dict[str, Any]) -> bool:
        """
        Process received uplink data from LoRa radio
        
        Args:
            rf_data: Raw LoRaWAN frame data
            metadata: Reception metadata (RSSI, SNR, timestamp, etc.)
        """
        try:
            # Parse LoRaWAN frame
            frame_info = await self._parse_lorawan_frame(rf_data)
            
            if not frame_info:
                return False
                
            # Create PUSH_DATA packet
            packet_data = await self._create_push_data(rf_data, metadata, frame_info)
            
            # Send to network server
            await self._send_packet(packet_data)
            
            # Handle application data if it's our device
            if frame_info['dev_addr'] in self.config.get('device_addresses', []):
                await self._handle_application_data(frame_info, metadata)
                
            return True
            
        except Exception as e:
            self.logger.error(f"Uplink processing error: {e}")
            return False
            
    async def _parse_lorawan_frame(self, rf_data: bytes) -> Optional[Dict[str, Any]]:
        """Parse LoRaWAN frame structure"""
        if len(rf_data) < 12:  # Minimum frame size
            return None
            
        try:
            # MHDR (1 byte)
            mhdr = rf_data[0]
            mtype = (mhdr >> 5) & 0x07
            major = mhdr & 0x03
            
            # DevAddr (4 bytes, little endian)
            dev_addr = struct.unpack('<I', rf_data[1:5])[0]
            
            # FCtrl (1 byte)
            fctrl = rf_data[5]
            adr = (fctrl >> 7) & 0x01
            adr_ack_req = (fctrl >> 6) & 0x01
            ack = (fctrl >> 5) & 0x01
            fpending = (fctrl >> 4) & 0x01
            fopts_len = fctrl & 0x0F
            
            # FCnt (2 bytes, little endian)
            fcnt = struct.unpack('<H', rf_data[6:8])[0]
            
            # FOpts (variable length)
            fopts_end = 8 + fopts_len
            fopts = rf_data[8:fopts_end] if fopts_len > 0 else b''
            
            # FPort (1 byte, optional)
            fport = None
            payload_start = fopts_end
            
            if len(rf_data) > fopts_end + 4:  # Has payload
                fport = rf_data[fopts_end]
                payload_start = fopts_end + 1
                
            # Payload (variable length)
            mic_start = len(rf_data) - 4
            payload = rf_data[payload_start:mic_start] if payload_start < mic_start else b''
            
            # MIC (4 bytes)
            mic = rf_data[mic_start:]
            
            return {
                'mtype': mtype,
                'major': major,
                'dev_addr': dev_addr,
                'fctrl': fctrl,
                'fcnt': fcnt,
                'fopts': fopts,
                'fport': fport,
                'payload': payload,
                'mic': mic,
                'raw_data': rf_data
            }
            
        except Exception as e:
            self.logger.error(f"Frame parsing error: {e}")
            return None
            
    async def _create_push_data(self, rf_data: bytes, metadata: Dict[str, Any], 
                               frame_info: Dict[str, Any]) -> bytes:
        """Create PUSH_DATA packet for network server"""
        # Packet header
        gateway_eui = bytes.fromhex(self.config['gateway_id'])
        token = struct.pack('>H', int(datetime.now().timestamp()) & 0xFFFF)
        
        header = struct.pack('BBB', 
                           self.PROTOCOL_VERSION,
                           token[0], token[1])
        header += struct.pack('B', self.PUSH_DATA)
        header += gateway_eui
        
        # JSON payload
        rxpk = {
            "time": metadata.get('time', datetime.utcnow().isoformat() + 'Z'),
            "tmst": metadata.get('timestamp', int(datetime.now().timestamp() * 1000000)),
            "freq": metadata.get('frequency', 868.1),
            "chan": metadata.get('channel', 0),
            "rfch": metadata.get('rf_chain', 0),
            "stat": 1,  # CRC OK
            "modu": "LORA",
            "datr": metadata.get('datarate', "SF7BW125"),
            "codr": metadata.get('coderate', "4/5"),
            "rssi": metadata.get('rssi', -80),
            "lsnr": metadata.get('snr', 8.5),
            "size": len(rf_data),
            "data": base64.b64encode(rf_data).decode('ascii')
        }
        
        json_payload = {
            "rxpk": [rxpk]
        }
        
        json_data = json.dumps(json_payload).encode('utf-8')
        
        return header + json_data
        
    async def _handle_application_data(self, frame_info: Dict[str, Any], 
                                     metadata: Dict[str, Any]):
        """Handle application-specific data processing"""
        try:
            dev_addr = frame_info['dev_addr']
            payload = frame_info['payload']
            fport = frame_info['fport']
            
            # Decrypt payload if we have the AppSKey
            if payload and fport and fport > 0:
                decrypted_payload = await self._decrypt_payload(
                    payload, 
                    frame_info, 
                    self.config.get('app_session_key')
                )
                
                if decrypted_payload:
                    await self._process_application_payload(
                        dev_addr, 
                        fport, 
                        decrypted_payload, 
                        metadata
                    )
                    
        except Exception as e:
            self.logger.error(f"Application data handling error: {e}")
            
    async def _decrypt_payload(self, payload: bytes, frame_info: Dict[str, Any], 
                              app_skey: str) -> Optional[bytes]:
        """Decrypt LoRaWAN application payload"""
        if not app_skey:
            return None
            
        try:
            key = bytes.fromhex(app_skey)
            
            # Create encryption block
            dev_addr = frame_info['dev_addr']
            fcnt = frame_info['fcnt']
            
            # S = 0x01 for uplink
            s_block = struct.pack('<BIBIH6x', 
                                0x01, 0x00, 0x00, 0x00, 
                                dev_addr, fcnt)
            
            # AES encrypt the S block to create keystream
            from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
            from cryptography.hazmat.backends import default_backend
            
            cipher = Cipher(algorithms.AES(key), modes.ECB(), backend=default_backend())
            encryptor = cipher.encryptor()
            
            decrypted = bytearray()
            
            for i in range(0, len(payload), 16):
                block = s_block[:15] + struct.pack('B', (i // 16) + 1)
                keystream = encryptor.update(block)
                
                chunk = payload[i:i+16]
                for j, byte in enumerate(chunk):
                    decrypted.append(byte ^ keystream[j])
                    
            encryptor.finalize()
            
            return bytes(decrypted)
            
        except Exception as e:
            self.logger.error(f"Payload decryption error: {e}")
            return None
            
    async def _process_application_payload(self, dev_addr: int, fport: int, 
                                         payload: bytes, metadata: Dict[str, Any]):
        """Process decrypted application payload"""
        try:
            self.logger.info(f"Application data from {dev_addr:08x} on port {fport}: "
                           f"{payload.hex()}")
            
            # Route based on FPort
            if fport == 1:  # Sensor data
                await self._handle_sensor_data(dev_addr, payload, metadata)
            elif fport == 2:  # Status data
                await self._handle_status_data(dev_addr, payload, metadata)
            elif fport == 10:  # Configuration
                await self._handle_config_data(dev_addr, payload, metadata)
                
        except Exception as e:
            self.logger.error(f"Application payload processing error: {e}")
            
    async def _handle_sensor_data(self, dev_addr: int, payload: bytes, 
                                metadata: Dict[str, Any]):
        """Handle sensor data payload"""
        if len(payload) >= 4:
            # Example: Temperature and humidity (2 bytes each)
            temp_raw = struct.unpack('>h', payload[:2])[0]
            humidity_raw = struct.unpack('>H', payload[2:4])[0]
            
            temperature = temp_raw / 100.0  # Convert to Celsius
            humidity = humidity_raw / 100.0  # Convert to %
            
            sensor_data = {
                "device_address": f"{dev_addr:08x}",
                "temperature": temperature,
                "humidity": humidity,
                "rssi": metadata.get('rssi'),
                "snr": metadata.get('snr'),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            self.logger.info(f"Sensor data: {sensor_data}")
            
            # Forward to application handler if registered
            if 'sensor_data' in self.message_handlers:
                await self.message_handlers['sensor_data'](sensor_data)
                
    async def _handle_status_data(self, dev_addr: int, payload: bytes, 
                                metadata: Dict[str, Any]):
        """Handle device status payload"""
        if len(payload) >= 3:
            battery = payload[0]  # Battery level %
            signal_quality = payload[1]  # Signal quality
            error_flags = payload[2]  # Error flags
            
            status_data = {
                "device_address": f"{dev_addr:08x}",
                "battery_level": battery,
                "signal_quality": signal_quality,
                "error_flags": error_flags,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            self.logger.info(f"Status data: {status_data}")
            
            if 'status_data' in self.message_handlers:
                await self.message_handlers['status_data'](status_data)
                
    async def _handle_config_data(self, dev_addr: int, payload: bytes, 
                                metadata: Dict[str, Any]):
        """Handle configuration data payload"""
        self.logger.info(f"Configuration data from {dev_addr:08x}: {payload.hex()}")
        
        if 'config_data' in self.message_handlers:
            config_data = {
                "device_address": f"{dev_addr:08x}",
                "config_payload": payload.hex(),
                "timestamp": datetime.utcnow().isoformat()
            }
            await self.message_handlers['config_data'](config_data)
            
    async def _handle_tx_ack(self, payload: bytes, token: int):
        """Handle TX_ACK from network server"""
        try:
            if payload:
                ack_data = json.loads(payload.decode('utf-8'))
                error = ack_data.get('txpk_ack', {}).get('error')
                
                if error:
                    self.logger.error(f"TX failed with error: {error}")
                else:
                    self.logger.debug(f"TX ACK received for token {token}")
                    
        except Exception as e:
            self.logger.error(f"TX_ACK handling error: {e}")
            
    def register_handler(self, message_type: str, handler):
        """Register a message handler"""
        self.message_handlers[message_type] = handler

# Example usage
async def main():
    config = {
        "gateway_id": "AA555A0000000000",  # 8-byte gateway EUI
        "server_address": "router.eu.thethings.network",
        "server_port": 1700,
        "frequency_plan": "EU868",
        "network_session_key": "00000000000000000000000000000000",
        "app_session_key": "00000000000000000000000000000000",
        "device_addresses": [0x12345678]  # Device addresses to handle locally
    }
    
    gateway = LoRaWANGateway(config)
    
    # Register handlers
    async def sensor_handler(data):
        print(f"Sensor data received: {data}")
        
    async def status_handler(data):
        print(f"Status data received: {data}")
        
    gateway.register_handler('sensor_data', sensor_handler)
    gateway.register_handler('status_data', status_handler)
    
    if await gateway.start():
        # Simulate receiving uplink data
        sample_frame = bytes.fromhex("40781234560020000001020304")  # Sample frame
        metadata = {
            "frequency": 868.1,
            "datarate": "SF7BW125",
            "rssi": -85,
            "snr": 7.5,
            "timestamp": int(datetime.now().timestamp() * 1000000)
        }
        
        await gateway.receive_uplink(sample_frame, metadata)
        
        # Keep running
        await asyncio.sleep(60)
        
        await gateway.stop()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())