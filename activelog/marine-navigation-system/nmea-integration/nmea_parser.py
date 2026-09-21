"""
NMEA Device Integration Module
Comprehensive NMEA 0183 and NMEA 2000 protocol support for marine navigation
"""

import asyncio
import serial_asyncio
import socket
import struct
import time
import logging
from typing import Dict, List, Optional, Callable, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import json
import math
from datetime import datetime, timezone
import threading
from queue import Queue

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NMEAVersion(Enum):
    NMEA_0183 = "0183"
    NMEA_2000 = "2000"

@dataclass
class GPSPosition:
    latitude: float
    longitude: float
    altitude: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.now)
    quality: int = 0
    satellites: int = 0
    hdop: Optional[float] = None
    speed: Optional[float] = None
    course: Optional[float] = None

@dataclass
class DepthData:
    depth_meters: float
    depth_feet: float
    depth_fathoms: float
    offset_meters: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class WindData:
    wind_angle: float  # degrees
    wind_speed_knots: float
    wind_speed_ms: float
    reference: str  # 'R' for relative, 'T' for true
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class WaterData:
    temperature_celsius: float
    temperature_fahrenheit: float
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class EngineData:
    rpm: Optional[float] = None
    temperature: Optional[float] = None
    oil_pressure: Optional[float] = None
    fuel_rate: Optional[float] = None
    hours: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class NMEAData:
    gps: Optional[GPSPosition] = None
    depth: Optional[DepthData] = None
    wind: Optional[WindData] = None
    water: Optional[WaterData] = None
    engine: Optional[EngineData] = None
    raw_sentences: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)

class NMEA0183Parser:
    """NMEA 0183 sentence parser"""
    
    def __init__(self):
        self.sentence_handlers = {
            'GPGGA': self._parse_gga,
            'GPRMC': self._parse_rmc,
            'GPGLL': self._parse_gll,
            'GPVTG': self._parse_vtg,
            'GPDBT': self._parse_dbt,
            'GPDPT': self._parse_dpt,
            'WIMWV': self._parse_mwv,
            'WIMTA': self._parse_mta,
            'YXXDR': self._parse_xdr,
        }
    
    def parse(self, sentence: str) -> Dict[str, Any]:
        """Parse a single NMEA 0183 sentence"""
        try:
            if not sentence.startswith('$'):
                return {}
            
            # Remove checksum if present
            if '*' in sentence:
                sentence = sentence.split('*')[0]
            
            parts = sentence[1:].split(',')
            sentence_id = parts[0]
            
            # Handle talker ID + sentence type
            if len(sentence_id) >= 5:
                sentence_type = sentence_id[-3:]  # Last 3 characters
                talker_id = sentence_id[:-3]      # Everything before last 3
                
                # Try with full sentence ID first, then just sentence type
                handler = (self.sentence_handlers.get(sentence_id) or 
                          self.sentence_handlers.get(sentence_type))
                
                if handler:
                    return handler(parts[1:])
            
            return {}
            
        except Exception as e:
            logger.error(f"Error parsing NMEA sentence: {sentence}, Error: {e}")
            return {}
    
    def _parse_gga(self, fields: List[str]) -> Dict[str, Any]:
        """Parse GGA sentence (GPS Fix Data)"""
        try:
            if len(fields) < 14:
                return {}
            
            time_str = fields[0]
            lat = self._parse_coordinate(fields[1], fields[2])
            lon = self._parse_coordinate(fields[3], fields[4])
            quality = int(fields[5]) if fields[5] else 0
            satellites = int(fields[6]) if fields[6] else 0
            hdop = float(fields[7]) if fields[7] else None
            altitude = float(fields[8]) if fields[8] else None
            
            return {
                'gps': GPSPosition(
                    latitude=lat,
                    longitude=lon,
                    altitude=altitude,
                    quality=quality,
                    satellites=satellites,
                    hdop=hdop,
                    timestamp=self._parse_time(time_str)
                )
            }
        except Exception as e:
            logger.error(f"Error parsing GGA: {e}")
            return {}
    
    def _parse_rmc(self, fields: List[str]) -> Dict[str, Any]:
        """Parse RMC sentence (Recommended Minimum)"""
        try:
            if len(fields) < 12:
                return {}
            
            time_str = fields[0]
            status = fields[1]
            if status != 'A':  # A = Active (valid), V = Void (invalid)
                return {}
            
            lat = self._parse_coordinate(fields[2], fields[3])
            lon = self._parse_coordinate(fields[4], fields[5])
            speed = float(fields[6]) if fields[6] else None
            course = float(fields[7]) if fields[7] else None
            date_str = fields[8]
            
            timestamp = self._parse_datetime(date_str, time_str)
            
            return {
                'gps': GPSPosition(
                    latitude=lat,
                    longitude=lon,
                    speed=speed,
                    course=course,
                    timestamp=timestamp
                )
            }
        except Exception as e:
            logger.error(f"Error parsing RMC: {e}")
            return {}
    
    def _parse_gll(self, fields: List[str]) -> Dict[str, Any]:
        """Parse GLL sentence (Geographic Position)"""
        try:
            if len(fields) < 6:
                return {}
            
            lat = self._parse_coordinate(fields[0], fields[1])
            lon = self._parse_coordinate(fields[2], fields[3])
            time_str = fields[4]
            status = fields[5]
            
            if status != 'A':
                return {}
            
            return {
                'gps': GPSPosition(
                    latitude=lat,
                    longitude=lon,
                    timestamp=self._parse_time(time_str)
                )
            }
        except Exception as e:
            logger.error(f"Error parsing GLL: {e}")
            return {}
    
    def _parse_vtg(self, fields: List[str]) -> Dict[str, Any]:
        """Parse VTG sentence (Track Made Good and Ground Speed)"""
        try:
            if len(fields) < 8:
                return {}
            
            course_true = float(fields[0]) if fields[0] else None
            course_magnetic = float(fields[2]) if fields[2] else None
            speed_knots = float(fields[4]) if fields[4] else None
            speed_kmh = float(fields[6]) if fields[6] else None
            
            return {
                'gps': GPSPosition(
                    latitude=0,  # VTG doesn't contain position
                    longitude=0,
                    speed=speed_knots,
                    course=course_true
                )
            }
        except Exception as e:
            logger.error(f"Error parsing VTG: {e}")
            return {}
    
    def _parse_dbt(self, fields: List[str]) -> Dict[str, Any]:
        """Parse DBT sentence (Depth Below Transducer)"""
        try:
            if len(fields) < 6:
                return {}
            
            depth_feet = float(fields[0]) if fields[0] else 0
            depth_meters = float(fields[2]) if fields[2] else 0
            depth_fathoms = float(fields[4]) if fields[4] else 0
            
            return {
                'depth': DepthData(
                    depth_meters=depth_meters,
                    depth_feet=depth_feet,
                    depth_fathoms=depth_fathoms
                )
            }
        except Exception as e:
            logger.error(f"Error parsing DBT: {e}")
            return {}
    
    def _parse_dpt(self, fields: List[str]) -> Dict[str, Any]:
        """Parse DPT sentence (Depth of Water)"""
        try:
            if len(fields) < 1:
                return {}
            
            depth_meters = float(fields[0]) if fields[0] else 0
            offset_meters = float(fields[1]) if len(fields) > 1 and fields[1] else None
            
            return {
                'depth': DepthData(
                    depth_meters=depth_meters,
                    depth_feet=depth_meters * 3.28084,
                    depth_fathoms=depth_meters * 0.546807,
                    offset_meters=offset_meters
                )
            }
        except Exception as e:
            logger.error(f"Error parsing DPT: {e}")
            return {}
    
    def _parse_mwv(self, fields: List[str]) -> Dict[str, Any]:
        """Parse MWV sentence (Wind Speed and Angle)"""
        try:
            if len(fields) < 5:
                return {}
            
            wind_angle = float(fields[0]) if fields[0] else 0
            reference = fields[1]  # R = Relative, T = True
            wind_speed = float(fields[2]) if fields[2] else 0
            speed_units = fields[3]  # N = knots, M = m/s, K = km/h
            status = fields[4]
            
            if status != 'A':
                return {}
            
            # Convert to knots and m/s
            if speed_units == 'M':
                wind_speed_ms = wind_speed
                wind_speed_knots = wind_speed * 1.94384
            elif speed_units == 'K':
                wind_speed_knots = wind_speed * 0.539957
                wind_speed_ms = wind_speed / 3.6
            else:  # Assume knots
                wind_speed_knots = wind_speed
                wind_speed_ms = wind_speed * 0.514444
            
            return {
                'wind': WindData(
                    wind_angle=wind_angle,
                    wind_speed_knots=wind_speed_knots,
                    wind_speed_ms=wind_speed_ms,
                    reference=reference
                )
            }
        except Exception as e:
            logger.error(f"Error parsing MWV: {e}")
            return {}
    
    def _parse_mta(self, fields: List[str]) -> Dict[str, Any]:
        """Parse MTA sentence (Water Temperature)"""
        try:
            if len(fields) < 2:
                return {}
            
            temperature = float(fields[0]) if fields[0] else 0
            units = fields[1]  # C = Celsius, F = Fahrenheit
            
            if units == 'F':
                temp_celsius = (temperature - 32) * 5/9
                temp_fahrenheit = temperature
            else:
                temp_celsius = temperature
                temp_fahrenheit = temperature * 9/5 + 32
            
            return {
                'water': WaterData(
                    temperature_celsius=temp_celsius,
                    temperature_fahrenheit=temp_fahrenheit
                )
            }
        except Exception as e:
            logger.error(f"Error parsing MTA: {e}")
            return {}
    
    def _parse_xdr(self, fields: List[str]) -> Dict[str, Any]:
        """Parse XDR sentence (Transducer Measurement)"""
        try:
            # XDR can contain multiple measurements
            result = {}
            
            for i in range(0, len(fields), 4):
                if i + 3 >= len(fields):
                    break
                
                sensor_type = fields[i]
                measurement = float(fields[i + 1]) if fields[i + 1] else 0
                units = fields[i + 2]
                sensor_name = fields[i + 3]
                
                # Engine RPM
                if 'RPM' in sensor_name.upper():
                    if 'engine' not in result:
                        result['engine'] = EngineData()
                    result['engine'].rpm = measurement
                
                # Engine temperature
                elif 'TEMP' in sensor_name.upper() and 'ENG' in sensor_name.upper():
                    if 'engine' not in result:
                        result['engine'] = EngineData()
                    result['engine'].temperature = measurement
                
                # Oil pressure
                elif 'OIL' in sensor_name.upper() and 'PRESS' in sensor_name.upper():
                    if 'engine' not in result:
                        result['engine'] = EngineData()
                    result['engine'].oil_pressure = measurement
            
            return result
            
        except Exception as e:
            logger.error(f"Error parsing XDR: {e}")
            return {}
    
    def _parse_coordinate(self, coord_str: str, direction: str) -> float:
        """Parse NMEA coordinate format (DDMM.MMMM)"""
        if not coord_str or not direction:
            return 0.0
        
        coord = float(coord_str)
        degrees = int(coord / 100)
        minutes = coord - (degrees * 100)
        decimal = degrees + minutes / 60
        
        if direction in ['S', 'W']:
            decimal = -decimal
        
        return decimal
    
    def _parse_time(self, time_str: str) -> datetime:
        """Parse NMEA time format (HHMMSS.sss)"""
        if not time_str:
            return datetime.now(timezone.utc)
        
        try:
            if '.' in time_str:
                hours = int(time_str[0:2])
                minutes = int(time_str[2:4])
                seconds_float = float(time_str[4:])
                seconds = int(seconds_float)
                microseconds = int((seconds_float - seconds) * 1000000)
            else:
                hours = int(time_str[0:2])
                minutes = int(time_str[2:4])
                seconds = int(time_str[4:6]) if len(time_str) >= 6 else 0
                microseconds = 0
            
            now = datetime.now(timezone.utc)
            return now.replace(hour=hours, minute=minutes, second=seconds, 
                            microsecond=microseconds)
        except:
            return datetime.now(timezone.utc)
    
    def _parse_datetime(self, date_str: str, time_str: str) -> datetime:
        """Parse NMEA date and time"""
        try:
            # Date format: DDMMYY
            day = int(date_str[0:2])
            month = int(date_str[2:4])
            year = 2000 + int(date_str[4:6])  # Assume 21st century
            
            time_dt = self._parse_time(time_str)
            
            return datetime(year, month, day, time_dt.hour, time_dt.minute, 
                          time_dt.second, time_dt.microsecond, timezone.utc)
        except:
            return datetime.now(timezone.utc)

class NMEA2000Parser:
    """NMEA 2000 (CAN bus) message parser"""
    
    def __init__(self):
        self.pgn_handlers = {
            129025: self._parse_position_rapid,
            129026: self._parse_cog_sog,
            129029: self._parse_gnss_position,
            128267: self._parse_water_depth,
            130306: self._parse_wind_data,
            130310: self._parse_water_temp,
            127488: self._parse_engine_rapid,
            127489: self._parse_engine_dynamic,
        }
    
    def parse(self, can_id: int, data: bytes) -> Dict[str, Any]:
        """Parse NMEA 2000 CAN message"""
        try:
            # Extract PGN from CAN ID
            pgn = (can_id >> 8) & 0x1FFFF
            
            handler = self.pgn_handlers.get(pgn)
            if handler:
                return handler(data)
            
            return {}
            
        except Exception as e:
            logger.error(f"Error parsing NMEA 2000 message: {e}")
            return {}
    
    def _parse_position_rapid(self, data: bytes) -> Dict[str, Any]:
        """Parse PGN 129025 - Position, Rapid Update"""
        try:
            if len(data) < 8:
                return {}
            
            lat_raw = struct.unpack('<i', data[0:4])[0]
            lon_raw = struct.unpack('<i', data[4:8])[0]
            
            latitude = lat_raw * 1e-7
            longitude = lon_raw * 1e-7
            
            return {
                'gps': GPSPosition(latitude=latitude, longitude=longitude)
            }
        except:
            return {}
    
    def _parse_cog_sog(self, data: bytes) -> Dict[str, Any]:
        """Parse PGN 129026 - COG & SOG, Rapid Update"""
        try:
            if len(data) < 8:
                return {}
            
            cog_raw = struct.unpack('<H', data[2:4])[0]
            sog_raw = struct.unpack('<H', data[4:6])[0]
            
            course = cog_raw * 0.0001 * 180 / math.pi  # Convert to degrees
            speed = sog_raw * 0.01 * 1.94384  # Convert cm/s to knots
            
            return {
                'gps': GPSPosition(
                    latitude=0, longitude=0,  # Not in this message
                    speed=speed,
                    course=course
                )
            }
        except:
            return {}
    
    def _parse_water_depth(self, data: bytes) -> Dict[str, Any]:
        """Parse PGN 128267 - Water Depth"""
        try:
            if len(data) < 8:
                return {}
            
            depth_raw = struct.unpack('<I', data[1:5])[0]
            offset_raw = struct.unpack('<h', data[5:7])[0]
            
            depth_meters = depth_raw * 0.01
            offset_meters = offset_raw * 0.001 if offset_raw != -32768 else None
            
            return {
                'depth': DepthData(
                    depth_meters=depth_meters,
                    depth_feet=depth_meters * 3.28084,
                    depth_fathoms=depth_meters * 0.546807,
                    offset_meters=offset_meters
                )
            }
        except:
            return {}
    
    def _parse_wind_data(self, data: bytes) -> Dict[str, Any]:
        """Parse PGN 130306 - Wind Data"""
        try:
            if len(data) < 8:
                return {}
            
            wind_speed_raw = struct.unpack('<H', data[1:3])[0]
            wind_angle_raw = struct.unpack('<H', data[3:5])[0]
            reference = data[5] & 0x07
            
            wind_speed_ms = wind_speed_raw * 0.01
            wind_angle = wind_angle_raw * 0.0001 * 180 / math.pi
            reference_str = 'T' if reference == 2 else 'R'
            
            return {
                'wind': WindData(
                    wind_angle=wind_angle,
                    wind_speed_knots=wind_speed_ms * 1.94384,
                    wind_speed_ms=wind_speed_ms,
                    reference=reference_str
                )
            }
        except:
            return {}
    
    def _parse_water_temp(self, data: bytes) -> Dict[str, Any]:
        """Parse PGN 130310 - Water Temperature"""
        try:
            if len(data) < 8:
                return {}
            
            temp_raw = struct.unpack('<H', data[2:4])[0]
            temp_kelvin = temp_raw * 0.01
            temp_celsius = temp_kelvin - 273.15
            
            return {
                'water': WaterData(
                    temperature_celsius=temp_celsius,
                    temperature_fahrenheit=temp_celsius * 9/5 + 32
                )
            }
        except:
            return {}
    
    def _parse_engine_rapid(self, data: bytes) -> Dict[str, Any]:
        """Parse PGN 127488 - Engine Parameters, Rapid Update"""
        try:
            if len(data) < 8:
                return {}
            
            rpm_raw = struct.unpack('<H', data[2:4])[0]
            rpm = rpm_raw * 0.25
            
            return {
                'engine': EngineData(rpm=rpm)
            }
        except:
            return {}
    
    def _parse_engine_dynamic(self, data: bytes) -> Dict[str, Any]:
        """Parse PGN 127489 - Engine Parameters, Dynamic"""
        try:
            if len(data) < 26:
                return {}
            
            oil_pressure_raw = struct.unpack('<H', data[1:3])[0]
            oil_temp_raw = struct.unpack('<H', data[3:5])[0]
            fuel_rate_raw = struct.unpack('<H', data[13:15])[0]
            engine_hours_raw = struct.unpack('<I', data[17:21])[0]
            
            oil_pressure = oil_pressure_raw * 100  # Pa
            oil_temp = oil_temp_raw * 0.03125 - 273  # Celsius
            fuel_rate = fuel_rate_raw * 0.1  # L/h
            engine_hours = engine_hours_raw * 0.05  # seconds to hours
            
            return {
                'engine': EngineData(
                    oil_pressure=oil_pressure,
                    temperature=oil_temp,
                    fuel_rate=fuel_rate,
                    hours=engine_hours
                )
            }
        except:
            return {}

class NMEADevice:
    """NMEA device connection manager"""
    
    def __init__(self, device_type: str = "serial", **kwargs):
        self.device_type = device_type
        self.config = kwargs
        self.is_connected = False
        self.connection = None
        self.data_callbacks = []
        self.error_callbacks = []
        
        self.nmea_0183_parser = NMEA0183Parser()
        self.nmea_2000_parser = NMEA2000Parser()
        
        self._stop_event = threading.Event()
        self._read_thread = None
        
    async def connect(self):
        """Connect to NMEA device"""
        try:
            if self.device_type == "serial":
                await self._connect_serial()
            elif self.device_type == "tcp":
                await self._connect_tcp()
            elif self.device_type == "udp":
                await self._connect_udp()
            elif self.device_type == "can":
                await self._connect_can()
            else:
                raise ValueError(f"Unsupported device type: {self.device_type}")
            
            self.is_connected = True
            logger.info(f"Connected to {self.device_type} NMEA device")
            
        except Exception as e:
            logger.error(f"Failed to connect to NMEA device: {e}")
            raise
    
    async def _connect_serial(self):
        """Connect to serial NMEA device"""
        port = self.config.get('port', '/dev/ttyUSB0')
        baudrate = self.config.get('baudrate', 4800)
        
        self.connection = await serial_asyncio.open_serial_connection(
            url=port, baudrate=baudrate
        )
        
        # Start reading in background
        self._read_thread = threading.Thread(target=self._read_serial_loop)
        self._read_thread.start()
    
    async def _connect_tcp(self):
        """Connect to TCP NMEA device"""
        host = self.config.get('host', 'localhost')
        port = self.config.get('port', 10110)
        
        self.connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connection.connect((host, port))
        
        # Start reading in background
        self._read_thread = threading.Thread(target=self._read_tcp_loop)
        self._read_thread.start()
    
    async def _connect_udp(self):
        """Connect to UDP NMEA device"""
        host = self.config.get('host', 'localhost')
        port = self.config.get('port', 10110)
        
        self.connection = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.connection.bind((host, port))
        
        # Start reading in background
        self._read_thread = threading.Thread(target=self._read_udp_loop)
        self._read_thread.start()
    
    async def _connect_can(self):
        """Connect to CAN bus for NMEA 2000"""
        try:
            import can
            
            channel = self.config.get('channel', 'can0')
            bustype = self.config.get('bustype', 'socketcan')
            
            self.connection = can.interface.Bus(channel=channel, bustype=bustype)
            
            # Start reading in background
            self._read_thread = threading.Thread(target=self._read_can_loop)
            self._read_thread.start()
            
        except ImportError:
            raise ImportError("python-can library required for CAN bus support")
    
    def _read_serial_loop(self):
        """Background serial reading loop"""
        reader, writer = self.connection
        buffer = ""
        
        while not self._stop_event.is_set():
            try:
                # Read available data
                data = asyncio.run(reader.read(1024))
                if not data:
                    continue
                
                buffer += data.decode('ascii', errors='ignore')
                
                # Process complete sentences
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    sentence = line.strip()
                    
                    if sentence.startswith('$'):
                        self._process_nmea_0183(sentence)
                        
            except Exception as e:
                self._handle_error(e)
                time.sleep(1)
    
    def _read_tcp_loop(self):
        """Background TCP reading loop"""
        buffer = ""
        
        while not self._stop_event.is_set():
            try:
                data = self.connection.recv(1024)
                if not data:
                    continue
                
                buffer += data.decode('ascii', errors='ignore')
                
                # Process complete sentences
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    sentence = line.strip()
                    
                    if sentence.startswith('$'):
                        self._process_nmea_0183(sentence)
                        
            except Exception as e:
                self._handle_error(e)
                time.sleep(1)
    
    def _read_udp_loop(self):
        """Background UDP reading loop"""
        while not self._stop_event.is_set():
            try:
                data, addr = self.connection.recvfrom(1024)
                sentence = data.decode('ascii', errors='ignore').strip()
                
                if sentence.startswith('$'):
                    self._process_nmea_0183(sentence)
                    
            except Exception as e:
                self._handle_error(e)
                time.sleep(1)
    
    def _read_can_loop(self):
        """Background CAN reading loop"""
        while not self._stop_event.is_set():
            try:
                message = self.connection.recv(timeout=1.0)
                if message:
                    self._process_nmea_2000(message.arbitration_id, message.data)
                    
            except Exception as e:
                self._handle_error(e)
                time.sleep(1)
    
    def _process_nmea_0183(self, sentence: str):
        """Process NMEA 0183 sentence"""
        try:
            parsed_data = self.nmea_0183_parser.parse(sentence)
            if parsed_data:
                nmea_data = NMEAData(
                    gps=parsed_data.get('gps'),
                    depth=parsed_data.get('depth'),
                    wind=parsed_data.get('wind'),
                    water=parsed_data.get('water'),
                    engine=parsed_data.get('engine'),
                    raw_sentences=[sentence]
                )
                self._notify_callbacks(nmea_data)
                
        except Exception as e:
            self._handle_error(e)
    
    def _process_nmea_2000(self, can_id: int, data: bytes):
        """Process NMEA 2000 CAN message"""
        try:
            parsed_data = self.nmea_2000_parser.parse(can_id, data)
            if parsed_data:
                nmea_data = NMEAData(
                    gps=parsed_data.get('gps'),
                    depth=parsed_data.get('depth'),
                    wind=parsed_data.get('wind'),
                    water=parsed_data.get('water'),
                    engine=parsed_data.get('engine')
                )
                self._notify_callbacks(nmea_data)
                
        except Exception as e:
            self._handle_error(e)
    
    def _notify_callbacks(self, data: NMEAData):
        """Notify all registered callbacks"""
        for callback in self.data_callbacks:
            try:
                callback(data)
            except Exception as e:
                logger.error(f"Error in data callback: {e}")
    
    def _handle_error(self, error: Exception):
        """Handle connection errors"""
        logger.error(f"NMEA device error: {error}")
        for callback in self.error_callbacks:
            try:
                callback(error)
            except Exception as e:
                logger.error(f"Error in error callback: {e}")
    
    def add_data_callback(self, callback: Callable[[NMEAData], None]):
        """Add data callback"""
        self.data_callbacks.append(callback)
    
    def add_error_callback(self, callback: Callable[[Exception], None]):
        """Add error callback"""
        self.error_callbacks.append(callback)
    
    def disconnect(self):
        """Disconnect from device"""
        self._stop_event.set()
        
        if self._read_thread:
            self._read_thread.join(timeout=5)
        
        if self.connection:
            if hasattr(self.connection, 'close'):
                self.connection.close()
        
        self.is_connected = False
        logger.info("Disconnected from NMEA device")

class NMEAIntegrationManager:
    """Main NMEA integration manager"""
    
    def __init__(self):
        self.devices: Dict[str, NMEADevice] = {}
        self.data_store = Queue()
        self.latest_data = NMEAData()
        self.data_callbacks = []
        
    def add_device(self, device_id: str, device: NMEADevice):
        """Add NMEA device"""
        self.devices[device_id] = device
        device.add_data_callback(self._on_device_data)
        device.add_error_callback(self._on_device_error)
        
        logger.info(f"Added NMEA device: {device_id}")
    
    async def connect_all_devices(self):
        """Connect all configured devices"""
        for device_id, device in self.devices.items():
            try:
                await device.connect()
                logger.info(f"Connected device: {device_id}")
            except Exception as e:
                logger.error(f"Failed to connect device {device_id}: {e}")
    
    def _on_device_data(self, data: NMEAData):
        """Handle data from any device"""
        # Merge with latest data
        if data.gps:
            self.latest_data.gps = data.gps
        if data.depth:
            self.latest_data.depth = data.depth
        if data.wind:
            self.latest_data.wind = data.wind
        if data.water:
            self.latest_data.water = data.water
        if data.engine:
            self.latest_data.engine = data.engine
        
        self.latest_data.timestamp = datetime.now()
        
        # Store in queue
        self.data_store.put(data)
        
        # Notify callbacks
        for callback in self.data_callbacks:
            callback(self.latest_data)
    
    def _on_device_error(self, error: Exception):
        """Handle device errors"""
        logger.error(f"Device error: {error}")
    
    def get_latest_data(self) -> NMEAData:
        """Get latest consolidated NMEA data"""
        return self.latest_data
    
    def get_position(self) -> Optional[GPSPosition]:
        """Get current GPS position"""
        return self.latest_data.gps
    
    def get_depth(self) -> Optional[DepthData]:
        """Get current depth data"""
        return self.latest_data.depth
    
    def get_wind(self) -> Optional[WindData]:
        """Get current wind data"""
        return self.latest_data.wind
    
    def get_water_temperature(self) -> Optional[WaterData]:
        """Get current water temperature"""
        return self.latest_data.water
    
    def get_engine_data(self) -> Optional[EngineData]:
        """Get current engine data"""
        return self.latest_data.engine
    
    def add_data_callback(self, callback: Callable[[NMEAData], None]):
        """Add callback for data updates"""
        self.data_callbacks.append(callback)
    
    def disconnect_all(self):
        """Disconnect all devices"""
        for device in self.devices.values():
            device.disconnect()
        
        logger.info("Disconnected all NMEA devices")

# Example usage and testing
async def example_usage():
    """Example of how to use the NMEA integration"""
    
    # Create integration manager
    manager = NMEAIntegrationManager()
    
    # Add serial GPS device
    gps_device = NMEADevice("serial", port="/dev/ttyUSB0", baudrate=4800)
    manager.add_device("gps", gps_device)
    
    # Add TCP chartplotter
    chartplotter = NMEADevice("tcp", host="192.168.1.100", port=10110)
    manager.add_device("chartplotter", chartplotter)
    
    # Add CAN bus for NMEA 2000
    can_device = NMEADevice("can", channel="can0", bustype="socketcan")
    manager.add_device("can_bus", can_device)
    
    # Add callback for data updates
    def on_data_update(data: NMEAData):
        if data.gps:
            print(f"Position: {data.gps.latitude:.6f}, {data.gps.longitude:.6f}")
        if data.depth:
            print(f"Depth: {data.depth.depth_meters:.1f}m")
        if data.wind:
            print(f"Wind: {data.wind.wind_speed_knots:.1f}kts @ {data.wind.wind_angle:.0f}°")
    
    manager.add_data_callback(on_data_update)
    
    # Connect all devices
    await manager.connect_all_devices()
    
    # Run for demonstration
    try:
        await asyncio.sleep(60)  # Run for 1 minute
    finally:
        manager.disconnect_all()

if __name__ == "__main__":
    asyncio.run(example_usage())