"""
Report Service - Generates import reports and statistics
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

from core.config import settings

logger = logging.getLogger(__name__)

@dataclass
class ImportSummary:
    """Summary of import operations"""
    period_start: datetime
    period_end: datetime
    total_files_processed: int
    total_files_succeeded: int
    total_files_failed: int
    total_duplicates_found: int
    total_size_processed: int
    total_batches: int
    average_processing_time: float
    success_rate: float
    file_types_breakdown: Dict[str, int]
    error_breakdown: Dict[str, int]

class ReportService:
    """Generates import reports and maintains statistics"""
    
    def __init__(self):
        self.reports_path = Path(settings.REPORTS_PATH)
        self.reports_path.mkdir(parents=True, exist_ok=True)
        
        # Statistics tracking
        self.stats = {
            "reports_generated": 0,
            "service_start_time": datetime.now(),
            "last_report": None,
            "total_files_reported": 0
        }
        
        # Daily batch tracking
        self.daily_batches = {}
        self.batch_history = []
        
        logger.info("Report service initialized")
    
    async def create_batch_report(self, batch_result) -> str:
        """Create a detailed report for a batch"""
        try:
            report_filename = f"batch_report_{batch_result.batch_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            report_path = self.reports_path / report_filename
            
            # Create detailed batch report
            report_data = {
                "batch_info": {
                    "batch_id": batch_result.batch_id,
                    "timestamp": batch_result.timestamp.isoformat(),
                    "processing_time": batch_result.processing_time,
                    "files_processed": batch_result.files_processed,
                    "files_succeeded": batch_result.files_succeeded,
                    "files_failed": batch_result.files_failed,
                    "success_rate": (batch_result.files_succeeded / batch_result.files_processed * 100) if batch_result.files_processed > 0 else 0
                },
                "file_results": [],
                "summary": {
                    "total_size": 0,
                    "file_types": {},
                    "errors": {},
                    "metadata_extracted": 0,
                    "thumbnails_generated": 0,
                    "duplicates_found": 0
                }
            }
            
            # Process individual file results
            for result in batch_result.results:
                file_data = {
                    "file_path": result.file_path,
                    "success": result.success,
                    "error_message": result.error_message,
                    "file_hash": result.file_hash,
                    "file_size": result.file_size,
                    "mime_type": result.mime_type,
                    "processing_time": result.processing_time,
                    "duplicate_of": result.duplicate_of,
                    "metadata_keys": list(result.metadata.keys()) if result.metadata else [],
                    "thumbnails_count": len(result.thumbnails)
                }
                
                report_data["file_results"].append(file_data)
                
                # Update summary statistics
                if result.success:
                    report_data["summary"]["total_size"] += result.file_size
                    
                    if result.metadata:
                        report_data["summary"]["metadata_extracted"] += 1
                    
                    if result.thumbnails:
                        report_data["summary"]["thumbnails_generated"] += 1
                
                # Track file types
                file_ext = Path(result.file_path).suffix.lower()
                report_data["summary"]["file_types"][file_ext] = report_data["summary"]["file_types"].get(file_ext, 0) + 1
                
                # Track errors
                if result.error_message:
                    error_type = self._categorize_error(result.error_message)
                    report_data["summary"]["errors"][error_type] = report_data["summary"]["errors"].get(error_type, 0) + 1
                
                # Track duplicates
                if result.duplicate_of:
                    report_data["summary"]["duplicates_found"] += 1
            
            # Write report to file
            with open(report_path, 'w') as f:
                json.dump(report_data, f, indent=2, default=str)
            
            # Update service statistics
            self.stats["reports_generated"] += 1
            self.stats["last_report"] = datetime.now()
            self.stats["total_files_reported"] += batch_result.files_processed
            
            # Track daily batches
            today = datetime.now().date()
            if today not in self.daily_batches:
                self.daily_batches[today] = []
            self.daily_batches[today].append(batch_result.batch_id)
            
            # Keep batch history (limit to recent batches)
            self.batch_history.append({
                "batch_id": batch_result.batch_id,
                "timestamp": batch_result.timestamp,
                "files_processed": batch_result.files_processed,
                "success_rate": (batch_result.files_succeeded / batch_result.files_processed * 100) if batch_result.files_processed > 0 else 0
            })
            
            # Keep only last 100 batches in memory
            if len(self.batch_history) > 100:
                self.batch_history = self.batch_history[-100:]
            
            logger.info(f"Created batch report: {report_filename}")
            return str(report_path)
            
        except Exception as e:
            logger.error(f"Error creating batch report: {e}")
            raise
    
    def _categorize_error(self, error_message: str) -> str:
        """Categorize error messages for reporting"""
        error_lower = error_message.lower()
        
        if "does not exist" in error_lower:
            return "file_not_found"
        elif "too large" in error_lower:
            return "file_too_large"
        elif "empty" in error_lower:
            return "empty_file"
        elif "duplicate" in error_lower:
            return "duplicate_file"
        elif "permission" in error_lower:
            return "permission_denied"
        elif "format" in error_lower or "unsupported" in error_lower:
            return "unsupported_format"
        elif "metadata" in error_lower:
            return "metadata_extraction_error"
        elif "thumbnail" in error_lower:
            return "thumbnail_generation_error"
        else:
            return "other_error"
    
    async def generate_daily_summary(self, date: Optional[datetime] = None) -> str:
        """Generate a daily summary report"""
        if date is None:
            date = datetime.now().date()
        
        try:
            summary_filename = f"daily_summary_{date.strftime('%Y%m%d')}.json"
            summary_path = self.reports_path / summary_filename
            
            # Collect all batch reports for the day
            daily_reports = []
            for report_file in self.reports_path.glob(f"batch_report_*{date.strftime('%Y%m%d')}*.json"):
                try:
                    with open(report_file, 'r') as f:
                        report_data = json.load(f)
                        daily_reports.append(report_data)
                except Exception as e:
                    logger.warning(f"Could not read report file {report_file}: {e}")
            
            # Aggregate statistics
            summary = {
                "date": date.isoformat(),
                "total_batches": len(daily_reports),
                "total_files_processed": 0,
                "total_files_succeeded": 0,
                "total_files_failed": 0,
                "total_size_processed": 0,
                "total_duplicates": 0,
                "total_metadata_extracted": 0,
                "total_thumbnails_generated": 0,
                "file_types": {},
                "error_types": {},
                "average_batch_size": 0,
                "average_processing_time": 0,
                "success_rate": 0,
                "batches": []
            }
            
            total_processing_time = 0
            
            for report in daily_reports:
                batch_info = report.get("batch_info", {})
                batch_summary = report.get("summary", {})
                
                # Aggregate batch-level statistics
                summary["total_files_processed"] += batch_info.get("files_processed", 0)
                summary["total_files_succeeded"] += batch_info.get("files_succeeded", 0)
                summary["total_files_failed"] += batch_info.get("files_failed", 0)
                summary["total_size_processed"] += batch_summary.get("total_size", 0)
                summary["total_duplicates"] += batch_summary.get("duplicates_found", 0)
                summary["total_metadata_extracted"] += batch_summary.get("metadata_extracted", 0)
                summary["total_thumbnails_generated"] += batch_summary.get("thumbnails_generated", 0)
                
                total_processing_time += batch_info.get("processing_time", 0)
                
                # Aggregate file types
                for file_type, count in batch_summary.get("file_types", {}).items():
                    summary["file_types"][file_type] = summary["file_types"].get(file_type, 0) + count
                
                # Aggregate error types
                for error_type, count in batch_summary.get("errors", {}).items():
                    summary["error_types"][error_type] = summary["error_types"].get(error_type, 0) + count
                
                # Add batch summary
                summary["batches"].append({
                    "batch_id": batch_info.get("batch_id"),
                    "timestamp": batch_info.get("timestamp"),
                    "files_processed": batch_info.get("files_processed", 0),
                    "success_rate": batch_info.get("success_rate", 0),
                    "processing_time": batch_info.get("processing_time", 0)
                })
            
            # Calculate averages
            if summary["total_batches"] > 0:
                summary["average_batch_size"] = summary["total_files_processed"] / summary["total_batches"]
                summary["average_processing_time"] = total_processing_time / summary["total_batches"]
            
            if summary["total_files_processed"] > 0:
                summary["success_rate"] = (summary["total_files_succeeded"] / summary["total_files_processed"]) * 100
            
            # Write summary to file
            with open(summary_path, 'w') as f:
                json.dump(summary, f, indent=2, default=str)
            
            logger.info(f"Generated daily summary: {summary_filename}")
            return str(summary_path)
            
        except Exception as e:
            logger.error(f"Error generating daily summary: {e}")
            raise
    
    async def generate_weekly_summary(self, start_date: Optional[datetime] = None) -> str:
        """Generate a weekly summary report"""
        if start_date is None:
            # Start from last Monday
            today = datetime.now().date()
            days_since_monday = today.weekday()
            start_date = today - timedelta(days=days_since_monday)
        
        end_date = start_date + timedelta(days=6)
        
        try:
            summary_filename = f"weekly_summary_{start_date.strftime('%Y%m%d')}_to_{end_date.strftime('%Y%m%d')}.json"
            summary_path = self.reports_path / summary_filename
            
            # Collect daily summaries for the week
            weekly_data = {
                "week_start": start_date.isoformat(),
                "week_end": end_date.isoformat(),
                "daily_summaries": [],
                "week_totals": {
                    "total_batches": 0,
                    "total_files_processed": 0,
                    "total_files_succeeded": 0,
                    "total_files_failed": 0,
                    "total_size_processed": 0,
                    "total_duplicates": 0,
                    "average_daily_files": 0,
                    "average_success_rate": 0,
                    "file_types": {},
                    "error_types": {}
                }
            }
            
            # Process each day in the week
            current_date = start_date
            daily_success_rates = []
            
            while current_date <= end_date:
                daily_summary_path = self.reports_path / f"daily_summary_{current_date.strftime('%Y%m%d')}.json"
                
                if daily_summary_path.exists():
                    try:
                        with open(daily_summary_path, 'r') as f:
                            daily_data = json.load(f)
                            weekly_data["daily_summaries"].append(daily_data)
                            
                            # Aggregate weekly totals
                            weekly_data["week_totals"]["total_batches"] += daily_data.get("total_batches", 0)
                            weekly_data["week_totals"]["total_files_processed"] += daily_data.get("total_files_processed", 0)
                            weekly_data["week_totals"]["total_files_succeeded"] += daily_data.get("total_files_succeeded", 0)
                            weekly_data["week_totals"]["total_files_failed"] += daily_data.get("total_files_failed", 0)
                            weekly_data["week_totals"]["total_size_processed"] += daily_data.get("total_size_processed", 0)
                            weekly_data["week_totals"]["total_duplicates"] += daily_data.get("total_duplicates", 0)
                            
                            if daily_data.get("success_rate", 0) > 0:
                                daily_success_rates.append(daily_data["success_rate"])
                            
                            # Aggregate file types
                            for file_type, count in daily_data.get("file_types", {}).items():
                                weekly_data["week_totals"]["file_types"][file_type] = weekly_data["week_totals"]["file_types"].get(file_type, 0) + count
                            
                            # Aggregate error types
                            for error_type, count in daily_data.get("error_types", {}).items():
                                weekly_data["week_totals"]["error_types"][error_type] = weekly_data["week_totals"]["error_types"].get(error_type, 0) + count
                                
                    except Exception as e:
                        logger.warning(f"Could not read daily summary for {current_date}: {e}")
                
                current_date += timedelta(days=1)
            
            # Calculate weekly averages
            days_with_data = len(weekly_data["daily_summaries"])
            if days_with_data > 0:
                weekly_data["week_totals"]["average_daily_files"] = weekly_data["week_totals"]["total_files_processed"] / days_with_data
            
            if daily_success_rates:
                weekly_data["week_totals"]["average_success_rate"] = sum(daily_success_rates) / len(daily_success_rates)
            
            # Write weekly summary to file
            with open(summary_path, 'w') as f:
                json.dump(weekly_data, f, indent=2, default=str)
            
            logger.info(f"Generated weekly summary: {summary_filename}")
            return str(summary_path)
            
        except Exception as e:
            logger.error(f"Error generating weekly summary: {e}")
            raise
    
    def get_recent_batches(self, limit: int = 10) -> List[Dict]:
        """Get information about recent batches"""
        return self.batch_history[-limit:] if self.batch_history else []
    
    def get_stats(self) -> Dict:
        """Get report service statistics"""
        stats = self.stats.copy()
        stats.update({
            "uptime_seconds": (datetime.now() - stats["service_start_time"]).total_seconds(),
            "batches_tracked": len(self.batch_history),
            "daily_tracking_days": len(self.daily_batches)
        })
        return stats
    
    def cleanup_old_reports(self, days_to_keep: int = 30):
        """Clean up old report files"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            for report_file in self.reports_path.glob("*.json"):
                try:
                    file_mtime = datetime.fromtimestamp(report_file.stat().st_mtime)
                    if file_mtime < cutoff_date:
                        report_file.unlink()
                        logger.debug(f"Deleted old report: {report_file.name}")
                except Exception as e:
                    logger.warning(f"Could not delete old report {report_file}: {e}")
                    
        except Exception as e:
            logger.error(f"Error during report cleanup: {e}")
    
    async def get_system_health_report(self) -> Dict:
        """Generate a system health report"""
        try:
            health_data = {
                "timestamp": datetime.now().isoformat(),
                "service_uptime": (datetime.now() - self.stats["service_start_time"]).total_seconds(),
                "reports_generated": self.stats["reports_generated"],
                "recent_activity": {
                    "last_24h_batches": 0,
                    "last_7d_batches": 0,
                    "recent_success_rate": 0
                },
                "storage": {
                    "reports_directory": str(self.reports_path),
                    "total_report_files": len(list(self.reports_path.glob("*.json"))),
                    "disk_usage_mb": sum(f.stat().st_size for f in self.reports_path.glob("*.json")) / (1024 * 1024)
                },
                "trends": {
                    "recent_batch_sizes": [],
                    "recent_processing_times": [],
                    "error_patterns": {}
                }
            }
            
            # Calculate recent activity
            now = datetime.now()
            last_24h = now - timedelta(hours=24)
            last_7d = now - timedelta(days=7)
            
            recent_successes = 0
            recent_total = 0
            
            for batch in self.batch_history:
                batch_time = batch["timestamp"]
                if isinstance(batch_time, str):
                    batch_time = datetime.fromisoformat(batch_time)
                
                if batch_time >= last_24h:
                    health_data["recent_activity"]["last_24h_batches"] += 1
                if batch_time >= last_7d:
                    health_data["recent_activity"]["last_7d_batches"] += 1
                
                # Calculate recent success rate
                if batch_time >= last_24h:
                    recent_total += batch["files_processed"]
                    recent_successes += int(batch["files_processed"] * batch["success_rate"] / 100)
            
            if recent_total > 0:
                health_data["recent_activity"]["recent_success_rate"] = (recent_successes / recent_total) * 100
            
            # Get trend data from recent batches
            recent_batches = self.batch_history[-20:] if len(self.batch_history) >= 20 else self.batch_history
            
            for batch in recent_batches:
                health_data["trends"]["recent_batch_sizes"].append(batch["files_processed"])
            
            return health_data
            
        except Exception as e:
            logger.error(f"Error generating health report: {e}")
            return {"error": str(e), "timestamp": datetime.now().isoformat()}