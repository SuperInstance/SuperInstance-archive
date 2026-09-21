#!/usr/bin/env python3
"""
Data Quality Monitor for ActiveLog
Monitors data quality, integrity, and health across the system
"""

import asyncio
import json
import logging
import os
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Union, Callable
from collections import defaultdict, Counter
from pathlib import Path
import numpy as np
from enum import Enum
import statistics

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class QualityMetric(Enum):
    """Types of quality metrics to monitor"""
    COMPLETENESS = "completeness"
    ACCURACY = "accuracy"
    CONSISTENCY = "consistency"
    TIMELINESS = "timeliness"
    VALIDITY = "validity"
    UNIQUENESS = "uniqueness"
    INTEGRITY = "integrity"

class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

@dataclass
class QualityCheck:
    """Represents a data quality check"""
    check_id: str
    name: str
    description: str
    metric_type: QualityMetric
    threshold_value: float
    threshold_operator: str  # "gt", "lt", "eq", "gte", "lte"
    enabled: bool = True
    check_function: Optional[Callable] = None

@dataclass
class QualityResult:
    """Result of a quality check"""
    check_id: str
    metric_value: float
    threshold_value: float
    passed: bool
    severity: AlertSeverity
    details: Dict[str, Any]
    checked_at: datetime
    affected_items: List[str] = None

@dataclass
class QualityReport:
    """Comprehensive quality report"""
    report_id: str
    user_id: str
    generated_at: datetime
    overall_score: float
    metric_scores: Dict[QualityMetric, float]
    check_results: List[QualityResult]
    recommendations: List[str]
    trend_analysis: Dict[str, Any]

@dataclass
class QualityAlert:
    """Quality alert notification"""
    alert_id: str
    user_id: str
    severity: AlertSeverity
    title: str
    description: str
    metric_type: QualityMetric
    affected_items_count: int
    created_at: datetime
    resolved: bool = False
    resolved_at: Optional[datetime] = None

class DataQualityChecker:
    """Core data quality checking engine"""
    
    def __init__(self):
        self.quality_checks = {}
        self._register_default_checks()
    
    def _register_default_checks(self):
        """Register default quality checks"""
        checks = [
            # Completeness checks
            QualityCheck(
                check_id="missing_metadata",
                name="Missing Metadata",
                description="Check for items missing essential metadata",
                metric_type=QualityMetric.COMPLETENESS,
                threshold_value=0.1,  # Max 10% missing metadata
                threshold_operator="lt"
            ),
            QualityCheck(
                check_id="missing_classifications",
                name="Missing Classifications",
                description="Check for unclassified data items",
                metric_type=QualityMetric.COMPLETENESS,
                threshold_value=0.05,  # Max 5% unclassified
                threshold_operator="lt"
            ),
            
            # Accuracy checks
            QualityCheck(
                check_id="low_confidence_classifications",
                name="Low Confidence Classifications",
                description="Check for classifications with low confidence",
                metric_type=QualityMetric.ACCURACY,
                threshold_value=0.2,  # Max 20% low confidence
                threshold_operator="lt"
            ),
            QualityCheck(
                check_id="invalid_timestamps",
                name="Invalid Timestamps",
                description="Check for invalid or future timestamps",
                metric_type=QualityMetric.VALIDITY,
                threshold_value=0.01,  # Max 1% invalid timestamps
                threshold_operator="lt"
            ),
            
            # Consistency checks
            QualityCheck(
                check_id="duplicate_content",
                name="Duplicate Content",
                description="Check for duplicate or near-duplicate content",
                metric_type=QualityMetric.UNIQUENESS,
                threshold_value=0.05,  # Max 5% duplicates
                threshold_operator="lt"
            ),
            QualityCheck(
                check_id="inconsistent_formats",
                name="Inconsistent Formats",
                description="Check for format inconsistencies within data types",
                metric_type=QualityMetric.CONSISTENCY,
                threshold_value=0.1,  # Max 10% format inconsistencies
                threshold_operator="lt"
            ),
            
            # Timeliness checks
            QualityCheck(
                check_id="stale_data",
                name="Stale Data",
                description="Check for data that hasn't been updated recently",
                metric_type=QualityMetric.TIMELINESS,
                threshold_value=0.3,  # Max 30% stale data
                threshold_operator="lt"
            ),
            
            # Integrity checks
            QualityCheck(
                check_id="broken_references",
                name="Broken References",
                description="Check for broken file references or missing content",
                metric_type=QualityMetric.INTEGRITY,
                threshold_value=0.02,  # Max 2% broken references
                threshold_operator="lt"
            )
        ]
        
        for check in checks:
            self.register_check(check)
    
    def register_check(self, check: QualityCheck):
        """Register a quality check"""
        self.quality_checks[check.check_id] = check
        logger.info(f"Registered quality check: {check.name}")
    
    async def run_quality_checks(self, user_id: str, data_items: List[Dict[str, Any]]) -> List[QualityResult]:
        """Run all enabled quality checks"""
        results = []
        
        for check in self.quality_checks.values():
            if not check.enabled:
                continue
            
            try:
                result = await self._run_single_check(check, user_id, data_items)
                results.append(result)
            except Exception as e:
                logger.error(f"Error running check {check.check_id}: {str(e)}")
                
                # Create error result
                error_result = QualityResult(
                    check_id=check.check_id,
                    metric_value=0.0,
                    threshold_value=check.threshold_value,
                    passed=False,
                    severity=AlertSeverity.ERROR,
                    details={"error": str(e)},
                    checked_at=datetime.now(timezone.utc)
                )
                results.append(error_result)
        
        return results
    
    async def _run_single_check(self, check: QualityCheck, user_id: str, 
                               data_items: List[Dict[str, Any]]) -> QualityResult:
        """Run a single quality check"""
        if check.check_function:
            metric_value, details, affected_items = await check.check_function(data_items)
        else:
            metric_value, details, affected_items = await self._run_built_in_check(check, data_items)
        
        # Evaluate threshold
        passed = self._evaluate_threshold(metric_value, check.threshold_value, check.threshold_operator)
        
        # Determine severity
        severity = self._determine_severity(check.metric_type, metric_value, check.threshold_value, passed)
        
        return QualityResult(
            check_id=check.check_id,
            metric_value=metric_value,
            threshold_value=check.threshold_value,
            passed=passed,
            severity=severity,
            details=details,
            checked_at=datetime.now(timezone.utc),
            affected_items=affected_items
        )
    
    async def _run_built_in_check(self, check: QualityCheck, 
                                 data_items: List[Dict[str, Any]]) -> tuple:
        """Run built-in quality checks"""
        if check.check_id == "missing_metadata":
            return await self._check_missing_metadata(data_items)
        elif check.check_id == "missing_classifications":
            return await self._check_missing_classifications(data_items)
        elif check.check_id == "low_confidence_classifications":
            return await self._check_low_confidence_classifications(data_items)
        elif check.check_id == "invalid_timestamps":
            return await self._check_invalid_timestamps(data_items)
        elif check.check_id == "duplicate_content":
            return await self._check_duplicate_content(data_items)
        elif check.check_id == "inconsistent_formats":
            return await self._check_inconsistent_formats(data_items)
        elif check.check_id == "stale_data":
            return await self._check_stale_data(data_items)
        elif check.check_id == "broken_references":
            return await self._check_broken_references(data_items)
        else:
            raise ValueError(f"Unknown built-in check: {check.check_id}")
    
    async def _check_missing_metadata(self, data_items: List[Dict[str, Any]]) -> tuple:
        """Check for items with missing essential metadata"""
        essential_fields = ['created_at', 'data_type', 'source']
        missing_metadata_items = []
        
        for item in data_items:
            missing_fields = [field for field in essential_fields if not item.get(field)]
            if missing_fields:
                missing_metadata_items.append({
                    'item_id': item.get('id', 'unknown'),
                    'missing_fields': missing_fields
                })
        
        missing_ratio = len(missing_metadata_items) / len(data_items) if data_items else 0
        
        return missing_ratio, {
            'missing_count': len(missing_metadata_items),
            'total_count': len(data_items),
            'missing_fields_distribution': Counter(
                field for item in missing_metadata_items for field in item['missing_fields']
            )
        }, [item['item_id'] for item in missing_metadata_items]
    
    async def _check_missing_classifications(self, data_items: List[Dict[str, Any]]) -> tuple:
        """Check for unclassified data items"""
        unclassified_items = [
            item.get('id', 'unknown') for item in data_items 
            if item.get('data_type') in [None, 'unknown', '']
        ]
        
        unclassified_ratio = len(unclassified_items) / len(data_items) if data_items else 0
        
        return unclassified_ratio, {
            'unclassified_count': len(unclassified_items),
            'total_count': len(data_items)
        }, unclassified_items
    
    async def _check_low_confidence_classifications(self, data_items: List[Dict[str, Any]]) -> tuple:
        """Check for classifications with low confidence scores"""
        low_confidence_threshold = 0.5
        low_confidence_items = []
        
        for item in data_items:
            confidence = item.get('confidence_score')
            if confidence is not None and confidence < low_confidence_threshold:
                low_confidence_items.append({
                    'item_id': item.get('id', 'unknown'),
                    'confidence': confidence,
                    'data_type': item.get('data_type')
                })
        
        low_confidence_ratio = len(low_confidence_items) / len(data_items) if data_items else 0
        
        return low_confidence_ratio, {
            'low_confidence_count': len(low_confidence_items),
            'total_count': len(data_items),
            'avg_confidence': statistics.mean([item['confidence'] for item in low_confidence_items]) if low_confidence_items else 0
        }, [item['item_id'] for item in low_confidence_items]
    
    async def _check_invalid_timestamps(self, data_items: List[Dict[str, Any]]) -> tuple:
        """Check for invalid timestamps"""
        invalid_timestamp_items = []
        current_time = datetime.now(timezone.utc)
        
        for item in data_items:
            created_at = item.get('created_at')
            if created_at:
                try:
                    if isinstance(created_at, str):
                        timestamp = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    else:
                        timestamp = created_at
                    
                    # Check if timestamp is in the future (more than 1 hour ahead)
                    if timestamp > current_time + timedelta(hours=1):
                        invalid_timestamp_items.append({
                            'item_id': item.get('id', 'unknown'),
                            'timestamp': timestamp,
                            'reason': 'future_timestamp'
                        })
                    
                    # Check if timestamp is too far in the past (before 1970)
                    elif timestamp.year < 1970:
                        invalid_timestamp_items.append({
                            'item_id': item.get('id', 'unknown'),
                            'timestamp': timestamp,
                            'reason': 'ancient_timestamp'
                        })
                
                except (ValueError, TypeError):
                    invalid_timestamp_items.append({
                        'item_id': item.get('id', 'unknown'),
                        'timestamp': created_at,
                        'reason': 'invalid_format'
                    })
        
        invalid_ratio = len(invalid_timestamp_items) / len(data_items) if data_items else 0
        
        return invalid_ratio, {
            'invalid_count': len(invalid_timestamp_items),
            'total_count': len(data_items),
            'reasons': Counter(item['reason'] for item in invalid_timestamp_items)
        }, [item['item_id'] for item in invalid_timestamp_items]
    
    async def _check_duplicate_content(self, data_items: List[Dict[str, Any]]) -> tuple:
        """Check for duplicate content based on hashes"""
        content_hashes = defaultdict(list)
        duplicate_items = []
        
        for item in data_items:
            content_hash = item.get('content_hash') or item.get('checksum')
            if content_hash:
                content_hashes[content_hash].append(item.get('id', 'unknown'))
        
        # Find duplicates
        for hash_value, item_ids in content_hashes.items():
            if len(item_ids) > 1:
                duplicate_items.extend(item_ids[1:])  # Keep first, mark others as duplicates
        
        duplicate_ratio = len(duplicate_items) / len(data_items) if data_items else 0
        
        return duplicate_ratio, {
            'duplicate_count': len(duplicate_items),
            'total_count': len(data_items),
            'duplicate_groups': len([ids for ids in content_hashes.values() if len(ids) > 1])
        }, duplicate_items
    
    async def _check_inconsistent_formats(self, data_items: List[Dict[str, Any]]) -> tuple:
        """Check for format inconsistencies within data types"""
        format_by_type = defaultdict(Counter)
        inconsistent_items = []
        
        for item in data_items:
            data_type = item.get('data_type')
            file_extension = item.get('metadata', {}).get('file_extension') or \
                           (item.get('filename', '').split('.')[-1] if '.' in item.get('filename', '') else None)
            
            if data_type and file_extension:
                format_by_type[data_type][file_extension] += 1
        
        # Check for types with too many different formats
        for data_type, formats in format_by_type.items():
            if len(formats) > 5:  # More than 5 different formats for one type
                # Find items with rare formats (less than 5% of total for that type)
                total_for_type = sum(formats.values())
                rare_formats = [fmt for fmt, count in formats.items() if count / total_for_type < 0.05]
                
                for item in data_items:
                    if item.get('data_type') == data_type:
                        item_extension = item.get('metadata', {}).get('file_extension')
                        if item_extension in rare_formats:
                            inconsistent_items.append(item.get('id', 'unknown'))
        
        inconsistent_ratio = len(inconsistent_items) / len(data_items) if data_items else 0
        
        return inconsistent_ratio, {
            'inconsistent_count': len(inconsistent_items),
            'total_count': len(data_items),
            'format_distribution': {k: dict(v) for k, v in format_by_type.items()}
        }, inconsistent_items
    
    async def _check_stale_data(self, data_items: List[Dict[str, Any]]) -> tuple:
        """Check for data that hasn't been accessed or updated recently"""
        current_time = datetime.now(timezone.utc)
        stale_threshold = timedelta(days=90)  # 90 days
        stale_items = []
        
        for item in data_items:
            # Use the most recent of created_at or updated_at
            timestamps = []
            
            for field in ['created_at', 'updated_at', 'last_accessed']:
                timestamp_value = item.get(field)
                if timestamp_value:
                    try:
                        if isinstance(timestamp_value, str):
                            timestamp = datetime.fromisoformat(timestamp_value.replace('Z', '+00:00'))
                        else:
                            timestamp = timestamp_value
                        timestamps.append(timestamp)
                    except (ValueError, TypeError):
                        continue
            
            if timestamps:
                most_recent = max(timestamps)
                if current_time - most_recent > stale_threshold:
                    stale_items.append({
                        'item_id': item.get('id', 'unknown'),
                        'last_activity': most_recent,
                        'days_stale': (current_time - most_recent).days
                    })
        
        stale_ratio = len(stale_items) / len(data_items) if data_items else 0
        
        return stale_ratio, {
            'stale_count': len(stale_items),
            'total_count': len(data_items),
            'avg_days_stale': statistics.mean([item['days_stale'] for item in stale_items]) if stale_items else 0
        }, [item['item_id'] for item in stale_items]
    
    async def _check_broken_references(self, data_items: List[Dict[str, Any]]) -> tuple:
        """Check for broken file references"""
        broken_items = []
        
        for item in data_items:
            # Check if file path exists (if provided)
            file_path = item.get('file_path') or item.get('metadata', {}).get('file_path')
            if file_path and not os.path.exists(file_path):
                broken_items.append({
                    'item_id': item.get('id', 'unknown'),
                    'file_path': file_path,
                    'reason': 'file_not_found'
                })
            
            # Check for missing required content
            content = item.get('content')
            if content is None or (isinstance(content, str) and len(content.strip()) == 0):
                broken_items.append({
                    'item_id': item.get('id', 'unknown'),
                    'reason': 'missing_content'
                })
        
        broken_ratio = len(broken_items) / len(data_items) if data_items else 0
        
        return broken_ratio, {
            'broken_count': len(broken_items),
            'total_count': len(data_items),
            'break_reasons': Counter(item['reason'] for item in broken_items)
        }, [item['item_id'] for item in broken_items]
    
    def _evaluate_threshold(self, value: float, threshold: float, operator: str) -> bool:
        """Evaluate if a value meets the threshold criteria"""
        if operator == "gt":
            return value > threshold
        elif operator == "lt":
            return value < threshold
        elif operator == "eq":
            return abs(value - threshold) < 0.001  # Small epsilon for float comparison
        elif operator == "gte":
            return value >= threshold
        elif operator == "lte":
            return value <= threshold
        else:
            raise ValueError(f"Unknown threshold operator: {operator}")
    
    def _determine_severity(self, metric_type: QualityMetric, value: float, 
                          threshold: float, passed: bool) -> AlertSeverity:
        """Determine alert severity based on metric type and values"""
        if passed:
            return AlertSeverity.INFO
        
        # Calculate how far the value is from the threshold
        if threshold != 0:
            deviation_ratio = abs(value - threshold) / threshold
        else:
            deviation_ratio = abs(value)
        
        # Determine severity based on metric type and deviation
        if metric_type in [QualityMetric.INTEGRITY, QualityMetric.ACCURACY]:
            if deviation_ratio > 0.5:
                return AlertSeverity.CRITICAL
            elif deviation_ratio > 0.2:
                return AlertSeverity.ERROR
            else:
                return AlertSeverity.WARNING
        
        elif metric_type in [QualityMetric.COMPLETENESS, QualityMetric.VALIDITY]:
            if deviation_ratio > 0.3:
                return AlertSeverity.ERROR
            elif deviation_ratio > 0.1:
                return AlertSeverity.WARNING
            else:
                return AlertSeverity.INFO
        
        else:  # CONSISTENCY, TIMELINESS, UNIQUENESS
            if deviation_ratio > 0.4:
                return AlertSeverity.WARNING
            else:
                return AlertSeverity.INFO

class QualityMonitor:
    """Main quality monitoring service"""
    
    def __init__(self, database_url: str = None):
        self.database_url = database_url
        self.checker = DataQualityChecker()
        self.alert_history = []
        self.quality_history = []
        self.monitoring_enabled = True
    
    async def run_quality_assessment(self, user_id: str, 
                                   data_items: List[Dict[str, Any]] = None) -> QualityReport:
        """Run comprehensive quality assessment"""
        if data_items is None:
            data_items = await self._get_user_data(user_id)
        
        # Run quality checks
        check_results = await self.checker.run_quality_checks(user_id, data_items)
        
        # Calculate metric scores
        metric_scores = self._calculate_metric_scores(check_results)
        
        # Calculate overall score
        overall_score = self._calculate_overall_score(metric_scores)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(check_results, metric_scores)
        
        # Generate trend analysis
        trend_analysis = await self._generate_trend_analysis(user_id, metric_scores)
        
        # Create report
        report = QualityReport(
            report_id=f"quality_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            user_id=user_id,
            generated_at=datetime.now(timezone.utc),
            overall_score=overall_score,
            metric_scores=metric_scores,
            check_results=check_results,
            recommendations=recommendations,
            trend_analysis=trend_analysis
        )
        
        # Store in history
        self.quality_history.append(report)
        
        # Generate alerts
        await self._generate_alerts(user_id, check_results)
        
        return report
    
    async def monitor_continuous(self, user_id: str, interval_minutes: int = 60):
        """Start continuous quality monitoring"""
        logger.info(f"Starting continuous quality monitoring for user {user_id}")
        
        while self.monitoring_enabled:
            try:
                await self.run_quality_assessment(user_id)
                await asyncio.sleep(interval_minutes * 60)
            except Exception as e:
                logger.error(f"Error in continuous monitoring: {str(e)}")
                await asyncio.sleep(300)  # Wait 5 minutes before retry
    
    def stop_monitoring(self):
        """Stop continuous monitoring"""
        self.monitoring_enabled = False
        logger.info("Quality monitoring stopped")
    
    async def get_quality_trends(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """Get quality trends over time"""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        relevant_reports = [
            report for report in self.quality_history
            if report.user_id == user_id and report.generated_at >= cutoff_date
        ]
        
        if not relevant_reports:
            return {"message": "No quality data available for the specified period"}
        
        # Extract trends
        dates = [report.generated_at for report in relevant_reports]
        overall_scores = [report.overall_score for report in relevant_reports]
        
        # Calculate trend for each metric
        metric_trends = {}
        for metric in QualityMetric:
            metric_values = [
                report.metric_scores.get(metric, 0) for report in relevant_reports
            ]
            
            if len(metric_values) >= 2:
                # Simple trend calculation
                trend_direction = "improving" if metric_values[-1] > metric_values[0] else "declining"
                metric_trends[metric.value] = {
                    "direction": trend_direction,
                    "current_value": metric_values[-1],
                    "change": metric_values[-1] - metric_values[0],
                    "values": metric_values
                }
        
        return {
            "period_days": days,
            "reports_count": len(relevant_reports),
            "overall_trend": {
                "direction": "improving" if overall_scores[-1] > overall_scores[0] else "declining",
                "current_score": overall_scores[-1],
                "change": overall_scores[-1] - overall_scores[0],
                "values": overall_scores
            },
            "metric_trends": metric_trends,
            "dates": [date.isoformat() for date in dates]
        }
    
    def _calculate_metric_scores(self, check_results: List[QualityResult]) -> Dict[QualityMetric, float]:
        """Calculate scores for each quality metric"""
        metric_results = defaultdict(list)
        
        # Group results by metric type
        for result in check_results:
            metric_type = None
            for check in self.checker.quality_checks.values():
                if check.check_id == result.check_id:
                    metric_type = check.metric_type
                    break
            
            if metric_type:
                # Convert metric value to a 0-1 score (1 being perfect)
                score = 1.0 - result.metric_value  # Assuming metric_value is error rate
                metric_results[metric_type].append(max(0, min(1, score)))
        
        # Calculate average score for each metric
        metric_scores = {}
        for metric, scores in metric_results.items():
            metric_scores[metric] = statistics.mean(scores) if scores else 0.0
        
        # Ensure all metrics have a score
        for metric in QualityMetric:
            if metric not in metric_scores:
                metric_scores[metric] = 1.0  # Perfect score if no checks for this metric
        
        return metric_scores
    
    def _calculate_overall_score(self, metric_scores: Dict[QualityMetric, float]) -> float:
        """Calculate overall quality score"""
        # Weight different metrics
        weights = {
            QualityMetric.COMPLETENESS: 0.2,
            QualityMetric.ACCURACY: 0.25,
            QualityMetric.CONSISTENCY: 0.15,
            QualityMetric.TIMELINESS: 0.1,
            QualityMetric.VALIDITY: 0.15,
            QualityMetric.UNIQUENESS: 0.1,
            QualityMetric.INTEGRITY: 0.05
        }
        
        weighted_sum = 0.0
        total_weight = 0.0
        
        for metric, score in metric_scores.items():
            weight = weights.get(metric, 0.1)  # Default weight
            weighted_sum += score * weight
            total_weight += weight
        
        return weighted_sum / total_weight if total_weight > 0 else 0.0
    
    def _generate_recommendations(self, check_results: List[QualityResult], 
                                metric_scores: Dict[QualityMetric, float]) -> List[str]:
        """Generate quality improvement recommendations"""
        recommendations = []
        
        # Based on failed checks
        failed_checks = [result for result in check_results if not result.passed]
        
        for result in failed_checks:
            if result.check_id == "missing_metadata":
                recommendations.append("Add missing metadata fields to improve data completeness")
            elif result.check_id == "missing_classifications":
                recommendations.append("Classify unidentified data items to improve data organization")
            elif result.check_id == "low_confidence_classifications":
                recommendations.append("Review and improve low-confidence classifications")
            elif result.check_id == "invalid_timestamps":
                recommendations.append("Fix invalid timestamps in your data")
            elif result.check_id == "duplicate_content":
                recommendations.append("Remove or merge duplicate content to optimize storage")
            elif result.check_id == "inconsistent_formats":
                recommendations.append("Standardize file formats within data types")
            elif result.check_id == "stale_data":
                recommendations.append("Archive or delete stale data that hasn't been accessed recently")
            elif result.check_id == "broken_references":
                recommendations.append("Fix broken file references and missing content")
        
        # Based on low metric scores
        for metric, score in metric_scores.items():
            if score < 0.7:  # Low score threshold
                if metric == QualityMetric.COMPLETENESS:
                    recommendations.append("Focus on improving data completeness by filling missing information")
                elif metric == QualityMetric.ACCURACY:
                    recommendations.append("Improve data accuracy by validating and correcting classification errors")
                elif metric == QualityMetric.CONSISTENCY:
                    recommendations.append("Enhance data consistency by standardizing formats and conventions")
                elif metric == QualityMetric.TIMELINESS:
                    recommendations.append("Update stale data and establish regular maintenance schedules")
                elif metric == QualityMetric.VALIDITY:
                    recommendations.append("Validate and correct invalid data entries")
                elif metric == QualityMetric.UNIQUENESS:
                    recommendations.append("Identify and remove duplicate entries")
                elif metric == QualityMetric.INTEGRITY:
                    recommendations.append("Repair broken references and restore missing content")
        
        # Remove duplicates and limit to top recommendations
        return list(dict.fromkeys(recommendations))[:5]
    
    async def _generate_trend_analysis(self, user_id: str, 
                                     current_scores: Dict[QualityMetric, float]) -> Dict[str, Any]:
        """Generate trend analysis based on historical data"""
        # Get recent reports for comparison
        recent_reports = [
            report for report in self.quality_history[-10:]  # Last 10 reports
            if report.user_id == user_id
        ]
        
        if len(recent_reports) < 2:
            return {"message": "Insufficient historical data for trend analysis"}
        
        # Compare current scores with previous
        previous_report = recent_reports[-2] if len(recent_reports) >= 2 else recent_reports[0]
        trends = {}
        
        for metric, current_score in current_scores.items():
            previous_score = previous_report.metric_scores.get(metric, 0.0)
            change = current_score - previous_score
            
            if abs(change) < 0.05:
                trend = "stable"
            elif change > 0:
                trend = "improving"
            else:
                trend = "declining"
            
            trends[metric.value] = {
                "trend": trend,
                "change": change,
                "current": current_score,
                "previous": previous_score
            }
        
        # Overall trend
        current_overall = sum(current_scores.values()) / len(current_scores)
        previous_overall = sum(previous_report.metric_scores.values()) / len(previous_report.metric_scores)
        overall_change = current_overall - previous_overall
        
        return {
            "overall_trend": {
                "trend": "improving" if overall_change > 0.05 else "declining" if overall_change < -0.05 else "stable",
                "change": overall_change,
                "current": current_overall,
                "previous": previous_overall
            },
            "metric_trends": trends,
            "reports_analyzed": len(recent_reports)
        }
    
    async def _generate_alerts(self, user_id: str, check_results: List[QualityResult]):
        """Generate quality alerts based on check results"""
        for result in check_results:
            if result.severity in [AlertSeverity.ERROR, AlertSeverity.CRITICAL]:
                alert = QualityAlert(
                    alert_id=f"alert_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",
                    user_id=user_id,
                    severity=result.severity,
                    title=f"Data Quality Issue: {result.check_id}",
                    description=f"Quality check failed with value {result.metric_value:.3f} (threshold: {result.threshold_value:.3f})",
                    metric_type=self._get_metric_type_for_check(result.check_id),
                    affected_items_count=len(result.affected_items) if result.affected_items else 0,
                    created_at=datetime.now(timezone.utc)
                )
                
                self.alert_history.append(alert)
                logger.warning(f"Quality alert generated: {alert.title} for user {user_id}")
    
    def _get_metric_type_for_check(self, check_id: str) -> QualityMetric:
        """Get metric type for a check ID"""
        for check in self.checker.quality_checks.values():
            if check.check_id == check_id:
                return check.metric_type
        return QualityMetric.INTEGRITY  # Default
    
    async def _get_user_data(self, user_id: str) -> List[Dict[str, Any]]:
        """Get user data for quality assessment (mock implementation)"""
        # In production, this would query the actual database
        return [
            {
                "id": f"item_{i}",
                "user_id": user_id,
                "data_type": ["image", "text", "document", "unknown"][i % 4],
                "source": ["google_photos", "dropbox", "email", "manual"][i % 4],
                "created_at": (datetime.now(timezone.utc) - timedelta(days=i % 30)).isoformat(),
                "size_bytes": 1024 * 1024 * (i % 10 + 1),
                "confidence_score": 0.2 + (i % 8) * 0.1,
                "content_hash": f"hash_{i % 50}",  # Some duplicates
                "metadata": {
                    "file_extension": ["jpg", "txt", "pdf", None][i % 4]
                }
            }
            for i in range(200)  # 200 mock items with some quality issues
        ]

# CLI Interface
async def main():
    """Command-line interface for quality monitor"""
    import argparse
    
    parser = argparse.ArgumentParser(description='ActiveLog Data Quality Monitor')
    parser.add_argument('action', choices=['assess', 'monitor', 'trends', 'alerts'])
    parser.add_argument('--user-id', default='test_user', help='User ID for assessment')
    parser.add_argument('--output', help='Output file for results')
    parser.add_argument('--format', choices=['json', 'summary'], default='summary', help='Output format')
    parser.add_argument('--days', type=int, default=30, help='Days for trend analysis')
    parser.add_argument('--interval', type=int, default=60, help='Monitoring interval in minutes')
    
    args = parser.parse_args()
    
    monitor = QualityMonitor()
    
    if args.action == 'assess':
        # Run quality assessment
        report = await monitor.run_quality_assessment(args.user_id)
        
        if args.format == 'json':
            output = json.dumps(asdict(report), indent=2, default=str)
        else:
            output = f"Quality Assessment Report for {args.user_id}\n"
            output += "=" * 50 + "\n\n"
            output += f"Overall Score: {report.overall_score:.2f}/1.00\n\n"
            
            output += "Metric Scores:\n"
            for metric, score in report.metric_scores.items():
                output += f"  {metric.value}: {score:.2f}\n"
            
            output += f"\nChecks Results ({len(report.check_results)}):\n"
            for result in report.check_results:
                status = "✓" if result.passed else "✗"
                output += f"  {status} {result.check_id}: {result.metric_value:.3f} ({result.severity.value})\n"
            
            output += f"\nRecommendations ({len(report.recommendations)}):\n"
            for rec in report.recommendations:
                output += f"  • {rec}\n"
        
        if args.output:
            with open(args.output, 'w') as f:
                f.write(output)
            print(f"Quality report saved to {args.output}")
        else:
            print(output)
    
    elif args.action == 'monitor':
        # Start continuous monitoring
        print(f"Starting continuous quality monitoring for {args.user_id}")
        print(f"Monitoring interval: {args.interval} minutes")
        print("Press Ctrl+C to stop monitoring")
        
        try:
            await monitor.monitor_continuous(args.user_id, args.interval)
        except KeyboardInterrupt:
            monitor.stop_monitoring()
            print("\nMonitoring stopped")
    
    elif args.action == 'trends':
        # Generate initial data
        await monitor.run_quality_assessment(args.user_id)
        await asyncio.sleep(1)
        await monitor.run_quality_assessment(args.user_id)  # Second report for trend
        
        trends = await monitor.get_quality_trends(args.user_id, args.days)
        
        if args.format == 'json':
            output = json.dumps(trends, indent=2)
        else:
            output = f"Quality Trends for {args.user_id} (last {args.days} days)\n"
            output += "=" * 50 + "\n\n"
            
            if "overall_trend" in trends:
                ot = trends["overall_trend"]
                output += f"Overall Trend: {ot['trend']} (change: {ot['change']:+.3f})\n"
                output += f"Current Score: {ot['current']:.3f}\n\n"
                
                output += "Metric Trends:\n"
                for metric, data in trends.get("metric_trends", {}).items():
                    output += f"  {metric}: {data['trend']} ({data['change']:+.3f})\n"
            else:
                output += trends.get("message", "No trend data available")
        
        if args.output:
            with open(args.output, 'w') as f:
                f.write(output)
            print(f"Trends report saved to {args.output}")
        else:
            print(output)
    
    elif args.action == 'alerts':
        # Show recent alerts
        await monitor.run_quality_assessment(args.user_id)  # Generate some alerts
        
        user_alerts = [alert for alert in monitor.alert_history if alert.user_id == args.user_id]
        
        if args.format == 'json':
            output = json.dumps([asdict(alert) for alert in user_alerts], indent=2, default=str)
        else:
            output = f"Quality Alerts for {args.user_id}\n"
            output += "=" * 50 + "\n\n"
            
            if user_alerts:
                for alert in user_alerts[-10:]:  # Last 10 alerts
                    icon = {"info": "ℹ", "warning": "⚠", "error": "✗", "critical": "🚨"}
                    output += f"{icon.get(alert.severity.value, '•')} {alert.title}\n"
                    output += f"  {alert.description}\n"
                    output += f"  Severity: {alert.severity.value}, Created: {alert.created_at}\n\n"
            else:
                output += "No alerts found\n"
        
        if args.output:
            with open(args.output, 'w') as f:
                f.write(output)
            print(f"Alerts report saved to {args.output}")
        else:
            print(output)

if __name__ == "__main__":
    asyncio.run(main())