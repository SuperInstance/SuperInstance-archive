#!/usr/bin/env python3
"""
Comprehensive Monitoring and Analytics System
============================================

- Storage usage tracking across all services
- Data lifecycle analytics (creation, usage, deletion)
- ML training effectiveness metrics
- Bot performance improvements from optimized data
- Storage allocation optimization per service
- Real-time monitoring with predictive alerts
"""

import os
import json
import sqlite3
import logging
import time
import threading
import psutil
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path
import numpy as np
import pandas as pd
from collections import defaultdict, deque
import matplotlib.pyplot as plt
import seaborn as sns
from flask import Flask, jsonify, render_template_string
import plotly.graph_objs as go
import plotly.utils

logger = logging.getLogger(__name__)

@dataclass
class StorageMetric:
    """Storage metric data point"""
    timestamp: datetime
    service_name: str
    total_size_bytes: int
    file_count: int
    data_types: Dict[str, int]
    growth_rate_mb_per_hour: float = 0.0
    efficiency_score: float = 0.0

@dataclass
class PerformanceMetric:
    """System performance metric"""
    timestamp: datetime
    cpu_usage_percent: float
    memory_usage_percent: float
    disk_io_read_mb: float
    disk_io_write_mb: float
    active_services: int
    cleanup_operations: int
    ml_training_jobs: int

@dataclass
class MLEffectivenessMetric:
    """ML training effectiveness metric"""
    timestamp: datetime
    model_name: str
    training_data_size_gb: float
    training_duration_minutes: float
    final_accuracy: float
    data_quality_score: float
    optimization_impact: float

class SystemResourceMonitor:
    """Monitor system resources and performance"""
    
    def __init__(self, monitoring_interval: int = 60):
        self.monitoring_interval = monitoring_interval
        self.metrics_history = deque(maxlen=1440)  # Keep 24 hours at 1-minute intervals
        self.monitoring_active = False
        
    def start_monitoring(self):
        """Start continuous resource monitoring"""
        self.monitoring_active = True
        
        def monitor_loop():
            while self.monitoring_active:
                try:
                    metric = self._collect_performance_metric()
                    self.metrics_history.append(metric)
                    
                    # Check for alerts
                    self._check_performance_alerts(metric)
                    
                    time.sleep(self.monitoring_interval)
                    
                except Exception as e:
                    logger.error(f"Error in resource monitoring: {e}")
                    time.sleep(30)  # Wait on error
        
        threading.Thread(target=monitor_loop, daemon=True).start()
        logger.info("System resource monitoring started")
    
    def _collect_performance_metric(self) -> PerformanceMetric:
        """Collect current system performance metrics"""
        # CPU and Memory
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        
        # Disk I/O
        disk_io = psutil.disk_io_counters()
        disk_read_mb = disk_io.read_bytes / (1024 * 1024) if disk_io else 0
        disk_write_mb = disk_io.write_bytes / (1024 * 1024) if disk_io else 0
        
        # Service count (rough estimate)
        active_services = len([p for p in psutil.process_iter(['name']) 
                             if 'python' in p.info['name'].lower() or 'node' in p.info['name'].lower()])
        
        return PerformanceMetric(
            timestamp=datetime.now(),
            cpu_usage_percent=cpu_percent,
            memory_usage_percent=memory.percent,
            disk_io_read_mb=disk_read_mb,
            disk_io_write_mb=disk_write_mb,
            active_services=active_services,
            cleanup_operations=0,  # Would be tracked by cleanup system
            ml_training_jobs=0     # Would be tracked by ML system
        )
    
    def _check_performance_alerts(self, metric: PerformanceMetric):
        """Check for performance-based alerts"""
        alerts = []
        
        if metric.cpu_usage_percent > 90:
            alerts.append(f"High CPU usage: {metric.cpu_usage_percent:.1f}%")
        
        if metric.memory_usage_percent > 85:
            alerts.append(f"High memory usage: {metric.memory_usage_percent:.1f}%")
        
        if metric.disk_io_write_mb > 1000:  # High disk write activity
            alerts.append(f"High disk write activity: {metric.disk_io_write_mb:.1f} MB")
        
        for alert in alerts:
            logger.warning(f"Performance Alert: {alert}")
    
    def get_performance_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get performance summary for the last N hours"""
        cutoff = datetime.now() - timedelta(hours=hours)
        recent_metrics = [m for m in self.metrics_history if m.timestamp > cutoff]
        
        if not recent_metrics:
            return {"error": "No metrics available"}
        
        cpu_values = [m.cpu_usage_percent for m in recent_metrics]
        memory_values = [m.memory_usage_percent for m in recent_metrics]
        
        return {
            "period_hours": hours,
            "samples_collected": len(recent_metrics),
            "cpu_usage": {
                "avg": np.mean(cpu_values),
                "max": np.max(cpu_values),
                "min": np.min(cpu_values),
                "current": cpu_values[-1] if cpu_values else 0
            },
            "memory_usage": {
                "avg": np.mean(memory_values),
                "max": np.max(memory_values),
                "min": np.min(memory_values),
                "current": memory_values[-1] if memory_values else 0
            },
            "disk_activity": {
                "total_read_gb": sum(m.disk_io_read_mb for m in recent_metrics) / 1024,
                "total_write_gb": sum(m.disk_io_write_mb for m in recent_metrics) / 1024
            },
            "service_activity": {
                "avg_active_services": np.mean([m.active_services for m in recent_metrics]),
                "max_active_services": np.max([m.active_services for m in recent_metrics])
            }
        }

class StorageAnalytics:
    """Advanced storage usage analytics"""
    
    def __init__(self, db_path: str = "storage_analytics.db"):
        self.db_path = db_path
        self._init_analytics_db()
        self.growth_predictions = {}
        
    def _init_analytics_db(self):
        """Initialize analytics database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Storage metrics over time
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS storage_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP NOT NULL,
                service_name TEXT NOT NULL,
                total_size_bytes INTEGER NOT NULL,
                file_count INTEGER NOT NULL,
                data_types TEXT NOT NULL,  -- JSON
                growth_rate_mb_per_hour REAL DEFAULT 0.0,
                efficiency_score REAL DEFAULT 0.0
            )
        ''')
        
        # Data lifecycle events
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS lifecycle_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP NOT NULL,
                event_type TEXT NOT NULL,  -- created, accessed, modified, deleted
                file_path TEXT NOT NULL,
                service_name TEXT NOT NULL,
                data_type TEXT NOT NULL,
                size_bytes INTEGER NOT NULL,
                metadata TEXT  -- JSON
            )
        ''')
        
        # ML effectiveness tracking
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ml_effectiveness (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP NOT NULL,
                model_name TEXT NOT NULL,
                training_data_size_gb REAL NOT NULL,
                training_duration_minutes REAL NOT NULL,
                final_accuracy REAL NOT NULL,
                data_quality_score REAL NOT NULL,
                optimization_impact REAL DEFAULT 0.0
            )
        ''')
        
        # Service performance correlation
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS service_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP NOT NULL,
                service_name TEXT NOT NULL,
                response_time_ms REAL NOT NULL,
                throughput_req_per_sec REAL NOT NULL,
                error_rate_percent REAL NOT NULL,
                storage_usage_gb REAL NOT NULL,
                cpu_usage_percent REAL NOT NULL,
                memory_usage_percent REAL NOT NULL
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def record_storage_metric(self, metric: StorageMetric):
        """Record a storage metric"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO storage_metrics 
            (timestamp, service_name, total_size_bytes, file_count, data_types, growth_rate_mb_per_hour, efficiency_score)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            metric.timestamp,
            metric.service_name,
            metric.total_size_bytes,
            metric.file_count,
            json.dumps(metric.data_types),
            metric.growth_rate_mb_per_hour,
            metric.efficiency_score
        ))
        
        conn.commit()
        conn.close()
    
    def record_lifecycle_event(self, event_type: str, file_path: str, 
                             service_name: str, data_type: str, 
                             size_bytes: int, metadata: Dict = None):
        """Record a data lifecycle event"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO lifecycle_events 
            (timestamp, event_type, file_path, service_name, data_type, size_bytes, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            datetime.now(),
            event_type,
            file_path,
            service_name,
            data_type,
            size_bytes,
            json.dumps(metadata or {})
        ))
        
        conn.commit()
        conn.close()
    
    def record_ml_effectiveness(self, metric: MLEffectivenessMetric):
        """Record ML training effectiveness"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO ml_effectiveness 
            (timestamp, model_name, training_data_size_gb, training_duration_minutes, 
             final_accuracy, data_quality_score, optimization_impact)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            metric.timestamp,
            metric.model_name,
            metric.training_data_size_gb,
            metric.training_duration_minutes,
            metric.final_accuracy,
            metric.data_quality_score,
            metric.optimization_impact
        ))
        
        conn.commit()
        conn.close()
    
    def analyze_growth_trends(self, service_name: str = None, days: int = 30) -> Dict[str, Any]:
        """Analyze storage growth trends"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get historical data
        if service_name:
            cursor.execute('''
                SELECT timestamp, total_size_bytes 
                FROM storage_metrics 
                WHERE service_name = ? AND timestamp > datetime('now', '-{} days')
                ORDER BY timestamp
            '''.format(days), (service_name,))
        else:
            cursor.execute('''
                SELECT timestamp, SUM(total_size_bytes) as total_size_bytes
                FROM storage_metrics 
                WHERE timestamp > datetime('now', '-{} days')
                GROUP BY timestamp
                ORDER BY timestamp
            '''.format(days))
        
        data = cursor.fetchall()
        conn.close()
        
        if len(data) < 2:
            return {"error": "Insufficient data for trend analysis"}
        
        # Calculate growth metrics
        timestamps = [datetime.fromisoformat(row[0]) for row in data]
        sizes_gb = [row[1] / (1024**3) for row in data]
        
        # Linear regression for growth rate
        time_deltas = [(t - timestamps[0]).total_seconds() / 3600 for t in timestamps]  # Hours
        growth_rate_gb_per_hour = np.polyfit(time_deltas, sizes_gb, 1)[0]
        
        # Growth predictions
        current_size = sizes_gb[-1]
        predicted_7d = current_size + (growth_rate_gb_per_hour * 24 * 7)
        predicted_30d = current_size + (growth_rate_gb_per_hour * 24 * 30)
        
        # Calculate volatility
        daily_changes = []
        for i in range(1, len(sizes_gb)):
            daily_change = sizes_gb[i] - sizes_gb[i-1]
            daily_changes.append(daily_change)
        
        volatility = np.std(daily_changes) if daily_changes else 0
        
        return {
            "service_name": service_name or "all_services",
            "analysis_period_days": days,
            "current_size_gb": current_size,
            "growth_rate_gb_per_hour": growth_rate_gb_per_hour,
            "growth_rate_gb_per_day": growth_rate_gb_per_hour * 24,
            "predictions": {
                "size_in_7_days_gb": predicted_7d,
                "size_in_30_days_gb": predicted_30d
            },
            "volatility_gb": volatility,
            "trend_classification": self._classify_growth_trend(growth_rate_gb_per_hour, volatility)
        }
    
    def _classify_growth_trend(self, growth_rate: float, volatility: float) -> str:
        """Classify growth trend"""
        if abs(growth_rate) < 0.001:  # Essentially stable
            return "stable"
        elif growth_rate > 0.1:  # Growing fast
            return "rapid_growth" if volatility < 0.5 else "volatile_growth"
        elif growth_rate > 0.01:
            return "steady_growth" if volatility < 0.2 else "irregular_growth"
        elif growth_rate < -0.01:
            return "declining"
        else:
            return "slow_growth"
    
    def analyze_data_lifecycle(self, days: int = 30) -> Dict[str, Any]:
        """Analyze data creation, usage, and deletion patterns"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT event_type, COUNT(*) as count, 
                   AVG(size_bytes) as avg_size,
                   SUM(size_bytes) as total_size,
                   service_name, data_type
            FROM lifecycle_events 
            WHERE timestamp > datetime('now', '-{} days')
            GROUP BY event_type, service_name, data_type
        '''.format(days))
        
        results = cursor.fetchall()
        conn.close()
        
        # Organize results
        lifecycle_stats = {
            'creation_patterns': defaultdict(lambda: {'count': 0, 'total_size_gb': 0}),
            'deletion_patterns': defaultdict(lambda: {'count': 0, 'total_size_gb': 0}),
            'access_patterns': defaultdict(lambda: {'count': 0}),
            'modification_patterns': defaultdict(lambda: {'count': 0}),
            'overall_stats': {
                'total_created_files': 0,
                'total_deleted_files': 0,
                'net_file_change': 0,
                'total_created_gb': 0,
                'total_deleted_gb': 0,
                'net_storage_change_gb': 0
            }
        }
        
        for row in results:
            event_type, count, avg_size, total_size, service, data_type = row
            size_gb = total_size / (1024**3)
            
            key = f"{service}:{data_type}"
            
            if event_type == 'created':
                lifecycle_stats['creation_patterns'][key]['count'] += count
                lifecycle_stats['creation_patterns'][key]['total_size_gb'] += size_gb
                lifecycle_stats['overall_stats']['total_created_files'] += count
                lifecycle_stats['overall_stats']['total_created_gb'] += size_gb
                
            elif event_type == 'deleted':
                lifecycle_stats['deletion_patterns'][key]['count'] += count
                lifecycle_stats['deletion_patterns'][key]['total_size_gb'] += size_gb
                lifecycle_stats['overall_stats']['total_deleted_files'] += count
                lifecycle_stats['overall_stats']['total_deleted_gb'] += size_gb
                
            elif event_type == 'accessed':
                lifecycle_stats['access_patterns'][key]['count'] += count
                
            elif event_type == 'modified':
                lifecycle_stats['modification_patterns'][key]['count'] += count
        
        # Calculate net changes
        lifecycle_stats['overall_stats']['net_file_change'] = (
            lifecycle_stats['overall_stats']['total_created_files'] - 
            lifecycle_stats['overall_stats']['total_deleted_files']
        )
        lifecycle_stats['overall_stats']['net_storage_change_gb'] = (
            lifecycle_stats['overall_stats']['total_created_gb'] - 
            lifecycle_stats['overall_stats']['total_deleted_gb']
        )
        
        return lifecycle_stats
    
    def analyze_ml_training_effectiveness(self, days: int = 30) -> Dict[str, Any]:
        """Analyze ML training effectiveness over time"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT model_name, 
                   AVG(training_data_size_gb) as avg_data_size,
                   AVG(training_duration_minutes) as avg_duration,
                   AVG(final_accuracy) as avg_accuracy,
                   AVG(data_quality_score) as avg_data_quality,
                   AVG(optimization_impact) as avg_optimization_impact,
                   COUNT(*) as training_runs
            FROM ml_effectiveness 
            WHERE timestamp > datetime('now', '-{} days')
            GROUP BY model_name
        '''.format(days))
        
        results = cursor.fetchall()
        conn.close()
        
        effectiveness_analysis = {
            'model_performance': {},
            'overall_trends': {
                'total_training_runs': 0,
                'avg_accuracy_all_models': 0,
                'avg_data_efficiency': 0,
                'optimization_effectiveness': 0
            }
        }
        
        all_accuracies = []
        all_data_efficiency = []  # Accuracy per GB of training data
        all_optimization_impacts = []
        
        for row in results:
            model, avg_data_size, avg_duration, avg_accuracy, avg_data_quality, avg_optimization, runs = row
            
            data_efficiency = avg_accuracy / avg_data_size if avg_data_size > 0 else 0
            time_efficiency = avg_accuracy / avg_duration if avg_duration > 0 else 0
            
            effectiveness_analysis['model_performance'][model] = {
                'avg_training_data_gb': avg_data_size,
                'avg_training_duration_minutes': avg_duration,
                'avg_final_accuracy': avg_accuracy,
                'avg_data_quality_score': avg_data_quality,
                'avg_optimization_impact': avg_optimization,
                'training_runs': runs,
                'data_efficiency': data_efficiency,
                'time_efficiency': time_efficiency
            }
            
            all_accuracies.append(avg_accuracy)
            all_data_efficiency.append(data_efficiency)
            all_optimization_impacts.append(avg_optimization)
            effectiveness_analysis['overall_trends']['total_training_runs'] += runs
        
        if all_accuracies:
            effectiveness_analysis['overall_trends']['avg_accuracy_all_models'] = np.mean(all_accuracies)
            effectiveness_analysis['overall_trends']['avg_data_efficiency'] = np.mean(all_data_efficiency)
            effectiveness_analysis['overall_trends']['optimization_effectiveness'] = np.mean(all_optimization_impacts)
        
        return effectiveness_analysis

class PredictiveAnalytics:
    """Predictive analytics for storage and performance"""
    
    def __init__(self, analytics_db: StorageAnalytics):
        self.analytics_db = analytics_db
        self.alert_thresholds = {
            'storage_critical': 0.95,  # 95% of limit
            'storage_warning': 0.85,   # 85% of limit
            'growth_rate_high': 1.0,   # 1 GB per day
            'performance_degradation': 0.8  # 80% performance drop
        }
    
    def predict_storage_exhaustion(self, total_limit_gb: float, 
                                 service_name: str = None) -> Dict[str, Any]:
        """Predict when storage will be exhausted"""
        growth_analysis = self.analytics_db.analyze_growth_trends(service_name, days=30)
        
        if 'error' in growth_analysis:
            return growth_analysis
        
        current_size = growth_analysis['current_size_gb']
        growth_rate_per_day = growth_analysis['growth_rate_gb_per_day']
        
        # Calculate time to exhaustion
        available_space = total_limit_gb - current_size
        
        if growth_rate_per_day <= 0:
            days_to_exhaustion = float('inf')
            exhaustion_date = None
        else:
            days_to_exhaustion = available_space / growth_rate_per_day
            exhaustion_date = datetime.now() + timedelta(days=days_to_exhaustion)
        
        # Calculate warning dates
        warning_size = total_limit_gb * self.alert_thresholds['storage_warning']
        critical_size = total_limit_gb * self.alert_thresholds['storage_critical']
        
        warning_space = warning_size - current_size
        critical_space = critical_size - current_size
        
        warning_days = warning_space / growth_rate_per_day if growth_rate_per_day > 0 else float('inf')
        critical_days = critical_space / growth_rate_per_day if growth_rate_per_day > 0 else float('inf')
        
        warning_date = datetime.now() + timedelta(days=warning_days) if warning_days != float('inf') else None
        critical_date = datetime.now() + timedelta(days=critical_days) if critical_days != float('inf') else None
        
        # Generate recommendations
        recommendations = []
        urgency_level = "low"
        
        if days_to_exhaustion < 7:
            urgency_level = "critical"
            recommendations.extend([
                "Immediate cleanup required - storage will be exhausted in less than a week",
                "Run aggressive garbage collection",
                "Consider emergency storage expansion"
            ])
        elif days_to_exhaustion < 30:
            urgency_level = "high"
            recommendations.extend([
                "Schedule cleanup within next few days",
                "Review and optimize storage allocation",
                "Consider data archival strategies"
            ])
        elif days_to_exhaustion < 90:
            urgency_level = "medium"
            recommendations.extend([
                "Plan storage optimization",
                "Monitor growth trends closely",
                "Evaluate data retention policies"
            ])
        
        return {
            'service_name': service_name or 'all_services',
            'current_usage_gb': current_size,
            'total_limit_gb': total_limit_gb,
            'available_space_gb': available_space,
            'growth_rate_gb_per_day': growth_rate_per_day,
            'days_to_exhaustion': days_to_exhaustion,
            'exhaustion_date': exhaustion_date.isoformat() if exhaustion_date else None,
            'warning_date': warning_date.isoformat() if warning_date else None,
            'critical_date': critical_date.isoformat() if critical_date else None,
            'urgency_level': urgency_level,
            'recommendations': recommendations
        }
    
    def generate_optimization_alerts(self, storage_status: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate optimization alerts based on current status"""
        alerts = []
        
        usage_percent = storage_status.get('usage_percent', 0)
        service_usage = storage_status.get('service_usage', {})
        
        # Storage level alerts
        if usage_percent >= self.alert_thresholds['storage_critical']:
            alerts.append({
                'type': 'critical',
                'category': 'storage',
                'message': f"Storage critically full: {usage_percent*100:.1f}%",
                'action': 'immediate_cleanup_required',
                'priority': 1
            })
        elif usage_percent >= self.alert_thresholds['storage_warning']:
            alerts.append({
                'type': 'warning',
                'category': 'storage',
                'message': f"Storage warning level: {usage_percent*100:.1f}%",
                'action': 'schedule_cleanup',
                'priority': 2
            })
        
        # Per-service alerts
        for service, usage in service_usage.items():
            if usage.get('usage_percent', 0) > 1.2:  # 120% of allocation
                alerts.append({
                    'type': 'warning',
                    'category': 'service_allocation',
                    'message': f"Service '{service}' exceeds allocation by {(usage['usage_percent']-1)*100:.1f}%",
                    'action': 'review_service_allocation',
                    'priority': 2,
                    'service': service
                })
        
        # Growth rate alerts
        for service in service_usage.keys():
            growth_analysis = self.analytics_db.analyze_growth_trends(service, days=7)
            if 'growth_rate_gb_per_day' in growth_analysis:
                daily_growth = growth_analysis['growth_rate_gb_per_day']
                if daily_growth > self.alert_thresholds['growth_rate_high']:
                    alerts.append({
                        'type': 'info',
                        'category': 'rapid_growth',
                        'message': f"Service '{service}' growing rapidly: {daily_growth:.2f} GB/day",
                        'action': 'monitor_growth_trend',
                        'priority': 3,
                        'service': service
                    })
        
        # Sort alerts by priority
        alerts.sort(key=lambda x: x['priority'])
        
        return alerts

class DataLifecycleAnalytics:
    """Main analytics orchestrator"""
    
    def __init__(self, db_path: str = "data_lifecycle_analytics.db"):
        self.storage_analytics = StorageAnalytics(db_path)
        self.resource_monitor = SystemResourceMonitor()
        self.predictive_analytics = PredictiveAnalytics(self.storage_analytics)
        
        # Start monitoring
        self.resource_monitor.start_monitoring()
        
    def get_comprehensive_dashboard_data(self) -> Dict[str, Any]:
        """Get comprehensive data for dashboard"""
        
        # Get basic storage status (would come from main system)
        storage_status = {
            'usage_percent': 0.65,  # Mock data - would come from actual system
            'total_size_gb': 19.5,
            'total_limit_gb': 30.0,
            'service_usage': {
                'dmlog': {'size_gb': 5.2, 'usage_percent': 1.04},
                'ai-insights': {'size_gb': 3.8, 'usage_percent': 0.95},
                'ml-platform': {'size_gb': 6.1, 'usage_percent': 0.76}
            }
        }
        
        # Performance metrics
        performance_summary = self.resource_monitor.get_performance_summary(24)
        
        # Growth trends
        growth_trends = self.storage_analytics.analyze_growth_trends(days=30)
        
        # Lifecycle analysis
        lifecycle_stats = self.storage_analytics.analyze_data_lifecycle(30)
        
        # ML effectiveness
        ml_effectiveness = self.storage_analytics.analyze_ml_training_effectiveness(30)
        
        # Predictive alerts
        exhaustion_prediction = self.predictive_analytics.predict_storage_exhaustion(30.0)
        optimization_alerts = self.predictive_analytics.generate_optimization_alerts(storage_status)
        
        return {
            'timestamp': datetime.now().isoformat(),
            'storage_status': storage_status,
            'performance_summary': performance_summary,
            'growth_trends': growth_trends,
            'lifecycle_stats': lifecycle_stats,
            'ml_effectiveness': ml_effectiveness,
            'exhaustion_prediction': exhaustion_prediction,
            'alerts': optimization_alerts,
            'recommendations': self._generate_comprehensive_recommendations(
                storage_status, growth_trends, ml_effectiveness, optimization_alerts
            )
        }
    
    def _generate_comprehensive_recommendations(self, storage_status: Dict, 
                                             growth_trends: Dict, 
                                             ml_effectiveness: Dict,
                                             alerts: List[Dict]) -> List[str]:
        """Generate comprehensive optimization recommendations"""
        recommendations = []
        
        # Critical actions first
        critical_alerts = [alert for alert in alerts if alert['type'] == 'critical']
        if critical_alerts:
            recommendations.append("🚨 CRITICAL: Immediate storage cleanup required")
            
        # Growth-based recommendations
        if 'trend_classification' in growth_trends:
            trend = growth_trends['trend_classification']
            if trend in ['rapid_growth', 'volatile_growth']:
                recommendations.append(f"📈 Address {trend}: implement proactive cleanup policies")
            elif trend == 'declining':
                recommendations.append("📉 Storage declining: review if cleanup is too aggressive")
        
        # ML effectiveness recommendations
        if ml_effectiveness.get('overall_trends', {}).get('avg_accuracy_all_models', 0) < 0.7:
            recommendations.append("🤖 ML performance low: improve data quality or model optimization")
        
        if ml_effectiveness.get('overall_trends', {}).get('avg_data_efficiency', 0) < 0.1:
            recommendations.append("💾 ML data inefficient: consolidate or clean training data")
        
        # Service allocation recommendations
        usage_percent = storage_status.get('usage_percent', 0)
        if usage_percent > 0.8:
            recommendations.append("⚖️ Rebalance service allocations based on actual usage patterns")
        
        # Proactive recommendations
        if len(recommendations) == 0:  # System running well
            recommendations.extend([
                "✅ System operating efficiently",
                "🔍 Continue monitoring growth trends",
                "🎯 Consider ML model consolidation opportunities"
            ])
        
        return recommendations
    
    def generate_analytics_report(self, days: int = 30) -> Dict[str, Any]:
        """Generate comprehensive analytics report"""
        dashboard_data = self.get_comprehensive_dashboard_data()
        
        # Additional detailed analysis
        report = {
            'report_period_days': days,
            'generated_at': datetime.now().isoformat(),
            'executive_summary': self._create_executive_summary(dashboard_data),
            'detailed_analysis': dashboard_data,
            'actionable_insights': self._create_actionable_insights(dashboard_data),
            'forecast': self._create_forecast(dashboard_data)
        }
        
        return report
    
    def _create_executive_summary(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create executive summary"""
        storage = data['storage_status']
        alerts = data['alerts']
        
        summary = {
            'storage_health': 'good',
            'key_metrics': {
                'storage_utilization_percent': storage['usage_percent'] * 100,
                'days_to_full': data['exhaustion_prediction'].get('days_to_exhaustion', 'N/A'),
                'active_alerts': len(alerts),
                'critical_alerts': len([a for a in alerts if a['type'] == 'critical'])
            },
            'primary_concerns': [],
            'achievements': []
        }
        
        # Determine health
        if storage['usage_percent'] > 0.9:
            summary['storage_health'] = 'critical'
        elif storage['usage_percent'] > 0.8:
            summary['storage_health'] = 'warning'
        
        # Add concerns
        if summary['key_metrics']['critical_alerts'] > 0:
            summary['primary_concerns'].append("Critical storage alerts require immediate attention")
        
        if data['exhaustion_prediction'].get('days_to_exhaustion', float('inf')) < 30:
            summary['primary_concerns'].append("Storage exhaustion predicted within 30 days")
        
        # Add achievements
        ml_effectiveness = data['ml_effectiveness']
        if ml_effectiveness.get('overall_trends', {}).get('avg_accuracy_all_models', 0) > 0.8:
            summary['achievements'].append("ML models achieving high accuracy")
        
        if len(summary['primary_concerns']) == 0:
            summary['achievements'].append("No critical storage issues detected")
        
        return summary
    
    def _create_actionable_insights(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create actionable insights"""
        insights = []
        
        # Storage optimization insights
        lifecycle = data['lifecycle_stats']
        net_change = lifecycle['overall_stats']['net_storage_change_gb']
        
        if net_change > 1.0:  # Growing more than 1GB
            insights.append({
                'category': 'storage_optimization',
                'insight': f"Storage growing by {net_change:.2f} GB/month",
                'action': 'Implement automated cleanup policies',
                'impact': 'high',
                'effort': 'medium'
            })
        
        # ML optimization insights
        ml_stats = data['ml_effectiveness']
        if ml_stats.get('overall_trends', {}).get('avg_data_efficiency', 0) < 0.1:
            insights.append({
                'category': 'ml_optimization',
                'insight': 'ML models have low data efficiency',
                'action': 'Consolidate and clean training datasets',
                'impact': 'medium',
                'effort': 'high'
            })
        
        return insights
    
    def _create_forecast(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create storage and performance forecast"""
        exhaustion = data['exhaustion_prediction']
        growth = data['growth_trends']
        
        return {
            'storage_forecast': {
                '7_days': exhaustion.get('current_usage_gb', 0) + (growth.get('growth_rate_gb_per_day', 0) * 7),
                '30_days': exhaustion.get('current_usage_gb', 0) + (growth.get('growth_rate_gb_per_day', 0) * 30),
                '90_days': exhaustion.get('current_usage_gb', 0) + (growth.get('growth_rate_gb_per_day', 0) * 90)
            },
            'trend_confidence': 'medium' if growth.get('volatility_gb', 0) < 1.0 else 'low',
            'risk_assessment': {
                'storage_exhaustion_risk': 'high' if exhaustion.get('days_to_exhaustion', float('inf')) < 60 else 'medium',
                'performance_degradation_risk': 'low',  # Would analyze performance trends
                'data_loss_risk': 'low'
            }
        }