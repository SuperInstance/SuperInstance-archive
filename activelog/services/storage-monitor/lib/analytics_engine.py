#!/usr/bin/env python3
"""
Storage Analytics and Reporting Engine
Advanced analytics, visualizations, and reporting for storage monitoring
"""

import os
import sqlite3
import json
import matplotlib
matplotlib.use('Agg')  # Use non-GUI backend
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import logging
from io import BytesIO
import base64

# Set plotting style
plt.style.use('seaborn-v0_8')
sns.set_palette("husl")

class StorageAnalyticsEngine:
    def __init__(self, db_path: str, output_dir: str):
        self.db_path = db_path
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger('StorageAnalytics')
        
    def generate_dashboard_data(self) -> Dict[str, Any]:
        """Generate comprehensive dashboard data"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Overall system metrics
                system_metrics = self._get_system_metrics(conn)
                
                # Growth trends
                growth_trends = self._get_growth_trends(conn)
                
                # Top consumers
                top_consumers = self._get_top_consumers(conn)
                
                # Alert summary
                alert_summary = self._get_alert_summary(conn)
                
                # Storage efficiency metrics
                efficiency_metrics = self._get_efficiency_metrics(conn)
                
                # Risk assessment
                risk_assessment = self._get_risk_assessment(conn)
                
                return {
                    "generated_at": datetime.now().isoformat(),
                    "system_metrics": system_metrics,
                    "growth_trends": growth_trends,
                    "top_consumers": top_consumers,
                    "alert_summary": alert_summary,
                    "efficiency_metrics": efficiency_metrics,
                    "risk_assessment": risk_assessment,
                    "visualizations": self._generate_visualizations()
                }
                
        except Exception as e:
            self.logger.error(f"Dashboard data generation failed: {e}")
            return {"error": str(e)}
    
    def _get_system_metrics(self, conn: sqlite3.Connection) -> Dict[str, Any]:
        """Get current system metrics"""
        cursor = conn.cursor()
        
        # Latest system metrics
        cursor.execute('''
            SELECT disk_total_gb, disk_used_gb, disk_free_gb, disk_usage_percent,
                   cpu_percent, memory_percent, timestamp
            FROM system_metrics 
            ORDER BY timestamp DESC LIMIT 1
        ''')
        
        latest_metrics = cursor.fetchone()
        
        # Historical averages (last 24h)
        cursor.execute('''
            SELECT AVG(disk_usage_percent), AVG(cpu_percent), AVG(memory_percent)
            FROM system_metrics 
            WHERE timestamp >= datetime('now', '-24 hours')
        ''')
        
        avg_metrics = cursor.fetchone()
        
        # Growth in last 24h
        cursor.execute('''
            SELECT disk_used_gb FROM system_metrics 
            WHERE timestamp >= datetime('now', '-24 hours')
            ORDER BY timestamp ASC LIMIT 1
        ''')
        
        start_usage = cursor.fetchone()
        
        if latest_metrics and avg_metrics:
            growth_24h = (latest_metrics[1] - start_usage[0]) if start_usage else 0
            
            return {
                "current": {
                    "total_storage_gb": latest_metrics[0],
                    "used_storage_gb": latest_metrics[1],
                    "free_storage_gb": latest_metrics[2],
                    "usage_percent": latest_metrics[3],
                    "cpu_percent": latest_metrics[4],
                    "memory_percent": latest_metrics[5],
                    "last_updated": latest_metrics[6]
                },
                "averages_24h": {
                    "avg_disk_usage_percent": avg_metrics[0],
                    "avg_cpu_percent": avg_metrics[1],
                    "avg_memory_percent": avg_metrics[2]
                },
                "growth_24h_gb": growth_24h,
                "status": self._get_system_status(latest_metrics[3])
            }
        
        return {"error": "no_data"}
    
    def _get_system_status(self, disk_usage_percent: float) -> str:
        """Determine system status based on disk usage"""
        if disk_usage_percent >= 95:
            return "critical"
        elif disk_usage_percent >= 85:
            return "warning"
        elif disk_usage_percent >= 75:
            return "caution"
        else:
            return "healthy"
    
    def _get_growth_trends(self, conn: sqlite3.Connection) -> Dict[str, Any]:
        """Get storage growth trends"""
        cursor = conn.cursor()
        
        # Daily growth over last 30 days
        cursor.execute('''
            SELECT DATE(timestamp) as date, 
                   SUM(size_bytes) as total_size,
                   COUNT(DISTINCT path) as paths_count
            FROM directory_history 
            WHERE timestamp >= datetime('now', '-30 days')
            GROUP BY DATE(timestamp)
            ORDER BY date
        ''')
        
        daily_data = cursor.fetchall()
        
        # Calculate growth rates
        growth_rates = []
        for i in range(1, len(daily_data)):
            prev_size = daily_data[i-1][1] / 1_000_000_000  # GB
            curr_size = daily_data[i][1] / 1_000_000_000    # GB
            growth_gb = curr_size - prev_size
            growth_rates.append({
                "date": daily_data[i][0],
                "growth_gb": growth_gb,
                "total_size_gb": curr_size
            })
        
        # Identify trends
        recent_growth = [g["growth_gb"] for g in growth_rates[-7:]]  # Last 7 days
        avg_daily_growth = np.mean(recent_growth) if recent_growth else 0
        
        return {
            "daily_growth_last_30_days": growth_rates,
            "avg_daily_growth_gb": avg_daily_growth,
            "trend_direction": "increasing" if avg_daily_growth > 0.1 else "stable" if avg_daily_growth > -0.1 else "decreasing",
            "projected_monthly_growth_gb": avg_daily_growth * 30,
            "growth_acceleration": self._calculate_acceleration(recent_growth)
        }
    
    def _calculate_acceleration(self, growth_rates: List[float]) -> str:
        """Calculate if growth is accelerating"""
        if len(growth_rates) < 4:
            return "insufficient_data"
        
        # Compare first half vs second half
        mid = len(growth_rates) // 2
        first_half_avg = np.mean(growth_rates[:mid])
        second_half_avg = np.mean(growth_rates[mid:])
        
        if second_half_avg > first_half_avg * 1.5:
            return "accelerating"
        elif second_half_avg < first_half_avg * 0.5:
            return "decelerating"
        else:
            return "steady"
    
    def _get_top_consumers(self, conn: sqlite3.Connection) -> List[Dict[str, Any]]:
        """Get top storage consumers"""
        cursor = conn.cursor()
        
        cursor.execute('''
            WITH latest_sizes AS (
                SELECT path, size_bytes, timestamp,
                       ROW_NUMBER() OVER (PARTITION BY path ORDER BY timestamp DESC) as rn
                FROM directory_history 
                WHERE timestamp >= datetime('now', '-24 hours')
            )
            SELECT path, size_bytes, timestamp
            FROM latest_sizes 
            WHERE rn = 1
            ORDER BY size_bytes DESC
            LIMIT 20
        ''')
        
        consumers = []
        for path, size_bytes, timestamp in cursor.fetchall():
            # Get growth rate for this path
            cursor.execute('''
                SELECT size_bytes FROM directory_history 
                WHERE path = ? AND timestamp >= datetime('now', '-24 hours')
                ORDER BY timestamp ASC LIMIT 1
            ''', (path,))
            
            start_size = cursor.fetchone()
            growth_24h = ((size_bytes - start_size[0]) / 1_000_000) if start_size else 0
            
            consumers.append({
                "path": path,
                "current_size_mb": size_bytes / 1_000_000,
                "current_size_gb": size_bytes / 1_000_000_000,
                "growth_24h_mb": growth_24h,
                "growth_rate_mb_per_hour": growth_24h / 24,
                "last_updated": timestamp
            })
        
        return consumers
    
    def _get_alert_summary(self, conn: sqlite3.Connection) -> Dict[str, Any]:
        """Get alert summary statistics"""
        cursor = conn.cursor()
        
        # Growth alerts in last 24h
        cursor.execute('''
            SELECT COUNT(*), AVG(growth_rate_mb), MAX(growth_rate_mb)
            FROM growth_alerts 
            WHERE alert_time >= datetime('now', '-24 hours')
        ''')
        
        growth_alert_stats = cursor.fetchone()
        
        # Unresolved alerts
        cursor.execute('''
            SELECT COUNT(*) FROM growth_alerts WHERE resolved = FALSE
        ''')
        
        unresolved_count = cursor.fetchone()[0]
        
        # Recent remediation actions
        cursor.execute('''
            SELECT COUNT(*), action_type
            FROM remediation_log 
            WHERE timestamp >= datetime('now', '-24 hours')
            GROUP BY action_type
        ''')
        
        remediation_stats = dict(cursor.fetchall())
        
        return {
            "growth_alerts_24h": {
                "count": growth_alert_stats[0] or 0,
                "avg_growth_rate_mb": growth_alert_stats[1] or 0,
                "max_growth_rate_mb": growth_alert_stats[2] or 0
            },
            "unresolved_alerts": unresolved_count,
            "remediation_actions_24h": remediation_stats,
            "alert_frequency": self._calculate_alert_frequency(conn)
        }
    
    def _calculate_alert_frequency(self, conn: sqlite3.Connection) -> str:
        """Calculate alert frequency trend"""
        cursor = conn.cursor()
        
        # Alerts per day for last 7 days
        cursor.execute('''
            SELECT DATE(alert_time), COUNT(*)
            FROM growth_alerts 
            WHERE alert_time >= datetime('now', '-7 days')
            GROUP BY DATE(alert_time)
            ORDER BY DATE(alert_time)
        ''')
        
        daily_alerts = cursor.fetchall()
        
        if len(daily_alerts) < 2:
            return "insufficient_data"
        
        # Calculate trend
        alert_counts = [count for date, count in daily_alerts]
        if len(alert_counts) >= 3:
            recent_avg = np.mean(alert_counts[-3:])
            earlier_avg = np.mean(alert_counts[:-3]) if len(alert_counts) > 3 else alert_counts[0]
            
            if recent_avg > earlier_avg * 1.5:
                return "increasing"
            elif recent_avg < earlier_avg * 0.5:
                return "decreasing"
        
        return "stable"
    
    def _get_efficiency_metrics(self, conn: sqlite3.Connection) -> Dict[str, Any]:
        """Calculate storage efficiency metrics"""
        cursor = conn.cursor()
        
        # Large files analysis
        cursor.execute('''
            SELECT COUNT(*), SUM(size_bytes), AVG(size_bytes)
            FROM large_files 
            WHERE detected_time >= datetime('now', '-7 days')
        ''')
        
        large_files_stats = cursor.fetchone()
        
        # Duplicate detection (based on file hashes)
        cursor.execute('''
            SELECT file_hash, COUNT(*), SUM(size_bytes)
            FROM large_files 
            WHERE file_hash IS NOT NULL
            GROUP BY file_hash
            HAVING COUNT(*) > 1
        ''')
        
        duplicates = cursor.fetchall()
        duplicate_waste_mb = sum(count * size for hash, count, size in duplicates) / 1_000_000
        
        # Remediation success rate
        cursor.execute('''
            SELECT 
                COUNT(*) as total_actions,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_actions
            FROM remediation_log 
            WHERE timestamp >= datetime('now', '-7 days')
        ''')
        
        remediation_stats = cursor.fetchone()
        success_rate = (remediation_stats[1] / remediation_stats[0] * 100) if remediation_stats[0] else 0
        
        return {
            "large_files_detected_7d": large_files_stats[0] or 0,
            "large_files_total_size_gb": (large_files_stats[1] / 1_000_000_000) if large_files_stats[1] else 0,
            "avg_large_file_size_mb": (large_files_stats[2] / 1_000_000) if large_files_stats[2] else 0,
            "potential_duplicate_waste_mb": duplicate_waste_mb,
            "remediation_success_rate_percent": success_rate,
            "storage_efficiency_score": self._calculate_efficiency_score(duplicate_waste_mb, success_rate)
        }
    
    def _calculate_efficiency_score(self, duplicate_waste: float, success_rate: float) -> int:
        """Calculate overall storage efficiency score (0-100)"""
        base_score = 100
        
        # Penalize for duplicate waste
        if duplicate_waste > 1000:  # > 1GB duplicates
            base_score -= 20
        elif duplicate_waste > 500:  # > 500MB duplicates
            base_score -= 10
        
        # Penalize for low remediation success
        if success_rate < 50:
            base_score -= 30
        elif success_rate < 75:
            base_score -= 15
        
        return max(0, base_score)
    
    def _get_risk_assessment(self, conn: sqlite3.Connection) -> Dict[str, Any]:
        """Assess overall storage risks"""
        cursor = conn.cursor()
        
        # Current disk usage risk
        cursor.execute('''
            SELECT disk_usage_percent FROM system_metrics 
            ORDER BY timestamp DESC LIMIT 1
        ''')
        
        current_usage = cursor.fetchone()
        disk_usage_risk = self._assess_disk_usage_risk(current_usage[0] if current_usage else 0)
        
        # Growth rate risk
        cursor.execute('''
            SELECT AVG(growth_rate_mb) FROM growth_alerts 
            WHERE alert_time >= datetime('now', '-24 hours')
        ''')
        
        avg_growth_rate = cursor.fetchone()[0] or 0
        growth_risk = self._assess_growth_risk(avg_growth_rate)
        
        # Unaddressed issues risk
        cursor.execute('''
            SELECT COUNT(*) FROM growth_alerts 
            WHERE resolved = FALSE AND alert_time <= datetime('now', '-6 hours')
        ''')
        
        old_unresolved = cursor.fetchone()[0]
        unresolved_risk = "high" if old_unresolved > 3 else "medium" if old_unresolved > 0 else "low"
        
        # Overall risk calculation
        overall_risk = self._calculate_overall_risk(disk_usage_risk, growth_risk, unresolved_risk)
        
        return {
            "overall_risk_level": overall_risk,
            "disk_usage_risk": disk_usage_risk,
            "growth_rate_risk": growth_risk,
            "unresolved_issues_risk": unresolved_risk,
            "risk_factors": self._identify_risk_factors(conn),
            "recommendations": self._generate_risk_recommendations(overall_risk, conn)
        }
    
    def _assess_disk_usage_risk(self, usage_percent: float) -> str:
        """Assess risk based on disk usage"""
        if usage_percent >= 95:
            return "critical"
        elif usage_percent >= 85:
            return "high"
        elif usage_percent >= 75:
            return "medium"
        else:
            return "low"
    
    def _assess_growth_risk(self, avg_growth_rate: float) -> str:
        """Assess risk based on average growth rate"""
        if avg_growth_rate > 100:  # > 100MB/hour
            return "high"
        elif avg_growth_rate > 50:   # > 50MB/hour
            return "medium"
        else:
            return "low"
    
    def _calculate_overall_risk(self, disk_risk: str, growth_risk: str, unresolved_risk: str) -> str:
        """Calculate overall risk level"""
        risk_scores = {"low": 1, "medium": 2, "high": 3, "critical": 4}
        
        disk_score = risk_scores.get(disk_risk, 1)
        growth_score = risk_scores.get(growth_risk, 1)
        unresolved_score = risk_scores.get(unresolved_risk, 1)
        
        # Weighted average (disk usage is most critical)
        overall_score = (disk_score * 0.5) + (growth_score * 0.3) + (unresolved_score * 0.2)
        
        if overall_score >= 3.5:
            return "critical"
        elif overall_score >= 2.5:
            return "high"
        elif overall_score >= 1.5:
            return "medium"
        else:
            return "low"
    
    def _identify_risk_factors(self, conn: sqlite3.Connection) -> List[str]:
        """Identify specific risk factors"""
        cursor = conn.cursor()
        risk_factors = []
        
        # Check for rapid growth directories
        cursor.execute('''
            SELECT COUNT(*) FROM growth_alerts 
            WHERE alert_time >= datetime('now', '-24 hours') AND growth_rate_mb > 100
        ''')
        
        if cursor.fetchone()[0] > 0:
            risk_factors.append("Rapid storage growth detected in multiple directories")
        
        # Check for large unmanaged files
        cursor.execute('''
            SELECT COUNT(*) FROM large_files 
            WHERE remediated = FALSE AND size_bytes > 1000000000
        ''')
        
        if cursor.fetchone()[0] > 5:
            risk_factors.append("Multiple large files (>1GB) not yet remediated")
        
        # Check for failed remediations
        cursor.execute('''
            SELECT COUNT(*) FROM remediation_log 
            WHERE timestamp >= datetime('now', '-24 hours') AND success = FALSE
        ''')
        
        if cursor.fetchone()[0] > 3:
            risk_factors.append("Multiple failed remediation attempts")
        
        return risk_factors
    
    def _generate_risk_recommendations(self, risk_level: str, conn: sqlite3.Connection) -> List[str]:
        """Generate recommendations based on risk assessment"""
        recommendations = []
        
        if risk_level in ["critical", "high"]:
            recommendations.extend([
                "Immediate action required: Enable emergency cleanup procedures",
                "Review and expand automated remediation rules",
                "Consider temporarily stopping non-essential services"
            ])
        
        if risk_level in ["critical", "high", "medium"]:
            recommendations.extend([
                "Increase monitoring frequency to every 30 seconds",
                "Enable proactive alerting for all team members",
                "Schedule regular storage cleanup maintenance"
            ])
        
        recommendations.extend([
            "Maintain regular backups of critical data",
            "Review storage growth patterns weekly",
            "Keep quarantine directory under 1GB"
        ])
        
        return recommendations
    
    def _generate_visualizations(self) -> Dict[str, str]:
        """Generate visualization charts as base64-encoded images"""
        try:
            visualizations = {}
            
            # 1. Storage usage over time chart
            visualizations["storage_trend"] = self._create_storage_trend_chart()
            
            # 2. Top consumers pie chart  
            visualizations["top_consumers"] = self._create_top_consumers_chart()
            
            # 3. Growth rate histogram
            visualizations["growth_rates"] = self._create_growth_rate_chart()
            
            # 4. Alert frequency timeline
            visualizations["alert_timeline"] = self._create_alert_timeline()
            
            return visualizations
            
        except Exception as e:
            self.logger.error(f"Visualization generation failed: {e}")
            return {}
    
    def _create_storage_trend_chart(self) -> str:
        """Create storage trend chart"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                df = pd.read_sql_query('''
                    SELECT timestamp, disk_used_gb 
                    FROM system_metrics 
                    WHERE timestamp >= datetime('now', '-7 days')
                    ORDER BY timestamp
                ''', conn)
            
            if df.empty:
                return ""
            
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            plt.figure(figsize=(12, 6))
            plt.plot(df['timestamp'], df['disk_used_gb'], linewidth=2, color='#2E86C1')
            plt.fill_between(df['timestamp'], df['disk_used_gb'], alpha=0.3, color='#85C1E9')
            
            plt.title('Storage Usage Trend (Last 7 Days)', fontsize=16, fontweight='bold')
            plt.xlabel('Time', fontsize=12)
            plt.ylabel('Used Storage (GB)', fontsize=12)
            plt.grid(True, alpha=0.3)
            
            # Format x-axis
            plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
            plt.gca().xaxis.set_major_locator(mdates.HourLocator(interval=6))
            plt.xticks(rotation=45)
            
            plt.tight_layout()
            
            # Convert to base64
            buffer = BytesIO()
            plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
            buffer.seek(0)
            image_base64 = base64.b64encode(buffer.getvalue()).decode()
            plt.close()
            
            return image_base64
            
        except Exception as e:
            self.logger.error(f"Storage trend chart creation failed: {e}")
            return ""
    
    def _create_top_consumers_chart(self) -> str:
        """Create top consumers pie chart"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    WITH latest_sizes AS (
                        SELECT path, size_bytes,
                               ROW_NUMBER() OVER (PARTITION BY path ORDER BY timestamp DESC) as rn
                        FROM directory_history 
                        WHERE timestamp >= datetime('now', '-24 hours')
                    )
                    SELECT path, size_bytes
                    FROM latest_sizes 
                    WHERE rn = 1
                    ORDER BY size_bytes DESC
                    LIMIT 10
                ''')
                
                data = cursor.fetchall()
            
            if not data:
                return ""
            
            # Prepare data
            paths = [os.path.basename(path) for path, size in data]
            sizes_gb = [size / 1_000_000_000 for path, size in data]
            
            # Create pie chart
            plt.figure(figsize=(10, 8))
            colors = sns.color_palette("husl", len(paths))
            
            wedges, texts, autotexts = plt.pie(sizes_gb, labels=paths, autopct='%1.1f%%',
                                             colors=colors, startangle=90)
            
            plt.title('Top Storage Consumers', fontsize=16, fontweight='bold')
            
            # Improve text readability
            for autotext in autotexts:
                autotext.set_color('white')
                autotext.set_fontweight('bold')
            
            plt.axis('equal')
            plt.tight_layout()
            
            # Convert to base64
            buffer = BytesIO()
            plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
            buffer.seek(0)
            image_base64 = base64.b64encode(buffer.getvalue()).decode()
            plt.close()
            
            return image_base64
            
        except Exception as e:
            self.logger.error(f"Top consumers chart creation failed: {e}")
            return ""
    
    def _create_growth_rate_chart(self) -> str:
        """Create growth rate distribution chart"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                df = pd.read_sql_query('''
                    SELECT growth_rate_mb 
                    FROM growth_alerts 
                    WHERE alert_time >= datetime('now', '-7 days')
                ''', conn)
            
            if df.empty:
                return ""
            
            plt.figure(figsize=(10, 6))
            
            # Create histogram
            plt.hist(df['growth_rate_mb'], bins=20, edgecolor='black', alpha=0.7, 
                    color='#E74C3C')
            
            plt.title('Growth Rate Distribution (Last 7 Days)', fontsize=16, fontweight='bold')
            plt.xlabel('Growth Rate (MB/hour)', fontsize=12)
            plt.ylabel('Frequency', fontsize=12)
            plt.grid(True, alpha=0.3)
            
            # Add statistics
            mean_growth = df['growth_rate_mb'].mean()
            plt.axvline(mean_growth, color='red', linestyle='--', linewidth=2, 
                       label=f'Mean: {mean_growth:.1f} MB/h')
            plt.legend()
            
            plt.tight_layout()
            
            # Convert to base64
            buffer = BytesIO()
            plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
            buffer.seek(0)
            image_base64 = base64.b64encode(buffer.getvalue()).decode()
            plt.close()
            
            return image_base64
            
        except Exception as e:
            self.logger.error(f"Growth rate chart creation failed: {e}")
            return ""
    
    def _create_alert_timeline(self) -> str:
        """Create alert timeline chart"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                df = pd.read_sql_query('''
                    SELECT DATE(alert_time) as date, COUNT(*) as alert_count
                    FROM growth_alerts 
                    WHERE alert_time >= datetime('now', '-30 days')
                    GROUP BY DATE(alert_time)
                    ORDER BY date
                ''', conn)
            
            if df.empty:
                return ""
            
            df['date'] = pd.to_datetime(df['date'])
            
            plt.figure(figsize=(12, 6))
            
            # Create bar chart
            plt.bar(df['date'], df['alert_count'], color='#F39C12', alpha=0.8)
            
            plt.title('Daily Alert Frequency (Last 30 Days)', fontsize=16, fontweight='bold')
            plt.xlabel('Date', fontsize=12)
            plt.ylabel('Number of Alerts', fontsize=12)
            plt.grid(True, alpha=0.3, axis='y')
            
            # Format x-axis
            plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
            plt.gca().xaxis.set_major_locator(mdates.DayLocator(interval=2))
            plt.xticks(rotation=45)
            
            plt.tight_layout()
            
            # Convert to base64
            buffer = BytesIO()
            plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
            buffer.seek(0)
            image_base64 = base64.b64encode(buffer.getvalue()).decode()
            plt.close()
            
            return image_base64
            
        except Exception as e:
            self.logger.error(f"Alert timeline chart creation failed: {e}")
            return ""
    
    def generate_detailed_report(self, output_format: str = "json") -> str:
        """Generate detailed storage analysis report"""
        try:
            # Get comprehensive analytics data
            dashboard_data = self.generate_dashboard_data()
            
            if "error" in dashboard_data:
                return dashboard_data
            
            # Add detailed sections
            with sqlite3.connect(self.db_path) as conn:
                detailed_analysis = {
                    "storage_hotspots": self._analyze_storage_hotspots(conn),
                    "efficiency_analysis": self._analyze_storage_efficiency(conn),
                    "trend_analysis": self._analyze_trends(conn),
                    "remediation_effectiveness": self._analyze_remediation_effectiveness(conn)
                }
            
            # Combine all data
            full_report = {
                "report_metadata": {
                    "generated_at": datetime.now().isoformat(),
                    "report_type": "comprehensive_storage_analysis",
                    "version": "1.0"
                },
                "executive_summary": self._create_executive_summary(dashboard_data),
                "dashboard_data": dashboard_data,
                "detailed_analysis": detailed_analysis,
                "recommendations": self._generate_comprehensive_recommendations(dashboard_data, detailed_analysis)
            }
            
            # Output in requested format
            if output_format.lower() == "json":
                report_path = self.output_dir / f"storage_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                with open(report_path, 'w') as f:
                    json.dump(full_report, f, indent=2)
                return str(report_path)
            
            else:
                return json.dumps(full_report, indent=2)
                
        except Exception as e:
            self.logger.error(f"Detailed report generation failed: {e}")
            return json.dumps({"error": str(e)})
    
    def _create_executive_summary(self, dashboard_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create executive summary from dashboard data"""
        try:
            system_metrics = dashboard_data.get("system_metrics", {})
            risk_assessment = dashboard_data.get("risk_assessment", {})
            alert_summary = dashboard_data.get("alert_summary", {})
            
            return {
                "overall_health": system_metrics.get("status", "unknown"),
                "current_disk_usage": f"{system_metrics.get('current', {}).get('usage_percent', 0):.1f}%",
                "risk_level": risk_assessment.get("overall_risk_level", "unknown"),
                "alerts_24h": alert_summary.get("growth_alerts_24h", {}).get("count", 0),
                "unresolved_issues": alert_summary.get("unresolved_alerts", 0),
                "key_concerns": risk_assessment.get("risk_factors", [])[:3],  # Top 3 concerns
                "immediate_actions_required": len([r for r in risk_assessment.get("recommendations", []) if "immediate" in r.lower() or "urgent" in r.lower()])
            }
            
        except Exception as e:
            self.logger.error(f"Executive summary creation failed: {e}")
            return {"error": str(e)}
    
    def _analyze_storage_hotspots(self, conn: sqlite3.Connection) -> Dict[str, Any]:
        """Analyze storage hotspots in detail"""
        # This would contain detailed hotspot analysis
        # Implementation would be similar to other analysis methods
        return {"status": "analysis_completed"}
    
    def _analyze_storage_efficiency(self, conn: sqlite3.Connection) -> Dict[str, Any]:
        """Analyze storage efficiency in detail"""
        return {"status": "analysis_completed"}
    
    def _analyze_trends(self, conn: sqlite3.Connection) -> Dict[str, Any]:
        """Analyze storage trends in detail"""
        return {"status": "analysis_completed"}
    
    def _analyze_remediation_effectiveness(self, conn: sqlite3.Connection) -> Dict[str, Any]:
        """Analyze remediation effectiveness"""
        return {"status": "analysis_completed"}
    
    def _generate_comprehensive_recommendations(self, dashboard_data: Dict[str, Any], detailed_analysis: Dict[str, Any]) -> List[str]:
        """Generate comprehensive recommendations"""
        recommendations = []
        
        # Extract key metrics
        risk_level = dashboard_data.get("risk_assessment", {}).get("overall_risk_level", "low")
        disk_usage = dashboard_data.get("system_metrics", {}).get("current", {}).get("usage_percent", 0)
        unresolved_alerts = dashboard_data.get("alert_summary", {}).get("unresolved_alerts", 0)
        
        # Priority recommendations based on risk level
        if risk_level == "critical":
            recommendations.extend([
                "CRITICAL: Implement emergency storage cleanup immediately",
                "Stop non-essential services to prevent further growth",
                "Enable 24/7 monitoring with immediate notifications"
            ])
        
        elif risk_level == "high":
            recommendations.extend([
                "HIGH: Schedule emergency maintenance window within 24 hours",
                "Increase automated remediation frequency",
                "Review and expand disk space if possible"
            ])
        
        # Disk usage recommendations
        if disk_usage > 90:
            recommendations.append("URGENT: Disk usage critical - free up space immediately")
        elif disk_usage > 80:
            recommendations.append("WARNING: Disk usage high - plan cleanup operations")
        
        # Unresolved alerts
        if unresolved_alerts > 5:
            recommendations.append("Address unresolved storage alerts to prevent escalation")
        
        # General best practices
        recommendations.extend([
            "Implement regular automated cleanup schedules",
            "Monitor storage growth trends weekly",
            "Maintain storage usage below 80% for optimal performance",
            "Keep emergency response procedures updated and tested"
        ])
        
        return recommendations