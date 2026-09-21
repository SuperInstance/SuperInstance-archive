import json
import time
import random
import threading
from typing import Dict, List, Any, Optional
from enum import Enum
from dataclasses import dataclass, asdict
import uuid
from datetime import datetime

class DeviceType(Enum):
    SENSOR = "sensor"
    ACTUATOR = "actuator" 
    CONTROLLER = "controller"
    DISPLAY = "display"
    STORAGE = "storage"
    NETWORK = "network"
    POWER = "power"
    AUDIO = "audio"
    VIDEO = "video"
    CUSTOM = "custom"

class Protocol(Enum):
    I2C = "i2c"
    SPI = "spi"
    UART = "uart"
    USB = "usb"
    ETHERNET = "ethernet"
    WIFI = "wifi"
    BLUETOOTH = "bluetooth"
    CAN = "can"
    MODBUS = "modbus"
    MQTT = "mqtt"
    HTTP = "http"
    CUSTOM = "custom"

@dataclass
class DeviceConfig:
    device_id: str
    name: str
    device_type: DeviceType
    protocol: Protocol
    address: str
    properties: Dict[str, Any]
    update_rate: float = 1.0
    failure_rate: float = 0.001
    latency_ms: float = 1.0

@dataclass
class DeviceState:
    device_id: str
    timestamp: datetime
    data: Dict[str, Any]
    status: str = "online"
    last_command: Optional[str] = None
    response_time_ms: float = 0.0

class VirtualDevice:
    def __init__(self, config: DeviceConfig):
        self.config = config
        self.state = DeviceState(
            device_id=config.device_id,
            timestamp=datetime.now(),
            data={}
        )
        self.is_running = False
        self.thread = None
        self.callbacks = []
        self.command_history = []
        
    def start(self):
        if not self.is_running:
            self.is_running = True
            self.thread = threading.Thread(target=self._run_loop)
            self.thread.daemon = True
            self.thread.start()
    
    def stop(self):
        self.is_running = False
        if self.thread:
            self.thread.join()
    
    def _run_loop(self):
        while self.is_running:
            self._update_state()
            time.sleep(1.0 / self.config.update_rate)
    
    def _update_state(self):
        self.state.timestamp = datetime.now()
        
        if random.random() < self.config.failure_rate:
            self.state.status = "error"
            self.state.data["error"] = "Simulated device failure"
        else:
            self.state.status = "online"
            if "error" in self.state.data:
                del self.state.data["error"]
        
        self._simulate_data()
        self._notify_callbacks()
    
    def _simulate_data(self):
        device_type = self.config.device_type
        
        if device_type == DeviceType.SENSOR:
            self._simulate_sensor_data()
        elif device_type == DeviceType.ACTUATOR:
            self._simulate_actuator_data()
        elif device_type == DeviceType.CONTROLLER:
            self._simulate_controller_data()
        elif device_type == DeviceType.DISPLAY:
            self._simulate_display_data()
        elif device_type == DeviceType.STORAGE:
            self._simulate_storage_data()
        elif device_type == DeviceType.NETWORK:
            self._simulate_network_data()
        elif device_type == DeviceType.POWER:
            self._simulate_power_data()
        elif device_type == DeviceType.AUDIO:
            self._simulate_audio_data()
        elif device_type == DeviceType.VIDEO:
            self._simulate_video_data()
    
    def _simulate_sensor_data(self):
        sensor_type = self.config.properties.get("sensor_type", "temperature")
        
        if sensor_type == "temperature":
            base_temp = self.config.properties.get("base_temperature", 25.0)
            self.state.data["temperature"] = base_temp + random.uniform(-5, 5)
            self.state.data["units"] = "celsius"
        elif sensor_type == "humidity":
            self.state.data["humidity"] = random.uniform(30, 80)
            self.state.data["units"] = "percent"
        elif sensor_type == "pressure":
            self.state.data["pressure"] = 1013.25 + random.uniform(-50, 50)
            self.state.data["units"] = "hPa"
        elif sensor_type == "accelerometer":
            self.state.data["x"] = random.uniform(-2, 2)
            self.state.data["y"] = random.uniform(-2, 2)
            self.state.data["z"] = random.uniform(8, 12)
            self.state.data["units"] = "m/s²"
        elif sensor_type == "gyroscope":
            self.state.data["roll"] = random.uniform(-180, 180)
            self.state.data["pitch"] = random.uniform(-90, 90)
            self.state.data["yaw"] = random.uniform(-180, 180)
            self.state.data["units"] = "degrees"
    
    def _simulate_actuator_data(self):
        actuator_type = self.config.properties.get("actuator_type", "motor")
        
        if actuator_type == "motor":
            self.state.data["speed"] = self.config.properties.get("current_speed", 0)
            self.state.data["position"] = self.state.data.get("position", 0) + self.state.data["speed"] * 0.1
            self.state.data["current"] = abs(self.state.data["speed"]) * 0.1 + random.uniform(-0.01, 0.01)
        elif actuator_type == "servo":
            self.state.data["angle"] = self.config.properties.get("target_angle", 90)
            self.state.data["torque"] = random.uniform(0.8, 1.2)
        elif actuator_type == "led":
            self.state.data["brightness"] = self.config.properties.get("brightness", 50)
            self.state.data["color"] = self.config.properties.get("color", "#FFFFFF")
            self.state.data["power_consumption"] = self.state.data["brightness"] * 0.02
    
    def _simulate_controller_data(self):
        self.state.data["cpu_usage"] = random.uniform(10, 90)
        self.state.data["memory_usage"] = random.uniform(20, 80)
        self.state.data["temperature"] = random.uniform(35, 75)
        self.state.data["uptime"] = time.time() - self.config.properties.get("start_time", time.time())
    
    def _simulate_display_data(self):
        self.state.data["resolution"] = self.config.properties.get("resolution", "1920x1080")
        self.state.data["refresh_rate"] = self.config.properties.get("refresh_rate", 60)
        self.state.data["brightness"] = self.config.properties.get("brightness", 50)
        self.state.data["power_consumption"] = self.state.data["brightness"] * 0.5
    
    def _simulate_storage_data(self):
        capacity = self.config.properties.get("capacity_gb", 1000)
        used = self.state.data.get("used_gb", capacity * 0.3)
        self.state.data["capacity_gb"] = capacity
        self.state.data["used_gb"] = used + random.uniform(-0.1, 0.5)
        self.state.data["free_gb"] = capacity - self.state.data["used_gb"]
        self.state.data["usage_percent"] = (self.state.data["used_gb"] / capacity) * 100
    
    def _simulate_network_data(self):
        self.state.data["bandwidth_mbps"] = self.config.properties.get("bandwidth", 100)
        self.state.data["current_usage_mbps"] = random.uniform(1, 20)
        self.state.data["packets_sent"] = self.state.data.get("packets_sent", 0) + random.randint(10, 100)
        self.state.data["packets_received"] = self.state.data.get("packets_received", 0) + random.randint(10, 100)
        self.state.data["latency_ms"] = random.uniform(1, 50)
    
    def _simulate_power_data(self):
        self.state.data["voltage"] = self.config.properties.get("voltage", 12.0) + random.uniform(-0.5, 0.5)
        self.state.data["current"] = random.uniform(0.5, 5.0)
        self.state.data["power"] = self.state.data["voltage"] * self.state.data["current"]
        self.state.data["battery_level"] = max(0, self.state.data.get("battery_level", 100) - random.uniform(0, 0.1))
    
    def _simulate_audio_data(self):
        self.state.data["volume"] = self.config.properties.get("volume", 50)
        self.state.data["frequency_hz"] = random.uniform(20, 20000)
        self.state.data["amplitude"] = random.uniform(0, 1)
        self.state.data["channels"] = self.config.properties.get("channels", 2)
    
    def _simulate_video_data(self):
        self.state.data["resolution"] = self.config.properties.get("resolution", "1080p")
        self.state.data["fps"] = self.config.properties.get("fps", 30)
        self.state.data["bitrate"] = random.uniform(1000, 5000)
        self.state.data["frame_count"] = self.state.data.get("frame_count", 0) + self.state.data["fps"]
    
    def send_command(self, command: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        start_time = time.time()
        
        if random.random() < self.config.failure_rate * 10:
            response = {
                "status": "error",
                "message": "Command failed - simulated error",
                "timestamp": datetime.now().isoformat()
            }
        else:
            response = self._process_command(command, params or {})
        
        response_time = (time.time() - start_time) * 1000
        self.state.response_time_ms = response_time + random.uniform(0, self.config.latency_ms)
        self.state.last_command = command
        
        self.command_history.append({
            "command": command,
            "params": params,
            "response": response,
            "timestamp": datetime.now().isoformat(),
            "response_time_ms": self.state.response_time_ms
        })
        
        return response
    
    def _process_command(self, command: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if command == "get_status":
            return {
                "status": "success",
                "data": asdict(self.state),
                "timestamp": datetime.now().isoformat()
            }
        elif command == "set_property":
            prop_name = params.get("property")
            prop_value = params.get("value")
            if prop_name:
                self.config.properties[prop_name] = prop_value
                return {
                    "status": "success",
                    "message": f"Property {prop_name} set to {prop_value}",
                    "timestamp": datetime.now().isoformat()
                }
        elif command == "reset":
            self.state.data = {}
            return {
                "status": "success",
                "message": "Device reset successfully",
                "timestamp": datetime.now().isoformat()
            }
        elif command == "calibrate":
            return {
                "status": "success",
                "message": "Device calibration completed",
                "calibration_data": {"offset": random.uniform(-0.1, 0.1)},
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "status": "error",
                "message": f"Unknown command: {command}",
                "timestamp": datetime.now().isoformat()
            }
    
    def add_callback(self, callback):
        self.callbacks.append(callback)
    
    def remove_callback(self, callback):
        if callback in self.callbacks:
            self.callbacks.remove(callback)
    
    def _notify_callbacks(self):
        for callback in self.callbacks:
            try:
                callback(self.state)
            except Exception as e:
                print(f"Callback error: {e}")
    
    def get_history(self, limit: int = 100) -> List[Dict]:
        return self.command_history[-limit:]
    
    def inject_failure(self, failure_type: str, duration: float = 5.0):
        def restore_normal():
            time.sleep(duration)
            self.state.status = "online"
            if "error" in self.state.data:
                del self.state.data["error"]
        
        self.state.status = "error"
        self.state.data["error"] = f"Injected failure: {failure_type}"
        
        restore_thread = threading.Thread(target=restore_normal)
        restore_thread.daemon = True
        restore_thread.start()

class VirtualDeviceManager:
    def __init__(self):
        self.devices: Dict[str, VirtualDevice] = {}
        self.device_configs: Dict[str, DeviceConfig] = {}
    
    def create_device(self, config: DeviceConfig) -> VirtualDevice:
        device = VirtualDevice(config)
        self.devices[config.device_id] = device
        self.device_configs[config.device_id] = config
        return device
    
    def remove_device(self, device_id: str):
        if device_id in self.devices:
            self.devices[device_id].stop()
            del self.devices[device_id]
            del self.device_configs[device_id]
    
    def get_device(self, device_id: str) -> Optional[VirtualDevice]:
        return self.devices.get(device_id)
    
    def list_devices(self) -> List[str]:
        return list(self.devices.keys())
    
    def start_all(self):
        for device in self.devices.values():
            device.start()
    
    def stop_all(self):
        for device in self.devices.values():
            device.stop()
    
    def create_preset_device(self, preset: str, device_id: str = None) -> VirtualDevice:
        if not device_id:
            device_id = f"{preset}_{uuid.uuid4().hex[:8]}"
        
        presets = {
            "temperature_sensor": DeviceConfig(
                device_id=device_id,
                name="Temperature Sensor",
                device_type=DeviceType.SENSOR,
                protocol=Protocol.I2C,
                address="0x48",
                properties={"sensor_type": "temperature", "base_temperature": 22.5},
                update_rate=2.0
            ),
            "servo_motor": DeviceConfig(
                device_id=device_id,
                name="Servo Motor",
                device_type=DeviceType.ACTUATOR,
                protocol=Protocol.SPI,
                address="0x01",
                properties={"actuator_type": "servo", "target_angle": 90},
                update_rate=10.0
            ),
            "rgb_led": DeviceConfig(
                device_id=device_id,
                name="RGB LED Strip",
                device_type=DeviceType.ACTUATOR,
                protocol=Protocol.UART,
                address="/dev/ttyUSB0",
                properties={"actuator_type": "led", "brightness": 75, "color": "#FF0000"},
                update_rate=5.0
            ),
            "accelerometer": DeviceConfig(
                device_id=device_id,
                name="3-Axis Accelerometer",
                device_type=DeviceType.SENSOR,
                protocol=Protocol.I2C,
                address="0x1D",
                properties={"sensor_type": "accelerometer"},
                update_rate=50.0
            ),
            "display": DeviceConfig(
                device_id=device_id,
                name="OLED Display",
                device_type=DeviceType.DISPLAY,
                protocol=Protocol.SPI,
                address="0x00",
                properties={"resolution": "128x64", "refresh_rate": 60, "brightness": 80},
                update_rate=1.0
            )
        }
        
        if preset not in presets:
            raise ValueError(f"Unknown preset: {preset}")
        
        return self.create_device(presets[preset])
    
    def export_configuration(self, filename: str):
        config_data = {
            "devices": [asdict(config) for config in self.device_configs.values()]
        }
        with open(filename, 'w') as f:
            json.dump(config_data, f, indent=2)
    
    def import_configuration(self, filename: str):
        with open(filename, 'r') as f:
            config_data = json.load(f)
        
        for device_data in config_data['devices']:
            device_data['device_type'] = DeviceType(device_data['device_type'])
            device_data['protocol'] = Protocol(device_data['protocol'])
            config = DeviceConfig(**device_data)
            self.create_device(config)

def create_demo_environment():
    manager = VirtualDeviceManager()
    
    devices = [
        manager.create_preset_device("temperature_sensor", "temp_01"),
        manager.create_preset_device("servo_motor", "servo_01"),
        manager.create_preset_device("rgb_led", "led_01"),
        manager.create_preset_device("accelerometer", "accel_01"),
        manager.create_preset_device("display", "display_01")
    ]
    
    return manager, devices

if __name__ == "__main__":
    print("Creating demo virtual device environment...")
    manager, devices = create_demo_environment()
    
    manager.start_all()
    
    print(f"Started {len(devices)} virtual devices:")
    for device in devices:
        print(f"  - {device.config.name} ({device.config.device_id})")
    
    try:
        time.sleep(5)
        
        for device in devices:
            print(f"\n{device.config.name} status:")
            response = device.send_command("get_status")
            print(f"  Data: {response['data']['data']}")
        
        print("\nTesting command execution...")
        led_device = manager.get_device("led_01")
        response = led_device.send_command("set_property", {"property": "brightness", "value": 100})
        print(f"LED brightness command result: {response}")
        
        print("\nInjecting failure into temperature sensor...")
        temp_device = manager.get_device("temp_01")
        temp_device.inject_failure("sensor_disconnected", 3.0)
        
        time.sleep(2)
        
    finally:
        print("\nStopping all devices...")
        manager.stop_all()
        print("Demo completed.")