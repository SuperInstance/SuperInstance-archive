"""
Health Trend Analysis for ActiveLog Health Suite
Advanced analytics engine for identifying health patterns, trends, and insights
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from scipy import stats
from scipy.signal import find_peaks
import json
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import IsolationForest

from ..devices.wearable_ingestion import HealthDataPoint, DataType, wearable_ingestion

logger = logging.getLogger(__name__)

class TrendType(Enum):
    """Types of health trends"""
    INCREASING = "increasing"
    DECREASING = "decreasing"
    STABLE = "stable"
    CYCLICAL = "cyclical"
    VOLATILE = "volatile"
    ANOMALOUS = "anomalous"

class TrendSignificance(Enum):
    """Significance levels for trends"""
    VERY_HIGH = "very_high"     # p < 0.001
    HIGH = "high"               # p < 0.01
    MODERATE = "moderate"       # p < 0.05
    LOW = "low"                 # p < 0.1
    NONE = "none"              # p >= 0.1

class AnalysisType(Enum):
    """Types of health analysis"""
    TREND_ANALYSIS = "trend_analysis"
    CORRELATION_ANALYSIS = "correlation_analysis"
    ANOMALY_DETECTION = "anomaly_detection"
    PATTERN_RECOGNITION = "pattern_recognition"
    PREDICTIVE_MODELING = "predictive_modeling"
    COMPARATIVE_ANALYSIS = "comparative_analysis"
    CIRCADIAN_ANALYSIS = "circadian_analysis"
    SEASONAL_ANALYSIS = "seasonal_analysis"

class TimeFrame(Enum):
    """Time frames for analysis"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    CUSTOM = "custom"

@dataclass
class TrendResult:
    """Result from trend analysis"""
    data_type: DataType
    trend_type: TrendType
    significance: TrendSignificance
    slope: float
    r_squared: float
    p_value: float
    confidence_interval: Tuple[float, float]
    start_date: datetime
    end_date: datetime
    data_points: int
    trend_description: str
    recommendations: List[str] = field(default_factory=list)

@dataclass
class CorrelationResult:
    """Result from correlation analysis"""
    data_type_1: DataType
    data_type_2: DataType
    correlation_coefficient: float
    p_value: float
    correlation_type: str  # "positive", "negative", "none"
    significance: TrendSignificance
    time_lag: int = 0  # Days of lag if applicable
    description: str = ""

@dataclass
class AnomalyResult:
    """Result from anomaly detection"""
    data_type: DataType
    timestamp: datetime
    value: float
    anomaly_score: float
    severity: str  # "low", "medium", "high", "critical"
    expected_value: Optional[float] = None
    description: str = ""
    potential_causes: List[str] = field(default_factory=list)

@dataclass
class PatternResult:
    """Result from pattern recognition"""
    pattern_type: str
    data_types: List[DataType]
    pattern_description: str
    confidence: float
    frequency: str  # "daily", "weekly", "monthly"
    next_occurrence: Optional[datetime] = None
    recommendations: List[str] = field(default_factory=list)

@dataclass
class HealthInsight:
    """Comprehensive health insight"""
    insight_id: str
    title: str
    description: str
    insight_type: str
    severity: str
    confidence: float
    data_types_involved: List[DataType]
    time_period: Tuple[datetime, datetime]
    recommendations: List[str] = field(default_factory=list)
    supporting_data: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

class HealthTrendAnalyzer:
    """Advanced health trend analysis engine"""
    
    def __init__(self):
        self.data_cache: Dict[str, pd.DataFrame] = {}
        self.trend_cache: Dict[str, List[TrendResult]] = {}
        self.correlation_cache: Dict[str, List[CorrelationResult]] = {}
        self.anomaly_detectors: Dict[DataType, IsolationForest] = {}
        self.baseline_models: Dict[DataType, Dict[str, Any]] = {}
        
        # Initialize anomaly detectors
        self._initialize_anomaly_detectors()
        
        # Start background analysis
        asyncio.create_task(self._background_analysis())
    
    def _initialize_anomaly_detectors(self):
        """Initialize anomaly detection models for each data type"""
        for data_type in DataType:
            self.anomaly_detectors[data_type] = IsolationForest(
                contamination=0.1,  # Expect 10% outliers
                random_state=42
            )
    
    async def analyze_trends(
        self,
        user_id: str,
        data_types: Optional[List[DataType]] = None,
        time_frame: TimeFrame = TimeFrame.MONTHLY,
        custom_period: Optional[Tuple[datetime, datetime]] = None
    ) -> List[TrendResult]:
        """Analyze health trends for a user"""
        
        try:
            # Get data
            data = await self._get_user_data(user_id, data_types, time_frame, custom_period)
            
            if data.empty:
                return []
            
            trends = []
            
            # Analyze trends for each data type
            for data_type in data['data_type'].unique():
                type_data = data[data['data_type'] == data_type].copy()
                
                if len(type_data) < 3:  # Need at least 3 points for trend analysis
                    continue
                
                trend_result = await self._analyze_single_trend(
                    DataType(data_type), type_data, time_frame
                )
                
                if trend_result:
                    trends.append(trend_result)
            
            # Cache results
            cache_key = f"{user_id}_{time_frame.value}_{datetime.now().date()}"
            self.trend_cache[cache_key] = trends
            
            logger.info(f"Analyzed {len(trends)} trends for user {user_id}")
            return trends
            
        except Exception as e:
            logger.error(f"Trend analysis failed for user {user_id}: {e}")
            return []
    
    async def _analyze_single_trend(
        self,
        data_type: DataType,
        data: pd.DataFrame,
        time_frame: TimeFrame
    ) -> Optional[TrendResult]:
        """Analyze trend for a single data type"""
        
        try:
            # Prepare data
            data = data.sort_values('timestamp')
            data['days_since_start'] = (data['timestamp'] - data['timestamp'].min()).dt.days
            
            # Extract numeric values
            numeric_values = []
            for value in data['value']:
                if isinstance(value, (int, float)):
                    numeric_values.append(value)
                elif isinstance(value, dict):
                    # For complex data types like sleep, extract primary metric
                    if data_type == DataType.SLEEP and 'duration' in value:
                        numeric_values.append(value['duration'])
                    else:
                        numeric_values.append(0)
                else:
                    numeric_values.append(0)
            
            if len(numeric_values) < 3:
                return None
            
            data['numeric_value'] = numeric_values
            
            # Perform linear regression
            X = data['days_since_start'].values.reshape(-1, 1)
            y = data['numeric_value'].values
            
            model = LinearRegression()
            model.fit(X, y)
            
            slope = model.coef_[0]
            r_squared = model.score(X, y)
            
            # Calculate p-value
            n = len(y)
            y_pred = model.predict(X)
            mse = np.mean((y - y_pred) ** 2)
            se_slope = np.sqrt(mse / np.sum((X.flatten() - np.mean(X)) ** 2))
            t_stat = slope / se_slope
            p_value = 2 * (1 - stats.t.cdf(abs(t_stat), n - 2))
            
            # Determine trend type
            trend_type = self._classify_trend_type(slope, r_squared, data['numeric_value'])
            significance = self._classify_significance(p_value)
            
            # Calculate confidence interval
            alpha = 0.05
            t_critical = stats.t.ppf(1 - alpha/2, n - 2)
            margin_error = t_critical * se_slope
            confidence_interval = (slope - margin_error, slope + margin_error)
            
            # Generate description and recommendations
            description = self._generate_trend_description(data_type, trend_type, slope, significance)
            recommendations = self._generate_trend_recommendations(data_type, trend_type, slope)
            
            return TrendResult(
                data_type=data_type,
                trend_type=trend_type,
                significance=significance,
                slope=slope,
                r_squared=r_squared,
                p_value=p_value,
                confidence_interval=confidence_interval,
                start_date=data['timestamp'].min(),
                end_date=data['timestamp'].max(),
                data_points=len(data),
                trend_description=description,
                recommendations=recommendations
            )
            
        except Exception as e:
            logger.warning(f"Failed to analyze trend for {data_type.value}: {e}")
            return None
    
    async def analyze_correlations(
        self,
        user_id: str,
        data_types: Optional[List[DataType]] = None,
        time_frame: TimeFrame = TimeFrame.MONTHLY
    ) -> List[CorrelationResult]:
        """Analyze correlations between different health metrics"""
        
        try:
            # Get data
            data = await self._get_user_data(user_id, data_types, time_frame)
            
            if data.empty:
                return []
            
            correlations = []
            
            # Get unique data types
            available_types = data['data_type'].unique()
            
            # Analyze correlations between all pairs
            for i, type1 in enumerate(available_types):
                for type2 in available_types[i+1:]:
                    correlation = await self._analyze_correlation_pair(
                        DataType(type1), DataType(type2), data
                    )
                    
                    if correlation:
                        correlations.append(correlation)
            
            # Cache results
            cache_key = f"{user_id}_correlations_{time_frame.value}_{datetime.now().date()}"
            self.correlation_cache[cache_key] = correlations
            
            logger.info(f"Analyzed {len(correlations)} correlations for user {user_id}")
            return correlations
            
        except Exception as e:
            logger.error(f"Correlation analysis failed for user {user_id}: {e}")
            return []
    
    async def _analyze_correlation_pair(
        self,
        data_type1: DataType,
        data_type2: DataType,
        data: pd.DataFrame
    ) -> Optional[CorrelationResult]:
        """Analyze correlation between two data types"""
        
        try:
            # Filter data for both types
            data1 = data[data['data_type'] == data_type1.value].copy()
            data2 = data[data['data_type'] == data_type2.value].copy()
            
            if len(data1) < 3 or len(data2) < 3:
                return None
            
            # Align data by timestamp (daily aggregation)
            data1['date'] = data1['timestamp'].dt.date
            data2['date'] = data2['timestamp'].dt.date
            
            # Extract numeric values
            data1['numeric_value'] = data1['value'].apply(self._extract_numeric_value)
            data2['numeric_value'] = data2['value'].apply(self._extract_numeric_value)
            
            # Aggregate by date
            daily1 = data1.groupby('date')['numeric_value'].mean()
            daily2 = data2.groupby('date')['numeric_value'].mean()
            
            # Find common dates
            common_dates = set(daily1.index) & set(daily2.index)
            
            if len(common_dates) < 3:
                return None
            
            # Align data
            values1 = [daily1[date] for date in sorted(common_dates)]
            values2 = [daily2[date] for date in sorted(common_dates)]
            
            # Calculate correlation
            correlation_coef, p_value = stats.pearsonr(values1, values2)
            
            # Classify correlation
            if abs(correlation_coef) >= 0.7:
                correlation_type = "strong_positive" if correlation_coef > 0 else "strong_negative"
            elif abs(correlation_coef) >= 0.3:
                correlation_type = "moderate_positive" if correlation_coef > 0 else "moderate_negative"
            elif abs(correlation_coef) >= 0.1:
                correlation_type = "weak_positive" if correlation_coef > 0 else "weak_negative"
            else:
                correlation_type = "none"
            
            significance = self._classify_significance(p_value)
            
            # Generate description
            description = self._generate_correlation_description(
                data_type1, data_type2, correlation_coef, significance
            )
            
            return CorrelationResult(
                data_type_1=data_type1,
                data_type_2=data_type2,
                correlation_coefficient=correlation_coef,
                p_value=p_value,
                correlation_type=correlation_type,
                significance=significance,
                description=description
            )
            
        except Exception as e:
            logger.warning(f"Failed to analyze correlation between {data_type1.value} and {data_type2.value}: {e}")
            return None
    
    async def detect_anomalies(
        self,
        user_id: str,
        data_types: Optional[List[DataType]] = None,
        sensitivity: float = 0.1
    ) -> List[AnomalyResult]:
        """Detect anomalies in health data"""
        
        try:
            # Get recent data
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
            data = await self._get_user_data(user_id, data_types, TimeFrame.CUSTOM, (start_date, end_date))
            
            if data.empty:
                return []
            
            anomalies = []
            
            # Detect anomalies for each data type
            for data_type in data['data_type'].unique():
                type_data = data[data['data_type'] == data_type].copy()
                
                if len(type_data) < 5:  # Need sufficient data for anomaly detection
                    continue
                
                type_anomalies = await self._detect_type_anomalies(
                    DataType(data_type), type_data, sensitivity
                )
                anomalies.extend(type_anomalies)
            
            logger.info(f"Detected {len(anomalies)} anomalies for user {user_id}")
            return anomalies
            
        except Exception as e:
            logger.error(f"Anomaly detection failed for user {user_id}: {e}")
            return []
    
    async def _detect_type_anomalies(
        self,
        data_type: DataType,
        data: pd.DataFrame,
        sensitivity: float
    ) -> List[AnomalyResult]:
        """Detect anomalies for a specific data type"""
        
        try:
            # Extract numeric values
            data['numeric_value'] = data['value'].apply(self._extract_numeric_value)
            data = data.dropna(subset=['numeric_value'])
            
            if len(data) < 5:
                return []
            
            # Prepare data for anomaly detection
            X = data['numeric_value'].values.reshape(-1, 1)
            
            # Train/update anomaly detector
            detector = self.anomaly_detectors[data_type]
            detector.contamination = sensitivity
            detector.fit(X)
            
            # Detect anomalies
            anomaly_scores = detector.decision_function(X)
            is_anomaly = detector.predict(X) == -1
            
            anomalies = []
            
            for i, (is_anom, score) in enumerate(zip(is_anomaly, anomaly_scores)):
                if is_anom:
                    # Calculate severity
                    severity = self._classify_anomaly_severity(score, data_type)
                    
                    # Estimate expected value
                    normal_values = X[~is_anomaly]
                    expected_value = np.median(normal_values) if len(normal_values) > 0 else None
                    
                    # Generate description
                    description = self._generate_anomaly_description(
                        data_type, data.iloc[i]['numeric_value'], expected_value, severity
                    )
                    
                    # Generate potential causes
                    potential_causes = self._generate_anomaly_causes(data_type, severity)
                    
                    anomalies.append(AnomalyResult(
                        data_type=data_type,
                        timestamp=data.iloc[i]['timestamp'],
                        value=data.iloc[i]['numeric_value'],
                        anomaly_score=score,
                        severity=severity,
                        expected_value=expected_value,
                        description=description,
                        potential_causes=potential_causes
                    ))
            
            return anomalies
            
        except Exception as e:
            logger.warning(f"Anomaly detection failed for {data_type.value}: {e}")
            return []
    
    async def recognize_patterns(
        self,
        user_id: str,
        data_types: Optional[List[DataType]] = None,
        pattern_types: Optional[List[str]] = None
    ) -> List[PatternResult]:
        """Recognize patterns in health data"""
        
        try:
            # Get data for pattern analysis
            data = await self._get_user_data(user_id, data_types, TimeFrame.MONTHLY)
            
            if data.empty:
                return []
            
            patterns = []
            
            # Detect circadian patterns
            circadian_patterns = await self._detect_circadian_patterns(data)
            patterns.extend(circadian_patterns)
            
            # Detect weekly patterns
            weekly_patterns = await self._detect_weekly_patterns(data)
            patterns.extend(weekly_patterns)
            
            # Detect activity patterns
            activity_patterns = await self._detect_activity_patterns(data)
            patterns.extend(activity_patterns)
            
            logger.info(f"Recognized {len(patterns)} patterns for user {user_id}")
            return patterns
            
        except Exception as e:
            logger.error(f"Pattern recognition failed for user {user_id}: {e}")
            return []
    
    async def generate_health_insights(
        self,
        user_id: str,
        time_frame: TimeFrame = TimeFrame.WEEKLY
    ) -> List[HealthInsight]:
        """Generate comprehensive health insights"""
        
        try:
            insights = []
            
            # Analyze trends
            trends = await self.analyze_trends(user_id, time_frame=time_frame)
            
            # Analyze correlations
            correlations = await self.analyze_correlations(user_id, time_frame=time_frame)
            
            # Detect anomalies
            anomalies = await self.detect_anomalies(user_id)
            
            # Recognize patterns
            patterns = await self.recognize_patterns(user_id)
            
            # Generate insights from trends
            for trend in trends:
                if trend.significance in [TrendSignificance.HIGH, TrendSignificance.VERY_HIGH]:
                    insight = self._create_trend_insight(trend)
                    insights.append(insight)
            
            # Generate insights from significant correlations
            for correlation in correlations:
                if correlation.significance in [TrendSignificance.HIGH, TrendSignificance.VERY_HIGH]:
                    insight = self._create_correlation_insight(correlation)
                    insights.append(insight)
            
            # Generate insights from anomalies
            critical_anomalies = [a for a in anomalies if a.severity in ['high', 'critical']]
            if critical_anomalies:
                insight = self._create_anomaly_insight(critical_anomalies)
                insights.append(insight)
            
            # Generate insights from patterns
            for pattern in patterns:
                if pattern.confidence > 0.8:
                    insight = self._create_pattern_insight(pattern)
                    insights.append(insight)
            
            # Sort by severity and confidence
            insights.sort(key=lambda x: (
                {'critical': 4, 'high': 3, 'medium': 2, 'low': 1}.get(x.severity, 0),
                x.confidence
            ), reverse=True)
            
            logger.info(f"Generated {len(insights)} health insights for user {user_id}")
            return insights
            
        except Exception as e:
            logger.error(f"Health insight generation failed for user {user_id}: {e}")
            return []
    
    async def _get_user_data(
        self,
        user_id: str,
        data_types: Optional[List[DataType]] = None,
        time_frame: TimeFrame = TimeFrame.MONTHLY,
        custom_period: Optional[Tuple[datetime, datetime]] = None
    ) -> pd.DataFrame:
        """Get user health data for analysis"""
        
        # Calculate time period
        if custom_period:
            start_date, end_date = custom_period
        else:
            end_date = datetime.now()
            if time_frame == TimeFrame.DAILY:
                start_date = end_date - timedelta(days=1)
            elif time_frame == TimeFrame.WEEKLY:
                start_date = end_date - timedelta(weeks=1)
            elif time_frame == TimeFrame.MONTHLY:
                start_date = end_date - timedelta(days=30)
            elif time_frame == TimeFrame.QUARTERLY:
                start_date = end_date - timedelta(days=90)
            else:  # YEARLY
                start_date = end_date - timedelta(days=365)
        
        # Get data from all user devices
        all_data = []
        
        # This would normally query from a database or cache
        # For now, get from wearable ingestion system
        devices = await wearable_ingestion.list_devices()
        
        for device_id in devices.keys():
            device_data = await wearable_ingestion.get_device_data(
                device_id, data_types, start_date
            )
            all_data.extend(device_data)
        
        if not all_data:
            return pd.DataFrame()
        
        # Convert to DataFrame
        data_records = []
        for dp in all_data:
            if dp.timestamp >= start_date and dp.timestamp <= end_date:
                data_records.append({
                    'timestamp': dp.timestamp,
                    'data_type': dp.data_type.value,
                    'value': dp.value,
                    'unit': dp.unit,
                    'device_id': dp.device_id,
                    'confidence': dp.confidence
                })
        
        return pd.DataFrame(data_records)
    
    def _extract_numeric_value(self, value: Any) -> Optional[float]:
        """Extract numeric value from various data types"""
        if isinstance(value, (int, float)):
            return float(value)
        elif isinstance(value, dict):
            # Handle complex values like sleep data
            if 'duration' in value:
                return float(value['duration'])
            elif 'average' in value:
                return float(value['average'])
            elif 'total' in value:
                return float(value['total'])
        return None
    
    def _classify_trend_type(self, slope: float, r_squared: float, values: pd.Series) -> TrendType:
        """Classify the type of trend"""
        if r_squared < 0.1:
            return TrendType.VOLATILE
        
        if abs(slope) < 0.01:
            return TrendType.STABLE
        
        # Check for cyclical patterns
        if self._is_cyclical(values):
            return TrendType.CYCLICAL
        
        if slope > 0:
            return TrendType.INCREASING
        else:
            return TrendType.DECREASING
    
    def _is_cyclical(self, values: pd.Series) -> bool:
        """Check if data shows cyclical patterns"""
        try:
            # Simple peak detection for cyclical patterns
            peaks, _ = find_peaks(values, distance=len(values)//10)
            valleys, _ = find_peaks(-values, distance=len(values)//10)
            
            return len(peaks) >= 2 and len(valleys) >= 2
        except:
            return False
    
    def _classify_significance(self, p_value: float) -> TrendSignificance:
        """Classify statistical significance"""
        if p_value < 0.001:
            return TrendSignificance.VERY_HIGH
        elif p_value < 0.01:
            return TrendSignificance.HIGH
        elif p_value < 0.05:
            return TrendSignificance.MODERATE
        elif p_value < 0.1:
            return TrendSignificance.LOW
        else:
            return TrendSignificance.NONE
    
    def _classify_anomaly_severity(self, score: float, data_type: DataType) -> str:
        """Classify anomaly severity"""
        # Lower scores indicate more anomalous
        if score < -0.5:
            return "critical"
        elif score < -0.3:
            return "high"
        elif score < -0.1:
            return "medium"
        else:
            return "low"
    
    def _generate_trend_description(
        self,
        data_type: DataType,
        trend_type: TrendType,
        slope: float,
        significance: TrendSignificance
    ) -> str:
        """Generate human-readable trend description"""
        
        data_name = data_type.value.replace('_', ' ').title()
        
        if trend_type == TrendType.INCREASING:
            direction = "increasing"
            rate = "rapidly" if abs(slope) > 1 else "gradually"
        elif trend_type == TrendType.DECREASING:
            direction = "decreasing"
            rate = "rapidly" if abs(slope) > 1 else "gradually"
        elif trend_type == TrendType.STABLE:
            return f"Your {data_name} has remained stable over the analysis period."
        elif trend_type == TrendType.CYCLICAL:
            return f"Your {data_name} shows cyclical patterns with regular ups and downs."
        else:
            return f"Your {data_name} shows volatile patterns with significant variation."
        
        confidence = {
            TrendSignificance.VERY_HIGH: "very high",
            TrendSignificance.HIGH: "high",
            TrendSignificance.MODERATE: "moderate",
            TrendSignificance.LOW: "low",
            TrendSignificance.NONE: "low"
        }.get(significance, "low")
        
        return f"Your {data_name} is {direction} {rate} with {confidence} confidence."
    
    def _generate_trend_recommendations(
        self,
        data_type: DataType,
        trend_type: TrendType,
        slope: float
    ) -> List[str]:
        """Generate recommendations based on trend analysis"""
        
        recommendations = []
        
        if data_type == DataType.HEART_RATE:
            if trend_type == TrendType.INCREASING and slope > 0.5:
                recommendations.extend([
                    "Consider increasing cardio exercise to improve heart health",
                    "Monitor stress levels as they may be affecting your heart rate",
                    "Ensure adequate sleep and recovery time"
                ])
            elif trend_type == TrendType.DECREASING and slope < -0.5:
                recommendations.extend([
                    "Great job! Your resting heart rate is improving",
                    "Continue your current fitness routine",
                    "Consider adding strength training to complement cardio"
                ])
        
        elif data_type == DataType.STEPS:
            if trend_type == TrendType.DECREASING:
                recommendations.extend([
                    "Try to increase daily activity gradually",
                    "Set small, achievable step goals",
                    "Consider taking stairs instead of elevators"
                ])
            elif trend_type == TrendType.INCREASING:
                recommendations.extend([
                    "Excellent progress on daily activity!",
                    "Maintain this positive trend",
                    "Consider adding variety to your activities"
                ])
        
        elif data_type == DataType.SLEEP:
            if trend_type == TrendType.DECREASING:
                recommendations.extend([
                    "Focus on sleep hygiene practices",
                    "Establish a consistent bedtime routine",
                    "Avoid screens 1 hour before bed"
                ])
        
        return recommendations
    
    def _generate_correlation_description(
        self,
        data_type1: DataType,
        data_type2: DataType,
        correlation: float,
        significance: TrendSignificance
    ) -> str:
        """Generate correlation description"""
        
        name1 = data_type1.value.replace('_', ' ')
        name2 = data_type2.value.replace('_', ' ')
        
        strength = "strong" if abs(correlation) >= 0.7 else "moderate" if abs(correlation) >= 0.3 else "weak"
        direction = "positive" if correlation > 0 else "negative"
        
        return f"There is a {strength} {direction} correlation between your {name1} and {name2}."
    
    def _generate_anomaly_description(
        self,
        data_type: DataType,
        value: float,
        expected_value: Optional[float],
        severity: str
    ) -> str:
        """Generate anomaly description"""
        
        data_name = data_type.value.replace('_', ' ')
        
        if expected_value is not None:
            diff = abs(value - expected_value)
            if value > expected_value:
                direction = "higher"
            else:
                direction = "lower"
            
            return f"Your {data_name} of {value:.1f} is unusually {direction} than expected ({expected_value:.1f})."
        else:
            return f"Your {data_name} reading of {value:.1f} appears to be unusual."
    
    def _generate_anomaly_causes(self, data_type: DataType, severity: str) -> List[str]:
        """Generate potential causes for anomalies"""
        
        common_causes = {
            DataType.HEART_RATE: [
                "Physical activity or exercise",
                "Stress or anxiety",
                "Caffeine consumption",
                "Medication effects",
                "Sleep deprivation"
            ],
            DataType.BLOOD_PRESSURE: [
                "Stress or anxiety",
                "Sodium intake",
                "Physical activity",
                "Medication timing",
                "Dehydration"
            ],
            DataType.SLEEP: [
                "Stress or anxiety",
                "Screen time before bed",
                "Caffeine or alcohol consumption",
                "Environmental factors",
                "Schedule changes"
            ]
        }
        
        return common_causes.get(data_type, ["Various lifestyle factors", "Environmental changes", "Stress"])
    
    async def _detect_circadian_patterns(self, data: pd.DataFrame) -> List[PatternResult]:
        """Detect circadian rhythm patterns"""
        patterns = []
        
        try:
            # Add hour of day to data
            data['hour'] = data['timestamp'].dt.hour
            
            # Analyze patterns by data type
            for data_type in data['data_type'].unique():
                type_data = data[data['data_type'] == data_type].copy()
                
                if len(type_data) < 24:  # Need at least 24 hours of data
                    continue
                
                # Group by hour and calculate average
                hourly_avg = type_data.groupby('hour')['value'].apply(
                    lambda x: np.mean([self._extract_numeric_value(v) for v in x if self._extract_numeric_value(v) is not None])
                )
                
                # Detect peaks (could indicate pattern)
                if len(hourly_avg) >= 12:
                    peaks, _ = find_peaks(hourly_avg, distance=3)
                    
                    if len(peaks) >= 1:
                        pattern = PatternResult(
                            pattern_type="circadian",
                            data_types=[DataType(data_type)],
                            pattern_description=f"Peak {data_type.replace('_', ' ')} occurs around {peaks[0]:02d}:00",
                            confidence=0.7,
                            frequency="daily",
                            recommendations=[
                                f"Consider timing activities around your natural {data_type.replace('_', ' ')} patterns"
                            ]
                        )
                        patterns.append(pattern)
        
        except Exception as e:
            logger.warning(f"Circadian pattern detection failed: {e}")
        
        return patterns
    
    async def _detect_weekly_patterns(self, data: pd.DataFrame) -> List[PatternResult]:
        """Detect weekly patterns"""
        patterns = []
        
        try:
            # Add day of week to data
            data['day_of_week'] = data['timestamp'].dt.day_name()
            
            for data_type in data['data_type'].unique():
                type_data = data[data['data_type'] == data_type].copy()
                
                if len(type_data) < 7:  # Need at least a week of data
                    continue
                
                # Group by day of week
                daily_avg = type_data.groupby('day_of_week')['value'].apply(
                    lambda x: np.mean([self._extract_numeric_value(v) for v in x if self._extract_numeric_value(v) is not None])
                )
                
                # Check for weekend vs weekday patterns
                weekend_days = ['Saturday', 'Sunday']
                weekday_days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
                
                weekend_avg = daily_avg[daily_avg.index.isin(weekend_days)].mean()
                weekday_avg = daily_avg[daily_avg.index.isin(weekday_days)].mean()
                
                if abs(weekend_avg - weekday_avg) > 0.2 * weekday_avg:
                    direction = "higher" if weekend_avg > weekday_avg else "lower"
                    
                    pattern = PatternResult(
                        pattern_type="weekly",
                        data_types=[DataType(data_type)],
                        pattern_description=f"{data_type.replace('_', ' ').title()} is typically {direction} on weekends",
                        confidence=0.6,
                        frequency="weekly",
                        recommendations=[
                            "Consider maintaining consistent patterns throughout the week"
                        ]
                    )
                    patterns.append(pattern)
        
        except Exception as e:
            logger.warning(f"Weekly pattern detection failed: {e}")
        
        return patterns
    
    async def _detect_activity_patterns(self, data: pd.DataFrame) -> List[PatternResult]:
        """Detect activity-related patterns"""
        patterns = []
        
        # This would analyze relationships between different metrics
        # For example, correlations between steps and heart rate
        
        return patterns
    
    def _create_trend_insight(self, trend: TrendResult) -> HealthInsight:
        """Create insight from trend analysis"""
        
        severity = "high" if trend.significance in [TrendSignificance.HIGH, TrendSignificance.VERY_HIGH] else "medium"
        
        return HealthInsight(
            insight_id=f"trend_{trend.data_type.value}_{datetime.now().timestamp()}",
            title=f"{trend.data_type.value.replace('_', ' ').title()} Trend Alert",
            description=trend.trend_description,
            insight_type="trend",
            severity=severity,
            confidence=1.0 - trend.p_value,
            data_types_involved=[trend.data_type],
            time_period=(trend.start_date, trend.end_date),
            recommendations=trend.recommendations,
            supporting_data={
                'slope': trend.slope,
                'r_squared': trend.r_squared,
                'p_value': trend.p_value
            }
        )
    
    def _create_correlation_insight(self, correlation: CorrelationResult) -> HealthInsight:
        """Create insight from correlation analysis"""
        
        return HealthInsight(
            insight_id=f"correlation_{correlation.data_type_1.value}_{correlation.data_type_2.value}_{datetime.now().timestamp()}",
            title="Health Metric Correlation",
            description=correlation.description,
            insight_type="correlation",
            severity="medium",
            confidence=abs(correlation.correlation_coefficient),
            data_types_involved=[correlation.data_type_1, correlation.data_type_2],
            time_period=(datetime.now() - timedelta(days=30), datetime.now()),
            supporting_data={
                'correlation_coefficient': correlation.correlation_coefficient,
                'p_value': correlation.p_value
            }
        )
    
    def _create_anomaly_insight(self, anomalies: List[AnomalyResult]) -> HealthInsight:
        """Create insight from anomaly detection"""
        
        severity_map = {'critical': 'critical', 'high': 'high', 'medium': 'medium', 'low': 'low'}
        max_severity = max(anomalies, key=lambda x: list(severity_map.keys()).index(x.severity))
        
        return HealthInsight(
            insight_id=f"anomaly_{datetime.now().timestamp()}",
            title="Health Anomaly Detected",
            description=f"Detected {len(anomalies)} unusual readings in your health data",
            insight_type="anomaly",
            severity=max_severity.severity,
            confidence=max(abs(a.anomaly_score) for a in anomalies),
            data_types_involved=list(set(a.data_type for a in anomalies)),
            time_period=(min(a.timestamp for a in anomalies), max(a.timestamp for a in anomalies)),
            supporting_data={
                'anomaly_count': len(anomalies),
                'anomalies': [a.__dict__ for a in anomalies[:5]]  # Limit details
            }
        )
    
    def _create_pattern_insight(self, pattern: PatternResult) -> HealthInsight:
        """Create insight from pattern recognition"""
        
        return HealthInsight(
            insight_id=f"pattern_{pattern.pattern_type}_{datetime.now().timestamp()}",
            title="Health Pattern Identified",
            description=pattern.pattern_description,
            insight_type="pattern",
            severity="medium",
            confidence=pattern.confidence,
            data_types_involved=pattern.data_types,
            time_period=(datetime.now() - timedelta(days=30), datetime.now()),
            recommendations=pattern.recommendations,
            supporting_data={
                'pattern_type': pattern.pattern_type,
                'frequency': pattern.frequency
            }
        )
    
    async def _background_analysis(self):
        """Background task for continuous health analysis"""
        
        while True:
            try:
                # This would run periodic analysis for all users
                # For now, just sleep to prevent busy waiting
                await asyncio.sleep(3600)  # Run every hour
                
            except Exception as e:
                logger.error(f"Background analysis error: {e}")
                await asyncio.sleep(1800)  # Wait 30 minutes on error

# Global singleton instance
health_trend_analyzer = HealthTrendAnalyzer()