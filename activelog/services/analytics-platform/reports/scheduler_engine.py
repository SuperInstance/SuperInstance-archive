"""
Scheduled Reports Engine
Automated report generation and delivery system
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Union, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import logging
import asyncio
import json
import uuid
from concurrent.futures import ThreadPoolExecutor
import schedule
import threading
import time

# Email and notification imports
try:
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from email.mime.base import MIMEBase
    from email import encoders
    EMAIL_AVAILABLE = True
except ImportError:
    EMAIL_AVAILABLE = False

logger = logging.getLogger(__name__)

class ReportFrequency(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    CUSTOM = "custom"

class ReportStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"

class DeliveryMethod(str, Enum):
    EMAIL = "email"
    WEBHOOK = "webhook"
    FILE_SYSTEM = "file_system"
    FTP = "ftp"
    SLACK = "slack"
    TEAMS = "teams"

@dataclass
class ReportTemplate:
    template_id: str
    name: str
    description: str
    analytics_job_type: str  # forecast, anomaly_detection, cohort_analysis, etc.
    data_query: Dict[str, Any]
    visualization_config: Dict[str, Any] = field(default_factory=dict)
    export_formats: List[str] = field(default_factory=lambda: ["pdf", "excel"])
    custom_content: Dict[str, Any] = field(default_factory=dict)

@dataclass
class DeliveryConfig:
    method: DeliveryMethod
    recipients: List[str] = field(default_factory=list)
    email_settings: Dict[str, Any] = field(default_factory=dict)
    webhook_url: Optional[str] = None
    file_path: Optional[str] = None
    custom_settings: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ScheduleConfig:
    frequency: ReportFrequency
    time_of_day: str = "09:00"  # HH:MM format
    day_of_week: Optional[int] = None  # 0=Monday, 6=Sunday
    day_of_month: Optional[int] = None  # 1-31
    timezone: str = "UTC"
    custom_cron: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

@dataclass
class ScheduledReport:
    report_id: str
    name: str
    template: ReportTemplate
    schedule: ScheduleConfig
    delivery: DeliveryConfig
    status: ReportStatus = ReportStatus.ACTIVE
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    run_count: int = 0
    failure_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ReportExecution:
    execution_id: str
    report_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: str = "running"
    results: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    delivery_status: Dict[str, Any] = field(default_factory=dict)

class ScheduledReportsEngine:
    """Engine for managing scheduled reports"""
    
    def __init__(self, analytics_service=None):
        self.analytics_service = analytics_service
        self.reports = {}
        self.templates = {}
        self.executions = {}
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.scheduler_thread = None
        self.scheduler_active = False
        
        # Initialize default templates
        self._create_default_templates()
        
        logger.info("Scheduled Reports Engine initialized")
    
    async def create_report_template(self, template_data: Dict[str, Any]) -> str:
        """Create a new report template"""
        template_id = str(uuid.uuid4())
        
        template = ReportTemplate(
            template_id=template_id,
            name=template_data['name'],
            description=template_data.get('description', ''),
            analytics_job_type=template_data['analytics_job_type'],
            data_query=template_data['data_query'],
            visualization_config=template_data.get('visualization_config', {}),
            export_formats=template_data.get('export_formats', ['pdf', 'excel']),
            custom_content=template_data.get('custom_content', {})
        )
        
        self.templates[template_id] = template
        logger.info(f"Report template created: {template_id}")
        
        return template_id
    
    async def create_scheduled_report(self, report_data: Dict[str, Any]) -> str:
        """Create a new scheduled report"""
        report_id = str(uuid.uuid4())
        
        # Get template
        template_id = report_data['template_id']
        if template_id not in self.templates:
            raise ValueError(f"Template {template_id} not found")
        
        template = self.templates[template_id]
        
        # Create schedule configuration
        schedule_config = ScheduleConfig(
            frequency=ReportFrequency(report_data['schedule']['frequency']),
            time_of_day=report_data['schedule'].get('time_of_day', '09:00'),
            day_of_week=report_data['schedule'].get('day_of_week'),
            day_of_month=report_data['schedule'].get('day_of_month'),
            timezone=report_data['schedule'].get('timezone', 'UTC'),
            custom_cron=report_data['schedule'].get('custom_cron'),
            start_date=datetime.fromisoformat(report_data['schedule']['start_date']) if 'start_date' in report_data['schedule'] else None,
            end_date=datetime.fromisoformat(report_data['schedule']['end_date']) if 'end_date' in report_data['schedule'] else None
        )
        
        # Create delivery configuration
        delivery_config = DeliveryConfig(
            method=DeliveryMethod(report_data['delivery']['method']),
            recipients=report_data['delivery'].get('recipients', []),
            email_settings=report_data['delivery'].get('email_settings', {}),
            webhook_url=report_data['delivery'].get('webhook_url'),
            file_path=report_data['delivery'].get('file_path'),
            custom_settings=report_data['delivery'].get('custom_settings', {})
        )
        
        # Create scheduled report
        scheduled_report = ScheduledReport(
            report_id=report_id,
            name=report_data['name'],
            template=template,
            schedule=schedule_config,
            delivery=delivery_config,
            status=ReportStatus.ACTIVE,
            metadata=report_data.get('metadata', {})
        )
        
        # Calculate next run time
        scheduled_report.next_run = self._calculate_next_run(schedule_config)
        
        self.reports[report_id] = scheduled_report
        
        # Start scheduler if not already running
        if not self.scheduler_active:
            await self._start_scheduler()
        
        logger.info(f"Scheduled report created: {report_id}")
        return report_id
    
    async def execute_report(self, report_id: str, force: bool = False) -> str:
        """Execute a scheduled report"""
        if report_id not in self.reports:
            raise ValueError(f"Report {report_id} not found")
        
        report = self.reports[report_id]
        
        # Check if report is active (unless forced)
        if not force and report.status != ReportStatus.ACTIVE:
            raise ValueError(f"Report {report_id} is not active")
        
        execution_id = str(uuid.uuid4())
        execution = ReportExecution(
            execution_id=execution_id,
            report_id=report_id,
            started_at=datetime.utcnow()
        )
        
        self.executions[execution_id] = execution
        
        try:
            # Execute analytics job
            analytics_results = await self._execute_analytics_job(report)
            
            # Generate report content
            report_content = await self._generate_report_content(report, analytics_results)
            
            # Export report in requested formats
            exported_files = await self._export_report(report, report_content)
            
            # Deliver report
            delivery_results = await self._deliver_report(report, exported_files)
            
            # Update execution
            execution.completed_at = datetime.utcnow()
            execution.status = "completed"
            execution.results = {
                'analytics_results': analytics_results,
                'exported_files': exported_files,
                'delivery_results': delivery_results
            }
            execution.delivery_status = delivery_results
            
            # Update report
            report.last_run = execution.completed_at
            report.next_run = self._calculate_next_run(report.schedule)
            report.run_count += 1
            
            logger.info(f"Report executed successfully: {report_id} (execution: {execution_id})")
            
        except Exception as e:
            execution.completed_at = datetime.utcnow()
            execution.status = "failed"
            execution.error_message = str(e)
            
            report.failure_count += 1
            
            logger.error(f"Report execution failed: {report_id} - {e}")
        
        return execution_id
    
    async def get_report_info(self, report_id: str) -> Dict[str, Any]:
        """Get information about a scheduled report"""
        if report_id not in self.reports:
            raise ValueError(f"Report {report_id} not found")
        
        report = self.reports[report_id]
        
        return {
            'report_id': report.report_id,
            'name': report.name,
            'status': report.status.value,
            'created_at': report.created_at.isoformat(),
            'last_run': report.last_run.isoformat() if report.last_run else None,
            'next_run': report.next_run.isoformat() if report.next_run else None,
            'run_count': report.run_count,
            'failure_count': report.failure_count,
            'template': {
                'template_id': report.template.template_id,
                'name': report.template.name,
                'analytics_job_type': report.template.analytics_job_type
            },
            'schedule': {
                'frequency': report.schedule.frequency.value,
                'time_of_day': report.schedule.time_of_day,
                'timezone': report.schedule.timezone
            },
            'delivery': {
                'method': report.delivery.method.value,
                'recipients': len(report.delivery.recipients)
            }
        }
    
    async def list_reports(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """List scheduled reports"""
        reports_list = []
        
        for report_id, report in self.reports.items():
            if status is None or report.status.value == status:
                reports_list.append({
                    'report_id': report_id,
                    'name': report.name,
                    'status': report.status.value,
                    'frequency': report.schedule.frequency.value,
                    'last_run': report.last_run.isoformat() if report.last_run else None,
                    'next_run': report.next_run.isoformat() if report.next_run else None,
                    'run_count': report.run_count
                })
        
        return reports_list
    
    async def list_templates(self) -> List[Dict[str, Any]]:
        """List available report templates"""
        templates_list = []
        
        for template_id, template in self.templates.items():
            templates_list.append({
                'template_id': template_id,
                'name': template.name,
                'description': template.description,
                'analytics_job_type': template.analytics_job_type,
                'export_formats': template.export_formats
            })
        
        return templates_list
    
    async def get_execution_info(self, execution_id: str) -> Dict[str, Any]:
        """Get information about a report execution"""
        if execution_id not in self.executions:
            raise ValueError(f"Execution {execution_id} not found")
        
        execution = self.executions[execution_id]
        
        return {
            'execution_id': execution_id,
            'report_id': execution.report_id,
            'started_at': execution.started_at.isoformat(),
            'completed_at': execution.completed_at.isoformat() if execution.completed_at else None,
            'status': execution.status,
            'error_message': execution.error_message,
            'delivery_status': execution.delivery_status
        }
    
    async def pause_report(self, report_id: str) -> bool:
        """Pause a scheduled report"""
        if report_id not in self.reports:
            return False
        
        self.reports[report_id].status = ReportStatus.PAUSED
        logger.info(f"Report paused: {report_id}")
        return True
    
    async def resume_report(self, report_id: str) -> bool:
        """Resume a paused report"""
        if report_id not in self.reports:
            return False
        
        report = self.reports[report_id]
        report.status = ReportStatus.ACTIVE
        report.next_run = self._calculate_next_run(report.schedule)
        
        logger.info(f"Report resumed: {report_id}")
        return True
    
    async def delete_report(self, report_id: str) -> bool:
        """Delete a scheduled report"""
        if report_id not in self.reports:
            return False
        
        del self.reports[report_id]
        logger.info(f"Report deleted: {report_id}")
        return True
    
    # Internal methods
    async def _start_scheduler(self):
        """Start the background scheduler"""
        if self.scheduler_active:
            return
        
        self.scheduler_active = True
        self.scheduler_thread = threading.Thread(target=self._scheduler_worker, daemon=True)
        self.scheduler_thread.start()
        
        logger.info("Scheduler started")
    
    def _scheduler_worker(self):
        """Background scheduler worker"""
        while self.scheduler_active:
            try:
                now = datetime.utcnow()
                
                # Check for reports that need to run
                for report_id, report in self.reports.items():
                    if (report.status == ReportStatus.ACTIVE and 
                        report.next_run and 
                        report.next_run <= now):
                        
                        # Schedule execution
                        asyncio.create_task(self.execute_report(report_id))
                
                # Sleep for 1 minute
                time.sleep(60)
                
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                time.sleep(60)
    
    def _calculate_next_run(self, schedule: ScheduleConfig) -> Optional[datetime]:
        """Calculate next run time for a schedule"""
        now = datetime.utcnow()
        
        if schedule.end_date and now >= schedule.end_date:
            return None
        
        if schedule.start_date and now < schedule.start_date:
            base_time = schedule.start_date
        else:
            base_time = now
        
        # Parse time of day
        hour, minute = map(int, schedule.time_of_day.split(':'))
        
        if schedule.frequency == ReportFrequency.DAILY:
            next_run = base_time.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if next_run <= now:
                next_run += timedelta(days=1)
                
        elif schedule.frequency == ReportFrequency.WEEKLY:
            days_ahead = (schedule.day_of_week or 0) - base_time.weekday()
            if days_ahead <= 0:  # Target day has passed this week
                days_ahead += 7
            next_run = base_time + timedelta(days=days_ahead)
            next_run = next_run.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
        elif schedule.frequency == ReportFrequency.MONTHLY:
            target_day = schedule.day_of_month or 1
            if base_time.day >= target_day:
                # Next month
                if base_time.month == 12:
                    next_run = base_time.replace(year=base_time.year + 1, month=1, day=target_day,
                                               hour=hour, minute=minute, second=0, microsecond=0)
                else:
                    next_run = base_time.replace(month=base_time.month + 1, day=target_day,
                                               hour=hour, minute=minute, second=0, microsecond=0)
            else:
                # This month
                next_run = base_time.replace(day=target_day, hour=hour, minute=minute, 
                                           second=0, microsecond=0)
        else:
            # Default to daily
            next_run = base_time.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if next_run <= now:
                next_run += timedelta(days=1)
        
        return next_run
    
    async def _execute_analytics_job(self, report: ScheduledReport) -> Dict[str, Any]:
        """Execute the analytics job for a report"""
        if not self.analytics_service:
            raise ValueError("Analytics service not configured")
        
        job_type = report.template.analytics_job_type
        query = report.template.data_query
        
        # This would integrate with the main analytics service
        # For now, return placeholder data
        return {
            'job_type': job_type,
            'results': query,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    async def _generate_report_content(self, report: ScheduledReport, analytics_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate report content from analytics results"""
        content = {
            'title': report.name,
            'generated_at': datetime.utcnow().isoformat(),
            'analytics_results': analytics_results,
            'custom_content': report.template.custom_content
        }
        
        return content
    
    async def _export_report(self, report: ScheduledReport, content: Dict[str, Any]) -> Dict[str, bytes]:
        """Export report content in requested formats"""
        exported_files = {}
        
        for format_type in report.template.export_formats:
            if format_type == 'pdf':
                # Generate PDF content (placeholder)
                exported_files['pdf'] = b'PDF content placeholder'
            elif format_type == 'excel':
                # Generate Excel content (placeholder)
                exported_files['excel'] = b'Excel content placeholder'
            elif format_type == 'json':
                # Generate JSON content
                exported_files['json'] = json.dumps(content).encode('utf-8')
        
        return exported_files
    
    async def _deliver_report(self, report: ScheduledReport, exported_files: Dict[str, bytes]) -> Dict[str, Any]:
        """Deliver report via configured delivery method"""
        delivery_results = {}
        
        if report.delivery.method == DeliveryMethod.EMAIL:
            delivery_results['email'] = await self._send_email_report(report, exported_files)
        elif report.delivery.method == DeliveryMethod.FILE_SYSTEM:
            delivery_results['file_system'] = await self._save_to_file_system(report, exported_files)
        elif report.delivery.method == DeliveryMethod.WEBHOOK:
            delivery_results['webhook'] = await self._send_webhook_report(report, exported_files)
        
        return delivery_results
    
    async def _send_email_report(self, report: ScheduledReport, exported_files: Dict[str, bytes]) -> Dict[str, Any]:
        """Send report via email"""
        if not EMAIL_AVAILABLE:
            return {'status': 'failed', 'error': 'Email functionality not available'}
        
        # Placeholder email sending logic
        return {'status': 'sent', 'recipients': len(report.delivery.recipients)}
    
    async def _save_to_file_system(self, report: ScheduledReport, exported_files: Dict[str, bytes]) -> Dict[str, Any]:
        """Save report to file system"""
        saved_files = []
        
        for format_type, content in exported_files.items():
            if report.delivery.file_path:
                filename = f"{report.name}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.{format_type}"
                filepath = f"{report.delivery.file_path}/{filename}"
                
                try:
                    with open(filepath, 'wb') as f:
                        f.write(content)
                    saved_files.append(filepath)
                except Exception as e:
                    logger.error(f"Failed to save file {filepath}: {e}")
        
        return {'status': 'saved', 'files': saved_files}
    
    async def _send_webhook_report(self, report: ScheduledReport, exported_files: Dict[str, bytes]) -> Dict[str, Any]:
        """Send report via webhook"""
        # Placeholder webhook sending logic
        return {'status': 'sent', 'webhook_url': report.delivery.webhook_url}
    
    def _create_default_templates(self):
        """Create default report templates"""
        
        # Daily Analytics Summary Template
        template_id = "daily_summary"
        self.templates[template_id] = ReportTemplate(
            template_id=template_id,
            name="Daily Analytics Summary",
            description="Daily overview of key analytics metrics",
            analytics_job_type="dashboard_overview",
            data_query={"timeframe": "daily", "include_forecasts": True},
            export_formats=["pdf", "excel"],
            custom_content={"include_charts": True, "include_summary": True}
        )
        
        # Weekly Cohort Analysis Template
        template_id = "weekly_cohort"
        self.templates[template_id] = ReportTemplate(
            template_id=template_id,
            name="Weekly Cohort Analysis",
            description="Weekly cohort retention analysis",
            analytics_job_type="cohort_analysis",
            data_query={"cohort_type": "weekly", "period_range": 12},
            export_formats=["pdf", "excel"],
            custom_content={"include_heatmap": True}
        )
        
        # Monthly Anomaly Report Template
        template_id = "monthly_anomalies"
        self.templates[template_id] = ReportTemplate(
            template_id=template_id,
            name="Monthly Anomaly Detection Report",
            description="Monthly summary of detected anomalies",
            analytics_job_type="anomaly_detection",
            data_query={"timeframe": "monthly", "detection_methods": ["ensemble"]},
            export_formats=["pdf", "json"],
            custom_content={"include_charts": True, "threshold_analysis": True}
        )
        
        logger.info("Default report templates created")