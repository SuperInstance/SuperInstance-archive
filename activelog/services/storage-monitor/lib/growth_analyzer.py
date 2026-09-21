#!/usr/bin/env python3
"""
Advanced Growth Detection and Analysis Algorithms
Sophisticated algorithms to detect runaway storage growth patterns
"""

import os
import sqlite3
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
import logging
from pathlib import Path
import json
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures
import warnings
warnings.filterwarnings('ignore')

class GrowthAnalyzer:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.logger = logging.getLogger('GrowthAnalyzer')
        
    def calculate_growth_velocity(self, path: str, hours_back: int = 24) -> Dict[str, float]:
        """
        Calculate growth velocity with multiple algorithms
        Returns growth rates in MB/hour, MB/day, etc.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get size history for the specified time period
                cutoff_time = datetime.now() - timedelta(hours=hours_back)
                
                cursor.execute('''
                    SELECT size_bytes, timestamp FROM directory_history 
                    WHERE path = ? AND timestamp >= ? 
                    ORDER BY timestamp ASC
                ''', (path, cutoff_time))
                
                results = cursor.fetchall()
                
                if len(results) < 3:
                    return {"error": "insufficient_data"}
                
                # Convert to numpy arrays for analysis
                timestamps = []
                sizes = []
                
                for size_bytes, timestamp_str in results:
                    timestamp = datetime.fromisoformat(timestamp_str)
                    timestamps.append(timestamp)
                    sizes.append(size_bytes / 1_000_000)  # Convert to MB
                
                # Calculate time deltas in hours
                time_deltas = [(t - timestamps[0]).total_seconds() / 3600 for t in timestamps]
                time_array = np.array(time_deltas).reshape(-1, 1)
                size_array = np.array(sizes)
                
                # 1. Linear growth rate (simple)
                linear_rate = self._calculate_linear_growth(time_array, size_array)
                
                # 2. Polynomial growth detection (for accelerating growth)
                poly_rate, acceleration = self._calculate_polynomial_growth(time_array, size_array)
                
                # 3. Recent burst detection (last hour vs previous hours)
                burst_rate = self._detect_growth_bursts(timestamps, sizes)
                
                # 4. Exponential growth detection
                exponential_rate = self._detect_exponential_growth(time_array, size_array)
                
                # 5. Pattern-based anomaly detection
                anomaly_score = self._calculate_anomaly_score(sizes)
                
                return {
                    "linear_growth_mb_per_hour": linear_rate,
                    "linear_growth_mb_per_day": linear_rate * 24,
                    "polynomial_growth_mb_per_hour": poly_rate,
                    "acceleration_mb_per_hour_squared": acceleration,
                    "recent_burst_mb_per_hour": burst_rate,
                    "exponential_growth_factor": exponential_rate,
                    "anomaly_score": anomaly_score,
                    "data_points": len(results),
                    "time_span_hours": hours_back,
                    "current_size_mb": sizes[-1] if sizes else 0,
                    "total_growth_mb": sizes[-1] - sizes[0] if len(sizes) >= 2 else 0
                }
                
        except Exception as e:
            self.logger.error(f"Growth velocity calculation failed for {path}: {e}")
            return {"error": str(e)}
    
    def _calculate_linear_growth(self, time_array: np.ndarray, size_array: np.ndarray) -> float:
        """Calculate linear growth rate using linear regression"""
        try:
            if len(size_array) < 2:
                return 0.0
                
            model = LinearRegression()
            model.fit(time_array, size_array)
            
            # Return slope (MB per hour)
            return float(model.coef_[0])
            
        except Exception:
            return 0.0
    
    def _calculate_polynomial_growth(self, time_array: np.ndarray, size_array: np.ndarray) -> Tuple[float, float]:
        """Calculate polynomial growth to detect acceleration"""
        try:
            if len(size_array) < 3:
                return 0.0, 0.0
                
            # Use quadratic polynomial
            poly_features = PolynomialFeatures(degree=2)
            time_poly = poly_features.fit_transform(time_array)
            
            model = LinearRegression()
            model.fit(time_poly, size_array)
            
            # Coefficients: [intercept, linear_coef, quadratic_coef]
            linear_coef = model.coef_[1] if len(model.coef_) > 1 else 0
            quadratic_coef = model.coef_[2] if len(model.coef_) > 2 else 0
            
            return float(linear_coef), float(quadratic_coef * 2)  # 2 * quadratic is acceleration
            
        except Exception:
            return 0.0, 0.0
    
    def _detect_growth_bursts(self, timestamps: List[datetime], sizes: List[float]) -> float:
        """Detect sudden bursts in growth rate"""
        try:
            if len(sizes) < 6:
                return 0.0
                
            # Compare last hour with previous hours
            now = timestamps[-1]
            one_hour_ago = now - timedelta(hours=1)
            
            # Find sizes in last hour and previous hours
            recent_sizes = []
            recent_times = []
            older_sizes = []
            older_times = []
            
            for i, timestamp in enumerate(timestamps):
                if timestamp >= one_hour_ago:
                    recent_sizes.append(sizes[i])
                    recent_times.append(timestamp)
                else:
                    older_sizes.append(sizes[i])
                    older_times.append(timestamp)
            
            if len(recent_sizes) < 2 or len(older_sizes) < 2:
                return 0.0
            
            # Calculate growth rate for recent period
            recent_growth = (recent_sizes[-1] - recent_sizes[0])
            recent_time_span = (recent_times[-1] - recent_times[0]).total_seconds() / 3600
            recent_rate = recent_growth / recent_time_span if recent_time_span > 0 else 0
            
            # Calculate growth rate for older period
            older_growth = (older_sizes[-1] - older_sizes[0])
            older_time_span = (older_times[-1] - older_times[0]).total_seconds() / 3600
            older_rate = older_growth / older_time_span if older_time_span > 0 else 0
            
            # Return burst rate (recent rate - baseline rate)
            return max(0.0, recent_rate - older_rate)
            
        except Exception:
            return 0.0
    
    def _detect_exponential_growth(self, time_array: np.ndarray, size_array: np.ndarray) -> float:
        """Detect exponential growth patterns"""
        try:
            if len(size_array) < 3 or np.min(size_array) <= 0:
                return 1.0  # No exponential growth
                
            # Take log of sizes to linearize exponential growth
            log_sizes = np.log(np.maximum(size_array, 1))  # Avoid log(0)
            
            model = LinearRegression()
            model.fit(time_array, log_sizes)
            
            # Exponential growth factor per hour
            exponential_factor = float(np.exp(model.coef_[0]))
            
            return exponential_factor
            
        except Exception:
            return 1.0
    
    def _calculate_anomaly_score(self, sizes: List[float]) -> float:
        """Calculate anomaly score based on size pattern deviations"""
        try:
            if len(sizes) < 5:
                return 0.0
                
            # Calculate rolling differences
            diffs = np.diff(sizes)
            
            if len(diffs) == 0:
                return 0.0
            
            # Calculate Z-score of recent changes
            mean_diff = np.mean(diffs[:-3]) if len(diffs) > 3 else np.mean(diffs)
            std_diff = np.std(diffs[:-3]) if len(diffs) > 3 else np.std(diffs)
            
            if std_diff == 0:
                return 0.0
            
            # Score recent changes
            recent_diffs = diffs[-3:] if len(diffs) >= 3 else diffs[-1:]
            z_scores = [(diff - mean_diff) / std_diff for diff in recent_diffs]
            
            # Return max absolute Z-score
            return float(max(abs(z) for z in z_scores))
            
        except Exception:
            return 0.0
    
    def predict_future_growth(self, path: str, hours_ahead: int = 24) -> Dict[str, Any]:
        """Predict future storage growth using multiple models"""
        try:
            growth_data = self.calculate_growth_velocity(path, hours_back=48)
            
            if "error" in growth_data:
                return growth_data
            
            current_size_mb = growth_data["current_size_mb"]
            linear_rate = growth_data["linear_growth_mb_per_hour"]
            poly_rate = growth_data["polynomial_growth_mb_per_hour"]
            acceleration = growth_data["acceleration_mb_per_hour_squared"]
            exponential_factor = growth_data["exponential_growth_factor"]
            
            # Linear prediction
            linear_prediction = current_size_mb + (linear_rate * hours_ahead)
            
            # Polynomial prediction (with acceleration)
            poly_prediction = (current_size_mb + 
                             (poly_rate * hours_ahead) + 
                             (0.5 * acceleration * hours_ahead * hours_ahead))
            
            # Exponential prediction
            exp_prediction = current_size_mb * (exponential_factor ** hours_ahead)
            
            # Conservative prediction (lowest growth)
            conservative_prediction = min(linear_prediction, poly_prediction, exp_prediction)
            
            # Aggressive prediction (highest growth) 
            aggressive_prediction = max(linear_prediction, poly_prediction, exp_prediction)
            
            # Risk assessment
            risk_level = self._assess_growth_risk(growth_data, aggressive_prediction)
            
            return {
                "current_size_mb": current_size_mb,
                "hours_ahead": hours_ahead,
                "predictions": {
                    "linear_mb": linear_prediction,
                    "polynomial_mb": poly_prediction,
                    "exponential_mb": exp_prediction,
                    "conservative_mb": conservative_prediction,
                    "aggressive_mb": aggressive_prediction
                },
                "risk_assessment": {
                    "risk_level": risk_level,
                    "predicted_growth_gb": (aggressive_prediction - current_size_mb) / 1000,
                    "time_to_1gb": self._calculate_time_to_size(growth_data, current_size_mb, 1000),
                    "time_to_5gb": self._calculate_time_to_size(growth_data, current_size_mb, 5000),
                    "time_to_10gb": self._calculate_time_to_size(growth_data, current_size_mb, 10000)
                },
                "growth_analysis": growth_data
            }
            
        except Exception as e:
            self.logger.error(f"Growth prediction failed for {path}: {e}")
            return {"error": str(e)}
    
    def _assess_growth_risk(self, growth_data: Dict[str, float], predicted_size_mb: float) -> str:
        """Assess risk level based on growth patterns"""
        try:
            linear_rate = growth_data.get("linear_growth_mb_per_hour", 0)
            acceleration = growth_data.get("acceleration_mb_per_hour_squared", 0)
            burst_rate = growth_data.get("recent_burst_mb_per_hour", 0)
            exponential_factor = growth_data.get("exponential_growth_factor", 1.0)
            anomaly_score = growth_data.get("anomaly_score", 0)
            
            # Risk factors
            risk_score = 0
            
            # High linear growth
            if linear_rate > 50:  # > 50MB/hour
                risk_score += 2
            elif linear_rate > 20:  # > 20MB/hour
                risk_score += 1
            
            # Positive acceleration
            if acceleration > 5:  # Accelerating growth
                risk_score += 3
            elif acceleration > 1:
                risk_score += 1
            
            # Recent bursts
            if burst_rate > 100:  # > 100MB burst
                risk_score += 4
            elif burst_rate > 50:
                risk_score += 2
            
            # Exponential growth
            if exponential_factor > 1.5:  # 50% growth per hour
                risk_score += 5
            elif exponential_factor > 1.2:  # 20% growth per hour
                risk_score += 2
            
            # Anomaly detection
            if anomaly_score > 3:  # High Z-score
                risk_score += 2
            elif anomaly_score > 2:
                risk_score += 1
            
            # Size-based risk
            if predicted_size_mb > 10000:  # > 10GB
                risk_score += 3
            elif predicted_size_mb > 5000:  # > 5GB
                risk_score += 2
            elif predicted_size_mb > 1000:  # > 1GB
                risk_score += 1
            
            # Risk classification
            if risk_score >= 10:
                return "critical"
            elif risk_score >= 6:
                return "high"
            elif risk_score >= 3:
                return "medium"
            elif risk_score >= 1:
                return "low"
            else:
                return "minimal"
                
        except Exception:
            return "unknown"
    
    def _calculate_time_to_size(self, growth_data: Dict[str, float], current_mb: float, target_mb: float) -> Optional[float]:
        """Calculate hours until directory reaches target size"""
        try:
            linear_rate = growth_data.get("linear_growth_mb_per_hour", 0)
            
            if linear_rate <= 0 or current_mb >= target_mb:
                return None
            
            hours_to_target = (target_mb - current_mb) / linear_rate
            return float(hours_to_target)
            
        except Exception:
            return None
    
    def identify_storage_hotspots(self, min_growth_rate: float = 10.0) -> List[Dict[str, Any]]:
        """Identify directories with concerning growth patterns"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get all unique paths from recent history
                cursor.execute('''
                    SELECT DISTINCT path FROM directory_history 
                    WHERE timestamp >= datetime('now', '-24 hours')
                ''')
                
                paths = [row[0] for row in cursor.fetchall()]
                hotspots = []
                
                for path in paths:
                    try:
                        growth_analysis = self.calculate_growth_velocity(path, hours_back=24)
                        
                        if "error" in growth_analysis:
                            continue
                        
                        linear_rate = growth_analysis.get("linear_growth_mb_per_hour", 0)
                        risk_level = self._assess_growth_risk(growth_analysis, 
                                                            growth_analysis.get("current_size_mb", 0))
                        
                        if (linear_rate >= min_growth_rate or 
                            risk_level in ["high", "critical"] or
                            growth_analysis.get("recent_burst_mb_per_hour", 0) > 50):
                            
                            hotspots.append({
                                "path": path,
                                "linear_growth_mb_per_hour": linear_rate,
                                "risk_level": risk_level,
                                "current_size_mb": growth_analysis.get("current_size_mb", 0),
                                "burst_rate_mb_per_hour": growth_analysis.get("recent_burst_mb_per_hour", 0),
                                "anomaly_score": growth_analysis.get("anomaly_score", 0),
                                "exponential_factor": growth_analysis.get("exponential_growth_factor", 1.0),
                                "acceleration": growth_analysis.get("acceleration_mb_per_hour_squared", 0)
                            })
                            
                    except Exception as e:
                        self.logger.warning(f"Failed to analyze path {path}: {e}")
                        continue
                
                # Sort by risk level and growth rate
                risk_priority = {"critical": 5, "high": 4, "medium": 3, "low": 2, "minimal": 1}
                hotspots.sort(key=lambda x: (
                    risk_priority.get(x["risk_level"], 0),
                    x["linear_growth_mb_per_hour"]
                ), reverse=True)
                
                return hotspots
                
        except Exception as e:
            self.logger.error(f"Failed to identify storage hotspots: {e}")
            return []
    
    def analyze_storage_patterns(self, days_back: int = 7) -> Dict[str, Any]:
        """Analyze overall storage patterns and trends"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cutoff_time = datetime.now() - timedelta(days=days_back)
                
                # Get aggregated data
                cursor.execute('''
                    SELECT 
                        DATE(timestamp) as date,
                        SUM(size_bytes) as total_size,
                        COUNT(DISTINCT path) as paths_monitored,
                        AVG(size_bytes) as avg_size_per_path
                    FROM directory_history 
                    WHERE timestamp >= ?
                    GROUP BY DATE(timestamp)
                    ORDER BY date
                ''', (cutoff_time,))
                
                daily_data = cursor.fetchall()
                
                if not daily_data:
                    return {"error": "no_data"}
                
                # Calculate trends
                dates = [row[0] for row in daily_data]
                total_sizes = [row[1] / 1_000_000_000 for row in daily_data]  # Convert to GB
                
                # Overall growth trend
                if len(total_sizes) >= 2:
                    overall_growth_gb = total_sizes[-1] - total_sizes[0]
                    daily_growth_rate = overall_growth_gb / len(total_sizes)
                else:
                    overall_growth_gb = 0
                    daily_growth_rate = 0
                
                # Find peak growth days
                daily_changes = []
                for i in range(1, len(total_sizes)):
                    change = total_sizes[i] - total_sizes[i-1]
                    daily_changes.append((dates[i], change))
                
                # Sort by change to find peaks
                daily_changes.sort(key=lambda x: x[1], reverse=True)
                peak_growth_days = daily_changes[:3]  # Top 3 growth days
                
                # Storage distribution analysis
                cursor.execute('''
                    SELECT 
                        path,
                        AVG(size_bytes) as avg_size,
                        MAX(size_bytes) - MIN(size_bytes) as size_variation
                    FROM directory_history 
                    WHERE timestamp >= ?
                    GROUP BY path
                    ORDER BY avg_size DESC
                    LIMIT 20
                ''', (cutoff_time,))
                
                path_analysis = []
                for row in cursor.fetchall():
                    path, avg_size, variation = row
                    path_analysis.append({
                        "path": path,
                        "avg_size_mb": avg_size / 1_000_000,
                        "size_variation_mb": variation / 1_000_000,
                        "stability_score": 1 / (1 + variation / avg_size) if avg_size > 0 else 0
                    })
                
                return {
                    "analysis_period_days": days_back,
                    "overall_trends": {
                        "total_growth_gb": overall_growth_gb,
                        "daily_growth_rate_gb": daily_growth_rate,
                        "current_total_size_gb": total_sizes[-1] if total_sizes else 0,
                        "growth_acceleration": self._calculate_growth_acceleration(total_sizes)
                    },
                    "peak_growth_days": [
                        {"date": date, "growth_gb": growth} 
                        for date, growth in peak_growth_days
                    ],
                    "top_storage_consumers": path_analysis,
                    "daily_timeline": [
                        {
                            "date": dates[i],
                            "total_size_gb": total_sizes[i],
                            "daily_change_gb": total_sizes[i] - total_sizes[i-1] if i > 0 else 0
                        }
                        for i in range(len(dates))
                    ]
                }
                
        except Exception as e:
            self.logger.error(f"Storage pattern analysis failed: {e}")
            return {"error": str(e)}
    
    def _calculate_growth_acceleration(self, sizes: List[float]) -> float:
        """Calculate if growth is accelerating or decelerating"""
        try:
            if len(sizes) < 4:
                return 0.0
            
            # Calculate daily changes
            changes = [sizes[i] - sizes[i-1] for i in range(1, len(sizes))]
            
            if len(changes) < 3:
                return 0.0
            
            # Calculate acceleration (change in change rate)
            accelerations = [changes[i] - changes[i-1] for i in range(1, len(changes))]
            
            # Return average acceleration
            return sum(accelerations) / len(accelerations)
            
        except Exception:
            return 0.0

    def generate_growth_report(self, path: str) -> Dict[str, Any]:
        """Generate comprehensive growth report for a specific path"""
        try:
            # Get growth analysis
            growth_data = self.calculate_growth_velocity(path, hours_back=48)
            
            if "error" in growth_data:
                return growth_data
            
            # Get predictions
            prediction_24h = self.predict_future_growth(path, hours_ahead=24)
            prediction_7d = self.predict_future_growth(path, hours_ahead=168)  # 7 days
            
            # Get historical context
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get size history
                cursor.execute('''
                    SELECT size_bytes, timestamp FROM directory_history 
                    WHERE path = ? 
                    ORDER BY timestamp DESC LIMIT 100
                ''', (path,))
                
                history_data = cursor.fetchall()
                
                # Check for large files
                cursor.execute('''
                    SELECT COUNT(*), AVG(size_bytes), MAX(size_bytes) 
                    FROM large_files 
                    WHERE path LIKE ?
                ''', (f"{path}%",))
                
                large_file_stats = cursor.fetchone()
            
            return {
                "path": path,
                "report_timestamp": datetime.now().isoformat(),
                "current_analysis": growth_data,
                "predictions": {
                    "24_hours": prediction_24h,
                    "7_days": prediction_7d
                },
                "large_files": {
                    "count": large_file_stats[0] if large_file_stats[0] else 0,
                    "avg_size_mb": (large_file_stats[1] / 1_000_000) if large_file_stats[1] else 0,
                    "largest_size_mb": (large_file_stats[2] / 1_000_000) if large_file_stats[2] else 0
                },
                "recommendations": self._generate_recommendations(growth_data, prediction_24h)
            }
            
        except Exception as e:
            self.logger.error(f"Growth report generation failed for {path}: {e}")
            return {"error": str(e)}
    
    def _generate_recommendations(self, growth_data: Dict[str, float], prediction: Dict[str, Any]) -> List[str]:
        """Generate actionable recommendations based on growth analysis"""
        recommendations = []
        
        try:
            linear_rate = growth_data.get("linear_growth_mb_per_hour", 0)
            risk_level = prediction.get("risk_assessment", {}).get("risk_level", "minimal")
            burst_rate = growth_data.get("recent_burst_mb_per_hour", 0)
            acceleration = growth_data.get("acceleration_mb_per_hour_squared", 0)
            
            # Growth rate recommendations
            if linear_rate > 100:
                recommendations.append("URGENT: Extremely high growth rate detected. Investigate immediately.")
            elif linear_rate > 50:
                recommendations.append("HIGH: Significant growth rate. Monitor closely and consider remediation.")
            elif linear_rate > 20:
                recommendations.append("MEDIUM: Moderate growth rate. Regular monitoring recommended.")
            
            # Risk level recommendations
            if risk_level == "critical":
                recommendations.append("CRITICAL: Implement emergency remediation measures immediately.")
                recommendations.append("Consider stopping related services until root cause is identified.")
            elif risk_level == "high":
                recommendations.append("HIGH RISK: Schedule immediate investigation and remediation.")
                recommendations.append("Enable automated cleanup if not already active.")
            
            # Burst recommendations
            if burst_rate > 100:
                recommendations.append("BURST DETECTED: Recent rapid growth spike requires immediate attention.")
                recommendations.append("Check for runaway processes or failed cleanup operations.")
            
            # Acceleration recommendations
            if acceleration > 5:
                recommendations.append("ACCELERATION: Growth is accelerating. Trend will worsen without intervention.")
                recommendations.append("Implement proactive measures before reaching critical thresholds.")
            
            # General recommendations
            if len(recommendations) == 0:
                recommendations.append("Storage growth appears normal. Continue regular monitoring.")
            
            # Always add monitoring recommendation
            recommendations.append("Enable continuous monitoring with automated alerts.")
            recommendations.append("Review and update cleanup policies regularly.")
            
        except Exception as e:
            recommendations.append(f"Error generating recommendations: {e}")
        
        return recommendations