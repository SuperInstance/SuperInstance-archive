import numpy as np
import pandas as pd
import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, asdict
from enum import Enum
import statistics
import warnings
warnings.filterwarnings('ignore')


class DriftType(Enum):
    DATA_DRIFT = "data_drift"
    CONCEPT_DRIFT = "concept_drift"
    PREDICTION_DRIFT = "prediction_drift"
    TARGET_DRIFT = "target_drift"


class DriftSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class DriftAlert:
    alert_id: str
    model_id: str
    model_version: str
    drift_type: DriftType
    severity: DriftSeverity
    drift_score: float
    threshold: float
    feature_name: Optional[str] = None
    detected_at: datetime = None
    description: str = ""
    metadata: Dict[str, Any] = None


@dataclass
class DriftReport:
    model_id: str
    model_version: str
    drift_type: DriftType
    drift_scores: Dict[str, float]
    overall_drift_score: float
    threshold: float
    is_drifting: bool
    detected_features: List[str]
    analysis_period: str
    reference_period: str
    generated_at: datetime
    metadata: Dict[str, Any] = None


class StatisticalTests:
    @staticmethod
    def kolmogorov_smirnov_test(reference: np.ndarray, current: np.ndarray) -> Tuple[float, float]:
        """Two-sample Kolmogorov-Smirnov test"""
        try:
            from scipy import stats
            statistic, p_value = stats.ks_2samp(reference, current)
            return float(statistic), float(p_value)
        except ImportError:
            # Fallback implementation
            return StatisticalTests._ks_test_fallback(reference, current)
    
    @staticmethod
    def _ks_test_fallback(reference: np.ndarray, current: np.ndarray) -> Tuple[float, float]:
        """Simple KS test implementation without scipy"""
        ref_sorted = np.sort(reference)
        cur_sorted = np.sort(current)
        
        n1, n2 = len(ref_sorted), len(cur_sorted)
        
        # Create empirical distribution functions
        all_values = np.sort(np.concatenate([ref_sorted, cur_sorted]))
        
        cdf1 = np.searchsorted(ref_sorted, all_values, side='right') / n1
        cdf2 = np.searchsorted(cur_sorted, all_values, side='right') / n2
        
        ks_statistic = np.max(np.abs(cdf1 - cdf2))
        
        # Approximate p-value (simplified)
        c_alpha = 1.36  # for alpha=0.05
        critical_value = c_alpha * np.sqrt((n1 + n2) / (n1 * n2))
        p_value = 1.0 if ks_statistic < critical_value else 0.0
        
        return float(ks_statistic), float(p_value)
    
    @staticmethod
    def chi_square_test(reference: np.ndarray, current: np.ndarray, bins: int = 10) -> Tuple[float, float]:
        """Chi-square test for categorical or binned continuous data"""
        try:
            from scipy import stats
            
            # Create bins for continuous data
            if np.issubdtype(reference.dtype, np.number):
                min_val = min(np.min(reference), np.min(current))
                max_val = max(np.max(reference), np.max(current))
                bin_edges = np.linspace(min_val, max_val, bins + 1)
                
                ref_counts, _ = np.histogram(reference, bins=bin_edges)
                cur_counts, _ = np.histogram(current, bins=bin_edges)
            else:
                # Categorical data
                unique_values = np.unique(np.concatenate([reference, current]))
                ref_counts = np.array([np.sum(reference == val) for val in unique_values])
                cur_counts = np.array([np.sum(current == val) for val in unique_values])
            
            # Avoid zero expected frequencies
            ref_counts = np.maximum(ref_counts, 1)
            cur_counts = np.maximum(cur_counts, 1)
            
            statistic, p_value = stats.chisquare(cur_counts, ref_counts)
            return float(statistic), float(p_value)
        
        except ImportError:
            return StatisticalTests._chi_square_fallback(reference, current, bins)
    
    @staticmethod
    def _chi_square_fallback(reference: np.ndarray, current: np.ndarray, bins: int = 10) -> Tuple[float, float]:
        """Fallback chi-square implementation"""
        if np.issubdtype(reference.dtype, np.number):
            min_val = min(np.min(reference), np.min(current))
            max_val = max(np.max(reference), np.max(current))
            bin_edges = np.linspace(min_val, max_val, bins + 1)
            
            ref_counts, _ = np.histogram(reference, bins=bin_edges)
            cur_counts, _ = np.histogram(current, bins=bin_edges)
        else:
            unique_values = np.unique(np.concatenate([reference, current]))
            ref_counts = np.array([np.sum(reference == val) for val in unique_values])
            cur_counts = np.array([np.sum(current == val) for val in unique_values])
        
        ref_counts = np.maximum(ref_counts, 1)
        cur_counts = np.maximum(cur_counts, 1)
        
        chi_square = np.sum((cur_counts - ref_counts) ** 2 / ref_counts)
        # Simplified p-value (not accurate, but gives indication)
        p_value = 0.05 if chi_square > 15.5 else 0.5  # Very rough approximation
        
        return float(chi_square), float(p_value)
    
    @staticmethod
    def psi_score(reference: np.ndarray, current: np.ndarray, bins: int = 10) -> float:
        """Population Stability Index (PSI)"""
        try:
            # Handle both continuous and categorical data
            if np.issubdtype(reference.dtype, np.number):
                # Continuous data - use quantile-based bins
                quantiles = np.linspace(0, 1, bins + 1)
                bin_edges = np.quantile(reference, quantiles)
                bin_edges[-1] += 1e-8  # Avoid edge case with max value
                
                ref_counts, _ = np.histogram(reference, bins=bin_edges)
                cur_counts, _ = np.histogram(current, bins=bin_edges)
            else:
                # Categorical data
                unique_values = np.unique(np.concatenate([reference, current]))
                ref_counts = np.array([np.sum(reference == val) for val in unique_values])
                cur_counts = np.array([np.sum(current == val) for val in unique_values])
            
            # Convert to proportions
            ref_props = ref_counts / np.sum(ref_counts)
            cur_props = cur_counts / np.sum(cur_counts)
            
            # Add small epsilon to avoid log(0)
            epsilon = 1e-8
            ref_props = np.maximum(ref_props, epsilon)
            cur_props = np.maximum(cur_props, epsilon)
            
            # Calculate PSI
            psi = np.sum((cur_props - ref_props) * np.log(cur_props / ref_props))
            
            return float(psi)
        
        except Exception as e:
            print(f"Error calculating PSI: {e}")
            return 0.0
    
    @staticmethod
    def wasserstein_distance(reference: np.ndarray, current: np.ndarray) -> float:
        """Earth Mover's Distance (Wasserstein distance) for continuous distributions"""
        try:
            from scipy import stats
            distance = stats.wasserstein_distance(reference, current)
            return float(distance)
        except ImportError:
            return StatisticalTests._wasserstein_fallback(reference, current)
    
    @staticmethod
    def _wasserstein_fallback(reference: np.ndarray, current: np.ndarray) -> float:
        """Simple approximation of Wasserstein distance"""
        # Sort both arrays
        ref_sorted = np.sort(reference)
        cur_sorted = np.sort(current)
        
        # Interpolate to same length if different
        n = min(len(ref_sorted), len(cur_sorted))
        if len(ref_sorted) != len(cur_sorted):
            ref_interp = np.interp(np.linspace(0, 1, n), np.linspace(0, 1, len(ref_sorted)), ref_sorted)
            cur_interp = np.interp(np.linspace(0, 1, n), np.linspace(0, 1, len(cur_sorted)), cur_sorted)
        else:
            ref_interp, cur_interp = ref_sorted, cur_sorted
        
        # Calculate mean absolute difference
        distance = np.mean(np.abs(ref_interp - cur_interp))
        return float(distance)


class DataDriftDetector:
    def __init__(self, model_id: str, model_version: str, db_path: str = "ml_platform.db"):
        self.model_id = model_id
        self.model_version = model_version
        self.db_path = db_path
        self.reference_data = None
        self.feature_names = []
        self.thresholds = {
            "ks_test": 0.05,
            "chi_square": 0.05,
            "psi": 0.2,
            "wasserstein": None  # Will be set based on data
        }
        self._init_database()
    
    def _init_database(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS drift_reference_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_id TEXT NOT NULL,
                model_version TEXT NOT NULL,
                feature_name TEXT NOT NULL,
                data_values TEXT NOT NULL,
                statistics TEXT NOT NULL,
                created_at TEXT NOT NULL,
                INDEX (model_id, model_version)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS drift_detections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_id TEXT NOT NULL,
                model_version TEXT NOT NULL,
                drift_type TEXT NOT NULL,
                feature_name TEXT,
                drift_score REAL NOT NULL,
                threshold REAL NOT NULL,
                is_drifting BOOLEAN NOT NULL,
                detected_at TEXT NOT NULL,
                metadata TEXT,
                INDEX (model_id, model_version, detected_at)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS drift_alerts (
                alert_id TEXT PRIMARY KEY,
                model_id TEXT NOT NULL,
                model_version TEXT NOT NULL,
                drift_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                drift_score REAL NOT NULL,
                threshold REAL NOT NULL,
                feature_name TEXT,
                detected_at TEXT NOT NULL,
                description TEXT,
                metadata TEXT,
                resolved BOOLEAN DEFAULT FALSE
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def set_reference_data(self, X: np.ndarray, feature_names: List[str], 
                          save_to_db: bool = True) -> bool:
        """Set reference data for drift detection"""
        try:
            self.reference_data = X.copy()
            self.feature_names = feature_names.copy()
            
            # Calculate reference statistics
            self._calculate_reference_statistics()
            
            if save_to_db:
                self._save_reference_data()
            
            return True
        
        except Exception as e:
            print(f"Error setting reference data: {e}")
            return False
    
    def _calculate_reference_statistics(self):
        """Calculate statistics for reference data"""
        self.reference_stats = {}
        
        for i, feature_name in enumerate(self.feature_names):
            feature_data = self.reference_data[:, i]
            
            stats = {
                "mean": float(np.mean(feature_data)),
                "std": float(np.std(feature_data)),
                "min": float(np.min(feature_data)),
                "max": float(np.max(feature_data)),
                "median": float(np.median(feature_data)),
                "q25": float(np.percentile(feature_data, 25)),
                "q75": float(np.percentile(feature_data, 75))
            }
            
            # Set adaptive Wasserstein threshold based on data scale
            data_range = stats["max"] - stats["min"]
            self.thresholds["wasserstein"] = data_range * 0.1  # 10% of data range
            
            self.reference_stats[feature_name] = stats
    
    def _save_reference_data(self):
        """Save reference data to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for i, feature_name in enumerate(self.feature_names):
            feature_data = self.reference_data[:, i]
            
            cursor.execute('''
                INSERT OR REPLACE INTO drift_reference_data 
                (model_id, model_version, feature_name, data_values, statistics, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                self.model_id,
                self.model_version,
                feature_name,
                json.dumps(feature_data.tolist()),
                json.dumps(self.reference_stats[feature_name]),
                datetime.now().isoformat()
            ))
        
        conn.commit()
        conn.close()
    
    def detect_data_drift(self, X_current: np.ndarray, 
                         methods: List[str] = None) -> DriftReport:
        """Detect data drift between reference and current data"""
        if self.reference_data is None:
            raise ValueError("Reference data not set. Call set_reference_data() first.")
        
        if methods is None:
            methods = ["ks_test", "psi", "wasserstein"]
        
        drift_scores = {}
        detected_features = []
        
        for i, feature_name in enumerate(self.feature_names):
            if i >= X_current.shape[1]:
                continue
                
            reference_feature = self.reference_data[:, i]
            current_feature = X_current[:, i]
            
            feature_drift_scores = {}
            
            # Kolmogorov-Smirnov test
            if "ks_test" in methods:
                ks_stat, ks_p = StatisticalTests.kolmogorov_smirnov_test(
                    reference_feature, current_feature
                )
                feature_drift_scores["ks_statistic"] = ks_stat
                feature_drift_scores["ks_p_value"] = ks_p
                
                if ks_p < self.thresholds["ks_test"]:
                    detected_features.append(feature_name)
            
            # Chi-square test
            if "chi_square" in methods:
                chi2_stat, chi2_p = StatisticalTests.chi_square_test(
                    reference_feature, current_feature
                )
                feature_drift_scores["chi2_statistic"] = chi2_stat
                feature_drift_scores["chi2_p_value"] = chi2_p
            
            # PSI score
            if "psi" in methods:
                psi_score = StatisticalTests.psi_score(reference_feature, current_feature)
                feature_drift_scores["psi_score"] = psi_score
                
                if psi_score > self.thresholds["psi"]:
                    if feature_name not in detected_features:
                        detected_features.append(feature_name)
            
            # Wasserstein distance
            if "wasserstein" in methods:
                wasserstein_dist = StatisticalTests.wasserstein_distance(
                    reference_feature, current_feature
                )
                feature_drift_scores["wasserstein_distance"] = wasserstein_dist
                
                if (self.thresholds["wasserstein"] and 
                    wasserstein_dist > self.thresholds["wasserstein"]):
                    if feature_name not in detected_features:
                        detected_features.append(feature_name)
            
            drift_scores[feature_name] = feature_drift_scores
        
        # Calculate overall drift score
        all_psi_scores = [scores.get("psi_score", 0) for scores in drift_scores.values()]
        overall_drift_score = np.mean(all_psi_scores) if all_psi_scores else 0.0
        
        is_drifting = len(detected_features) > 0
        
        report = DriftReport(
            model_id=self.model_id,
            model_version=self.model_version,
            drift_type=DriftType.DATA_DRIFT,
            drift_scores=drift_scores,
            overall_drift_score=overall_drift_score,
            threshold=self.thresholds["psi"],
            is_drifting=is_drifting,
            detected_features=detected_features,
            analysis_period="current",
            reference_period="baseline",
            generated_at=datetime.now()
        )
        
        # Store detection results
        self._store_drift_detection(report)
        
        # Generate alerts if needed
        if is_drifting:
            self._generate_drift_alerts(report)
        
        return report
    
    def _store_drift_detection(self, report: DriftReport):
        """Store drift detection results in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for feature_name, scores in report.drift_scores.items():
            for metric, score in scores.items():
                cursor.execute('''
                    INSERT INTO drift_detections 
                    (model_id, model_version, drift_type, feature_name, drift_score,
                     threshold, is_drifting, detected_at, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    report.model_id,
                    report.model_version,
                    report.drift_type.value,
                    feature_name,
                    score,
                    report.threshold,
                    feature_name in report.detected_features,
                    report.generated_at.isoformat(),
                    json.dumps({
                        "metric": metric,
                        "overall_drift_score": report.overall_drift_score
                    })
                ))
        
        conn.commit()
        conn.close()
    
    def _generate_drift_alerts(self, report: DriftReport):
        """Generate drift alerts for drifting features"""
        for feature_name in report.detected_features:
            feature_scores = report.drift_scores.get(feature_name, {})
            max_score = max([score for score in feature_scores.values() 
                           if isinstance(score, (int, float))], default=0)
            
            # Determine severity
            if max_score > 0.5:
                severity = DriftSeverity.CRITICAL
            elif max_score > 0.3:
                severity = DriftSeverity.HIGH
            elif max_score > 0.15:
                severity = DriftSeverity.MEDIUM
            else:
                severity = DriftSeverity.LOW
            
            alert = DriftAlert(
                alert_id=f"drift_{self.model_id}_{feature_name}_{int(datetime.now().timestamp())}",
                model_id=self.model_id,
                model_version=self.model_version,
                drift_type=DriftType.DATA_DRIFT,
                severity=severity,
                drift_score=max_score,
                threshold=report.threshold,
                feature_name=feature_name,
                detected_at=datetime.now(),
                description=f"Data drift detected in feature '{feature_name}' with score {max_score:.3f}",
                metadata={"drift_scores": feature_scores}
            )
            
            self._store_drift_alert(alert)
    
    def _store_drift_alert(self, alert: DriftAlert):
        """Store drift alert in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO drift_alerts 
            (alert_id, model_id, model_version, drift_type, severity, drift_score,
             threshold, feature_name, detected_at, description, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            alert.alert_id,
            alert.model_id,
            alert.model_version,
            alert.drift_type.value,
            alert.severity.value,
            alert.drift_score,
            alert.threshold,
            alert.feature_name,
            alert.detected_at.isoformat(),
            alert.description,
            json.dumps(alert.metadata) if alert.metadata else None
        ))
        
        conn.commit()
        conn.close()


class ConceptDriftDetector:
    def __init__(self, model_id: str, model_version: str, db_path: str = "ml_platform.db"):
        self.model_id = model_id
        self.model_version = model_version
        self.db_path = db_path
        self.reference_performance = None
        self.performance_threshold = 0.05  # 5% degradation threshold
    
    def set_reference_performance(self, performance_metrics: Dict[str, float]):
        """Set baseline performance metrics"""
        self.reference_performance = performance_metrics.copy()
    
    def detect_concept_drift(self, current_metrics: Dict[str, float]) -> DriftReport:
        """Detect concept drift based on performance degradation"""
        if self.reference_performance is None:
            raise ValueError("Reference performance not set.")
        
        drift_scores = {}
        detected_metrics = []
        
        for metric_name in self.reference_performance.keys():
            if metric_name in current_metrics:
                ref_value = self.reference_performance[metric_name]
                curr_value = current_metrics[metric_name]
                
                # Calculate relative change
                if ref_value != 0:
                    relative_change = abs((curr_value - ref_value) / ref_value)
                else:
                    relative_change = abs(curr_value)
                
                drift_scores[metric_name] = {
                    "reference_value": ref_value,
                    "current_value": curr_value,
                    "relative_change": relative_change,
                    "absolute_change": abs(curr_value - ref_value)
                }
                
                if relative_change > self.performance_threshold:
                    detected_metrics.append(metric_name)
        
        overall_drift_score = np.mean([scores["relative_change"] 
                                     for scores in drift_scores.values()])
        
        report = DriftReport(
            model_id=self.model_id,
            model_version=self.model_version,
            drift_type=DriftType.CONCEPT_DRIFT,
            drift_scores=drift_scores,
            overall_drift_score=overall_drift_score,
            threshold=self.performance_threshold,
            is_drifting=len(detected_metrics) > 0,
            detected_features=detected_metrics,
            analysis_period="current",
            reference_period="baseline",
            generated_at=datetime.now()
        )
        
        return report


class DriftMonitor:
    def __init__(self, db_path: str = "ml_platform.db"):
        self.db_path = db_path
        self.detectors = {}
    
    def register_model(self, model_id: str, model_version: str,
                      reference_data: np.ndarray, feature_names: List[str],
                      reference_performance: Optional[Dict[str, float]] = None):
        """Register a model for drift monitoring"""
        
        # Data drift detector
        data_detector = DataDriftDetector(model_id, model_version, self.db_path)
        data_detector.set_reference_data(reference_data, feature_names)
        
        # Concept drift detector
        concept_detector = ConceptDriftDetector(model_id, model_version, self.db_path)
        if reference_performance:
            concept_detector.set_reference_performance(reference_performance)
        
        key = f"{model_id}:{model_version}"
        self.detectors[key] = {
            "data_detector": data_detector,
            "concept_detector": concept_detector
        }
    
    def check_drift(self, model_id: str, model_version: str,
                   current_data: Optional[np.ndarray] = None,
                   current_performance: Optional[Dict[str, float]] = None) -> Dict[str, DriftReport]:
        """Check for all types of drift"""
        key = f"{model_id}:{model_version}"
        
        if key not in self.detectors:
            raise ValueError(f"Model {key} not registered for drift monitoring")
        
        results = {}
        
        # Data drift
        if current_data is not None:
            data_detector = self.detectors[key]["data_detector"]
            data_drift_report = data_detector.detect_data_drift(current_data)
            results["data_drift"] = data_drift_report
        
        # Concept drift
        if current_performance is not None:
            concept_detector = self.detectors[key]["concept_detector"]
            concept_drift_report = concept_detector.detect_concept_drift(current_performance)
            results["concept_drift"] = concept_drift_report
        
        return results
    
    def get_drift_history(self, model_id: str, model_version: str,
                         drift_type: Optional[DriftType] = None,
                         days: int = 30) -> List[Dict[str, Any]]:
        """Get drift detection history"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        start_time = datetime.now() - timedelta(days=days)
        
        query = '''
            SELECT drift_type, feature_name, drift_score, threshold, 
                   is_drifting, detected_at, metadata
            FROM drift_detections 
            WHERE model_id = ? AND model_version = ? AND detected_at >= ?
        '''
        params = [model_id, model_version, start_time.isoformat()]
        
        if drift_type:
            query += " AND drift_type = ?"
            params.append(drift_type.value)
        
        query += " ORDER BY detected_at DESC"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        history = []
        for row in rows:
            history.append({
                "drift_type": row[0],
                "feature_name": row[1],
                "drift_score": row[2],
                "threshold": row[3],
                "is_drifting": bool(row[4]),
                "detected_at": row[5],
                "metadata": json.loads(row[6]) if row[6] else {}
            })
        
        return history
    
    def get_active_alerts(self, model_id: Optional[str] = None,
                         severity: Optional[DriftSeverity] = None) -> List[DriftAlert]:
        """Get active drift alerts"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = "SELECT * FROM drift_alerts WHERE resolved = FALSE"
        params = []
        
        if model_id:
            query += " AND model_id = ?"
            params.append(model_id)
        
        if severity:
            query += " AND severity = ?"
            params.append(severity.value)
        
        query += " ORDER BY detected_at DESC"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        alerts = []
        for row in rows:
            alert = DriftAlert(
                alert_id=row[0],
                model_id=row[1],
                model_version=row[2],
                drift_type=DriftType(row[3]),
                severity=DriftSeverity(row[4]),
                drift_score=row[5],
                threshold=row[6],
                feature_name=row[7],
                detected_at=datetime.fromisoformat(row[8]),
                description=row[9],
                metadata=json.loads(row[10]) if row[10] else None
            )
            alerts.append(alert)
        
        return alerts


# Usage example
if __name__ == "__main__":
    # Create sample data
    np.random.seed(42)
    
    # Reference data
    X_ref = np.random.normal(0, 1, (1000, 5))
    feature_names = [f"feature_{i}" for i in range(5)]
    
    # Current data with drift in feature 0
    X_current = X_ref.copy()
    X_current[:, 0] += 2  # Add drift to feature 0
    
    # Initialize drift monitor
    monitor = DriftMonitor()
    
    # Register model
    reference_performance = {"accuracy": 0.85, "precision": 0.82}
    monitor.register_model("test_model", "1.0", X_ref, feature_names, reference_performance)
    
    # Check for drift
    current_performance = {"accuracy": 0.78, "precision": 0.75}  # Performance degraded
    
    drift_results = monitor.check_drift(
        "test_model", "1.0",
        current_data=X_current,
        current_performance=current_performance
    )
    
    print("Drift Detection Results:")
    for drift_type, report in drift_results.items():
        print(f"\n{drift_type.upper()}:")
        print(f"  Overall drift score: {report.overall_drift_score:.3f}")
        print(f"  Is drifting: {report.is_drifting}")
        print(f"  Detected features: {report.detected_features}")
    
    # Get active alerts
    alerts = monitor.get_active_alerts("test_model")
    print(f"\nActive alerts: {len(alerts)}")
    for alert in alerts:
        print(f"  {alert.severity.value}: {alert.description}")