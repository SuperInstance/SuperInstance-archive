"""
Wearable Device Data Ingestion for ActiveLog Health Suite
Integrates with major wearable devices and health platforms to collect real-time health data
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Union, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import json
import requests
import numpy as np
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class DeviceType(Enum):
    """Types of wearable devices"""
    SMARTWATCH = "smartwatch"
    FITNESS_TRACKER = "fitness_tracker"
    HEART_RATE_MONITOR = "heart_rate_monitor"
    SLEEP_TRACKER = "sleep_tracker"
    BLOOD_PRESSURE_MONITOR = "blood_pressure_monitor"
    GLUCOSE_MONITOR = "glucose_monitor"
    SMART_SCALE = "smart_scale"
    PULSE_OXIMETER = "pulse_oximeter"
    ECG_MONITOR = "ecg_monitor"
    TEMPERATURE_SENSOR = "temperature_sensor"

class DeviceBrand(Enum):
    """Supported device brands"""
    FITBIT = "fitbit"
    APPLE_WATCH = "apple_watch"
    GARMIN = "garmin"
    SAMSUNG = "samsung"
    POLAR = "polar"
    OURA = "oura"
    WITHINGS = "withings"
    OMRON = "omron"
    DEXCOM = "dexcom"
    FREESTYLE = "freestyle"
    GENERIC = "generic"

class DataType(Enum):
    """Types of health data"""
    HEART_RATE = "heart_rate"
    STEPS = "steps"
    CALORIES = "calories"
    DISTANCE = "distance"
    SLEEP = "sleep"
    BLOOD_PRESSURE = "blood_pressure"
    BLOOD_GLUCOSE = "blood_glucose"
    WEIGHT = "weight"
    BODY_FAT = "body_fat"
    TEMPERATURE = "temperature"
    OXYGEN_SATURATION = "oxygen_saturation"
    STRESS_LEVEL = "stress_level"
    ACTIVITY = "activity"
    ECG = "ecg"
    HYDRATION = "hydration"

class SyncStatus(Enum):
    """Device synchronization status"""
    CONNECTED = "connected"
    SYNCING = "syncing"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    RATE_LIMITED = "rate_limited"
    UNAUTHORIZED = "unauthorized"

@dataclass
class DeviceCredentials:
    """Authentication credentials for device APIs"""
    device_id: str
    brand: DeviceBrand
    access_token: str
    refresh_token: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    expires_at: Optional[datetime] = None
    scopes: List[str] = field(default_factory=list)
    webhook_url: Optional[str] = None

@dataclass
class HealthDataPoint:
    """Individual health data measurement"""
    device_id: str
    data_type: DataType
    value: Union[float, int, str, Dict[str, Any]]
    unit: str
    timestamp: datetime
    confidence: float = 1.0  # 0-1 confidence score
    source: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class DeviceInfo:
    """Information about a registered device"""
    device_id: str
    user_id: str
    brand: DeviceBrand
    device_type: DeviceType
    model: str
    name: str
    last_sync: Optional[datetime] = None
    battery_level: Optional[int] = None
    firmware_version: Optional[str] = None
    sync_status: SyncStatus = SyncStatus.DISCONNECTED
    data_types: List[DataType] = field(default_factory=list)
    sync_frequency: int = 300  # seconds
    is_active: bool = True

@dataclass
class SyncResult:
    """Result from device data synchronization"""
    device_id: str
    success: bool
    data_points_synced: int = 0
    sync_duration: float = 0.0
    last_sync_time: Optional[datetime] = None
    error_message: Optional[str] = None
    rate_limit_info: Optional[Dict[str, Any]] = None
    new_data_available: bool = False

class WearableDeviceInterface(ABC):
    """Abstract interface for wearable device integrations"""
    
    @abstractmethod
    async def authenticate(self, credentials: DeviceCredentials) -> bool:
        """Authenticate with device API"""
        pass
    
    @abstractmethod
    async def get_device_info(self, credentials: DeviceCredentials) -> DeviceInfo:
        """Get device information"""
        pass
    
    @abstractmethod
    async def sync_data(self, credentials: DeviceCredentials, since: datetime) -> List[HealthDataPoint]:
        """Sync health data from device"""
        pass
    
    @abstractmethod
    async def get_realtime_data(self, credentials: DeviceCredentials) -> List[HealthDataPoint]:
        """Get real-time data if supported"""
        pass

class FitbitIntegration(WearableDeviceInterface):
    """Fitbit device integration"""
    
    def __init__(self):
        self.base_url = "https://api.fitbit.com"
        self.api_version = "1.2"
        
    async def authenticate(self, credentials: DeviceCredentials) -> bool:
        """Authenticate with Fitbit API"""
        try:
            headers = {
                'Authorization': f'Bearer {credentials.access_token}',
                'Accept': 'application/json'
            }
            
            response = requests.get(
                f"{self.base_url}/{self.api_version}/user/-/profile.json",
                headers=headers,
                timeout=10
            )
            
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Fitbit authentication failed: {e}")
            return False
    
    async def get_device_info(self, credentials: DeviceCredentials) -> DeviceInfo:
        """Get Fitbit device information"""
        try:
            headers = {
                'Authorization': f'Bearer {credentials.access_token}',
                'Accept': 'application/json'
            }
            
            # Get devices
            response = requests.get(
                f"{self.base_url}/{self.api_version}/user/-/devices.json",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                devices = response.json()
                if devices:
                    device_data = devices[0]  # Primary device
                    
                    return DeviceInfo(
                        device_id=device_data.get('id', credentials.device_id),
                        user_id=credentials.device_id,
                        brand=DeviceBrand.FITBIT,
                        device_type=self._get_fitbit_device_type(device_data.get('type', '')),
                        model=device_data.get('deviceVersion', 'Unknown'),
                        name=device_data.get('deviceVersion', 'Fitbit Device'),
                        last_sync=datetime.fromisoformat(device_data.get('lastSyncTime', datetime.now().isoformat())),
                        battery_level=device_data.get('battery', 'High') == 'High' and 80 or 20,
                        firmware_version=device_data.get('deviceVersion'),
                        sync_status=SyncStatus.CONNECTED,
                        data_types=[
                            DataType.HEART_RATE, DataType.STEPS, DataType.CALORIES,
                            DataType.DISTANCE, DataType.SLEEP, DataType.ACTIVITY
                        ]
                    )
            
            # Fallback device info
            return DeviceInfo(
                device_id=credentials.device_id,
                user_id=credentials.device_id,
                brand=DeviceBrand.FITBIT,
                device_type=DeviceType.FITNESS_TRACKER,
                model="Unknown",
                name="Fitbit Device"
            )
            
        except Exception as e:
            logger.error(f"Failed to get Fitbit device info: {e}")
            raise
    
    async def sync_data(self, credentials: DeviceCredentials, since: datetime) -> List[HealthDataPoint]:
        """Sync data from Fitbit"""
        data_points = []
        
        try:
            headers = {
                'Authorization': f'Bearer {credentials.access_token}',
                'Accept': 'application/json'
            }
            
            date_str = since.strftime('%Y-%m-%d')
            
            # Sync heart rate data
            hr_data = await self._get_fitbit_heart_rate(headers, date_str)
            data_points.extend(hr_data)
            
            # Sync steps data
            steps_data = await self._get_fitbit_steps(headers, date_str)
            data_points.extend(steps_data)
            
            # Sync sleep data
            sleep_data = await self._get_fitbit_sleep(headers, date_str)
            data_points.extend(sleep_data)
            
            # Sync activity data
            activity_data = await self._get_fitbit_activities(headers, date_str)
            data_points.extend(activity_data)
            
            # Add device ID to all data points
            for point in data_points:
                point.device_id = credentials.device_id
            
            logger.info(f"Synced {len(data_points)} data points from Fitbit")
            return data_points
            
        except Exception as e:
            logger.error(f"Fitbit sync failed: {e}")
            return []
    
    async def get_realtime_data(self, credentials: DeviceCredentials) -> List[HealthDataPoint]:
        """Get real-time Fitbit data"""
        # Fitbit doesn't support true real-time, return recent intraday data
        return await self.sync_data(credentials, datetime.now() - timedelta(hours=1))
    
    async def _get_fitbit_heart_rate(self, headers: Dict, date: str) -> List[HealthDataPoint]:
        """Get heart rate data from Fitbit"""
        try:
            response = requests.get(
                f"{self.base_url}/{self.api_version}/user/-/activities/heart/date/{date}/1d/1min.json",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                points = []
                
                if 'activities-heart-intraday' in data:
                    for entry in data['activities-heart-intraday']['dataset']:
                        timestamp = datetime.strptime(f"{date} {entry['time']}", "%Y-%m-%d %H:%M:%S")
                        
                        points.append(HealthDataPoint(
                            device_id="",
                            data_type=DataType.HEART_RATE,
                            value=entry['value'],
                            unit="bpm",
                            timestamp=timestamp,
                            source="fitbit_api"
                        ))
                
                return points
                
        except Exception as e:
            logger.warning(f"Failed to get Fitbit heart rate: {e}")
        
        return []
    
    async def _get_fitbit_steps(self, headers: Dict, date: str) -> List[HealthDataPoint]:
        """Get steps data from Fitbit"""
        try:
            response = requests.get(
                f"{self.base_url}/{self.api_version}/user/-/activities/steps/date/{date}/1d/15min.json",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                points = []
                
                if 'activities-steps-intraday' in data:
                    for entry in data['activities-steps-intraday']['dataset']:
                        timestamp = datetime.strptime(f"{date} {entry['time']}", "%Y-%m-%d %H:%M:%S")
                        
                        points.append(HealthDataPoint(
                            device_id="",
                            data_type=DataType.STEPS,
                            value=entry['value'],
                            unit="steps",
                            timestamp=timestamp,
                            source="fitbit_api"
                        ))
                
                return points
                
        except Exception as e:
            logger.warning(f"Failed to get Fitbit steps: {e}")
        
        return []
    
    async def _get_fitbit_sleep(self, headers: Dict, date: str) -> List[HealthDataPoint]:
        """Get sleep data from Fitbit"""
        try:
            response = requests.get(
                f"{self.base_url}/{self.api_version}/user/-/sleep/date/{date}.json",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                points = []
                
                for sleep_log in data.get('sleep', []):
                    start_time = datetime.fromisoformat(sleep_log['startTime'].replace('Z', '+00:00'))
                    
                    points.append(HealthDataPoint(
                        device_id="",
                        data_type=DataType.SLEEP,
                        value={
                            'duration': sleep_log['duration'],
                            'efficiency': sleep_log['efficiency'],
                            'stages': sleep_log.get('levels', {})
                        },
                        unit="minutes",
                        timestamp=start_time,
                        source="fitbit_api"
                    ))
                
                return points
                
        except Exception as e:
            logger.warning(f"Failed to get Fitbit sleep: {e}")
        
        return []
    
    async def _get_fitbit_activities(self, headers: Dict, date: str) -> List[HealthDataPoint]:
        """Get activity data from Fitbit"""
        try:
            response = requests.get(
                f"{self.base_url}/{self.api_version}/user/-/activities/date/{date}.json",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                points = []
                
                # Daily summary
                summary = data.get('summary', {})
                date_obj = datetime.strptime(date, "%Y-%m-%d")
                
                points.extend([
                    HealthDataPoint(
                        device_id="",
                        data_type=DataType.CALORIES,
                        value=summary.get('caloriesOut', 0),
                        unit="calories",
                        timestamp=date_obj,
                        source="fitbit_api"
                    ),
                    HealthDataPoint(
                        device_id="",
                        data_type=DataType.DISTANCE,
                        value=sum(d.get('distance', 0) for d in summary.get('distances', [])),
                        unit="km",
                        timestamp=date_obj,
                        source="fitbit_api"
                    )
                ])
                
                return points
                
        except Exception as e:
            logger.warning(f"Failed to get Fitbit activities: {e}")
        
        return []
    
    def _get_fitbit_device_type(self, device_type: str) -> DeviceType:
        """Map Fitbit device type to our enum"""
        mapping = {
            'TRACKER': DeviceType.FITNESS_TRACKER,
            'WATCH': DeviceType.SMARTWATCH,
            'SCALE': DeviceType.SMART_SCALE
        }
        return mapping.get(device_type.upper(), DeviceType.FITNESS_TRACKER)

class AppleHealthIntegration(WearableDeviceInterface):
    """Apple Health integration"""
    
    def __init__(self):
        self.base_url = "https://developer.apple.com/health"  # Placeholder
        
    async def authenticate(self, credentials: DeviceCredentials) -> bool:
        """Apple Health uses local device authentication"""
        return True  # Assumes app has HealthKit permissions
    
    async def get_device_info(self, credentials: DeviceCredentials) -> DeviceInfo:
        """Get Apple device info"""
        return DeviceInfo(
            device_id=credentials.device_id,
            user_id=credentials.device_id,
            brand=DeviceBrand.APPLE_WATCH,
            device_type=DeviceType.SMARTWATCH,
            model="Apple Watch",
            name="Apple Watch",
            sync_status=SyncStatus.CONNECTED,
            data_types=[
                DataType.HEART_RATE, DataType.STEPS, DataType.CALORIES,
                DataType.DISTANCE, DataType.SLEEP, DataType.ECG, DataType.OXYGEN_SATURATION
            ]
        )
    
    async def sync_data(self, credentials: DeviceCredentials, since: datetime) -> List[HealthDataPoint]:
        """Sync Apple Health data"""
        # This would integrate with HealthKit
        # For now, return simulated data
        data_points = []
        
        # Simulate heart rate data
        for i in range(24):  # 24 hours of data
            timestamp = since + timedelta(hours=i)
            data_points.append(HealthDataPoint(
                device_id=credentials.device_id,
                data_type=DataType.HEART_RATE,
                value=np.random.normal(75, 10),
                unit="bpm",
                timestamp=timestamp,
                source="apple_health"
            ))
        
        return data_points
    
    async def get_realtime_data(self, credentials: DeviceCredentials) -> List[HealthDataPoint]:
        """Get real-time Apple Health data"""
        return await self.sync_data(credentials, datetime.now() - timedelta(minutes=5))

class WearableDataIngestion:
    """Main wearable device data ingestion system"""
    
    def __init__(self):
        self.devices: Dict[str, DeviceInfo] = {}
        self.credentials: Dict[str, DeviceCredentials] = {}
        self.integrations: Dict[DeviceBrand, WearableDeviceInterface] = {}
        self.data_buffer: Dict[str, List[HealthDataPoint]] = {}
        self.sync_tasks: Dict[str, asyncio.Task] = {}
        self.webhooks: Dict[str, Callable] = {}
        
        # Initialize integrations
        self._initialize_integrations()
        
        # Start background sync scheduler
        asyncio.create_task(self._sync_scheduler())
    
    def _initialize_integrations(self):
        """Initialize device brand integrations"""
        self.integrations = {
            DeviceBrand.FITBIT: FitbitIntegration(),
            DeviceBrand.APPLE_WATCH: AppleHealthIntegration(),
            # Add more integrations as needed
        }
        
        logger.info(f"Initialized {len(self.integrations)} device integrations")
    
    async def register_device(self, credentials: DeviceCredentials) -> str:
        """Register a new wearable device"""
        try:
            # Get integration for device brand
            if credentials.brand not in self.integrations:
                raise ValueError(f"Brand {credentials.brand.value} not supported")
            
            integration = self.integrations[credentials.brand]
            
            # Authenticate device
            auth_success = await integration.authenticate(credentials)
            if not auth_success:
                raise RuntimeError("Device authentication failed")
            
            # Get device information
            device_info = await integration.get_device_info(credentials)
            device_info.sync_status = SyncStatus.CONNECTED
            
            # Store device and credentials
            self.devices[credentials.device_id] = device_info
            self.credentials[credentials.device_id] = credentials
            self.data_buffer[credentials.device_id] = []
            
            # Start sync task
            await self._start_device_sync(credentials.device_id)
            
            logger.info(f"Registered device: {credentials.device_id} ({credentials.brand.value})")
            return credentials.device_id
            
        except Exception as e:
            logger.error(f"Failed to register device {credentials.device_id}: {e}")
            raise
    
    async def sync_device_data(self, device_id: str, force: bool = False) -> SyncResult:
        """Manually sync data from a specific device"""
        if device_id not in self.devices:
            raise ValueError(f"Device {device_id} not registered")
        
        device = self.devices[device_id]
        credentials = self.credentials[device_id]
        integration = self.integrations[device.brand]
        
        start_time = datetime.now()
        
        try:
            # Determine sync window
            if force or device.last_sync is None:
                since = datetime.now() - timedelta(days=7)  # Last week
            else:
                since = device.last_sync
            
            # Sync data
            device.sync_status = SyncStatus.SYNCING
            data_points = await integration.sync_data(credentials, since)
            
            # Store data points
            self.data_buffer[device_id].extend(data_points)
            
            # Update device status
            device.last_sync = datetime.now()
            device.sync_status = SyncStatus.CONNECTED
            
            sync_duration = (datetime.now() - start_time).total_seconds()
            
            result = SyncResult(
                device_id=device_id,
                success=True,
                data_points_synced=len(data_points),
                sync_duration=sync_duration,
                last_sync_time=device.last_sync,
                new_data_available=len(data_points) > 0
            )
            
            logger.info(f"Synced {len(data_points)} data points from {device_id}")
            return result
            
        except Exception as e:
            device.sync_status = SyncStatus.ERROR
            sync_duration = (datetime.now() - start_time).total_seconds()
            
            logger.error(f"Sync failed for device {device_id}: {e}")
            
            return SyncResult(
                device_id=device_id,
                success=False,
                sync_duration=sync_duration,
                error_message=str(e)
            )
    
    async def get_device_data(
        self,
        device_id: str,
        data_types: Optional[List[DataType]] = None,
        since: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[HealthDataPoint]:
        """Get health data from device buffer"""
        if device_id not in self.data_buffer:
            return []
        
        data_points = self.data_buffer[device_id]
        
        # Apply filters
        if data_types:
            data_points = [dp for dp in data_points if dp.data_type in data_types]
        
        if since:
            data_points = [dp for dp in data_points if dp.timestamp >= since]
        
        # Sort by timestamp
        data_points.sort(key=lambda x: x.timestamp, reverse=True)
        
        if limit:
            data_points = data_points[:limit]
        
        return data_points
    
    async def get_realtime_data(self, device_id: str) -> List[HealthDataPoint]:
        """Get real-time data from device"""
        if device_id not in self.devices:
            raise ValueError(f"Device {device_id} not registered")
        
        device = self.devices[device_id]
        credentials = self.credentials[device_id]
        integration = self.integrations[device.brand]
        
        try:
            return await integration.get_realtime_data(credentials)
        except Exception as e:
            logger.error(f"Failed to get real-time data from {device_id}: {e}")
            return []
    
    async def _start_device_sync(self, device_id: str):
        """Start background sync task for device"""
        if device_id in self.sync_tasks:
            self.sync_tasks[device_id].cancel()
        
        async def sync_loop():
            while device_id in self.devices:
                try:
                    await self.sync_device_data(device_id)
                    device = self.devices[device_id]
                    await asyncio.sleep(device.sync_frequency)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Sync loop error for {device_id}: {e}")
                    await asyncio.sleep(300)  # Wait 5 minutes on error
        
        self.sync_tasks[device_id] = asyncio.create_task(sync_loop())
    
    async def _sync_scheduler(self):
        """Background scheduler for device synchronization"""
        while True:
            try:
                # Check for devices needing sync
                for device_id, device in self.devices.items():
                    if device.is_active and device.sync_status == SyncStatus.CONNECTED:
                        time_since_sync = (datetime.now() - device.last_sync).total_seconds() if device.last_sync else float('inf')
                        
                        if time_since_sync >= device.sync_frequency:
                            asyncio.create_task(self.sync_device_data(device_id))
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Sync scheduler error: {e}")
                await asyncio.sleep(300)
    
    async def setup_webhook(self, device_id: str, webhook_url: str, callback: Callable):
        """Setup webhook for real-time data updates"""
        self.webhooks[device_id] = callback
        
        # Update device credentials with webhook URL
        if device_id in self.credentials:
            self.credentials[device_id].webhook_url = webhook_url
        
        logger.info(f"Setup webhook for device {device_id}: {webhook_url}")
    
    async def handle_webhook(self, device_id: str, data: Dict[str, Any]):
        """Handle incoming webhook data"""
        if device_id in self.webhooks:
            try:
                await self.webhooks[device_id](device_id, data)
            except Exception as e:
                logger.error(f"Webhook handling error for {device_id}: {e}")
    
    async def get_device_status(self, device_id: str) -> Dict[str, Any]:
        """Get comprehensive device status"""
        if device_id not in self.devices:
            return {'exists': False}
        
        device = self.devices[device_id]
        
        # Calculate data statistics
        data_points = self.data_buffer.get(device_id, [])
        data_stats = {
            'total_points': len(data_points),
            'data_types': list(set(dp.data_type.value for dp in data_points)),
            'last_data_point': max(dp.timestamp for dp in data_points).isoformat() if data_points else None,
            'oldest_data_point': min(dp.timestamp for dp in data_points).isoformat() if data_points else None
        }
        
        return {
            'exists': True,
            'device': {
                'brand': device.brand.value,
                'type': device.device_type.value,
                'model': device.model,
                'name': device.name,
                'is_active': device.is_active,
                'battery_level': device.battery_level,
                'firmware_version': device.firmware_version
            },
            'sync_status': {
                'status': device.sync_status.value,
                'last_sync': device.last_sync.isoformat() if device.last_sync else None,
                'sync_frequency': device.sync_frequency,
                'has_sync_task': device_id in self.sync_tasks
            },
            'data_statistics': data_stats
        }
    
    async def list_devices(self) -> Dict[str, Dict[str, Any]]:
        """List all registered devices"""
        return {
            device_id: {
                'brand': device.brand.value,
                'type': device.device_type.value,
                'name': device.name,
                'sync_status': device.sync_status.value,
                'is_active': device.is_active,
                'last_sync': device.last_sync.isoformat() if device.last_sync else None,
                'data_points': len(self.data_buffer.get(device_id, []))
            }
            for device_id, device in self.devices.items()
        }
    
    async def get_aggregated_data(
        self,
        data_type: DataType,
        timeframe: str = "day",  # "hour", "day", "week", "month"
        devices: Optional[List[str]] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Get aggregated health data across devices"""
        
        if devices is None:
            devices = list(self.devices.keys())
        
        aggregated = {}
        
        for device_id in devices:
            if device_id not in self.data_buffer:
                continue
            
            device_data = [dp for dp in self.data_buffer[device_id] if dp.data_type == data_type]
            
            if not device_data:
                continue
            
            # Group by timeframe
            grouped_data = self._group_by_timeframe(device_data, timeframe)
            aggregated[device_id] = grouped_data
        
        return aggregated
    
    def _group_by_timeframe(self, data_points: List[HealthDataPoint], timeframe: str) -> List[Dict[str, Any]]:
        """Group data points by timeframe"""
        grouped = {}
        
        for dp in data_points:
            if timeframe == "hour":
                key = dp.timestamp.strftime("%Y-%m-%d %H:00")
            elif timeframe == "day":
                key = dp.timestamp.strftime("%Y-%m-%d")
            elif timeframe == "week":
                key = dp.timestamp.strftime("%Y-W%W")
            elif timeframe == "month":
                key = dp.timestamp.strftime("%Y-%m")
            else:
                key = dp.timestamp.isoformat()
            
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(dp.value)
        
        # Calculate aggregations
        result = []
        for timeframe_key, values in grouped.items():
            if isinstance(values[0], (int, float)):
                result.append({
                    'timeframe': timeframe_key,
                    'count': len(values),
                    'average': np.mean(values),
                    'min': np.min(values),
                    'max': np.max(values),
                    'sum': np.sum(values)
                })
            else:
                result.append({
                    'timeframe': timeframe_key,
                    'count': len(values),
                    'values': values
                })
        
        return sorted(result, key=lambda x: x['timeframe'])

# Global singleton instance
wearable_ingestion = WearableDataIngestion()