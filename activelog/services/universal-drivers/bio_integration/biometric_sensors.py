import numpy as np
import asyncio
import threading
import time
import random
from typing import Dict, List, Any, Optional, Callable, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import json
from datetime import datetime, timedelta
import math

class BiometricType(Enum):
    HEART_RATE = "heart_rate"
    BLOOD_PRESSURE = "blood_pressure"
    BLOOD_OXYGEN = "blood_oxygen"
    GLUCOSE = "glucose"
    TEMPERATURE = "temperature"
    RESPIRATORY_RATE = "respiratory_rate"
    ECG = "ecg"
    PPG = "ppg"
    GSR = "gsr"  # Galvanic Skin Response
    ACCELEROMETER = "accelerometer"
    GYROSCOPE = "gyroscope"
    PEDOMETER = "pedometer"
    SLEEP_STAGE = "sleep_stage"
    STRESS_LEVEL = "stress_level"
    HYDRATION = "hydration"
    CALORIES_BURNED = "calories_burned"

class SensorLocation(Enum):
    WRIST = "wrist"
    FINGER = "finger"
    CHEST = "chest"
    ARM = "arm"
    EAR = "ear"
    FOREHEAD = "forehead"
    ANKLE = "ankle"
    WAIST = "waist"
    IMPLANTED = "implanted"

@dataclass
class BiometricReading:
    sensor_type: BiometricType
    timestamp: datetime
    value: float
    unit: str
    confidence: float
    location: SensorLocation
    metadata: Dict[str, Any]
    quality_indicators: Dict[str, float]

@dataclass
class SensorConfiguration:
    sensor_type: BiometricType
    location: SensorLocation
    sampling_rate: float
    measurement_range: Tuple[float, float]
    accuracy: float
    calibration_required: bool
    battery_life_hours: int
    waterproof: bool
    wireless_protocol: str

class BiometricSensor:
    def __init__(self, config: SensorConfiguration):
        self.config = config
        self.is_active = False
        self.calibrated = not config.calibration_required
        self.battery_level = 100.0
        self.readings_buffer = []
        self.callbacks = {}
        self.background_thread = None
        
        # Physiological baseline values
        self.baselines = self._initialize_baselines()
        self.current_state = self._initialize_state()
        
    def _initialize_baselines(self) -> Dict[str, float]:
        """Initialize physiological baseline values"""
        baselines = {
            BiometricType.HEART_RATE: 70.0,  # BPM
            BiometricType.BLOOD_PRESSURE: 120.0,  # mmHg systolic
            BiometricType.BLOOD_OXYGEN: 98.0,  # %
            BiometricType.GLUCOSE: 90.0,  # mg/dL
            BiometricType.TEMPERATURE: 36.5,  # Celsius
            BiometricType.RESPIRATORY_RATE: 16.0,  # breaths/min
            BiometricType.GSR: 5.0,  # µS
            BiometricType.STRESS_LEVEL: 3.0,  # 1-10 scale
            BiometricType.HYDRATION: 75.0,  # percentage
        }
        return baselines
    
    def _initialize_state(self) -> Dict[str, Any]:
        """Initialize sensor state variables"""
        return {
            'activity_level': 'resting',
            'time_since_meal': 3.0,  # hours
            'time_since_exercise': 2.0,  # hours
            'ambient_temperature': 22.0,  # Celsius
            'altitude': 0,  # meters
            'caffeine_intake': False,
            'stress_event': False,
            'sleep_debt': 0.0  # hours
        }
    
    async def start_monitoring(self):
        """Start continuous monitoring"""
        if self.is_active:
            return
        
        if not self.calibrated:
            await self.calibrate()
        
        self.is_active = True
        self.background_thread = threading.Thread(target=self._monitoring_loop)
        self.background_thread.daemon = True
        self.background_thread.start()
    
    async def stop_monitoring(self):
        """Stop monitoring"""
        self.is_active = False
        if self.background_thread:
            self.background_thread.join()
    
    def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.is_active:
            try:
                # Take measurement
                reading = self._take_measurement()
                
                # Store reading
                self.readings_buffer.append(reading)
                if len(self.readings_buffer) > 1000:  # Keep last 1000 readings
                    self.readings_buffer.pop(0)
                
                # Update battery
                self.battery_level -= 0.01 / self.config.sampling_rate  # Drain based on usage
                self.battery_level = max(0, self.battery_level)
                
                # Trigger callbacks
                self._trigger_callbacks(reading)
                
                # Wait for next sample
                time.sleep(1.0 / self.config.sampling_rate)
                
            except Exception as e:
                print(f"Monitoring error: {e}")
                time.sleep(1.0)
    
    def _take_measurement(self) -> BiometricReading:
        """Take a single measurement"""
        timestamp = datetime.now()
        
        # Get base value for sensor type
        base_value = self.baselines.get(self.config.sensor_type, 50.0)
        
        # Apply physiological variations
        value = self._simulate_physiological_value(base_value)
        
        # Add sensor noise and accuracy limitations
        noise_factor = (100 - self.config.accuracy) / 100.0
        noise = random.gauss(0, value * noise_factor * 0.1)
        value += noise
        
        # Clamp to measurement range
        min_val, max_val = self.config.measurement_range
        value = max(min_val, min(max_val, value))
        
        # Calculate confidence based on signal quality
        confidence = self._calculate_confidence()
        
        # Get appropriate unit
        unit = self._get_unit_for_sensor_type()
        
        # Calculate quality indicators
        quality_indicators = self._calculate_quality_indicators()
        
        return BiometricReading(
            sensor_type=self.config.sensor_type,
            timestamp=timestamp,
            value=value,
            unit=unit,
            confidence=confidence,
            location=self.config.location,
            metadata={
                'activity_level': self.current_state['activity_level'],
                'battery_level': self.battery_level,
                'calibrated': self.calibrated
            },
            quality_indicators=quality_indicators
        )
    
    def _simulate_physiological_value(self, base_value: float) -> float:
        """Simulate realistic physiological variations"""
        sensor_type = self.config.sensor_type
        
        # Time-based variations
        current_hour = datetime.now().hour
        time_factor = 1.0
        
        # Circadian rhythm effects
        if sensor_type == BiometricType.HEART_RATE:
            # Lower heart rate at night, higher during day
            time_factor = 0.9 + 0.2 * math.sin((current_hour - 6) * math.pi / 12)
        elif sensor_type == BiometricType.TEMPERATURE:
            # Body temperature variation throughout day
            time_factor = 0.995 + 0.01 * math.sin((current_hour - 6) * math.pi / 12)
        elif sensor_type == BiometricType.GLUCOSE:
            # Higher after meals, lower when fasting
            time_since_meal = self.current_state['time_since_meal']
            if time_since_meal < 2:
                time_factor = 1.2 - 0.1 * time_since_meal
            else:
                time_factor = 0.9
        
        # Activity level effects
        activity_multipliers = {
            'resting': 1.0,
            'light': 1.1,
            'moderate': 1.3,
            'vigorous': 1.6,
            'intense': 2.0
        }
        activity_factor = activity_multipliers.get(self.current_state['activity_level'], 1.0)
        
        if sensor_type in [BiometricType.HEART_RATE, BiometricType.RESPIRATORY_RATE]:
            value = base_value * time_factor * activity_factor
        elif sensor_type == BiometricType.TEMPERATURE:
            # Temperature increases less dramatically with activity
            value = base_value * time_factor + (activity_factor - 1.0) * 0.5
        else:
            value = base_value * time_factor
        
        # Add stress effects
        if self.current_state['stress_event']:
            if sensor_type == BiometricType.HEART_RATE:
                value *= 1.2
            elif sensor_type == BiometricType.BLOOD_PRESSURE:
                value *= 1.15
            elif sensor_type == BiometricType.GSR:
                value *= 1.4
        
        # Add random physiological variation
        variation = random.gauss(0, base_value * 0.05)  # 5% standard variation
        value += variation
        
        return max(0, value)
    
    def _calculate_confidence(self) -> float:
        """Calculate measurement confidence"""
        confidence = 0.8  # Base confidence
        
        # Reduce confidence for low battery
        if self.battery_level < 20:
            confidence *= 0.8
        
        # Reduce confidence if not calibrated
        if not self.calibrated:
            confidence *= 0.6
        
        # Reduce confidence for high activity (motion artifacts)
        activity_penalties = {
            'resting': 1.0,
            'light': 0.95,
            'moderate': 0.85,
            'vigorous': 0.7,
            'intense': 0.5
        }
        confidence *= activity_penalties.get(self.current_state['activity_level'], 0.8)
        
        # Add some random variation
        confidence += random.gauss(0, 0.05)
        
        return max(0.1, min(1.0, confidence))
    
    def _get_unit_for_sensor_type(self) -> str:
        """Get appropriate unit for sensor type"""
        units = {
            BiometricType.HEART_RATE: "bpm",
            BiometricType.BLOOD_PRESSURE: "mmHg",
            BiometricType.BLOOD_OXYGEN: "%",
            BiometricType.GLUCOSE: "mg/dL",
            BiometricType.TEMPERATURE: "°C",
            BiometricType.RESPIRATORY_RATE: "breaths/min",
            BiometricType.GSR: "µS",
            BiometricType.STRESS_LEVEL: "level(1-10)",
            BiometricType.HYDRATION: "%",
            BiometricType.CALORIES_BURNED: "cal/min",
            BiometricType.ACCELEROMETER: "g",
            BiometricType.GYROSCOPE: "deg/s",
            BiometricType.PEDOMETER: "steps/min"
        }
        return units.get(self.config.sensor_type, "units")
    
    def _calculate_quality_indicators(self) -> Dict[str, float]:
        """Calculate signal quality indicators"""
        return {
            'signal_noise_ratio': random.uniform(0.7, 0.95),
            'motion_artifact': random.uniform(0.0, 0.3),
            'ambient_interference': random.uniform(0.0, 0.2),
            'sensor_contact': random.uniform(0.8, 1.0),
            'temperature_stability': random.uniform(0.85, 1.0)
        }
    
    async def calibrate(self):
        """Perform sensor calibration"""
        print(f"Calibrating {self.config.sensor_type.value} sensor...")
        await asyncio.sleep(2)  # Simulate calibration time
        self.calibrated = True
        print("Calibration complete")
    
    def set_activity_level(self, activity: str):
        """Update current activity level"""
        valid_activities = ['resting', 'light', 'moderate', 'vigorous', 'intense']
        if activity in valid_activities:
            self.current_state['activity_level'] = activity
    
    def trigger_stress_event(self, duration: float = 60.0):
        """Simulate stress event"""
        self.current_state['stress_event'] = True
        
        def reset_stress():
            time.sleep(duration)
            self.current_state['stress_event'] = False
        
        thread = threading.Thread(target=reset_stress)
        thread.daemon = True
        thread.start()
    
    def register_callback(self, event_type: str, callback: Callable):
        """Register callback for events"""
        if event_type not in self.callbacks:
            self.callbacks[event_type] = []
        self.callbacks[event_type].append(callback)
    
    def _trigger_callbacks(self, reading: BiometricReading):
        """Trigger registered callbacks"""
        # General reading callback
        if 'new_reading' in self.callbacks:
            for callback in self.callbacks['new_reading']:
                try:
                    callback(reading)
                except Exception as e:
                    print(f"Callback error: {e}")
        
        # Threshold-based callbacks
        self._check_thresholds(reading)
        
        # Low battery callback
        if self.battery_level < 20 and 'low_battery' in self.callbacks:
            for callback in self.callbacks['low_battery']:
                try:
                    callback(self.battery_level)
                except Exception as e:
                    print(f"Battery callback error: {e}")
    
    def _check_thresholds(self, reading: BiometricReading):
        """Check for threshold violations"""
        value = reading.value
        sensor_type = reading.sensor_type
        
        # Define normal ranges
        normal_ranges = {
            BiometricType.HEART_RATE: (60, 100),
            BiometricType.BLOOD_PRESSURE: (90, 140),
            BiometricType.BLOOD_OXYGEN: (95, 100),
            BiometricType.GLUCOSE: (70, 140),
            BiometricType.TEMPERATURE: (36.1, 37.2),
            BiometricType.RESPIRATORY_RATE: (12, 20)
        }
        
        if sensor_type in normal_ranges:
            min_val, max_val = normal_ranges[sensor_type]
            if value < min_val or value > max_val:
                if 'threshold_violation' in self.callbacks:
                    for callback in self.callbacks['threshold_violation']:
                        try:
                            callback(reading, 'out_of_range')
                        except Exception as e:
                            print(f"Threshold callback error: {e}")
    
    def get_recent_readings(self, count: int = 10) -> List[BiometricReading]:
        """Get recent readings"""
        return self.readings_buffer[-count:] if self.readings_buffer else []
    
    def get_statistics(self, duration_minutes: int = 60) -> Dict[str, Any]:
        """Get statistics for recent period"""
        cutoff_time = datetime.now() - timedelta(minutes=duration_minutes)
        recent_readings = [r for r in self.readings_buffer if r.timestamp > cutoff_time]
        
        if not recent_readings:
            return {'status': 'no_data'}
        
        values = [r.value for r in recent_readings]
        confidences = [r.confidence for r in recent_readings]
        
        return {
            'count': len(recent_readings),
            'duration_minutes': duration_minutes,
            'value_stats': {
                'mean': np.mean(values),
                'std': np.std(values),
                'min': np.min(values),
                'max': np.max(values),
                'median': np.median(values)
            },
            'confidence_stats': {
                'mean': np.mean(confidences),
                'min': np.min(confidences)
            },
            'sensor_status': {
                'battery_level': self.battery_level,
                'calibrated': self.calibrated,
                'active': self.is_active
            }
        }

class WearableDevice:
    """Multi-sensor wearable device simulator"""
    
    def __init__(self, device_type: str = "smartwatch"):
        self.device_type = device_type
        self.sensors = {}
        self.device_id = f"{device_type}_{int(time.time())}"
        
        # Initialize sensors based on device type
        self._initialize_sensors()
        
    def _initialize_sensors(self):
        """Initialize sensors based on device type"""
        if self.device_type == "smartwatch":
            sensors = [
                SensorConfiguration(BiometricType.HEART_RATE, SensorLocation.WRIST, 1.0, (30, 200), 95.0, False, 48, True, "bluetooth"),
                SensorConfiguration(BiometricType.ACCELEROMETER, SensorLocation.WRIST, 50.0, (-8, 8), 90.0, True, 48, True, "bluetooth"),
                SensorConfiguration(BiometricType.GYROSCOPE, SensorLocation.WRIST, 50.0, (-500, 500), 90.0, True, 48, True, "bluetooth"),
                SensorConfiguration(BiometricType.PEDOMETER, SensorLocation.WRIST, 0.1, (0, 1000), 85.0, True, 48, True, "bluetooth")
            ]
        elif self.device_type == "fitness_band":
            sensors = [
                SensorConfiguration(BiometricType.HEART_RATE, SensorLocation.WRIST, 1.0, (30, 200), 90.0, False, 120, True, "bluetooth"),
                SensorConfiguration(BiometricType.PEDOMETER, SensorLocation.WRIST, 0.1, (0, 1000), 80.0, True, 120, True, "bluetooth"),
                SensorConfiguration(BiometricType.SLEEP_STAGE, SensorLocation.WRIST, 0.002, (0, 4), 75.0, True, 120, True, "bluetooth")
            ]
        elif self.device_type == "chest_strap":
            sensors = [
                SensorConfiguration(BiometricType.HEART_RATE, SensorLocation.CHEST, 1.0, (30, 200), 98.0, False, 200, True, "bluetooth"),
                SensorConfiguration(BiometricType.ECG, SensorLocation.CHEST, 250.0, (-5, 5), 95.0, True, 200, True, "bluetooth"),
                SensorConfiguration(BiometricType.RESPIRATORY_RATE, SensorLocation.CHEST, 0.25, (5, 40), 90.0, False, 200, True, "bluetooth")
            ]
        elif self.device_type == "continuous_glucose_monitor":
            sensors = [
                SensorConfiguration(BiometricType.GLUCOSE, SensorLocation.ARM, 0.017, (40, 400), 93.0, True, 168, True, "bluetooth"),
                SensorConfiguration(BiometricType.TEMPERATURE, SensorLocation.ARM, 0.1, (30, 45), 92.0, False, 168, True, "bluetooth")
            ]
        
        # Create sensor instances
        for config in sensors:
            sensor = BiometricSensor(config)
            self.sensors[config.sensor_type] = sensor
    
    async def start_all_sensors(self):
        """Start all sensors"""
        for sensor in self.sensors.values():
            await sensor.start_monitoring()
    
    async def stop_all_sensors(self):
        """Stop all sensors"""
        for sensor in self.sensors.values():
            await sensor.stop_monitoring()
    
    def get_sensor(self, sensor_type: BiometricType) -> Optional[BiometricSensor]:
        """Get specific sensor"""
        return self.sensors.get(sensor_type)
    
    def get_all_current_readings(self) -> Dict[str, Any]:
        """Get current readings from all sensors"""
        readings = {}
        for sensor_type, sensor in self.sensors.items():
            recent = sensor.get_recent_readings(1)
            if recent:
                readings[sensor_type.value] = {
                    'value': recent[0].value,
                    'unit': recent[0].unit,
                    'timestamp': recent[0].timestamp.isoformat(),
                    'confidence': recent[0].confidence
                }
        return readings
    
    def simulate_workout(self, duration_minutes: int = 30):
        """Simulate workout session"""
        activities = ['light', 'moderate', 'vigorous', 'vigorous', 'moderate', 'light']
        
        def workout_simulation():
            segment_duration = duration_minutes * 60 / len(activities)
            for activity in activities:
                for sensor in self.sensors.values():
                    sensor.set_activity_level(activity)
                time.sleep(segment_duration)
            
            # Return to resting
            for sensor in self.sensors.values():
                sensor.set_activity_level('resting')
        
        thread = threading.Thread(target=workout_simulation)
        thread.daemon = True
        thread.start()

if __name__ == "__main__":
    print("Biometric Sensor Simulation")
    print("=" * 50)
    
    async def demo():
        # Create wearable device
        watch = WearableDevice("smartwatch")
        
        # Register callbacks
        def on_heart_rate_reading(reading):
            if reading.sensor_type == BiometricType.HEART_RATE:
                print(f"Heart Rate: {reading.value:.0f} {reading.unit} (confidence: {reading.confidence:.2f})")
        
        def on_threshold_violation(reading, violation_type):
            print(f"⚠️  {reading.sensor_type.value} threshold violation: {reading.value:.1f} {reading.unit}")
        
        # Register callbacks for all sensors
        for sensor in watch.sensors.values():
            sensor.register_callback('new_reading', on_heart_rate_reading)
            sensor.register_callback('threshold_violation', on_threshold_violation)
        
        print(f"Starting {watch.device_type} with {len(watch.sensors)} sensors...")
        await watch.start_all_sensors()
        
        try:
            # Monitor at rest for 5 seconds
            print("Monitoring at rest...")
            await asyncio.sleep(5)
            
            # Simulate workout
            print("Starting workout simulation...")
            watch.simulate_workout(10)  # 10-minute workout
            
            # Monitor for 15 seconds during workout
            for i in range(15):
                await asyncio.sleep(1)
                readings = watch.get_all_current_readings()
                if readings:
                    print(f"Time: {i+1}s - Current readings:")
                    for sensor_type, data in readings.items():
                        if sensor_type == 'heart_rate':
                            print(f"  {sensor_type}: {data['value']:.0f} {data['unit']}")
            
            # Show statistics
            print("\nSession Statistics:")
            for sensor_type, sensor in watch.sensors.items():
                stats = sensor.get_statistics(duration_minutes=1)
                if 'value_stats' in stats:
                    print(f"{sensor_type.value}:")
                    print(f"  Mean: {stats['value_stats']['mean']:.1f}")
                    print(f"  Range: {stats['value_stats']['min']:.1f} - {stats['value_stats']['max']:.1f}")
                    print(f"  Battery: {stats['sensor_status']['battery_level']:.1f}%")
        
        finally:
            await watch.stop_all_sensors()
            print("Monitoring stopped")
    
    asyncio.run(demo())