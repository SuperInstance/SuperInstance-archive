"""
Device Health Monitoring System
Monitors device health, performance, and status
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
import statistics

logger = logging.getLogger(__name__)

class DeviceHealthMonitor:
    """Monitors health and performance of all devices"""
    
    def __init__(self, config, device_registry):
        self.config = config
        self.device_registry = device_registry
        self.health_data: Dict[str, Dict[str, Any]] = {}
        self.status_callback: Optional[Callable] = None
        self.monitoring_active = False
        
        # Health thresholds
        self.thresholds = {
            'temperature': {'warning': 70, 'critical': 85},  # Celsius
            'cpu_usage': {'warning': 80, 'critical': 95},    # Percentage
            'memory_usage': {'warning': 85, 'critical': 95}, # Percentage
            'response_time': {'warning': 1000, 'critical': 5000}, # ms
            'error_rate': {'warning': 0.05, 'critical': 0.1}, # Percentage
            'uptime': {'warning': 86400, 'critical': 3600}    # Seconds (1 day warning, 1 hour critical)
        }
    
    async def start_monitoring(self):
        """Start device health monitoring"""
        logger.info("Starting device health monitoring...")
        
        self.monitoring_active = True
        
        # Start monitoring tasks
        asyncio.create_task(self.health_monitoring_task())
        asyncio.create_task(self.performance_monitoring_task())
        asyncio.create_task(self.predictive_maintenance_task())
        
        logger.info("Device health monitoring started")
    
    async def stop_monitoring(self):
        """Stop device health monitoring"""
        logger.info("Stopping device health monitoring...")
        self.monitoring_active = False
    
    def set_status_callback(self, callback: Callable):
        """Set callback for status updates"""
        self.status_callback = callback
    
    async def subscribe_device(self, device_id: str, websocket):
        """Subscribe to device-specific health updates"""
        if device_id not in self.health_data:
            self.health_data[device_id] = {
                'subscribers': [],
                'last_health_check': None,
                'metrics': {},
                'alerts': []
            }
        
        self.health_data[device_id]['subscribers'].append(websocket)
    
    async def health_monitoring_task(self):
        """Main health monitoring task"""
        while self.monitoring_active:
            try:
                devices = self.device_registry.get_all_devices()
                
                for device in devices:
                    await self.check_device_health(device.device_id)
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Health monitoring task error: {e}")
                await asyncio.sleep(60)
    
    async def performance_monitoring_task(self):
        """Performance monitoring task"""
        while self.monitoring_active:
            try:
                devices = self.device_registry.get_all_devices()
                
                for device in devices:
                    await self.monitor_device_performance(device.device_id)
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Performance monitoring task error: {e}")
                await asyncio.sleep(120)
    
    async def predictive_maintenance_task(self):
        """Predictive maintenance task"""
        while self.monitoring_active:
            try:
                devices = self.device_registry.get_all_devices()
                
                for device in devices:
                    await self.predict_maintenance_needs(device.device_id)
                
                await asyncio.sleep(3600)  # Check every hour
                
            except Exception as e:
                logger.error(f"Predictive maintenance task error: {e}")
                await asyncio.sleep(1800)
    
    async def check_device_health(self, device_id: str):
        """Check health of a specific device"""
        try:
            # Initialize device health data if needed
            if device_id not in self.health_data:
                self.health_data[device_id] = {
                    'subscribers': [],
                    'last_health_check': None,
                    'metrics': {},
                    'alerts': [],
                    'status': 'unknown'
                }
            
            health_info = self.health_data[device_id]
            
            # Get device status
            device_status = await self.device_registry.get_device_status(device_id)
            
            if not device_status or device_status.get('status') == 'disconnected':
                health_info['status'] = 'offline'
                await self.generate_alert(device_id, 'critical', 'Device offline')
                return
            
            # Collect health metrics
            metrics = await self.collect_health_metrics(device_id)
            health_info['metrics'] = metrics
            health_info['last_health_check'] = datetime.utcnow()
            
            # Analyze health
            health_status = await self.analyze_health(device_id, metrics)
            health_info['status'] = health_status
            
            # Generate alerts if needed
            await self.check_thresholds(device_id, metrics)
            
            # Broadcast status update
            if self.status_callback:
                await self.status_callback(device_id, {
                    'health_status': health_status,
                    'metrics': metrics,
                    'timestamp': datetime.utcnow().isoformat()
                })
            
        except Exception as e:
            logger.error(f"Error checking health for device {device_id}: {e}")
    
    async def collect_health_metrics(self, device_id: str) -> Dict[str, Any]:
        """Collect health metrics for a device"""
        try:
            # Get basic device status
            device_status = await self.device_registry.get_device_status(device_id)
            
            # Simulate health metrics collection
            # In a real implementation, this would query actual device metrics
            metrics = {
                'temperature': 45.0,  # Celsius
                'cpu_usage': 35.0,    # Percentage
                'memory_usage': 60.0, # Percentage
                'disk_usage': 45.0,   # Percentage
                'network_latency': 12.0, # ms
                'error_count': 0,
                'uptime': 86400,      # seconds
                'last_response_time': 50, # ms
                'throughput': 100,    # operations/second
                'availability': 99.9, # percentage
                'connection_quality': 'good'
            }
            
            # Add device-specific metrics
            if device_status:
                metrics.update({
                    'device_connected': device_status.get('connected', False),
                    'device_type': device_status.get('type', 'unknown')
                })
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error collecting metrics for {device_id}: {e}")
            return {}
    
    async def analyze_health(self, device_id: str, metrics: Dict[str, Any]) -> str:
        """Analyze device health based on metrics"""
        try:
            health_score = 100
            issues = []
            
            # Check temperature
            temp = metrics.get('temperature', 0)
            if temp > self.thresholds['temperature']['critical']:
                health_score -= 30
                issues.append('Critical temperature')
            elif temp > self.thresholds['temperature']['warning']:
                health_score -= 15
                issues.append('High temperature')
            
            # Check CPU usage
            cpu = metrics.get('cpu_usage', 0)
            if cpu > self.thresholds['cpu_usage']['critical']:
                health_score -= 25
                issues.append('Critical CPU usage')
            elif cpu > self.thresholds['cpu_usage']['warning']:
                health_score -= 10
                issues.append('High CPU usage')
            
            # Check memory usage
            memory = metrics.get('memory_usage', 0)
            if memory > self.thresholds['memory_usage']['critical']:
                health_score -= 20
                issues.append('Critical memory usage')
            elif memory > self.thresholds['memory_usage']['warning']:
                health_score -= 8
                issues.append('High memory usage')
            
            # Check response time
            response_time = metrics.get('last_response_time', 0)
            if response_time > self.thresholds['response_time']['critical']:
                health_score -= 20
                issues.append('Critical response time')
            elif response_time > self.thresholds['response_time']['warning']:
                health_score -= 10
                issues.append('Slow response time')
            
            # Check connection
            if not metrics.get('device_connected', True):
                health_score -= 50
                issues.append('Device disconnected')
            
            # Determine health status
            if health_score >= 90:
                status = 'excellent'
            elif health_score >= 75:
                status = 'good'
            elif health_score >= 50:
                status = 'fair'
            elif health_score >= 25:
                status = 'poor'
            else:
                status = 'critical'
            
            # Store issues for reporting
            if device_id in self.health_data:
                self.health_data[device_id]['issues'] = issues
                self.health_data[device_id]['health_score'] = health_score
            
            return status
            
        except Exception as e:
            logger.error(f"Error analyzing health for {device_id}: {e}")
            return 'unknown'
    
    async def check_thresholds(self, device_id: str, metrics: Dict[str, Any]):
        """Check metrics against thresholds and generate alerts"""
        try:
            for metric_name, value in metrics.items():
                if metric_name in self.thresholds and isinstance(value, (int, float)):
                    thresholds = self.thresholds[metric_name]
                    
                    if value > thresholds['critical']:
                        await self.generate_alert(
                            device_id, 'critical', 
                            f'{metric_name.replace("_", " ").title()} is critical: {value}'
                        )
                    elif value > thresholds['warning']:
                        await self.generate_alert(
                            device_id, 'warning',
                            f'{metric_name.replace("_", " ").title()} is high: {value}'
                        )
            
        except Exception as e:
            logger.error(f"Error checking thresholds for {device_id}: {e}")
    
    async def generate_alert(self, device_id: str, severity: str, message: str):
        """Generate health alert"""
        try:
            alert = {
                'device_id': device_id,
                'severity': severity,
                'message': message,
                'timestamp': datetime.utcnow().isoformat(),
                'acknowledged': False
            }
            
            if device_id in self.health_data:
                self.health_data[device_id]['alerts'].append(alert)
                
                # Keep only last 100 alerts
                if len(self.health_data[device_id]['alerts']) > 100:
                    self.health_data[device_id]['alerts'] = self.health_data[device_id]['alerts'][-100:]
            
            logger.warning(f"Health alert for {device_id} ({severity}): {message}")
            
            # Broadcast alert to subscribers
            await self.broadcast_alert(device_id, alert)
            
        except Exception as e:
            logger.error(f"Error generating alert: {e}")
    
    async def broadcast_alert(self, device_id: str, alert: Dict[str, Any]):
        """Broadcast alert to subscribers"""
        if device_id not in self.health_data:
            return
        
        subscribers = self.health_data[device_id]['subscribers']
        disconnected = []
        
        for websocket in subscribers:
            try:
                await websocket.send_text(json.dumps({
                    'type': 'health_alert',
                    'device_id': device_id,
                    'alert': alert
                }))
            except:
                disconnected.append(websocket)
        
        # Remove disconnected subscribers
        for websocket in disconnected:
            subscribers.remove(websocket)
    
    async def monitor_device_performance(self, device_id: str):
        """Monitor device performance metrics"""
        try:
            if device_id not in self.health_data:
                return
            
            # Collect performance metrics
            performance_metrics = await self.collect_performance_metrics(device_id)
            
            # Store in health data
            health_info = self.health_data[device_id]
            if 'performance_history' not in health_info:
                health_info['performance_history'] = []
            
            health_info['performance_history'].append({
                'timestamp': datetime.utcnow(),
                'metrics': performance_metrics
            })
            
            # Keep only last 24 hours of data
            cutoff_time = datetime.utcnow() - timedelta(hours=24)
            health_info['performance_history'] = [
                entry for entry in health_info['performance_history']
                if entry['timestamp'] > cutoff_time
            ]
            
            # Analyze performance trends
            await self.analyze_performance_trends(device_id)
            
        except Exception as e:
            logger.error(f"Error monitoring performance for {device_id}: {e}")
    
    async def collect_performance_metrics(self, device_id: str) -> Dict[str, float]:
        """Collect performance metrics"""
        # Simulate performance metrics
        import random
        
        return {
            'response_time': random.uniform(10, 100),
            'throughput': random.uniform(50, 200),
            'cpu_utilization': random.uniform(20, 80),
            'memory_utilization': random.uniform(30, 70),
            'network_utilization': random.uniform(10, 50),
            'error_rate': random.uniform(0, 0.05)
        }
    
    async def analyze_performance_trends(self, device_id: str):
        """Analyze performance trends"""
        try:
            health_info = self.health_data[device_id]
            history = health_info.get('performance_history', [])
            
            if len(history) < 5:  # Need at least 5 data points
                return
            
            # Analyze trends for each metric
            trends = {}
            
            for metric_name in ['response_time', 'throughput', 'cpu_utilization']:
                values = [entry['metrics'].get(metric_name, 0) for entry in history[-10:]]
                
                if len(values) >= 3:
                    # Simple trend analysis
                    recent_avg = statistics.mean(values[-3:])
                    older_avg = statistics.mean(values[:-3]) if len(values) > 3 else recent_avg
                    
                    if recent_avg > older_avg * 1.2:
                        trends[metric_name] = 'increasing'
                    elif recent_avg < older_avg * 0.8:
                        trends[metric_name] = 'decreasing'
                    else:
                        trends[metric_name] = 'stable'
            
            # Store trends
            health_info['performance_trends'] = trends
            
            # Generate alerts for concerning trends
            if trends.get('response_time') == 'increasing':
                await self.generate_alert(
                    device_id, 'warning',
                    'Response time trend is increasing'
                )
            
            if trends.get('cpu_utilization') == 'increasing':
                await self.generate_alert(
                    device_id, 'warning',
                    'CPU utilization trend is increasing'
                )
            
        except Exception as e:
            logger.error(f"Error analyzing trends for {device_id}: {e}")
    
    async def predict_maintenance_needs(self, device_id: str):
        """Predict maintenance needs based on health data"""
        try:
            if device_id not in self.health_data:
                return
            
            health_info = self.health_data[device_id]
            
            # Simple predictive maintenance logic
            predictions = []
            
            # Check uptime
            metrics = health_info.get('metrics', {})
            uptime = metrics.get('uptime', 0)
            
            # Predict maintenance based on uptime (example: every 30 days)
            if uptime > 30 * 24 * 3600:  # 30 days
                predictions.append({
                    'type': 'routine_maintenance',
                    'priority': 'low',
                    'estimated_time': datetime.utcnow() + timedelta(days=7),
                    'reason': 'Scheduled maintenance due'
                })
            
            # Check error rates
            performance_history = health_info.get('performance_history', [])
            if len(performance_history) >= 5:
                recent_errors = [
                    entry['metrics'].get('error_rate', 0) 
                    for entry in performance_history[-5:]
                ]
                avg_error_rate = statistics.mean(recent_errors)
                
                if avg_error_rate > 0.02:  # 2% error rate
                    predictions.append({
                        'type': 'error_investigation',
                        'priority': 'medium',
                        'estimated_time': datetime.utcnow() + timedelta(days=1),
                        'reason': f'High error rate: {avg_error_rate:.3f}'
                    })
            
            # Store predictions
            health_info['maintenance_predictions'] = predictions
            
            # Generate alerts for urgent predictions
            for prediction in predictions:
                if prediction['priority'] in ['high', 'critical']:
                    await self.generate_alert(
                        device_id, prediction['priority'],
                        f"Maintenance needed: {prediction['reason']}"
                    )
            
        except Exception as e:
            logger.error(f"Error predicting maintenance for {device_id}: {e}")
    
    async def get_device_health_summary(self, device_id: str) -> Dict[str, Any]:
        """Get comprehensive health summary for device"""
        if device_id not in self.health_data:
            return {"status": "unknown", "error": "Device not found"}
        
        health_info = self.health_data[device_id]
        
        return {
            "device_id": device_id,
            "status": health_info.get('status', 'unknown'),
            "health_score": health_info.get('health_score', 0),
            "last_check": health_info.get('last_health_check'),
            "current_metrics": health_info.get('metrics', {}),
            "issues": health_info.get('issues', []),
            "recent_alerts": health_info.get('alerts', [])[-10:],  # Last 10 alerts
            "performance_trends": health_info.get('performance_trends', {}),
            "maintenance_predictions": health_info.get('maintenance_predictions', [])
        }
    
    async def get_system_health_overview(self) -> Dict[str, Any]:
        """Get system-wide health overview"""
        total_devices = len(self.health_data)
        
        if total_devices == 0:
            return {
                "total_devices": 0,
                "healthy_devices": 0,
                "warning_devices": 0,
                "critical_devices": 0,
                "offline_devices": 0
            }
        
        status_counts = {
            "excellent": 0,
            "good": 0,
            "fair": 0,
            "poor": 0,
            "critical": 0,
            "offline": 0,
            "unknown": 0
        }
        
        total_alerts = 0
        
        for device_id, health_info in self.health_data.items():
            status = health_info.get('status', 'unknown')
            status_counts[status] = status_counts.get(status, 0) + 1
            total_alerts += len(health_info.get('alerts', []))
        
        healthy_devices = status_counts['excellent'] + status_counts['good']
        warning_devices = status_counts['fair'] + status_counts['poor'] 
        critical_devices = status_counts['critical'] + status_counts['offline']
        
        return {
            "total_devices": total_devices,
            "healthy_devices": healthy_devices,
            "warning_devices": warning_devices, 
            "critical_devices": critical_devices,
            "offline_devices": status_counts['offline'],
            "status_breakdown": status_counts,
            "total_active_alerts": total_alerts,
            "system_health_score": (healthy_devices * 100 + warning_devices * 50) / total_devices if total_devices > 0 else 0
        }