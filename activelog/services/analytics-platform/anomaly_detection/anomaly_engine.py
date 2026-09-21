"""
Anomaly Detection Engine
Advanced anomaly detection using multiple algorithms
"""

import asyncio
import logging
import warnings
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import pandas as pd
import numpy as np
from scipy import stats
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

# Anomaly detection libraries
from pyod.models.iforest import IForest
from pyod.models.lof import LOF
from pyod.models.ocsvm import OCSVM
from pyod.models.knn import KNN
from pyod.models.pca import PCA
from pyod.models.auto_encoder import AutoEncoder
from sklearn.ensemble import IsolationForest
from sklearn.svm import OneClassSVM
from sklearn.preprocessing import StandardScaler, RobustScaler
from sklearn.decomposition import PCA as SklearnPCA
from sklearn.cluster import DBSCAN
from sklearn.metrics import classification_report, confusion_matrix
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, LSTM, Dropout
import torch
import torch.nn as nn

warnings.filterwarnings('ignore')
logger = logging.getLogger(__name__)

class AnomalyMethod(str, Enum):
    ISOLATION_FOREST = "isolation_forest"
    ONE_CLASS_SVM = "one_class_svm"
    LOCAL_OUTLIER_FACTOR = "lof"
    DBSCAN = "dbscan"
    PCA_BASED = "pca"
    AUTOENCODER = "autoencoder"
    LSTM_AUTOENCODER = "lstm_autoencoder"
    STATISTICAL = "statistical"
    ENSEMBLE = "ensemble"

class AnomalyType(str, Enum):
    POINT = "point"
    CONTEXTUAL = "contextual"
    COLLECTIVE = "collective"
    SEASONAL = "seasonal"

@dataclass
class AnomalyConfig:
    method: AnomalyMethod
    contamination: float = 0.1  # Expected fraction of anomalies
    parameters: Dict[str, Any] = field(default_factory=dict)
    preprocessing: Dict[str, Any] = field(default_factory=dict)
    detection_type: AnomalyType = AnomalyType.POINT
    time_window: Optional[int] = None  # For time series anomalies
    seasonal_period: Optional[int] = None  # For seasonal anomalies

@dataclass
class AnomalyResult:
    method_name: str
    anomalies: pd.DataFrame  # Contains original data + anomaly scores + labels
    anomaly_scores: np.ndarray
    anomaly_labels: np.ndarray  # 1 for anomaly, 0 for normal
    threshold: float
    statistics: Dict[str, Any]
    parameters: Dict[str, Any]
    execution_time: float
    model_info: Optional[Dict[str, Any]] = None

class StatisticalAnomalyDetector:
    """Statistical methods for anomaly detection"""
    
    @staticmethod
    async def detect_zscore_anomalies(data: pd.Series, threshold: float = 3.0) -> Dict[str, Any]:
        """Z-score based anomaly detection"""
        z_scores = np.abs(stats.zscore(data.dropna()))
        anomalies = z_scores > threshold
        
        return {
            'anomaly_scores': z_scores,
            'anomaly_labels': anomalies.astype(int),
            'threshold': threshold,
            'num_anomalies': np.sum(anomalies)
        }
    
    @staticmethod
    async def detect_modified_zscore_anomalies(data: pd.Series, threshold: float = 3.5) -> Dict[str, Any]:
        """Modified Z-score based anomaly detection (more robust)"""
        median = np.median(data.dropna())
        mad = np.median(np.abs(data.dropna() - median))
        modified_z_scores = 0.6745 * (data - median) / mad
        anomalies = np.abs(modified_z_scores) > threshold
        
        return {
            'anomaly_scores': np.abs(modified_z_scores),
            'anomaly_labels': anomalies.astype(int),
            'threshold': threshold,
            'num_anomalies': np.sum(anomalies)
        }
    
    @staticmethod
    async def detect_iqr_anomalies(data: pd.Series, k: float = 1.5) -> Dict[str, Any]:
        """IQR (Interquartile Range) based anomaly detection"""
        Q1 = data.quantile(0.25)
        Q3 = data.quantile(0.75)
        IQR = Q3 - Q1
        
        lower_bound = Q1 - k * IQR
        upper_bound = Q3 + k * IQR
        
        anomalies = (data < lower_bound) | (data > upper_bound)
        anomaly_scores = np.where(
            data < lower_bound,
            (lower_bound - data) / IQR,
            np.where(
                data > upper_bound,
                (data - upper_bound) / IQR,
                0
            )
        )
        
        return {
            'anomaly_scores': anomaly_scores,
            'anomaly_labels': anomalies.astype(int),
            'threshold': k,
            'bounds': {'lower': lower_bound, 'upper': upper_bound},
            'num_anomalies': np.sum(anomalies)
        }
    
    @staticmethod
    async def detect_seasonal_anomalies(data: pd.Series, seasonal_period: int, 
                                      method: str = 'stl') -> Dict[str, Any]:
        """Seasonal anomaly detection"""
        from statsmodels.tsa.seasonal import STL
        
        if len(data) < 2 * seasonal_period:
            raise ValueError("Insufficient data for seasonal decomposition")
        
        # STL decomposition
        stl = STL(data.dropna(), seasonal=seasonal_period)
        decomposition = stl.fit()
        
        # Anomalies based on residuals
        residuals = decomposition.resid
        residual_std = np.std(residuals)
        threshold = 2.5 * residual_std
        
        anomalies = np.abs(residuals) > threshold
        anomaly_scores = np.abs(residuals) / residual_std
        
        return {
            'anomaly_scores': anomaly_scores,
            'anomaly_labels': anomalies.astype(int),
            'threshold': threshold,
            'decomposition': {
                'trend': decomposition.trend,
                'seasonal': decomposition.seasonal,
                'residual': residuals
            },
            'num_anomalies': np.sum(anomalies)
        }

class MLAnomalyDetector:
    """Machine learning based anomaly detection"""
    
    def __init__(self):
        self.scaler = StandardScaler()
        self.models = {}
    
    async def detect_isolation_forest(self, data: np.ndarray, config: AnomalyConfig) -> Dict[str, Any]:
        """Isolation Forest anomaly detection"""
        params = config.parameters.copy()
        params.setdefault('contamination', config.contamination)
        params.setdefault('random_state', 42)
        params.setdefault('n_estimators', 100)
        
        # Fit model
        model = IForest(**params)
        model.fit(data)
        
        # Predict anomalies
        anomaly_labels = model.predict(data)  # 1 for inlier, -1 for outlier
        anomaly_scores = model.decision_function(data)
        
        # Convert to standard format (1 for anomaly, 0 for normal)
        anomaly_labels_binary = (anomaly_labels == -1).astype(int)
        
        # Normalize scores to [0, 1]
        anomaly_scores_norm = (anomaly_scores - anomaly_scores.min()) / (anomaly_scores.max() - anomaly_scores.min())
        
        return {
            'model': model,
            'anomaly_scores': 1 - anomaly_scores_norm,  # Higher score = more anomalous
            'anomaly_labels': anomaly_labels_binary,
            'threshold': model.threshold_,
            'num_anomalies': np.sum(anomaly_labels_binary)
        }
    
    async def detect_one_class_svm(self, data: np.ndarray, config: AnomalyConfig) -> Dict[str, Any]:
        """One-Class SVM anomaly detection"""
        params = config.parameters.copy()
        params.setdefault('nu', config.contamination)
        params.setdefault('kernel', 'rbf')
        params.setdefault('gamma', 'scale')
        
        # Fit model
        model = OCSVM(**params)
        model.fit(data)
        
        # Predict anomalies
        anomaly_labels = model.predict(data)
        anomaly_scores = model.decision_function(data)
        
        # Convert to standard format
        anomaly_labels_binary = (anomaly_labels == -1).astype(int)
        anomaly_scores_norm = (anomaly_scores - anomaly_scores.min()) / (anomaly_scores.max() - anomaly_scores.min())
        
        return {
            'model': model,
            'anomaly_scores': 1 - anomaly_scores_norm,
            'anomaly_labels': anomaly_labels_binary,
            'num_anomalies': np.sum(anomaly_labels_binary)
        }
    
    async def detect_local_outlier_factor(self, data: np.ndarray, config: AnomalyConfig) -> Dict[str, Any]:
        """Local Outlier Factor anomaly detection"""
        params = config.parameters.copy()
        params.setdefault('contamination', config.contamination)
        params.setdefault('n_neighbors', 20)
        
        # Fit model
        model = LOF(**params)
        model.fit(data)
        
        # Predict anomalies
        anomaly_labels = model.predict(data)
        anomaly_scores = model.decision_function(data)
        
        # Convert to standard format
        anomaly_labels_binary = (anomaly_labels == 1).astype(int)  # LOF uses 1 for outlier
        anomaly_scores_norm = (anomaly_scores - anomaly_scores.min()) / (anomaly_scores.max() - anomaly_scores.min())
        
        return {
            'model': model,
            'anomaly_scores': anomaly_scores_norm,
            'anomaly_labels': anomaly_labels_binary,
            'num_anomalies': np.sum(anomaly_labels_binary)
        }
    
    async def detect_dbscan_anomalies(self, data: np.ndarray, config: AnomalyConfig) -> Dict[str, Any]:
        """DBSCAN clustering for anomaly detection"""
        params = config.parameters.copy()
        params.setdefault('eps', 0.5)
        params.setdefault('min_samples', 5)
        
        # Fit DBSCAN
        model = DBSCAN(**params)
        cluster_labels = model.fit_predict(data)
        
        # Points with label -1 are anomalies
        anomaly_labels = (cluster_labels == -1).astype(int)
        
        # Calculate anomaly scores based on distance to nearest cluster
        anomaly_scores = np.zeros(len(data))
        for i, point in enumerate(data):
            if cluster_labels[i] == -1:  # Anomaly
                # Find distance to nearest core point
                core_points = data[model.core_sample_indices_]
                if len(core_points) > 0:
                    distances = np.linalg.norm(point - core_points, axis=1)
                    anomaly_scores[i] = np.min(distances)
                else:
                    anomaly_scores[i] = 1.0
        
        # Normalize scores
        if anomaly_scores.max() > 0:
            anomaly_scores = anomaly_scores / anomaly_scores.max()
        
        return {
            'model': model,
            'anomaly_scores': anomaly_scores,
            'anomaly_labels': anomaly_labels,
            'cluster_labels': cluster_labels,
            'num_clusters': len(set(cluster_labels)) - (1 if -1 in cluster_labels else 0),
            'num_anomalies': np.sum(anomaly_labels)
        }
    
    async def detect_pca_anomalies(self, data: np.ndarray, config: AnomalyConfig) -> Dict[str, Any]:
        """PCA-based anomaly detection"""
        params = config.parameters.copy()
        params.setdefault('contamination', config.contamination)
        params.setdefault('n_components', min(5, data.shape[1]))
        
        # Fit PCA model
        model = PCA(**params)
        model.fit(data)
        
        # Predict anomalies
        anomaly_labels = model.predict(data)
        anomaly_scores = model.decision_function(data)
        
        # Convert to standard format
        anomaly_labels_binary = (anomaly_labels == 1).astype(int)
        anomaly_scores_norm = (anomaly_scores - anomaly_scores.min()) / (anomaly_scores.max() - anomaly_scores.min())
        
        return {
            'model': model,
            'anomaly_scores': anomaly_scores_norm,
            'anomaly_labels': anomaly_labels_binary,
            'num_anomalies': np.sum(anomaly_labels_binary)
        }

class DeepLearningAnomalyDetector:
    """Deep learning based anomaly detection"""
    
    async def detect_autoencoder_anomalies(self, data: np.ndarray, config: AnomalyConfig) -> Dict[str, Any]:
        """Autoencoder anomaly detection"""
        params = config.parameters.copy()
        
        # Model parameters
        hidden_neurons = params.get('hidden_neurons', [64, 32, 16, 32, 64])
        epochs = params.get('epochs', 100)
        batch_size = params.get('batch_size', 32)
        contamination = config.contamination
        
        # Build autoencoder
        input_dim = data.shape[1]
        
        model = Sequential()
        
        # Encoder
        model.add(Dense(hidden_neurons[0], activation='relu', input_shape=(input_dim,)))
        for neurons in hidden_neurons[1:len(hidden_neurons)//2]:
            model.add(Dense(neurons, activation='relu'))
            model.add(Dropout(0.2))
        
        # Bottleneck
        bottleneck_dim = hidden_neurons[len(hidden_neurons)//2]
        model.add(Dense(bottleneck_dim, activation='relu'))
        
        # Decoder
        for neurons in hidden_neurons[len(hidden_neurons)//2 + 1:]:
            model.add(Dense(neurons, activation='relu'))
            model.add(Dropout(0.2))
        
        model.add(Dense(input_dim, activation='linear'))
        
        # Compile model
        model.compile(optimizer='adam', loss='mse')
        
        # Train model
        history = model.fit(
            data, data,
            epochs=epochs,
            batch_size=batch_size,
            shuffle=True,
            validation_split=0.2,
            verbose=0
        )
        
        # Calculate reconstruction errors
        reconstructed = model.predict(data, verbose=0)
        reconstruction_errors = np.mean(np.square(data - reconstructed), axis=1)
        
        # Determine threshold
        threshold = np.percentile(reconstruction_errors, (1 - contamination) * 100)
        
        # Identify anomalies
        anomaly_labels = (reconstruction_errors > threshold).astype(int)
        anomaly_scores = (reconstruction_errors - reconstruction_errors.min()) / (reconstruction_errors.max() - reconstruction_errors.min())
        
        return {
            'model': model,
            'anomaly_scores': anomaly_scores,
            'anomaly_labels': anomaly_labels,
            'threshold': threshold,
            'reconstruction_errors': reconstruction_errors,
            'training_history': history.history,
            'num_anomalies': np.sum(anomaly_labels)
        }
    
    async def detect_lstm_autoencoder_anomalies(self, data: np.ndarray, config: AnomalyConfig) -> Dict[str, Any]:
        """LSTM Autoencoder for time series anomaly detection"""
        params = config.parameters.copy()
        
        # Model parameters
        sequence_length = params.get('sequence_length', 10)
        lstm_units = params.get('lstm_units', 50)
        epochs = params.get('epochs', 100)
        batch_size = params.get('batch_size', 32)
        contamination = config.contamination
        
        # Prepare sequences
        def create_sequences(data, seq_length):
            sequences = []
            for i in range(len(data) - seq_length + 1):
                sequences.append(data[i:i + seq_length])
            return np.array(sequences)
        
        sequences = create_sequences(data.flatten(), sequence_length)
        
        # Build LSTM autoencoder
        model = Sequential()
        
        # Encoder
        model.add(LSTM(lstm_units, activation='relu', input_shape=(sequence_length, 1), return_sequences=True))
        model.add(LSTM(int(lstm_units/2), activation='relu', return_sequences=False))
        model.add(Dropout(0.2))
        model.add(Dense(int(lstm_units/4), activation='relu'))
        
        # Decoder
        model.add(Dense(int(lstm_units/2), activation='relu'))
        model.add(Dropout(0.2))
        model.add(Dense(lstm_units, activation='relu'))
        model.add(Dense(sequence_length, activation='linear'))
        
        model.compile(optimizer='adam', loss='mse')
        
        # Reshape for LSTM
        X_train = sequences.reshape(sequences.shape[0], sequence_length, 1)
        y_train = sequences
        
        # Train model
        history = model.fit(
            X_train, y_train,
            epochs=epochs,
            batch_size=batch_size,
            validation_split=0.2,
            verbose=0
        )
        
        # Calculate reconstruction errors
        predictions = model.predict(X_train, verbose=0)
        reconstruction_errors = np.mean(np.square(y_train - predictions), axis=1)
        
        # Extend errors to match original data length
        extended_errors = np.zeros(len(data.flatten()))
        for i, error in enumerate(reconstruction_errors):
            extended_errors[i:i + sequence_length] += error / sequence_length
        
        # Determine threshold
        threshold = np.percentile(extended_errors, (1 - contamination) * 100)
        
        # Identify anomalies
        anomaly_labels = (extended_errors > threshold).astype(int)
        anomaly_scores = (extended_errors - extended_errors.min()) / (extended_errors.max() - extended_errors.min())
        
        return {
            'model': model,
            'anomaly_scores': anomaly_scores,
            'anomaly_labels': anomaly_labels,
            'threshold': threshold,
            'reconstruction_errors': extended_errors,
            'training_history': history.history,
            'num_anomalies': np.sum(anomaly_labels)
        }

class EnsembleAnomalyDetector:
    """Ensemble anomaly detection using multiple methods"""
    
    def __init__(self):
        self.ml_detector = MLAnomalyDetector()
        self.dl_detector = DeepLearningAnomalyDetector()
        self.statistical_detector = StatisticalAnomalyDetector()
    
    async def detect_ensemble_anomalies(self, data: np.ndarray, configs: List[AnomalyConfig],
                                      voting_method: str = 'soft') -> Dict[str, Any]:
        """Ensemble anomaly detection"""
        individual_results = []
        
        # Run each detector
        for config in configs:
            try:
                if config.method == AnomalyMethod.ISOLATION_FOREST:
                    result = await self.ml_detector.detect_isolation_forest(data, config)
                elif config.method == AnomalyMethod.ONE_CLASS_SVM:
                    result = await self.ml_detector.detect_one_class_svm(data, config)
                elif config.method == AnomalyMethod.LOCAL_OUTLIER_FACTOR:
                    result = await self.ml_detector.detect_local_outlier_factor(data, config)
                elif config.method == AnomalyMethod.AUTOENCODER:
                    result = await self.dl_detector.detect_autoencoder_anomalies(data, config)
                else:
                    continue
                
                individual_results.append({
                    'method': config.method,
                    'scores': result['anomaly_scores'],
                    'labels': result['anomaly_labels'],
                    'result': result
                })
            except Exception as e:
                logger.warning(f"Method {config.method} failed: {e}")
                continue
        
        if not individual_results:
            raise ValueError("No successful detectors in ensemble")
        
        # Combine results
        if voting_method == 'soft':
            # Average anomaly scores
            ensemble_scores = np.mean([r['scores'] for r in individual_results], axis=0)
            
            # Determine threshold (average of individual thresholds)
            contamination = configs[0].contamination
            threshold = np.percentile(ensemble_scores, (1 - contamination) * 100)
            
            ensemble_labels = (ensemble_scores > threshold).astype(int)
            
        elif voting_method == 'hard':
            # Majority voting
            votes = np.array([r['labels'] for r in individual_results])
            ensemble_labels = (np.mean(votes, axis=0) > 0.5).astype(int)
            ensemble_scores = np.mean([r['scores'] for r in individual_results], axis=0)
            threshold = 0.5
        
        else:
            raise ValueError(f"Unknown voting method: {voting_method}")
        
        return {
            'ensemble_scores': ensemble_scores,
            'ensemble_labels': ensemble_labels,
            'threshold': threshold,
            'individual_results': individual_results,
            'voting_method': voting_method,
            'num_methods': len(individual_results),
            'num_anomalies': np.sum(ensemble_labels)
        }

class AnomalyDetectionEngine:
    """Main anomaly detection engine"""
    
    def __init__(self):
        self.statistical_detector = StatisticalAnomalyDetector()
        self.ml_detector = MLAnomalyDetector()
        self.dl_detector = DeepLearningAnomalyDetector()
        self.ensemble_detector = EnsembleAnomalyDetector()
        self.scaler = StandardScaler()
    
    async def detect_anomalies(self, data: pd.DataFrame, config: AnomalyConfig) -> AnomalyResult:
        """Main anomaly detection method"""
        start_time = datetime.utcnow()
        
        # Preprocess data
        processed_data = await self._preprocess_data(data, config)
        
        # Select detection method
        if config.method == AnomalyMethod.STATISTICAL:
            result = await self._detect_statistical_anomalies(processed_data, config)
        elif config.method == AnomalyMethod.ISOLATION_FOREST:
            result = await self.ml_detector.detect_isolation_forest(processed_data, config)
        elif config.method == AnomalyMethod.ONE_CLASS_SVM:
            result = await self.ml_detector.detect_one_class_svm(processed_data, config)
        elif config.method == AnomalyMethod.LOCAL_OUTLIER_FACTOR:
            result = await self.ml_detector.detect_local_outlier_factor(processed_data, config)
        elif config.method == AnomalyMethod.DBSCAN:
            result = await self.ml_detector.detect_dbscan_anomalies(processed_data, config)
        elif config.method == AnomalyMethod.PCA_BASED:
            result = await self.ml_detector.detect_pca_anomalies(processed_data, config)
        elif config.method == AnomalyMethod.AUTOENCODER:
            result = await self.dl_detector.detect_autoencoder_anomalies(processed_data, config)
        elif config.method == AnomalyMethod.LSTM_AUTOENCODER:
            result = await self.dl_detector.detect_lstm_autoencoder_anomalies(processed_data, config)
        else:
            raise ValueError(f"Unsupported detection method: {config.method}")
        
        # Calculate execution time
        execution_time = (datetime.utcnow() - start_time).total_seconds()
        
        # Create result dataframe
        anomaly_df = data.copy()
        anomaly_df['anomaly_score'] = result['anomaly_scores']
        anomaly_df['is_anomaly'] = result['anomaly_labels']
        
        # Calculate statistics
        statistics = {
            'total_points': len(data),
            'anomalies_detected': np.sum(result['anomaly_labels']),
            'anomaly_rate': np.mean(result['anomaly_labels']),
            'score_statistics': {
                'mean': np.mean(result['anomaly_scores']),
                'std': np.std(result['anomaly_scores']),
                'min': np.min(result['anomaly_scores']),
                'max': np.max(result['anomaly_scores']),
                'median': np.median(result['anomaly_scores'])
            }
        }
        
        return AnomalyResult(
            method_name=config.method.value,
            anomalies=anomaly_df,
            anomaly_scores=result['anomaly_scores'],
            anomaly_labels=result['anomaly_labels'],
            threshold=result.get('threshold', 0.5),
            statistics=statistics,
            parameters=config.parameters,
            execution_time=execution_time,
            model_info=result.get('model')
        )
    
    async def _preprocess_data(self, data: pd.DataFrame, config: AnomalyConfig) -> np.ndarray:
        """Preprocess data for anomaly detection"""
        # Handle missing values
        processed_data = data.fillna(data.mean())
        
        # Select numeric columns only
        numeric_columns = processed_data.select_dtypes(include=[np.number]).columns
        processed_data = processed_data[numeric_columns]
        
        # Apply preprocessing based on configuration
        preprocessing_config = config.preprocessing
        
        if preprocessing_config.get('scale', True):
            scaler_type = preprocessing_config.get('scaler_type', 'standard')
            
            if scaler_type == 'standard':
                self.scaler = StandardScaler()
            elif scaler_type == 'robust':
                self.scaler = RobustScaler()
            
            processed_data = self.scaler.fit_transform(processed_data)
        
        return processed_data
    
    async def _detect_statistical_anomalies(self, data: np.ndarray, config: AnomalyConfig) -> Dict[str, Any]:
        """Handle statistical anomaly detection"""
        # For multivariate data, use Mahalanobis distance
        if data.shape[1] > 1:
            return await self._detect_mahalanobis_anomalies(data, config)
        else:
            # For univariate data, use specified method
            method = config.parameters.get('method', 'zscore')
            data_series = pd.Series(data.flatten())
            
            if method == 'zscore':
                return await self.statistical_detector.detect_zscore_anomalies(data_series)
            elif method == 'modified_zscore':
                return await self.statistical_detector.detect_modified_zscore_anomalies(data_series)
            elif method == 'iqr':
                return await self.statistical_detector.detect_iqr_anomalies(data_series)
            else:
                raise ValueError(f"Unknown statistical method: {method}")
    
    async def _detect_mahalanobis_anomalies(self, data: np.ndarray, config: AnomalyConfig) -> Dict[str, Any]:
        """Mahalanobis distance based anomaly detection"""
        # Calculate covariance matrix
        cov_matrix = np.cov(data.T)
        
        # Calculate Mahalanobis distance
        mean = np.mean(data, axis=0)
        inv_cov = np.linalg.pinv(cov_matrix)
        
        mahal_distances = []
        for point in data:
            diff = point - mean
            mahal_dist = np.sqrt(diff.T @ inv_cov @ diff)
            mahal_distances.append(mahal_dist)
        
        mahal_distances = np.array(mahal_distances)
        
        # Determine threshold
        contamination = config.contamination
        threshold = np.percentile(mahal_distances, (1 - contamination) * 100)
        
        # Identify anomalies
        anomaly_labels = (mahal_distances > threshold).astype(int)
        
        # Normalize scores
        anomaly_scores = (mahal_distances - mahal_distances.min()) / (mahal_distances.max() - mahal_distances.min())
        
        return {
            'anomaly_scores': anomaly_scores,
            'anomaly_labels': anomaly_labels,
            'threshold': threshold,
            'mahalanobis_distances': mahal_distances,
            'num_anomalies': np.sum(anomaly_labels)
        }
    
    async def detect_ensemble_anomalies(self, data: pd.DataFrame, 
                                      configs: List[AnomalyConfig]) -> AnomalyResult:
        """Detect anomalies using ensemble of methods"""
        start_time = datetime.utcnow()
        
        # Preprocess data (use first config for preprocessing)
        processed_data = await self._preprocess_data(data, configs[0])
        
        # Run ensemble detection
        ensemble_result = await self.ensemble_detector.detect_ensemble_anomalies(processed_data, configs)
        
        execution_time = (datetime.utcnow() - start_time).total_seconds()
        
        # Create result dataframe
        anomaly_df = data.copy()
        anomaly_df['anomaly_score'] = ensemble_result['ensemble_scores']
        anomaly_df['is_anomaly'] = ensemble_result['ensemble_labels']
        
        # Add individual method scores
        for i, result in enumerate(ensemble_result['individual_results']):
            method_name = result['method'].value
            anomaly_df[f'{method_name}_score'] = result['scores']
            anomaly_df[f'{method_name}_label'] = result['labels']
        
        # Calculate statistics
        statistics = {
            'total_points': len(data),
            'anomalies_detected': ensemble_result['num_anomalies'],
            'anomaly_rate': np.mean(ensemble_result['ensemble_labels']),
            'num_methods': ensemble_result['num_methods'],
            'voting_method': ensemble_result['voting_method'],
            'score_statistics': {
                'mean': np.mean(ensemble_result['ensemble_scores']),
                'std': np.std(ensemble_result['ensemble_scores']),
                'min': np.min(ensemble_result['ensemble_scores']),
                'max': np.max(ensemble_result['ensemble_scores']),
                'median': np.median(ensemble_result['ensemble_scores'])
            }
        }
        
        return AnomalyResult(
            method_name='Ensemble',
            anomalies=anomaly_df,
            anomaly_scores=ensemble_result['ensemble_scores'],
            anomaly_labels=ensemble_result['ensemble_labels'],
            threshold=ensemble_result['threshold'],
            statistics=statistics,
            parameters={'methods': [config.method.value for config in configs]},
            execution_time=execution_time,
            model_info=ensemble_result
        )
    
    async def generate_anomaly_visualization(self, result: AnomalyResult) -> go.Figure:
        """Generate interactive anomaly visualization"""
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=['Anomaly Scores', 'Data Distribution', 'Time Series (if applicable)', 'Anomaly Details'],
            specs=[[{"secondary_y": False}, {"secondary_y": False}],
                   [{"secondary_y": False}, {"secondary_y": False}]]
        )
        
        # Anomaly scores
        normal_mask = result.anomaly_labels == 0
        anomaly_mask = result.anomaly_labels == 1
        
        fig.add_trace(
            go.Scatter(
                x=np.where(normal_mask)[0],
                y=result.anomaly_scores[normal_mask],
                mode='markers',
                name='Normal',
                marker=dict(color='blue', size=4)
            ),
            row=1, col=1
        )
        
        fig.add_trace(
            go.Scatter(
                x=np.where(anomaly_mask)[0],
                y=result.anomaly_scores[anomaly_mask],
                mode='markers',
                name='Anomaly',
                marker=dict(color='red', size=6)
            ),
            row=1, col=1
        )
        
        # Add threshold line
        fig.add_hline(
            y=result.threshold,
            line_dash="dash",
            line_color="green",
            row=1, col=1
        )
        
        # Score distribution
        fig.add_trace(
            go.Histogram(
                x=result.anomaly_scores,
                name='Score Distribution',
                opacity=0.7
            ),
            row=1, col=2
        )
        
        # If data has timestamp, create time series plot
        if hasattr(result.anomalies.index, 'to_datetime'):
            timestamps = result.anomalies.index
            
            # Plot first numeric column
            numeric_columns = result.anomalies.select_dtypes(include=[np.number]).columns
            if len(numeric_columns) > 0:
                first_col = numeric_columns[0]
                
                fig.add_trace(
                    go.Scatter(
                        x=timestamps[normal_mask],
                        y=result.anomalies[first_col].iloc[normal_mask],
                        mode='markers',
                        name='Normal Points',
                        marker=dict(color='blue', size=4)
                    ),
                    row=2, col=1
                )
                
                fig.add_trace(
                    go.Scatter(
                        x=timestamps[anomaly_mask],
                        y=result.anomalies[first_col].iloc[anomaly_mask],
                        mode='markers',
                        name='Anomalies',
                        marker=dict(color='red', size=8)
                    ),
                    row=2, col=1
                )
        
        # Anomaly statistics
        stats_text = f"""
        Total Points: {result.statistics['total_points']}
        Anomalies Detected: {result.statistics['anomalies_detected']}
        Anomaly Rate: {result.statistics['anomaly_rate']:.2%}
        Method: {result.method_name}
        Execution Time: {result.execution_time:.2f}s
        
        Score Statistics:
        Mean: {result.statistics['score_statistics']['mean']:.4f}
        Std: {result.statistics['score_statistics']['std']:.4f}
        Min: {result.statistics['score_statistics']['min']:.4f}
        Max: {result.statistics['score_statistics']['max']:.4f}
        """
        
        fig.add_annotation(
            text=stats_text,
            xref="paper", yref="paper",
            x=0.02, y=0.4,
            xanchor="left", yanchor="top",
            showarrow=False,
            font=dict(family="monospace", size=10),
            row=2, col=2
        )
        
        fig.update_layout(
            title=f'Anomaly Detection Results - {result.method_name}',
            showlegend=True,
            height=800
        )
        
        return fig
    
    async def evaluate_anomaly_detection(self, result: AnomalyResult, 
                                       true_labels: np.ndarray) -> Dict[str, Any]:
        """Evaluate anomaly detection performance against ground truth"""
        from sklearn.metrics import precision_score, recall_score, f1_score, roc_auc_score
        
        predicted_labels = result.anomaly_labels
        anomaly_scores = result.anomaly_scores
        
        # Calculate metrics
        precision = precision_score(true_labels, predicted_labels)
        recall = recall_score(true_labels, predicted_labels)
        f1 = f1_score(true_labels, predicted_labels)
        
        try:
            auc_score = roc_auc_score(true_labels, anomaly_scores)
        except ValueError:
            auc_score = None  # Can't calculate AUC if only one class present
        
        # Confusion matrix
        cm = confusion_matrix(true_labels, predicted_labels)
        
        return {
            'precision': precision,
            'recall': recall,
            'f1_score': f1,
            'auc_score': auc_score,
            'confusion_matrix': cm.tolist(),
            'classification_report': classification_report(true_labels, predicted_labels, output_dict=True)
        }