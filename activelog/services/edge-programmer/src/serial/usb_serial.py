"""
USB Serial Communication for Direct Code Upload
"""

import serial
import serial.tools.list_ports
import subprocess
import tempfile
import os
import uuid
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import asyncio
import threading
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from ..database import SerialConnection, Device, CodeGeneration, CodeGenerationStatus, DeviceType


class USBSerialManager:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.active_connections: Dict[str, serial.Serial] = {}
        self.upload_processes: Dict[uuid.UUID, subprocess.Popen] = {}
        
        # Arduino CLI and platform configurations
        self.arduino_cli_path = self._find_arduino_cli()
        self.platform_configs = {
            DeviceType.ARDUINO_UNO: {
                "platform": "arduino:avr",
                "board": "arduino:avr:uno",
                "programmer": "arduino",
                "upload_speed": 115200
            },
            DeviceType.ARDUINO_NANO: {
                "platform": "arduino:avr",
                "board": "arduino:avr:nano:cpu=atmega328",
                "programmer": "arduino",
                "upload_speed": 57600
            },
            DeviceType.ARDUINO_MEGA: {
                "platform": "arduino:avr",
                "board": "arduino:avr:mega:cpu=atmega2560",
                "programmer": "wiring",
                "upload_speed": 115200
            },
            DeviceType.ESP32: {
                "platform": "esp32:esp32",
                "board": "esp32:esp32:esp32",
                "programmer": "esptool",
                "upload_speed": 921600
            },
            DeviceType.ESP8266: {
                "platform": "esp8266:esp8266",
                "board": "esp8266:esp8266:nodemcuv2",
                "programmer": "esptool",
                "upload_speed": 921600
            }
        }
    
    def _find_arduino_cli(self) -> Optional[str]:
        """Find Arduino CLI executable"""
        possible_paths = [
            "arduino-cli",
            "/usr/local/bin/arduino-cli",
            "/usr/bin/arduino-cli",
            os.path.expanduser("~/bin/arduino-cli"),
            "./arduino-cli"
        ]
        
        for path in possible_paths:
            try:
                result = subprocess.run([path, "version"], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    return path
            except (subprocess.TimeoutExpired, FileNotFoundError):
                continue
        
        return None
    
    async def scan_serial_ports(self) -> List[Dict[str, Any]]:
        """Scan for available serial ports"""
        ports = []
        
        for port in serial.tools.list_ports.comports():
            port_info = {
                "port": port.device,
                "description": port.description,
                "hwid": port.hwid,
                "vid": getattr(port, 'vid', None),
                "pid": getattr(port, 'pid', None),
                "manufacturer": getattr(port, 'manufacturer', None),
                "product": getattr(port, 'product', None),
                "device_type": self._detect_device_type(port)
            }
            ports.append(port_info)
        
        return ports
    
    def _detect_device_type(self, port) -> Optional[DeviceType]:
        """Detect device type from port information"""
        vid = getattr(port, 'vid', None)
        pid = getattr(port, 'pid', None)
        
        # Common VID/PID mappings for Arduino devices
        device_mappings = {
            (0x2341, 0x0043): DeviceType.ARDUINO_UNO,    # Arduino Uno R3
            (0x2341, 0x0001): DeviceType.ARDUINO_UNO,    # Arduino Uno
            (0x1A86, 0x7523): DeviceType.ARDUINO_NANO,   # CH340 (common on clones)
            (0x0403, 0x6001): DeviceType.ARDUINO_NANO,   # FTDI (Arduino Nano)
            (0x2341, 0x0042): DeviceType.ARDUINO_MEGA,   # Arduino Mega 2560
            (0x10C4, 0xEA60): DeviceType.ESP32,          # CP2102 (ESP32)
            (0x1A86, 0x7523): DeviceType.ESP8266,        # CH340 (NodeMCU)
        }
        
        if vid and pid and (vid, pid) in device_mappings:
            return device_mappings[(vid, pid)]
        
        # Fallback to description-based detection
        description = port.description.lower()
        if "arduino" in description:
            if "uno" in description:
                return DeviceType.ARDUINO_UNO
            elif "nano" in description:
                return DeviceType.ARDUINO_NANO
            elif "mega" in description:
                return DeviceType.ARDUINO_MEGA
        elif "esp32" in description:
            return DeviceType.ESP32
        elif "esp8266" in description or "nodemcu" in description:
            return DeviceType.ESP8266
        
        return None
    
    async def connect_to_port(
        self,
        port: str,
        baud_rate: int = 115200,
        device_id: Optional[uuid.UUID] = None
    ) -> uuid.UUID:
        """Connect to a serial port"""
        
        try:
            # Create serial connection
            ser = serial.Serial(port, baud_rate, timeout=1)
            self.active_connections[port] = ser
            
            # Store connection in database
            connection = SerialConnection(
                port=port,
                baud_rate=baud_rate,
                is_connected=True,
                last_activity=datetime.utcnow(),
                device_id=device_id
            )
            
            self.session.add(connection)
            await self.session.commit()
            await self.session.refresh(connection)
            
            return connection.id
            
        except serial.SerialException as e:
            raise Exception(f"Failed to connect to {port}: {str(e)}")
    
    async def disconnect_from_port(self, port: str):
        """Disconnect from a serial port"""
        
        if port in self.active_connections:
            self.active_connections[port].close()
            del self.active_connections[port]
            
            # Update database
            await self.session.execute(
                update(SerialConnection)
                .where(SerialConnection.port == port)
                .values(is_connected=False)
            )
            await self.session.commit()
    
    async def read_serial_data(self, port: str, timeout: float = 1.0) -> Optional[str]:
        """Read data from serial port"""
        
        if port not in self.active_connections:
            raise Exception(f"Not connected to port {port}")
        
        ser = self.active_connections[port]
        
        try:
            ser.timeout = timeout
            data = ser.readline().decode('utf-8').strip()
            
            if data:
                # Update last activity
                await self.session.execute(
                    update(SerialConnection)
                    .where(SerialConnection.port == port)
                    .values(last_activity=datetime.utcnow())
                )
                await self.session.commit()
            
            return data if data else None
            
        except Exception as e:
            print(f"Error reading from {port}: {str(e)}")
            return None
    
    async def write_serial_data(self, port: str, data: str) -> bool:
        """Write data to serial port"""
        
        if port not in self.active_connections:
            raise Exception(f"Not connected to port {port}")
        
        ser = self.active_connections[port]
        
        try:
            ser.write(data.encode('utf-8'))
            ser.flush()
            
            # Update last activity
            await self.session.execute(
                update(SerialConnection)
                .where(SerialConnection.port == port)
                .values(last_activity=datetime.utcnow())
            )
            await self.session.commit()
            
            return True
            
        except Exception as e:
            print(f"Error writing to {port}: {str(e)}")
            return False
    
    async def compile_and_upload_code(
        self,
        generation_id: uuid.UUID,
        port: str,
        device_type: DeviceType
    ) -> bool:
        """Compile and upload Arduino code to device"""
        
        if not self.arduino_cli_path:
            raise Exception("Arduino CLI not found. Please install Arduino CLI.")
        
        # Get code generation record
        result = await self.session.execute(
            select(CodeGeneration).where(CodeGeneration.id == generation_id)
        )
        code_gen = result.scalar_one_or_none()
        
        if not code_gen or not code_gen.generated_code:
            raise Exception("Code generation not found or incomplete")
        
        # Update status to compiling
        await self.session.execute(
            update(CodeGeneration)
            .where(CodeGeneration.id == generation_id)
            .values(status=CodeGenerationStatus.COMPILING)
        )
        await self.session.commit()
        
        try:
            # Create temporary directory for Arduino sketch
            with tempfile.TemporaryDirectory() as temp_dir:
                sketch_dir = Path(temp_dir) / "sketch"
                sketch_dir.mkdir()
                
                # Write Arduino code to .ino file
                sketch_file = sketch_dir / "sketch.ino"
                sketch_file.write_text(code_gen.generated_code)
                
                # Get platform configuration
                config = self.platform_configs.get(device_type)
                if not config:
                    raise Exception(f"Unsupported device type: {device_type}")
                
                # Install platform if needed
                await self._ensure_platform_installed(config["platform"])
                
                # Compile the sketch
                compile_success, compile_output = await self._compile_sketch(
                    str(sketch_file), config
                )
                
                if not compile_success:
                    await self.session.execute(
                        update(CodeGeneration)
                        .where(CodeGeneration.id == generation_id)
                        .values(
                            status=CodeGenerationStatus.FAILED,
                            compilation_output=compile_output
                        )
                    )
                    await self.session.commit()
                    return False
                
                # Update status to uploading
                await self.session.execute(
                    update(CodeGeneration)
                    .where(CodeGeneration.id == generation_id)
                    .values(
                        status=CodeGenerationStatus.UPLOADING,
                        compilation_output=compile_output
                    )
                )
                await self.session.commit()
                
                # Upload to device
                upload_success, upload_output = await self._upload_sketch(
                    str(sketch_file), port, config
                )
                
                # Update final status
                final_status = (CodeGenerationStatus.COMPLETED if upload_success 
                              else CodeGenerationStatus.FAILED)
                
                await self.session.execute(
                    update(CodeGeneration)
                    .where(CodeGeneration.id == generation_id)
                    .values(
                        status=final_status,
                        upload_output=upload_output
                    )
                )
                await self.session.commit()
                
                return upload_success
                
        except Exception as e:
            await self.session.execute(
                update(CodeGeneration)
                .where(CodeGeneration.id == generation_id)
                .values(
                    status=CodeGenerationStatus.FAILED,
                    error_message=str(e)
                )
            )
            await self.session.commit()
            raise
    
    async def _ensure_platform_installed(self, platform: str) -> bool:
        """Ensure Arduino platform is installed"""
        
        try:
            # Check if platform is installed
            result = subprocess.run([
                self.arduino_cli_path, "core", "list"
            ], capture_output=True, text=True, timeout=30)
            
            if platform in result.stdout:
                return True
            
            # Install platform
            print(f"Installing platform {platform}...")
            result = subprocess.run([
                self.arduino_cli_path, "core", "install", platform
            ], capture_output=True, text=True, timeout=300)
            
            return result.returncode == 0
            
        except Exception as e:
            print(f"Error installing platform {platform}: {str(e)}")
            return False
    
    async def _compile_sketch(
        self,
        sketch_path: str,
        config: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """Compile Arduino sketch"""
        
        try:
            result = subprocess.run([
                self.arduino_cli_path, "compile",
                "--fqbn", config["board"],
                sketch_path
            ], capture_output=True, text=True, timeout=120)
            
            output = f"STDOUT:\\n{result.stdout}\\nSTDERR:\\n{result.stderr}"
            return result.returncode == 0, output
            
        except Exception as e:
            return False, f"Compilation error: {str(e)}"
    
    async def _upload_sketch(
        self,
        sketch_path: str,
        port: str,
        config: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """Upload compiled sketch to device"""
        
        try:
            # Disconnect serial connection during upload
            if port in self.active_connections:
                await self.disconnect_from_port(port)
                await asyncio.sleep(1)  # Give time for port to close
            
            result = subprocess.run([
                self.arduino_cli_path, "upload",
                "--fqbn", config["board"],
                "--port", port,
                sketch_path
            ], capture_output=True, text=True, timeout=120)
            
            output = f"STDOUT:\\n{result.stdout}\\nSTDERR:\\n{result.stderr}"
            
            # Reconnect serial connection after upload
            await asyncio.sleep(2)  # Wait for device reset
            
            return result.returncode == 0, output
            
        except Exception as e:
            return False, f"Upload error: {str(e)}"
    
    async def monitor_serial_output(
        self,
        port: str,
        duration: int = 60,
        callback: Optional[callable] = None
    ) -> List[str]:
        """Monitor serial output from device"""
        
        if port not in self.active_connections:
            await self.connect_to_port(port)
        
        output_lines = []
        start_time = datetime.utcnow()
        
        while (datetime.utcnow() - start_time).seconds < duration:
            line = await self.read_serial_data(port, timeout=0.1)
            if line:
                output_lines.append(f"[{datetime.utcnow().isoformat()}] {line}")
                if callback:
                    callback(line)
        
        return output_lines
    
    async def send_command_to_device(
        self,
        port: str,
        command: str
    ) -> Optional[str]:
        """Send command to device and read response"""
        
        if port not in self.active_connections:
            raise Exception(f"Not connected to port {port}")
        
        # Send command
        success = await self.write_serial_data(port, command + "\\n")
        if not success:
            return None
        
        # Wait for response
        await asyncio.sleep(0.1)
        response = await self.read_serial_data(port, timeout=2.0)
        
        return response
    
    async def get_device_info(self, port: str) -> Optional[Dict[str, Any]]:
        """Get device information via serial communication"""
        
        # Send info command and collect responses
        responses = []
        
        # Try common info commands
        commands = [
            "info",
            "version",
            "status",
            "whoami"
        ]
        
        for command in commands:
            response = await self.send_command_to_device(port, command)
            if response:
                responses.append({"command": command, "response": response})
        
        if not responses:
            return None
        
        return {
            "port": port,
            "timestamp": datetime.utcnow().isoformat(),
            "responses": responses
        }
    
    async def reset_device(self, port: str) -> bool:
        """Reset device via DTR/RTS signals"""
        
        if port not in self.active_connections:
            raise Exception(f"Not connected to port {port}")
        
        try:
            ser = self.active_connections[port]
            
            # Toggle DTR and RTS to reset most Arduino-compatible devices
            ser.dtr = False
            ser.rts = False
            await asyncio.sleep(0.1)
            
            ser.dtr = True
            ser.rts = True
            await asyncio.sleep(0.1)
            
            ser.dtr = False
            ser.rts = False
            
            # Wait for device to boot
            await asyncio.sleep(2)
            
            return True
            
        except Exception as e:
            print(f"Error resetting device on {port}: {str(e)}")
            return False
    
    async def flash_firmware(
        self,
        port: str,
        device_type: DeviceType,
        firmware_path: str
    ) -> bool:
        """Flash firmware binary to device"""
        
        config = self.platform_configs.get(device_type)
        if not config:
            raise Exception(f"Unsupported device type: {device_type}")
        
        try:
            # Disconnect during flashing
            if port in self.active_connections:
                await self.disconnect_from_port(port)
                await asyncio.sleep(1)
            
            # Use appropriate flashing tool based on device type
            if device_type in [DeviceType.ESP32, DeviceType.ESP8266]:
                # Use esptool for ESP devices
                result = subprocess.run([
                    "esptool.py", "--port", port, "--baud", "921600",
                    "write_flash", "0x10000", firmware_path
                ], capture_output=True, text=True, timeout=120)
            else:
                # Use avrdude for Arduino devices
                result = subprocess.run([
                    "avrdude", "-p", "m328p", "-c", config["programmer"],
                    "-P", port, "-b", str(config["upload_speed"]),
                    "-U", f"flash:w:{firmware_path}:i"
                ], capture_output=True, text=True, timeout=120)
            
            return result.returncode == 0
            
        except Exception as e:
            print(f"Error flashing firmware: {str(e)}")
            return False
    
    async def cleanup_connections(self):
        """Clean up all active serial connections"""
        
        for port in list(self.active_connections.keys()):
            await self.disconnect_from_port(port)