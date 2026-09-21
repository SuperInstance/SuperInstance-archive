"""
Bluetooth Headset Support for Voice Excellence System

This module provides comprehensive Bluetooth headset integration for
marine and industrial environments with advanced audio processing,
noise handling, and multi-device management.

Author: Claude
Date: 2025-08-24
"""

import json
import time
import asyncio
import threading
from typing import Dict, List, Optional, Any, Callable, Tuple
from enum import Enum
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import logging
import sqlite3
import struct
import wave
from pathlib import Path
import subprocess
import re

class BluetoothProtocol(Enum):
    """Bluetooth audio protocols"""
    A2DP = "a2dp"           # Advanced Audio Distribution Profile
    HSP = "hsp"             # Headset Profile
    HFP = "hfp"             # Hands-Free Profile
    AVRCP = "avrcp"         # Audio/Video Remote Control Profile
    HID = "hid"             # Human Interface Device Profile

class AudioCodec(Enum):
    """Supported audio codecs"""
    SBC = "sbc"             # Subband Coding (mandatory)
    AAC = "aac"             # Advanced Audio Coding
    APTX = "aptx"           # aptX codec
    APTX_HD = "aptx_hd"     # aptX HD codec
    LDAC = "ldac"           # Sony LDAC
    LC3 = "lc3"             # Low Complexity Communication Codec

class DeviceType(Enum):
    """Types of Bluetooth devices"""
    HEADSET = "headset"
    EARBUDS = "earbuds"
    HEADPHONES = "headphones"
    HEARING_AID = "hearing_aid"
    BONE_CONDUCTION = "bone_conduction"
    INDUSTRIAL_HEADSET = "industrial_headset"
    MARINE_HEADSET = "marine_headset"
    SAFETY_HEADSET = "safety_headset"

class ConnectionState(Enum):
    """Bluetooth connection states"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    PAIRED = "paired"
    ACTIVE = "active"
    ERROR = "error"

@dataclass
class BluetoothDevice:
    """Bluetooth device information"""
    device_id: str
    name: str
    mac_address: str
    device_type: DeviceType
    supported_protocols: List[BluetoothProtocol]
    supported_codecs: List[AudioCodec]
    battery_level: Optional[int]
    signal_strength: Optional[int]  # RSSI in dBm
    connection_state: ConnectionState
    last_connected: Optional[datetime]
    audio_latency_ms: float
    noise_cancellation: bool
    microphone_quality: str
    speaker_quality: str
    environmental_rating: str  # IP rating
    manufacturer: str
    model: str
    firmware_version: str

@dataclass
class AudioSession:
    """Audio session with Bluetooth device"""
    session_id: str
    device_id: str
    user_id: str
    started_at: datetime
    ended_at: Optional[datetime]
    protocol_used: BluetoothProtocol
    codec_used: AudioCodec
    sample_rate: int
    bit_depth: int
    channels: int
    total_audio_time: float
    audio_quality_score: float
    connection_drops: int
    latency_measurements: List[float]
    noise_level_db: float
    voice_clarity_score: float

@dataclass
class AudioProfile:
    """Audio profile for different environments"""
    profile_id: str
    name: str
    description: str
    environment_type: str
    noise_suppression_level: float
    microphone_gain: float
    speaker_volume: float
    equalizer_settings: Dict[str, float]
    voice_enhancement: bool
    echo_cancellation: bool
    wind_noise_reduction: bool
    codec_preference: List[AudioCodec]

class BluetoothHeadsetManager:
    """
    Comprehensive Bluetooth headset management system for voice
    excellence in marine and industrial environments.
    """
    
    def __init__(self, db_path: str = "bluetooth_headsets.db"):
        """
        Initialize Bluetooth headset manager.
        
        Args:
            db_path: Path to the Bluetooth headsets database
        """
        self.db_path = db_path
        self.paired_devices: Dict[str, BluetoothDevice] = {}
        self.active_sessions: Dict[str, AudioSession] = {}
        self.audio_profiles: Dict[str, AudioProfile] = {}
        self.connection_callbacks: Dict[str, List[Callable]] = {}
        self.audio_processors: Dict[str, Any] = {}
        self.device_monitors: Dict[str, threading.Thread] = {}
        self.lock = threading.Lock()
        self.logger = logging.getLogger(__name__)
        
        # Initialize database
        self._init_database()
        
        # Load audio profiles
        self._load_default_audio_profiles()
        
        # Initialize Bluetooth subsystem
        self._init_bluetooth_subsystem()
        
        # Start device discovery
        self._start_device_discovery()
        
        self.logger.info("Bluetooth Headset Manager initialized")
    
    def _init_database(self):
        """Initialize the Bluetooth database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Devices table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bluetooth_devices (
                device_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                mac_address TEXT UNIQUE NOT NULL,
                device_type TEXT NOT NULL,
                supported_protocols TEXT NOT NULL,
                supported_codecs TEXT NOT NULL,
                manufacturer TEXT,
                model TEXT,
                firmware_version TEXT,
                environmental_rating TEXT,
                connection_state TEXT NOT NULL DEFAULT 'disconnected',
                last_connected TEXT,
                battery_level INTEGER,
                signal_strength INTEGER,
                audio_latency_ms REAL,
                noise_cancellation BOOLEAN DEFAULT FALSE,
                microphone_quality TEXT DEFAULT 'standard',
                speaker_quality TEXT DEFAULT 'standard',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Audio sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audio_sessions (
                session_id TEXT PRIMARY KEY,
                device_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                started_at TEXT NOT NULL,
                ended_at TEXT,
                protocol_used TEXT NOT NULL,
                codec_used TEXT NOT NULL,
                sample_rate INTEGER NOT NULL,
                bit_depth INTEGER NOT NULL,
                channels INTEGER NOT NULL,
                total_audio_time REAL DEFAULT 0.0,
                audio_quality_score REAL DEFAULT 0.0,
                connection_drops INTEGER DEFAULT 0,
                latency_measurements TEXT,
                noise_level_db REAL,
                voice_clarity_score REAL,
                FOREIGN KEY (device_id) REFERENCES bluetooth_devices (device_id)
            )
        """)
        
        # Audio profiles table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audio_profiles (
                profile_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                environment_type TEXT NOT NULL,
                noise_suppression_level REAL NOT NULL,
                microphone_gain REAL NOT NULL,
                speaker_volume REAL NOT NULL,
                equalizer_settings TEXT,
                voice_enhancement BOOLEAN DEFAULT TRUE,
                echo_cancellation BOOLEAN DEFAULT TRUE,
                wind_noise_reduction BOOLEAN DEFAULT FALSE,
                codec_preference TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Connection events table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS connection_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                event_data TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (device_id) REFERENCES bluetooth_devices (device_id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    def _load_default_audio_profiles(self):
        """Load default audio profiles for different environments"""
        default_profiles = [
            AudioProfile(
                profile_id="marine_bridge",
                name="Marine Bridge",
                description="Optimized for ship bridge operations",
                environment_type="marine_bridge",
                noise_suppression_level=0.8,
                microphone_gain=0.7,
                speaker_volume=0.8,
                equalizer_settings={
                    "low": -2.0, "mid_low": 1.0, "mid": 2.0, 
                    "mid_high": 1.5, "high": -1.0
                },
                voice_enhancement=True,
                echo_cancellation=True,
                wind_noise_reduction=True,
                codec_preference=[AudioCodec.APTX, AudioCodec.AAC, AudioCodec.SBC]
            ),
            AudioProfile(
                profile_id="engine_room",
                name="Engine Room",
                description="High noise industrial environment",
                environment_type="engine_room",
                noise_suppression_level=0.95,
                microphone_gain=0.9,
                speaker_volume=0.95,
                equalizer_settings={
                    "low": -5.0, "mid_low": 3.0, "mid": 5.0, 
                    "mid_high": 3.0, "high": -2.0
                },
                voice_enhancement=True,
                echo_cancellation=True,
                wind_noise_reduction=False,
                codec_preference=[AudioCodec.LDAC, AudioCodec.APTX_HD, AudioCodec.APTX]
            ),
            AudioProfile(
                profile_id="deck_operations",
                name="Deck Operations",
                description="Outdoor marine operations with wind",
                environment_type="deck",
                noise_suppression_level=0.75,
                microphone_gain=0.8,
                speaker_volume=0.85,
                equalizer_settings={
                    "low": -1.0, "mid_low": 2.0, "mid": 3.0, 
                    "mid_high": 2.0, "high": 0.0
                },
                voice_enhancement=True,
                echo_cancellation=True,
                wind_noise_reduction=True,
                codec_preference=[AudioCodec.APTX, AudioCodec.AAC, AudioCodec.SBC]
            ),
            AudioProfile(
                profile_id="industrial_manufacturing",
                name="Industrial Manufacturing",
                description="Factory floor with machinery noise",
                environment_type="industrial",
                noise_suppression_level=0.9,
                microphone_gain=0.85,
                speaker_volume=0.9,
                equalizer_settings={
                    "low": -3.0, "mid_low": 4.0, "mid": 4.0, 
                    "mid_high": 2.0, "high": -1.0
                },
                voice_enhancement=True,
                echo_cancellation=True,
                wind_noise_reduction=False,
                codec_preference=[AudioCodec.APTX_HD, AudioCodec.APTX, AudioCodec.AAC]
            ),
            AudioProfile(
                profile_id="quiet_office",
                name="Quiet Office",
                description="Low noise office environment",
                environment_type="office",
                noise_suppression_level=0.3,
                microphone_gain=0.5,
                speaker_volume=0.6,
                equalizer_settings={
                    "low": 0.0, "mid_low": 0.0, "mid": 0.0, 
                    "mid_high": 0.0, "high": 0.0
                },
                voice_enhancement=False,
                echo_cancellation=True,
                wind_noise_reduction=False,
                codec_preference=[AudioCodec.AAC, AudioCodec.SBC]
            )
        ]
        
        for profile in default_profiles:
            self.audio_profiles[profile.profile_id] = profile
            self._save_audio_profile(profile)
    
    def _save_audio_profile(self, profile: AudioProfile):
        """Save audio profile to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO audio_profiles 
            (profile_id, name, description, environment_type, noise_suppression_level,
             microphone_gain, speaker_volume, equalizer_settings, voice_enhancement,
             echo_cancellation, wind_noise_reduction, codec_preference)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            profile.profile_id,
            profile.name,
            profile.description,
            profile.environment_type,
            profile.noise_suppression_level,
            profile.microphone_gain,
            profile.speaker_volume,
            json.dumps(profile.equalizer_settings),
            profile.voice_enhancement,
            profile.echo_cancellation,
            profile.wind_noise_reduction,
            json.dumps([codec.value for codec in profile.codec_preference])
        ))
        
        conn.commit()
        conn.close()
    
    def _init_bluetooth_subsystem(self):
        """Initialize Bluetooth subsystem"""
        try:
            # Check if Bluetooth is available (Linux)
            result = subprocess.run(
                ["bluetoothctl", "--version"], 
                capture_output=True, 
                text=True, 
                timeout=5
            )
            
            if result.returncode == 0:
                self.logger.info("Bluetooth subsystem available")
                
                # Enable Bluetooth adapter
                subprocess.run(["bluetoothctl", "power", "on"], timeout=10)
                subprocess.run(["bluetoothctl", "discoverable", "on"], timeout=10)
                subprocess.run(["bluetoothctl", "pairable", "on"], timeout=10)
                
            else:
                self.logger.warning("Bluetooth subsystem not available")
        
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            self.logger.warning(f"Bluetooth initialization failed: {e}")
    
    def _start_device_discovery(self):
        """Start continuous device discovery"""
        def discovery_loop():
            while True:
                try:
                    self._discover_devices()
                    time.sleep(30)  # Discover every 30 seconds
                except Exception as e:
                    self.logger.error(f"Device discovery error: {e}")
                    time.sleep(60)
        
        discovery_thread = threading.Thread(target=discovery_loop, daemon=True)
        discovery_thread.start()
    
    def _discover_devices(self):
        """Discover available Bluetooth devices"""
        try:
            # Check if bluetoothctl is available
            check_result = subprocess.run(
                ["which", "bluetoothctl"],
                capture_output=True,
                text=True
            )
            
            if check_result.returncode != 0:
                self.logger.warning("bluetoothctl not available, using mock devices")
                # Add mock device for testing
                mock_device = BluetoothDevice(
                    mac_address="00:11:22:33:44:55",
                    name="Mock Bluetooth Headset",
                    device_class="Audio/Video",
                    is_paired=False,
                    is_connected=False,
                    signal_strength=-50,
                    battery_level=85,
                    supported_protocols=[BluetoothProtocol.A2DP, BluetoothProtocol.HFP]
                )
                self.discovered_devices["00:11:22:33:44:55"] = mock_device
                return
            
            # Use bluetoothctl to scan for devices
            scan_process = subprocess.Popen(
                ["bluetoothctl", "scan", "on"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Let it scan for 10 seconds
            time.sleep(10)
            scan_process.terminate()
            
            # Get list of discovered devices
            result = subprocess.run(
                ["bluetoothctl", "devices"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                self._parse_discovered_devices(result.stdout)
        
        except Exception as e:
            self.logger.error(f"Device discovery failed: {e}")
    
    def _parse_discovered_devices(self, devices_output: str):
        """Parse bluetoothctl devices output"""
        device_pattern = r"Device\s+([A-F0-9:]+)\s+(.+)"
        
        for line in devices_output.split('\n'):
            match = re.match(device_pattern, line)
            if match:
                mac_address = match.group(1)
                device_name = match.group(2).strip()
                
                # Check if it's an audio device
                if self._is_audio_device(device_name):
                    device_id = f"bt_{mac_address.replace(':', '')}"
                    
                    if device_id not in self.paired_devices:
                        # Get more device info
                        device_info = self._get_device_info(mac_address)
                        
                        if device_info:
                            device = self._create_bluetooth_device(
                                device_id, device_name, mac_address, device_info
                            )
                            self.paired_devices[device_id] = device
                            self._save_device_to_db(device)
                            
                            self.logger.info(f"Discovered audio device: {device_name}")
    
    def _is_audio_device(self, device_name: str) -> bool:
        """Check if device is likely an audio device"""
        audio_keywords = [
            "headset", "headphone", "earbuds", "airpods", "speaker",
            "sennheiser", "bose", "sony", "jabra", "plantronics",
            "beats", "audio", "microphone", "bluetooth"
        ]
        
        device_name_lower = device_name.lower()
        return any(keyword in device_name_lower for keyword in audio_keywords)
    
    def _get_device_info(self, mac_address: str) -> Optional[Dict[str, Any]]:
        """Get detailed device information"""
        try:
            result = subprocess.run(
                ["bluetoothctl", "info", mac_address],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                return self._parse_device_info(result.stdout)
        
        except Exception as e:
            self.logger.error(f"Failed to get device info for {mac_address}: {e}")
        
        return None
    
    def _parse_device_info(self, info_output: str) -> Dict[str, Any]:
        """Parse bluetoothctl info output"""
        device_info = {
            "connected": False,
            "paired": False,
            "trusted": False,
            "rssi": None,
            "uuids": [],
            "manufacturer": "Unknown",
            "model": "Unknown"
        }
        
        for line in info_output.split('\n'):
            line = line.strip()
            
            if line.startswith("Connected:"):
                device_info["connected"] = "yes" in line.lower()
            elif line.startswith("Paired:"):
                device_info["paired"] = "yes" in line.lower()
            elif line.startswith("Trusted:"):
                device_info["trusted"] = "yes" in line.lower()
            elif line.startswith("RSSI:"):
                try:
                    device_info["rssi"] = int(line.split(":")[1].strip())
                except:
                    pass
            elif line.startswith("UUID:"):
                uuid_info = line.split(":", 1)[1].strip()
                device_info["uuids"].append(uuid_info)
        
        return device_info
    
    def _create_bluetooth_device(
        self, 
        device_id: str, 
        name: str, 
        mac_address: str, 
        device_info: Dict[str, Any]
    ) -> BluetoothDevice:
        """Create BluetoothDevice from discovered info"""
        
        # Determine device type from name and UUIDs
        device_type = self._determine_device_type(name, device_info.get("uuids", []))
        
        # Determine supported protocols from UUIDs
        supported_protocols = self._determine_protocols(device_info.get("uuids", []))
        
        # Default supported codecs (would be detected from actual device capabilities)
        supported_codecs = [AudioCodec.SBC, AudioCodec.AAC]
        
        # Determine connection state
        connection_state = ConnectionState.CONNECTED if device_info.get("connected", False) else (
            ConnectionState.PAIRED if device_info.get("paired", False) else ConnectionState.DISCONNECTED
        )
        
        return BluetoothDevice(
            device_id=device_id,
            name=name,
            mac_address=mac_address,
            device_type=device_type,
            supported_protocols=supported_protocols,
            supported_codecs=supported_codecs,
            battery_level=None,
            signal_strength=device_info.get("rssi"),
            connection_state=connection_state,
            last_connected=datetime.now() if device_info.get("connected", False) else None,
            audio_latency_ms=50.0,  # Default latency
            noise_cancellation=self._has_noise_cancellation(name),
            microphone_quality=self._determine_mic_quality(name),
            speaker_quality=self._determine_speaker_quality(name),
            environmental_rating=self._determine_environmental_rating(name),
            manufacturer=device_info.get("manufacturer", "Unknown"),
            model=device_info.get("model", "Unknown"),
            firmware_version="Unknown"
        )
    
    def _determine_device_type(self, name: str, uuids: List[str]) -> DeviceType:
        """Determine device type from name and UUIDs"""
        name_lower = name.lower()
        
        if any(keyword in name_lower for keyword in ["industrial", "safety", "hard hat"]):
            return DeviceType.INDUSTRIAL_HEADSET
        elif any(keyword in name_lower for keyword in ["marine", "waterproof", "nautical"]):
            return DeviceType.MARINE_HEADSET
        elif "hearing aid" in name_lower:
            return DeviceType.HEARING_AID
        elif "bone" in name_lower and "conduction" in name_lower:
            return DeviceType.BONE_CONDUCTION
        elif any(keyword in name_lower for keyword in ["earbud", "airpod", "ear"]):
            return DeviceType.EARBUDS
        elif "headphone" in name_lower:
            return DeviceType.HEADPHONES
        else:
            return DeviceType.HEADSET
    
    def _determine_protocols(self, uuids: List[str]) -> List[BluetoothProtocol]:
        """Determine supported protocols from UUIDs"""
        protocols = []
        
        # Standard Bluetooth audio UUIDs
        uuid_protocol_map = {
            "0000110b": BluetoothProtocol.A2DP,  # Audio Sink
            "0000110a": BluetoothProtocol.A2DP,  # Audio Source
            "00001108": BluetoothProtocol.HSP,   # Headset
            "0000111e": BluetoothProtocol.HFP,   # Hands-Free
            "0000110e": BluetoothProtocol.AVRCP, # AV Remote Control
            "00001124": BluetoothProtocol.HID    # Human Interface Device
        }
        
        for uuid_str in uuids:
            for uuid_part, protocol in uuid_protocol_map.items():
                if uuid_part in uuid_str.lower():
                    if protocol not in protocols:
                        protocols.append(protocol)
        
        # Default to basic protocols if none detected
        if not protocols:
            protocols = [BluetoothProtocol.A2DP, BluetoothProtocol.HFP]
        
        return protocols
    
    def _has_noise_cancellation(self, name: str) -> bool:
        """Determine if device has noise cancellation"""
        nc_keywords = ["noise cancel", "anc", "active noise", "noise reduction"]
        return any(keyword in name.lower() for keyword in nc_keywords)
    
    def _determine_mic_quality(self, name: str) -> str:
        """Determine microphone quality level"""
        if any(keyword in name.lower() for keyword in ["studio", "professional", "broadcast"]):
            return "professional"
        elif any(keyword in name.lower() for keyword in ["premium", "high-end", "audiophile"]):
            return "high"
        else:
            return "standard"
    
    def _determine_speaker_quality(self, name: str) -> str:
        """Determine speaker quality level"""
        if any(keyword in name.lower() for keyword in ["studio", "monitor", "reference"]):
            return "professional"
        elif any(keyword in name.lower() for keyword in ["premium", "high-res", "audiophile"]):
            return "high"
        else:
            return "standard"
    
    def _determine_environmental_rating(self, name: str) -> str:
        """Determine environmental protection rating"""
        if any(keyword in name.lower() for keyword in ["waterproof", "marine", "ip67", "ip68"]):
            return "IP67"
        elif any(keyword in name.lower() for keyword in ["water resistant", "splash", "ip54", "ip65"]):
            return "IP54"
        elif any(keyword in name.lower() for keyword in ["industrial", "rugged", "dustproof"]):
            return "IP54"
        else:
            return "None"
    
    async def connect_device(self, device_id: str, audio_profile_id: str = "marine_bridge") -> bool:
        """
        Connect to a Bluetooth device.
        
        Args:
            device_id: ID of the device to connect
            audio_profile_id: Audio profile to use for the connection
            
        Returns:
            True if connection successful, False otherwise
        """
        if device_id not in self.paired_devices:
            self.logger.error(f"Device {device_id} not found")
            return False
        
        device = self.paired_devices[device_id]
        
        try:
            # Update connection state
            device.connection_state = ConnectionState.CONNECTING
            self._update_device_in_db(device)
            
            # Connect using bluetoothctl
            result = subprocess.run(
                ["bluetoothctl", "connect", device.mac_address],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                device.connection_state = ConnectionState.CONNECTED
                device.last_connected = datetime.now()
                
                # Apply audio profile
                if audio_profile_id in self.audio_profiles:
                    await self._apply_audio_profile(device, self.audio_profiles[audio_profile_id])
                
                # Start device monitoring
                self._start_device_monitoring(device)
                
                # Log connection event
                self._log_connection_event(device_id, "connected")
                
                self.logger.info(f"Successfully connected to {device.name}")
                
                # Trigger connection callbacks
                await self._trigger_connection_callbacks(device_id, "connected")
                
                return True
            else:
                device.connection_state = ConnectionState.ERROR
                self.logger.error(f"Failed to connect to {device.name}: {result.stderr}")
                
        except Exception as e:
            device.connection_state = ConnectionState.ERROR
            self.logger.error(f"Connection error for {device.name}: {e}")
        
        finally:
            self._update_device_in_db(device)
        
        return False
    
    async def disconnect_device(self, device_id: str) -> bool:
        """
        Disconnect from a Bluetooth device.
        
        Args:
            device_id: ID of the device to disconnect
            
        Returns:
            True if disconnection successful, False otherwise
        """
        if device_id not in self.paired_devices:
            return False
        
        device = self.paired_devices[device_id]
        
        try:
            # Disconnect using bluetoothctl
            result = subprocess.run(
                ["bluetoothctl", "disconnect", device.mac_address],
                capture_output=True,
                text=True,
                timeout=15
            )
            
            device.connection_state = ConnectionState.DISCONNECTED
            
            # Stop device monitoring
            self._stop_device_monitoring(device_id)
            
            # End any active audio sessions
            await self._end_audio_sessions_for_device(device_id)
            
            # Log disconnection event
            self._log_connection_event(device_id, "disconnected")
            
            self.logger.info(f"Disconnected from {device.name}")
            
            # Trigger disconnection callbacks
            await self._trigger_connection_callbacks(device_id, "disconnected")
            
            return True
        
        except Exception as e:
            self.logger.error(f"Disconnection error for {device.name}: {e}")
            return False
        
        finally:
            self._update_device_in_db(device)
    
    async def _apply_audio_profile(self, device: BluetoothDevice, profile: AudioProfile):
        """Apply audio profile settings to device"""
        try:
            self.logger.info(f"Applying audio profile '{profile.name}' to {device.name}")
            
            # In a real implementation, this would configure:
            # - Codec selection
            # - Audio quality settings
            # - Noise suppression parameters
            # - Equalizer settings
            # - Microphone gain
            # - Speaker volume
            
            # For demonstration, we simulate profile application
            await asyncio.sleep(0.5)  # Simulate configuration time
            
            # Store profile application
            self.audio_processors[device.device_id] = {
                "profile": profile,
                "applied_at": datetime.now(),
                "active": True
            }
            
            self.logger.info(f"Audio profile '{profile.name}' applied successfully")
        
        except Exception as e:
            self.logger.error(f"Failed to apply audio profile: {e}")
    
    def _start_device_monitoring(self, device: BluetoothDevice):
        """Start monitoring device connection and audio quality"""
        if device.device_id in self.device_monitors:
            return  # Already monitoring
        
        def monitor_device():
            while device.connection_state in [ConnectionState.CONNECTED, ConnectionState.ACTIVE]:
                try:
                    # Check connection status
                    self._check_device_status(device)
                    
                    # Monitor audio quality if active session
                    if device.device_id in self.active_sessions:
                        self._monitor_audio_quality(device)
                    
                    time.sleep(5)  # Check every 5 seconds
                
                except Exception as e:
                    self.logger.error(f"Device monitoring error for {device.name}: {e}")
                    time.sleep(10)
        
        monitor_thread = threading.Thread(target=monitor_device, daemon=True)
        monitor_thread.start()
        self.device_monitors[device.device_id] = monitor_thread
    
    def _stop_device_monitoring(self, device_id: str):
        """Stop monitoring device"""
        if device_id in self.device_monitors:
            # Thread will exit naturally when connection state changes
            del self.device_monitors[device_id]
    
    def _check_device_status(self, device: BluetoothDevice):
        """Check device connection status and update metrics"""
        try:
            # Get device info
            result = subprocess.run(
                ["bluetoothctl", "info", device.mac_address],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                device_info = self._parse_device_info(result.stdout)
                
                # Update signal strength
                if device_info.get("rssi"):
                    device.signal_strength = device_info["rssi"]
                
                # Check if still connected
                if not device_info.get("connected", False) and device.connection_state == ConnectionState.CONNECTED:
                    device.connection_state = ConnectionState.DISCONNECTED
                    self._log_connection_event(device.device_id, "unexpected_disconnect")
                    
                self._update_device_in_db(device)
        
        except Exception as e:
            self.logger.error(f"Status check failed for {device.name}: {e}")
    
    def _monitor_audio_quality(self, device: BluetoothDevice):
        """Monitor audio quality metrics"""
        session_id = None
        
        # Find active session
        for sid, session in self.active_sessions.items():
            if session.device_id == device.device_id:
                session_id = sid
                break
        
        if not session_id:
            return
        
        session = self.active_sessions[session_id]
        
        try:
            # Simulate audio quality monitoring
            # In real implementation would measure:
            # - Latency
            # - Packet loss
            # - Audio dropouts
            # - Signal-to-noise ratio
            
            # Update session metrics
            session.latency_measurements.append(device.audio_latency_ms)
            session.noise_level_db = 45.0  # Simulated
            session.voice_clarity_score = 0.85  # Simulated
            
            # Update device metrics
            if len(session.latency_measurements) > 100:
                session.latency_measurements = session.latency_measurements[-50:]  # Keep last 50
        
        except Exception as e:
            self.logger.error(f"Audio quality monitoring error: {e}")
    
    async def start_audio_session(
        self, 
        device_id: str, 
        user_id: str,
        preferred_codec: AudioCodec = AudioCodec.AAC
    ) -> Optional[str]:
        """
        Start an audio session with a connected device.
        
        Args:
            device_id: ID of the connected device
            user_id: ID of the user starting the session
            preferred_codec: Preferred audio codec
            
        Returns:
            Session ID if successful, None otherwise
        """
        if device_id not in self.paired_devices:
            self.logger.error(f"Device {device_id} not found")
            return None
        
        device = self.paired_devices[device_id]
        
        if device.connection_state != ConnectionState.CONNECTED:
            self.logger.error(f"Device {device.name} not connected")
            return None
        
        # Select codec
        selected_codec = preferred_codec if preferred_codec in device.supported_codecs else device.supported_codecs[0]
        
        # Select protocol
        selected_protocol = BluetoothProtocol.A2DP if BluetoothProtocol.A2DP in device.supported_protocols else device.supported_protocols[0]
        
        # Create session
        session_id = f"session_{device_id}_{int(time.time())}"
        
        session = AudioSession(
            session_id=session_id,
            device_id=device_id,
            user_id=user_id,
            started_at=datetime.now(),
            ended_at=None,
            protocol_used=selected_protocol,
            codec_used=selected_codec,
            sample_rate=44100,  # Default sample rate
            bit_depth=16,       # Default bit depth
            channels=2,         # Stereo
            total_audio_time=0.0,
            audio_quality_score=0.0,
            connection_drops=0,
            latency_measurements=[],
            noise_level_db=0.0,
            voice_clarity_score=0.0
        )
        
        # Store session
        with self.lock:
            self.active_sessions[session_id] = session
        
        # Update device state
        device.connection_state = ConnectionState.ACTIVE
        self._update_device_in_db(device)
        
        # Save session to database
        self._save_session_to_db(session)
        
        self.logger.info(f"Started audio session {session_id} with {device.name} using {selected_codec.value}")
        
        return session_id
    
    async def end_audio_session(self, session_id: str) -> bool:
        """
        End an audio session.
        
        Args:
            session_id: ID of the session to end
            
        Returns:
            True if session ended successfully, False otherwise
        """
        if session_id not in self.active_sessions:
            return False
        
        session = self.active_sessions[session_id]
        device = self.paired_devices.get(session.device_id)
        
        # Update session
        session.ended_at = datetime.now()
        session.total_audio_time = (session.ended_at - session.started_at).total_seconds()
        
        # Calculate audio quality score
        session.audio_quality_score = self._calculate_audio_quality_score(session)
        
        # Update database
        self._update_session_in_db(session)
        
        # Remove from active sessions
        with self.lock:
            del self.active_sessions[session_id]
        
        # Update device state
        if device:
            device.connection_state = ConnectionState.CONNECTED
            self._update_device_in_db(device)
        
        self.logger.info(f"Ended audio session {session_id}")
        
        return True
    
    async def _end_audio_sessions_for_device(self, device_id: str):
        """End all audio sessions for a device"""
        sessions_to_end = []
        
        with self.lock:
            for session_id, session in self.active_sessions.items():
                if session.device_id == device_id:
                    sessions_to_end.append(session_id)
        
        for session_id in sessions_to_end:
            await self.end_audio_session(session_id)
    
    def _calculate_audio_quality_score(self, session: AudioSession) -> float:
        """Calculate overall audio quality score"""
        score = 1.0
        
        # Penalize for connection drops
        if session.connection_drops > 0:
            score -= min(session.connection_drops * 0.1, 0.3)
        
        # Consider latency
        if session.latency_measurements:
            avg_latency = sum(session.latency_measurements) / len(session.latency_measurements)
            if avg_latency > 150:  # High latency
                score -= 0.2
            elif avg_latency > 100:  # Medium latency
                score -= 0.1
        
        # Consider voice clarity
        if session.voice_clarity_score > 0:
            score = score * session.voice_clarity_score
        
        return max(0.0, min(1.0, score))
    
    def add_connection_callback(self, device_id: str, callback: Callable):
        """Add callback for connection events"""
        if device_id not in self.connection_callbacks:
            self.connection_callbacks[device_id] = []
        
        self.connection_callbacks[device_id].append(callback)
    
    async def _trigger_connection_callbacks(self, device_id: str, event_type: str):
        """Trigger connection callbacks"""
        if device_id in self.connection_callbacks:
            for callback in self.connection_callbacks[device_id]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(device_id, event_type)
                    else:
                        callback(device_id, event_type)
                except Exception as e:
                    self.logger.error(f"Connection callback error: {e}")
    
    def _save_device_to_db(self, device: BluetoothDevice):
        """Save device to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO bluetooth_devices 
            (device_id, name, mac_address, device_type, supported_protocols,
             supported_codecs, manufacturer, model, firmware_version,
             environmental_rating, connection_state, last_connected,
             battery_level, signal_strength, audio_latency_ms,
             noise_cancellation, microphone_quality, speaker_quality)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            device.device_id,
            device.name,
            device.mac_address,
            device.device_type.value,
            json.dumps([p.value for p in device.supported_protocols]),
            json.dumps([c.value for c in device.supported_codecs]),
            device.manufacturer,
            device.model,
            device.firmware_version,
            device.environmental_rating,
            device.connection_state.value,
            device.last_connected.isoformat() if device.last_connected else None,
            device.battery_level,
            device.signal_strength,
            device.audio_latency_ms,
            device.noise_cancellation,
            device.microphone_quality,
            device.speaker_quality
        ))
        
        conn.commit()
        conn.close()
    
    def _update_device_in_db(self, device: BluetoothDevice):
        """Update device in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE bluetooth_devices 
            SET connection_state = ?, last_connected = ?, battery_level = ?,
                signal_strength = ?, updated_at = CURRENT_TIMESTAMP
            WHERE device_id = ?
        """, (
            device.connection_state.value,
            device.last_connected.isoformat() if device.last_connected else None,
            device.battery_level,
            device.signal_strength,
            device.device_id
        ))
        
        conn.commit()
        conn.close()
    
    def _save_session_to_db(self, session: AudioSession):
        """Save audio session to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO audio_sessions 
            (session_id, device_id, user_id, started_at, ended_at, protocol_used,
             codec_used, sample_rate, bit_depth, channels, total_audio_time,
             audio_quality_score, connection_drops, latency_measurements,
             noise_level_db, voice_clarity_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            session.session_id,
            session.device_id,
            session.user_id,
            session.started_at.isoformat(),
            session.ended_at.isoformat() if session.ended_at else None,
            session.protocol_used.value,
            session.codec_used.value,
            session.sample_rate,
            session.bit_depth,
            session.channels,
            session.total_audio_time,
            session.audio_quality_score,
            session.connection_drops,
            json.dumps(session.latency_measurements),
            session.noise_level_db,
            session.voice_clarity_score
        ))
        
        conn.commit()
        conn.close()
    
    def _update_session_in_db(self, session: AudioSession):
        """Update audio session in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE audio_sessions 
            SET ended_at = ?, total_audio_time = ?, audio_quality_score = ?,
                connection_drops = ?, latency_measurements = ?, noise_level_db = ?,
                voice_clarity_score = ?
            WHERE session_id = ?
        """, (
            session.ended_at.isoformat() if session.ended_at else None,
            session.total_audio_time,
            session.audio_quality_score,
            session.connection_drops,
            json.dumps(session.latency_measurements),
            session.noise_level_db,
            session.voice_clarity_score,
            session.session_id
        ))
        
        conn.commit()
        conn.close()
    
    def _log_connection_event(self, device_id: str, event_type: str, event_data: Dict[str, Any] = None):
        """Log connection event to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO connection_events (device_id, event_type, event_data)
            VALUES (?, ?, ?)
        """, (
            device_id,
            event_type,
            json.dumps(event_data) if event_data else None
        ))
        
        conn.commit()
        conn.close()
    
    def get_connected_devices(self) -> List[Dict[str, Any]]:
        """Get list of connected devices"""
        connected_devices = []
        
        for device in self.paired_devices.values():
            if device.connection_state in [ConnectionState.CONNECTED, ConnectionState.ACTIVE]:
                device_dict = asdict(device)
                device_dict["device_type"] = device.device_type.value
                device_dict["supported_protocols"] = [p.value for p in device.supported_protocols]
                device_dict["supported_codecs"] = [c.value for c in device.supported_codecs]
                device_dict["connection_state"] = device.connection_state.value
                device_dict["last_connected"] = device.last_connected.isoformat() if device.last_connected else None
                connected_devices.append(device_dict)
        
        return connected_devices
    
    def get_device_status(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific device"""
        if device_id not in self.paired_devices:
            return None
        
        device = self.paired_devices[device_id]
        
        # Check for active session
        active_session = None
        for session in self.active_sessions.values():
            if session.device_id == device_id:
                active_session = {
                    "session_id": session.session_id,
                    "user_id": session.user_id,
                    "started_at": session.started_at.isoformat(),
                    "protocol_used": session.protocol_used.value,
                    "codec_used": session.codec_used.value
                }
                break
        
        device_dict = asdict(device)
        device_dict["device_type"] = device.device_type.value
        device_dict["supported_protocols"] = [p.value for p in device.supported_protocols]
        device_dict["supported_codecs"] = [c.value for c in device.supported_codecs]
        device_dict["connection_state"] = device.connection_state.value
        device_dict["last_connected"] = device.last_connected.isoformat() if device.last_connected else None
        device_dict["active_session"] = active_session
        device_dict["audio_profile"] = self.audio_processors.get(device_id, {}).get("profile", {})
        
        return device_dict
    
    def get_bluetooth_statistics(self) -> Dict[str, Any]:
        """Get Bluetooth system statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Device statistics
        cursor.execute("SELECT COUNT(*) FROM bluetooth_devices")
        total_devices = cursor.fetchone()[0]
        
        cursor.execute("SELECT device_type, COUNT(*) FROM bluetooth_devices GROUP BY device_type")
        device_type_distribution = dict(cursor.fetchall())
        
        # Connection statistics
        cursor.execute("SELECT connection_state, COUNT(*) FROM bluetooth_devices GROUP BY connection_state")
        connection_state_distribution = dict(cursor.fetchall())
        
        # Session statistics
        cursor.execute("SELECT COUNT(*) FROM audio_sessions")
        total_sessions = cursor.fetchone()[0]
        
        cursor.execute("SELECT AVG(audio_quality_score) FROM audio_sessions WHERE audio_quality_score > 0")
        avg_quality = cursor.fetchone()[0] or 0
        
        # Recent activity
        cursor.execute("""
            SELECT COUNT(*) FROM connection_events 
            WHERE timestamp > datetime('now', '-1 hour')
        """)
        recent_events = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "total_devices": total_devices,
            "connected_devices": len([d for d in self.paired_devices.values() 
                                    if d.connection_state in [ConnectionState.CONNECTED, ConnectionState.ACTIVE]]),
            "active_sessions": len(self.active_sessions),
            "device_type_distribution": device_type_distribution,
            "connection_state_distribution": connection_state_distribution,
            "total_audio_sessions": total_sessions,
            "average_audio_quality": round(avg_quality, 2),
            "recent_connection_events": recent_events,
            "available_audio_profiles": len(self.audio_profiles)
        }


# Example usage and testing
async def main():
    """Example usage of Bluetooth headset manager"""
    bluetooth_manager = BluetoothHeadsetManager()
    
    # Wait for device discovery
    await asyncio.sleep(2)
    
    # Show discovered devices
    print("=== Discovered Devices ===")
    for device_id, device in bluetooth_manager.paired_devices.items():
        print(f"Device: {device.name}")
        print(f"  Type: {device.device_type.value}")
        print(f"  MAC: {device.mac_address}")
        print(f"  State: {device.connection_state.value}")
        print(f"  Protocols: {[p.value for p in device.supported_protocols]}")
        print(f"  Codecs: {[c.value for c in device.supported_codecs]}")
        print()
    
    # Try to connect to first available device
    if bluetooth_manager.paired_devices:
        device_id = list(bluetooth_manager.paired_devices.keys())[0]
        print(f"=== Connecting to {device_id} ===")
        
        connected = await bluetooth_manager.connect_device(device_id, "marine_bridge")
        if connected:
            print("Connection successful!")
            
            # Start audio session
            session_id = await bluetooth_manager.start_audio_session(device_id, "test_user")
            if session_id:
                print(f"Audio session started: {session_id}")
                
                # Simulate audio session
                await asyncio.sleep(5)
                
                # End session
                await bluetooth_manager.end_audio_session(session_id)
                print("Audio session ended")
            
            # Disconnect device
            await bluetooth_manager.disconnect_device(device_id)
            print("Device disconnected")
    
    # Show statistics
    stats = bluetooth_manager.get_bluetooth_statistics()
    print(f"=== Statistics ===")
    print(f"Total devices: {stats['total_devices']}")
    print(f"Connected devices: {stats['connected_devices']}")
    print(f"Audio sessions: {stats['total_audio_sessions']}")
    print(f"Average quality: {stats['average_audio_quality']}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())