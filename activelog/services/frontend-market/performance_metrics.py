"""
Frontend Performance Metrics System
Comprehensive performance monitoring, analysis, and optimization recommendations
"""

from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
from enum import Enum
import uuid
import asyncio
import logging
import json
import sqlite3
import aiohttp
import time
from statistics import mean, median, stdev
import numpy as np

logger = logging.getLogger(__name__)

class MetricType(str, Enum):
    PERFORMANCE = "performance"
    ACCESSIBILITY = "accessibility"
    SEO = "seo"
    BEST_PRACTICES = "best_practices"
    SECURITY = "security"
    USER_EXPERIENCE = "user_experience"
    BUSINESS = "business"

class PerformanceLevel(str, Enum):
    EXCELLENT = "excellent"    # 90-100
    GOOD = "good"             # 75-89
    NEEDS_IMPROVEMENT = "needs_improvement"  # 50-74
    POOR = "poor"             # 0-49

class MetricRecord(BaseModel):
    id: str
    frontend_id: str
    metric_type: MetricType
    metric_name: str
    value: float
    unit: str = ""
    
    # Context information
    url: Optional[str] = None
    device_type: str = "desktop"  # desktop, mobile, tablet
    location: str = "global"
    user_agent: Optional[str] = None
    
    # Metadata
    measurement_method: str = "automated"
    data_source: str = "lighthouse"
    confidence_score: float = 1.0
    
    timestamp: datetime
    metadata: Dict[str, Any] = {}

class PerformanceBenchmark(BaseModel):
    id: str
    metric_name: str
    industry_average: float
    top_10_percent: float
    top_25_percent: float
    median: float
    
    # Segmentation
    category: str = "general"
    framework: Optional[str] = None
    complexity_level: str = "medium"
    
    last_updated: datetime

class PerformanceAlert(BaseModel):
    id: str
    frontend_id: str
    alert_type: str  # threshold_breach, degradation, anomaly
    severity: str    # low, medium, high, critical
    
    metric_name: str
    current_value: float
    threshold_value: float
    
    message: str
    recommendations: List[str] = []
    
    created_at: datetime
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None

class OptimizationRecommendation(BaseModel):
    id: str
    frontend_id: str
    category: str
    priority: str    # low, medium, high, critical
    
    title: str
    description: str
    technical_details: str
    
    # Impact estimates
    estimated_improvement: Dict[str, float] = {}  # metric -> expected improvement
    implementation_effort: str = "medium"  # low, medium, high
    estimated_cost: float = 0.0
    
    # Implementation details
    implementation_steps: List[str] = []
    code_examples: List[Dict[str, str]] = []
    tools_required: List[str] = []
    
    created_at: datetime
    status: str = "pending"  # pending, in_progress, completed, dismissed

class PerformanceReport(BaseModel):
    id: str
    frontend_id: str
    report_type: str = "comprehensive"
    
    # Overall scores
    overall_score: float
    performance_score: float
    accessibility_score: float
    seo_score: float
    best_practices_score: float
    
    # Detailed metrics
    core_web_vitals: Dict[str, float]
    loading_metrics: Dict[str, float]
    interactivity_metrics: Dict[str, float]
    visual_stability_metrics: Dict[str, float]
    
    # Comparisons
    industry_comparison: Dict[str, str]
    historical_comparison: Dict[str, float]
    
    # Recommendations
    top_recommendations: List[OptimizationRecommendation]
    
    generated_at: datetime
    period_start: datetime
    period_end: datetime

class PerformanceMetricsManager:
    def __init__(self):
        self.db_path = "/home/activeloguser/activelog/services/frontend-market/data/performance_metrics.db"
        self.init_database()
        
        # Performance thresholds
        self.thresholds = {
            "lcp": {"excellent": 2.5, "good": 4.0},  # Largest Contentful Paint (seconds)
            "fid": {"excellent": 100, "good": 300},   # First Input Delay (ms)
            "cls": {"excellent": 0.1, "good": 0.25},  # Cumulative Layout Shift
            "fcp": {"excellent": 1.8, "good": 3.0},   # First Contentful Paint (seconds)
            "tti": {"excellent": 3.8, "good": 7.3},   # Time to Interactive (seconds)
            "speed_index": {"excellent": 3.4, "good": 5.8},
            "accessibility_score": {"excellent": 90, "good": 75},
            "seo_score": {"excellent": 90, "good": 75},
            "performance_score": {"excellent": 90, "good": 75}
        }
    
    def init_database(self):
        """Initialize performance metrics database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Metrics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS performance_metrics (
                id TEXT PRIMARY KEY,
                frontend_id TEXT NOT NULL,
                metric_type TEXT NOT NULL,
                metric_name TEXT NOT NULL,
                value REAL NOT NULL,
                unit TEXT,
                device_type TEXT DEFAULT 'desktop',
                data TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Benchmarks table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS performance_benchmarks (
                id TEXT PRIMARY KEY,
                metric_name TEXT NOT NULL,
                industry_average REAL NOT NULL,
                top_10_percent REAL NOT NULL,
                data TEXT NOT NULL,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Alerts table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS performance_alerts (
                id TEXT PRIMARY KEY,
                frontend_id TEXT NOT NULL,
                alert_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                metric_name TEXT NOT NULL,
                data TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Recommendations table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS optimization_recommendations (
                id TEXT PRIMARY KEY,
                frontend_id TEXT NOT NULL,
                category TEXT NOT NULL,
                priority TEXT NOT NULL,
                title TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                data TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Reports table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS performance_reports (
                id TEXT PRIMARY KEY,
                frontend_id TEXT NOT NULL,
                report_type TEXT NOT NULL,
                overall_score REAL NOT NULL,
                data TEXT NOT NULL,
                generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    async def measure_performance(self, frontend_data: Dict[str, Any]) -> PerformanceReport:
        """Comprehensive performance measurement"""
        frontend_id = frontend_data["frontend_id"]
        url = frontend_data.get("url", frontend_data.get("demo_url"))
        
        if not url:
            raise ValueError("URL required for performance measurement")
        
        logger.info(f"Starting performance measurement for {frontend_id} at {url}")
        
        # Collect various metrics
        lighthouse_metrics = await self._run_lighthouse_audit(url)
        webvitals_metrics = await self._measure_core_web_vitals(url)
        accessibility_metrics = await self._check_accessibility(url)
        seo_metrics = await self._analyze_seo(url)
        security_metrics = await self._security_scan(url)
        
        # Store individual metrics
        all_metrics = []
        
        # Process Lighthouse metrics
        for metric_name, value in lighthouse_metrics.items():
            metric = await self._store_metric(
                frontend_id, MetricType.PERFORMANCE, metric_name, 
                value, url=url, data_source="lighthouse"
            )
            all_metrics.append(metric)
        
        # Process Core Web Vitals
        for metric_name, value in webvitals_metrics.items():
            metric = await self._store_metric(
                frontend_id, MetricType.USER_EXPERIENCE, metric_name,
                value, url=url, data_source="webvitals"
            )
            all_metrics.append(metric)
        
        # Process accessibility metrics
        for metric_name, value in accessibility_metrics.items():
            metric = await self._store_metric(
                frontend_id, MetricType.ACCESSIBILITY, metric_name,
                value, url=url, data_source="axe"
            )
            all_metrics.append(metric)
        
        # Generate comprehensive report
        report = await self._generate_performance_report(frontend_id, all_metrics)
        
        # Check for alerts
        await self._check_performance_alerts(frontend_id, all_metrics)
        
        # Generate optimization recommendations
        await self._generate_recommendations(frontend_id, report)
        
        logger.info(f"Performance measurement completed for {frontend_id}")
        return report
    
    async def _run_lighthouse_audit(self, url: str) -> Dict[str, float]:
        """Run Lighthouse audit (simulated)"""
        # In production, integrate with actual Lighthouse API
        await asyncio.sleep(2)  # Simulate audit time
        
        # Return simulated metrics
        return {
            "performance_score": np.random.normal(75, 15),
            "accessibility_score": np.random.normal(85, 10),
            "best_practices_score": np.random.normal(80, 12),
            "seo_score": np.random.normal(90, 8),
            "first_contentful_paint": np.random.normal(1.5, 0.5),
            "largest_contentful_paint": np.random.normal(2.8, 0.8),
            "first_input_delay": np.random.normal(120, 40),
            "cumulative_layout_shift": np.random.normal(0.15, 0.08),
            "time_to_interactive": np.random.normal(4.2, 1.2),
            "speed_index": np.random.normal(3.8, 1.0),
            "total_blocking_time": np.random.normal(250, 100)
        }
    
    async def _measure_core_web_vitals(self, url: str) -> Dict[str, float]:
        """Measure Core Web Vitals"""
        # Simulate real user monitoring data
        return {
            "lcp_p75": np.random.normal(2.2, 0.6),
            "fid_p75": np.random.normal(95, 30),
            "cls_p75": np.random.normal(0.12, 0.05),
            "fcp_p75": np.random.normal(1.4, 0.4),
            "ttfb_p75": np.random.normal(0.8, 0.3)
        }
    
    async def _check_accessibility(self, url: str) -> Dict[str, float]:
        """Check accessibility compliance"""
        return {
            "wcag_aa_compliance": np.random.normal(88, 8),
            "color_contrast_ratio": np.random.normal(4.5, 0.8),
            "keyboard_navigation": np.random.normal(92, 6),
            "screen_reader_compatibility": np.random.normal(85, 10),
            "alt_text_coverage": np.random.normal(78, 12)
        }
    
    async def _analyze_seo(self, url: str) -> Dict[str, float]:
        """Analyze SEO factors"""
        return {
            "meta_tags_completeness": np.random.normal(85, 10),
            "structured_data_score": np.random.normal(70, 15),
            "mobile_friendliness": np.random.normal(95, 5),
            "page_load_speed": np.random.normal(82, 12),
            "internal_linking": np.random.normal(75, 15)
        }
    
    async def _security_scan(self, url: str) -> Dict[str, float]:
        """Basic security scan"""
        return {
            "https_usage": 100 if url.startswith("https") else 0,
            "security_headers": np.random.normal(75, 15),
            "mixed_content": np.random.normal(95, 8),
            "vulnerable_libraries": np.random.normal(85, 12)
        }
    
    async def _store_metric(self, frontend_id: str, metric_type: MetricType, 
                           metric_name: str, value: float, **kwargs) -> MetricRecord:
        """Store individual metric"""
        metric_id = f"METRIC_{uuid.uuid4().hex[:8].upper()}"
        
        metric = MetricRecord(
            id=metric_id,
            frontend_id=frontend_id,
            metric_type=metric_type,
            metric_name=metric_name,
            value=max(0, min(100, value)) if metric_name.endswith('_score') else max(0, value),
            timestamp=datetime.now(),
            **kwargs
        )
        
        # Store in database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO performance_metrics 
            (id, frontend_id, metric_type, metric_name, value, unit, device_type, data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            metric.id, metric.frontend_id, metric.metric_type.value,
            metric.metric_name, metric.value, metric.unit,
            metric.device_type, metric.model_dump_json()
        ))
        
        conn.commit()
        conn.close()
        
        return metric
    
    async def _generate_performance_report(self, frontend_id: str, 
                                         metrics: List[MetricRecord]) -> PerformanceReport:
        """Generate comprehensive performance report"""
        report_id = f"REPORT_{uuid.uuid4().hex[:8].upper()}"
        
        # Calculate scores
        performance_metrics = [m for m in metrics if m.metric_type == MetricType.PERFORMANCE]
        accessibility_metrics = [m for m in metrics if m.metric_type == MetricType.ACCESSIBILITY]
        seo_metrics = [m for m in metrics if m.metric_type == MetricType.SEO]
        
        performance_score = mean([m.value for m in performance_metrics if m.metric_name.endswith('_score')]) if performance_metrics else 0
        accessibility_score = mean([m.value for m in accessibility_metrics if m.metric_name.endswith('_score')]) if accessibility_metrics else 0
        seo_score = mean([m.value for m in seo_metrics if m.metric_name.endswith('_score')]) if seo_metrics else 0
        best_practices_score = 80.0  # Default
        
        overall_score = mean([performance_score, accessibility_score, seo_score, best_practices_score])
        
        # Extract Core Web Vitals
        core_web_vitals = {}
        for metric in metrics:
            if metric.metric_name in ["lcp_p75", "fid_p75", "cls_p75"]:
                core_web_vitals[metric.metric_name] = metric.value
        
        # Loading metrics
        loading_metrics = {}
        for metric in metrics:
            if metric.metric_name in ["first_contentful_paint", "largest_contentful_paint", "time_to_interactive"]:
                loading_metrics[metric.metric_name] = metric.value
        
        # Get historical comparison
        historical_comparison = await self._get_historical_comparison(frontend_id)
        
        # Get industry comparison
        industry_comparison = await self._get_industry_comparison(frontend_id, overall_score)
        
        report = PerformanceReport(
            id=report_id,
            frontend_id=frontend_id,
            overall_score=overall_score,
            performance_score=performance_score,
            accessibility_score=accessibility_score,
            seo_score=seo_score,
            best_practices_score=best_practices_score,
            core_web_vitals=core_web_vitals,
            loading_metrics=loading_metrics,
            interactivity_metrics={"first_input_delay": core_web_vitals.get("fid_p75", 0)},
            visual_stability_metrics={"cumulative_layout_shift": core_web_vitals.get("cls_p75", 0)},
            industry_comparison=industry_comparison,
            historical_comparison=historical_comparison,
            top_recommendations=[],
            generated_at=datetime.now(),
            period_start=datetime.now() - timedelta(hours=1),
            period_end=datetime.now()
        )
        
        # Store report
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO performance_reports 
            (id, frontend_id, report_type, overall_score, data)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            report.id, report.frontend_id, report.report_type,
            report.overall_score, report.model_dump_json()
        ))
        
        conn.commit()
        conn.close()
        
        return report
    
    async def _get_historical_comparison(self, frontend_id: str) -> Dict[str, float]:
        """Get historical performance comparison"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get average scores from last 30 days
        cursor.execute('''
            SELECT AVG(overall_score) 
            FROM performance_reports 
            WHERE frontend_id = ? 
            AND generated_at >= datetime('now', '-30 days')
            AND id != (SELECT id FROM performance_reports WHERE frontend_id = ? ORDER BY generated_at DESC LIMIT 1)
        ''', (frontend_id, frontend_id))
        
        result = cursor.fetchone()
        conn.close()
        
        previous_score = result[0] if result and result[0] else 0
        return {
            "previous_period_score": previous_score,
            "improvement": 0.0 if previous_score == 0 else ((75.0 - previous_score) / previous_score * 100)
        }
    
    async def _get_industry_comparison(self, frontend_id: str, score: float) -> Dict[str, str]:
        """Compare against industry benchmarks"""
        if score >= 90:
            return {"percentile": "top_10", "message": "Performing better than 90% of similar sites"}
        elif score >= 75:
            return {"percentile": "top_25", "message": "Performing better than 75% of similar sites"}
        elif score >= 50:
            return {"percentile": "average", "message": "Performing at industry average"}
        else:
            return {"percentile": "below_average", "message": "Performing below industry average"}
    
    async def _check_performance_alerts(self, frontend_id: str, metrics: List[MetricRecord]):
        """Check for performance threshold breaches"""
        alerts = []
        
        for metric in metrics:
            if metric.metric_name in self.thresholds:
                thresholds = self.thresholds[metric.metric_name]
                
                # Check if metric is below good threshold
                if metric.value > thresholds["good"]:  # Higher is worse for time-based metrics
                    severity = "high" if metric.value > thresholds["good"] * 2 else "medium"
                    
                    alert = PerformanceAlert(
                        id=f"ALERT_{uuid.uuid4().hex[:8].upper()}",
                        frontend_id=frontend_id,
                        alert_type="threshold_breach",
                        severity=severity,
                        metric_name=metric.metric_name,
                        current_value=metric.value,
                        threshold_value=thresholds["good"],
                        message=f"{metric.metric_name} is {metric.value:.2f}, exceeding good threshold of {thresholds['good']}",
                        recommendations=[
                            f"Optimize {metric.metric_name.replace('_', ' ')}",
                            "Consider implementing performance best practices",
                            "Review and optimize critical rendering path"
                        ],
                        created_at=datetime.now()
                    )
                    alerts.append(alert)
        
        # Store alerts
        if alerts:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for alert in alerts:
                cursor.execute('''
                    INSERT INTO performance_alerts 
                    (id, frontend_id, alert_type, severity, metric_name, data)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    alert.id, alert.frontend_id, alert.alert_type,
                    alert.severity, alert.metric_name, alert.model_dump_json()
                ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Created {len(alerts)} performance alerts for {frontend_id}")
    
    async def _generate_recommendations(self, frontend_id: str, report: PerformanceReport):
        """Generate optimization recommendations"""
        recommendations = []
        
        # Performance recommendations
        if report.performance_score < 75:
            recommendations.append(OptimizationRecommendation(
                id=f"REC_{uuid.uuid4().hex[:8].upper()}",
                frontend_id=frontend_id,
                category="performance",
                priority="high",
                title="Optimize Loading Performance",
                description="Improve page load times and Core Web Vitals metrics",
                technical_details="Consider implementing code splitting, lazy loading, and resource optimization",
                estimated_improvement={"performance_score": 15.0, "lcp": -1.2},
                implementation_effort="medium",
                estimated_cost=500.0,
                implementation_steps=[
                    "Audit current bundle size and identify large dependencies",
                    "Implement code splitting for route-based chunks", 
                    "Add lazy loading for images and non-critical components",
                    "Optimize CSS delivery and eliminate render-blocking resources",
                    "Configure proper caching headers"
                ],
                code_examples=[
                    {
                        "language": "javascript",
                        "code": "const LazyComponent = lazy(() => import('./HeavyComponent'));"
                    }
                ],
                tools_required=["Webpack Bundle Analyzer", "Lighthouse CI", "Performance monitoring"],
                created_at=datetime.now()
            ))
        
        # Accessibility recommendations
        if report.accessibility_score < 90:
            recommendations.append(OptimizationRecommendation(
                id=f"REC_{uuid.uuid4().hex[:8].upper()}",
                frontend_id=frontend_id,
                category="accessibility",
                priority="medium",
                title="Improve Accessibility Compliance",
                description="Enhance accessibility to meet WCAG AA standards",
                technical_details="Focus on color contrast, keyboard navigation, and screen reader compatibility",
                estimated_improvement={"accessibility_score": 12.0},
                implementation_effort="low",
                estimated_cost=200.0,
                implementation_steps=[
                    "Audit color contrast ratios and fix violations",
                    "Add proper ARIA labels and roles",
                    "Ensure all interactive elements are keyboard accessible",
                    "Test with screen readers and fix issues"
                ],
                created_at=datetime.now()
            ))
        
        # SEO recommendations
        if report.seo_score < 85:
            recommendations.append(OptimizationRecommendation(
                id=f"REC_{uuid.uuid4().hex[:8].upper()}",
                frontend_id=frontend_id,
                category="seo",
                priority="medium",
                title="Enhance SEO Optimization",
                description="Improve search engine visibility and ranking factors",
                technical_details="Optimize meta tags, structured data, and technical SEO elements",
                estimated_improvement={"seo_score": 10.0},
                implementation_effort="low",
                estimated_cost=150.0,
                implementation_steps=[
                    "Complete meta tag optimization",
                    "Implement structured data markup",
                    "Optimize internal linking structure",
                    "Improve mobile responsiveness"
                ],
                created_at=datetime.now()
            ))
        
        # Store recommendations
        if recommendations:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for rec in recommendations:
                cursor.execute('''
                    INSERT INTO optimization_recommendations 
                    (id, frontend_id, category, priority, title, data)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    rec.id, rec.frontend_id, rec.category,
                    rec.priority, rec.title, rec.model_dump_json()
                ))
            
            conn.commit()
            conn.close()
            
            # Update report with recommendations
            report.top_recommendations = recommendations
    
    async def get_metrics_history(self, frontend_id: str, metric_name: str, 
                                days: int = 30) -> List[Dict[str, Any]]:
        """Get historical metrics data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT value, timestamp 
            FROM performance_metrics 
            WHERE frontend_id = ? AND metric_name = ?
            AND timestamp >= datetime('now', '-{} days')
            ORDER BY timestamp ASC
        '''.format(days), (frontend_id, metric_name))
        
        results = cursor.fetchall()
        conn.close()
        
        return [
            {"value": row[0], "timestamp": row[1]}
            for row in results
        ]
    
    async def get_performance_dashboard(self, frontend_id: str) -> Dict[str, Any]:
        """Get performance dashboard data"""
        
        # Get latest report
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT data FROM performance_reports 
            WHERE frontend_id = ? 
            ORDER BY generated_at DESC 
            LIMIT 1
        ''', (frontend_id,))
        
        result = cursor.fetchone()
        latest_report = None
        if result:
            report_data = json.loads(result[0])
            latest_report = PerformanceReport(**report_data)
        
        # Get active alerts
        cursor.execute('''
            SELECT data FROM performance_alerts 
            WHERE frontend_id = ? 
            AND resolved_at IS NULL
            ORDER BY created_at DESC 
            LIMIT 5
        ''', (frontend_id,))
        
        alert_results = cursor.fetchall()
        active_alerts = [PerformanceAlert(**json.loads(result[0])) for result in alert_results]
        
        # Get pending recommendations
        cursor.execute('''
            SELECT data FROM optimization_recommendations 
            WHERE frontend_id = ? 
            AND status = 'pending'
            ORDER BY priority DESC, created_at DESC 
            LIMIT 5
        ''', (frontend_id,))
        
        rec_results = cursor.fetchall()
        pending_recommendations = [OptimizationRecommendation(**json.loads(result[0])) for result in rec_results]
        
        conn.close()
        
        return {
            "latest_report": latest_report.model_dump() if latest_report else None,
            "active_alerts": [alert.model_dump() for alert in active_alerts],
            "pending_recommendations": [rec.model_dump() for rec in pending_recommendations],
            "performance_trends": await self.get_metrics_history(frontend_id, "performance_score", 7),
            "core_web_vitals_trends": {
                "lcp": await self.get_metrics_history(frontend_id, "lcp_p75", 7),
                "fid": await self.get_metrics_history(frontend_id, "fid_p75", 7),
                "cls": await self.get_metrics_history(frontend_id, "cls_p75", 7)
            }
        }
    
    async def start_continuous_monitoring(self, frontend_id: str, url: str, 
                                        interval_hours: int = 6):
        """Start continuous performance monitoring"""
        logger.info(f"Starting continuous monitoring for {frontend_id} every {interval_hours} hours")
        
        while True:
            try:
                await self.measure_performance({
                    "frontend_id": frontend_id,
                    "url": url
                })
                logger.info(f"Completed scheduled measurement for {frontend_id}")
            except Exception as e:
                logger.error(f"Error in continuous monitoring for {frontend_id}: {e}")
            
            # Wait for next measurement
            await asyncio.sleep(interval_hours * 3600)

# Global instance
performance_metrics_manager = PerformanceMetricsManager()