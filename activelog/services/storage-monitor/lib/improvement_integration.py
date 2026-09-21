#!/usr/bin/env python3
"""
Integration with Improvement System
Bidirectional communication and coordination between storage monitor and improvement system
"""

import requests
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path
import subprocess
import asyncio
import time

class ImprovementSystemIntegration:
    def __init__(self, improvement_system_url: str = "http://localhost:8500",
                 storage_monitor_url: str = "http://localhost:8490"):
        self.improvement_url = improvement_system_url
        self.storage_url = storage_monitor_url
        self.logger = logging.getLogger('ImprovementIntegration')
        self.session = requests.Session()
        self.session.timeout = 10
        
    def notify_storage_emergency(self, path: str, growth_rate: float, 
                               remediation_actions: List[str]) -> bool:
        """Notify improvement system of storage emergency"""
        try:
            payload = {
                "type": "storage_emergency",
                "severity": "critical" if growth_rate > 500 else "high",
                "path": path,
                "growth_rate_mb_per_hour": growth_rate,
                "remediation_actions_taken": remediation_actions,
                "timestamp": datetime.now().isoformat(),
                "source": "storage_monitor"
            }
            
            response = self.session.post(
                f"{self.improvement_url}/emergency-alert",
                json=payload,
                timeout=5
            )
            
            if response.status_code == 200:
                self.logger.info(f"Storage emergency notification sent: {path}")
                return True
            else:
                self.logger.warning(f"Failed to notify improvement system: {response.status_code}")
                return False
                
        except requests.RequestException as e:
            self.logger.error(f"Failed to notify improvement system: {e}")
            return False
    
    def request_emergency_cleanup(self, target_size_reduction_gb: float = 1.0) -> Dict[str, Any]:
        """Request emergency cleanup from improvement system"""
        try:
            payload = {
                "action": "emergency_cleanup",
                "target_reduction_gb": target_size_reduction_gb,
                "requester": "storage_monitor",
                "urgency": "high",
                "timestamp": datetime.now().isoformat()
            }
            
            response = self.session.post(
                f"{self.improvement_url}/cleanup",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                self.logger.info(f"Emergency cleanup requested: {result}")
                return {"success": True, "result": result}
            else:
                self.logger.error(f"Cleanup request failed: {response.status_code}")
                return {"success": False, "error": f"HTTP {response.status_code}"}
                
        except requests.RequestException as e:
            self.logger.error(f"Cleanup request failed: {e}")
            return {"success": False, "error": str(e)}
    
    def get_checkpoint_status(self) -> Dict[str, Any]:
        """Get current checkpoint system status"""
        try:
            response = self.session.get(f"{self.improvement_url}/status", timeout=10)
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"HTTP {response.status_code}"}
                
        except requests.RequestException as e:
            self.logger.error(f"Failed to get checkpoint status: {e}")
            return {"error": str(e)}
    
    def trigger_checkpoint_cleanup(self, cleanup_type: str = "size") -> bool:
        """Trigger checkpoint cleanup in improvement system"""
        try:
            # Use the improvement system's cleanup script directly
            improvement_base = "/home/activeloguser/activelog/services/improvement-system"
            cleanup_script = f"{improvement_base}/bin/cleanup-checkpoints.sh"
            
            if Path(cleanup_script).exists():
                result = subprocess.run([cleanup_script, cleanup_type], 
                                      capture_output=True, text=True, timeout=120)
                
                if result.returncode == 0:
                    self.logger.info(f"Checkpoint cleanup '{cleanup_type}' completed successfully")
                    return True
                else:
                    self.logger.error(f"Checkpoint cleanup failed: {result.stderr}")
                    return False
            else:
                self.logger.warning("Improvement system cleanup script not found")
                return False
                
        except subprocess.TimeoutExpired:
            self.logger.error("Checkpoint cleanup timed out")
            return False
        except Exception as e:
            self.logger.error(f"Checkpoint cleanup failed: {e}")
            return False
    
    def coordinate_remediation_efforts(self, storage_alert: Dict[str, Any]) -> Dict[str, Any]:
        """Coordinate remediation efforts between systems"""
        try:
            path = storage_alert.get("path", "")
            growth_rate = storage_alert.get("growth_rate_mb_per_hour", 0)
            
            coordination_plan = {
                "storage_actions": [],
                "improvement_actions": [],
                "priority": "medium",
                "estimated_effectiveness": 0
            }
            
            # Determine if this is checkpoint-related
            if "checkpoint" in path.lower() or "improvement-system" in path:
                coordination_plan["improvement_actions"].extend([
                    "trigger_checkpoint_cleanup",
                    "review_checkpoint_policies",
                    "enable_aggressive_cleanup_mode"
                ])
                coordination_plan["priority"] = "high"
                coordination_plan["estimated_effectiveness"] += 70
                
                # Execute improvement system actions
                if self.trigger_checkpoint_cleanup("full"):
                    coordination_plan["improvement_actions"].append("cleanup_executed_successfully")
                else:
                    coordination_plan["improvement_actions"].append("cleanup_failed")
            
            # Determine storage monitor actions based on growth rate
            if growth_rate > 100:  # Critical growth
                coordination_plan["storage_actions"].extend([
                    "emergency_quarantine_large_files",
                    "stop_related_processes", 
                    "compress_old_files"
                ])
                coordination_plan["priority"] = "critical"
                coordination_plan["estimated_effectiveness"] += 50
                
            elif growth_rate > 50:  # High growth
                coordination_plan["storage_actions"].extend([
                    "quarantine_largest_files",
                    "compress_old_logs"
                ])
                coordination_plan["estimated_effectiveness"] += 30
            
            # Add monitoring actions
            coordination_plan["storage_actions"].append("increase_monitoring_frequency")
            
            return coordination_plan
            
        except Exception as e:
            self.logger.error(f"Coordination planning failed: {e}")
            return {"error": str(e)}
    
    def sync_configuration_changes(self) -> bool:
        """Sync configuration changes between systems"""
        try:
            # Get improvement system config
            improvement_config = self.get_checkpoint_status()
            
            if "error" not in improvement_config:
                # Extract relevant settings
                sync_data = {
                    "checkpoint_limits": {
                        "max_checkpoint_size_mb": improvement_config.get("max_checkpoint_size_mb", 100),
                        "max_total_size_gb": improvement_config.get("max_total_size_gb", 1),
                        "max_checkpoints": improvement_config.get("max_checkpoints", 5)
                    },
                    "monitoring_paths": [
                        improvement_config.get("checkpoint_dir", "/home/activeloguser/activelog/services/improvement-system/checkpoints")
                    ]
                }
                
                # Update storage monitor configuration
                response = self.session.post(
                    f"{self.storage_url}/config/sync",
                    json=sync_data,
                    timeout=10
                )
                
                if response.status_code == 200:
                    self.logger.info("Configuration sync completed successfully")
                    return True
                    
            return False
            
        except Exception as e:
            self.logger.error(f"Configuration sync failed: {e}")
            return False
    
    def report_storage_metrics_to_improvement_system(self, metrics: Dict[str, Any]) -> bool:
        """Report storage metrics to improvement system for analysis"""
        try:
            # Prepare metrics summary
            metrics_summary = {
                "timestamp": datetime.now().isoformat(),
                "total_monitored_size_gb": metrics.get("total_size_monitored_gb", 0),
                "growth_rate_mb_per_hour": metrics.get("avg_growth_rate", 0),
                "disk_usage_percent": metrics.get("disk_usage_percent", 0),
                "alerts_active": metrics.get("alerts_active", 0),
                "large_files_detected": metrics.get("large_files_count", 0),
                "remediation_success_rate": metrics.get("remediation_success_rate", 0)
            }
            
            # Send to improvement system
            response = self.session.post(
                f"{self.improvement_url}/storage-metrics",
                json=metrics_summary,
                timeout=5
            )
            
            return response.status_code == 200
            
        except Exception as e:
            self.logger.error(f"Failed to report storage metrics: {e}")
            return False
    
    def check_improvement_system_health(self) -> Dict[str, Any]:
        """Check health status of improvement system"""
        try:
            response = self.session.get(f"{self.improvement_url}/", timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "healthy": True,
                    "status": data.get("status", "unknown"),
                    "version": data.get("version", "unknown"),
                    "response_time_ms": response.elapsed.total_seconds() * 1000
                }
            else:
                return {
                    "healthy": False,
                    "status": f"HTTP {response.status_code}",
                    "error": "Non-200 response"
                }
                
        except requests.RequestException as e:
            return {
                "healthy": False,
                "status": "unreachable", 
                "error": str(e)
            }
    
    def create_joint_incident_response(self, incident_type: str, severity: str, 
                                     details: Dict[str, Any]) -> str:
        """Create joint incident response between both systems"""
        try:
            incident_id = f"storage_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            incident_data = {
                "incident_id": incident_id,
                "type": incident_type,
                "severity": severity,
                "created_at": datetime.now().isoformat(),
                "systems_involved": ["storage_monitor", "improvement_system"],
                "details": details,
                "status": "active",
                "response_plan": self._create_response_plan(incident_type, severity, details)
            }
            
            # Log incident locally
            self.logger.critical(f"Joint incident created: {incident_id} - {incident_type}")
            
            # Notify improvement system
            try:
                self.session.post(
                    f"{self.improvement_url}/incident",
                    json=incident_data,
                    timeout=10
                )
            except Exception as e:
                self.logger.warning(f"Failed to notify improvement system of incident: {e}")
            
            return incident_id
            
        except Exception as e:
            self.logger.error(f"Incident creation failed: {e}")
            return ""
    
    def _create_response_plan(self, incident_type: str, severity: str, 
                           details: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create automated response plan for incidents"""
        response_steps = []
        
        if incident_type == "runaway_storage_growth":
            if severity == "critical":
                response_steps.extend([
                    {
                        "step": 1,
                        "action": "emergency_stop_services",
                        "system": "both",
                        "timeout_minutes": 2,
                        "description": "Stop services contributing to growth"
                    },
                    {
                        "step": 2, 
                        "action": "emergency_cleanup",
                        "system": "improvement_system",
                        "timeout_minutes": 10,
                        "description": "Run emergency checkpoint cleanup"
                    },
                    {
                        "step": 3,
                        "action": "quarantine_large_files", 
                        "system": "storage_monitor",
                        "timeout_minutes": 5,
                        "description": "Move large files to quarantine"
                    }
                ])
            
            elif severity == "high":
                response_steps.extend([
                    {
                        "step": 1,
                        "action": "increase_monitoring_frequency",
                        "system": "storage_monitor", 
                        "timeout_minutes": 1,
                        "description": "Monitor every 30 seconds"
                    },
                    {
                        "step": 2,
                        "action": "trigger_cleanup",
                        "system": "improvement_system",
                        "timeout_minutes": 15,
                        "description": "Run scheduled cleanup operations"
                    }
                ])
        
        elif incident_type == "disk_space_critical":
            response_steps.extend([
                {
                    "step": 1,
                    "action": "emergency_space_recovery",
                    "system": "both",
                    "timeout_minutes": 5,
                    "description": "Free up disk space immediately"
                },
                {
                    "step": 2,
                    "action": "prevent_new_operations",
                    "system": "both", 
                    "timeout_minutes": 1,
                    "description": "Prevent operations that consume disk space"
                }
            ])
        
        return response_steps
    
    def execute_coordinated_response(self, response_plan: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Execute coordinated response plan"""
        execution_results = {
            "started_at": datetime.now().isoformat(),
            "steps_executed": [],
            "steps_failed": [],
            "overall_success": True
        }
        
        try:
            for step in response_plan:
                step_start = time.time()
                step_result = {
                    "step": step["step"],
                    "action": step["action"],
                    "system": step["system"],
                    "started_at": datetime.now().isoformat(),
                    "success": False,
                    "details": ""
                }
                
                try:
                    # Execute step based on system and action
                    if step["system"] == "storage_monitor" or step["system"] == "both":
                        success = self._execute_storage_action(step["action"], step)
                        if success:
                            step_result["success"] = True
                            step_result["details"] = "Storage action completed successfully"
                    
                    if step["system"] == "improvement_system" or step["system"] == "both":
                        success = self._execute_improvement_action(step["action"], step)
                        if success and step_result["success"]:
                            step_result["success"] = True
                            step_result["details"] = "Both systems completed successfully"
                        elif success:
                            step_result["success"] = True
                            step_result["details"] = "Improvement system action completed"
                
                except Exception as e:
                    step_result["details"] = f"Step execution failed: {e}"
                    execution_results["overall_success"] = False
                
                step_result["duration_seconds"] = time.time() - step_start
                
                if step_result["success"]:
                    execution_results["steps_executed"].append(step_result)
                else:
                    execution_results["steps_failed"].append(step_result)
                    execution_results["overall_success"] = False
            
            execution_results["completed_at"] = datetime.now().isoformat()
            return execution_results
            
        except Exception as e:
            self.logger.error(f"Coordinated response execution failed: {e}")
            execution_results["error"] = str(e)
            execution_results["overall_success"] = False
            return execution_results
    
    def _execute_storage_action(self, action: str, step: Dict[str, Any]) -> bool:
        """Execute storage monitor specific actions"""
        try:
            if action == "emergency_stop_services":
                # This would stop services - placeholder for safety
                self.logger.info("Emergency service stop requested")
                return True
                
            elif action == "quarantine_large_files":
                # Trigger quarantine via API
                response = self.session.post(
                    f"{self.storage_url}/remediate",
                    json={
                        "action": "quarantine_large_files",
                        "path": step.get("target_path", "/"),
                        "confirm": True
                    },
                    timeout=step.get("timeout_minutes", 5) * 60
                )
                return response.status_code == 200
                
            elif action == "increase_monitoring_frequency":
                # Update monitoring config
                response = self.session.post(
                    f"{self.storage_url}/config",
                    json={"thresholds": {"scan_interval_seconds": 30}},
                    timeout=10
                )
                return response.status_code == 200
                
            return False
            
        except Exception as e:
            self.logger.error(f"Storage action '{action}' failed: {e}")
            return False
    
    def _execute_improvement_action(self, action: str, step: Dict[str, Any]) -> bool:
        """Execute improvement system specific actions"""
        try:
            if action == "emergency_cleanup":
                return self.trigger_checkpoint_cleanup("full")
                
            elif action == "trigger_cleanup":
                return self.trigger_checkpoint_cleanup("size")
                
            elif action == "emergency_stop_services":
                # This would coordinate with improvement system to stop services
                self.logger.info("Emergency service stop requested from improvement system")
                return True
                
            return False
            
        except Exception as e:
            self.logger.error(f"Improvement action '{action}' failed: {e}")
            return False
    
    def get_integration_status(self) -> Dict[str, Any]:
        """Get overall integration status between systems"""
        try:
            improvement_health = self.check_improvement_system_health()
            checkpoint_status = self.get_checkpoint_status()
            
            return {
                "integration_healthy": improvement_health.get("healthy", False),
                "improvement_system": improvement_health,
                "checkpoint_system": checkpoint_status,
                "last_sync": datetime.now().isoformat(),
                "communication_latency_ms": improvement_health.get("response_time_ms", 0)
            }
            
        except Exception as e:
            return {
                "integration_healthy": False,
                "error": str(e)
            }

class StorageMonitorIntegrationEndpoints:
    """Additional API endpoints for storage monitor to handle improvement system integration"""
    
    def __init__(self, integration: ImprovementSystemIntegration):
        self.integration = integration
        self.logger = logging.getLogger('StorageMonitorIntegration')
    
    async def handle_improvement_alert(self, alert_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming alerts from improvement system"""
        try:
            alert_type = alert_data.get("type", "unknown")
            severity = alert_data.get("severity", "low")
            
            if alert_type == "checkpoint_size_exceeded":
                # Coordinate response to checkpoint size issues
                response = self.integration.coordinate_remediation_efforts({
                    "path": alert_data.get("path", ""),
                    "growth_rate_mb_per_hour": alert_data.get("growth_rate", 0)
                })
                
                return {"status": "processing", "response_plan": response}
                
            elif alert_type == "cleanup_failed":
                # Handle cleanup failures
                self.logger.warning(f"Improvement system cleanup failed: {alert_data}")
                return {"status": "acknowledged", "action": "escalate_to_manual_intervention"}
            
            return {"status": "acknowledged", "message": "Alert received and logged"}
            
        except Exception as e:
            self.logger.error(f"Failed to handle improvement alert: {e}")
            return {"status": "error", "message": str(e)}
    
    async def provide_storage_recommendations(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Provide storage recommendations to improvement system"""
        try:
            context = request_data.get("context", "general")
            current_usage = request_data.get("current_disk_usage_percent", 0)
            
            recommendations = []
            
            if context == "checkpoint_creation":
                if current_usage > 90:
                    recommendations.extend([
                        "CRITICAL: Defer checkpoint creation until cleanup completed",
                        "Enable aggressive cleanup mode immediately",
                        "Consider temporary service shutdown"
                    ])
                elif current_usage > 80:
                    recommendations.extend([
                        "WARNING: Run cleanup before checkpoint creation",
                        "Monitor disk space during checkpoint process"
                    ])
                else:
                    recommendations.append("Safe to proceed with checkpoint creation")
            
            elif context == "general_optimization":
                recommendations.extend([
                    f"Current disk usage: {current_usage:.1f}%",
                    "Maintain regular cleanup schedules",
                    "Monitor for growth acceleration patterns"
                ])
            
            return {
                "recommendations": recommendations,
                "safe_to_proceed": current_usage < 85,
                "suggested_cleanup_mb": max(0, (current_usage - 75) * 10) if current_usage > 75 else 0
            }
            
        except Exception as e:
            self.logger.error(f"Failed to provide storage recommendations: {e}")
            return {"error": str(e)}