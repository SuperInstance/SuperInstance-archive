#!/usr/bin/env python3
"""
ActiveLog Edge Agent for Raspberry Pi
Handles device management, data collection, and sync operations
"""

import asyncio
import json
import logging
import os
import signal
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import psutil
import requests
from cryptography.fernet import Fernet
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

# Add the virtual environment to Python path
venv_path = Path.home() / "activelog-venv" / "lib" / "python3.11" / "site-packages"
if venv_path.exists():
    sys.path.insert(0, str(venv_path))

try:
    import paho.mqtt.client as mqtt
    import websockets
    from picamera2 import Picamera2
    from RPi import GPIO
except ImportError as e:
    print(f"Warning: Some optional dependencies not available: {e}")

class EdgeAgent:
    def __init__(self, config_path: str = "/etc/activelog/edge.conf"):
        self.config_path = config_path
        self.config = self.load_config()
        self.device_id = self.config.get("device", {}).get("id")
        self.running = False
        self.tasks = []
        
        # Initialize logging
        self.setup_logging()
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.sync_queue = []
        self.camera = None
        self.mqtt_client = None
        self.websocket = None
        self.encryption_key = self.load_or_generate_key()
        
        # File watcher
        self.file_observer = None
        
        # System stats
        self.last_stats_time = 0
        
        self.logger.info(f"EdgeAgent initialized for device {self.device_id}")

    def load_config(self) -> Dict:
        """Load configuration from file"""
        try:
            with open(self.config_path, 'r') as f:
                config = {}
                current_section = None
                
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    if line.startswith('[') and line.endswith(']'):
                        current_section = line[1:-1]
                        config[current_section] = {}
                    elif '=' in line and current_section:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        
                        # Convert boolean and numeric values
                        if value.lower() in ('true', 'false'):
                            value = value.lower() == 'true'
                        elif value.isdigit():
                            value = int(value)
                        elif value.replace('.', '').isdigit():
                            value = float(value)
                        
                        config[current_section][key] = value
                
                return config
        except Exception as e:
            print(f"Error loading config: {e}")
            return {}

    def setup_logging(self):
        """Setup logging configuration"""
        log_config = self.config.get("logging", {})
        log_level = getattr(logging, log_config.get("level", "INFO"))
        log_file = log_config.get("file_path", "/var/log/activelog/edge.log")
        
        # Create log directory if it doesn't exist
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )

    def load_or_generate_key(self) -> Fernet:
        """Load or generate encryption key"""
        key_file = "/etc/activelog/encryption.key"
        
        try:
            with open(key_file, 'rb') as f:
                key = f.read()
        except FileNotFoundError:
            key = Fernet.generate_key()
            os.makedirs(os.path.dirname(key_file), exist_ok=True)
            with open(key_file, 'wb') as f:
                f.write(key)
            os.chmod(key_file, 0o600)
        
        return Fernet(key)

    async def start(self):
        """Start the edge agent"""
        self.logger.info("Starting ActiveLog Edge Agent")
        self.running = True
        
        try:
            # Start components
            await self.start_mqtt_client()
            await self.start_websocket_client()
            await self.start_camera()
            await self.start_file_watcher()
            
            # Start background tasks
            self.tasks = [
                asyncio.create_task(self.system_monitor_loop()),
                asyncio.create_task(self.sync_loop()),
                asyncio.create_task(self.health_check_loop()),
                asyncio.create_task(self.cleanup_loop())
            ]
            
            self.logger.info("Edge agent started successfully")
            
            # Wait for shutdown signal
            await self.wait_for_shutdown()
            
        except Exception as e:
            self.logger.error(f"Error starting edge agent: {e}")
        finally:
            await self.stop()

    async def stop(self):
        """Stop the edge agent"""
        self.logger.info("Stopping ActiveLog Edge Agent")
        self.running = False
        
        # Cancel background tasks
        for task in self.tasks:
            task.cancel()
        
        # Stop components
        if self.camera:
            try:
                self.camera.stop()
            except:
                pass
        
        if self.mqtt_client:
            self.mqtt_client.disconnect()
        
        if self.file_observer:
            self.file_observer.stop()
            self.file_observer.join()
        
        self.logger.info("Edge agent stopped")

    async def start_mqtt_client(self):
        """Initialize MQTT client"""
        try:
            self.mqtt_client = mqtt.Client()
            self.mqtt_client.on_connect = self.on_mqtt_connect
            self.mqtt_client.on_message = self.on_mqtt_message
            
            # Configure TLS if enabled
            security_config = self.config.get("security", {})
            if security_config.get("enable_encryption"):
                cert_path = security_config.get("certificate_path")
                key_path = security_config.get("private_key_path")
                if cert_path and key_path:
                    self.mqtt_client.tls_set(cert_path, key_path)
            
            # Connect to MQTT broker
            sync_config = self.config.get("sync", {})
            server_url = sync_config.get("server_url", "mqtt.activelog.ai")
            
            self.mqtt_client.connect(server_url, 8883, 60)
            self.mqtt_client.loop_start()
            
            self.logger.info("MQTT client connected")
        except Exception as e:
            self.logger.error(f"Failed to start MQTT client: {e}")

    def on_mqtt_connect(self, client, userdata, flags, rc):
        """MQTT connection callback"""
        if rc == 0:
            self.logger.info("Connected to MQTT broker")
            # Subscribe to device-specific topics
            client.subscribe(f"activelog/device/{self.device_id}/commands")
            client.subscribe(f"activelog/device/{self.device_id}/config")
        else:
            self.logger.error(f"MQTT connection failed with code {rc}")

    def on_mqtt_message(self, client, userdata, msg):
        """MQTT message callback"""
        try:
            topic = msg.topic
            payload = json.loads(msg.payload.decode())
            
            self.logger.info(f"Received MQTT message on {topic}: {payload}")
            
            if "commands" in topic:
                asyncio.create_task(self.handle_command(payload))
            elif "config" in topic:
                asyncio.create_task(self.handle_config_update(payload))
                
        except Exception as e:
            self.logger.error(f"Error handling MQTT message: {e}")

    async def start_websocket_client(self):
        """Initialize WebSocket client for real-time communication"""
        try:
            sync_config = self.config.get("sync", {})
            server_url = sync_config.get("server_url", "wss://ws.activelog.ai")
            ws_url = f"{server_url}/edge/{self.device_id}"
            
            asyncio.create_task(self.websocket_loop(ws_url))
            self.logger.info("WebSocket client initialized")
        except Exception as e:
            self.logger.error(f"Failed to start WebSocket client: {e}")

    async def websocket_loop(self, url):
        """WebSocket connection loop with reconnection"""
        while self.running:
            try:
                async with websockets.connect(url) as websocket:
                    self.websocket = websocket
                    self.logger.info("WebSocket connected")
                    
                    async for message in websocket:
                        data = json.loads(message)
                        await self.handle_websocket_message(data)
                        
            except Exception as e:
                self.logger.error(f"WebSocket error: {e}")
                await asyncio.sleep(5)  # Reconnect delay

    async def handle_websocket_message(self, data):
        """Handle WebSocket messages"""
        message_type = data.get("type")
        
        if message_type == "command":
            await self.handle_command(data.get("payload", {}))
        elif message_type == "sync_request":
            await self.handle_sync_request(data.get("payload", {}))
        elif message_type == "config_update":
            await self.handle_config_update(data.get("payload", {}))

    async def start_camera(self):
        """Initialize camera if available"""
        processing_config = self.config.get("processing", {})
        if not processing_config.get("enable_camera", False):
            return
        
        try:
            self.camera = Picamera2()
            self.camera.configure(self.camera.create_preview_configuration())
            self.camera.start()
            self.logger.info("Camera initialized")
        except Exception as e:
            self.logger.warning(f"Camera initialization failed: {e}")

    async def start_file_watcher(self):
        """Start file system watcher"""
        try:
            watch_path = "/var/lib/activelog/data"
            os.makedirs(watch_path, exist_ok=True)
            
            event_handler = FileEventHandler(self)
            self.file_observer = Observer()
            self.file_observer.schedule(event_handler, watch_path, recursive=True)
            self.file_observer.start()
            
            self.logger.info(f"File watcher started for {watch_path}")
        except Exception as e:
            self.logger.error(f"Failed to start file watcher: {e}")

    async def system_monitor_loop(self):
        """Background system monitoring"""
        while self.running:
            try:
                stats = self.collect_system_stats()
                
                # Send stats if significant change or time interval
                current_time = time.time()
                if (current_time - self.last_stats_time) >= 300:  # 5 minutes
                    await self.queue_for_sync("system_stats", stats)
                    self.last_stats_time = current_time
                
                await asyncio.sleep(60)  # Check every minute
            except Exception as e:
                self.logger.error(f"System monitor error: {e}")
                await asyncio.sleep(60)

    def collect_system_stats(self) -> Dict:
        """Collect system statistics"""
        try:
            # Basic system stats
            stats = {
                "timestamp": datetime.now().isoformat(),
                "device_id": self.device_id,
                "cpu_percent": psutil.cpu_percent(interval=1),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": psutil.disk_usage('/').percent,
                "uptime": time.time() - psutil.boot_time(),
                "load_average": os.getloadavg(),
            }
            
            # Temperature (Raspberry Pi specific)
            try:
                with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                    temp = float(f.read()) / 1000.0
                    stats["cpu_temperature"] = temp
            except:
                pass
            
            # Network interfaces
            net_stats = psutil.net_io_counters(pernic=True)
            stats["network"] = {
                interface: {
                    "bytes_sent": stat.bytes_sent,
                    "bytes_recv": stat.bytes_recv
                }
                for interface, stat in net_stats.items()
                if interface in ['eth0', 'wlan0']
            }
            
            return stats
        except Exception as e:
            self.logger.error(f"Error collecting system stats: {e}")
            return {}

    async def sync_loop(self):
        """Background sync loop"""
        while self.running:
            try:
                if self.sync_queue:
                    await self.process_sync_queue()
                
                sync_config = self.config.get("sync", {})
                interval = sync_config.get("sync_interval", 300)
                await asyncio.sleep(interval)
            except Exception as e:
                self.logger.error(f"Sync loop error: {e}")
                await asyncio.sleep(60)

    async def queue_for_sync(self, data_type: str, data: Dict, priority: int = 5):
        """Add data to sync queue"""
        sync_item = {
            "id": f"{int(time.time())}_{len(self.sync_queue)}",
            "timestamp": datetime.now().isoformat(),
            "device_id": self.device_id,
            "type": data_type,
            "data": data,
            "priority": priority,
            "retries": 0
        }
        
        # Encrypt sensitive data
        if self.config.get("security", {}).get("enable_encryption"):
            sync_item["data"] = self.encryption_key.encrypt(
                json.dumps(data).encode()
            ).decode()
            sync_item["encrypted"] = True
        
        self.sync_queue.append(sync_item)
        
        # Limit queue size
        max_size = self.config.get("sync", {}).get("offline_queue_size", 1000)
        if len(self.sync_queue) > max_size:
            self.sync_queue.pop(0)  # Remove oldest item

    async def process_sync_queue(self):
        """Process pending sync items"""
        if not self.sync_queue:
            return
        
        sync_config = self.config.get("sync", {})
        server_url = sync_config.get("server_url", "https://api.activelog.ai")
        
        # Sort by priority (lower number = higher priority)
        self.sync_queue.sort(key=lambda x: x["priority"])
        
        # Process items in batches
        batch_size = 10
        batch = self.sync_queue[:batch_size]
        
        try:
            response = await self.send_sync_batch(server_url, batch)
            
            if response and response.status_code == 200:
                # Remove successfully synced items
                self.sync_queue = self.sync_queue[batch_size:]
                self.logger.info(f"Synced {len(batch)} items")
            else:
                # Increment retry count for failed items
                for item in batch:
                    item["retries"] += 1
                    if item["retries"] > 3:
                        self.sync_queue.remove(item)
                        self.logger.warning(f"Dropping sync item after 3 retries: {item['id']}")
                
        except Exception as e:
            self.logger.error(f"Sync error: {e}")

    async def send_sync_batch(self, server_url: str, batch: List[Dict]):
        """Send sync batch to server"""
        try:
            headers = {
                "Content-Type": "application/json",
                "X-Device-ID": self.device_id
            }
            
            # Add authentication if available
            auth_token = self.get_auth_token()
            if auth_token:
                headers["Authorization"] = f"Bearer {auth_token}"
            
            response = requests.post(
                f"{server_url}/api/edge/sync",
                json={"items": batch},
                headers=headers,
                timeout=30
            )
            
            return response
            
        except Exception as e:
            self.logger.error(f"Failed to send sync batch: {e}")
            return None

    def get_auth_token(self) -> Optional[str]:
        """Get authentication token"""
        # Implementation would depend on auth method
        # For now, return None (anonymous)
        return None

    async def health_check_loop(self):
        """Background health monitoring"""
        while self.running:
            try:
                health_status = self.get_health_status()
                
                # Send health status if there are issues
                if health_status["status"] != "healthy":
                    await self.queue_for_sync("health_status", health_status, priority=1)
                
                await asyncio.sleep(120)  # Check every 2 minutes
            except Exception as e:
                self.logger.error(f"Health check error: {e}")
                await asyncio.sleep(120)

    def get_health_status(self) -> Dict:
        """Get device health status"""
        status = {
            "timestamp": datetime.now().isoformat(),
            "device_id": self.device_id,
            "status": "healthy",
            "issues": []
        }
        
        # Check CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        if cpu_percent > 90:
            status["issues"].append(f"High CPU usage: {cpu_percent}%")
            status["status"] = "warning"
        
        # Check memory usage
        memory_percent = psutil.virtual_memory().percent
        if memory_percent > 90:
            status["issues"].append(f"High memory usage: {memory_percent}%")
            status["status"] = "warning"
        
        # Check disk space
        disk_percent = psutil.disk_usage('/').percent
        if disk_percent > 95:
            status["issues"].append(f"Low disk space: {disk_percent}% used")
            status["status"] = "critical"
        elif disk_percent > 85:
            status["issues"].append(f"High disk usage: {disk_percent}%")
            status["status"] = "warning"
        
        # Check temperature
        try:
            with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                temp = float(f.read()) / 1000.0
                if temp > 80:
                    status["issues"].append(f"High temperature: {temp}°C")
                    status["status"] = "critical"
                elif temp > 70:
                    status["issues"].append(f"Elevated temperature: {temp}°C")
                    if status["status"] == "healthy":
                        status["status"] = "warning"
        except:
            pass
        
        return status

    async def cleanup_loop(self):
        """Background cleanup tasks"""
        while self.running:
            try:
                # Clean old log files
                await self.cleanup_logs()
                
                # Clean old data files
                await self.cleanup_data()
                
                # Sleep for 1 hour
                await asyncio.sleep(3600)
            except Exception as e:
                self.logger.error(f"Cleanup error: {e}")
                await asyncio.sleep(3600)

    async def cleanup_logs(self):
        """Clean up old log files"""
        log_dir = Path("/var/log/activelog")
        if not log_dir.exists():
            return
        
        # Keep logs for 30 days
        cutoff_time = time.time() - (30 * 24 * 60 * 60)
        
        for log_file in log_dir.glob("*.log.*"):
            if log_file.stat().st_mtime < cutoff_time:
                log_file.unlink()
                self.logger.info(f"Deleted old log file: {log_file}")

    async def cleanup_data(self):
        """Clean up old data files"""
        data_dir = Path("/var/lib/activelog/data")
        if not data_dir.exists():
            return
        
        # Clean based on available disk space
        disk_usage = psutil.disk_usage(str(data_dir))
        free_percent = (disk_usage.free / disk_usage.total) * 100
        
        if free_percent < 10:  # Less than 10% free space
            # Remove oldest files until we have 20% free space
            files = list(data_dir.glob("**/*"))
            files.sort(key=lambda f: f.stat().st_mtime)
            
            target_free = 0.2 * disk_usage.total
            bytes_to_free = target_free - disk_usage.free
            bytes_freed = 0
            
            for file_path in files:
                if file_path.is_file() and bytes_freed < bytes_to_free:
                    file_size = file_path.stat().st_size
                    file_path.unlink()
                    bytes_freed += file_size
                    self.logger.info(f"Deleted data file: {file_path}")

    async def handle_command(self, command: Dict):
        """Handle incoming commands"""
        cmd_type = command.get("type")
        
        if cmd_type == "capture_image":
            await self.capture_image(command.get("params", {}))
        elif cmd_type == "restart":
            await self.restart_agent()
        elif cmd_type == "update_config":
            await self.update_config(command.get("params", {}))
        elif cmd_type == "sync_now":
            await self.process_sync_queue()
        else:
            self.logger.warning(f"Unknown command type: {cmd_type}")

    async def capture_image(self, params: Dict):
        """Capture image with camera"""
        if not self.camera:
            self.logger.error("Camera not available")
            return
        
        try:
            filename = params.get("filename", f"capture_{int(time.time())}.jpg")
            output_path = f"/var/lib/activelog/data/images/{filename}"
            
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            self.camera.capture_file(output_path)
            
            # Queue image for sync
            await self.queue_for_sync("image_capture", {
                "filename": filename,
                "path": output_path,
                "timestamp": datetime.now().isoformat(),
                "params": params
            })
            
            self.logger.info(f"Image captured: {output_path}")
            
        except Exception as e:
            self.logger.error(f"Image capture failed: {e}")

    async def handle_config_update(self, config_update: Dict):
        """Handle configuration updates"""
        try:
            # Update configuration
            for section, values in config_update.items():
                if section not in self.config:
                    self.config[section] = {}
                self.config[section].update(values)
            
            # Save updated configuration
            self.save_config()
            
            self.logger.info("Configuration updated")
            
        except Exception as e:
            self.logger.error(f"Config update failed: {e}")

    def save_config(self):
        """Save configuration to file"""
        try:
            with open(self.config_path, 'w') as f:
                for section, values in self.config.items():
                    f.write(f"[{section}]\n")
                    for key, value in values.items():
                        f.write(f"{key} = {value}\n")
                    f.write("\n")
        except Exception as e:
            self.logger.error(f"Failed to save config: {e}")

    async def wait_for_shutdown(self):
        """Wait for shutdown signal"""
        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}")
            self.running = False
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        while self.running:
            await asyncio.sleep(1)


class FileEventHandler(FileSystemEventHandler):
    """File system event handler"""
    
    def __init__(self, agent: EdgeAgent):
        self.agent = agent
    
    def on_created(self, event):
        if not event.is_directory:
            asyncio.create_task(self.agent.queue_for_sync(
                "file_created",
                {"path": event.src_path, "timestamp": datetime.now().isoformat()}
            ))
    
    def on_modified(self, event):
        if not event.is_directory:
            asyncio.create_task(self.agent.queue_for_sync(
                "file_modified",
                {"path": event.src_path, "timestamp": datetime.now().isoformat()}
            ))


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="ActiveLog Edge Agent")
    parser.add_argument("--config", default="/etc/activelog/edge.conf",
                        help="Configuration file path")
    parser.add_argument("--daemon", action="store_true",
                        help="Run as daemon")
    
    args = parser.parse_args()
    
    # Create and run the agent
    agent = EdgeAgent(args.config)
    
    try:
        asyncio.run(agent.start())
    except KeyboardInterrupt:
        print("Agent stopped by user")
    except Exception as e:
        print(f"Agent error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()