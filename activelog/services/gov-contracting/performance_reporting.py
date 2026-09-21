#!/usr/bin/env python3
"""
Performance Reporting System
Comprehensive KPI tracking and performance reporting for government contracts
"""

import asyncio
import logging
import sqlite3
import json
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Any
from enum import Enum
import uuid
import statistics

logger = logging.getLogger(__name__)

class ReportType(Enum):
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"
    MILESTONE = "milestone"
    AD_HOC = "ad_hoc"

class KPICategory(Enum):
    COST = "cost"
    SCHEDULE = "schedule"
    QUALITY = "quality"
    CUSTOMER_SATISFACTION = "customer_satisfaction"
    RISK = "risk"
    RESOURCE_UTILIZATION = "resource_utilization"
    DELIVERY = "delivery"

class PerformanceStatus(Enum):
    ON_TARGET = "on_target"
    AHEAD = "ahead"
    BEHIND = "behind"
    AT_RISK = "at_risk"
    CRITICAL = "critical"

class TrendDirection(Enum):
    IMPROVING = "improving"
    STABLE = "stable"
    DECLINING = "declining"
    VOLATILE = "volatile"

class PerformanceReportingSystem:
    def __init__(self):
        self.db_path = "data/performance_reporting.db"
        self.kpi_definitions = {}
        self.dashboard_templates = {}

    async def initialize(self):
        """Initialize performance reporting system"""
        try:
            await self._create_database_schema()
            await self._setup_kpi_definitions()
            await self._setup_dashboard_templates()
            logger.info("Performance Reporting System initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Performance Reporting System: {e}")
            raise

    async def _create_database_schema(self):
        """Create database tables for performance reporting"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # KPI metrics table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS kpi_metrics (
                id TEXT PRIMARY KEY,
                contract_id TEXT NOT NULL,
                kpi_name TEXT NOT NULL,
                kpi_category TEXT NOT NULL,
                measurement_period TEXT NOT NULL,
                target_value REAL,
                actual_value REAL,
                variance_value REAL,
                variance_percentage REAL,
                unit_of_measure TEXT,
                data_source TEXT,
                collection_date TEXT NOT NULL,
                performance_status TEXT,
                trend_direction TEXT,
                notes TEXT,
                collected_by TEXT,
                approved_by TEXT,
                created_at TEXT NOT NULL
            )
        """)
        
        # Performance reports table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS performance_reports (
                id TEXT PRIMARY KEY,
                contract_id TEXT NOT NULL,
                report_type TEXT NOT NULL,
                reporting_period_start TEXT NOT NULL,
                reporting_period_end TEXT NOT NULL,
                report_title TEXT NOT NULL,
                executive_summary TEXT,
                key_accomplishments TEXT,
                challenges_issues TEXT,
                risk_mitigation TEXT,
                upcoming_activities TEXT,
                overall_status TEXT,
                cost_performance_index REAL,
                schedule_performance_index REAL,
                quality_score REAL,
                customer_satisfaction REAL,
                report_data TEXT,
                generated_by TEXT,
                approved_by TEXT,
                approval_date TEXT,
                distribution_list TEXT,
                status TEXT NOT NULL DEFAULT 'draft',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        # Contract milestones tracking table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS milestone_tracking (
                id TEXT PRIMARY KEY,
                contract_id TEXT NOT NULL,
                milestone_name TEXT NOT NULL,
                milestone_description TEXT,
                planned_start_date TEXT,
                actual_start_date TEXT,
                planned_completion_date TEXT NOT NULL,
                actual_completion_date TEXT,
                percentage_complete REAL DEFAULT 0.0,
                status TEXT NOT NULL,
                dependencies TEXT,
                deliverables TEXT,
                acceptance_criteria TEXT,
                responsible_party TEXT,
                customer_approval_required BOOLEAN DEFAULT 0,
                customer_approval_date TEXT,
                budget_allocated REAL DEFAULT 0.0,
                actual_cost REAL DEFAULT 0.0,
                variance_days INTEGER DEFAULT 0,
                critical_path BOOLEAN DEFAULT 0,
                risk_level TEXT DEFAULT 'low',
                notes TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        # Resource utilization table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS resource_utilization (
                id TEXT PRIMARY KEY,
                contract_id TEXT NOT NULL,
                resource_type TEXT NOT NULL,
                resource_name TEXT NOT NULL,
                reporting_period TEXT NOT NULL,
                planned_hours REAL DEFAULT 0.0,
                actual_hours REAL DEFAULT 0.0,
                utilization_rate REAL DEFAULT 0.0,
                efficiency_rate REAL DEFAULT 0.0,
                cost_per_hour REAL DEFAULT 0.0,
                total_cost REAL DEFAULT 0.0,
                availability_percentage REAL DEFAULT 100.0,
                skill_match_score REAL DEFAULT 100.0,
                performance_rating REAL DEFAULT 100.0,
                assignments TEXT,
                created_at TEXT NOT NULL
            )
        """)
        
        # Quality metrics table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS quality_metrics (
                id TEXT PRIMARY KEY,
                contract_id TEXT NOT NULL,
                measurement_period TEXT NOT NULL,
                defect_count INTEGER DEFAULT 0,
                defect_density REAL DEFAULT 0.0,
                first_pass_yield REAL DEFAULT 100.0,
                customer_satisfaction_score REAL DEFAULT 100.0,
                rework_percentage REAL DEFAULT 0.0,
                on_time_delivery_rate REAL DEFAULT 100.0,
                compliance_score REAL DEFAULT 100.0,
                process_improvement_count INTEGER DEFAULT 0,
                quality_audits_passed INTEGER DEFAULT 0,
                quality_audits_total INTEGER DEFAULT 0,
                certification_maintenance TEXT,
                training_completion_rate REAL DEFAULT 100.0,
                created_at TEXT NOT NULL
            )
        """)
        
        # Risk assessments table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS risk_assessments (
                id TEXT PRIMARY KEY,
                contract_id TEXT NOT NULL,
                assessment_date TEXT NOT NULL,
                risk_category TEXT NOT NULL,
                risk_description TEXT NOT NULL,
                probability REAL NOT NULL,
                impact REAL NOT NULL,
                risk_score REAL NOT NULL,
                risk_level TEXT NOT NULL,
                mitigation_strategy TEXT,
                mitigation_status TEXT,
                owner TEXT,
                target_resolution_date TEXT,
                actual_resolution_date TEXT,
                contingency_plan TEXT,
                monitoring_frequency TEXT,
                last_review_date TEXT,
                next_review_date TEXT,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        # Customer feedback table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS customer_feedback (
                id TEXT PRIMARY KEY,
                contract_id TEXT NOT NULL,
                feedback_date TEXT NOT NULL,
                feedback_type TEXT NOT NULL,
                customer_contact TEXT,
                feedback_category TEXT,
                feedback_summary TEXT NOT NULL,
                satisfaction_rating REAL,
                areas_of_strength TEXT,
                areas_for_improvement TEXT,
                specific_recommendations TEXT,
                follow_up_required BOOLEAN DEFAULT 0,
                follow_up_actions TEXT,
                response_provided TEXT,
                response_date TEXT,
                created_at TEXT NOT NULL
            )
        """)
        
        conn.commit()
        conn.close()

    async def _setup_kpi_definitions(self):
        """Setup standard KPI definitions"""
        self.kpi_definitions = {
            KPICategory.COST.value: {
                "cost_performance_index": {
                    "name": "Cost Performance Index (CPI)",
                    "description": "Earned Value / Actual Cost",
                    "target_value": 1.0,
                    "unit_of_measure": "ratio",
                    "calculation": "earned_value / actual_cost",
                    "green_threshold": 0.95,
                    "yellow_threshold": 0.90
                },
                "budget_utilization": {
                    "name": "Budget Utilization Rate",
                    "description": "Percentage of budget consumed vs. time elapsed",
                    "target_value": 100.0,
                    "unit_of_measure": "percentage",
                    "calculation": "(actual_cost / budget) * 100",
                    "green_threshold": 95.0,
                    "yellow_threshold": 85.0
                }
            },
            KPICategory.SCHEDULE.value: {
                "schedule_performance_index": {
                    "name": "Schedule Performance Index (SPI)",
                    "description": "Earned Value / Planned Value",
                    "target_value": 1.0,
                    "unit_of_measure": "ratio",
                    "calculation": "earned_value / planned_value",
                    "green_threshold": 0.95,
                    "yellow_threshold": 0.90
                },
                "on_time_delivery": {
                    "name": "On-Time Delivery Rate",
                    "description": "Percentage of deliverables delivered on time",
                    "target_value": 100.0,
                    "unit_of_measure": "percentage",
                    "calculation": "(on_time_deliveries / total_deliveries) * 100",
                    "green_threshold": 95.0,
                    "yellow_threshold": 90.0
                }
            },
            KPICategory.QUALITY.value: {
                "defect_rate": {
                    "name": "Defect Rate",
                    "description": "Number of defects per unit delivered",
                    "target_value": 0.0,
                    "unit_of_measure": "defects/unit",
                    "calculation": "total_defects / total_units",
                    "green_threshold": 0.02,
                    "yellow_threshold": 0.05
                },
                "customer_satisfaction": {
                    "name": "Customer Satisfaction Score",
                    "description": "Average customer satisfaction rating",
                    "target_value": 4.5,
                    "unit_of_measure": "score (1-5)",
                    "calculation": "sum(satisfaction_scores) / count(scores)",
                    "green_threshold": 4.0,
                    "yellow_threshold": 3.5
                }
            }
        }

    async def _setup_dashboard_templates(self):
        """Setup dashboard templates"""
        self.dashboard_templates = {
            "executive": {
                "title": "Executive Dashboard",
                "sections": [
                    "contract_overview",
                    "key_performance_indicators",
                    "financial_summary",
                    "risk_status",
                    "upcoming_milestones"
                ]
            },
            "program_manager": {
                "title": "Program Manager Dashboard", 
                "sections": [
                    "schedule_performance",
                    "resource_utilization",
                    "milestone_tracking",
                    "quality_metrics",
                    "team_performance"
                ]
            },
            "customer": {
                "title": "Customer Dashboard",
                "sections": [
                    "delivery_status",
                    "quality_metrics",
                    "upcoming_deliverables",
                    "change_requests",
                    "satisfaction_feedback"
                ]
            }
        }

    async def generate_report(self, contract_id: str, reporting_period: str) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        try:
            report_id = str(uuid.uuid4())
            now = datetime.now().isoformat()
            
            # Parse reporting period
            period_start, period_end = self._parse_reporting_period(reporting_period)
            
            # Collect performance data
            performance_data = await self._collect_performance_data(
                contract_id, period_start, period_end
            )
            
            # Calculate key metrics
            key_metrics = await self._calculate_key_metrics(
                contract_id, period_start, period_end
            )
            
            # Generate executive summary
            executive_summary = await self._generate_executive_summary(
                performance_data, key_metrics
            )
            
            # Identify key accomplishments
            accomplishments = await self._identify_accomplishments(
                contract_id, period_start, period_end
            )
            
            # Identify challenges and issues
            challenges = await self._identify_challenges(
                contract_id, period_start, period_end
            )
            
            # Generate risk assessment
            risk_assessment = await self._generate_risk_assessment(contract_id)
            
            # Plan upcoming activities
            upcoming_activities = await self._plan_upcoming_activities(
                contract_id, period_end
            )
            
            # Store report
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            report_title = f"Performance Report - {reporting_period}"
            overall_status = self._determine_overall_status(key_metrics)
            
            cursor.execute("""
                INSERT INTO performance_reports (
                    id, contract_id, report_type, reporting_period_start,
                    reporting_period_end, report_title, executive_summary,
                    key_accomplishments, challenges_issues, risk_mitigation,
                    upcoming_activities, overall_status, cost_performance_index,
                    schedule_performance_index, quality_score, customer_satisfaction,
                    report_data, generated_by, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                report_id, contract_id, ReportType.MONTHLY.value,
                period_start, period_end, report_title, executive_summary,
                json.dumps(accomplishments), json.dumps(challenges),
                json.dumps(risk_assessment["mitigation_strategies"]),
                json.dumps(upcoming_activities), overall_status,
                key_metrics.get("cost_performance_index", 1.0),
                key_metrics.get("schedule_performance_index", 1.0),
                key_metrics.get("quality_score", 100.0),
                key_metrics.get("customer_satisfaction", 100.0),
                json.dumps(performance_data), "system", now, now
            ))
            
            conn.commit()
            conn.close()
            
            # Generate visualizations and charts
            charts = await self._generate_performance_charts(performance_data, key_metrics)
            
            result = {
                "report_id": report_id,
                "contract_id": contract_id,
                "reporting_period": reporting_period,
                "period_start": period_start,
                "period_end": period_end,
                "overall_status": overall_status,
                "executive_summary": executive_summary,
                "key_metrics": key_metrics,
                "performance_data": performance_data,
                "key_accomplishments": accomplishments,
                "challenges_issues": challenges,
                "risk_assessment": risk_assessment,
                "upcoming_activities": upcoming_activities,
                "performance_charts": charts,
                "recommendations": await self._generate_recommendations(
                    key_metrics, challenges, risk_assessment
                )
            }
            
            logger.info(f"Performance report generated: {report_id} for period {reporting_period}")
            return result
            
        except Exception as e:
            logger.error(f"Error generating performance report: {e}")
            return {"error": str(e)}

    def _parse_reporting_period(self, period: str) -> tuple:
        """Parse reporting period string into start and end dates"""
        # Handle different period formats
        if period.startswith("2024"):
            # Monthly format: "2024-03"
            if len(period) == 7:
                year, month = period.split("-")
                start_date = f"{year}-{month}-01"
                
                # Calculate end date
                next_month = int(month) + 1
                next_year = int(year)
                if next_month > 12:
                    next_month = 1
                    next_year += 1
                
                end_date = f"{next_year}-{next_month:02d}-01"
                return start_date, end_date
        
        # Default to current month
        now = datetime.now()
        start_date = now.replace(day=1).isoformat()
        if now.month == 12:
            end_date = now.replace(year=now.year+1, month=1, day=1).isoformat()
        else:
            end_date = now.replace(month=now.month+1, day=1).isoformat()
        
        return start_date, end_date

    async def _collect_performance_data(self, contract_id: str, 
                                       period_start: str, period_end: str) -> Dict[str, Any]:
        """Collect comprehensive performance data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        performance_data = {}
        
        # Get KPI metrics
        cursor.execute("""
            SELECT kpi_category, kpi_name, target_value, actual_value,
                   variance_percentage, performance_status, unit_of_measure
            FROM kpi_metrics 
            WHERE contract_id = ? AND collection_date BETWEEN ? AND ?
        """, (contract_id, period_start, period_end))
        
        kpi_data = []
        for row in cursor.fetchall():
            kpi_data.append({
                "category": row[0],
                "name": row[1],
                "target": row[2],
                "actual": row[3],
                "variance_percentage": row[4],
                "status": row[5],
                "unit": row[6]
            })
        
        performance_data["kpis"] = kpi_data
        
        # Get milestone data
        cursor.execute("""
            SELECT milestone_name, planned_completion_date, actual_completion_date,
                   percentage_complete, status, variance_days
            FROM milestone_tracking 
            WHERE contract_id = ?
        """, (contract_id,))
        
        milestone_data = []
        for row in cursor.fetchall():
            milestone_data.append({
                "name": row[0],
                "planned_completion": row[1],
                "actual_completion": row[2],
                "percentage_complete": row[3],
                "status": row[4],
                "variance_days": row[5]
            })
        
        performance_data["milestones"] = milestone_data
        
        # Get resource utilization
        cursor.execute("""
            SELECT resource_type, AVG(utilization_rate), AVG(efficiency_rate),
                   SUM(actual_hours), SUM(total_cost)
            FROM resource_utilization 
            WHERE contract_id = ? AND reporting_period BETWEEN ? AND ?
            GROUP BY resource_type
        """, (contract_id, period_start, period_end))
        
        resource_data = []
        for row in cursor.fetchall():
            resource_data.append({
                "type": row[0],
                "avg_utilization": row[1],
                "avg_efficiency": row[2],
                "total_hours": row[3],
                "total_cost": row[4]
            })
        
        performance_data["resources"] = resource_data
        
        # Get quality metrics
        cursor.execute("""
            SELECT defect_count, first_pass_yield, customer_satisfaction_score,
                   on_time_delivery_rate, compliance_score
            FROM quality_metrics 
            WHERE contract_id = ? AND measurement_period BETWEEN ? AND ?
            ORDER BY measurement_period DESC LIMIT 1
        """, (contract_id, period_start, period_end))
        
        quality_row = cursor.fetchone()
        if quality_row:
            performance_data["quality"] = {
                "defect_count": quality_row[0],
                "first_pass_yield": quality_row[1],
                "customer_satisfaction": quality_row[2],
                "on_time_delivery": quality_row[3],
                "compliance_score": quality_row[4]
            }
        
        conn.close()
        return performance_data

    async def _calculate_key_metrics(self, contract_id: str, 
                                   period_start: str, period_end: str) -> Dict[str, Any]:
        """Calculate key performance metrics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get latest KPI values
        cursor.execute("""
            SELECT kpi_name, actual_value, performance_status
            FROM kpi_metrics 
            WHERE contract_id = ? AND collection_date BETWEEN ? AND ?
            ORDER BY collection_date DESC
        """, (contract_id, period_start, period_end))
        
        metrics = {}
        for row in cursor.fetchall():
            kpi_name = row[0].replace(" ", "_").replace("(", "").replace(")", "").lower()
            metrics[kpi_name] = {
                "value": row[1],
                "status": row[2]
            }
        
        # Calculate milestone performance
        cursor.execute("""
            SELECT AVG(percentage_complete), 
                   COUNT(CASE WHEN status = 'completed' THEN 1 END) * 100.0 / COUNT(*),
                   AVG(variance_days)
            FROM milestone_tracking 
            WHERE contract_id = ?
        """, (contract_id,))
        
        milestone_row = cursor.fetchone()
        if milestone_row:
            metrics["milestone_completion_rate"] = {
                "value": milestone_row[0] or 0,
                "status": self._determine_status(milestone_row[0] or 0, 90, 80)
            }
            metrics["milestone_success_rate"] = {
                "value": milestone_row[1] or 0,
                "status": self._determine_status(milestone_row[1] or 0, 95, 85)
            }
            metrics["schedule_variance_days"] = {
                "value": milestone_row[2] or 0,
                "status": "on_target" if (milestone_row[2] or 0) <= 5 else "behind"
            }
        
        # Calculate overall performance score
        status_scores = {
            "on_target": 100,
            "ahead": 110,
            "behind": 80,
            "at_risk": 60,
            "critical": 40
        }
        
        total_score = 0
        metric_count = 0
        
        for metric_data in metrics.values():
            if isinstance(metric_data, dict) and "status" in metric_data:
                total_score += status_scores.get(metric_data["status"], 70)
                metric_count += 1
        
        overall_score = total_score / metric_count if metric_count > 0 else 85
        metrics["overall_performance_score"] = {
            "value": overall_score,
            "status": self._determine_status(overall_score, 90, 70)
        }
        
        conn.close()
        return metrics

    def _determine_status(self, value: float, green_threshold: float, yellow_threshold: float) -> str:
        """Determine performance status based on thresholds"""
        if value >= green_threshold:
            return PerformanceStatus.ON_TARGET.value
        elif value >= yellow_threshold:
            return PerformanceStatus.AT_RISK.value
        else:
            return PerformanceStatus.BEHIND.value

    async def _generate_executive_summary(self, performance_data: Dict[str, Any],
                                        key_metrics: Dict[str, Any]) -> str:
        """Generate executive summary"""
        # Count metrics by status
        status_counts = {}
        for metric in key_metrics.values():
            if isinstance(metric, dict) and "status" in metric:
                status = metric["status"]
                status_counts[status] = status_counts.get(status, 0) + 1
        
        # Generate summary based on performance
        if status_counts.get("critical", 0) > 0:
            summary = "CRITICAL ATTENTION REQUIRED: "
        elif status_counts.get("at_risk", 0) > 2:
            summary = "ATTENTION REQUIRED: "
        elif status_counts.get("on_target", 0) > status_counts.get("behind", 0):
            summary = "PERFORMING WELL: "
        else:
            summary = "MIXED PERFORMANCE: "
        
        summary += f"Contract performance shows {status_counts.get('on_target', 0)} metrics on target, "
        summary += f"{status_counts.get('at_risk', 0)} at risk, and "
        summary += f"{status_counts.get('behind', 0)} behind target. "
        
        # Add specific insights
        if "milestones" in performance_data:
            completed_milestones = len([m for m in performance_data["milestones"] if m["status"] == "completed"])
            total_milestones = len(performance_data["milestones"])
            summary += f"Milestone completion: {completed_milestones}/{total_milestones}. "
        
        if "quality" in performance_data and performance_data["quality"]["customer_satisfaction"]:
            satisfaction = performance_data["quality"]["customer_satisfaction"]
            summary += f"Customer satisfaction: {satisfaction:.1f}/5.0. "
        
        return summary

    async def _identify_accomplishments(self, contract_id: str,
                                      period_start: str, period_end: str) -> List[str]:
        """Identify key accomplishments for the period"""
        accomplishments = []
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check for completed milestones
        cursor.execute("""
            SELECT milestone_name FROM milestone_tracking 
            WHERE contract_id = ? AND status = 'completed'
            AND actual_completion_date BETWEEN ? AND ?
        """, (contract_id, period_start, period_end))
        
        for row in cursor.fetchall():
            accomplishments.append(f"Successfully completed milestone: {row[0]}")
        
        # Check for performance improvements
        cursor.execute("""
            SELECT kpi_name, actual_value FROM kpi_metrics 
            WHERE contract_id = ? AND performance_status = 'ahead'
            AND collection_date BETWEEN ? AND ?
        """, (contract_id, period_start, period_end))
        
        for row in cursor.fetchall():
            accomplishments.append(f"Exceeded target for {row[0]}: {row[1]}")
        
        # Check for early deliveries
        cursor.execute("""
            SELECT COUNT(*) FROM milestone_tracking 
            WHERE contract_id = ? AND variance_days < 0
        """, (contract_id,))
        
        early_count = cursor.fetchone()[0]
        if early_count > 0:
            accomplishments.append(f"Delivered {early_count} milestone(s) ahead of schedule")
        
        conn.close()
        
        if not accomplishments:
            accomplishments = [
                "Maintained contract performance standards",
                "Continued progress on scheduled activities",
                "Sustained quality delivery processes"
            ]
        
        return accomplishments

    async def _identify_challenges(self, contract_id: str,
                                 period_start: str, period_end: str) -> List[str]:
        """Identify challenges and issues"""
        challenges = []
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check for behind schedule milestones
        cursor.execute("""
            SELECT milestone_name, variance_days FROM milestone_tracking 
            WHERE contract_id = ? AND (status = 'behind' OR variance_days > 0)
            ORDER BY variance_days DESC LIMIT 3
        """, (contract_id,))
        
        for row in cursor.fetchall():
            challenges.append(f"Milestone '{row[0]}' running {row[1]} days behind schedule")
        
        # Check for underperforming KPIs
        cursor.execute("""
            SELECT kpi_name, variance_percentage FROM kpi_metrics 
            WHERE contract_id = ? AND performance_status IN ('behind', 'at_risk')
            AND collection_date BETWEEN ? AND ?
            ORDER BY variance_percentage ASC LIMIT 3
        """, (contract_id, period_start, period_end))
        
        for row in cursor.fetchall():
            challenges.append(f"{row[0]} underperforming by {abs(row[1]):.1f}%")
        
        # Check for resource constraints
        cursor.execute("""
            SELECT resource_type, utilization_rate FROM resource_utilization 
            WHERE contract_id = ? AND utilization_rate > 95
            AND reporting_period BETWEEN ? AND ?
        """, (contract_id, period_start, period_end))
        
        for row in cursor.fetchall():
            challenges.append(f"{row[0]} resources over-utilized at {row[1]:.1f}%")
        
        conn.close()
        return challenges

    async def _generate_risk_assessment(self, contract_id: str) -> Dict[str, Any]:
        """Generate current risk assessment"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get active risks
        cursor.execute("""
            SELECT risk_category, risk_description, risk_level, risk_score,
                   mitigation_strategy, mitigation_status
            FROM risk_assessments 
            WHERE contract_id = ? AND status = 'active'
            ORDER BY risk_score DESC
        """, (contract_id,))
        
        risks = []
        total_risk_score = 0
        risk_levels = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        
        for row in cursor.fetchall():
            risk = {
                "category": row[0],
                "description": row[1],
                "level": row[2],
                "score": row[3],
                "mitigation_strategy": row[4],
                "mitigation_status": row[5]
            }
            risks.append(risk)
            total_risk_score += row[3]
            risk_levels[row[2]] = risk_levels.get(row[2], 0) + 1
        
        # Calculate overall risk profile
        if risk_levels["critical"] > 0:
            overall_risk = "critical"
        elif risk_levels["high"] > 2:
            overall_risk = "high"
        elif risk_levels["medium"] > 3:
            overall_risk = "medium"
        else:
            overall_risk = "low"
        
        mitigation_strategies = [
            "Regular risk monitoring and assessment",
            "Proactive stakeholder communication",
            "Contingency plan activation when needed",
            "Resource reallocation as required"
        ]
        
        conn.close()
        
        return {
            "overall_risk_level": overall_risk,
            "total_risk_score": total_risk_score,
            "risk_distribution": risk_levels,
            "top_risks": risks[:5],
            "mitigation_strategies": mitigation_strategies,
            "risk_trend": "stable"  # Would calculate from historical data
        }

    async def _plan_upcoming_activities(self, contract_id: str, period_end: str) -> List[str]:
        """Plan upcoming activities for next period"""
        activities = []
        next_period_end = (datetime.fromisoformat(period_end) + timedelta(days=30)).isoformat()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get upcoming milestones
        cursor.execute("""
            SELECT milestone_name, planned_completion_date FROM milestone_tracking 
            WHERE contract_id = ? AND status != 'completed'
            AND planned_completion_date BETWEEN ? AND ?
            ORDER BY planned_completion_date ASC LIMIT 5
        """, (contract_id, period_end, next_period_end))
        
        for row in cursor.fetchall():
            activities.append(f"Complete milestone: {row[0]} (due {row[1]})")
        
        # Standard activities
        activities.extend([
            "Continue performance monitoring and reporting",
            "Conduct regular team reviews and planning sessions",
            "Maintain customer communication and feedback loops",
            "Execute risk mitigation strategies",
            "Prepare for upcoming contract reviews"
        ])
        
        conn.close()
        return activities

    def _determine_overall_status(self, key_metrics: Dict[str, Any]) -> str:
        """Determine overall contract performance status"""
        status_weights = {
            "critical": 0,
            "behind": 25,
            "at_risk": 50,
            "on_target": 75,
            "ahead": 100
        }
        
        total_score = 0
        metric_count = 0
        
        for metric in key_metrics.values():
            if isinstance(metric, dict) and "status" in metric:
                total_score += status_weights.get(metric["status"], 50)
                metric_count += 1
        
        if metric_count == 0:
            return PerformanceStatus.ON_TARGET.value
        
        average_score = total_score / metric_count
        
        if average_score >= 90:
            return PerformanceStatus.AHEAD.value
        elif average_score >= 70:
            return PerformanceStatus.ON_TARGET.value
        elif average_score >= 50:
            return PerformanceStatus.AT_RISK.value
        elif average_score >= 25:
            return PerformanceStatus.BEHIND.value
        else:
            return PerformanceStatus.CRITICAL.value

    async def _generate_performance_charts(self, performance_data: Dict[str, Any],
                                         key_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Generate performance visualization data"""
        return {
            "kpi_dashboard": {
                "type": "gauge_chart",
                "data": [
                    {
                        "name": "Cost Performance",
                        "value": key_metrics.get("cost_performance_index", {}).get("value", 1.0),
                        "target": 1.0,
                        "status": key_metrics.get("cost_performance_index", {}).get("status", "on_target")
                    },
                    {
                        "name": "Schedule Performance", 
                        "value": key_metrics.get("schedule_performance_index", {}).get("value", 1.0),
                        "target": 1.0,
                        "status": key_metrics.get("schedule_performance_index", {}).get("status", "on_target")
                    }
                ]
            },
            "milestone_timeline": {
                "type": "timeline_chart",
                "data": performance_data.get("milestones", [])
            },
            "resource_utilization": {
                "type": "bar_chart", 
                "data": performance_data.get("resources", [])
            },
            "quality_trends": {
                "type": "line_chart",
                "data": performance_data.get("quality", {})
            }
        }

    async def _generate_recommendations(self, key_metrics: Dict[str, Any],
                                      challenges: List[str],
                                      risk_assessment: Dict[str, Any]) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []
        
        # Performance-based recommendations
        behind_metrics = [name for name, data in key_metrics.items() 
                         if isinstance(data, dict) and data.get("status") == "behind"]
        
        if behind_metrics:
            recommendations.append(f"Focus improvement efforts on: {', '.join(behind_metrics)}")
        
        # Risk-based recommendations
        if risk_assessment["overall_risk_level"] in ["critical", "high"]:
            recommendations.append("Implement enhanced risk mitigation measures immediately")
        
        # Challenge-based recommendations
        if len(challenges) > 3:
            recommendations.append("Conduct detailed analysis of performance bottlenecks")
        
        # Standard recommendations
        recommendations.extend([
            "Maintain regular stakeholder communication",
            "Continue proactive performance monitoring",
            "Review and update project plans as needed",
            "Ensure adequate resource allocation for critical activities"
        ])
        
        return recommendations[:8]  # Return top 8 recommendations

    async def get_metrics(self, contract_id: str) -> Dict[str, Any]:
        """Get current performance metrics for contract"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get latest KPI metrics
            cursor.execute("""
                SELECT kpi_category, kpi_name, target_value, actual_value,
                       variance_percentage, performance_status, collection_date
                FROM kpi_metrics 
                WHERE contract_id = ?
                ORDER BY collection_date DESC
            """, (contract_id,))
            
            current_metrics = {}
            for row in cursor.fetchall():
                category = row[0]
                if category not in current_metrics:
                    current_metrics[category] = []
                
                current_metrics[category].append({
                    "name": row[1],
                    "target": row[2],
                    "actual": row[3],
                    "variance_percentage": row[4],
                    "status": row[5],
                    "last_updated": row[6]
                })
            
            # Get milestone summary
            cursor.execute("""
                SELECT COUNT(*) as total,
                       SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                       AVG(percentage_complete) as avg_completion
                FROM milestone_tracking 
                WHERE contract_id = ?
            """, (contract_id,))
            
            milestone_summary = cursor.fetchone()
            
            # Get recent performance trends
            cursor.execute("""
                SELECT collection_date, kpi_name, actual_value
                FROM kpi_metrics 
                WHERE contract_id = ? 
                ORDER BY collection_date DESC 
                LIMIT 20
            """, (contract_id,))
            
            trend_data = []
            for row in cursor.fetchall():
                trend_data.append({
                    "date": row[0],
                    "kpi": row[1],
                    "value": row[2]
                })
            
            conn.close()
            
            return {
                "contract_id": contract_id,
                "current_metrics": current_metrics,
                "milestone_summary": {
                    "total_milestones": milestone_summary[0],
                    "completed_milestones": milestone_summary[1],
                    "completion_rate": milestone_summary[2] or 0
                },
                "performance_trends": trend_data,
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting performance metrics: {e}")
            return {"error": str(e)}

    async def update_milestones(self, contract_id: str, 
                              milestone_updates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Update contract milestone progress"""
        try:
            updated_count = 0
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for update in milestone_updates:
                milestone_name = update.get("milestone_name")
                percentage_complete = update.get("percentage_complete")
                status = update.get("status")
                actual_completion = update.get("actual_completion_date")
                
                # Calculate variance if completion date provided
                variance_days = 0
                if actual_completion:
                    cursor.execute("""
                        SELECT planned_completion_date FROM milestone_tracking 
                        WHERE contract_id = ? AND milestone_name = ?
                    """, (contract_id, milestone_name))
                    
                    planned = cursor.fetchone()
                    if planned and planned[0]:
                        planned_date = datetime.fromisoformat(planned[0])
                        actual_date = datetime.fromisoformat(actual_completion)
                        variance_days = (actual_date - planned_date).days
                
                # Update milestone
                cursor.execute("""
                    UPDATE milestone_tracking 
                    SET percentage_complete = ?, status = ?, 
                        actual_completion_date = ?, variance_days = ?,
                        updated_at = ?
                    WHERE contract_id = ? AND milestone_name = ?
                """, (
                    percentage_complete, status, actual_completion, variance_days,
                    datetime.now().isoformat(), contract_id, milestone_name
                ))
                
                updated_count += cursor.rowcount
            
            conn.commit()
            conn.close()
            
            return {
                "contract_id": contract_id,
                "milestones_updated": updated_count,
                "update_status": "success",
                "updated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error updating milestones: {e}")
            return {"error": str(e)}

# Global instance
performance_system = PerformanceReportingSystem()