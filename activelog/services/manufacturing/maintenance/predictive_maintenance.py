#!/usr/bin/env python3
"""
ActiveLog Manufacturing Suite - Predictive Maintenance Scheduling

AI-powered predictive maintenance system using IoT sensors, machine learning,
and operational data to optimize equipment maintenance schedules.
"""

import asyncio
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
import sqlite3
from pathlib import Path
import aiohttp
from sklearn.ensemble import RandomForestClassifier, IsolationForest
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats, signal
import warnings
warnings.filterwarnings('ignore')


class MaintenanceType(Enum):
    PREVENTIVE = "preventive"
    PREDICTIVE = "predictive"
    CORRECTIVE = "corrective"
    CONDITION_BASED = "condition_based"
    EMERGENCY = "emergency"


class EquipmentStatus(Enum):
    OPERATIONAL = "operational"
    WARNING = "warning"
    CRITICAL = "critical"
    DOWN = "down"
    MAINTENANCE = "maintenance"


class SensorType(Enum):
    VIBRATION = "vibration"
    TEMPERATURE = "temperature"
    PRESSURE = "pressure"
    CURRENT = "current"
    VOLTAGE = "voltage"
    FLOW_RATE = "flow_rate"
    RPM = "rpm"
    TORQUE = "torque"
    ACOUSTIC = "acoustic"
    OIL_QUALITY = "oil_quality"


class FailureMode(Enum):
    BEARING_FAILURE = "bearing_failure"
    MISALIGNMENT = "misalignment"
    IMBALANCE = "imbalance"
    LOOSENESS = "looseness"
    BELT_WEAR = "belt_wear"
    OVERHEATING = "overheating"
    ELECTRICAL_FAULT = "electrical_fault"
    LUBRICATION_FAILURE = "lubrication_failure"
    FATIGUE = "fatigue"
    CORROSION = "corrosion"


class Priority(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class Equipment:
    equipment_id: str
    name: str
    type: str
    manufacturer: str
    model: str
    serial_number: str
    location: str
    installation_date: datetime
    last_maintenance_date: Optional[datetime]
    next_scheduled_maintenance: Optional[datetime]
    operating_hours: float
    status: EquipmentStatus
    criticality_score: float  # 0.0 to 1.0
    specifications: Dict[str, Any]


@dataclass
class SensorReading:
    reading_id: str
    equipment_id: str
    sensor_type: SensorType
    timestamp: datetime
    value: float
    unit: str
    quality_flag: str  # good, poor, bad
    calibration_date: Optional[datetime]


@dataclass
class MaintenanceTask:
    task_id: str
    equipment_id: str
    maintenance_type: MaintenanceType
    priority: Priority
    description: str
    estimated_duration_hours: float
    estimated_cost: float
    required_parts: List[str]
    required_skills: List[str]
    scheduled_date: datetime
    completion_date: Optional[datetime]
    assigned_technician: Optional[str]
    work_order_status: str
    failure_modes_addressed: List[FailureMode]


@dataclass
class FailurePrediction:
    prediction_id: str
    equipment_id: str
    failure_mode: FailureMode
    probability: float
    confidence: float
    time_to_failure_days: float
    contributing_factors: List[str]
    recommended_actions: List[str]
    prediction_date: datetime
    model_version: str


@dataclass
class MaintenanceMetrics:
    metrics_date: datetime
    mean_time_between_failures: float
    mean_time_to_repair: float
    overall_equipment_effectiveness: float
    planned_maintenance_percentage: float
    emergency_maintenance_percentage: float
    maintenance_cost_per_hour: float
    parts_availability: float
    technician_utilization: float


class SensorDataProcessor:
    """Processor for sensor data analysis and anomaly detection"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.scalers = {}
        self.anomaly_detectors = {}
        self.feature_extractors = {}
    
    async def process_sensor_data(self, equipment_id: str, 
                                sensor_type: SensorType,
                                time_window_hours: int = 24) -> Dict[str, Any]:
        """Process sensor data for equipment"""
        # Get recent sensor readings
        readings = await self._get_sensor_readings(
            equipment_id, sensor_type, time_window_hours
        )
        
        if len(readings) < 10:  # Minimum data points needed
            return {'status': 'insufficient_data', 'readings_count': len(readings)}
        
        # Extract features from time series data
        features = await self._extract_features(readings, sensor_type)
        
        # Detect anomalies
        anomalies = await self._detect_anomalies(equipment_id, sensor_type, features)
        
        # Calculate health indicators
        health_indicators = await self._calculate_health_indicators(readings, sensor_type)
        
        # Generate trending analysis
        trends = await self._analyze_trends(readings, sensor_type)
        
        return {
            'equipment_id': equipment_id,
            'sensor_type': sensor_type.value,
            'analysis_timestamp': datetime.now(),
            'readings_count': len(readings),
            'features': features,
            'anomalies': anomalies,
            'health_indicators': health_indicators,
            'trends': trends,
            'data_quality': await self._assess_data_quality(readings)
        }
    
    async def _get_sensor_readings(self, equipment_id: str, sensor_type: SensorType,
                                 time_window_hours: int) -> pd.DataFrame:
        """Get sensor readings from database"""
        conn = sqlite3.connect(self.db_path)
        
        start_time = datetime.now() - timedelta(hours=time_window_hours)
        
        query = """
        SELECT timestamp, value, unit, quality_flag
        FROM sensor_readings 
        WHERE equipment_id = ? AND sensor_type = ? 
        AND timestamp >= ?
        ORDER BY timestamp
        """
        
        df = pd.read_sql_query(
            query, conn, 
            params=(equipment_id, sensor_type.value, start_time)
        )
        conn.close()
        
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.set_index('timestamp')
            # Filter out bad quality readings
            df = df[df['quality_flag'] == 'good']
        
        return df
    
    async def _extract_features(self, readings: pd.DataFrame, 
                              sensor_type: SensorType) -> Dict[str, float]:
        """Extract statistical and frequency domain features"""
        if readings.empty:
            return {}
        
        values = readings['value'].values
        
        # Time domain features
        features = {
            'mean': np.mean(values),
            'std': np.std(values),
            'variance': np.var(values),
            'rms': np.sqrt(np.mean(values**2)),
            'peak': np.max(values),
            'peak_to_peak': np.max(values) - np.min(values),
            'crest_factor': np.max(values) / np.sqrt(np.mean(values**2)) if np.mean(values**2) > 0 else 0,
            'skewness': stats.skew(values),
            'kurtosis': stats.kurtosis(values),
            'range': np.max(values) - np.min(values)
        }
        
        # Frequency domain features for vibration data
        if sensor_type == SensorType.VIBRATION and len(values) >= 64:
            # FFT analysis
            fft_values = np.fft.fft(values)
            fft_freq = np.fft.fftfreq(len(values))
            power_spectrum = np.abs(fft_values)**2
            
            features.update({
                'dominant_frequency': fft_freq[np.argmax(power_spectrum[1:len(power_spectrum)//2]) + 1],
                'spectral_centroid': np.sum(fft_freq[:len(fft_freq)//2] * power_spectrum[:len(power_spectrum)//2]) / np.sum(power_spectrum[:len(power_spectrum)//2]),
                'spectral_rolloff': self._calculate_spectral_rolloff(power_spectrum, fft_freq),
                'spectral_flux': np.sum(np.diff(power_spectrum)**2)
            })
        
        # Trend features
        if len(values) > 1:
            slope, intercept, r_value, p_value, std_err = stats.linregress(
                range(len(values)), values
            )
            features.update({
                'trend_slope': slope,
                'trend_r_squared': r_value**2
            })
        
        return features
    
    def _calculate_spectral_rolloff(self, power_spectrum: np.ndarray, 
                                  frequencies: np.ndarray, threshold: float = 0.85) -> float:
        """Calculate spectral rolloff frequency"""
        cumulative_power = np.cumsum(power_spectrum[:len(power_spectrum)//2])
        total_power = cumulative_power[-1]
        
        rolloff_idx = np.where(cumulative_power >= threshold * total_power)[0]
        if len(rolloff_idx) > 0:
            return frequencies[rolloff_idx[0]]
        return frequencies[len(frequencies)//2 - 1]
    
    async def _detect_anomalies(self, equipment_id: str, sensor_type: SensorType,
                              features: Dict[str, float]) -> Dict[str, Any]:
        """Detect anomalies in sensor features"""
        feature_key = f"{equipment_id}_{sensor_type.value}"
        
        # Get or create anomaly detector
        if feature_key not in self.anomaly_detectors:
            self.anomaly_detectors[feature_key] = IsolationForest(
                contamination=0.1, random_state=42
            )
            
            # Train with historical data
            historical_features = await self._get_historical_features(equipment_id, sensor_type)
            if len(historical_features) > 10:
                self.anomaly_detectors[feature_key].fit(historical_features)
        
        detector = self.anomaly_detectors[feature_key]
        
        if not features:
            return {'anomaly_detected': False, 'anomaly_score': 0.0}
        
        # Convert features to array
        feature_array = np.array(list(features.values())).reshape(1, -1)
        
        # Detect anomaly
        anomaly_prediction = detector.predict(feature_array)
        anomaly_score = detector.decision_function(feature_array)[0]
        
        return {
            'anomaly_detected': anomaly_prediction[0] == -1,
            'anomaly_score': float(anomaly_score),
            'features_analyzed': list(features.keys())
        }
    
    async def _get_historical_features(self, equipment_id: str, 
                                     sensor_type: SensorType) -> np.ndarray:
        """Get historical features for training anomaly detector"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get historical feature data (simplified - in production, store features separately)
        cursor.execute("""
            SELECT features FROM sensor_analysis_history 
            WHERE equipment_id = ? AND sensor_type = ?
            ORDER BY analysis_date DESC LIMIT 100
        """, (equipment_id, sensor_type.value))
        
        results = cursor.fetchall()
        conn.close()
        
        if not results:
            # Generate synthetic historical data for demo
            return np.random.normal(0, 1, (50, 10))
        
        feature_arrays = []
        for result in results:
            features_dict = json.loads(result[0])
            feature_arrays.append(list(features_dict.values()))
        
        return np.array(feature_arrays)
    
    async def _calculate_health_indicators(self, readings: pd.DataFrame,
                                         sensor_type: SensorType) -> Dict[str, float]:
        """Calculate equipment health indicators"""
        if readings.empty:
            return {}
        
        values = readings['value'].values
        
        # Generic health indicators
        indicators = {
            'overall_health': min(1.0, max(0.0, 1.0 - (np.std(values) / np.mean(values)) if np.mean(values) > 0 else 0)),
            'stability_index': 1.0 / (1.0 + np.std(values)) if np.std(values) > 0 else 1.0,
            'degradation_indicator': self._calculate_degradation_indicator(values)
        }
        
        # Sensor-specific indicators
        if sensor_type == SensorType.VIBRATION:
            indicators.update({
                'vibration_severity': self._classify_vibration_severity(np.mean(values)),
                'bearing_health': self._estimate_bearing_health(values),
                'alignment_health': self._estimate_alignment_health(values)
            })
        elif sensor_type == SensorType.TEMPERATURE:
            indicators.update({
                'thermal_stability': 1.0 / (1.0 + np.std(values)),
                'overheating_risk': self._calculate_overheating_risk(values)
            })
        
        return indicators
    
    def _calculate_degradation_indicator(self, values: np.ndarray) -> float:
        """Calculate equipment degradation indicator"""
        if len(values) < 10:
            return 0.0
        
        # Use trend analysis to estimate degradation
        x = np.arange(len(values))
        slope, _, r_value, _, _ = stats.linregress(x, values)
        
        # Higher absolute slope indicates more degradation
        degradation = min(1.0, abs(slope) * len(values) / (np.mean(values) if np.mean(values) > 0 else 1))
        
        return float(degradation)
    
    def _classify_vibration_severity(self, rms_velocity: float) -> float:
        """Classify vibration severity based on ISO 10816"""
        # Simplified classification (mm/s RMS)
        if rms_velocity < 2.8:
            return 0.2  # Good
        elif rms_velocity < 7.1:
            return 0.5  # Satisfactory
        elif rms_velocity < 18.0:
            return 0.8  # Unsatisfactory
        else:
            return 1.0  # Unacceptable
    
    def _estimate_bearing_health(self, vibration_values: np.ndarray) -> float:
        """Estimate bearing health from vibration data"""
        # Simplified bearing health estimation
        rms = np.sqrt(np.mean(vibration_values**2))
        peak_factor = np.max(vibration_values) / rms if rms > 0 else 1
        
        # Higher peak factor often indicates bearing defects
        health_score = max(0.0, 1.0 - (peak_factor - 3.0) / 10.0)
        return float(health_score)
    
    def _estimate_alignment_health(self, vibration_values: np.ndarray) -> float:
        """Estimate alignment health from vibration data"""
        # Misalignment often shows up as increased 2x and 3x harmonics
        # Simplified estimation based on overall vibration level
        rms = np.sqrt(np.mean(vibration_values**2))
        
        # Lower RMS typically indicates better alignment
        alignment_score = max(0.0, 1.0 - rms / 10.0)
        return float(alignment_score)
    
    def _calculate_overheating_risk(self, temperature_values: np.ndarray) -> float:
        """Calculate overheating risk from temperature data"""
        max_temp = np.max(temperature_values)
        mean_temp = np.mean(temperature_values)
        
        # Simplified risk calculation (assuming normal operating range 20-80°C)
        if max_temp > 100:
            return 1.0  # High risk
        elif max_temp > 90:
            return 0.8
        elif max_temp > 80:
            return 0.5
        else:
            return 0.2
    
    async def _analyze_trends(self, readings: pd.DataFrame,
                            sensor_type: SensorType) -> Dict[str, Any]:
        """Analyze trends in sensor data"""
        if readings.empty or len(readings) < 5:
            return {'trend': 'insufficient_data'}
        
        values = readings['value'].values
        timestamps = readings.index
        
        # Calculate trend
        x = np.arange(len(values))
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, values)
        
        # Classify trend
        if abs(slope) < std_err:
            trend_direction = 'stable'
        elif slope > 0:
            trend_direction = 'increasing'
        else:
            trend_direction = 'decreasing'
        
        # Calculate trend strength
        trend_strength = min(1.0, abs(r_value))
        
        # Detect change points
        change_points = self._detect_change_points(values)
        
        return {
            'trend': trend_direction,
            'slope': float(slope),
            'strength': float(trend_strength),
            'r_squared': float(r_value**2),
            'p_value': float(p_value),
            'change_points': change_points,
            'recent_average': float(np.mean(values[-10:])) if len(values) >= 10 else float(np.mean(values))
        }
    
    def _detect_change_points(self, values: np.ndarray) -> List[int]:
        """Detect change points in time series data"""
        if len(values) < 10:
            return []
        
        # Simple change point detection using sliding window
        window_size = max(5, len(values) // 10)
        change_points = []
        
        for i in range(window_size, len(values) - window_size):
            before = values[i-window_size:i]
            after = values[i:i+window_size]
            
            # Use t-test to detect significant change
            statistic, p_value = stats.ttest_ind(before, after)
            
            if p_value < 0.01:  # Significant change
                change_points.append(i)
        
        return change_points
    
    async def _assess_data_quality(self, readings: pd.DataFrame) -> Dict[str, Any]:
        """Assess quality of sensor data"""
        if readings.empty:
            return {'quality': 'no_data', 'score': 0.0}
        
        total_readings = len(readings)
        good_readings = len(readings[readings['quality_flag'] == 'good'])
        
        # Calculate missing data percentage
        expected_readings = total_readings  # Simplified
        missing_percentage = max(0, (expected_readings - total_readings) / expected_readings * 100)
        
        # Calculate data quality score
        quality_score = (good_readings / total_readings) * (1 - missing_percentage / 100)
        
        if quality_score >= 0.9:
            quality_level = 'excellent'
        elif quality_score >= 0.7:
            quality_level = 'good'
        elif quality_score >= 0.5:
            quality_level = 'fair'
        else:
            quality_level = 'poor'
        
        return {
            'quality': quality_level,
            'score': float(quality_score),
            'total_readings': total_readings,
            'good_readings': good_readings,
            'missing_percentage': float(missing_percentage)
        }


class FailurePredictionEngine:
    """Machine learning engine for predicting equipment failures"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.models = {}
        self.scalers = {}
        self.feature_importance = {}
    
    async def predict_failure(self, equipment_id: str) -> FailurePrediction:
        """Predict equipment failure"""
        # Get current equipment state
        equipment_features = await self._get_equipment_features(equipment_id)
        
        if not equipment_features:
            return self._create_default_prediction(equipment_id)
        
        # Get or train prediction model
        model = await self._get_or_train_model(equipment_id)
        
        # Make prediction
        feature_vector = self._prepare_features(equipment_features)
        
        failure_probability = model.predict_proba([feature_vector])[0][1]  # Probability of failure
        confidence = model.predict_proba([feature_vector])[0].max()
        
        # Estimate time to failure
        time_to_failure = await self._estimate_time_to_failure(
            equipment_id, failure_probability, equipment_features
        )
        
        # Identify contributing factors
        contributing_factors = await self._identify_contributing_factors(
            equipment_id, equipment_features
        )
        
        # Generate recommendations
        recommendations = await self._generate_recommendations(
            equipment_id, failure_probability, contributing_factors
        )
        
        # Determine most likely failure mode
        failure_mode = await self._predict_failure_mode(equipment_id, equipment_features)
        
        prediction_id = f"PRED_{equipment_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        return FailurePrediction(
            prediction_id=prediction_id,
            equipment_id=equipment_id,
            failure_mode=failure_mode,
            probability=float(failure_probability),
            confidence=float(confidence),
            time_to_failure_days=float(time_to_failure),
            contributing_factors=contributing_factors,
            recommended_actions=recommendations,
            prediction_date=datetime.now(),
            model_version="1.0"
        )
    
    async def _get_equipment_features(self, equipment_id: str) -> Dict[str, float]:
        """Get current features for equipment"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get equipment basic info
        cursor.execute("""
            SELECT operating_hours, 
                   julianday('now') - julianday(last_maintenance_date) as days_since_maintenance,
                   julianday('now') - julianday(installation_date) as equipment_age_days,
                   criticality_score
            FROM equipment 
            WHERE equipment_id = ?
        """, (equipment_id,))
        
        equipment_row = cursor.fetchone()
        
        if not equipment_row:
            conn.close()
            return {}
        
        features = {
            'operating_hours': equipment_row[0] or 0,
            'days_since_maintenance': equipment_row[1] or 0,
            'equipment_age_days': equipment_row[2] or 0,
            'criticality_score': equipment_row[3] or 0.5
        }
        
        # Get latest sensor analysis results
        cursor.execute("""
            SELECT sensor_type, features, health_indicators
            FROM sensor_analysis_history 
            WHERE equipment_id = ? 
            ORDER BY analysis_date DESC LIMIT 10
        """, (equipment_id,))
        
        sensor_results = cursor.fetchall()
        
        for sensor_type, features_json, health_json in sensor_results:
            try:
                sensor_features = json.loads(features_json)
                health_indicators = json.loads(health_json)
                
                # Add sensor-specific features with prefix
                prefix = f"{sensor_type}_"
                for key, value in sensor_features.items():
                    if isinstance(value, (int, float)):
                        features[f"{prefix}{key}"] = value
                
                for key, value in health_indicators.items():
                    if isinstance(value, (int, float)):
                        features[f"{prefix}health_{key}"] = value
                        
            except (json.JSONDecodeError, TypeError):
                continue
        
        conn.close()
        return features
    
    def _create_default_prediction(self, equipment_id: str) -> FailurePrediction:
        """Create default prediction when insufficient data"""
        prediction_id = f"PRED_{equipment_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        return FailurePrediction(
            prediction_id=prediction_id,
            equipment_id=equipment_id,
            failure_mode=FailureMode.BEARING_FAILURE,  # Default
            probability=0.1,  # Low default probability
            confidence=0.3,   # Low confidence
            time_to_failure_days=90.0,  # Default 3 months
            contributing_factors=['Insufficient data for analysis'],
            recommended_actions=['Collect more sensor data', 'Perform manual inspection'],
            prediction_date=datetime.now(),
            model_version="1.0"
        )
    
    async def _get_or_train_model(self, equipment_id: str):
        """Get existing model or train new one"""
        if equipment_id in self.models:
            return self.models[equipment_id]
        
        # Get training data
        training_data = await self._get_training_data(equipment_id)
        
        if len(training_data) < 20:  # Insufficient training data
            # Use generic model or create simple heuristic-based model
            return self._create_heuristic_model()
        
        # Prepare features and labels
        X, y = self._prepare_training_data(training_data)
        
        # Train model
        model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            class_weight='balanced'
        )
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        # Scale features
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        # Train model
        model.fit(X_train_scaled, y_train)
        
        # Store model and scaler
        self.models[equipment_id] = model
        self.scalers[equipment_id] = scaler
        
        # Store feature importance
        if hasattr(model, 'feature_importances_'):
            self.feature_importance[equipment_id] = model.feature_importances_
        
        return model
    
    def _create_heuristic_model(self):
        """Create simple heuristic-based model"""
        class HeuristicModel:
            def predict_proba(self, X):
                # Simple heuristic based on operating hours and time since maintenance
                predictions = []
                for features in X:
                    # Assume features[0] is operating_hours, features[1] is days_since_maintenance
                    operating_hours = features[0] if len(features) > 0 else 0
                    days_since_maintenance = features[1] if len(features) > 1 else 0
                    
                    # Simple failure probability calculation
                    base_prob = 0.01  # 1% base failure probability
                    
                    # Increase probability with operating hours
                    hours_factor = min(0.5, operating_hours / 10000)  # Max 50% increase
                    
                    # Increase probability with time since maintenance
                    maintenance_factor = min(0.3, days_since_maintenance / 365)  # Max 30% increase
                    
                    failure_prob = min(0.95, base_prob + hours_factor + maintenance_factor)
                    
                    predictions.append([1 - failure_prob, failure_prob])
                
                return np.array(predictions)
        
        return HeuristicModel()
    
    async def _get_training_data(self, equipment_id: str) -> List[Dict[str, Any]]:
        """Get historical training data for equipment"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get historical failure events and normal operation periods
        cursor.execute("""
            SELECT 
                maintenance_date,
                maintenance_type,
                description,
                operating_hours_at_maintenance
            FROM maintenance_history 
            WHERE equipment_id = ? 
            ORDER BY maintenance_date
        """, (equipment_id,))
        
        maintenance_events = cursor.fetchall()
        conn.close()
        
        # Create training samples (simplified)
        training_data = []
        
        for event in maintenance_events:
            is_failure = event[1] in ['corrective', 'emergency']
            
            # Create training sample
            sample = {
                'operating_hours': event[3] or 0,
                'days_since_maintenance': 30,  # Simplified
                'equipment_age_days': 365,     # Simplified
                'failure': 1 if is_failure else 0
            }
            
            training_data.append(sample)
        
        return training_data
    
    def _prepare_training_data(self, training_data: List[Dict[str, Any]]) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare training data for model"""
        features = []
        labels = []
        
        for sample in training_data:
            feature_vector = [
                sample.get('operating_hours', 0),
                sample.get('days_since_maintenance', 0),
                sample.get('equipment_age_days', 0)
            ]
            
            features.append(feature_vector)
            labels.append(sample.get('failure', 0))
        
        return np.array(features), np.array(labels)
    
    def _prepare_features(self, equipment_features: Dict[str, float]) -> List[float]:
        """Prepare features for prediction"""
        # Extract key features in consistent order
        feature_vector = [
            equipment_features.get('operating_hours', 0),
            equipment_features.get('days_since_maintenance', 0),
            equipment_features.get('equipment_age_days', 0),
            equipment_features.get('criticality_score', 0.5)
        ]
        
        # Add sensor-based features (simplified)
        vibration_health = equipment_features.get('vibration_health_overall_health', 1.0)
        temperature_stability = equipment_features.get('temperature_health_thermal_stability', 1.0)
        
        feature_vector.extend([vibration_health, temperature_stability])
        
        return feature_vector
    
    async def _estimate_time_to_failure(self, equipment_id: str, failure_probability: float,
                                      equipment_features: Dict[str, float]) -> float:
        """Estimate time to failure in days"""
        if failure_probability < 0.1:
            return 365.0  # Low risk, assume 1 year
        elif failure_probability < 0.3:
            return 180.0  # Medium-low risk, 6 months
        elif failure_probability < 0.7:
            return 90.0   # Medium-high risk, 3 months
        else:
            return 30.0   # High risk, 1 month
    
    async def _identify_contributing_factors(self, equipment_id: str,
                                           equipment_features: Dict[str, float]) -> List[str]:
        """Identify factors contributing to failure risk"""
        factors = []
        
        # Check operating hours
        operating_hours = equipment_features.get('operating_hours', 0)
        if operating_hours > 8000:
            factors.append('High operating hours')
        
        # Check maintenance overdue
        days_since_maintenance = equipment_features.get('days_since_maintenance', 0)
        if days_since_maintenance > 180:
            factors.append('Overdue maintenance')
        
        # Check equipment age
        equipment_age = equipment_features.get('equipment_age_days', 0)
        if equipment_age > 3650:  # 10 years
            factors.append('Equipment aging')
        
        # Check sensor health indicators
        overall_health = equipment_features.get('vibration_health_overall_health', 1.0)
        if overall_health < 0.7:
            factors.append('Poor vibration health')
        
        thermal_stability = equipment_features.get('temperature_health_thermal_stability', 1.0)
        if thermal_stability < 0.8:
            factors.append('Temperature instability')
        
        if not factors:
            factors.append('Normal operating conditions')
        
        return factors
    
    async def _generate_recommendations(self, equipment_id: str, failure_probability: float,
                                      contributing_factors: List[str]) -> List[str]:
        """Generate maintenance recommendations"""
        recommendations = []
        
        if failure_probability > 0.7:
            recommendations.append('Schedule immediate inspection')
            recommendations.append('Consider emergency maintenance')
        elif failure_probability > 0.3:
            recommendations.append('Schedule preventive maintenance within 30 days')
            recommendations.append('Increase monitoring frequency')
        else:
            recommendations.append('Continue normal operation')
            recommendations.append('Monitor trends closely')
        
        # Factor-specific recommendations
        for factor in contributing_factors:
            if 'vibration' in factor.lower():
                recommendations.append('Check bearing condition and alignment')
            elif 'temperature' in factor.lower():
                recommendations.append('Inspect cooling system and lubrication')
            elif 'maintenance' in factor.lower():
                recommendations.append('Schedule overdue maintenance immediately')
            elif 'aging' in factor.lower():
                recommendations.append('Consider equipment replacement planning')
        
        return list(set(recommendations))  # Remove duplicates
    
    async def _predict_failure_mode(self, equipment_id: str,
                                  equipment_features: Dict[str, float]) -> FailureMode:
        """Predict most likely failure mode"""
        # Simplified failure mode prediction based on dominant issues
        
        vibration_health = equipment_features.get('vibration_health_overall_health', 1.0)
        bearing_health = equipment_features.get('vibration_health_bearing_health', 1.0)
        temperature_risk = equipment_features.get('temperature_health_overheating_risk', 0.0)
        
        if bearing_health < 0.5:
            return FailureMode.BEARING_FAILURE
        elif temperature_risk > 0.7:
            return FailureMode.OVERHEATING
        elif vibration_health < 0.6:
            return FailureMode.MISALIGNMENT
        else:
            return FailureMode.BEARING_FAILURE  # Default most common failure


class MaintenanceScheduler:
    """Scheduler for optimizing maintenance tasks"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    async def optimize_maintenance_schedule(self, time_horizon_days: int = 90) -> List[MaintenanceTask]:
        """Optimize maintenance schedule for given time horizon"""
        # Get all equipment that needs attention
        equipment_list = await self._get_equipment_requiring_maintenance()
        
        # Get failure predictions
        predictions = {}
        for equipment_id in equipment_list:
            # In production, this would use the FailurePredictionEngine
            prediction = self._simulate_failure_prediction(equipment_id)
            predictions[equipment_id] = prediction
        
        # Generate maintenance tasks
        tasks = []
        task_counter = 1
        
        for equipment_id, prediction in predictions.items():
            if prediction['probability'] > 0.2:  # Threshold for maintenance scheduling
                task = await self._create_maintenance_task(
                    equipment_id, prediction, task_counter
                )
                tasks.append(task)
                task_counter += 1
        
        # Sort tasks by priority and urgency
        tasks.sort(key=lambda x: (x.priority.value, x.scheduled_date))
        
        return tasks
    
    async def _get_equipment_requiring_maintenance(self) -> List[str]:
        """Get equipment that may require maintenance"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT equipment_id FROM equipment 
            WHERE status IN ('operational', 'warning')
            ORDER BY criticality_score DESC
        """)
        
        equipment_ids = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        return equipment_ids
    
    def _simulate_failure_prediction(self, equipment_id: str) -> Dict[str, Any]:
        """Simulate failure prediction (for demo purposes)"""
        # Random failure probability for demonstration
        probability = np.random.beta(2, 8)  # Skewed toward lower probabilities
        
        return {
            'probability': probability,
            'time_to_failure_days': np.random.uniform(30, 365),
            'failure_mode': np.random.choice(list(FailureMode)).value,
            'contributing_factors': ['Simulated factor']
        }
    
    async def _create_maintenance_task(self, equipment_id: str, 
                                     prediction: Dict[str, Any],
                                     task_counter: int) -> MaintenanceTask:
        """Create maintenance task based on prediction"""
        probability = prediction['probability']
        time_to_failure = prediction['time_to_failure_days']
        
        # Determine task priority
        if probability > 0.8:
            priority = Priority.CRITICAL
            maintenance_type = MaintenanceType.EMERGENCY
            schedule_days = 1
        elif probability > 0.5:
            priority = Priority.HIGH
            maintenance_type = MaintenanceType.PREDICTIVE
            schedule_days = min(7, int(time_to_failure * 0.1))
        elif probability > 0.2:
            priority = Priority.MEDIUM
            maintenance_type = MaintenanceType.PREVENTIVE
            schedule_days = min(30, int(time_to_failure * 0.3))
        else:
            priority = Priority.LOW
            maintenance_type = MaintenanceType.CONDITION_BASED
            schedule_days = 60
        
        # Generate task details
        task_id = f"MAINT_{equipment_id}_{task_counter:04d}"
        
        failure_mode = FailureMode(prediction['failure_mode'])
        description = f"Maintenance for {equipment_id} - {failure_mode.value.replace('_', ' ').title()}"
        
        # Estimate duration and cost
        duration_hours = self._estimate_task_duration(maintenance_type, failure_mode)
        cost = self._estimate_task_cost(maintenance_type, failure_mode, duration_hours)
        
        # Required parts and skills
        parts = self._get_required_parts(failure_mode)
        skills = self._get_required_skills(maintenance_type, failure_mode)
        
        return MaintenanceTask(
            task_id=task_id,
            equipment_id=equipment_id,
            maintenance_type=maintenance_type,
            priority=priority,
            description=description,
            estimated_duration_hours=duration_hours,
            estimated_cost=cost,
            required_parts=parts,
            required_skills=skills,
            scheduled_date=datetime.now() + timedelta(days=schedule_days),
            completion_date=None,
            assigned_technician=None,
            work_order_status='scheduled',
            failure_modes_addressed=[failure_mode]
        )
    
    def _estimate_task_duration(self, maintenance_type: MaintenanceType,
                               failure_mode: FailureMode) -> float:
        """Estimate task duration in hours"""
        base_hours = {
            MaintenanceType.PREVENTIVE: 2.0,
            MaintenanceType.PREDICTIVE: 4.0,
            MaintenanceType.CORRECTIVE: 6.0,
            MaintenanceType.CONDITION_BASED: 3.0,
            MaintenanceType.EMERGENCY: 8.0
        }
        
        complexity_multiplier = {
            FailureMode.BEARING_FAILURE: 2.0,
            FailureMode.MISALIGNMENT: 1.5,
            FailureMode.IMBALANCE: 1.2,
            FailureMode.LOOSENESS: 1.0,
            FailureMode.BELT_WEAR: 0.8,
            FailureMode.OVERHEATING: 1.5,
            FailureMode.ELECTRICAL_FAULT: 3.0,
            FailureMode.LUBRICATION_FAILURE: 1.0,
            FailureMode.FATIGUE: 2.5,
            FailureMode.CORROSION: 2.0
        }
        
        base = base_hours.get(maintenance_type, 4.0)
        multiplier = complexity_multiplier.get(failure_mode, 1.0)
        
        return base * multiplier
    
    def _estimate_task_cost(self, maintenance_type: MaintenanceType,
                           failure_mode: FailureMode, duration_hours: float) -> float:
        """Estimate task cost"""
        labor_rate = 75.0  # Per hour
        
        parts_cost = {
            FailureMode.BEARING_FAILURE: 500.0,
            FailureMode.MISALIGNMENT: 100.0,
            FailureMode.IMBALANCE: 150.0,
            FailureMode.LOOSENESS: 50.0,
            FailureMode.BELT_WEAR: 200.0,
            FailureMode.OVERHEATING: 300.0,
            FailureMode.ELECTRICAL_FAULT: 400.0,
            FailureMode.LUBRICATION_FAILURE: 50.0,
            FailureMode.FATIGUE: 800.0,
            FailureMode.CORROSION: 600.0
        }
        
        labor_cost = duration_hours * labor_rate
        parts = parts_cost.get(failure_mode, 100.0)
        
        return labor_cost + parts
    
    def _get_required_parts(self, failure_mode: FailureMode) -> List[str]:
        """Get required parts for failure mode"""
        parts_map = {
            FailureMode.BEARING_FAILURE: ['bearing', 'lubricant', 'seals'],
            FailureMode.MISALIGNMENT: ['shims', 'coupling'],
            FailureMode.IMBALANCE: ['weights', 'balancing_equipment'],
            FailureMode.LOOSENESS: ['bolts', 'nuts', 'washers'],
            FailureMode.BELT_WEAR: ['belt', 'tensioner'],
            FailureMode.OVERHEATING: ['thermal_compound', 'fan', 'coolant'],
            FailureMode.ELECTRICAL_FAULT: ['wiring', 'connectors', 'fuses'],
            FailureMode.LUBRICATION_FAILURE: ['lubricant', 'filters'],
            FailureMode.FATIGUE: ['replacement_parts', 'reinforcement'],
            FailureMode.CORROSION: ['protective_coating', 'replacement_metal']
        }
        
        return parts_map.get(failure_mode, ['general_parts'])
    
    def _get_required_skills(self, maintenance_type: MaintenanceType,
                            failure_mode: FailureMode) -> List[str]:
        """Get required skills for task"""
        skills_map = {
            FailureMode.BEARING_FAILURE: ['mechanical', 'alignment'],
            FailureMode.MISALIGNMENT: ['alignment', 'precision_measurement'],
            FailureMode.IMBALANCE: ['balancing', 'vibration_analysis'],
            FailureMode.LOOSENESS: ['mechanical', 'torque_specification'],
            FailureMode.BELT_WEAR: ['mechanical', 'belt_installation'],
            FailureMode.OVERHEATING: ['thermal_analysis', 'cooling_systems'],
            FailureMode.ELECTRICAL_FAULT: ['electrical', 'troubleshooting'],
            FailureMode.LUBRICATION_FAILURE: ['lubrication', 'filtration'],
            FailureMode.FATIGUE: ['welding', 'structural_repair'],
            FailureMode.CORROSION: ['surface_treatment', 'protective_coatings']
        }
        
        return skills_map.get(failure_mode, ['general_mechanical'])


class PredictiveMaintenanceSystem:
    """Main predictive maintenance system"""
    
    def __init__(self, db_path: str = "predictive_maintenance.db"):
        self.db_path = db_path
        self.sensor_processor = SensorDataProcessor(db_path)
        self.prediction_engine = FailurePredictionEngine(db_path)
        self.scheduler = MaintenanceScheduler(db_path)
        self._initialize_database()
    
    def _initialize_database(self):
        """Initialize predictive maintenance database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Equipment table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS equipment (
                equipment_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT,
                manufacturer TEXT,
                model TEXT,
                serial_number TEXT,
                location TEXT,
                installation_date TIMESTAMP,
                last_maintenance_date TIMESTAMP,
                next_scheduled_maintenance TIMESTAMP,
                operating_hours REAL,
                status TEXT,
                criticality_score REAL,
                specifications TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Sensor readings table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sensor_readings (
                reading_id TEXT PRIMARY KEY,
                equipment_id TEXT,
                sensor_type TEXT,
                timestamp TIMESTAMP,
                value REAL,
                unit TEXT,
                quality_flag TEXT,
                calibration_date TIMESTAMP,
                FOREIGN KEY (equipment_id) REFERENCES equipment (equipment_id)
            )
        """)
        
        # Sensor analysis history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sensor_analysis_history (
                analysis_id TEXT PRIMARY KEY,
                equipment_id TEXT,
                sensor_type TEXT,
                analysis_date TIMESTAMP,
                features TEXT,  -- JSON
                health_indicators TEXT,  -- JSON
                anomalies TEXT,  -- JSON
                trends TEXT,  -- JSON
                FOREIGN KEY (equipment_id) REFERENCES equipment (equipment_id)
            )
        """)
        
        # Maintenance tasks table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS maintenance_tasks (
                task_id TEXT PRIMARY KEY,
                equipment_id TEXT,
                maintenance_type TEXT,
                priority TEXT,
                description TEXT,
                estimated_duration_hours REAL,
                estimated_cost REAL,
                required_parts TEXT,  -- JSON
                required_skills TEXT,  -- JSON
                scheduled_date TIMESTAMP,
                completion_date TIMESTAMP,
                assigned_technician TEXT,
                work_order_status TEXT,
                failure_modes_addressed TEXT,  -- JSON
                FOREIGN KEY (equipment_id) REFERENCES equipment (equipment_id)
            )
        """)
        
        # Maintenance history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS maintenance_history (
                history_id TEXT PRIMARY KEY,
                equipment_id TEXT,
                maintenance_date TIMESTAMP,
                maintenance_type TEXT,
                description TEXT,
                technician TEXT,
                duration_hours REAL,
                cost REAL,
                parts_used TEXT,  -- JSON
                operating_hours_at_maintenance REAL,
                notes TEXT,
                FOREIGN KEY (equipment_id) REFERENCES equipment (equipment_id)
            )
        """)
        
        # Failure predictions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS failure_predictions (
                prediction_id TEXT PRIMARY KEY,
                equipment_id TEXT,
                failure_mode TEXT,
                probability REAL,
                confidence REAL,
                time_to_failure_days REAL,
                contributing_factors TEXT,  -- JSON
                recommended_actions TEXT,  -- JSON
                prediction_date TIMESTAMP,
                model_version TEXT,
                FOREIGN KEY (equipment_id) REFERENCES equipment (equipment_id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    async def run_maintenance_cycle(self) -> Dict[str, Any]:
        """Run complete predictive maintenance cycle"""
        cycle_start = datetime.now()
        
        # Get all equipment
        equipment_list = await self._get_all_equipment()
        
        # Process sensor data for each equipment
        sensor_analyses = {}
        for equipment_id in equipment_list:
            try:
                # Process different sensor types
                for sensor_type in [SensorType.VIBRATION, SensorType.TEMPERATURE]:
                    analysis = await self.sensor_processor.process_sensor_data(
                        equipment_id, sensor_type, 24
                    )
                    
                    if analysis.get('status') != 'insufficient_data':
                        key = f"{equipment_id}_{sensor_type.value}"
                        sensor_analyses[key] = analysis
                        
                        # Store analysis results
                        await self._store_sensor_analysis(analysis)
                        
            except Exception as e:
                print(f"Error processing sensors for {equipment_id}: {e}")
        
        # Generate failure predictions
        predictions = {}
        for equipment_id in equipment_list:
            try:
                prediction = await self.prediction_engine.predict_failure(equipment_id)
                predictions[equipment_id] = prediction
                
                # Store prediction
                await self._store_prediction(prediction)
                
            except Exception as e:
                print(f"Error predicting failure for {equipment_id}: {e}")
        
        # Generate maintenance schedule
        maintenance_tasks = await self.scheduler.optimize_maintenance_schedule(90)
        
        # Store maintenance tasks
        stored_tasks = 0
        for task in maintenance_tasks:
            if await self._store_maintenance_task(task):
                stored_tasks += 1
        
        processing_time = (datetime.now() - cycle_start).total_seconds()
        
        return {
            'cycle_start': cycle_start,
            'processing_time_seconds': processing_time,
            'equipment_processed': len(equipment_list),
            'sensor_analyses': len(sensor_analyses),
            'predictions_generated': len(predictions),
            'maintenance_tasks_scheduled': stored_tasks,
            'high_priority_tasks': len([t for t in maintenance_tasks if t.priority in [Priority.CRITICAL, Priority.HIGH]])
        }
    
    async def _get_all_equipment(self) -> List[str]:
        """Get all equipment IDs"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT equipment_id FROM equipment WHERE status != 'down'")
        equipment_ids = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        return equipment_ids
    
    async def _store_sensor_analysis(self, analysis: Dict[str, Any]):
        """Store sensor analysis results"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        analysis_id = f"ANALYSIS_{analysis['equipment_id']}_{analysis['sensor_type']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        cursor.execute("""
            INSERT OR REPLACE INTO sensor_analysis_history 
            (analysis_id, equipment_id, sensor_type, analysis_date, features, 
             health_indicators, anomalies, trends)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            analysis_id, analysis['equipment_id'], analysis['sensor_type'],
            analysis['analysis_timestamp'], json.dumps(analysis.get('features', {})),
            json.dumps(analysis.get('health_indicators', {})),
            json.dumps(analysis.get('anomalies', {})),
            json.dumps(analysis.get('trends', {}))
        ))
        
        conn.commit()
        conn.close()
    
    async def _store_prediction(self, prediction: FailurePrediction):
        """Store failure prediction"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO failure_predictions 
            (prediction_id, equipment_id, failure_mode, probability, confidence,
             time_to_failure_days, contributing_factors, recommended_actions,
             prediction_date, model_version)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            prediction.prediction_id, prediction.equipment_id, prediction.failure_mode.value,
            prediction.probability, prediction.confidence, prediction.time_to_failure_days,
            json.dumps(prediction.contributing_factors), json.dumps(prediction.recommended_actions),
            prediction.prediction_date, prediction.model_version
        ))
        
        conn.commit()
        conn.close()
    
    async def _store_maintenance_task(self, task: MaintenanceTask) -> bool:
        """Store maintenance task"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO maintenance_tasks 
                (task_id, equipment_id, maintenance_type, priority, description,
                 estimated_duration_hours, estimated_cost, required_parts, required_skills,
                 scheduled_date, completion_date, assigned_technician, work_order_status,
                 failure_modes_addressed)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                task.task_id, task.equipment_id, task.maintenance_type.value,
                task.priority.value, task.description, task.estimated_duration_hours,
                task.estimated_cost, json.dumps(task.required_parts),
                json.dumps(task.required_skills), task.scheduled_date,
                task.completion_date, task.assigned_technician, task.work_order_status,
                json.dumps([fm.value for fm in task.failure_modes_addressed])
            ))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"Error storing maintenance task: {e}")
            return False
    
    async def get_maintenance_dashboard(self) -> Dict[str, Any]:
        """Get predictive maintenance dashboard"""
        dashboard_data = {
            'dashboard_date': datetime.now(),
            'equipment_status': await self._get_equipment_status_summary(),
            'maintenance_summary': await self._get_maintenance_summary(),
            'prediction_summary': await self._get_prediction_summary(),
            'upcoming_tasks': await self._get_upcoming_tasks(),
            'critical_alerts': await self._get_critical_alerts(),
            'performance_metrics': await self._calculate_performance_metrics()
        }
        
        return dashboard_data
    
    async def _get_equipment_status_summary(self) -> Dict[str, Any]:
        """Get equipment status summary"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT status, COUNT(*) as count
            FROM equipment
            GROUP BY status
        """)
        
        status_counts = dict(cursor.fetchall())
        
        cursor.execute("SELECT COUNT(*) FROM equipment")
        total_equipment = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'total_equipment': total_equipment,
            'operational': status_counts.get('operational', 0),
            'warning': status_counts.get('warning', 0),
            'critical': status_counts.get('critical', 0),
            'down': status_counts.get('down', 0),
            'maintenance': status_counts.get('maintenance', 0)
        }
    
    async def _get_maintenance_summary(self) -> Dict[str, Any]:
        """Get maintenance task summary"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT priority, COUNT(*) as count
            FROM maintenance_tasks
            WHERE work_order_status = 'scheduled'
            GROUP BY priority
        """)
        
        priority_counts = dict(cursor.fetchall())
        
        cursor.execute("""
            SELECT COUNT(*) FROM maintenance_tasks
            WHERE work_order_status = 'scheduled'
            AND scheduled_date <= date('now', '+7 days')
        """)
        
        due_this_week = cursor.fetchone()[0]
        conn.close()
        
        return {
            'total_scheduled': sum(priority_counts.values()),
            'critical_priority': priority_counts.get('critical', 0),
            'high_priority': priority_counts.get('high', 0),
            'medium_priority': priority_counts.get('medium', 0),
            'low_priority': priority_counts.get('low', 0),
            'due_this_week': due_this_week
        }
    
    async def _get_prediction_summary(self) -> Dict[str, Any]:
        """Get failure prediction summary"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                COUNT(*) as total_predictions,
                AVG(probability) as avg_probability,
                COUNT(CASE WHEN probability > 0.7 THEN 1 END) as high_risk_equipment,
                COUNT(CASE WHEN time_to_failure_days < 30 THEN 1 END) as immediate_attention
            FROM failure_predictions
            WHERE prediction_date >= date('now', '-1 day')
        """)
        
        result = cursor.fetchone()
        conn.close()
        
        return {
            'total_predictions': result[0] if result else 0,
            'average_failure_probability': result[1] if result and result[1] else 0,
            'high_risk_equipment': result[2] if result else 0,
            'immediate_attention_required': result[3] if result else 0
        }
    
    async def _get_upcoming_tasks(self, days_ahead: int = 14) -> List[Dict[str, Any]]:
        """Get upcoming maintenance tasks"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        end_date = datetime.now() + timedelta(days=days_ahead)
        
        cursor.execute("""
            SELECT task_id, equipment_id, maintenance_type, priority, 
                   description, scheduled_date, estimated_duration_hours
            FROM maintenance_tasks
            WHERE work_order_status = 'scheduled'
            AND scheduled_date <= ?
            ORDER BY priority DESC, scheduled_date
            LIMIT 10
        """, (end_date,))
        
        tasks = cursor.fetchall()
        conn.close()
        
        return [
            {
                'task_id': row[0],
                'equipment_id': row[1],
                'maintenance_type': row[2],
                'priority': row[3],
                'description': row[4],
                'scheduled_date': row[5],
                'estimated_duration_hours': row[6]
            }
            for row in tasks
        ]
    
    async def _get_critical_alerts(self) -> List[Dict[str, Any]]:
        """Get critical maintenance alerts"""
        alerts = []
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # High failure probability alerts
        cursor.execute("""
            SELECT equipment_id, failure_mode, probability, time_to_failure_days
            FROM failure_predictions
            WHERE probability > 0.7
            AND prediction_date >= date('now', '-1 day')
            ORDER BY probability DESC
        """)
        
        high_risk_predictions = cursor.fetchall()
        
        for pred in high_risk_predictions:
            alerts.append({
                'type': 'high_failure_risk',
                'equipment_id': pred[0],
                'message': f"High failure risk ({pred[2]:.1%}) for {pred[1]}",
                'urgency': 'critical',
                'time_to_failure_days': pred[3]
            })
        
        # Overdue maintenance alerts
        cursor.execute("""
            SELECT equipment_id, name, last_maintenance_date
            FROM equipment
            WHERE julianday('now') - julianday(last_maintenance_date) > 180
            OR last_maintenance_date IS NULL
        """)
        
        overdue_equipment = cursor.fetchall()
        
        for equip in overdue_equipment:
            alerts.append({
                'type': 'overdue_maintenance',
                'equipment_id': equip[0],
                'equipment_name': equip[1],
                'message': f"Maintenance overdue for {equip[1]}",
                'urgency': 'high',
                'days_overdue': (datetime.now() - datetime.fromisoformat(equip[2])).days if equip[2] else None
            })
        
        conn.close()
        return alerts[:10]  # Limit to top 10 alerts
    
    async def _calculate_performance_metrics(self) -> MaintenanceMetrics:
        """Calculate maintenance performance metrics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Mean Time Between Failures (MTBF)
        cursor.execute("""
            SELECT AVG(operating_hours_at_maintenance)
            FROM maintenance_history
            WHERE maintenance_type IN ('corrective', 'emergency')
            AND maintenance_date >= date('now', '-365 days')
        """)
        mtbf_result = cursor.fetchone()
        mtbf = mtbf_result[0] if mtbf_result and mtbf_result[0] else 2000.0
        
        # Mean Time To Repair (MTTR)
        cursor.execute("""
            SELECT AVG(duration_hours)
            FROM maintenance_history
            WHERE maintenance_type IN ('corrective', 'emergency')
            AND maintenance_date >= date('now', '-365 days')
        """)
        mttr_result = cursor.fetchone()
        mttr = mttr_result[0] if mttr_result and mttr_result[0] else 4.0
        
        # Overall Equipment Effectiveness (simplified calculation)
        availability = mtbf / (mtbf + mttr) if (mtbf + mttr) > 0 else 0.95
        performance = 0.95  # Assume 95% performance efficiency
        quality = 0.98      # Assume 98% quality rate
        oee = availability * performance * quality
        
        # Maintenance type breakdown
        cursor.execute("""
            SELECT 
                COUNT(CASE WHEN maintenance_type IN ('preventive', 'predictive') THEN 1 END) as planned,
                COUNT(*) as total
            FROM maintenance_history
            WHERE maintenance_date >= date('now', '-365 days')
        """)
        maintenance_breakdown = cursor.fetchone()
        planned_percentage = (maintenance_breakdown[0] / maintenance_breakdown[1] * 100) if maintenance_breakdown[1] > 0 else 80.0
        emergency_percentage = 100.0 - planned_percentage
        
        # Cost metrics (simplified)
        cursor.execute("""
            SELECT AVG(cost) FROM maintenance_history
            WHERE maintenance_date >= date('now', '-90 days')
        """)
        avg_cost_result = cursor.fetchone()
        avg_cost = avg_cost_result[0] if avg_cost_result and avg_cost_result[0] else 500.0
        
        conn.close()
        
        return MaintenanceMetrics(
            metrics_date=datetime.now(),
            mean_time_between_failures=mtbf,
            mean_time_to_repair=mttr,
            overall_equipment_effectiveness=oee,
            planned_maintenance_percentage=planned_percentage,
            emergency_maintenance_percentage=emergency_percentage,
            maintenance_cost_per_hour=avg_cost / mttr if mttr > 0 else avg_cost,
            parts_availability=0.92,  # Simplified
            technician_utilization=0.75  # Simplified
        )
    
    async def add_sample_data(self):
        """Add sample data for testing"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Sample equipment
        sample_equipment = [
            ('EQ001', 'Main Production Line Motor', 'Motor', 'Siemens', 'IE3-1LE1', 'SN001', 'Production Floor A', datetime.now() - timedelta(days=365*3), datetime.now() - timedelta(days=90), datetime.now() + timedelta(days=90), 8500.0, 'operational', 0.9),
            ('EQ002', 'Conveyor Belt Drive', 'Drive System', 'ABB', 'M2BA', 'SN002', 'Production Floor A', datetime.now() - timedelta(days=365*2), datetime.now() - timedelta(days=60), datetime.now() + timedelta(days=120), 6200.0, 'warning', 0.8),
            ('EQ003', 'Hydraulic Press', 'Press', 'Bosch Rexroth', 'A4VG', 'SN003', 'Production Floor B', datetime.now() - timedelta(days=365*5), datetime.now() - timedelta(days=180), datetime.now() + timedelta(days=30), 12000.0, 'critical', 0.95),
            ('EQ004', 'Cooling System Pump', 'Pump', 'Grundfos', 'CR15', 'SN004', 'Utility Room', datetime.now() - timedelta(days=365), datetime.now() - timedelta(days=30), datetime.now() + timedelta(days=90), 3800.0, 'operational', 0.7),
            ('EQ005', 'Air Compressor', 'Compressor', 'Atlas Copco', 'GA22', 'SN005', 'Utility Room', datetime.now() - timedelta(days=365*4), datetime.now() - timedelta(days=120), datetime.now() + timedelta(days=60), 9500.0, 'warning', 0.85)
        ]
        
        for equip in sample_equipment:
            cursor.execute("""
                INSERT OR REPLACE INTO equipment 
                (equipment_id, name, type, manufacturer, model, serial_number, location,
                 installation_date, last_maintenance_date, next_scheduled_maintenance,
                 operating_hours, status, criticality_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, equip)
        
        # Sample sensor readings
        base_time = datetime.now() - timedelta(hours=48)
        
        for i in range(48):  # 48 hours of hourly data
            timestamp = base_time + timedelta(hours=i)
            
            for equip_id in ['EQ001', 'EQ002', 'EQ003', 'EQ004', 'EQ005']:
                # Vibration readings (mm/s RMS)
                base_vibration = {'EQ001': 2.0, 'EQ002': 3.5, 'EQ003': 1.8, 'EQ004': 2.2, 'EQ005': 2.8}[equip_id]
                vibration = base_vibration + np.random.normal(0, base_vibration * 0.2)
                
                cursor.execute("""
                    INSERT OR REPLACE INTO sensor_readings 
                    (reading_id, equipment_id, sensor_type, timestamp, value, unit, quality_flag)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    f"VIB_{equip_id}_{i:03d}", equip_id, 'vibration', timestamp, 
                    vibration, 'mm/s', 'good'
                ))
                
                # Temperature readings (°C)
                base_temp = {'EQ001': 65, 'EQ002': 70, 'EQ003': 55, 'EQ004': 45, 'EQ005': 75}[equip_id]
                temperature = base_temp + np.random.normal(0, 5)
                
                cursor.execute("""
                    INSERT OR REPLACE INTO sensor_readings 
                    (reading_id, equipment_id, sensor_type, timestamp, value, unit, quality_flag)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    f"TEMP_{equip_id}_{i:03d}", equip_id, 'temperature', timestamp,
                    temperature, 'celsius', 'good'
                ))
        
        # Sample maintenance history
        sample_maintenance = [
            ('HIST001', 'EQ001', datetime.now() - timedelta(days=90), 'preventive', 'Scheduled bearing replacement', 'Tech001', 4.0, 850.0, '["bearing", "lubricant"]', 7500.0),
            ('HIST002', 'EQ002', datetime.now() - timedelta(days=60), 'corrective', 'Belt replacement due to wear', 'Tech002', 2.5, 320.0, '["belt", "tensioner"]', 5800.0),
            ('HIST003', 'EQ003', datetime.now() - timedelta(days=180), 'preventive', 'Hydraulic system service', 'Tech001', 6.0, 1200.0, '["hydraulic_fluid", "filters"]', 10500.0),
            ('HIST004', 'EQ004', datetime.now() - timedelta(days=30), 'predictive', 'Impeller replacement', 'Tech003', 3.0, 450.0, '["impeller", "seals"]', 3600.0),
            ('HIST005', 'EQ005', datetime.now() - timedelta(days=120), 'emergency', 'Compressor shutdown repair', 'Tech002', 8.0, 1800.0, '["compressor_valve", "gaskets"]', 8900.0)
        ]
        
        for maint in sample_maintenance:
            cursor.execute("""
                INSERT OR REPLACE INTO maintenance_history 
                (history_id, equipment_id, maintenance_date, maintenance_type, description,
                 technician, duration_hours, cost, parts_used, operating_hours_at_maintenance)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, maint)
        
        conn.commit()
        conn.close()


async def main():
    """Example usage of Predictive Maintenance System"""
    maintenance_system = PredictiveMaintenanceSystem()
    
    # Add sample data
    await maintenance_system.add_sample_data()
    print("Added sample maintenance data")
    
    # Run maintenance cycle
    results = await maintenance_system.run_maintenance_cycle()
    
    print(f"\n" + "="*50)
    print(f"PREDICTIVE MAINTENANCE CYCLE RESULTS")
    print(f"="*50)
    
    print(f"Processing Time: {results['processing_time_seconds']:.2f} seconds")
    print(f"Equipment Processed: {results['equipment_processed']}")
    print(f"Sensor Analyses: {results['sensor_analyses']}")
    print(f"Predictions Generated: {results['predictions_generated']}")
    print(f"Maintenance Tasks Scheduled: {results['maintenance_tasks_scheduled']}")
    print(f"High Priority Tasks: {results['high_priority_tasks']}")
    
    # Get maintenance dashboard
    dashboard = await maintenance_system.get_maintenance_dashboard()
    
    print(f"\n" + "="*50)
    print(f"MAINTENANCE DASHBOARD")
    print(f"="*50)
    
    print(f"\nEquipment Status:")
    equipment_status = dashboard['equipment_status']
    print(f"Total Equipment: {equipment_status['total_equipment']}")
    print(f"Operational: {equipment_status['operational']}")
    print(f"Warning: {equipment_status['warning']}")
    print(f"Critical: {equipment_status['critical']}")
    print(f"Down: {equipment_status['down']}")
    
    print(f"\nMaintenance Summary:")
    maint_summary = dashboard['maintenance_summary']
    print(f"Total Scheduled: {maint_summary['total_scheduled']}")
    print(f"Critical Priority: {maint_summary['critical_priority']}")
    print(f"High Priority: {maint_summary['high_priority']}")
    print(f"Due This Week: {maint_summary['due_this_week']}")
    
    print(f"\nPrediction Summary:")
    pred_summary = dashboard['prediction_summary']
    print(f"Total Predictions: {pred_summary['total_predictions']}")
    print(f"Average Failure Probability: {pred_summary['average_failure_probability']:.1%}")
    print(f"High Risk Equipment: {pred_summary['high_risk_equipment']}")
    print(f"Immediate Attention Required: {pred_summary['immediate_attention_required']}")
    
    print(f"\nPerformance Metrics:")
    metrics = dashboard['performance_metrics']
    print(f"MTBF: {metrics.mean_time_between_failures:.0f} hours")
    print(f"MTTR: {metrics.mean_time_to_repair:.1f} hours")
    print(f"OEE: {metrics.overall_equipment_effectiveness:.1%}")
    print(f"Planned Maintenance: {metrics.planned_maintenance_percentage:.1f}%")
    
    print(f"\nCritical Alerts:")
    for alert in dashboard['critical_alerts'][:5]:
        print(f"- {alert['message']} (Equipment: {alert['equipment_id']})")
    
    print(f"\nUpcoming Tasks:")
    for task in dashboard['upcoming_tasks'][:5]:
        print(f"- {task['description']} ({task['priority']} priority, {task['scheduled_date']})")


if __name__ == "__main__":
    asyncio.run(main())